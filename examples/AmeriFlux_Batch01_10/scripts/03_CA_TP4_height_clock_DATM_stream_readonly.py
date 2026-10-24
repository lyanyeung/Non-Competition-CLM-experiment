#!/usr/bin/env python3
"""AmeriFlux AD400 Stage03 READ ONLY: inspect CA-TP4 height/clock + the actual
CH-Dav B01 FIXNC AD400 CDEPS/DATM stream contract, to prepare ONE AD5 pilot.

Source products: final Stage80 10-site forcing, Stage81 213 NetCDF, Stage82
213 SHA checks, Stage31 BASE height candidate policies and original BASE rows.
Never assert TA_F sensor mapping merely from a BASE variable name. Never
modify the existing NetCDF time axis, ZBOT, surface, CIME, run or Slurm jobs.
This script has no write actions.
"""
from __future__ import annotations
import argparse,csv,hashlib,json,math,xml.etree.ElementTree as ET
from pathlib import Path
from datetime import datetime

BASE=Path('/iridisfs/scratch/ly3n24/CLM_FATES')
AMF=BASE/'experiments/AmeriFlux_MultiSite_10'
CASE=BASE/'cases/CH-Dav_B01_FIXNC_AD400'
SITE='CA-TP4'
HEIGHT_REPORT=AMF/'reports/stage31_provisional_ZBOT_scenarios_20261022T022341481986Z/01_provisional_site_height_policies.json'
HEIGHT_RAW=Path.home()/'CLM-FATES-single-site-workflows/examples/AmeriFlux_sites/metadata/BASE_MeasurementHeight_20260908.csv'
HEIGHT_RAW_SHA='1c1e4171d295406a13d503f877b58661a651c88ffb6f0b6ec498f56bb1fcec5a'
STAGE80=AMF/'reports/stage80_RH_lt1_final_20261024T123353Z'
STAGE81=AMF/'reports/stage81_DATM_technical_20261024T162235Z'
STAGE82=AMF/'reports/stage82_DATM_case_integration_preflight_20261024T231124502670Z'
SITE_SOURCE=BASE/'sites/MY_EC_SITE'/SITE
SRC_PACKAGE='AMF_CA-TP4_FLUXNET_2002-2023_v1.3_r1'
VAR='TA_PI_F_1_1_1'
MET=('FLDS','FSDS','PRECTmms','PSRF','TBOT','WIND','SHUM')
MAX_META=3_000_000

def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
 return h.hexdigest()

def manifest(path):
 if not path.is_file():raise RuntimeError('Missing prior successful report '+str(path))
 return json.loads(path.read_text(encoding='utf-8'))

def read_sample(path,n=3):
 with path.open(newline='',encoding='utf-8-sig',errors='replace') as f:
  reader=csv.DictReader(f)
  cols=reader.fieldnames or []
  if not cols or len(cols)!=len(set(cols)):
   raise RuntimeError('Invalid CSV columns '+str(path))
  rows=[]
  for i,row in enumerate(reader):
   if i>=n:break
   rows.append(row)
  return cols,rows

def inspect_base():
 if sha(HEIGHT_RAW)!=HEIGHT_RAW_SHA:
  raise RuntimeError('Original BASE measurement height CSV checksum drift')
 p=manifest(HEIGHT_REPORT)
 if p.get('method')!='AmeriFlux_STAGE31_BASE_STATIC_DYNAMIC_POLICY_SCENARIOS':
  raise RuntimeError('Stage31 height policy method changed')
 policy=p['provisional_sensor_policy'][SITE]
 if policy['candidate_ZBOT_mode']!='STATIC' or float(policy['baseline_m'])!=28 or policy['variable_BASE']!=VAR:
  raise RuntimeError('Unexpected CA-TP4 BASE candidate change')
 if policy.get('dated_events'):raise RuntimeError('CA-TP4 candidate has unaccounted dated event(s)')
 print('=== ZBOT RESEARCH EVIDENCE — NOT A VERIFIED TA_F CROSSWALK ===')
 print('BASE snapshot SHA256:',HEIGHT_RAW_SHA)
 print('STAGE31 snapshot SHA256:',sha(HEIGHT_REPORT))
 print('SITE:',SITE,'BASE_VARIABLE:',VAR,
       'CANDIDATE_HEIGHT_M:',policy['baseline_m'],
       'MODE:',policy['candidate_ZBOT_mode'])
 print('FLUXNET_TA_F_CROSSWALK:',policy['FLUXNET_TA_F_sensor_crosswalk'])
 cols,rows=read_sample(HEIGHT_RAW,0)
 required={'Site_ID','Variable','Height','Start_Date'}
 if not required.issubset(cols):raise RuntimeError('BASE metadata unexpected columns')
 matched=[]
 with HEIGHT_RAW.open(newline='',encoding='utf-8-sig') as f:
  for row in csv.DictReader(f):
   if row['Site_ID']==SITE and row['Variable'].upper().startswith('TA'):
    matched.append(row)
 for r in matched[:35]:
  print('BASE_TA_SENSOR:',r['Variable'],'HEIGHT_M:',r['Height'],
        'EFFECTIVE_FROM:',r['Start_Date'] or 'SOURCE_START_UNDATED',
        'INSTRUMENT:',(r.get('Instrument_Model') or '')[:110],
        'COMMENT:',(r.get('Comment') or '')[:170])
 if not any(r['Variable']==VAR and abs(float(r['Height'])-28)<1e-6 for r in matched):
  raise RuntimeError('Chosen BASE row with 28m height not found')
 print('NOT_PROVEN: FLUXNET TA_F references this exact BASE sensor; 28m remains a documented provisional pilot option.')

def inspect_raw_clock():
 print('=== OFFICIAL FLUXNET PRODUCT TIME SUPPORT / COLUMN EVIDENCE ===')
 folder=SITE_SOURCE/'forcing/raw'/SRC_PACKAGE
 print('PACKAGE_RAW_DIRECTORY:',str(folder),'exists',folder.is_dir())
 if not folder.is_dir():
  print('RAW_TIME_LABEL_HOLD: official product not extracted at expected raw source directory')
  return
 entries=sorted(x for x in folder.glob('*.csv') if x.is_file())
 met=[p for p in entries if ('FLUXMET' in p.name.upper() or 'FULLSET' in p.name.upper())
      and ('_HH_' in p.name.upper() or '_HR_' in p.name.upper())]
 print('FLUXMET_OR_FULLSET_HH_HR_FILES:',[p.name for p in met[:12]])
 for p in met[:3]:
  cols,rows=read_sample(p,3)
  print('SOURCE_FILE:',p.name)
  print('TIME_FIELDS:',[x for x in cols if 'TIMESTAMP' in x.upper() or x.upper() in ('TIME','DATE')])
  print('TA_COLUMN_MATCHES:',[x for x in cols if x.upper().startswith(('TA_F','TA_PI'))][:18])
  for r in rows:
   print('SOURCE_SAMPLE_TIMESTAMPS:',{k:r.get(k) for k in cols if 'TIMESTAMP' in k.upper()})
 if not met:print('RAW_TIME_SUPPORT_UNRESOLVED: no extractable HH/HR CSV shown')
 print('CRITICAL: TIMESTAMP_START vs TIMESTAMP_END cannot be resolved solely by the NetCDF time.units field.')
 print('REQUIRE: identify whether Stage80 time is START, END or midpoint and station local-standard vs UTC before coupling.')

def inspect_stage81():
 import numpy as np
 from netCDF4 import Dataset
 m=manifest(STAGE81/'manifest.json')
 a=manifest(STAGE82/'manifest.json')
 s80=manifest(STAGE80/'manifest.json')
 if (s80.get('native_ERA5_joint_replaced_rows')!=18 or m.get('all_annual_netcdf_files')!=213
     or a.get('verified_annual_files_sha256')!=213):
  raise RuntimeError('Pinned Stage80/81/82 provenance chain changed')
 if sha(STAGE81/'manifest.json')!=a.get('input_stage81_manifest_sha256'):
  raise RuntimeError('Stage82 no longer matches Stage81')
 record=next((x for x in m['sites'] if x['site']==SITE),None)
 if record is None or len(record['annual_files'])!=22:raise RuntimeError('Missing CA-TP4 22-year NetCDF')
 first=record['annual_files'][0]
 path=Path(first['file'])
 if sha(path)!=first['sha256']:raise RuntimeError('CA-TP4 first yearly NC SHA changed')
 source=Path(record['forcing_path'])
 if sha(source)!=record['forcing_sha256']:
  raise RuntimeError('CA-TP4 source Stage80 forcing SHA changed')
 cols,rows=read_sample(source,4)
 print('=== ACTUAL SELECTED CA-TP4 METEO / NC CLOCK ===')
 print('ORIGINAL_STAGE80_CSV:',str(source))
 print('CSV_HEAD_TIMESTAMPS:',[r['time'] for r in rows])
 with Dataset(path,'r') as nc:
  print('NETCDF_FIRST_YEAR:',str(path))
  print('NC_FILE_FORMAT:',nc.file_format)
  print('NC_TIME_UNITS:',nc.variables['time'].units,
        'CALENDAR:',nc.variables['time'].calendar)
  print('NC_TIME_FIRST_VALUES:',[float(x) for x in nc.variables['time'][:4]])
  print('NC_SOURCE_TIME_NOTICE:',getattr(nc,'time_label_status','MISSING'))
  print('NC_MAPPED_FIELDS:',{k:dict(dims=nc.variables[k].dimensions,
             units=getattr(nc.variables[k],'units','UNKNOWN')) for k in MET})
  print('NC_ZBOT_VARIABLE_PRESENT:','ZBOT' in nc.variables)
  for k in MET:
   arr=np.asarray(nc.variables[k][:2,0,0])
   if not np.isfinite(arr).all():raise RuntimeError('NC first sample nonfinite '+k)
 print('NC_TIME_INTERPRETATION: ORIGINAL_LOCAL_LABEL_UNVERIFIED (DO NOT SILENTLY SHIFT BY +15m).')

def xml_child_text(n,name):
 # Read direct children by local name, preserving compatibility with CIME markup.
 for x in n:
  if x.tag.split('}')[-1]==name:return ''.join(x.itertext()).strip()
 return ''

def inspect_reference(case):
 xml=case/'CaseDocs/datm.streams.xml'
 if not xml.is_file():raise RuntimeError('Reference case missing effective CaseDocs/datm.streams.xml')
 print('=== ACTUAL CIME / CDEPS EFFECTIVE STREAM STRUCTURE ===')
 print('REFERENCE_CASE:',str(case))
 print('STREAM_SOURCE_SHA256:',sha(xml))
 root=ET.parse(xml).getroot()
 print('STREAM_XML_ROOT:',root.tag)
 streams=[x for x in root.iter() if x.tag.split('}')[-1]=='stream_info']
 if not streams:raise RuntimeError('Reference XML contains no stream_info')
 available=set()
 for i,st in enumerate(streams):
  print('STREAM_INDEX:',i,'STREAM_NAME:',st.attrib.get('name','UNKNOWN'))
  for key in ('taxmode','tintalgo','mapalgo','readmode','year_first','year_last',
              'year_align','offset','meshfile','dtlimit'):
   print('  '+key.upper()+':',xml_child_text(st,key)[:270] or 'ABSENT')
  source=next((x for x in st if x.tag.split('}')[-1]=='datafiles'),None)
  files=[str(x.text or '').strip() for x in source] if source is not None else []
  print('  ACTUAL_DATAFILES_N:',len(files))
  print('  ACTUAL_DATAFILE_EXAMPLE:',files[0] if files else 'MISSING')
  varparent=next((x for x in st if x.tag.split('}')[-1]=='datavars'),None)
  mapping=[str(x.text or '').strip() for x in varparent] if varparent is not None else []
  for item in mapping[:35]:
   print('  SOURCE_TO_MODEL_VAR:',item)
   bits=item.split()
   if bits:available.add(bits[0])
  print('  ACTUAL_MAP_SOURCE_FIELDS:',sorted(available))
 print('STAGE81_MET_FIELDS:',','.join(MET))
 print('DIRECT_COPY_OF_STAGE81_STREAMSTEMPLATE: NOT ALLOWED; needs real <file>/<stream_info> XML plus valid mesh/domain and mappings.')
 print('FINAL_INPUT_STREAM_MAPPING: NOT CONFIGURED; candidate must be separately generated and previewed for CA-TP4.')
 print('REF case CO2/FATES settings and grid are EUROPEAN ONLY; never transplant site-specific years or landcover.')

def selftest():
 root=ET.fromstring("<file><stream_info name='test'><taxmode>cycle</taxmode><datavars><var>SHUM Sa_shum</var></datavars></stream_info></file>")
 n=list(root.iter('stream_info'))[0]
 assert xml_child_text(n,'taxmode')=='cycle'
 assert xml_child_text(n,'datavars').split()==['SHUM','Sa_shum']
 assert len(MET)==7 and VAR=='TA_PI_F_1_1_1'
 print('SELF-TEST PASS: active stream_info XML parser, CA-TP4 sensor identifier, 7 forcing variables')

def main():
 p=argparse.ArgumentParser(description=__doc__)
 x=p.add_mutually_exclusive_group(required=True)
 x.add_argument('--self-test',action='store_true')
 x.add_argument('--check',action='store_true')
 p.add_argument('--reference-case',type=Path,default=CASE)
 args=p.parse_args()
 if args.self_test:selftest();return
 inspect_base()
 inspect_stage81()
 inspect_raw_clock()
 inspect_reference(args.reference_case.resolve(strict=True))
 print('=== CA-TP4 FIRST AD5 SMOKE GATE ===')
 print('ZBOT SOURCE: 28m BASE CANDIDATE ONLY; TA_F sensor crosswalk not verified; PROVISIONAL_OR_HOLD decision required.')
 print('DATM CLOCK: midpoint/local-to-UTC semantics NOT verified. No blind automatic timestamp shift.')
 print('DATM STREAM: REFERENCE FORMAT RECOGNIZED, but CA-TP4 effective stream NOT built.')
 print('PFT / SOIL / SURFACE: separate site-specific FATES fixed-biogeography/no-competition case checks still required.')
 print('AD5 JOB / AD400 / NORMAL400: NOT STARTED.')
 print('READ-ONLY CHECK COMPLETE. NO CASE, NC, SURFACE, OR SLURM CHANGES.')

if __name__=='__main__':main()
