#!/usr/bin/env python3
"""Prepare, but never apply, conservative candidate TA/VPD/QBOT repairs.

Find unique QC0 observations >10 C from FLUXNET ERA5 at a >8 C source jump.
Only propose short bracketed blocks if both observed TA/VPD anchors agree
with ERA within 5 C, every intervening TA/VPD point is QC0, differs from the
linear candidate by >8 C and differs from ERA by >5 C. All other points HOLD.
The candidate is a sensitivity hypothesis, not proof of invalid observations;
no forcing, case, source or Slurm file is changed.
"""
from __future__ import annotations
import argparse
import csv
from datetime import datetime, timedelta
import importlib.util
import json
import math
from pathlib import Path

SITES = ('CA-Cbo', 'CA-Man', 'CA-TP1', 'CA-TP3', 'US-Aud', 'US-Bar')
STAGE80 = Path('/iridisfs/scratch/ly3n24/CLM_FATES/experiments/AmeriFlux_MultiSite_10/reports/stage80_RH_lt1_final_20261024T123353Z/10_site_selected_forcing_sources.tsv')


def helper(path):
    spec = importlib.util.spec_from_file_location('six_context', path)
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); return mod


def num(v):
    try:
        n = float(v)
        return n if math.isfinite(n) and n > -9990 else None
    except (ValueError, TypeError): return None


def qc0(value):
    return num(value) == 0


def fmt(dt): return dt.strftime('%Y-%m-%d %H:%M:%S')


def read_candidates(path):
    chosen = {}
    with Path(path).open(encoding='utf-8-sig', newline='') as f:
        for event in csv.DictReader(f):
            for side in ('left', 'right'):
                if not qc0(event.get('tower_' + side + '_TA_QC')): continue
                tower, era = num(event.get('tower_' + side + '_C')), num(event.get('era_' + side + '_C'))
                if tower is None or era is None or abs(tower - era) <= 10: continue
                if event.get(side + '_selected_differs_tower', '').lower() != 'false': continue
                stamp = event[side + '_time_local']
                chosen.setdefault(stamp, {'time_local': stamp, 'tower_ta_C': tower,
                                          'era_ta_C': era, 'jump_count': 0})['jump_count'] += 1
    return chosen


def records_for_times(site, wanted, chosen, selection, h):
    selected = Path(selection['selected_source'])
    if h.sha(selected) != selection['selected_sha256']: raise ValueError(site + ': selected forcing SHA mismatch')
    raw, raw_info = h.sources(site, 'FLUXMET_HH'); era, era_info = h.sources(site, 'ERA5_HH')
    if raw is None or era is None: raise ValueError(site + ': missing/ambiguous source: ' + json.dumps([raw_info, era_info]))
    sel = h.read_subset(selected, 'time', wanted, ('TA_USE', 'VPD_USE', 'TBOT', 'QBOT', 'PSRF'))
    tower = h.read_subset(raw, 'TIMESTAMP_START', wanted, ('TA_F', 'TA_F_QC', 'VPD_F', 'VPD_F_QC'), True)
    rean = h.read_subset(era, 'TIMESTAMP_START', wanted, ('TA_ERA', 'VPD_ERA'), True)
    return {time: {'selected': sel.get(time, {}), 'tower': tower.get(time, {}), 'era': rean.get(time, {})}
            for time in wanted}, raw_info, era_info


def good_observed(record):
    tower, selected, era = record['tower'], record['selected'], record['era']
    ta, vpd, st, sv, e = (num(tower.get('TA_F')), num(tower.get('VPD_F')),
                          num(selected.get('TA_USE')), num(selected.get('VPD_USE')), num(era.get('TA_ERA')))
    return (qc0(tower.get('TA_F_QC')) and qc0(tower.get('VPD_F_QC')) and
            all(x is not None for x in (ta, vpd, st, sv, e)) and
            abs(ta - st) <= .001 and abs(vpd - sv) <= .001)


def anchor_ok(record):
    return (good_observed(record) and
            abs(num(record['tower']['TA_F']) - num(record['era']['TA_ERA'])) <= 5.)


def humidity(temp_c, vpd_hpa, pressure_pa):
    if not all(math.isfinite(x) for x in (temp_c, vpd_hpa, pressure_pa)) or not 49000 < pressure_pa < 111000:
        raise ValueError('Invalid coupled candidate input')
    es = 6.112 * math.exp(17.67 * temp_c / (temp_c + 243.5))
    vapour = es - vpd_hpa
    if vpd_hpa < 0 or vapour <= 0 or vapour > es or pressure_pa/100 <= .378 * vapour:
        raise ValueError('Interpolated TA/VPD/pressure is physically invalid')
    q = .622 * vapour / (pressure_pa/100. - .378 * vapour)
    if not 0 < q < .08: raise ValueError('Interpolated specific humidity out of bounds')
    return q


def propose(time, frames):
    """One timestamp -> proposed full short block or HOLD, never change input."""
    center = datetime.strptime(time, '%Y-%m-%d %H:%M:%S')
    anchors = []
    for sign in (-1, 1):
        nearest = next((center + timedelta(minutes=sign * 30 * k) for k in range(1, 5)
                        if anchor_ok(frames.get(fmt(center + timedelta(minutes=sign * 30 * k)),
                                                {'tower': {}, 'selected': {}, 'era': {}}))), None)
        if nearest is None: return None, 'HOLD_NO_TWO_CORROBORATED_QC0_ANCHORS'
        anchors.append(nearest)
    left, right = anchors
    l, r = frames[fmt(left)], frames[fmt(right)]
    t0, t1 = num(l['tower']['TA_F']), num(r['tower']['TA_F'])
    v0, v1 = num(l['tower']['VPD_F']), num(r['tower']['VPD_F'])
    if abs(t1 - t0) > 8: return None, 'HOLD_ANCHORS_DIFFER_GT8C'
    block = []; n = int((right-left).total_seconds() / 1800)
    for k in range(1, n):
        when = left + timedelta(minutes=30*k); record = frames.get(fmt(when), {'tower': {}, 'selected': {}, 'era': {}})
        if not good_observed(record): return None, 'HOLD_INTERIOR_NOT_OBSERVED_QC0_OR_ALREADY_CHANGED'
        original = num(record['tower']['TA_F']); era = num(record['era']['TA_ERA'])
        proposed_t = t0 + (t1-t0) * k / n; proposed_v = v0 + (v1-v0) * k / n
        if abs(original-proposed_t) <= 8 or abs(original-era) <= 5:
            return None, 'HOLD_INTERIOR_NOT_UNIFORMLY_SUPPORTED'
        pressure = num(record['selected'].get('PSRF'))
        if pressure is None: return None, 'HOLD_MISSING_PRESSURE'
        try: q = humidity(proposed_t, proposed_v, pressure)
        except ValueError: return None, 'HOLD_COUPLED_MET_PHYSICS'
        block.append({'time_local': fmt(when), 'original_TA_C': original,
                      'original_VPD_hPa': num(record['tower']['VPD_F']), 'ERA_TA_C': era,
                      'proposed_TA_C': proposed_t, 'proposed_VPD_hPa': proposed_v,
                      'proposed_QBOT_kgkg': q, 'pressure_Pa_unchanged': pressure,
                      'left_anchor': fmt(left), 'right_anchor': fmt(right)})
    if not block: return None, 'HOLD_EMPTY_BLOCK'
    return block, 'PROVISIONAL_SHORT_BLOCK_CANDIDATE_NOT_APPLIED'


def write_csv(path, rows, fields):
    with path.open('w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction='ignore'); w.writeheader(); w.writerows(rows)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--report', required=True, type=Path); ap.add_argument('--helper', required=True, type=Path)
    ap.add_argument('--out', required=True, type=Path); args = ap.parse_args()
    report = args.report.resolve(strict=True); out = args.out.expanduser().resolve()
    if out.exists() or out.is_symlink(): raise ValueError('Output directory must be new')
    h = helper(args.helper)
    with STAGE80.open(encoding='utf-8-sig', newline='') as f:
        selections = {r['site']: r for r in csv.DictReader(f, delimiter='\t')}
    summary_in = json.loads((report / 'summary.json').read_text())
    if summary_in.get('errors') or {x.get('site') for x in summary_in.get('sites', [])} != set(SITES):
        raise ValueError('Previous six-site classification is incomplete')
    out.mkdir(parents=True); all_suspects, all_proposals, all_context, results = [], [], [], []
    for site in SITES:
        try:
            src = report / (site + '_temperature_jumps.csv')
            suspects = read_candidates(src); wanted = set()
            for time in suspects:
                center = datetime.strptime(time, '%Y-%m-%d %H:%M:%S')
                for k in range(-4, 5): wanted.add(fmt(center + timedelta(minutes=30*k)))
            if not suspects:
                result = {'site': site, 'qc0_suspect_observations': 0, 'proposed_blocks': 0, 'proposed_records': 0, 'status': 'COMPLETE'}
                results.append(result); print('PROPOSAL SUMMARY', json.dumps(result, sort_keys=True), flush=True); continue
            frames, raw_info, era_info = records_for_times(site, wanted, suspects, selections[site], h)
            proposals = {}; reasons = {}; candidate_block = {}
            for time in sorted(suspects):
                block, why = propose(time, frames); reasons[time] = why
                if block:
                    key = (block[0]['left_anchor'], block[0]['right_anchor'])
                    proposals[key] = block
                    candidate_block[time] = key
            owners = {}
            for key, block in proposals.items():
                for row in block: owners.setdefault(row['time_local'], set()).add(key)
            conflicts = {key for keys in owners.values() if len(keys) > 1 for key in keys}
            held = {time for time, reason in reasons.items() if reason.startswith('HOLD')}
            conflicts |= {key for key, block in proposals.items()
                          if any(row['time_local'] in held for row in block)}
            for key in conflicts: proposals.pop(key)
            for time, key in candidate_block.items():
                if key in conflicts: reasons[time] = 'HOLD_OVERLAPPING_CANDIDATE_BLOCKS'
            for time, info in sorted(suspects.items()):
                all_suspects.append({'site': site, **info, 'status': reasons[time]})
            for key, block in sorted(proposals.items()):
                for row in block: all_proposals.append({'site': site, **row, 'status': 'CANDIDATE_NOT_APPLIED'})
            for time in sorted(wanted):
                d = frames[time]; all_context.append({'site': site, 'time_local': time,
                    'selected_json': json.dumps(d['selected'], sort_keys=True), 'tower_json': json.dumps(d['tower'], sort_keys=True),
                    'era_json': json.dumps(d['era'], sort_keys=True)})
            result = {'site': site, 'qc0_suspect_observations': len(suspects), 'proposed_blocks': len(proposals),
                      'proposed_records': sum(len(x) for x in proposals.values()), 'held_suspects': sum(reasons[x].startswith('HOLD') for x in suspects),
                      'source_events_sha256': h.sha(src), 'selected_forcing_sha256': selections[site]['selected_sha256'],
                      'FLUXMET_source': raw_info, 'ERA5_source': era_info, 'status': 'COMPLETE'}
            results.append(result); print('PROPOSAL SUMMARY', json.dumps(result, sort_keys=True), flush=True)
        except Exception as e:
            results.append({'site': site, 'status': 'ERROR', 'error': str(e)})
            print('PROPOSAL ERROR', site, type(e).__name__ + ':', str(e), flush=True)
    suspects_fields = ('site','time_local','tower_ta_C','era_ta_C','jump_count','status')
    proposal_fields = ('site','time_local','original_TA_C','original_VPD_hPa','ERA_TA_C','proposed_TA_C',
                       'proposed_VPD_hPa','proposed_QBOT_kgkg','pressure_Pa_unchanged','left_anchor','right_anchor','status')
    write_csv(out / 'suspects.csv', all_suspects, suspects_fields)
    write_csv(out / 'candidate_changes_NOT_APPLIED.csv', all_proposals, proposal_fields)
    write_csv(out / 'source_context.csv', all_context, ('site','time_local','selected_json','tower_json','era_json'))
    errors = [r['site'] for r in results if r['status'] != 'COMPLETE']
    (out / 'summary.json').write_text(json.dumps({'results': results, 'errors': errors,
        'note': 'Candidates are local sensitivity hypotheses and have NOT been applied; ERA5 companion is not always independent.'}, indent=2) + '\n')
    print('CANDIDATE REPORT:', out, 'SITE_ERRORS:', errors, flush=True)
    for row in all_proposals: print('CANDIDATE NOT APPLIED', json.dumps(row, sort_keys=True), flush=True)
    return int(bool(errors))


if __name__ == '__main__': raise SystemExit(main())

