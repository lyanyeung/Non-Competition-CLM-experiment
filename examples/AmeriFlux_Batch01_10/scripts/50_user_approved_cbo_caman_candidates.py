#!/usr/bin/env python3
"""Build user-approved CA-Cbo 04 and CA-Man 11/12 detached candidates.

CA-Cbo 2018 also retains previously approved 02/03 edits. CA-Man 2005 uses
ERA TA/VPD for exactly 45 half-hours confirmed by independent station review.
The 2007 ID13+14 candidate is linked, never overwritten. No cases or jobs.
"""
import argparse, csv, importlib.util, json, shutil
from datetime import datetime, timedelta
from pathlib import Path
import numpy as np
from netCDF4 import Dataset

STAGE80=Path('/iridisfs/scratch/ly3n24/CLM_FATES/experiments/AmeriFlux_MultiSite_10/reports/stage80_RH_lt1_final_20261024T123353Z/10_site_selected_forcing_sources.tsv')
FIELDS=('TBOT','QBOT','SHUM','RH')
CBO={'2018-07-18 16:00:00':(34.069,33.572,1/3), '2018-07-18 16:30:00':(32.333,32.425,2/3)}


def module(path,name):
    spec=importlib.util.spec_from_file_location(name,path); m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m


def number(v):
    x=float(v)
    if not np.isfinite(x) or x<=-9990: raise ValueError('Invalid source numerical value')
    return x


def read_rows(path):
    with Path(path).open(encoding='utf-8-sig',newline='') as f: return list(csv.DictReader(f))


def check_close(actual,expected,what,tol=.002):
    if abs(number(actual)-number(expected))>tol: raise ValueError('Source mismatch '+what)


def get_inputs(h,root,site):
    rec=next(x for x in json.loads((root/'COMPLETE.json').read_text())['sites'] if x['site']==site)
    path=Path(rec['manifest']).resolve(strict=True)
    if root not in path.parents or h.sha(path)!=rec['sha256']: raise ValueError(site+': Stage23 manifest checksum mismatch')
    m=json.loads(path.read_text()); selected=next(x for x in read_rows_tsv(STAGE80) if x['site']==site)
    source=Path(selected['selected_source'])
    if h.sha(source)!=selected['selected_sha256']: raise ValueError(site+': selected forcing checksum mismatch')
    tower,tinfo=h.sources(site,'FLUXMET_HH'); era,einfo=h.sources(site,'ERA5_HH')
    if tower is None or era is None: raise ValueError(site+': tower or ERA source unavailable')
    return rec,m,selected,source,tower,era,tinfo,einfo


def read_rows_tsv(path):
    with Path(path).open(encoding='utf-8-sig',newline='') as f: return list(csv.DictReader(f,delimiter='\t'))


def frames(h,selected,tower,era,wanted):
    s=h.read_subset(selected,'time',wanted,('TA_USE','VPD_USE','QBOT','PSRF'))
    t=h.read_subset(tower,'TIMESTAMP_START',wanted,('TA_F','TA_F_QC','VPD_F','VPD_F_QC'),True)
    e=h.read_subset(era,'TIMESTAMP_START',wanted,('TA_ERA','VPD_ERA'),True)
    if any(set(x)!=wanted for x in (s,t,e)): raise ValueError('Missing or duplicated source timestamp')
    return {k:{'selected':s[k],'tower':t[k],'era':e[k]} for k in wanted}


def src_nc(h,root,m,year):
    entry=next(x for x in m['annual_files'] if int(x['year'])==year); path=Path(entry['path']).resolve(strict=True)
    if root not in path.parents or h.sha(path)!=entry['sha256']: raise ValueError('Original annual forcing checksum mismatch')
    return entry,path


def checked_previous(h,report,site,year,original,entry,expected_ids):
    row=next(x for x in report['sites'] if x['site']==site); file=next(x for x in row['files'] if int(x['year'])==year)
    if Path(file['source']).resolve(strict=True)!=original or file['source_sha256']!=entry['sha256']:
        raise ValueError('Previous candidate source mismatch')
    prior=Path(file['candidate']).resolve(strict=True)
    if h.sha(prior)!=file['candidate_sha256'] or {x['id'] for x in file['changes']}!=set(expected_ids):
        raise ValueError('Previous candidate checksum/record IDs mismatch')
    return prior,file['changes']


def validate_origin(original,change,selected):
    with Dataset(str(original)) as ds:
        i=change['UTC_index']
        for var,expected,tol in (('TBOT',number(selected['TA_USE'])+273.15,1e-6),
                                 ('QBOT',number(selected['QBOT']),1e-8),('PSRF',number(selected['PSRF']),.001)):
            if abs(float(ds[var][i,0,0])-expected)>tol: raise ValueError('Stage23 source timestamp mismatch '+var)


def save_candidate(h,original,base,dest,old_changes,new_changes):
    allchanges=old_changes+new_changes; indices={int(x['UTC_index']) for x in allchanges}
    if len(indices)!=len(allchanges): raise ValueError('Overlapping changes')
    shutil.copyfile(base,dest)
    with Dataset(str(dest),'r+') as ds:
        for x in new_changes:
            i=x['UTC_index']; ds['TBOT'][i,0,0]=x['candidate_TA_C']+273.15
            ds['QBOT'][i,0,0]=x['candidate_QBOT']; ds['SHUM'][i,0,0]=x['candidate_QBOT']; ds['RH'][i,0,0]=x['candidate_RH_pct']
        ds.temperature_sensitivity='User-approved repair; detached forcing candidate, not used by model cases'
    with Dataset(str(original)) as a,Dataset(str(dest)) as b:
        if set(a.variables)!=set(b.variables): raise ValueError('Variable set changed')
        for var in a.variables:
            x=np.ma.asarray(a[var][:]); y=np.ma.asarray(b[var][:])
            if var in FIELDS:
                if x.shape!=y.shape or x.shape[0]!=17520: raise ValueError('Unexpected variable shape '+var)
                mask=np.ones(x.shape[0],dtype=bool); mask[list(indices)]=False
                if not np.ma.allequal(x[mask],y[mask]): raise ValueError('Unexpected changed time '+var)
            elif not np.ma.allequal(x,y): raise ValueError('Unexpected changed variable '+var)
        for x in allchanges:
            i=x['UTC_index']
            for var,want in (('TBOT',x['candidate_TA_C']+273.15),('QBOT',x['candidate_QBOT']),('SHUM',x['candidate_QBOT']),('RH',x['candidate_RH_pct'])):
                if abs(float(b[var][i,0,0])-float(want))>1e-5: raise ValueError('Candidate readback mismatch '+var)
    return {'original':str(original),'original_sha256':h.sha(original),'previous_candidate':str(base),
            'previous_candidate_sha256':h.sha(base),'candidate':str(dest),'candidate_sha256':h.sha(dest),'changes':allchanges}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for x in ('run','previous','man2007','context-helper','physics-helper','out'): p.add_argument('--'+x,required=True,type=Path)
    a=p.parse_args(); root=a.run.resolve(strict=True); previous=a.previous.resolve(strict=True); man2007=a.man2007.resolve(strict=True); out=a.out.expanduser().resolve()
    if out.exists() or out.is_symlink(): raise ValueError('Output already exists')
    h=module(a.context_helper,'context29'); phys=module(a.physics_helper,'physics32')
    old=json.loads(previous.read_text())
    if old.get('status')!='DETACHED_NOT_USED_BY_CASES': raise ValueError('Previous report invalid')
    linked=json.loads(man2007.read_text())
    if linked.get('status')!='DETACHED_NOT_USED_BY_CASES' or linked.get('site')!='CA-Man' or h.sha(linked['candidate'])!=linked['candidate_sha256']:
        raise ValueError('CA-Man 2007 merged 13/14 candidate invalid')
    context_path=previous.parent/'extended_context.csv'; context=read_rows(context_path)
    out.mkdir(parents=True); results=[]

    site='CA-Cbo'; rec,m,sel,source,tower,era,tinfo,einfo=get_inputs(h,root,site)
    wanted=set(CBO)|{'2018-07-18 15:30:00','2018-07-18 17:00:00'}
    f=frames(h,source,tower,era,wanted); left=f['2018-07-18 15:30:00']; right=f['2018-07-18 17:00:00']
    for frame,expected in ((left,(24.855,12.377,1,1)),(right,(28.238,25.496,0,0))):
        for actual,want in ((frame['tower']['TA_F'],expected[0]),(frame['tower']['VPD_F'],expected[1]),
                            (frame['tower']['TA_F_QC'],expected[2]),(frame['tower']['VPD_F_QC'],expected[3]),
                            (frame['selected']['TA_USE'],expected[0]),(frame['selected']['VPD_USE'],expected[1])):
            check_close(actual,want,'CA-Cbo interpolation anchor')
    entry,original=src_nc(h,root,m,2018); base,old_changes=checked_previous(h,old,site,2018,original,entry,{2,3}); new=[]
    for time,(t0,v0,fraction) in CBO.items():
        x=f[time]; check_close(x['tower']['TA_F'],t0,time); check_close(x['tower']['VPD_F'],v0,time)
        check_close(x['tower']['TA_F_QC'],0,time); check_close(x['tower']['VPD_F_QC'],0,time)
        check_close(x['selected']['TA_USE'],t0,time); check_close(x['selected']['VPD_USE'],v0,time)
        temp=24.855+(28.238-24.855)*fraction; vpd=12.377+(25.496-12.377)*fraction; pressure=number(x['selected']['PSRF'])
        q,rh=phys.q_from_tvpd(temp,vpd,pressure); year,index=phys.utc_index(time,int(m['UTC_shift_halfhours']),*m['years'])
        if year!=2018: raise ValueError('CA-Cbo unexpected UTC year')
        row={'id':4,'site':site,'time_local':time,'UTC_index':index,'UTC_year':year,'original_TA_C':t0,'original_VPD_hPa':v0,
             'pressure_Pa':pressure,'candidate_TA_C':temp,'candidate_VPD_hPa':vpd,'candidate_QBOT':q,'candidate_RH_pct':rh,
             'method':'USER_APPROVED_LINEAR_15:30_QC1_TO_17:00_QC0','left_anchor':'2018-07-18 15:30:00','right_anchor':'2018-07-18 17:00:00'}
        validate_origin(original,row,x['selected']); new.append(row)
    result=save_candidate(h,original,base,out/'CA-Cbo_2018_ID02_03_04_sensitivity.nc',old_changes,new)
    result.update(site=site,year=2018,source_manifest_sha256=rec['sha256'],stage80_sha256=sel['selected_sha256'],FLUXMET_source=tinfo,ERA_source=einfo)
    results.append(result)
    for row in new: print('APPROVED CBO04',json.dumps(row,sort_keys=True),flush=True)

    site='CA-Man'; rec,m,sel,source,tower,era,tinfo,einfo=get_inputs(h,root,site)
    if linked.get('stage23_manifest_sha256')!=rec['sha256']: raise ValueError('CA-Man 2007 candidate references different Stage23 input')
    begin=datetime.fromisoformat('2004-12-31 18:00:00'); dates=[(begin+timedelta(minutes=30*i)).strftime('%Y-%m-%d %H:%M:%S') for i in range(45)]
    if dates[-1]!='2005-01-01 16:00:00': raise ValueError('Unexpected 45-record interval')
    f=frames(h,source,tower,era,set(dates)); ext={x['time_local']:x for x in context if x['site']==site and x['review_id']=='11_12'}
    entry,original=src_nc(h,root,m,2005); new=[]
    with Dataset(str(original)) as ds:
        for time in dates:
            row=ext.get(time)
            if not row: raise ValueError('User-reviewed extended context missing '+time)
            x=f[time]
            for source_val,review_val in ((x['tower']['TA_F'],row['tower_TA_C']),(x['tower']['TA_F_QC'],row['tower_TA_QC']),
                (x['tower']['VPD_F'],row['tower_VPD_hPa']),(x['tower']['VPD_F_QC'],row['tower_VPD_QC']),
                (x['era']['TA_ERA'],row['era_TA_C']),(x['era']['VPD_ERA'],row['era_VPD_hPa']),
                (x['selected']['TA_USE'],row['selected_TA_C']),(x['selected']['VPD_USE'],row['selected_VPD_hPa'])):
                check_close(source_val,review_val,'CA-Man reviewed segment '+time)
            year,index=phys.utc_index(time,int(m['UTC_shift_halfhours']),*m['years'])
            if year!=2005: raise ValueError('CA-Man segment spans unexpected UTC year')
            pressure=number(x['selected']['PSRF']); temp=number(x['era']['TA_ERA']); vpd=number(x['era']['VPD_ERA'])
            q,rh=phys.q_from_tvpd(temp,vpd,pressure)
            for var,want,tol in (('TBOT',number(x['selected']['TA_USE'])+273.15,1e-6),('QBOT',number(x['selected']['QBOT']),1e-8),('PSRF',pressure,.001)):
                if abs(float(ds[var][index,0,0])-want)>tol: raise ValueError('Stage23 segment timestamp mismatch '+time+' '+var)
            new.append({'id':'11_12','site':site,'time_local':time,'UTC_year':year,'UTC_index':index,
                'original_TA_C':number(x['selected']['TA_USE']),'original_VPD_hPa':number(x['selected']['VPD_USE']),
                'original_TA_QC':number(x['tower']['TA_F_QC']),'original_VPD_QC':number(x['tower']['VPD_F_QC']),
                'pressure_Pa':pressure,'candidate_TA_C':temp,'candidate_VPD_hPa':vpd,'candidate_QBOT':q,'candidate_RH_pct':rh,
                'method':'USER_APPROVED_ERA5_TA_AND_VPD'})
    result=save_candidate(h,original,original,out/'CA-Man_2005_ID11_12_ERA_sensitivity.nc',[],new)
    result.update(site=site,year=2005,source_manifest_sha256=rec['sha256'],stage80_sha256=sel['selected_sha256'],FLUXMET_source=tinfo,ERA_source=einfo)
    result['independent_comparison']={'station':'ECCC Thompson A, stationID 3905, climate ID 5062922',
        'approx_distance_km':39.5,'sampling':'hourly local standard time, not exact tower half-hour',
        'samples_C':{'2004-12-31 18:00':-27.6,'2005-01-01 08:00':-33.5,'2005-01-01 16:00':-26.2},
        'urls':['https://climate.weather.gc.ca/climate_data/bulk_data_e.html?format=csv&stationID=3905&Year=2004&Month=12&Day=31&timeframe=1',
                'https://climate.weather.gc.ca/climate_data/bulk_data_e.html?format=csv&stationID=3905&Year=2005&Month=1&Day=1&timeframe=1']}
    results.append(result)
    print('APPROVED CA-MAN 11_12',len(new),'records',dates[0],'through',dates[-1],flush=True)
    for row in (new[0],new[-1]): print('SEGMENT ENDPOINT',json.dumps(row,sort_keys=True),flush=True)
    final={'status':'DETACHED_NOT_USED_BY_CASES','previous_report':str(previous),'previous_report_sha256':h.sha(previous),
        'review_context':str(context_path),'review_context_sha256':h.sha(context_path),'files':results,
        'linked_CA_Man_2007_13_14_manifest':str(man2007),'linked_CA_Man_2007_13_14_manifest_sha256':h.sha(man2007),
        'other_previous_candidates_are_not_merged':True,
        'note':'User-approved sensitivities; Q1 adjacent periods and other held records remain for separate assessment.',
        'no_original_or_case_modified':True,'no_slurm_jobs':True}
    (out/'manifest.json').write_text(json.dumps(final,indent=2)+'\n')
    print('COMPLETE',out/'manifest.json','NO MODEL CASE OR SLURM JOB MODIFIED',flush=True)


if __name__=='__main__': main()
