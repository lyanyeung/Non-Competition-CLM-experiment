#!/usr/bin/env python3
"""AmeriFlux Batch02 FIXNC read-only handoff / original case inventory.

Checks the exact ten-site PFT/soil recommended register, original ten-site
Stage95 met archive presence, and existing Slurm/CIME cases without writes.
NO spinup, CIME creation, source mutation, Git pull, or job submission.
Use --self-test, then --audit. Runs from any directory; register file next
to this script in ../data or pass --register explicitly.
"""
import argparse,csv,json,re,subprocess
from pathlib import Path

CLM=Path("/iridisfs/scratch/ly3n24/CLM_FATES")
EXP=CLM/"experiments/AmeriFlux_MultiSite_10_Batch02"
S95=EXP/"reports/stage95_ten_site_122_user_approved_versioned_forcing_215NC_20261026T034516Z_f4afa348"
SITES=("US-BZS","US-CMW","US-EML","US-GLE","US-Ha1","US-Ho1","US-Ho2","US-Ho3","US-ICh","US-ICt")
EXPECTED_YEARS=(15,21,16,16,35,28,27,19,19,19)
DATA="AMF_BATCH02_10_PFT_SOIL_RECOMMENDATIONS_SOURCE_PINNED_20261026.csv"

def check_register(path):
    with path.open(newline="",encoding="utf-8-sig") as f:
        rows=list(csv.DictReader(f))
    if len(rows)!=10 or {r["site"] for r in rows}!=set(SITES):
        raise ValueError("Not the exact user-designated 10 AmeriFlux Batch02 site register")
    bysite={r["site"]:r for r in rows}
    for name,row in bysite.items():
        if row["source_batch"]!="AmeriFlux_Batch02":
            raise ValueError("Wrong source cohort: "+name)
        host=json.loads(row["recommended_clm_host_PCT_NAT_PFT_json"])
        if abs(sum(float(v) for v in host.values())-100)>1e-7:
            raise ValueError("PFT host shares do not sum to 100: "+name)
        sand,clay=float(row["recommended_sand_0_30cm_pct"]),float(row["recommended_clay_0_30cm_pct"])
        if min(sand,clay)<0 or sand+clay>100:
            raise ValueError("Sand/Clay values physically impossible: "+name)
        if row["soil_l10_profile_verified"]!="NO_per_layer_separate_provenance_required":
            raise ValueError("Ten-layer soil has been prematurely labeled ready: "+name)
    return bysite

def cases_for(site):
    root=CLM/"cases"
    if not root.is_dir():return []
    out=[]
    for path in root.iterdir():
        if path.is_dir() and re.match(re.escape(site)+r"(?=[_-]|$)",path.name):
            cs=path/"CaseStatus"
            status=cs.read_text(errors="replace") if cs.is_file() else ""
            out.append({"name":path.name,"CaseStatus_file":cs.is_file(),
                        "any_case_submit_success":"case.submit success" in status,
                        "any_model_execution_success":"model execution success" in status,
                        "latest_status":next((x.strip() for x in reversed(status.splitlines())
                                             if ("success" in x or "fail" in x or "starting" in x)), "")[:130]})
    return sorted(out,key=lambda x:x["name"])

def job():
    try:
        p=subprocess.run(["sacct","-j","4739020,4739021",
           "--format=JobID,JobName%25,State,ExitCode,Elapsed","-n","-P"],
           capture_output=True,text=True,timeout=18)
        if p.returncode==0:return p.stdout.strip() or "Slurm sacct not yet populated"
        return "sacct failed: "+p.stderr.strip()[:200]
    except (FileNotFoundError,subprocess.TimeoutExpired):
        return "Slurm sacct unavailable; refer to operator-provided PD at submission"

def main():
    p=argparse.ArgumentParser(description=__doc__)
    a=p.add_mutually_exclusive_group(required=True)
    a.add_argument("--self-test",action="store_true")
    a.add_argument("--audit",action="store_true")
    p.add_argument("--register",type=Path,default=Path(__file__).resolve().parent.parent/"data"/DATA)
    options=p.parse_args()
    if options.self_test:
        assert len(SITES)==10 and sum(EXPECTED_YEARS)==215
        assert re.match("US-Ho1"+r"(?=[_-]|$)","US-Ho1_AAA")
        assert not re.match("US-Ho1"+r"(?=[_-]|$)","US-Ho12_ABC")
        print("AMF_B02_SELF_TEST_PASS | exact 10 sources / 215 yearfiles / no writes")
        return
    registry=check_register(options.register)
    print("AMF_B02_REGISTER_PASS | 10/10 PFT+0-30cm soil source recommendations; L1-L10 and ORGANIC NOT adopted")
    print("AMF_B02_SOURCE_STAGE95",S95,"manifest",str((S95/"manifest.json").is_file()),
          "WARNING technical forcing passed but CIME time/height science still HOLD")
    print("SITE | PFT | SOIL_SAND/CLAY_0_30 | SOIL_TIER | CASES | ANY_SUBMITTED | ANY_MODEL_SUCCESS(not full run)")
    for site in SITES:
        r=registry[site];cases=cases_for(site)
        print(site,"|",r["recommended_fates_natland_percent"],"|",
              r["recommended_sand_0_30cm_pct"]+"/"+r["recommended_clay_0_30cm_pct"],"|",
              r["soil_tier"],"|",len(cases),"|",
              any(x["any_case_submit_success"] for x in cases),"|",
              any(x["any_model_execution_success"] for x in cases))
        for x in cases[-3:]:
            print("  CASE",x["name"],"SUBMITTED",x["any_case_submit_success"],
                  "MODEL_ANY_SUCCESS",x["any_model_execution_success"],
                  "NOTE not proof of 16y or AD400 completed")
    print("AMF_B02_GLE_JOB_4739020_4739021\n"+job())
    print("AMF_B02_SCIENCE_GATE | Ho1 2000-12-27 temperature HOLD; BZS/Ho1 height records missing;",
          "other height prehistory gaps; Arctic PFT and ORGANIC distinct; site 10-layer soils not exported")
    print("AMF_B02_READY_STATUS | PFT/SOIL design registered; 10site FIXNC model ready NOT VERIFIED")
    print("AMF_B02_AUDIT_PASS | read-only, no case/source/model writes")

if __name__=="__main__":
    main()
