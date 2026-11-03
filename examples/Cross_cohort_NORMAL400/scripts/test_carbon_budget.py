"""Test 11_diagnose_carbon_budget.py on two synthetic single-PFT cases."""
import csv
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

import numpy as np

import test_collapse_diagnostics as tcd   # noqa: F401  (installs the netCDF4 shim when needed)

HERE = Path(__file__).resolve().parent
NPFT = 3
KGS = 1.0 / (1000.0 * 86400.0)            # 1 g C m-2 d-1 in kg m-2 s-1


def write(path, year, month, pft, n, leafc_g, gpp_g, mr_g, store_g):
    from scipy.io import netcdf_file
    cum = np.cumsum([0, 31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30]); nd = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    s0 = (year - 1) * 365 + cum[month - 1]
    ds = netcdf_file(str(path), "w")
    for d, k in (("time", None), ("lndgrid", 1), ("hist_interval", 2), ("fates_levpft", NPFT)):
        ds.createDimension(d, k)
    t = ds.createVariable("time", "f8", ("time",)); t.units = "days since 0001-01-01 00:00:00"; t.calendar = "noleap"; t[:] = [s0 + nd[month - 1]]
    tb = ds.createVariable("time_bounds", "f8", ("time", "hist_interval")); tb[:] = [[s0, s0 + nd[month - 1]]]
    def sv(name, val, units):
        x = ds.createVariable(name, "f8", ("time", "lndgrid")); x.units = units; x[:] = [[val]]
    def pv(name, val, units):
        x = ds.createVariable(name, "f8", ("time", "fates_levpft", "lndgrid")); x.units = units
        a = np.zeros(NPFT); a[pft - 1] = val; x[:] = a.reshape(1, NPFT, 1)
    npp = gpp_g - mr_g - 0.1 * gpp_g
    sv("FATES_GPP", gpp_g * KGS, "kg m-2 s-1"); sv("FATES_NPP", npp * KGS, "kg m-2 s-1")
    sv("FATES_MAINT_RESP", mr_g * KGS, "kg m-2 s-1"); sv("FATES_GROWTH_RESP", 0.1 * gpp_g * KGS, "kg m-2 s-1")
    sv("FATES_LEAFMAINTAR", 0.5 * mr_g * KGS, "kg m-2 s-1"); sv("FATES_FROOTMAINTAR", 0.3 * mr_g * KGS, "kg m-2 s-1")
    sv("FATES_LSTEMMAINTAR", 0.2 * mr_g * KGS, "kg m-2 s-1")
    sv("FATES_LEAFC", leafc_g / 1000.0, "kg m-2"); sv("FATES_LAI", leafc_g * 0.012, "m2 m-2")
    sv("FATES_STOREC_TF", 0.8, "kg kg-1")
    pv("FATES_NPLANT_PF", n, "m-2"); pv("FATES_LEAFC_PF", leafc_g / 1000.0, "kg m-2"); pv("FATES_GPP_PF", gpp_g * KGS, "kg m-2 s-1")
    pv("FATES_NPP_PF", npp * KGS, "kg m-2 s-1"); pv("FATES_STOREC_PF", store_g / 1000.0, "kg m-2")
    pv("FATES_VEGC_PF", 10 * leafc_g / 1000.0, "kg m-2"); pv("FATES_NOCOMP_PATCHAREA_PF", 1.0, "m2 m-2")
    pv("FATES_CANOPYCROWNAREA_PF", min(1.0, n * 0.5), "m2 m-2")
    ds.close()


class CarbonBudgetTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.cases, self.archive = root / "cases", root / "arch" / "archive"
        prm = root / "params.json"
        prm.write_text(json.dumps({"parameters": {
            "fates_pftname": {"dims": ["fates_pft"], "data": ["bet", "needleleaf_evergreen_extratrop_tree", "broadleaf_colddecid"]},
            "fates_leaf_vcmax25top": {"dims": ["fates_leafage_class", "fates_pft"], "units": "umol", "data": [[50, 62, 58]]},
            "fates_alloc_storage_cushion": {"dims": ["fates_pft"], "data": [1.2, 1.2, 1.2]},
            "fates_leaf_slatop": {"dims": ["fates_pft"], "data": [0.012, 0.01, 0.03]},
            "fates_grperc": {"dims": ["fates_pft"], "data": [0.11, 0.11, 0.11]}}}))
        # needleleaf: winter MR exceeds GPP; broadleaf: positive
        specs = {"NET_DIAG": (2, 0.2, 30.0, lambda m: 2.0 if m in (6, 7, 8) else 0.0, 0.6, 20.0),
                 "BDT_NORMAL": (3, 0.05, 200.0, lambda m: 8.0 if m in (6, 7, 8) else 0.0, 1.0, 300.0)}
        for case, (pft, n, leafc, gppf, mr, store) in specs.items():
            d = self.cases / case; (d / "CaseDocs").mkdir(parents=True)
            (d / "env_run.xml").write_text('<file><entry id="RUN_STARTDATE" value="0001-01-01"/></file>')
            (d / "CaseDocs" / "lnd_in").write_text(f"&clm_inparm\n use_fates_dbh_init = .false.\n use_fates_nocomp = .true.\n/\n"
                                                    f"&fates_inparm\n fates_paramfile = '{prm}'\n/\n")
            h = self.archive / case / "lnd" / "hist"; h.mkdir(parents=True)
            for y in range(1, 7):
                for m in range(1, 13):
                    write(h / f"{case}.clm2.h0.{y:04d}-{m:02d}.nc", y, m, pft, n, leafc, gppf(m), mr, store)
        spec = importlib.util.spec_from_file_location("cb11", HERE / "11_diagnose_carbon_budget.py")
        self.mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(self.mod)

    def tearDown(self):
        self.tmp.cleanup()

    def test_end_to_end(self):
        out = Path(self.tmp.name) / "out"
        code = self.mod.main(["--output-root", str(out), "--years", "5",
                              "--cases", "NET:NET_DIAG:first50", "BDT:BDT_NORMAL:last50", "MISSING:NO_SUCH_CASE",
                              "--archive-root", str(self.archive), "--cases-root", str(self.cases)])
        self.assertEqual(code, 0)
        with (out / "carbon_budget_summary.csv").open() as f:
            rows = {r["Label"]: r for r in csv.DictReader(f)}
        net, bdt, miss = rows["NET"], rows["BDT"], rows["MISSING"]
        self.assertEqual(miss["Status"], "FAILED")
        self.assertTrue(net["Focal_PFT"].startswith("2 needleleaf"))
        self.assertEqual(net["Single_PFT_site"], "True")
        self.assertAlmostEqual(float(net["plants_ha_first5y"]), 2000.0, 6)
        self.assertAlmostEqual(float(net["GPP_per_kgleafC_d_JJA"]), 2.0 / 0.030, 4)       # g C d-1 per kg leaf C
        self.assertAlmostEqual(float(net["MR_per_kgleafC_d_DJF"]), 0.6 / 0.030, 4)
        self.assertAlmostEqual(float(net["biomass_gC_plant_first5y"]), 300.0 / 0.2, 4)
        self.assertAlmostEqual(float(net["share_MR leaf"]) * float(net["GPP_gC_m2_d"]), 0.3, 6)
        self.assertGreater(float(net["MR_over_GPP"]), 1.0)                                 # carbon-negative needleleaf
        self.assertLess(float(bdt["MR_over_GPP"]), 1.0)
        self.assertAlmostEqual(float(net["winter_reserve_ratio_median"]), (20 / 0.2) / ((0.6 + 0) / 0.2 * 90), 4)
        self.assertEqual(net["nml_use_fates_dbh_init"], ".false.")
        self.assertEqual(net["use_fates_dbh_init_option_present"], "True")
        with (out / "parameter_differences.csv").open() as f:
            prm = [r["parameter"] for r in csv.DictReader(f)]
        self.assertEqual(prm[:2], ["fates_leaf_vcmax25top", "fates_leaf_slatop"] if prm[0] == "fates_leaf_vcmax25top"
                         else ["fates_leaf_slatop", "fates_leaf_vcmax25top"])
        self.assertNotIn("fates_alloc_storage_cushion", prm)
        self.assertNotIn("fates_grperc", prm)
        for n in ("CB_09_trajectories.png", "CB_10_seasonal.png", "CB_11_carbon_use.png"):
            self.assertEqual((out / n).read_bytes()[:4], b"\x89PNG", n)


if __name__ == "__main__":
    unittest.main()
