"""Test 14_diagnose_site_anomalies.py on a synthetic target / reference pair.

Target: forcing temperature written in degC (should be flagged), one non-path namelist difference,
a different parameter file, vegetation gone from AD year 5, EC ET larger than precipitation.
Reference: same set-up with correct forcing, vegetation persists.
"""
import csv
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

import numpy as np

import test_collapse_diagnostics as tcd   # installs the netCDF4 shim when netCDF4 is absent  # noqa: F401

HERE = Path(__file__).resolve().parent
DAYS = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
CUM = np.concatenate([[0], np.cumsum(DAYS)])
Z = np.array([0.05, 0.3, 0.75, 1.5])
DZ = np.array([0.1, 0.4, 0.5, 1.0])


def load():
    spec = importlib.util.spec_from_file_location("m14", HERE / "14_diagnose_site_anomalies.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def nc(path, dims, time, tunits, variables, bounds=None):
    from scipy.io import netcdf_file
    ds = netcdf_file(str(path), "w")
    ds.createDimension("time", None)
    for d, n in dims.items():
        ds.createDimension(d, n)
    t = ds.createVariable("time", "f8", ("time",)); t.units = tunits; t.calendar = "noleap"; t[:] = time
    if bounds is not None:
        ds.createDimension("hist_interval", 2)
        b = ds.createVariable("time_bounds", "f8", ("time", "hist_interval")); b[:] = bounds
    for name, (vd, val, units) in variables.items():
        v = ds.createVariable(name, "f8", vd); v.units = units; v[:] = val
    ds.close()


def hist(path, year, month, scal, lay=None, pft=None):
    start = (year - 1) * 365 + CUM[month - 1]
    dims = {"lndgrid": 1, "levsoi": len(Z), "levgrnd": len(Z), "fates_levpft": 3}
    v = {k: (("time", "lndgrid"), np.array([[x]]), u) for k, (x, u) in scal.items()}
    v["ZSOI"] = (("levgrnd", "lndgrid"), Z.reshape(-1, 1), "m")
    v["DZSOI"] = (("levgrnd", "lndgrid"), DZ.reshape(-1, 1), "m")
    for k, (a, u) in (lay or {}).items():
        v[k] = (("time", "levsoi", "lndgrid"), np.asarray(a, float).reshape(1, -1, 1), u)
    for k, (a, u) in (pft or {}).items():
        v[k] = (("time", "fates_levpft", "lndgrid"), np.asarray(a, float).reshape(1, -1, 1), u)
    nc(path, dims, [start + DAYS[month - 1]], "days since 0001-01-01 00:00:00", v,
       bounds=[[start, start + DAYS[month - 1]]])


class SiteAnomalyTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.cases, self.arch, self.sites = self.root / "cases", self.root / "out" / "archive", self.root / "sites"
        for site, bad in (("TGT", True), ("REF", False)):
            self.make_site(site, bad)

    def tearDown(self):
        self.tmp.cleanup()

    def make_site(self, site, bad):
        ad, no = f"{site}_AD400", f"{site}_NORMAL400"
        fdir = self.root / "forcing" / site; fdir.mkdir(parents=True)
        files = []
        for y in (2001, 2002):
            for m in range(1, 13):
                n = DAYS[m - 1] * 8
                tK = 283.0 + 10 * np.sin((m - 4) / 12 * 2 * np.pi)
                p = fdir / f"{y}-{m:02d}.nc"
                nc(p, {"lndgrid": 1}, np.arange(n) / 8.0, f"days since {y}-{m:02d}-01 00:00:00",
                   {"TBOT": (("time", "lndgrid"), np.full((n, 1), tK - 273.15 if bad else tK), "K"),
                    "PRECTmms": (("time", "lndgrid"), np.full((n, 1), 1.0 / 86400), "mm/s"),
                    "FSDS": (("time", "lndgrid"), np.full((n, 1), 180.0), "W/m2"),
                    "QBOT": (("time", "lndgrid"), np.full((n, 1), 0.006), "kg/kg"),
                    "WIND": (("time", "lndgrid"), np.full((n, 1), 2.0), "m/s"),
                    "PSRF": (("time", "lndgrid"), np.full((n, 1), 95000.0), "Pa")})
                files.append(p)
        streams = ("<file id='stream'><stream_info name='CLM_USRDAT.ALL'><taxmode>cycle</taxmode><tintalgo>linear</tintalgo>"
                   "<offset>0</offset><year_first>2001</year_first><year_last>2002</year_last><year_align>1</year_align>"
                   "<datafiles>" + "".join(f"<file>{p}</file>" for p in files) + "</datafiles><datavars>"
                   + "".join(f"<var>{v} Sa_x</var>" for v in ("TBOT", "PRECTmms", "FSDS", "QBOT", "WIND", "PSRF"))
                   + "</datavars></stream_info></file>")
        surf = self.root / "surf" / f"surfdata_{site}.nc"; surf.parent.mkdir(exist_ok=True)
        from scipy.io import netcdf_file
        ds = netcdf_file(str(surf), "w"); ds.createDimension("lsmpft", 3); ds.createDimension("x", 1)
        for k, val in (("PCT_NATVEG", [100.0]), ("PCT_GLACIER", [0.0]), ("ORGANIC", [5.0])):
            v = ds.createVariable(k, "f8", ("x",)); v[:] = val
        v = ds.createVariable("PCT_NAT_PFT", "f8", ("lsmpft",)); v[:] = [0.0, 0.0, 100.0]
        ds.close()
        par = self.root / "params" / f"p_{site}.json"; par.parent.mkdir(exist_ok=True)
        par.write_text(json.dumps({"parameters": {"fates_leaf_slatop": {"data": [0.012, 0.03 if bad else 0.02, 0.03]}}}))
        for case, ref in ((ad, ""), (no, ad)):
            d = self.cases / case; (d / "CaseDocs").mkdir(parents=True)
            run = self.root / "out" / case / "run"; run.mkdir(parents=True)
            entries = (f'<entry id="RUN_STARTDATE" value="0001-01-01"/><entry id="RUNDIR" value="{run}"/>'
                       f'<entry id="DATM_MODE" value="CLM1PT"/>' + (f'<entry id="RUN_REFCASE" value="{ref}"/>' if ref else ""))
            (d / "env_run.xml").write_text(f"<file>{entries}</file>")
            cst = 2 if bad else 1
            (run / "lnd_in").write_text(
                f"&clm_inparm\n fsurdat = '{surf}'\n fates_paramfile = '{par}'\n use_fates = .true.\n"
                f" fates_cstarvation_model = {cst}\n hist_nhtfrq = 0\n/\n")
            (run / "datm.streams.xml").write_text(streams)
            (d / "user_nl_clm").write_text("hist_mfilt = 1\n")
            (self.arch / case / "lnd" / "hist").mkdir(parents=True)
        for y in range(1, 13):
            for m in range(1, 13):
                alive = not (bad and y >= 5)
                hist(self.arch / ad / "lnd" / "hist" / f"{ad}.clm2.h0.{y:04d}-{m:02d}.nc", y, m,
                     {"TLAI": (3.0 if alive else 0.0, "m2/m2"), "FATES_GPP": ((4e-5 if alive else 0.0) / 86.4, "kg m-2 s-1"),
                      "FATES_NPP": ((2e-5 if alive else 0.0) / 86.4, "kg m-2 s-1"), "TOTSOMC": (1000.0 if alive else 10.0, "gC/m^2"),
                      "TWS": (5000.0, "mm"), "H2OSNO": (0.0, "mm")})
        for y in range(401, 405):
            for m in range(1, 13):
                summer = m in (5, 6, 7, 8, 9)
                hist(self.arch / no / "lnd" / "hist" / f"{no}.clm2.h0.{y:04d}-{m:02d}.nc", y, m,
                     {"FATES_GPP": ((1.0 if (summer and not bad) else 0.3) / 86400000, "kg m-2 s-1"),
                      "TLAI": (2.0 if summer else 0.2, "m2/m2"), "BTRAN": (0.1 if bad else 0.8, "unitless"),
                      "RAIN": (1.0 / 86400, "mm/s"), "SNOW": (0.0, "mm/s"), "QVEGT": (0.6 / 86400, "mm/s"),
                      "QVEGE": (0.1 / 86400, "mm/s"), "QSOIL": (0.2 / 86400, "mm/s"), "ZWT": (8.0, "m"),
                      "FATES_DAYSINCE_COLDLEAFON": ((150000.0 + 30 * m) if bad else 30.0 * m, "days")},
                     lay={"H2OSOI": ([0.1, 0.12, 0.15, 0.2], "mm3/mm3")},
                     pft={"FATES_GPP_PF": ([0.0, 0.0, 1e-8], "kg m-2 s-1"),
                          "FATES_NOCOMP_PATCHAREA_PF": ([0.0, 0.7, 0.3], "m2 m-2"),
                          "FATES_CANOPYCROWNAREA_PF": ([0.0, 0.5, 0.3], "m2 m-2"),
                          "FATES_LEAFC_PF": ([0.0, 0.0 if bad else 0.1, 0.05], "kg m-2")})
        raw = self.sites / site / "forcing" / "raw"; raw.mkdir(parents=True)
        with (raw / f"AMF_{site}_FLUXNET_FULLSET_HH_2001-2002.csv").open("w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["TIMESTAMP_START", "NEE_VUT_REF", "GPP_NT_VUT_REF", "TA_F", "SW_IN_F", "P_F", "LE_F_MDS", "SWC_F_MDS_1"])
            for y in (2001, 2002):
                for doy in range(365):
                    m = int(np.searchsorted(CUM, doy, side="right"))
                    dd = doy - CUM[m - 1] + 1
                    ta = 10 * np.sin((m - 4) / 12 * 2 * np.pi) + 9.85
                    for h in range(24):
                        le = (3.0 if bad else 0.8) * 2.45e6 / 86400       # 3 mm/d ET at the target
                        w.writerow([f"{y}{m:02d}{dd:02d}{h:02d}00", -1.0, 5.0 if m in (5, 6, 7, 8, 9) else 0.5,
                                    round(ta, 3), 180.0, 1.0 / 24, round(le, 3), 15.0])

    def test_end_to_end(self):
        m = load()
        out = self.root / "result"
        rc = m.main(["--output-root", str(out), "--allow-scratch-output", "--ad-years", "12",
                     "--archive-root", str(self.arch), "--cases-root", str(self.cases), "--sites-root", str(self.sites),
                     "--specs", "TGT:TGT_NORMAL400:REF:REF_NORMAL400"])
        self.assertEqual(rc, 0)
        summ = list(csv.DictReader((out / "site_anomaly_summary.csv").open()))
        self.assertEqual(summ[0]["Status"], "OK", summ[0].get("Errors"))
        self.assertEqual(summ[0]["AD_collapse_year"], "5")
        txt = (out / "TGT" / "TGT_findings.txt").read_text()
        self.assertIn("looks like degC", txt)
        self.assertIn("T_forcing_minus_EC_C -273", txt)
        self.assertIn("forcing does not match the tower", txt)
        self.assertIn("vegetation gone from AD year 5", txt)
        self.assertIn("vegetation persists", txt)
        self.assertIn("EC ET exceeds precipitation", txt)
        self.assertIn("water-stressed", txt)
        self.assertIn("PFT 2: patch area 0.70", txt)
        self.assertIn("leafless all year", txt)
        self.assertIn("never cold", txt)
        self.assertTrue((out / "TGT" / "TGT_reference_REF_normal_seasonal.csv").is_file())
        diff = list(csv.DictReader((out / "TGT" / "TGT_setup_diff.csv").open()))
        real = {(d["section"], d["key"]) for d in diff if d["differs"] == "True" and not d["note"].startswith(("site", "path"))}
        self.assertIn(("lnd_in_AD", "fates_cstarvation_model"), real)
        self.assertIn(("parameters", "fates_leaf_slatop"), real)
        self.assertNotIn(("lnd_in_AD", "fsurdat"), real)            # site-specific name only
        self.assertFalse(any(d["section"] == "surface" and d["differs"] == "True" for d in diff))
        fc = {r["check"]: r for r in csv.DictReader((out / "TGT" / "TGT_forcing_checks.csv").open())}
        self.assertEqual(fc["TBOT"]["status"], "FAIL")
        self.assertEqual(fc["PRECTmms"]["status"], "ok")
        self.assertAlmostEqual(float(fc["PRECTmms"]["value"]), 365.0, delta=1.0)
        seas = list(csv.DictReader((out / "TGT" / "TGT_normal_seasonal.csv").open()))
        self.assertEqual(len(seas), 12)
        self.assertAlmostEqual(float(seas[5]["EC_ET_mm_day"]), 3.0, places=2)
        self.assertAlmostEqual(float(seas[5]["EC_P_mm_day"]), 1.0, places=2)
        for k in ("01_forcing_vs_EC", "02_AD_first_years", "03_seasonal_water_carbon"):
            self.assertTrue((out / "TGT" / f"TGT_{k}.png").is_file(), k)

    def test_dead_months(self):
        import pandas as pd
        m = load()
        c = pd.DataFrame({"Month": range(1, 13), "EC_GPP": [5.0] * 12, "GPP_gC_m2_d": [0.0] * 12, "TLAI": [0.0] * 12,
                          "BTRAN": [0.0] * 12})
        self.assertTrue(all("vegetation dead" in r[-1] for r in m.classify_months(c)))

    def test_parse_nml_and_times(self):
        m = load()
        d = m.parse_nml("&a\n x = 1\n y = 'p/q.nc'\n z = 1, 2,\n   3\n/\n&b\n w = .true. ! c\n/\n")
        self.assertEqual(d, {"x": "1", "y": "'p/q.nc'", "z": "1, 2, 3", "w": ".true."})


if __name__ == "__main__":
    unittest.main()
