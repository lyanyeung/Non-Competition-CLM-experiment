#!/usr/bin/env python3
"""Stage64: add 12 user-approved US-Aud NOAA records to Stage62 candidate.

The 2023-12-19 10:00 QC0 record is preserved, and its humidity is reviewed
using available tower, ERA and NOAA fields. All output is detached; no jobs.
"""
import argparse, csv, hashlib, importlib.util, json, math
from datetime import datetime, timedelta
from pathlib import Path
from netCDF4 import Dataset

HOME=Path('/iridisfs/home/ly3n24/CLM_FATES_PLOTS')
PINS={'stage59':'09d6cc0cad4494b75a0671c1c8f11df41a830533','stage58':'82b63dbf16665df05060c7ed70ea77023ba2cea5',
      'context':'6f6e594d2ed57ac2c00c9af2f325cd179b10ecb3','noaa':'10cbb506af8781a130db793e93ea9d4ce5612f2a',
      'humidity':'8a0b8585c3478af6abf42dc714fd52397f3b0b6b','merge':'3c9b0f93cdb731cb434a850c96c9620f7471d415',
      'physics':'12799912ed323a28cc12c502d2c35eaf70ee0b97','boundary':'2f7f77c1cc9ca8da9ead0a14b7f842b56020be7f'}
NOAA_SHA='137dd43c1dc621e6e04ee67c4a437eea41b9dee811a7c7b8924623b4754aa514'
GROUPS=[('2023_APR_MORNING','2023-04-30 09:30:00',6),('2023_DEC19_BEFORE','2023-12-19 10:30:00',6)]
HOLD='2023-12-19 10:00:00'
FIELDS=('TBOT','QBOT','SHUM','RH')


def check(ok,msg):
    if not ok: raise ValueError(msg)


def load(path,name):
    p=Path(path).resolve(strict=True); raw=p.read_bytes()
    digest=hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()
    check(digest==PINS[name],name+' helper checksum mismatch')
    spec=importlib.util.spec_from_file_location('stage64_'+name,p); m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m


def ticks(start,count):
    t=datetime.fromisoformat(start)
    return [(t+timedelta(minutes=30*i)).strftime('%Y-%m-%d %H:%M:%S') for i in range(count)]


def number(x):
    x=float(x); check(math.isfinite(x) and x>-9990,'invalid numeric value'); return x


def close(a,b,msg,tol=.002): check(abs(number(a)-number(b))<=tol,msg)


def rh_from_tvpd(temp,vpd):
    es=6.112*math.exp(17.67*temp/(temp+243.5)); return 100*(1-vpd/es)


def main():
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('--self-test',action='store_true')
    for name in PINS: p.add_argument('--'+name,required=True,type=Path)
    p.add_argument('--review',required=True,type=Path); p.add_argument('--previous',required=True,type=Path)
    p.add_argument('--approved',type=Path,default=HOME/'approved_met_candidates.TVqWqlLi/result/manifest.json')
    p.add_argument('--joint',type=Path,default=HOME/'approved_cbo_caman.b5Ve5c8S/result/manifest.json')
    p.add_argument('--merged',type=Path,default=HOME/'approved_q1_cbo.QeDyqeSz/result/manifest.json')
    p.add_argument('--out',type=Path); a=p.parse_args()
    modules={name:load(getattr(a,name),name) for name in PINS}
    stage,s58,h,noaa,humidity,merge,physics,boundary=(modules[x] for x in ('stage59','stage58','context','noaa','humidity','merge','physics','boundary'))
    check(callable(getattr(stage,'select_canonical',None)) and callable(getattr(noaa,'noaa',None)) and
          callable(getattr(merge,'save_candidate',None)) and callable(getattr(boundary,'met',None)),'helper API mismatch')
    requested={time:label for label,start,count in GROUPS for time in ticks(start,count)}
    check(len(requested)==12 and HOLD not in requested,'approved periods overlap or include held record')
    if a.self_test:
        check(ticks('2023-04-30 09:30:00',6)[-1]=='2023-04-30 12:00:00','April endpoint')
        check(ticks('2023-12-19 10:30:00',6)[-1]=='2023-12-19 13:00:00','December endpoint')
        print('STAGE64 SELF-TEST PASS | pinned helpers, 12 approvals, held QC0; NO WRITES',flush=True); return
    check(a.out is not None,'--out is required'); out=a.out.expanduser().resolve()
    check(not out.exists() and not out.is_symlink(),'output already exists')
    review=a.review.resolve(strict=True); review_manifest=review/'manifest.json'; review_csv=review/'us_aud_review.csv'
    report=json.loads(review_manifest.read_text()); check(report.get('status')=='READ_ONLY_REVIEW' and
        report.get('no_original_candidate_or_case_modified') is True and report.get('no_slurm_jobs') is True,'Stage61 review invalid')
    reviewed={}
    context_times=set(ticks('2023-12-19 09:00:00',5))
    with review_csv.open(encoding='utf-8-sig',newline='') as f:
        for row in csv.DictReader(f):
            time=row['time_local']
            if time in requested or time in context_times:
                check(time not in reviewed,'duplicate review timestamp '+time); reviewed[time]=row
    check(set(requested)|context_times <= set(reviewed),'Stage61 review missing required timestamps')
    previous=a.previous.resolve(strict=True); old=json.loads(previous.read_text())
    check(old.get('status')=='DETACHED_NOT_USED_BY_CASES' and old.get('no_original_or_case_modified') is True and old.get('no_slurm_jobs') is True,'Stage62 candidate manifest invalid')
    old2023=next(x for x in old['files'] if x['site']=='US-Aud' and int(x['year'])==2023)
    old2012=next(x for x in old['files'] if x['site']=='US-Aud' and int(x['year'])==2012)
    check(len(old2023['changes'])==27 and len(old2012['changes'])==8,'Stage62 candidate counts changed')
    for item in (old2023,old2012): check(stage.sha256(item['candidate'])==item['candidate_sha256'],'Stage62 candidate checksum changed')
    canonical=stage.select_canonical(s58,a); stage.verify_sources(canonical,stage.ROOT,s58)
    rec,meta,sel,source,tower,era,tinfo,einfo=merge.get_inputs(h,stage.ROOT,'US-Aud')
    check(abs(float(meta['UTC_offset_hours'])+7)<1e-8,'US-Aud time offset changed')
    entry,original=merge.src_nc(h,stage.ROOT,meta,2023)
    check(Path(old2023['original']).resolve(strict=True)==original and old2023['original_sha256']==entry['sha256'],
          'Stage62 candidate uses a different source')
    check(old2023.get('stage23_manifest_sha256')==rec['sha256'] and old2023.get('stage80_sha256')==sel['selected_sha256'],
          'Stage62 source lineage changed')
    wanted=set(requested)|context_times
    selected=h.read_subset(source,'time',wanted,('TA_USE','VPD_USE','QBOT','PSRF'))
    tower_rows=h.read_subset(tower,'TIMESTAMP_START',wanted,('TA','TA_F','TA_F_QC','VPD','VPD_F','VPD_F_QC','RH','RH_F','SW_IN_F','P_F'),True)
    er=h.read_subset(era,'TIMESTAMP_START',wanted,('TA_ERA','VPD_ERA'),True)
    check(set(selected)==wanted and set(tower_rows)==wanted and set(er)==wanted,'source timestamps missing')
    events={}
    for time in requested:
        r=reviewed[time]; s=selected[time]; t=tower_rows[time]
        check(r['candidate_edit'].lower()=='false','new approved time already edited '+time)
        for actual,was in ((s['TA_USE'],r['selected_T_C']),(s['VPD_USE'],r['selected_VPD_hPa']),
                           (t['TA_F'],r['tower_T_C']),(t['VPD_F'],r['tower_VPD_hPa']),
                           (t['TA_F_QC'],r['tower_T_QC']),(t['VPD_F_QC'],r['tower_VPD_QC'])):
            close(actual,was,'source differs from user-reviewed Stage61 '+time)
        expected_qc=0 if time=='2023-04-30 09:30:00' else 1
        check(number(t['TA_F_QC'])==expected_qc and number(t['VPD_F_QC'])==expected_qc,'unexpected QC '+time)
        check(int(r['NOAA_good_5min'])==6,'NOAA missing five-minute samples '+time)
        events[time]=(number(s['TA_USE']),number(s['VPD_USE']),number(r['NOAA_T_C']),number(r['NOAA_RH_pct']))
    noaa.EVENTS=events; noaa.SHA={2023:NOAA_SHA}
    print('STAGE64 NOAA SOURCE 2023 | rechecking approved five-minute intervals',flush=True)
    ndata=noaa.noaa(2023); changes=[]
    for time,label in sorted(requested.items()):
        s=selected[time]; tower_info=tower_rows[time]; pressure=number(s['PSRF']); samples=ndata['samples'][time]
        temp,vpd,q,rh=humidity.from_noaa(samples,pressure); year,index=physics.utc_index(time,int(meta['UTC_shift_halfhours']),*meta['years'])
        check(year==2023,'unexpected UTC year '+time)
        row={'site':'US-Aud','group':label,'time_local':time,'UTC_year':year,'UTC_index':index,
             'original_TA_C':number(s['TA_USE']),'original_VPD_hPa':number(s['VPD_USE']),
             'original_tower_TA_C':number(tower_info['TA_F']),'original_tower_VPD_hPa':number(tower_info['VPD_F']),
             'original_TA_QC':int(number(tower_info['TA_F_QC'])),'original_VPD_QC':int(number(tower_info['VPD_F_QC'])),
             'pressure_Pa':pressure,'candidate_TA_C':temp,'candidate_VPD_hPa':vpd,'candidate_QBOT':q,'candidate_RH_pct':rh,
             'method':{'type':'USER_APPROVED_NOAA_USCRN_T_RH','station':'53132 AZ Elgin 5 S','url':ndata['url'],
                       'annual_sha256':ndata['sha256'],'five_minute_samples':samples,
                       'humidity':'mean of six specific humidities at original half-hour pressure'}}
        merge.validate_origin(original,row,s); changes.append(row)
    out.mkdir(parents=True); base=Path(old2023['candidate']).resolve(strict=True)
    result=merge.save_candidate(h,original,base,out/'US-Aud_2023_approved_39_edits_sensitivity.nc',old2023['changes'],changes)
    check(len(result['changes'])==39,'expected 27 prior plus 12 new edits')
    hold_year,hold_index=physics.utc_index(HOLD,int(meta['UTC_shift_halfhours']),*meta['years']); check(hold_year==2023,'hold year')
    check(hold_index not in {x['UTC_index'] for x in result['changes']},'held 10:00 record has an edit')
    with Dataset(str(original)) as source_ds,Dataset(result['candidate']) as candidate_ds:
        for field in FIELDS:
            check(float(source_ds[field][hold_index,0,0])==float(candidate_ds[field][hold_index,0,0]),'held QC0 field changed '+field)
    context=[]
    for time in sorted(context_times):
        r=reviewed[time]; s=selected[time]; t=tower_rows[time]; z=er[time]
        for source_value,review_value in ((s['TA_USE'],r['selected_T_C']),(s['VPD_USE'],r['selected_VPD_hPa']),
                                          (t['TA_F'],r['tower_T_C']),(t['VPD_F'],r['tower_VPD_hPa'])):
            close(source_value,review_value,'humidity context mismatch '+time)
        item={'time_local':time,'selected_T_C':number(s['TA_USE']),'selected_VPD_hPa':number(s['VPD_USE']),
              'derived_selected_RH_pct':rh_from_tvpd(number(s['TA_USE']),number(s['VPD_USE'])),
              'tower_TA_QC':t['TA_F_QC'],'tower_VPD_QC':t['VPD_F_QC'],'ERA_T_C':z['TA_ERA'],'ERA_VPD_hPa':z['VPD_ERA'],
              'NOAA_T_C':r['NOAA_T_C'],'NOAA_RH_pct':r['NOAA_RH_pct'],'NOAA_VPD_hPa':r['NOAA_VPD_hPa'],
              'raw_source_fields':{k:t.get(k,'') for k in ('TA','VPD','RH','RH_F','SW_IN_F','P_F')}}
        context.append(item); print('STAGE64 HUMIDITY_CONTEXT',json.dumps(item,sort_keys=True),flush=True)
    bounds=[]
    for label,start,count in GROUPS:
        subset=sorted((x for x in changes if x['group']==label),key=lambda x:x['UTC_index']); idx=[x['UTC_index'] for x in subset]
        check(len(idx)==count and idx==list(range(idx[0],idx[0]+count)) and idx[0]>0 and idx[-1]<17519,'invalid boundary group')
        with Dataset(result['candidate']) as ds:
            a0,a1=boundary.met(ds,idx[0]-1),boundary.met(ds,idx[0]); b0,b1=boundary.met(ds,idx[-1]),boundary.met(ds,idx[-1]+1)
        dtl,dvl=a1[0]-a0[0],a1[1]-a0[1]; dtr,dvr=b1[0]-b0[0],b1[1]-b0[1]
        item={'group':label,'left_dT_C':dtl,'left_dVPD_hPa':dvl,'right_dT_C':dtr,'right_dVPD_hPa':dvr,
              'boundary_over_4':any(abs(x)>4 for x in (dtl,dvl,dtr,dvr))}
        bounds.append(item); print('STAGE64 BOUNDARY',json.dumps(item,sort_keys=True),flush=True)
    for row in changes: print('STAGE64 APPROVED',json.dumps(row,sort_keys=True),flush=True)
    final={'status':'DETACHED_NOT_USED_BY_CASES','site':'US-Aud','year':2023,'file':result,'prior_report':str(previous),
           'prior_report_sha256':stage.sha256(previous),'prior_2012_candidate':old2012['candidate'],
           'prior_2012_candidate_sha256':old2012['candidate_sha256'],'review_csv':str(review_csv),
           'review_csv_sha256':stage.sha256(review_csv),'new_changes':12,'total_changes':39,'boundaries':bounds,
           'held_2023_12_19_1000':{'time_local':HOLD,'UTC_index':hold_index,'all_four_forcing_fields_unchanged':True,'context':context},
           'note':'NOAA and interpolated values are proxies; original Stage80 replacement at April 09:30 is preserved in provenance only. Other issues remain.',
           'tower_source':tinfo,'ERA_source':einfo,'no_original_or_case_modified':True,'no_slurm_jobs':True}
    (out/'manifest.json').write_text(json.dumps(final,indent=2)+'\n',encoding='utf-8')
    print('STAGE64 COMPLETE 12 new approved candidates; 39 total edits; held 10:00 QC0 unchanged; manifest',out/'manifest.json',flush=True)
    print('SCIENCE HOLD | QC0 humidity disagreement and remaining boundary jumps need review; no automatic AD400',flush=True)


if __name__=='__main__': main()
