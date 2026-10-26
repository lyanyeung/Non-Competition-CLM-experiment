#!/usr/bin/env python3
"""ES-LJu Stage26: independent AD400 direct (80x5y) case, pinned Stage25 DATM.
--self-test (pure), --audit (read-only), --prepare --confirm ... (create isolated
clone with Stage25 21 yearly DATM, NO jobs), --start --confirm ... (one-time
real Slurm submission, ONLY after a successful --audit). NEVER retarget old
ES-LJu AD5 preview or any previously submitted Batch02 case.
Stage24 site PFT composition (bare49, C3grass31, shrub20) is an operator-
accepted, explicitly IDEALIZED model proxy, not independently verified census.
"""
import argparse,hashlib,json,re,resource,os,socket,shutil,subprocess,configparser
import xml.etree.ElementTree as ET
from pathlib import Path
from datetime import datetime,timezone

B=Path("/iridisfs/scratch/ly3n24/CLM_FATES")
E=B/"experiments/NonCompetitionObserved22/Batch02_10"
CTSM=B/"CTSM"
SOURCE=B/"cases/ES-LJu_B02_FIXNC_AD400_BARE49_C3GRA31_SHRUB20_AD5"
NAME="ES-LJu_B02_FIXNC_AD400_BARE49_C3GRA31_SHRUB20_MET24"
CASE=B/"cases"/NAME
RUNROOT=Path("/scratch/ly3n24/CTSM_FATES_OUTPUTS")
RUN=RUNROOT/NAME/"run"
ARCH=RUNROOT/"archive"/NAME
SURF=E/"stage12_remaining6_bare_shrub_candidates_v1/ES-LJu/surfdata_ES-LJu_B02_BARESHRUB_PFT_proxy_v1.nc"
SURF_SHA="d44083a1eef069f6c74d389667f8a82802a93c5085665c712245470221e18762"
SOURCE_RECEIPT=E/"stage13_two_bare_shrub_AD5_preview/ES-LJu_prepare_attempt.json"
OVERLAY=E/"_private_ctsm_FATES_AD5_namelist_overlay_v1"
RECORDS=E/"stage26_ES_LJu_MET24_direct_AD400"
PREP=RECORDS/"prepare_attempt.json"
SUBMIT=RECORDS/"submission_attempt.json"
PREP_ACK="PREPARE_ES_LJU_STAGE24_INDEPENDENT_AD400_NO_SUBMIT"
START_ACK="SUBMIT_ES_LJU_STAGE24_DIRECT_AD400_ONCE"

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
 mpath=folder/"02_manifest.json"
 ensure(mpath.is_file(),f"Stage25 manifest missing {mpath}")
 m=json.loads(mpath.read_text())
 ensure(m.get("site")=="ES-LJu" and m.get("year_count")==21 and
        m.get("source_year_first")==2004 and
        m.get("source_year_last")==2024 and
        m.get("records_per_year")==17520,
        "Stage25 DATM count/time/site unexpected")
 paths=[Path(z) for z in m["new_annual_DATM_paths"]]
 sums=m["new_annual_DATM_sha256"]
 ensure(len(paths)==len(sums)==21 and len(set(paths))==21,"21 unique Stage25 data paths required")
 for year,p,digest in zip(range(2004,2025),paths,sums):
  ensure(p.is_file() and p.is_relative_to(folder.resolve()) and
         p.name==f"ES-LJu_DATM_{year}_STAGE24_FIXNC_PROVISIONAL.nc",
         f"Wrong Stage25 output for {year}: {p}")
  ensure(sha(p)==digest,f"Stage25 DATM {year} hash mismatch")
 src=Path(m["stage24_source_path"])
 ensure(src.is_file() and sha(src)==m["stage24_source_sha256"],
        "Stage25 parent Stage24 source has changed")
 ensure(m["originals_untouched"] and not m["slurm_submitted"],
        "Unexpected Stage25 mutation/Slurm marker")
 return m,paths
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
 ensure((int(read("year_first")),int(read("year_last")))==(2004,2024),
        "Unexpected DATM cyclic years")
 ensure(read("taxmode")=="cycle" and int(read("year_align"))==2004 and
        read("offset")=="0","Unexpected DATM time alignment")
 data=s.find("datafiles")
 ensure(data is not None and len(list(data))==21,"Expected exact 21 DATM entries")
 paths=[Path((v.text or "").strip()) for v in data]
 return xml,paths
def set_new_stream(case,paths):
 old,oldfiles=actual_stream(case)
 root=ET.parse(old).getroot()
 blocks=[s for s in root.iter("stream_info") if s.get("name")=="CLM_USRDAT.UNSET"]
 data=blocks[0].find("datafiles")
 ensure(data is not None and len(data)==21,"DATM datafiles structure mutated")
 for node,target in zip(data,paths):
  node.text=str(target)
 # Save to a separate temporary file then replace within NEW case only.
 tmp=old.with_name(old.name+".stage26.tmp")
 ensure(not tmp.exists(),"Unexpected temporary stream existing")
 ET.ElementTree(root).write(tmp,encoding="utf-8",xml_declaration=True)
 os.replace(tmp,old)
 run=Path(query(case,"RUNDIR"))/"datm.streams.xml"
 shutil.copy2(old,run)
 now,files=actual_stream(case)
 ensure(files==paths,"CDEPS did not retain Stage25 21-file datafiles mapping")
 return sha(now)
def verify_original_preview():
 ensure(SOURCE.is_dir() and SOURCE_RECEIPT.is_file(),"Original Stage13 case/receipt absent")
 a=json.loads(SOURCE_RECEIPT.read_text())
 ensure(a.get("phase")=="PREVIEW_VERIFIED_NOT_SUBMITTED" and
        a.get("slurm_submitted") is False,"Original ES-LJu Stage13 preview uncertain/submitted")
 ensure(a.get("verified",{}).get("point")==[36.926594,357.247885],
        "Source coupler point record changed")
 ensure(SURF.is_file() and sha(SURF)==SURF_SHA,
        "Original Stage12 ES-LJu idealized surface SHA changed")
 ensure(query(SOURCE,"RUN_STARTDATE")=="2004-01-01" and
        query(SOURCE,"CALENDAR")=="NO_LEAP" and
        query(SOURCE,"BUILD_COMPLETE").lower()=="true",
        "Stage13 source case clock/build changed")
 ensure(query(SOURCE,"RESUBMIT")=="0" and query(SOURCE,"CONTINUE_RUN").lower()=="false",
        "Source Stage13 preview already running/altered")
 ensure((SOURCE/"env_case.xml").read_bytes()==(SOURCE/"LockedFiles/env_case.xml").read_bytes(),
        "Source CIME env_case lock changed")
 expected=SOURCE/"CaseDocs/lnd_in"
 srcnl=expected.read_text(encoding="utf8")
 for k,v in {"spinup_state":"2","use_fates":".true.",
             "use_fates_nocomp":".true.","use_fates_fixed_biogeog":".true.",
             "use_fates_sp":".false.","use_cn":".false.","finidat":""}.items():
  ensure(field(srcnl,k)==v,"Source FATES flag mismatch "+k)
 ensure(field(srcnl,"fsurdat")==str(SURF),"Stage13 surface not actual input")
 exe=Path(query(SOURCE,"EXEROOT"))/"cesm.exe"
 ensure(exe.is_file(),"Stage13 compiled executable missing")
 if (SOURCE/"CaseStatus").is_file():
  cs=(SOURCE/"CaseStatus").read_text(errors="replace")
  ensure("case.submit starting" not in cs and
         "case.run starting" not in cs,
         "Original Stage13 case was submitted; do not clone uncertain state")
 return exe
def validate_new(folder,expected_resubmit=None):
 manifest,paths=load_manifest(folder)
 exe=verify_original_preview()
 ensure(CASE.is_dir(),"Stage26 new case not yet created")
 for k,v in {
  "CASE":NAME,"RUN_TYPE":"startup","CONTINUE_RUN":"FALSE",
  "STOP_OPTION":"nyears","STOP_N":"5","REST_OPTION":"nyears",
  "REST_N":"5","RUN_STARTDATE":"2004-01-01",
  "RESUBMIT_SETS_CONTINUE_RUN":"TRUE","DOUT_S":"TRUE",
  "CLM_ACCELERATED_SPINUP":"on","CLM_FORCE_COLDSTART":"on",
  "PTS_DOMAINFILE":"UNSET","BUILD_COMPLETE":"TRUE",
  "RUNDIR":str(RUN),"DOUT_S_ROOT":str(ARCH)
 }.items():
  ensure(query(CASE,k).lower()==v.lower(),f"Stage26 CIME {k} mismatch: {query(CASE,k)}")
 if expected_resubmit is not None:
  ensure(query(CASE,"RESUBMIT")==str(expected_resubmit),
         "RESUBMIT value mismatch")
 for k,v in {"PTS_LAT":36.926594,"PTS_LON":357.247885,
             "CCSM_CO2_PPMV":376.95}.items():
  got=float(query(CASE,k))
  if k=="PTS_LON":got=got%360
  ensure(abs(got-v)<0.0001,f"ES-LJu CIME point/CO2 changed {k}")
 ensure(Path(query(CASE,"EXEROOT"))/"cesm.exe"==exe,
        "Compiled executable different from original Stage13")
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
  ensure(field(nl,k)==v,"Stage26 actual lnd_in key changed "+k)
 _,live_files=actual_stream(CASE)
 ensure(live_files==paths,"Stage26 effective DATM not Stage25 21y files")
 for runconfig in (CASE/"CaseDocs/nuopc.runconfig",RUN/"nuopc.runconfig"):
  ensure(runconfig.is_file(),"Missing point-coupler runconfig: "+str(runconfig))
  cfg=runconfig.read_text()
  for key,val in {"scol_lat":36.926594,"scol_lon":357.247885}.items():
   mt=re.findall(r"(?im)^\s*"+key+r"\s*=\s*([^\r\n]+)",cfg)
   ensure(len(mt)==1 and abs(float(mt[0])-val)<1e-4,
          f"NUOPC spatial point mismatch {key}: {runconfig}")
 ensure(not list(RUN.glob("rpointer*")) and not list(RUN.glob("*.r.*.nc")),
        "New Stage26 RUNDIR contains unexpected restart")
 print("STAGE26 AUDIT PASS: new independent case, original exe/PFT, 21 new DATM, AD namelist, no restart")
 return {"datm_dir":str(folder.resolve()),
         "datm_manifest_sha256":sha(folder/"02_manifest.json"),
         "effective_case_stream_sha256":sha(CASE/"CaseDocs/datm.streams.xml")}
def prepare(folder):
 ensure(not CASE.exists() and not CASE.is_symlink() and
        not RUN.exists() and not ARCH.exists() and
        not PREP.exists() and not SUBMIT.exists(),
        "Stage26 case/run/archive/attempt already exists: NO rerun")
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
 print("STAGE26 ONE-TIME CASE CLONE (no Slurm):",CASE,flush=True)
 command([CTSM/"cime/scripts/create_clone","--case",CASE,
          "--clone",SOURCE,"--keepexe"],at=CTSM/"cime/scripts",timeout=600)
 for k,v in (
  ("RUNDIR",str(RUN)),("DOUT_S_ROOT",str(ARCH)),
  ("RUN_TYPE","startup"),("CONTINUE_RUN","FALSE"),
  ("RUN_STARTDATE","2004-01-01"),("STOP_OPTION","nyears"),
  ("STOP_N","5"),("REST_OPTION","nyears"),("REST_N","5"),
  ("RESUBMIT","0"),("CLM_ACCELERATED_SPINUP","on"),
  ("CLM_FORCE_COLDSTART","on"),("DOUT_S","TRUE"),
  ("PTS_LAT","36.926594"),("PTS_LON","357.247885"),
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
        "Stage26 cloned CTSM root mismatch")
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
 result.update({"phase":"PREPARED_NEW_MET24_NOT_SUBMITTED",
                "created_utc":clock(),"case":str(CASE),
                "stage25_21_annual_DTM_files":len(paths),
                "effective_stream_sha256":new_sha})
 PREP.write_text(json.dumps(result,indent=2)+"\n")
 print("STAGE26 PREPARE PASS (NO JOBS)",CASE)
 print("STAGE26 NEW DATA STREAM SHA:",new_sha)
def audit(folder):
 ensure(PREP.is_file(),"Stage26 must be prepared before --audit")
 receipt=json.loads(PREP.read_text())
 ensure(receipt.get("phase")=="PREPARED_NEW_MET24_NOT_SUBMITTED",
        "Stage26 one-time preparation receipt unclear")
 ensure(receipt.get("datm_dir")==str(folder.resolve()),
        "Stage26 provided DATM dir differs from prepare receipt")
 resub=int(query(CASE,"RESUBMIT"))
 ensure(resub in (0,79),"Unexpected Stage26 RESUBMIT configuration")
 r=validate_new(folder,expected_resubmit=resub)
 ensure(r["effective_case_stream_sha256"]==
        receipt["effective_case_stream_sha256"],"Stage26 source stream drift")
 if SUBMIT.exists():
  d=json.loads(SUBMIT.read_text())
  print("STAGE26 ALREADY HAS SUBMISSION ATTEMPT; NEVER RESUBMIT",d.get("phase"))
 print("STAGE26 READONLY AUDIT SUCCESS | case",CASE,"RESUBMIT",resub)
 return receipt
def start(folder):
 audit(folder)
 ensure(not SUBMIT.exists(),"Stage26 already has a submission attempt!")
 ensure(query(CASE,"RESUBMIT")=="0","Stage26 pre-submit RESUBMIT should be 0")
 # Check for another submission of the exact *new* case; other site's Slurm
 # jobs are never touched.
 sq=subprocess.run(["squeue","-h","-u",os.environ.get("USER","ly3n24"),
                    "-o","%i|%j|%T"],capture_output=True,text=True,timeout=60)
 ensure(sq.returncode==0,"Cannot verify Slurm queue; do NOT submit")
 ensure(NAME not in sq.stdout,"Stage26 new case has queued/running Slurm job")
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
 print("STAGE26 SUBMIT STACK",resource.getrlimit(resource.RLIMIT_STACK),"HOST",socket.gethostname())
 record={"phase":"SUBMISSION_ATTEMPT_UNCERTAIN","case":str(CASE),
         "datm_dir":str(folder.resolve()),
         "started_utc":clock(),"years":400,"segments":80,"resubmit":79,
         "science":"OPERATOR_APPROVED_STAGE24_MET__IDEALIZED_PFT_PROXY"}
 with SUBMIT.open("x") as f:
  json.dump(record,f,indent=2);f.write("\n");f.flush();os.fsync(f.fileno())
 change(CASE,"RESUBMIT","79")
 ensure(query(CASE,"RESUBMIT")=="79","RESUBMIT set failed; attempt uncertain")
 p=subprocess.run(
                  [str(CASE/"case.submit"),"--skip-preview-namelist"],
                  cwd=CASE,capture_output=True,text=True,timeout=650,check=False)
 print(p.stdout[-7000:],p.stderr[-2300:],flush=True)
 ensure(p.returncode==0,
        "Stage26 Slurm submit returned error; attempt uncertain; NO retry")
 runids=re.findall(r"Submitted job case\.run with id (\d+)",p.stdout)
 archids=re.findall(r"Submitted job case\.st_archive with id (\d+)",p.stdout)
 ensure(len(runids)==1 and len(archids)==1,
        "Stage26 job IDs ambiguous; inspect squeue/sacct; NO retry")
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
 print("STAGE26 ES-LJu AD400 SUBMITTED",runids[0],archids[0],
       "80x5yr (NO model-years yet verified!) skip_preview_persisted",persisted)
 if not persisted:
  print("WARNING: .submit_options skip_pnl not persistent. Automatic chained resubmits may regenerate stale DATM. Stop and inspect; do not retry case.submit.")
def self_test():
 ensure(5*(79+1)==400 and 2004+400==2404,"AD400 algebra error")
 ensure(NAME.startswith("ES-LJu_B02_FIXNC") and CASE!=SOURCE,
        "Unsafe cloning case identity")
 ensure(SURF_SHA.startswith("d44083a1"),"Site surface SHA")
 # Guard against the former subprocess.run(at=CASE) mistake (valid only for our command helper).
 import ast, inspect, textwrap
 tree=ast.parse(textwrap.dedent(inspect.getsource(start)))
 direct=[n for n in ast.walk(tree) if isinstance(n,ast.Call) and
         isinstance(n.func,ast.Attribute) and
         isinstance(n.func.value,ast.Name) and n.func.value.id=="subprocess" and
         n.func.attr=="run"]
 ensure(len(direct)==3 and all(all(k.arg!="at" for k in n.keywords) for n in direct),
        "Stage26 direct subprocess.run must use cwd=, never at=")
 print("STAGE26 SELF-TEST PASS: separate ES-LJu case, 80x5y, subprocess.run cwd; no writes")
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
 ensure(args.datm_dir is not None,"--datm-dir Stage25 output is required")
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
