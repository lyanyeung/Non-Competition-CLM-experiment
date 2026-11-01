import importlib.util
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('met_context', HERE / '28_six_met_flag_context.py')
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class ContextTests(unittest.TestCase):
    def test_source_local_year_wrap_and_leap_day(self):
        self.assertEqual(mod.source_stamp(1996, 0, 1996, 2024, 10), '2024-12-31 19:00:00')
        self.assertEqual(mod.source_stamp(1996, 10, 1996, 2024, 10), '1996-01-01 00:00:00')
        self.assertEqual(mod.source_stamp(2008, 59 * 48 + 10, 2002, 2023, 10), '2008-03-01 00:00:00')

    def test_selected_raw_timestamps_match_local_times(self):
        with tempfile.TemporaryDirectory(dir=HERE) as tmp:
            f = Path(tmp) / 'raw.csv'
            f.write_text('TIMESTAMP_START,TA_F,TA_F_QC\n200204010030,9.5,0\n')
            found = mod.lookup(f, 'TIMESTAMP_START', {'2002-04-01 00:30:00'}, ('TA_F', 'TA_F_QC'), True)
            self.assertEqual(found['2002-04-01 00:30:00']['TA_F_QC'], '0')


if __name__ == '__main__': unittest.main()

