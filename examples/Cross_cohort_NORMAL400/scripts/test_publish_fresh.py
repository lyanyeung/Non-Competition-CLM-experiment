import csv
import hashlib
import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("fresh_publish", HERE / "18_publish_fresh_AD_NORMAL.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class FreshPublishTests(unittest.TestCase):
    def test_only_fresh_results_are_selected_and_plotter_is_verified(self):
        with tempfile.TemporaryDirectory(dir=HERE) as tmp:
            root = Path(tmp) / "fresh"
            folder = root / "AA-X" / "AA-X_NORMAL"
            folder.mkdir(parents=True)
            plotter = Path(tmp) / "plot.py"
            plotter.write_text("# plotter\n", encoding="utf-8")
            sha = hashlib.sha256(plotter.read_bytes()).hexdigest()
            Path(str(root) + ".analysis_exit_status").write_text(f"123|0|{sha}\n")
            with (root / "all_sites_summary.csv").open("w", newline="", encoding="utf-8") as f:
                w = csv.DictWriter(f, fieldnames=["Site", "Normal_case", "Status"])
                w.writeheader(); w.writerow({"Site": "AA-X", "Normal_case": "AA-X_NORMAL", "Status": "OK"})
            (folder / "AA-X_01_carbon_pools_AD400_NORMAL400.png").write_bytes(b"\x89PNG\r\n\x1a\nmock")
            (folder / "AA-X_convergence_metrics.csv").write_text("Variable\nTOTSOMC\n")
            (folder / "raw.nc").write_text("never published")
            published = []
            def fake_git(*args, cwd=None):
                if args[0] == "clone":
                    checkout = Path(args[-1]); (checkout / module.PLOT_PATH).parent.mkdir(parents=True)
                    (checkout / module.PLOT_PATH).write_bytes(plotter.read_bytes())
                if args[0] == "rev-parse": return "testcommit"
                if args[0] == "push":
                    published.extend(p.name for p in (Path(cwd) / "figures").rglob("*") if p.is_file())
                return ""
            argv = ["publish.py", "--run", str(root), "--job", "123", "--plotter", str(plotter)]
            with patch.object(sys, "argv", argv), patch.object(module, "git", fake_git), \
                 patch.object(module.subprocess, "run", return_value=SimpleNamespace(stdout="123|COMPLETED|\n")):
                module.main()
                self.assertIn("AA-X_convergence_metrics.csv", published)
                self.assertNotIn("raw.nc", published)
                plotter.write_text("changed\n", encoding="utf-8")
                with self.assertRaisesRegex(ValueError, "differs from the version"):
                    module.main()

    def test_login_requires_matching_marker_before_accessing_results(self):
        with tempfile.TemporaryDirectory(dir=HERE) as tmp:
            root = Path(tmp) / "fresh"
            root.mkdir()
            plotter = Path(tmp) / "plot.py"
            plotter.write_text("# plotter\n", encoding="utf-8")
            run_id = "login-" + "a" * 32
            sha = hashlib.sha256(plotter.read_bytes()).hexdigest()
            marker = Path(str(root) + ".analysis_exit_status")
            marker.write_text(f"login-{'b' * 32}|0|{sha}\n")
            argv = ["publish.py", "--run", str(root), "--login", run_id, "--plotter", str(plotter)]
            with patch.object(sys, "argv", argv), patch.object(module.subprocess, "run") as subprocess_run:
                with self.assertRaisesRegex(ValueError, "marker"):
                    module.main()
                subprocess_run.assert_not_called()


if __name__ == "__main__":
    unittest.main()

