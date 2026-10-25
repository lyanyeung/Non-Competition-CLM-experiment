#!/usr/bin/env python3
"""Stage15: directly start exploratory IT-Noe 400-year AD spin-up.
This uses the existing independent Stage13 CIME case, 80 * 5-year chunks:
STOP_N=5, REST_N=5, RESUBMIT=79; no separate 5-year pilot.
ES-LJu is EXCLUDED: 2005-2008 hourly-23 rainfall concentration.
IT-Noe original v3 DATM and Juniperus/broadleaf proxy are not
scientifically approved. This is an explicitly labelled trial.
--audit read-only; --start --confirm ... one-time real Slurm submission.
No original source CIME case, FATES parameters, forcing, surface,
restart, or other site's jobs are modified.
"""
import argparse,hashlib,json,os,re,resource,socket,subprocess
from pathlib import Path
from datetime import datetime,timezone

B=Path("/iridisfs/scratch/ly3n24/CLM_FATES")
C=B/"cases/IT-Noe_B02_FIXNC_AD400_BARE34_SHRUB66_AD5"
E=B/"experiments/NonCompetitionObserved22/Batch02_10"
R=Path("/scratch/ly3n24/CTSM_FATES_OUTPUTS")/C.name/"run"
S=E/"stage12_remaining6_bare_shrub_candidates_v1/IT-Noe/surfdata_IT-Noe_B02_BARESHRUB_PFT_proxy_v1.nc"
A=E/"stage13_two_bare_shrub_AD5_preview/IT-Noe_prepare_attempt.json"
OUT=E/"stage15_IT_NoE_direct_AD400"
STAMP=OUT/"submission_attempt.json"
ACK="SUBMIT_IT_NOE_EXPLORATORY_DIRECT_AD400_ONCE"
MET_SHA="e095da5c749c57a53bb2ea49a267a0b8635daafe0fc68188acbde1210bbc949d"
SURF_SHA="9158bdc492bf09c530193eb2480eab0b72978194314a0c3ee59d1749fc82ed7a"
def err(s):raise RuntimeError(s)
def call(args,cwd=None):
 p=subprocess.run(list(map(str,args)),cwd=cwd,capture_output=True,text=True,timeout=100)
 if p.returncode:err("FAILED: "+repr(args)+" "+(p.stdout+p.stderr)[-1300:])
 return p.stdout.strip()
def q(k):return call([C/"xmlquery",k,"--value"],C)
def sha(p):
 h=hashlib.sha256()
 with Path(p).open("rb") as f:
  for part in iter(lambda:f.read(1<<20),b""):h.update(part)
 return h.hexdigest()
def field(t,k):
 vals=re.findall(r"(?im)^\s*"+re.escape(k)+r"\s*=\s*([^\r\n!]*)",t)
 if len(vals)>1:err("Duplicate FATES key "+k)
 return vals[0].strip().rstrip(",").strip("'\"") if vals else None
def audit():
 if STAMP.exists():err("Stage15 submission already attempted, no duplicate "+str(STAMP))
 if not A.is_file():err("Stage13 receipt absent")
 a=json.loads(A.read_text())
 if a.get("phase")!="PREVIEW_VERIFIED_NOT_SUBMITTED" or \
    a.get("slurm_submitted") is not False or \
    a.get("verified",{}).get("point")!=[40.606176,8.151694]:
  err("Original successful Stage13 preflight ledger changed")
 if not S.is_file() or sha(S)!=SURF_SHA:err("Original Stage12 surface SHA changed")
 for k,v in {"CASE":C.name,"RUN_TYPE":"startup","CONTINUE_RUN":"FALSE",
             "RUN_STARTDATE":"2004-01-01","STOP_OPTION":"nyears",
             "STOP_N":"5","REST_OPTION":"nyears","REST_N":"5",
             "RESUBMIT":"0","RESUBMIT_SETS_CONTINUE_RUN":"TRUE",
             "CLM_ACCELERATED_SPINUP":"on","BUILD_COMPLETE":"TRUE",
             "PTS_DOMAINFILE":"UNSET"}.items():
  if q(k).lower()!=v.lower():err("CIME "+k+" changed: "+q(k))
 for k,v in {"PTS_LAT":40.606176,"PTS_LON":8.151694,"CCSM_CO2_PPMV":376.95}.items():
  if abs(float(q(k))-v)>1e-5:err("CIME point/CO2 changed: "+k)
 if (C/"env_case.xml").read_bytes()!=(C/"LockedFiles/env_case.xml").read_bytes():
  err("Original env_case CIME lock mismatch")
 l=C/"CaseDocs/lnd_in"
 if sha(l)!=sha(R/"lnd_in"):err("RUNDIR FATES lnd_in changed")
 t=l.read_text()
 for k,v in {"fsurdat":str(S),"finidat":"",
             "spinup_state":"2","use_fates":".true.","use_cn":".false.",
             "use_fates_sp":".false.","use_fates_nocomp":".true.",
             "use_fates_fixed_biogeog":".true."}.items():
  if field(t,k)!=v:err("Original verified FATES input changed "+k)
 if sha(C/"CaseDocs/datm.streams.xml")!=MET_SHA or \
    sha(R/"datm.streams.xml")!=MET_SHA:err("Active Stage14 DATM stream changed")
 xml=(C/"CaseDocs/datm.streams.xml").read_text()
 tag="datm_11_IT-Noe_QC_v3_RHcap_20261021_230447"
 paths=set(re.findall(r"/[^\s<>\"']*/"+tag+r"/IT-Noe_DATM_\d{4}\.nc",xml))
 if len(paths)!=22 or any(not Path(p).is_file() for p in paths):
  err("Not all 22 selected original verified QC-v3 annual met files exist")
 for p in (C/"CaseDocs/nuopc.runconfig",R/"nuopc.runconfig"):
  s=p.read_text()
  for key,value in {"scol_lat":40.606176,"scol_lon":8.151694}.items():
   x=re.findall(r"(?im)^\s*"+key+r"\s*=\s*([^\r\n]+)",s)
   if len(x)!=1 or abs(float(x[0])-value)>1e-5:
    err("Actual coupled coordinate mismatch: "+str(p)+" "+key)
 if not (Path(q("EXEROOT"))/"cesm.exe").is_file():err("FATES executable absent")
 if list(R.glob("rpointer*")) or list(R.glob("*.r.*.nc")):
  err("Preexisting restart in prepared startup RUNDIR")
 if (C/"CaseStatus").is_file():
  c=(C/"CaseStatus").read_text(errors="replace")
  if "case.submit starting" in c or "case.run starting" in c:
   err("CIME has prior submission; cannot submit again")
 mlog=Path.home()/"Batch02_Stage14_DATM_QC.log"
 if not mlog.is_file():err("Stage14 numerical report missing")
 log=mlog.read_text(errors="replace")
 m=re.findall(r"(?m)^AGGREGATE IT-Noe (\{[^\n]+\})$",log)
 if len(m)!=1 or not all(json.loads(m[0]).get(k)==0 for k in
              ("invalid","rh_lt5","rh_gt100","jumps","rain_gt40")):
  err("Stage14 actual active IT-Noe forcing numerical screen not clean")
 if MET_SHA not in log or tag not in log or \
    "STAGE14 READONLY MET REVIEW DONE" not in log:
  err("Stage14 actual input source or review incomplete")
 print("STAGE15 AUDIT PASS: IT-Noe exact Stage13 preview; QC-v3 22y selected; original surface/coupler; model AD state")
 print("EXPLORATORY UNAPPROVED; NO ES-LJu; direct AD400=80x5y, 2004->2404")
def start():
 audit()
 limits=resource.getrlimit(resource.RLIMIT_STACK)
 if limits[0]!=resource.RLIM_INFINITY and limits[0]<64*1024**2:
  hard=limits[1]
  if hard!=resource.RLIM_INFINITY and hard<64*1024**2:
   err("Slurm inherited stack too small")
  resource.setrlimit(resource.RLIMIT_STACK,(hard if hard!=resource.RLIM_INFINITY else resource.RLIM_INFINITY,hard))
 print("STACK",resource.getrlimit(resource.RLIMIT_STACK),"HOST",socket.gethostname())
 OUT.mkdir(parents=True,exist_ok=True)
 record={"site":"IT-Noe","phase":"SUBMISSION_ATTEMPT_UNCERTAIN",
         "CIME_CASE":str(C),"years":400,"stop_n":5,"resubmit":79,
         "science":"EXPLORATORY_QCv3_Juniperus_broadleaf_proxy",
         "prior_stage13_receipt":str(A),"started_utc":datetime.now(timezone.utc).isoformat()}
 with STAMP.open("x") as f:
  json.dump(record,f,indent=2);f.write("\n");f.flush();os.fsync(f.fileno())
 call([C/"xmlchange","RESUBMIT=79"],C)
 if q("RESUBMIT")!="79":err("Failed to set 79 resubmits; no retry")
 p=subprocess.run([str(C/"case.submit"),"--skip-preview-namelist"],cwd=C,
                  capture_output=True,text=True,timeout=600)
 print(p.stdout[-6000:],p.stderr[-1500:],flush=True)
 if p.returncode:err("case.submit failed, submit state uncertain; DO NOT RETRY")
 runid=re.findall(r"Submitted job case\.run with id (\d+)",p.stdout)
 archid=re.findall(r"Submitted job case\.st_archive with id (\d+)",p.stdout)
 if len(runid)!=1 or len(archid)!=1:err("Job IDs uncertain; no retry")
 record.update({"phase":"SUBMITTED_MODEL_NOT_YET_VERIFIED","run_job":runid[0],
                "archive_job":archid[0]})
 STAMP.write_text(json.dumps(record,indent=2)+"\n")
 print("DIRECT IT-Noe AD400 SUBMITTED run",runid[0],"archive",archid[0],
       "80 x 5yr segments, currently no completed years proved")
def main():
 p=argparse.ArgumentParser()
 g=p.add_mutually_exclusive_group(required=True)
 g.add_argument("--self-test",action="store_true")
 g.add_argument("--audit",action="store_true")
 g.add_argument("--start",action="store_true")
 p.add_argument("--confirm")
 x=p.parse_args()
 if x.self_test:
  assert 5*(79+1)==400 and 2004+400==2404
  print("SELF-TEST PASS: IT-Noe only, direct 400y 80x5y; no Slurm")
 elif x.audit:audit()
 else:
  if x.confirm!=ACK:p.error("--start requires --confirm "+ACK)
  start()
if __name__=="__main__":main()
