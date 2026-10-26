#!/usr/bin/env python3
"""AmeriFlux Batch04 20-arm AD5 submission readiness, read-only.

Do NOT submit CIME or Slurm. Verify exact user-confirmed:
  - ten final SYVH9 original meteorology, all source SHA and Gate0 10/10
  - ten SYVH12 original point-surface SHAs
  - ten shared initial PFT research candidate SHA receipts
  - 20-arm FULL vs FIXNC AD400/Normal400 plan and source key
  - actual stack >=65536 KiB and Slurm PropagateResourceLimits STACK/ALL
Enumerate evidence for prerequisites not yet constructed:
  verified native-LST->UTC/time-centered NOLEAP DATM streams and annual NC,
  source-specific ZBOT TA/WS provenance, per-layer soils/ORGANIC, FATES
  functional/Arctic mapping, case model PTS/domain and saved job/archival.
Do not mistake no file at a conventional path for globally nonexistence.
Only operator-provided exact evidence can approve, never pretend ready.

Phase is strictly AD5 (not AD400, AD395 or Normal) until independent
complete AD5 archived restart is verified separately per arm.

USAGE:
  python3 -B 03_batch04_AD5_readiness_gate_READONLY.py --self-test
  python3 -B 03_batch04_AD5_readiness_gate_READONLY.py --check
No original/input/model/source writes in either mode. --check exits 2 for
scientific/model readiness HOLD even if technical source checks all pass.
"""
import argparse,csv,hashlib,importlib.util,json,math
from pathlib import Path
HERE=Path(__file__).resolve().parent
SOURCE=HERE/"01_audit_source_PFT_soil_surface_and_pair_plan.py"
STACK=HERE/"b04_stack_guard.py"
ROOT=Path("/iridisfs/scratch/ly3n24/CLM_FATES")
EXP=ROOT/"experiments/NonCompetitionObserved22/AmeriFlux_Batch04_10"
SOURCE_PFT_FOLDER=EXP/("PFT_surface_candidate_research_ONLY/"
      "candidate_20261026T165944Z_ab70c90d")
SOURCE_PFT_RECEIPT=SOURCE_PFT_FOLDER/"AMF_B04_PFT_SURFACES_BOTH_ARMS_RESEARCH_ONLY.json"
PLAN=EXP/("paired_FATES_FIXNC_AD400_Normal400_plan_"
      "20261026T165940Z_1e6b7e17.json")
EXPECTED_SITES=("US-Rpf","US-SP1","US-SRG","US-SRM","US-Seg",
                "US-Ses","US-Slt","US-Syv","US-Ton","US-Uaf")
EXPECTED_ARMS=("FULL_FATES_COMPETITION","FIXED_BIOGEOG_NO_COMPETITION")
REQUIREMENTS=(
    "ACTIVE_NATIVE_LST_TO_UTC_NOLEAP_DATM_STREAM_AND_ANNUAL_NETCDF",
    "INDEPENDENT_DATM_VARIABLE_UNITS_TIME_CENTER_QBOT_VPD_ROUNDING",
    "TA_AND_WIND_SENSOR_ZBOT_PROVENANCE_OR_EXPLICIT_APPROVED_SENSITIVITY",
    "SITE_SOIL_10_LAYER_AND_ORGANIC_SCIENCE_APPROVAL",
    "FATES_PARAM_MAP_PFT_ARCTIC_BARE_SCENARIO_SCIENCE_APPROVAL",
    "SOURCE_PINNED_CASE_CIME_PTS_DOMAIN_BUILD_AND_NAMELISTS",
    "ACTIVE_RUN_DIR_VS_CASEDOCS_DATM_INPUT_EQUIVALENCE",
    "UNIQUE_NOT_PREVIOUSLY_SUBMITTED_AD5_CASES_AND_ATTEMPT_LEDGERS",
)
def chk(ok,msg):
    if not ok:raise RuntimeError(msg)
def file(p):
    chk(p.is_file() and not p.is_symlink(),
        "Required Batch04 independent source file missing/symlink: "+str(p))
    return p
def sha(p):
    h=hashlib.sha256()
    with file(p).open("rb") as f:
        for chunk in iter(lambda:f.read(4<<20),b""):h.update(chunk)
    return h.hexdigest()
def j(p):return json.loads(file(p).read_text(encoding="utf-8"))
def load(p,module):
    chk(p.is_file() and not p.is_symlink(),
        "Required sourced Batch04 audit module absent: "+str(p))
    spec=importlib.util.spec_from_file_location(module,str(p))
    obj=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(obj)
    return obj
def phase_pair_checks(plant,plan):
    chk(plant.get("n_sites")==10 and
        plant.get("n_planned_model_arms")==20 and
        plant.get("active_CIME_case_created") is False and
        plant.get("submitted_SLURM_jobs") is False,
        "Existing ten site PFT research receipt no longer matches")
    ck_rows=plant["site_surfaces"]
    chk(len(ck_rows)==10 and
        {r["site"] for r in ck_rows}==set(EXPECTED_SITES),
        "Ten verified PFT study candidates not exact cohort")
    chk(len(plan.get("experiments",[]))==20 and
        {r["site"] for r in plan["experiments"]}==set(EXPECTED_SITES)
        and {r["arm"] for r in plan["experiments"]}==set(EXPECTED_ARMS)
        and len({(r["site"],r["arm"]) for r in plan["experiments"]})==20,
        "Expected exact 20 independent paired arms are not pinned")
    chk(plan.get("paired_model_runs_not_submitted") is True,
        "Planning receipt no longer guarantees unsubmitted study")
    chk(all(r["AD400_years"]==400 and r["Normal400_years"]==400 and
        r["AD_first_smoke"]==5 and r["Normal_first_smoke"]==5
        and r["spinup_authorized"] is False for r in plan["experiments"]),
        "Expected AD5/AD395/Normal5/Normal395 guarded phases differ")
    bysite={r["site"]:r for r in ck_rows}
    for row in plan["experiments"]:
        plantrow=bysite[row["site"]]
        chk(row["surface_source_sha256"]==plantrow["source_surface_SHA256"] and
            row["fates_PFT_mapping_profile"]==plantrow["FATES_mapping_profile"],
            "Selected initial site PFT/candidate register drift "+row["site"])
    for site in EXPECTED_SITES:
        item=bysite[site]
        surface=Path(item["new_model_hypothesis_surface"])
        chk(surface.is_relative_to(SOURCE_PFT_FOLDER/site) and
            sha(surface)==item["new_surface_SHA256"] and
            item["FULL_FATES_start_surface"]==str(surface) and
            item["FIXED_NO_COMP_START_SURFACE"]==str(surface) and
            item["ZBOT_verified"] is False and
            item["case_submitted"] is False,
            "Research PFT surface proof/source changed "+site)
        print("AMF_B04 AD5 SHARED START PFT SHA VERIFIED",site,
              item["new_surface_SHA256"],flush=True)
def main():
    ap=argparse.ArgumentParser(description=__doc__)
    g=ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--self-test",action="store_true")
    g.add_argument("--check",action="store_true")
    args=ap.parse_args()
    chk(len(EXPECTED_SITES)==10 and len(EXPECTED_ARMS)==2 and
        len(REQUIREMENTS)==8 and all(x.startswith("US-") for x in EXPECTED_SITES),
        "Batch04 10 site / 20 arm AD5 readiness selftest failed")
    print("AMF_B04 AD5 GATE SYNTHETIC SELFTEST PASS 10 sites, 20 arms, no writes")
    if args.self_test:return
    base=load(SOURCE,"b04_exact_source_auditor")
    rows,_,source_sha=base.audit()
    chk(len(rows)==10,"SYVH9 and SYVH12 original source SHA audit not 10/10")
    plan=j(PLAN);plant=j(SOURCE_PFT_RECEIPT)
    phase_pair_checks(plant,plan)
    chk(plan.get("source_receipts")==source_sha,
        "Operator AD400 paired plan no longer matches source snapshots")
    print("AMF_B04 10/10 SOURCE SHA PASS, 10/10 SHARED PFT SHA PASS, 20/20 ARMS PINNED")
    stack=load(STACK,"b04_live_stack_resource_guard")
    stack.inspect_or_raise(may_raise=False)
    stack.verify_slurm_propagation()
    print("AMF_B04 STACK 65536 KiB AND SLURM PROPAGATION PASS")
    for x in REQUIREMENTS:
        print("AMF_B04 AD5 MODEL SCIENCE HOLD",x)
    print("AMF_B04 AD5_READY=False, AD395_READY=False, "
          "CASE_BUILT=False, RUN_SUBMITTED=False")
    print("AMF_B04 ONLY ORIGINAL VERIFIED DATA AND RESEARCH SURFACES ARE READY")
    print("AMF_B04 NO NETCDF/DATM/CIME/CASE/SLURM JOB WRITES")
    raise SystemExit(2)
if __name__=="__main__":main()
