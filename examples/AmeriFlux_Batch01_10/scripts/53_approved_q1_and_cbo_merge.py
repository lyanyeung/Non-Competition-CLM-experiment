#!/usr/bin/env python3
"""Build user-approved US-Aud Q1 NOAA candidates and merge CA-Cbo June.

Works only on detached, verified candidates; never alters original inputs or
model cases. Re-fetches NOAA five-minute TA/RH and verifies pinned yearly SHA.
Previously approved edits are included; other unresolved Q1s are not changed.
"""
import argparse, hashlib, importlib.util, json, math, urllib.request
from datetime import datetime, timedelta
from pathlib import Path
from netCDF4 import Dataset

EVENTS={
 '2019-04-04 14:30:00':(10.042,8.409,23.43,11.67),
 '2019-04-04 15:30:00':(15.522,16.748,22.92,12.17),
 '2023-04-30 16:00:00':(17.819,15.899,28.62,10.00),
 '2023-04-30 16:30:00':(21.023,19.896,29.05,9.50),
 '2023-12-18 18:30:00':(6.256,5.510,14.22,18.00),
 '2023-12-18 19:00:00':(6.242,5.494,10.78,22.50)}
SHA={2019:'f73cf0841a719063516858673e0df684a7ef97b9ea4d122b55a84f062f777281',
     2023:'137dd43c1dc621e6e04ee67c4a437eea41b9dee811a7c7b8924623b4754aa514'}


def load(path,name):
    spec=importlib.util.spec_from_file_location(name,path); m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m


def noaa(year):
    wanted={}; found={}
    for time in EVENTS:
        if int(time[:4])!=year: continue
        found[time]={}; start=datetime.fromisoformat(time)+timedelta(hours=7)
        for minute in (5,10,15,20,25,30): wanted[(start+timedelta(minutes=minute)).strftime('%Y%m%d%H%M')]=(time,minute)
    url=f'https://www.ncei.noaa.gov/pub/data/uscrn/products/subhourly01/{year}/CRNS0101-05-{year}-AZ_Elgin_5_S.txt'
    req=urllib.request.Request(url,headers={'User-Agent':'Research-Input-QC/1.0'}); digest=hashlib.sha256(); count=0
    with urllib.request.urlopen(req,timeout=90) as f:
        for raw in f:
            digest.update(raw); count+=len(raw)
            if count>30_000_000: raise ValueError('Unexpected NOAA file size')
            p=raw.decode('ascii').split()
            if len(p)<17 or p[0]!='53132': raise ValueError('Unexpected NOAA station/format')
            key=p[1]+p[2].zfill(4)
            if key not in wanted: continue
            time,minute=wanted[key]; utc=datetime.strptime(key,'%Y%m%d%H%M'); lst=datetime.strptime(p[3]+p[4].zfill(4),'%Y%m%d%H%M')
            if utc-lst!=timedelta(hours=7) or abs(float(p[7])-31.5907)>.05 or abs(float(p[6])+110.5104)>.05: raise ValueError('NOAA time/location mismatch')
            t,rh=float(p[8]),float(p[15])
            if p[16]!='0' or not (math.isfinite(t) and -90<t<65 and 0<rh<=100) or minute in found[time]: raise ValueError('NOAA invalid QC or duplicate')
            found[time][minute]={'utc_end':utc.isoformat(),'T_C':t,'RH_pct':rh,'RH_QC':p[16]}
    if digest.hexdigest()!=SHA[year]: raise ValueError('NOAA annual source differs from reviewed SHA')
    output={}
    for time,items in found.items():
        if set(items)!={5,10,15,20,25,30}: raise ValueError('NOAA missing half-hour samples '+time)
        samples=[items[k] for k in sorted(items)]; expected=EVENTS[time]
        if abs(sum(x['T_C'] for x in samples)/6-expected[2])>.015 or abs(sum(x['RH_pct'] for x in samples)/6-expected[3])>.015:
            raise ValueError('NOAA samples differ from user-reviewed values '+time)
        output[time]=samples
    return {'url':url,'sha256':digest.hexdigest(),'samples':output}


def close(a,b,what,tol=.002):
    a,b=float(a),float(b)
    if not math.isfinite(a) or not math.isfinite(b) or abs(a-b)>tol: raise ValueError('Mismatch '+what)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for x in ('run','approved','initial','joint','context-helper','physics-helper','prior-helper','merge-helper','out'): p.add_argument('--'+x,required=True,type=Path)
    a=p.parse_args(); root=a.run.resolve(strict=True); out=a.out.expanduser().resolve()
    if out.exists() or out.is_symlink(): raise ValueError('Output directory already exists')
    h=load(a.context_helper,'context29'); phys=load(a.physics_helper,'physics32')
    prior=load(a.prior_helper,'approved43'); merge=load(a.merge_helper,'merge50')
    old=json.loads(a.approved.read_text()); initial=json.loads(a.initial.read_text()); joint=json.loads(a.joint.read_text())
    if old.get('status')!='DETACHED_NOT_USED_BY_CASES' or joint.get('status')!='DETACHED_NOT_USED_BY_CASES': raise ValueError('Prior candidate report invalid')
    out.mkdir(parents=True); results=[]
    print('VERIFYING USER-APPROVED CA-CBO JUNE CANDIDATE',flush=True)
    base_row=next(x for x in joint['files'] if x['site']=='CA-Cbo' and x['year']==2018)
    intro=next(x for x in initial['results'] if x['site']=='CA-Cbo')
    first=next(x for x in intro['candidates'] if x['year']==2018)
    original=Path(base_row['original']).resolve(strict=True); base=Path(base_row['candidate']).resolve(strict=True); early=Path(first['candidate']).resolve(strict=True)
    if root not in original.parents or h.sha(original)!=base_row['original_sha256'] or h.sha(base)!=base_row['candidate_sha256']:
        raise ValueError('CA-Cbo base/source checksum mismatch')
    if Path(first['original']).resolve(strict=True)!=original or first['original_sha256']!=base_row['original_sha256'] or h.sha(early)!=first['candidate_sha256']:
        raise ValueError('CA-Cbo June candidate source/checksum mismatch')
    if len(first['changes'])!=1: raise ValueError('Expected a single June candidate')
    jun=dict(first['changes'][0]); jun['id']='2018-06-28'; jun['method']='USER_APPROVED_PREVIOUS_INTERPOLATION'
    if jun['time_local']!='2018-06-28 08:00:00' or int(jun['UTC_index'])!=8570: raise ValueError('Unexpected June candidate timestamp')
    for key,expected in (('original_TA_C',35.227),('candidate_TA_C',20.5535),('candidate_VPD_hPa',4.8815)):
        close(jun[key],expected,'CA-Cbo '+key)
    q,rh=phys.q_from_tvpd(jun['candidate_TA_C'],jun['candidate_VPD_hPa'],jun['pressure_Pa'])
    close(jun['candidate_QBOT'],q,'CA-Cbo June humidity',1e-8); close(jun['candidate_RH_pct'],rh,'CA-Cbo June RH',1e-5)
    with Dataset(str(early)) as ds:
        i=jun['UTC_index']
        for field,want in (('TBOT',jun['candidate_TA_C']+273.15),('QBOT',q),('SHUM',q),('RH',rh)):
            close(ds[field][i,0,0],want,'CA-Cbo June candidate '+field,1e-5)
    cbo=merge.save_candidate(h,original,base,out/'CA-Cbo_2018_JUNE_AND_IDS02_03_04_sensitivity.nc',base_row['changes'],[jun])
    cbo.update(site='CA-Cbo',year=2018,initial_candidate=str(early),initial_candidate_sha256=first['candidate_sha256'])
    results.append(cbo); print('CA-CBO MERGED',len(cbo['changes']),'records',cbo['candidate'],flush=True)

    print('READING NOAA SOURCE 2019 AND 2023',flush=True)
    records={year:noaa(year) for year in (2019,2023)}
    site='US-Aud'; rec,m,sel,source,tower,era,tinfo,einfo=merge.get_inputs(h,root,site)
    if abs(float(m['UTC_offset_hours'])+7)>1e-9: raise ValueError('US-Aud offset changed')
    wanted=set(EVENTS); s=h.read_subset(source,'time',wanted,('TA_USE','VPD_USE','QBOT','PSRF'))
    t=h.read_subset(tower,'TIMESTAMP_START',wanted,('TA_F','TA_F_QC','VPD_F','VPD_F_QC'),True)
    if set(s)!=wanted or set(t)!=wanted: raise ValueError('Reviewed Q1 timestamps missing')
    changes=[]
    for time,(orig_t,orig_v,_,_) in EVENTS.items():
        for value,want in ((s[time]['TA_USE'],orig_t),(s[time]['VPD_USE'],orig_v),
                           (t[time]['TA_F'],orig_t),(t[time]['VPD_F'],orig_v),
                           (t[time]['TA_F_QC'],1),(t[time]['VPD_F_QC'],1)):
            close(value,want,'US-Aud source '+time)
        pressure=float(s[time]['PSRF']); noaa_data=records[int(time[:4])]; samples=noaa_data['samples'][time]
        temp,vpd,q,rh=prior.from_noaa(samples,pressure)
        year,index=phys.utc_index(time,int(m['UTC_shift_halfhours']),*m['years'])
        changes.append({'id':'USER_APPROVED_ADJACENT_Q1','site':site,'time_local':time,'UTC_year':year,'UTC_index':index,
            'original_TA_C':orig_t,'original_VPD_hPa':orig_v,'original_TA_QC':1,'original_VPD_QC':1,'pressure_Pa':pressure,
            'candidate_TA_C':temp,'candidate_VPD_hPa':vpd,'candidate_QBOT':q,'candidate_RH_pct':rh,
            'method':{'type':'USER_APPROVED_NOAA_USCRN_TEMP_AND_RH','station':'53132 AZ Elgin 5 S','url':noaa_data['url'],
                      'annual_sha256':noaa_data['sha256'],'five_minute_samples':samples,
                      'humidity':'mean of six specific humidities using original half-hour pressure'}})
    for year,ids in ((2019,{26}),(2023,{27,28})):
        group=[x for x in changes if x['UTC_year']==year]; entry,original=merge.src_nc(h,root,m,year)
        base,old_changes=merge.checked_previous(h,old,site,year,original,entry,ids)
        with Dataset(str(original)) as ds:
            for x in group:
                i=x['UTC_index']; selected=s[x['time_local']]
                for field,want,tol in (('TBOT',x['original_TA_C']+273.15,1e-6),('QBOT',float(selected['QBOT']),1e-8),('PSRF',x['pressure_Pa'],.001)):
                    close(ds[field][i,0,0],want,'US-Aud original '+field,tol)
        result=merge.save_candidate(h,original,base,out/f'US-Aud_{year}_CENTER_AND_Q1_NOAA_sensitivity.nc',old_changes,group)
        result.update(site=site,year=year,stage23_manifest_sha256=rec['sha256'],stage80_sha256=sel['selected_sha256'],FLUXMET_source=tinfo,ERA_source=einfo)
        results.append(result)
        for x in group: print('USER APPROVED Q1 NOAA',json.dumps(x,sort_keys=True),flush=True)
        print('US-AUD MERGED',year,len(result['changes']),'records',result['candidate'],flush=True)
    final={'status':'DETACHED_NOT_USED_BY_CASES','files':results,'prior_report':str(a.approved.resolve()),
           'prior_report_sha256':h.sha(a.approved),'CA_Cbo_first_report':str(a.initial.resolve()),'CA_Cbo_first_report_sha256':h.sha(a.initial),
           'CA_Cbo_joint_report':str(a.joint.resolve()),'CA_Cbo_joint_report_sha256':h.sha(a.joint),
           'method':'User-approved NOAA nearby-station TA/RH for six Q1 records and previously generated June CA-Cbo interpolation',
           'other_candidates_not_merged':True,'note':'Other suspected Q1/Q0 records require separate review; no original input or case changed.',
           'no_slurm_jobs':True}
    (out/'manifest.json').write_text(json.dumps(final,indent=2)+'\n')
    print('COMPLETE',out/'manifest.json','NO ORIGINAL INPUT OR CASE MODIFIED; NO JOBS',flush=True)


if __name__=='__main__': main()
