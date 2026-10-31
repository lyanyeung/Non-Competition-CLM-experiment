import csv
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np
import pandas as pd
from netCDF4 import Dataset

HERE = Path(__file__).resolve().parent
def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module

fig = load("icos38", HERE / "21_icos38_full_sequence.py")
ad_audit = load("ad_audit", HERE / "24_audit_ad_nee_histories.py")
core_path = HERE / "15_plot_AD400_NORMAL400_convergence_and_EC.py"
if not core_path.exists():
    core_path = HERE.parents[1] / "Batch03_10/scripts/15_plot_AD400_NORMAL400_convergence_and_EC.py"
core = load("core", core_path)


class FullSequenceTests(unittest.TestCase):
    def test_38_station_registry_has_unique_requested_sites(self):
        self.assertEqual(len(fig.SITES), 38)
        self.assertEqual(len(set(fig.SITES)), 38)
        self.assertTrue({"DE-Hai", "NL-Loo", "CH-Aws", "GL-ZaH"}.issubset(fig.SITES))

    def test_ad_history_audit_finds_nee_and_respiration_fields(self):
        self.assertEqual(ad_audit.candidates(["FATES_NEP", "FATES_GPP", "SOIL_RESP", "TLAI"]),
                         ["FATES_GPP", "FATES_NEP", "SOIL_RESP"])

    def test_model_history_flux_conversion_and_missing_fields(self):
        with tempfile.TemporaryDirectory(dir=HERE) as tmp:
            path = Path(tmp) / "model.nc"
            with Dataset(path, "w") as ds:
                ds.createDimension("time", 12); ds.createDimension("nbnd", 2)
                t = ds.createVariable("time", "f8", ("time",)); t.units = "days since 2400-01-01"; t.calendar = "noleap"
                b = ds.createVariable("time_bounds", "f8", ("time", "nbnd"))
                starts = np.r_[0, np.cumsum(fig.MONTH_DAYS)[:-1]]
                b[:] = np.column_stack((starts, starts + fig.MONTH_DAYS)); t[:] = starts
                for key, val in (("FATES_GPP", 1.e-8), ("FATES_NEP", 2.e-8)):
                    v = ds.createVariable(key, "f8", ("time",)); v.units = "kgC m-2 s-1"; v[:] = val
            rows, missing = fig.model_year(core, 2400, 401, "NORMAL", [path])
            self.assertEqual(len(rows), 12)
            self.assertAlmostEqual(rows[0]["GPP"], .864)
            self.assertAlmostEqual(rows[0]["NEE"], -1.728)
            self.assertEqual(missing, {"NPP", "LAI"})
            self.assertTrue(np.isnan(rows[0]["LAI"]))
            with Dataset(path, "a") as ds:
                ds.variables["time_bounds"][0, 1] = 30
            with self.assertRaisesRegex(ValueError, "durations"):
                fig.model_year(core, 2400, 401, "NORMAL", [path])

    def test_cached_data_pair_year_phase_and_hash(self):
        with tempfile.TemporaryDirectory(dir=HERE) as tmp:
            root = Path(tmp); spin = np.repeat(np.arange(1, 801), 12)
            df = pd.DataFrame({"SpinupYear": spin, "Month": np.tile(np.arange(1, 13), 800),
                               "ModelYear": 2002 + spin - 1, "Phase": np.where(spin <= 400, "AD", "NORMAL"),
                               "GPP": 1., "NEE": np.nan, "NPP": .5, "LAI": 2.})
            csv_path = root / "DE-Hai_model_monthly_derived.csv"
            df.to_csv(csv_path, index=False)
            meta_path = root / "DE-Hai_metadata.json"
            meta_path.write_text(json.dumps({"site": "DE-Hai", "ad_case": "ad", "normal_case": "normal",
                                             "missing_model_fields": ["NEE"]}), encoding="utf-8")
            frame, missing, checksum = fig.load_cached_model(root, "DE-Hai", "ad", "normal", 2002)
            self.assertEqual(len(frame), 9600)
            self.assertEqual(missing, {"NEE"})
            self.assertEqual(len(checksum), 64)
            with self.assertRaisesRegex(ValueError, "provenance"):
                fig.load_cached_model(root, "DE-Hai", "wrong", "normal", 2002)
            with self.assertRaisesRegex(ValueError, "dates or phase"):
                fig.load_cached_model(root, "DE-Hai", "ad", "normal", 2003)

    def test_all_38_in_manifest_with_unavailable_sites_and_nt_counts(self):
        import sys
        with tempfile.TemporaryDirectory(dir=HERE) as tmp:
            root = Path(tmp)
            rows = [dict(name="DE-Hai_AD", site="DE-Hai", mode="AD", verdict="DONE"),
                    dict(name="DE-Hai_NORMAL", site="DE-Hai", mode="NORMAL", verdict="DONE", refcase="DE-Hai_AD")]
            scan = SimpleNamespace(USER="test", OUT=root, BASE=root, scan=lambda *a: rows)
            runner = SimpleNamespace(verified_queue=lambda user: {}, restart_check=lambda *a: None,
                                     stream_status=lambda *a: ("MATCH", None, None))
            fake_core = SimpleNamespace(inventory=lambda *a: {"complete": True,
                "ad_years": list(range(2000, 2400)), "normal_years": list(range(2400, 2800)),
                "fad": {y: [] for y in range(2000, 2400)}, "fno": {y: [] for y in range(2400, 2800)},
                "forcing": (2000, 2009, 2000)}, GPP_NT="GPP_NT_VUT_REF", GPP_DT="GPP_DT_VUT_REF")
            def model(core, year, spin, phase, paths):
                return ([{"SpinupYear": spin, "ModelYear": year, "Phase": phase, "Month": m,
                          "GPP": 1., "NEE": 0., "NPP": 0.5, "LAI": 1.} for m in range(1, 13)], set())
            ref = {k: {"mean": 1.} for k in ("GPP", "NEE")}
            out = root / "out"
            recorded = []
            with patch.object(sys, "argv", ["runner", "--output-root", str(out)]), \
                 patch.object(fig, "load", side_effect=[fake_core, scan, runner]), \
                 patch.object(fig, "model_year", side_effect=model), \
                 patch.object(fig, "ec_reference", return_value=(ref, [], {"GPP_NT_VUT_REF": 10})), \
                 patch.object(fig, "plot_overviews"), \
                 patch.object(fig, "save", side_effect=lambda path, entries: recorded.__setitem__(slice(None), [dict(x) for x in entries])), \
                 patch.object(fig, "plot_site", return_value=None):
                self.assertEqual(fig.main(), 1)
            fig.save(out, recorded)
            with (out / "site_status.csv").open(newline="", encoding="utf-8") as f:
                saved = list(csv.DictReader(f))
            self.assertEqual(len(saved), 38)
            hai = next(x for x in saved if x["Site"] == "DE-Hai")
            self.assertEqual(hai["Status"], "OK")
            self.assertEqual(hai["NT_days"], "10")
            self.assertEqual(next(x for x in saved if x["Site"] == "NL-Loo")["Status"], "MISSING")


if __name__ == "__main__":
    unittest.main()

