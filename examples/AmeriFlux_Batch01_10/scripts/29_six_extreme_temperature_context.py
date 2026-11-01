#!/usr/bin/env python3
"""Trace largest six-site temperature jumps into original and ERA5 companion data.

Reads prior MET CONTEXT output and Stage80's selected source, preserving all
inputs. Reports source local times and raw QC codes; no repair is performed.
ERA5_HH is a companion product and is not claimed independent of FLUXNET fill.
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
from datetime import datetime, timedelta
from pathlib import Path

SITES = ('CA-Cbo', 'CA-Man', 'CA-TP1', 'CA-TP3', 'US-Aud', 'US-Bar')
RAW = Path('/iridisfs/scratch/ly3n24/CLM_FATES/sites/MY_EC_SITE')
STAGE80 = Path('/iridisfs/scratch/ly3n24/CLM_FATES/experiments/AmeriFlux_MultiSite_10/reports/stage80_RH_lt1_final_20261024T123353Z/10_site_selected_forcing_sources.tsv')


def sha(p):
    h = hashlib.sha256()
    with Path(p).open('rb') as f:
        for chunk in iter(lambda: f.read(1048576), b''): h.update(chunk)
    return h.hexdigest()


def read_events(path):
    result = {}
    for line in Path(path).read_text(encoding='utf-8').splitlines():
        if line.startswith('MET CONTEXT '):
            obj = json.loads(line[len('MET CONTEXT '):]); result[obj['site']] = obj
    if set(result) != set(SITES): raise ValueError('Met context log must contain all six sites')
    return result


def distinct_events(events):
    selected = []
    for e in events:
        left = datetime.strptime(e['left_local'], '%Y-%m-%d %H:%M:%S')
        right = datetime.strptime(e['right_local'], '%Y-%m-%d %H:%M:%S')
        if right - left != timedelta(minutes=30): continue  # forcing-cycle wrap
        if any(abs((right - prior[0]).total_seconds()) < 7200 for prior in selected): continue
        selected.append((right, e))
        if len(selected) == 3: break
    return selected


def read_subset(path, stamp_col, wanted, cols, compact=False):
    wanted_key = {s.replace('-', '').replace(':', '').replace(' ', '')[:12]: s for s in wanted} if compact else {}
    result = {}
    with Path(path).open(encoding='latin-1', newline='') as f:
        rows = csv.DictReader(f)
        if stamp_col not in (rows.fieldnames or []): raise ValueError('Missing timestamp column in ' + str(path))
        for row in rows:
            key = (row.get(stamp_col) or '').strip()
            if compact:
                if key.endswith('.0'): key = key[:-2]
                key = wanted_key.get(key, '')
            if key in wanted:
                if key in result: raise ValueError('Duplicate timestamp in ' + str(path))
                result[key] = {col: row.get(col, '') for col in cols}
    return result


def one_raw(site, kind):
    matches = sorted((RAW / site / 'forcing/raw').glob('AMF_' + site + '_FLUXNET_*/*' + kind + '*.csv'))
    if len(matches) != 1: raise ValueError(f'{site}: expected one {kind} CSV, found {len(matches)}')
    return matches[0]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--met-log', required=True, type=Path)
    args = p.parse_args()
    events = read_events(args.met_log)
    with STAGE80.open(encoding='utf-8-sig', newline='') as f:
        selections = {r['site']: r for r in csv.DictReader(f, delimiter='\t')}
    for site in SITES:
        chosen = distinct_events(events[site]['largest_jumps'])
        wanted = set()
        for stamp, _ in chosen:
            for minutes in range(-90, 91, 30):
                wanted.add((stamp + timedelta(minutes=minutes)).strftime('%Y-%m-%d %H:%M:%S'))
        row = selections[site]; selected = Path(row['selected_source'])
        if sha(selected) != row['selected_sha256']: raise ValueError(site + ': selected forcing checksum mismatch')
        fluxmet, era = one_raw(site, 'FLUXMET_HH'), one_raw(site, 'ERA5_HH')
        chosen_data = read_subset(selected, 'time', wanted, ('TA_USE', 'VPD_USE', 'TBOT', 'QBOT', 'PSRF'))
        tower_data = read_subset(fluxmet, 'TIMESTAMP_START', wanted,
            ('TA_F', 'TA_F_QC', 'VPD_F', 'VPD_F_QC', 'SW_IN_F', 'SW_IN_F_QC'), compact=True)
        era_data = read_subset(era, 'TIMESTAMP_START', wanted, ('TA_ERA', 'VPD_ERA', 'SW_IN_ERA'), compact=True)
        out = []
        for stamp, event in chosen:
            frames = []
            for minutes in range(-90, 91, 30):
                key = (stamp + timedelta(minutes=minutes)).strftime('%Y-%m-%d %H:%M:%S')
                frames.append({'local_time': key, 'selected': chosen_data.get(key, {}),
                               'tower': tower_data.get(key, {}), 'era_companion': era_data.get(key, {})})
            out.append({'event': {k: event[k] for k in ('left_local', 'right_local', 'left_final_C', 'right_final_C', 'difference_C')},
                        'context': frames})
        print('TEMPERATURE CONTEXT', json.dumps({'site': site, 'max_rh_pct': events[site]['max_rh_pct'],
            'stage80_selected_sha256': row['selected_sha256'], 'fluxmet_file': fluxmet.name,
            'era_companion_file': era.name, 'events': out}, sort_keys=True), flush=True)
    print('DONE: all timestamps are source local labels; no modifications, model runs or Slurm jobs.')


if __name__ == '__main__': main()

