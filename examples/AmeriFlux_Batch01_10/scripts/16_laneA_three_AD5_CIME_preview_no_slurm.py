#!/usr/bin/env python3
"""Stage16: BR-Ma2, CA-Ca3, CA-LP1 FATES FIXNC AD5 case previews, NO SLURM.
Reuse existing Stage14 UTC meteorology + Stage15 isolated idealized point
forest surfaces. Each --stage handles ONE site and writes a one-time attempt
record before CIME mutation; never rerun a failed stage over a partial case.
--check audits all 3 read-only. --self-test needs no files.
US-Bar remains held pending its ~3% unclassified PFT fraction.

CO2: global-background NOAA 2026-10 annual initial-forcing-year values,
BR-Ma2 1999 367.79ppm, CA-Ca3 2001 370.57ppm, CA-LP1 2007 382.90ppm.
https://gml.noaa.gov/webdata/ccgg/trends/co2/co2_annmean_gl.csv
These values are global annual means, not site observations. The fixed-PFT
100% NATVEG surfaces and static TA_F-height ZBOT are TECHNICAL PROXIES,
NOT measurements of groundcover/sensor crosswalk. No model is submitted.
"""
from __future__ import annotations
import argparse,hashlib,importlib.util,json,subprocess,xml.etree.ElementTree as ET
from datetime import datetime,timezone
from pathlib import Path
import numpy as np
from netCDF4 import Dataset

ROOT=Path("/iridisfs/scratch/ly3n24/CLM_FATES")
CTSM=ROOT/"CTSM"
OUT=Path("/scratch/ly3n24/CTSM_FATES_OUTPUTS")
PROJ=ROOT/"experiments/NonCompetitionObserved22/AmeriFlux_Batch01_10"
S14=ROOT/"experiments/AmeriFlux_MultiSite_10/reports/stage14_LaneA_UTC_20261025T083517624796820Z"
S15=ROOT/"experiments/AmeriFlux_MultiSite_10/reports/stage15_LaneA_SURF_20261025T084151593400561Z"
SOURCE=ROOT/"cases/CA-TP4_AMF_FIXNC_AD400_UTC_V2_AD5"
S12=PROJ/"CA-TP4/stage12_CA_TP4_UTC_V2_AD5_PREVIEW_ATTEMPT.json"
HELPER=Path(__file__).resolve().with_name("08_CA_TP4_create_AD5_CIME_case_preview_no_slurm.py")
HELPER_BLOB="38cb1acbfd6502b3a9d49b5249bf7e9c006d1528"
EXE=OUT/"GF-Guy_FATES_SURF2000_CO2405_1PT/bld/cesm.exe"
ACK="CREATE_ONE_LANEA_AD5_CASE_PREVIEW_NO_SLURM"
STATE_DIR=PROJ/"LaneA_Stage16_CIME_preview"
SITES={"BR-Ma2":(1999,2016,367.79,1,51.1),
       "CA-Ca3":(2001,2024,370.57,2,12.0),
       "CA-LP1":(2007,2024,382.90,2,26.0)}
FIELDS={"PRECTmms":"Faxa_precn","FSDS":"Faxa_swdn","ZBOT":"Sa_z",
        "TBOT":"Sa_tbot","WIND":"Sa_wind","QBOT":"Sa_shum",
        "PSRF":"Sa_pbot","FLDS":"Faxa_lwdn"}

def fail(reason):raise RuntimeError(str(reason))
def digest(p):
 h=hashlib.sha256()
 with p.open("rb") as fd:
  for b in iter(lambda:fd.read(1048576),b""):h.update(b)
 return h.hexdigest()
def load(p):
 if not p.is_file():fail("Missing scientific manifest "+str(p))
 return json.loads(p.read_text(encoding="utf8"))
def proc(command,cwd=None,timeout=180):
 p=subprocess.run([str(x) for x in command],cwd=cwd,text=True,
                  capture_output=True,timeout=timeout,check=False)
 if p.returncode:fail("CIME error %d %s\nOUT %s\nERR %s"%
                      (p.returncode,command,p.stdout[-2200:],p.stderr[-2200:]))
 return p.stdout.strip()
def xmlq(case,k):return proc([case/"xmlquery",k,"--value"],cwd=case,timeout=90)
def xmlc(case,k,val):proc([case/"xmlchange",f"{k}={val}"],cwd=case,timeout=90)
def identity(site):
 name=f"{site}_AMF_FIXNC_AD400_UTC_AD5"
 return name,ROOT/"cases"/name,OUT/name/"run",OUT/"archive"/name,STATE_DIR/f"{site}_attempt.json"
def unused(site):
 t=identity(site)
 for p in t[1:]:
  if p.exists() or p.is_symlink():fail("Never overwrite existing/partial CIME state: "+str(p))
 return t

def helper():
 if not HELPER.is_file():fail("Pinned Stage08 build helper missing")
 data=HELPER.read_bytes()
 b=hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()
 if b!=HELPER_BLOB:fail("Stage08 helper hash mismatch")
 spec=importlib.util.spec_from_file_location("stage16_fates_helper",HELPER)
 m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
 m.overlay_test()
 return m

def template():
 z=load(S12)
 if (z.get("state")!="PREVIEW_VERIFIED_NOT_SUBMITTED" or
     z.get("model_jobs_submitted") is not False or
     z.get("ready_to_submit_AD5") is not False):fail("Stage12 original case is not completed/unsubmitted")
 for field,name in (("generated_lnd_in_sha256","lnd_in"),
                    ("generated_datm_stream_sha256","datm.streams.xml")):
  if digest(SOURCE/"CaseDocs"/name)!=z[field]:fail("Stage12 original CaseDocs changed")
 if (SOURCE/"env_case.xml").read_bytes()!=(SOURCE/"LockedFiles/env_case.xml").read_bytes():
  fail("Source CIME env_case lock differs")
 if xmlq(SOURCE,"BUILD_COMPLETE").lower()!="true" or xmlq(SOURCE,"EXEROOT")!=str(EXE.parent):
  fail("Original FATES AD5 case binary not usable")
 if not EXE.is_file():fail("CIME built cesm.exe missing")
 print("REFERENCE PASS: proven CA-TP4 UTC-V2 fixed FATES AD CIME executable, unchanged")
 return z

def receipts():
 a=load(S14/"manifest.json");b=load(S15/"manifest.json")
 if (a.get("stage")!=14 or len(a.get("sites",[]))!=4 or
     a.get("model_case_created") is not False or a.get("slurm_submitted") is not False):
  fail("Original Stage14 input status changed")
 if (b.get("stage")!=15 or b.get("source_stage14_manifest_sha256")!=digest(S14/"manifest.json") or
     b.get("model_cases_created") is not False or b.get("slurm_submitted") is not False or
     b.get("US-Bar")!="HOLD_UNCLASSIFIED_PFT_SHARE_NOT_ASSIGNED"):
  fail("Original Stage15 input/US-Bar PFT HOLD changed")
 m={r["site"]:r for r in a["sites"]}
 s={r["site"]:r for r in b["sites"]}
 if not set(SITES).issubset(m) or set(s)!=set(SITES):
  fail("Missing three desired UTC/PFT site evidence sources")
 return m,s

def source_site(site,mrec,srec):
 first,last,co2,pft,height=SITES[site]
 metfile=S14/site/"manifest.json"
 surfacefile=S15/site/"manifest.json"
 if (Path(mrec["manifest"])!=metfile or digest(metfile)!=mrec["manifest_sha256"] or
     Path(srec["manifest"])!=surfacefile or digest(surfacefile)!=srec["sha256"]):
  fail(site+": independent source site receipt moved/changed")
 met=load(metfile);land=load(surfacefile)
 if (met["site"]!=site or met["start_year"]!=first or met["last_year"]!=last or
     len(met["files"])!=last-first+1 or met.get("source_TA_F_sensor_height_verified") is not False or
     abs(float(met["ZBOT_STATIC_M_PROVISIONAL"])-height)>1e-4 or
     met.get("slurm_submitted") is not False):fail(site+": source UTC forcing/height policy drift")
 surface=Path(land["new_surface"])
 if (land["site"]!=site or digest(surface)!=land["new_surface_sha256"] or
     land["source_fates_pft"]["FATES_PFT_SLOT"]!=pft or
     land.get("site_soil_measured") is not False or land.get("model_case_created") is not False):
  fail(site+": PFT science or source surface changed")
 allfiles=[]
 for year,entry in zip(range(first,last+1),met["files"]):
  nc=S14/site/"yearly"/f"{year}.nc"
  if entry["year"]!=year or Path(entry["path"])!=nc or digest(nc)!=entry["sha256"]:
   fail(site+f": UTC year checksum not verified: {year}")
  allfiles.append(nc)
 with Dataset(allfiles[0]) as nc,Dataset(surface) as ds:
  t=nc.variables["time"]
  if len(t)!=17520 or t.calendar!="noleap" or not np.allclose(
     t[[0,1,-1]],[1/96,1/48+1/96,17519/48+1/96],atol=1e-10,rtol=0):
   fail(site+": midpoint UTC forcing data mismatch")
  for k in ("LATIXY","LONGXY"):
   if not np.allclose(nc.variables[k][:],ds.variables[k][:],atol=1e-5,rtol=0):
    fail(site+": UTC forcing/surface spatial coordinate mismatch "+k)
  if not np.allclose(nc.variables["ZBOT"][[0,123,17519],0,0],height,atol=1e-6):
   fail(site+": technical sensor ZBOT changed")
  host_idx=land["source_fates_pft"]["CLM_HOST_NATPFT_INDEX"]
  group=np.ma.filled(ds.variables["PCT_NAT_PFT"][:],np.nan).ravel()
  want=np.zeros(len(group));want[host_idx]=100.
  if not np.allclose(group,want,rtol=0,atol=1e-5) or \
      abs(float(np.asarray(ds.variables["PCT_NATVEG"][:]).ravel()[0])-100)>1e-3:
   fail(site+": model site PFT group not correct")
 print("SOURCE SITE PASS:",site,"UTC YEARS",len(allfiles),
       "FIXED CO2",co2,"FATES PFT SLOT",pft,"ZBOT PROXY",height,"m",flush=True)
 return allfiles,surface,met

def stream_user(m,files,first,last):
 original=(SOURCE/"user_nl_datm_streams").read_text(encoding="utf8")
 sections=m.stream_assignments(original);prefix="CLM_USRDAT.UNSET:"
 repl={"year_first":str(first),"year_last":str(last),"year_align":str(first),
       "offset":"0","taxmode":"cycle","tintalgo":"linear",
       "mapalgo":"none","meshfile":"none",
       "datafiles":",".join(str(p) for p in files)}
 for key in (*repl,"datavars"):
  count=len(sections.get(prefix+key,[]))
  if count!=1 and not (key=="offset" and count==0):
   fail("Source CDEPS stream missing/duplicate "+key)
 changed=original
 loc=[(sections[prefix+k][0][0],sections[prefix+k][0][1],
       prefix+k+" = "+value+"\n") for k,value in repl.items() if sections.get(prefix+k)]
 for i,j,v in sorted(loc,reverse=True):changed=changed[:i]+v+changed[j:]
 if not sections.get(prefix+"offset"):
  changed=changed.rstrip()+"\n"+prefix+"offset = 0\n"
 after=m.stream_assignments(changed)
 if any(len(after.get(prefix+k,[]))!=1 for k in repl):
  fail("Effective site DATM override validation failed")
 if any(str(p) not in after[prefix+"datafiles"][0][2] for p in files):
  fail("New site CDEPS output datafiles incomplete")
 if "CA-TP4" in changed or "CH-Dav" in changed:
  fail("Unexpected inherited site-specific DATM path")
 return changed

def land_user(m,surface):
 base=(SOURCE/"user_nl_clm").read_text(encoding="utf8")
 if m.nml(base,"finidat") not in (None,"") or m.nml(base,"reseed_dead_plants") is not None:
  fail("Source AD namelist unexpectedly has restart/reseed")
 d={"fsurdat":"'"+str(surface)+"'",
    "use_fates":".true.","use_fates_sp":".false.",
    "use_fates_fixed_biogeog":".true.","use_fates_nocomp":".true.",
    "spinup_state":"2"}
 for k,v in d.items():base=m.replace_nml(base,k,v)
 if "CA-TP4" in base or "CH-Dav" in base:fail("Old tower-specific source leaked into land namelist")
 return base

def configuration(m,site,run,arch):
 first,last,co2,pft,height=SITES[site]
 z=m.xml_settings()
 z.update({"RUNDIR":str(run),"DOUT_S_ROOT":str(arch),
           "RUN_TYPE":"startup","RUN_STARTDATE":f"{first}-01-01",
           "DATM_YR_START":str(first),"DATM_YR_END":str(last),
           "DATM_YR_ALIGN":str(first),
           "CLM_CO2_TYPE":"constant","DATM_CO2_TSERIES":"none",
           "CCSM_CO2_PPMV":str(co2),
           "STOP_N":"5","REST_N":"5","RESUBMIT":"0"})
 return z

def canonical(e):
 return (e.tag,tuple(sorted(e.attrib.items())),(e.text or "").strip(),
         tuple(canonical(v) for v in e))
def generated(site,case,files,surface,m,settings):
 first,last,co2,pft,height=SITES[site]
 new=ET.parse(case/"CaseDocs/datm.streams.xml").getroot()
 old=ET.parse(SOURCE/"CaseDocs/datm.streams.xml").getroot()
 a={e.attrib.get("name"):e for e in new.iter("stream_info")}
 b={e.attrib.get("name"):e for e in old.iter("stream_info")}
 if set(a)!=set(b) or "CLM_USRDAT.UNSET" not in a:
  fail(site+": CDEPS stream membership changed")
 for k in set(a)-{"CLM_USRDAT.UNSET"}:
  if canonical(a[k])!=canonical(b[k]):
   fail(site+": shared ancillary stream unexpectedly modified "+str(k))
 main=a["CLM_USRDAT.UNSET"]
 for k,v in (("year_first",str(first)),("year_last",str(last)),
             ("year_align",str(first)),("offset","0"),("taxmode","cycle"),
             ("tintalgo","linear"),("mapalgo","none"),("meshfile","none")):
  e=main.find(k)
  if e is None or (e.text or "").strip()!=v:
   fail(site+": generated CDEPS meteorological stream wrong "+k)
 fields={}
 for e in main.find("datavars"):
  pair=(e.text or "").split()
  if len(pair)!=2 or pair[0] in fields:fail(site+": generated DATM mapping broken")
  fields[pair[0]]=pair[1]
 if any(fields.get(k)!=v for k,v in FIELDS.items()):
  fail(site+": generated DATM met mapping not 8 correct vars")
 if [Path((x.text or "").strip()) for x in main.find("datafiles")]!=files:
  fail(site+": generated CDEPS forcing not exact Stage14 site years")
 t=(case/"CaseDocs/lnd_in").read_text(encoding="utf8")
 for k,v in (("fsurdat",str(surface)),("spinup_state","2"),
             ("use_fates",".true."),("use_fates_sp",".false."),
             ("use_fates_fixed_biogeog",".true."),("use_fates_nocomp",".true."),
             ("use_cn",".false.")):
  if m.nml(t,k)!=v:fail(site+": generated FATES AD land setting bad "+k)
 if m.nml(t,"finidat") not in (None,"") or m.nml(t,"reseed_dead_plants") is not None:
  fail(site+": FATES AD5 non-coldstart input")
 landco2=m.nml(t,"co2_ppmv")
 if landco2 is not None and abs(float(landco2)-co2)>0.03:
  fail(site+": generated CLM constant CO2 inconsistent")
 for k,val in settings.items():
  if xmlq(case,k).lower()!=str(val).lower():
   fail(site+": generated CIME setting mismatches "+k)
 return {"lnd_in_sha256":digest(case/"CaseDocs/lnd_in"),
         "datm_stream_sha256":digest(case/"CaseDocs/datm.streams.xml")}

def stage(site,m,files,surface,met):
 name,case,run,arch,state=unused(site)
 newstream=stream_user(m,files,*SITES[site][:2])
 newland=land_user(m,surface)
 opts=configuration(m,site,run,arch)
 STATE_DIR.mkdir(parents=True,exist_ok=True)
 with state.open("x",encoding="utf8") as f:
  json.dump({"stage":16,"site":site,"state":"ATTEMPTED_UNCERTAIN",
    "source_case":str(SOURCE),"target_case":str(case),
    "forcing_receipt_sha256":digest(S14/site/"manifest.json"),
    "surface_receipt_sha256":digest(S15/site/"manifest.json"),
    "model_jobs_submitted":False,
    "created_utc":datetime.now(timezone.utc).isoformat()},f,indent=2)
  f.write("\n")
 print("ONE-TIME STAGE16 ATTEMPT:",state,flush=True)
 proc([CTSM/"cime/scripts/create_clone","--case",case,
       "--clone",SOURCE,"--keepexe"],cwd=CTSM/"cime/scripts",timeout=420)
 if not case.is_dir() or xmlq(case,"CASE")!=name or \
     xmlq(case,"EXEROOT")!=str(EXE.parent) or xmlq(case,"BUILD_COMPLETE").lower()!="true":
  fail(site+": new FATES CIME case clone/binary failed")
 for k,v in opts.items():xmlc(case,k,v)
 (case/"user_nl_datm_streams").write_text(newstream,encoding="utf8")
 (case/"user_nl_clm").write_text(newland,encoding="utf8")
 if not (case/".case.run").is_file():
  proc([case/"case.setup"],cwd=case,timeout=300)
 a=case/"env_case.xml";b=case/"LockedFiles/env_case.xml"
 if not b.is_file() or a.read_bytes()!=b.read_bytes():
  fail(site+": CIME lock already inconsistent before preview")
 original=a.read_bytes()
 x={e.attrib.get("id"):e.attrib.get("value") for e in ET.parse(b).iter("entry")}
 if x.get("COMP_ROOT_DIR_LND")!="$SRCROOT" or \
     Path(xmlq(case,"COMP_ROOT_DIR_LND")).resolve()!=CTSM.resolve():
  fail(site+": CIME private build-namelist overlay precondition invalid")
 try:
  xmlc(case,"COMP_ROOT_DIR_LND",str(m.OVERLAY))
  proc([case/"preview_namelists"],cwd=case,timeout=600)
 finally:
  xmlc(case,"COMP_ROOT_DIR_LND","$SRCROOT")
  if a.read_bytes()!=original or b.read_bytes()!=original:
   fail(site+": STOP: CIME env_case.xml lock not restored")
 print("PRIVATE FATES PREVIEW PASS / CIME LOCK RESTORED",site)
 hashes=generated(site,case,files,surface,m,opts)
 result=load(state)
 result.update({"state":"PREVIEW_VERIFIED_NOT_SUBMITTED",
    "model_case_created":True,"model_jobs_submitted":False,
    "ready_to_submit_AD5":False,
    "source_stage14_sha256":digest(S14/"manifest.json"),
    "source_stage15_sha256":digest(S15/"manifest.json"),
    "source_surface_sha256":digest(surface),
    "first_met_year":SITES[site][0],"last_met_year":SITES[site][1],
    "fixed_global_CO2_ppm":SITES[site][2],
    "ZBOT_TA_F_sensor_crosswalk_verified":False,
    "original_FLUXNET_native_timestamp_start_verified":False,
    "PFT_percent_observed_groundcover":False,"soil_site_observed":False,
    "coupler_geometry_and_clock_verified":False,
    "AD395_or_Normal400_submitted":False,
    "result":hashes,
    "validated_utc":datetime.now(timezone.utc).isoformat()})
 state.write_text(json.dumps(result,indent=2)+"\n",encoding="utf8")
 print("STAGE16 SUCCESS",site,"AD5 CIME CASE PREVIEW VERIFIED; NO SLURM")
 print("CASE",case,"CO2",SITES[site][2],
       "STOP_N=5 REST_N=5 RESUBMIT=0 FATES spinup_state=2")

def selftest():
 assert set(SITES)=={"BR-Ma2","CA-Ca3","CA-LP1"}
 assert sum(last-first+1 for first,last,*_ in SITES.values())==60
 assert len(FIELDS)==8
 print("SELF-TEST PASS: 3 independent UTC AD5 cases, 60 forcing years, site global-CO2 baselines, US-Bar excluded")

def main():
 a=argparse.ArgumentParser(description=__doc__)
 g=a.add_mutually_exclusive_group(required=True)
 g.add_argument("--self-test",action="store_true")
 g.add_argument("--check",action="store_true")
 g.add_argument("--stage",action="store_true")
 a.add_argument("--site",choices=[*SITES,"all"],default="all")
 a.add_argument("--confirm")
 v=a.parse_args()
 if v.self_test:selftest();return
 if v.stage and (v.site=="all" or v.confirm!=ACK):
  a.error("--stage needs a single --site and --confirm "+ACK)
 if v.check and (v.site!="all" or v.confirm):
  a.error("--check must audit all 3 with no confirm")
 m=helper()
 template()
 met,surf=receipts()
 for site in ([v.site] if v.stage else SITES):
  files,land,source=source_site(site,met[site],surf[site])
  unused(site)
  stream_user(m,files,*SITES[site][:2])
  land_user(m,land)
  print("PREFLIGHT PASS",site,"CASE",identity(site)[1],flush=True)
  if v.stage:stage(site,m,files,land,source)
 if v.check:print("STAGE16 READ-ONLY CHECK PASS: three sites ready for independent AD5 CIME previews; NO MODEL OR SLURM")

if __name__=="__main__":main()
