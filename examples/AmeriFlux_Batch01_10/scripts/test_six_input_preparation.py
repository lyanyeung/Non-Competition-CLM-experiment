import importlib.util
import json
import shutil
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np
from netCDF4 import Dataset

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('six_prepare', HERE / '23_prepare_six_batch01_inputs.py')
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class SixInputTests(unittest.TestCase):
    def test_utc_shifts_height_with_forcing_and_cyclic_boundary(self):
        policy = {'baseline_m': 4, 'dated_events': [
            {'earliest_possible': '2007-04-01 00:00:00', 'latest_upper_bound': '2007-05-01 00:00:00', 'height_m': 5},
            {'earliest_possible': '2008-01-01 00:00:00', 'latest_upper_bound': '2009-01-01 00:00:00', 'height_m': 6}]}
        vals = mod.utc_heights(2002, 2002, 2023, 10, policy)
        self.assertTrue(np.all(vals[:10] == 6))
        self.assertTrue(np.all(vals[10:] == 4))
        early = mod.utc_heights(2008, 2002, 2023, 10, policy, 'earliest_possible')
        late = mod.utc_heights(2008, 2002, 2023, 10, policy, 'latest_upper_bound')
        self.assertEqual(len(early), 17520)
        self.assertTrue(np.all(early[:10] == 5))
        self.assertTrue(np.all(early[10:] == 6))
        self.assertTrue(np.all(late == 5))

    def test_fates_mapping_keeps_bare_outside_vegetation(self):
        matrix = np.eye(14)
        row = {'site': 'TEST', 'clm_pct_nat_pft_json': '{"0":30,"14":70}',
               'fates_natland_percent_json': '{"14":70}', 'bare_percent': '30'}
        host, mapped = mod.verify_map(row, matrix)
        self.assertEqual(host[0], 30)
        self.assertEqual(mapped, {14: 70.0})
        row['fates_natland_percent_json'] = '{"14":100}'
        with self.assertRaises(ValueError): mod.verify_map(row, matrix)

    def test_surface_changes_land_and_pft_but_preserves_original_soil(self):
        with tempfile.TemporaryDirectory(dir=HERE) as tmp:
            src = Path(tmp) / 'original.nc'; dst = Path(tmp) / 'candidate.nc'
            with Dataset(str(src), 'w') as ds:
                ds.createDimension('one', 1); ds.createDimension('pft', 15); ds.createDimension('soil', 10)
                for k in mod.ZERO_LAND + ('PCT_NATVEG',):
                    ds.createVariable(k, 'f8', ('one',))[:] = [3]
                ds.createVariable('PCT_NAT_PFT', 'f8', ('pft',))[:] = np.zeros(15)
                for k in ('PCT_SAND', 'PCT_CLAY', 'ORGANIC'):
                    ds.createVariable(k, 'f8', ('soil',))[:] = np.arange(10)
            mod.make_surface(src, dst, 'TEST', {0: 30, 14: 70})
            with Dataset(str(dst)) as ds:
                self.assertEqual(float(ds.variables['PCT_NATVEG'][0]), 100)
                self.assertEqual(float(ds.variables['PCT_NAT_PFT'][0]), 30)
                self.assertEqual(float(ds.variables['PCT_NAT_PFT'][14]), 70)
                np.testing.assert_array_equal(ds.variables['ORGANIC'][:], np.arange(10))
                self.assertIn('GRID_SOIL', ds.six_site_soil_policy)

    def test_detached_build_and_completion_receipt(self):
        with tempfile.TemporaryDirectory(dir=HERE) as tmp:
            tmp = Path(tmp); surface = tmp / 'surface.nc'; forcing = tmp / 'input.nc'; param = tmp / 'params.json'
            param.write_text('{}')
            with Dataset(str(surface), 'w') as ds:
                ds.createDimension('one', 1); ds.createDimension('pft', 15); ds.createDimension('soil', 10)
                for k in mod.ZERO_LAND + ('PCT_NATVEG',): ds.createVariable(k, 'f8', ('one',))[:] = 1
                ds.createVariable('PCT_NAT_PFT', 'f8', ('pft',))[:] = np.zeros(15)
                for k in ('PCT_SAND', 'PCT_CLAY', 'ORGANIC'): ds.createVariable(k, 'f8', ('soil',))[:] = np.arange(10)
            with Dataset(str(forcing), 'w') as ds:
                ds.createDimension('time', 17520); ds.createDimension('lat', 1); ds.createDimension('lon', 1)
                ds.createVariable('TBOT', 'f8', ('time', 'lat', 'lon'))[:, 0, 0] = np.arange(17520)
            def reindex(year, original, dest, shift, zbot, prev):
                shutil.copyfile(original, dest)
                with Dataset(str(dest), 'r+') as ds:
                    ds.createVariable('ZBOT', 'f8', ('time', 'lat', 'lon'))[:] = zbot
            def stream():
                root = ET.Element('root'); node = ET.SubElement(root, 'stream_info')
                for name in ('year_first', 'year_last', 'year_align', 'offset', 'datafiles'): ET.SubElement(node, name)
                return root, node
            stage = SimpleNamespace(reindex_one=reindex, stream_template=stream, solar_bad_fraction=lambda *a: 0.)
            site = {'years': (2002, 2002), 'tz': -5, 'NC': [(2002, forcing, mod.sha(forcing))],
                    'ZBOT': 4., 'policy': {'baseline_m': 4, 'dated_events': []}, 'surface': surface,
                    'host': {0: 30, 14: 70}, 'fates': {14: 70}, 'recommendation': 'C4 70 / bare 30',
                    'point_lat_lon': (1., 2.), 'bif_sha256': 'test'}
            target = tmp / 'prepared'
            with patch.object(mod, 'SITES', ('TEST',)):
                mod.build(stage, target, {'TEST': site}, param)
            self.assertEqual(len(json.loads((target / 'COMPLETE.json').read_text())['sites']), 1)
            receipt = json.loads((target / 'TEST/manifest.json').read_text())
            self.assertFalse(receipt['jobs_submitted'])
            with Dataset(str(target / 'TEST/yearly/2002.nc')) as ds:
                self.assertTrue(np.all(ds.variables['ZBOT'][:] == 4))
            with self.assertRaises(ValueError):
                mod.build(stage, target, {'TEST': site}, param)


if __name__ == '__main__': unittest.main()

