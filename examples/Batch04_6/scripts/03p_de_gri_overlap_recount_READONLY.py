#!/usr/bin/env python3
"""Read-only recount of DE-Gri target episodes from a Stage03D report.

Every target window is counted independently, including overlapping windows.
Outputs aggregate summaries only; timestamps are compared as naive labels,
which does not establish cross-product timezone or averaging alignment.
"""
import argparse
import bisect
import csv
import hashlib
import json
import math
from datetime import datetime, timedelta
from pathlib import Path

EXPECTED = 'STAGE03D_BATCH04_RECOVER_OLD_RAIN_AND_TARGETED_ORIGINAL_SOURCE_CONTEXT'


def dt(value, source=False):
    value = str(value).strip().strip("'\"")
    if source:
        if value.endswith('.0') and value[:-2].isdigit():
            value = value[:-2]
        return datetime.strptime(value, '%Y%m%d%H%M')
    result = datetime.fromisoformat(value)
    if result.tzinfo is not None:
        raise ValueError('Expected naive timestamp, got timezone-aware timestamp')
    return result


def number(value):
    try:
        n = float(value)
        return n if math.isfinite(n) and n != -9999 else None
    except (ValueError, TypeError):
        return None


def match_windows(windows, stamp):
    """Return every containing window, including overlaps."""
    starts = [x[0] for x in windows]
    return [x for x in windows[:bisect.bisect_right(starts, stamp)] if stamp <= x[1]]


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def scan(path, windows, source):
    fields = ('TA_F', 'VPD_F', 'TA_F_QC', 'VPD_F_QC') if source else ('TA_USE', 'VPD_USE')
    timefield = 'TIMESTAMP_START' if source else 'time'
    found = {key: {} for _, _, key in windows}
    with path.open(encoding='utf-8-sig', newline='') as f:
        reader = csv.DictReader(f)
        if not set(fields + (timefield,)).issubset(reader.fieldnames or []):
            raise ValueError('Missing required input columns for ' + ('source' if source else 'selected'))
        starts = [w[0] for w in windows]
        for row in reader:
            try:
                stamp = dt(row[timefield], source)
            except (ValueError, TypeError):
                raise ValueError('Unparseable timestamp in ' + ('source' if source else 'selected'))
            limit = bisect.bisect_right(starts, stamp)
            for lo, hi, key in windows[:limit]:
                if stamp <= hi:
                    if stamp in found[key]:
                        raise ValueError('Duplicate timestamp in episode ' + key)
                    found[key][stamp] = {field: number(row[field]) for field in fields}
    return found


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--stage03d', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True, help='new private JSON file')
    a = p.parse_args()
    report = json.loads(a.stage03d.read_text(encoding='utf-8'))
    if report.get('stage') != EXPECTED or report.get('read_only') is not True or report.get('science_release') is not False:
        raise ValueError('Expected read-only Stage03D science-HOLD report')
    sites = [s for s in report['sites'] if s.get('site') == 'DE-Gri']
    events = [e for e in report['target_event_context'] if e.get('site') == 'DE-Gri']
    if len(sites) != 1 or len(events) != 49 or len({e['episode'] for e in events}) != 49:
        raise ValueError('Expected one DE-Gri site and 49 distinct episodes')
    windows = []
    for e in events:
        lo = dt(e['window_start']) + timedelta(hours=2)
        hi = dt(e['window_end']) - timedelta(hours=2)
        if hi < lo or (hi-lo).total_seconds() % 1800:
            raise ValueError('Invalid padded target window ' + e['episode'])
        windows.append((lo, hi, e['episode']))
    windows.sort()
    src = Path(sites[0]['source_manifest_primary_file'])
    met = Path(sites[0]['Stage28_selected_forcing_path'])
    if not src.is_file() or not met.is_file():
        raise FileNotFoundError('Stage03D input file no longer exists')
    before = [digest(src), digest(met)]
    original = scan(src, windows, True)
    selected = scan(met, windows, False)
    if [digest(src), digest(met)] != before:
        raise RuntimeError('Input changed during scan; results discarded')
    summary = []
    for lo, hi, key in windows:
        s, m = original[key], selected[key]
        common = s.keys() & m.keys()
        differences = {}
        for left, right, label in [('TA_F', 'TA_USE', 'TA_C'), ('VPD_F', 'VPD_USE', 'VPD_hPa')]:
            diffs = [abs(s[t][left] - m[t][right]) for t in common if s[t][left] is not None and m[t][right] is not None]
            differences[label] = {'pairs': len(diffs), 'max_abs_difference': max(diffs) if diffs else None}
        expected = int((hi-lo).total_seconds()/1800) + 1
        summary.append({'episode': key, 'start': str(lo), 'end': str(hi),
                        'expected_HH': expected, 'source_HH': len(s), 'selected_HH': len(m),
                        'same_label_HH': len(common), 'differences': differences,
                        'science_release': False})
    result = {'stage': 'DE_GRI_OVERLAP_RECOUNT', 'read_only': True,
              'time_alignment_verified': False, 'science_release': False,
              'source_sha256': before[0], 'selected_sha256': before[1], 'episodes': summary}
    with a.out.open('x', encoding='utf-8') as f:
        json.dump(result, f, indent=2)
        f.write('\n')
    for e in summary:
        print('DE-GRI RECOUNT', json.dumps(e, separators=(',', ':')))
    print('COMPLETE', len(summary), 'episodes; report', a.out, 'SCIENCE HOLD; NO INPUTS OR CASES MODIFIED')


if __name__ == '__main__':
    main()
