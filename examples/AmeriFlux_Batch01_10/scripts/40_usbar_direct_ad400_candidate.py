#!/usr/bin/env python3
"""US-Bar direct AD400 using the three-point detached sensitivity candidate.

This is a provisional forcing experiment, not a claim that all other Met
flags have been resolved. Reuses Stage23 for every other year. The candidate
and its source are verified before preparation AND submission. New case only.
"""
import argparse, importlib.util, json, math
from pathlib import Path
import numpy as np
from netCDF4 import Dataset

SITE='US-Bar'
TIMES=('2015-11-06 20:00:00','2015-11-06 20:30:00','2015-11-06 21:00:00')
INDICES=(14882,14883,14884)
FIELDS=('TBOT','QBOT','SHUM','RH')


def load(path,name):
    spec=importlib.util.spec_from_file_location(name,path); m=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m); return m


def verified_candidate(h,data,manifest_path):
    p=manifest_path.resolve(strict=True); m=json.loads(p.read_text()); item=data[SITE]
    if m.get('site')!=SITE or m.get('status')!='DETACHED_SENSITIVITY_NOT_APPLIED': raise ValueError('wrong candidate status/site')
    if m.get('source_manifest_sha256')!=h.digest(item['manifest']): raise ValueError('candidate belongs to a different Stage23 manifest')
    source=Path(m['source_nc']).resolve(strict=True); candidate=Path(m['candidate_nc']).resolve(strict=True)
    expected=item['files'][2015-item['years'][0]].resolve(strict=True)
    if source!=expected or h.digest(source)!=m['source_sha256'] or h.digest(candidate)!=m['candidate_sha256']:
        raise ValueError('original or candidate forcing checksum/identity mismatch')
    changes=sorted(m['proposed_changes'],key=lambda x:x['time_local'])
    if tuple(x['time_local'] for x in changes)!=TIMES or tuple(x['UTC_index'] for x in changes)!=INDICES:
        raise ValueError('candidate timestamp/index set changed')
    with Dataset(str(source)) as a, Dataset(str(candidate)) as b:
        if set(a.variables)!=set(b.variables): raise ValueError('candidate variable set changed')
        for name in a.variables:
            x=np.ma.asarray(a[name][:]); y=np.ma.asarray(b[name][:])
            if name in FIELDS:
                if x.shape!=y.shape or x.shape[0]!=17520: raise ValueError('forcing dimensions changed: '+name)
                mask=np.ones(x.shape[0],dtype=bool); mask[list(INDICES)]=False
                if not np.ma.allequal(x[mask],y[mask]): raise ValueError('candidate changed outside approved times: '+name)
            elif not np.ma.allequal(x,y): raise ValueError('candidate changed unrelated variable: '+name)
        for change in changes:
            i=change['UTC_index']; pressure=float(a['PSRF'][i,0,0]); temp=float(change['candidate_TA_C'])
            vpd=float(change['candidate_VPD_hPa']); es=6.112*math.exp(17.67*temp/(temp+243.5)); vapor=es-vpd
            if not (0<vapor<=es and 49000<pressure<111000): raise ValueError('invalid candidate thermodynamics')
            q=.622*vapor/(pressure/100-.378*vapor); rh=100*vapor/es
            for key,value,tol in (('TBOT',temp+273.15,1e-5),('QBOT',q,1e-8),('SHUM',q,1e-8),('RH',rh,1e-5)):
                if abs(float(b[key][i,0,0])-value)>tol: raise ValueError('candidate readback mismatch: '+key)
            if abs(float(a['TBOT'][i,0,0])-(float(change['original_TA_C'])+273.15))>1e-5: raise ValueError('original temperature mismatch')
    updated=list(item['files']); updated[2015-item['years'][0]]=candidate; item['files']=updated
    return {'manifest':str(p),'manifest_sha256':h.digest(p),'candidate':str(candidate),'candidate_sha256':m['candidate_sha256'],
            'source':str(source),'source_sha256':m['source_sha256'],'changes':changes}


def main():
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('action',choices=('check','prepare','submit','status'))
    for opt in ('run','helper','stage26','direct','candidate-manifest','co2-csv'): p.add_argument('--'+opt,required=True,type=Path)
    a=p.parse_args(); d=load(a.direct,'direct36'); s=load(a.stage26,'stage26'); h=s.load_helper(a.helper)
    root,data=s.inputs(a.run); proof=verified_candidate(h,data,a.candidate_manifest); d.setup(s,h,root,data)
    if a.action in ('check','prepare'):
        ctx=d.preflight(h,data,a.co2_csv,(SITE,),input_label='Stage23 with verified 2015 three-point sensitivity')
        if a.action=='prepare':
            h.prepare_one(SITE,ctx); path=h.ledger(SITE); o=h.load(path)
            if o.get('phase')!='CASE_VERIFIED_NOT_SUBMITTED': raise ValueError('case preview did not pass')
            o.update(stage23_input_manifest=str(data[SITE]['manifest']),stage23_input_manifest_sha256=h.digest(data[SITE]['manifest']),
                     met_review='PARTIALLY_CORRECTED_EXPLORATORY_OTHER_FLAGS_UNRESOLVED',candidate_repairs_applied=True,
                     temperature_candidate=proof)
            h.save(path,o); print('US-Bar DIRECT AD400 PREPARED WITH THREE-POINT CANDIDATE; NO JOBS',flush=True)
    elif a.action=='submit':
        o=h.load(h.ledger(SITE))
        if o.get('phase')!='CASE_VERIFIED_NOT_SUBMITTED': raise ValueError('not a verified, unsubmitted case')
        if o.get('temperature_candidate')!=proof: raise ValueError('candidate or source changed after preparation')
        if h.digest(data[SITE]['manifest'])!=o.get('stage23_input_manifest_sha256'): raise ValueError('Stage23 manifest changed')
        if h.digest(Path(h.xq(h.TEMPLATE,'EXEROOT'))/'cesm.exe')!=o['executable_sha256']: raise ValueError('executable changed')
        co2=float(o['co2_ppmv']); settings=h.xml_settings(SITE,data[SITE]['surface'],co2)
        h.validate_case(SITE,data[SITE]['surface'],data[SITE]['files'],Path(o['fates_paramfile']),co2,settings)
        stack=h.stack_guard()
        print('US-Bar: THREE-POINT REPAIR APPLIED; OTHER MET FLAGS REMAIN; EXPERIMENT IS PROVISIONAL',flush=True)
        h.submit_one(SITE,stack)
    else: h.status((SITE,))


if __name__=='__main__': main()
