#!/usr/bin/env python3
"""Create user-approved detached Met candidates; no cases or jobs changed.

User decisions: retain review IDs 01 and 15-24; interpolate tower TA/VPD for
02,03,05,14; use matched NOAA USCRN half-hour temperature/humidity for 25-28.
The older June CA-Cbo and April US-Aud candidates are deliberately NOT merged.
These are provenance-labelled sensitivity values, not observed tower records.
"""
import argparse, csv, hashlib, importlib.util, json, math, shutil, urllib.request
from datetime import datetime, timedelta
from pathlib import Path
import numpy as np
from netCDF4 import Dataset

STAGE80=Path('/iridisfs/scratch/ly3n24/CLM_FATES/experiments/AmeriFlux_MultiSite_10/reports/stage80_RH_lt1_final_20261024T123353Z/10_site_selected_forcing_sources.tsv')
TOWER={
 'CA-Cbo':{'2018-07-03 08:30:00':(2,38.764,23.14,(27.421,15.957,1,1),(29.77,16.943,0,0)),
           '2018-07-03 09:30:00':(3,38.697,26.521,(29.77,16.943,0,0),(27.378,19.974,1,1))},
 'CA-Man':{'1994-04-10 14:00:00':(5,-15.367,0.,(-7.037,2.181,1,1),(1.294,4.361,0,0)),
           '2007-03-10 11:00:00':(14,-27.931,0.,(-11.996,.547,2,2),(-10.993,1.097,1,1))}}
NOAA={
 '2012-08-28 07:00:00':(25,29.4,28.661,[(21.3,64),(21.4,65),(21.6,65),(21.7,65),(21.5,66),(21.6,66)]),
 '2019-04-04 15:00:00':(26,3.967,5.099,[(23.3,12),(23.3,12),(23.1,11),(23.0,12),(23.1,12),(23.4,12)]),
 '2023-04-30 15:30:00':(27,0.,0.,[(29.3,9),(29.2,9),(28.9,9),(29.1,9),(28.8,10),(28.5,10)]),
 '2023-12-18 18:00:00':(28,0.,0.,[(15.9,17),(15.4,17),(15.0,17),(14.8,17),(14.3,18),(14.5,18)])}
FIELDS=('TBOT','QBOT','SHUM','RH')
EXTENDED={
 'CA-Cbo': [('04','2018-07-18 16:00:00',-4,4)],
 'CA-Man': [('13','2007-01-23 17:00:00',-8,8),
            ('11_12','2004-12-31 18:00:00',-4,48)]}


def module(path,name):
    spec=importlib.util.spec_from_file_location(name,path); m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m


def n(x):
    x=float(x)
    if not math.isfinite(x) or x<=-9990: raise ValueError('Missing or invalid numerical source value')
    return x


def distance(lat,lon):
    a,b=math.radians(31.5907),math.radians(lat); dlat=b-a; dlon=math.radians(lon+110.5104)
    x=math.sin(dlat/2)**2+math.cos(a)*math.cos(b)*math.sin(dlon/2)**2
    return 12742.0176*math.asin(min(1,math.sqrt(x)))


def get_noaa(year, events):
    wanted={}
    for time in events:
        t=datetime.fromisoformat(time)+timedelta(hours=7)
        for minute in (5,10,15,20,25,30):
            stamp=t+timedelta(minutes=minute); wanted[stamp.strftime('%Y%m%d%H%M')]=(time,minute)
    url=f'https://www.ncei.noaa.gov/pub/data/uscrn/products/subhourly01/{year}/CRNS0101-05-{year}-AZ_Elgin_5_S.txt'
    req=urllib.request.Request(url,headers={'User-Agent':'Research-Input-QC/1.0'})
    values={time:{} for time in events}; hasher=hashlib.sha256(); total=0
    with urllib.request.urlopen(req,timeout=90) as f:
        for line in f:
            hasher.update(line); total+=len(line)
            if total>30_000_000: raise ValueError('Unexpected NOAA source file size')
            p=line.decode('ascii').split()
            if len(p)<17 or p[0]!='53132': raise ValueError('Invalid NOAA station data row')
            key=p[1]+p[2].zfill(4)
            if key not in wanted: continue
            time,minute=wanted[key]
            if minute in values[time]: raise ValueError('Duplicate NOAA observation '+key)
            utc=datetime.strptime(key,'%Y%m%d%H%M'); lst=datetime.strptime(p[3]+p[4].zfill(4),'%Y%m%d%H%M')
            if utc-lst!=timedelta(hours=7) or distance(float(p[7]),float(p[6]))>5: raise ValueError('NOAA station clock or location differs')
            t,rh=n(p[8]),n(p[15])
            if p[16]!='0' or not (-90<t<65 and 0<rh<=100): raise ValueError('NOAA TA or RH QC invalid '+key)
            values[time][minute]={'utc_end':utc.isoformat(),'T_C':t,'RH_pct':rh,'RH_QC':p[16]}
    if total==0: raise ValueError('Empty NOAA data')
    result={}
    for time,samples in values.items():
        if set(samples)!={5,10,15,20,25,30}: raise ValueError('NOAA half-hour incomplete '+time)
        ordered=[samples[i] for i in (5,10,15,20,25,30)]
        expected=NOAA[time][3]
        if any(abs(x['T_C']-a)>.051 or abs(x['RH_pct']-b)>.51 for x,(a,b) in zip(ordered,expected)):
            raise ValueError('NOAA values differ from prior reviewed release '+time)
        result[time]=ordered
    return {'url':url,'sha256':hasher.hexdigest(),'bytes':total,'samples':result}


def from_noaa(samples,pressure):
    if not 49000<pressure<111000: raise ValueError('Pressure out of range')
    values=[]
    for x in samples:
        t=x['T_C']; es=6.112*math.exp(17.67*t/(t+243.5)); e=es*x['RH_pct']/100
        values.append(.622*e/(pressure/100-.378*e))
    temp=sum(x['T_C'] for x in samples)/len(samples); q=sum(values)/len(values)
    e=(q*pressure/100)/(.622+.378*q); es=6.112*math.exp(17.67*temp/(temp+243.5))
    rh=100*e/es; vpd=es-e
    if not (0<q<.08 and 0<rh<=100 and vpd>=0): raise ValueError('NOAA half-hour humidity invalid')
    return temp,vpd,q,rh


def verify_anchor(frame, expected):
    selected,tower=frame['selected'],frame['tower']; ta,vpd,tq,vq=expected
    for val,want in ((n(selected['TA_USE']),ta),(n(selected['VPD_USE']),vpd),
                     (n(tower['TA_F']),ta),(n(tower['VPD_F']),vpd),
                     (n(tower['TA_F_QC']),tq),(n(tower['VPD_F_QC']),vq)):
        if abs(val-want)>.002: raise ValueError('Interpolation anchor differs from operator-reviewed record')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for opt in ('run','review','context-helper','physics-helper','out'): p.add_argument('--'+opt,required=True,type=Path)
    a=p.parse_args(); root=a.run.resolve(strict=True); review=a.review.resolve(strict=True); out=a.out.expanduser().resolve()
    if out.exists() or out.is_symlink(): raise ValueError('Output directory already exists')
    h=module(a.context_helper,'context29'); phys=module(a.physics_helper,'physics32')
    rows=json.loads(review.read_text())['records']; by_id={int(x['id']):x for x in rows}
    for site,events in TOWER.items():
        for time,(id,*_) in events.items():
            if by_id.get(id,{}).get('site')!=site or by_id[id]['time_local']!=time: raise ValueError('Review ID mismatch')
    for time,(id,*_) in NOAA.items():
        if by_id.get(id,{}).get('site')!='US-Aud' or by_id[id]['time_local']!=time: raise ValueError('Review ID mismatch')
    receipt={r['site']:r for r in json.loads((root/'COMPLETE.json').read_text())['sites']}
    with STAGE80.open(encoding='utf-8-sig',newline='') as f: selection={r['site']:r for r in csv.DictReader(f,delimiter='\t')}
    out.mkdir(parents=True); noaa={}
    for year in sorted({int(t[:4]) for t in NOAA}):
        print('READING NOAA USCRN',year,flush=True)
        times=[t for t in NOAA if t.startswith(str(year))]; noaa[year]=get_noaa(year,times)
        print('NOAA SOURCE VERIFIED',year,'sha256',noaa[year]['sha256'],flush=True)
    report=[]; overall_changes=[]; extended_rows=[]
    for site in ('CA-Cbo','CA-Man','US-Aud'):
        print('READING TOWER AND ERA',site,flush=True)
        rec=receipt[site]; manifest=Path(rec['manifest']).resolve(strict=True)
        if root not in manifest.parents or h.sha(manifest)!=rec['sha256']: raise ValueError(site+': Stage23 manifest hash mismatch')
        m=json.loads(manifest.read_text()); sel=selection[site]; selected=Path(sel['selected_source'])
        if h.sha(selected)!=sel['selected_sha256']: raise ValueError(site+': Stage80 forcing checksum changed')
        raw,ri=h.sources(site,'FLUXMET_HH'); era,ei=h.sources(site,'ERA5_HH')
        if raw is None or era is None: raise ValueError(site+': missing/ambiguous FLUXMET or ERA')
        events=NOAA if site=='US-Aud' else TOWER[site]; wanted=set(events)
        if site!='US-Aud':
            for time in events:
                d=datetime.fromisoformat(time)
                wanted.update((d+timedelta(minutes=x)).strftime('%Y-%m-%d %H:%M:%S') for x in (-30,30))
        for label,center,first,last in EXTENDED.get(site,[]):
            d=datetime.fromisoformat(center)
            wanted.update((d+timedelta(minutes=30*k)).strftime('%Y-%m-%d %H:%M:%S') for k in range(first,last+1))
        s=h.read_subset(selected,'time',wanted,('TA_USE','VPD_USE','TBOT','QBOT','PSRF'))
        t=h.read_subset(raw,'TIMESTAMP_START',wanted,('TA_F','TA_F_QC','VPD_F','VPD_F_QC'),True)
        e=h.read_subset(era,'TIMESTAMP_START',wanted,('TA_ERA','VPD_ERA'),True)
        frames={time:{'selected':s.get(time,{}),'tower':t.get(time,{}),'era':e.get(time,{})} for time in wanted}
        changes=[]
        for time,info in events.items():
            f=frames[time]; sc,tc=f['selected'],f['tower']; id,old_t,old_v=info[:3]
            if n(tc['TA_F_QC'])!=0 or abs(n(tc['TA_F'])-old_t)>.002 or abs(n(sc['TA_USE'])-old_t)>.002 or abs(n(sc['VPD_USE'])-old_v)>.002:
                raise ValueError(site+': reviewed source differs '+time)
            pressure=n(sc['PSRF'])
            if site!='US-Aud':
                left=(datetime.fromisoformat(time)-timedelta(minutes=30)).strftime('%Y-%m-%d %H:%M:%S')
                right=(datetime.fromisoformat(time)+timedelta(minutes=30)).strftime('%Y-%m-%d %H:%M:%S')
                l,r=info[3:]; verify_anchor(frames[left],l); verify_anchor(frames[right],r)
                nt=(l[0]+r[0])/2; nv=(l[1]+r[1])/2; q,rh=phys.q_from_tvpd(nt,nv,pressure)
                method={'type':'USER_APPROVED_LINEAR_TOWER_AND_VPD','left':left,'right':right,
                        'left_TA_VPD_QC':list(l[2:]),'right_TA_VPD_QC':list(r[2:])}
            else:
                if abs(float(m['UTC_offset_hours'])+7)>1e-9: raise ValueError('US-Aud UTC offset changed')
                source=noaa[int(time[:4])]; samples=source['samples'][time]
                nt,nv,q,rh=from_noaa(samples,pressure)
                method={'type':'USER_APPROVED_NOAA_USCRN_TEMP_AND_RH','station':'53132 AZ Elgin 5 S',
                        'url':source['url'],'annual_sha256':source['sha256'],'five_minute_samples':samples,
                        'humidity':'mean of six specific humidities using original half-hour pressure'}
            year,index=phys.utc_index(time,int(m['UTC_shift_halfhours']),*m['years'])
            changes.append({'id':id,'site':site,'time_local':time,'UTC_year':year,'UTC_index':index,
                            'original_TA_C':old_t,'original_VPD_hPa':old_v,'pressure_Pa':pressure,
                            'candidate_TA_C':nt,'candidate_VPD_hPa':nv,'candidate_QBOT':q,'candidate_RH_pct':rh,'method':method})
        files={int(x['year']):x for x in m['annual_files']}; created=[]
        for year in sorted({x['UTC_year'] for x in changes}):
            group=[x for x in changes if x['UTC_year']==year]; entry=files[year]; original=Path(entry['path']).resolve(strict=True)
            if root not in original.parents or h.sha(original)!=entry['sha256']: raise ValueError(site+': annual file checksum mismatch')
            with Dataset(str(original)) as ds:
                for x in group:
                    i=x['UTC_index']; old_q,_=phys.q_from_tvpd(x['original_TA_C'],x['original_VPD_hPa'],x['pressure_Pa'])
                    if abs(float(ds['TBOT'][i,0,0])-(x['original_TA_C']+273.15))>1e-6 or abs(float(ds['QBOT'][i,0,0])-old_q)>1e-8 or abs(float(ds['PSRF'][i,0,0])-x['pressure_Pa'])>.001:
                        raise ValueError(site+': Stage23 source mismatch '+x['time_local'])
            dest=out/f'{site}_{year}_USER_APPROVED_SENSITIVITY.nc'; shutil.copyfile(original,dest)
            with Dataset(str(dest),'r+') as ds:
                for x in group:
                    i=x['UTC_index']; ds['TBOT'][i,0,0]=x['candidate_TA_C']+273.15
                    ds['QBOT'][i,0,0]=x['candidate_QBOT']; ds['SHUM'][i,0,0]=x['candidate_QBOT']; ds['RH'][i,0,0]=x['candidate_RH_pct']
                ds.temperature_sensitivity='Operator-approved tower interpolation or NOAA proxy; detached, not applied to cases'
            with Dataset(str(original)) as src,Dataset(str(dest)) as dst:
                indices={x['UTC_index'] for x in group}
                for var in src.variables:
                    first=np.ma.asarray(src[var][:]); second=np.ma.asarray(dst[var][:])
                    if var in FIELDS:
                        mask=np.ones(first.shape[0],dtype=bool); mask[list(indices)]=False
                        if not np.ma.allequal(first[mask],second[mask]): raise ValueError('unexpected changed time '+var)
                    elif not np.ma.allequal(first,second): raise ValueError('unexpected changed variable '+var)
                for x in group:
                    for var,want in (('TBOT',x['candidate_TA_C']+273.15),('QBOT',x['candidate_QBOT']),('SHUM',x['candidate_QBOT']),('RH',x['candidate_RH_pct'])):
                        if abs(float(dst[var][x['UTC_index'],0,0])-want)>1e-5: raise ValueError('candidate readback mismatch '+var)
            created.append({'year':year,'source':str(original),'source_sha256':entry['sha256'],'candidate':str(dest),
                            'candidate_sha256':h.sha(dest),'changes':group})
        for label,center,first,last in EXTENDED.get(site,[]):
            base=datetime.fromisoformat(center)
            print('EXTENDED REVIEW',site,label,'LOCAL START; TOWER / QC / ERA / VPD / VPD_QC / ERA_VPD',flush=True)
            for k in range(first,last+1):
                time=(base+timedelta(minutes=30*k)).strftime('%Y-%m-%d %H:%M:%S'); f=frames[time]; tt=f['tower']; ee=f['era']; ss=f['selected']
                row={'site':site,'review_id':label,'time_local':time,'tower_TA_C':tt.get('TA_F',''),
                     'tower_TA_QC':tt.get('TA_F_QC',''),'era_TA_C':ee.get('TA_ERA',''),
                     'tower_VPD_hPa':tt.get('VPD_F',''),'tower_VPD_QC':tt.get('VPD_F_QC',''),
                     'era_VPD_hPa':ee.get('VPD_ERA',''),'selected_TA_C':ss.get('TA_USE',''),'selected_VPD_hPa':ss.get('VPD_USE','')}
                extended_rows.append(row)
                print('EXTENDED'+label,site,time,row['tower_TA_C'],row['tower_TA_QC'],row['era_TA_C'],row['tower_VPD_hPa'],row['tower_VPD_QC'],row['era_VPD_hPa'],flush=True)
        for x in changes: print('USER APPROVED CANDIDATE',json.dumps(x,sort_keys=True),flush=True)
        overall_changes.extend(changes)
        report.append({'site':site,'source_manifest':str(manifest),'source_manifest_sha256':rec['sha256'],
                       'stage80_sha256':sel['selected_sha256'],'FLUXMET_source':ri,'ERA_source':ei,'files':created})
    final={'status':'DETACHED_NOT_USED_BY_CASES','review_file':str(review),'review_sha256':h.sha(review),
           'user_decisions':{'retain_ids':[1]+list(range(15,25)),'tower_interpolation_ids':[2,3,5,14],'NOAA_T_RH_ids':[25,26,27,28],
                             'id13':'inspect extended window first'},
           'sites':report,'older_june_CA_Cbo_and_april_US_Aud_candidates_merged':False,
           'caveat':'NOAA and interpolated anchor values are provisional proxies. Other held events and adjacent filled periods are not repaired.',
           'no_original_files_or_cases_modified':True,'no_slurm_jobs':True}
    with (out/'extended_context.csv').open('w',encoding='utf-8',newline='') as f:
        fields=('site','review_id','time_local','tower_TA_C','tower_TA_QC','era_TA_C','tower_VPD_hPa','tower_VPD_QC','era_VPD_hPa','selected_TA_C','selected_VPD_hPa')
        w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(extended_rows)
    (out/'manifest.json').write_text(json.dumps(final,indent=2)+'\n')
    print('COMPLETE',out/'manifest.json','records',len(overall_changes),'NO CASES OR SLURM MODIFIED',flush=True)


if __name__=='__main__': main()
