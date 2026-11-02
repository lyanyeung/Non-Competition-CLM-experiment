#!/usr/bin/env python3
"""Read-only audit of reviewed candidate years and direct AD400 preflight."""
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

def main():
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('--self-test',action='store_true')
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
        print('STAGE68 SELF-TEST PASS | pinned helpers and candidate counts; NO WRITES',flush=True); return
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
        check(Path(record['original']).resolve(strict=True)==Path(prior['original']).resolve(strict=True) and record['original_sha256']==prior['original_sha256'],'candidate original mismatch')
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
        print('STAGE68 CANDIDATE VERIFIED',site,year,'edits',len(changes),'candidate',candidate,flush=True)
    helper=s26.load_helper(a.helper); d.setup(s26,helper,root,data); failed=[]
    for site in SITES:
        try:
            d.preflight(helper,data,a.co2_csv,(site,),input_label='reviewed detached candidates plus verified Stage23')
            print('STAGE68 PREFLIGHT PASS',site,flush=True)
        except Exception as exc:
            failed.append(site); print('STAGE68 PREFLIGHT HOLD',site,type(exc).__name__,str(exc),flush=True)
    print('STAGE68 COMPLETE | candidate/source integrity verified; user-retained 2012 records unchanged; preflight holds:',','.join(failed) or 'none',flush=True)
    print('SCIENCE NOTE | sensitivity inputs; prior unresolved flags and proxy heights remain documented; no case or SLURM job created',flush=True)
    if failed: raise SystemExit(1)

if __name__=='__main__': main()
