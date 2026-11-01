#!/usr/bin/env python3
"""Read-only classification of all Stage80 adjacent >8 C temperature changes.

For each site, align the selected forcing, FLUXMET and companion ERA5 records
on source-local half-hour timestamps. Write a new review CSV and per-site
summary. Does not alter any forcing, observed data, cases or jobs. ERA5_HH can
be the source of FLUXMET QC2 values and is not independent in those records.
"""
from __future__ import annotations
import argparse
from collections import Counter
from contextlib import ExitStack
import csv
from datetime import datetime, timedelta
import heapq
import importlib.util
import io
import json
import math
from pathlib import Path
from zipfile import ZipFile

SITES = ('CA-Cbo', 'CA-Man', 'CA-TP1', 'CA-TP3', 'US-Aud', 'US-Bar')
N = 17520
STAGE80 = Path('/iridisfs/scratch/ly3n24/CLM_FATES/experiments/AmeriFlux_MultiSite_10/reports/stage80_RH_lt1_final_20261024T123353Z/10_site_selected_forcing_sources.tsv')
COLS = ('site', 'left_time_local', 'right_time_local', 'selected_left_C', 'selected_right_C', 'selected_step_C',
        'tower_left_C', 'tower_right_C', 'tower_left_TA_QC', 'tower_right_TA_QC',
        'tower_left_VPD', 'tower_right_VPD', 'tower_left_VPD_QC', 'tower_right_VPD_QC',
        'era_left_C', 'era_right_C', 'era_step_C', 'era_left_VPD', 'era_right_VPD',
        'selected_left_VPD', 'selected_right_VPD', 'qc_pair', 'source_switch',
        'left_selected_differs_tower', 'right_selected_differs_tower')


def load_helper(path):
    spec = importlib.util.spec_from_file_location('six_event_context', path)
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    return mod


def num(value):
    try:
        x = float(value)
        return x if math.isfinite(x) and x > -9990 else None
    except (ValueError, TypeError): return None


def norm_qc(value):
    x = num(value)
    if x is not None and x in (0, 1, 2): return str(int(x))
    return '?'


def compact(value):
    return ''.join(ch for ch in value if ch.isdigit())[:12]


def read_rows(source, stamp_key, first, last, stack):
    if isinstance(source, tuple):
        z = stack.enter_context(ZipFile(source[0]))
        f = stack.enter_context(io.TextIOWrapper(z.open(source[1]), encoding='latin-1', newline=''))
    else:
        f = stack.enter_context(Path(source).open(encoding='latin-1', newline=''))
    reader = csv.DictReader(f)
    if stamp_key not in (reader.fieldnames or []): raise ValueError('Missing timestamp column: ' + str(source))
    last_key = ''
    for row in reader:
        key = compact((row.get(stamp_key) or '').strip())
        if len(key) != 12: raise ValueError('Invalid timestamp in ' + str(source))
        year = int(key[:4])
        if year < first or year > last or key[4:8] == '0229': continue
        if key <= last_key: raise ValueError('Duplicate or unordered timestamps in ' + str(source))
        last_key = key
        yield key, row


def observe(selected, raw, era, first, last):
    """Yield aligned rows, verifying exact chronological source timestamps."""
    with ExitStack() as stack:
        streams = [iter(read_rows(selected, 'time', first, last, stack)),
                   iter(read_rows(raw, 'TIMESTAMP_START', first, last, stack)),
                   iter(read_rows(era, 'TIMESTAMP_START', first, last, stack))]
        for step in range((last - first + 1) * N):
            current = [next(stream, None) for stream in streams]
            if any(x is None for x in current): raise ValueError('A source stream is truncated at row ' + str(step))
            if len({x[0] for x in current}) != 1: raise ValueError('Source timestamps differ: ' + str([x[0] for x in current]))
            yield current[0][0], current[0][1], current[1][1], current[2][1]
        if any(next(stream, None) is not None for stream in streams): raise ValueError('Source has unexpected extra rows')


def describe(site, left, right):
    _, a, at, ae = left; _, b, bt, be = right
    t1, t2 = num(a.get('TA_USE')), num(b.get('TA_USE'))
    if t1 is None or t2 is None: raise ValueError(site + ': selected temperature missing')
    x1, x2 = num(at.get('TA_F')), num(bt.get('TA_F'))
    e1, e2 = num(ae.get('TA_ERA')), num(be.get('TA_ERA'))
    q1, q2 = norm_qc(at.get('TA_F_QC')), norm_qc(bt.get('TA_F_QC'))
    return {'site': site, 'left_time_local': a['time'], 'right_time_local': b['time'],
        'selected_left_C': t1, 'selected_right_C': t2, 'selected_step_C': t2 - t1,
        'tower_left_C': x1, 'tower_right_C': x2, 'tower_left_TA_QC': q1, 'tower_right_TA_QC': q2,
        'tower_left_VPD': num(at.get('VPD_F')), 'tower_right_VPD': num(bt.get('VPD_F')),
        'tower_left_VPD_QC': norm_qc(at.get('VPD_F_QC')), 'tower_right_VPD_QC': norm_qc(bt.get('VPD_F_QC')),
        'era_left_C': e1, 'era_right_C': e2, 'era_step_C': e2 - e1 if e1 is not None and e2 is not None else None,
        'era_left_VPD': num(ae.get('VPD_ERA')), 'era_right_VPD': num(be.get('VPD_ERA')),
        'selected_left_VPD': num(a.get('VPD_USE')), 'selected_right_VPD': num(b.get('VPD_USE')),
        'qc_pair': q1 + '-' + q2, 'source_switch': q1 != '?' and q2 != '?' and q1 != q2,
        'left_selected_differs_tower': abs(t1-x1) > .001 if x1 is not None else None,
        'right_selected_differs_tower': abs(t2-x2) > .001 if x2 is not None else None}


def run_site(site, years, sources, writer):
    prev = None; total = 0; flags = Counter(); evidence = Counter(); top_qc0 = []; max_step = 0.; skipped_noleap = 0
    for key, chosen, raw, era in observe(*sources, *years):
        row = (key, chosen, raw, era)
        if prev is not None:
            dt = datetime.strptime(key, '%Y%m%d%H%M') - datetime.strptime(prev[0], '%Y%m%d%H%M')
            if dt == timedelta(minutes=30):
                t0, t1 = num(prev[1].get('TA_USE')), num(chosen.get('TA_USE'))
                if t0 is None or t1 is None: raise ValueError(site + ': nonnumeric selected TA_USE')
                if abs(t1-t0) > 8:
                    event = describe(site, prev, row); writer.writerow(event); total += 1
                    flags[event['qc_pair']] += 1; max_step = max(max_step, abs(event['selected_step_C']))
                    if event['source_switch']: evidence['qc_source_switch'] += 1
                    if any(event[f'tower_{side}_TA_QC'] == '0' and event[f'era_{side}_C'] is not None and
                           event[f'tower_{side}_C'] is not None and
                           abs(event[f'tower_{side}_C'] - event[f'era_{side}_C']) > 10
                           for side in ('left', 'right')):
                        evidence['qc0_endpoint_vs_era_gt10_C'] += 1
                        item = (abs(event['selected_step_C']), event['left_time_local'], event)
                        if len(top_qc0) < 3: heapq.heappush(top_qc0, item)
                        elif item[:2] > top_qc0[0][:2]: heapq.heapreplace(top_qc0, item)
            else: skipped_noleap += 1
        prev = row
    return {'site': site, 'local_jumps_gt8_C': total, 'qc_pairs': dict(flags),
            'review_counts': dict(evidence),
            'largest_qc0_era_review_examples': [x[2] for x in sorted(top_qc0, key=lambda x: x[:2], reverse=True)],
            'largest_jump_C': round(max_step, 4), 'non_30min_edges_excluded': skipped_noleap,
            'scope': 'chronological source; forcing-cycle wrap excluded'}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--run', required=True, type=Path)
    p.add_argument('--helper', required=True, type=Path)
    p.add_argument('--out', required=True, type=Path)
    args = p.parse_args(); root = args.run.resolve(strict=True); out = args.out.expanduser().resolve()
    if out.exists() or out.is_symlink(): raise ValueError('Output directory must not already exist')
    helper = load_helper(args.helper)
    completion = json.loads((root / 'COMPLETE.json').read_text())
    if len(completion.get('sites', [])) != 6 or {r.get('site') for r in completion['sites']} != set(SITES):
        raise ValueError('Invalid six-site Stage23 receipt')
    with STAGE80.open(encoding='utf-8-sig', newline='') as f:
        selected = {r['site']: r for r in csv.DictReader(f, delimiter='\t')}
    manifests = {r['site']: r for r in completion['sites']}
    out.mkdir(parents=True); summary = []; errors = []
    for site in SITES:
        try:
            rec = manifests[site]; manifest = Path(rec['manifest']).resolve(strict=True)
            if root not in manifest.parents or helper.sha(manifest) != rec['sha256']:
                raise ValueError('Invalid input manifest or checksum')
            meta = json.loads(manifest.read_text()); years = meta['years']
            sel = selected[site]; source = Path(sel['selected_source'])
            if helper.sha(source) != sel['selected_sha256']: raise ValueError('Selected forcing checksum mismatch')
            flux, flux_info = helper.sources(site, 'FLUXMET_HH')
            era, era_info = helper.sources(site, 'ERA5_HH')
            if not flux or not era: raise ValueError('FLUXMET/ERA source missing or ambiguous: ' + json.dumps([flux_info, era_info]))
            path = out / (site + '_temperature_jumps.csv')
            with path.open('w', encoding='utf-8', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=COLS); writer.writeheader()
                result = run_site(site, years, (source, flux, era), writer)
            result.update(status='COMPLETE', selected_sha256=sel['selected_sha256'], output=str(path),
                          FLUXMET_source=flux_info, ERA5_source=era_info)
            summary.append(result); print('SITE CLASSIFICATION', json.dumps(result, sort_keys=True), flush=True)
        except Exception as e:
            errors.append(site); summary.append({'site': site, 'status': 'ERROR', 'error': str(e)})
            print('SITE ERROR', site, type(e).__name__ + ':', str(e), flush=True)
    (out / 'summary.json').write_text(json.dumps({'sites': summary, 'errors': errors,
        'notes': ['No input modified', 'QC and ERA differences are review evidence, not automated truth',
                  'ERA5_HH may be the source of FLUXNET QC2', 'Noleap gaps and forcing-cycle wrap excluded']}, indent=2) + '\n')
    print('REPORT:', out, 'SITE_ERRORS:', errors, flush=True)
    return int(bool(errors))


if __name__ == '__main__': raise SystemExit(main())

