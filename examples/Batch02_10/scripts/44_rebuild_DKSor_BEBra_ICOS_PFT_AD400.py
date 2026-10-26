#!/usr/bin/env python3
"""Batch02 Stage44: rebuild DK-Sor and BE-Bra with ICOS-basal-area PFT, delete old outputs, AD400 80x5.

Evidence (ICOS ETC ancillary reports, tree basal area by species, 26 Oct 2026):
  DK-Sor  Fagus sylvatica 98.9% (CP 2023), 100% (SP 2021)      -> DBF 100       host {7:100}
  BE-Bra  Pinus sylvestris 85.2% (CP 2023), 82.1% (SP 2020)    -> ENF 84/DBF 16 host {1:84, 7:16}
Register: CLM-FATES-single-site-workflows ICOS_PFT/FINAL_38_SITE_FIXNC_PFT_20261026_ICOS.csv.
FR-FBn keeps its running Stage43 case (ENF 75 / EBF 25 is inside the ICOS CP-SP range).

The template for each new case is the Stage43 history-fixed case (FATES_GPP/FATES_NPP history,
verified meteorology selection, private FATES AD overlay, same executable). Only the surface
changes, plus (DK-Sor, optional) the annual forcing files when --forcing-dir is given.

Actions
  self-test
  inventory                  READ ONLY: template config, every forcing file per year (records,
                             missing/fill values, means), candidate forcing folders, the exact
                             old B02 case/run/archive folders that purge-old would delete
  prepare --confirm PREPARE_STAGE44_ICOS_PFT_CASES_NO_SLURM [--sites ..]
          [--forcing-dir DK-Sor=/path/to/annual_nc] [--co2 DK-Sor=361.93]
                             new surface + new case + preview + validate; no Slurm
  purge-old --confirm DELETE_OLD_B02_DKSOR_BEBRA_CASES_AND_OUTPUTS --sites ..
                             permanently delete the listed old cases and outputs (only after the
                             new case for that site is verified; refuses if any job is queued)
  submit --confirm SUBMIT_STAGE44_ICOS_PFT_AD400_80x5_ONCE [--sites ..]
  status / audit-first5      READ ONLY
"""
import argparse, configparser, getpass, hashlib, json, os, re, resource, shutil, subprocess, sys
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

BASE = Path('/iridisfs/scratch/ly3n24/CLM_FATES')
OUTPUT = Path('/scratch/ly3n24/CTSM_FATES_OUTPUTS')
EXPERIMENT = BASE / 'experiments/NonCompetitionObserved22/Batch02_10'
CTSM = BASE / 'CTSM'
OVERLAY = EXPERIMENT / '_private_ctsm_FATES_AD5_namelist_overlay_v1'
D44 = EXPERIMENT / 'stage44_ICOS_PFT_rebuild'
SITE_SRC = BASE / 'sites/MY_EC_SITE'
AFTER = ['TOTSOMC', 'TOTSOMN', 'TLAI', 'FATES_GPP', 'FATES_NPP', 'TWS', 'H2OSNO']
SITES = {
    'DK-Sor': dict(template='DK-Sor_B02_FIXNC_FOREST_GPPNPP_HISTFIX_AD400', new='DK-Sor_B02_FIXNC_ICOS_DBF100_AD400',
                   tag='ICOS_DBF100', host={7: 100.0}, old_hosts={1, 3, 7}),
    'BE-Bra': dict(template='BE-Bra_B02_FIXNC_MET34_GPPNPP_HISTFIX_AD400', new='BE-Bra_B02_FIXNC_ICOS_ENF84_DBF16_AD400',
                   tag='ICOS_ENF84_DBF16', host={1: 84.0, 7: 16.0}, old_hosts={1, 7}),
}
ACK_PREP = 'PREPARE_STAGE44_ICOS_PFT_CASES_NO_SLURM'
ACK_PURGE = 'DELETE_OLD_B02_DKSOR_BEBRA_CASES_AND_OUTPUTS'
ACK_SUB = 'SUBMIT_STAGE44_ICOS_PFT_AD400_80x5_ONCE'
FATES = {'use_fates': '.true.', 'use_fates_sp': '.false.', 'use_fates_fixed_biogeog': '.true.',
         'use_fates_nocomp': '.true.', 'use_cn': '.false.', 'spinup_state': '2'}
YEAR_RE = re.compile(r'(?<!\d)(19[5-9]\d|20[0-4]\d)(?!\d)')


def need(ok, why):
    if not ok: raise RuntimeError(str(why))


def call(args, cwd=None, timeout=300):
    p = subprocess.run([str(a) for a in args], cwd=cwd, text=True, capture_output=True, timeout=timeout)
    need(p.returncode == 0, 'COMMAND FAILED ' + ' '.join(map(str, args)) + '\n' + (p.stdout + p.stderr)[-3000:])
    return p.stdout.strip()


def query(case, k): return call([Path(case) / 'xmlquery', k, '--value'], cwd=case)
def change(case, k, v): call([Path(case) / 'xmlchange', f'{k}={v}'], cwd=case)
def utc(): return datetime.now(timezone.utc).isoformat()


def digest(p):
    h = hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''): h.update(b)
    return h.hexdigest()


def nml(text, key):
    hits = re.findall(r'(?im)^\s*' + re.escape(key) + r'\s*=\s*([^\r\n!]*)', text)
    need(len(hits) <= 1, 'duplicate namelist key ' + key)
    return hits[0].strip().rstrip(',').strip().strip("'\"").strip() if hits else None


def nml_pairs(text):
    out = {}
    for ln in text.splitlines():
        s = ln.strip()
        if not s or s.startswith(('!', '&', '/')): continue
        m = re.match(r'([A-Za-z_]\w*)\s*=\s*(.*)$', s)
        if m: out[m.group(1).lower()] = m.group(2).strip().rstrip(',')
    return out


def nml_set(text, key, val):
    pat = r'(?im)^[ \t]*' + re.escape(key) + r'[ \t]*=[^\r\n]*$'
    hits = list(re.finditer(pat, text))
    need(len(hits) <= 1, 'duplicate user_nl key ' + key)
    line = f'{key} = {val}'
    return text[:hits[0].start()] + line + text[hits[0].end():] if hits else text.rstrip() + '\n' + line + '\n'


def hist_fields(text):
    m = re.search(r"(?ims)^[ \t]*hist_fincl1[ \t]*=[ \t]*(.*?)(?=^[ \t]*[A-Za-z_]\w*[ \t]*=|^[ \t]*/[ \t]*$|\Z)", text)
    return re.findall(r"['\"]([^'\"]+)['\"]", m.group(1)) if m else []


def load(p): return json.loads(Path(p).read_text()) if Path(p).is_file() else {}
def save(p, obj):
    Path(p).parent.mkdir(parents=True, exist_ok=True)
    t = Path(str(p) + '.tmp'); t.write_text(json.dumps(obj, indent=2, default=str) + '\n'); t.replace(p)


def P(site):
    c = SITES[site]
    return dict(site=site, tpl=BASE / 'cases' / c['template'], new=BASE / 'cases' / c['new'], name=c['new'],
                run=OUTPUT / c['new'] / 'run', arch=OUTPUT / 'archive' / c['new'],
                surf=D44 / site / f"surfdata_{site}_B02_{c['tag']}_v1.nc", ledger=D44 / f'{site}_state.json')


def queue_names():
    out = call(['squeue', '-h', '-u', getpass.getuser(), '-o', '%i|%j|%T'], timeout=60)
    return [ln.split('|') for ln in out.splitlines() if ln.count('|') == 2]


def queued_for(names):
    want = {f'{a}.{n}' for n in names for a in ('run', 'st_archive')}
    return [r for r in queue_names() if r[1] in want]


# ------------------------------------------------------------------ streams / forcing
def stream_block(xml_path):
    root = ET.parse(xml_path).getroot()
    blocks = [b for b in root.iter('stream_info') if b.get('name') == 'CLM_USRDAT.UNSET']
    need(len(blocks) == 1, f'{xml_path}: expected one CLM_USRDAT.UNSET stream')
    b = blocks[0]
    files = [Path((x.text or '').strip()) for x in b.find('datafiles')]
    dv = [(x.text or '').split()[0] for x in b.find('datavars') if (x.text or '').split()]
    return root, b, files, dv, int(b.findtext('year_first')), int(b.findtext('year_last'))


def year_stats(path, varnames):
    from netCDF4 import Dataset
    st = {'file': str(path), 'bytes': path.stat().st_size}
    with Dataset(str(path)) as ds:
        t = ds.variables['time']
        st['records'] = int(np.asarray(t[:]).size)
        st['time_units'] = getattr(t, 'units', '')
        st['calendar'] = getattr(t, 'calendar', '')
        miss = []
        for v in varnames:
            if v not in ds.variables:
                miss.append(v); continue
            a = np.ma.filled(np.ma.asarray(ds.variables[v][:], dtype=float), np.nan).ravel()
            bad = ~np.isfinite(a) | (np.abs(a) > 1e20)
            st[f'{v}_bad'] = int(bad.sum())
            ok = a[~bad]
            st[f'{v}_mean'] = float(ok.mean()) if ok.size else None
            if ok.size > 2: st[f'{v}_maxrun_const'] = int(max_run(ok))
        st['missing_vars'] = miss
    return st


def max_run(a):
    best = cur = 1
    for i in range(1, a.size):
        cur = cur + 1 if a[i] == a[i - 1] else 1
        best = max(best, cur)
    return best


def forcing_dir_files(d, first=None, last=None):
    d = Path(d); need(d.is_dir(), f'forcing dir missing: {d}')
    by = {}
    for f in sorted(d.glob('*.nc')):
        ys = YEAR_RE.findall(f.name)
        if len(ys) == 1: by.setdefault(int(ys[0]), []).append(f)
    need(by, f'{d}: no annual NC files with a single year in the name')
    dup = {y: v for y, v in by.items() if len(v) > 1}
    need(not dup, f'{d}: several files per year {list(dup)[:3]}')
    years = sorted(by)
    if first is not None: years = [y for y in years if first <= y <= last]
    need(years == list(range(years[0], years[-1] + 1)), f'{d}: years not contiguous {years[:3]}..{years[-3:]}')
    return [by[y][0] for y in years], years[0], years[-1]


def check_forcing(files, varnames, ref_records):
    rows = []
    for f in files:
        s = year_stats(f, varnames)
        need(not s['missing_vars'], f'{f}: missing stream variables {s["missing_vars"]}')
        need(s['records'] in ref_records, f'{f}: {s["records"]} records, template files have {sorted(ref_records)}')
        bad = {k: v for k, v in s.items() if k.endswith('_bad') and v}
        need(not bad, f'{f}: missing/fill values {bad}')
        rows.append(s)
    return rows


def candidate_forcing_dirs(site):
    roots = [SITE_SRC / site, EXPERIMENT]
    out = []
    for r in roots:
        if not r.is_dir(): continue
        for d, _, fs in os.walk(r):
            if site not in d and r == EXPERIMENT: continue
            ncs = [f for f in fs if f.endswith('.nc') and len(YEAR_RE.findall(f)) == 1]
            if len(ncs) >= 5:
                ys = sorted(int(YEAR_RE.findall(f)[0]) for f in ncs)
                out.append((d, len(ncs), ys[0], ys[-1]))
    return out


def old_dirs(site, keep_template=False):
    """Every Batch02 case/run/archive folder of this site except the new Stage44 one
    (and, before the new case is verified, except the Stage43 template case folder)."""
    keep = SITES[site]['new']
    tpl_case = BASE / 'cases' / SITES[site]['template']
    names = sorted({p.name for p in (BASE / 'cases').glob(f'{site}_B02_*') if p.name != keep} |
                   {p.name for p in OUTPUT.glob(f'{site}_B02_*') if p.name != keep} |
                   {p.name for p in (OUTPUT / 'archive').glob(f'{site}_B02_*') if p.name != keep})
    dirs = []
    for n in names:
        for p in (BASE / 'cases' / n, OUTPUT / n, OUTPUT / 'archive' / n):
            if p.exists() and not p.is_symlink() and not (keep_template and p == tpl_case): dirs.append(p)
    return names, dirs


def du(p):
    try: return call(['du', '-sh', str(p)], timeout=300).split()[0]
    except Exception: return '?'


# ------------------------------------------------------------------ surface
def build_surface(site, src, dst):
    from netCDF4 import Dataset
    c = SITES[site]
    with Dataset(str(src)) as ds:
        pft = np.ma.filled(ds.variables['PCT_NAT_PFT'][:], np.nan).ravel()
        nat = float(np.asarray(ds.variables['PCT_NATVEG'][:]).ravel()[0])
    nz = {i for i, v in enumerate(pft) if v > 1e-6}
    need(pft.size == 15 and abs(nat - 100) < 1e-3, f'{site}: template surface not NATVEG100 natpft15')
    need(nz <= c['old_hosts'], f'{site}: template surface hosts {sorted(nz)} not in {sorted(c["old_hosts"])}')
    want = np.array([c['host'].get(i, 0.0) for i in range(15)])
    if dst.is_file():
        rec = load(str(dst) + '.json')
        need(rec.get('sha256') == digest(dst) and rec.get('source_sha256') == digest(src), f'{site}: existing new surface differs; move aside')
        with Dataset(str(dst)) as ds:
            need(np.allclose(np.ma.filled(ds.variables['PCT_NAT_PFT'][:], np.nan).ravel(), want, atol=1e-6), f'{site}: existing surface PFT wrong')
        print(f'  {site}: surface reused {dst}', flush=True)
        return dst
    dst.parent.mkdir(parents=True, exist_ok=True)
    tmp = Path(str(dst) + '.partial'); shutil.copyfile(src, tmp)
    with Dataset(str(tmp), 'r+') as ds:
        v = ds.variables['PCT_NAT_PFT']; v[:] = want.reshape(v.shape)
        ds.setncattr('stage44_PFT', f"{site} ICOS ETC basal area: host PCT_NAT_PFT {c['host']}")
    with Dataset(str(tmp)) as ds:
        got = np.ma.filled(ds.variables['PCT_NAT_PFT'][:], np.nan).ravel()
        need(np.allclose(got, want, atol=1e-6), f'{site}: surface write failed')
        for k in ('PCT_SAND', 'PCT_CLAY', 'PCT_NATVEG', 'LATIXY', 'LONGXY'):
            with Dataset(str(src)) as s0:
                need(np.array_equal(np.ma.filled(s0.variables[k][:], -1), np.ma.filled(ds.variables[k][:], -1)), f'{site}: {k} changed')
    tmp.rename(dst)
    save(str(dst) + '.json', {'site': site, 'surface': str(dst), 'sha256': digest(dst), 'source': str(src),
                              'source_sha256': digest(src), 'host_PCT_NAT_PFT': c['host'], 'created_utc': utc()})
    print(f'  {site}: surface built {dst} host={c["host"]}', flush=True)
    return dst


# ------------------------------------------------------------------ actions
def inventory(sites):
    for site in sites:
        p = P(site); tpl = p['tpl']
        print(f'\n===== {site} =====')
        if not tpl.is_dir():
            print('  TEMPLATE MISSING', tpl)
        else:
            for k in ('RUN_STARTDATE', 'DATM_YR_START', 'DATM_YR_END', 'DATM_YR_ALIGN', 'CCSM_CO2_PPMV', 'PTS_LAT', 'PTS_LON', 'RESUBMIT'):
                print(f'  {k:16} {query(tpl, k)}')
            lnd = (tpl / 'CaseDocs/lnd_in').read_text()
            print('  fsurdat        ', nml(lnd, 'fsurdat'))
            print('  history        ', ','.join(hist_fields(lnd)))
            _, b, files, dv, y0, y1 = stream_block(tpl / 'CaseDocs/datm.streams.xml')
            print(f'  stream years {y0}-{y1} files={len(files)} datavars={dv}')
            dirs = sorted({str(f.parent) for f in files})
            print('  stream folder(s):', ' | '.join(dirs))
            print(f'  {"year":6} {"records":>7} {"bad":>5} {"TBOT":>8} {"FSDS":>8} {"P_mm/yr":>10} {"maxconstTBOT":>12} file')
            for f in files:
                try:
                    s = year_stats(f, dv)
                    bad = sum(v for k, v in s.items() if k.endswith('_bad'))
                    ys = YEAR_RE.findall(f.name)
                    print(f"  {ys[0] if ys else '?':6} {s['records']:>7} {bad:>5} {s.get('TBOT_mean') or 0:>8.2f} {s.get('FSDS_mean') or 0:>8.2f} "
                          f"{(s.get('PRECTmms_mean') or 0)*86400*365:>10.0f} {s.get('TBOT_maxrun_const')!s:>12} {f.name}"
                          + (f"  MISSING {s['missing_vars']}" if s['missing_vars'] else ''))
                except Exception as e:
                    print('  ERROR', f, e)
        print('  candidate annual-NC forcing folders (>=5 years):')
        for d, n, a, b2 in candidate_forcing_dirs(site):
            print(f'    {a}-{b2} n={n:3}  {d}')
        raw = SITE_SRC / site / 'forcing'
        if raw.is_dir():
            print('  raw forcing folder', raw, ':', ', '.join(sorted(x.name for x in raw.iterdir())[:12]))
        names, dirs = old_dirs(site)
        print(f'  purge-old DELETES {len(dirs)} folders ({len(names)} old B02 cases); the template case folder only after prepare:')
        for d in dirs: print(f'    {du(d):>7}  {d}')
        q = queued_for(names + [SITES[site]['new']])
        print('  queued jobs for these names:', q or 'none')
        o = load(p['ledger']); print('  Stage44 ledger:', o.get('phase', '-'))


def prepare_one(site, args):
    p = P(site); c = SITES[site]; tpl, new = p['tpl'], p['new']
    need(not p['ledger'].exists(), f'{site}: ledger exists ({load(p["ledger"]).get("phase")}); no duplicate prepare')
    for x in (new, p['run'].parent, p['arch']): need(not x.exists(), f'{site}: exists, no overwrite: {x}')
    need(tpl.is_dir(), f'{site}: template case missing {tpl}')
    need(not queued_for([c['template'], c['new']]), f'{site}: template/new jobs still queued; cancel first')
    tl = (tpl / 'CaseDocs/lnd_in').read_text()
    need(hist_fields(tl) == AFTER, f'{site}: template history is not the fixed list')
    for k, v in FATES.items(): need(nml(tl, k) == v, f'{site}: template {k}={nml(tl, k)}')
    root, blk, files, dv, y0, y1 = stream_block(tpl / 'CaseDocs/datm.streams.xml')
    ref_records = {year_stats(files[0], dv)['records'], year_stats(files[-1], dv)['records']}
    newfiles = None; co2 = None; start = None
    fd = dict(x.split('=', 1) for x in (args.forcing_dir or [])).get(site)
    if fd:
        newfiles, a, b = forcing_dir_files(fd)
        stats = check_forcing(newfiles, dv, ref_records)
        start = a
        co2s = dict(x.split('=', 1) for x in (args.co2 or [])).get(site)
        if a != int(query(tpl, 'RUN_STARTDATE')[:4]):
            need(co2s, f'{site}: new forcing starts {a}; pass --co2 {site}=<NOAA global mean {a}>')
        co2 = float(co2s) if co2s else None
        print(f'  {site}: new forcing {a}-{b} ({len(newfiles)} files) from {fd}; all years complete, no missing values', flush=True)
    src = Path(nml(tl, 'fsurdat'))
    surf = build_surface(site, src, p['surf'])
    save(p['ledger'], {'site': site, 'phase': 'PREPARE_ATTEMPTED_UNCERTAIN', 'at': utc()})
    call([CTSM / 'cime/scripts/create_clone', '--case', new, '--clone', tpl, '--keepexe'], cwd=CTSM / 'cime/scripts', timeout=700)
    need(query(new, 'CASE') == p['name'], f'{site}: clone identity')
    settings = {'RUNDIR': p['run'], 'DOUT_S_ROOT': p['arch'], 'RUN_TYPE': 'startup', 'CONTINUE_RUN': 'FALSE',
                'STOP_OPTION': 'nyears', 'STOP_N': '5', 'REST_OPTION': 'nyears', 'REST_N': '5', 'RESUBMIT': '0',
                'RESUBMIT_SETS_CONTINUE_RUN': 'TRUE', 'CLM_ACCELERATED_SPINUP': 'on', 'CLM_FORCE_COLDSTART': 'on', 'DOUT_S': 'TRUE'}
    # DATM_YR_* must describe the forcing actually streamed. The Stage43 templates inherited
    # 2018-2019 from the old reference cases while their effective stream XML cycles the full record.
    sy0, sy1 = (start, start + len(newfiles) - 1) if newfiles else (y0, y1)
    settings.update({'DATM_YR_START': sy0, 'DATM_YR_END': sy1, 'DATM_YR_ALIGN': sy0})
    if newfiles:
        settings['RUN_STARTDATE'] = f'{start:04d}-01-01'
        if co2 is not None: settings['CCSM_CO2_PPMV'] = f'{co2:.2f}'
    else:
        need(int(query(tpl, 'RUN_STARTDATE')[:4]) == y0, f'{site}: template RUN_STARTDATE year != stream year_first {y0}')
    for k, v in settings.items(): change(new, k, v)
    if not (new / '.case.run').is_file(): call([new / 'case.setup'], cwd=new, timeout=400)
    u = new / 'user_nl_clm'; t = nml_set(u.read_text(), 'fsurdat', f"'{surf}'"); u.write_text(t)
    lock = (new / 'LockedFiles/env_case.xml').read_bytes()
    need((new / 'env_case.xml').read_bytes() == lock, f'{site}: lock differs before preview')
    raw = [x.get('value') for x in ET.parse(new / 'env_case.xml').getroot().iter('entry') if x.get('id') == 'COMP_ROOT_DIR_LND']
    need(len(raw) == 1, f'{site}: COMP_ROOT_DIR_LND entry'); restore = raw[0]
    try:
        change(new, 'COMP_ROOT_DIR_LND', OVERLAY)
        call([new / 'preview_namelists'], cwd=new, timeout=800)
    finally:
        change(new, 'COMP_ROOT_DIR_LND', restore)
    need((new / 'env_case.xml').read_bytes() == lock, f'{site}: lock not restored')
    # Meteorology: the approved selection lives in the template's effective CDEPS XML (as Stage43).
    if newfiles:
        df = blk.find('datafiles')
        for x in list(df): df.remove(x)
        for f in newfiles:
            e = ET.SubElement(df, 'file'); e.text = str(f)
        for k, v in (('year_first', start), ('year_last', start + len(newfiles) - 1), ('year_align', start)):
            blk.find(k).text = str(v)
        payload = ET.tostring(root, encoding='unicode').encode()
    else:
        payload = (tpl / 'CaseDocs/datm.streams.xml').read_bytes()
    for target in (new / 'CaseDocs/datm.streams.xml', p['run'] / 'datm.streams.xml'):
        need(target.is_file(), f'{site}: preview did not write {target}')
        target.write_bytes(payload)
    h = validate(site, surf, newfiles, co2)
    save(p['ledger'], {'site': site, 'phase': 'CASE_VERIFIED_NOT_SUBMITTED', 'case': str(new), 'template': str(tpl),
                       'surface': str(surf), 'surface_sha256': digest(surf), 'host_PCT_NAT_PFT': c['host'],
                       'start_year': int(query(new, 'RUN_STARTDATE')[:4]), 'forcing_dir': fd,
                       'forcing_years': [int(query(new, 'DATM_YR_START')), int(query(new, 'DATM_YR_END'))],
                       'co2_ppmv': float(query(new, 'CCSM_CO2_PPMV')), **h, 'created_utc': utc()})
    print(f'{site} CASE VERIFIED {p["name"]} host={c["host"]} start={query(new, "RUN_STARTDATE")} '
          f'DATM {query(new, "DATM_YR_START")}-{query(new, "DATM_YR_END")} CO2={query(new, "CCSM_CO2_PPMV")} | NO SLURM', flush=True)


def validate(site, surf, newfiles, co2):
    p = P(site); new, tpl = p['new'], p['tpl']
    doc, run = new / 'CaseDocs/lnd_in', p['run'] / 'lnd_in'
    need(doc.is_file() and run.is_file() and digest(doc) == digest(run), f'{site}: lnd_in missing or CaseDocs != RUNDIR')
    t = doc.read_text(); a = nml_pairs((tpl / 'CaseDocs/lnd_in').read_text()); b = nml_pairs(t)
    need(nml(t, 'fsurdat') == str(surf), f'{site}: fsurdat {nml(t, "fsurdat")}')
    need(hist_fields(t) == AFTER, f'{site}: history fields changed')
    for k, v in FATES.items(): need(nml(t, k) == v, f'{site}: {k}={nml(t, k)}')
    allowed = {'fsurdat'} | ({'co2_ppmv'} if co2 is not None else set())
    diff = sorted(k for k in set(a) | set(b) if a.get(k) != b.get(k) and k not in allowed)
    need(not diff, f'{site}: unexpected lnd_in differences from template: {diff[:6]}')
    for k in ('RUN_TYPE', 'CONTINUE_RUN', 'STOP_N', 'REST_N', 'RESUBMIT', 'CLM_ACCELERATED_SPINUP', 'DOUT_S'):
        want = {'RUN_TYPE': 'startup', 'CONTINUE_RUN': 'false', 'STOP_N': '5', 'REST_N': '5', 'RESUBMIT': '0',
                'CLM_ACCELERATED_SPINUP': 'on', 'DOUT_S': 'true'}[k]
        need(query(new, k).lower() == want, f'{site}: {k}={query(new, k)}')
    for k in ('PTS_LAT', 'PTS_LON', 'EXEROOT', 'ATM_NCPL', 'CALENDAR', 'MPI_RUN_COMMAND'):
        need(query(new, k) == query(tpl, k), f'{site}: {k} differs from template')
    s1, s2 = new / 'CaseDocs/datm.streams.xml', p['run'] / 'datm.streams.xml'
    need(digest(s1) == digest(s2), f'{site}: stream XML CaseDocs != RUNDIR')
    _, _, files, dv, y0, y1 = stream_block(s1)
    need([int(query(new, 'DATM_YR_START')), int(query(new, 'DATM_YR_END'))] == [y0, y1], f'{site}: DATM_YR vs stream years')
    need(len(files) == y1 - y0 + 1 and all(f.is_file() for f in files), f'{site}: stream files missing')
    if newfiles: need(files == [Path(f) for f in newfiles], f'{site}: stream datafiles not the new forcing')
    else: need(digest(s1) == digest(tpl / 'CaseDocs/datm.streams.xml'), f'{site}: stream XML differs from template')
    for path in (new / 'CaseDocs/nuopc.runconfig', p['run'] / 'nuopc.runconfig'):
        if path.is_file():
            txt = path.read_text()
            for key, xk in (('scol_lat', 'PTS_LAT'), ('scol_lon', 'PTS_LON')):
                v = re.findall(r'(?im)^\s*' + key + r'\s*=\s*([^\r\n]+)', txt)
                need(len(v) == 1 and abs(float(v[0]) - float(query(new, xk))) < 1e-4, f'{site}: {key} mismatch')
    return {'lnd_in_sha256': digest(doc), 'datm_streams_sha256': digest(s1)}


def purge_one(site):
    p = P(site); o = load(p['ledger'])
    verified = o.get('phase') in ('CASE_VERIFIED_NOT_SUBMITTED', 'SUBMIT_ATTEMPTED_UNCERTAIN', 'AD400_SUBMITTED')
    need(not o or verified, f'{site}: Stage44 prepare is uncertain ({o.get("phase")}); resolve it before deleting anything')
    names, dirs = old_dirs(site, keep_template=not verified)
    if not verified:
        print(f'  {site}: keeping template case {p["tpl"]} until the new case is verified (rerun purge-old afterwards)')
    need(SITES[site]['new'] not in names, 'new case in delete list')
    q = queued_for(names)
    need(not q, f'{site}: queued jobs for old cases: {q}')
    rec = D44 / f'{site}_purge_receipt.json'
    deleted = []
    for d in dirs:
        need(str(d).startswith((str(BASE / 'cases') + '/', str(OUTPUT) + '/')) and f'{site}_B02_' in d.name, f'unsafe path {d}')
        size = du(d)
        print(f'  deleting {size:>7} {d}', flush=True)
        shutil.rmtree(d)
        deleted.append({'path': str(d), 'size': size})
    old = load(rec).get('rounds', [])
    save(rec, {'site': site, 'rounds': old + [{'deleted_cases': names, 'deleted': deleted, 'template_kept': not verified, 'utc': utc()}]})
    print(f'{site} PURGE DONE {len(deleted)} folders; receipt {rec}')


def stack_guard():
    soft, hard = resource.getrlimit(resource.RLIMIT_STACK)
    if soft != resource.RLIM_INFINITY and soft < 65536 * 1024:
        need(hard == resource.RLIM_INFINITY or hard >= 65536 * 1024, 'stack hard limit < 64 MiB')
        resource.setrlimit(resource.RLIMIT_STACK, (hard, hard)); soft = hard
    ov = os.environ.get('SBATCH_PROPAGATE', '')
    need(not ov or {'ALL', 'STACK'} & set(ov.upper().split(',')), 'SBATCH_PROPAGATE excludes STACK')
    cfg = call(['scontrol', 'show', 'config'], timeout=60)
    m = re.search(r'(?im)^\s*PropagateResourceLimits\s*=\s*(\S+)', cfg)
    prop = m.group(1) if m else ''
    need(prop.upper() == 'ALL' or 'STACK' in prop.upper().split(','), 'Slurm PropagateResourceLimits excludes STACK')
    print('STACK GUARD PASS', 'unlimited' if soft == resource.RLIM_INFINITY else f'{soft // 1024}KiB', prop)
    return {'soft': str(soft), 'propagate': prop}


def submit_one(site, stack):
    p = P(site); o = load(p['ledger']); new = p['new']
    need(o.get('phase') == 'CASE_VERIFIED_NOT_SUBMITTED', f'{site}: phase {o.get("phase")}')
    cs = (new / 'CaseStatus').read_text(errors='replace') if (new / 'CaseStatus').is_file() else ''
    need(not re.search(r'case\.submit (starting|success)|case\.run starting', cs), f'{site}: CaseStatus shows a submission')
    need(not queued_for([p['name']]), f'{site}: jobs already queued')
    need(digest(new / 'CaseDocs/lnd_in') == o['lnd_in_sha256'] and digest(new / 'CaseDocs/datm.streams.xml') == o['datm_streams_sha256'],
         f'{site}: CaseDocs changed after verification')
    need(digest(o['surface']) == o['surface_sha256'], f'{site}: surface changed')
    o.update(phase='SUBMIT_ATTEMPTED_UNCERTAIN', stack=stack, submit_utc=utc()); save(p['ledger'], o)
    change(new, 'RESUBMIT', '79'); need(query(new, 'RESUBMIT') == '79', f'{site}: RESUBMIT not set; DO NOT RETRY')
    out = call([new / 'case.submit', '--skip-preview-namelist'], cwd=new, timeout=800)
    r = re.findall(r'Submitted job case\.run with id (\d+)', out); a = re.findall(r'Submitted job case\.st_archive with id (\d+)', out)
    need(len(r) == len(a) == 1, f'{site}: job IDs not parsed; DO NOT RETRY. {out[-600:]}')
    cp = configparser.RawConfigParser(); cp.read(new / '.submit_options')
    persisted = cp.has_section('SubmitOptions') and cp.getboolean('SubmitOptions', 'skip_pnl', fallback=False)
    o.update(phase='AD400_SUBMITTED', first_run_job=r[0], first_archive_job=a[0], skip_pnl_persisted=persisted); save(p['ledger'], o)
    print(f'{site} AD400 SUBMITTED {p["name"]} 80x5 run={r[0]} archive={a[0]} skip_pnl={persisted}', flush=True)


def first5_one(site):
    from netCDF4 import Dataset
    p = P(site); o = load(p['ledger'])
    need(o.get('phase') == 'AD400_SUBMITTED', f'{site}: phase {o.get("phase")}')
    y = o['start_year'] + 5; stamp = f'{y:04d}-01-01-00000'
    f = p['arch'] / 'rest' / stamp / f"{p['name']}.clm2.r.{stamp}.nc"
    need(f.is_file(), f'{site}: missing {f}')
    with Dataset(str(f)) as ds:
        st = int(np.asarray(ds.variables['spinup_state'][:]).ravel()[0]) if 'spinup_state' in ds.variables else int(ds.getncattr('spinup_state'))
    need(st == 2, f'{site}: spinup_state={st}')
    return {'restart': stamp, 'spinup_state': st}


def batch(label, sites, fn):
    bad = []
    for s in sites:
        try: fn(s)
        except Exception as e:
            print(s, label, 'HOLD - DO NOT RETRY BLINDLY:', str(e)[-1500:], flush=True); bad.append(s)
    print(label, 'SUMMARY ok=', len(sites) - len(bad), 'hold=', bad, flush=True)
    if bad: raise SystemExit(2)


def self_test():
    assert set(SITES) == {'DK-Sor', 'BE-Bra'}
    for s, c in SITES.items():
        assert abs(sum(c['host'].values()) - 100) < 1e-9 and set(c['host']) <= c['old_hosts']
        assert c['new'] != c['template'] and c['new'].startswith(s + '_B02_')
    assert YEAR_RE.findall('DK-Sor_2004.nc') == ['2004'] and YEAR_RE.findall('clmforc.1996-2024.nc') == ['1996', '2024']
    t = "fsurdat = 'a'\nhist_fincl1 = 'TOTSOMC','TOTSOMN','TLAI','FATES_GPP','FATES_NPP','TWS','H2OSNO'\n"
    assert nml(nml_set(t, 'fsurdat', "'b'"), 'fsurdat') == 'b' and hist_fields(t) == AFTER
    assert max_run(np.array([1, 1, 2, 2, 2, 3.])) == 3
    assert len({ACK_PREP, ACK_PURGE, ACK_SUB}) == 3
    print('STAGE44 SELF-TEST PASS (no files, no HPC)')


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('action', choices=('self-test', 'inventory', 'prepare', 'purge-old', 'submit', 'status', 'audit-first5'))
    ap.add_argument('--sites', nargs='+', choices=list(SITES))
    ap.add_argument('--confirm', default='')
    ap.add_argument('--forcing-dir', nargs='*', help='SITE=/folder/with/one/NC/per/year (DK-Sor full record)')
    ap.add_argument('--co2', nargs='*', help='SITE=ppm, required if the new forcing changes the start year')
    a = ap.parse_args()
    sites = list(dict.fromkeys(a.sites or SITES))
    if a.action == 'self-test': return self_test()
    if a.action == 'inventory': return inventory(sites)
    if a.action == 'status':
        for s in sites:
            o = load(P(s)['ledger']); print(s, o.get('phase', '-'), o.get('first_run_job', '-'), queued_for([SITES[s]['new']]) or '')
        return
    if a.action == 'audit-first5':
        bad = []
        for s in sites:
            try: print('PASS', s, first5_one(s))
            except Exception as e: print('HOLD', s, e); bad.append(s)
        raise SystemExit(2 if bad else 0)
    if a.action == 'prepare':
        need(a.confirm == ACK_PREP, 'requires --confirm ' + ACK_PREP)
        return batch('PREPARE', sites, lambda s: prepare_one(s, a))
    if a.action == 'purge-old':
        need(a.confirm == ACK_PURGE and a.sites, 'requires explicit --sites and --confirm ' + ACK_PURGE)
        return batch('PURGE', sites, purge_one)
    if a.action == 'submit':
        need(a.confirm == ACK_SUB, 'requires --confirm ' + ACK_SUB)
        st = stack_guard()
        return batch('SUBMIT', sites, lambda s: submit_one(s, st))


if __name__ == '__main__':
    main()
