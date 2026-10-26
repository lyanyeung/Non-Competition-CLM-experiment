#!/usr/bin/env python3
"""Read-only triage of five exact Batch02 failed AD400 submissions.

Never modifies a case, meteorology, receipts, restart or Slurm job. Failure
labels describe observed log signatures; a SIGSEGV alone is not proof of stack
exhaustion. IT-Noe and the four completed Batch02 sites are not selected.
"""
import argparse
import getpass
import gzip
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

BASE = Path('/iridisfs/scratch/ly3n24/CLM_FATES')
OUTPUT = Path('/scratch/ly3n24/CTSM_FATES_OUTPUTS')
EXPERIMENT = BASE / 'experiments/NonCompetitionObserved22/Batch02_10'
TARGETS = [
    ('ES-LJu', '4734425', 'ES-LJu_B02_FIXNC_AD400_BARE49_C3GRA31_SHRUB20_MET24',
     'stage26_ES_LJu_MET24_direct_AD400/submission_attempt.json'),
    ('DK-Sor', '4734485', 'DK-Sor_B02_FIXNC_FOREST_PROXY_AD5',
     'stage31_forest_direct_AD400_submission_receipts/DK-Sor_AD400_submission_attempt.json'),
    ('FR-FBn', '4734487', 'FR-FBn_B02_FIXNC_FOREST_PROXY_AD5',
     'stage31_forest_direct_AD400_submission_receipts/FR-FBn_AD400_submission_attempt.json'),
    ('BE-Bra', '4734696', 'BE-Bra_B02_FIXNC_FOREST_MET34_AD400',
     'stage35_BE_Bra_MET34_direct_AD400/submission_attempt.json'),
    ('CH-Lae', '4734856', 'CH-Lae_B02_FIXNC_FOREST_MET36_AD400',
     'stage37_CH_Lae_MET36_direct_AD400/submission_attempt.json'),
]
ASSIGN = re.compile(r'^\s*([a-z][a-z_0-9]*(?:\s*\(\s*\d+\s*\))?)\s*=', re.I)
QUOTED = re.compile(r"['\"]([^'\"]+)['\"]")
REGISTER = re.compile(r'(?m)^\s*\d+\s+([A-Za-z][A-Za-z0-9_]+)\s{2,}')
ERROR = re.compile(r'(?i)htapes_fieldlist|histFileMod|fatal|\berror\b|SIGSEGV|'
                   r'segmentation|forrtl|MPI_Abort|out.of.memory|oom.kill|'
                   r'HumanIndex|negative.*RH|stack|ESMF_MeshCreate')
HISTORY_FATAL = re.compile(r'htapes_fieldlist\s+ERROR:\s*([A-Za-z0-9_]+)\s+in\s+fincl', re.I)


def call(args, timeout=45, cwd=None):
    try:
        p = subprocess.run([str(a) for a in args], capture_output=True,
                           text=True, errors='replace', timeout=timeout, cwd=cwd)
        if p.returncode:
            print('COMMAND_UNAVAILABLE', list(map(str, args)), p.returncode,
                  (p.stderr or p.stdout)[-1000:].strip())
            return ''
        return p.stdout
    except (OSError, subprocess.TimeoutExpired) as exc:
        print('COMMAND_UNAVAILABLE', list(map(str, args)), str(exc))
        return ''


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def strip_comment(line):
    quote = None
    i = 0
    while i < len(line):
        char = line[i]
        if quote:
            if char == quote:
                if i + 1 < len(line) and line[i+1] == quote:
                    i += 2
                    continue
                quote = None
        elif char in "'\"":
            quote = char
        elif char == '!':
            return line[:i]
        i += 1
    return line


def history_fields(text):
    result = []
    key = None
    value = []
    for raw in text.splitlines() + ['/']:
        line = strip_comment(raw)
        match = ASSIGN.match(line)
        if match or line.strip() == '/':
            if key and re.fullmatch(r'hist_fincl(?:\d+|\(\d+\))', key):
                result.append((key, QUOTED.findall('\n'.join(value))))
            key = re.sub(r'\s+', '', match.group(1).lower()) if match else None
            value = [line[match.end():]] if match else []
        elif key:
            value.append(line)
    return result


def classify(text):
    hit = HISTORY_FATAL.search(text)
    if hit:
        return 'CONFIRMED_HISTORY_FIELD_NOT_REGISTERED:' + hit.group(1).upper()
    if re.search(r'out.of.memory|oom.kill|oom_kill|OUT_OF_MEMORY', text, re.I):
        return 'EXPLICIT_OOM_SIGNATURE_REVIEW_ACCOUNTING'
    if re.search(r'HumanIndex|negative.*relative humidity|negative.*RH', text, re.I):
        return 'HUMIDITY_PHYSICS_SIGNATURE_REVIEW_ORIGINAL_ERROR'
    if re.search(r'SIGSEGV|segmentation|forrtl.*severe.*174', text, re.I):
        return 'SEGFAULT_CAUSE_UNCONFIRMED_NOT_PROOF_OF_LOW_STACK'
    return 'CAUSE_UNCONFIRMED_REVIEW_PRINTED_LOGS'


def log_text(path):
    opener = gzip.open if path.suffix == '.gz' else open
    with opener(path, 'rb') as handle:
        raw = handle.read(24 * 1024 * 1024 + 1)
    if len(raw) > 24 * 1024 * 1024:
        print('LOG_TRUNCATED_TO_24_MIB', path)
    return raw[:24 * 1024 * 1024].decode(errors='replace')


def query(case, key):
    if not (case / 'xmlquery').is_file():
        return ''
    return call([case / 'xmlquery', key, '--value'], cwd=case).strip()


def queue():
    text = call(['squeue', '-h', '-u', getpass.getuser(), '-o', '%i|%j|%T'])
    return [line for line in text.splitlines() if line.strip()]


def accounting_logs(job, case_name):
    text = call(['sacct', '-n', '-P', '-X', '-j', job,
                 '--format=JobIDRaw,StdOut%1024,StdErr%1024,WorkDir%1024'])
    paths = []
    for line in text.splitlines():
        columns = [x.strip() for x in line.split('|')]
        if len(columns) < 4 or columns[0] != job:
            continue
        for item in columns[1:3]:
            if not item or item.upper() in ('UNKNOWN', 'NONE', 'N/A', '(NULL)'):
                continue
            item = item.replace('%j', job).replace('%J', job).replace('%x', 'run.'+case_name)
            path = Path(item)
            if not path.is_absolute() and columns[3].startswith('/'):
                path = Path(columns[3]) / path
            paths.append(path)
    return paths


def diagnose(target, jobs):
    site, job, name, receipt = target
    case = BASE / 'cases' / name
    print('\n' + '=' * 80)
    print('SITE', site, 'FAILED_RUN', job, 'CASE', case)
    current = [line for line in jobs if len(line.split('|')) >= 3 and
               line.split('|')[1] in ('run.'+name, 'st_archive.'+name)]
    print('CURRENT_EXACT_CASE_QUEUE', current or 'none reported; see queue-command warnings')
    print(call(['sacct', '-j', job+','+str(int(job)+1), '-P',
                '--format=JobIDRaw,JobName%120,State,ExitCode,Elapsed,MaxRSS,ReqMem,NodeList%50']).strip())
    if not case.is_dir():
        print('STOP_MISSING_EXACT_CASE; do not substitute a similar case name')
        return site, 'MISSING_CASE'
    values = {key: query(case, key) for key in
              ['RUNDIR', 'DOUT_S_ROOT', 'RUN_STARTDATE', 'RUN_TYPE',
               'CONTINUE_RUN', 'STOP_N', 'RESUBMIT', 'CLM_ACCELERATED_SPINUP',
               'MPI_RUN_COMMAND']}
    print('CIME', json.dumps(values, sort_keys=True))
    run = Path(values['RUNDIR']) if values['RUNDIR'].startswith('/') and '$' not in values['RUNDIR'] else OUTPUT/name/'run'
    archive = Path(values['DOUT_S_ROOT']) if values['DOUT_S_ROOT'].startswith('/') and '$' not in values['DOUT_S_ROOT'] else OUTPUT/'archive'/name
    print('INSPECT_RUN', run, 'ARCHIVE', archive)
    rec = EXPERIMENT / receipt
    if rec.is_file():
        record = json.loads(rec.read_text())
        print('SUBMISSION_RECEIPT', rec)
        print(json.dumps({k:v for k,v in record.items() if
                          re.search(r'job|phase|stack|started|skip_preview', k)}, sort_keys=True))
    else:
        print('SUBMISSION_RECEIPT_MISSING', rec)
    for script in [case/'.case.run', case/'.case.st_archive', case/'.submit_options',
                   case/'env_batch.xml', case/'env_mach_specific.xml']:
        if script.is_file():
            print('RUNTIME_SUBMISSION_SETTINGS', script)
            for n, line in enumerate(script.read_text(errors='replace').splitlines(), 1):
                if re.search(r'ulimit|stack|propagate|srun|mpirun|skip_pnl|skip-preview', line, re.I):
                    print('SCRIPT_LINE', n, line[:800])
    documents = [case/'CaseDocs/lnd_in', run/'lnd_in']
    requested = []
    hashes = []
    for document in documents:
        if document.is_file():
            hashes.append(sha(document))
            parsed = history_fields(document.read_text(errors='replace'))
            print('EFFECTIVE_HISTORY', document, 'SHA256', hashes[-1], parsed)
            if not requested:
                requested = parsed
    print('CASE_DOCS_EQUALS_RUN', len(hashes) == 2 and hashes[0] == hashes[1])
    paths = accounting_logs(job, name)
    for folder in [run, case, case/'logs']:
        if folder.is_dir():
            for pattern in ['lnd.log.'+job+'.*', 'cesm.log.'+job+'.*',
                            'cpl.log.'+job+'.*', '*'+job+'*']:
                paths.extend(p for p in folder.glob(pattern) if p.is_file())
    paths = list(dict.fromkeys(paths))
    all_text = []
    registry = set()
    for path in paths[:24]:
        if not path.is_file():
            print('LOG_NOT_FOUND', path)
            continue
        # Do not interpret restart/history NetCDFs as text.
        if path.name.endswith('.nc'):
            continue
        text = log_text(path)
        all_text.append(text)
        size = path.stat().st_size
        print('LOG', path, 'BYTES', size, 'SHA256',
              sha(path) if size <= 24 * 1024 * 1024 else 'NOT_HASHED_LARGE_LOG')
        if path.name.startswith('lnd.log.'+job+'.'):
            registry.update(x.upper() for x in REGISTER.findall(text))
        hits = [(n, line) for n, line in enumerate(text.splitlines(), 1) if ERROR.search(line)]
        for n, line in hits[-22:]:
            print('ERROR_CONTEXT', n, line[:700])
        print('LOG_READ_BLOCK_TAIL', '\n'.join(text.splitlines()[-8:])[:5000])
    print('EXACT_FAILED_RUN_REGISTRY_COUNT', len(registry))
    print('FATES_ALTERNATIVES_REGISTERED', {f:f in registry for f in ['FATES_GPP', 'FATES_NPP']})
    for tape, fields in requested:
        for index, field in enumerate(fields, 1):
            base = field.split(':', 1)[0].strip().upper()
            state = 'REGISTERED' if base in registry else 'NOT_REGISTERED' if len(registry) > 100 else 'REGISTRY_UNAVAILABLE'
            print('REQUESTED_FIELD', tape, index, field, state)
    restarts = sorted(p.name for p in run.glob('*.r.*.nc')) if run.is_dir() else []
    pointers = sorted(p.name for p in run.glob('rpointer*')) if run.is_dir() else []
    rest = archive / 'rest'
    stamps = sorted(p.name for p in rest.iterdir() if p.is_dir()) if rest.is_dir() else []
    print('RESTART_ARTIFACTS', json.dumps(dict(run_restarts=restarts[-12:],
          run_pointers=pointers, archived_dates=stamps[-12:])))
    print('RESTART_CONTENTS_NOT_VALIDATED: existing artifacts prohibit blind cold restart')
    result = classify('\n'.join(all_text))
    print('DIAGNOSIS', site, result)
    return site, result


def self_test():
    trial = "&clm\nhist_fincl1='TLAI', ! 'GPP' is a comment\n 'FATES_GPP', 'NPP'\nhist_fincl2='FSH'\n/\n! 'ignored'\n"
    assert history_fields(trial) == [('hist_fincl1', ['TLAI','FATES_GPP','NPP']), ('hist_fincl2',['FSH'])]
    assert history_fields("hist_fincl(1)='TLAI'\n/\n") == [('hist_fincl(1)', ['TLAI'])]
    assert strip_comment("x='a!b' ! comment") == "x='a!b' "
    assert classify('htapes_fieldlist ERROR: GPP in fincl(4) for history tape 1 not found\nSIGKILL') == 'CONFIRMED_HISTORY_FIELD_NOT_REGISTERED:GPP'
    assert classify('ESMF_MeshCreate SIGSEGV') == 'SEGFAULT_CAUSE_UNCONFIRMED_NOT_PROOF_OF_LOW_STACK'
    assert classify('plain SIGKILL') == 'CAUSE_UNCONFIRMED_REVIEW_PRINTED_LOGS'
    assert len(TARGETS) == 5 and all(t[0] != 'IT-Noe' for t in TARGETS)
    print('SELF-TEST PASS: exact five cases; namelist comments/continuations; error precedence; no guessed stack cause')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--self-test', action='store_true')
    mode.add_argument('--diagnose', action='store_true')
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return 0
    print('BATCH02 FIVE FAILED AD400 READ-ONLY DIAGNOSIS; NO SUBMIT/CANCEL/EDIT')
    print('STACK_REFERENCE AmeriFlux_Batch01_10 Stage21: submit-shell soft stack >=65536 KB; '
          'same-shell inheritance and skip-preview-namelist; not a history-field repair')
    jobs = queue()
    results = []
    for target in TARGETS:
        try:
            results.append(diagnose(target, jobs))
        except (OSError, ValueError, RuntimeError) as exc:
            print('DIAGNOSTIC_ERROR', target[0], str(exc))
            results.append((target[0], 'DIAGNOSTIC_ERROR'))
    print('\nSUMMARY', json.dumps(dict(results), sort_keys=True))
    print('READ ONLY END: do not rerun old one-shot submit controllers or reset RESUBMIT=79.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
