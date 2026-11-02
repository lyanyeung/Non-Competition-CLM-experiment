#!/usr/bin/env python3
"""Prepare and submit three provisional direct AD400 cases with reviewed inputs.

Every execution rechecks all candidate and Stage23 identities. Existing cases or
jobs are never overwritten or resubmitted by the prepare phase. Submission is
once per freshly verified ledger; failures require status inspection.
"""
import argparse, hashlib, importlib.util, json, math
from pathlib import Path
import numpy as np
from netCDF4 import Dataset

HOME=Path('/iridisfs/home/ly3n24/CLM_FATES_PLOTS')
SITES=('CA-Cbo','CA-Man','US-Aud')
COUNTS={('CA-Cbo',2018):5,('CA-Man',1994):1,('CA-Man',2005):45,('CA-Man',2007):3,
        ('US-Aud',2012):8,('US-Aud',2019):3,('US-Aud',2023):40}
PINS={'stage59':'09d6cc0cad4494b75a0671c1c8f11df41a830533',
      'stage58':'82b63dbf16665df05060c7ed70ea77023ba2cea5',
      'context':'6f6e594d2ed57ac2c00c9af2f325cd179b10ecb3',
      'stage26':'76dfa29e4d36c0e329cfb9c688268540b62ba7fd',
      'direct':'8a3fc17eed43d1112852327c8c5ef60e2c490b3e',
      'physics':'12799912ed323a28cc12c502d2c35eaf70ee0b97'}
FIELDS=('TBOT','QBOT','SHUM','RH')

def check(ok,msg):
    if not ok: raise ValueError(msg)

def load(path,name):
    path=Path(path).resolve(strict=True); raw=path.read_bytes()
    check(hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()==PINS[name],name+' blob mismatch')
    spec=importlib.util.spec_from_file_location('stage68_'+name,path); m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m

def verify_file(orig,candidate,changes):
    indices={int(x['UTC_index']) for x in changes}
    check(len(indices)==len(changes) and all(0<=i<17520 for i in indices),'invalid edit indices')
    with Dataset(str(orig)) as a,Dataset(str(candidate)) as b:
        check(set(a.variables)==set(b.variables),'variable set mismatch')
        for key in a.variables:
            x=np.ma.asarray(a[key][:]); y=np.ma.asarray(b[key][:]); check(x.shape==y.shape,'shape mismatch '+key)
            if key in FIELDS:
                check(x.shape[0]==17520,'time length mismatch '+key)
                mask=np.ones(x.shape[0],dtype=bool); mask[list(indices)]=False
                check(np.ma.allequal(x[mask],y[mask]),'unapproved changes '+key)
            else: check(np.ma.allequal(x,y),'unapproved variable changes '+key)
        for c in changes:
            i=int(c['UTC_index']); t=float(c['candidate_TA_C']); q=float(c['candidate_QBOT']); rh=float(c['candidate_RH_pct'])
            pressure=float(a['PSRF'][i,0,0]); vpd=float(c['candidate_VPD_hPa'])
            check(all(math.isfinite(z) for z in (t,q,rh,pressure,vpd)) and 49000<pressure<111000 and 0<q<.08 and 0<rh<=100 and vpd>=0,'candidate physics')
            es=6.112*math.exp(17.67*t/(t+243.5)); e=q*(pressure/100)/(.622+.378*q)
            check(abs((es-e)-vpd)<.02 and abs(100*e/es-rh)<.05,'candidate humidity inconsistency')
            for name,want,tol in (('TBOT',t+273.15,1e-4),('QBOT',q,1e-8),('SHUM',q,1e-8),('RH',rh,1e-4)):
                check(abs(float(b[name][i,0,0])-want)<tol,'readback mismatch '+name)
    return indices

def execute(action,helper,d,data,proofs,co2_csv):
    if action in ('check','prepare','run'):
        contexts={}; failed=[]
        for site in SITES:
            try:
                contexts[site]=d.preflight(helper,data,co2_csv,(site,),input_label='verified user-reviewed sensitivity candidates plus Stage23')
                print('STAGE70 PREFLIGHT PASS',site,flush=True)
            except Exception as exc:
                failed.append(site); print('STAGE70 PREFLIGHT HOLD',site,type(exc).__name__,str(exc),flush=True)
        if failed: raise SystemExit('Preflight failed: '+', '.join(failed)+'; no cases prepared by this invocation')
        if action=='check':
            print('STAGE70 CHECK COMPLETE | no cases or jobs created',flush=True); return
        for site in SITES:
            helper.prepare_one(site,contexts[site])
            ledger_path=helper.ledger(site); obj=helper.load(ledger_path)
            check(obj.get('phase')=='CASE_VERIFIED_NOT_SUBMITTED',site+': case preparation incomplete')
            obj.update(stage23_input_manifest=str(data[site]['manifest']),
                       stage23_input_manifest_sha256=helper.digest(data[site]['manifest']),
                       candidate_proof=proofs[site],
                       met_review='USER_REVIEWED_SENSITIVITY_CANDIDATES_REMAINING_FLAGS_AND_PROXY_HEIGHTS_DOCUMENTED',
                       candidate_repairs_applied=True,
                       retained_us_aud_2012='19:00 and 19:30 Q1; next-day 02:00 and 02:30 Q0 retained by user')
            helper.save(ledger_path,obj)
            print('STAGE70 CASE VERIFIED',site,'DIRECT AD400 80x5 NO SLURM',flush=True)
        print('STAGE70 PREPARATION COMPLETE | three verified provisional cases',flush=True)
        if action=='prepare': return
    if action in ('submit','run'):
        # Validate all three *before* any submission so a mismatch blocks all.
        for site in SITES:
            obj=helper.load(helper.ledger(site)); item=data[site]
            check(obj.get('phase')=='CASE_VERIFIED_NOT_SUBMITTED',site+': no verified unsubmitted case; inspect status before retry')
            check(obj.get('candidate_proof')==proofs[site],site+': candidate/source evidence changed')
            check(helper.digest(item['manifest'])==obj.get('stage23_input_manifest_sha256'),site+': Stage23 manifest changed')
            check(helper.digest(Path(helper.xq(helper.TEMPLATE,'EXEROOT'))/'cesm.exe')==obj['executable_sha256'],site+': executable changed')
            co2=float(obj['co2_ppmv']); settings=helper.xml_settings(site,item['surface'],co2)
            helper.validate_case(site,item['surface'],item['files'],Path(obj['fates_paramfile']),co2,settings)
        stack=helper.stack_guard()
        for site in SITES:
            print('STAGE70 SUBMITTING',site,'provisional 80x5; recorded flags remain',flush=True)
            helper.submit_one(site,stack)
        print('STAGE70 SUBMISSION COMPLETE | inspect job IDs above',flush=True)

def main():
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('--self-test',action='store_true')
    p.add_argument('action',choices=('check','prepare','submit','run'))
    for k in PINS: p.add_argument('--'+k,required=True,type=Path)
    p.add_argument('--helper',required=True,type=Path); p.add_argument('--co2-csv',required=True,type=Path)
    p.add_argument('--approved',type=Path,default=HOME/'approved_met_candidates.TVqWqlLi/result/manifest.json')
    p.add_argument('--joint',type=Path,default=HOME/'approved_cbo_caman.b5Ve5c8S/result/manifest.json')
    p.add_argument('--merged',type=Path,default=HOME/'approved_q1_cbo.QeDyqeSz/result/manifest.json')
    p.add_argument('--stage62',type=Path,default=HOME/'us_aud_stage61_62.p1REVBxA/candidates/manifest.json')
    p.add_argument('--stage66',type=Path,default=HOME/'us_aud_stage66.LK9D5Gfp/result/manifest.json')
    a=p.parse_args(); mods={k:load(getattr(a,k),k) for k in PINS}
    stage,s58,s26,d,phys=(mods[k] for k in ('stage59','stage58','stage26','direct','physics'))
    check(COUNTS[('US-Aud',2023)]==40 and sum(COUNTS.values())==105,'unexpected inventory')
    if a.self_test:
        check(callable(getattr(stage,'verify_sources',None)) and callable(getattr(d,'preflight',None)),'helper API')
        print('STAGE70 SELF-TEST PASS | pinned helpers and candidate counts; NO WRITES',flush=True); return
    canonical=stage.select_canonical(s58,a); stage.verify_sources(canonical,stage.ROOT,s58)
    old=json.loads(a.stage62.resolve(strict=True).read_text()); latest=json.loads(a.stage66.resolve(strict=True).read_text())
    check(old.get('status')=='DETACHED_NOT_USED_BY_CASES' and latest.get('status')=='DETACHED_NOT_USED_BY_CASES','US-Aud manifest status')
    aud2012=next(x for x in old['files'] if x['site']=='US-Aud' and int(x['year'])==2012)
    aud2023=latest['file']
    check(latest.get('tower_temperature_exactly_unchanged') is True and latest.get('total_changes')==40,'Stage66 not verified')
    check(stage.sha256(aud2012['candidate'])==aud2012['candidate_sha256']==latest['prior_2012_candidate_sha256'],'2012 candidate SHA')
    check(Path(aud2012['candidate']).resolve(strict=True)==Path(latest['prior_2012_candidate']).resolve(strict=True),'2012 candidate identity')
    for site,year,record in [('US-Aud',2012,aud2012),('US-Aud',2023,aud2023)]:
        prior=canonical[(site,year)]
        prior_original=prior.get('original',prior.get('source')); prior_sha=prior.get('original_sha256',prior.get('source_sha256'))
        check(Path(record['original']).resolve(strict=True)==Path(prior_original).resolve(strict=True) and record['original_sha256']==prior_sha,'candidate original mismatch')
        check(stage.sha256(record['candidate'])==record['candidate_sha256'],'candidate SHA mismatch')
        canonical[(site,year)]=record
    check(set(canonical)==set(COUNTS),'candidate inventory mismatch')
    root,data=s26.inputs(stage.ROOT)
    for (site,year),record in sorted(canonical.items()):
        item=data[site]; orig=item['files'][year-item['years'][0]].resolve(strict=True)
        candidate=Path(record['candidate']).resolve(strict=True); changes=record['changes']
        recorded_orig=record.get('original',record.get('source')); recorded_sha=record.get('original_sha256',record.get('source_sha256'))
        check(len(changes)==COUNTS[(site,year)] and orig==Path(recorded_orig).resolve(strict=True),'unexpected candidate identity or count')
        check(stage.sha256(orig)==recorded_sha and stage.sha256(candidate)==record['candidate_sha256'],'file SHA mismatch')
        inds=verify_file(orig,candidate,changes)
        if (site,year)==('US-Aud',2012):
            meta=item['receipt']; shift=int(meta['UTC_shift_halfhours'])
            for time in ('2012-08-28 19:00:00','2012-08-28 19:30:00','2012-08-29 02:00:00','2012-08-29 02:30:00'):
                y,i=phys.utc_index(time,shift,*item['years']); check(y==2012 and i not in inds,'user-retained 2012 record changed '+time)
        item['files'][year-item['years'][0]]=candidate
        print('STAGE70 CANDIDATE VERIFIED',site,year,'edits',len(changes),'candidate',candidate,flush=True)
    helper=s26.load_helper(a.helper); d.setup(s26,helper,root,data)
    proofs={site:[{'year':year,'candidate':str(Path(f['candidate']).resolve(strict=True)),
                   'candidate_sha256':f['candidate_sha256'],
                   'original_sha256':f.get('original_sha256',f.get('source_sha256')),
                   'edit_count':len(f['changes'])}
                  for (s,year),f in sorted(canonical.items()) if s==site] for site in SITES}
    execute(a.action,helper,d,data,proofs,a.co2_csv)

if __name__=='__main__': main()
