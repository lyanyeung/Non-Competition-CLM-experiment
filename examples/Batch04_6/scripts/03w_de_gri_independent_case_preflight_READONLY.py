#!/usr/bin/env python3
"""Stage03W: read-only preflight for an independent DE-Gri sensitivity case.

Consumes the private Stage03V input plan (22 annual DATM files, 2011/2024 being
detached sensitivities) and answers, BEFORE any case exists:

  1. Are all 22 annual files and the B04 surface still byte-identical to the plan?
  2. Do the two sensitivity files differ from their historical baselines ONLY in
     the approved variables and the approved number of half-hours, with the same
     dimensions, time axis, attributes and dtypes (so DATM can read them)?
  3. Does the B04 surface carry HLM13 grass 100 / NATVEG 100 / CROP 0 and keep
     the template surface's location, sand, clay and ORGANIC unchanged?
  4. Does the chosen template case (read-only, built, --keepexe clone source)
     reference exactly the plan's baseline annual paths, and which stream
     entries would a new case have to change?
  5. When would a 5-year smoke or a 400-year cycle first read 2011 and 2024?

It prints a proposed case design but NEVER creates or changes a case, stages a
file, calls CIME or submits Slurm. The only file it writes is one new JSON report
(exclusive create). Licensed/forcing values are not written; only hashes, counts
and paths.

Commands:
  python3 -B 03w_...py self-test
  python3 -B 03w_...py list-templates [--cases-dir DIR]
  python3 -B 03w_...py plan --input-plan PLAN.json --template-case CASE_DIR --out NEW.json
"""
import argparse
import hashlib
import json
import re
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

SITE = 'DE-Gri'
STAGE = 'STAGE03W_DE_GRI_INDEPENDENT_CASE_PREFLIGHT_READONLY'
SURFACE_SHA = '08887d2daf5d529b5fed89ca21c8094e19dd471ff3387a758ce23b471211ed2b'
YEARS = list(range(2004, 2026))
SENS = {2011: 11, 2024: 23}
ALLOWED_CHANGES = {2011: {'TBOT', 'QBOT'}, 2024: {'QBOT'}}
REQUIRED = {'time', 'TBOT', 'QBOT', 'PSRF', 'FSDS', 'FLDS', 'WIND', 'PRECTmms', 'ZBOT'}
PROVENANCE_ATTRS = {'provenance_status', 'sensitivity_base_nc_sha256',
                    'sensitivity_candidate_csv_sha256', 'sensitivity_description'}
CASES_DIR = Path('/iridisfs/scratch/ly3n24/CLM_FATES/cases')
CREATE_CLONE = Path('/iridisfs/scratch/ly3n24/CLM_FATES/CTSM/cime/scripts/create_clone')
DEFAULT_CASE = 'DE-Gri_B04_FIXNC_SENS_AD400'
HEX64 = re.compile(r'^[0-9a-f]{64}$')
DATM_REF = re.compile(r'''([^\s'"<>,;=]+/DE-Gri_DATM_(\d{4})[^\s'"<>,;/]*\.nc)''')


def fail(msg):
    raise ValueError(str(msg))


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for part in iter(lambda: f.read(1024 * 1024), b''):
            h.update(part)
    return h.hexdigest()


def netcdf():
    try:
        import numpy as np
        from netCDF4 import Dataset
    except ImportError as exc:
        fail('numpy/netCDF4 unavailable (activate clm_fates_env): ' + str(exc))
    return np, Dataset


# ---------------------------------------------------------------- plan

def validate_plan(plan):
    if plan.get('site') != SITE or plan.get('status') != 'INPUT_PLAN_ONLY_NOT_MODEL_RELEASE':
        fail('Not a DE-Gri Stage03V input plan')
    if plan.get('case_or_slurm_modified') is not False or plan.get('source_science_or_soil_release') is not False:
        fail('Plan claims a case/Slurm change or a science release')
    if plan.get('surface_sha256') != SURFACE_SHA:
        fail('Plan surface SHA is not the approved B04 DE-Gri surface')
    rows = plan.get('annual_inputs')
    if not isinstance(rows, list) or [r.get('year') for r in rows] != YEARS:
        fail('Plan must list DE-Gri 2004-2025 exactly once, in order')
    for r in rows:
        year = r['year']
        want = 'approved_sensitivity' if year in SENS else 'historical_baseline'
        if r.get('kind') != want:
            fail('Unexpected kind for %d: %s' % (year, r.get('kind')))
        if not HEX64.match(r.get('sha256', '')) or not str(r.get('path', '')).startswith('/'):
            fail('Bad path/SHA for %d' % year)
    return rows


def baseline_path(rows, year):
    """Historical path for a year: itself, or the sibling name of the 20 others."""
    row = [r for r in rows if r['year'] == year][0]
    if row['kind'] == 'historical_baseline':
        return Path(row['path'])
    hist = {Path(r['path']).parent for r in rows if r['kind'] == 'historical_baseline'}
    if len(hist) != 1:
        fail('Historical files are not in exactly one directory')
    return hist.pop() / ('DE-Gri_DATM_%d_PROVISIONAL.nc' % year)


# ---------------------------------------------------------------- NetCDF

def read_var(nc, name):
    np, _ = netcdf()
    v = np.ma.asarray(nc.variables[name][:])
    return np.ma.getdata(v), np.ma.getmaskarray(v)


def attrs_of(obj, skip=()):
    out = {}
    for k in obj.ncattrs():
        if k in skip:
            continue
        v = obj.getncattr(k)
        out[k] = v.tolist() if hasattr(v, 'tolist') else v
    return out


def changed_times(a, b):
    np, _ = netcdf()
    (da, ma), (db, mb) = a, b
    if da.shape != db.shape:
        fail('Variable shape differs from baseline')
    both_nan = np.isnan(da) & np.isnan(db) if da.dtype.kind == 'f' else np.zeros(da.shape, bool)
    neq = (ma != mb) | (~ma & ~mb & ~((da == db) | both_nan))
    return np.flatnonzero(neq.reshape(neq.shape[0], -1).any(axis=1)) if neq.ndim else np.array([], int)


def check_annual(path, year):
    np, Dataset = netcdf()
    with Dataset(path, 'r') as nc:
        names = set(nc.variables)
        if not REQUIRED.issubset(names):
            fail('%d missing required variables' % year)
        t = nc.variables['time']
        if len(t) != 17520 or getattr(t, 'calendar', None) not in ('noleap', '365_day'):
            fail('%d must have 17520 no-leap time values' % year)
        if getattr(nc, 'site', None) != SITE or int(getattr(nc, 'forcing_year', -1)) != year:
            fail('%d site/forcing_year attribute mismatch' % year)
        return names


def compare_sensitivity(base, cand, year):
    """Candidate must equal baseline except approved variables/half-hours."""
    np, Dataset = netcdf()
    with Dataset(base, 'r') as old, Dataset(cand, 'r') as new:
        if set(old.variables) != set(new.variables) or \
                {k: len(v) for k, v in old.dimensions.items()} != {k: len(v) for k, v in new.dimensions.items()}:
            fail('%d candidate variables/dimensions differ from baseline' % year)
        if attrs_of(old, PROVENANCE_ATTRS) != attrs_of(new, PROVENANCE_ATTRS):
            fail('%d candidate global attributes differ beyond provenance' % year)
        if getattr(new, 'provenance_status', '') != 'DETACHED_SENSITIVITY_NOT_SCIENCE_RELEASED':
            fail('%d candidate lacks the detached-sensitivity provenance tag' % year)
        union, per_var, maxdelta = set(), {}, {}
        for name in sorted(old.variables):
            vo, vn = old.variables[name], new.variables[name]
            if vo.dimensions != vn.dimensions or vo.dtype != vn.dtype or attrs_of(vo) != attrs_of(vn):
                fail('%d variable %s metadata differs from baseline' % (year, name))
            a, b = read_var(old, name), read_var(new, name)
            idx = changed_times(a, b)
            if len(idx):
                if name not in ALLOWED_CHANGES[year]:
                    fail('%d unapproved variable changed: %s' % (year, name))
                per_var[name] = int(len(idx))
                union.update(int(i) for i in idx)
                maxdelta[name] = float(np.max(np.abs(a[0][idx].astype('f8') - b[0][idx].astype('f8'))))
                vals = b[0][idx].astype('f8')
                if not np.all(np.isfinite(vals)):
                    fail('%d non-finite candidate %s' % (year, name))
                if name == 'QBOT' and not (np.all(vals > 0) and np.all(vals < 0.05)):
                    fail('%d candidate QBOT outside (0, 0.05) kg/kg' % year)
                if name == 'TBOT' and not (np.all(vals > 200) and np.all(vals < 330)):
                    fail('%d candidate TBOT outside 200-330 K' % year)
        if len(union) != SENS[year]:
            fail('%d changed half-hours %d != approved %d' % (year, len(union), SENS[year]))
        return {'changed_half_hours': len(union), 'changed_by_variable': per_var,
                'max_abs_change': maxdelta, 'time_axis_identical': True}


def check_surface(path, template_surface=None):
    np, Dataset = netcdf()
    with Dataset(path, 'r') as nc:
        natveg = float(np.ma.getdata(nc.variables['PCT_NATVEG'][:]).reshape(-1)[0])
        crop = float(np.ma.getdata(nc.variables['PCT_CROP'][:]).reshape(-1)[0])
        pft = np.ma.getdata(nc.variables['PCT_NAT_PFT'][:]).astype('f8').reshape(-1)
        if natveg != 100 or crop != 0 or len(pft) != 15:
            fail('Surface landunit/PFT geometry is not NATVEG 100, CROP 0, 15 natpft')
        if abs(pft[13] - 100) > 1e-6 or abs(pft.sum() - 100) > 1e-6:
            fail('Surface is not HLM13 cool C3 grass 100%')
        fields = {n: np.ma.getdata(nc.variables[n][:]).astype('f8') for n in
                  ('LATIXY', 'LONGXY', 'PCT_SAND', 'PCT_CLAY', 'ORGANIC') if n in nc.variables}
    result = {'natpft13': float(pft[13]), 'inherited_fields_compared': []}
    if template_surface is not None:
        with Dataset(template_surface, 'r') as nc:
            for n, mine in fields.items():
                if n not in nc.variables:
                    fail('Template surface lacks ' + n)
                theirs = np.ma.getdata(nc.variables[n][:]).astype('f8')
                if mine.shape != theirs.shape or not np.allclose(mine, theirs, rtol=0, atol=1e-9):
                    fail('Surface %s differs from the template surface (inherited soil/location must be unchanged)' % n)
                result['inherited_fields_compared'].append(n)
    return result


# ---------------------------------------------------------------- template case

def env_values(case):
    values = {}
    for name in ('env_run.xml', 'env_build.xml', 'env_case.xml'):
        f = case / name
        if f.is_file():
            for e in ET.parse(f).getroot().iter('entry'):
                if e.get('id') and e.get('value') is not None:
                    values[e.get('id')] = e.get('value')
    return values


def nl_value(text, key):
    m = re.search(r"(?im)^\s*%s\s*=\s*(.+?)\s*$" % re.escape(key), text)
    return m.group(1).strip().strip("'\"") if m else None


def read_text(path):
    return path.read_text(encoding='utf-8', errors='replace') if path.is_file() else ''


def inspect_template(case):
    env = env_values(case)
    lnd = read_text(case / 'CaseDocs' / 'lnd_in')
    user_clm = read_text(case / 'user_nl_clm')
    user_streams = read_text(case / 'user_nl_datm_streams')
    streams_xml = read_text(case / 'CaseDocs' / 'datm.streams.xml')
    refs = {}
    for source, text in (('user_nl_datm_streams', user_streams), ('datm.streams.xml', streams_xml)):
        for path, year in DATM_REF.findall(text):
            refs.setdefault(int(year), {}).setdefault(path, set()).add(source)
    first = re.findall(r'<year_first>\s*(\d+)', streams_xml) or re.findall(r'year_first\s*=\s*(\d+)', user_streams)
    last = re.findall(r'<year_last>\s*(\d+)', streams_xml) or re.findall(r'year_last\s*=\s*(\d+)', user_streams)
    align = re.findall(r'<year_align>\s*(\d+)', streams_xml) or re.findall(r'year_align\s*=\s*(\d+)', user_streams)
    return {'name': case.name, 'env': {k: env.get(k) for k in (
                'BUILD_COMPLETE', 'DATM_MODE', 'RUN_STARTDATE', 'RUN_TYPE', 'STOP_OPTION', 'STOP_N',
                'REST_N', 'RESUBMIT', 'CLM_USRDAT_NAME', 'CLM_BLDNML_OPTS')},
            'fsurdat': nl_value(lnd, 'fsurdat'), 'use_fates': nl_value(lnd, 'use_fates'),
            'fates_paramfile': nl_value(lnd, 'fates_paramfile'), 'finidat': nl_value(lnd, 'finidat'),
            'user_nl_clm_fates_lines': [x.strip() for x in user_clm.splitlines()
                                        if re.search(r'fates|fsurdat|finidat', x, re.I)
                                        and not x.strip().startswith('!')][:20],
            'stream_files': {y: {p: sorted(s) for p, s in d.items()} for y, d in sorted(refs.items())},
            'year_first': sorted(set(first)), 'year_last': sorted(set(last)), 'year_align': sorted(set(align)),
            'has_user_nl_datm_streams': bool(user_streams), 'has_streams_xml': bool(streams_xml),
            'diagnostics': stream_diagnostics(user_streams, streams_xml, refs)}


def stream_diagnostics(user_streams, streams_xml, refs):
    """Structure of the template's stream definition (paths/settings only, no data values)."""
    def cut(x):
        return x.strip()[:220]
    lines = [x for x in user_streams.splitlines() if x.strip() and not x.strip().startswith('!')]
    return {'user_nl_datm_streams_lines': len(lines),
            'user_nl_datm_streams_first_lines': [cut(x) for x in lines[:4]],
            'user_nl_datm_streams_key_names': sorted({x.split('=')[0].strip()[:60] for x in lines})[:12],
            'streams_xml_chars': len(streams_xml),
            'stream_names': re.findall(r'<stream_info\s+name="([^"]+)"', streams_xml)[:12],
            'year_lines_in_xml': [cut(x) for x in streams_xml.splitlines() if 'year_' in x][:8],
            'references_per_year_min_max': [min((sum(len(v) for v in d.values()) for d in refs.values()), default=0),
                                            max((sum(len(v) for v in d.values()) for d in refs.values()), default=0)]}


def forcing_year(model_year, first, last, align):
    n = last - first + 1
    return first + ((model_year - align) % n)


def sensitivity_schedule(start_year, first, last, align, horizon=400):
    firsts = {}
    for k in range(horizon):
        fy = forcing_year(start_year + k, first, last, align)
        if fy in SENS and fy not in firsts:
            firsts[fy] = k + 1
    smoke = [forcing_year(start_year + k, first, last, align) for k in range(5)]
    return {'first_model_year_index_using': firsts, 'five_year_smoke_forcing_years': smoke,
            'five_year_smoke_reads_sensitivity': any(y in SENS for y in smoke)}


# ---------------------------------------------------------------- plan command

def run_plan(plan_path, template_case, case_name, cases_dir, stage_dir):
    plan = json.loads(Path(plan_path).read_text(encoding='utf-8'))
    rows = validate_plan(plan)
    holds, notes = [], []
    print('PLAN_INPUT PASS | 22 years 2004-2025 | sensitivities 2011,2024 | surface SHA pinned')

    # 1. byte-identity of everything the plan names
    for r in rows:
        p = Path(r['path'])
        if not p.is_file() or digest(p) != r['sha256']:
            fail('File missing or SHA changed since plan: %d %s' % (r['year'], p))
    surface = Path(plan['surface_path'])
    if not surface.is_file() or digest(surface) != SURFACE_SHA:
        fail('B04 surface missing or SHA changed since plan')
    print('HASHES PASS | 22 annual files + B04 surface re-hashed and unchanged')

    # 2. structure of all 22 files; sensitivity-vs-baseline difference scope
    varsets = {r['year']: check_annual(Path(r['path']), r['year']) for r in rows}
    if len({frozenset(v) for v in varsets.values()}) != 1:
        fail('The 22 annual files do not share one variable set')
    print('NC_STRUCTURE PASS | 22 x 17520 no-leap half-hours, site/forcing_year attrs, identical variable set')
    diffs = {}
    for year in SENS:
        base = baseline_path(rows, year)
        if not base.is_file():
            holds.append('BASELINE_FILE_MISSING_%d' % year)
            continue
        diffs[year] = compare_sensitivity(base, Path([r for r in rows if r['year'] == year][0]['path']), year)
        diffs[year]['baseline_path'] = str(base)
        diffs[year]['baseline_sha256'] = digest(base)
        print('SENSITIVITY_DIFF PASS', year, json.dumps(diffs[year], sort_keys=True, separators=(',', ':')))

    # 3. template case + surface
    template_case = Path(template_case)
    if not template_case.is_dir():
        fail('Template case not found: %s' % template_case)
    tpl = inspect_template(template_case)
    env = tpl['env']
    if env['BUILD_COMPLETE'] != 'TRUE':
        holds.append('TEMPLATE_NOT_BUILT_KEEPEXE_UNSAFE')
    if env['DATM_MODE'] != '1PT':
        holds.append('TEMPLATE_DATM_MODE_NOT_1PT')
    if tpl['use_fates'] not in ('.true.', 'true', 'T', '.T.'):
        holds.append('TEMPLATE_NOT_A_FATES_CASE')
    if not re.fullmatch(r'\d{4}-01-01', env['RUN_STARTDATE'] or ''):
        holds.append('TEMPLATE_RUN_STARTDATE_NOT_YYYY_01_01')
    if tpl['fsurdat'] and 'B04' in Path(tpl['fsurdat']).name:
        holds.append('TEMPLATE_ALREADY_USES_A_B04_SURFACE')
    template_surface = Path(tpl['fsurdat']) if tpl['fsurdat'] else None
    if template_surface is None or not template_surface.is_file():
        holds.append('TEMPLATE_ORIGINAL_SURFACE_NOT_READABLE')
        surf = check_surface(surface)
    else:
        surf = check_surface(surface, template_surface)
    print('SURFACE PASS | HLM13 100, NATVEG 100, CROP 0 | unchanged vs template:', ','.join(surf['inherited_fields_compared']) or 'not compared')
    print('TEMPLATE', json.dumps({k: tpl[k] for k in ('name', 'env', 'fsurdat', 'use_fates', 'finidat',
                                                      'year_first', 'year_last', 'year_align')}, sort_keys=True, separators=(',', ':')))
    print('TEMPLATE_STREAM_DIAG', json.dumps(tpl['diagnostics'], sort_keys=True, separators=(',', ':')))
    if tpl['finidat']:
        notes.append('Template lnd_in has finidat; a fresh AD case must not inherit it')

    # 4. stream references: template must equal the plan's baseline paths
    stream_status = {}
    for r in rows:
        year = r['year']
        want = str(baseline_path(rows, year))
        got = tpl['stream_files'].get(year, {})
        if set(got) != {want}:
            holds.append('TEMPLATE_STREAM_PATH_MISMATCH_%d' % year)
        stream_status[year] = {'template_paths': sorted(got), 'baseline_expected': want,
                               'new_case_path': r['path'], 'change': r['kind'] == 'approved_sensitivity'}
    if set(tpl['stream_files']) - set(YEARS):
        holds.append('TEMPLATE_HAS_EXTRA_DATM_YEARS')
    if not tpl['has_user_nl_datm_streams']:
        notes.append('Template has no user_nl_datm_streams; stream edit mechanism must be confirmed before build')
    print('STREAM_MATCH | template years %s | mismatching years: %s' % (
        '%d-%d' % (min(tpl['stream_files']), max(tpl['stream_files'])) if tpl['stream_files'] else 'none',
        [y for y in YEARS if ('TEMPLATE_STREAM_PATH_MISMATCH_%d' % y) in holds] or 'none'))

    # 5. design and coverage
    schedule = None
    if tpl['year_first'] and tpl['year_last'] and tpl['year_align'] and re.match(r'\d{4}', env['RUN_STARTDATE'] or ''):
        schedule = sensitivity_schedule(int(env['RUN_STARTDATE'][:4]), int(tpl['year_first'][0]),
                                        int(tpl['year_last'][0]), int(tpl['year_align'][0]))
        print('SCHEDULE', json.dumps(schedule, sort_keys=True, separators=(',', ':')))
        notes.append('Schedule assumes year_align is the model year at which year_first is used (CDEPS taxmode=cycle); '
                     'confirm with the first preview_namelists of the new case')
        if not schedule['five_year_smoke_reads_sensitivity']:
            notes.append('A 5-year AD smoke does NOT read 2011 or 2024; the sensitivity files are first read at model year '
                         + str(schedule['first_model_year_index_using']))
    else:
        holds.append('TEMPLATE_STREAM_YEAR_WINDOW_NOT_PARSED')
    new_case = Path(cases_dir) / case_name
    if new_case.exists():
        holds.append('NEW_CASE_NAME_ALREADY_EXISTS')
    cand_home = [r['year'] for r in rows if r['kind'] == 'approved_sensitivity' and r['path'].startswith('/home/')]
    stage = Path(stage_dir) if stage_dir else Path(plan['surface_path']).parent.parent / 'Batch04_DE-Gri_SENS_DATM'
    if cand_home:
        notes.append('Sensitivity candidates %s live under /home; copy them SHA-verified to %s before the case references them' % (cand_home, stage))
    design = {
        'case_name': case_name, 'case_dir': str(new_case), 'clone_source': str(template_case),
        'clone_command_NOT_RUN': [str(CREATE_CLONE), '--case', str(new_case),
                                  '--clone', str(template_case), '--keepexe'],
        'stage_dir_NOT_CREATED': str(stage),
        'stage_copies_NOT_DONE': [{'year': r['year'], 'from': r['path'], 'to': str(stage / Path(r['path']).name),
                                   'sha256': r['sha256']} for r in rows if r['kind'] == 'approved_sensitivity'],
        'stream_entries_to_change': {str(y): s['new_case_path'] for y, s in stream_status.items() if s['change']},
        'fsurdat_to_set': str(surface), 'fsurdat_sha256': SURFACE_SHA,
        'protocol_after_build': 'AD5 smoke (STOP_N=REST_N=5, RESUBMIT=0, stack soft limit >= 65536 KB), then AD395',
        'static_checks_after_clone': ['preview_namelists then streams list exactly these 22 paths',
                                      'lnd_in fsurdat == fsurdat_to_set and use_fates true',
                                      'fixed-biogeography / no-competition lines carried from template',
                                      'no finidat; spinup_state=2 in AD']}
    print('DESIGN (not executed)', json.dumps({k: design[k] for k in ('case_name', 'clone_source', 'stage_dir_NOT_CREATED',
                                                                       'stream_entries_to_change', 'fsurdat_to_set')},
                                              sort_keys=True, separators=(',', ':')))
    for n in notes:
        print('NOTE', n)
    for h in holds:
        print('HOLD', h)
    report = {'stage': STAGE, 'read_only': True, 'case_or_slurm_modified': False, 'model_submission_authorised': False,
              'science_release': False, 'holds': holds, 'notes': notes, 'sensitivity_diffs': diffs,
              'surface_check': surf, 'template': tpl, 'stream_status': stream_status, 'schedule': schedule,
              'design': design, 'plan_input': str(plan_path)}
    return report


def run_list(cases_dir):
    cases = Path(cases_dir)
    if not cases.is_dir():
        fail('Cases dir not found: %s' % cases)
    found = sorted(p for p in cases.glob('DE-Gri*') if p.is_dir())
    for p in found:
        t = inspect_template(p)
        years = sorted(t['stream_files'])
        print('TEMPLATE_CANDIDATE', json.dumps({'case': p.name, 'built': t['env']['BUILD_COMPLETE'],
                                                'start': t['env']['RUN_STARTDATE'], 'fsurdat': t['fsurdat'],
                                                'datm_years': '%d-%d' % (years[0], years[-1]) if years else None,
                                                'use_fates': t['use_fates']}, separators=(',', ':')))
    print('LISTED %d DE-Gri case directories | none selected automatically' % len(found))


# ---------------------------------------------------------------- self test

def _make_annual(path, year, tbot=290.0, qbot=0.01, extra_change=None, edits=None, provenance=False):
    np, Dataset = netcdf()
    with Dataset(path, 'w', format='NETCDF4_CLASSIC') as nc:
        nc.createDimension('time', 17520); nc.createDimension('lat', 1); nc.createDimension('lon', 1)
        t = nc.createVariable('time', 'f8', ('time',))
        t.units = 'days since %d-01-01 00:00:00' % year; t.calendar = 'noleap'; t[:] = np.arange(17520) / 48.0
        for name in sorted(REQUIRED - {'time'}):
            v = nc.createVariable(name, 'f8' if name == 'ZBOT' else 'f4', ('time', 'lat', 'lon'))
            v[:] = {'TBOT': tbot, 'QBOT': qbot, 'PSRF': 97000.0}.get(name, 3.0)
        nc.site = SITE; nc.forcing_year = year
        for var, idx, val in (edits or []):
            nc.variables[var][idx, 0, 0] = val
        if extra_change:
            nc.variables[extra_change][5, 0, 0] = 99.0
        if provenance:
            nc.provenance_status = 'DETACHED_SENSITIVITY_NOT_SCIENCE_RELEASED'


def _make_surface(path, pft13=100.0):
    np, Dataset = netcdf()
    with Dataset(path, 'w', format='NETCDF4_CLASSIC') as nc:
        nc.createDimension('lsmlat', 1); nc.createDimension('lsmlon', 1)
        nc.createDimension('natpft', 15); nc.createDimension('nlevsoi', 10)
        for n, val in (('PCT_NATVEG', 100.0), ('PCT_CROP', 0.0), ('LATIXY', 50.95), ('LONGXY', 13.51)):
            nc.createVariable(n, 'f8', ('lsmlat', 'lsmlon'))[:] = val
        p = nc.createVariable('PCT_NAT_PFT', 'f8', ('natpft', 'lsmlat', 'lsmlon'))
        arr = np.zeros((15, 1, 1)); arr[13] = pft13; arr[0] = 100.0 - pft13; p[:] = arr
        for n, val in (('PCT_SAND', 30.0), ('PCT_CLAY', 20.0), ('ORGANIC', 5.0)):
            nc.createVariable(n, 'f8', ('nlevsoi', 'lsmlat', 'lsmlon'))[:] = val


def _make_case(case, surface, years, base_dir, mutate_year=None, built='TRUE', align=1):
    (case / 'CaseDocs').mkdir(parents=True)
    for name, entries in (('env_run.xml', {'DATM_MODE': '1PT', 'RUN_STARTDATE': '0001-01-01', 'STOP_N': '5',
                                           'STOP_OPTION': 'nyears', 'REST_N': '5', 'RESUBMIT': '0', 'RUN_TYPE': 'startup'}),
                          ('env_build.xml', {'BUILD_COMPLETE': built}), ('env_case.xml', {})):
        root = ET.Element('file')
        for k, v in entries.items():
            ET.SubElement(root, 'entry', id=k, value=v)
        ET.ElementTree(root).write(case / name)
    (case / 'CaseDocs' / 'lnd_in').write_text("&clm_inparm\n fsurdat = '%s'\n use_fates = .true.\n/\n" % surface)
    (case / 'user_nl_clm').write_text("use_fates_nocomp = .true.\nuse_fates_fixed_biogeog = .true.\n")
    lines = []
    for y in years:
        d = Path(base_dir)
        name = 'DE-Gri_DATM_%d_PROVISIONAL.nc' % (y + (1 if y == mutate_year else 0))
        lines.append('CLM_USRDAT.Solar:datafiles=%s/%s' % (d, name))
    (case / 'user_nl_datm_streams').write_text('\n'.join(lines) + '\n')
    (case / 'CaseDocs' / 'datm.streams.xml').write_text(
        '<stream_info name="CLM_USRDAT.Solar"><year_first>2004</year_first><year_last>2025</year_last>'
        '<year_align>%d</year_align></stream_info>\n' % align)


def self_test(root):
    global SURFACE_SHA
    np, Dataset = netcdf()
    import shutil
    with tempfile.TemporaryDirectory(dir=root) as tmp:
        tmp = Path(tmp)
        hist = tmp / 'hist'; cand = tmp / 'home_candidates'; surf = tmp / 'B04'; tpl_surf = tmp / 'orig_surface.nc'
        for d in (hist, cand, surf):
            d.mkdir()
        for y in YEARS:
            _make_annual(hist / ('DE-Gri_DATM_%d_PROVISIONAL.nc' % y), y)
        base11 = hist / 'DE-Gri_DATM_2011_PROVISIONAL.nc'; base24 = hist / 'DE-Gri_DATM_2024_PROVISIONAL.nc'
        _make_annual(cand / 'DE-Gri_2011_approved_sensitivity.nc', 2011, provenance=True,
                     edits=[('TBOT', 100 + i, 285.0 + i * .1) for i in range(11)] +
                           [('QBOT', 100 + i, 0.007 + i * 1e-4) for i in range(11)])
        _make_annual(cand / 'DE-Gri_2024_approved_sensitivity.nc', 2024, provenance=True,
                     edits=[('QBOT', 200 + i, 0.006 + i * 1e-5) for i in range(23)])
        _make_surface(surf / 'DE-Gri_B04_GITHUBPFT_POINT_CANDIDATE.nc')
        _make_surface(tpl_surf, pft13=60.0)
        surface = surf / 'DE-Gri_B04_GITHUBPFT_POINT_CANDIDATE.nc'
        rows = []
        for y in YEARS:
            p = cand / ('DE-Gri_%d_approved_sensitivity.nc' % y) if y in SENS else hist / ('DE-Gri_DATM_%d_PROVISIONAL.nc' % y)
            rows.append({'year': y, 'kind': 'approved_sensitivity' if y in SENS else 'historical_baseline',
                         'path': str(p), 'sha256': digest(p)})

        def write_plan(name, rr=None, surf_sha=None):
            plan = {'site': SITE, 'status': 'INPUT_PLAN_ONLY_NOT_MODEL_RELEASE', 'surface_path': str(surface),
                    'surface_sha256': surf_sha or SURFACE_SHA, 'annual_inputs': rr or rows, 'case_or_slurm_modified': False,
                    'source_science_or_soil_release': False}
            f = tmp / name; f.write_text(json.dumps(plan)); return f

        # The real surface hash is pinned, so patch the pin for the synthetic surface only.
        real_pin, SURFACE_SHA = SURFACE_SHA, digest(surface)
        try:
            case = tmp / 'cases' / 'DE-Gri_FATES_SPINUP1000_S30SHARED'
            _make_case(case, tpl_surf, YEARS, hist)
            good = write_plan('plan.json')
            rep = run_plan(good, case, DEFAULT_CASE, tmp / 'cases', None)
            assert not rep['holds'], rep['holds']
            assert rep['sensitivity_diffs'][2011]['changed_half_hours'] == 11
            assert rep['sensitivity_diffs'][2024]['changed_by_variable'] == {'QBOT': 23}
            assert rep['schedule']['first_model_year_index_using'] == {2011: 8, 2024: 21}
            assert rep['schedule']['five_year_smoke_reads_sensitivity'] is False
            assert 'DE-Gri_2011_approved_sensitivity.nc' in json.dumps(rep['design']['stream_entries_to_change'])

            def expect_fail(label, fn):
                try:
                    fn()
                except ValueError:
                    return
                raise AssertionError('did not reject: ' + label)

            # tampered historical byte
            victim = hist / 'DE-Gri_DATM_2007_PROVISIONAL.nc'; shutil.copy(victim, tmp / 'v.bak')
            with victim.open('r+b') as f:
                f.seek(2000); b = f.read(1); f.seek(2000); f.write(bytes([b[0] ^ 1]))
            expect_fail('tampered file', lambda: run_plan(good, case, DEFAULT_CASE, tmp / 'cases', None))
            shutil.copy(tmp / 'v.bak', victim)
            # missing year
            expect_fail('missing year', lambda: validate_plan(json.loads(write_plan('p2.json', rows[:-1]).read_text())))
            # unapproved variable changed in a candidate
            _make_annual(tmp / 'zb.nc', 2024, provenance=True, extra_change='ZBOT',
                         edits=[('QBOT', 200 + i, 0.006 + i * 1e-5) for i in range(23)])
            expect_fail('ZBOT change', lambda: compare_sensitivity(base24, tmp / 'zb.nc', 2024))
            # wrong number of edits
            _make_annual(tmp / 'few.nc', 2011, provenance=True,
                         edits=[('QBOT', 100 + i, 0.007 + i * 1e-4) for i in range(10)])
            expect_fail('edit count', lambda: compare_sensitivity(base11, tmp / 'few.nc', 2011))
            # surface that is not grass 100
            expect_fail('surface PFT', lambda: check_surface(tpl_surf))
            # template referencing a wrong year file is a HOLD, not a crash
            bad_case = tmp / 'cases' / 'DE-Gri_bad'
            _make_case(bad_case, tpl_surf, YEARS, hist, mutate_year=2015)
            rep2 = run_plan(good, bad_case, DEFAULT_CASE, tmp / 'cases', None)
            assert 'TEMPLATE_STREAM_PATH_MISMATCH_2015' in rep2['holds'], rep2['holds']
            # unbuilt template and pre-existing new case name are holds
            ub = tmp / 'cases' / 'DE-Gri_unbuilt'
            _make_case(ub, tpl_surf, YEARS, hist, built='FALSE')
            (tmp / 'cases' / DEFAULT_CASE).mkdir()
            rep3 = run_plan(good, ub, DEFAULT_CASE, tmp / 'cases', None)
            assert {'TEMPLATE_NOT_BUILT_KEEPEXE_UNSAFE', 'NEW_CASE_NAME_ALREADY_EXISTS'} <= set(rep3['holds'])
            shifted = tmp / 'cases' / 'DE-Gri_align2004'
            _make_case(shifted, tpl_surf, YEARS, hist, align=2004)
            rep4 = run_plan(good, shifted, 'DE-Gri_B04_other', tmp / 'cases', None)
            assert rep4['schedule']['first_model_year_index_using'] == {2011: 9, 2024: 22}
            run_list(tmp / 'cases')
        finally:
            SURFACE_SHA = real_pin
    print('SELF-TEST PASS | hash/tamper, variable-scope, edit-count, surface, stream-path, schedule and hold logic')


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest='cmd', required=True)
    s = sub.add_parser('self-test'); s.add_argument('--test-dir', type=Path)
    l = sub.add_parser('list-templates'); l.add_argument('--cases-dir', type=Path, default=CASES_DIR)
    q = sub.add_parser('plan')
    q.add_argument('--input-plan', type=Path, required=True)
    q.add_argument('--template-case', type=Path, required=True)
    q.add_argument('--case-name', default=DEFAULT_CASE)
    q.add_argument('--cases-dir', type=Path, default=CASES_DIR)
    q.add_argument('--stage-dir', type=Path)
    q.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    try:
        if a.cmd == 'self-test':
            self_test(a.test_dir)
        elif a.cmd == 'list-templates':
            run_list(a.cases_dir)
        else:
            if a.out.exists():
                fail('Refusing to overwrite existing report: %s' % a.out)
            report = run_plan(a.input_plan, a.template_case, a.case_name, a.cases_dir, a.stage_dir)
            with a.out.open('x', encoding='utf-8') as f:
                json.dump(report, f, indent=2, default=str); f.write('\n')
            print('CASE PREFLIGHT %s | read-only, NO CASE/STAGING/SLURM | %s' % (
                'HOLD %d' % len(report['holds']) if report['holds'] else 'PASS', a.out))
    except ValueError as exc:
        print('ERROR', exc, file=sys.stderr)
        sys.exit(2)


if __name__ == '__main__':
    main()
