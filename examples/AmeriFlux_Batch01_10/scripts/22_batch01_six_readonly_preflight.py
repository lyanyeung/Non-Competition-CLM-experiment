#!/usr/bin/env python3
"""Read-only input and case inventory for the six outstanding AmeriFlux Batch01 sites.

Reads existing Stage31/81/82 provenance, raw BIF, original surface and case/
archive evidence. Does not create data, edit cases, submit jobs or infer that
an absent case was never run. Proxy heights are model assumptions, not verified
TA_F sensor crosswalks. Use the same local-standard-to-UTC assumption as the
prior Batch01 technical pilot only after a subsequent site-specific audit.
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
import re
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

SITES = ('CA-Cbo', 'CA-Man', 'CA-TP1', 'CA-TP3', 'US-Aud', 'US-Bar')
PROXY = {'CA-Cbo': ('TA_1_1_1', 42.), 'CA-Man': ('TA_1_1_1', 30.),
         'US-Bar': ('TA_PI_F_1_1_1', 23.8)}
DYNAMIC = {'CA-TP1', 'CA-TP3', 'US-Aud'}
BASE_SHA = '1c1e4171d295406a13d503f877b58661a651c88ffb6f0b6ec498f56bb1fcec5a'


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''): h.update(chunk)
    return h.hexdigest()


def read_json(path):
    if not path.is_file(): return None
    try: return json.loads(path.read_text(encoding='utf-8'))
    except (ValueError, OSError) as e: return {'READ_ERROR': str(e)}


def env(case, key):
    for filename in ('env_run.xml', 'env_case.xml', 'env_build.xml'):
        path = case / filename
        if path.is_file():
            try:
                for entry in ET.parse(path).getroot().iter('entry'):
                    if entry.get('id') == key: return entry.get('value')
            except (OSError, ET.ParseError) as e: return 'READ_ERROR:' + str(e)
    return None


def queue(user):
    try:
        p = subprocess.run(['squeue', '-u', user, '-h', '-o', '%i|%j|%T'],
                           text=True, capture_output=True, timeout=60)
        if p.returncode: return None, p.stderr.strip() or 'squeue failed'
        return [line for line in p.stdout.splitlines() if line], ''
    except (OSError, subprocess.TimeoutExpired) as e: return None, str(e)


def bif(path):
    values = {k: set() for k in ('UTC_OFFSET', 'LOCATION_LAT', 'LOCATION_LONG')}
    with path.open(encoding='utf-8-sig', newline='') as f:
        for row in csv.DictReader(f):
            key = (row.get('VARIABLE') or '').strip().upper()
            value = (row.get('DATAVALUE') or '').strip()
            if key in values and value: values[key].add(value)
    return {k: sorted(v) for k, v in values.items()}


def surface_info(path):
    from netCDF4 import Dataset
    import numpy as np
    with Dataset(str(path)) as ds:
        out = {}
        for key in ('LATIXY', 'LONGXY', 'PCT_NATVEG', 'PCT_CROP', 'PCT_NAT_PFT',
                    'PCT_SAND', 'PCT_CLAY', 'ORGANIC'):
            if key not in ds.variables:
                out[key] = 'MISSING'
                continue
            raw = np.ma.asarray(ds.variables[key][:])
            v = np.asarray(np.ma.filled(raw, np.nan), dtype=float).ravel()
            out[key] = {'count': int(v.size), 'finite': int(np.isfinite(v).sum()),
                        'min': float(np.nanmin(v)) if np.isfinite(v).any() else None,
                        'max': float(np.nanmax(v)) if np.isfinite(v).any() else None}
            if key in ('LATIXY', 'LONGXY', 'PCT_NATVEG', 'PCT_CROP') and len(v) == 1:
                out[key]['value'] = float(v[0]) if np.isfinite(v[0]) else None
        return out


def inventory(root, output, user):
    reports = root / 'experiments/AmeriFlux_MultiSite_10/reports'
    p31 = reports / 'stage31_provisional_ZBOT_scenarios_20261022T022341481986Z/01_provisional_site_height_policies.json'
    p81 = reports / 'stage81_DATM_technical_20261024T162235Z/manifest.json'
    p82 = reports / 'stage82_DATM_case_integration_preflight_20261024T231124502670Z/manifest.json'
    s31, s81, s82 = (read_json(p) for p in (p31, p81, p82))
    q, q_error = queue(user)
    receipt_ok = bool(s81 and s82 and s81.get('stage') == 81 and s82.get('stage') == 82 and
                      s82.get('verified_annual_files_sha256') == 213 and p81.is_file() and
                      s82.get('input_stage81_manifest_sha256') == digest(p81))
    print('=== READ-ONLY SIX-SITE INVENTORY ===')
    print('Stage31:', p31, 'PRESENT' if s31 and 'READ_ERROR' not in s31 else 'MISSING_OR_INVALID')
    print('Stage81:', p81, 'PRESENT' if s81 and 'READ_ERROR' not in s81 else 'MISSING_OR_INVALID')
    print('Stage82 receipt matches Stage81:', receipt_ok)
    print('BASE height snapshot expected SHA256:', BASE_SHA)
    print('QUEUE:', 'AVAILABLE' if q is not None else 'UNAVAILABLE: ' + q_error)
    records = {r.get('site'): r for r in (s81 or {}).get('sites', []) if isinstance(r, dict)}
    policies = (s31 or {}).get('provisional_sensor_policy', {})
    case_root, archive = root / 'cases', output / 'archive'
    for site in SITES:
        print('\n===', site, '===', flush=True)
        rec = records.get(site, {})
        annual = rec.get('annual_files', [])
        years = [r.get('year') for r in annual if isinstance(r, dict)]
        missing = [str(r.get('file')) for r in annual if not Path(str(r.get('file', ''))).is_file()]
        print('STAGE81: years=', rec.get('years', 'UNKNOWN'), 'files=', len(annual),
              'missing=', len(missing), 'years_list=', years)
        if missing: print('MISSING_ANNUAL_FILES:', missing)
        if site in PROXY:
            print('HEIGHT_MODEL_PROXY: variable=%s height_m=%g; TA_F mapping unverified' % PROXY[site])
            if site == 'US-Bar':
                policy = policies.get(site, {})
                print('STAGE31_STATIC_POLICY:', json.dumps(policy, ensure_ascii=False, sort_keys=True))
        else:
            pol = policies.get(site)
            print('STAGE31_DYNAMIC_POLICY:', json.dumps(pol, ensure_ascii=False, sort_keys=True) if pol else 'MISSING')
        forcing = root / 'sites/MY_EC_SITE' / site / 'forcing/raw'
        bifs = sorted(forcing.glob('AMF_' + site + '_FLUXNET_*/AMF_' + site + '_FLUXNET_BIF_*.csv'))
        print('BIF_FILES:', len(bifs))
        for path in bifs:
            try: print('BIF:', path, 'VALUES:', json.dumps(bif(path), sort_keys=True))
            except Exception as e: print('BIF_READ_ERROR:', type(e).__name__, str(e))
        surfdir = root / 'sites/MY_EC_SITE' / site / 'subset_data'
        surfaces = sorted(surfdir.glob('surfdata*.nc'))
        print('SOURCE_SURFACES:', len(surfaces))
        for path in surfaces:
            try: print('SURFACE:', path, json.dumps(surface_info(path), sort_keys=True))
            except Exception as e: print('SURFACE_READ_ERROR:', type(e).__name__, str(e))
        cases = sorted(p for p in case_root.glob(site + '_*') if p.is_dir())
        archives = sorted(p for p in archive.glob(site + '_*') if p.is_dir())
        jobs = [line for line in q or [] if site + '_' in line]
        print('CURRENT_QUEUE_MATCHES:', jobs if q is not None else 'UNKNOWN')
        print('CASE_DIRECTORIES:', [p.name for p in cases])
        print('ARCHIVE_DIRECTORIES:', [p.name for p in archives])
        for case in cases:
            print('CASE:', case.name, 'ACCELERATED=', env(case, 'CLM_ACCELERATED_SPINUP'),
                  'START=', env(case, 'RUN_STARTDATE'), 'REFCASE=', env(case, 'RUN_REFCASE'))
            status = case / 'CaseStatus'
            if status.is_file():
                print('RECENT_CASE_STATUS:', status.read_text(errors='replace').splitlines()[-5:])
        for folder in archives:
            rest = folder / 'rest'
            stamps = sorted(p.name for p in rest.iterdir() if p.is_dir() and re.fullmatch(r'\d{4}-\d{2}-\d{2}-\d{5}', p.name)) if rest.is_dir() else []
            print('ARCHIVE:', folder.name, 'RESTART_COUNT=', len(stamps), 'LATEST=', stamps[-1] if stamps else 'NONE')
    print('\n=== END: No files, cases or jobs were changed. ===')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root', type=Path, default=Path('/iridisfs/scratch/ly3n24/CLM_FATES'))
    p.add_argument('--output', type=Path, default=Path('/scratch/ly3n24/CTSM_FATES_OUTPUTS'))
    p.add_argument('--user', default='ly3n24')
    a = p.parse_args()
    inventory(a.root, a.output, a.user)


if __name__ == '__main__': main()

