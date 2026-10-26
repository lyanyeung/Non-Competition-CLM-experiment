#!/usr/bin/env python3
"""Stage38 | IT-Noe failed AD400 job 4733521: source-aware, READ ONLY triage.

No CIME, NetCDF, Slurm, source or job writes. Inspect job & steps accounting,
CIME status, effective FATES/DATM config, Slurm stdout/stderr paths returned
by accounting and selected bounded logs; never retry or cancel any job.
Especially distinguish failed CIME launch from model physics/RH crashes.
"""
from __future__ import annotations
import argparse
import collections
import json
import os
import re
import subprocess
from pathlib import Path

B=Path("/iridisfs/scratch/ly3n24/CLM_FATES")
E=B/"experiments/NonCompetitionObserved22/Batch02_10"
C=B/"cases/IT-Noe_B02_FIXNC_AD400_BARE34_SHRUB66_AD5"
R=Path("/scratch/ly3n24/CTSM_FATES_OUTPUTS")/C.name/"run"
A=Path("/scratch/ly3n24/CTSM_FATES_OUTPUTS")/"archive"/C.name
REC=E/"stage15_IT_NoE_direct_AD400/submission_attempt.json"
JOB="4733521"
ARCH="4733522"
PAT=re.compile(
 r"(?i)(?:\b(?:ERROR|FATAL|FAIL(?:ED|URE)?|ABORT(?:ING|ED)?|"
 r"EXCEPTION|TRACEBACK|SIG(?:SEGV|BUS|KILL)|SEGV|SEGMENTATION|"
 r"NaN|INFINITY|negative|HumanIndex|MPI_Abort|MemoryError|"
 r"OOM|OUT_OF_MEMORY|exceeded memory|cannot open|file not found|"
 r"forrtl|floating point|pnetcdf|netcdf|esmf error|stack overflow|"
 r"case\.run.*failed)\b)"
)
LOG_GLOBS=(
 "cesm.log*","cpl.log*","lnd.log*","atm.log*","ice.log*",
 "rof.log*","*.err","*.stderr","*.out","*.stdout",
 "slurm-*","*.log","*.log.*","*4733521*","run.*"
)
def call(args,limit=13000,timeout=45):
 try:
  p=subprocess.run(args,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                   text=True,errors="replace",timeout=timeout,check=False)
  data=(p.stdout+"\n"+p.stderr)
  print("CMD",repr(args),"RC",p.returncode)
  print(data[-limit:].strip())
  return p.returncode,p.stdout
 except (OSError,subprocess.TimeoutExpired) as err:
  print("CMD_UNAVAILABLE",repr(args),str(err))
  return -1,""
def clip(path,read_limit=48*1024*1024):
 try:
  if not path.is_file():
   print("LOG_NOT_FOUND",path);return
  size=path.stat().st_size
  print("\n--- LOG",path,"bytes",size,"---")
  # Do not read arbitrary model binary or enormous multi-year output.
  if size>read_limit:
   print("TOO_LARGE_FOR_AUTO_PARSE - inspect tail manually");return
  tail=collections.deque(maxlen=45)
  hits=collections.deque(maxlen=22)
  with path.open("r",encoding="utf-8",errors="replace") as f:
   for n,line in enumerate(f,1):
    line=line.rstrip("\n")
    tail.append((n,line))
    if PAT.search(line):
     hits.append((n,line))
  for label,rows in (("ERROR_MATCHES",hits),("TAIL",tail)):
   print(label,len(rows))
   for number,line in rows:
    print(str(number).rjust(7),line[:550])
 except (OSError,UnicodeError) as err: print("LOG_READ_ERROR",path,str(err))
def unique(paths):
 out=[];seen=set()
 for p in paths:
  s=str(p)
  if s not in seen:seen.add(s);out.append(p)
 return out
def gather_paths_from_accounting():
 cmd=["sacct","-n","-P","-X","-j",JOB+","+ARCH,
      "--format=JobIDRaw,StdOut,StdErr,WorkDir"]
 rc,s=call(cmd)
 result=[]
 if rc:
  print("STDOUT_ACCOUNTING_MISSING; fall back to case and rundir search")
  return result
 for line in s.splitlines():
  fields=line.split("|")
  if len(fields)<4:continue
  identifier,stdout,stderr,workdir=fields[:4]
  if identifier not in (JOB,ARCH):continue
  for p in (stdout,stderr):
   p=p.strip()
   if p and p.upper() not in ("UNKNOWN","NONE","N/A"):
    for k,v in (("%j",identifier),("%J",identifier),("%x","run."+C.name)):
     p=p.replace(k,v)
    item=Path(p)
    if not item.is_absolute() and workdir.startswith("/"):
     item=Path(workdir)/item
    result.append(item)
  print("ACCOUNTING_LOG_LOCATIONS",identifier,"STDOUT",stdout,
        "STDERR",stderr,"WORKDIR",workdir)
 return result
def report():
 print("STAGE38 IT-NOE AD400 FAILURE FORENSICS READ-ONLY")
 print("HISTORICAL_REFERENCE_RUN",JOB,"ARCHIVE",ARCH)
 print("CASE",C,"EXISTS",C.is_dir(),"RUN",R,"EXISTS",R.is_dir())
 print("ARCHIVE",A,"EXISTS",A.is_dir())
 if REC.is_file():
  try:
   d=json.loads(REC.read_text())
   print("STAGE15_RECEIPT",
         {k:d.get(k) for k in ("phase","run_job","archive_job","skip_preview_persisted","science")})
  except (OSError,ValueError) as err:print("RECEIPT_READ_ERROR",err)
 else:print("STAGE15_RECEIPT_MISSING",REC)
 print("\n====== JOB + STEPS ======")
 call(["sacct","-j",JOB+","+ARCH,
       "--format=JobID%22,JobName%45,State%25,ExitCode,Elapsed,NodeList%18,MaxRSS,ReqMem,Reason%35"],
      limit=19000)
 print("\n====== SLURM JOB DETAILS IF RETAINED ======")
 call(["scontrol","show","job",JOB],limit=9500)
 print("\n====== JOB STDOUT/STDERR PATHS ======")
 extras=gather_paths_from_accounting()
 print("\n====== CIME XML RUNNING STATE (READ ONLY) ======")
 if C.is_dir():
  for key in ("CASE","RUN_TYPE","CONTINUE_RUN","RESUBMIT","STOP_N","REST_N",
              "CLM_ACCELERATED_SPINUP","BUILD_COMPLETE","EXEROOT","RUNDIR"):
   if (C/"xmlquery").is_file():
    call([str(C/"xmlquery"),key,"--value"],limit=300)
 for p in (C/"CaseStatus",C/".submit_options"):
  if p.is_file():clip(p,2*1024*1024)
 print("\n====== EFFECTIVE CLM INPUT FLAGS ======")
 for p in (C/"CaseDocs/lnd_in",R/"lnd_in"):
  if not p.is_file():continue
  print("CONFIG",p)
  for line in p.read_text(errors="replace").splitlines():
   if re.match(r"\s*(?:use_fates|use_fates_nocomp|use_fates_fixed_biogeog|"
               r"spinup_state|finidat|fsurdat|fates_paramfile|co2_ppmv)\s*=",line):
    print(line[:400])
 print("\n====== LOG PATH CANDIDATES ======")
 logs=list(extras)
 roots=(R,C,C/"logs",C/"timing",Path.home())
 for root in roots:
  if not root.is_dir():continue
  for pattern in LOG_GLOBS:
   try:
    logs.extend(p for p in root.glob(pattern)
                if p.is_file() and
                (root!=Path.home() or JOB in p.name or C.name in p.name))
   except OSError as err:print("SEARCH_ERROR",root,pattern,str(err))
 logs=unique(logs)
 # Print any explicitly reported stdout/err first, then the most recent case logs.
 first=unique(extras)
 rest=sorted((p for p in logs if p not in first),
             key=lambda x:x.stat().st_mtime if x.exists() else 0,reverse=True)
 selected=unique(first+rest[:24])
 print("DISCOVERED",len(logs),"INSPECTING",len(selected))
 for p in selected:clip(p)
 print("\n====== CHECK FOR RESTART ARTIFACTS ======")
 for root in (R,A):
  if not root.is_dir():continue
  for pattern in ("rpointer*","*.r.*.nc","*.h0*.nc"):
   q=sorted(root.glob(pattern))
   print(str(root),pattern,"COUNT",len(q),
         "SAMPLES",[p.name for p in q[:7]])
 print("\nSTAGE38 END - diagnosis only; no Slurm submits, cancellations or file writes")
def main():
 ap=argparse.ArgumentParser(description=__doc__)
 g=ap.add_mutually_exclusive_group(required=True)
 g.add_argument("--self-test",action="store_true")
 g.add_argument("--diagnose",action="store_true")
 a=ap.parse_args()
 if a.self_test:
  assert JOB=="4733521" and ARCH=="4733522"
  assert PAT.search("FATAL: negative RH")
  assert PAT.search("segmentation fault")
  assert PAT.search("MPI_Abort")
  assert not PAT.search("CLM steps are progressing")
  print("STAGE38 SELF-TEST PASS: historical exact job IDs, error parser; READ ONLY")
 else:report()
if __name__=="__main__":main()
