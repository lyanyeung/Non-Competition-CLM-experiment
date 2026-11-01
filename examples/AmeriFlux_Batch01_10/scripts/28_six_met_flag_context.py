#!/usr/bin/env python3
"""Read-only summary of RH above 100% and largest temperature jumps.

Maps Stage23 UTC samples back to Stage80 local timestamps, reports the largest
five >8 C adjacent jumps per site and looks up their exact source observations
and source quality codes. Flags are evidence for review, not automatic errors.
"""
from __future__ import annotations
import argparse
import calendar
import csv
import heapq
import json
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
from netCDF4 import Dataset

SITES = ('CA-Cbo', 'CA-Man', 'CA-TP1', 'CA-TP3', 'US-Aud', 'US-Bar')
N = 17520
SOURCE = Path('/iridisfs/scratch/ly3n24/CLM_FATES/sites/MY_EC_SITE')
STAGE80 = Path('/iridisfs/scratch/ly3n24/CLM_FATES/experiments/AmeriFlux_MultiSite_10/reports/stage80_RH_lt1_final_20261024T123353Z/10_site_selected_forcing_sources.tsv')


def source_stamp(year, index, first, last, shift):
    if not 0 <= index < N or not 0 < shift < N: raise ValueError('Invalid sample or UTC shift')
    source_year = (last if year == first else year - 1) if index < shift else year
    index = N - shift + index if index < shift else index - shift
    days, halfhour = divmod(index, 48)
    # The input timeline has no February 29 even in Gregorian leap years.
    if calendar.isleap(source_year) and days >= 59: days += 1
    return (datetime(source_year, 1, 1) + timedelta(days=days, minutes=30 * halfhour)).strftime('%Y-%m-%d %H:%M:%S')


def add_event(heap, site, first, last, shift, left_y, left_i, left_t, right_y, right_i, right_t):
    delta = float(right_t - left_t)
    if abs(delta) <= 8: return
    event = {'left_local': source_stamp(left_y, left_i, first, last, shift),
             'right_local': source_stamp(right_y, right_i, first, last, shift),
             'left_final_C': float(left_t - 273.15), 'right_final_C': float(right_t - 273.15),
             'difference_C': delta, 'utc_output_year': right_y, 'utc_halfhour_index': right_i}
    item = (abs(delta), right_y, right_i, event)
    if len(heap) < 5: heapq.heappush(heap, item)
    elif item[:3] > heap[0][:3]: heapq.heapreplace(heap, item)


def find_raw(site):
    return sorted((SOURCE / site / 'forcing/raw').glob('AMF_' + site + '_FLUXNET_*/*FLUXMET_HH*.csv'))


def lookup(path, time_key, wanted, cols, compact):
    found = {}
    if not path or not path.is_file(): return found
    compact_keys = {s.replace('-', '').replace(':', '').replace(' ', '')[:12]: s for s in wanted} if compact else {}
    with path.open(encoding='latin-1', newline='') as f:
        reader = csv.DictReader(f)
        if time_key not in (reader.fieldnames or []): return found
        for row in reader:
            key = (row.get(time_key) or '').strip()
            if compact:
                if key.endswith('.0'): key = key[:-2]
                key = compact_keys.get(key, '')
            if key in wanted:
                found[key] = {k: row.get(k, '') for k in cols}
                if len(found) == len(wanted): break
    return found


def audit(root):
    root = root.resolve(strict=True)
    completion = json.loads((root / 'COMPLETE.json').read_text())
    rows = completion['sites']
    if len(rows) != 6 or {r['site'] for r in rows} != set(SITES): raise ValueError('Not a six-site receipt')
    if STAGE80.is_file():
        with STAGE80.open(encoding='utf-8-sig', newline='') as f:
            selections = {r['site']: r for r in csv.DictReader(f, delimiter='\t')}
    else: selections = {}
    for row in rows:
        site = row['site']; manifest = Path(row['manifest']).resolve()
        if root not in manifest.parents: raise ValueError('Manifest outside candidate root')
        obj = json.loads(manifest.read_text()); first, last = obj['years']; shift = obj['UTC_shift_halfhours']
        heap = []; counts = {'rh_gt100': 0, 'rh_gt100_01': 0, 'rh_gt100_1': 0, 'rh_gt100_25': 0}
        rh_max = None; previous = None
        for item in obj['annual_files']:
            year = item['year']; path = Path(item['path']).resolve()
            if root not in path.parents: raise ValueError('Met file outside candidate root')
            with Dataset(str(path)) as ds:
                t = np.asarray(ds.variables['TBOT'][:, 0, 0], dtype=float)
                rh = np.asarray(ds.variables['RH'][:, 0, 0], dtype=float)
            if len(t) != N or len(rh) != N or not np.isfinite(t).all() or not np.isfinite(rh).all():
                raise ValueError(site + ': invalid Met arrays')
            for key, threshold in [('rh_gt100', 100), ('rh_gt100_01', 100.01), ('rh_gt100_1', 100.1), ('rh_gt100_25', 100.25)]:
                counts[key] += int(np.count_nonzero(rh > threshold))
            rh_max = max(float(rh.max()), rh_max if rh_max is not None else -float('inf'))
            if previous is not None:
                py, pt = previous
                add_event(heap, site, first, last, shift, py, N - 1, pt, year, 0, t[0])
            diffs = np.abs(np.diff(t)); indices = np.where(diffs > 8)[0]
            leap_edge = 59 * 48 + shift - 1 if calendar.isleap(year) else -1
            for i in indices:
                if i != leap_edge: add_event(heap, site, first, last, shift, year, int(i), t[i], year, int(i + 1), t[i + 1])
            previous = (year, float(t[-1]))
        events = [v[3] for v in sorted(heap, key=lambda x: x[:3], reverse=True)]
        wanted = {event[k] for event in events for k in ('left_local', 'right_local')}
        selection = selections.get(site, {})
        selected_path = Path(selection['selected_source']) if selection.get('selected_source') else None
        selected = lookup(selected_path, 'time', wanted, ('TA_USE', 'VPD_USE', 'TBOT', 'QBOT', 'PSRF'), False)
        raw = find_raw(site)
        tower = lookup(raw[0] if len(raw) == 1 else None, 'TIMESTAMP_START', wanted,
                       ('TA_F', 'TA_F_QC', 'VPD_F', 'VPD_F_QC'), True)
        for e in events:
            e['left_selected'] = selected.get(e['left_local'], {})
            e['right_selected'] = selected.get(e['right_local'], {})
            e['left_tower'] = tower.get(e['left_local'], {})
            e['right_tower'] = tower.get(e['right_local'], {})
        print('MET CONTEXT', json.dumps({'site': site, **counts, 'max_rh_pct': rh_max,
              'selected_forcing_found': bool(selected_path and selected_path.is_file()),
              'raw_fluxmet_candidates': len(raw), 'largest_jumps': events}, sort_keys=True), flush=True)
    print('All timestamps above are source LOCAL interval-start labels; QA flags do not prove source error.')


def main():
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('--run', required=True, type=Path)
    audit(p.parse_args().run)


if __name__ == '__main__': main()

