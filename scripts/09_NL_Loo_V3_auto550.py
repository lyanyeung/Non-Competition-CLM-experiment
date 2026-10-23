#!/usr/bin/env python3
"""NL-Loo V3 single-launch 50 normal -> 200 AD -> 300 post-AD.

One initial launch, then an hourly Slurm watcher handles stage handoffs and
stops safely on failed jobs / invalid checkpoints. All V3 paths are isolated.
Use 'preflight' before 'launch'. No deletion or modification of V1/V2.
"""
from __future__ import annotations
import argparse, fcntl, hashlib, json, os, re, shutil, subprocess, sys
from datetime import datetime, timezone
from pathlib import Path

U = 'ly3n24'
ROOT = Path(f'/iridisfs/scratch/{U}/CLM_FATES')
CTSM = ROOT/'CTSM'
BASE = ROOT/'cases/NL-Loo_OBSPFT_NC_V2_PRE50'
CS = CTSM/'cime/scripts'
OUT = Path(f'/scratch/{U}/CTSM_FATES_OUTPUTS')
WORK = Path.home()/'NL_Loo_V3_auto550'
WATCH = WORK/'watch.sh'
STATE = WORK/'controller.json'
LOCK = WORK/'controller.lock'
STOP = WORK/'STOP'
SURF = ROOT/'experiments/NonCompetitionObserved22/NL-Loo/surface/surfdata_NL-Loo_obsPFT_grass_proxy_v1.nc'
SURF_HASH = '81ca2872a9758325c0a18121ad060496ce47745a590264353b3cbcfcdcc95920'
PARAM = CTSM/'src/fates/parameter_files/fates_params_default.json'
PARAM_HASH = '0819f8fddcb3566f6209f72bb1159a3161d03c8225a1464727b1d2b21aec6c04'
REV = 'd5ea9d0136530370a62ef267ccfaff6f001ef914'
P = ('PRE50','AD200','POST300')
NAME = {x:f'NL-Loo_OBSPFT_NC_V3_{x}' for x in P}
CASE = {x:ROOT/'cases'/NAME[x] for x in P}
RUN = {x:OUT/NAME[x]/'run' for x in P}
ARCH = {x:OUT/'archive'/NAME[x] for x in P}
BEGIN = {'PRE50':1997, 'AD200':2047, 'POST300':2247}
END = {'PRE50':2047, 'AD200':2247, 'POST300':2547}
MODE = {'PRE50':'off', 'AD200':'on', 'POST300':'off'}
STEPS = {'PRE50':10, 'AD200':40, 'POST300':60}
SOURCE = {'AD200':'PRE50', 'POST300':'AD200'}
CONFIRM = 'LAUNCH_NL_LOO_FRESH_V3_550_YEARS'


def die(s): raise RuntimeError(str(s))
def utc(): return datetime.now(timezone.utc).isoformat()
def cmd(a,cwd=None,quiet=True,timeout=180):
    v=subprocess.run([str(t) for t in a],cwd=cwd,text=True,timeout=timeout,
                     capture_output=quiet,check=False)
    if v.returncode: die(f"{' '.join(map(str,a))}: rc={v.returncode}; {v.stderr[-900:] if quiet else 'inspect log'}")
    return v.stdout.strip() if quiet else ''
def xq(stage,key): return cmd(['./xmlquery',key,'--value'],CASE[stage])
def change(stage,key,val): cmd(['./xmlchange',f'{key}={val}'],CASE[stage])
def hashfile(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for a in iter(lambda:f.read(1024*1024),b''):h.update(a)
    return h.hexdigest()
def slurm(stage):
    s=cmd(['squeue','-u',U,'-h','-o','%i|%j|%T'])
    return [l for l in s.splitlines() if len(l.split('|'))==3 and
            l.split('|')[1] in ('run.'+NAME[stage],'st_archive.'+NAME[stage])]
def all_old_jobs():
    s=cmd(['squeue','-u',U,'-h','-o','%i|%j|%T'])
    return [l for l in s.splitlines() if re.search(r'\b(?:run|st_archive)\.NL-Loo_OBSPFT_NC_(?:PRE50|V2_PRE50)\b',l)]
def quota():
    # Some IRIDIS installs vary the myfiles formatting: report but stop if >85% parsed.
    r=cmd(['myfiles'])
    for exp in [r'Scratch number of files used:\s*([\d,]+)/([\d,]+)',
                r'Scratch.*?([\d,]+)\s*/\s*([\d,]+)\s*files']:
        m=re.search(exp,r,re.I|re.S)
        if m:
            use,limit=(int(z.replace(',','')) for z in m.groups())
            if use/limit >= .85:die(f'High Scratch inode use: {use}/{limit}')
            print(f'SCRATCH INODES {use}/{limit}',flush=True);return
    print('WARNING: myfiles inode values not parsed; review quotas manually',flush=True)
def validate_base():
    if not BASE.is_dir():die('V2 case (clone template) absent')
    if not SURF.is_file() or hashfile(SURF)!=SURF_HASH:die('Surface missing/changed')
    if not PARAM.is_file() or hashfile(PARAM)!=PARAM_HASH:die('FATES JSON missing/changed')
    if cmd(['git','rev-parse','HEAD'],CTSM)!=REV:die('CTSM source revision changed')
    if all_old_jobs():die('Old V1/V2 NL-Loo jobs still active; inspect before launch')
    if cmd(['./xmlquery','BUILD_COMPLETE','--value'],BASE).lower()!='true':die('Base executable not built')
    if not (Path(cmd(['./xmlquery','EXEROOT','--value'],BASE))/'cesm.exe').is_file():die('Base executable missing')
    if 'use_fates_nocomp = .true.' not in (BASE/'CaseDocs/lnd_in').read_text():die('Base no-comp setting missing')
    quota()
def nml_get(s,key):
    m=re.search(r'(?im)^\s*'+re.escape(key)+r'\s*=\s*(.*?)\s*$',s)
    return m.group(1).strip().strip("'\"") if m else None
def check(stage):
    c=CASE[stage]
    if not (c/'CaseDocs/lnd_in').is_file():die(f'{stage}: land namelist missing')
    n=(c/'CaseDocs/lnd_in').read_text()
    for k,expected in [('use_fates','.true.'),('use_fates_sp','.false.'),
      ('use_fates_fixed_biogeog','.true.'),('use_fates_nocomp','.true.'),('fsurdat',str(SURF))]:
        if (nml_get(n,k) or '').lower()!=expected.lower():die(f'{stage}: {k} differs')
    if stage=='AD200' and nml_get(n,'spinup_state') not in ('1','2'):
        die('AD not selected in land namelist (spinup_state missing/invalid)')
    if stage!='AD200' and nml_get(n,'spinup_state') not in (None,'0'):
        die('Normal stage spinup_state not 0')
    for k,v in [('CLM_ACCELERATED_SPINUP',MODE[stage]),('STOP_OPTION','nyears'),
                ('STOP_N','5'),('REST_OPTION','nyears'),('REST_N','5'),
                ('RUNDIR',str(RUN[stage])),('DOUT_S_ROOT',str(ARCH[stage]))]:
        if xq(stage,k).lower()!=v.lower():die(f'{stage}: {k} mismatch')
    if xq(stage,'BUILD_COMPLETE').lower()!='true':die(f'{stage}: unbuilt case')
    if xq(stage,'EXEROOT')!=cmd(['./xmlquery','EXEROOT','--value'],BASE):die('Executable changed')
    if not (c/'.case.run').is_file() or not (c/'case.st_archive').is_file():die('Case setup missing')
    if re.search(r'(?im)^#SBATCH .*--exclusive',(c/'.case.run').read_text()):die('Exclusive allocation not allowed')
    if 'NL-Loo_DATM_1997.nc' not in (c/'user_nl_datm_streams').read_text():die('Different DATM stream')
def checkpoint(stage,year):
    stamp=f'{year:04d}-01-01-00000'
    folder=ARCH[stage]/'rest'/stamp
    if not folder.is_dir():return None
    for comp in ('cpl','datm','clm2'):
        f=folder/f'{NAME[stage]}.{comp}.r.{stamp}.nc'
        if not f.is_file() or f.stat().st_size<1024:die(f'Incomplete checkpoint: {f}')
    if not list(folder.glob('rpointer.*')):die(f'No archive restart pointers: {folder}')
    return folder
def spinup_value(stage,year):
    f=ARCH[stage]/'rest'/f'{year:04d}-01-01-00000'/f'{NAME[stage]}.clm2.r.{year:04d}-01-01-00000.nc'
    from netCDF4 import Dataset
    with Dataset(f) as d:
        import numpy as np
        if 'spinup_state' in d.variables:
            return int(np.asarray(d.variables['spinup_state'][:]).reshape(-1)[0])
        if 'spinup_state' in d.ncattrs():
            return int(d.getncattr('spinup_state'))
        die('spinup_state missing from restart variables/attributes; version audit needed')
def complete(stage,year):
    if slurm(stage):return False
    if not checkpoint(stage,year):return False
    log=(CASE[stage]/'CaseStatus').read_text(errors='replace')
    if not re.search(r'case\.run success',log,re.I) or not re.search(r'(?:case\.)?st_archive success',log,re.I):
        die(f'{stage}: checkpoint exists but case/archiver success not recorded')
    actual=spinup_value(stage,year)
    if stage=='AD200' and actual not in (1,2):die(f'AD restart spinup_state={actual}')
    if stage!='AD200' and actual!=0:die(f'Normal restart spinup_state={actual}')
    return True

def prepare(stage):
    if any(p.exists() for p in (CASE[stage],ARCH[stage],RUN[stage])):
        die(f'{stage}: V3 case/run/archive already exist, do not overwrite')
    if stage!='PRE50' and not complete(SOURCE[stage],END[SOURCE[stage]]):
        die(f'Previous {SOURCE[stage]} phase not completed')
    quota()
    cmd([CS/'create_clone','--case',CASE[stage],'--clone',BASE,'--keepexe'],CS,quiet=False)
    cfg={'RUN_TYPE':'startup' if stage=='PRE50' else 'hybrid',
         'CONTINUE_RUN':'FALSE','RUN_STARTDATE':f'{BEGIN[stage]:04d}-01-01',
         'CLM_ACCELERATED_SPINUP':MODE[stage], 'STOP_OPTION':'nyears','STOP_N':'5',
         'REST_OPTION':'nyears','REST_N':'5',
         'RESUBMIT':'9' if stage=='PRE50' else '0',
         'DOUT_S':'TRUE','RUNDIR':str(RUN[stage]),'DOUT_S_ROOT':str(ARCH[stage]),
         'MPI_RUN_COMMAND':'srun --mpi=pmix --ntasks=1 --cpus-per-task=1 --cpu-bind=cores'}
    if stage!='PRE50':
        prev=SOURCE[stage]
        cfg.update({'RUN_REFCASE':NAME[prev],'RUN_REFDATE':f'{END[prev]:04d}-01-01',
                    'GET_REFCASE':'FALSE','CLM_FORCE_COLDSTART':'off'})
    for k,v in cfg.items():change(stage,k,v)
    if stage!='PRE50':
        prev=SOURCE[stage];year=END[prev];ref=checkpoint(prev,year)
        if ref is None:die('Reference restart disappeared')
        RUN[stage].mkdir(parents=True,exist_ok=True)
        if any(RUN[stage].iterdir()):die('Target RUNDIR unexpectedly nonempty')
        for f in ref.iterdir():
            if f.is_file() and (f.name.startswith('rpointer.') or '.r.' in f.name):
                shutil.copy2(f,RUN[stage]/f.name)
        stamp=f'{year:04d}-01-01-00000'
        for f in list(RUN[stage].glob('rpointer.*')):
            if f.name.endswith('.'+stamp):
                new=RUN[stage]/f.name[:-len('.'+stamp)]
                if not new.exists():shutil.copy2(f,new)
        for f in RUN[stage].glob('rpointer.*'):
            if f.name.endswith('.'+stamp):continue
            for line in f.read_text(errors='replace').splitlines():
                filename=line.strip().strip("'\"")
                if filename.endswith('.nc') and not (RUN[stage]/Path(filename).name).is_file():
                    die(f'Dangling restart pointer: {f.name} => {filename}')
        fin=RUN[stage]/f'{NAME[prev]}.clm2.r.{stamp}.nc'
        if not fin.is_file():die('Missing finidat')
        n=CASE[stage]/'user_nl_clm'
        original=n.read_text()
        if re.search(r'(?m)^\s*finidat\s*=',original):
            die('Inherited finidat already exists; must inspect before replacing')
        n.write_text(original.rstrip()+f"\nfinidat = '{fin}'\n")
    if not (CASE[stage]/'.case.run').is_file():cmd(['./case.setup'],CASE[stage],quiet=False)
    cmd(['./preview_namelists'],CASE[stage],quiet=False)
    cmd(['./check_input_data'],CASE[stage],quiet=False)
    check(stage)
    return CASE[stage]

def submit(stage,phase):
    check(stage)
    if slurm(stage):die(f'{stage}: Slurm jobs already exist')
    log=(CASE[stage]/'CaseStatus').read_text(errors='replace')
    if phase=='first' and 'case.submit starting' in log:die('Already submitted first segment')
    marker=CASE[stage]/f'V3_{phase}_submission_attempt.json'
    if marker.exists():die(f'Submission already attempted: {marker}')
    marker.write_text(json.dumps({'phase':phase,'attempted':utc()})+'\n')
    cmd(['./case.submit'],CASE[stage],quiet=False)
    print('SUBMITTED',stage,phase,flush=True)

def continuation(stage):
    if not complete(stage,BEGIN[stage]+5):die('First 5y smoke checkpoint not ready')
    if slurm(stage):die('Stage has live jobs')
    if xq(stage,'RESUBMIT')!='0':die('Expected single smoke job before continuation')
    # Some CIME short-term archivers MOVE the completed checkpoint out of RUN.
    # Restore ONLY files for this verified first five-year checkpoint; never
    # overwrite an existing local restart or pointer with different content.
    ref=checkpoint(stage,BEGIN[stage]+5)
    RUN[stage].mkdir(parents=True,exist_ok=True)
    for f in ref.iterdir():
        if not f.is_file() or not (f.name.startswith('rpointer.') or '.r.' in f.name):
            continue
        dest=RUN[stage]/f.name
        if dest.exists():
            if hashfile(dest)!=hashfile(f):die(f'Conflicting staged restart: {dest}')
        else:
            shutil.copy2(f,dest)
    stamp=f'{BEGIN[stage]+5:04d}-01-01-00000'
    for f in list(RUN[stage].glob('rpointer.*')):
        if f.name.endswith('.'+stamp):
            dest=RUN[stage]/f.name[:-len('.'+stamp)]
            if dest.exists():
                if hashfile(dest)!=hashfile(f):die(f'Conflicting live pointer: {dest}')
            else:shutil.copy2(f,dest)
    if not list(RUN[stage].glob('rpointer.*')):
        die('Cannot safely stage the first 5-year restart pointers')
    change(stage,'CONTINUE_RUN','TRUE')
    change(stage,'RESUBMIT',str(STEPS[stage]-2))
    submit(stage,'remaining')

def load(): return json.loads(STATE.read_text())
def save(d):
    t=STATE.with_suffix('.tmp');t.write_text(json.dumps(d,indent=2)+'\n');t.replace(STATE)
def once(d,label,callback):
    if label in d['actions']:
        if d['actions'][label]=='DONE':return
        die(f'Previous {label} attempted but uncertain; inspect case instead of repeating')
    d['actions'][label]='ATTEMPTED';save(d)
    callback()
    d['actions'][label]='DONE';save(d)
def next_watch(d):
    if STOP.exists() or not d['armed']:return
    jid=cmd(['sbatch','--parsable','--begin=now+1hour',WATCH],WORK)
    d['watch_job']=jid;save(d)
    print('WATCH_SCHEDULED',jid,flush=True)
def tick(d):
    if not d['armed'] or STOP.exists():return False
    validate_base()
    if not complete('PRE50',2047):
        if not slurm('PRE50'):die('PRE50 has neither live jobs nor final verified checkpoint')
        print('WAIT PRE50',flush=True);return True
    if 'AD200_first' not in d['actions']:
        once(d,'AD200_first',lambda:(prepare('AD200'),submit('AD200','first')))
        return True
    if slurm('AD200'):return True
    if not complete('AD200',2247):
        if d['actions'].get('AD200_remaining')=='DONE':
            die('AD200 continuation stalled or failed before year 2247')
        if complete('AD200',2052):
            once(d,'AD200_remaining',lambda:continuation('AD200'))
            return True
        die('AD first segment stalled without checkpoint; stopping')
    if 'POST300_first' not in d['actions']:
        once(d,'POST300_first',lambda:(prepare('POST300'),submit('POST300','first')))
        return True
    if slurm('POST300'):return True
    if not complete('POST300',2547):
        if d['actions'].get('POST300_remaining')=='DONE':
            die('POST300 continuation stalled or failed before year 2547')
        if complete('POST300',2252):
            once(d,'POST300_remaining',lambda:continuation('POST300'))
            return True
        die('POST first segment stalled without checkpoint; stopping')
    d['armed']=False;d['complete_at']=utc();save(d)
    print('COMPLETE: all three phases reach model date 2547',flush=True)
    return False

def makewatch():
    script=f'''#!/usr/bin/env bash
#SBATCH --job-name=NL-Loo-V3-watch
#SBATCH --partition=batch
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=1G
#SBATCH --time=00:20:00
#SBATCH --output={WORK}/watch-%j.log
set -euo pipefail
exec '{sys.executable}' '{Path(__file__).resolve()}' tick
'''
    if WATCH.exists() and WATCH.read_text()!=script:die('Existing watchdog differs')
    WATCH.write_text(script);WATCH.chmod(0o700)

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('action',choices=['preflight','launch','tick','status','disarm'])
    ap.add_argument('--confirm',default='')
    a=ap.parse_args()
    if a.action=='preflight':
        validate_base()
        for p in P:print(p,'exists=',CASE[p].exists(),'jobs=',slurm(p))
        if STATE.exists() or STOP.exists() or any(CASE[p].exists() or RUN[p].exists() or ARCH[p].exists() for p in P):
            print('NOT READY TO LAUNCH: some V3 controller/case/output state exists; inspect status.')
        else:
            print('PREFLIGHT PASS: fresh V3 case namespace is free; launch NOT performed.')
            print('NEXT COMMAND: python scripts/09_NL_Loo_V3_auto550.py launch --confirm LAUNCH_NL_LOO_FRESH_V3_550_YEARS')
            print('CAUTION: stage transitions are guarded by runtime checks but remain scientifically untested on this local CTSM-FATES build.')
        return
    if a.action=='status':
        if STATE.exists():print(STATE.read_text())
        for p in P:print(p,'exists=',CASE[p].exists(),'jobs=',slurm(p))
        return
    if a.action=='disarm':
        WORK.mkdir(parents=True,exist_ok=True);STOP.write_text('operator stopped watcher\n')
        print('Future watcher actions disarmed; running model jobs NOT canceled')
        return
    if a.action=='launch':
        if a.confirm!=CONFIRM:die('Requires --confirm '+CONFIRM)
        validate_base()
        if STATE.exists() or STOP.exists() or any(CASE[p].exists() or RUN[p].exists() or ARCH[p].exists() for p in P):
            die('V3 files/ledger already exist: no duplicate launch')
        WORK.mkdir(parents=True,exist_ok=True)
        makewatch()
        d={'armed':False,'created':utc(),'actions':{}}
        save(d)
        try:
            once(d,'PRE50_first',lambda:(prepare('PRE50'),submit('PRE50','first')))
            d['armed']=True;save(d);next_watch(d)
        except Exception:
            d['armed']=False;save(d);raise
        print('V3 PIPELINE LAUNCHED. PRE50 CIME has 9 resubmissions; watchdog will handle AD/POST.')
        return
    if a.action=='tick':
        if not STATE.exists():die('No controller state; not launched')
        with LOCK.open('a') as fh:
            fcntl.flock(fh,fcntl.LOCK_EX|fcntl.LOCK_NB)
            d=load()
            try:
                if tick(d):next_watch(d)
            except Exception as ex:
                d['armed']=False;d['error']={'at':utc(),'message':str(ex)};save(d)
                raise

if __name__=='__main__':main()