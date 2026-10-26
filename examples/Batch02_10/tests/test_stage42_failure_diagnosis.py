import contextlib
import gzip
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

TESTDIR = Path(__file__).resolve().parent
SCRIPT = TESTDIR.parent/'scripts/42_diagnose_five_failed_AD400_readonly.py'
spec = importlib.util.spec_from_file_location('stage42', SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class DiagnosticTests(unittest.TestCase):
    def test_all_five_plain_and_gzip_logs_and_no_writes(self):
        temp = tempfile.TemporaryDirectory(prefix='_stage42_fixture_', dir=TESTDIR)
        root = Path(temp.name).resolve()
        self.assertEqual(root.parent, TESTDIR)
        try:
            base = root/'base'
            output = root/'outputs'
            experiment = root/'experiment'
            namelist = "hist_fincl1='TOTSOMC','TOTSOMN','TLAI','GPP','NPP','TWS','H2OSNO'\n/\n"
            names = ['TOTSOMC','TOTSOMN','TLAI','TWS','H2OSNO','FATES_GPP','FATES_NPP']
            registry = '\n'.join('  {} {}          units'.format(i+1, name)
                                 for i, name in enumerate(names + ['FIELD_'+str(n) for n in range(110)]))
            text = registry + '\nhtapes_fieldlist ERROR: GPP in fincl(4) for history tape 1 not found\nSIGKILL\n'
            for i, (site, job, name, receipt) in enumerate(module.TARGETS):
                case = base/'cases'/name
                run = output/name/'run'
                (case/'CaseDocs').mkdir(parents=True)
                run.mkdir(parents=True)
                (case/'xmlquery').write_text('placeholder')
                (case/'.case.run').write_text('ulimit -s 300000\nsrun --mpi=pmix cesm.exe\n')
                (case/'.submit_options').write_text('[SubmitOptions]\nskip_pnl = True\n')
                (case/'CaseDocs/lnd_in').write_text(namelist)
                (run/'lnd_in').write_text(namelist)
                log = run/('lnd.log.'+job+'.fixture'+('.gz' if i == 0 else ''))
                if i == 0:
                    with gzip.open(log, 'wb') as handle:
                        handle.write(text.encode())
                else:
                    log.write_text(text)
                rec = experiment/receipt
                rec.parent.mkdir(parents=True, exist_ok=True)
                rec.write_text(json.dumps({'run_job':job,'phase':'SUBMITTED','stack':[67108864,-1]}))
            initial = {p.relative_to(root).as_posix():(p.read_bytes(),p.stat().st_mtime_ns)
                       for p in root.rglob('*') if p.is_file()}
            commands = []
            def fake_call(args, timeout=45, cwd=None):
                commands.append([str(a) for a in args])
                if str(args[0]).endswith('xmlquery'):
                    case = Path(args[0]).parent
                    self.assertEqual(cwd, case)
                    values = {'RUNDIR':str(output/case.name/'run'),
                              'DOUT_S_ROOT':str(output/'archive'/case.name),
                              'RUN_STARTDATE':'2000-01-01','RUN_TYPE':'startup',
                              'CONTINUE_RUN':'FALSE','STOP_N':'5','RESUBMIT':'79',
                              'CLM_ACCELERATED_SPINUP':'on', 'MPI_RUN_COMMAND':'srun --mpi=pmix --ntasks=1'}
                    return values[args[1]]
                self.assertIn(str(args[0]), ['squeue','sacct'])
                return ''
            captured = io.StringIO()
            with patch.object(module,'BASE',base), patch.object(module,'OUTPUT',output), \
                 patch.object(module,'EXPERIMENT',experiment), patch.object(module,'call',side_effect=fake_call), \
                 patch('sys.argv',[str(SCRIPT),'--diagnose']), contextlib.redirect_stdout(captured):
                self.assertEqual(module.main(), 0)
            result = captured.getvalue()
            self.assertEqual(result.count('DIAGNOSIS '), 5)
            self.assertEqual(result.count('CONFIRMED_HISTORY_FIELD_NOT_REGISTERED:GPP'), 10)
            self.assertIn('FATES_GPP', result)
            self.assertIn('NPP NOT_REGISTERED', result)
            self.assertIn('ulimit -s 300000', result)
            self.assertIn('skip_pnl = True', result)
            self.assertNotIn('SEGFAULT_CAUSE_UNCONFIRMED', result)
            final = {p.relative_to(root).as_posix():(p.read_bytes(),p.stat().st_mtime_ns)
                     for p in root.rglob('*') if p.is_file()}
            self.assertEqual(initial, final)
            self.assertTrue(commands)
        finally:
            self.assertEqual(root.parent, TESTDIR)
            self.assertTrue(root.name.startswith('_stage42_fixture_'))
            temp.cleanup()

    def test_classification_does_not_infer_stack_from_crash(self):
        self.assertEqual(module.classify('forrtl severe (174) SIGSEGV ESMF_MeshCreate'),
                         'SEGFAULT_CAUSE_UNCONFIRMED_NOT_PROOF_OF_LOW_STACK')
        self.assertEqual(module.classify('SIGKILL'), 'CAUSE_UNCONFIRMED_REVIEW_PRINTED_LOGS')
        module.self_test()


if __name__ == '__main__':
    unittest.main(verbosity=2)
