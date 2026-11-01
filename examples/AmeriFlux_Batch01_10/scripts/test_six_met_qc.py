import importlib.util
import json
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

import numpy as np
from netCDF4 import Dataset

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('six_qc', HERE / '25_audit_six_prepared_met.py')
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def sample_nc(path, year, bad_q=False):
    with Dataset(str(path), 'w') as ds:
        ds.createDimension('time', mod.N); ds.createDimension('lat', 1); ds.createDimension('lon', 1)
        time = ds.createVariable('time', 'f8', ('time',))
        time.units = f'days since {year}-01-01 00:00:00'; time.calendar = 'noleap'
        time[:] = np.arange(mod.N) / 48. + 1. / 96.
        t = np.full(mod.N, 288.15); q = np.full(mod.N, .005); p = np.full(mod.N, 100000.)
        t[100] += 9.; rh = mod.rh_from_state(t, q, p)
        if bad_q: q[3] = 0.
        data = {'TBOT': t, 'QBOT': q, 'SHUM': q, 'PSRF': p, 'FSDS': np.full(mod.N, 200.),
                'FLDS': np.full(mod.N, 300.), 'WIND': np.full(mod.N, 2.), 'PRECTmms': np.zeros(mod.N),
                'RH': rh, 'ZBOT': np.full(mod.N, 10.)}
        for name, unit in mod.UNITS.items():
            v = ds.createVariable(name, 'f8', ('time', 'lat', 'lon'))
            v.units = unit; v[:, 0, 0] = data[name]


class MetTests(unittest.TestCase):
    def test_full_year_timing_humidity_and_jump_flags(self):
        with tempfile.TemporaryDirectory(dir=HERE) as tmp:
            path = Path(tmp) / 'year.nc'; sample_nc(path, 2008)
            info, final = mod.scan_year(path, 2008)
            self.assertEqual(info['samples'], 17520)
            self.assertEqual(info['temperature_jumps_gt8C'], 2)
            self.assertEqual(final, 288.15)
            _, _ = mod.scan_year(path, 2008, previous_t=280.)
            with self.assertRaises(ValueError): mod.scan_year(path, 2009)

    def test_invalid_specific_humidity_fails(self):
        with tempfile.TemporaryDirectory(dir=HERE) as tmp:
            path = Path(tmp) / 'year.nc'; sample_nc(path, 2002, bad_q=True)
            with self.assertRaisesRegex(ValueError, 'QBOT'): mod.scan_year(path, 2002)

    def test_site_validates_hashes_and_stream_reference(self):
        with tempfile.TemporaryDirectory(dir=HERE) as tmp:
            root = Path(tmp); year = root / '2002.nc'; sample_nc(year, 2002)
            surface = root / 's.nc'; surface.write_bytes(b'surface')
            stream = root / 'stream.xml'; x = ET.Element('root'); node = ET.SubElement(x, 'stream_info', name='CLM_USRDAT.UNSET')
            for k, v in [('year_first', 2002), ('year_last', 2002), ('year_align', 2002), ('offset', 0)]:
                ET.SubElement(node, k).text = str(v)
            ET.SubElement(ET.SubElement(node, 'datafiles'), 'file').text = str(year)
            ET.ElementTree(x).write(str(stream), encoding='utf-8', xml_declaration=True)
            obj = {'site': 'TEST', 'jobs_submitted': False, 'case_created': False,
                   'candidate_surface': str(surface), 'candidate_surface_sha256': mod.sha(surface),
                   'detached_stream': str(stream), 'detached_stream_sha256': mod.sha(stream),
                   'years': [2002, 2002], 'UTC_shift_halfhours': 10,
                   'annual_files': [{'year': 2002, 'path': str(year), 'sha256': mod.sha(year)}]}
            manifest = root / 'manifest.json'; manifest.write_text(json.dumps(obj))
            record = {'site': 'TEST', 'manifest': str(manifest), 'sha256': mod.sha(manifest)}
            self.assertEqual(mod.audit_site(root.resolve(), record)['samples'], 17520)
            surface.write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError, 'Checksum mismatch'): mod.audit_site(root.resolve(), record)


if __name__ == '__main__': unittest.main()

