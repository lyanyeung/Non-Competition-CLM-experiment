#!/usr/bin/env python3
"""Stage62: detached US-Aud NOAA candidates for 28 user-approved half-hours.

Reads the verified Stage60 tower/ERA/NOAA review and original forcing, retains
all seven pre-existing US-Aud candidate edits, and produces new annual files
for 2012 and 2023. Preserves original QC in the change manifest. Rechecks NOAA
five-minute values and coupled humidity. Does not activate inputs or submit.
"""
from __future__ import annotations
import argparse, csv, hashlib, importlib.util, json, math
from datetime import datetime, timedelta
from pathlib import Path
from netCDF4 import Dataset

HOME=Path('/iridisfs/home/ly3n24/CLM_FATES_PLOTS')
PINS={'stage59':'09d6cc0cad4494b75a0671c1c8f11df41a830533','stage58':'82b63dbf16665df05060c7ed70ea77023ba2cea5',
      'context':'6f6e594d2ed57ac2c00c9af2f325cd179b10ecb3','noaa':'10cbb506af8781a130db793e93ea9d4ce5612f2a',
      'humidity':'8a0b8585c3478af6abf42dc714fd52397f3b0b6b','merge':'3c9b0f93cdb731cb434a850c96c9620f7471d415',
      'physics':'12799912ed323a28cc12c502d2c35eaf70ee0b97'}
NOAA_SHA={2012:'3ceb58596137d5282c0c4f680e7585562e0e868bfce9f062775afb59a0103e14',
          2023:'137dd43c1dc621e6e04ee67c4a437eea41b9dee811a7c7b8924623b4754aa514'}
GROUPS=[('2012_QC0','2012-08-28 07:30:00',7,0),('2023_APR_QC1','2023-04-30 17:00:00',3,1),
        ('2023_DEC18_QC1','2023-12-18 19:30:00',3,1),('2023_DEC19_QC1','2023-12-19 13:30:00',15,1)]


def check(ok,msg):
    if not ok: raise ValueError(msg)


def load(path,name):
    path=Path(path).resolve(strict=True); raw=path.read_bytes()
    sha=hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()
    check(sha==PINS[name],name+' helper checksum mismatch')
    spec=importlib.util.spec_from_file_location('stage62_'+name,path); m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m


def group_times(start,count):
    base=datetime.fromisoformat(start)
    return [(base+timedelta(minutes=30*i)).strftime('%Y-%m-%d %H:%M:%S') for i in range(count)]


def number(x):
    n=float(x); check(math.isfinite(n) and n>-9990,'invalid numeric value'); return n


def close(a,b,msg,tol=.002):
    check(abs(number(a)-number(b))<=tol,msg)


def met(ds,index):
    t=float(ds['TBOT'][index,0,0])-273.15; q=float(ds['QBOT'][index,0,0]); p=float(ds['PSRF'][index,0,0])/100
    check(-90<t<65 and 0<q<.08 and 490<p<1110,'nonphysical forcing at boundary')
    es=6.112*math.exp(17.67*t/(t+243.5)); e=q*p/(.622+.378*q)
    return t,es-e


def main():
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('--self-test',action='store_true')
    for name in PINS: p.add_argument('--'+name,required=True,type=Path)
    p.add_argument('--review',required=True,type=Path)
    p.add_argument('--approved',type=Path,default=HOME/'approved_met_candidates.TVqWqlLi/result/manifest.json')
    p.add_argument('--joint',type=Path,default=HOME/'approved_cbo_caman.b5Ve5c8S/result/manifest.json')
    p.add_argument('--merged',type=Path,default=HOME/'approved_q1_cbo.QeDyqeSz/result/manifest.json')
    p.add_argument('--out',type=Path); a=p.parse_args()
    modules={name:load(getattr(a,name),name) for name in PINS}
    stage,s58,h,noaa,humidity,merge,physics=(modules[x] for x in ('stage59','stage58','context','noaa','humidity','merge','physics'))
    check(callable(getattr(stage,'select_canonical',None)) and callable(getattr(noaa,'noaa',None)) and
          callable(getattr(merge,'save_candidate',None)) and callable(getattr(humidity,'from_noaa',None)), 'helper API mismatch')
    requested={t:(label,qc) for label,start,count,qc in GROUPS for t in group_times(start,count)}
    check(len(requested)==28,'approved intervals overlap or wrong size')
    if a.self_test:
        check(group_times('2023-12-19 13:30:00',15)[-1]=='2023-12-19 20:30:00','episode endpoint mismatch')
        print('STAGE62 SELF-TEST PASS | pinned APIs, 28 approved records; NO WRITES',flush=True); return
    check(a.out is not None,'--out is required'); out=a.out.expanduser().resolve()
    check(not out.exists() and not out.is_symlink(),'output path already exists')
    review=a.review.resolve(strict=True); report=json.loads((review/'manifest.json').read_text()); review_csv=review/'us_aud_review.csv'
    check(report.get('status')=='READ_ONLY_REVIEW' and report.get('no_original_candidate_or_case_modified') is True and
          report.get('no_slurm_jobs') is True,'Stage60 report is not a read-only review')
    reviewed={}
    with review_csv.open(encoding='utf-8-sig',newline='') as f:
        for row in csv.DictReader(f):
            time=row['time_local']
            if time in requested:
                check(time not in reviewed,'duplicate reviewed timestamp '+time); reviewed[time]=row
    check(set(reviewed)==set(requested),'Stage60 review lacks approved timestamps')
    canonical=stage.select_canonical(s58,a); stage.verify_sources(canonical,stage.ROOT,s58)
    rec,m,sel,source,tower,era,tinfo,einfo=merge.get_inputs(h,stage.ROOT,'US-Aud')
    check(abs(float(m['UTC_offset_hours'])+7)<1e-8,'US-Aud offset changed')
    wanted=set(requested)
    selected=h.read_subset(source,'time',wanted,('TA_USE','VPD_USE','QBOT','PSRF'))
    original=h.read_subset(tower,'TIMESTAMP_START',wanted,('TA_F','TA_F_QC','VPD_F','VPD_F_QC'),True)
    check(set(selected)==wanted and set(original)==wanted,'missing source timestamp')
    events={}
    for time,(label,qc) in requested.items():
        r=reviewed[time]; s=selected[time]; t=original[time]
        check(r['candidate_edit'].lower()=='false','requested time already has a candidate '+time)
        for actual,reviewed_value in ((s['TA_USE'],r['selected_T_C']),(s['VPD_USE'],r['selected_VPD_hPa']),
            (t['TA_F'],r['tower_T_C']),(t['VPD_F'],r['tower_VPD_hPa']),
            (t['TA_F_QC'],r['tower_T_QC']),(t['VPD_F_QC'],r['tower_VPD_QC'])):
            close(actual,reviewed_value,'source differs from Stage60 review '+time)
        check(number(t['TA_F_QC'])==qc and number(t['VPD_F_QC'])==qc,'unexpected original QC '+time)
        check(int(r['NOAA_good_5min'])==6,'reviewed NOAA interval is incomplete '+time)
        events[time]=(number(s['TA_USE']),number(s['VPD_USE']),number(r['NOAA_T_C']),number(r['NOAA_RH_pct']))
    # Stage53 accepts (original T, original VPD, reviewed NOAA T, reviewed NOAA RH).
    noaa.EVENTS=events; noaa.SHA=dict(NOAA_SHA); sources={}
    for year in (2012,2023):
        print('STAGE62 NOAA SOURCE',year,'rechecking public five-minute archive',flush=True)
        sources[year]=noaa.noaa(year)
        print('STAGE62 NOAA VERIFIED',year,sources[year]['sha256'],flush=True)
    changes=[]
    for time,(label,qc) in sorted(requested.items()):
        s=selected[time]; source_noaa=sources[int(time[:4])]; samples=source_noaa['samples'][time]
        pressure=number(s['PSRF']); t,v,q,rh=humidity.from_noaa(samples,pressure)
        row=reviewed[time]; close(t,row['NOAA_T_C'],'NOAA T differs from reviewed '+time,.015)
        year,index=physics.utc_index(time,int(m['UTC_shift_halfhours']),*m['years'])
        check(year==int(time[:4]),'unexpected UTC output year '+time)
        changes.append({'site':'US-Aud','group':label,'time_local':time,'UTC_year':year,'UTC_index':index,
            'original_TA_C':number(s['TA_USE']),'original_VPD_hPa':number(s['VPD_USE']),
            'original_TA_QC':qc,'original_VPD_QC':qc,'pressure_Pa':pressure,
            'candidate_TA_C':t,'candidate_VPD_hPa':v,'candidate_QBOT':q,'candidate_RH_pct':rh,
            'method':{'type':'USER_APPROVED_NOAA_USCRN_T_RH','station':'53132 AZ Elgin 5 S',
                'url':source_noaa['url'],'annual_sha256':source_noaa['sha256'],'five_minute_samples':samples,
                'humidity':'mean of six specific humidities at the original half-hour pressure'}})
    out.mkdir(parents=True); outputs=[]; paths={}
    for year in (2012,2023):
        base=canonical[('US-Aud',year)]; source_record,src=merge.src_nc(h,stage.ROOT,m,year)
        original_path=Path(base.get('original',base.get('source'))).resolve(strict=True)
        check(original_path==src and base.get('original_sha256',base.get('source_sha256'))==source_record['sha256'],
              'canonical candidate source mismatch')
        candidate=Path(base['candidate']).resolve(strict=True)
        check(stage.sha256(candidate)==base['candidate_sha256'],'canonical candidate checksum changed')
        group=[x for x in changes if x['UTC_year']==year]
        for row in group: merge.validate_origin(src,row,selected[row['time_local']])
        result=merge.save_candidate(h,src,candidate,out/f'US-Aud_{year}_approved_extended_NOAA_sensitivity.nc',base['changes'],group)
        result.update(site='US-Aud',year=year,stage23_manifest_sha256=rec['sha256'],stage80_sha256=sel['selected_sha256'])
        paths[year]=Path(result['candidate']); outputs.append(result)
        print('STAGE62 YEAR',year,'prior_edits',len(base['changes']),'new_edits',len(group),'total',len(result['changes']),flush=True)
        for row in group: print('STAGE62 APPROVED',json.dumps(row,sort_keys=True),flush=True)
    boundaries=[]
    for label,start,count,qc in GROUPS:
        subset=sorted((x for x in changes if x['group']==label),key=lambda x:x['UTC_index'])
        check(len(subset)==count and len({x['UTC_year'] for x in subset})==1,'group year/count mismatch '+label)
        indices=[x['UTC_index'] for x in subset]
        check(indices==list(range(indices[0],indices[0]+count)) and indices[0]>0 and indices[-1]<17519,'group indices not contiguous or at year edge')
        with Dataset(str(paths[subset[0]['UTC_year']])) as ds:
            left0,left1=met(ds,indices[0]-1),met(ds,indices[0]); right0,right1=met(ds,indices[-1]),met(ds,indices[-1]+1)
        ld,lv=left1[0]-left0[0],left1[1]-left0[1]; rd,rv=right1[0]-right0[0],right1[1]-right0[1]
        b={'group':label,'left_dT_C':ld,'left_dVPD_hPa':lv,'right_dT_C':rd,'right_dVPD_hPa':rv,
           'boundary_over_4':any(abs(x)>4 for x in (ld,lv,rd,rv))}
        boundaries.append(b); print('STAGE62 BOUNDARY',json.dumps(b,sort_keys=True),flush=True)
    final={'status':'DETACHED_NOT_USED_BY_CASES','files':outputs,'new_changes':28,'boundaries':boundaries,
           'review_csv':str(review_csv),'review_csv_sha256':stage.sha256(review_csv),
           'review_manifest':str(review/'manifest.json'),'review_manifest_sha256':stage.sha256(review/'manifest.json'),
           'user_decision':'2012 QC0 07:30-10:30; 2023 Apr Q1 17:00-18:00; Dec18 Q1 19:30-20:30; Dec19 Q1 13:30-20:30',
           'boundary_caveat':'Dec19 13:30 is provisional; preceding interval requires Stage61 review',
           'other_sources_and_unreviewed_records_remain':True,'no_original_or_case_modified':True,'no_slurm_jobs':True,
           'station_source':tinfo,'ERA_source':einfo}
    (out/'manifest.json').write_text(json.dumps(final,indent=2)+'\n',encoding='utf-8')
    print('STAGE62 COMPLETE 28 approved detached candidates; manifest',out/'manifest.json',flush=True)
    print('SCIENCE HOLD | proxies are not tower observations; inspect boundaries and remaining events before production',flush=True)
    print('NO ORIGINAL/CANDIDATE/CASE/SLURM MODIFIED',flush=True)


if __name__=='__main__': main()
