#!/usr/bin/env python3
"""Read-only DE-Gri context for two previously flagged meteorological events.

Reads paths from an operator-provided Stage03D report. Outputs only selected
event windows. Naive timestamps are labels, not proof of UTC alignment.
"""
import argparse
import csv
import hashlib
import json
from datetime import datetime, timedelta
from pathlib import Path

EXPECTED = 'STAGE03D_BATCH04_RECOVER_OLD_RAIN_AND_TARGETED_ORIGINAL_SOURCE_CONTEXT'
TARGETS = (datetime(2011, 6, 13, 7), datetime(2024, 7, 4, 7, 30))
SRC = ('TA_F', 'TA_F_QC', 'TA_ERA', 'VPD_F', 'VPD_F_QC', 'VPD_ERA', 'PA_F', 'P_F', 'P_F_QC')
MET = ('TA_USE', 'VPD_USE', 'TBOT', 'QBOT', 'PSRF', 'PRECTmms')


def sha(path):
    result = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1048576), b''):
            result.update(chunk)
    return result.hexdigest()


def read(path, time_key, source):
    collected = {}
    fields = SRC if source else MET
    with path.open(encoding='utf-8-sig', newline='') as f:
        reader = csv.DictReader(f)
        required = {time_key, 'TA_F', 'TA_F_QC', 'VPD_F', 'VPD_F_QC'} if source else {time_key, 'TA_USE', 'VPD_USE'}
        if not required.issubset(reader.fieldnames or []):
            raise ValueError('Required columns missing: ' + str(required - set(reader.fieldnames or [])))
        selected = [key for key in fields if key in reader.fieldnames]
        for r in reader:
            val = str(r[time_key]).strip().strip("'\"")
            if source and val.endswith('.0') and val[:-2].isdigit():
                val = val[:-2]
            try:
                t = datetime.strptime(val, '%Y%m%d%H%M') if source else datetime.fromisoformat(val)
            except ValueError:
                raise ValueError('Unparseable source/forcing timestamp')
            if t.tzinfo is not None:
                raise ValueError('Expected naive timestamp label')
            if any(abs(t - x) <= timedelta(hours=2) for x in TARGETS):
                if t in collected:
                    raise ValueError('Duplicate time in context: ' + str(t))
                collected[t] = {key: r[key] for key in selected}
    return collected, selected


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--stage03d', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True, help='new private JSON file')
    a = p.parse_args()
    report = json.loads(a.stage03d.read_text(encoding='utf-8'))
    if report.get('stage') != EXPECTED or report.get('read_only') is not True or report.get('science_release') is not False:
        raise ValueError('Expected original Stage03D read-only HOLD report')
    rows = [x for x in report['sites'] if x.get('site') == 'DE-Gri']
    if len(rows) != 1:
        raise ValueError('Expected exactly one DE-Gri site')
    src, met = (Path(rows[0][x]) for x in ('source_manifest_primary_file', 'Stage28_selected_forcing_path'))
    before = [sha(src), sha(met)]
    original, source_fields = read(src, 'TIMESTAMP_START', True)
    selected, selected_fields = read(met, 'time', False)
    if [sha(src), sha(met)] != before:
        raise ValueError('Input changed during scan')
    result = {'read_only': True, 'science_release': False, 'time_alignment_verified': False,
              'source_sha256': before[0], 'selected_sha256': before[1],
              'source_fields': source_fields, 'selected_fields': selected_fields, 'events': []}
    for target in TARGETS:
        times = [target + timedelta(minutes=30*i) for i in range(-4, 5)]
        event = {'target': str(target), 'rows': [
            {'time': str(t), 'source': original.get(t), 'selected': selected.get(t)} for t in times]}
        result['events'].append(event)
    with a.out.open('x', encoding='utf-8') as f:
        json.dump(result, f, indent=2)
        f.write('\n')
    for e in result['events']:
        for row in e['rows']:
            print('DE-GRI CONTEXT', json.dumps({'target': e['target'], **row}, separators=(',', ':')))
    print('COMPLETE two windows, SCIENCE HOLD; no forcing, NetCDF, case or job modified; output', a.out)


if __name__ == '__main__':
    main()
