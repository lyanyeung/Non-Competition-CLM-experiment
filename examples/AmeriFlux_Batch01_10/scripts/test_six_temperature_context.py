import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from zipfile import ZipFile

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('temperature_context', HERE / '29_six_extreme_temperature_context.py')
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class TemperatureContextTests(unittest.TestCase):
    def test_excludes_cycle_wrap_and_collapses_nearby_events(self):
        def ev(a, b): return {'left_local': a, 'right_local': b}
        events = [ev('2023-12-31 23:30:00', '2002-01-01 00:00:00'),
                  ev('2015-11-06 19:30:00', '2015-11-06 20:00:00'),
                  ev('2015-11-06 20:00:00', '2015-11-06 20:30:00'),
                  ev('2023-02-04 05:30:00', '2023-02-04 06:00:00')]
        out = mod.distinct_events(events)
        self.assertEqual(len(out), 2)
        self.assertEqual(out[0][1]['right_local'], '2015-11-06 20:00:00')

    def test_lookup_matches_compact_and_preserves_original_qc(self):
        with tempfile.TemporaryDirectory(dir=HERE) as tmp:
            p = Path(tmp) / 'source.csv'; p.write_text('TIMESTAMP_START,TA_F,TA_F_QC\n201511062000,-20.171,0\n')
            rows = mod.read_subset(p, 'TIMESTAMP_START', {'2015-11-06 20:00:00'}, ('TA_F', 'TA_F_QC'), True)
            self.assertEqual(rows['2015-11-06 20:00:00'], {'TA_F': '-20.171', 'TA_F_QC': '0'})

    def test_missing_era_is_reported_without_stopping(self):
        with tempfile.TemporaryDirectory(dir=HERE) as tmp:
            root = Path(tmp); (root / 'CA-Cbo/forcing/raw/AMF_CA-Cbo_FLUXNET_TEST').mkdir(parents=True)
            with patch.object(mod, 'RAW', root):
                source, info = mod.sources('CA-Cbo', 'ERA5_HH')
            self.assertIsNone(source)
            self.assertEqual(info['status'], 'MISSING')

    def test_reads_single_original_zip_member_without_extracting(self):
        with tempfile.TemporaryDirectory(dir=HERE) as tmp:
            root = Path(tmp); package = 'AMF_CA-Cbo_FLUXNET_TEST'
            (root / 'CA-Cbo/forcing/raw' / package).mkdir(parents=True)
            folder = root / 'CA-Cbo/forcing/packages'; folder.mkdir(parents=True)
            archive = folder / (package + '.zip')
            with ZipFile(archive, 'w') as z:
                z.writestr('nested/CA-Cbo_ERA5_HH.csv', 'TIMESTAMP_START,TA_ERA\n201511062000,3.5\n')
            with patch.object(mod, 'RAW', root):
                source, info = mod.sources('CA-Cbo', 'ERA5_HH')
                found = mod.read_subset(source, 'TIMESTAMP_START', {'2015-11-06 20:00:00'}, ('TA_ERA',), True)
            self.assertEqual(info['status'], 'RELEASE_ZIP')
            self.assertEqual(found['2015-11-06 20:00:00']['TA_ERA'], '3.5')
            self.assertFalse((root / 'CA-Cbo/forcing/raw' / package / 'nested').exists())


if __name__ == '__main__': unittest.main()

