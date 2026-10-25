"""Controlled wrapper and mocked single-case recovery; never contacts Slurm."""
import contextlib
import importlib.util
import io
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

spec = importlib.util.spec_from_file_location(
    'stackpilot', Path(__file__).resolve().parents[1] / 'scripts/08_retry_FI_Hyy_AD5_stack256_pilot.py')
M = importlib.util.module_from_spec(spec)
spec.loader.exec_module(M)


class StackPilotTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        case = self.root / 'case'
        case.mkdir()
        site = self.root / 'site'
        site.mkdir()
        fields = dict(CASE=case, SITE_ROOT=site, STATE=site / 'AD5_case_state.json',
                      PILOT=site / 'pilot', RECEIPT=site / 'pilot/retry_state.json',
                      WRAPPER=site / 'pilot/task_stack256.sh')
        for k, v in fields.items():
            p = patch.object(M, k, v)
            p.start()
            self.addCleanup(p.stop)
        self.exe = self.root / 'cesm.exe'
        self.exe.write_text('#!/usr/bin/env bash\nprintf "ARG=%s\\n" "$@"\n')
        self.exe.chmod(0o700)
        self.obj = dict(executable=str(self.exe), first_run_job=M.OLD_RUN, first_archive_job=M.OLD_ARCHIVE)
        M.STATE.write_text(json.dumps(self.obj))
        (case / '.submit_options').write_text('[SubmitOptions]\nskip_pnl=True\n')
        (case / 'env_run.xml').write_text('original')
        self.calls = []

    def fake_call(self, args, **kwargs):
        args = list(map(str, args))
        self.calls.append(args)
        self.assertTrue(Path(args[0]).name in ('bash', 'xmlchange', 'scancel'))
        return ''

    def fake_submit(self, args, **kwargs):
        self.assertEqual(args, [str(M.CASE / 'case.submit'), '--skip-preview-namelist'])
        self.assertEqual(json.loads(M.RECEIPT.read_text())['phase'], 'ATTEMPTED_UNCERTAIN')
        return subprocess.CompletedProcess(args, 0,
            'Submitted job case.run with id 999101\nSubmitted job case.st_archive with id 999102\n', '')

    def run_retry(self, submit=None, queues=None):
        with patch.object(M, 'audit', return_value=(self.obj, {str(self.exe): M.digest(self.exe)})), \
             patch.object(M, 'old_jobs'), patch.object(M, 'call', side_effect=self.fake_call), \
             patch.object(M, 'query', return_value=M.MPI + ' ' + str(M.WRAPPER)), \
             patch.object(M, 'queue', return_value=[] if queues is None else queues), \
             patch.object(M.subprocess, 'run', side_effect=submit or self.fake_submit), \
             contextlib.redirect_stdout(io.StringIO()):
            M.retry()

    def test_wrapper_sets_task_stack_and_preserves_args(self):
        wrapper = self.root / 'wrapper.sh'
        wrapper.write_text(M.wrapper_text(str(self.exe)))
        before = M.resource.getrlimit(M.resource.RLIMIT_STACK)
        proc = subprocess.run(['bash', str(wrapper), str(self.exe), 'one', 'two words'],
                              capture_output=True, text=True, env=dict(os.environ, OMP_STACKSIZE='64M'))
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn('after_kib=262144', proc.stdout)
        self.assertIn('OMP_STACKSIZE=64M', proc.stdout)
        self.assertIn('ARG=two words', proc.stdout)
        self.assertEqual(M.resource.getrlimit(M.resource.RLIMIT_STACK), before)
        proc = subprocess.run(['bash', str(wrapper), '/wrong/cesm.exe'], capture_output=True, text=True)
        self.assertEqual(proc.returncode, 64)

    def test_success_changes_only_launcher_and_cancels_one_archive(self):
        self.run_retry()
        self.assertEqual([c for c in self.calls if c[0] == 'scancel'], [['scancel', M.OLD_ARCHIVE]])
        changes = [c for c in self.calls if Path(c[0]).name == 'xmlchange']
        self.assertEqual(len(changes), 1)
        self.assertTrue(changes[0][1].startswith('MPI_RUN_COMMAND='))
        rec = json.loads(M.RECEIPT.read_text())
        self.assertEqual(rec['phase'], 'SUBMITTED')
        self.assertEqual(rec['run_job'], '999101')
        self.assertEqual(json.loads(M.STATE.read_text())['first_run_job'], M.OLD_RUN)
        self.assertTrue((M.PILOT / 'before/AD5_case_state.json').is_file())
        with self.assertRaisesRegex(RuntimeError, 'already attempted'):
            M.audit()

    def test_partial_submit_retains_attempt_and_full_output(self):
        def partial(args, **kwargs):
            return subprocess.CompletedProcess(args, 0, 'Submitted job case.run with id 999101', '')
        with self.assertRaisesRegex(RuntimeError, 'ambiguous'):
            self.run_retry(submit=partial)
        self.assertEqual(json.loads(M.RECEIPT.read_text())['phase'], 'ATTEMPTED_UNCERTAIN')
        self.assertIn('999101', (M.PILOT / 'case_submit_output.txt').read_text())

    def test_other_active_job_stops_before_submit(self):
        with self.assertRaisesRegex(RuntimeError, 'Unexpected active'):
            self.run_retry(queues=[['999999', 'run.' + M.NAME, 'RUNNING', 'node']])
        self.assertFalse((M.PILOT / 'case_submit_output.txt').exists())

    def test_immutable_input_drift_is_rejected(self):
        sha = M.digest(self.exe)
        self.exe.write_text('changed')
        with self.assertRaisesRegex(RuntimeError, 'changed an input'):
            M.verify_immutable({str(self.exe): sha})

    def test_exact_failed_run_and_archive_identity_required(self):
        good = M.OLD_RUN + '|run.' + M.NAME + '|FAILED|1:0\n' + M.OLD_ARCHIVE + '|st_archive.' + M.NAME + '|PENDING|0:0\n'
        with patch.object(M, 'call', return_value=good), patch.object(M, 'queue', return_value=[
                [M.OLD_ARCHIVE, 'st_archive.' + M.NAME, 'PENDING', '(DependencyNeverSatisfied)']]):
            M.old_jobs()
        with patch.object(M, 'call', return_value=good.replace('FAILED', 'COMPLETED')):
            with self.assertRaisesRegex(RuntimeError, 'known FAILED'):
                M.old_jobs()


if __name__ == '__main__':
    unittest.main()
