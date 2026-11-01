import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

import numpy as np

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('six_ad5', HERE / '26_six_ad5_case_preparation.py')
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class AD5PreparationTests(unittest.TestCase):
    def test_readonly_check_and_smoke_settings(self):
        with tempfile.TemporaryDirectory(dir=HERE) as tmp:
            tmp = Path(tmp); param = tmp / 'fates.json'; param.write_text('{}')
            helper = SimpleNamespace(B=tmp / 'base', OUT=tmp / 'output', TEMPLATE=tmp / 'template',
                template_info=lambda: {'paramfile': param, 'param_sha256': mod.digest(param)},
                co2_table=lambda p: ({2002: 373.}, str(p), 'test'), _json_map=lambda obj: np.eye(14),
                queued=lambda _: [], sacct_name=lambda _: [])
            helper.case_dir = lambda s: helper.B / 'cases' / helper.name(s)
            helper.arch_dir = lambda s: helper.OUT / 'archive' / helper.name(s)
            helper.ledger = lambda s: helper.D06 / (s + '_state.json')
            data = {s: {'years': (2002, 2003), 'manifest': tmp / (s + '.json'), 'files': [],
                        'surface': {'path': tmp / 'surface.nc', 'host': {1: 100.}, 'lat': 1., 'lon': 2.},
                        'fates': {1: 100.}, 'receipt': {'fates_parameter_sha256': mod.digest(param),
                          'UTC_offset_hours': -5, 'height_policy': {'baseline_m': 4., 'dated_events': []}}}
                    for s in mod.SITES}
            for s in mod.SITES: data[s]['manifest'].write_text('{}')
            mod.configure(helper, tmp, data)
            self.assertEqual(helper.SEGMENTS, 1)
            self.assertEqual(helper.SEG_YEARS, 5)
            self.assertTrue(helper.name('CA-TP1').endswith('_FIXNC_AD400_AD5'))
            ctx = mod.check(helper, tmp, data, tmp / 'co2.csv')
            self.assertEqual(len(ctx['surface']), 6)
            self.assertFalse(helper.D06.exists())
            helper.case_dir('CA-Man').mkdir(parents=True)
            with self.assertRaisesRegex(ValueError, 'existing case'):
                mod.check(helper, tmp, data, tmp / 'co2.csv')

    def test_prepare_relabels_inherited_protocol_and_records_dynamic_height(self):
        with tempfile.TemporaryDirectory(dir=HERE) as tmp:
            tmp = Path(tmp)
            def ledger(s): return tmp / (s + '.json')
            def write(path, obj): Path(path).write_text(json.dumps(obj))
            def run(s, ctx): write(ledger(s), {'phase': 'CASE_VERIFIED_NOT_SUBMITTED', 'protocol': 'DIRECT_400'})
            helper = SimpleNamespace(ledger=ledger, prepare_one=run,
                                     load=lambda p: json.loads(Path(p).read_text()), save=write)
            data = {s: {'manifest': tmp / (s + '.input'), 'receipt': {'height_policy':
                         {'dated_events': [{'height_m': 5}] if s == 'US-Aud' else []}}} for s in mod.SITES}
            for s in mod.SITES: data[s]['manifest'].write_text('{}')
            mod.prepare(helper, data, {})
            obj = json.loads(ledger('US-Aud').read_text())
            self.assertEqual(obj['protocol'], 'AD5_SMOKE_ONLY_RESUBMIT_0_NO_AUTOMATIC_CONTINUATION')
            self.assertEqual(obj['height_type'], 'DYNAMIC')


if __name__ == '__main__': unittest.main()

