#!/usr/bin/env python3
"""Borrow Batch03's working high-submit-stack recovery for four Batch02 AD5s.

Raise only this Python process's low soft stack, preserving high/unlimited values;
Slurm inherits it through case.submit. No MPI wrapper, XML/science edits, model
rebuild, mesh replacement or probe prerequisite. Verify all four failed initial
jobs/inputs, preserve records, cancel only their blocked archives, submit AD5 once.
"""
import argparse
import configparser
import hashlib
import json
import os
import re
import resource
import shutil
import socket
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

BASE = Path('/iridisfs/scratch/ly3n24/CLM_FATES')
OUT = BASE / 'experiments/NonCompetitionObserved22/Batch02_10'
OUTPUTS = Path('/scratch/ly3n24/CTSM_FATES_OUTPUTS')
JOBS = {'FI-Hyy': ('4728102', '4728103'), 'FR-Hes': ('4728104', '4728105'),
        'CH-Fru': ('4728106', '4728107'), 'IT-MBo': ('4728108', '4728109')}
MPI = 'srun --mpi=pmix --ntasks=1 --cpus-per-task=1 --cpu-bind=cores'
MIN_STACK = 64 * 1024 * 1024
BATCH = OUT / '_stage09_Batch03_method_retry.json'
VERSION = 'batch02-stage09-Batch03-submit-stack-method-v1-20261025'


def fail(message):
    raise RuntimeError(message)


def now():
    return datetime.now(timezone.utc).isoformat()


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def save(path, obj, exclusive=False):
    with path.open('x' if exclusive else 'w', encoding='utf-8') as f:
        json.dump(obj, f, indent=2, allow_nan=False)
        f.write('\n')
        f.flush()
        os.fsync(f.fileno())


def call(args, cwd=None):
    p = subprocess.run(list(map(str, args)), cwd=cwd, capture_output=True, text=True, timeout=60)
    if p.returncode:
        fail('Command failed: ' + repr(list(map(str, args))) + '\n' + (p.stdout + p.stderr)[-3000:])
    return p.stdout.strip()


def paths(site):
    name = site + '_B02_FIXNC_AD400'
    return (name, BASE / 'cases' / name, OUTPUTS / name / 'run', OUTPUTS / 'archive' / name,
            OUT / site / 'AD5_case_state.json', OUT / site / 'stage09_Batch03_method_retry')


def query(case, key):
    return call([case / 'xmlquery', key, '--value'], cwd=case)


def stack_policy(soft, hard):
    if soft == resource.RLIM_INFINITY or soft >= MIN_STACK:
        return soft
    if hard == resource.RLIM_INFINITY:
        return resource.RLIM_INFINITY
    if hard < MIN_STACK:
        fail('Stack hard limit is below the proven Batch03 minimum 64 MiB')
    return min(hard, 300000 * 1024)


def stack_guard(raise_low=False):
    soft, hard = resource.getrlimit(resource.RLIMIT_STACK)
    before = soft
    target = stack_policy(soft, hard)
    if raise_low and target != soft:
        resource.setrlimit(resource.RLIMIT_STACK, (target, hard))
        soft, hard = resource.getrlimit(resource.RLIMIT_STACK)
    adequate = soft == resource.RLIM_INFINITY or soft >= MIN_STACK
    record = {'host': socket.gethostname(), 'pid': os.getpid(), 'soft_bytes_before': before,
              'soft_bytes_at_submit': soft, 'hard_bytes': hard, 'adequate': adequate,
              'soft_KiB_at_submit': 'unlimited' if soft == resource.RLIM_INFINITY else soft // 1024,
              'changed_current_python_process_only': before != soft, 'scope': 'CURRENT submit process; historical failed-task limits unknown'}
    print('STACK GUARD', json.dumps(record), flush=True)
    if raise_low and not adequate:
        fail('Submit stack is still below 64 MiB')
    return record


def queue():
    result = []
    for line in call(['squeue', '-u', 'ly3n24', '-h', '-o', '%i|%j|%T|%R']).splitlines():
        if line.strip():
            r = [x.strip() for x in line.split('|')]
            if len(r) != 4:
                fail('Unparseable queue output')
            result.append(r)
    return result


def accounting(ids):
    text = call(['sacct', '-X', '-j', ','.join(ids), '-n', '-P', '--format=JobIDRaw,JobName%128,State%40,ExitCode'])
    rows = {}
    for line in text.splitlines():
        r = [x.strip() for x in line.split('|')]
        if len(r) >= 4 and r[0] in ids:
            rows[r[0]] = r[:4]
    return rows


def scalar(text, key):
    r = re.findall(r'(?im)^[ \t]*' + re.escape(key) + r'[ \t]*=[ \t]*([^\r\n!]*)', text)
    if len(r) != 1:
        fail('Ambiguous/missing namelist value: ' + key)
    return r[0].strip().rstrip(',').strip().strip("'\"")


def preflight():
    if BATCH.exists() or BATCH.is_symlink():
        fail('Stage09 already attempted; use status, never resubmit blindly: ' + str(BATCH))
    config = call(['scontrol', 'show', 'config'])
    m = re.search(r'(?m)^\s*PropagateResourceLimits\s*=\s*(\S+)', config)
    if not m or m[1] != 'ALL':
        fail('Batch03 method requires verified current PropagateResourceLimits=ALL')
    override = os.environ.get('SBATCH_PROPAGATE')
    if override and not ({'ALL', 'STACK'} & set(override.split(','))):
        fail('SBATCH_PROPAGATE excludes STACK; inspect rather than overriding it')
    ids = [j for pair in JOBS.values() for j in pair]
    rows, active = accounting(ids), queue()
    plan = {}
    for site, (oldrun, oldarch) in JOBS.items():
        name, case, run, archive, state, retrydir = paths(site)
        if case.is_symlink() or not case.is_dir() or state.is_symlink() or not state.is_file():
            fail(site + ': missing/unsafe independent case or state')
        if archive.is_symlink():
            fail(site + ': unexpected archive symlink')
        if retrydir.exists() or retrydir.is_symlink() or (OUT / site / 'AD5_stack256_pilot_v1').exists():
            fail(site + ': another recovery already attempted; inspect before Stage09')
        obj = json.loads(state.read_text())
        for key, value in {'site': site, 'case': str(case), 'run': str(run), 'archive': str(archive),
                           'phase': 'FIRST_5Y_SUBMITTED', 'first_run_job': oldrun, 'first_archive_job': oldarch,
                           'spinup_state': 2, 'RESUBMIT': 0, 'skip_preview_persisted': True}.items():
            if obj.get(key) != value:
                fail(site + ': original submission state differs: ' + key)
        if rows.get(oldrun) != [oldrun, 'run.' + name, 'FAILED', '1:0']:
            fail(site + ': original run not the exact failed job: ' + repr(rows.get(oldrun)))
        ar = rows.get(oldarch)
        if not ar or ar[1] != 'st_archive.' + name or not (ar[2] == 'PENDING' or ar[2].startswith('CANCELLED')):
            fail(site + ': old archive accounting unexpected: ' + repr(ar))
        mine = [r for r in active if r[1] in ('run.' + name, 'st_archive.' + name)]
        if any(r[0] != oldarch or r[2] != 'PENDING' or 'DependencyNeverSatisfied' not in r[3] for r in mine):
            fail(site + ': unexpected active run/archive: ' + repr(mine))
        for key, value in {'CASE': name, 'RUN_TYPE': 'startup', 'RUN_STARTDATE': obj['start_date'],
                           'CONTINUE_RUN': 'FALSE', 'CLM_FORCE_COLDSTART': 'on', 'CLM_ACCELERATED_SPINUP': 'on',
                           'STOP_OPTION': 'nyears', 'STOP_N': '5', 'REST_OPTION': 'nyears', 'REST_N': '5',
                           'RESUBMIT': '0', 'RUNDIR': str(run), 'DOUT_S_ROOT': str(archive), 'MPI_RUN_COMMAND': MPI,
                           'TOTALPES': '1', 'NTHRDS_LND': '1', 'BUILD_COMPLETE': 'TRUE'}.items():
            if query(case, key).lower() != value.lower():
                fail(site + ': current CIME value differs: ' + key)
        if Path(query(case, 'EXEROOT')).resolve() != Path(obj['executable']).parent.resolve():
            fail(site + ': executable root changed')
        if any(run.glob('*.r.*.nc')) or any(run.glob('rpointer.*')) or any(run.glob(name + '.clm2.h*.nc')) or next(archive.rglob('*.r.*.nc'), None):
            fail(site + ': restart/pointer/history exists; no automatic cold-start overwrite')
        if (case / 'env_case.xml').read_bytes() != (case / 'LockedFiles/env_case.xml').read_bytes():
            fail(site + ': CIME case lock changed')
        fingerprints = {str(Path(obj['surface'])): obj['surface_sha256'], str(Path(obj['executable'])): obj['executable_sha256']}
        for rel, key in (('lnd_in', 'generated_lnd_in_sha256'), ('datm.streams.xml', 'generated_stream_sha256')):
            for folder in (case / 'CaseDocs', run):
                fingerprints[str(folder / rel)] = obj[key]
        for filename, h in obj['user_DATM_files'].items():
            fingerprints[str(case / filename)] = h
        for p, h in fingerprints.items():
            if sha(Path(p)) != h:
                fail(site + ': pinned input/executable changed: ' + p)
        text = (run / 'lnd_in').read_text()
        for key, value in {'spinup_state': '2', 'use_fates': '.true.', 'use_fates_sp': '.false.',
                           'use_fates_fixed_biogeog': '.true.', 'use_fates_nocomp': '.true.', 'finidat': ''}.items():
            if scalar(text, key) != value:
                fail(site + ': effective AD5 namelist differs: ' + key)
        param = Path(scalar(text, 'fates_paramfile'))
        if sha(param) != obj['parameter_sha256']:
            fail(site + ': active FATES parameters changed')
        for p in [case / 'user_nl_clm', case / '.env_mach_specific.sh', case / '.env_mach_specific.csh', param]:
            if p.is_file():
                fingerprints[str(p)] = sha(p)
        cp = configparser.RawConfigParser()
        cp.read(case / '.submit_options')
        if not cp.getboolean('SubmitOptions', 'skip_pnl', fallback=False):
            fail(site + ': missing persistent skip-preview option')
        for line in (case / '.case.run').read_text().splitlines():
            if line.lstrip().startswith('#SBATCH') and '--propagate' in line and not re.search(r'--propagate(?:=|\s+)(?:ALL|STACK)\b', line):
                fail(site + ': unexpected batch propagation override: ' + line)
        plan[site] = {'obj': obj, 'hashes': fingerprints, 'old_run': rows[oldrun], 'old_archive': ar,
                      'cancel_archive': bool(mine)}
        print(site, 'B03_METHOD_RETRY_PREFLIGHT_PASS', oldrun, oldarch, flush=True)
    print('PREFLIGHT PASS 4/4 | original MPI command, inputs and executable retained; no model/science changes')
    return plan


def verify_hashes(hashes):
    for p, h in hashes.items():
        if sha(Path(p)) != h:
            fail('Input changed after preflight: ' + p)


def parse_ids(text):
    run = re.findall(r'Submitted job case\.run with id (\d+)', text)
    arch = re.findall(r'Submitted job case\.st_archive with id (\d+)', text)
    oldids = {j for pair in JOBS.values() for j in pair}
    if len(run) != 1 or len(arch) != 1 or run[0] == arch[0] or run[0] in oldids or arch[0] in oldids:
        fail('New CIME job IDs ambiguous; preserve receipt and do not repeat resubmit')
    return run[0], arch[0]


def one_retry(site, item, stack):
    name, case, run, archive, state, retrydir = paths(site)
    if json.loads(state.read_text()) != item['obj']:
        fail(site + ': original ledger changed after preflight')
    verify_hashes(item['hashes'])
    retrydir.mkdir(exist_ok=False)
    before = retrydir / 'before'
    before.mkdir()
    for p in (state, case / 'env_run.xml', case / 'CaseStatus', case / '.submit_options',
              case / ('run.' + name + '.out'), case / ('run.' + name + '.err')):
        if p.is_file():
            shutil.copy2(p, before / p.name)
            if sha(p) != sha(before / p.name):
                fail('Backup bytes differ: ' + str(p))
    rec = {'version': VERSION, 'site': site, 'phase': 'ATTEMPTED_UNCERTAIN', 'at': now(),
           'old_run': item['old_run'], 'old_archive': item['old_archive'], 'stack_limit_at_submit': stack}
    receipt = retrydir / 'retry_state.json'
    save(receipt, rec, exclusive=True)
    obj = dict(item['obj'], phase='STAGE09_RESUBMISSION_ATTEMPTED_UNCERTAIN')
    obj.setdefault('failed_AD5_attempts', []).append({'run_job': JOBS[site][0], 'archive_job': JOBS[site][1],
        'sacct_run': item['old_run'], 'historical_submit_stack': 'NOT_RECORDED', 'recorded_utc': now()})
    save(state, obj)
    if item['cancel_archive']:
        current = [r for r in queue() if r[1] in ('run.' + name, 'st_archive.' + name)]
        if current != [[JOBS[site][1], 'st_archive.' + name, 'PENDING', '(DependencyNeverSatisfied)']]:
            if len(current) != 1 or current[0][:3] != [JOBS[site][1], 'st_archive.' + name, 'PENDING'] or 'DependencyNeverSatisfied' not in current[0][3]:
                fail(site + ': old archive no longer matches the verified blocked job')
        call(['scancel', JOBS[site][1]])
        rec['old_archive_cancel_requested'] = True
        save(receipt, rec)
    for n in range(10):
        active = [r for r in queue() if r[1] in ('run.' + name, 'st_archive.' + name)]
        if not active:
            break
        if any(r[0] != JOBS[site][1] for r in active):
            fail(site + ': unexpected new queued job')
        if n < 9:
            time.sleep(1)
    if active:
        fail(site + ': old archive cancellation not confirmed; stop without resubmitting')
    verify_hashes(item['hashes'])
    rec['stack_limit_immediately_before_submit'] = stack_guard(raise_low=True)
    save(receipt, rec)
    output_path = retrydir / 'case_submit_output.txt'
    try:
        p = subprocess.run([str(case / 'case.submit'), '--skip-preview-namelist'], cwd=case,
                           capture_output=True, text=True, timeout=360)
    except Exception as exc:
        part = getattr(exc, 'stdout', '') or ''
        if isinstance(part, bytes):
            part = part.decode(errors='replace')
        output_path.write_text(part + '\n' + str(exc))
        raise
    text = p.stdout + '\n' + p.stderr
    output_path.write_text(text)
    runid, archid = parse_ids(text)
    rec.update(run_job=runid, archive_job=archid, submission_exit_code=p.returncode)
    save(receipt, rec)
    cp = configparser.RawConfigParser()
    cp.read(case / '.submit_options')
    skip = cp.getboolean('SubmitOptions', 'skip_pnl', fallback=False)
    rec.update(phase='SUBMITTED' if p.returncode == 0 and skip else 'SUBMITTED_REVIEW', skip_preview_persisted=skip)
    save(receipt, rec)
    obj.update(phase='FIRST_5Y_RESUBMITTED_STACK_GUARD', active_run_job=runid, active_archive_job=archid,
               stack_limit_at_submit=rec['stack_limit_immediately_before_submit'], stage09_retry_receipt=str(receipt))
    save(state, obj)
    if rec['phase'] != 'SUBMITTED':
        fail(site + ': new jobs have IDs but CIME/options need review; do not repeat submission')
    print(site, 'AD5_RESUBMITTED RUN=' + runid + ' ARCHIVE=' + archid + ' YEARS=5 RESUBMIT=0', flush=True)


def resubmit():
    stack = stack_guard(raise_low=True)
    plan = preflight()
    save(BATCH, {'version': VERSION, 'phase': 'ATTEMPTED_UNCERTAIN', 'at': now(),
                 'stack': stack, 'sites': list(JOBS)}, exclusive=True)
    done = []
    try:
        for site, item in plan.items():
            one_retry(site, item, stack)
            done.append(site)
    except Exception as exc:
        save(BATCH, {'version': VERSION, 'phase': 'STOPPED_REVIEW_REQUIRED', 'successful_before_error': done, 'error': str(exc)})
        print('STAGE09 STOPPED:', str(exc))
        print('Use status and retained receipts; do not repeat resubmit after an uncertain result.')
        return 2
    save(BATCH, {'version': VERSION, 'phase': 'FOUR_AD5_RESUBMITTED', 'sites': done, 'at': now()})
    print('STAGE09 RESUBMIT SUMMARY submitted= 4 uncertain= []')
    print('Same Batch03 submission-stack method. AD5 only; no AD395 or Normal400 submitted.')
    return 0


def status():
    states, ids = {}, []
    for site in JOBS:
        p = paths(site)[5] / 'retry_state.json'
        obj = json.loads(p.read_text()) if p.is_file() else {'phase': 'NOT_ATTEMPTED'}
        states[site] = obj
        ids += [obj[k] for k in ('run_job', 'archive_job') if obj.get(k)]
    acct = accounting(ids) if ids else {}
    active = queue()
    for site, obj in states.items():
        name = paths(site)[0]
        print(site, 'PHASE=' + obj['phase'], 'RUN=' + str(obj.get('run_job', '-')), acct.get(obj.get('run_job'), '-'),
              'ARCHIVE=' + str(obj.get('archive_job', '-')), acct.get(obj.get('archive_job'), '-'),
              'QUEUE=', [r for r in active if r[1] in ('run.' + name, 'st_archive.' + name)])
    print('Submission/runtime status only; exact successful archives and AD-state restarts are required before AD395.')


def self_test():
    assert stack_policy(-1, -1) == -1
    assert stack_policy(300000 * 1024, -1) == 300000 * 1024
    assert stack_policy(8 * 1024 * 1024, -1) == -1
    assert stack_policy(8 * 1024 * 1024, 300000 * 1024) == 300000 * 1024
    assert parse_ids('Submitted job case.run with id 999001\nSubmitted job case.st_archive with id 999002') == ('999001', '999002')
    assert len(JOBS) == 4
    print('STAGE09 SELF-TEST PASS: Batch03 stack guard, never lower high/unlimited limits, exact four Batch02 sites; no jobs')


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('action', choices=('self-test', 'check', 'resubmit', 'status'))
    a = p.parse_args()
    if a.action == 'self-test':
        self_test()
    elif a.action == 'check':
        stack_guard()
        preflight()
    elif a.action == 'status':
        status()
    else:
        raise SystemExit(resubmit())
