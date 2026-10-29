import csv
import importlib.util
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("all_sites", HERE / "03_plot_all_completed_sites.py")
job = importlib.util.module_from_spec(spec)
spec.loader.exec_module(job)


class BatchSelectionTests(unittest.TestCase):
    def test_pairs_via_refcase_and_keeps_skipped_cases(self):
        with tempfile.TemporaryDirectory(dir=HERE) as t:
            root = Path(t)
            rows = [
                dict(name="X_AD", site="X", mode="AD", verdict="DONE", latest="2400-01-01-00000"),
                dict(name="X_NORMAL", site="X", mode="NORMAL", verdict="DONE", refcase="X_AD", latest="2800-01-01-00000"),
                dict(name="Y_NORMAL", site="Y", mode="NORMAL", verdict="DONE", refcase="wrong_AD", latest="2800-01-01-00000"),
                dict(name="Z_NORMAL", site="Z", mode="NORMAL", verdict="RUNNING", refcase="Z_AD", latest="2750-01-01-00000"),
            ]
            for name, year in (("X_AD", "2400-01-01-00000"), ("X_NORMAL", "2800-01-01-00000")):
                directory = root / "archive" / name / "rest" / year
                directory.mkdir(parents=True)
                for comp in ("clm2", "datm", "cpl"):
                    (directory / f"{name}.{comp}.r.{year}.nc").write_bytes(b"x" * 1024)
            scan = SimpleNamespace(USER="example", OUT=root, BASE=root,
                                   scan=lambda *a: rows,
                                   stream_info=lambda n: (Path(n), ["f"], ("2000", "2020", "2000")))
            calls = []
            def process(pair, settings):
                calls.append((pair["site"], pair["ad"], pair["normal"]))
                return {"Status": "OK"}
            plot = SimpleNamespace(process=process)
            with patch.object(job, "load", side_effect=[scan, plot]), patch.object(job, "verified_queue", return_value={}), \
                 patch("sys.argv", ["job", "--output-root", str(root / "out")]):
                code = job.main()
            self.assertEqual(code, 1)  # Y is marked DONE but has no valid AD reference
            self.assertEqual(calls, [("X", "X_AD", "X_NORMAL")])
            with (root / "out" / "all_sites_summary.csv").open(newline="", encoding="utf-8") as f:
                saved = {r["Site"]: r for r in csv.DictReader(f)}
            self.assertEqual(saved["X"]["Status"], "OK")
            self.assertEqual(saved["Y"]["Status"], "SKIPPED")
            self.assertEqual(saved["Z"]["Status"], "SKIPPED")

    def test_missing_restart_component_is_rejected(self):
        with tempfile.TemporaryDirectory(dir=HERE) as t:
            scan = SimpleNamespace(OUT=Path(t))
            with self.assertRaises(ValueError):
                job.restart_check(scan, {"name": "x", "latest": "2400-01-01-00000"})


if __name__ == "__main__":
    unittest.main()

