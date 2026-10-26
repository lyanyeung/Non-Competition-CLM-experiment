#!/usr/bin/env python3
"""Stage40 isolated IT-Noe history-output fix & new AD400 CIME clone.

Stage39: failed 4733521 during CLM initial history output: tape1 item4 GPP and
item5 NPP unavailable with FATES. Keep other five requested history fields.
Choose FATES_GPP/FATES_NPP only if exact failed-run hist registry verifies both.
--self-test and --audit-source are READ ONLY.
--prepare creates only a fresh independent same-site CIME case, NO SLURM.
--verify audits new ready case READ ONLY.
--start submits ONLY the fresh case once, after explicit confirmation.
Never alter failed source case, original science/met/params/surface or Slurm jobs.
"""
from __future__ import annotations
import argparse,configparser,hashlib,json,os,re,resource,subprocess
from datetime import datetime,timezone
from pathlib import Path

B=Path("/iridisfs/scratch/ly3n24/CLM_FATES")
E=B/"experiments/NonCompetitionObserved22/Batch02_10"
CTSM=B/"CTSM"
OLDNAME="IT-Noe_B02_FIXNC_AD400_BARE34_SHRUB66_AD5"
OLD=B/"cases"/OLDNAME
NAME="IT-Noe_B02_FIXNC_GPPNPP_HISTFIX_AD400"
NEW=B/"cases"/NAME
O=Path("/scratch/ly3n24/CTSM_FATES_OUTPUTS")
OLDRUN=O/OLDNAME/"run"
RUN=O/NAME/"run"
ARCH=O/"archive"/NAME
RECORDS=E/"stage40_IT_Noe_GPPNPP_histfix_AD400"
PREP=RECORDS/"prepare_attempt.json"
SUBMIT=RECORDS/"submission_attempt.json"
SURF=E/"stage12_remaining6_bare_shrub_candidates_v1/IT-Noe/surfdata_IT-Noe_B02_BARESHRUB_PFT_proxy_v1.nc"
OVERLAY=E/"_private_ctsm_FATES_AD5_namelist_overlay_v1"
SURF_SHA="9158bdc492bf09c530193eb2480eab0b72978194314a0c3ee59d1749fc82ed7a"
MET_SHA="e095da5c749c57a53bb2ea49a267a0b8635daafe0fc68188acbde1210bbc949d"
OLD_NML_SHA="a270910c91f55cb492d417109b034a39a1d05ba84c0109434b1c5db7258aeea6"
OLD_LOG_SHA="be88700306ad1347d20a50c02f7e9fa82e6253c63dc37a68eef6d81d8a7c9158"
BEFORE=["TOTSOMC","TOTSOMN","TLAI","GPP","NPP","TWS","H2OSNO"]
AFTER=["TOTSOMC","TOTSOMN","TLAI","FATES_GPP","FATES_NPP","TWS","H2OSNO"]
P_ACK="PREPARE_IT_NOE_STAGE40_GPPNPP_NEW_CASE_NO_SUBMIT"
S_ACK="SUBMIT_IT_NOE_STAGE40_GPPNPP_AD400_ONCE"
TAPE=re.compile(r"(?ims)^[ \t]*hist_fincl1[ \t]*=[ \t]*(.*?)(?=^[ \t]*[A-Za-z_]\w*[ \t]*=|^[ \t]*/[ \t]*$|\Z)")
QUOTES=re.compile(r"['\"]([^'\"]+)['\"]")
REGISTER=re.compile(r"(?m)^\s*\d+\s+([A-Za-z][A-Za-z0-9_]+)\s{2,}")

def need(ok,why):
 if not ok:raise RuntimeError(str(why))
def sha(path):
 h=hashlib.sha256()
 with Path(path).open("rb") as f:
  for v in iter(lambda:f.read(1<<20),b""):h.update(v)
 return h.hexdigest()
def call(args,cwd=None,timeout=180):
 p=subprocess.run(list(map(str,args)),cwd=cwd,text=True,capture_output=True,timeout=timeout)
 need(p.returncode==0,"CMD FAILED "+repr(args)+"\n"+(p.stdout+p.stderr)[-3000:])
 return p.stdout.strip()
def q(case,key):return call([case/"xmlquery",key,"--value"],cwd=case,timeout=80)
def ch(case,key,val):return call([case/"xmlchange",key+"="+str(val)],cwd=case,timeout=90)
def fields(text):
 m=list(TAPE.finditer(text))
 need(len(m)==1,"Expected unique hist_fincl1 assignment")
 return [z.strip() for z in QUOTES.findall(m[0].group(1))]
def fix(text):
 m=list(TAPE.finditer(text))
 need(len(m)==1 and fields(text)==BEFORE,
      "user_nl_clm original hist_fincl1 not exactly 7 expected fields")
 corrected="hist_fincl1 = "+", ".join("'"+v+"'" for v in AFTER)+"\n"
 output=text[:m[0].start()]+corrected+text[m[0].end():]
 need(fields(output)==AFTER,"History field replacement not exact")
 return output
def nmlkey(text,key):
 x=re.findall(r"(?im)^\s*"+re.escape(key)+r"\s*=\s*([^\r\n!]*)",text)
 need(len(x)==1,"Missing or duplicate effective namelist key "+key)
 return x[0].strip().rstrip(",").strip("'\"").strip()
def source():
 need(OLD.is_dir() and OLDRUN.is_dir(),"Stage15 original site case or RUN missing")
 odoc=OLD/"CaseDocs/lnd_in"; rdoc=OLDRUN/"lnd_in"
 need(odoc.is_file() and rdoc.is_file() and sha(odoc)==sha(rdoc)==OLD_NML_SHA,
      "Stage39 original effective lnd_in SHA changed")
 need(fields(odoc.read_text())==BEFORE,"Stage39 exact 7 original field list changed")
 logs=list(OLDRUN.glob("lnd.log.4733521.*"))
 need(len(logs)==1 and sha(logs[0])==OLD_LOG_SHA,
      "Stage38 original histFileMod failure log SHA changed")
 log=logs[0].read_text(errors="replace")
 need("htapes_fieldlist ERROR: GPP in fincl(" in log and
      "ERROR in histFileMod.F90 at line 899" in log,
      "Expected exact historical fatal not found")
 regs={v.upper() for v in REGISTER.findall(log)}
 need(len(regs)>=1000,"Cannot recover full model registered-field inventory")
 need(set(AFTER).issubset(regs) and "GPP" not in regs and "NPP" not in regs,
      "FATES_GPP/NPP unavailable or original GPP/NPP now available; STOP: "+
      repr(sorted(set(AFTER)-regs)))
 need(sha(OLD/"CaseDocs/datm.streams.xml")==MET_SHA and
      sha(OLDRUN/"datm.streams.xml")==MET_SHA,"Original 22y DATM stream changed")
 need(SURF.is_file() and sha(SURF)==SURF_SHA,"Original PFT proxy SHA changed")
 for key,value in {"fsurdat":str(SURF),"finidat":"","spinup_state":"2",
                   "use_fates":".true.","use_fates_nocomp":".true.",
                   "use_fates_fixed_biogeog":".true.","use_fates_sp":".false.",
                   "use_cn":".false."}.items():
  need(nmlkey(odoc.read_text(),key)==value,
       "Original FATES/PFT science changed "+key)
 need(q(OLD,"RUN_STARTDATE")=="2004-01-01" and
      q(OLD,"CALENDAR")=="NO_LEAP" and q(OLD,"RESUBMIT")=="79",
      "Source case prior submitted state changed")
 need((OLD/"env_case.xml").read_bytes()==(OLD/"LockedFiles/env_case.xml").read_bytes(),
      "Original case CIME env case lock changed")
 need((OLD/"user_nl_clm").is_file(),"Source user_nl_clm missing")
 fix((OLD/"user_nl_clm").read_text())
 ledger=E/"stage15_IT_NoE_direct_AD400/submission_attempt.json"
 need(ledger.is_file(),"Original one-time Stage15 submit receipt missing")
 attempt=json.loads(ledger.read_text())
 need(attempt.get("run_job")=="4733521" and
      attempt.get("skip_preview_persisted") is True,
      "Original submitted job receipt differs")
 exe=Path(q(OLD,"EXEROOT"))/"cesm.exe"
 need(exe.is_file(),"Same-site original executable missing")
 need(not list(OLDRUN.glob("rpointer*")) and not list(OLDRUN.glob("*.r.*.nc")),
      "Source generated a restart: re-evaluate before new cold start")
 print("STAGE40 SOURCE AUDIT PASS: original GPP/NPP not registered, FATES_GPP/FATES_NPP both registered")
 print("STAGE40 PRESERVED ORIGINAL 22-YR MET, PFT, EXECUTABLE",exe)
 return exe
def stream(case):
 a=case/"CaseDocs/datm.streams.xml"
 b=Path(q(case,"RUNDIR"))/"datm.streams.xml"
 need(a.is_file() and b.is_file() and sha(a)==sha(b)==MET_SHA,
      "Original exact 22y datm stream not retained")
def verify_new(resubmit=0):
 exe=source()
 need(NEW.is_dir(),"Independent Stage40 new case does not exist")
 for k,v in {"CASE":NAME,"RUN_TYPE":"startup","RUN_STARTDATE":"2004-01-01",
             "RESUBMIT":str(resubmit),"STOP_OPTION":"nyears","STOP_N":"5",
             "REST_OPTION":"nyears","REST_N":"5","CLM_ACCELERATED_SPINUP":"on",
             "RUNDIR":str(RUN),"DOUT_S_ROOT":str(ARCH),
             "BUILD_COMPLETE":"TRUE"}.items():
  need(q(NEW,k).lower()==v.lower(),"Stage40 new CIME value changed "+k)
 if resubmit==0:need(q(NEW,"CONTINUE_RUN").lower()=="false",
                     "Stage40 initial cold start not configured")
 for k,v in {"PTS_LAT":40.606176,"PTS_LON":8.151694,"CCSM_CO2_PPMV":376.95}.items():
  need(abs(float(q(NEW,k))-v)<.0001,
       "Model/coupler site constant changed "+k)
 need(Path(q(NEW,"EXEROOT"))/"cesm.exe"==exe,
      "Original compiled executable was not reused")
 need((NEW/"env_case.xml").read_bytes()==(NEW/"LockedFiles/env_case.xml").read_bytes(),
      "New case CIME env lock differs")
 stream(NEW)
 orig=(OLD/"CaseDocs/lnd_in").read_text()
 for p in (NEW/"CaseDocs/lnd_in",RUN/"lnd_in"):
  need(p.is_file() and fields(p.read_text())==AFTER,
       "Effective new 7 history fields not fixed: "+str(p))
  for k in ("fsurdat","fates_paramfile","finidat","spinup_state","use_cn",
            "use_fates","use_fates_sp","use_fates_nocomp",
            "use_fates_fixed_biogeog"):
   need(nmlkey(p.read_text(),k)==nmlkey(orig,k),
        "Unexpected scientific parameter change "+k+" at "+str(p))
 need(sha(NEW/"CaseDocs/lnd_in")==sha(RUN/"lnd_in"),
      "New effective land namelists differ")
 need(fields((NEW/"user_nl_clm").read_text())==AFTER,
      "New durable user_nl_clm not patched")
 for p in (NEW/"CaseDocs/nuopc.runconfig",RUN/"nuopc.runconfig"):
  need(p.is_file(),"Stage40 coupled point config missing")
  for k,v in {"scol_lat":40.606176,"scol_lon":8.151694}.items():
   vals=re.findall(r"(?im)^\s*"+k+r"\s*=\s*([^\r\n]+)",p.read_text())
   need(len(vals)==1 and abs(float(vals[0])-v)<.0001,
        "Effective coupler site point changed "+k)
 need(not list(RUN.glob("rpointer*")) and not list(RUN.glob("*.r.*.nc")) and
      not list(RUN.glob("*.h0*.nc")),"New case contains pre-existing model output")
 print("STAGE40 NEW CASE AUDIT PASS | isolated case; seven registered tape1 fields; same source DATM/PFT/exe")
 return {"case":str(NEW),"history_namelist_sha256":sha(NEW/"CaseDocs/lnd_in"),
         "datm_sha256":MET_SHA}
def prepare():
 source()
 need(not any(x.exists() or x.is_symlink() for x in (NEW,RUN,ARCH,PREP,SUBMIT)),
      "Stage40 new case already exists or partial attempt - never rerun prepare")
 need((OVERLAY/"bld/CLMBuildNamelist.pm").is_file() and
      (OVERLAY/"bld/build-namelist").is_file(),
      "Known private FATES accelerated spinup namelist overlay missing")
 RECORDS.mkdir(parents=True,exist_ok=True)
 with PREP.open("x") as f:
  json.dump({"phase":"PREPARATION_ATTEMPT_UNCERTAIN","created_utc":datetime.now(timezone.utc).isoformat()},f)
  f.flush();os.fsync(f.fileno())
 print("STAGE40 CREATING FRESH CASE, NO SLURM",NEW,flush=True)
 call([CTSM/"cime/scripts/create_clone","--case",NEW,"--clone",OLD,"--keepexe"],
      cwd=CTSM/"cime/scripts",timeout=600)
 for k,v in (("RUNDIR",RUN),("DOUT_S_ROOT",ARCH),("RUN_TYPE","startup"),
             ("CONTINUE_RUN","FALSE"),("RUN_STARTDATE","2004-01-01"),
             ("STOP_OPTION","nyears"),("STOP_N","5"),
             ("REST_OPTION","nyears"),("REST_N","5"),("RESUBMIT","0"),
             ("CLM_ACCELERATED_SPINUP","on"),("CLM_FORCE_COLDSTART","on"),
             ("PTS_LAT","40.606176"),("PTS_LON","8.151694"),
             ("PTS_DOMAINFILE","UNSET")):ch(NEW,k,v)
 if not (NEW/".case.run").is_file():call([NEW/"case.setup"],cwd=NEW,timeout=400)
 nl=NEW/"user_nl_clm"
 need(nl.is_file(),"New user_nl_clm missing")
 nl.write_text(fix(nl.read_text()))
 lock=(NEW/"LockedFiles/env_case.xml").read_bytes()
 need((NEW/"env_case.xml").read_bytes()==lock,"Cloned env case XML lock not equal")
 oldroot=q(NEW,"COMP_ROOT_DIR_LND")
 need(oldroot=="$SRCROOT" or Path(oldroot).resolve()==CTSM.resolve(),
      "Unexpected CTSM source tree when enabling local namelist overlay")
 try:
  ch(NEW,"COMP_ROOT_DIR_LND",OVERLAY)
  call([NEW/"preview_namelists"],cwd=NEW,timeout=700)
 finally:
  ch(NEW,"COMP_ROOT_DIR_LND","$SRCROOT")
 need((NEW/"env_case.xml").read_bytes()==lock,
      "New CIME lock did not restore")
 data=verify_new(0)
 data.update({"phase":"PREPARED_NEW_HISTFIX_NOT_SUBMITTED",
              "source_failed_job":"4733521",
              "edited_history_fields":{"GPP":"FATES_GPP","NPP":"FATES_NPP"},
              "created_utc":datetime.now(timezone.utc).isoformat()})
 PREP.write_text(json.dumps(data,indent=2)+"\n")
 print("STAGE40 PREPARE PASS (NO SLURM)",NEW)
def audit_new():
 need(PREP.is_file(),"Stage40 first --prepare is required")
 rec=json.loads(PREP.read_text())
 need(rec.get("phase")=="PREPARED_NEW_HISTFIX_NOT_SUBMITTED",
      "Stage40 earlier preparation attempt uncertain")
 res=q(NEW,"RESUBMIT")
 need(res in ("0","79"),"Stage40 unexpected RESUBMIT")
 data=verify_new(int(res))
 need(rec["history_namelist_sha256"]==data["history_namelist_sha256"] and
      rec["datm_sha256"]==data["datm_sha256"],"Prepared exact inputs changed")
 if SUBMIT.exists():print("STAGE40 ALREADY SUBMITTED/ATTEMPTED: NEVER SUBMIT AGAIN")
 print("STAGE40 READONLY AUDIT SUCCESS",NEW,"RESUBMIT",res)
def start():
 audit_new()
 need(not SUBMIT.exists() and q(NEW,"RESUBMIT")=="0",
      "Already submitted or CIME start modified")
 queue=subprocess.run(["squeue","-h","-u",os.getenv("USER","ly3n24"),
                       "-o","%i|%j|%T"],capture_output=True,text=True,timeout=70)
 need(queue.returncode==0 and NAME not in queue.stdout,
      "Cannot check queue or new-case duplicate job found")
 helptext=subprocess.run([str(NEW/"case.submit"),"--help"],
                         cwd=NEW,capture_output=True,text=True,timeout=70)
 need("--skip-preview-namelist" in helptext.stdout+helptext.stderr,
      "CIME --skip-preview-namelist unavailable")
 soft,hard=resource.getrlimit(resource.RLIMIT_STACK)
 if soft!=resource.RLIM_INFINITY and soft<64*1024*1024:
  need(hard==resource.RLIM_INFINITY or hard>=64*1024*1024,
       "Inherited hard stack limit too small")
  resource.setrlimit(resource.RLIMIT_STACK,(hard,hard))
 rec={"phase":"SUBMISSION_ATTEMPT_UNCERTAIN","case":str(NEW),
      "old_failed_job":"4733521","years":400,"segments":80,
      "science":"EXPLORATORY_IT_NOE_QCv3_JUNIPERUS_BROADLEAF_SHRUB",
      "attempt_utc":datetime.now(timezone.utc).isoformat()}
 with SUBMIT.open("x") as f:
  json.dump(rec,f,indent=2);f.flush();os.fsync(f.fileno())
 ch(NEW,"RESUBMIT",79)
 need(q(NEW,"RESUBMIT")=="79","Uncertain RESUBMIT; never rerun")
 p=subprocess.run([str(NEW/"case.submit"),"--skip-preview-namelist"],
                  cwd=NEW,text=True,capture_output=True,timeout=650)
 print(p.stdout[-7000:],p.stderr[-1800:])
 need(p.returncode==0,"CIME submission uncertain; NEVER RETRY")
 ids=re.findall(r"Submitted job case\.run with id (\d+)",p.stdout)
 arc=re.findall(r"Submitted job case\.st_archive with id (\d+)",p.stdout)
 need(len(ids)==len(arc)==1,"Submitted Slurm IDs ambiguous; NEVER RETRY")
 ini=configparser.RawConfigParser()
 ini.read(NEW/".submit_options")
 persisted=ini.has_section("SubmitOptions") and ini.getboolean("SubmitOptions","skip_pnl",fallback=False)
 rec.update({"phase":"SUBMITTED_NOT_YET_COMPLETED",
             "run_jobid":ids[0],"archive_jobid":arc[0],
             "skip_preview_persisted":persisted})
 SUBMIT.write_text(json.dumps(rec,indent=2)+"\n")
 print("STAGE40 IT-NOE AD400 SUBMITTED",ids[0],arc[0],
       "skip_preview_persisted",persisted)
 if not persisted:print("WARNING automatic chained resubmits may regenerate namelists; stop and review")
def main():
 parser=argparse.ArgumentParser(description=__doc__)
 modes=parser.add_mutually_exclusive_group(required=True)
 for mode in ("self-test","audit-source","prepare","verify","start"):
  modes.add_argument("--"+mode,action="store_true")
 parser.add_argument("--confirm",default="")
 args=parser.parse_args()
 if args.self_test:
  assert BEFORE[3:5]==["GPP","NPP"] and AFTER[3:5]==["FATES_GPP","FATES_NPP"]
  trial="hist_fincl1 = 'TOTSOMC','TOTSOMN','TLAI','GPP','NPP','TWS','H2OSNO'\nhist_mfilt = 12\n"
  assert fields(trial)==BEFORE and fields(fix(trial))==AFTER
  assert len(OLD_LOG_SHA)==len(OLD_NML_SHA)==len(MET_SHA)==64
  print("STAGE40 SELF-TEST PASS | isolated 7-field history correction, no writes")
 elif args.audit_source:
  need(not args.confirm,"Do not confirm audit-source")
  source()
 elif args.prepare:
  need(args.confirm==P_ACK,"--prepare needs --confirm "+P_ACK)
  prepare()
 elif args.verify:
  need(not args.confirm,"Do not confirm verify")
  audit_new()
 else:
  need(args.confirm==S_ACK,"--start needs --confirm "+S_ACK)
  start()
if __name__=="__main__":main()
