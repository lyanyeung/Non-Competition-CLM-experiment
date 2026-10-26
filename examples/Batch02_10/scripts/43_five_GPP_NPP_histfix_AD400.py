#!/usr/bin/env python3
"""Isolated, one-shot history-output recovery of five proven Batch02 failures.

--audit-source/--verify/--status are read-only. --prepare creates NEW cases,
never submits. --start submits each prepared new case once for 80 x 5 AD years.
Old cases, pending archive jobs, meteorology, PFT/soil and executables are read
only. A failed/uncertain preparation or submission must never be repeated.
"""
import argparse
import configparser
from datetime import datetime, timezone
import getpass
import hashlib
import json
import os
from pathlib import Path
import re
import socket
import subprocess
import sys
import xml.etree.ElementTree as ET

BASE = Path('/iridisfs/scratch/ly3n24/CLM_FATES')
OUTPUT = Path('/scratch/ly3n24/CTSM_FATES_OUTPUTS')
EXPERIMENT = BASE/'experiments/NonCompetitionObserved22/Batch02_10'
CTSM = BASE/'CTSM'
OVERLAY = EXPERIMENT/'_private_ctsm_FATES_AD5_namelist_overlay_v1'
RECORDS = EXPERIMENT/'stage43_five_GPP_NPP_histfix_AD400'
BEFORE = ['TOTSOMC','TOTSOMN','TLAI','GPP','NPP','TWS','H2OSNO']
AFTER = ['TOTSOMC','TOTSOMN','TLAI','FATES_GPP','FATES_NPP','TWS','H2OSNO']
TARGETS = {
 'ES-LJu': ('4734425','ES-LJu_B02_FIXNC_AD400_BARE49_C3GRA31_SHRUB20_MET24',
  'ES-LJu_B02_FIXNC_MET24_GPPNPP_HISTFIX_AD400','2004-01-01',
  '224e0ab95befe3e809f3f7898adcf0abae93e382004ed483c8f82ce8c4c899dc',
  'lnd.log.4734425.261026-032356','e53a0e2a28b78dfc32ebf950f7182baf209fdafbd74ed545f82c4dae5883cc4b'),
 'DK-Sor': ('4734485','DK-Sor_B02_FIXNC_FOREST_PROXY_AD5',
  'DK-Sor_B02_FIXNC_FOREST_GPPNPP_HISTFIX_AD400','1996-01-01',
  '3f20956e1cb171f76714ae1580bf9a88c29679dc64c26b856dce5c2196962ba3',
  'lnd.log.4734485.261026-033333','308886396b2f0df6d073dbd112c1949e6ccc0bd244de81ad93207e303537d3f7'),
 'FR-FBn': ('4734487','FR-FBn_B02_FIXNC_FOREST_PROXY_AD5',
  'FR-FBn_B02_FIXNC_FOREST_GPPNPP_HISTFIX_AD400','2008-01-01',
  '8615638bdb81cba64b8d68c137846b1f61d9e6cea518f000ee8fd14fb8f806d8',
  'lnd.log.4734487.261026-033333','b1a0e602df2d5cf808e648e280a05fad764a52ac35893a27a547c6cf7057fa85'),
 'BE-Bra': ('4734696','BE-Bra_B02_FIXNC_FOREST_MET34_AD400',
  'BE-Bra_B02_FIXNC_MET34_GPPNPP_HISTFIX_AD400','1996-01-01',
  '6b46f2fae04058a6a25b7d74d9ad625891cf6ef60942c125e886443103731808',
  'lnd.log.4734696.261026-041133','bebb91da510217091c8e87596497d643a207660ba4b47d31f38372be64cca36e'),
 'CH-Lae': ('4734856','CH-Lae_B02_FIXNC_FOREST_MET36_AD400',
  'CH-Lae_B02_FIXNC_MET36_GPPNPP_HISTFIX_AD400','2004-01-01',
  '6adca5cbfe9c90ccdcca7fcca984a4283617d48396d23c5dae1b42a27bc26833',
  'lnd.log.4734856.261026-043534','98813aa6d67343524a8e3d7ad5c22151c5d1f640979d6b951b8ae1ed898a2faf'),
}
SCIENCE_XML = ('RUN_STARTDATE','CALENDAR','PTS_LAT','PTS_LON','PTS_DOMAINFILE',
 'CCSM_CO2_PPMV','ATM_NCPL','DATM_MODE','DATM_YR_START','DATM_YR_END',
 'DATM_YR_ALIGN','MPI_RUN_COMMAND','EXEROOT')
TAPE = re.compile(r'(?ims)^[ \t]*hist_fincl1[ \t]*=[ \t]*(.*?)(?=^[ \t]*[A-Za-z_]\w*[ \t]*=|^[ \t]*/[ \t]*$|\Z)')
QUOTES = re.compile(r"['\"]([^'\"]+)['\"]")
REGISTER = re.compile(r'(?m)^\s*\d+\s+([A-Za-z][A-Za-z0-9_]+)\s{2,}')
P_ACK = 'PREPARE_FIVE_BATCH02_HISTORY_ONLY_NEW_CASES_NO_SUBMIT'
S_ACK = 'SUBMIT_FIVE_BATCH02_HISTORY_FIXED_AD400_ONCE'
_HASH_CACHE = {}


def need(ok, why):
    if not ok:
        raise RuntimeError(str(why))


def call(args, cwd=None, timeout=120):
    p = subprocess.run(list(map(str,args)), cwd=cwd, text=True,
                       capture_output=True, timeout=timeout)
    need(p.returncode == 0, 'COMMAND FAILED '+repr(list(map(str,args)))+'\n'+(p.stdout+p.stderr)[-4000:])
    return p.stdout.strip()


def query(case, key):
    return call([case/'xmlquery',key,'--value'],cwd=case)


def change(case, key, value):
    call([case/'xmlchange',key+'='+str(value)],cwd=case)


def digest(path):
    path = Path(path)
    st = path.stat()
    key = (str(path.resolve()),st.st_size,st.st_mtime_ns,st.st_ino)
    if key not in _HASH_CACHE:
        h = hashlib.sha256()
        with path.open('rb') as handle:
            for chunk in iter(lambda:handle.read(1024*1024),b''):
                h.update(chunk)
        after = path.stat()
        need((st.st_size,st.st_mtime_ns,st.st_ino) == (after.st_size,after.st_mtime_ns,after.st_ino),
             'File changed during hashing: '+str(path))
        _HASH_CACHE[key] = h.hexdigest()
    return _HASH_CACHE[key]


def stamp():
    return datetime.now(timezone.utc).isoformat()


def write_json(path, data, exclusive=False):
    with path.open('x' if exclusive else 'w') as handle:
        json.dump(data,handle,indent=2,sort_keys=True)
        handle.write('\n');handle.flush();os.fsync(handle.fileno())


def paths(site):
    job, old, new, start, nml_sha, log_name, log_sha = TARGETS[site]
    return dict(site=site,job=job,old=BASE/'cases'/old,new=BASE/'cases'/new,
                oldrun=OUTPUT/old/'run',oldarch=OUTPUT/'archive'/old,
                run=OUTPUT/new/'run',arch=OUTPUT/'archive'/new,
                prep=RECORDS/(site+'_prepare.json'),submit=RECORDS/(site+'_submit.json'),
                start=start,nml_sha=nml_sha,log_name=log_name,log_sha=log_sha)


def fields(text):
    hits = list(TAPE.finditer(text))
    need(len(hits)==1,'Expected exactly one effective hist_fincl1')
    return QUOTES.findall(hits[0].group(1))


def fixed_user_nl(text):
    hits = list(TAPE.finditer(text))
    need(len(hits)<=1,'Duplicate user_nl_clm history list')
    replacement = 'hist_fincl1 = '+', '.join("'"+x+"'" for x in AFTER)+'\n'
    return text[:hits[0].start()]+replacement+text[hits[0].end():] if hits else text.rstrip()+'\n'+replacement


def compare_land(old, new, oldcase, newcase):
    def remove(text):
        hits = list(TAPE.finditer(text));need(len(hits)==1,'Ambiguous effective history tape')
        m=hits[0]
        return text[:m.start()]+'__HISTORY_TAPE_1__\n'+text[m.end():]
    a,b = remove(old),remove(new)
    if a==b:
        return
    aa,bb = a.splitlines(keepends=True),b.splitlines(keepends=True)
    need(len(aa)==len(bb),'Land input line count changed beyond history')
    changes = [(x,y) for x,y in zip(aa,bb) if x!=y]
    need(len(changes)==1,'Unexpected effective land differences beyond history: '+repr(changes[:3]))
    x,y = changes[0]
    need(x.startswith('!#     ') and y.startswith('!#     ') and
         all(token in x for token in ('build-namelist',' -infile ',' -envxml_dir ',' -config ')) and
         str(oldcase) in x and x.replace(str(oldcase),str(newcase))==y,
         'Non-history difference is not the proven CIME case-path comment')


def nml_value(text, key):
    hits = re.findall(r'(?im)^\s*'+re.escape(key)+r'\s*=\s*([^\r\n!]*)',text)
    need(len(hits)==1,'Missing/duplicate land key '+key)
    return hits[0].strip().rstrip(',').strip("'\"")


def empty_outputs(run, arch):
    for pattern in ('rpointer*','*.r.*.nc','*.h*.nc'):
        need(not list(run.glob(pattern)),'Existing output '+str(run/pattern)+'; no cold-start recovery')
    if arch.exists():
        need(not any(arch.rglob('*.nc')) and not any(arch.rglob('rpointer*')),
             'Existing archived output; validate continuation instead')


def queue_guard(p):
    text = call(['squeue','-h','-u',getpass.getuser(),'-o','%i|%j|%T'])
    for line in text.splitlines():
        vals = line.split('|')
        need(len(vals)==3,'Unrecognized Slurm queue record')
        jid,name,state = (x.strip() for x in vals)
        need(name not in ('run.'+p['new'].name,'st_archive.'+p['new'].name),
             'New history-fix case already queued/running: '+line)
        if name in ('run.'+p['old'].name,'st_archive.'+p['old'].name):
            need(jid==str(int(p['job'])+1) and name=='st_archive.'+p['old'].name and state=='PENDING',
                 'Source case has an unexpected active job: '+line)


def source_snapshot(p):
    old,run = p['old'],p['oldrun']
    need(old.is_dir() and not old.is_symlink() and run.is_dir(),'Exact failed source case/run missing')
    queue_guard(p)
    need(query(old,'RUNDIR')==str(run) and query(old,'DOUT_S_ROOT')==str(p['oldarch']),
         'Source run/archive root changed')
    acc = call(['sacct','-n','-P','-X','-j',p['job'],'--format=JobIDRaw,State'])
    need(any(line.split('|')[:2]==[p['job'],'FAILED'] for line in acc.splitlines()),
         'Pinned original failed job is not confirmed FAILED')
    doc=old/'CaseDocs/lnd_in';eff=run/'lnd_in';log=run/p['log_name']
    need(doc.is_file() and eff.is_file() and digest(doc)==digest(eff)==p['nml_sha'],
         'Operator-proven source land namelist SHA changed')
    need(log.is_file() and digest(log)==p['log_sha'],'Exact failed model log SHA changed')
    text=doc.read_text();logs=log.read_text(errors='replace')
    need(fields(text)==BEFORE and 'htapes_fieldlist ERROR: GPP in fincl(' in logs and
         'ERROR in histFileMod.F90 at line 899' in logs,'Source failure no longer matches proven history error')
    registry={x.upper() for x in REGISTER.findall(logs)}
    need(len(registry)>1000 and set(AFTER)<=registry and not {'GPP','NPP'}&registry,
         'Failed-run registry does not verify exactly the intended output repair')
    empty_outputs(run,p['oldarch'])
    xml={k:query(old,k) for k in SCIENCE_XML}
    need(xml['RUN_STARTDATE']==p['start'],'Source start date changed')
    for key,value in {'RUN_TYPE':'startup','CONTINUE_RUN':'false','CLM_ACCELERATED_SPINUP':'on',
                      'STOP_N':'5','REST_N':'5','RESUBMIT':'79','BUILD_COMPLETE':'true',
                      'STOP_OPTION':'nyears','REST_OPTION':'nyears','DOUT_S':'true',
                      'RESUBMIT_SETS_CONTINUE_RUN':'true'}.items():
        need(query(old,key).lower()==value,'Unexpected source CIME setting '+key)
    for key,value in {'use_fates':'.true.','use_fates_nocomp':'.true.',
                      'use_fates_fixed_biogeog':'.true.','use_fates_sp':'.false.',
                      'use_cn':'.false.','spinup_state':'2','finidat':''}.items():
        need(nml_value(text,key)==value,'Source FATES/AD setting changed '+key)
    stream=old/'CaseDocs/datm.streams.xml'
    need(stream.is_file() and digest(stream)==digest(run/'datm.streams.xml'),
         'Source selected DATM stream differs between CaseDocs/run')
    root=ET.parse(stream).getroot()
    blocks=[x for x in root.iter('stream_info') if x.get('name')=='CLM_USRDAT.UNSET']
    need(len(blocks)==1,'Source main 1PT CDEPS stream ambiguous')
    block=blocks[0];data=block.find('datafiles')
    need(data is not None,'No source annual forcing files')
    files=[Path((node.text or '').strip()) for node in data]
    first,last=int(block.findtext('year_first')),int(block.findtext('year_last'))
    need(len(files)==last-first+1 and len(set(files))==len(files),'Source selected year/file count mismatch')
    inputs={}
    for path in files+[Path(nml_value(text,'fsurdat')),Path(nml_value(text,'fates_paramfile')),
                       Path(xml['EXEROOT'])/'cesm.exe']:
        need(path.is_absolute() and path.is_file(),'Source model input missing '+str(path))
        inputs[str(path)]=digest(path)
    keep={}
    for relative in ('user_nl_clm','user_nl_datm_streams','CaseDocs/lnd_in','CaseDocs/datm.streams.xml',
                     'env_case.xml','LockedFiles/env_case.xml','CaseStatus'):
        path=old/relative
        need(path.is_file(),'Source case provenance missing '+relative)
        keep[relative]=digest(path)
    need(keep['env_case.xml']==keep['LockedFiles/env_case.xml'],'Source env_case lock differs')
    return dict(xml=xml,inputs=inputs,source_files=keep,datm_sha=digest(stream),
                source_job=p['job'],old_name=old.name,new_name=p['new'].name,
                overlay={str(OVERLAY/x):digest(OVERLAY/x) for x in ['bld/CLMBuildNamelist.pm','bld/build-namelist']})


def verify(p, saved):
    need(source_snapshot(p)==saved['source'],'Source inputs/config changed after preparation')
    new,run=p['new'],p['run']
    need(new.is_dir() and not new.is_symlink(),'New case missing or symlinked')
    for key,value in saved['source']['xml'].items():
        need(query(new,key)==value,'New scientific/runtime XML differs: '+key)
    for key,value in {'CASE':new.name,'RUN_TYPE':'startup','RUN_STARTDATE':p['start'],
                     'CLM_ACCELERATED_SPINUP':'on','RUNDIR':str(run),'DOUT_S_ROOT':str(p['arch']),
                     'STOP_N':'5','REST_N':'5','BUILD_COMPLETE':'true','STOP_OPTION':'nyears',
                     'REST_OPTION':'nyears','DOUT_S':'true','RESUBMIT_SETS_CONTINUE_RUN':'true'}.items():
        need(query(new,key).lower()==value.lower(),'New case setting differs: '+key)
    need(query(new,'RESUBMIT') in ('0','79'),'Unexpected new RESUBMIT')
    need(query(new,'CONTINUE_RUN').lower()=='false','New case has already advanced; use status')
    status_file=new/'CaseStatus'
    if status_file.is_file():
        need(not re.search(r'case\.submit (?:starting|success)|case\.run starting',
                           status_file.read_text(errors='replace')),
             'New case already has submission/launch history; inspect status, never repeat')
    need(digest(new/'env_case.xml')==digest(new/'LockedFiles/env_case.xml'),'New env_case lock differs')
    oldtext=(p['old']/'CaseDocs/lnd_in').read_text()
    for path in (new/'CaseDocs/lnd_in',run/'lnd_in'):
        text=path.read_text();need(fields(text)==AFTER,'New effective history fix missing')
        compare_land(oldtext,text,p['old'],new)
    need(digest(new/'CaseDocs/lnd_in')==digest(run/'lnd_in'),'New effective lnd_in files differ')
    need(fields((new/'user_nl_clm').read_text())==AFTER,'Durable new user_nl history fix missing')
    for path in (new/'CaseDocs/datm.streams.xml',run/'datm.streams.xml'):
        need(digest(path)==saved['source']['datm_sha'],'Selected source meteorology XML changed')
    for path in (new/'CaseDocs/nuopc.runconfig',run/'nuopc.runconfig'):
        text=path.read_text()
        for key,xmlkey in (('scol_lat','PTS_LAT'),('scol_lon','PTS_LON')):
            vals=re.findall(r'(?im)^\s*'+key+r'\s*=\s*([^\r\n]+)',text)
            need(len(vals)==1 and abs(float(vals[0])-float(saved['source']['xml'][xmlkey]))<0.0001,
                 'Effective coupler point differs: '+key)
    empty_outputs(run,p['arch'])
    if 'land_sha' in saved:
        need(digest(new/'CaseDocs/lnd_in')==saved['land_sha'],'Prepared new land input changed')
    return digest(new/'CaseDocs/lnd_in')


def prepare(p, source):
    need(not any(x.exists() or x.is_symlink() for x in [p['new'],p['run'].parent,p['run'],p['arch'],p['prep'],p['submit']]),
         'New case or prior attempt exists; do not rerun preparation')
    RECORDS.mkdir(parents=True,exist_ok=True)
    record=dict(phase='PREPARATION_ATTEMPT_UNCERTAIN',source=source,created_utc=stamp())
    write_json(p['prep'],record,exclusive=True)
    print('PREPARE BEGIN',p['site'],p['new'],'RECEIPT',p['prep'],'NO JOBS',flush=True)
    call([CTSM/'cime/scripts/create_clone','--case',p['new'],'--clone',p['old'],'--keepexe'],
         cwd=CTSM/'cime/scripts',timeout=700)
    new=p['new']
    for key,value in {'RUNDIR':p['run'],'DOUT_S_ROOT':p['arch'],'RUN_TYPE':'startup',
                      'CONTINUE_RUN':'FALSE','RUN_STARTDATE':p['start'],'STOP_OPTION':'nyears',
                      'STOP_N':'5','REST_OPTION':'nyears','REST_N':'5','RESUBMIT':'0',
                      'RESUBMIT_SETS_CONTINUE_RUN':'TRUE',
                      'CLM_ACCELERATED_SPINUP':'on','CLM_FORCE_COLDSTART':'on','DOUT_S':'TRUE'}.items():
        change(new,key,value)
    if not (new/'.case.run').is_file():
        call([new/'case.setup'],cwd=new,timeout=400)
    user=new/'user_nl_clm';user.write_text(fixed_user_nl(user.read_text()))
    lock=(new/'LockedFiles/env_case.xml').read_bytes()
    need((new/'env_case.xml').read_bytes()==lock,'New case lock already differs')
    original_root=query(new,'COMP_ROOT_DIR_LND')
    need(original_root=='$SRCROOT' or Path(original_root).resolve()==CTSM.resolve(),'Unexpected source tree')
    entries=[x.get('value') for x in ET.parse(new/'env_case.xml').getroot().iter('entry')
             if x.get('id')=='COMP_ROOT_DIR_LND']
    need(len(entries)==1 and isinstance(entries[0],str),'Cannot identify raw case source-root value')
    restore_root=entries[0]
    need(restore_root=='$SRCROOT' or Path(restore_root).resolve()==CTSM.resolve(),
         'Raw case source root is not the expected CTSM tree')
    try:
        change(new,'COMP_ROOT_DIR_LND',OVERLAY)
        call([new/'preview_namelists'],cwd=new,timeout=800)
    finally:
        change(new,'COMP_ROOT_DIR_LND',restore_root)
    need((new/'env_case.xml').read_bytes()==lock,'New case root/lock was not restored')
    # The source controllers installed approved MET24/MET34/MET36 selections
    # in effective CDEPS XML. Retain that exact selection in NEW files only.
    source_stream=(p['old']/'CaseDocs/datm.streams.xml').read_bytes()
    for target in (new/'CaseDocs/datm.streams.xml',p['run']/'datm.streams.xml'):
        need(target.is_file(),'CIME preview did not generate the new stream')
        target.write_bytes(source_stream)
    record['land_sha']=verify(p,record)
    record.update(phase='PREPARED_HISTORY_FIXED_NO_SUBMISSION',prepared_utc=stamp())
    write_json(p['prep'],record)
    print('PREPARE PASS',p['site'],new,'NO JOBS',flush=True)


def prepared(p):
    need(p['prep'].is_file(),'Prepare receipt missing')
    record=json.loads(p['prep'].read_text())
    need(record['phase']=='PREPARED_HISTORY_FIXED_NO_SUBMISSION','Uncertain preparation; do not repeat')
    verify(p,record)
    return record


def stack_guard():
    import resource
    soft,hard=resource.getrlimit(resource.RLIMIT_STACK)
    need(soft==resource.RLIM_INFINITY or soft>=65536*1024,
         'Submit-shell stack below65536KB; raise it in THIS shell before start')
    override=os.environ.get('SBATCH_PROPAGATE','')
    need(not override or {'ALL','STACK'}&set(override.upper().split(',')),
         'SBATCH_PROPAGATE excludes STACK; inspect before submission')
    return dict(soft_bytes=soft,hard_bytes=hard,host=socket.gethostname())


def start(p, record, stack):
    verify(p,record)
    queue_guard(p)
    need(not p['submit'].exists() and query(p['new'],'RESUBMIT')=='0','Submission already attempted')
    helptext=call([p['new']/'case.submit','--help'],cwd=p['new'])
    need('--skip-preview-namelist' in helptext,'Installed CIME skip-preview option missing')
    for line in (p['new']/'.case.run').read_text().splitlines():
        if line.lstrip().startswith('#SBATCH') and '--propagate' in line:
            need(re.search(r'--propagate(?:=|\s+)(?:ALL|STACK)\b',line),
                 'Batch script overrides stack propagation')
    attempt=dict(phase='SUBMISSION_ATTEMPT_UNCERTAIN',case=str(p['new']),
                 source_failed_job=p['job'],stack_at_submit=stack,started_utc=stamp(),
                 total_years=400,segments=80,land_sha=record['land_sha'])
    write_json(p['submit'],attempt,exclusive=True)
    print('SUBMIT ATTEMPT',p['site'],p['new'],'RECEIPT',p['submit'],flush=True)
    change(p['new'],'RESUBMIT','79')
    need(query(p['new'],'RESUBMIT')=='79','Uncertain RESUBMIT change; no retry')
    out=call([p['new']/'case.submit','--skip-preview-namelist'],cwd=p['new'],timeout=800)
    print(out[-6000:],flush=True)
    run=re.findall(r'Submitted job case\.run with id (\d+)',out)
    archive=re.findall(r'Submitted job case\.st_archive with id (\d+)',out)
    need(len(run)==len(archive)==1,'Submission IDs uncertain; never repeat start')
    options=configparser.RawConfigParser();options.read(p['new']/'.submit_options')
    persisted=options.has_section('SubmitOptions') and options.getboolean('SubmitOptions','skip_pnl',fallback=False)
    attempt.update(phase='SUBMITTED_AD400_NOT_COMPLETED' if persisted else 'SUBMITTED_PREVIEW_PERSISTENCE_UNCERTAIN',
                   run_jobid=run[0],archive_jobid=archive[0],skip_preview_persisted=persisted)
    write_json(p['submit'],attempt)
    need(persisted,'New jobs submitted but skip-preview persistence uncertain; inspect, never repeat')
    print('AD400 SUBMITTED',p['site'],'RUN',run[0],'ARCHIVE',archive[0],'80x5years; no years yet verified',flush=True)


def status(sites):
    callout=call(['squeue','-h','-u',getpass.getuser(),'-o','%i|%j|%T|%R'])
    for site in sites:
        p=paths(site)
        print('STATUS',site,'CASE',p['new'])
        if p['submit'].is_file():
            rec=json.loads(p['submit'].read_text());print(json.dumps(rec,sort_keys=True))
            if rec.get('run_jobid') and rec.get('archive_jobid'):
                print(call(['sacct','-j',rec['run_jobid']+','+rec['archive_jobid'],
                            '--format=JobIDRaw,State,ExitCode,Elapsed']))
        for line in callout.splitlines():
            if '|run.'+p['new'].name+'|' in line or '|st_archive.'+p['new'].name+'|' in line:
                print(line)
    print('STATUS ONLY; archived three-component restarts must establish AD400 completion')


def self_test():
    sample="hist_fincl1='TOTSOMC','TOTSOMN','TLAI','GPP','NPP','TWS','H2OSNO'\nhist_mfilt=12\n"
    need(fields(fixed_user_nl(sample))==AFTER,'History replacement regression')
    compare_land(sample,fixed_user_nl(sample),Path('/old'),Path('/new'))
    try:
        compare_land(sample,fixed_user_nl(sample).replace('hist_mfilt=12','hist_mfilt=24'),Path('/old'),Path('/new'))
    except RuntimeError:
        pass
    else:
        raise AssertionError('Scientific change was accepted')
    need(len(TARGETS)==5 and 'IT-Noe' not in TARGETS and 5*80==400,'Target scope/count')
    print('SELF-TEST PASS: five exact proven failures; history-only delta; 80x5 AD400; no writes')


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    modes=ap.add_mutually_exclusive_group(required=True)
    for mode in ('self-test','audit-source','prepare','verify','start','status'):
        modes.add_argument('--'+mode,action='store_true')
    ap.add_argument('--sites',nargs='+',choices=list(TARGETS),default=list(TARGETS))
    ap.add_argument('--confirm',default='')
    args=ap.parse_args()
    try:
        if args.self_test:
            self_test();return 0
        sites=list(dict.fromkeys(args.sites))
        if args.status:
            need(not args.confirm,'No confirmation for status');status(sites);return 0
        ps=[paths(s) for s in sites]
        if args.audit_source:
            need(not args.confirm,'No confirmation for audit')
            for p in ps:
                snap=source_snapshot(p);print('SOURCE AUDIT PASS',p['site'],'annual/input files',len(snap['inputs']))
        elif args.prepare:
            need(args.confirm==P_ACK,'Prepare requires --confirm '+P_ACK)
            sources=[]
            for p in ps:
                print('SOURCE CHECK',p['site'],flush=True)
                sources.append(source_snapshot(p))
            for p in ps:
                need(not any(x.exists() or x.is_symlink() for x in [p['new'],p['run'].parent,p['run'],p['arch'],p['prep'],p['submit']]),
                     'Existing target/attempt for '+p['site']+'; use only remaining --sites')
            for p,snap in zip(ps,sources):
                prepare(p,snap)
        elif args.verify:
            need(not args.confirm,'No confirmation for verify')
            for p in ps:
                prepared(p);print('VERIFY PASS',p['site'])
        else:
            need(args.confirm==S_ACK,'Start requires --confirm '+S_ACK)
            stack=stack_guard();records=[prepared(p) for p in ps]
            for p in ps:
                need(not p['submit'].exists() and query(p['new'],'RESUBMIT')=='0','Existing submit attempt '+p['site'])
            for p,rec in zip(ps,records):
                start(p,rec,stack)
        return 0
    except (OSError,ValueError,RuntimeError,subprocess.TimeoutExpired) as exc:
        print('STOP:',str(exc),file=sys.stderr)
        print('Preserve receipts/partial cases. Do not repeat stateful actions after an uncertain result.',file=sys.stderr)
        return 1


if __name__=='__main__':
    sys.exit(main())
