#!/usr/bin/env python3
"""Prepare a read-only, hash-verified DE-Gri DATM input plan.

Reuses the 22 historical annual files, with two detached sensitivities. This
does not create a case, change a stream, or authorize a model submission.
"""
import argparse
import csv
import hashlib
import json
from pathlib import Path

SURFACE_SHA = '08887d2daf5d529b5fed89ca21c8094e19dd471ff3387a758ce23b471211ed2b'
STAGE = 'STAGE03B_BATCH04_REUSE_FLUXNET13_STAGE28_STAGE29B_30_SOURCE_LINEAGE'
FILENAMES = {'STAGE30_CONSOLIDATED': '04_consolidated_13site_271_DATM_SHA256_manifest.csv',
             'STAGE29B': '10_annual_full_DATM_SHA256_manifest.csv'}


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for part in iter(lambda: f.read(1024*1024), b''):
            h.update(part)
    return h.hexdigest()


def load(path):
    return json.loads(path.read_text(encoding='utf-8'))


def plan(b, m, surface, receipt):
    if b.get('stage') != STAGE or b.get('read_only') is not True or b.get('science_release') is not False:
        raise ValueError('Expected Stage03B science HOLD report')
    sites = [x for x in b['sites'] if x.get('site') == 'DE-Gri']
    if len(sites) != 1 or sites[0].get('all_current_paths_match_historical') is not True or sites[0].get('stage28_met_SHA_verified') is not True:
        raise ValueError('Stage03B DE-Gri lineage not verified')
    if sha(surface) != SURFACE_SHA:
        raise ValueError('Approved DE-Gri surface SHA mismatch')
    if receipt.get('site') != 'DE-Gri' or receipt.get('candidate_sha256') != SURFACE_SHA or receipt.get('model_proxy_GitHub_approved') is not True:
        raise ValueError('Approved DE-Gri surface receipt mismatch')
    if m.get('site') != 'DE-Gri' or m.get('status') != 'DETACHED_SENSITIVITY_NOT_RELEASED' or m.get('case_or_slurm_modified') is not False:
        raise ValueError('Expected detached sensitivity DATM manifest')
    overrides = {}
    for r in m.get('annual_files', []):
        year = int(r['year'])
        if year not in (2011, 2024) or year in overrides or r.get('logical_all_variables_verified') is not True or r.get('edits') != {2011:11, 2024:23}[year]:
            raise ValueError('Unexpected sensitivity candidate scope')
        path = Path(r['candidate_path'])
        if not path.is_file() or sha(path) != r['candidate_sha256']:
            raise ValueError('Sensitivity candidate missing or hash changed')
        overrides[year] = r
    if set(overrides) != {2011, 2024}:
        raise ValueError('Both verified 2011/2024 candidates required')
    s = sites[0]
    history = Path(s['historical_DATM_manifest'])
    if history.is_dir():
        key = s.get('historical_manifest_selected')
        if key not in FILENAMES:
            raise ValueError('Unknown historical manifest')
        history = history / FILENAMES[key]
    with history.open(encoding='utf-8-sig', newline='') as f:
        rows = [r for r in csv.DictReader(f) if r.get('site') == 'DE-Gri']
    years = set(range(2004, 2026))
    if len(rows) != 22 or {int(r['year']) for r in rows} != years:
        raise ValueError('Expected complete DE-Gri 2004–2025 annual manifest')
    comparisons = {int(x['year']): x for x in s['yearly_path_comparisons']}
    if len(s['yearly_path_comparisons']) != 22 or set(comparisons) != years:
        raise ValueError('Stage03B annual path count/year mismatch')
    result = []
    for r in sorted(rows, key=lambda x: int(x['year'])):
        y = int(r['year']); entry = comparisons[y]
        original = Path(r['datm_nc']); expected = r['sha256']
        if entry.get('literal_path_equal') is not True or entry.get('current') != str(original) or len(expected) != 64 or not original.is_file() or sha(original) != expected:
            raise ValueError('Annual historical path or SHA mismatch: '+str(y))
        use = overrides.get(y)
        if use and (use['baseline_path'] != str(original) or use['baseline_sha256'] != expected):
            raise ValueError('Sensitivity original does not match historical annual: '+str(y))
        result.append({'year':y, 'kind':'approved_sensitivity' if use else 'historical_baseline',
                       'path':use['candidate_path'] if use else str(original),
                       'sha256':use['candidate_sha256'] if use else expected})
    return {'site':'DE-Gri','status':'INPUT_PLAN_ONLY_NOT_MODEL_RELEASE', 'surface_path':str(surface),
            'surface_sha256':SURFACE_SHA, 'annual_inputs':result,
            'case_or_slurm_modified':False,'source_science_or_soil_release':False,
            'time_alignment_caveat':'no-leap DATM verified, independent source clock still a science uncertainty'}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--stage03b',type=Path,required=True)
    p.add_argument('--datm-dir',type=Path,required=True)
    p.add_argument('--surface-dir',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    a=p.parse_args()
    surface=a.surface_dir/'DE-Gri_B04_GITHUBPFT_POINT_CANDIDATE.nc'
    receipt=load(a.surface_dir/'DE-Gri_B04_surface_manifest.json')
    result=plan(load(a.stage03b),load(a.datm_dir/'manifest_PRIVATE.json'),surface,receipt)
    with a.out.open('x',encoding='utf-8') as f:
        json.dump(result,f,indent=2);f.write('\n')
    for row in result['annual_inputs']:
        print('DATM PLAN',json.dumps(row,separators=(',',':')))
    print('INPUT PLAN COMPLETE 22 years; 2 sensitivities; surface hash verified; NO CASE/SLURM |',a.out)


if __name__=='__main__':main()
