#!/usr/bin/env python3
"""Read-only full-year numerical and integrity QC of Stage23 six-site Met inputs.

Checks hashes, timeline, field units, finite/physical values, humidity closure,
surface/stream hashes and reports low humidity and large temperature jumps as
review flags. Does not establish that tower measurements or source QC0 edits are
scientifically correct and does not change inputs, cases or Slurm jobs.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path

import numpy as np
from netCDF4 import Dataset

SITES = ('CA-Cbo', 'CA-Man', 'CA-TP1', 'CA-TP3', 'US-Aud', 'US-Bar')
UNITS = {'TBOT': 'K', 'QBOT': 'kg kg-1', 'SHUM': 'kg kg-1', 'PSRF': 'Pa',
         'FSDS': 'W m-2', 'FLDS': 'W m-2', 'WIND': 'm s-1',
         'PRECTmms': 'mm s-1', 'RH': 'percent', 'ZBOT': 'm'}
N = 17520


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for data in iter(lambda: f.read(1048576), b''): h.update(data)
    return h.hexdigest()


def required_file(path, expected_hash, root):
    p = Path(path).resolve(strict=True)
    if root not in p.parents: raise ValueError('File outside candidate root: ' + str(p))
    if sha(p) != expected_hash: raise ValueError('Checksum mismatch: ' + str(p))
    return p


def rh_from_state(t, q, p):
    tc = t - 273.15
    return 100.0 * ((q * (p / 100.0)) / (0.622 + 0.378 * q)) / (6.112 * np.exp(17.67 * tc / (tc + 243.5)))


def scan_year(path, year, previous_t=None, utc_shift=0):
    stats = {'samples': 0, 'low_rh_lt1': 0, 'low_rh_1to5': 0, 'over_100_rh': 0,
             'temperature_jumps_gt8C': 0, 'leap_day_edges_excluded': 0}
    with Dataset(str(path)) as ds:
        time = ds.variables['time']
        values = np.asarray(np.ma.filled(time[:], np.nan), dtype=float).ravel()
        if time.calendar != 'noleap' or not str(time.units).startswith(f'days since {year:04d}-01-01'):
            raise ValueError('Unsupported time units/calendar')
        if len(values) != N or not np.allclose(values, np.arange(N) / 48. + 1. / 96., rtol=0, atol=1e-9):
            raise ValueError('Invalid UTC midpoint timeline')
        arr = {}
        for name, units in UNITS.items():
            if name not in ds.variables: raise ValueError('Missing field ' + name)
            v = ds.variables[name]
            if str(getattr(v, 'units', '')).strip() != units: raise ValueError(name + ': unexpected units ' + str(getattr(v, 'units', '')))
            if v.dimensions != ('time', 'lat', 'lon') or v.shape != (N, 1, 1):
                raise ValueError(name + ': unexpected dimensions')
            a = np.asarray(np.ma.filled(v[:], np.nan), dtype=float).reshape(-1)
            if not np.isfinite(a).all(): raise ValueError(name + ': missing/nonfinite values')
            arr[name] = a
        t, p, q, rh = arr['TBOT'], arr['PSRF'], arr['QBOT'], arr['RH']
        checks = {'TBOT': (t > 180) & (t < 340), 'PSRF': (p > 49000) & (p < 111000),
                  'QBOT': (q > 0) & (q < .08), 'WIND': arr['WIND'] >= 0,
                  'FSDS': arr['FSDS'] >= 0, 'FLDS': arr['FLDS'] >= 0,
                  'PRECTmms': arr['PRECTmms'] >= 0, 'ZBOT': (arr['ZBOT'] > 0) & (arr['ZBOT'] <= 150),
                  'RH': (rh >= 0) & (rh <= 100.5)}
        for name, ok in checks.items():
            if not np.all(ok): raise ValueError(name + ': physical range failure count=' + str(int(np.count_nonzero(~ok))))
        if not np.allclose(arr['SHUM'], q, atol=1e-10, rtol=1e-6): raise ValueError('SHUM differs from QBOT')
        if not np.allclose(rh_from_state(t, q, p), rh, atol=.005, rtol=.0005):
            raise ValueError('RH inconsistent with TBOT/QBOT/PSRF')
        jumps = np.abs(np.diff(t)) > 8.
        # The local Feb 29 gap shifts with the forcing into the UTC output.
        if year % 4 == 0 and (year % 100 != 0 or year % 400 == 0):
            edge = (31 + 28) * 48 + utc_shift - 1
            if jumps[edge]: stats['leap_day_edges_excluded'] += 1
            jumps[edge] = False
        stats['temperature_jumps_gt8C'] = int(jumps.sum())
        if previous_t is not None and abs(float(t[0]) - previous_t) > 8:
            stats['temperature_jumps_gt8C'] += 1
        stats.update(samples=len(t), low_rh_lt1=int((rh < 1).sum()),
                     low_rh_1to5=int(((rh >= 1) & (rh < 5)).sum()),
                     over_100_rh=int((rh > 100).sum()),
                     t_min=float(t.min()), t_max=float(t.max()),
                     z_min=float(arr['ZBOT'].min()), z_max=float(arr['ZBOT'].max()))
        return stats, float(t[-1])


def audit_site(root, record):
    site = record['site']
    manifest = required_file(record['manifest'], record['sha256'], root)
    obj = json.loads(manifest.read_text(encoding='utf-8'))
    if obj.get('site') != site or obj.get('jobs_submitted') is not False or obj.get('case_created') is not False:
        raise ValueError('Invalid candidate manifest')
    required_file(obj['candidate_surface'], obj['candidate_surface_sha256'], root)
    stream = required_file(obj['detached_stream'], obj['detached_stream_sha256'], root)
    files = obj['annual_files']; first, last = obj['years']
    shift = obj['UTC_shift_halfhours']
    if not isinstance(shift, int) or not 0 < shift < 48:
        raise ValueError('Unsupported UTC shift')
    if [x['year'] for x in files] != list(range(first, last + 1)):
        raise ValueError('Noncontiguous forcing years')
    node = ET.parse(stream).getroot()
    entries = [e for e in node.iter('stream_info') if e.attrib.get('name') == 'CLM_USRDAT.UNSET']
    if len(entries) != 1: raise ValueError('No unique CLM_USRDAT stream')
    ent = entries[0]
    for key, val in [('year_first', first), ('year_last', last), ('year_align', first), ('offset', 0)]:
        v = ent.find(key)
        if v is None or (v.text or '').strip() != str(val): raise ValueError('Stream ' + key + ' mismatch')
    data = ent.find('datafiles')
    if data is None or [(e.text or '').strip() for e in data.findall('file')] != [x['path'] for x in files]:
        raise ValueError('Stream file list mismatch')
    summary = {'site': site, 'years': len(files), 'samples': 0, 'low_rh_lt1': 0, 'low_rh_1to5': 0,
               'over_100_rh': 0, 'temperature_jumps_gt8C': 0, 'leap_day_edges_excluded': 0,
               't_min': None, 't_max': None, 'z_min': None, 'z_max': None}
    previous = None
    for item in files:
        path = required_file(item['path'], item['sha256'], root)
        stats, previous = scan_year(path, item['year'], previous, shift)
        for key in ('samples', 'low_rh_lt1', 'low_rh_1to5', 'over_100_rh', 'temperature_jumps_gt8C', 'leap_day_edges_excluded'):
            summary[key] += stats[key]
        for key, fn in [('t_min', min), ('t_max', max), ('z_min', min), ('z_max', max)]:
            summary[key] = stats[key] if summary[key] is None else fn(summary[key], stats[key])
        print('YEAR PASS', site, item['year'], flush=True)
    return summary


def audit(root):
    root = Path(root).resolve(strict=True)
    completion = json.loads((root / 'COMPLETE.json').read_text(encoding='utf-8'))
    rows = completion.get('sites', [])
    if completion.get('model_jobs_submitted') is not False or len(rows) != 6 or {r.get('site') for r in rows} != set(SITES):
        raise ValueError('Invalid six-site completion receipt')
    results = []
    for row in rows:
        site = row['site']
        try:
            result = audit_site(root, row); result['status'] = 'NUMERICAL_PASS'
        except Exception as e:
            result = {'site': site, 'status': 'ERROR', 'error': type(e).__name__ + ': ' + str(e)}
        results.append(result)
        print('SITE RESULT', json.dumps(result, sort_keys=True), flush=True)
    print('\nFINAL RESULTS:', json.dumps(results, sort_keys=True), flush=True)
    print('RH and temperature jumps are review flags, not automatic evidence of incorrect data.')
    print('This audit cannot verify TA_F sensor mapping, source QC0 edit decisions, or actual model coupling.')
    return int(any(r['status'] != 'NUMERICAL_PASS' for r in results))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--run', required=True, type=Path)
    args = p.parse_args()
    return audit(args.run)


if __name__ == '__main__': raise SystemExit(main())

