#!/usr/bin/env python3
"""Approved US-ICh-only repair, 28 Oct 2026. Run once, or resume data preparation.

Policy: input RH<1%, independent CDS water RH>=50%, |Tsite-Tera|<=8 C.
Keep TA, pressure, height, all other records/variables; rebuild RH/QBOT/SHUM
and any existing VPD consistently. New forcing only. Preview and validate
before a single cold-start AD400 retry; archive partial history rather than delete.
No other site is touched. A submission attempt is never automatically repeated.
"""
from __future__ import annotations
import argparse, copy, csv, gzip, hashlib, importlib.util, json, re, shutil
import sys, zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
import xml.etree.ElementTree as ET
import numpy as np
from netCDF4 import Dataset, num2date

HERE = Path(__file__).resolve().parent
SITE = 'US-ICh'
OLD_RUN, OLD_ARCH = '4741683', '4741684'
ACK = 'APPLY_APPROVED_USICH_RH1_ERA50_DT8_AND_RETRY_ONCE'
PRODUCT = 'reanalysis-era5-single-levels-timeseries'
GRID = (68.50, -149.25)
S6 = None


def need(ok, msg):
    if not ok:
        raise RuntimeError(str(msg))


def stage6():
    global S6
    if S6 is None:
        spec = importlib.util.spec_from_file_location('amf_stage06', HERE/'06_direct_AD400_ten_site_cases_and_submit.py')
        S6 = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(S6)
    return S6


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def save(path, obj):
    path = Path(path)
    tmp = path.with_suffix(path.suffix+'.tmp')
    tmp.write_text(json.dumps(obj, indent=2, default=str)+'\n')
    tmp.replace(path)


def utc():
    return datetime.now(timezone.utc).isoformat()


def arrays(ds):
    return {k: np.ma.filled(v[:], np.nan) if v.dtype.kind in 'fiu' else v[:]
            for k, v in ds.variables.items()}


def source_dates(ds, year, shift):
    """Actual Gregorian source UTC, including cyclic 2025 tail -> 2007 head."""
    tv = ds.variables['time']
    need(getattr(tv, 'calendar', '').lower() in ('noleap', '365_day'), 'forcing calendar is not NOLEAP')
    raw = num2date(tv[:], tv.units, calendar=tv.calendar)
    native = [datetime(d.year, d.month, d.day, d.hour, d.minute, d.second) for d in raw]
    need(len(native) == 17520 and all(d.year == year for d in native), f'{year}: expected 17520 same-year half hours')
    expected_time = np.arange(17520)/48 + 1/96
    need(tv.units == f'days since {year}-01-01 00:00:00' and
         np.allclose(np.asarray(tv[:]), expected_time, rtol=0, atol=1e-9),
         f'{year}: source half-hour clock differs')
    need(all(d.minute in (15, 45) for d in native), 'forcing is not UTC midpoint')
    need(shift == 18, 'expected 9-hour local-to-UTC shift')
    # Reverse Stage06's array shift using the LOCAL source calendar, then add
    # nine real Gregorian hours. Reading the artificial UTC labels alone is
    # wrong at the 2025->2007 wrap AND during the first nine hours of March 1
    # in leap years (those records originated on local Feb 28 -> UTC Feb 29).
    previous = 2025 if year == 2007 else year-1
    tail_start = datetime(previous,12,31,15,15)
    before = [tail_start+timedelta(minutes=30*i,hours=9) for i in range(shift)]
    return before+[d+timedelta(hours=9) for d in native[:-shift]]


def es_water(t):
    """Same Bolton water convention as source-workflow Stage19/60 (hPa)."""
    t = np.asarray(t, dtype=float)
    return 6.112*np.exp(17.67*t/(t+243.5))


def proposed(tk, pressure, rh, era_t, era_rh):
    tc = np.asarray(tk, float)-273.15
    p = np.asarray(pressure, float)
    old = np.asarray(rh, float)
    et, er = np.asarray(era_t, float), np.asarray(era_rh, float)
    finite = np.isfinite(tc)&np.isfinite(p)&np.isfinite(old)&np.isfinite(et)&np.isfinite(er)
    # Only a floating-point comparison tolerance at the approved 8 C boundary.
    mask = finite&(p > 0)&(old < 1)&(er >= 50)&(er <= 100.05)&(np.abs(tc-et) <= 8+1e-10)
    saturation = es_water(tc)*100
    vapor = saturation*er/100
    q = .622*vapor/(p-.378*vapor)
    vpd = (saturation-vapor)/100
    need(np.all(np.isfinite(q[mask])&(q[mask] > 0)&(q[mask] < .08)&(vpd[mask] >= 0)), 'invalid humidity candidate')
    return mask, q, vpd


def inventory(folder):
    m = json.loads((folder/'manifest.json').read_text())
    need(m.get('complete') and m.get('site') == SITE, 'source forcing manifest incomplete')
    need(m.get('utc_offset_h') == -9 and m.get('shift_records') == 18, 'source UTC/cyclic convention differs')
    records = sorted(m['files'], key=lambda r: int(r['year']))
    need([int(r['year']) for r in records] == list(range(2007, 2026)), 'source years are not 2007-2025')
    low, meta = [], []
    for r in records:
        y, f = int(r['year']), Path(r['path'])
        need(f.resolve() == (folder/f'{y}.nc').resolve() and sha(f) == r['sha256'], f'source changed: {f}')
        with Dataset(f) as ds:
            need(getattr(ds, 'utc_offset_hours', None) == -9, f'{y}: UTC offset metadata differs')
            dates = source_dates(ds, y, 18)
            a = arrays(ds)
            for k in ('RH', 'QBOT', 'SHUM', 'TBOT', 'PSRF', 'ZBOT'):
                need(k in a and a[k].shape == (17520, 1, 1), f'{y}: {k} missing/wrong shape')
                need(np.isfinite(a[k]).all(), f'{y}: nonfinite {k}')
            need(np.array_equal(a['QBOT'], a['SHUM']), f'{y}: QBOT and SHUM disagree')
            need(np.all(a['ZBOT'] == 1.93), f'{y}: unexpected ZBOT')
            need(ds.variables['TBOT'].units == 'K' and ds.variables['PSRF'].units == 'Pa', 'T/P units differ')
            for i in np.flatnonzero(a['RH'].reshape(-1) < 1):
                low.append({'file_year': y, 'index': int(i), 'source_utc': dates[i].isoformat(),
                            'RH_before': float(a['RH'][i,0,0]), 'TA_C': float(a['TBOT'][i,0,0]-273.15),
                            'PA_Pa': float(a['PSRF'][i,0,0]), 'QBOT_before': float(a['QBOT'][i,0,0]),
                            'VPD_before_hPa': float(es_water(a['TBOT'][i,0,0]-273.15)*(1-a['RH'][i,0,0]/100))})
        meta.append({'year': y, 'path': str(f), 'sha256': r['sha256']})
    need(low, 'no RH<1 records found; do not retry the model without a diagnosed change')
    return meta, low


def read_cds(nc, start, end):
    with Dataset(nc) as ds:
        need(set(('t2m','d2m','sp')).issubset(ds.variables), 'CDS variables missing')
        lat = float(np.asarray(ds.variables['latitude'][:]).ravel()[0])
        lon = float(np.asarray(ds.variables['longitude'][:]).ravel()[0])
        need(abs(lat-GRID[0]) < .001 and abs((lon-GRID[1]+180)%360-180) < .001, 'CDS grid mismatch')
        v = ds.variables['valid_time']
        dates = num2date(v[:], v.units, calendar=getattr(v, 'calendar', 'standard'))
        dates = [datetime(d.year,d.month,d.day,d.hour,d.minute,d.second) for d in dates]
        want = [start+timedelta(hours=i) for i in range(int((end-start).total_seconds()/3600)+24)]
        need(dates == want, 'CDS hourly time axis incomplete or unexpected')
        data = {}
        for k, unit in (('t2m','K'), ('d2m','K'), ('sp','Pa')):
            v = ds.variables[k]
            need(v.units == unit and v.dimensions == ('valid_time',), f'CDS {k} units/dimensions differ')
            data[k] = np.ma.filled(v[:], np.nan).astype(float)
            need(np.isfinite(data[k]).all(), f'CDS {k} contains missing values')
        t, td = data['t2m']-273.15, data['d2m']-273.15
        need(np.all((t > -90)&(t < 65)&(td > -100)&(td < 65)&(data['sp'] > 49000)&(data['sp'] < 111000)), 'CDS range check failed')
        rh = 100*es_water(td)/es_water(t)
        need(np.all((rh > 0)&(rh <= 100.05)), 'CDS water RH invalid; manual phase review required')
    epoch = datetime(1970,1,1)
    seconds = np.array([(d-epoch).total_seconds() for d in dates])
    return seconds, t, rh


def acquire(root, low):
    dates = sorted(datetime.fromisoformat(r['source_utc']) for r in low)
    start = datetime.combine(dates[0].date(), datetime.min.time())
    end = datetime.combine(dates[-1].date(), datetime.min.time())+timedelta(days=1)
    request = {'variable': ['2m_temperature','2m_dewpoint_temperature','surface_pressure'],
               'location': {'latitude': GRID[0], 'longitude': GRID[1]},
               'date': [start.date().isoformat(), end.date().isoformat()], 'data_format': 'netcdf'}
    d = root/'cds'; d.mkdir(exist_ok=True)
    rec = d/'receipt.json'; oldreq = d/'request.json'
    if oldreq.exists():
        need(json.loads(oldreq.read_text()) == request, 'cached request differs')
    else:
        save(oldreq, request)
    if rec.exists():
        r = json.loads(rec.read_text()); nc = Path(r['netcdf_path'])
        need(sha(nc) == r['netcdf_sha256'] and sha(d/'original_payload.bin') == r['payload_sha256'], 'CDS cache hash differs')
        return read_cds(nc, start, end)
    payload = d/'original_payload.bin'
    if not payload.exists():
        import cdsapi
        partial = d/'download.partial'
        if partial.exists():
            partial.rename(d/('interrupted_'+datetime.now().strftime('%Y%m%dT%H%M%S%f')+'.bin'))
        print('CDS point-timeseries request:', json.dumps(request), flush=True)
        cdsapi.Client().retrieve(PRODUCT, request, str(partial))
        partial.replace(payload)
    nc = payload
    if zipfile.is_zipfile(payload):
        with zipfile.ZipFile(payload) as z:
            names = [n for n in z.namelist() if n.lower().endswith('.nc')]
            need(len(names) == 1, f'expected one CDS NetCDF, got {names}')
            nc = d/'hourly_UTC.nc'; nc.write_bytes(z.read(names[0]))
    data = read_cds(nc, start, end)
    save(rec, {'dataset': PRODUCT, 'request': request, 'netcdf_path': str(nc),
               'netcdf_sha256': sha(nc), 'payload_sha256': sha(payload), 'verified_utc': utc()})
    return data


def decisions(low, era):
    seconds, et, er = era
    epoch = datetime(1970,1,1)
    times = np.array([(datetime.fromisoformat(r['source_utc'])-epoch).total_seconds() for r in low])
    need(times.min() >= seconds.min() and times.max() <= seconds.max(), 'CDS does not bracket requested timestamps')
    ta = np.interp(times, seconds, et)
    rh = np.interp(times, seconds, er)  # Native-hour water RH, linear to UTC midpoint (Stage19 method).
    tk = np.array([r['TA_C']+273.15 for r in low]); p = np.array([r['PA_Pa'] for r in low])
    mask, q, vpd = proposed(tk, p, [r['RH_before'] for r in low], ta, rh)
    rows = []
    for i, old in enumerate(low):
        r = dict(old, ERA_TA_C=float(ta[i]), ERA_RH_water_pct=float(rh[i]),
                 delta_T_C=float(tk[i]-273.15-ta[i]), decision='REPAIR' if mask[i] else 'RETAIN_OUTSIDE_RULE')
        if mask[i]:
            r.update(RH_after=float(rh[i]), QBOT_after=float(q[i]), VPD_after_hPa=float(vpd[i]))
        rows.append(r)
    # The diagnosed failure must be addressed before releasing a real model retry.
    need(any(r['source_utc'] == '2008-01-11T15:15:00' and r['decision'] == 'REPAIR' for r in rows),
         'known failing 2008-01-11 15:15 UTC record is not eligible; manual review required')
    return rows


def write_csv(path, rows):
    fields = list(dict.fromkeys(k for r in rows for k in r))
    with path.open('w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=fields); w.writeheader(); w.writerows(rows)


def build_forcing(root, sources, rows):
    dest = root/'forcing_UTC_midpoint_ZBOT_stage08_v1'
    manifest = dest/'manifest.json'
    if manifest.exists():
        m = json.loads(manifest.read_text())
        need(m['sources'] == sources and m['decisions_sha256'] == sha(root/'all_low_RH_decisions.csv'), 'candidate provenance changed')
        need(all(sha(r['path']) == r['sha256'] for r in m['files']), 'candidate forcing changed')
        return dest, m
    partial = root/'forcing.partial'
    if partial.exists():
        partial.rename(root/('interrupted_forcing_'+datetime.now().strftime('%Y%m%dT%H%M%S%f')))
    partial.mkdir()
    changed = []
    for source in sources:
        y, src = source['year'], Path(source['path'])
        dst = partial/f'{y}.nc'; shutil.copy2(src, dst)
        edits = [r for r in rows if r['file_year'] == y and r['decision'] == 'REPAIR']
        indices = np.array([r['index'] for r in edits], dtype=int)
        with Dataset(dst, 'r+') as ds:
            values = {'RH': 'RH_after', 'QBOT': 'QBOT_after', 'SHUM': 'QBOT_after'}
            if 'VPD' in ds.variables:
                need(ds.variables['VPD'].units in ('hPa','mb'), 'existing VPD unit differs')
                values['VPD'] = 'VPD_after_hPa'
            for k, field in values.items():
                v = ds.variables[k]; a = v[:]
                if edits:
                    a[indices,0,0] = [r[field] for r in edits]
                    v[:] = a
            ds.setncattr('stage08_reviewed_policy', 'US-ICh: RH<1; CDS water RH>=50; abs(Tsite-Tera)<=8C; retain T/P/ZBOT')
            ds.setncattr('stage08_decisions_sha256', sha(root/'all_low_RH_decisions.csv'))
        with Dataset(src) as a, Dataset(dst) as b:
            need(set(a.variables) == set(b.variables), 'variable set changed')
            for k in a.variables:
                av, bv = a.variables[k], b.variables[k]
                need(av.dimensions == bv.dimensions and av.dtype == bv.dtype, f'{y} {k}: schema changed')
                x, z = np.asarray(av[:]), np.asarray(bv[:])
                if k in values:
                    keep = np.ones(x.shape[0], bool); keep[indices] = False
                    need(np.array_equal(x[keep], z[keep], equal_nan=True), f'{y} {k}: unapproved records changed')
                    if edits:
                        need(np.allclose(z[indices,0,0], [r[values[k]] for r in edits], rtol=1e-12, atol=0), f'{y} {k}: readback differs')
                else:
                    need(np.array_equal(x, z, equal_nan=True), f'{y}: unrelated variable changed: {k}')
            need(np.array_equal(b.variables['QBOT'][:], b.variables['SHUM'][:]), 'QBOT/SHUM differ')
        need(sha(src) == source['sha256'], 'original forcing changed during repair')
        changed.append({'year': y, 'path': str(dest/dst.name), 'sha256': sha(dst), 'repaired_records': len(edits)})
    m = {'site': SITE, 'sources': sources, 'files': changed, 'years': [2007,2025],
         'decisions_sha256': sha(root/'all_low_RH_decisions.csv'), 'created_utc': utc(), 'complete': True}
    save(partial/'manifest.json', m); partial.rename(dest)
    return dest, m


def canonical(e):
    return (e.tag, tuple(sorted(e.attrib.items())), (e.text or '').strip(), tuple(canonical(k) for k in e))


def replace_paths(text, mapping):
    for old, new in mapping.items():
        need(text.count(old) == 1, f'expected one user stream occurrence: {old}')
        text = text.replace(old, new)
    return text


def expected_xml(text, mapping):
    root = ET.fromstring(text)
    for e in root.iter():
        if e.text and e.text.strip() in mapping:
            e.text = mapping[e.text.strip()]
    return canonical(root)


def stream_files(text):
    matches = [e for e in ET.fromstring(text).iter('stream_info') if e.attrib.get('name') == 'CLM_USRDAT.UNSET']
    need(len(matches) == 1, 'met stream name/count differs')
    return [(e.text or '').strip() for e in matches[0].find('datafiles')]


def guard_case():
    s = stage6(); case, run = s.case_dir(SITE), s.run_dir(SITE)
    need(s.xq(case, 'CASE') == s.name(SITE), 'case identity differs')
    starts = re.findall(r'case\.run starting (\d+)', (case/'CaseStatus').read_text())
    need(starts and starts[-1] == OLD_RUN, 'a newer model run exists; refuse duplicate retry')
    rows = s.sacct_name(s.name(SITE))
    need(any(str(r[0]) == OLD_RUN and r[2] == 'FAILED' for r in rows), 'diagnosed run is not FAILED')
    q = s.queued(s.name(SITE))
    need(all(r[0] == OLD_ARCH and r[2] == 'PENDING' for r in q), f'other jobs exist: {q}')
    need(s.latest(SITE)[1] == 0 and not list(run.glob('*.r.*.nc')), 'usable restart exists; cold-start recovery is not appropriate')
    for k, v in (('RUNDIR',str(run)), ('DOUT_S_ROOT',str(s.arch_dir(SITE))), ('RUN_TYPE','startup'),
                 ('RUN_STARTDATE','2007-01-01'), ('CONTINUE_RUN','false'), ('CLM_FORCE_COLDSTART','on'),
                 ('CLM_ACCELERATED_SPINUP','on'), ('STOP_N','5'), ('REST_N','5'), ('STOP_OPTION','nyears'),
                 ('REST_OPTION','nyears'), ('RESUBMIT','79'), ('RESUBMIT_SETS_CONTINUE_RUN','true')):
        need(s.xq(case,k).lower() == v.lower(), f'CIME {k} differs')
    t = (case/'CaseDocs/lnd_in').read_text()
    for k, v in {**s.FATES_FLAGS, 'spinup_state':'2'}.items():
        need(s.nml_get(t,k) == v, f'land {k} differs')
    surface = Path(s.nml_get(t,'fsurdat'))
    need(surface.name == 'surfdata_US-ICh_FIXNC_PFT_soil10_stage07_v2.nc', 'Stage07 soil repair not active')
    ledger = s.load(s.ledger(SITE))
    need(ledger.get('phase') == 'AD400_SUBMITTED' and str(ledger.get('first_run_job')) == OLD_RUN, 'Stage06 ledger differs')
    for k, p in (('surface',surface), ('fates_paramfile',Path(s.nml_get(t,'fates_paramfile')))):
        need(str(p) == ledger[k] and sha(p) == ledger[k+'_sha256'], f'{k} no longer matches the verified ledger')
    return case, run, ledger


def apply_and_submit(root, state, sources, fm):
    s = stage6(); case, run, ledger = guard_case()
    stack = s.stack_guard()
    mapping = {a['path']: b['path'] for a,b in zip(sources,fm['files'])}
    oldxml = (case/'CaseDocs/datm.streams.xml').read_text()
    need(stream_files(oldxml) == list(mapping), 'effective DATM files differ from audited Stage06 files')
    oldtext = (case/'user_nl_datm_streams').read_text()
    newtext = replace_paths(oldtext, mapping)
    backup = root/'case_backup'
    need(not backup.exists(), 'case backup already exists; inspect attempt state before retry')
    backup.mkdir()
    rels = ['env_run.xml','env_case.xml','LockedFiles/env_case.xml','user_nl_datm_streams','user_nl_clm',
            'CaseDocs/lnd_in','CaseDocs/datm.streams.xml','CaseDocs/datm_in',
            f'run.{s.name(SITE)}.out', f'run.{s.name(SITE)}.err']
    for rel in rels:
        f = case/rel
        if f.is_file():
            (backup/'case'/rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(f, backup/'case'/rel)
    for rel in ('lnd_in','datm.streams.xml','datm_in'):
        if (run/rel).is_file():
            (backup/'run').mkdir(exist_ok=True); shutil.copy2(run/rel, backup/'run'/rel)
    s.save(backup/'stage06_ledger.json', ledger)
    s.save(root/'state.json', dict(state, phase='CASE_CHANGE_ATTEMPTED_UNCERTAIN', at=utc()))
    env, lock = case/'env_case.xml', case/'LockedFiles/env_case.xml'
    original = env.read_bytes()
    need(original == lock.read_bytes(), 'env_case lock differs before preview')
    (case/'user_nl_datm_streams').write_text(newtext)
    try:
        try:
            s.xc(case,'COMP_ROOT_DIR_LND',str(s.OVERLAY))
            print(s.cmd([case/'preview_namelists'],cwd=case,timeout=650), flush=True)
        finally:
            s.xc(case,'COMP_ROOT_DIR_LND','$SRCROOT')
        need(env.read_bytes() == original and lock.read_bytes() == original, 'env_case lock not restored')
        clean = lambda text: '\n'.join(line.split('!',1)[0].strip() for line in text.splitlines() if line.split('!',1)[0].strip())
        oldland = (backup/'case/CaseDocs/lnd_in').read_text()
        need(clean((case/'CaseDocs/lnd_in').read_text()) == clean(oldland), 'land namelist changed during met-only repair')
        need(sha(case/'CaseDocs/lnd_in') == sha(run/'lnd_in'), 'runtime lnd_in differs from preview')
        for p in (case/'CaseDocs/datm.streams.xml', run/'datm.streams.xml'):
            need(canonical(ET.fromstring(p.read_text())) == expected_xml(oldxml,mapping), f'other stream content changed: {p}')
        for src in sources:
            need(sha(src['path']) == src['sha256'], 'original forcing changed')
        need(all(sha(r['path']) == r['sha256'] for r in fm['files']), 'candidate forcing changed')
        # Recheck scheduler and case configuration after a potentially long preview.
        guard_case()
    except Exception:
        # No model submission or history movement has happened. Restore the
        # captured case/runtime files so a failed preview cannot activate inputs.
        for src in (backup/'case').rglob('*'):
            if src.is_file(): shutil.copy2(src, case/src.relative_to(backup/'case'))
        for src in (backup/'run').glob('*'):
            shutil.copy2(src, run/src.name)
        s.save(root/'state.json', dict(state,phase='CASE_CHANGE_FAILED_RESTORED',at=utc()))
        raise
    # Failed first segment has no restart; preserve all partial history for audit
    # before restarting from 2007, so history files are not silently overwritten.
    hist = backup/'partial_history'; hist.mkdir()
    for f in sorted(run.glob(s.name(SITE)+'.*.h*.nc')):
        shutil.move(str(f), str(hist/f.name))
    queued = s.queued(s.name(SITE))
    need(all(r[0] == OLD_ARCH and r[2] == 'PENDING' for r in queued), f'queue changed: {queued}')
    if queued:
        s.cmd(['scancel',OLD_ARCH])
    need(not s.queued(s.name(SITE)), 'old archive still queued; retry has NOT been submitted')
    attempt = dict(state, phase='SUBMIT_ATTEMPTED_UNCERTAIN', at=utc(), stack=stack,
                   original_failed_run=OLD_RUN, original_failed_archive=OLD_ARCH,
                   forcing_manifest=str(Path(fm['files'][0]['path']).parent/'manifest.json'))
    s.save(root/'state.json', attempt)  # Never automatically retry beyond this boundary.
    out = s.cmd([case/'case.submit','--skip-preview-namelist'],cwd=case,timeout=650)
    print(out, flush=True)
    rid, aid = s.RUN_RE.search(out), s.ARCH_RE.search(out)
    need(rid and aid, 'submission IDs unclear; DO NOT run again; inspect squeue')
    attempt.update(phase='SUBMITTED',run_job=rid.group(1),archive_job=aid.group(1),submit_output=out)
    s.save(root/'state.json', attempt)
    ledger.setdefault('history',[]).append({k:ledger.get(k) for k in ('phase','first_run_job','first_archive_job','forcing_manifest','lnd_in_sha256')})
    ledger.update(first_run_job=rid.group(1),first_archive_job=aid.group(1),forcing_manifest=attempt['forcing_manifest'],
                  stage08_state=str(root/'state.json'),stage08_policy='RH<1; ERAwaterRH>=50; absDT<=8; keepTA_PA_ZBOT',
                  lnd_in_sha256=sha(case/'CaseDocs/lnd_in'),datm_streams_sha256=sha(case/'CaseDocs/datm.streams.xml'))
    s.save(s.ledger(SITE),ledger)
    print('US-ICh REPAIR SUBMITTED run='+rid.group(1)+' archive='+aid.group(1)+' AD400 2007->2407 (80x5)',flush=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('action',choices=('run','status'))
    ap.add_argument('--confirm',default='')
    a = ap.parse_args()
    s = stage6(); root = s.EXP/'Stage08_USICh_reviewed_humidity'
    statefile = root/'state.json'
    state = json.loads(statefile.read_text()) if statefile.exists() else {}
    if a.action == 'status':
        print(json.dumps(state,indent=2)); return
    need(a.confirm == ACK, 'requires --confirm '+ACK)
    if state.get('phase') == 'SUBMITTED':
        print('ALREADY SUBMITTED; no new job. run=',state.get('run_job'),'archive=',state.get('archive_job')); return
    need(state.get('phase') in (None,'DATA_PREPARATION','FORCING_BUILT'),
         'previous case/submission attempt requires inspection; refusing automatic retry: '+str(state.get('phase')))
    guard_case()
    root.mkdir(parents=True,exist_ok=True)
    # Atomic directory lock prevents concurrent invocations and duplicate CDS or model work.
    lock = root/'active.lock'
    lock.mkdir()  # An interrupted run leaves this for explicit inspection/removal.
    try:
        state.update(phase='DATA_PREPARATION',policy_approved_utc='2026-10-28',script_sha256=sha(__file__))
        save(statefile,state)
        sources, low = inventory(s.forcing_dir(SITE))
        save(root/'source_inventory.json', {'sources':sources,'low_RH_records':len(low)})
        print('19-year scan:',len(low),'RH<1 records; source SHA PASS',flush=True)
        era = acquire(root,low)
        rows = decisions(low,era)
        write_csv(root/'all_low_RH_decisions.csv',rows)
        repairs = sum(r['decision']=='REPAIR' for r in rows)
        print('Approved repairs:',repairs,'; retained outside rule:',len(rows)-repairs,flush=True)
        _,fm = build_forcing(root,sources,rows)
        state.update(phase='FORCING_BUILT',repairs=repairs,retained_low_RH=len(rows)-repairs)
        save(statefile,state)
        apply_and_submit(root,state,sources,fm)
    finally:
        lock.rmdir()


if __name__ == '__main__':
    main()
