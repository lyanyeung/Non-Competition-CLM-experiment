#!/usr/bin/env python3
"""Stage35 BE-Bra: isolated new AD400 80x5y from Stage30 forest preview, using
Stage34 independently versioned 30 annual DATM (4 targeted edited years, 26
original years). This is explicitly LOCAL-INTERPOLATED EXPLORATORY meteorology
not native tower-QC or ERA5 independently verified. Original case not touched;
prepare and audit do not submit; start is guarded single submit attempt only.
"""
import argparse,hashlib,json,re,resource,os,socket,shutil,subprocess,configparser
import xml.etree.ElementTree as ET
from pathlib import Path
from datetime import datetime,timezone

B=Path("/iridisfs/scratch/ly3n24/CLM_FATES")
E=B/"experiments/NonCompetitionObserved22/Batch02_10"
CTSM=B/"CTSM"
SOURCE=B/"cases/BE-Bra_B02_FIXNC_FOREST_PROXY_AD5"
NAME="BE-Bra_B02_FIXNC_FOREST_MET34_AD400"
CASE=B/"cases"/NAME
RUNROOT=Path("/scratch/ly3n24/CTSM_FATES_OUTPUTS")
RUN=RUNROOT/NAME/"run"
ARCH=RUNROOT/"archive"/NAME
SURF=E/"stage29_remaining4_forest_PFT_proxy_v1/BE-Bra/surfdata_BE-Bra_B02_FOREST_PFT_proxy_v1.nc"
SURF_SHA="86af5eea96b3d9895546c46a77c2b086479170c38ad5559f35c10fb24f148917"
SOURCE_RECEIPT=E/"stage30_four_forest_AD5_preview/BE-Bra_prepare_attempt.json"
SOURCE_STREAM_SHA="7fafea5869f183173fda3a00dc9b013e654daf1237b72bb19d46ed1f5a000109"
OVERLAY=E/"_private_ctsm_FATES_AD5_namelist_overlay_v1"
RECORDS=E/"stage35_BE_Bra_MET34_direct_AD400"
PREP=RECORDS/"prepare_attempt.json"
SUBMIT=RECORDS/"submission_attempt.json"
PREP_ACK="PREPARE_BE_BRA_STAGE35_INDEPENDENT_MET34_AD400_NO_SUBMIT"
START_ACK="SUBMIT_BE_BRA_STAGE35_CURATED_EXPLORATORY_AD400_ONCE"

def fail(msg):raise RuntimeError(str(msg))
def ensure(ok,msg):
 if not bool(ok):fail(msg)
def sha(p):
 h=hashlib.sha256()
 with Path(p).open("rb") as f:
  for chunk in iter(lambda:f.read(1048576),b""):h.update(chunk)
 return h.hexdigest()
def command(argv,at=None,timeout=180,allow_rc=(0,)):
 p=subprocess.run([str(z) for z in argv],cwd=at,capture_output=True,
                  text=True,timeout=timeout,check=False)
 if p.returncode not in allow_rc:
  fail(f"CMD {argv} rc {p.returncode}\n{(p.stdout+p.stderr)[-2700:]}")
 return p.stdout.strip()
def query(case,key):
 return command([case/"xmlquery",key,"--value"],at=case,timeout=90)
def change(case,k,v):
 return command([case/"xmlchange",k+"="+str(v)],at=case,timeout=90)
def field(t,key):
 vals=re.findall(r"(?im)^\s*"+re.escape(key)+r"\s*=\s*([^\r\n!]*)",t)
 ensure(len(vals)==1,f"Missing or duplicate land namelist {key}")
 return vals[0].strip().rstrip(",").strip("'\"").strip()
def clock():
 return datetime.now(timezone.utc).isoformat()
def load_manifest(folder):
 mp=folder/"manifest.json"
 ensure(mp.is_file(),"Stage34 selected 30-year manifest absent")
 m=json.loads(mp.read_text())
 ensure(folder.name=="stage34_BE_Bra_curated_MET_QC_v2" and
        m.get("version")=="BE-Bra-1996-1999-2005-2021-curated-QC-v2-20261026",
        "Only new Stage34 v2 verified model inputs permitted")
 ensure(m.get("site")=="BE-Bra" and m.get("years")==[1996,2025]
        and m.get("record_count_per_year")==17520 and
        m.get("source_case")==SOURCE.name and
        m.get("source_stream_sha256")==SOURCE_STREAM_SHA,
        "Stage34 source case/year/time provenance changed")
 ensure(m.get("science_status")==
        "EXPLORATORY_LOCAL_BRACKET_INTERPOLATION_PENDING_NATIVE_QC_ERA_VALIDATION",
        "Stage34 cannot be misrepresented as source-verified QA")
 ensure(m.get("total_QBOT_edits")==27 and m.get("total_TBOT_edits")==4
        and m.get("unmodified_2002_rain_original_retained") is True
        and m.get("original_source_files_modified") is False
        and m.get("CIME_case_modified") is False
        and m.get("Slurm_submitted") is False,
        "Stage34 science patch and original-protection guards changed")
 changes=m.get("modified_years",{})
 ensure(set(map(str,changes))=={"1996","1999","2005","2021"},
        "Stage34 four changed years missing or unexpected")
 for y,items in changes.items():
  require_counts={
    "1996":(2,12),"1999":(0,13),
    "2005":(1,1),"2021":(1,1)}
  tb,qb=require_counts[str(y)]
  ensure(len(items.get("changes",{}).get("TBOT",{}))==tb and
         len(items.get("changes",{}).get("QBOT",{}))==qb,
         "Stage34 unexpected year-specific authorised TBOT/QBOT changes: "+str(y))
 records=m.get("selected_30_annual_DATM",[])
 ensure(len(records)==30 and len({x.get("path") for x in records})==30,
        "Stage34 expected 30 unique yearly file paths")
 out=[]
 for y,rec in zip(range(1996,2026),records):
  p=Path(rec["path"])
  modified=y in (1996,1999,2005,2021)
  ensure(int(rec["year"])==y and rec["modified"]==modified and
         p.is_file() and p.name.startswith(f"BE-Bra_DATM_{y}"),
         f"Stage34 file identity {y} differs")
  ensure(sha(p)==rec["sha256"],"Stage34 selected annual SHA drift: "+str(y))
  if modified:
   ensure(p.is_relative_to(folder.resolve()) and
          p.name==f"BE-Bra_DATM_{y}_STAGE34_CURATED_EXPLORATORY.nc",
          "Stage34 edited year is not in selected isolated output")
  else:
   ensure("datm_11_provisional_dynamic_zbot_v1" in p.parts,
          "Unmodified annual DATM not from original source selected version "+str(y))
  out.append(p)
 return m,out

def actual_stream(case):
 xml=case/"CaseDocs/datm.streams.xml"
 run=Path(query(case,"RUNDIR"))/"datm.streams.xml"
 ensure(xml.is_file() and run.is_file() and sha(xml)==sha(run),
        "CIME CaseDocs and RUNDIR DATM stream differ")
 root=ET.parse(xml).getroot()
 blocks=[s for s in root.iter("stream_info") if s.get("name")=="CLM_USRDAT.UNSET"]
 ensure(len(blocks)==1,"Missing/ambiguous CLM_USRDAT.UNSET stream")
 s=blocks[0]
 def read(k):
  v=s.find(k)
  ensure(v is not None,"Missing DATM key "+k)
  return (v.text or "").strip()
 ensure((int(read("year_first")),int(read("year_last")))==(1996,2025),
        "Unexpected DATM cyclic years")
 ensure(read("taxmode")=="cycle" and int(read("year_align"))==1996 and
        read("offset")=="0","Unexpected DATM time alignment")
 data=s.find("datafiles")
 ensure(data is not None and len(list(data))==30,"Expected exact 30 DATM entries")
 paths=[Path((v.text or "").strip()) for v in data]
 return xml,paths
def set_new_stream(case,paths):
 old,oldfiles=actual_stream(case)
 root=ET.parse(old).getroot()
 blocks=[s for s in root.iter("stream_info") if s.get("name")=="CLM_USRDAT.UNSET"]
 data=blocks[0].find("datafiles")
 ensure(data is not None and len(data)==30,"DATM datafiles structure mutated")
 for node,target in zip(data,paths):
  node.text=str(target)
 # Save to a separate temporary file then replace within NEW case only.
 tmp=old.with_name(old.name+".stage35.tmp")
 ensure(not tmp.exists(),"Unexpected temporary stream existing")
 ET.ElementTree(root).write(tmp,encoding="utf-8",xml_declaration=True)
 os.replace(tmp,old)
 run=Path(query(case,"RUNDIR"))/"datm.streams.xml"
 shutil.copy2(old,run)
 now,files=actual_stream(case)
 ensure(files==paths,"CDEPS did not retain Stage34 30-file datafiles mapping")
 return sha(now)
def verify_original_preview():
 ensure(SOURCE.is_dir() and SOURCE_RECEIPT.is_file(),
        "Stage30 unsubmitted BE-Bra source preview not available")
 rec=json.loads(SOURCE_RECEIPT.read_text())
 ensure(rec.get("phase")=="PREVIEW_VERIFIED_NOT_SUBMITTED" and
        rec.get("slurm_submitted") is False and
        rec.get("verified",{}).get("point")==[51.30761,4.51984],
        "Stage30 source preview receipt phase/site point changed")
 ensure(SURF.is_file() and sha(SURF)==SURF_SHA,
        "Stage29 BE-Bra site surface SHA changed")
 ensure(query(SOURCE,"RUN_STARTDATE")=="1996-01-01" and
        query(SOURCE,"CALENDAR")=="NO_LEAP" and
        query(SOURCE,"BUILD_COMPLETE").lower()=="true",
        "Stage30 site original clock/build changed")
 ensure(query(SOURCE,"RESUBMIT")=="0" and
        query(SOURCE,"CONTINUE_RUN").lower()=="false",
        "Stage30 source case already running/modified")
 ensure((SOURCE/"env_case.xml").read_bytes()==
        (SOURCE/"LockedFiles/env_case.xml").read_bytes(),
        "Stage30 source locked CIME env differs")
 nl=(SOURCE/"CaseDocs/lnd_in").read_text()
 for k,v in {"spinup_state":"2","use_fates":".true.",
             "use_fates_nocomp":".true.","use_fates_fixed_biogeog":".true.",
             "use_fates_sp":".false.","use_cn":".false.","finidat":""}.items():
  ensure(field(nl,k)==v,"Stage30 exact FATES science flag drift "+k)
 ensure(field(nl,"fsurdat")==str(SURF),
        "Stage30 source PFT surface does not match Stage29")
 xml,selected=actual_stream(SOURCE)
 ensure(sha(xml)==SOURCE_STREAM_SHA and len(selected)==30,
        "Stage30 source actual original DATM stream changed")
 exe=Path(query(SOURCE,"EXEROOT"))/"cesm.exe"
 ensure(exe.is_file(),"Stage30 same-site compiled CESM/FATES binary absent")
 if (SOURCE/"CaseStatus").is_file():
  cs=(SOURCE/"CaseStatus").read_text(errors="replace")
  ensure("case.submit starting" not in cs and "case.run starting" not in cs,
         "Stage30 pre-existing case had prior submission")
 return exe

def validate_new(folder,expected_resubmit=None):
 manifest,paths=load_manifest(folder)
 exe=verify_original_preview()
 ensure(CASE.is_dir(),"Stage35 new case not yet created")
 for k,v in {
  "CASE":NAME,"RUN_TYPE":"startup","CONTINUE_RUN":"FALSE",
  "STOP_OPTION":"nyears","STOP_N":"5","REST_OPTION":"nyears",
  "REST_N":"5","RUN_STARTDATE":"1996-01-01",
  "RESUBMIT_SETS_CONTINUE_RUN":"TRUE","DOUT_S":"TRUE",
  "CLM_ACCELERATED_SPINUP":"on","CLM_FORCE_COLDSTART":"on",
  "PTS_DOMAINFILE":"UNSET","BUILD_COMPLETE":"TRUE",
  "RUNDIR":str(RUN),"DOUT_S_ROOT":str(ARCH)
 }.items():
  ensure(query(CASE,k).lower()==v.lower(),f"Stage35 CIME {k} mismatch: {query(CASE,k)}")
 if expected_resubmit is not None:
  ensure(query(CASE,"RESUBMIT")==str(expected_resubmit),
         "RESUBMIT value mismatch")
 for k,v in {"PTS_LAT":51.30761,"PTS_LON":4.51984,
             "CCSM_CO2_PPMV":361.93}.items():
  got=float(query(CASE,k))
  if k=="PTS_LON":got=got%360
  ensure(abs(got-v)<0.0001,f"BE-Bra CIME point/CO2 changed {k}")
 ensure(Path(query(CASE,"EXEROOT"))/"cesm.exe"==exe,
        "Compiled executable different from original Stage30")
 ensure((CASE/"env_case.xml").read_bytes()==
        (CASE/"LockedFiles/env_case.xml").read_bytes(),
        "New case CIME env_case XML lock changed")
 ensure((CASE/"CaseDocs/lnd_in").is_file() and (RUN/"lnd_in").is_file() and
        sha(CASE/"CaseDocs/lnd_in")==sha(RUN/"lnd_in"),
        "Effective original AD land namelists unequal")
 nl=(CASE/"CaseDocs/lnd_in").read_text()
 for k,v in {"spinup_state":"2","use_fates":".true.",
             "use_fates_sp":".false.","use_fates_nocomp":".true.",
             "use_fates_fixed_biogeog":".true.","finidat":"",
             "fsurdat":str(SURF)}.items():
  ensure(field(nl,k)==v,"Stage35 actual lnd_in key changed "+k)
 _,live_files=actual_stream(CASE)
 ensure(live_files==paths,"Stage35 effective DATM not Stage34 30y files")
 for runconfig in (CASE/"CaseDocs/nuopc.runconfig",RUN/"nuopc.runconfig"):
  ensure(runconfig.is_file(),"Missing point-coupler runconfig: "+str(runconfig))
  cfg=runconfig.read_text()
  for key,val in {"scol_lat":51.30761,"scol_lon":4.51984}.items():
   mt=re.findall(r"(?im)^\s*"+key+r"\s*=\s*([^\r\n]+)",cfg)
   ensure(len(mt)==1 and abs(float(mt[0])-val)<1e-4,
          f"NUOPC spatial point mismatch {key}: {runconfig}")
 ensure(not list(RUN.glob("rpointer*")) and not list(RUN.glob("*.r.*.nc")),
        "New Stage35 RUNDIR contains unexpected restart")
 print("STAGE35 AUDIT PASS: new independent case, original exe/PFT, 30 selected DATM, AD namelist, no restart")
 return {"datm_dir":str(folder.resolve()),
         "datm_manifest_sha256":sha(folder/"manifest.json"),
         "effective_case_stream_sha256":sha(CASE/"CaseDocs/datm.streams.xml")}
def prepare(folder):
 ensure(not CASE.exists() and not CASE.is_symlink() and
        not RUN.exists() and not ARCH.exists() and
        not PREP.exists() and not SUBMIT.exists(),
        "Stage35 case/run/archive/attempt already exists: NO rerun")
 manifest,paths=load_manifest(folder)
 verify_original_preview()
 ensure((OVERLAY/"bld/CLMBuildNamelist.pm").is_file() and
        (OVERLAY/"bld/build-namelist").is_file(),
        "Private CTSM FATES AD buildnamelist overlay absent")
 RECORDS.mkdir(parents=True,exist_ok=True)
 with PREP.open("x") as f:
  json.dump({"phase":"PREPARATION_ATTEMPT_UNCERTAIN","created_utc":clock(),
             "case":str(CASE),"datm_dir":str(folder.resolve())},f,indent=2)
  f.write("\n");f.flush();os.fsync(f.fileno())
 print("STAGE35 ONE-TIME CASE CLONE (no Slurm):",CASE,flush=True)
 command([CTSM/"cime/scripts/create_clone","--case",CASE,
          "--clone",SOURCE,"--keepexe"],at=CTSM/"cime/scripts",timeout=600)
 for k,v in (
  ("RUNDIR",str(RUN)),("DOUT_S_ROOT",str(ARCH)),
  ("RUN_TYPE","startup"),("CONTINUE_RUN","FALSE"),
  ("RUN_STARTDATE","1996-01-01"),("STOP_OPTION","nyears"),
  ("STOP_N","5"),("REST_OPTION","nyears"),("REST_N","5"),
  ("RESUBMIT","0"),("CLM_ACCELERATED_SPINUP","on"),
  ("CLM_FORCE_COLDSTART","on"),("DOUT_S","TRUE"),
  ("PTS_LAT","51.30761"),("PTS_LON","4.51984"),
  ("PTS_DOMAINFILE","UNSET")
 ):
  change(CASE,k,v)
 if not (CASE/".case.run").is_file():
  command([CASE/"case.setup"],at=CASE,timeout=390)
 original_lock=(CASE/"LockedFiles/env_case.xml").read_bytes()
 ensure((CASE/"env_case.xml").read_bytes()==original_lock,
        "CIME new-case env_case lock already divergent")
 original_lnd_root=query(CASE,"COMP_ROOT_DIR_LND")
 ensure(Path(original_lnd_root).resolve()==CTSM.resolve() or
        original_lnd_root=="$SRCROOT",
        "Stage35 cloned CTSM root mismatch")
 try:
  change(CASE,"COMP_ROOT_DIR_LND",str(OVERLAY))
  command([CASE/"preview_namelists"],at=CASE,timeout=680)
 finally:
  change(CASE,"COMP_ROOT_DIR_LND","$SRCROOT")
 ensure((CASE/"env_case.xml").read_bytes()==original_lock,
        "CIME env_case lock not restored after private overlay")
 # With --skip-preview-namelist, this exact case-local XML will be used on submit.
 actual_stream(CASE)
 new_sha=set_new_stream(CASE,paths)
 result=validate_new(folder,expected_resubmit=0)
 result.update({"phase":"PREPARED_NEW_MET34_NOT_SUBMITTED",
                "created_utc":clock(),"case":str(CASE),
                "stage34_30_selected_annual_DATM_files":len(paths),
                "effective_stream_sha256":new_sha})
 PREP.write_text(json.dumps(result,indent=2)+"\n")
 print("STAGE35 PREPARE PASS (NO JOBS)",CASE)
 print("STAGE35 NEW DATA STREAM SHA:",new_sha)
def audit(folder):
 ensure(PREP.is_file(),"Stage35 must be prepared before --audit")
 receipt=json.loads(PREP.read_text())
 ensure(receipt.get("phase")=="PREPARED_NEW_MET34_NOT_SUBMITTED",
        "Stage35 one-time preparation receipt unclear")
 ensure(receipt.get("datm_dir")==str(folder.resolve()),
        "Stage35 provided DATM dir differs from prepare receipt")
 resub=int(query(CASE,"RESUBMIT"))
 ensure(resub in (0,79),"Unexpected Stage35 RESUBMIT configuration")
 r=validate_new(folder,expected_resubmit=resub)
 ensure(r["effective_case_stream_sha256"]==
        receipt["effective_case_stream_sha256"],"Stage35 source stream drift")
 if SUBMIT.exists():
  d=json.loads(SUBMIT.read_text())
  print("STAGE35 ALREADY HAS SUBMISSION ATTEMPT; NEVER RESUBMIT",d.get("phase"))
 print("STAGE35 READONLY AUDIT SUCCESS | case",CASE,"RESUBMIT",resub)
 return receipt
def start(folder):
 audit(folder)
 ensure(not SUBMIT.exists(),"Stage35 already has a submission attempt!")
 ensure(query(CASE,"RESUBMIT")=="0","Stage35 pre-submit RESUBMIT should be 0")
 # Check for another submission of the exact *new* case; other site's Slurm
 # jobs are never touched.
 sq=subprocess.run(["squeue","-h","-u",os.environ.get("USER","ly3n24"),
                    "-o","%i|%j|%T"],capture_output=True,text=True,timeout=60)
 ensure(sq.returncode==0,"Cannot verify Slurm queue; do NOT submit")
 ensure(NAME not in sq.stdout,"Stage35 new case has queued/running Slurm job")
 h=subprocess.run([str(CASE/"case.submit"),"--help"],cwd=CASE,
                  capture_output=True,text=True,timeout=80)
 ensure("--skip-preview-namelist" in h.stdout+h.stderr,
        "CIME case.submit lacks mandatory skip-preview-namelist")
 limits=resource.getrlimit(resource.RLIMIT_STACK)
 if limits[0]!=resource.RLIM_INFINITY and limits[0]<64*1024*1024:
  hard=limits[1]
  ensure(hard==resource.RLIM_INFINITY or hard>=64*1024*1024,
         "Inherited stack hard limit is too small")
  resource.setrlimit(resource.RLIMIT_STACK,
                    (resource.RLIM_INFINITY if hard==resource.RLIM_INFINITY else hard,hard))
 print("STAGE35 SUBMIT STACK",resource.getrlimit(resource.RLIMIT_STACK),"HOST",socket.gethostname())
 record={"phase":"SUBMISSION_ATTEMPT_UNCERTAIN","case":str(CASE),
         "datm_dir":str(folder.resolve()),
         "started_utc":clock(),"years":400,"segments":80,"resubmit":79,
         "science":"EXPLORATORY_LOCAL_INTERPOLATION_NOT_NATIVE_QC_OR_ERA5_VERIFIED"}
 with SUBMIT.open("x") as f:
  json.dump(record,f,indent=2);f.write("\n");f.flush();os.fsync(f.fileno())
 change(CASE,"RESUBMIT","79")
 ensure(query(CASE,"RESUBMIT")=="79","RESUBMIT set failed; attempt uncertain")
 p=subprocess.run(
                  [str(CASE/"case.submit"),"--skip-preview-namelist"],
                  cwd=CASE,capture_output=True,text=True,timeout=650,check=False)
 print(p.stdout[-7000:],p.stderr[-2300:],flush=True)
 ensure(p.returncode==0,
        "Stage35 Slurm submit returned error; attempt uncertain; NO retry")
 runids=re.findall(r"Submitted job case\.run with id (\d+)",p.stdout)
 archids=re.findall(r"Submitted job case\.st_archive with id (\d+)",p.stdout)
 ensure(len(runids)==1 and len(archids)==1,
        "Stage35 job IDs ambiguous; inspect squeue/sacct; NO retry")
 opts=CASE/".submit_options"
 persisted=False
 if opts.is_file():
  cp=configparser.RawConfigParser()
  cp.read(opts)
  persisted=cp.has_section("SubmitOptions") and cp.getboolean(
             "SubmitOptions","skip_pnl",fallback=False)
 record.update({"phase":"SUBMITTED_MODEL_NOT_YET_COMPLETED" if persisted else
                        "SUBMITTED_SKIP_PREVIEW_PERSISTENCE_UNCERTAIN",
                "run_jobid":runids[0],"archive_jobid":archids[0],
                "skip_preview_persisted":persisted,"submitted_utc":clock()})
 SUBMIT.write_text(json.dumps(record,indent=2)+"\n")
 print("STAGE35 BE-Bra AD400 SUBMITTED",runids[0],archids[0],
       "80x5yr (NO model-years yet verified!) skip_preview_persisted",persisted)
 if not persisted:
  print("WARNING: .submit_options skip_pnl not persistent. Automatic chained resubmits may regenerate stale DATM. Stop and inspect; do not retry case.submit.")
def self_test():
 ensure(5*(79+1)==400 and 1996+400==2396,"AD400 algebra error")
 ensure(NAME.startswith("BE-Bra_B02_FIXNC") and CASE!=SOURCE,
        "Unsafe cloning case identity")
 ensure(SURF_SHA.startswith("86af5eea"),"Site surface SHA")
 # Guard against the former subprocess.run(at=CASE) mistake (valid only for our command helper).
 import ast, inspect, textwrap
 tree=ast.parse(textwrap.dedent(inspect.getsource(start)))
 direct=[n for n in ast.walk(tree) if isinstance(n,ast.Call) and
         isinstance(n.func,ast.Attribute) and
         isinstance(n.func.value,ast.Name) and n.func.value.id=="subprocess" and
         n.func.attr=="run"]
 ensure(len(direct)==3 and all(all(k.arg!="at" for k in n.keywords) for n in direct),
        "Stage35 direct subprocess.run must use cwd=, never at=")
 print("STAGE35 SELF-TEST PASS: separate BE-Bra case, 80x5y, subprocess.run cwd; no writes")
def main():
 ap=argparse.ArgumentParser(description=__doc__)
 g=ap.add_mutually_exclusive_group(required=True)
 for x in ("self-test","audit","prepare","start"):
  g.add_argument("--"+x,action="store_true")
 ap.add_argument("--datm-dir",type=Path)
 ap.add_argument("--confirm")
 args=ap.parse_args()
 self_test()
 if args.self_test:return
 ensure(args.datm_dir is not None,"--datm-dir Stage34 output is required")
 folder=args.datm_dir.expanduser().resolve()
 if args.prepare:
  ensure(args.confirm==PREP_ACK,"--prepare requires --confirm "+PREP_ACK)
  prepare(folder)
 elif args.start:
  ensure(args.confirm==START_ACK,"--start requires --confirm "+START_ACK)
  start(folder)
 else:
  ensure(args.confirm is None,"--confirm not valid for readonly --audit")
  audit(folder)
if __name__=="__main__":main()
