#!/usr/bin/env python3
"""Create a detached US-Bar 2015 forcing sensitivity for three reported points.

The input and original cases are never modified and this does not submit jobs.
It checks the exact Stage23/Stage80 lineage, raw observations, QC0 anchors,
ERA5 comparison, interpolation, and coupled humidity before copying one NC.
Also reports the original HOLD reasons for the other six-site candidates.
"""
from __future__ import annotations
import argparse
import calendar
from collections import Counter
import csv
from datetime import datetime
import importlib.util
import json
import math
import shutil
from pathlib import Path

import numpy as np
from netCDF4 import Dataset

SITE = 'US-Bar'
LEFT = '2015-11-06 19:30:00'
RIGHT = '2015-11-06 21:30:00'
TIMES = ('2015-11-06 20:00:00', '2015-11-06 20:30:00', '2015-11-06 21:00:00')
FIELDS = {'TBOT', 'QBOT', 'SHUM', 'RH'}
STAGE80 = Path('/iridisfs/scratch/ly3n24/CLM_FATES/experiments/AmeriFlux_MultiSite_10/reports/stage80_RH_lt1_final_20261024T123353Z/10_site_selected_forcing_sources.tsv')


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    obj = importlib.util.module_from_spec(spec); spec.loader.exec_module(obj); return obj


def numeric(value):
    x = float(value)
    if not math.isfinite(x) or x <= -9990: raise ValueError('Invalid source number')
    return x


def utc_index(local, shift, first, last):
    dt = datetime.strptime(local, '%Y-%m-%d %H:%M:%S')
    if dt.minute not in (0, 30) or dt.second: raise ValueError('Non half-hour timestamp')
    if dt.month == 2 and dt.day == 29: raise ValueError('No leap-day records')
    day = dt.timetuple().tm_yday - 1 - int(calendar.isleap(dt.year) and dt.month > 2)
    index = day * 48 + dt.hour * 2 + dt.minute // 30 + shift
    year = dt.year
    if index >= 17520:
        index -= 17520; year = first if year == last else year + 1
    if not first <= year <= last: raise ValueError('Timestamp outside forcing cycle')
    return year, index


def q_from_tvpd(t, vpd, pressure):
    es = 6.112 * math.exp(17.67 * t / (t + 243.5))
    e = es - vpd
    if not (0 <= vpd < es and 49000 < pressure < 111000 and 0 < e):
        raise ValueError('Invalid candidate thermodynamics')
    q = .622 * e / (pressure / 100. - .378 * e)
    if not 0 < q < .08: raise ValueError('Invalid candidate specific humidity')
    return q, 100 * e / es


def load_csv(path):
    with Path(path).open(encoding='utf-8-sig', newline='') as f: return list(csv.DictReader(f))


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--run', required=True, type=Path); ap.add_argument('--proposals', required=True, type=Path)
    ap.add_argument('--helper', required=True, type=Path); ap.add_argument('--out', required=True, type=Path)
    args = ap.parse_args(); root = args.run.resolve(strict=True); proposal_root = args.proposals.resolve(strict=True)
    out = args.out.expanduser().resolve()
    if out.exists() or out.is_symlink(): raise ValueError('Candidate output must be a new directory')
    h = module('source_context_29', args.helper)
    proposal_summary = json.loads((proposal_root / 'summary.json').read_text())
    if proposal_summary.get('errors'): raise ValueError('Proposal report has site errors')
    suspects = load_csv(proposal_root / 'suspects.csv')
    hold = Counter((r['site'], r['status']) for r in suspects if r['status'].startswith('HOLD'))
    for site in ('CA-Cbo', 'CA-Man', 'CA-TP1', 'CA-TP3', 'US-Aud', 'US-Bar'):
        print('HOLD REASONS', site, json.dumps({reason: count for (s, reason), count in hold.items() if s == site}, sort_keys=True), flush=True)
    changes = load_csv(proposal_root / 'candidate_changes_NOT_APPLIED.csv')
    if len(changes) != 3 or {r['site'] for r in changes} != {SITE} or {r['time_local'] for r in changes} != set(TIMES):
        raise ValueError('Expected exactly the reviewed US-Bar three-record candidate')
    if any(r['left_anchor'] != LEFT or r['right_anchor'] != RIGHT or r['status'] != 'CANDIDATE_NOT_APPLIED' for r in changes):
        raise ValueError('Candidate anchors or status changed')
    completion = json.loads((root / 'COMPLETE.json').read_text())
    recs = [r for r in completion['sites'] if r.get('site') == SITE]
    if len(recs) != 1: raise ValueError('No unique US-Bar Stage23 receipt')
    mpath = Path(recs[0]['manifest']).resolve(strict=True)
    if root not in mpath.parents or h.sha(mpath) != recs[0]['sha256']: raise ValueError('Stage23 receipt hash mismatch')
    m = json.loads(mpath.read_text()); first, last = m['years']; shift = int(m['UTC_shift_halfhours'])
    if m.get('site') != SITE or m.get('case_created') is not False or m.get('jobs_submitted') is not False:
        raise ValueError('Invalid Stage23 provenance')
    yearly = {int(x['year']): x for x in m['annual_files']}
    source_entry = yearly[2015]; source = Path(source_entry['path']).resolve(strict=True)
    if root not in source.parents or h.sha(source) != source_entry['sha256']: raise ValueError('Original NC checksum mismatch')
    with STAGE80.open(encoding='utf-8-sig', newline='') as f:
        selections = {x['site']: x for x in csv.DictReader(f, delimiter='\t')}
    selected = Path(selections[SITE]['selected_source'])
    if h.sha(selected) != selections[SITE]['selected_sha256']: raise ValueError('Stage80 selected forcing hash mismatch')
    entries = {r['site']: r for r in proposal_summary['results']}
    if entries[SITE]['selected_forcing_sha256'] != selections[SITE]['selected_sha256']:
        raise ValueError('Proposal and Stage80 forcing disagree')
    raw, ri = h.sources(SITE, 'FLUXMET_HH'); era, ei = h.sources(SITE, 'ERA5_HH')
    if raw is None or era is None: raise ValueError('Original FLUXMET/ERA5 source missing or ambiguous')
    wanted = set(TIMES) | {LEFT, RIGHT}
    src = h.read_subset(selected, 'time', wanted, ('TA_USE', 'VPD_USE', 'QBOT', 'PSRF'))
    tower = h.read_subset(raw, 'TIMESTAMP_START', wanted, ('TA_F', 'TA_F_QC', 'VPD_F', 'VPD_F_QC'), True)
    rean = h.read_subset(era, 'TIMESTAMP_START', wanted, ('TA_ERA', 'VPD_ERA'), True)
    if any(set(x) != wanted for x in (src, tower, rean)): raise ValueError('Required source timestamps not found uniquely')
    for time in wanted:
        a, b = src[time], tower[time]
        if numeric(b['TA_F_QC']) != 0 or numeric(b['VPD_F_QC']) != 0:
            raise ValueError('Candidate or anchor is not paired QC0: ' + time)
        if abs(numeric(a['TA_USE'])-numeric(b['TA_F'])) > .001 or abs(numeric(a['VPD_USE'])-numeric(b['VPD_F'])) > .001:
            raise ValueError('Selected forcing no longer matches QC0 source: ' + time)
    for time in (LEFT, RIGHT):
        if abs(numeric(tower[time]['TA_F']) - numeric(rean[time]['TA_ERA'])) > 5:
            raise ValueError('Anchor and ERA disagree >5 C: ' + time)
    t0, t1 = numeric(tower[LEFT]['TA_F']), numeric(tower[RIGHT]['TA_F'])
    v0, v1 = numeric(tower[LEFT]['VPD_F']), numeric(tower[RIGHT]['VPD_F'])
    if abs(t0-t1) > 8: raise ValueError('Anchor temperature disagreement')
    verified = []
    for row in sorted(changes, key=lambda x: x['time_local']):
        time = row['time_local']; frac = (datetime.fromisoformat(time) - datetime.fromisoformat(LEFT)).total_seconds() / 7200.
        t, v, p = t0+(t1-t0)*frac, v0+(v1-v0)*frac, numeric(src[time]['PSRF'])
        q, rh = q_from_tvpd(t, v, p)
        if abs(numeric(row['proposed_TA_C'])-t) > 1e-8 or abs(numeric(row['proposed_VPD_hPa'])-v) > 1e-8 or abs(numeric(row['proposed_QBOT_kgkg'])-q) > 1e-10:
            raise ValueError('Proposed values do not reproduce interpolation and humidity: ' + time)
        if abs(numeric(tower[time]['TA_F'])-t) <= 8 or abs(numeric(tower[time]['TA_F'])-numeric(rean[time]['TA_ERA'])) <= 5:
            raise ValueError('Candidate no longer satisfies diagnostic thresholds')
        year, index = utc_index(time, shift, first, last)
        if year != 2015: raise ValueError('Unexpected target UTC year')
        verified.append({'time_local': time, 'UTC_index': index, 'original_TA_C': numeric(tower[time]['TA_F']),
                         'original_VPD_hPa': numeric(tower[time]['VPD_F']), 'candidate_TA_C': t,
                         'candidate_VPD_hPa': v, 'candidate_QBOT': q, 'candidate_RH_pct': rh})
    with Dataset(str(source)) as ds:
        for x in verified:
            i = x['UTC_index']; pressure = numeric(ds.variables['PSRF'][i,0,0]); original_q = numeric(ds.variables['QBOT'][i,0,0])
            expected_q, _ = q_from_tvpd(x['original_TA_C'], x['original_VPD_hPa'], pressure)
            if abs(numeric(ds.variables['TBOT'][i,0,0]) - (x['original_TA_C'] + 273.15)) > 1e-6 or abs(original_q-expected_q) > 1e-8:
                raise ValueError('Stage23 original value does not match source timestamp')
            if abs(pressure-numeric(src[x['time_local']]['PSRF'])) > .001: raise ValueError('Pressure mismatch')
    out.mkdir(parents=True)
    dest = out / 'US-Bar_2015_UTC_sensitivity_NOT_APPLIED.nc'
    shutil.copyfile(source, dest)
    with Dataset(str(dest), 'r+') as ds:
        for x in verified:
            i = x['UTC_index']
            ds.variables['TBOT'][i,0,0] = x['candidate_TA_C'] + 273.15
            ds.variables['QBOT'][i,0,0] = x['candidate_QBOT']
            ds.variables['SHUM'][i,0,0] = x['candidate_QBOT']
            ds.variables['RH'][i,0,0] = x['candidate_RH_pct']
        ds.temperature_sensitivity = 'Three provisional QC0 interpolation candidates; not applied to any case'
    with Dataset(str(source)) as a, Dataset(str(dest)) as b:
        indices = {x['UTC_index'] for x in verified}
        for name in a.variables:
            orig, new = np.ma.asarray(a.variables[name][:]), np.ma.asarray(b.variables[name][:])
            if name not in FIELDS:
                if not np.ma.allequal(orig, new): raise ValueError('Unexpected variable change: ' + name)
            else:
                mask = np.ones(orig.shape[0], dtype=bool); mask[list(indices)] = False
                if not np.ma.allequal(orig[mask], new[mask]): raise ValueError('Unexpected time change: ' + name)
    manifest = {'site': SITE, 'status': 'DETACHED_SENSITIVITY_NOT_APPLIED', 'source_nc': str(source),
                'source_sha256': source_entry['sha256'], 'candidate_nc': str(dest), 'candidate_sha256': h.sha(dest),
                'source_manifest_sha256': recs[0]['sha256'], 'stage80_sha256': selections[SITE]['selected_sha256'],
                'source_FLUXMET': ri, 'source_ERA5_companion': ei, 'proposed_changes': verified,
                'hold_counts': {f'{s}:{reason}': count for (s, reason), count in hold.items()},
                'no_original_files_or_cases_modified': True, 'no_slurm_jobs_submitted': True}
    (out / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print('DETACHED CANDIDATE:', dest, flush=True)
    for x in verified: print('CANDIDATE SAMPLE', json.dumps(x, sort_keys=True), flush=True)
    print('MANIFEST:', out / 'manifest.json', 'NO INPUTS OR CASES MODIFIED', flush=True)


if __name__ == '__main__': main()

