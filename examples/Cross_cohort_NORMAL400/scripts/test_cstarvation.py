"""Test 12_check_cstarvation.py: observed mortality generated with the FATES formula must be recovered."""
import csv
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

import numpy as np

import test_collapse_diagnostics as tcd   # noqa: F401  (netCDF4 shim)

HERE = Path(__file__).resolve().parent
NPFT, NSCLS = 3, 4


def ratio(month):
    # storage / leaf C: full (1.2) in late summer, drawn down to 0.6 by March
    return {1: 0.8, 2: 0.7, 3: 0.6, 4: 0.7, 5: 0.9, 6: 1.05, 7: 1.15, 8: 1.2, 9: 1.2, 10: 1.1, 11: 1.0, 12: 0.9}[month]


def write(path, year, month, pft, leafc_kg, n, cstarv_on):
    from scipy.io import netcdf_file
    cum = np.cumsum([0, 31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30]); nd = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    s0 = (year - 1) * 365 + cum[month - 1]
    fr = ratio(month)
    rate = 0.6 * max(0.0, 1.0 - fr) if cstarv_on else 0.0          # yr-1
    ds = netcdf_file(str(path), "w")
    for d, k in (("time", None), ("lndgrid", 1), ("hist_interval", 2), ("fates_levpft", NPFT), ("fates_levscls", NSCLS),
                 ("fates_levscpf", NPFT * NSCLS)):
        ds.createDimension(d, k)
    t = ds.createVariable("time", "f8", ("time",)); t.units = "days since 0001-01-01 00:00:00"; t.calendar = "noleap"; t[:] = [s0 + nd[month - 1]]
    tb = ds.createVariable("time_bounds", "f8", ("time", "hist_interval")); tb[:] = [[s0, s0 + nd[month - 1]]]
    pm = ds.createVariable("fates_pftmap_levscpf", "i4", ("fates_levscpf",)); pm[:] = np.repeat(np.arange(1, NPFT + 1), NSCLS)
    def pv(name, val, units):
        x = ds.createVariable(name, "f8", ("time", "fates_levpft", "lndgrid")); x.units = units
        a = np.zeros(NPFT); a[pft - 1] = val; x[:] = a.reshape(1, NPFT, 1)
    pv("FATES_NPLANT_PF", n, "m-2"); pv("FATES_LEAFC_PF", leafc_kg, "kg m-2"); pv("FATES_STOREC_PF", fr * leafc_kg, "kg m-2")
    pv("FATES_VEGC_PF", 10 * leafc_kg, "kg m-2"); pv("FATES_NOCOMP_PATCHAREA_PF", 1.0, "m2 m-2")
    sz = np.zeros(NPFT * NSCLS); sz[(pft - 1) * NSCLS:(pft - 1) * NSCLS + 2] = rate * n / 2
    x = ds.createVariable("FATES_MORTALITY_CSTARV_SZPF", "f8", ("time", "fates_levscpf", "lndgrid")); x.units = "m-2 yr-1"
    x[:] = sz.reshape(1, -1, 1)
    x = ds.createVariable("FATES_STOREC_TF", "f8", ("time", "lndgrid")); x.units = "kg kg-1"; x[:] = [[fr / 1.2]]
    ds.close()


class CstarvationCheckTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.cases, self.archive = root / "cases", root / "arch" / "archive"
        prm = root / "params.json"
        prm.write_text(json.dumps({"parameters": {
            "fates_pftname": {"data": ["bet", "needleleaf_evergreen_extratrop_tree", "broadleaf_colddecid"]},
            "fates_mort_scalar_cstarvation": {"data": [0.6, 0.6, 0.6]},
            "fates_mort_upthresh_cstarvation": {"data": [1.0, 1.0, 1.0]},
            "fates_alloc_storage_cushion": {"data": [1.2, 1.2, 1.2]},
            "fates_leaf_slatop": {"data": [0.012, 0.005, 0.03]},
            "fates_turnover_leaf_canopy": {"data": [[1.5, 4.0, 1.0]]}}}))
        for case, pft, on in (("NET_DIAG", 2, True), ("BDT_NORMAL", 3, False)):
            d = self.cases / case; (d / "CaseDocs").mkdir(parents=True)
            (d / "env_run.xml").write_text('<file><entry id="RUN_STARTDATE" value="0001-01-01"/></file>')
            (d / "CaseDocs" / "lnd_in").write_text(
                "&clm_inparm\n fates_cstarvation_model = 'linear'\n fates_leafresp_model = 'ryan1991'\n use_fates_dbh_init = .false.\n/\n"
                f"&fates_inparm\n fates_paramfile = '{prm}'\n/\n")
            h = self.archive / case / "lnd" / "hist"; h.mkdir(parents=True)
            for y in range(1, 4):
                for m in range(1, 13):
                    write(h / f"{case}.clm2.h0.{y:04d}-{m:02d}.nc", y, m, pft, 0.05, 0.2, on)
        spec = importlib.util.spec_from_file_location("cs12", HERE / "12_check_cstarvation.py")
        self.mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(self.mod)

    def tearDown(self):
        self.tmp.cleanup()

    def test_end_to_end(self):
        out = Path(self.tmp.name) / "out"
        code = self.mod.main(["--output-root", str(out), "--years", "3", "--cases", "NET:NET_DIAG:first50", "BDT:BDT_NORMAL:last50",
                              "--archive-root", str(self.archive), "--cases-root", str(self.cases)])
        self.assertEqual(code, 0)
        with (out / "cstarvation_check_summary.csv").open() as f:
            rows = {r["Label"]: r for r in csv.DictReader(f)}
        net, bdt = rows["NET"], rows["BDT"]
        self.assertAlmostEqual(float(net["r_leafC"]), 1.0, 6)
        self.assertAlmostEqual(float(net["slope_obs_vs_pred_leafC"]), 1.0, 6)
        self.assertAlmostEqual(float(net["r_TF"]), 1.0, 6)
        self.assertAlmostEqual(float(net["share_months_frac_below_upthresh"]), 6 / 12, 6)
        self.assertAlmostEqual(float(net["frac_min"]), 0.6, 6)
        self.assertEqual(net["nml_fates_cstarvation_model"], "linear")
        self.assertEqual(net["nml_fates_leafresp_model"], "ryan1991")
        self.assertEqual(float(net["param_fates_alloc_storage_cushion"]), 1.2)
        self.assertEqual(float(net["param_fates_leaf_slatop"]), 0.005)
        self.assertIn("SZPF", net["Observed_source"])
        self.assertEqual(float(bdt["mean_observed_yr"]), 0.0)
        for n in ("CS_12_NET.png", "CS_12_BDT.png", "CS_12_all_cases_scatter.png"):
            self.assertEqual((out / n).read_bytes()[:4], b"\x89PNG", n)


if __name__ == "__main__":
    unittest.main()
