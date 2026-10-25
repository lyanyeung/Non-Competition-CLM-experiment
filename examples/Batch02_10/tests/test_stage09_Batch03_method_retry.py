"""Mocked exact-site recovery tests; never runs Slurm/CIME or changes limits."""
import contextlib
import importlib.util
import io
import json
import resource
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('b02retry', Path(__file__).resolve().parents[1] /
                                            'scripts/09_resubmit_four_AD5_with_Batch03_stack_guard.py')
M = importlib.util.module_from_spec(spec)
spec.loader.exec_module(M)


class RetryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        for key, val in dict(BASE=root/'base',OUT=root/'exp',OUTPUTS=root/'outputs',BATCH=root/'exp/batch_attempt.json').items():
            p = patch.object(M,key,val)
            p.start()
            self.addCleanup(p.stop)
        M.OUT.mkdir()
        self.plan = {}
        self.active = [['77','run.IT-Lav_B03_FIXNC_AD400','RUNNING','red6083']]
        self.cancelled = []
        self.submitted = []
        for site,(r,a) in M.JOBS.items():
            name,case,run,archive,state,retrydir=M.paths(site)
            case.mkdir(parents=True)
            state.parent.mkdir(parents=True)
            (case/'.submit_options').write_text('[SubmitOptions]\nskip_pnl=True\n')
            (case/'env_run.xml').write_text('ORIGINAL XML')
            obj=dict(site=site,phase='FIRST_5Y_SUBMITTED',first_run_job=r,first_archive_job=a)
            state.write_text(json.dumps(obj))
            self.plan[site]=dict(obj=obj,hashes={str(case/'env_run.xml'):M.sha(case/'env_run.xml')},
                                 old_run=[r,'run.'+name,'FAILED','1:0'],old_archive=[a,'st_archive.'+name,'PENDING','0:0'],cancel_archive=True)
            self.active.append([a,'st_archive.'+name,'PENDING','(DependencyNeverSatisfied)'])

    def fake_call(self,args,**kwargs):
        self.assertEqual(args[0],'scancel')
        self.assertIn(args[1],{a for r,a in M.JOBS.values()})
        self.cancelled.append(args[1])
        self.active[:]=[r for r in self.active if r[0]!=args[1]]
        return ''

    def fake_submit(self,args,**kwargs):
        self.assertEqual(args[1:],["--skip-preview-namelist"])
        case=Path(kwargs['cwd']);site=case.name.split('_B02_')[0]
        rec=json.loads((M.paths(site)[5]/'retry_state.json').read_text())
        self.assertEqual(rec['phase'],'ATTEMPTED_UNCERTAIN')
        self.assertNotIn(M.JOBS[site][1],[r[0] for r in self.active])
        self.submitted.append(site)
        i=99000+2*len(self.submitted)
        return subprocess.CompletedProcess(args,0,f'Submitted job case.run with id {i}\nSubmitted job case.st_archive with id {i+1}','')

    def execute(self,submit=None):
        with patch.object(M,'preflight',return_value=self.plan),patch.object(M,'stack_guard',return_value={'soft_KiB_at_submit':'unlimited'}), \
             patch.object(M,'queue',side_effect=lambda:list(self.active)),patch.object(M,'call',side_effect=self.fake_call), \
             patch.object(M.subprocess,'run',side_effect=submit or self.fake_submit),contextlib.redirect_stdout(io.StringIO()):
            return M.resubmit()

    def test_four_exact_archives_and_only_case_submit_no_xml_edit(self):
        self.assertEqual(self.execute(),0)
        self.assertEqual(self.cancelled,[a for r,a in M.JOBS.values()])
        self.assertEqual(self.submitted,list(M.JOBS))
        self.assertEqual(self.active,[['77','run.IT-Lav_B03_FIXNC_AD400','RUNNING','red6083']])
        for site in M.JOBS:
            name,case,run,archive,state,retrydir=M.paths(site)
            self.assertEqual((case/'env_run.xml').read_text(),'ORIGINAL XML')
            self.assertEqual(json.loads(state.read_text())['first_run_job'],M.JOBS[site][0])
            self.assertTrue((retrydir/'before/AD5_case_state.json').is_file())
        with self.assertRaisesRegex(RuntimeError,'already attempted'):
            M.preflight()

    def test_partial_response_stops_batch_and_retains_output(self):
        def partial(args,**kwargs):
            p=self.fake_submit(args,**kwargs)
            if len(self.submitted)==2:p.stdout='Submitted job case.run with id 99111'
            return p
        self.assertEqual(self.execute(partial),2)
        self.assertEqual(len(self.submitted),2)
        site=list(M.JOBS)[1]
        self.assertIn('99111',(M.paths(site)[5]/'case_submit_output.txt').read_text())
        self.assertEqual(json.loads(M.BATCH.read_text())['phase'],'STOPPED_REVIEW_REQUIRED')

    def test_stack_policy_preserves_large_and_unlimited(self):
        self.assertEqual(M.stack_policy(300000*1024,-1),300000*1024)
        self.assertEqual(M.stack_policy(-1,-1),-1)
        self.assertEqual(M.stack_policy(8388608,-1),-1)
        with self.assertRaisesRegex(RuntimeError,'hard limit'):
            M.stack_policy(8388608,8388608)

    def test_guard_only_raises_low_soft_limit(self):
        with patch.object(M.resource,'getrlimit',return_value=(300000*1024,-1)),patch.object(M.resource,'setrlimit') as change, \
             contextlib.redirect_stdout(io.StringIO()):
            M.stack_guard(True)
            change.assert_not_called()
        with patch.object(M.resource,'getrlimit',side_effect=[(8388608,-1),(-1,-1)]),patch.object(M.resource,'setrlimit') as change, \
             contextlib.redirect_stdout(io.StringIO()):
            M.stack_guard(True)
            change.assert_called_once_with(resource.RLIMIT_STACK,(-1,-1))

    def test_immutable_input_drift_rejected(self):
        site=next(iter(M.JOBS));name,case,*_=M.paths(site)
        (case/'env_run.xml').write_text('CHANGED')
        with self.assertRaisesRegex(RuntimeError,'Input changed'):
            M.verify_hashes(self.plan[site]['hashes'])

    def test_new_ids_cannot_equal_original_jobs(self):
        with self.assertRaisesRegex(RuntimeError,'ambiguous'):
            M.parse_ids('Submitted job case.run with id 4728102\nSubmitted job case.st_archive with id 99999')


if __name__=='__main__':
    unittest.main()
