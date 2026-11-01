#!/usr/bin/env python3
"""Prepare six Batch01 AD5 cases from Stage23 inputs; no Slurm submissions.

Reuses the proven Batch02 Stage06 CIME clone/preview/validation machinery with
one 5-year segment and RESUBMIT=0. All inputs and a real template are verified
before creating new site-specific case directories. Existing cases and attempt
ledgers are never overwritten. Scientific Met flags remain review items.
"""
from __future__ import annotations
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path

import numpy as np
from netCDF4 import Dataset

SITES = ('CA-Cbo', 'CA-Man', 'CA-TP1', 'CA-TP3', 'US-Aud', 'US-Bar')
HELPER_BLOB = 'decc61898a89109c3819faca2c8c3134ebed77ee'


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for part in iter(lambda: f.read(1048576), b''): h.update(part)
    return h.hexdigest()


def load_helper(path):
    data = Path(path).read_bytes()
    blob = hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()
    if blob != HELPER_BLOB: raise ValueError('Batch02 helper source checksum mismatch')
    spec = importlib.util.spec_from_file_location('validated_batch02_stage06', path)
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    return mod


def safe_file(path, expected_hash, root):
    path = Path(path).resolve(strict=True)
    if root not in path.parents: raise ValueError('Path outside candidate root: ' + str(path))
    if digest(path) != expected_hash: raise ValueError('SHA256 mismatch: ' + str(path))
    return path


def inputs(root):
    root = Path(root).resolve(strict=True)
    done = json.loads((root / 'COMPLETE.json').read_text())
    records = done.get('sites', [])
    if len(records) != 6 or {r.get('site') for r in records} != set(SITES) or done.get('model_jobs_submitted') is not False:
        raise ValueError('Stage23 six-site completion receipt invalid')
    result = {}
    for rec in records:
        site = rec['site']; path = safe_file(rec['manifest'], rec['sha256'], root)
        obj = json.loads(path.read_text())
        if obj.get('site') != site or obj.get('case_created') is not False or obj.get('jobs_submitted') is not False:
            raise ValueError(site + ': input receipt invalid')
        surface = safe_file(obj['candidate_surface'], obj['candidate_surface_sha256'], root)
        safe_file(obj['detached_stream'], obj['detached_stream_sha256'], root)
        years = tuple(obj['years']); files = obj['annual_files']
        if len(years) != 2 or [r['year'] for r in files] != list(range(years[0], years[1] + 1)):
            raise ValueError(site + ': forcing years incomplete')
        nc = [safe_file(r['path'], r['sha256'], root) for r in files]
        host = {int(k): float(v) for k, v in obj['host_pct'].items()}
        fates = {int(k): float(v) for k, v in obj['fates_pct'].items()}
        with Dataset(str(surface)) as ds:
            pft = np.ma.filled(ds.variables['PCT_NAT_PFT'][:], np.nan).ravel()
            if pft.size != 15 or not np.allclose(pft, [host.get(i, 0.) for i in range(15)], atol=1e-4):
                raise ValueError(site + ': surface host PFT mismatch')
            lat = float(np.asarray(ds.variables['LATIXY'][:]).ravel()[0])
            lon = float(np.asarray(ds.variables['LONGXY'][:]).ravel()[0]) % 360
            nat = float(np.asarray(ds.variables['PCT_NATVEG'][:]).ravel()[0])
            if abs(nat - 100) > 1e-4: raise ValueError(site + ': natural landunit mismatch')
        result[site] = {'manifest': path, 'receipt': obj, 'years': years, 'files': nc,
                        'surface': {'path': surface, 'sha256': obj['candidate_surface_sha256'],
                                    'host': host, 'lat': lat, 'lon': lon}, 'fates': fates}
    return root, result


def configure(helper, root, data):
    helper.SITES = {s: data[s]['years'] for s in SITES}
    helper.ORDER = SITES
    helper.ARCTIC = ()
    helper.SEGMENTS = 1  # AD5 smoke only, no automatic continuation.
    helper.SEG_YEARS = 5
    helper.D06 = helper.B / 'experiments/NonCompetitionObserved22/AmeriFlux_Batch01_10/Stage26_six_AD5'
    helper.name = lambda site: f'{site}_AMF_B01SIX_FIXNC_AD400_AD5'
    helper.surface = lambda site: data[site]['surface']['path']
    helper.forcing_dir = lambda site: root / site
    helper.stage95_files = lambda site, full_sha=False: data[site]['files']
    helper.build_forcing = lambda site, files, surface, clock: {
        'files': [{'path': str(p)} for p in files], 'step_minutes': 30}


def check(helper, root, data, co2_file, sites=SITES):
    template = helper.template_info()
    co2, co2_src, co2_sha = helper.co2_table(co2_file)
    for site in sites:
        v = co2[data[site]['years'][0]]
        if not 250 < v < 500: raise ValueError(site + ': first-year CO2 outside expected range')
    matrix = helper._json_map(json.loads(template['paramfile'].read_text()))
    ctx = {'tpl': template, 'co2': co2, 'co2_src': co2_src + ' sha256=' + co2_sha,
           'surface': {}, 'clock': {}}
    for site in sites:
        obj = data[site]['receipt']; host = data[site]['surface']['host']
        if obj['fates_parameter_sha256'] != template['param_sha256']:
            raise ValueError(site + ': Stage23 FATES parameters do not match actual template')
        mapped = {}
        for i, val in host.items():
            if i:
                for slot, weight in enumerate(matrix[i - 1]):
                    if weight > 0: mapped[slot + 1] = mapped.get(slot + 1, 0.) + val * float(weight)
        expected = data[site]['fates']
        if any(abs(mapped.get(k, 0) - expected.get(k, 0)) > 1e-3 for k in set(mapped) | set(expected)):
            raise ValueError(site + ': FATES mapping differs from template')
        case = helper.case_dir(site); ledger = helper.ledger(site)
        for p in (case, helper.OUT / helper.name(site), helper.arch_dir(site), ledger):
            if p.exists() or p.is_symlink(): raise ValueError(site + ': existing case/output/ledger ' + str(p))
        if helper.queued(helper.name(site)) or helper.sacct_name(helper.name(site)):
            raise ValueError(site + ': matching Slurm jobs already exist')
        pol = obj['height_policy']
        ctx['surface'][site] = data[site]['surface']
        ctx['clock'][site] = {'utc_offset_h': float(obj['UTC_offset_hours']),
                              'zbot_m': float(pol['baseline_m']),
                              'height_policy': pol,
                              'zbot_note': 'baseline only; actual file can have dynamic ZBOT',
                              'source_receipt_sha256': digest(data[site]['manifest'])}
        print('CHECK PASS', site, 'years', data[site]['years'], 'case', helper.name(site),
              'CO2', co2[data[site]['years'][0]], 'height baseline', pol['baseline_m'],
              'events', len(pol.get('dated_events', [])), flush=True)
    print('TEMPLATE:', helper.TEMPLATE, 'FATES SHA:', template['param_sha256'], flush=True)
    print('CHECK COMPLETE: 5-year AD smoke only, RESUBMIT=0; no cases or jobs created.', flush=True)
    return ctx


def prepare(helper, data, ctx, sites=SITES):
    for site in sites:
        helper.prepare_one(site, ctx)
        path = helper.ledger(site)
        ledger = helper.load(path)
        if ledger.get('phase') != 'CASE_VERIFIED_NOT_SUBMITTED':
            raise ValueError(site + ': preview did not establish verified unsubmitted case')
        ledger['protocol'] = 'AD5_SMOKE_ONLY_RESUBMIT_0_NO_AUTOMATIC_CONTINUATION'
        ledger['stage23_input_manifest'] = str(data[site]['manifest'])
        ledger['stage23_input_manifest_sha256'] = digest(data[site]['manifest'])
        ledger['height_type'] = 'DYNAMIC' if data[site]['receipt']['height_policy'].get('dated_events') else 'STATIC_PROXY'
        ledger['scientific_met_flags'] = 'Previously identified RH and temperature flags remain for scientific review'
        helper.save(path, ledger)
        print('AD5 CASE VERIFIED', site, 'NO SLURM SUBMITTED', flush=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('action', choices=('check', 'prepare'))
    ap.add_argument('--run', type=Path, required=True)
    ap.add_argument('--helper', type=Path, required=True)
    ap.add_argument('--co2-csv', type=Path, required=True)
    ap.add_argument('--sites', nargs='+', choices=SITES, help='Limit to unprepared sites after a partial run')
    args = ap.parse_args()
    root, data = inputs(args.run)
    helper = load_helper(args.helper)
    configure(helper, root, data)
    sites = tuple(s for s in SITES if not args.sites or s in args.sites)
    ctx = check(helper, root, data, args.co2_csv, sites)
    if args.action == 'prepare': prepare(helper, data, ctx, sites)
    else: print('Read-only preflight only; use prepare after checking output.', flush=True)


if __name__ == '__main__': main()

