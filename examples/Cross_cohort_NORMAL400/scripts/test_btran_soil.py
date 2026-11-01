"""Test 10_diagnose_btran_soil.py on synthetic layered CLM-FATES history."""
import csv
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

import numpy as np

import test_collapse_diagnostics as tcd   # installs the netCDF4 shim when netCDF4 is absent

HERE = Path(__file__).resolve().parent
Z = np.array([0.01, 0.04, 0.09, 0.16, 0.26, 0.40, 0.58, 0.80])
DZ = np.array([0.02, 0.04, 0.06, 0.08, 0.12, 0.16, 0.20, 0.24])
NSOI, NGRND, NPFT = 6, 8, 3
WATSAT, SUCSAT, BSW = 0.45, 100.0, 6.0
SMPSO, SMPSC = -66000.0, -255000.0
ROOT = np.array([0.6, 0.4, 0.0, 0.0, 0.0, 0.0])       # roots only in the top 6 cm


def state(month, dry_top):
    winter = month in (12, 1, 2, 3)
    liq = np.full(NSOI, 0.35)
    if dry_top:
        liq[:2] = 0.13                                # dry-ish topsoil where all roots are (w ~ 0.44)
    ice = np.zeros(NSOI)
    T = np.full(NGRND, 285.0)
    if winter:
        ice[:3] = 0.25; liq[:3] = 0.03; T[:4] = 265.0
    eff = np.maximum(WATSAT - ice, 0.01)
    s = np.clip(liq / eff, 0.01, 1)
    smp = np.maximum(-SUCSAT * s ** (-BSW), SMPSC)
    w = np.clip(eff / WATSAT * (smp - SMPSC) / (SMPSO - SMPSC), 0, 1)
    gate = ((T[:NSOI] - 273.15 > -2) & (liq > 0)).astype(float)
    return liq, ice, T, float(np.sum(ROOT * w * gate))


def write(path, year, month, area, dry_top):
    from scipy.io import netcdf_file
    cum = np.cumsum([0, 31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30]); nd = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    start = (year - 1) * 365 + cum[month - 1]
    liq, ice, T, btran = state(month, dry_top)
    ds = netcdf_file(str(path), "w")
    for d, n in (("time", None), ("lndgrid", 1), ("hist_interval", 2), ("levsoi", NSOI), ("levgrnd", NGRND), ("fates_levpft", NPFT)):
        ds.createDimension(d, n)
    t = ds.createVariable("time", "f8", ("time",)); t.units = "days since 0001-01-01 00:00:00"; t.calendar = "noleap"
    t[:] = [start + nd[month - 1]]
    tb = ds.createVariable("time_bounds", "f8", ("time", "hist_interval")); tb[:] = [[start, start + nd[month - 1]]]
    for n, v in (("ZSOI", Z), ("DZSOI", DZ), ("WATSAT", np.full(NGRND, WATSAT)), ("SUCSAT", np.full(NGRND, SUCSAT)),
                 ("BSW", np.full(NGRND, BSW))):
        x = ds.createVariable(n, "f8", ("levgrnd", "lndgrid")); x[:] = v.reshape(NGRND, 1); x.units = "m"
    def tv(n, dims, val, units):
        x = ds.createVariable(n, "f8", ("time",) + dims + ("lndgrid",)); x.units = units
        x[:] = np.asarray(val, float).reshape((1,) + tuple({"levsoi": NSOI, "levgrnd": NGRND, "fates_levpft": NPFT}[d] for d in dims) + (1,))
    tv("BTRAN", (), [btran * area], "unitless")
    tv("FATES_GPP", (), [1e-8 * btran * area], "kg m-2 s-1")
    tv("TSA", (), [270.0 if month in (12, 1, 2) else 288.0], "K")
    tv("SOILLIQ", ("levsoi",), liq * DZ[:NSOI] * 1000.0, "kg/m2")
    tv("SOILICE", ("levsoi",), ice * DZ[:NSOI] * 917.0, "kg/m2")
    tv("TSOI", ("levgrnd",), T, "K")
    tv("FATES_FROOTC_SL", ("levsoi",), ROOT / DZ[:NSOI] * 0.01, "kg m-3")
    tv("FATES_NOCOMP_PATCHAREA_PF", ("fates_levpft",), [0.0, area, 0.0], "m2 m-2")
    tv("FATES_VEGC_PF", ("fates_levpft",), [0.0, 1.0, 0.0], "kg m-2")
    ds.close()


class BtranSoilTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.cases, self.archive = root / "cases", root / "arch" / "archive"
        prm = root / "fates_params.json"
        prm.write_text(json.dumps({"parameters": {
            "fates_pftname": {"data": ["broadleaf_evergreen_tropical_tree", "needleleaf_evergreen_extratrop_tree", "c3_grass"]},
            "fates_nonhydro_smpso": {"data": [SMPSO] * 3}, "fates_nonhydro_smpsc": {"data": [SMPSC] * 3}}}))
        for case, area, dry in (("SITE_A_DIAG5", 1.0, True), ("SITE_B_NORMAL", 0.4, False)):
            d = self.cases / case; (d / "CaseDocs").mkdir(parents=True)
            (d / "env_run.xml").write_text('<file><entry id="RUN_STARTDATE" value="0001-01-01"/></file>')
            (d / "CaseDocs" / "lnd_in").write_text(f"&fates_inparm\n fates_paramfile = '{prm}'\n/\n")
            h = self.archive / case / "lnd" / "hist"; h.mkdir(parents=True)
            for y in range(1, 7):
                for m in range(1, 13):
                    write(h / f"{case}.clm2.h0.{y:04d}-{m:02d}.nc", y, m, area, dry)
        spec = importlib.util.spec_from_file_location("btran10", HERE / "10_diagnose_btran_soil.py")
        self.mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(self.mod)

    def tearDown(self):
        self.tmp.cleanup()

    def test_end_to_end(self):
        out = Path(self.tmp.name) / "out"
        code = self.mod.main(["--output-root", str(out), "--years", "5", "--max-depth", "1",
                              "--cases", "A:SITE_A_DIAG5:first50", "B:SITE_B_NORMAL:last50",
                              "--archive-root", str(self.archive), "--cases-root", str(self.cases)])
        for lab in ("A", "B"):
            e = out / lab / "ERROR.txt"
            self.assertFalse(e.exists(), e.read_text() if e.exists() else "")
        self.assertEqual(code, 0)
        with (out / "btran_soil_summary.csv").open() as f:
            rows = {r["Label"]: r for r in csv.DictReader(f)}
        a, b = rows["A"], rows["B"]
        self.assertEqual(a["Years"], "1-5"); self.assertEqual(b["Years"], "2-6")
        self.assertTrue(a["Dominant_PFT"].startswith("2 needleleaf"))
        self.assertAlmostEqual(float(a["BTRAN_est_vegetated_JJA"]), float(a["BTRAN_model_JJA"]), 4)
        self.assertEqual(a["Estimate_vs_model"], "estimate matches model BTRAN")
        self.assertIn("dry soil", a["Most_limiting_JJA"])
        self.assertGreater(float(a["BTRAN_model_JJA"]), 0.3); self.assertLess(float(a["BTRAN_model_JJA"]), 0.6)
        self.assertIn("no soil limitation", b["Most_limiting_JJA"])
        self.assertAlmostEqual(float(a["Root_depth_90pct_m"]), 0.06, 6)
        self.assertAlmostEqual(float(a["Root_frac_top10cm"]), 1.0, 6)
        self.assertAlmostEqual(float(b["Vegetated_patch_area_frac"]), 0.4, 6)
        self.assertIn("site average dilutes", b["Estimate_vs_model"])
        self.assertEqual(float(a["smpso_mm"]), SMPSO)
        for lab in ("A", "B"):
            for tag in ("_06_btran_soil_timeseries.png", "_07_btran_soil_profiles.png"):
                self.assertEqual((out / lab / f"{lab}{tag}").read_bytes()[:4], b"\x89PNG")
        self.assertTrue((out / "ALL_CASES_08_btran_soil_comparison.png").is_file())
        mon = __import__("pandas").read_csv(out / "A" / "A_btran_soil_monthly.csv")
        winter = mon[mon.Month == 1]
        self.assertTrue((winter["BTRAN_est"] < 1e-9).all())          # frozen topsoil closes the gate


if __name__ == "__main__":
    unittest.main()
