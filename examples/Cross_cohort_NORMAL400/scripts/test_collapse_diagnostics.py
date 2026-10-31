"""End-to-end test of 08_diagnose_collapse_mortality.py on synthetic CLM-FATES history.

Uses netCDF4 when installed; otherwise a tiny shim over scipy.io.netcdf_file (NetCDF3)
with the parts of the netCDF4 API the scripts use.
"""
import csv
import importlib.util
import sys
import tempfile
import types
import unittest
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent

try:
    import netCDF4  # noqa: F401
    HAVE_NC4 = True
except ImportError:
    HAVE_NC4 = False
    from scipy.io import netcdf_file

    class _Var:
        def __init__(self, v):
            self._v = v
            self.dimensions = tuple(v.dimensions)
            self.shape = tuple(v.shape)
            for k, val in v._attributes.items():
                setattr(self, k, val.decode() if isinstance(val, bytes) else val)

        def __getitem__(self, idx):
            return np.array(self._v.data[idx])

    class _Dim:
        def __init__(self, n):
            self.n = n

        def __len__(self):
            return self.n

    class Dataset:
        def __init__(self, path, mode="r"):
            self._f = netcdf_file(path, "r", mmap=False)
            self.variables = {k: _Var(v) for k, v in self._f.variables.items()}
            self.dimensions = {k: _Dim(n if n is not None else 0) for k, n in self._f.dimensions.items()}

        def __enter__(self):
            return self

        def __exit__(self, *a):
            self._f.close()

    sys.modules["netCDF4"] = types.SimpleNamespace(Dataset=Dataset, chartostring=None)


def write_nc(path, year, month, values):
    """values: {name: (dims, array_without_time, units)}; one monthly sample."""
    cum = np.cumsum([0, 31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30])
    ndays = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    start = (year - 1) * 365 + cum[month - 1]
    if HAVE_NC4:
        from netCDF4 import Dataset as W
        ds = W(str(path), "w")
        mk_dim, mk_var = ds.createDimension, lambda n, t, d: ds.createVariable(n, t, d)
    else:
        ds = netcdf_file(str(path), "w")
        mk_dim, mk_var = ds.createDimension, lambda n, t, d: ds.createVariable(n, t, d)
    mk_dim("time", None); mk_dim("lndgrid", 1); mk_dim("hist_interval", 2)
    mk_dim("fates_levpft", 3); mk_dim("fates_levscls", 4); mk_dim("fates_levscpf", 12)
    t = mk_var("time", "f8", ("time",)); t.units = "days since 0001-01-01 00:00:00"; t.calendar = "noleap"
    tb = mk_var("time_bounds", "f8", ("time", "hist_interval"))
    pm = mk_var("fates_pftmap_levscpf", "i4", ("fates_levscpf",))
    if HAVE_NC4:
        t[0] = start + ndays[month - 1]; tb[0, :] = [start, start + ndays[month - 1]]; pm[:] = np.repeat([1, 2, 3], 4)
    else:
        t[:] = [start + ndays[month - 1]]; tb[:] = [[start, start + ndays[month - 1]]]; pm[:] = np.repeat([1, 2, 3], 4)
    for name, (dims, arr, units) in values.items():
        v = mk_var(name, "f8", ("time",) + dims + ("lndgrid",))
        v.units = units
        a = np.asarray(arr, dtype=float).reshape((1,) + tuple({"fates_levpft": 3, "fates_levscls": 4, "fates_levscpf": 12}[d] for d in dims) + (1,))
        if HAVE_NC4:
            v[:] = a
        else:
            v[:] = a
    ds.close()


AD_MINIMAL = {"FATES_GPP", "FATES_NPP", "TLAI"}   # what the real AD400 cases wrote


def site_values(spin, month, minimal=False, all_dead=False):
    v = _site_values(spin, month)
    if all_dead:
        for k in ("FATES_VEGC_PF", "FATES_NPLANT_PF", "FATES_RECRUITMENT_PF", "FATES_NPP_PF"):
            d, a, u = v[k]; v[k] = (d, np.zeros_like(np.asarray(a, dtype=float)), u)
        v["FATES_VEGC"] = ((), [0.0], "kg m-2")
    return {k: x for k, x in v.items() if k in AD_MINIMAL} if minimal else v


def _site_values(spin, month):
    """Needleleaf PFT2 starves: storage and density decline to ~0 by year 8; PFT3 tiny but alive."""
    alive = max(0.0, 1.0 - (spin - 1) / 8.0) if spin <= 400 else 0.0
    winter = month in (12, 1, 2)
    n2 = 0.05 * alive + 1e-9                         # m-2
    vegc = np.array([0.0, 10.0 * alive, 0.05])       # kg m-2
    nplant = np.array([0.0, n2, 0.01])
    cst = np.zeros(12); cst[4:8] = 0.02 * alive / 4  # m-2 yr-1 (PFT2 size classes)
    bg = np.zeros(12); bg[4:8] = 0.002 * alive / 4; bg[8:12] = 0.0005
    canopy = np.full(12, 1.0)                        # must be ignored (split of total)
    frz = np.full(4, 0.001 * alive / 4)              # SZ only (no PFT detail)
    gpp = (0.0 if winter else 3e-8) * (alive + 0.01)
    return {
        "FATES_GPP": ((), [gpp], "kg m-2 s-1"),
        "FATES_NPP": ((), [gpp * 0.2 - 2e-9], "kg m-2 s-1"),
        "FATES_MAINT_RESP": ((), [gpp * 0.6 + 1e-9], "kg m-2 s-1"),
        "FATES_VEGC": ((), [vegc.sum()], "kg m-2"),
        "FATES_STOREC_TF": ((), [0.9 * alive + 0.01], "kg kg-1"),
        "BTRAN": ((), [0.3 if winter else 0.9], "unitless"),
        "TSA": ((), [258.0 if winter else 285.0], "K"),
        "TLAI": ((), [2.0 * alive], "m^2/m^2"),
        "FATES_NPLANT_PF": (("fates_levpft",), nplant, "m-2"),
        "FATES_VEGC_PF": (("fates_levpft",), vegc, "kg m-2"),
        "FATES_RECRUITMENT_PF": (("fates_levpft",), [0.0, 1e-4, 1e-4], "m-2 yr-1"),
        "FATES_NPP_PF": (("fates_levpft",), [0.0, gpp * 0.2 - 2e-9, 1e-10], "kg m-2 s-1"),
        "FATES_MORTALITY_CSTARV_SZPF": (("fates_levscpf",), cst, "m-2 yr-1"),
        "FATES_MORTALITY_BACKGROUND_SZPF": (("fates_levscpf",), bg, "m-2 yr-1"),
        "FATES_MORTALITY_CANOPY_SZPF": (("fates_levscpf",), canopy, "m-2 yr-1"),
        "FATES_MORTALITY_FREEZING_SZ": (("fates_levscls",), frz, "m-2 yr-1"),
    }


class CollapseDiagnosticsTest(unittest.TestCase):
    AD_YEARS, NO_YEARS = 40, 6
    AD_MINIMAL = False

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.cases, self.archive = root / "cases", root / "arch" / "archive"
        ad, no = "FI-Sod_AD", "FI-Sod_B01_FIXNC_NORMAL400"
        for case, start, ref in ((ad, "0001-01-01", ""), (no, "0401-01-01", ad)):
            d = self.cases / case; d.mkdir(parents=True)
            entries = f'<entry id="RUN_STARTDATE" value="{start}"/>' + (f'<entry id="RUN_REFCASE" value="{ref}"/>' if ref else "")
            (d / "env_run.xml").write_text(f"<file>{entries}</file>")
            (d / "user_nl_datm_streams").write_text(
                "CLM_USRDAT.FI-Sod:year_first = 2001\nCLM_USRDAT.FI-Sod:year_last = 2010\nCLM_USRDAT.FI-Sod:year_align = 1\n")
            hist = self.archive / case / "lnd" / "hist"; hist.mkdir(parents=True)
        for y in range(1, self.AD_YEARS + 1):
            for m in range(1, 13):
                write_nc(self.archive / ad / "lnd" / "hist" / f"{ad}.clm2.h0.{y:04d}-{m:02d}.nc", y, m, site_values(y, m, self.AD_MINIMAL))
        for k in range(self.NO_YEARS):
            y = 401 + k
            for m in range(1, 13):
                write_nc(self.archive / no / "lnd" / "hist" / f"{no}.clm2.h0.{y:04d}-{m:02d}.nc", y, m, site_values(y, m, all_dead=self.AD_MINIMAL))
        spec = importlib.util.spec_from_file_location("diag08", HERE / "08_diagnose_collapse_mortality.py")
        self.mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.mod)

    def tearDown(self):
        self.tmp.cleanup()

    def test_units(self):
        c = self.mod.convert
        self.assertEqual(c("kg m-2 s-1")[0], 86400e3)
        self.assertEqual(c("kg m-2")[0], 1000.0)
        self.assertEqual(c("m-2")[0], 1e4)
        self.assertEqual(c("m-2 yr-1")[:1] + (c("m-2 yr-1")[2],), (1e4, "ha-1 yr-1"))
        self.assertEqual(c("N/ha/yr")[0], 1.0)
        self.assertEqual(c("m^2/m^2")[0], 1.0)
        self.assertEqual(c("kg kg-1")[0], 1.0)
        self.assertEqual(c("K")[1], -273.15)

    def test_end_to_end(self):
        out = Path(self.tmp.name) / "out"
        code = self.mod.main(["--output-root", str(out), "--sites", "FI-Sod", "--workers", "1", "--first-years", "12",
                              "--archive-root", str(self.archive), "--cases-root", str(self.cases)])
        err = out / "FI-Sod" / "ERROR.txt"
        self.assertEqual(code, 0, err.read_text() if err.exists() else "")
        with (out / "collapse_summary.csv").open() as f:
            rows = list(csv.DictReader(f))
        r = rows[0]
        self.assertEqual(r["Status"], "OK")
        self.assertTrue(r["Focal_PFT"].startswith("2 needleleaf"), r["Focal_PFT"])
        self.assertEqual(int(r["Collapse_year"]), 9)            # VEGC_pft2 = 0 from year 9
        self.assertEqual(r["Dominant_mortality"], "CSTARV")
        self.assertNotIn("CANOPY", r["Mortality_types_found"])
        self.assertIn("FREEZING", r["Mortality_types_found"])
        self.assertAlmostEqual(float(r["Share_CSTARV_pct"]) + float(r["Share_BACKGROUND_pct"]) + float(r["Share_FREEZING_pct"]), 100, 3)
        self.assertIn("FATES_MORTALITY_HYDRAULIC_SZPF", r["Missing_suggested_vars"])
        ann = __import__("pandas").read_csv(out / "FI-Sod" / "FI-Sod_collapse_annual.csv")
        self.assertEqual(sorted(ann.SpinupYear)[:2], [1, 2])
        self.assertIn(401, set(ann.SpinupYear))
        y1 = ann[ann.SpinupYear == 1].iloc[0]
        self.assertAlmostEqual(y1["FATES_NPLANT_PF__pft2"], (0.05 + 1e-9) * 1e4, 3)   # m-2 -> ha-1
        self.assertAlmostEqual(y1["TSA_min"], 258.0 - 273.15, 6)
        self.assertAlmostEqual(y1["TLAI"], 2.0, 6)
        for tag in ("_04_collapse_diagnostics_full800.png", "_05_collapse_diagnostics_first12y.png"):
            p = out / "FI-Sod" / f"FI-Sod{tag}"
            self.assertTrue(p.is_file() and p.read_bytes()[:4] == b"\x89PNG", tag)
        self.assertTrue((out / "RUN_COMPLETE.json").is_file())
        self.assertIn("FATES_MORTALITY_CSTARV_SZPF", (out / "FI-Sod" / "FI-Sod_history_inventory.txt").read_text())


class MinimalADHistoryTest(CollapseDiagnosticsTest):
    """Real layout: AD wrote only GPP/NPP/TLAI; Normal has full output but all plants are dead."""
    AD_MINIMAL = True

    def test_units(self):
        pass

    def test_end_to_end(self):
        out = Path(self.tmp.name) / "out"
        code = self.mod.main(["--output-root", str(out), "--sites", "FI-Sod", "--workers", "1", "--first-years", "12",
                              "--archive-root", str(self.archive), "--cases-root", str(self.cases)])
        err = out / "FI-Sod" / "ERROR.txt"
        self.assertEqual(code, 0, err.read_text() if err.exists() else "")
        with (out / "collapse_summary.csv").open() as f:
            r = list(csv.DictReader(f))[0]
        self.assertEqual(r["Collapse_year"], "")                       # not determinable, not "1"
        self.assertIn("written only for spin-up years 401-406", r["Output_note"])
        self.assertIn("zero in all of them", r["Output_note"])
        self.assertGreater(float(r["GPP_year1_gC_m-2_d-1"]), 0)
        self.assertEqual(int(r["GPP_max_year"]), 1)


if __name__ == "__main__":
    unittest.main()
