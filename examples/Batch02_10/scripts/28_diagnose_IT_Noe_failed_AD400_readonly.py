#!/usr/bin/env python3
"""Read-only IT-Noe Stage15 Slurm 4733521 failure context. No retries, no scancel."""
import argparse, subprocess, re
from pathlib import Path
BASE=Path("/iridisfs/scratch/ly3n24/CLM_FATES")
NAME="IT-Noe_B02_FIXNC_AD400_BARE34_SHRUB66_AD5"
CASE=BASE/"cases"/NAME
RUN=Path("/scratch/ly3n24/CTSM_FATES_OUTPUTS")/NAME/"run"
ARCH=Path("/scratch/ly3n24/CTSM_FATES_OUTPUTS")/"archive"/NAME
JOB="4733521"
PAT=re.compile(r"error|fatal|abort|segmentation|signal 11|traceback|exception|rh\b|humanindex|esmf|mesh|stack|mpi_abort|failed|nan|negative",re.I)
def run(args):
 p=subprocess.run(args,capture_output=True,text=True,timeout=60,check=False)
 print("$ "+" ".join(args), "RC",p.returncode)
 print((p.stdout+p.stderr)[-12000:])
def excerpt(path):
 try:
  sz=path.stat().st_size
  if sz>300*1024*1024:
   print("SKIP VERY LARGE",path,sz)
   return
  with path.open(errors="replace") as f: lines=f.readlines()
  interesting=[i for i,l in enumerate(lines) if PAT.search(l)]
  print("FILE",str(path),"bytes",sz,"lines",len(lines),"matches",len(interesting))
  selected=set()
  for i in interesting[-12:]:
   selected.update(range(max(0,i-3),min(len(lines),i+4)))
  selected.update(range(max(0,len(lines)-45),len(lines)))
  for i in sorted(selected):
   print(f"{i+1}: {lines[i].rstrip()[:480]}")
 except Exception as e:print("READ ISSUE",path,type(e).__name__,str(e))
def main():
 p=argparse.ArgumentParser()
 p.add_argument("--self-test",action="store_true")
 p.add_argument("--diagnose",action="store_true")
 a=p.parse_args()
 if a.self_test:
  assert PAT.search("ESMF fatal ERROR") and NAME.startswith("IT-Noe")
  print("STAGE28 SELF-TEST PASS | read-only");return
 if not a.diagnose:p.error("choose --self-test or --diagnose")
 print("IT-Noe failed run 4733521; archive 4733522 DependencyNeverSatisfied")
 run(["sacct","-X","-j","4733521,4733522","--format=JobID,JobName%80,State,Elapsed,ExitCode,NodeList"])
 run(["scontrol","show","job","4733521"])
 for k,folder in (("CASE",CASE),("RUN",RUN),("ARCHIVE",ARCH)):
  print(k,folder,"exists",folder.is_dir())
 if (CASE/"CaseStatus").is_file():excerpt(CASE/"CaseStatus")
 possible=[]
 for root in (RUN,CASE):
  if not root.is_dir():continue
  for pattern in ("cesm.log*","cpl.log*","lnd.log*","atm.log*","*.err","*.out","slurm-*","*.log.*"):
   possible.extend(p for p in root.glob(pattern) if p.is_file())
 unique={str(x):x for x in possible}
 logs=sorted(unique.values(),key=lambda q:q.stat().st_mtime,reverse=True)[:16]
 if not logs:print("NO RUN/CASE LOGS; check Slurm StdOut/StdErr filenames in scontrol")
 for file in logs:excerpt(file)
 print("NO MODIFICATIONS; DO NOT REPEAT STAGE15 --start")
if __name__=="__main__":main()
