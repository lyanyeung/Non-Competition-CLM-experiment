#!/usr/bin/env python3
"""Batch04 FIXNC-only CIME cases, direct AD400, Batch01 machinery.

prepare: NEW cases and namelist previews, no Slurm; completed preparations
are verified/reused, interrupted ones held. submit-ad400: explicit case
selection, once-only ledger + live stack/Slurm guard before case.submit.
audit-ad400: only complete 80-segment archived integrations pass.

No AD5 test/handoff. Each case starts 80x5 years with RESUBMIT=79.
Operator correction: only fixed biogeography/no competition is authorized.
FULL preparation/submission is refused even through direct function calls.
Existing FULL cases are handled only by the separate cancellation script.
"""
from __future__ import annotations
import argparse
import configparser
import copy
import csv
from datetime import datetime, timezone
import getpass
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import xml.etree.ElementTree as ET
import numpy as np

HERE = Path(__file__).resolve().parent
B = Path('/iridisfs/scratch/ly3n24/CLM_FATES')
CTSM = B/'CTSM'
OUT = Path('/scratch/ly3n24/CTSM_FATES_OUTPUTS')
EXP = B/'experiments/NonCompetitionObserved22/AmeriFlux_Batch04_10'
STATE = EXP/'direct_AD400_case_records_v1'
REFERENCE = B/'cases/CA-Ca3_AMF_FIXNC_AD400_UTC_V2_PTS_AD5'
OVERLAY = B/'experiments/NonCompetitionObserved22/Batch01_10/_private_ctsm_FATES_AD400_namelist_overlay'
PARAM = CTSM/'src/fates/parameter_files/fates_params_default.json'
PARAM_SHA = '0819f8fddcb3566f6209f72bb1159a3161d03c8225a1464727b1d2b21aec6c04'
SHARED_BLOB = '698f2396aba8e11cbbbdd58c74ad221e6b7e7038'
SITES = ('US-Rpf','US-SP1','US-SRG','US-SRM','US-Seg','US-Ses','US-Slt','US-Syv','US-Ton','US-Uaf')
ARMS = ('FIXNC',)
ACK_PREP = 'PREPARE_BATCH04_DIRECT_AD400_CASES_NO_SLURM'
ACK_SUBMIT = 'SUBMIT_BATCH04_DIRECT_AD400_80x5_WITH_STACK_GUARD_ONCE'
METMAP = {'PRECTmms':'Faxa_precn','FSDS':'Faxa_swdn','ZBOT':'Sa_z',
          'TBOT':'Sa_tbot','WIND':'Sa_wind','QBOT':'Sa_shum','PSRF':'Sa_pbot','FLDS':'Faxa_lwdn'}
HISTORY = ('TOTSOMC','TOTSOMN','TLAI','FATES_GPP','FATES_NPP','TWS','H2OSNO')
_HASHES = {}


def need(ok, msg):
    if not ok:
        raise RuntimeError(str(msg))


def load_module(file, name):
    spec = importlib.util.spec_from_file_location(name, file)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def sha(path):
    path = Path(path)
    a = path.stat()
    key = (str(path.resolve()),a.st_size,a.st_mtime_ns,a.st_ino)
    if key not in _HASHES:
        h = hashlib.sha256()
        with path.open('rb') as f:
            for block in iter(lambda:f.read(4<<20),b''):
                h.update(block)
        z = path.stat()
        need((a.st_size,a.st_mtime_ns,a.st_ino) == (z.st_size,z.st_mtime_ns,z.st_ino), 'File changed during hashing')
        _HASHES[key] = h.hexdigest()
    return _HASHES[key]


def j(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def save(path, data, exclusive=False):
    path = Path(path)
    with path.open('x' if exclusive else 'w',encoding='utf-8') as f:
        json.dump(data,f,indent=2,allow_nan=False)
        f.write('\n')


def run(args, cwd=None, timeout=180):
    p = subprocess.run(list(map(str,args)),cwd=cwd,text=True,capture_output=True,timeout=timeout)
    need(p.returncode == 0, 'COMMAND FAILED '+repr(list(map(str,args)))+'\n'+(p.stdout+p.stderr)[-5000:])
    return p.stdout.strip()


def q(case,key):
    return run([case/'xmlquery',key,'--value'],cwd=case,timeout=60)


def xc(case,key,value):
    run([case/'xmlchange',key+'='+str(value)],cwd=case,timeout=60)


def name(site,arm):
    return site+'_AMF_B04_'+arm+'_AD400_BASETA_V1'


def paths(site,arm):
    n = name(site,arm)
    return B/'cases'/n,OUT/n/'run',OUT/'archive'/n,STATE/(n+'.json')


def nml(text,key):
    pattern = r'(?ims)^[ \t]*'+re.escape(key)+r'[ \t]*=[ \t]*(.*?)(?=^[ \t]*[A-Za-z_]\w*[ \t]*=|^[ \t]*/|\Z)'
    got = re.findall(pattern,text)
    need(len(got) <= 1, 'Duplicate namelist key '+key)
    return got[0].split('!')[0].strip().rstrip(',').strip().strip("'\"") if got else None


def setnml(text,key,value):
    pattern = r'(?ims)^[ \t]*'+re.escape(key)+r'[ \t]*=[ \t]*(.*?)(?=^[ \t]*[A-Za-z_]\w*[ \t]*=|^[ \t]*/|\Z)'
    need(len(re.findall(pattern,text)) <= 1,'Duplicate user namelist '+key)
    replacement = key+' = '+value+'\n'
    return re.sub(pattern,lambda _:replacement,text) if re.search(pattern,text) else text.rstrip()+'\n'+replacement


def settings(row,case,rundir,archive,co2):
    first = row['first_year']
    return {'RUN_TYPE':'startup','RUN_STARTDATE':f'{first}-01-01','CALENDAR':'NO_LEAP',
        'CONTINUE_RUN':'FALSE','CLM_FORCE_COLDSTART':'on','CLM_ACCELERATED_SPINUP':'on',
        'STOP_OPTION':'nyears','STOP_N':'5','REST_OPTION':'nyears','REST_N':'5',
        'RESUBMIT':'79','RESUBMIT_SETS_CONTINUE_RUN':'TRUE','DOUT_S':'TRUE',
        'RUNDIR':str(rundir),'DOUT_S_ROOT':str(archive),
        'DATM_MODE':'1PT','DATM_YR_START':str(first),'DATM_YR_END':str(row['last_year']),
        'DATM_YR_ALIGN':str(first),'ATM_NCPL':'48','CLM_USRDAT_NAME':'UNSET',
        'PTS_LAT':str(row['model_tower_coordinates'][0]),'PTS_LON':str(row['model_tower_coordinates'][1]%360),
        'PTS_DOMAINFILE':'UNSET','CCSM_CO2_PPMV':str(co2),
        'CLM_BLDNML_OPTS':'--bgc fates --no-megan --no-drydep --no-fire_emis',
        'MPI_RUN_COMMAND':'srun --mpi=pmix --ntasks=1 --cpus-per-task=1 --cpu-bind=cores'}


def flags(arm):
    need(arm == 'FIXNC','FULL is disabled: operator authorized FIXNC only')
    fixed = '.true.'
    return {'use_fates':'.true.','use_fates_sp':'.false.','use_cn':'.false.',
            'use_fates_fixed_biogeog':fixed,'use_fates_nocomp':fixed,'spinup_state':'2'}


def parameter_data(base,profile):
    data = copy.deepcopy(base)
    matrix = np.asarray(data['parameters']['fates_hlm_pft_map']['data'],dtype=float)
    need(matrix.shape == (14,14),'Installed 14x14 host/FATES map required')
    if profile == 'ARCTIC_PURE':
        matrix[8,:] = 0
        matrix[8,9] = 1
        matrix[10,:] = 0
        matrix[10,10] = 1
    else:
        need(profile == 'DEFAULT14','Unknown site mapping profile')
    data['parameters']['fates_hlm_pft_map']['data'] = matrix.tolist()
    return data


def pft_check(row,data):
    from netCDF4 import Dataset
    need(sha(row['shared_surface_path']) == row['shared_surface_sha256'],'Shared PFT surface SHA drift')
    with Dataset(row['shared_surface_path']) as nc:
        host = np.ma.filled(nc['PCT_NAT_PFT'][:],np.nan).ravel()
        need(host.size == 15 and abs(float(nc['PCT_NATVEG'][:].ravel()[0])-100)<1e-5,'NATVEG100 / host15 required')
        for key in ('PCT_CROP','PCT_LAKE','PCT_WETLAND','PCT_GLACIER','PCT_URBAN'):
            if key in nc.variables:
                need(np.all(nc[key][:] == 0),'Unexpected non-NATVEG landunit '+key)
    matrix = np.asarray(data['parameters']['fates_hlm_pft_map']['data'],dtype=float)
    got = host[1:]@matrix
    source = {r['site']:r for r in csv.DictReader((HERE.parent/'data/AMF_BATCH04_10_PFT_SOURCE_SNAPSHOT_20261026.csv').open(encoding='utf-8'))}[row['site']]
    want = json.loads(source['fates_natland_percent_json'])
    need(abs(host[0]-float(source['bare_percent']))<1e-5 and
         all(abs(got[i]-float(want.get(str(i+1),0)))<1e-4 for i in range(14)),
         row['site']+' forward HLM->FATES percentage mismatch')
    return {'host_bare_pct':float(host[0]),'mapped_FATES_pct':got.tolist(),
            'profile':row['FATES_mapping_profile']}


def stream_user(text,row):
    starts = list(re.finditer(r'(?m)^([A-Za-z][\w.-]*:[A-Za-z_]\w*)\s*=',text))
    chunks = {m.group(1):text[m.start():starts[i+1].start() if i+1<len(starts) else len(text)] for i,m in enumerate(starts)}
    need(len(chunks) == len(starts),'Duplicate reference DATM stream overrides')
    prefix = 'CLM_USRDAT.UNSET:'
    need(prefix+'datavars' in chunks,'No proven 1PT reference variable map')
    edits = {'taxmode':'cycle','tintalgo':'linear','mapalgo':'none','meshfile':'none','offset':'0',
             'year_first':str(row['first_year']),'year_last':str(row['last_year']),
             'year_align':str(row['first_year']),
             'datafiles':','.join(x['path'] for x in row['annual_files'])}
    for key,value in edits.items():
        chunks[prefix+key] = prefix+key+' = '+value+'\n'
    return '\n'.join(chunks.values())


def overlay_check():
    shared = CTSM/'bld/CLMBuildNamelist.pm'
    raw = shared.read_bytes()
    blob = hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()
    need(blob == SHARED_BLOB,'Shared CTSM namelist branch changed; inspect before applying Batch01 overlay')
    text = shared.read_text()
    start = text.index('sub setup_cmdl_spinup {')
    end = text.index('sub setup_cmdl_simulation_year {',start)
    part = text[start:end]
    old = "if ( &value_is_true($nl_flags->{'use_cn'}) ) {"
    new = "if ( &value_is_true($nl_flags->{'use_cn'}) || &value_is_true($nl_flags->{'use_fates'}) ) {"
    old2 = 'if ( $nl_flags->{$var} ne "off" ) {'
    new2 = 'if ( $nl_flags->{$var} ne "off" && &value_is_true($nl_flags->{\'use_cn\'}) ) {'
    need(part.count(old) == part.count(old2) == 1,'Batch01 overlay patch precondition changed')
    expected = text[:start]+part.replace(old,new,1).replace(old2,new2,1)+text[end:]
    need((OVERLAY/'bld/CLMBuildNamelist.pm').read_text() == expected and
         (OVERLAY/'bld/build-namelist').is_file(),'Proven Batch01 FATES AD overlay unavailable/changed')


def inputs(manifest):
    data = j(manifest)
    m = load_module(HERE/'04_build_UTC_NOLEAP_DATM_and_inventory.py','b04_forcing')
    need(data['direct_AD400_protocol'] == m.PROTOCOL and len(data['sites']) == 10,'Wrong source forcing/protocol manifest')
    need({r['site'] for r in data['sites']} == set(SITES),'Wrong Batch04 cohort')
    policies = j(HERE.parent/'data/AMF_BATCH04_TA_SENSOR_PROXY_POLICY_20261026.json')
    for row in data['sites']:
        need(row.get('height') == policies[row['site']] and row['eight_DATM_fields_present'],
             row['site']+' source-locked TA proxy/ZBOT not present')
        need(sha(row['meteorology_path']) == row['meteorology_SHA256'] and
             sha(row['metadata']['BIF_path']) == row['metadata']['BIF_sha256'],'Meteorology/BIF source drift')
        need([r['year'] for r in row['annual_files']] == list(range(row['first_year'],row['last_year']+1)),
             'Wrong annual file-year list')
        for entry in row['annual_files']:
            need(sha(entry['path']) == entry['sha256'],'Annual forcing SHA drift')
    return {r['site']:r for r in data['sites']}


def generated(case,rundir,row,arm,param,co2,initial=True):
    casepath,runpath,archpath,_ = paths(row['site'],arm)
    need(case == casepath and rundir == runpath,'Wrong target identity')
    expected = settings(row,case,rundir,archpath,co2)
    if not initial:
        for key in ('CONTINUE_RUN','RESUBMIT'):
            expected.pop(key)
    for key,want in expected.items():
        got = q(case,key)
        need(got.lower() == str(want).lower(), 'Actual CIME '+key+'='+got+' expected '+str(want))
    land = (case/'CaseDocs/lnd_in').read_text()
    for key,want in {**flags(arm),'fsurdat':row['shared_surface_path'],'fates_paramfile':str(param)}.items():
        need(nml(land,key) == want,'Generated lnd_in differs '+key)
    need(nml(land,'finidat') in (None,''),'AD400 must start cold')
    for bad in ('GPP','NPP'):
        need(not re.search(r"['\"]"+bad+r"['\"]",land),'Unsupported plain '+bad+' history request')
    root = ET.parse(case/'CaseDocs/datm.streams.xml').getroot()
    streams = [s for s in root.iter('stream_info') if s.get('name') == 'CLM_USRDAT.UNSET']
    need(len(streams) == 1,'One actual 1PT stream required')
    met = streams[0]
    want = {'taxmode':'cycle','tintalgo':'linear','mapalgo':'none','meshfile':'none','offset':'0',
            'year_first':str(row['first_year']),'year_last':str(row['last_year']),'year_align':str(row['first_year'])}
    for key,val in want.items():
        need((met.findtext(key) or '').strip() == val,'Actual DATM '+key+' mismatch')
    gotmap = dict((e.text or '').split() for e in met.find('datavars'))
    need(all(gotmap.get(k) == v for k,v in METMAP.items()),'Actual CDEPS field mapping differs')
    need([(x.text or '').strip() for x in met.find('datafiles')] == [x['path'] for x in row['annual_files']],
         'Actual CDEPS still points to wrong station/year files')
    for key in ('lnd_in','datm.streams.xml'):
        need((rundir/key).is_file() and sha(rundir/key) == sha(case/'CaseDocs'/key),
             'Effective RUNDIR vs CaseDocs mismatch '+key)
    for location in (case/'CaseDocs/nuopc.runconfig',rundir/'nuopc.runconfig'):
        text = location.read_text()
        for key,val in (('scol_lat',row['model_tower_coordinates'][0]),('scol_lon',row['model_tower_coordinates'][1])):
            found = re.findall(r'(?m)^\s*'+key+r'\s*=\s*(\S+)',text)
            need(len(found) == 1,'Missing effective coupler '+key)
            actual = float(found[0])
            err = abs(actual-val) if key == 'scol_lat' else abs((actual-val+180)%360-180)
            need(err<1e-5,'Effective NUOPC point coordinates differ from station surface '+str(location))
        domain = re.findall(r'(?m)^\s*single_column_lnd_domainfile\s*=\s*(.*?)\s*$',text)
        need(len(domain) == 1 and domain[0].strip("'\"") == 'UNSET','Inherited wrong-station point domain')
    need(q(case,'BUILD_COMPLETE').lower() == 'true','Case not built')
    exe = Path(q(case,'EXEROOT'))/'cesm.exe'
    need(exe.is_file(),'Reference FATES executable missing')
    return {'executable':str(exe),'executable_sha256':sha(exe),
            'case_files_sha256':{f:sha(case/f) for f in
                ('CaseDocs/lnd_in','CaseDocs/datm.streams.xml','CaseDocs/nuopc.runconfig',
                 'user_nl_clm','user_nl_datm_streams','.case.run','.submit_options')},
            'parameter_path':str(param),'parameter_sha256':sha(param)}


def prepare_one(site,arm,row,manifest,co2):
    need(arm == 'FIXNC','FULL preparation is disabled by operator instruction')
    case,rundir,archive,ledger = paths(site,arm)
    if ledger.exists():
        rec = j(ledger)
        need(rec['state'] == 'PREPARED_NOT_SUBMITTED','Existing partial/submitted case; no automatic retry '+str(ledger))
        verify_one(site,arm,row,manifest,co2)
        print('B04 REUSE VERIFIED PREPARATION',site,arm,flush=True)
        return
    for p in (case,OUT/case.name,archive):
        need(not p.exists() and not p.is_symlink(),'Refuse existing target '+str(p))
    need(sha(PARAM) == PARAM_SHA,'Installed common parameter SHA changed')
    data = parameter_data(j(PARAM),row['FATES_mapping_profile'])
    forward = pft_check(row,data)
    STATE.mkdir(parents=True,exist_ok=True)
    param = STATE/(site+'_FATES_'+row['FATES_mapping_profile']+'_params.json')
    if param.exists():
        need(j(param) == data,'Existing site parameter contents differ')
    else:
        save(param,data,True)
    land = (REFERENCE/'user_nl_clm').read_text()
    for key,value in {**flags(arm),'fsurdat':"'"+row['shared_surface_path']+"'",
                      'fates_paramfile':"'"+str(param)+"'",'finidat':"''",
                      'hist_fincl1':','.join("'"+s+"'" for s in HISTORY)}.items():
        land = setnml(land,key,value)
    stream = stream_user((REFERENCE/'user_nl_datm_streams').read_text(),row)
    save(ledger,{'state':'PREPARATION_ATTEMPTED_UNCERTAIN','site':site,'arm':arm,
        'case':str(case),'forcing_manifest':str(manifest),'forcing_manifest_sha256':sha(manifest),
        'protocol':'DIRECT_AD400_80x5_NO_AD5_HANDOFF','start_year':row['first_year'],
        'target_end_year':row['first_year']+400,'source_PFT_forward_map':forward,
        'height_policy':row['height'],'constant_global_CO2_ppm':co2,
        'soil_policy':'ORIGINAL_GRID_DEPTH_LAYERS_PRESERVED_NOT_SITE_MEASUREMENTS',
        'experiment_policy':'FIXED_BIOGEOGRAPHY_NO_COMPETITION_ONLY',
        'Slurm_submitted':False,'created_utc':datetime.now(timezone.utc).isoformat()},True)
    print('B04 PREPARATION ATTEMPT',site,arm,ledger,flush=True)
    run([CTSM/'cime/scripts/create_clone','--case',case,'--clone',REFERENCE,'--keepexe'],
        cwd=CTSM/'cime/scripts',timeout=480)
    need(q(case,'CASE') == case.name,'CIME clone identity mismatch')
    for key,value in settings(row,case,rundir,archive,co2).items():
        xc(case,key,value)
    (case/'user_nl_clm').write_text(land)
    (case/'user_nl_datm_streams').write_text(stream)
    if not (case/'.case.run').is_file():
        run([case/'case.setup'],cwd=case,timeout=300)
    env,lock = case/'env_case.xml',case/'LockedFiles/env_case.xml'
    snapshot = env.read_bytes()
    need(lock.read_bytes() == snapshot and Path(q(case,'COMP_ROOT_DIR_LND')).resolve() == CTSM.resolve(),
         'New CIME source lock differs before private preview')
    try:
        xc(case,'COMP_ROOT_DIR_LND',OVERLAY)
        run([case/'preview_namelists'],cwd=case,timeout=650)
    finally:
        xc(case,'COMP_ROOT_DIR_LND','$SRCROOT')
        need(env.read_bytes() == snapshot and lock.read_bytes() == snapshot,'CIME source lock not restored')
    options = configparser.RawConfigParser()
    options.read(case/'.submit_options')
    if not options.has_section('SubmitOptions'):
        options.add_section('SubmitOptions')
    options.set('SubmitOptions','skip_pnl','True')
    with (case/'.submit_options').open('w') as f:
        options.write(f)
    rec = j(ledger)
    rec.update(generated(case,rundir,row,arm,param,co2),state='PREPARED_NOT_SUBMITTED')
    save(ledger,rec)
    print('B04 CASE PREPARED',site,arm,'AD400 80x5 RESUBMIT=79 | NO SLURM',flush=True)


def verify_one(site,arm,row,manifest,co2):
    case,rundir,_,ledger = paths(site,arm)
    rec = j(ledger)
    need(rec['state'] == 'PREPARED_NOT_SUBMITTED' and rec['site'] == site and rec['arm'] == arm,
         'Case not prepared/unsubmitted')
    need(rec['forcing_manifest_sha256'] == sha(manifest),'Forcing manifest changed since preparation')
    for file,digest in rec['case_files_sha256'].items():
        need(sha(case/file) == digest,'Case changed since preview '+file)
    need(sha(rec['parameter_path']) == rec['parameter_sha256'],'Private PFT map drift')
    pft_check(row,j(rec['parameter_path']))
    actual = generated(case,rundir,row,arm,Path(rec['parameter_path']),co2)
    need(actual['executable_sha256'] == rec['executable_sha256'],'Compiled executable changed')
    status = case/'CaseStatus'
    need(not status.is_file() or not re.search(r'case\.submit starting|case\.run starting|model execution starting',status.read_text()),
         'Prior submission exists; refuse duplicate')
    cp = configparser.RawConfigParser()
    cp.read(case/'.submit_options')
    need(cp.getboolean('SubmitOptions','skip_pnl',fallback=False),'Batch01 skip-preview option not persisted')
    return rec


def submit_one(site,arm,row,manifest,co2):
    need(arm == 'FIXNC','FULL submission is disabled by operator instruction')
    rec = verify_one(site,arm,row,manifest,co2)
    case,_,_,ledger = paths(site,arm)
    queued = run(['squeue','-u',getpass.getuser(),'-h','-o','%j'],timeout=45)
    need(not any(case.name in line for line in queued.splitlines()),'Case already in Slurm queue')
    attempt = ledger.with_name(ledger.stem+'_SUBMIT_ATTEMPT.json')
    need(not attempt.exists(),'Prior submit attempt/uncertain outcome; do not repeat')
    guard = load_module(HERE/'b04_stack_guard.py','b04_submit_stack')
    # SAME process: CIME subprocess inherits this live limit, Slurm carries it.
    proof = guard.require_for_submission(site=site,phase='AD400',may_raise=True)
    save(attempt,{'state':'ATTEMPT_BEFORE_CASE_SUBMIT_NO_BLIND_RETRY','case':str(case),
        'prepared_receipt_sha256':sha(ledger),'stack':proof,
        'created_utc':datetime.now(timezone.utc).isoformat()},True)
    output = run([case/'case.submit','--skip-preview-namelist'],cwd=case,timeout=660)
    rid = re.search(r'Submitted job case\.run with id (\d+)',output)
    aid = re.search(r'Submitted job case\.st_archive with id (\d+)',output)
    need(rid and aid,'Submission unparseable; inspect ledger/Slurm, never repeat blindly: '+output)
    rec.update(state='AD400_SUBMITTED_MODEL_COMPLETION_UNVERIFIED',Slurm_submitted=True,
               first_run_job=rid.group(1),first_archive_job=aid.group(1),stack=proof,
               submitted_utc=datetime.now(timezone.utc).isoformat(),submit_output=output)
    save(ledger,rec)
    print('B04 DIRECT AD400 SUBMITTED',site,arm,'run='+rid.group(1),'archive='+aid.group(1),
          '80x5y | RESUBMIT=79 | NO AD5 HANDOFF',flush=True)


def audit_one(site,arm):
    from netCDF4 import Dataset
    case,_,archive,ledger = paths(site,arm)
    rec = j(ledger)
    need(rec['state'] == 'AD400_SUBMITTED_MODEL_COMPLETION_UNVERIFIED','No successful submit receipt')
    first = rec['start_year']
    expected = [f'{y:04d}-01-01-00000' for y in range(first+5,first+401,5)]
    found = sorted(p.name for p in (archive/'rest').iterdir() if p.is_dir())
    need(found == expected,'AD400 archive is incomplete: '+str(len(found))+'/80')
    for stamp in expected:
        for kind in ('clm2','datm','cpl'):
            path = archive/'rest'/stamp/(case.name+'.'+kind+'.r.'+stamp+'.nc')
            need(path.is_file() and path.stat().st_size>0,'Missing archived restart '+str(path))
    final = archive/'rest'/expected[-1]/(case.name+'.clm2.r.'+expected[-1]+'.nc')
    with Dataset(final) as nc:
        state = int(np.asarray(nc['spinup_state'][:]).ravel()[0]) if 'spinup_state' in nc.variables else int(nc.getncattr('spinup_state'))
        need(state == 2,'Final AD spinup_state must be 2')
    need(q(case,'RESUBMIT') == '0','CIME resubmissions not exhausted')
    queued = run(['squeue','-u',getpass.getuser(),'-h','-o','%j'],timeout=45)
    need(not any(case.name in line for line in queued.splitlines()),'Case still queued/running')
    account = run(['sacct','-u',getpass.getuser(),'-S',rec['submitted_utc'][:10],
                   '-X','-n','-P','-o','JobIDRaw,JobName%140,State%30'],timeout=60)
    jobs = [s.split('|') for s in account.splitlines()]
    for prefix in ('run.','st_archive.'):
        relevant = [s for s in jobs if len(s)>=3 and s[1] == prefix+case.name]
        need(len(relevant) == 80 and all(s[2].strip() == 'COMPLETED' for s in relevant),
             'Need exactly 80 completed '+prefix+' accounting jobs')
    print('B04 AD400 COMPLETE',site,arm,'80 run + 80 archive jobs; final',expected[-1],
          'spinup_state=2 SHA256='+sha(final),flush=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('action',choices=('self-test','prepare','verify','submit-ad400','audit-ad400','status'))
    ap.add_argument('--manifest',type=Path)
    ap.add_argument('--sites',nargs='+',choices=SITES,default=list(SITES))
    ap.add_argument('--arms',nargs='+',choices=ARMS,default=list(ARMS))
    ap.add_argument('--confirm',default='')
    a = ap.parse_args()
    need(len(a.sites) == len(set(a.sites)) and len(a.arms) == len(set(a.arms)),'Duplicate site/arm selection')
    if a.action == 'self-test':
        need(5*(79+1) == 400 and ARMS == ('FIXNC',) and
             flags('FIXNC')['use_fates_nocomp'] == '.true.' and
             flags('FIXNC')['use_fates_fixed_biogeog'] == '.true.','FIXNC-only AD400 configuration invalid')
        sample = "x = 1\nhist_fincl1 = 'GPP',\n 'NPP'\ny = 2\n"
        fixed = setnml(sample,'hist_fincl1',"'FATES_GPP','FATES_NPP'")
        need('y = 2' in fixed and "'GPP'" not in fixed,'Multiline history replacement failed')
        print('B04 DIRECT AD400 CASE CONTROLLER SELF-TEST PASS; NO HPC ACCESS')
        return
    if a.action in ('status','audit-ad400'):
        rows = None
    else:
        need(a.manifest is not None,'--manifest required')
        rows = inputs(a.manifest)
    if a.action == 'prepare':
        need(a.confirm == ACK_PREP,'prepare requires --confirm '+ACK_PREP)
        overlay_check()
        need(q(REFERENCE,'BUILD_COMPLETE').lower() == 'true' and
             q(REFERENCE,'DATM_MODE') == '1PT' and q(REFERENCE,'ATM_NCPL') == '48',
             'Proven Batch01 1PT FATES machine/executable reference not available')
    if a.action == 'submit-ad400':
        need(a.confirm == ACK_SUBMIT,'submit-ad400 requires --confirm '+ACK_SUBMIT)
    policy = j(HERE.parent/'data/AMF_BATCH04_CO2_POLICY_20261026.json')
    holds = []
    for site in a.sites:
        for arm in a.arms:
            try:
                if a.action == 'status':
                    recpath = paths(site,arm)[3]
                    print('B04 STATUS',site,arm,j(recpath)['state'] if recpath.is_file() else 'NOT_PREPARED',flush=True)
                elif a.action == 'audit-ad400':
                    audit_one(site,arm)
                else:
                    co2 = policy[site]['constant_global_background_CO2_ppm']
                    need(policy[site]['first_forcing_year'] == rows[site]['first_year'],'CO2 source-year mismatch')
                    if a.action == 'prepare':
                        prepare_one(site,arm,rows[site],a.manifest,co2)
                    elif a.action == 'verify':
                        verify_one(site,arm,rows[site],a.manifest,co2)
                        print('B04 PRE-SUBMIT VERIFY PASS',site,arm,flush=True)
                    else:
                        submit_one(site,arm,rows[site],a.manifest,co2)
            except Exception as e:
                holds.append((site,arm,str(e)))
                print('B04 HOLD',site,arm,str(e),flush=True)
    print('B04 SUMMARY',a.action,'selected',len(a.sites)*len(a.arms),'hold',len(holds),flush=True)
    if holds:
        raise SystemExit(2)


if __name__ == '__main__':
    main()
