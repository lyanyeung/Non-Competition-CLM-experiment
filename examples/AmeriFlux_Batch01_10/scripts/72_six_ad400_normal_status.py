#!/usr/bin/env python3
"""Read-only six-site AD400 completion and known Normal case status."""
import argparse, hashlib, importlib.util
from pathlib import Path

SITES=('CA-Cbo','CA-Man','CA-TP1','CA-TP3','US-Aud','US-Bar')
NEW={'CA-Cbo','CA-Man','US-Aud'}
PINS={'normal':'0cba910633de61e0736b5eb07ff3b1e9a668d86e',
      'stage26':'76dfa29e4d36c0e329cfb9c688268540b62ba7fd',
      'direct':'8a3fc17eed43d1112852327c8c5ef60e2c490b3e',
      'lane':'c461a85feef163830316c71410c1c3fd2c4d859e'}
ROOT=Path('/iridisfs/scratch/ly3n24/CLM_FATES/experiments/NonCompetitionObserved22/AmeriFlux_Batch01_10/Stage23_six_inputs_amf_six_inputs_tool.OSXxymF5')

def load(path,name):
    raw=Path(path).read_bytes(); sha=hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()
    if sha!=PINS[name]: raise ValueError('wrong helper source '+name)
    spec=importlib.util.spec_from_file_location('stage72_'+name,path); mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); return mod

def check_candidate_proofs(site,helper):
    if site not in NEW: return
    obj=helper.load(helper.ledger(site)); proof=obj.get('candidate_proof')
    if not obj.get('candidate_repairs_applied') or not isinstance(proof,list) or not proof:
        raise ValueError('reviewed candidate proof missing from AD ledger')
    for item in proof:
        if helper.digest(item['candidate'])!=item['candidate_sha256']:
            raise ValueError('AD candidate changed: '+item['candidate'])

def site_status(site,helper,lane,normal,gate):
    print('\n===',site,'===',flush=True)
    try: helper.status((site,))
    except Exception as e: print('AD STATUS UNAVAILABLE',site,type(e).__name__,str(e),flush=True)
    try:
        info=normal.audit(site,helper,lane,gate); check_candidate_proofs(site,helper)
        print('AD400 VERIFIED COMPLETE',site,'runs',info['runs'],'archives',info['archives'],
              'final_restart',info['final'],'spinup_state',info['spinup_state'],flush=True)
    except Exception as e:
        print('AD400 NOT VERIFIED',site,type(e).__name__,str(e),flush=True)
    try:
        path=lane.n_ledger(site); case=lane.n_case(site); name=lane.n_name(site)
        if path.exists():
            obj=lane.load(path)
            print('NORMAL RECORD',site,'phase',obj.get('phase','UNKNOWN'),'case',case,
                  'first_run',obj.get('first_run_job','-'),'first_archive',obj.get('first_archive_job','-'),flush=True)
        else: print('NORMAL RECORD',site,'NO_STANDARD_LEDGER','case_exists',case.exists(),'case',case,flush=True)
        q=lane.queued(name)
        print('NORMAL QUEUE',site,q if q else '-',flush=True)
    except Exception as e: print('NORMAL STATUS UNAVAILABLE',site,type(e).__name__,str(e),flush=True)

def main():
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('--self-test',action='store_true')
    for k in PINS:p.add_argument('--'+k,required=True,type=Path)
    p.add_argument('--helper',required=True,type=Path); a=p.parse_args()
    mods={k:load(getattr(a,k),k) for k in PINS}; normal,s26,d,lane=(mods[x] for x in ('normal','stage26','direct','lane'))
    if a.self_test:
        if not callable(getattr(normal,'audit',None)) or not callable(getattr(normal,'configure',None)):
            raise ValueError('normal audit API mismatch')
        print('STAGE72 SELF-TEST PASS | pinned audit helpers; NO WRITES',flush=True); return
    helper=s26.load_helper(a.helper); root,data=s26.inputs(ROOT)
    normal.SITES=SITES; gate=normal.configure(s26,d,helper,lane,root,data)
    for site in SITES:site_status(site,helper,lane,normal,gate)
    print('STAGE72 COMPLETE | read-only; NOT VERIFIED includes still running and audit errors; no case or Slurm changes',flush=True)
    print('NORMAL scope: expected Stage45 names/ledger only; another naming scheme requires separate lookup',flush=True)

if __name__=='__main__':main()
