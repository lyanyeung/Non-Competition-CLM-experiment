#!/usr/bin/env python3
"""Stage30: independent site-specific AD5 PREVIEW for four forest PFT scenario
candidates from Stage29. Never submit Slurm, never overwrite site source cases.
The closed 100% PFT vectors are unapproved sensitivities from reviewed ICOS
observations, NOT measured complete inventories. Before any real AD400 submission
perform forcing QA and scientific review. Use Stage30 proven private overlay.
"""

from __future__ import annotations
import argparse,hashlib,json,os,re,subprocess
import xml.etree.ElementTree as ET
from pathlib import Path
from datetime import datetime,timezone
import numpy as np
from netCDF4 import Dataset

BASE=Path("/iridisfs/scratch/ly3n24/CLM_FATES")
CTSM=BASE/"CTSM"
ROOT=BASE/"experiments/NonCompetitionObserved22/Batch02_10"
OUTPUTS=Path("/scratch/ly3n24/CTSM_FATES_OUTPUTS")
OVERLAY=ROOT/"_private_ctsm_FATES_AD5_namelist_overlay_v1"
SHARED_BLOB="698f2396aba8e11cbbbdd58c74ad221e6b7e7038"
PARAM=CTSM/"src/fates/parameter_files/fates_params_default.json"
PARAM_SHA="0819f8fddcb3566f6209f72bb1159a3161d03c8225a1464727b1d2b21aec6c04"
ATTEMPTS=ROOT/"stage30_four_forest_AD5_preview"
ACK="PREPARE_FOUR_BATCH02_FOREST_AD5_PREVIEWS_NO_SLURM"
BGC_OPTS="--bgc fates --no-megan --no-drydep --no-fire_emis"
OLD_GUARD="if ( &value_is_true($nl_flags->{'use_cn'}) ) {"
NEW_GUARD="if ( &value_is_true($nl_flags->{'use_cn'}) || &value_is_true($nl_flags->{'use_fates'}) ) {"
OLD_RESEED='if ( $nl_flags->{$var} ne "off" ) {'
NEW_RESEED='if ( $nl_flags->{$var} ne "off" && &value_is_true($nl_flags->{\'use_cn\'}) ) {'
SITES={
 "DK-Sor":{"source":"DK-Sor_FATES_SPINUP500","case":"DK-Sor_B02_FIXNC_FOREST_PROXY_AD5",
    "pft":{1:10,3:10,7:80},"scenario":"MID_SPLIT_TRIAL",
    "science_hold":"ENF_DNF_20_COMBINED_UNRESOLVED_PROXY"},
 "FR-FBn":{"source":"FR-FBn_FATES_SPINUP500","case":"FR-FBn_B02_FIXNC_FOREST_PROXY_AD5",
    "pft":{1:75,5:25},"scenario":"OAK_UPPER_BOUND",
    "science_hold":"REMAINDER25_NOT_VERIFIED_ALL_EBF"},
 "BE-Bra":{"source":"BE-Bra_FATES_SPINUP500_11P","case":"BE-Bra_B02_FIXNC_FOREST_PROXY_AD5",
    "pft":{1:55,7:45},"scenario":"UNKNOWN22_TO_DBF_BOUND",
    "science_hold":"UNKNOWN22_ASSIGNED_TO_DBF_SENSITIVITY_ONLY"},
 "CH-Lae":{"source":"CH-Lae_FATES_SPINUP500_11P","case":"CH-Lae_B02_FIXNC_FOREST_PROXY_AD5",
    "pft":{1:12,7:88},"scenario":"UNKNOWN8_TO_DBF_BOUND",
    "science_hold":"UNKNOWN8_ASSIGNED_TO_DBF_SENSITIVITY_ONLY"},
}
FIELDS={"use_fates":".true.","use_fates_sp":".false.","use_fates_fixed_biogeog":".true.",
        "use_fates_nocomp":".true.","spinup_state":"2","finidat":""}
def stop(s):raise RuntimeError(str(s))
def call(cmd,cwd=None,timeout=180):
 p=subprocess.run([str(z) for z in cmd],cwd=cwd,text=True,capture_output=True,
                  check=False,timeout=timeout)
 if p.returncode:
  stop("CMD FAIL "+repr(list(map(str,cmd)))+" rc="+str(p.returncode)+
       "\n"+(p.stdout+"\n"+p.stderr)[-2200:])
 return p.stdout.strip()
def sha(p):
 h=hashlib.sha256()
 with p.open("rb") as f:
  for c in iter(lambda:f.read(1<<20),b""):h.update(c)
 return h.hexdigest()
def blob(b):return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()
def query(case,key):return call([case/"xmlquery",key,"--value"],cwd=case,timeout=90)
def change(case,key,v):return call([case/"xmlchange",key+"="+str(v)],cwd=case,timeout=90)
def field(t,k):
 a=re.findall(r"(?im)^\s*"+re.escape(k)+r"\s*=\s*([^\r\n!]*)",t)
 if len(a)>1:stop("Duplicate land namelist "+k)
 return a[0].strip().rstrip(",").strip("'\"").strip() if a else None
def setfield(t,k,v):
 field(t,k)
 pattern=r"(?im)^[ \t]*"+re.escape(k)+r"[ \t]*=[^\r\n]*$"
 replacement=k+" = "+v
 return re.sub(pattern,lambda _:replacement,t) if re.search(pattern,t) else t.rstrip()+"\n"+replacement+"\n"
def site_paths(site):
 item=SITES[site]
 name=item["case"]
 old=BASE/"cases"/item["source"]
 case=BASE/"cases"/name
 run=OUTPUTS/name/"run"
 arch=OUTPUTS/"archive"/name
 surf=ROOT/"stage29_remaining4_forest_PFT_proxy_v1"/site/("surfdata_"+site+"_B02_FOREST_PFT_proxy_v1.nc")
 receipt=surf.parent/"manifest.json"
 attempt=ATTEMPTS/(site+"_prepare_attempt.json")
 return old,case,run,arch,surf,receipt,attempt

def preload_manifests():
 # Stage29 manifest is input provenance; never trust a bare NetCDF without receipt.
 for site,item in SITES.items():
  old,case,run,arch,surf,receipt,attempt=site_paths(site)
  if not receipt.is_file() or not surf.is_file() or surf.is_symlink():
   stop(site+": Stage29 built surface and manifest required before Stage30")
  doc=json.loads(receipt.read_text(encoding="utf8"))
  if doc.get("PFT_scenario")!=item["scenario"] or doc.get("original_case")!=item["source"]:
   stop(site+": Stage29 source/scenario mismatch")
  if doc.get("science_gate")!=item["science_hold"]:
   stop(site+": Stage29 recorded science gate mismatch")
  expected=[0.]*15
  for k,v in item["pft"].items():expected[k]=float(v)
  if any(abs(float(x)-y)>1e-5 for x,y in zip(doc.get("PCT_NAT_PFT_15_HOST",[]),expected)) or len(doc.get("PCT_NAT_PFT_15_HOST",[]))!=15:
   stop(site+": Stage29 manifest PFT vector changed")
  item["candidate_sha"]=doc.get("candidate_sha256")
  if not isinstance(item["candidate_sha"],str) or len(item["candidate_sha"])!=64 or sha(surf)!=item["candidate_sha"]:
   stop(site+": candidate SHA mismatch")


def pftpoint(surf,pft):
 with Dataset(surf) as f:
  if f.variables["PCT_NAT_PFT"].size!=15:stop("Not a 15-HLM point surface")
  vv=np.asarray(f.variables["PCT_NAT_PFT"][:],dtype=float).ravel()
  a=np.zeros(15)
  for k,v in pft.items():a[k]=v
  if not np.allclose(vv,a,atol=1e-5):stop("Stage12 PFT fractions changed")
  if abs(float(np.asarray(f.variables["PCT_NATVEG"][:]).reshape(-1)[0])-100)>0.001:
   stop("Stage12 PCT_NATVEG not100")
  if abs(float(np.asarray(f.variables["PCT_CROP"][:]).reshape(-1)[0]))>0.001:
   stop("Stage12 PCT_CROP not0")
  lat=float(np.asarray(f.variables["LATIXY"][:]).ravel()[0])
  lon=float(np.asarray(f.variables["LONGXY"][:]).ravel()[0])%360
  if not (-90<=lat<=90 and 0<=lon<360):stop("Invalid site coords")
 return lat,lon
def distance(p,q):
 return max(abs(p[0]-q[0]),abs((p[1]-q[1]+180)%360-180))
def stream(case,site,point):
 p=case/"CaseDocs/datm.streams.xml"
 if not p.is_file():stop("CDEPS stream XML absent "+str(p))
 root=ET.parse(p).getroot()
 streams=[x for x in root.iter("stream_info") if x.attrib.get("name")=="CLM_USRDAT.UNSET"]
 if len(streams)!=1:stop("Not a unique source 1PT datm met stream")
 st=streams[0]
 read=lambda key:(st.find(key).text or "").strip()
 first=int(read("year_first"));last=int(read("year_last"))
 if first>last or read("taxmode")!="cycle" or read("offset")!="0" or int(read("year_align"))!=first:
  stop("Source year/time alignment incompatible with site 1PT")
 records=[Path((c.text or "").strip()) for c in st.find("datafiles")]
 if len(records)!=last-first+1:stop("Source year count inconsistent")
 provisional=0
 for year,file in zip(range(first,last+1),records):
  if not file.name.startswith(site+"_DATM_") or not file.name.endswith(".nc") or \
     not re.search(r"(?<!\d)"+str(year)+r"(?!\d)",file.stem):
   stop("Wrong original source forcing SITE/YEAR/NAME "+str(file))
  if not file.is_file() or file.stat().st_size==0:stop("Missing original forcing "+str(file))
  if "PROVISIONAL" in file.name or "provisional" in str(file).lower():provisional+=1
 # Read only the first yearly NC header/co-location, if available.
 with Dataset(records[0]) as f:
  if "LATIXY" in f.variables and "LONGXY" in f.variables:
   lp=(float(np.asarray(f.variables["LATIXY"][:]).ravel()[0]),
       float(np.asarray(f.variables["LONGXY"][:]).ravel()[0])%360)
   if distance(lp,point)>0.0001:
    stop("Met source and site surface coords differ")
 return {"first":first,"last":last,"files":records,"provisional_years":provisional,
         "stream_sha":sha(p)}
def overlay():
 shared=CTSM/"bld/CLMBuildNamelist.pm"
 if not shared.is_file() or blob(shared.read_bytes())!=SHARED_BLOB:
  stop("Original shared CTSM FATES file changed")
 if OVERLAY.is_symlink() or not (OVERLAY/"bld/CLMBuildNamelist.pm").is_file():
  stop("Proven private Batch02 AD buildnml overlay missing")
 if (OVERLAY/"bld/CLMBuildNamelist.pm").is_symlink():
  stop("Private CLMBuildNamelist must NOT point to shared file")
 original=shared.read_text()
 lo=original.index("sub setup_cmdl_spinup {")
 hi=original.index("sub setup_cmdl_simulation_year {",lo)
 section=original[lo:hi]
 if section.count(OLD_GUARD)!=1 or section.count(OLD_RESEED)!=1:
  stop("Shared buildnml signatures no longer pinned")
 expected=original[:lo]+section.replace(OLD_GUARD,NEW_GUARD,1).replace(OLD_RESEED,NEW_RESEED,1)+original[hi:]
 if (OVERLAY/"bld/CLMBuildNamelist.pm").read_text()!=expected:
  stop("Private AD FATES patch modified")
 if (OVERLAY/"bld/build-namelist").read_bytes()!=(CTSM/"bld/build-namelist").read_bytes():
  stop("Private buildnml launcher differs")
 print("FATES BATCH02 AD PRIVATE NAMELIST OVERLAY PASS")
def preflight(site,existing=False):
 item=SITES[site]
 old,case,run,arch,surf,receipt,attempt=site_paths(site)
 if not old.is_dir():stop(site+" old same-site case missing")
 if sha(PARAM)!=PARAM_SHA:stop("Original shared FATES PARAM changed")
 if not surf.is_file() or surf.is_symlink() or sha(surf)!=item["candidate_sha"]:
  stop(site+" verified Stage12 candidate SHA changed")
 if not receipt.is_file():stop(site+" Stage12 provenance manifest missing")
 doc=json.loads(receipt.read_text(encoding="utf8"))
 if doc.get("candidate")!=str(surf) or doc.get("candidate_sha256")!=item["candidate_sha"] or \
    doc.get("original_case")!=item["source"]:
  stop(site+" Stage12 candidate receipt disagrees")
 source_surf=Path(doc.get("original_fsurdat",""))
 if not source_surf.is_file() or sha(source_surf)!=doc.get("original_fsurdat_sha256"):
  stop(site+" original fsurdat SHA changed")
 point=pftpoint(surf,item["pft"])
 if old==case:stop("Unsafe same case path")
 exe=Path(query(old,"EXEROOT"))/"cesm.exe"
 if not exe.is_file():stop(site+" original compiled executable unavailable")
 if query(old,"BUILD_COMPLETE").lower()!="true" or query(old,"CALENDAR")!="NO_LEAP":
  stop(site+" source not pinned compiled NO_LEAP case")
 if query(old,"DATM_MODE")!="1PT" or query(old,"ATM_NCPL")!="48":
  stop(site+" source not pinned half-hour 1PT")
 first=stream(old,site,point)
 start=query(old,"RUN_STARTDATE")
 if not re.fullmatch(r"\d{4}-01-01",start) or not first["first"]<=int(start[:4])<=first["last"]:
  stop(site+" source date not inside CDEPS forcing loop")
 if query(old,"CLM_CO2_TYPE")!="constant":
  stop(site+" source CO2 not constant")
 co2=float(query(old,"CCSM_CO2_PPMV"))
 if not 300<co2<600:stop(site+" nonphysical constant CO2")
 original_nl=(old/"CaseDocs/lnd_in").read_text(encoding="utf8")
 if Path(field(original_nl,"fsurdat"))!=source_surf:
  stop(site+" source CIME land surface differs from signed Stage12 receipt")
 srcparam=Path(field(original_nl,"fates_paramfile"))
 if srcparam.resolve()!=PARAM.resolve():stop(site+" source FATES parameter differs")
 before=(float(query(old,"PTS_LAT")),float(query(old,"PTS_LON"))%360)
 if distance(before,point)>0.001:
  print("SOURCE PTS MISMATCH (legacy diagnostic)",site,before,"vs true surface",point,
        "| independent new case will explicitly reset PTS_LAT/LON and validate NUOPC")
 if not existing:
  for p in (case,run,arch,attempt):
   if p.exists() or p.is_symlink():
    stop(site+" new case/attempt exists; never overwrite "+str(p))
 return {"site":site,"point":point,"old":old,"case":case,
         "run":run,"arch":arch,"surf":surf,"attempt":attempt,
         "source_stream":first,"exe":exe,"source_start":start,
         "co2":co2,"original_case_lnd":sha(old/"CaseDocs/lnd_in")}
def config(site,z):
 case=z["case"]
 nl=case/"CaseDocs/lnd_in"
 rundir=z["run"]
 for key,value in (
   ("CASE",SITES[site]["case"]),("RUNDIR",str(rundir)),
   ("DOUT_S_ROOT",str(z["arch"])),("PTS_DOMAINFILE","UNSET"),
   ("RUN_TYPE","startup"),("CONTINUE_RUN","FALSE"),
   ("CLM_FORCE_COLDSTART","on"),("CLM_ACCELERATED_SPINUP","on"),
   ("STOP_OPTION","nyears"),("STOP_N","5"),
   ("REST_OPTION","nyears"),("REST_N","5"),("RESUBMIT","0"),
   ("DOUT_S","TRUE"),("CLM_BLDNML_OPTS",BGC_OPTS)):
  if query(case,key).lower()!=value.lower():
   stop(site+" new CIME setting incorrect "+key)
 actual=(float(query(case,"PTS_LAT")),float(query(case,"PTS_LON"))%360)
 if distance(z["point"],actual)>1e-5:stop(site+" xml PTS wrong")
 if query(case,"BUILD_COMPLETE").lower()!="true":
  stop(site+" compiled binary not held")
 if (Path(query(case,"EXEROOT"))/"cesm.exe")!=z["exe"]:
  stop(site+" compiled original binary not reused")
 for x in ("env_case.xml","LockedFiles/env_case.xml"):
  if not (case/x).is_file():stop(site+" missing CIME XML lock "+x)
 if (case/"env_case.xml").read_bytes()!=(case/"LockedFiles/env_case.xml").read_bytes():
  stop(site+" original env case lock not restored")
 if not nl.is_file() or not (rundir/"lnd_in").is_file():
  stop(site+" effective lnd_in missing")
 if sha(nl)!=sha(rundir/"lnd_in"):stop(site+" RUNDIR namelist != CaseDocs")
 doc=nl.read_text(encoding="utf8")
 for key,value in FIELDS.items():
  if field(doc,key)!=value:stop(site+" original requested FATES AD flag "+key+" wrong")
 if field(doc,"use_cn")!=".false.":stop(site+" CN-only active")
 if field(doc,"reseed_dead_plants") is not None:
  stop(site+" forbidden CN-only reseed")
 if field(doc,"fsurdat")!=str(z["surf"]):
  stop(site+" generated fsurdat wrong")
 if Path(field(doc,"fates_paramfile")).resolve()!=PARAM.resolve():
  stop(site+" generated shared 14-PFT file changed")
 if abs(float(field(doc,"co2_ppmv"))-z["co2"])>0.001:
  stop(site+" source CO2 changed")
 if query(case,"RUN_STARTDATE")!=z["source_start"] or abs(float(query(case,"CCSM_CO2_PPMV"))-z["co2"])>0.001:
  stop(site+" original source clock/CO2 changed")
 ss=stream(case,site,z["point"])
 if ss["first"]!=z["source_stream"]["first"] or ss["last"]!=z["source_stream"]["last"] or \
    ss["stream_sha"]!=z["source_stream"]["stream_sha"]:
  stop(site+" source meteorological CDEPS stream changed")
 if not (rundir/"datm.streams.xml").is_file() or sha(rundir/"datm.streams.xml")!=ss["stream_sha"]:
  stop(site+" effective RUNDIR DATM input differs")
 for p in (case/"CaseDocs/nuopc.runconfig",rundir/"nuopc.runconfig"):
  if not p.is_file():stop(site+" actual NUOPC coupler point file missing")
  t=p.read_text(encoding="utf8")
  coords={}
  for key in ("scol_lat","scol_lon","single_column_lnd_domainfile"):
   m=re.findall(r"(?im)^\s*"+key+r"\s*=\s*(.*?)\s*$",t)
   if len(m)!=1:stop(site+" NUOPC key missing "+key+" at "+str(p))
   coords[key]=m[0].strip()
  pt=float(coords["scol_lat"]),float(coords["scol_lon"])%360
  if distance(pt,z["point"])>0.0001 or coords["single_column_lnd_domainfile"]!="UNSET":
   stop(site+" effective NUOPC PTS doesn't match site surface")
  print("EFFECTIVE COUPLER PASS",site,p.parent.name,"surface vs scol",pt,flush=True)
 # The private overlay has been restored in CIME XML; any future submit must
 # use --skip-preview-namelist to retain these checked AD FATES flags.
 check_help=subprocess.run([str(case/"case.submit"),"--help"],cwd=case,
                           capture_output=True,text=True,check=False,timeout=80)
 if check_help.returncode not in (0,1) or \
    "--skip-preview-namelist" not in (check_help.stdout+check_help.stderr):
  stop(site+" actual CIME submit lacks mandatory skip-preview flag")
 if any(rundir.glob("rpointer*")) or any(rundir.glob("*.r.*.nc")):
  stop(site+" new AD5 startup unexpectedly contains restarts")
 return {"site":site,"case":str(case),"point":list(z["point"]),
         "met_years":[ss["first"],ss["last"]],"provisional_years":ss["provisional_years"],
         "selected_2000_CO2_PPMV":z["co2"],
         "scientific_release":False,"case_prepared_not_submitted":True}
def create(site,z):
 case=z["case"]
 z["attempt"].parent.mkdir(parents=True,exist_ok=True)
 with z["attempt"].open("x",encoding="utf8") as f:
  json.dump({"site":site,"phase":"ATTEMPTED_UNCERTAIN","case":str(case),
             "slurm_submitted":False,"created_utc":datetime.now(timezone.utc).isoformat()},f,indent=2)
  f.write("\n")
 print("ONE-TIME NEW CASE CREATION",site,case,flush=True)
 call([CTSM/"cime/scripts/create_clone","--case",case,
       "--clone",z["old"],"--keepexe"],cwd=CTSM/"cime/scripts",timeout=460)
 for key,value in (
  ("RUN_TYPE","startup"),("RUN_STARTDATE",z["source_start"]),
  ("CONTINUE_RUN","FALSE"),("CLM_FORCE_COLDSTART","on"),
  ("CLM_ACCELERATED_SPINUP","on"),("CLM_BLDNML_OPTS",BGC_OPTS),
  ("STOP_OPTION","nyears"),("STOP_N","5"),
  ("REST_OPTION","nyears"),("REST_N","5"),
  ("RESUBMIT","0"),("DOUT_S","TRUE"),
  ("RUNDIR",str(z["run"])),("DOUT_S_ROOT",str(z["arch"])),
  ("PTS_LAT",str(z["point"][0])),("PTS_LON",str(z["point"][1])),
  ("PTS_DOMAINFILE","UNSET")):
  change(case,key,value)
 nl=case/"user_nl_clm"
 if not nl.is_file():stop(site+" cloned user_nl_clm missing")
 t=nl.read_text(encoding="utf8")
 for key,value in {
  "fsurdat":"'"+str(z["surf"])+"'",
  "fates_paramfile":"'"+str(PARAM)+"'",
  "finidat":"''",
  "use_fates":".true.","use_fates_sp":".false.",
  "use_fates_fixed_biogeog":".true.","use_fates_nocomp":".true.",
  "spinup_state":"2"}.items():
  t=setfield(t,key,value)
 nl.write_text(t,encoding="utf8")
 if not (case/".case.run").is_file():call([case/"case.setup"],cwd=case,timeout=320)
 locked=(case/"LockedFiles/env_case.xml").read_bytes()
 if (case/"env_case.xml").read_bytes()!=locked:
  stop(site+" CIME case env lock mismatch after setup")
 if query(case,"COMP_ROOT_DIR_LND")!=str(CTSM):
  # xmlquery commonly expands $SRCROOT to an absolute path.
  if Path(query(case,"COMP_ROOT_DIR_LND")).resolve()!=CTSM.resolve():
   stop(site+" unexpected original CTSM root")
 try:
  change(case,"COMP_ROOT_DIR_LND",str(OVERLAY))
  call([case/"preview_namelists"],cwd=case,timeout=650)
 finally:
  change(case,"COMP_ROOT_DIR_LND","$SRCROOT")
  if (case/"env_case.xml").read_bytes()!=locked or \
     (case/"LockedFiles/env_case.xml").read_bytes()!=locked:
   stop(site+" CIME lock not correctly restored")
 record=config(site,z)
 current=json.loads(z["attempt"].read_text(encoding="utf8"))
 current.update({"phase":"PREVIEW_VERIFIED_NOT_SUBMITTED",
   "verified":record,"preview_utc":datetime.now(timezone.utc).isoformat()})
 z["attempt"].write_text(json.dumps(current,indent=2)+"\n",encoding="utf8")
 print("STAGE30 CASE PREVIEW PASS",site,"NO SLURM",case,flush=True)
def main():
 ap=argparse.ArgumentParser(description=__doc__)
 group=ap.add_mutually_exclusive_group(required=True)
 group.add_argument("--self-test",action="store_true")
 group.add_argument("--check",action="store_true")
 group.add_argument("--prepare",action="store_true")
 group.add_argument("--verify",action="store_true")
 ap.add_argument("--confirm")
 a=ap.parse_args()
 if a.self_test:
  assert len(SITES)==4 and set(SITES)=={"DK-Sor","FR-FBn","BE-Bra","CH-Lae"}
  assert all(abs(sum(z["pft"].values())-100)<1e-8 for z in SITES.values())
  assert distance((42.7102,-80.3574),(42.7102,279.6426))<1e-8
  assert json.loads(json.dumps({"point":list((40.606176,8.151694))})) == {"point":[40.606176,8.151694]}
  print("STAGE30 SELF-TEST PASS: four exact forest proxy sites, longitude wrap, JSON-list PTS receipts; NO WRITES")
  return
 if a.prepare and a.confirm!=ACK:ap.error("--prepare requires --confirm "+ACK)
 if not a.prepare and a.confirm:ap.error("No confirmation option for read-only modes")
 preload_manifests()
 overlay()
 if a.verify:
  for site in SITES:
   z=preflight(site,existing=True)
   record=json.loads(z["attempt"].read_text())
   if record.get("phase")!="PREVIEW_VERIFIED_NOT_SUBMITTED":
    stop(site+" new preview was not successfully completed")
   verified=config(site,z)
   if verified!=record.get("verified"):
    stop(site+" verified source state changed; expected/actual: "+repr(record.get("verified"))+" / "+repr(verified))
  print("STAGE30 VERIFIED FOUR FOREST AD5 CASES 4/4; NO SLURM")
  return
 samples={site:preflight(site) for site in SITES}
 for site,z in samples.items():
  print("PRECHECK PASS",site,"start",z["source_start"],"surface",z["surf"],
        "PTS",z["point"],"CDEPS YEARS",z["source_stream"]["first"],z["source_stream"]["last"],
        "PROVISIONAL MET",z["source_stream"]["provisional_years"],
        "FIXED_CO2",z["co2"],"SCIENCE HOLD",SITES[site]["science_hold"])
 if a.check:
  print("STAGE30 READ ONLY PRECHECK PASS 4/4; NO MODEL/CIME/SLURM CHANGES")
  return
 for site in SITES:create(site,samples[site])
 print("STAGE30 FOUR FOREST AD5 PREVIEWS CREATED; DO NOT SUBMIT BEFORE SOURCE QC RELEASE")
if __name__=="__main__":main()
