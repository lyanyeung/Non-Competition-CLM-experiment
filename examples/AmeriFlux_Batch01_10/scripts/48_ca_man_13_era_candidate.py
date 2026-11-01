#!/usr/bin/env python3
"""Build user-approved CA-Man 13 ERA candidate together with prior 14 candidate.

Only the two explicitly selected half-hours (16:30 and 17:00 local), plus the
previously approved 14 repair already in the detached 2007 file, are changed.
No original forcing or case is touched and no jobs are submitted.
"""
import argparse, csv, importlib.util, json, shutil
from pathlib import Path
import numpy as np
from netCDF4 import Dataset

SITE='CA-Man'
STAGE80=Path('/iridisfs/scratch/ly3n24/CLM_FATES/experiments/AmeriFlux_MultiSite_10/reports/stage80_RH_lt1_final_20261024T123353Z/10_site_selected_forcing_sources.tsv')
EVENTS={'2007-01-23 16:30:00':(-15.832,.408,1,2,-23.993,.408),
        '2007-01-23 17:00:00':(-10.282,.220,0,1,-23.126,.419)}
FIELDS=('TBOT','QBOT','SHUM','RH')


def load(path,name):
    spec=importlib.util.spec_from_file_location(name,path); m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for x in ('run','previous','context-helper','physics-helper','out'): p.add_argument('--'+x,required=True,type=Path)
    a=p.parse_args(); root=a.run.resolve(strict=True); previous=a.previous.resolve(strict=True); out=a.out.expanduser().resolve()
    if out.exists() or out.is_symlink(): raise ValueError('Output directory already exists')
    h=load(a.context_helper,'context29'); phys=load(a.physics_helper,'physics32')
    completed=json.loads((root/'COMPLETE.json').read_text()); rec=next(x for x in completed['sites'] if x['site']==SITE)
    source_manifest=Path(rec['manifest']).resolve(strict=True)
    if root not in source_manifest.parents or h.sha(source_manifest)!=rec['sha256']: raise ValueError('Stage23 manifest invalid')
    meta=json.loads(source_manifest.read_text()); file=next(x for x in meta['annual_files'] if int(x['year'])==2007)
    original=Path(file['path']).resolve(strict=True)
    if root not in original.parents or h.sha(original)!=file['sha256']: raise ValueError('Original 2007 file changed')
    old_report=json.loads(previous.read_text())
    if old_report.get('status')!='DETACHED_NOT_USED_BY_CASES': raise ValueError('Prior candidate report invalid')
    old_site=next(x for x in old_report['sites'] if x['site']==SITE)
    if old_site['source_manifest_sha256']!=rec['sha256']: raise ValueError('Prior candidate uses different Stage23')
    prior=next(x for x in old_site['files'] if int(x['year'])==2007)
    if Path(prior['source']).resolve(strict=True)!=original or prior['source_sha256']!=file['sha256']: raise ValueError('Prior candidate source mismatch')
    base=Path(prior['candidate']).resolve(strict=True)
    if h.sha(base)!=prior['candidate_sha256']: raise ValueError('Prior 2007 candidate checksum changed')
    previous_changes=prior['changes']
    if len(previous_changes)!=1 or previous_changes[0].get('id')!=14 or previous_changes[0].get('time_local')!='2007-03-10 11:00:00':
        raise ValueError('Previous file must contain only the approved ID14 repair')
    with STAGE80.open(encoding='utf-8-sig',newline='') as f: selected=next(x for x in csv.DictReader(f,delimiter='\t') if x['site']==SITE)
    source=Path(selected['selected_source'])
    if h.sha(source)!=selected['selected_sha256']: raise ValueError('Selected source checksum changed')
    raw,raw_info=h.sources(SITE,'FLUXMET_HH'); era,era_info=h.sources(SITE,'ERA5_HH')
    if raw is None or era is None: raise ValueError('Original FLUXMET or ERA5 unavailable')
    wanted=set(EVENTS)
    s=h.read_subset(source,'time',wanted,('TA_USE','VPD_USE','QBOT','PSRF'))
    t=h.read_subset(raw,'TIMESTAMP_START',wanted,('TA_F','TA_F_QC','VPD_F','VPD_F_QC'),True)
    e=h.read_subset(era,'TIMESTAMP_START',wanted,('TA_ERA','VPD_ERA'),True)
    if any(set(x)!=wanted for x in (s,t,e)): raise ValueError('Reviewed timestamps missing or duplicated')
    changes=[]
    for time,(old_t,old_v,ta_qc,vpd_qc,era_t,era_v) in EVENTS.items():
        values=((float(s[time]['TA_USE']),old_t),(float(s[time]['VPD_USE']),old_v),
                (float(t[time]['TA_F']),old_t),(float(t[time]['VPD_F']),old_v),
                (float(t[time]['TA_F_QC']),ta_qc),(float(t[time]['VPD_F_QC']),vpd_qc),
                (float(e[time]['TA_ERA']),era_t),(float(e[time]['VPD_ERA']),era_v))
        if any(abs(v-w)>.002 for v,w in values): raise ValueError('Source differs from reviewed record: '+time)
        pressure=float(s[time]['PSRF']); q,rh=phys.q_from_tvpd(era_t,era_v,pressure)
        year,index=phys.utc_index(time,int(meta['UTC_shift_halfhours']),*meta['years'])
        if year!=2007: raise ValueError('Unexpected UTC output year')
        changes.append({'id':13,'site':SITE,'time_local':time,'UTC_year':year,'UTC_index':index,
            'original_TA_C':old_t,'original_VPD_hPa':old_v,'tower_TA_QC':ta_qc,'tower_VPD_QC':vpd_qc,
            'pressure_Pa':pressure,'candidate_TA_C':era_t,'candidate_VPD_hPa':era_v,'candidate_QBOT':q,
            'candidate_RH_pct':rh,'method':'USER_APPROVED_ERA5_TA_AND_VPD'})
    allchanges=previous_changes+changes; indices={int(x['UTC_index']) for x in allchanges}
    if len(indices)!=3: raise ValueError('Unexpected overlapping candidate indices')
    with Dataset(str(original)) as old:
        for x in changes:
            i=x['UTC_index']; time=x['time_local']
            if abs(float(old['TBOT'][i,0,0])-(x['original_TA_C']+273.15))>1e-6 or abs(float(old['QBOT'][i,0,0])-float(s[time]['QBOT']))>1e-8 or abs(float(old['PSRF'][i,0,0])-x['pressure_Pa'])>.001:
                raise ValueError('Stage23 timestamp/forcing mismatch: '+time)
    out.mkdir(parents=True); dest=out/'CA-Man_2007_ID13_ID14_ERA_AND_INTERPOLATED_SENSITIVITY.nc'; shutil.copyfile(base,dest)
    with Dataset(str(dest),'r+') as ds:
        for x in changes:
            i=x['UTC_index']; ds['TBOT'][i,0,0]=x['candidate_TA_C']+273.15
            ds['QBOT'][i,0,0]=x['candidate_QBOT']; ds['SHUM'][i,0,0]=x['candidate_QBOT']; ds['RH'][i,0,0]=x['candidate_RH_pct']
        ds.temperature_sensitivity='User-approved ID13 ERA TA/VPD and ID14 tower interpolation; detached, not applied'
    with Dataset(str(original)) as a0,Dataset(str(dest)) as b:
        for key in a0.variables:
            x=np.ma.asarray(a0[key][:]); y=np.ma.asarray(b[key][:])
            if key in FIELDS:
                mask=np.ones(x.shape[0],dtype=bool); mask[list(indices)]=False
                if not np.ma.allequal(x[mask],y[mask]): raise ValueError('Unexpected changed time '+key)
            elif not np.ma.allequal(x,y): raise ValueError('Unexpected changed field '+key)
        for x in allchanges:
            i=x['UTC_index']
            for name,value in (('TBOT',x['candidate_TA_C']+273.15),('QBOT',x['candidate_QBOT']),('SHUM',x['candidate_QBOT']),('RH',x['candidate_RH_pct'])):
                if abs(float(b[name][i,0,0])-float(value))>1e-5: raise ValueError('Candidate readback mismatch '+name)
    report={'status':'DETACHED_NOT_USED_BY_CASES','site':SITE,'year':2007,
        'original':str(original),'original_sha256':file['sha256'],'previous_manifest':str(previous),'previous_manifest_sha256':h.sha(previous),
        'previous_candidate':str(base),'previous_candidate_sha256':prior['candidate_sha256'],
        'candidate':str(dest),'candidate_sha256':h.sha(dest),'stage23_manifest_sha256':rec['sha256'],
        'stage80_sha256':selected['selected_sha256'],'FLUXMET_source':raw_info,'ERA_source':era_info,
        'changes':allchanges,'user_decision':'ID13 use ERA for exactly 16:30 and 17:00; preserve prior approved ID14 candidate',
        'caveat':'ERA5 is a proxy and not necessarily independent of FLUXNET fill',
        'no_original_or_case_modified':True,'no_slurm_jobs':True}
    (out/'manifest.json').write_text(json.dumps(report,indent=2)+'\n')
    for x in changes: print('ID13 ERA CANDIDATE',json.dumps(x,sort_keys=True),flush=True)
    print('CA-Man 2007: ID13 AND PRIOR ID14 CANDIDATES COMBINED',dest,flush=True)
    print('MANIFEST',out/'manifest.json','NO CASE OR SLURM MODIFIED',flush=True)


if __name__=='__main__': main()
