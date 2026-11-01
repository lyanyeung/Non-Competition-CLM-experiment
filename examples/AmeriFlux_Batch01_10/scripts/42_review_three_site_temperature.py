#!/usr/bin/env python3
"""Print the three-site unresolved temperature events for operator review.

Uses existing source_context.csv and suspects.csv from Stage31 and excludes
only individually verified Stage38 candidates. No input or case is changed.
ERA5 is a comparison source, not necessarily independent of FLUXNET fills.
"""
import argparse, csv, hashlib, json
from datetime import datetime, timedelta
from pathlib import Path

SITES=('CA-Cbo','CA-Man','US-Aud')


def digest(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for part in iter(lambda:f.read(1048576),b''): h.update(part)
    return h.hexdigest()


def csvrows(path):
    with Path(path).open(encoding='utf-8-sig',newline='') as f: return list(csv.DictReader(f))


def show(x):
    if x is None or str(x).strip() in ('','None','nan','-9999','-9999.0'): return '--'
    return str(x).strip()


def main():
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('--proposals',required=True,type=Path)
    p.add_argument('--candidates',required=True,type=Path); p.add_argument('--out',required=True,type=Path)
    a=p.parse_args(); proposal=a.proposals.resolve(strict=True); manifest=a.candidates.resolve(strict=True)
    out=a.out.expanduser().resolve()
    if out.exists() or out.is_symlink(): raise ValueError('Output path already exists')
    summary=json.loads((proposal/'summary.json').read_text())
    if summary.get('errors'): raise ValueError('Original proposal report contains site errors')
    obj=json.loads(manifest.read_text()); completed=set()
    for result in obj['results']:
        if result.get('status')=='ERROR': raise ValueError('Candidate report contains a site error: '+result.get('site','?'))
        for file in result.get('candidates',[]):
            if digest(file['candidate'])!=file['candidate_sha256'] or digest(file['original'])!=file['original_sha256']:
                raise ValueError('Candidate or original file checksum changed: '+result['site'])
            for x in file['changes']: completed.add((result['site'],x['time_local']))
    frames={}
    for row in csvrows(proposal/'source_context.csv'):
        site,time=row['site'],row['time_local']
        if site not in SITES: continue
        key=(site,time)
        if key in frames: raise ValueError('Duplicate source context: '+repr(key))
        frames[key]={k:json.loads(row[k+'_json']) for k in ('selected','tower','era')}
    suspects=[row for row in csvrows(proposal/'suspects.csv')
              if row['site'] in SITES and (row['site'],row['time_local']) not in completed]
    suspects.sort(key=lambda r:(SITES.index(r['site']),r['time_local']))
    if len({(r['site'],r['time_local']) for r in suspects})!=len(suspects): raise ValueError('Duplicate suspects')
    out.mkdir(parents=True); records=[]
    print('UNRESOLVED EVENTS:',len(suspects),'| Times are local standard START; values in degrees C / hPa.',flush=True)
    print('QC: 0 observed, 1 or 2 filled; ERA5 may overlap with the fill source. -- means absent.',flush=True)
    print('Options: KEEP original; INTERPOLATE after validating anchors; ERA candidate after validating TA/VPD; HOLD.',flush=True)
    print('Every option requires physical QA; no values will be changed by this script.',flush=True)
    for i,row in enumerate(suspects,1):
        site,time=row['site'],row['time_local']; center=datetime.fromisoformat(time)
        print('\n'+'='*88,flush=True)
        print(f'[{i:02d}/{len(suspects)}] {site}  {time}  {row["status"]}',flush=True)
        print('Position | Local time          | Tower TA  QC | ERA TA  | Tower VPD QC | ERA VPD | Selected TA/VPD',flush=True)
        samples=[]
        for minutes in (-60,-30,0,30,60):
            stamp=(center+timedelta(minutes=minutes)).strftime('%Y-%m-%d %H:%M:%S')
            f=frames.get((site,stamp)); mark='  <==' if minutes==0 else ''
            if f:
                t,e,s=f['tower'],f['era'],f['selected']
                val={'time_local':stamp,'tower_TA_C':t.get('TA_F'),'tower_TA_QC':t.get('TA_F_QC'),
                     'era_TA_C':e.get('TA_ERA'),'tower_VPD_hPa':t.get('VPD_F'),'tower_VPD_QC':t.get('VPD_F_QC'),
                     'era_VPD_hPa':e.get('VPD_ERA'),'selected_TA_C':s.get('TA_USE'),'selected_VPD_hPa':s.get('VPD_USE')}
                print(f'{minutes:+4d} min | {stamp} | {show(val["tower_TA_C"]):>8} {show(val["tower_TA_QC"]):>3} | {show(val["era_TA_C"]):>7} | {show(val["tower_VPD_hPa"]):>9} {show(val["tower_VPD_QC"]):>3} | {show(val["era_VPD_hPa"]):>7} | {show(val["selected_TA_C"])}/{show(val["selected_VPD_hPa"])}{mark}',flush=True)
            else:
                val={'time_local':stamp,'missing':True}; print(f'{minutes:+4d} min | {stamp} | -- source context absent{mark}',flush=True)
            samples.append(val)
        records.append({'id':i,'site':site,'time_local':time,'prior_hold_reason':row['status'],'samples':samples})
    (out/'review.json').write_text(json.dumps({'records':records,'excluded_existing_candidates':sorted(completed),
        'source_context_sha256':digest(proposal/'source_context.csv'),'suspects_sha256':digest(proposal/'suspects.csv'),
        'candidate_manifest_sha256':digest(manifest),'no_data_or_case_modified':True},indent=2)+'\n',encoding='utf-8')
    with (out/'decisions_template.csv').open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=('id','site','time_local','decision','notes')); w.writeheader()
        for x in records: w.writerow({'id':x['id'],'site':x['site'],'time_local':x['time_local'],'decision':'','notes':''})
    print('\nREVIEW JSON:',out/'review.json',flush=True)
    print('OPTIONAL DECISIONS TEMPLATE:',out/'decisions_template.csv',flush=True)
    print('NO FORCING, CASE OR SLURM JOB MODIFIED',flush=True)


if __name__=='__main__': main()
