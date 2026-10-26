#!/usr/bin/env python3
"""AmeriFlux Batch02 Stage07: repair surfaces with 0/0 sand+clay layers (peat) and resubmit once.

Failure (26 Oct 2026, run jobs 4741116 US-ICh, 4741118 US-ICt, 6 s after start):
  SoilStateInitTimeConstMod.F90 line 351 "found depth points that do NOT sum to zero when surface does"
CTSM requires PCT_SAND+PCT_CLAY > 0 in every soil layer when any layer is > 0. The Stage02/05 surfaces of
the Imnavait tundra sites carry SSURGO organic (peat) horizons as sand = clay = 0. In CLM the organic
content is represented by ORGANIC (kg m-3); PCT_SAND/PCT_CLAY describe the mineral fraction. Each 0/0
layer therefore takes the texture of the nearest layer BELOW with sand+clay > 0 (peat over silt/till,
BADM), or the nearest layer above if none exists below. ORGANIC and everything else are unchanged.

Actions
  self-test
  check                READ ONLY: every Batch02 surface layer by layer (sand, clay, ORGANIC), flags 0/0 layers,
                       and the failure evidence for the Stage06 cases that hit the error
  repair --sites ... --confirm REPAIR_AMF_B02_ZERO_TEXTURE_AND_RESUBMIT_ONCE
                       new surface *_soil10_stage07_v2.nc, fsurdat switched in the SAME Stage06 case, preview
                       with the private AD overlay, lnd_in must differ from before ONLY in fsurdat, one
                       case.submit (80x5, RESUBMIT=79). Stage06 ledger updated (history kept).
Requires: failed first run job with exactly this error, no queued jobs (cancel the dependent st_archive),
no restart/history output, CaseStatus last event "case.run error".
"""
import argparse, importlib.util, json, re, shutil
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('s06', HERE / '06_direct_AD400_ten_site_cases_and_submit.py')
S6 = importlib.util.module_from_spec(spec); spec.loader.exec_module(S6)
ERR = 'found depth points that do NOT sum to zero when surface does'
ACK = 'REPAIR_AMF_B02_ZERO_TEXTURE_AND_RESUBMIT_ONCE'
utc, digest = S6.utc, S6.digest


def need(ok, why):
    if not ok: raise RuntimeError(str(why))


def v2_surface(s): return S6.EXP / s / 'surface' / f'surfdata_{s}_FIXNC_PFT_soil10_stage07_v2.nc'


def layers(path):
    from netCDF4 import Dataset
    with Dataset(str(path)) as ds:
        sand = np.ma.filled(ds.variables['PCT_SAND'][:], np.nan).astype(float).ravel()
        clay = np.ma.filled(ds.variables['PCT_CLAY'][:], np.nan).astype(float).ravel()
        org = np.ma.filled(ds.variables['ORGANIC'][:], np.nan).astype(float).ravel() if 'ORGANIC' in ds.variables else None
    return sand, clay, org


def fill_plan(sand, clay):
    tot = sand + clay
    zero = [i for i in range(tot.size) if not tot[i] > 0]
    if not zero or len(zero) == tot.size: return zero, {}
    plan = {}
    for i in zero:
        below = [j for j in range(i + 1, tot.size) if tot[j] > 0]
        above = [j for j in range(i - 1, -1, -1) if tot[j] > 0]
        plan[i] = below[0] if below else above[0]
    return zero, plan


def run_log_error(s):
    logs = sorted(S6.run_dir(s).glob('lnd.log.*')) + sorted(S6.run_dir(s).glob('cesm.log.*'))
    for f in logs:
        try:
            if ERR in f.read_text(errors='replace'): return f
        except Exception: pass
    return None


def check(sites):
    hit = []
    for s in sites:
        p = S6.surface(s)
        if not p.is_file(): print(f'{s:7} surface missing {p}'); continue
        sand, clay, org = layers(p)
        zero, plan = fill_plan(sand, clay)
        print(f'{s:7} ' + ' '.join(f'L{i+1}:{sand[i]:.1f}/{clay[i]:.1f}' for i in range(sand.size)))
        if org is not None: print(f'{"":7} ORGANIC kg/m3 ' + ' '.join(f'{x:.0f}' for x in org[:10]))
        if plan:
            hit.append(s)
            print(f'{"":7} ZERO-TEXTURE LAYERS {[i+1 for i in zero]} -> fill from ' + ', '.join(f'L{i+1}<-L{j+1}' for i, j in plan.items()))
            o = S6.load(S6.ledger(s)); f = run_log_error(s)
            print(f'{"":7} Stage06 phase={o.get("phase")} first_run_job={o.get("first_run_job")} log_with_error={f}')
    print('CHECK: sites needing repair:', hit or 'none')
    return hit


def failed_first(s, o):
    rows = {r[0]: r for r in S6.sacct_name(S6.name(s))}
    r = rows.get(int(o['first_run_job']))
    need(r and r[2] == 'FAILED', f'{s}: first run job {o.get("first_run_job")} is not FAILED: {r}')
    need(not S6.queued(S6.name(s)), f'{s}: jobs still queued for {S6.name(s)} (scancel the dependent st_archive first)')
    cs = (S6.case_dir(s) / 'CaseStatus').read_text(errors='replace')
    last = [ln for ln in cs.splitlines() if re.search(r'case\.run|case\.submit|model execution', ln)][-1]
    need('case.run error' in last, f'{s}: last CaseStatus event is not case.run error: {last}')
    need(run_log_error(s), f'{s}: the zero-texture error is not in the run logs')
    for pat in ('rpointer*', '*.r.*.nc', '*.h0*.nc'):
        need(not list(S6.run_dir(s).glob(pat)), f'{s}: run dir has {pat}; not a clean init failure')
    need(S6.latest(s)[1] == 0, f'{s}: archive already has restarts')


def build_v2(s, src, dst):
    from netCDF4 import Dataset
    sand, clay, _ = layers(src)
    zero, plan = fill_plan(sand, clay)
    need(plan, f'{s}: no zero-texture layer to repair')
    if dst.is_file():
        r = json.loads(Path(str(dst) + '.json').read_text())
        need(r.get('sha256') == digest(dst) and r.get('source_sha256') == digest(src), f'{s}: existing v2 surface differs; move aside')
        print(f'  {s}: v2 surface reused {dst}'); return dst, r['fill_plan']
    tmp = Path(str(dst) + '.partial'); shutil.copyfile(src, tmp)
    with Dataset(str(tmp), 'r+') as ds:
        for name in ('PCT_SAND', 'PCT_CLAY'):
            v = ds.variables[name]; a = np.ma.filled(v[:], np.nan).astype(float); flat = a.reshape(-1)
            for i, j in plan.items(): flat[i] = flat[j]
            v[:] = flat.reshape(a.shape)
        ds.setncattr('stage07_zero_texture_fill', '; '.join(f'L{i+1}<-L{j+1}' for i, j in plan.items()) + ' (organic layers keep ORGANIC; mineral texture from nearest mineral layer)')
    s2, c2, _ = layers(tmp)
    need(np.all(s2 + c2 > 0), f'{s}: repair left zero layers')
    with Dataset(str(src)) as a, Dataset(str(tmp)) as b:
        for k in a.variables:
            if k in ('PCT_SAND', 'PCT_CLAY'): continue
            x, y = np.ma.filled(a.variables[k][:], -999), np.ma.filled(b.variables[k][:], -999)
            need(np.array_equal(x, y), f'{s}: {k} changed')
    tmp.rename(dst)
    fp = {f'L{i+1}': f'L{j+1}' for i, j in plan.items()}
    Path(str(dst) + '.json').write_text(json.dumps({'site': s, 'surface': str(dst), 'sha256': digest(dst), 'source': str(src),
                                                    'source_sha256': digest(src), 'fill_plan': fp,
                                                    'sand_after': s2.tolist(), 'clay_after': c2.tolist(), 'created_utc': utc()}, indent=2) + '\n')
    print(f'  {s}: v2 surface built {dst} fill {fp}', flush=True)
    return dst, fp


def repair_one(s, stack):
    o = S6.load(S6.ledger(s))
    need(o.get('phase') == 'AD400_SUBMITTED', f'{s}: Stage06 phase {o.get("phase")}')
    failed_first(s, o)
    case = S6.case_dir(s); src = Path(o['surface'])
    need(digest(src) == o['surface_sha256'], f'{s}: Stage06 surface changed')
    dst, fp = build_v2(s, src, v2_surface(s))
    old_lnd = (case / 'CaseDocs/lnd_in').read_text(); old_stream = digest(case / 'CaseDocs/datm.streams.xml')
    o.setdefault('history', []).append({k: o.get(k) for k in ('phase', 'first_run_job', 'first_archive_job', 'surface', 'surface_sha256', 'lnd_in_sha256')})
    o.update(phase='STAGE07_REPAIR_ATTEMPTED_UNCERTAIN', stage07_utc=utc()); S6.save(S6.ledger(s), o)
    u = case / 'user_nl_clm'; u.write_text(S6.nml_set(u.read_text(), 'fsurdat', f"'{dst}'"))
    env, lock = case / 'env_case.xml', case / 'LockedFiles/env_case.xml'
    need(env.read_bytes() == lock.read_bytes(), f'{s}: env_case lock differs before preview')
    original = env.read_bytes()
    try:
        S6.xc(case, 'COMP_ROOT_DIR_LND', str(S6.OVERLAY))
        S6.cmd([case / 'preview_namelists'], cwd=case, timeout=600)
    finally:
        S6.xc(case, 'COMP_ROOT_DIR_LND', '$SRCROOT')
        need(env.read_bytes() == original and lock.read_bytes() == original, f'{s}: STOP env_case lock not restored')
    new_lnd = (case / 'CaseDocs/lnd_in').read_text()
    need(digest(case / 'CaseDocs/lnd_in') == digest(S6.run_dir(s) / 'lnd_in'), f'{s}: lnd_in CaseDocs != RUNDIR')
    need(S6.nml_get(new_lnd, 'fsurdat') == str(dst), f'{s}: fsurdat not switched')
    pairs = lambda t: {m.group(1).lower(): m.group(2).strip() for m in re.finditer(r'(?m)^\s*([A-Za-z_]\w*)\s*=\s*(.*?)\s*$', t)}
    a, b = pairs(old_lnd), pairs(new_lnd)
    diff = sorted(k for k in set(a) | set(b) if a.get(k) != b.get(k) and k != 'fsurdat')
    need(not diff, f'{s}: lnd_in differs beyond fsurdat: {diff[:6]}')
    need(digest(case / 'CaseDocs/datm.streams.xml') == old_stream, f'{s}: DATM streams changed')
    for k, v in (('RESUBMIT', '79'), ('CONTINUE_RUN', 'false'), ('STOP_N', '5'), ('CLM_ACCELERATED_SPINUP', 'on')):
        need(S6.xq(case, k).lower() == v, f'{s}: {k}={S6.xq(case, k)}')
    out = S6.cmd([case / 'case.submit', '--skip-preview-namelist'], cwd=case, timeout=650)
    r, ar = S6.RUN_RE.search(out), S6.ARCH_RE.search(out)
    need(r and ar, f'{s}: job IDs not parsed; DO NOT RETRY. {out[-500:]}')
    o.update(phase='AD400_SUBMITTED', first_run_job=r.group(1), first_archive_job=ar.group(1), surface=str(dst),
             surface_sha256=digest(dst), lnd_in_sha256=digest(case / 'CaseDocs/lnd_in'), stage07_fill_plan=fp,
             stage07_stack=stack, stage07_submit_tail=out[-600:])
    S6.save(S6.ledger(s), o)
    print(f'{s} STAGE07 RESUBMITTED with v2 surface run={r.group(1)} archive={ar.group(1)} (80x5)', flush=True)


def self_test():
    z, p = fill_plan(np.array([0, 0, 0, 10, 20.]), np.array([0, 0, 0, 2, 5.]))
    assert z == [0, 1, 2] and p == {0: 3, 1: 3, 2: 3}
    z, p = fill_plan(np.array([10, 0, 20.]), np.array([5, 0, 5.]))
    assert p == {1: 2}
    z, p = fill_plan(np.array([10, 20, 0.]), np.array([5, 5, 0.]))
    assert p == {2: 1}
    assert fill_plan(np.zeros(3), np.zeros(3))[1] == {}
    print('STAGE07 SELF-TEST PASS (no files)')


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('action', choices=('self-test', 'check', 'repair'))
    ap.add_argument('--sites', nargs='+')
    ap.add_argument('--confirm', default='')
    a = ap.parse_args()
    sites = S6.pick(a.sites)
    if a.action == 'self-test': self_test()
    elif a.action == 'check': check(sites)
    else:
        need(a.confirm == ACK and a.sites, 'requires explicit --sites and --confirm ' + ACK)
        st = S6.stack_guard()
        S6.batch('STAGE07 REPAIR', sites, lambda s: repair_one(s, st))
