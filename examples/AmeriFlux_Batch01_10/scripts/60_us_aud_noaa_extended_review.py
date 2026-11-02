#!/usr/bin/env python3
"""Stage60: read-only US-Aud tower/ERA/candidate/independent NOAA review.

Expands Stage59's unresolved episodes, including the censored 2023-12-19
boundary, and prints comparable half-hour values. NOAA station height and
sampling are different; comparisons are evidence, not automatic repairs.
Only a private CSV/JSON review report is created; no forcing/case/Slurm writes.
"""
from __future__ import annotations
import argparse, csv, hashlib, importlib.util, json, math, urllib.request
from datetime import datetime, timedelta
from pathlib import Path

HOME=Path('/iridisfs/home/ly3n24/CLM_FATES_PLOTS')
PIN59='09d6cc0cad4494b75a0671c1c8f11df41a830533'
PIN58='82b63dbf16665df05060c7ed70ea77023ba2cea5'
PIN29='6f6e594d2ed57ac2c00c9af2f325cd179b10ecb3'
NOAA_SHA={2012:'3ceb58596137d5282c0c4f680e7585562e0e868bfce9f062775afb59a0103e14',
          2023:'137dd43c1dc621e6e04ee67c4a437eea41b9dee811a7c7b8924623b4754aa514'}
WINDOWS=[
 ('2012_AM','2012-08-28 06:00:00','2012-08-28 11:30:00'),
 ('2012_PM','2012-08-28 18:00:00','2012-08-28 20:30:00'),
 ('2012_NIGHT','2012-08-29 01:00:00','2012-08-29 03:30:00'),
 ('2023_APR_MORNING','2023-04-30 08:30:00','2023-04-30 10:30:00'),
 ('2023_APR_AFTERNOON','2023-04-30 14:30:00','2023-04-30 19:30:00'),
 ('2023_DEC18','2023-12-18 16:30:00','2023-12-18 21:00:00'),
 ('2023_DEC19_EXPANDED','2023-12-19 13:30:00','2023-12-20 06:00:00'),
]
FIELDS=('window','time_local','tower_T_C','tower_T_QC','tower_VPD_hPa','tower_VPD_QC',
        'ERA_T_C','ERA_VPD_hPa','selected_T_C','selected_VPD_hPa','candidate_edit',
        'candidate_T_C','candidate_VPD_hPa','NOAA_T_C','NOAA_RH_pct','NOAA_VPD_hPa',
        'NOAA_good_5min','tower_minus_NOAA_T_C','tower_minus_ERA_T_C','review_flags')


def check(ok,message):
    if not ok: raise ValueError(message)


def blob(raw): return hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()


def module(path,name,expected):
    p=Path(path).resolve(strict=True); check(blob(p.read_bytes())==expected,name+' checksum mismatch')
    spec=importlib.util.spec_from_file_location(name,p); m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m


def ticks(start,end):
    a,b=datetime.fromisoformat(start),datetime.fromisoformat(end)
    check(a<=b and a.minute in (0,30) and b.minute in (0,30),'invalid window')
    return [(a+timedelta(minutes=30*i)).strftime('%Y-%m-%d %H:%M:%S') for i in range(int((b-a).total_seconds()/1800)+1)]


def val(row,key):
    try:
        x=float(row.get(key,'')); return x if math.isfinite(x) and x>-9990 else None
    except (ValueError,TypeError): return None


def noaa(year,times):
    wanted={}; samples={t:{} for t in times}
    for local in times:
        start=datetime.fromisoformat(local)+timedelta(hours=7)
        for minute in (5,10,15,20,25,30): wanted[(start+timedelta(minutes=minute)).strftime('%Y%m%d%H%M')]=(local,minute)
    url=f'https://www.ncei.noaa.gov/pub/data/uscrn/products/subhourly01/{year}/CRNS0101-05-{year}-AZ_Elgin_5_S.txt'
    req=urllib.request.Request(url,headers={'User-Agent':'Research-Input-QC/1.0'}); h=hashlib.sha256(); n=0
    with urllib.request.urlopen(req,timeout=90) as f:
        for line in f:
            h.update(line); n+=len(line); check(n<=30_000_000,'unexpected NOAA file size')
            p=line.decode('ascii').split(); check(len(p)>=17 and p[0]=='53132','unexpected NOAA format/station')
            key=p[1]+p[2].zfill(4)
            if key not in wanted: continue
            local,minute=wanted[key]; utc=datetime.strptime(key,'%Y%m%d%H%M'); lst=datetime.strptime(p[3]+p[4].zfill(4),'%Y%m%d%H%M')
            check(utc-lst==timedelta(hours=7) and abs(float(p[7])-31.5907)<.05 and abs(float(p[6])+110.5104)<.05,'NOAA clock/location mismatch')
            check(minute not in samples[local],'duplicate NOAA timestamp')
            t,rh=float(p[8]),float(p[15])
            if math.isfinite(t) and -90<t<65 and 0<rh<=100 and p[16]=='0': samples[local][minute]=(t,rh)
            else: samples[local][minute]=None
    check(h.hexdigest()==NOAA_SHA[year],f'NOAA {year} file differs from previously reviewed SHA; inspect source update')
    result={}
    for time,values in samples.items():
        valid=[values[k] for k in sorted(values) if values[k] is not None]
        item={'good':len(valid),'T':None,'RH':None,'VPD':None}
        if len(values)==6 and len(valid)==6:
            item['T']=sum(t for t,rh in valid)/6; item['RH']=sum(rh for t,rh in valid)/6
            item['VPD']=sum(6.112*math.exp(17.67*t/(t+243.5))*(1-rh/100) for t,rh in valid)/6
        result[time]=item
    return result,{'url':url,'sha256':h.hexdigest(),'bytes':n,'station':'USCRN AZ Elgin 5 S, WBAN 53132'}


def main():
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('--self-test',action='store_true')
    for opt in ('stage59','stage58','context-helper'): p.add_argument('--'+opt,required=True,type=Path)
    p.add_argument('--approved',type=Path,default=HOME/'approved_met_candidates.TVqWqlLi/result/manifest.json')
    p.add_argument('--joint',type=Path,default=HOME/'approved_cbo_caman.b5Ve5c8S/result/manifest.json')
    p.add_argument('--merged',type=Path,default=HOME/'approved_q1_cbo.QeDyqeSz/result/manifest.json')
    p.add_argument('--out',type=Path); a=p.parse_args()
    stage=module(a.stage59,'stage59_60',PIN59); s58=module(a.stage58,'stage58_60',PIN58); h=module(a.context_helper,'context29_60',PIN29)
    check(callable(getattr(stage,'select_canonical',None)) and callable(getattr(stage,'verify_sources',None)),'Stage59 API mismatch')
    if a.self_test:
        check(len(ticks('2023-12-19 23:30:00','2023-12-20 00:30:00'))==3,'cross-day time test')
        check(sum(1 for item in WINDOWS if item[0]=='2023_DEC19_EXPANDED')==1,'expanded window test')
        print('STAGE60 SELF-TEST PASS | pinned helper APIs and time windows; NO WRITES',flush=True); return
    check(a.out is not None,'--out is required'); out=a.out.expanduser().resolve()
    check(not out.exists() and not out.is_symlink(),'output directory already exists')
    selected=stage.select_canonical(s58,a); stage.verify_sources(selected,stage.ROOT,s58)
    recs={r['site']:r for r in s58.read_json(stage.ROOT/'COMPLETE.json')['sites']}; rec=recs['US-Aud']
    manifest=Path(rec['manifest']).resolve(strict=True); check(stage.ROOT.resolve() in manifest.parents and stage.sha256(manifest)==rec['sha256'],'US-Aud manifest mismatch')
    meta=s58.read_json(manifest); check(abs(float(meta['UTC_offset_hours'])+7)<1e-8,'US-Aud offset differs from UTC-7')
    with h.STAGE80.open(encoding='utf-8-sig',newline='') as f: chosen=next(r for r in csv.DictReader(f,delimiter='\t') if r['site']=='US-Aud')
    source=Path(chosen['selected_source']).resolve(strict=True); check(stage.sha256(source)==chosen['selected_sha256'],'Stage80 SHA mismatch')
    tower,ti=h.sources('US-Aud','FLUXMET_HH'); era,ei=h.sources('US-Aud','ERA5_HH')
    check(tower is not None and era is not None,'tower or ERA source missing/ambiguous')
    times=sorted({t for _,a0,b0 in WINDOWS for t in ticks(a0,b0)}); wanted=set(times)
    print('STAGE60 VERIFY | seven canonical candidate/source files; reading tower and ERA',flush=True)
    sr=h.read_subset(source,'time',wanted,('TA_USE','VPD_USE'))
    tw=h.read_subset(tower,'TIMESTAMP_START',wanted,('TA_F','TA_F_QC','VPD_F','VPD_F_QC'),True)
    er=h.read_subset(era,'TIMESTAMP_START',wanted,('TA_ERA','VPD_ERA'),True)
    for label,rows in (('selected',sr),('tower',tw),('ERA',er)):
        missing=sorted(wanted-set(rows)); check(not missing,f'{label} source missing {len(missing)} rows: {missing[:3]}')
    edits={}
    for (site,year),file in selected.items():
        if site!='US-Aud': continue
        for change in file['changes']:
            time=change['time_local']; check(time not in edits,'duplicate candidate time')
            edits[time]=change
    observed={}; noaa_sources=[]
    for year in (2012,2023):
        print('STAGE60 NOAA SOURCE',year,'loading official public archive',flush=True)
        vals,info=noaa(year,[t for t in times if int(t[:4])==year]); observed.update(vals); noaa_sources.append(info)
    rows=[]; summaries=[]
    for label,start,end in WINDOWS:
        stamps=ticks(start,end); window_rows=[]
        for time in stamps:
            t,e,s=tw[time],er[time],sr[time]; ref=observed[time]; change=edits.get(time)
            tt,tv,et,ev=val(t,'TA_F'),val(t,'VPD_F'),val(e,'TA_ERA'),val(e,'VPD_ERA')
            dt_noaa=tt-ref['T'] if tt is not None and ref['T'] is not None else None
            dt_era=tt-et if tt is not None and et is not None else None
            flags=[]
            if dt_era is not None and abs(dt_era)>=8: flags.append('ERA_T_DIFF_GE8')
            if tv is not None and ev is not None and abs(tv-ev)>=10: flags.append('ERA_VPD_DIFF_GE10')
            if dt_noaa is not None and abs(dt_noaa)>=8: flags.append('NOAA_T_DIFF_GE8')
            if tv is not None and ref['VPD'] is not None and abs(tv-ref['VPD'])>=10: flags.append('NOAA_VPD_DIFF_GE10')
            if tt==0 and tv==0: flags.append('T_AND_VPD_ZERO')
            r={'window':label,'time_local':time,'tower_T_C':tt,'tower_T_QC':val(t,'TA_F_QC'),
               'tower_VPD_hPa':tv,'tower_VPD_QC':val(t,'VPD_F_QC'),'ERA_T_C':et,'ERA_VPD_hPa':ev,
               'selected_T_C':val(s,'TA_USE'),'selected_VPD_hPa':val(s,'VPD_USE'),'candidate_edit':bool(change),
               'candidate_T_C':change.get('candidate_TA_C') if change else None,
               'candidate_VPD_hPa':change.get('candidate_VPD_hPa') if change else None,
               'NOAA_T_C':ref['T'],'NOAA_RH_pct':ref['RH'],'NOAA_VPD_hPa':ref['VPD'],'NOAA_good_5min':ref['good'],
               'tower_minus_NOAA_T_C':dt_noaa,'tower_minus_ERA_T_C':dt_era,'review_flags':','.join(flags)}
            rows.append(r); window_rows.append(r)
            text=lambda v:'NA' if v is None else f'{v:.2f}' if isinstance(v,float) else str(v)
            print('STAGE60 ROW',label,time,'tower',text(tt),'TQC',text(r['tower_T_QC']),'VPD',text(tv),'VQC',text(r['tower_VPD_QC']),
                  'ERA',text(et),'ERA_VPD',text(ev),'NOAA',text(ref['T']),'NOAA_RH',text(ref['RH']),'NOAA_VPD',text(ref['VPD']),
                  'NOAA_5MIN',ref['good'],'candidate',text(r['candidate_T_C']),'candidate_VPD',text(r['candidate_VPD_hPa']),
                  'flags',r['review_flags'] or '-',flush=True)
        summaries.append({'window':label,'start':start,'end':end,'rows':len(window_rows),'flagged':sum(bool(x['review_flags']) for x in window_rows),
                          'noaa_missing':sum(x['NOAA_T_C'] is None for x in window_rows),
                          'first_flagged':bool(window_rows[0]['review_flags']),'last_flagged':bool(window_rows[-1]['review_flags'])})
        print('STAGE60 WINDOW',json.dumps(summaries[-1],sort_keys=True),flush=True)
    out.mkdir(parents=True)
    with (out/'us_aud_review.csv').open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=FIELDS); w.writeheader(); w.writerows(rows)
    manifest={'status':'READ_ONLY_REVIEW','rows':len(rows),'windows':summaries,'noaa_sources':noaa_sources,
        'clock':'local standard interval start UTC-7; USCRN values are five-minute interval ends',
        'temperature_vpd_thresholds_are_diagnostic_only':True,'tower_qc0_is_not_proof_of_correctness':True,
        'NOAA_and_ERA_are_not_automatically_tower_truth':True,'candidate_values_are_from_validated_manifests':True,
        'no_original_candidate_or_case_modified':True,'no_slurm_jobs':True,
        'stage80_selected_sha256':chosen['selected_sha256'],'tower_source':ti,'ERA_source':ei}
    (out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
    print('STAGE60 COMPLETE',len(rows),'rows; CSV',out/'us_aud_review.csv','MANIFEST',out/'manifest.json',flush=True)
    print('SCIENCE HOLD | differences are review markers; do not automatically replace measured QC0',flush=True)
    print('READ ONLY | no forcing/candidate/case/Slurm writes',flush=True)


if __name__=='__main__': main()
