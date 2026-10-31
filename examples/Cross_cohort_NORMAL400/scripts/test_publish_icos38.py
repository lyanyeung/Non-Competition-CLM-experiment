import csv
import hashlib
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("publish38", HERE / "22_publish_icos38_full_sequence.py")
mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)


class PublishTests(unittest.TestCase):
    def test_publish_uses_fresh_output_only_and_removes_source_paths(self):
        with tempfile.TemporaryDirectory(dir=HERE.parents[1]) as tmp:
            root = Path(tmp) / "fresh"; folder = root / "DE-Hai" / "DE-Hai_NORMAL"
            folder.mkdir(parents=True)
            core, script = Path(tmp) / "core.py", Path(tmp) / "script.py"
            core.write_text("# core\n"); script.write_text("# plotter\n")
            h = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
            run = "login-" + "a" * 32
            Path(str(root) + ".analysis_exit_status").write_text(f"{run}|1|{h(core)}|{h(script)}\n")
            rows = [{"Site": "DE-Hai", "Normal_case": "DE-Hai_NORMAL", "Status": "OK", "NT_days": "300", "DT_days": "0"}]
            rows += [{"Site": f"S{i}", "Normal_case": "", "Status": "MISSING"} for i in range(37)]
            with (root / "site_status.csv").open("w", newline="", encoding="utf-8") as f:
                w = csv.DictWriter(f, fieldnames=["Site", "Normal_case", "Status", "NT_days", "DT_days"])
                w.writeheader(); w.writerows(rows)
            (folder / "DE-Hai_03_GPP_NEE_full_sequence_AD400_NORMAL400.png").write_bytes(b"\x89PNG\r\n\x1a\nmock")
            (folder / "DE-Hai_01_carbon_pools_AD400_NORMAL400.png").write_bytes(b"\x89PNG\r\n\x1a\nmock")
            (folder / "DE-Hai_02_carbon_pools_NORMAL400_panels.png").write_bytes(b"\x89PNG\r\n\x1a\nmock")
            (folder / "DE-Hai_convergence_metrics.csv").write_text("Variable\nTOTSOMC\n")
            for name in ("GPP", "NEE"):
                (root / f"ALL_38_{name}_full_sequence_overview.png").write_bytes(b"\x89PNG\r\n\x1a\nmock")
            for filename in ("ALL_38_TOTSOMC_AD_NORMAL_overview.png", "ALL_38_TOTSOMC_NORMAL_overview.png"):
                (root / filename).write_bytes(b"\x89PNG\r\n\x1a\nmock")
            (folder / "DE-Hai_metadata.json").write_text(json.dumps({"ec_sources": [{"path": "/private/dir/tower.csv", "gpp_column": "GPP_NT_VUT_REF"}]}))
            (folder / "raw.nc").write_text("never published")
            seen = {}
            def fake_git(*args, cwd=None):
                if args[0] == "clone":
                    checkout = Path(args[-1])
                    for rel, data in ((mod.CORE, core), (mod.SCRIPT, script)):
                        (checkout / rel).parent.mkdir(parents=True, exist_ok=True)
                        (checkout / rel).write_bytes(data.read_bytes())
                if args[0] == "rev-parse": return "testcommit"
                if args[0] == "push":
                    for p in (Path(cwd) / "figures").rglob("*"):
                        if p.is_file(): seen[p.name] = p.read_bytes()
                return ""
            argv = ["publish", "--run", str(root), "--run-id", run, "--core", str(core), "--script", str(script)]
            with patch.object(sys, "argv", argv), patch.object(mod, "git", fake_git):
                mod.main()
            self.assertNotIn("raw.nc", seen)
            self.assertIn("DE-Hai_01_carbon_pools_AD400_NORMAL400.png", seen)
            self.assertIn("DE-Hai_02_carbon_pools_NORMAL400_panels.png", seen)
            self.assertIn("DE-Hai_convergence_metrics.csv", seen)
            self.assertNotIn(b"/private/dir", seen["DE-Hai_provenance.json"])
            self.assertIn(b"tower.csv", seen["DE-Hai_provenance.json"])
            self.assertEqual(sum(line.startswith(b"| S") and b"| MISSING |" in line
                                 for line in seen["README.md"].splitlines()), 37)


if __name__ == "__main__": unittest.main()

