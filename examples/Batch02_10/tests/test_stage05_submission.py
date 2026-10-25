"""Mocked scheduler/CIME tests. No real CIME or Slurm commands are run."""
import contextlib
import importlib.util
import io
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

spec = importlib.util.spec_from_file_location(
    "stage05", Path(__file__).resolve().parents[1] / "scripts/05_submit_four_AD5_cases.py")
C = importlib.util.module_from_spec(spec)
spec.loader.exec_module(C)


class SubmitTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        self.patches = [patch.object(C.B, "OUT", root / "out"),
                        patch.object(C.B, "BASE", root / "base"),
                        patch.object(C.B, "OUTPUTS", root / "outputs")]
        for p in self.patches:
            p.start()
            self.addCleanup(p.stop)
        self.records = {}
        for site in C.B.S.SELECTED:
            case, _, _, ledger = C.B.paths(site)
            case.mkdir(parents=True)
            (case / "CaseStatus").write_text("preview_namelists success\n")
            ledger.parent.mkdir(parents=True)
            obj = {"site": site, "phase": C.PREPARED, "Slurm_jobs_submitted": False}
            ledger.write_text(json.dumps(obj))
            self.records[site] = obj
        self.calls = []

    def fake_submit(self, args, **kwargs):
        self.calls.append(args)
        self.assertEqual(args[1:], ["--skip-preview-namelist"])
        self.assertEqual(Path(args[0]).name, "case.submit")
        # Verify an exclusive marker and uncertain state precede external action.
        case = Path(kwargs["cwd"])
        site = case.name.split("_B02_")[0]
        self.assertTrue(C.site_attempt(site).is_file())
        self.assertEqual(C.load_state(site)["phase"], C.ATTEMPTED)
        (case / ".submit_options").write_text("[SubmitOptions]\nskip_pnl = True\n")
        n = 100 + 2 * len(self.calls)
        return subprocess.CompletedProcess(args, 0,
            f"Submitted job case.run with id {n}\nSubmitted job case.st_archive with id {n + 1}\n", "")

    def quiet_submit(self):
        with contextlib.redirect_stdout(io.StringIO()):
            return C.submit()

    def test_four_successes_and_actual_ids_retained(self):
        with patch.object(C, "preflight", return_value=self.records), patch.object(C, "queue_rows", return_value=[]), \
             patch.object(C.subprocess, "run", side_effect=self.fake_submit):
            self.assertEqual(self.quiet_submit(), 0)
        self.assertEqual(len(self.calls), 4)
        ids = []
        for site in C.B.S.SELECTED:
            obj = C.load_state(site)
            self.assertEqual(obj["phase"], C.SUBMITTED)
            self.assertTrue(obj["Slurm_jobs_submitted"])
            self.assertTrue(obj["skip_preview_persisted"])
            ids.extend([obj["first_run_job"], obj["first_archive_job"]])
        self.assertEqual(len(set(ids)), 8)
        with self.assertRaisesRegex(RuntimeError, "already attempted"):
            C.preflight()

    def test_partial_submission_stops_and_preserves_attempt(self):
        def partial(args, **kwargs):
            result = self.fake_submit(args, **kwargs)
            if len(self.calls) == 2:
                result.stdout = "Submitted job case.run with id 777\n"
            return result
        with patch.object(C, "preflight", return_value=self.records), patch.object(C, "queue_rows", return_value=[]), \
             patch.object(C.subprocess, "run", side_effect=partial):
            self.assertEqual(self.quiet_submit(), 2)
        self.assertEqual(len(self.calls), 2)
        first, second, third, _ = C.B.S.SELECTED
        self.assertEqual(C.load_state(first)["phase"], C.SUBMITTED)
        self.assertEqual(C.load_state(second)["phase"], C.ATTEMPTED)
        self.assertEqual(C.load_state(third)["phase"], C.PREPARED)
        self.assertIn("777", (C.B.OUT / second / "AD5_case_submit_output.txt").read_text())

    def test_timeout_preserves_output_without_retry(self):
        site = C.B.S.SELECTED[0]
        with patch.object(C.subprocess, "run", side_effect=subprocess.TimeoutExpired(
                "case.submit", 360, output=b"Submitted job case.run with id 456\n")):
            with self.assertRaises(subprocess.TimeoutExpired):
                C.submit_one(site, self.records[site])
        self.assertEqual(C.load_state(site)["phase"], C.ATTEMPTED)
        self.assertTrue(C.site_attempt(site).is_file())
        self.assertIn("456", (C.B.OUT / site / "AD5_case_submit_output.txt").read_text())

    def test_nonzero_cime_preserves_ids_as_review(self):
        site = C.B.S.SELECTED[0]
        def nonzero(args, **kwargs):
            result = self.fake_submit(args, **kwargs)
            result.returncode = 1
            return result
        with patch.object(C.subprocess, "run", side_effect=nonzero):
            with self.assertRaisesRegex(RuntimeError, "need review"):
                C.submit_one(site, self.records[site])
        obj = C.load_state(site)
        self.assertEqual(obj["phase"], C.REVIEW)
        self.assertEqual(obj["first_run_job"], "102")

    def test_missing_skip_preview_receipt_preserves_ids(self):
        site = C.B.S.SELECTED[0]
        def nooptions(args, **kwargs):
            result = self.fake_submit(args, **kwargs)
            (Path(kwargs["cwd"]) / ".submit_options").unlink()
            return result
        with patch.object(C.subprocess, "run", side_effect=nooptions):
            with self.assertRaisesRegex(RuntimeError, "need review"):
                C.submit_one(site, self.records[site])
        self.assertEqual(C.load_state(site)["phase"], C.REVIEW)
        self.assertEqual(C.load_state(site)["first_archive_job"], "103")

    def test_queued_target_rejected_other_batches_ignored(self):
        site = C.B.S.SELECTED[0]
        with self.assertRaisesRegex(RuntimeError, "already queued"):
            C.no_active_jobs([["55", "run." + C.B.name(site), "RUNNING"]])
        C.no_active_jobs([["56", "run.CZ-BK1_B01_FIXNC_AD400", "RUNNING"]])

    def test_prior_case_submission_rejected(self):
        case = C.B.paths(C.B.S.SELECTED[0])[0]
        (case / "CaseStatus").write_text("case.submit starting\n")
        with self.assertRaisesRegex(RuntimeError, "history"):
            C.no_case_submission(case)


if __name__ == "__main__":
    unittest.main()
