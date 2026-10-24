#!/usr/bin/env python3
"""Read-only AmeriFlux Batch01 checkpoint before ANY new AD400→Normal400 case.

Cross-repository provenance from CLM-FATES-single-site-workflows:
  Stage80: 18 original RH<1% native ERA5 coupled corrections, 1091 RH1-5 kept
  Stage81: 213 annual NOLEAP 30min DATM technical files
  Stage82: operator-confirmed 213/213 SHA pass, no active DATM streams

This script never writes, changes CIME files, or submits Slurm. It does not
approve ZBOT, the DATM clock, FATES PFT fractions or an 800-year run.
"""
from __future__ import annotations
import argparse,csv,hashlib,json,re
from pathlib import Path
from collections import Counter

BASE=Path("/iridisfs/scratch/ly3n24/CLM_FATES")
AMF=BASE/"experiments/AmeriFlux_MultiSite_10"
STAGE80=AMF/"reports/stage80_RH_lt1_final_20261024T123353Z"
STAGE81=AMF/"reports/stage81_DATM_technical_20261024T162235Z"
STAGE82=AMF/"reports/stage82_DATM_case_integration_preflight_20261024T231124502670Z"
EXPECTED={"BR-Ma2":18,"CA-Ca3":24,"CA-Cbo":29,"CA-LP1":18,
          "CA-Man":15,"CA-TP1":22,"CA-TP3":22,"CA-TP4":22,
          "US-Aud":23,"US-Bar":20}
REPO=Path(__file__).resolve().parents[3]
OTHER=REPO.parent/"CLM-FATES-single-site-workflows"
def digest(path):
 h=hashlib.sha256()
 with path.open("rb") as f:
  for b in iter(lambda:f.read(1024*1024),b""):h.update(b)
 return h.hexdigest()
def load(path):
 return json.loads(path.read_text(encoding="utf-8"))
def stage31_status():
 folders=sorted((AMF/"reports").glob("stage31_provisional_ZBOT_scenarios_*"),
                reverse=True)
 for d in folders:
  p=d/"01_provisional_site_height_policies.json"
  if not p.is_file():continue
  x=load(p)
  if x.get("method")!="AmeriFlux_STAGE31_BASE_STATIC_DYNAMIC_POLICY_SCENARIOS":
   continue
  return d,x
 return None,None
def sample_cases():
 root=BASE/"cases"
 if not root.is_dir():return []
 found=[]
 for p in sorted(root.iterdir()):
  if not p.is_dir() or not (p/"env_run.xml").is_file():continue
  if any(s in p.name for s in ("AD400","SPINUP500","SPINUP1000","DE-Tha")):
   docs=p/"CaseDocs"
   found.append(dict(case=str(p),name=p.name,
      datm_in=(docs/"datm_in").is_file(),
      legacy_stream=bool(list(docs.glob("datm.streams*"))) if docs.is_dir() else False,
      user_nl_datm=(p/"user_nl_datm").is_file(),
      xmlquery=(p/"xmlquery").is_file(),
      generated_lnd_in=(docs/"lnd_in").is_file()))
 return found[:25]
def main():
 p=argparse.ArgumentParser(description=__doc__)
 p.add_argument("--check",action="store_true",help="Read-only exact scientific / CIME preflight")
 p.add_argument("--self-test",action="store_true")
 args=p.parse_args()
 if args.self_test:
  assert len(EXPECTED)==10 and sum(EXPECTED.values())==213
  print("SELF-TEST PASS: unique ten AmeriFlux stations / 213 annual NOLEAP NC expectations")
  return
 if not args.check:p.error("specify --check or --self-test")
 if not STAGE82.joinpath("manifest.json").is_file():
  raise RuntimeError("User-confirmed Stage82 audit report missing")
 m82=load(STAGE82/"manifest.json")
 if (m82.get("stage")!=82 or m82.get("sites")!=10 or m82.get("annual_files")!=213
     or m82.get("verified_annual_files_sha256")!=213):
  raise RuntimeError("Stage82 ten-site ALL-213 SHA audit receipt mismatch")
 m81=load(STAGE81/"manifest.json")
 if m81.get("stage")!=81 or m81.get("all_annual_netcdf_files")!=213:
  raise RuntimeError("Stage81 213 NetCDF manifest incorrect")
 m80=load(STAGE80/"manifest.json")
 if (m80.get("stage")!=80 or m80.get("native_ERA5_joint_replaced_rows")!=18
     or m80.get("original_RH_1to5_restored_and_retained")!=1091):
  raise RuntimeError("Stage80 RH threshold changed")
 if digest(STAGE81/"manifest.json")!=m82["input_stage81_manifest_sha256"]:
  raise RuntimeError("Stage81 manifest was modified after Stage82 validation")
 if digest(STAGE80/"manifest.json")!=m81["stage80_receipt_sha256"]:
  raise RuntimeError("Stage80 receipt was modified after Stage81")
 actual={r["site"]:r for r in m81["sites"]}
 if set(actual)!=set(EXPECTED):raise RuntimeError("Stage81 sites do not match known AmeriFlux cohort")
 print("MET_SOURCE_CHAIN PASS: STAGE80(18 RH<1) -> STAGE81(213 NC) -> STAGE82(213 SHA verified)")
 print("NO REAL DATM STREAM ACTIVATED: reference-case scan still required")
 print("ACTIVE AD400 NORMAL400 JOB SUBMISSION: NOT AUTHORIZED BY THIS AUDIT")
 folder,heights=stage31_status()
 if heights is None:
  print("STAGE31 HEIGHT REPORT MISSING: re-run existing Stage31 --check/--run; no height chosen")
  policies={}
 else:
  print("STAGE31 ZBOT candidate report:",folder)
  policies=heights.get("provisional_sensor_policy",{})
 for site in sorted(EXPECTED):
  item=actual[site]
  if int(item.get("years_written",-1))!=EXPECTED[site]:
   raise RuntimeError(site+" annual forcing count unexpectedly changed")
  pol=policies.get(site)
  if pol is None:
   typ="MISSING_OR_BLOCKED";level="NO_CROSSWALK"
  else:
   typ=pol["candidate_ZBOT_mode"]
   level="TA_F_CROSSWALK="+pol["FLUXNET_TA_F_sensor_crosswalk"]
  if site in ("CA-Cbo","CA-Man"):
   typ="MULTI_LAYER_TA_MAPPING_BLOCKED"
  print(f"{site:7} NC={EXPECTED[site]:2d} ZBOT={typ:35} {level}")
 cases=sample_cases()
 print("EXISTING CIME CASES FOUND:",len(cases),"matching relevant patterns (first 25)")
 for case in cases:
  print(" ",case["name"],"datm_in",case["datm_in"],
        "streams",case["legacy_stream"],"lnd_in",case["generated_lnd_in"])
 print("HOLD: choose a working reference with actual CaseDocs/datm_in and stream files.")
 print("HOLD: ZBOT source-to-FLUXNET TA_F mapping, dated heights, DATM midpoint/local clock, and site surface/PFT/soil.")
 print("SAFE NEXT ACTION: validate actual reference case and a single new site AD5, not 10 x AD400 or NORMAL400.")
 print("AUDIT COMPLETE: READ ONLY / NO FILE WRITES / NO CIME OR SLURM ACTION")

if __name__=="__main__":main()
