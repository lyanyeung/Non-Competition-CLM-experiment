#!/usr/bin/env python3
"""Audit and stage Normal400 for the three submitted Batch01 six-site AD runs.

Uses the existing proven Lane A hybrid staging implementation, but validates
these sites' separate direct AD400 ledgers and Stage23 inputs. Each completed
site is staged independently; incomplete sites are held. No Slurm submission.
"""
import argparse, hashlib, importlib.util, json, re
from pathlib import Path

import numpy as np

SITES=('CA-TP1','CA-TP3','US-Bar')
LANE_BLOB='c461a85feef163830316c71410c1c3fd2c4d859e'


def load(path,name,expected_blob=None):
    raw=Path(path).read_bytes()
    if expected_blob:
        sha=hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()
        if sha!=expected_blob: raise ValueError('Lane A controller differs from pinned reference')
    spec=importlib.util.spec_from_file_location(name,path); m=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m); return m


def configure(stage,direct,helper,lane,root,data):
    direct.setup(stage,helper,root,data)
    lane.CASES={s:helper.name(s) for s in SITES}; lane.SITE_ORDER=SITES
    lane.D21=helper.B/'experiments/NonCompetitionObserved22/AmeriFlux_Batch01_10/Stage45_six_NORMAL400'
    lane.n_name=lambda s: f'{s}_AMF_B01SIX_FIXNC_NORMAL400_DIRECT'

    def pft_gate(site,case=None):
        item=data[site]; ad=helper.load(helper.ledger(site)); case=case or helper.case_dir(site)
        land=(case/'CaseDocs/lnd_in').read_text()
        surface=Path(helper.nml_get(land,'fsurdat')).resolve(strict=True)
        parameter=Path(helper.nml_get(land,'fates_paramfile')).resolve(strict=True)
        if surface!=item['surface']['path'].resolve(strict=True) or helper.digest(surface)!=ad.get('surface_sha256'):
            raise ValueError(site+': actual surface differs from Stage23 or AD ledger')
        if helper.digest(parameter)!=ad.get('fates_paramfile_sha256'): raise ValueError(site+': FATES parameters changed')
        if helper.digest(item['manifest'])!=ad.get('stage23_input_manifest_sha256'): raise ValueError(site+': Stage23 manifest changed')
        matrix=helper._json_map(json.loads(parameter.read_text()))
        host=item['surface']['host']; mapped={}
        for idx,value in host.items():
            if idx:
                for slot,weight in enumerate(matrix[idx-1]):
                    if weight>0: mapped[slot+1]=mapped.get(slot+1,0.)+value*float(weight)
        want=item['fates']
        if any(abs(mapped.get(k,0)-want.get(k,0))>1e-3 for k in set(mapped)|set(want)):
            raise ValueError(site+': FATES mapping differs from verified Stage23 recommendation')
        if site=='US-Bar':
            proof=ad.get('temperature_candidate',{})
            if not ad.get('candidate_repairs_applied') or helper.digest(proof['candidate'])!=proof['candidate_sha256']:
                raise ValueError('US-Bar provisional 2015 forcing candidate missing or changed')
        return {'surface':str(surface),'host':host,'fates':mapped,'bare':host.get(0,0.),
                'recommended':item['receipt'].get('PFT','Stage23 verified')}

    lane.pft_gate=pft_gate
    return pft_gate


def audit(site,h,lane,gate):
    info=h.ad400_one(site); ledger=h.load(h.ledger(site)); case=h.case_dir(site)
    status=(case/'CaseStatus').read_text(errors='replace')
    for what,regex in (('model',r'case\.run (success|error)'),('archive',r'st_archive (success|error)')):
        hits=re.findall(regex,status)
        if not hits or hits[-1]!='success': raise ValueError(site+': last '+what+' status is not success')
    for filename,key in (('CaseDocs/lnd_in','lnd_in_sha256'),('CaseDocs/datm.streams.xml','datm_streams_sha256')):
        if h.digest(case/filename)!=ledger[key]: raise ValueError(site+': AD configuration differs from submitted ledger: '+filename)
    exe=Path(h.xq(case,'EXEROOT'))/'cesm.exe'
    if h.digest(exe)!=ledger['executable_sha256']: raise ValueError(site+': AD executable changed')
    info['pft_gate']=gate(site); return info


def prepare(site,info,h,lane):
    name=lane.n_name(site)
    if lane.queued(name) or lane.sacct_name(name): raise ValueError(site+': matching Normal job already exists')
    # Stage36/helper.ad400_one serializes restart paths as strings; Lane A
    # stage_normal_one expects pathlib.Path objects for each restart triplet.
    info=dict(info)
    info['files']={k:Path(v) for k,v in info['files'].items()}
    lane.stage_normal_one(site,info)
    case=lane.n_case(site); ledger=lane.n_ledger(site); record=lane.load(ledger)
    if record.get('phase')!='PREPARED_NOT_SUBMITTED': raise ValueError(site+': Normal stage did not pass validation')
    if lane.xq(case,'RESUBMIT_SETS_CONTINUE_RUN').lower()!='true': raise ValueError(site+': automatic continuation not enabled')
    lane.xc(case,'RESUBMIT','79')
    for key,want in (('RESUBMIT','79'),('STOP_N','5'),('REST_N','5'),('CONTINUE_RUN','false'),
                     ('CLM_ACCELERATED_SPINUP','off'),('RUN_TYPE','hybrid')):
        if lane.xq(case,key).lower()!=want: raise ValueError(site+': final Normal configuration mismatch '+key)
    record.update(protocol='DIRECT_NORMAL400_80x5_RESUBMIT79_NOT_SUBMITTED',normal_met_caveat=(
        'US-Bar uses provisional AD forcing with other Met flags unresolved' if site=='US-Bar' else 'Stage23 tower forcing'))
    lane.save(ledger,record)
    print('NORMAL400 PREPARED',site,'start',record['normal_start_year'],'target',record['normal400_target_year'],
          '80x5 RESUBMIT=79 NO JOBS SUBMITTED',flush=True)


def main():
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('action',choices=('audit','prepare'))
    for opt in ('run','helper','stage26','direct','lane'): p.add_argument('--'+opt,required=True,type=Path)
    p.add_argument('--sites',nargs='+',choices=SITES,default=SITES); a=p.parse_args()
    stage=load(a.stage26,'stage26'); direct=load(a.direct,'direct36'); lane=load(a.lane,'lane21',LANE_BLOB)
    helper=stage.load_helper(a.helper); root,data=stage.inputs(a.run); gate=configure(stage,direct,helper,lane,root,data)
    passed=[]; held=[]
    for site in a.sites:
        try:
            info=audit(site,helper,lane,gate)
            print('AD400 PASS',site,'run_segments',info['runs'],'archives',info['archives'],
                  'final',info['final'],'spinup_state',info['spinup_state'],flush=True)
            if a.action=='prepare': prepare(site,info,helper,lane)
            passed.append(site)
        except Exception as exc:
            print('HOLD',site,type(exc).__name__,str(exc),flush=True); held.append(site)
    print('SUMMARY action',a.action,'passed',','.join(passed) or '-', 'held',','.join(held) or '-',flush=True)
    print('NO NORMAL SLURM JOBS SUBMITTED. Do not blindly retry a partial Normal stage.',flush=True)
    return int(bool(held))


if __name__=='__main__': raise SystemExit(main())
