#!/usr/bin/env python3
"""Prepare six detached Batch01 forcing/surface candidates; never create cases/jobs.

Uses the existing, SHA-verified Stage81/82 forcing, Stage31 height policy and
Stage14 UTC transformation. Ambiguous dates use earliest bound as a clearly
labelled scenario, not an observed installation date. CA-Cbo/CA-Man use the
user-authorized top-level BASE TA proxy. Grid soil is preserved and labelled.
All input files are read-only; output root must be new. A COMPLETE receipt is
written only after all six sites pass full checks.
"""
from __future__ import annotations
import argparse
import copy
import csv
import hashlib
import importlib.util
import json
import shutil
import xml.etree.ElementTree as ET
from pathlib import Path

import numpy as np
import pandas as pd
from netCDF4 import Dataset

SITES = ('CA-Cbo', 'CA-Man', 'CA-TP1', 'CA-TP3', 'US-Aud', 'US-Bar')
STATIC = {'CA-Cbo': ('TA_1_1_1', 42.), 'CA-Man': ('TA_1_1_1', 30.),
          'US-Bar': ('TA_PI_F_1_1_1', 23.8)}
DYNAMIC = {'CA-TP1', 'CA-TP3', 'US-Aud'}
BASE_SHA = '1c1e4171d295406a13d503f877b58661a651c88ffb6f0b6ec498f56bb1fcec5a'
PFT_BLOB = '14c6352f46c4ed07da1f73dc58474ac0a55ef1ee'
ZERO_LAND = ('PCT_CROP', 'PCT_LAKE', 'PCT_WETLAND', 'PCT_GLACIER', 'PCT_URBAN')
CHANGED = set(ZERO_LAND) | {'PCT_NATVEG', 'PCT_NAT_PFT'}


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(1048576), b''): h.update(block)
    return h.hexdigest()


def blob_sha(path):
    data = Path(path).read_bytes()
    return hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()


def load_module(path):
    spec = importlib.util.spec_from_file_location('batch01_stage14', path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def height_year(year, policy, bound='earliest_possible'):
    """Heights on the LOCAL interval-start axis, excluding leap day."""
    if bound not in ('earliest_possible', 'latest_upper_bound'):
        raise ValueError('Unknown event boundary')
    t = pd.date_range(f'{year}-01-01', f'{year + 1}-01-01', freq='30min', inclusive='left')
    t = t[~((t.month == 2) & (t.day == 29))]
    if len(t) != 17520: raise ValueError('Invalid noleap timeline')
    arr = np.full(len(t), float(policy['baseline_m']), dtype=float)
    previous = None
    for event in policy.get('dated_events', []):
        when = pd.Timestamp(event[bound])
        if previous is not None and when < previous: raise ValueError('Unsorted height events')
        previous = when
        arr[t >= when] = float(event['height_m'])
    if not np.isfinite(arr).all() or np.any((arr <= 0) | (arr > 150)):
        raise ValueError('Invalid height values')
    return arr


def utc_heights(year, first, last, shift, policy, bound='earliest_possible'):
    if not 0 < shift < 17520: raise ValueError('UTC shift outside supported range')
    previous = last if year == first else year - 1
    before = height_year(previous, policy, bound)
    current = height_year(year, policy, bound)
    return np.concatenate((before[-shift:], current[:-shift]))


def checked_recommendations(path):
    if blob_sha(path) != PFT_BLOB: raise ValueError('Batch01 PFT source blob does not match')
    with Path(path).open(encoding='utf-8-sig', newline='') as f:
        rows = list(csv.DictReader(f))
    selected = {r['site']: r for r in rows if r['site'] in SITES}
    if len(selected) != len(SITES): raise ValueError('Missing PFT sites')
    for site, row in selected.items():
        host = {int(k): float(v) for k, v in json.loads(row['clm_pct_nat_pft_json']).items()}
        if any(k < 0 or k >= 15 or not 0 <= v <= 100 for k, v in host.items()) or abs(sum(host.values()) - 100) > 1e-6:
            raise ValueError(site + ': invalid host PFT')
    return selected


def checked_base(path):
    if sha(path) != BASE_SHA: raise ValueError('BASE measurement height source does not match')
    found = set()
    with Path(path).open(encoding='utf-8-sig', newline='') as f:
        for r in csv.DictReader(f):
            site = r.get('Site_ID')
            if site in STATIC:
                var, value = STATIC[site]
                if r.get('Variable') == var:
                    try:
                        if abs(float(r.get('Height', '')) - value) < 1e-8: found.add(site)
                    except ValueError: pass
    if found != set(STATIC): raise ValueError('Selected static proxy absent from BASE metadata')


def expected_fates(host, matrix):
    out = {}
    if matrix.ndim != 2 or matrix.shape[0] < 14: raise ValueError('Invalid HLM/FATES map')
    for k, value in host.items():
        if k == 0: continue
        for slot, weight in enumerate(matrix[k - 1]):
            if weight > 0: out[slot + 1] = out.get(slot + 1, 0.) + float(value) * float(weight)
    return out


def verify_map(row, matrix):
    host = {int(k): float(v) for k, v in json.loads(row['clm_pct_nat_pft_json']).items()}
    target = {int(k): float(v) for k, v in json.loads(row['fates_natland_percent_json']).items()}
    result = expected_fates(host, matrix)
    for k in set(target) | set(result):
        if abs(target.get(k, 0.) - result.get(k, 0.)) > 1e-3:
            raise ValueError(row['site'] + ': host-to-FATES mapping mismatch')
    if abs(host.get(0, 0.) - float(row['bare_percent'])) > 1e-6:
        raise ValueError(row['site'] + ': bare mismatch')
    return host, result


def make_surface(source, target, site, host):
    shutil.copyfile(source, target)
    with Dataset(str(target), 'r+') as ds:
        for name in CHANGED:
            if name not in ds.variables: raise ValueError(site + ': missing surface ' + name)
        ds.variables['PCT_NATVEG'][:] = 100.
        for name in ZERO_LAND: ds.variables[name][:] = 0.
        v = ds.variables['PCT_NAT_PFT']
        if v.size != 15: raise ValueError(site + ': not 15 host PFTs')
        values = np.zeros(v.shape)
        for k, val in host.items(): values.reshape(-1)[k] = val
        v[:] = values
        ds.six_site_soil_policy = 'SOURCE_GRID_SOIL_UNCHANGED_NOT_SITE_MEASUREMENT'
        ds.six_site_pft_policy = 'MODEL_HYPOTHESIS_NOT_MEASURED_LAND_COVER'
    with Dataset(str(source)) as a, Dataset(str(target)) as b:
        for name in a.variables:
            if name not in CHANGED and not np.ma.allequal(a.variables[name][:], b.variables[name][:]):
                raise ValueError(site + ': unrelated surface variable changed: ' + name)
        p = np.ma.filled(b.variables['PCT_NAT_PFT'][:], np.nan).ravel()
        expected = np.array([host.get(i, 0.) for i in range(15)])
        if not np.allclose(p, expected, atol=1e-5): raise ValueError(site + ': PFT output mismatch')
        for k, target_value in [('PCT_NATVEG', 100.), *((x, 0.) for x in ZERO_LAND)]:
            if not np.allclose(b.variables[k][:], target_value, atol=1e-6):
                raise ValueError(site + ': landunit output mismatch: ' + k)


def source_inputs(stage, base_csv, pft_csv):
    checked_base(base_csv)
    recommendations = checked_recommendations(pft_csv)
    s81 = stage.jload(stage.ST81); s82 = stage.jload(stage.ST82); s31 = stage.jload(stage.ST31)
    if (s81.get('stage') != 81 or s81.get('all_annual_netcdf_files') != 213 or
        s82.get('stage') != 82 or s82.get('verified_annual_files_sha256') != 213 or
        s82.get('input_stage81_manifest_sha256') != sha(stage.ST81) or
        s31.get('method') != 'AmeriFlux_STAGE31_BASE_STATIC_DYNAMIC_POLICY_SCENARIOS'):
        raise ValueError('Existing Stage31/81/82 receipts are not consistent')
    stage.stream_template()  # validate before any output is made
    records = {r['site']: r for r in s81['sites']}
    policies = s31.get('provisional_sensor_policy', {})
    param = stage.R / 'CTSM/src/fates/parameter_files/fates_params_default.json'
    pdata = json.loads(param.read_text())['parameters']
    matrix = np.asarray(pdata['fates_hlm_pft_map']['data'], dtype=float)
    out = {}
    for site in SITES:
        row = recommendations[site]; host, fates = verify_map(row, matrix)
        met, bif_sha = stage.clock_bif(site)
        shift_float = -float(met['UTC_OFFSET']) * 2
        if shift_float != int(shift_float) or not 0 < shift_float < 17520:
            raise ValueError(site + ': unsupported UTC offset')
        rec = records[site]; files = rec['annual_files']
        years = [int(r['year']) for r in files]
        if not years or years != list(range(years[0], years[-1] + 1)) or len(files) != rec['years_written']:
            raise ValueError(site + ': annual forcing sequence incomplete')
        nc = [(int(x['year']), Path(x['file']), x['sha256']) for x in files]
        if any(not p.is_file() or not p.is_absolute() for _, p, _ in nc):
            raise ValueError(site + ': annual forcing file missing')
        point = (float(rec['point_grid_lat']), float(rec['point_grid_lon']) % 360)
        if abs(point[0] - met['LOCATION_LAT']) > .1 or abs((point[1] - met['LOCATION_LONG'] + 180) % 360 - 180) > .1:
            raise ValueError(site + ': forcing point differs from BIF')
        if site in DYNAMIC:
            pol = copy.deepcopy(policies.get(site))
            if not pol or pol.get('candidate_ZBOT_mode') != 'DYNAMIC' or not pol.get('dated_events') or pol.get('source_snapshot_SHA256') != BASE_SHA:
                raise ValueError(site + ': missing Stage31 dynamic policy')
        else:
            variable, height = STATIC[site]
            if site == 'US-Bar':
                original = policies.get(site, {})
                if original.get('candidate_ZBOT_mode') != 'STATIC' or abs(float(original.get('baseline_m', 0)) - height) > 1e-6:
                    raise ValueError(site + ': Stage31 static policy mismatch')
            pol = {'site': site, 'variable_BASE': variable, 'baseline_m': height,
                   'dated_events': [], 'FLUXNET_TA_F_sensor_crosswalk': 'UNVERIFIED'}
        height_year(years[0], pol); height_year(years[-1], pol)
        candidates = sorted((stage.R / 'sites/MY_EC_SITE' / site / 'subset_data').glob('surfdata*.nc'))
        if len(candidates) != 1: raise ValueError(site + ': expected one source surface')
        src = candidates[0]
        with Dataset(str(src)) as ds:
            lat = float(np.asarray(ds.variables['LATIXY'][:]).ravel()[0])
            lon = float(np.asarray(ds.variables['LONGXY'][:]).ravel()[0]) % 360
            if abs(lat - met['LOCATION_LAT']) > 1e-5 or abs((lon - met['LOCATION_LONG'] + 180) % 360 - 180) > 1e-5:
                raise ValueError(site + ': PTS source surface does not match BIF')
            for key in CHANGED | {'PCT_SAND', 'PCT_CLAY', 'ORGANIC'}:
                if key not in ds.variables: raise ValueError(site + ': source surface lacks ' + key)
            for key in ('PCT_SAND', 'PCT_CLAY', 'ORGANIC'):
                arr = np.asarray(np.ma.filled(ds.variables[key][:], np.nan), dtype=float)
                if arr.size != 10 or not np.isfinite(arr).all(): raise ValueError(site + ': invalid original soil ' + key)
        out[site] = {'years': (years[0], years[-1]), 'tz': met['UTC_OFFSET'], 'ZBOT': float(pol['baseline_m']),
                     'NC': nc, 'point_lat_lon': point, 'policy': pol, 'bif_sha256': bif_sha,
                     'surface': src, 'host': host, 'fates': fates, 'recommendation': row['recommended_percent']}
    stage.check_nc(out, allsha=True)
    return out, param


def build(stage, out, sites, param):
    if set(sites) != set(SITES): raise ValueError('Refusing incomplete six-site input set')
    if out.exists() or out.is_symlink(): raise ValueError('Refusing existing output root')
    out.mkdir(parents=True)
    all_receipts = []
    for site, obj in sites.items():
        first, last = obj['years']; shift = int(-obj['tz'] * 2)
        source = {y: p for y, p, _ in obj['NC']}
        folder = out / site; yearly = folder / 'yearly'; yearly.mkdir(parents=True)
        surface = folder / ('surfdata_' + site + '_FIXNC_candidate.nc')
        make_surface(obj['surface'], surface, site, obj['host'])
        years = []
        for year, path, input_hash in obj['NC']:
            dest = yearly / f'{year}.nc'
            prev = last if year == first else year - 1
            stage.reindex_one(year, path, dest, shift, obj['ZBOT'], source[prev])
            heights = utc_heights(year, first, last, shift, obj['policy'])
            with Dataset(str(dest), 'r+') as ds:
                ds.variables['ZBOT'][:, 0, 0] = heights
                ds.variables['ZBOT'].long_name = 'PROVISIONAL BASE TA proxy; FLUXNET TA_F crosswalk unverified'
                ds.height_policy = 'LOCAL_INTERVAL_START_EARLIEST_EVENT_BOUND_THEN_SAME_UTC_SHIFT_AS_MET'
            with Dataset(str(dest)) as ds:
                if not np.array_equal(np.asarray(ds.variables['ZBOT'][:, 0, 0]), heights):
                    raise ValueError(site + ': UTC height mapping mismatch')
            if year in {first, (first + last) // 2, last}:
                bad = stage.solar_bad_fraction(dest, *obj['point_lat_lon'])
                print('SOLAR NIGHT FRACTION', site, year, round(bad, 3), '%', flush=True)
                if bad > 10: raise ValueError(site + ': UTC solar phase inconsistent')
            years.append({'year': year, 'path': str(dest), 'sha256': sha(dest),
                          'source_sha256': input_hash, 'previous_source_year': prev})
            print('FORCING READY', site, year, flush=True)
        tree, stream = stage.stream_template()
        for key, value in [('year_first', first), ('year_last', last), ('year_align', first), ('offset', 0)]:
            node = stream.find(key)
            if node is None: raise ValueError('Template missing ' + key)
            node.text = str(value)
        data = stream.find('datafiles')
        if data is None: raise ValueError('Template has no datafiles')
        for node in list(data): data.remove(node)
        for item in years: ET.SubElement(data, 'file').text = item['path']
        xml = folder / f'datm.streams.{site}.UTC_DETACHED.xml'
        ET.ElementTree(tree).write(str(xml), encoding='utf-8', xml_declaration=True)
        receipt = {'site': site, 'years': [first, last], 'source_bif_sha256': obj['bif_sha256'],
                   'UTC_offset_hours': obj['tz'], 'UTC_shift_halfhours': shift,
                   'source_surface': str(obj['surface']), 'source_surface_sha256': sha(obj['surface']),
                   'candidate_surface': str(surface), 'candidate_surface_sha256': sha(surface),
                   'soil': 'ORIGINAL GRID SOIL AND ORGANIC UNCHANGED; not a site observation',
                   'PFT': obj['recommendation'], 'host_pct': obj['host'], 'fates_pct': obj['fates'],
                   'fates_parameter_file': str(param), 'fates_parameter_sha256': sha(param),
                   'height_policy': obj['policy'], 'height_time_assumption': 'earliest bound scenario; not an observed date',
                   'clock_assumption': 'local interval start, plus midpoint and UTC shift; original crosswalk unverified',
                   'detached_stream': str(xml), 'detached_stream_sha256': sha(xml), 'annual_files': years,
                   'case_created': False, 'jobs_submitted': False}
        (folder / 'manifest.json').write_text(json.dumps(receipt, indent=2) + '\n')
        all_receipts.append({'site': site, 'manifest': str(folder / 'manifest.json'), 'sha256': sha(folder / 'manifest.json')})
        print('SITE READY', site, 'candidate inputs only', flush=True)
    (out / 'COMPLETE.json').write_text(json.dumps({'sites': all_receipts, 'model_jobs_submitted': False}, indent=2) + '\n')
    print('COMPLETE:', out, 'detached inputs only; NO cases or Slurm jobs', flush=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--stage14', type=Path, required=True)
    ap.add_argument('--base-csv', type=Path, required=True)
    ap.add_argument('--pft-csv', type=Path, required=True)
    ap.add_argument('--output', type=Path, required=True)
    ap.add_argument('--build', action='store_true')
    args = ap.parse_args()
    stage = load_module(args.stage14)
    sites, param = source_inputs(stage, args.base_csv, args.pft_csv)
    for site, obj in sites.items():
        print('INPUT VERIFIED', site, 'years', obj['years'], 'ZBOT baseline', obj['ZBOT'],
              'UTC', obj['tz'], 'PFT', obj['recommendation'], flush=True)
    if args.build: build(stage, args.output.expanduser().resolve(), sites, param)
    else: print('READ ONLY CHECK PASSED; --build creates detached candidates in new output directory')


if __name__ == '__main__': main()

