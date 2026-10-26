#!/usr/bin/env python3
"""Stage31: gated one-time DIRECT AD400 from four Stage30 verified forest previews.

IMPORTANT SCIENCE: model vectors are explicitly UNAPPROVED exploratory proxy
allocations, not observed complete PFT composition. No met-QC certification is
implied by the CDEPS stream structural audit. Model results must be labelled
sensitivity experiments. Use --audit BEFORE --start. Never repeat --start
after an uncertain outcome. Stage31 does not submit other Batch02 sites.
"""
from __future__ import annotations
import argparse,configparser,importlib.util,json,os,re,resource,socket,subprocess
from pathlib import Path
from datetime import datetime,timezone

HERE=Path(__file__).resolve().parent
S30PATH=HERE/"30_prepare_four_forest_AD5_proxies_no_slurm.py"
ROOT=Path("/iridisfs/scratch/ly3n24/CLM_FATES/experiments/NonCompetitionObserved22/Batch02_10")
LEDGER=ROOT/"stage31_forest_direct_AD400_submission_receipts"
SITES=("DK-Sor","FR-FBn","BE-Bra","CH-Lae")
ACK="SUBMIT_FOUR_BATCH02_EXPLORATORY_FOREST_AD400_ONCE"

def req(ok,s):
 if not ok:raise RuntimeError(str(s))
def get30():
 req(S30PATH.is_file(),"Stage30 source script missing at "+str(S30PATH))
 spec=importlib.util.spec_from_file_location("stage30_four_forest",S30PATH)
 req(spec is not None and spec.loader is not None,"Stage30 loader failure")
 module=importlib.util.module_from_spec(spec)
 spec.loader.exec_module(module)
 req(tuple(module.SITES)==SITES,"Stage30 site group changed")
 return module
def paths(s):
 return LEDGER/(s+"_AD400_submission_attempt.json")
def queue(s):
 p=subprocess.run(["squeue","-h","-u",os.environ.get("USER","ly3n24"),
                   "-o","%i|%j|%T"],capture_output=True,text=True,timeout=70)
 req(p.returncode==0,"Cannot read Slurm queue: "+p.stderr[-1200:])
 return [x for x in p.stdout.splitlines() if ("run."+s+"_B02_FIXNC_FOREST_PROXY_AD5" in x
                                               or "st_archive."+s+"_B02_FIXNC_FOREST_PROXY_AD5" in x)]
def one_audit(m,site):
 z=m.preflight(site,existing=True)
 receipt=json.loads(z["attempt"].read_text())
 req(receipt.get("phase")=="PREVIEW_VERIFIED_NOT_SUBMITTED" and
     receipt.get("slurm_submitted") is False,
     site+": Stage30 CIME preview not completed or previously marked submitted")
 req(m.config(site,z)==receipt.get("verified"),site+": CIME inputs have drifted")
 req(not paths(site).exists(),site+": Stage31 submission attempt exists; NEVER resubmit")
 req(not queue(site),site+": active/queued Slurm job already exists")
 case=z["case"]
 req(m.query(case,"RESUBMIT")=="0",site+": RESUBMIT not zero before first submit")
 # This audit is deliberately not a scientific met-QC release.
 req(receipt["verified"]["scientific_release"] is False,
     site+": expected explicit proxy/PFT-science label missing")
 h=subprocess.run([str(case/"case.submit"),"--help"],cwd=case,
                  capture_output=True,text=True,timeout=100)
 req("--skip-preview-namelist" in h.stdout+h.stderr,
     site+": CIME skip-preview unavailable")
 print("STAGE31 AUDIT PASS",site, "source_met_years",
       receipt["verified"]["met_years"],"PFT_SENSITIVITY",
       m.SITES[site]["scenario"],"UNRELEASED_MET_SCIENCE",flush=True)
 return z
def stack_guard():
 soft,hard=resource.getrlimit(resource.RLIMIT_STACK)
 if soft!=resource.RLIM_INFINITY and soft<64*1024*1024:
  req(hard==resource.RLIM_INFINITY or hard>=64*1024*1024,
      "Inherited stack hard limit below64MiB")
  target=resource.RLIM_INFINITY if hard==resource.RLIM_INFINITY else min(hard,300000*1024)
  resource.setrlimit(resource.RLIMIT_STACK,(target,hard))
 print("STAGE31 STACK",resource.getrlimit(resource.RLIMIT_STACK),"HOST",socket.gethostname(),flush=True)
def one_submit(m,site,z):
 case=z["case"]
 receipt=paths(site)
 req(not receipt.exists(),site+": stage31 ledger already present")
 LEDGER.mkdir(parents=True,exist_ok=True)
 data={"site":site,"case":str(case),"phase":"SUBMISSION_ATTEMPT_UNCERTAIN",
       "PFT_scenario":m.SITES[site]["scenario"],
       "PFT_source":"stage29_EXPLORATORY_NOT_OBSERVED",
       "source_Met_years":z["source_stream"]["first"],
       "target_AD_years":400,"segments":80,"run_segment_years":5,
       "created_utc":datetime.now(timezone.utc).isoformat()}
 with receipt.open("x") as f:
  json.dump(data,f,indent=2);f.write("\n");f.flush();os.fsync(f.fileno())
 m.change(case,"RESUBMIT","79")
 req(m.query(case,"RESUBMIT")=="79",site+": uncertain RESUBMIT state, NO RETRY")
 out=subprocess.run([str(case/"case.submit"),"--skip-preview-namelist"],cwd=case,
                    capture_output=True,text=True,timeout=650)
 print(out.stdout[-6000:],out.stderr[-1200:],flush=True)
 req(out.returncode==0,site+": case.submit failed, attempt uncertain; NO RETRY")
 runs=re.findall(r"Submitted job case\.run with id (\d+)",out.stdout)
 archives=re.findall(r"Submitted job case\.st_archive with id (\d+)",out.stdout)
 req(len(runs)==len(archives)==1,
     site+": submission IDs ambiguous; consult Slurm, NO RETRY")
 opts=configparser.RawConfigParser()
 opts.read(case/".submit_options")
 persist=opts.has_section("SubmitOptions") and opts.getboolean("SubmitOptions","skip_pnl",fallback=False)
 data.update({"phase":"SUBMITTED_AD400_NOT_YET_COMPLETED" if persist
             else "SUBMITTED_SKIP_PREVIEW_UNCERTAIN",
              "run_jobid":runs[0],"archive_jobid":archives[0],
              "skip_preview_persisted":persist,
              "submitted_utc":datetime.now(timezone.utc).isoformat()})
 receipt.write_text(json.dumps(data,indent=2)+"\n")
 print("STAGE31 SUBMITTED",site,runs[0],archives[0],
       "AD400 80x5y","skip_preview_persisted",persist,flush=True)
 if not persist:print("WARNING: check chained resubmits; do NOT run case.submit again")
def main():
 p=argparse.ArgumentParser(description=__doc__)
 g=p.add_mutually_exclusive_group(required=True)
 for name in ("self-test","audit","start","status"):
  g.add_argument("--"+name,action="store_true")
 p.add_argument("--sites",nargs="+",choices=SITES)
 p.add_argument("--confirm",default="")
 a=p.parse_args()
 if a.self_test:
  req(len(SITES)==4 and len(set(SITES))==4,"Site list")
  req(80*5==400 and len(ACK)>16,"400 yr arithmetic")
  print("STAGE31 SELF-TEST PASS; four isolated site identities; no writes")
  return
 m=get30()
 sites=a.sites or list(SITES)
 req(len(sites)==len(set(sites)),"Duplicate site names forbidden")
 if a.status:
  for site in sites:
   file=paths(site)
   state=json.loads(file.read_text()) if file.is_file() else {}
   print("STAGE31 STATUS",site,"receipt_phase",state.get("phase","NONE"),
         "run_id",state.get("run_jobid","-"),
         "archive_id",state.get("archive_jobid","-"),"queue",queue(site))
  return
 m.preload_manifests()
 m.overlay()
 if a.audit:
  bad=[]
  for site in sites:
   try:one_audit(m,site)
   except Exception as exc:
    bad.append(site);print("STAGE31 HOLD",site,str(exc)[-900:])
  print("STAGE31 AUDIT SUMMARY",len(sites)-len(bad),"/",len(sites),"HOLD",bad)
  if bad:raise SystemExit(2)
  return
 req(a.confirm==ACK,"--start requires --confirm "+ACK)
 # All chosen sites must pass read-only preflight before any write/Slurm.
 ready={site:one_audit(m,site) for site in sites}
 stack_guard()
 for site in sites:
  # A failed attempt is deliberately terminal: inspect receipts and Slurm.
  one_submit(m,site,ready[site])
 print("STAGE31 FOREST AD400 FIRST JOBS SUBMITTED (NOT COMPLETED)")
if __name__=="__main__":main()
