import csv
import hashlib
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np
from netCDF4 import Dataset

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('usbar_candidate', HERE / '32_usbar_inspectable_candidate.py')
mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)


def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class InspectableCandidateTests(unittest.TestCase):
    def test_utc_mapping_and_cycle_wrap(self):
        self.assertEqual([mod.utc_index(t, 10, 2004, 2023) for t in mod.TIMES],
                         [(2015, 14882), (2015, 14883), (2015, 14884)])
        self.assertEqual(mod.utc_index('2023-12-31 23:30:00', 10, 2004, 2023), (2004, 9))
        self.assertEqual(mod.utc_index('2008-03-01 00:00:00', 10, 2004, 2023), (2008, 2842))
        with self.assertRaises(ValueError): mod.utc_index('2008-02-29 00:00:00', 10, 2004, 2023)

    def test_recorded_candidate_preserves_source_and_other_fields(self):
        points = {mod.LEFT: (19.706, 9.919, 17.701, 94200),
                  mod.TIMES[0]: (-20.171, .617, 17.726, 94200),
                  mod.TIMES[1]: (8.508, 5.194, 17.554, 94300),
                  mod.TIMES[2]: (-17.178, .82, 17.381, 94300),
                  mod.RIGHT: (17.455, 9.392, 17.190, 94400)}
        with tempfile.TemporaryDirectory(dir=HERE) as temp:
            base = Path(temp); root = base/'run'; proposals = base/'proposals'; out = base/'candidate'
            root.mkdir(); proposals.mkdir(); source = root/'US-Bar_2015.nc'; selected = base/'source.csv'; selected.write_text('pinned input')
            with Dataset(str(source), 'w') as ds:
                ds.createDimension('time', 17520); ds.createDimension('lat', 1); ds.createDimension('lon', 1)
                for name in ('TBOT','QBOT','SHUM','RH','PSRF','FSDS'):
                    ds.createVariable(name, 'f8', ('time','lat','lon'))[:] = 1.
                for t in mod.TIMES:
                    temperature, vpd, _, pressure = points[t]; _, i = mod.utc_index(t, 10, 2004, 2023)
                    q, rh = mod.q_from_tvpd(temperature, vpd, pressure)
                    for k, v in {'TBOT': temperature+273.15, 'QBOT': q, 'SHUM': q, 'RH': rh, 'PSRF': pressure}.items():
                        ds.variables[k][i,0,0] = v
            orig_sha = sha(source)
            manifest = root/'US-Bar.json'; manifest.write_text(json.dumps({'site':'US-Bar','years':[2004,2023],
                'UTC_shift_halfhours':10,'case_created':False,'jobs_submitted':False,
                'annual_files':[{'year':2015,'path':str(source),'sha256':orig_sha}]}))
            (root/'COMPLETE.json').write_text(json.dumps({'sites':[{'site':'US-Bar','manifest':str(manifest),'sha256':sha(manifest)}]}))
            (proposals/'summary.json').write_text(json.dumps({'errors':[], 'results':[{'site':'US-Bar','selected_forcing_sha256':sha(selected)}]}))
            (proposals/'suspects.csv').write_text('site,status\nCA-Cbo,HOLD_NO_TWO_CORROBORATED_QC0_ANCHORS\n')
            rows=[]
            for k,t in enumerate(mod.TIMES,1):
                temperature=19.706+(17.455-19.706)*k/4; vpd=9.919+(9.392-9.919)*k/4
                q,_=mod.q_from_tvpd(temperature,vpd,points[t][3])
                rows.append({'site':'US-Bar','time_local':t,'left_anchor':mod.LEFT,'right_anchor':mod.RIGHT,
                             'status':'CANDIDATE_NOT_APPLIED','proposed_TA_C':temperature,
                             'proposed_VPD_hPa':vpd,'proposed_QBOT_kgkg':q})
            with (proposals/'candidate_changes_NOT_APPLIED.csv').open('w', newline='') as f:
                w=csv.DictWriter(f,fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
            selection = base/'stage80.tsv'; selection.write_text('site\tselected_source\tselected_sha256\nUS-Bar\t'+str(selected)+'\t'+sha(selected)+'\n')
            data={t:{'selected':{'TA_USE':str(v[0]),'VPD_USE':str(v[1]),'PSRF':str(v[3])},
                     'tower':{'TA_F':str(v[0]),'TA_F_QC':'0','VPD_F':str(v[1]),'VPD_F_QC':'0'},
                     'era':{'TA_ERA':str(v[2])}} for t,v in points.items()}
            raw = base/'raw'; era = base/'era'
            def read(p, *args):
                key = 'selected' if p == selected else 'tower' if p == raw else 'era'
                return {t: x[key] for t,x in data.items()}
            helper = SimpleNamespace(sha=sha, sources=lambda site,k: (raw, {'status':'EXTRACTED'}) if k=='FLUXMET_HH' else (era, {'status':'RELEASE_ZIP'}), read_subset=read)
            argv=['script','--run',str(root),'--proposals',str(proposals),'--helper','unused','--out',str(out)]
            with patch.object(sys, 'argv', argv), patch.object(mod, 'module', return_value=helper), patch.object(mod, 'STAGE80', selection):
                mod.main()
            self.assertEqual(sha(source), orig_sha)
            with Dataset(str(out/'US-Bar_2015_UTC_sensitivity_NOT_APPLIED.nc')) as ds:
                self.assertAlmostEqual(float(ds.variables['TBOT'][14882,0,0])-273.15, 19.14325)
                self.assertEqual(float(ds.variables['FSDS'][14882,0,0]), 1.)
            obj=json.loads((out/'manifest.json').read_text())
            self.assertTrue(obj['no_original_files_or_cases_modified'])
            self.assertTrue(obj['no_slurm_jobs_submitted'])


if __name__ == '__main__': unittest.main()

