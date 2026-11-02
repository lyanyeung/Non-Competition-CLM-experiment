#!/usr/bin/env python3
"""Combine explicitly approved DE-Gri 2011 and 2024 CSV sensitivity edits.

Writes a new private candidate, preserving source, base CSV, cases and NetCDF.
The result is a sensitivity CSV, not a scientifically verified DATM release.
"""
import argparse
import csv
import hashlib
import json
import math
import os
from datetime import datetime, timedelta
from itertools import zip_longest
from pathlib import Path

START = datetime(2024, 7, 4, 5)
END = datetime(2024, 7, 4, 16)
LEFT = START - timedelta(minutes=30)
RIGHT = END + timedelta(minutes=30)
CHANGED = {'VPD_USE', 'QBOT'}


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1024*1024), b''):
            h.update(block)
    return h.hexdigest()


def parse(s, source=False):
    s = str(s).strip().strip("'\"")
    if source and s.endswith('.0') and s[:-2].isdigit():
        s = s[:-2]
    d = datetime.strptime(s, '%Y%m%d%H%M') if source else datetime.fromisoformat(s)
    if d.tzinfo is not None:
        raise ValueError('Timezone-aware timestamp unsupported')
    return d


def value(s):
    n = float(s)
    if not math.isfinite(n) or n == -9999:
        raise ValueError('Invalid value')
    return n


def humidity(temp, vpd, pressure):
    sat = 6.112 * math.exp(17.67 * temp / (temp + 243.5))
    e = (sat - vpd) * 100
    if not 0 <= vpd <= sat or not 50000 <= pressure <= 115000 or not 0 <= e < pressure:
        raise ValueError('Nonphysical candidate')
    return 0.622 * e / (pressure - 0.378 * e), 100 * (sat - vpd) / sat


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--stage03d', type=Path, required=True)
    p.add_argument('--context', type=Path, required=True)
    p.add_argument('--prior-dir', type=Path, required=True)
    p.add_argument('--out-dir', type=Path, required=True)
    p.add_argument('--confirm-approved-2024', action='store_true')
    a = p.parse_args()
    if not a.confirm_approved_2024:
        p.error('Explicit approval is required for 23 VPD sensitivity values')
    if not a.out_dir.is_dir() or a.out_dir.is_symlink() or any(a.out_dir.iterdir()):
        raise ValueError('Output must be an existing empty private directory')
    d = json.loads(a.stage03d.read_text(encoding='utf-8'))
    c = json.loads(a.context.read_text(encoding='utf-8'))
    m = json.loads((a.prior_dir / 'manifest_PRIVATE.json').read_text(encoding='utf-8'))
    if d.get('stage') != 'STAGE03D_BATCH04_RECOVER_OLD_RAIN_AND_TARGETED_ORIGINAL_SOURCE_CONTEXT' or d.get('read_only') is not True or c.get('read_only') is not True or m.get('candidate_kind') != '2011_DETACHED_CSV_ONLY_NOT_DATM' or len(m.get('edits', [])) != 11:
        raise ValueError('Expected original stage reports and 11-edit candidate manifest')
    sites = [x for x in d['sites'] if x.get('site') == 'DE-Gri']
    if len(sites) != 1:
        raise ValueError('DE-Gri site missing or ambiguous')
    src = Path(sites[0]['source_manifest_primary_file'])
    baseline = Path(sites[0]['Stage28_selected_forcing_path'])
    prior = a.prior_dir / 'DE-Gri_2011_approved_sensitivity.csv'
    input_hashes = [sha(src), sha(baseline), sha(prior)]
    if input_hashes != [c.get('source_sha256'), c.get('selected_sha256'), m.get('candidate_sha256')] or m.get('baseline_sha256') != input_hashes[1]:
        raise ValueError('Source, baseline or 2011 candidate hash mismatch')
    needed = {START + timedelta(minutes=30*i) for i in range(23)}
    source = {}
    with src.open(encoding='utf-8-sig', newline='') as f:
        reader = csv.DictReader(f)
        fields = ('TA_F', 'TA_F_QC', 'VPD_F', 'VPD_F_QC', 'VPD_ERA', 'PA_F')
        if not set(fields + ('TIMESTAMP_START',)).issubset(reader.fieldnames or []):
            raise ValueError('Required source fields missing')
        for row in reader:
            t = parse(row['TIMESTAMP_START'], True)
            if t in needed or t in (LEFT, RIGHT):
                if t in source:
                    raise ValueError('Duplicate source time')
                source[t] = {key: row[key] for key in fields}
    if not needed.issubset(source):
        raise ValueError('Approved 2024 source values incomplete')
    temporary = a.out_dir / 'DE-Gri_2011_2024_approved_sensitivity.csv.partial'
    final = a.out_dir / 'DE-Gri_2011_2024_approved_sensitivity.csv'
    edits, observed, boundary = [], set(), {}
    try:
        with prior.open(encoding='utf-8-sig', newline='') as inp, temporary.open('x', encoding='utf-8', newline='') as out:
            reader = csv.DictReader(inp)
            required = {'time', 'TA_USE', 'VPD_USE', 'TBOT', 'QBOT', 'PSRF'}
            if not required.issubset(reader.fieldnames or []):
                raise ValueError('Candidate fields missing')
            writer = csv.DictWriter(out, fieldnames=reader.fieldnames); writer.writeheader()
            for row in reader:
                t = parse(row['time'])
                if t in needed:
                    if t in observed:
                        raise ValueError('Duplicate target')
                    observed.add(t)
                    orig = source[t]
                    if orig['TA_F_QC'] not in ('0', '0.0') or orig['VPD_F_QC'] not in ('1', '1.0'):
                        raise ValueError('Expected QC0 T and QC1 VPD')
                    temp, pressure = value(row['TA_USE']), value(row['PSRF'])
                    if abs(temp - value(orig['TA_F'])) > 1e-7 or abs(pressure - 1000*value(orig['PA_F'])) > 1:
                        raise ValueError('Temperature or pressure mismatch')
                    vpd = value(orig['VPD_ERA'])
                    q, rh = humidity(temp, vpd, pressure)
                    before = {key: row[key] for key in CHANGED}
                    row.update(VPD_USE=str(vpd), QBOT=str(q))
                    edits.append({'time':str(t), 'TA_C_unchanged':temp, 'before':before,
                                  'after':{key:row[key] for key in CHANGED}, 'RH_pct':rh})
                if t in (LEFT, RIGHT):
                    if t in boundary:
                        raise ValueError('Duplicate boundary')
                    boundary[t] = {'time':str(t), 'source':source.get(t),
                                   'selected':{k:row[k] for k in ('TA_USE','VPD_USE','QBOT','PSRF')}}
                writer.writerow(row)
        if observed != needed or set(boundary) != {LEFT, RIGHT}:
            raise ValueError('One or more target/boundary times missing')
        with prior.open(encoding='utf-8-sig', newline='') as f1, temporary.open(encoding='utf-8', newline='') as f2:
            r1, r2 = csv.DictReader(f1), csv.DictReader(f2)
            if r1.fieldnames != r2.fieldnames:
                raise ValueError('Header mismatch')
            for old, new in zip_longest(r1, r2):
                if old is None or new is None:
                    raise ValueError('Row count changed')
                is_target = parse(old['time']) in needed
                for key in r1.fieldnames:
                    if (not is_target or key not in CHANGED) and old[key] != new[key]:
                        raise ValueError('Unexpected modification: ' + key)
        if [sha(src), sha(baseline), sha(prior)] != input_hashes:
            raise ValueError('Input changed while processing')
        edits.sort(key=lambda x: x['time'])
        changes = {'left_VPD_delta_hPa':float(edits[0]['after']['VPD_USE'])-float(boundary[LEFT]['selected']['VPD_USE']),
                   'right_VPD_delta_hPa':float(boundary[RIGHT]['selected']['VPD_USE'])-float(edits[-1]['after']['VPD_USE'])}
        result = {'read_only_source':True, 'model_input_approved':False, 'time_alignment_verified':False,
                  'candidate_kind':'2011_2024_DETACHED_CSV_ONLY_NOT_DATM', 'prior_candidate_sha256':input_hashes[2],
                  'baseline_sha256':input_hashes[1], 'source_sha256':input_hashes[0],
                  'candidate_sha256':sha(temporary), 'prior_2011_edits':m['edits'],
                  'approved_2024_edits':edits, 'boundaries':[boundary[LEFT],boundary[RIGHT]], 'boundary_deltas':changes}
        with (a.out_dir/'manifest_PRIVATE.json').open('x', encoding='utf-8') as f:
            json.dump(result, f, indent=2); f.write('\n')
        os.replace(temporary, final)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise
    for e in edits: print('2024 APPROVED SENSITIVITY', json.dumps(e, separators=(',', ':')))
    for x in result['boundaries']: print('2024 BOUNDARY', json.dumps(x, separators=(',', ':')))
    print('2024 VPD BOUNDARY DELTAS', json.dumps(changes, separators=(',', ':')))
    print('COMPLETE 2011+2024 DETACHED CSV', final, '| 11+23 edits; NO NETCDF, CASE OR SLURM')


if __name__ == '__main__':
    main()
