#!/usr/bin/env python3
"""Make a detached approved DE-Gri 2011 CSV candidate; audit 2024 boundary.

No source files, annual NetCDFs, CIME cases or Slurm jobs are modified. The
candidate is a CSV sensitivity input, not a model-ready DATM NetCDF.
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

START = datetime(2011, 6, 13, 7)
END = datetime(2011, 6, 13, 12)
DAY = datetime(2024, 7, 4, 14)
STOP = datetime(2024, 7, 4, 23, 30)
CHANGED = {'TA_USE', 'VPD_USE', 'TBOT', 'QBOT'}


def sha(path):
    result = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            result.update(block)
    return result.hexdigest()


def parse(s, source=False):
    s = str(s).strip().strip("'\"")
    if source and s.endswith('.0') and s[:-2].isdigit():
        s = s[:-2]
    d = datetime.strptime(s, '%Y%m%d%H%M') if source else datetime.fromisoformat(s)
    if d.tzinfo is not None:
        raise ValueError('Timezone-aware time unsupported')
    return d


def value(s):
    x = float(s)
    if not math.isfinite(x) or x == -9999:
        raise ValueError('Missing/nonfinite value')
    return x


def humidity(temp, vpd, pressure):
    sat = 6.112 * math.exp(17.67 * temp / (temp + 243.5))
    e = (sat - vpd) * 100
    if not 0 <= vpd <= sat or not 50000 <= pressure <= 115000 or not 0 <= e < pressure:
        raise ValueError('Nonphysical T, VPD or pressure')
    return 0.622 * e / (pressure - 0.378 * e), (sat - vpd) / sat * 100


def collect_source(path):
    source = {}
    fields = ('TA_F', 'TA_F_QC', 'TA_ERA', 'VPD_F', 'VPD_F_QC', 'VPD_ERA', 'PA_F')
    with path.open(encoding='utf-8-sig', newline='') as f:
        reader = csv.DictReader(f)
        if not set(fields + ('TIMESTAMP_START',)).issubset(reader.fieldnames or []):
            raise ValueError('Required tower product or ERA columns absent')
        for row in reader:
            t = parse(row['TIMESTAMP_START'], True)
            if START <= t <= END or DAY <= t <= STOP:
                if t in source:
                    raise ValueError('Duplicate source time ' + str(t))
                source[t] = {k: row[k] for k in fields}
    return source


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--stage03d', type=Path, required=True)
    p.add_argument('--context', type=Path, required=True)
    p.add_argument('--out-dir', type=Path, required=True, help='new empty private directory')
    p.add_argument('--confirm-approved-2011', action='store_true')
    a = p.parse_args()
    if not a.confirm_approved_2011:
        p.error('Explicit 2011 sensitivity approval required')
    if not a.out_dir.is_dir() or a.out_dir.is_symlink() or any(a.out_dir.iterdir()):
        raise ValueError('Output must be an existing empty directory')
    d = json.loads(a.stage03d.read_text(encoding='utf-8'))
    c = json.loads(a.context.read_text(encoding='utf-8'))
    if d.get('stage') != 'STAGE03D_BATCH04_RECOVER_OLD_RAIN_AND_TARGETED_ORIGINAL_SOURCE_CONTEXT' or d.get('read_only') is not True or c.get('read_only') is not True or c.get('science_release') is not False:
        raise ValueError('Expected original readonly reports')
    sites = [s for s in d['sites'] if s.get('site') == 'DE-Gri']
    if len(sites) != 1:
        raise ValueError('DE-Gri site entry missing/ambiguous')
    source = Path(sites[0]['source_manifest_primary_file'])
    selected = Path(sites[0]['Stage28_selected_forcing_path'])
    baseline = [sha(source), sha(selected)]
    if baseline != [c.get('source_sha256'), c.get('selected_sha256')]:
        raise ValueError('Inputs changed since prior extended context report')
    b = json.loads(Path(d['source_stage03b']).read_text(encoding='utf-8'))
    old = [x for x in b['sites'] if x.get('site') == 'DE-Gri']
    if len(old) != 1 or old[0].get('stage28_met_SHA_verified') is not True or old[0].get('stage28_met_SHA_expected') != baseline[1]:
        raise ValueError('Historical Stage28 meteorology hash verification failed')
    records = collect_source(source)
    targets = [START + timedelta(minutes=30*i) for i in range(11)]
    if any(t not in records for t in targets):
        raise ValueError('Approved 2011 source records missing')
    target_seen, edits, afternoon = set(), [], {}
    temporary = a.out_dir / 'DE-Gri_2011_approved_sensitivity.csv.partial'
    final = a.out_dir / 'DE-Gri_2011_approved_sensitivity.csv'
    try:
        with selected.open(encoding='utf-8-sig', newline='') as inp, temporary.open('x', encoding='utf-8', newline='') as out:
            reader = csv.DictReader(inp)
            required = CHANGED | {'time', 'PSRF', 'FSDS', 'FLDS', 'WIND', 'PRECTmms'}
            if not required.issubset(reader.fieldnames or []):
                raise ValueError('Selected forcing columns missing')
            writer = csv.DictWriter(out, fieldnames=reader.fieldnames)
            writer.writeheader()
            for row in reader:
                t = parse(row['time'])
                if t in targets:
                    if t in target_seen:
                        raise ValueError('Duplicate selected target timestamp')
                    target_seen.add(t)
                    src = records[t]
                    if src['TA_F_QC'] not in ('1', '1.0') or src['VPD_F_QC'] not in ('1', '1.0'):
                        raise ValueError('Target no longer QC1 for temperature and VPD')
                    if abs(value(row['TA_USE']) - value(src['TA_F'])) > 1e-7 or abs(value(row['VPD_USE']) - value(src['VPD_F'])) > 1e-7:
                        raise ValueError('Selected baseline differs from approved target evidence')
                    pressure = value(row['PSRF'])
                    if abs(pressure - value(src['PA_F']) * 1000) > 1:
                        raise ValueError('Pressure units/source mismatch')
                    before = {k: row[k] for k in CHANGED}
                    temp, vpd = value(src['TA_ERA']), value(src['VPD_ERA'])
                    q, rh = humidity(temp, vpd, pressure)
                    row.update(TA_USE=str(temp), VPD_USE=str(vpd), TBOT=str(temp + 273.15), QBOT=str(q))
                    edits.append({'time': str(t), 'before': before, 'after': {k: row[k] for k in CHANGED}, 'RH_pct': rh})
                if DAY <= t <= STOP:
                    if t in afternoon:
                        raise ValueError('Duplicate 2024 boundary timestamp')
                    afternoon[t] = {k: row[k] for k in ('TA_USE', 'VPD_USE', 'TBOT', 'QBOT', 'PSRF')}
                writer.writerow(row)
        if target_seen != set(targets):
            raise ValueError('Selected forcing lacks one or more target timestamps')
        with selected.open(encoding='utf-8-sig', newline='') as left, temporary.open(encoding='utf-8', newline='') as right:
            old_reader, new_reader = csv.DictReader(left), csv.DictReader(right)
            if old_reader.fieldnames != new_reader.fieldnames:
                raise ValueError('Candidate header differs from baseline')
            for old_row, new_row in zip_longest(old_reader, new_reader):
                if old_row is None or new_row is None:
                    raise ValueError('Candidate row count changed')
                target = parse(old_row['time']) in target_seen
                for key in old_reader.fieldnames:
                    if (not target or key not in CHANGED) and old_row[key] != new_row[key]:
                        raise ValueError('Unexpected candidate change: ' + key)
        if [sha(source), sha(selected)] != baseline:
            raise ValueError('Source or baseline changed during processing')
        boundary = []
        for i in range(20):
            t = DAY + timedelta(minutes=30*i)
            boundary.append({'time': str(t), 'source': records.get(t), 'selected': afternoon.get(t)})
        summary = {'read_only_source': True, 'model_input_approved': False,
                   'candidate_kind': '2011_DETACHED_CSV_ONLY_NOT_DATM', 'time_alignment_verified': False,
                   'source_sha256': baseline[0], 'baseline_sha256': baseline[1],
                   'candidate_sha256': sha(temporary), 'edits': edits,
                   'boundary_2024_no_changes': boundary}
        with (a.out_dir / 'manifest_PRIVATE.json').open('x', encoding='utf-8') as f:
            json.dump(summary, f, indent=2); f.write('\n')
        os.replace(temporary, final)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise
    for edit in edits:
        print('2011 APPROVED SENSITIVITY', json.dumps(edit, separators=(',', ':')))
    for row in boundary:
        print('2024 RIGHT BOUNDARY', json.dumps(row, separators=(',', ':')))
    print('COMPLETE 2011 detached CSV', final, '| 11 edits; 2024 NOT MODIFIED; NO NETCDF, CASE OR JOB')


if __name__ == '__main__':
    main()
