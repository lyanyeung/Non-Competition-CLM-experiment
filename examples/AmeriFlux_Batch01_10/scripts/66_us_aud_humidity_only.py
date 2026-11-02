#!/usr/bin/env python3
"""Make the user-approved 2023-12-19 10:00 humidity-only candidate.

This is a detached sensitivity file. It never alters the source or a case.
"""
import argparse, csv, hashlib, json, math
from pathlib import Path
from netCDF4 import Dataset

TIME='2023-12-19 10:00:00'
NOAA_SHA='137dd43c1dc621e6e04ee67c4a437eea41b9dee811a7c7b8924623b4754aa514'

def require(ok, message):
    if not ok: raise ValueError(message)

def vapor_from_q(q, pressure):
    return q*(pressure/100)/(.622+.378*q)

def humidity_at_tower_t(temp, pressure, noaa_q):
    es=6.112*math.exp(17.67*temp/(temp+243.5))
    e=vapor_from_q(noaa_q,pressure)
    rh=100*e/es; vpd=es-e
    require(0 < rh <= 100 and vpd >= 0, 'invalid retained-temperature humidity')
    return vpd,rh

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--self-test',action='store_true')
    for name in ('stage64','stage59','stage58','context','noaa','humidity','merge','physics','boundary'):
        p.add_argument('--'+name,required=True,type=Path)
    p.add_argument('--previous',required=True,type=Path)
    p.add_argument('--review',required=True,type=Path)
    p.add_argument('--out',type=Path)
    a=p.parse_args()
    raw=a.stage64.read_bytes()
    require(hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()=='239bae595ef3e45853295125c41e57a6e49fd95c','stage64 checksum mismatch')
    import importlib.util
    spec=importlib.util.spec_from_file_location('stage64',a.stage64); s=importlib.util.module_from_spec(spec); spec.loader.exec_module(s)
    mods={k:s.load(getattr(a,k),k) for k in s.PINS}
    stage,h,noaa,humidity,merge,physics,boundary=(mods[x] for x in ('stage59','context','noaa','humidity','merge','physics','boundary'))
    if a.self_test:
        q=.0025; v,r=humidity_at_tower_t(17.49,85424,q)
        require(0<r<100 and v>0 and abs(vapor_from_q(q,85424)-q*(85424/100)/(.622+.378*q))<1e-12,'humidity arithmetic')
        print('STAGE66 SELF-TEST PASS | NOAA specific humidity, tower temperature retained; NO WRITES',flush=True); return
    require(a.out is not None,'output directory required')
    out=a.out.expanduser().resolve(); require(not out.exists() and not out.is_symlink(),'output already exists')
    prior=a.previous.resolve(strict=True); old=json.loads(prior.read_text())
    require(old.get('status')=='DETACHED_NOT_USED_BY_CASES' and old.get('no_original_or_case_modified') is True and old.get('no_slurm_jobs') is True,'invalid Stage64 manifest')
    f=old['file']; require(old['total_changes']==39 and len(f['changes'])==39,'unexpected prior edit count')
    original=Path(f['original']).resolve(strict=True); base=Path(f['candidate']).resolve(strict=True)
    require(h.sha(original)==f['original_sha256'] and h.sha(base)==f['candidate_sha256'],'candidate or original checksum mismatch')
    require(h.sha(old['prior_2012_candidate'])==old['prior_2012_candidate_sha256'],'2012 candidate checksum mismatch')
    require(old['held_2023_12_19_1000']['all_four_forcing_fields_unchanged'] is True,'prior record not held')
    review=a.review.resolve(strict=True); require(h.sha(review)==old['review_csv_sha256'],'review checksum mismatch')
    with review.open(encoding='utf-8-sig',newline='') as src:
        matches=[x for x in csv.DictReader(src) if x['time_local']==TIME]
    require(len(matches)==1,'review timestamp missing or duplicated'); r=matches[0]
    rec,meta,sel,source,tower,era,tinfo,einfo=merge.get_inputs(h,stage.ROOT,'US-Aud')
    entry,verified_original=merge.src_nc(h,stage.ROOT,meta,2023)
    require(original==verified_original and h.sha(original)==entry['sha256'],'Stage23 lineage mismatch')
    wanted={TIME}; selected=h.read_subset(source,'time',wanted,('TA_USE','VPD_USE','QBOT','PSRF'))[TIME]
    rawtower=h.read_subset(tower,'TIMESTAMP_START',wanted,('TA_F','TA_F_QC','VPD_F','VPD_F_QC','RH'),True)[TIME]
    for actual,expected in ((selected['TA_USE'],17.49),(selected['VPD_USE'],8.28),(rawtower['TA_F'],17.49),
                            (rawtower['VPD_F'],8.28),(rawtower['TA_F_QC'],0),(rawtower['VPD_F_QC'],0),
                            (r['NOAA_T_C'],17.95),(r['NOAA_RH_pct'],15.6666666667)):
        s.close(actual,expected,'reviewed 10:00 source mismatch')
    noaa.EVENTS={TIME:(17.49,8.28,float(r['NOAA_T_C']),float(r['NOAA_RH_pct']))}; noaa.SHA={2023:NOAA_SHA}
    data=noaa.noaa(2023); samples=data['samples'][TIME]; pressure=s.number(selected['PSRF'])
    noaa_temp,_,q,_=humidity.from_noaa(samples,pressure)
    tower_temp=s.number(selected['TA_USE']); vpd,rh=humidity_at_tower_t(tower_temp,pressure,q)
    year,index=physics.utc_index(TIME,int(meta['UTC_shift_halfhours']),*meta['years'])
    require(year==2023 and index==old['held_2023_12_19_1000']['UTC_index'],'UTC index mismatch')
    require(index not in {int(x['UTC_index']) for x in f['changes']},'10:00 already modified')
    row={'site':'US-Aud','time_local':TIME,'UTC_year':year,'UTC_index':index,
         'original_TA_C':tower_temp,'original_VPD_hPa':s.number(selected['VPD_USE']),
         'original_TA_QC':0,'original_VPD_QC':0,'pressure_Pa':pressure,
         'candidate_TA_C':tower_temp,'candidate_QBOT':q,'candidate_RH_pct':rh,'candidate_VPD_hPa':vpd,
         'method':{'type':'USER_APPROVED_NOAA_SPECIFIC_HUMIDITY_ONLY_TOWER_T_RETAINED',
                   'station':'53132 AZ Elgin 5 S','url':data['url'],'annual_sha256':data['sha256'],
                   'five_minute_samples':samples,'NOAA_mean_T_C':noaa_temp,
                   'humidity':'mean of six NOAA specific humidities at original pressure; RH and VPD recomputed at retained tower temperature'}}
    merge.validate_origin(original,row,selected)
    out.mkdir(parents=True)
    result=merge.save_candidate(h,original,base,out/'US-Aud_2023_approved_40_edits_sensitivity.nc',f['changes'],[row])
    require(len(result['changes'])==40,'unexpected total changes')
    with Dataset(str(original)) as src,Dataset(result['candidate']) as dst:
        require(float(src['TBOT'][index,0,0])==float(dst['TBOT'][index,0,0]),'tower temperature changed')
        adjacent=[boundary.met(dst,i) for i in (index-1,index,index+1)]
    b={'left_dT_C':adjacent[1][0]-adjacent[0][0],'left_dVPD_hPa':adjacent[1][1]-adjacent[0][1],
       'right_dT_C':adjacent[2][0]-adjacent[1][0],'right_dVPD_hPa':adjacent[2][1]-adjacent[1][1]}
    b['boundary_over_4']=any(abs(x)>4 for x in b.values())
    final={'status':'DETACHED_NOT_USED_BY_CASES','site':'US-Aud','year':2023,'file':result,
           'prior_manifest':str(prior),'prior_manifest_sha256':h.sha(prior),
           'prior_2012_candidate':old['prior_2012_candidate'],'prior_2012_candidate_sha256':old['prior_2012_candidate_sha256'],
           'tower_temperature_exactly_unchanged':True,'boundary':b,'new_changes':1,'total_changes':40,
           'no_original_or_case_modified':True,'no_slurm_jobs':True,
           'note':'NOAA is a nearby-station proxy; site-wide forcing and residual flags still require verification.'}
    (out/'manifest.json').write_text(json.dumps(final,indent=2)+'\n',encoding='utf-8')
    print('STAGE66 APPROVED',json.dumps(row,sort_keys=True),flush=True)
    print('STAGE66 BOUNDARY',json.dumps(b,sort_keys=True),flush=True)
    print('STAGE66 COMPLETE 1 humidity-only edit; 40 total; TBOT unchanged; manifest',out/'manifest.json',flush=True)
    print('SCIENCE HOLD | site-wide QC and other remaining flags require review; NO AD400 submitted',flush=True)

if __name__=='__main__': main()
