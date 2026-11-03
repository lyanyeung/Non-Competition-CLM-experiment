import importlib.util
import json
from pathlib import Path
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('b04_stop',Path(__file__).resolve().parents[1]/'scripts/07_stop_FULL_keep_FIXNC.py')
stop = importlib.util.module_from_spec(spec)
spec.loader.exec_module(stop)


class StopTests(unittest.TestCase):
    def test_selects_only_exact_full_names(self):
        text = ('101|run.US-Rpf_AMF_B04_FULL_AD400_BASETA_V1|RUNNING\n'
                '102|st_archive.US-Rpf_AMF_B04_FULL_AD400_BASETA_V1|PENDING\n'
                '103|run.US-Rpf_AMF_B04_FIXNC_AD400_BASETA_V1|RUNNING\n'
                '104|run.US-Rpf_AMF_B03_FULL_AD400_BASETA_V1|RUNNING\n'
                '105|run.US-Rpf_AMF_B04_FULL_AD400_BASETA_V1_OTHER|PENDING\n')
        self.assertEqual([r['id'] for r in stop.selected(stop.parse_queue(text))],['101','102'])

    def test_batch_cancel_never_passes_fixnc_ids(self):
        rows = stop.parse_queue('101|run.US-Ton_AMF_B04_FULL_AD400_BASETA_V1|RUNNING\n'
                                '102|run.US-Ton_AMF_B04_FIXNC_AD400_BASETA_V1|RUNNING\n')
        with patch.object(stop,'command') as call:
            call.return_value.returncode = 0
            call.return_value.stdout = ''
            call.return_value.stderr = ''
            proof = stop.cancel(rows)
            self.assertEqual(proof['requested_ids'],['101'])
            call.assert_called_once_with(['scancel','101'],check=False)

    def test_dry_check_is_read_only_and_cg_is_not_reported_stopped(self):
        rows = stop.parse_queue('101|run.US-Ton_AMF_B04_FULL_AD400_BASETA_V1|COMPLETING\n'
                                '102|run.US-Ton_AMF_B04_FIXNC_AD400_BASETA_V1|RUNNING\n')
        with patch.object(stop,'queue',return_value=rows),patch.object(stop,'command') as command:
            self.assertEqual(stop.stop(False),2)
            command.assert_not_called()  # Fixture has no actual HPC case paths.

    def test_second_sweep_cancels_new_chain_job_id(self):
        before = stop.parse_queue('101|run.US-Ton_AMF_B04_FULL_AD400_BASETA_V1|RUNNING\n')
        racing = stop.parse_queue('201|st_archive.US-Ton_AMF_B04_FULL_AD400_BASETA_V1|PENDING\n')
        after = stop.parse_queue('102|run.US-Ton_AMF_B04_FIXNC_AD400_BASETA_V1|RUNNING\n')
        # Exercise the same apply sequence without touching a real filesystem.
        class MissingPath:
            def __truediv__(self,other): return self
            def is_file(self): return False
        class Receipt:
            def __truediv__(self,other): return self
            def mkdir(self,**kw): pass
            def open(self,*args,**kw):
                import io
                return io.StringIO()
            def write_text(self,text): self.record=json.loads(text)
        receipt = Receipt()
        with patch.object(stop,'B',MissingPath()),patch.object(stop,'EXP',receipt),\
             patch.object(stop,'queue',side_effect=[before,racing,after]),\
             patch.object(stop,'cancel',return_value={'requested_ids':[]}) as cancel:
            self.assertEqual(stop.stop(True),0)
            self.assertEqual(cancel.call_args_list[0].args[0],before)
            self.assertEqual(cancel.call_args_list[1].args[0],racing)
            self.assertEqual(receipt.record['FIXNC_queue_after'][0]['id'],'102')
            self.assertFalse(receipt.record['FIXNC_mutated'])


if __name__ == '__main__':
    unittest.main()
