import csv
import importlib.util
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from zipfile import ZipFile

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('met_jump_review', HERE / '30_classify_six_met_jumps.py')
mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)


class JumpReviewTests(unittest.TestCase):
    def test_classifies_qc0_observations_without_replacing(self):
        with tempfile.TemporaryDirectory(dir=HERE) as d:
            root = Path(d)
            selected = root / 'selected.csv'
            selected.write_text('time,TA_USE,VPD_USE\n2015-11-06 19:30:00,19.706,9.919\n'
                                '2015-11-06 20:00:00,-20.171,0.617\n2015-11-06 20:30:00,8.508,5.194\n')
            tower = root / 'tower.csv'
            tower.write_text('TIMESTAMP_START,TA_F,TA_F_QC,VPD_F,VPD_F_QC\n'
                '201511061930,19.706,0,9.919,0\n201511062000,-20.171,0,0.617,0\n201511062030,8.508,0,5.194,0\n')
            archive = root / 'era.zip'
            with ZipFile(archive, 'w') as z:
                z.writestr('era.csv', 'TIMESTAMP_START,TA_ERA,VPD_ERA\n201511061930,17.7,3.9\n'
                           '201511062000,17.7,3.7\n201511062030,17.5,3.7\n')
            buffer = io.StringIO(); writer = csv.DictWriter(buffer, fieldnames=mod.COLS); writer.writeheader()
            with patch.object(mod, 'N', 3):
                stats = mod.run_site('US-Bar', (2015, 2015), (selected, tower, (archive, 'era.csv')), writer)
            rows = list(csv.DictReader(io.StringIO(buffer.getvalue())))
            self.assertEqual(stats['local_jumps_gt8_C'], 2)
            self.assertEqual(stats['qc_pairs'], {'0-0': 2})
            self.assertEqual(stats['review_counts']['qc0_endpoint_vs_era_gt10_C'], 2)
            self.assertEqual(len(stats['largest_qc0_era_review_examples']), 2)
            self.assertAlmostEqual(float(rows[0]['selected_step_C']), -39.877)
            self.assertEqual(rows[0]['era_right_C'], '17.7')
            self.assertEqual(rows[0]['left_selected_differs_tower'], 'False')

    def test_alignment_mismatch_is_not_silently_joined(self):
        with tempfile.TemporaryDirectory(dir=HERE) as d:
            root = Path(d)
            a = root/'a.csv'; a.write_text('time,TA_USE\n2002-01-01 00:00:00,2\n')
            b = root/'b.csv'; b.write_text('TIMESTAMP_START,TA_F\n200201010030,3\n')
            c = root/'c.csv'; c.write_text('TIMESTAMP_START,TA_ERA\n200201010000,4\n')
            with patch.object(mod, 'N', 1), self.assertRaisesRegex(ValueError, 'timestamps differ'):
                list(mod.observe(a, b, c, 2002, 2002))


if __name__ == '__main__': unittest.main()

