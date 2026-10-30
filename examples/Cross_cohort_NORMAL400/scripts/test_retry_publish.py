import csv
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
def load(name, filename):
    spec = importlib.util.spec_from_file_location(name, HERE / filename)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

retry = load("retry", "04_retry_missing_sites.py")
publish = load("publish", "05_publish_completed_figures.py")
PNG = b"\x89PNG\r\n\x1a\nexample"


def summary(root, rows):
    root.mkdir(parents=True, exist_ok=True)
    with (root / "all_sites_summary.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["Site", "Normal_case", "AD_case", "Status"])
        w.writeheader(); w.writerows(rows)


def figures(root, site="AA-X", case="AA-X_NORMAL", count=3):
    path = root / site / case
    path.mkdir(parents=True, exist_ok=True)
    for suffix in publish.SUFFIXES[:count]:
        (path / (site + suffix)).write_bytes(PNG)
    (path / (site + "_metadata.json")).write_text(json.dumps({
        "status": "OK", "ad_case": "AA-X_AD", "normal_case": case}), encoding="utf-8")
    return path


class RetryTests(unittest.TestCase):
    def test_reuse_requires_all_figures_and_matching_provenance(self):
        with tempfile.TemporaryDirectory(dir=HERE) as t:
            root = Path(t)
            row = {"Site": "AA-X", "Normal_case": "AA-X_NORMAL", "AD_case": "AA-X_AD", "Status": "OK"}
            summary(root, [row]); path = figures(root)
            data = retry.load_previous(root)
            self.assertEqual(retry.reusable(data, root, "AA-X", "AA-X_AD", "AA-X_NORMAL"), path.resolve())
            (path / ("AA-X" + publish.SUFFIXES[2])).unlink()
            self.assertIsNone(retry.reusable(data, root, "AA-X", "AA-X_AD", "AA-X_NORMAL"))

    def test_running_job_is_not_accepted(self):
        result = type("Result", (), {"returncode": 0, "stdout": "123|RUNNING\n", "stderr": ""})()
        with patch.object(retry.subprocess, "run", return_value=result):
            with self.assertRaises(RuntimeError):
                retry.previous_job_finished("123")

    def test_log_chooses_previous_output(self):
        with tempfile.TemporaryDirectory(dir=HERE) as t:
            root = Path(t); old = root / "All_completed_AD400_NORMAL400_1"
            summary(old, [])
            (root / "all_sites_123.log").write_text("Manifest: " + old.as_posix() + "/all_sites_summary.csv\n")
            self.assertEqual(retry.find_previous(None, "123", root), old.resolve())

    def test_no_previous_summary_does_not_block_fresh_analysis(self):
        with tempfile.TemporaryDirectory(dir=HERE) as t:
            self.assertIsNone(retry.find_previous(None, "123", Path(t)))

    def test_locates_supplement_by_job_and_original_pair(self):
        with tempfile.TemporaryDirectory(dir=HERE) as t:
            base = Path(t); old = base / "old"; old.mkdir()
            extra = base / "Missing_completed_AD400_NORMAL400_test"
            summary(extra, [])
            (extra / "RUN_INFO.json").write_text(json.dumps({"retry_job": "456", "previous_job": "123", "previous_root": str(old)}))
            self.assertEqual(retry.find_retry_output("456", base, old, "123"), extra.resolve())
            self.assertIsNone(retry.find_retry_output("999", base, old, "123"))

    def test_only_missing_completed_cases_are_drawn(self):
        with tempfile.TemporaryDirectory(dir=HERE) as t:
            base = Path(t); old = base / "old"; out = base / "retry"
            row = {"Site": "AA-X", "Normal_case": "AA-X_NORMAL", "AD_case": "AA-X_AD", "Status": "OK"}
            summary(old, [row]); figures(old)
            rows = []
            for site in ("AA-X", "BB-Y"):
                ad, normal = site + "_AD", site + "_NORMAL"
                rows.extend([dict(site=site, name=ad, mode="AD", verdict="DONE", latest="2400-01-01-00000"),
                             dict(site=site, name=normal, mode="NORMAL", verdict="DONE", refcase=ad, latest="2800-01-01-00000")])
            scan = SimpleNamespace(USER="test", BASE=base, OUT=base,
                                   scan=lambda *a: rows,
                                   stream_info=lambda n: (Path(n), ["forcing"], ("2000",)))
            called = []
            plot = SimpleNamespace(process=lambda pair, args: called.append(pair["site"]) or {"Status": "OK"})
            with patch.object(retry, "load", side_effect=[scan, plot]), \
                 patch.object(retry, "verified_queue", return_value={}), \
                 patch.object(retry, "restart_check"), \
                 patch.object(retry, "previous_job_finished", return_value="COMPLETED"), \
                 patch("sys.argv", ["retry", "--output-root", str(out), "--previous-job", "123", "--previous-run", str(old)]):
                self.assertEqual(retry.main(), 0)
            self.assertEqual(called, ["BB-Y"])
            with (out / "all_sites_summary.csv").open(newline="", encoding="utf-8") as f:
                saved = {r["Site"]: r["Status"] for r in csv.DictReader(f)}
            self.assertEqual(saved, {"AA-X": "REUSED", "BB-Y": "OK"})


class PublicationTests(unittest.TestCase):
    def test_repository_uses_github_ssh(self):
        self.assertEqual(publish.REPO, "git@github.com:lyanyeung/Non-Competition-CLM-experiment.git")

    def test_inventory_reuses_more_complete_original_and_does_not_mix(self):
        with tempfile.TemporaryDirectory(dir=HERE) as t:
            base = Path(t); old = base / "old"; new = base / "new"
            row = {"Site": "AA-X", "Normal_case": "AA-X_NORMAL", "AD_case": "AA-X_AD", "Status": "OK"}
            summary(old, [row]); summary(new, [{**row, "Status": "CARBON_OK_EC_ERROR"}])
            figures(old, count=3); figures(new, count=2)
            (new / "RUN_INFO.json").write_text(json.dumps({"previous_root": str(old), "previous_job": "123"}))
            _, selected = publish.inventory(new)
            self.assertEqual(len(selected), 1)
            self.assertEqual(selected[0][1], old.resolve())
            self.assertEqual(len(selected[0][3]), 3)

    def test_conflicting_ad_or_unsafe_names_rejected(self):
        with self.assertRaises(ValueError):
            publish.check_name("../escape")
        with tempfile.TemporaryDirectory(dir=HERE) as t:
            base = Path(t); old = base / "old"; new = base / "new"
            row = {"Site": "AA-X", "Normal_case": "AA-X_NORMAL", "AD_case": "A", "Status": "OK"}
            summary(old, [row]); summary(new, [{**row, "AD_case": "B"}])
            (new / "RUN_INFO.json").write_text(json.dumps({"previous_root": str(old), "previous_job": "123"}))
            with self.assertRaises(ValueError):
                publish.inventory(new)

    def test_publication_stages_only_png_and_index(self):
        with tempfile.TemporaryDirectory(dir=HERE) as t:
            base = Path(t); old = base / "old"; new = base / "new"
            row = {"Site": "AA-X", "Normal_case": "AA-X_NORMAL", "AD_case": "AA-X_AD", "Status": "OK"}
            summary(old, [row]); summary(new, [row]); p = figures(old)
            (p / "private_observations.csv").write_text("must not be copied")
            (new / "RUN_INFO.json").write_text(json.dumps({"previous_root": str(old), "previous_job": "123", "retry_job": "456"}))
            staged = []
            def fake_git(*args, cwd=None):
                if args[0] == "clone":
                    Path(args[-1]).mkdir()
                elif args[0] == "add":
                    staged.extend(str(x.relative_to(cwd)) for x in Path(cwd).rglob("*") if x.is_file())
                elif args[0] == "rev-parse":
                    return "abcdef"
                elif args[0] == "ls-remote":
                    return "abcdef refs/heads/main"
                return ""
            with patch.object(publish, "git", side_effect=fake_git), patch.object(publish, "require_job_finished", return_value="COMPLETED"), \
                 patch("sys.argv", ["publish", "--run", str(new), "--retry-job", "456", "--publish"]):
                self.assertEqual(publish.main(), 0)
            self.assertEqual(sum(x.endswith(".png") for x in staged), 3)
            self.assertFalse(any(x.endswith(".csv") for x in staged))

    def test_login_publication_requires_matching_completion_marker(self):
        with tempfile.TemporaryDirectory(dir=HERE) as t:
            root = Path(t)
            row = {"Site": "AA-X", "Normal_case": "AA-X_NORMAL", "AD_case": "AA-X_AD", "Status": "OK"}
            summary(root, [row]); figures(root)
            (root / "RUN_INFO.json").write_text(json.dumps({"previous_root": "", "previous_roots": [],
                "previous_job": "123", "run_mode": "login", "run_id": "abc"}))
            (root / "RUN_COMPLETE.json").write_text(json.dumps({"run_id": "bad"}))
            with patch("sys.argv", ["publish", "--run", str(root), "--login"]):
                with self.assertRaises(ValueError):
                    publish.main()
            (root / "RUN_COMPLETE.json").write_text(json.dumps({"run_id": "abc"}))
            with patch("sys.argv", ["publish", "--run", str(root), "--login"]):
                self.assertEqual(publish.main(), 0)


if __name__ == "__main__":
    unittest.main()
