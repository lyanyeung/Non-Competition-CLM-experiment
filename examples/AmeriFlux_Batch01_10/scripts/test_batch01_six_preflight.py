import contextlib
import importlib.util
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('six_preflight', HERE / '22_batch01_six_readonly_preflight.py')
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class PreflightTests(unittest.TestCase):
    def test_reports_each_site_missing_assets_and_unknown_queue(self):
        with tempfile.TemporaryDirectory(dir=HERE) as tmp:
            tmp = Path(tmp)
            buf = io.StringIO()
            with patch.object(mod, 'queue', return_value=(None, 'unavailable')), contextlib.redirect_stdout(buf):
                mod.inventory(tmp / 'model', tmp / 'outputs', 'user')
            output = buf.getvalue()
            for site in mod.SITES:
                self.assertIn('=== ' + site + ' ===', output)
            self.assertIn('QUEUE: UNAVAILABLE', output)
            self.assertIn('CURRENT_QUEUE_MATCHES: UNKNOWN', output)
            self.assertIn('STAGE31_DYNAMIC_POLICY: MISSING', output)
            self.assertIn('height_m=42', output)
            self.assertIn('TA_F mapping unverified', output)
            self.assertEqual(list(tmp.iterdir()), [])

    def test_receipt_validation_and_archive_discovery(self):
        with tempfile.TemporaryDirectory(dir=HERE) as tmp:
            tmp = Path(tmp); root = tmp / 'model'; out = tmp / 'out'
            reports = root / 'experiments/AmeriFlux_MultiSite_10/reports'
            s81 = reports / 'stage81_DATM_technical_20261024T162235Z/manifest.json'
            s82 = reports / 'stage82_DATM_case_integration_preflight_20261024T231124502670Z/manifest.json'
            s81.parent.mkdir(parents=True); s82.parent.mkdir(parents=True)
            s81.write_text(json.dumps({'stage': 81, 'sites': []}))
            s82.write_text(json.dumps({'stage': 82, 'verified_annual_files_sha256': 213,
                                       'input_stage81_manifest_sha256': mod.digest(s81)}))
            rest = out / 'archive/CA-Man_AMF_FIXNC_NORMAL400/rest/2400-01-01-00000'
            rest.mkdir(parents=True)
            buf = io.StringIO()
            with patch.object(mod, 'queue', return_value=([], '')), contextlib.redirect_stdout(buf):
                mod.inventory(root, out, 'user')
            result = buf.getvalue()
            self.assertIn('Stage82 receipt matches Stage81: True', result)
            self.assertIn('CA-Man_AMF_FIXNC_NORMAL400', result)
            self.assertIn('LATEST= 2400-01-01-00000', result)


if __name__ == '__main__': unittest.main()

