#!/usr/bin/env python3
"""Create independently supported, detached temperature sensitivity inputs.

The NOAA comparisons below are screening evidence, not replacement values.
Only isolated half-hour points with adjacent acceptable paired TA/VPD anchors
are interpolated. Failed checks remain held. This creates NO model cases/jobs
and NEVER overwrites Stage23 or the source tower data. US-Bar's already audited
three-point candidate is checked and reported, not regenerated here.
"""
import argparse, csv, importlib.util, json, math, shutil
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
from netCDF4 import Dataset

# Station observations independently checked in the previous review. Values
# are approximate at/near the target half-hour; metadata and time assumptions
# are in the resulting manifest. No station value is inserted into forcing.
EVIDENCE={
 'CA-Cbo': {'2018-06-28 08:00:00':(19.5,35.227,18.147),
            '2018-07-03 08:30:00':(27.0,38.764,21.805),
            '2018-07-03 09:30:00':(28.9,38.697,24.464),
            '2018-07-18 16:00:00':(23.0,34.069,22.024)},
 'CA-Man': {'1994-04-10 14:00:00':(-1.0,-15.367,-2.975),
            '2004-06-20 15:00:00':(11.0,21.680,6.890),
            '2004-06-20 16:00:00':(12.0,22.305,6.943),
            '2007-01-23 17:00:00':(-24.0,-10.282,-23.126),
            '2007-03-10 11:00:00':(-14.0,-27.931,-11.603)},
 'US-Aud': {'2019-04-04 15:00:00':(23.2,3.967,21.817),
            '2023-04-11 07:00:00':(14.9333333333,29.320,12.610),
            '2023-04-30 15:30:00':(28.9666666667,0.,29.524),
            '2023-12-18 18:00:00':(14.9833333333,0.,15.473)}}
INFO={
 'CA-Cbo':{'station':'NOAA ISD BORDEN 71534099999, approximately 7.7 km',
           'url':'https://noaa-global-hourly-pds.s3.amazonaws.com/2018/71534099999.csv'},
 'CA-Man':{'station':'NOAA ISD THOMPSON 71079099999, approximately 39.5 km',
           'url':'https://noaa-global-hourly-pds.s3.amazonaws.com/{year}/71079099999.csv'},
 'US-Aud':{'station':'NOAA USCRN AZ Elgin 5 S WBAN 53132, co-located approximately',
           'url':'https://www.ncei.noaa.gov/pub/data/uscrn/products/subhourly01/{year}/CRNS0101-05-{year}-AZ_Elgin_5_S.txt'}}
SITES=tuple(EVIDENCE)
STAGE80=Path('/iridisfs/scratch/ly3n24/CLM_FATES/experiments/AmeriFlux_MultiSite_10/reports/stage80_RH_lt1_final_20261024T123353Z/10_site_selected_forcing_sources.tsv')


def load(path,name):
    spec=importlib.util.spec_from_file_location(name,path); mod=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod); return mod


def number(x):
    try:
        x=float(x)
        if not math.isfinite(x) or x<=-9990: return None
        return x
    except (ValueError,TypeError): return None


def anchor(frame):
    s,t,e=frame['s'],frame['t'],frame['e']
    ta,v,st,sv,era=(number(t.get('TA_F')),number(t.get('VPD_F')),number(s.get('TA_USE')),
                     number(s.get('VPD_USE')),number(e.get('TA_ERA')))
    qta,qv=number(t.get('TA_F_QC')),number(t.get('VPD_F_QC'))
    if any(vv is None for vv in (ta,v,st,sv,era)) or qta not in (0.,1.) or qv not in (0.,1.): return None
    if abs(ta-st)>.001 or abs(v-sv)>.001 or abs(ta-era)>5: return None
    return ta,v,int(qta),int(qv)


def one(site,time,frames,physics):
    ref,expected,era_expected=EVIDENCE[site][time]; center=frames.get(time,{'s':{},'t':{},'e':{}})
    s,t,e=center['s'],center['t'],center['e']
    tower,chosen,vpd,era=(number(t.get('TA_F')),number(s.get('TA_USE')),number(s.get('VPD_USE')),number(e.get('TA_ERA')))
    if any(x is None for x in (tower,chosen,vpd,era)) or number(t.get('TA_F_QC'))!=0: raise ValueError('missing or non-QC0 tower temperature')
    if abs(tower-expected)>.002 or abs(era-era_expected)>.002 or abs(tower-chosen)>.001: raise ValueError('source temperature does not match reviewed event')
    if abs(tower-ref)<=10 or abs(era-ref)>6: raise ValueError('independent station and ERA do not jointly support this anomaly')
    dt=datetime.fromisoformat(time); left=(dt-timedelta(minutes=30)).strftime('%Y-%m-%d %H:%M:%S'); right=(dt+timedelta(minutes=30)).strftime('%Y-%m-%d %H:%M:%S')
    l=anchor(frames.get(left,{'s':{},'t':{},'e':{}})); r=anchor(frames.get(right,{'s':{},'t':{},'e':{}}))
    if not l or not r: raise ValueError('no acceptable paired TA/VPD anchors immediately on both sides')
    if abs(l[0]-r[0])>8: raise ValueError('anchor temperatures differ by more than 8 C')
    newt=(l[0]+r[0])/2; newv=(l[1]+r[1])/2
    if abs(newt-ref)>6 or abs(newt-tower)<=8: raise ValueError('interpolation not supported by independent station')
    pressure=number(s.get('PSRF'))
    q,rh=physics.q_from_tvpd(newt,newv,pressure)
    return {'site':site,'time_local':time,'original_TA_C':tower,'original_VPD_hPa':vpd,'pressure_Pa':pressure,
            'candidate_TA_C':newt,'candidate_VPD_hPa':newv,'candidate_QBOT':q,'candidate_RH_pct':rh,
            'noaa_screen_C':ref,'ERA_TA_C':era,'left_anchor':left,'right_anchor':right,
            'left_TA_VPD_QC':list(l[2:]),'right_TA_VPD_QC':list(r[2:]),'status':'DETACHED_SENSITIVITY'}


def main():
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('--run',required=True,type=Path)
    p.add_argument('--context-helper',required=True,type=Path); p.add_argument('--physics-helper',required=True,type=Path)
    p.add_argument('--usbar-manifest',required=True,type=Path); p.add_argument('--out',required=True,type=Path)
    a=p.parse_args(); root=a.run.resolve(strict=True); out=a.out.expanduser().resolve()
    if out.exists() or out.is_symlink(): raise ValueError('Output path already exists')
    h=load(a.context_helper,'context29'); physics=load(a.physics_helper,'candidate32')
    complete=json.loads((root/'COMPLETE.json').read_text()); receipts={r['site']:r for r in complete['sites']}
    with STAGE80.open(encoding='utf-8-sig',newline='') as f: selections={r['site']:r for r in csv.DictReader(f,delimiter='\t')}
    out.mkdir(parents=True); results=[]; allchanges=[]
    for site in SITES:
        try:
            print('SCANNING',site,'selected, tower and ERA source records',flush=True)
            rec=receipts[site]; mp=Path(rec['manifest']).resolve(strict=True)
            if root not in mp.parents or h.sha(mp)!=rec['sha256']: raise ValueError('Stage23 manifest hash mismatch')
            m=json.loads(mp.read_text()); sel=selections[site]; src=Path(sel['selected_source'])
            if h.sha(src)!=sel['selected_sha256']: raise ValueError('Stage80 source hash mismatch')
            raw,ri=h.sources(site,'FLUXMET_HH'); era,ei=h.sources(site,'ERA5_HH')
            if raw is None or era is None: raise ValueError('Missing or ambiguous FLUXMET/ERA sources')
            wanted=set()
            for time in EVIDENCE[site]:
                d=datetime.fromisoformat(time)
                wanted.update((d+timedelta(minutes=i)).strftime('%Y-%m-%d %H:%M:%S') for i in (-30,0,30))
            selected=h.read_subset(src,'time',wanted,('TA_USE','VPD_USE','TBOT','QBOT','PSRF'))
            tower=h.read_subset(raw,'TIMESTAMP_START',wanted,('TA_F','TA_F_QC','VPD_F','VPD_F_QC'),True)
            rean=h.read_subset(era,'TIMESTAMP_START',wanted,('TA_ERA','VPD_ERA'),True)
            frames={t:{'s':selected.get(t,{}),'t':tower.get(t,{}),'e':rean.get(t,{})} for t in wanted}
            candidates=[]; held=[]
            for time in EVIDENCE[site]:
                try: candidates.append(one(site,time,frames,physics))
                except (ValueError,TypeError,OverflowError) as exc: held.append({'time_local':time,'reason':str(exc)})
            # An anchor must not itself be a targeted anomalous record.
            targets=set(EVIDENCE[site]); safe=[]
            for change in candidates:
                if change['left_anchor'] in targets or change['right_anchor'] in targets:
                    held.append({'time_local':change['time_local'],'reason':'adjacent record is also a target'})
                else: safe.append(change)
            files={int(x['year']):x for x in m['annual_files']}; grouped={}
            for x in safe:
                year,index=physics.utc_index(x['time_local'],int(m['UTC_shift_halfhours']),*m['years'])
                x.update(UTC_year=year,UTC_index=index); grouped.setdefault(year,[]).append(x)
            built=[]
            for year,changes in sorted(grouped.items()):
                entry=files[year]; original=Path(entry['path']).resolve(strict=True)
                if root not in original.parents or h.sha(original)!=entry['sha256']: raise ValueError('annual forcing hash mismatch')
                with Dataset(str(original)) as ds:
                    for x in changes:
                        i=x['UTC_index']; q,_=physics.q_from_tvpd(x['original_TA_C'],x['original_VPD_hPa'],x['pressure_Pa'])
                        if abs(float(ds['TBOT'][i,0,0])-(x['original_TA_C']+273.15))>1e-6 or abs(float(ds['QBOT'][i,0,0])-q)>1e-8 or abs(float(ds['PSRF'][i,0,0])-x['pressure_Pa'])>.001: raise ValueError('annual source mismatch at '+x['time_local'])
                dest=out/f'{site}_{year}_sensitivity_NOT_APPLIED.nc'; shutil.copyfile(original,dest)
                with Dataset(str(dest),'r+') as ds:
                    for x in changes:
                        i=x['UTC_index']; ds['TBOT'][i,0,0]=x['candidate_TA_C']+273.15
                        ds['QBOT'][i,0,0]=x['candidate_QBOT']; ds['SHUM'][i,0,0]=x['candidate_QBOT']; ds['RH'][i,0,0]=x['candidate_RH_pct']
                    ds.temperature_sensitivity='NOAA-screened isolated TA/VPD interpolations; NOT APPLIED to cases'
                indices={x['UTC_index'] for x in changes}
                with Dataset(str(original)) as srcds, Dataset(str(dest)) as dst:
                    for name in srcds.variables:
                        a0=np.ma.asarray(srcds[name][:]); b0=np.ma.asarray(dst[name][:])
                        if name in ('TBOT','QBOT','SHUM','RH'):
                            mask=np.ones(a0.shape[0],dtype=bool); mask[list(indices)]=False
                            if not np.ma.allequal(a0[mask],b0[mask]): raise ValueError('unexpected changed time in '+name)
                        elif not np.ma.allequal(a0,b0): raise ValueError('unexpected variable change '+name)
                    for x in changes:
                        i=x['UTC_index']
                        for name,value in (('TBOT',x['candidate_TA_C']+273.15),('QBOT',x['candidate_QBOT']),
                                           ('SHUM',x['candidate_QBOT']),('RH',x['candidate_RH_pct'])):
                            if abs(float(dst[name][i,0,0])-value)>1e-5: raise ValueError('candidate readback failed '+name+' '+x['time_local'])
                built.append({'year':year,'original':str(original),'original_sha256':entry['sha256'],'candidate':str(dest),'candidate_sha256':h.sha(dest),'changes':changes})
            results.append({'site':site,'status':'CANDIDATES_CREATED' if built else 'HELD','candidates':built,'held':held,
                            'station':INFO[site], 'stage23_manifest_sha256':rec['sha256'],'stage80_sha256':sel['selected_sha256'],
                            'FLUXMET_source':ri,'ERA_source':ei})
            allchanges.extend(safe)
            print('SITE RESULT',site,'candidate_records',len(safe),'held_target_records',len(held),flush=True)
            for x in safe: print('CANDIDATE',json.dumps(x,sort_keys=True),flush=True)
            for x in held: print('HOLD',site,json.dumps(x,sort_keys=True),flush=True)
        except Exception as exc:
            results.append({'site':site,'status':'ERROR','error':str(exc)}); print('SITE ERROR',site,type(exc).__name__,str(exc),flush=True)
    try:
        ub=json.loads(a.usbar_manifest.read_text()); candidate=Path(ub['candidate_nc']); original=Path(ub['source_nc'])
        if ub.get('site')!='US-Bar' or ub.get('status')!='DETACHED_SENSITIVITY_NOT_APPLIED' or h.sha(candidate)!=ub['candidate_sha256'] or h.sha(original)!=ub['source_sha256'] or len(ub['proposed_changes'])!=3: raise ValueError('US-Bar candidate provenance does not match')
        results.append({'site':'US-Bar','status':'EXISTING_CANDIDATE_VERIFIED','manifest':str(a.usbar_manifest.resolve()),'candidate':str(candidate),'candidate_sha256':ub['candidate_sha256'],'records':3})
        print('US-Bar EXISTING CANDIDATE VERIFIED',candidate,flush=True)
    except Exception as exc:
        results.append({'site':'US-Bar','status':'ERROR','error':str(exc)}); print('SITE ERROR US-Bar',type(exc).__name__,str(exc),flush=True)
    report={'results':results,'note':'Provisional interpolation sensitivity, not truth. Original files and all cases unmodified; no jobs. Other suspect records and QC1/QC2 jumps are not repaired.',
            'clock_assumptions':'tower local interval start; Cbo UTC-5, Man UTC-6, Aud UTC-7; NOAA 5-min ends',
            'warning':'Station heights, location, sampling differences; Thompson is 39.5 km away. ERA is not always independent. Evidence thresholds are screening rules.'}
    (out/'manifest.json').write_text(json.dumps(report,indent=2)+'\n')
    print('REPORT',out/'manifest.json','NO FORCING INPUTS OR CASES MODIFIED; NO JOBS',flush=True)
    return int(any(x['status']=='ERROR' for x in results))


if __name__=='__main__': raise SystemExit(main())
