#!/usr/bin/env python3
"""Build two detached annual DE-Gri DATM sensitivities from approved CSV.

Inputs must have the verified Stage03B/Stage30 provenance and the 11+23
operator-approved edits. No existing DATM, case, forcing or Slurm is changed.
"""
import argparse
import csv
import hashlib
import json
import os
import shutil
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
from netCDF4 import Dataset, date2num

STARTS = {2011: datetime(2011, 6, 13, 7), 2024: datetime(2024, 7, 4, 5)}
COUNTS = {2011: 11, 2024: 23}
REQUIRED = {'time', 'TBOT', 'QBOT', 'PSRF', 'FSDS', 'FLDS', 'WIND', 'PRECTmms', 'ZBOT'}


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda: f.read(1024 * 1024), b''):
            h.update(b)
    return h.hexdigest()


def load_json(path):
    return json.loads(path.read_text(encoding='utf-8'))


def index_for(nc, stamp):
    coord = nc.variables['time']
    if len(coord) != 17520 or getattr(coord, 'calendar', None) not in ('noleap', '365_day'):
        raise ValueError('Annual DATM time axis must have 17520 no-leap points')
    wanted = float(date2num(stamp, units=coord.units, calendar=coord.calendar))
    times = np.asarray(coord[:], dtype=np.float64)
    hits = np.flatnonzero(np.isclose(times, wanted, rtol=0, atol=1e-9))
    if len(hits) != 1:
        raise ValueError('Target time absent or duplicated in DATM: ' + str(stamp))
    return int(hits[0])


def check_close(got, expected, label, tolerance):
    if not np.isfinite(got) or not np.isfinite(expected) or abs(float(got)-float(expected)) > tolerance:
        raise ValueError('DATM/CSV baseline mismatch for ' + label)


def make_annual(original, temporary, year, rows, base_hash, csv_hash):
    """Copy an annual file, verify baseline and logical changes, preserve ZBOT."""
    if temporary.exists():
        raise ValueError('Candidate already exists')
    with original.open('rb') as src, temporary.open('xb') as dst:
        shutil.copyfileobj(src, dst, 1024*1024)
    expected = {}
    with Dataset(original, 'r') as old, Dataset(temporary, 'r+') as new:
        if not REQUIRED.issubset(old.variables) or set(old.variables) != set(new.variables):
            raise ValueError('Original annual DATM variables missing or copied incorrectly')
        if getattr(old, 'site', None) != 'DE-Gri' or int(getattr(old, 'forcing_year', -1)) != year:
            raise ValueError('Annual DATM site/year mismatch')
        if old.variables['TBOT'].shape != (17520, 1, 1) or old.variables['QBOT'].shape != (17520, 1, 1):
            raise ValueError('Unexpected annual DATM geometry')
        for row in rows:
            stamp = datetime.fromisoformat(row['time'])
            i = index_for(old, stamp)
            check_close(old.variables['TBOT'][i, 0, 0], row['baseline_TBOT'], 'TBOT '+str(stamp), 3e-5)
            check_close(old.variables['QBOT'][i, 0, 0], row['baseline_QBOT'], 'QBOT '+str(stamp), 1e-8)
            check_close(old.variables['PSRF'][i, 0, 0], row['PSRF'], 'PSRF '+str(stamp), 0.02)
            expected[i] = row
            if year == 2011:
                new.variables['TBOT'][i, 0, 0] = row['candidate_TBOT']
            new.variables['QBOT'][i, 0, 0] = row['candidate_QBOT']
        if len(expected) != COUNTS[year]:
            raise ValueError('Expected exact number of unique changes')
        new.provenance_status = 'DETACHED_SENSITIVITY_NOT_SCIENCE_RELEASED'
        new.sensitivity_base_nc_sha256 = base_hash
        new.sensitivity_candidate_csv_sha256 = csv_hash
        new.sensitivity_description = '2011 approved TA+VPD' if year == 2011 else '2024 approved VPD, TA retained'
    # Compare the full arrays of every original variable, not just samples.
    with Dataset(original, 'r') as old, Dataset(temporary, 'r') as new:
        if set(old.variables) != set(new.variables):
            raise ValueError('Candidate variable list changed')
        for name in old.variables:
            before = np.ma.asarray(old.variables[name][:])
            after = np.ma.asarray(new.variables[name][:])
            if name not in ('TBOT', 'QBOT'):
                if not np.ma.allequal(before, after):
                    raise ValueError('Unexpected DATM variable change: '+name)
                continue
            expected_array = before.copy()
            if name == 'QBOT' or year == 2011:
                for i, row in expected.items():
                    expected_array[i, 0, 0] = row['candidate_'+name]
            if not np.ma.allequal(expected_array, after):
                raise ValueError('DATM target or outside-target values mismatch: '+name)
    if digest(original) != base_hash:
        raise ValueError('Original annual file changed during candidate creation')


def read_candidate_rows(path, manifest):
    plans = {}
    by_year = {2011: manifest.get('prior_2011_edits', []), 2024: manifest.get('approved_2024_edits', [])}
    for year, edits in by_year.items():
        times = {str(STARTS[year] + timedelta(minutes=30*i)) for i in range(COUNTS[year])}
        if len(edits) != COUNTS[year] or {x['time'] for x in edits} != times:
            raise ValueError('Approved target scope mismatch for '+str(year))
        plans.update({x['time']: (year, x) for x in edits})
    result = {2011: [], 2024: []}
    with path.open(encoding='utf-8-sig', newline='') as f:
        reader = csv.DictReader(f)
        if not {'time', 'TA_USE', 'VPD_USE', 'TBOT', 'QBOT', 'PSRF'}.issubset(reader.fieldnames or []):
            raise ValueError('Combined sensitivity CSV columns missing')
        seen = set()
        for row in reader:
            time = row['time']
            if time not in plans:
                continue
            if time in seen:
                raise ValueError('Duplicate CSV edit timestamp')
            seen.add(time)
            year, edit = plans[time]
            after = edit['after']
            check_close(float(row['QBOT']), float(after['QBOT']), 'CSV candidate QBOT', 1e-12)
            check_close(float(row['VPD_USE']), float(after['VPD_USE']), 'CSV candidate VPD', 1e-10)
            if year == 2011:
                check_close(float(row['TBOT']), float(after['TBOT']), 'CSV candidate TBOT', 1e-8)
                check_close(float(row['TA_USE']), float(after['TA_USE']), 'CSV candidate TA', 1e-8)
                old_t = float(edit['before']['TBOT'])
            else:
                old_t = float(edit['TA_C_unchanged']) + 273.15
                check_close(float(row['TBOT']), old_t, 'CSV retained TBOT', 1e-8)
                check_close(float(row['TA_USE']), float(edit['TA_C_unchanged']), 'CSV retained TA', 1e-8)
            result[year].append({'time':time, 'baseline_TBOT':old_t, 'baseline_QBOT':float(edit['before']['QBOT']),
                                 'candidate_TBOT':float(row['TBOT']), 'candidate_QBOT':float(row['QBOT']), 'PSRF':float(row['PSRF'])})
    if seen != set(plans):
        raise ValueError('Candidate CSV lacks one or more approved times')
    return result


def locate_annual(b, year):
    sites = [x for x in b['sites'] if x.get('site') == 'DE-Gri']
    if len(sites) != 1 or sites[0].get('all_current_paths_match_historical') is not True:
        raise ValueError('Stage03B DE-Gri path lineage not verified')
    site = sites[0]
    matches = [x for x in site['yearly_path_comparisons'] if int(x['year']) == year]
    if len(matches) != 1 or matches[0].get('literal_path_equal') is not True:
        raise ValueError('Annual file lineage missing')
    annual = Path(matches[0]['current'])
    with Path(site['historical_DATM_manifest']).open(encoding='utf-8-sig', newline='') as f:
        manifest_rows = [x for x in csv.DictReader(f) if x.get('site') == 'DE-Gri' and x.get('year') == str(year)]
    if len(manifest_rows) != 1 or manifest_rows[0].get('datm_nc') != str(annual):
        raise ValueError('Historical DATM manifest mismatch')
    expected = manifest_rows[0].get('sha256', '')
    if len(expected) != 64 or digest(annual) != expected:
        raise ValueError('Annual DATM SHA mismatch')
    return annual, expected


def self_test(root):
    with tempfile.TemporaryDirectory(dir=root) as d:
        d = Path(d); orig = d/'base.nc'; dest = d/'candidate.nc'
        with Dataset(orig, 'w', format='NETCDF4_CLASSIC') as nc:
            nc.createDimension('time',17520); nc.createDimension('lat',1); nc.createDimension('lon',1)
            t=nc.createVariable('time','f8',('time',)); t.units='days since 2011-01-01 00:00:00'; t.calendar='noleap'; t[:]=np.arange(17520)/48
            for name in sorted(REQUIRED-{'time'}):
                v=nc.createVariable(name,'f8' if name=='ZBOT' else 'f4',('time','lat','lon'))
                v[:]= 290.0 if name=='TBOT' else .01 if name=='QBOT' else 97000 if name=='PSRF' else 3
            nc.site='DE-Gri'; nc.forcing_year=2011; nc.provenance_status='BASE'
        rows=[{'time':str(STARTS[2011]+timedelta(minutes=30*i)), 'baseline_TBOT':290., 'baseline_QBOT':.01,
               'candidate_TBOT':285.+i*.1,'candidate_QBOT':.007+i*.0001,'PSRF':97000.} for i in range(11)]
        before=digest(orig)
        make_annual(orig,dest,2011,rows,before,'1'*64)
        if digest(orig)!=before: raise ValueError('Self-test altered original')
        with Dataset(dest) as n:
            i=index_for(n,STARTS[2011]); check_close(n.variables['TBOT'][i,0,0],285.,'self test',1e-5)
            check_close(n.variables['ZBOT'][i,0,0],3.,'self test ZBOT',1e-8)
        bad = [dict(x) for x in rows]; bad[0]['baseline_TBOT']=100
        try: make_annual(orig,d/'bad.nc',2011,bad,before,'1'*64)
        except ValueError: pass
        else: raise ValueError('Self-test failed to reject changed baseline')
        orig24=d/'base24.nc'; dest24=d/'candidate24.nc'
        with Dataset(orig24,'w',format='NETCDF4_CLASSIC') as nc:
            nc.createDimension('time',17520); nc.createDimension('lat',1); nc.createDimension('lon',1)
            t=nc.createVariable('time','f8',('time',)); t.units='days since 2024-01-01 00:00:00'; t.calendar='noleap'; t[:]=np.arange(17520)/48
            for name in sorted(REQUIRED-{'time'}):
                v=nc.createVariable(name,'f8' if name=='ZBOT' else 'f4',('time','lat','lon'))
                v[:]=290.0 if name=='TBOT' else .01 if name=='QBOT' else 97000 if name=='PSRF' else 3
            nc.site='DE-Gri'; nc.forcing_year=2024
        rows24=[{'time':str(STARTS[2024]+timedelta(minutes=30*i)), 'baseline_TBOT':290., 'baseline_QBOT':.01,
                 'candidate_TBOT':290., 'candidate_QBOT':.007+i*.00001,'PSRF':97000.} for i in range(23)]
        make_annual(orig24,dest24,2024,rows24,digest(orig24),'2'*64)
        with Dataset(dest24) as n:
            i=index_for(n,STARTS[2024])
            expected=((STARTS[2024]-datetime(2024,1,1)).days-1)*48+10
            if i != expected: raise ValueError('Leap-year noleap index mismatch')
            check_close(n.variables['TBOT'][i,0,0],290.,'self test 2024 TBOT',1e-5)
    print('SELF-TEST PASS | 2011 and 2024 no-leap indexing, variable preservation and mismatch guard')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--self-test',action='store_true')
    p.add_argument('--test-dir',type=Path)
    p.add_argument('--stage03b',type=Path)
    p.add_argument('--combined-dir',type=Path)
    p.add_argument('--out-dir',type=Path)
    a=p.parse_args()
    if a.self_test:
        if a.test_dir is None or not a.test_dir.is_dir(): p.error('--test-dir required')
        self_test(a.test_dir); return
    if a.stage03b is None or a.combined_dir is None or a.out_dir is None:
        p.error('Stage03B, combined-dir and out-dir required')
    if not a.out_dir.is_dir() or a.out_dir.is_symlink() or any(a.out_dir.iterdir()):
        raise ValueError('Output must be an existing empty private directory')
    b=load_json(a.stage03b)
    if b.get('stage') != 'STAGE03B_BATCH04_REUSE_FLUXNET13_STAGE28_STAGE29B_30_SOURCE_LINEAGE' or b.get('read_only') is not True or b.get('science_release') is not False:
        raise ValueError('Expected readonly Stage03B science HOLD report')
    m=load_json(a.combined_dir/'manifest_PRIVATE.json')
    if m.get('candidate_kind') != '2011_2024_DETACHED_CSV_ONLY_NOT_DATM' or m.get('model_input_approved') is not False:
        raise ValueError('Expected combined approved CSV sensitivity manifest')
    gri_sites=[x for x in b['sites'] if x.get('site') == 'DE-Gri']
    if len(gri_sites) != 1 or gri_sites[0].get('stage28_met_SHA_verified') is not True or gri_sites[0].get('stage28_met_SHA_expected') != m.get('baseline_sha256'):
        raise ValueError('Candidate does not derive from verified Stage28 baseline')
    candidate=a.combined_dir/'DE-Gri_2011_2024_approved_sensitivity.csv'
    csv_hash=digest(candidate)
    if csv_hash != m.get('candidate_sha256'):
        raise ValueError('Combined candidate CSV hash mismatch')
    rows=read_candidate_rows(candidate,m)
    files={year:locate_annual(b,year) for year in (2011,2024)}
    temp=[]; results=[]
    try:
        for year in (2011,2024):
            original, old_hash=files[year]
            partial=a.out_dir/f'DE-Gri_{year}_approved_sensitivity.partial.nc'
            final=a.out_dir/f'DE-Gri_{year}_approved_sensitivity.nc'
            temp.append(partial)
            make_annual(original,partial,year,rows[year],old_hash,csv_hash)
            results.append({'year':year,'baseline_path':str(original),'baseline_sha256':old_hash,
                            'candidate_path':str(final),'candidate_sha256':digest(partial),
                            'edits':len(rows[year]),'logical_all_variables_verified':True})
        if digest(candidate) != csv_hash:
            raise ValueError('Candidate CSV changed during conversion')
        report={'site':'DE-Gri','status':'DETACHED_SENSITIVITY_NOT_RELEASED','source_csv_sha256':csv_hash,
                'time_alignment_verified_from_stage29b_noleap_coordinate':True,'observational_time_alignment_proved':False,
                'case_or_slurm_modified':False,'annual_files':results}
        with (a.out_dir/'manifest_PRIVATE.json').open('x',encoding='utf-8') as f:
            json.dump(report,f,indent=2);f.write('\n')
        for year, partial in zip((2011,2024),temp):
            os.replace(partial,a.out_dir/f'DE-Gri_{year}_approved_sensitivity.nc')
    except BaseException:
        for path in temp:path.unlink(missing_ok=True)
        raise
    for x in results: print('DATM CANDIDATE VERIFIED',json.dumps(x,separators=(',',':')))
    print('COMPLETE 2 annual DATM sensitivities | no cases or Slurm changed |',a.out_dir)


if __name__=='__main__': main()
