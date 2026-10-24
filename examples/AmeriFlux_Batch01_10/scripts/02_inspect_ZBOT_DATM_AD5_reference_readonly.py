#!/usr/bin/env python3
"""Read-only AmeriFlux AD400/Normal400 Stage02:
1) 10-site real Stage31 BASE TA-height candidate scope, especially CA-TP4;
2) real, existing European FIXNC AD case's CIME/DATM/FATES generated files;
3) compare the Stage81 file metadata/field list for new AmeriFlux cases.
NEVER decide sensor crosswalk, modify case/forcing/surface, or submit jobs.
"""
from __future__ import annotations
import argparse,hashlib,json,re,xml.etree.ElementTree as ET
from pathlib import Path

ROOT=Path('/iridisfs/scratch/ly3n24/CLM_FATES')
AMF=ROOT/'experiments/AmeriFlux_MultiSite_10'
REPORT=AMF/'reports/stage31_provisional_ZBOT_scenarios_20261022T022341481986Z'
STAGE81=AMF/'reports/stage81_DATM_technical_20261024T162235Z/manifest.json'
STAGE82=AMF/'reports/stage82_DATM_case_integration_preflight_20261024T231124502670Z/manifest.json'
DEFAULT_CASE=ROOT/'cases/CH-Dav_B01_FIXNC_AD400'
EXPECTED={'BR-Ma2','CA-Ca3','CA-Cbo','CA-LP1','CA-Man','CA-TP1','CA-TP3','CA-TP4','US-Aud','US-Bar'}
CIME_KEYS={'DATM_MODE','DATM_YR_START','DATM_YR_END','DATM_YR_ALIGN',
           'CALENDAR','ATM_NCPL','RUN_STARTDATE','RUN_TYPE','RUN_REFDATE',
           'STOP_OPTION','STOP_N','REST_N','RESUBMIT','CLM_ACCELERATED_SPINUP',
           'COMPSET','DIN_LOC_ROOT'}
LND_KEYS={'use_fates','use_fates_sp','use_fates_nocomp','use_fates_fixed_biogeog',
          'spinup_state','fates_paramfile','fates_hlm_pft_map','fsurdat','finidat'}
DATM_KEYS={'streams','taxmode','tintalgo','mapalgo','year_first','year_last',
           'year_align','fields','offset','datafiles','datafilepath','domainfile'}
MAX_READ=2_000_000

def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()

def textread(p):
 if not p.is_file():return None,'ABSENT'
 if p.is_symlink():return None,'SYMLINK_NOT_FOLLOWED'
 if p.stat().st_size>MAX_READ:return None,'TOO_LARGE'
 return p.read_text(encoding='utf-8',errors='replace'),'OK'

def xmlvars(root,keyset):
 out={}
 for ent in root.iter():
  if ent.tag.split('}')[-1]=='entry':
   name=ent.attrib.get('id')
   if name in keyset:out[name]=ent.attrib.get('value','')
 return out

def nml(raw,keys):
 out={}
 for k in sorted(keys):
  hits=re.findall(r'(?im)^\s*'+re.escape(k)+r'\s*=\s*([^\n!]+)',raw)
  if hits:out[k]=hits[-1].strip()
 return out

def relevant(raw,keys,max_lines=30):
 found=[]
 for ln in raw.splitlines():
  s=ln.strip()
  if not s or s.startswith(('#','!')):continue
  if any(b in s.lower() for b in ('password','access_token','secret','api_key','private_key')):continue
  if any(k in s.lower() for k in keys):
   found.append(s[:240])
   if len(found)>=max_lines:break
 return found

def print_doc(path,keywords,maxlines):
 raw,status=textread(path)
 print('DOCUMENT:',str(path),'STATUS:',status)
 if raw is None:return
 print('  SHA256:',sha(path),'BYTES:',path.stat().st_size)
 if path.name=='lnd_in':
  print('  FATES_LND_KEYS:',json.dumps(nml(raw,LND_KEYS),sort_keys=True))
 elif path.name=='datm_in':
  print('  DATM_NML_KEYS:',json.dumps(nml(raw,DATM_KEYS),sort_keys=True))
 else:
  try:
   node=ET.fromstring(raw)
   print('  XML_ROOT:',node.tag)
  except ET.ParseError as exc:
   print('  XML_PARSE_STATUS: NOT_XML',str(exc)[:120])
 for line in relevant(raw,keywords,max_lines=maxlines):
  print('  EVIDENCE:',line)

def zbot():
 meta=REPORT/'01_provisional_site_height_policies.json'
 if not meta.is_file():raise RuntimeError('Pinned Stage31 height report missing '+str(meta))
 d=json.loads(meta.read_text(encoding='utf-8'))
 if d.get('method')!='AmeriFlux_STAGE31_BASE_STATIC_DYNAMIC_POLICY_SCENARIOS':
  raise RuntimeError('Stage31 source method changed')
 pol=d.get('provisional_sensor_policy')
 if not isinstance(pol,dict) or set(pol)!=(EXPECTED-{'CA-Cbo','CA-Man'}):
  raise RuntimeError('Stage31 must have exactly 8 provisional unapproved TA crosswalks, not 10 approvals')
 print('=== ORIGINAL BASE TA SENSOR HEIGHT CANDIDATES (NOT VERIFIED TA_F) ===')
 print('STAGE31_SHA256:',sha(meta))
 for site in sorted(EXPECTED):
  p=pol.get(site)
  if p is None:
   print(site,'MULTILAYER: HOLD; no numeric ZBOT assigned')
   continue
  events=p.get('dated_events',[])
  print(site,'MODE:',p['candidate_ZBOT_mode'],
        'BASE_VAR:',p['variable_BASE'],'BASELINE_M:',p['baseline_m'],
        'EVENTS:',len(events),'HALFHOURS_UNCERTAIN:',p.get('scenario_difference_halfhours'),
        'CROSSWALK:',p['FLUXNET_TA_F_sensor_crosswalk'])
  if site=='CA-TP4':
   for event in events:
    print(' CA-TP4 EVENT:',json.dumps(event,ensure_ascii=False,sort_keys=True))
 if pol['CA-TP4']['candidate_ZBOT_mode']!='STATIC':
  raise RuntimeError('CA-TP4 is not a static candidate in saved Stage31 snapshot')
 return pol

def case_inspect(path):
 case=path.expanduser().resolve(strict=True)
 if not case.is_dir() or not (case/'env_run.xml').is_file():
  raise RuntimeError('Reference must be an actual existing CIME case folder with env_run.xml')
 print('=== REAL EUROPEAN FIXNC REFERENCE CIME CASE (READ ONLY) ===')
 print('CASE:',case)
 cfg={}
 for name in ('env_run.xml','env_case.xml','env_build.xml'):
  f=case/name
  raw,stat=textread(f)
  if raw is not None:
   try:cfg.update(xmlvars(ET.fromstring(raw),CIME_KEYS))
   except ET.ParseError:print('XML_WARNING',name,'cannot parse')
 print('CIME_SETTINGS:',json.dumps(cfg,sort_keys=True))
 doc=case/'CaseDocs'
 print('CASEDOCS_PRESENT:',doc.is_dir())
 paths=[doc/'datm_in',doc/'lnd_in',case/'user_nl_datm',case/'user_nl_clm']
 if doc.is_dir():
  paths+=sorted(doc.glob('datm.streams*'))[:12]
  paths+=sorted(doc.glob('*domain*'))[:8]
 for p in paths:
  print_doc(p,('stream','year_','datafile','domain','taxmode','tintalgo','field','zbot','shum','rh','fl','wind','fates','spinup','fsurdat'),28 if p.name.startswith('datm.stream') else 16)
 good_streams=[p for p in paths if p.name.startswith('datm.streams') and p.is_file()]
 if not good_streams:
  print('BLOCKER: no CaseDocs datm streams found; use another complete reference')
 if not (doc/'datm_in').is_file() or not (doc/'lnd_in').is_file():
  print('BLOCKER: generated DATM/LND input not both available')
 return len(good_streams)>0

def stage81_fields():
 m=json.loads(STAGE81.read_text(encoding='utf-8'))
 p=json.loads(STAGE82.read_text(encoding='utf-8'))
 if m.get('all_annual_netcdf_files')!=213 or p.get('verified_annual_files_sha256')!=213:
  raise RuntimeError('Stage81/82 successful data counts drift')
 if sha(STAGE81)!=p.get('input_stage81_manifest_sha256'):
  raise RuntimeError('Stage82 provenance SHA no longer matches Stage81')
 print('=== EXISTING AMERIFLUX MODEL INPUT MET DATA ===')
 print('SITE_COUNT:',len(m['sites']),'YEARLY_NETCDF:',m['all_annual_netcdf_files'])
 print('STAGE81_FIELDS:',','.join(sorted(m.get('input_units',{}))))
 print('TIME_AXIS:',m.get('time_axis'))
 print('MET_RELEASE:',m.get('model_activation'))
 print('REQUIRE: real target case DATM stream must map SHUM correctly and include valid domain')
 print('REQUIRE: evidence for station local-standard clock offset + half-hour interval centering')
 print('REQUIRE: source height scientifically chosen before implementing ZBOT')

def self_test():
 assert len(EXPECTED)==10
 assert len(EXPECTED-{'CA-Cbo','CA-Man'})==8
 assert nml('use_fates_nocomp=.true.\n',LND_KEYS)['use_fates_nocomp']=='.true.'
 assert xmlvars(ET.fromstring('<config><entry id="DATM_MODE" value="1PT"/></config>'),CIME_KEYS)['DATM_MODE']=='1PT'
 print('SELF-TEST PASS: exact 8+2 ZBOT census, namelist, XML parsing')

def main():
 p=argparse.ArgumentParser(description=__doc__)
 m=p.add_mutually_exclusive_group(required=True)
 m.add_argument('--self-test',action='store_true')
 m.add_argument('--check',action='store_true')
 p.add_argument('--reference-case',type=Path,default=DEFAULT_CASE)
 args=p.parse_args()
 if args.self_test:self_test();return
 zbot()
 stage81_fields()
 result=case_inspect(args.reference_case)
 print('=== MODEL RUN DECISION ===')
 print('REFERENCE_STREAM_FILES:', 'FOUND' if result else 'NOT_FOUND')
 print('SCIENTIFIC ZBOT/HEIGHT: HOLD (CA-TP4 is static only, TA_F crosswalk not verified)')
 print('START AD400/NORMAL400: NO; first validate DATM timing/streams and run one AD5 smoke')
 print('EXISTING CASES/NETCDF/SURFACES/SLURM: ALL UNCHANGED (READ ONLY)')

if __name__=='__main__':main()
