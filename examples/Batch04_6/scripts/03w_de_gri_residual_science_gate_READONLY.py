#!/usr/bin/env python3
"""ICOS Batch04 DE-Gri residual-science audit (saved reports only, no model writes)."""
import argparse,collections,datetime,json
from pathlib import Path

SC="STAGE03C_BATCH04_REUSE_HISTORICAL_SCIENCE_HOLDS_AND_AMERIFLUX_DELTA_SCOPE"
SD="STAGE03D_BATCH04_RECOVER_OLD_RAIN_AND_TARGETED_ORIGINAL_SOURCE_CONTEXT"
EXPECTED={"ORIGINAL_MDS_QC1_BLOCK_PENDING":49,"PARTIAL_STAGE28_SEVEN_SITE_RAIN_SOURCE_REVIEW":12,"STAGE28_REMAINING_MET_FLAG":14,"HISTORICAL_STAGE20_11_HALF_HOUR_MODIFICATIONS":1}
W=[(datetime.datetime(2011,6,13,7),datetime.datetime(2011,6,13,12)),(datetime.datetime(2024,7,4,5),datetime.datetime(2024,7,4,16))]

def dt(s):
    s=str(s or "").strip()
    for fmt in ("%Y-%m-%d %H:%M:%S","%Y-%m-%d %H:%M","%Y-%m-%dT%H:%M:%S","%Y%m%d%H%M"):
        try:return datetime.datetime.strptime(s,fmt)
        except ValueError:pass
    return None

def mark(r):
    a=dt(r.get("start_or_time")); b=dt(r.get("end")) if r.get("end") else a
    if a is None or b is None or b<a:return "UNKNOWN_TIME"
    for x,y in W:
        if a<=y and b>=x:return "OVERLAP_"+str(x.year)+"_NOT_PROVEN_FIXED"
    return "OUTSIDE_EDIT_WINDOWS"

def analyze(c,d,v,u):
    if c.get("stage")!=SC or c.get("science_release") is not False or d.get("stage")!=SD or d.get("science_release") is not False:raise ValueError("Wrong legacy HOLD reports")
    if v.get("site")!="DE-Gri" or v.get("status")!="INPUT_PLAN_ONLY_NOT_MODEL_RELEASE" or v.get("source_science_or_soil_release") is not False:raise ValueError("Stage03V was not HOLD")
    if u.get("site")!="DE-Gri" or u.get("status")!="DETACHED_SENSITIVITY_NOT_RELEASED":raise ValueError("Stage03U manifest not detached")
    rows=v.get("annual_inputs",[])
    if len(rows)!=22 or {a["year"] for a in rows}!=set(range(2004,2026)) or {a["year"] for a in rows if a["kind"]=="approved_sensitivity"}!={2011,2024}:raise ValueError("Stage03V 22-year scope mismatch")
    us={x["year"]:x for x in u.get("annual_files",[])}
    if set(us)!={2011,2024} or any(us[y].get("edits")!=n or us[y].get("logical_all_variables_verified") is not True or us[y].get("candidate_sha256")!=next(x["sha256"] for x in rows if x["year"]==y) for y,n in ((2011,11),(2024,23))):raise ValueError("Stage03U versus V mismatched")
    issues=[x for x in c.get("issues",[]) if x.get("site")=="DE-Gri"]
    counts=dict(collections.Counter(x.get("issue") for x in issues))
    if counts!=EXPECTED:raise ValueError("Historical category counts changed "+str(counts))
    mds=[x for x in issues if x["issue"]=="ORIGINAL_MDS_QC1_BLOCK_PENDING"]
    flags=[x for x in issues if x["issue"]=="STAGE28_REMAINING_MET_FLAG"]
    events=[x for x in d.get("target_event_context",[]) if x.get("site")=="DE-Gri"]
    if len(events)!=49 or len({x.get("episode") for x in events})!=49:raise ValueError("49 original source windows missing")
    paired=sum(bool(x.get("original_HH_rows_in_window")) and bool(x.get("Stage28_HH_rows_in_window")) for x in events)
    rain=[x for x in d.get("four_site_old_rain_rows",[]) if x.get("site")=="DE-Gri"]
    rp=d.get("historical_rain_provenance",{})
    if len(rain)!=12 or rp.get("status")!="FOUND_ACTUAL_STAGE21_OR_INHERITED_RAIN_LEDGER" or not (rp.get("stage21_found") or rp.get("stage22_prefixed_found")):raise ValueError("Real 12-rain ledger not recovered")
    stats=lambda rr:dict(sorted(collections.Counter(mark(x) for x in rr).items()))
    return {"site":"DE-Gri","read_only":True,"science_release":False,"AD5_authorized":False,"case_or_slurm_modified":False,"verified_annual_years":22,"two_sensitivity_edit_counts":{"2011":11,"2024":23},"historical_counts":counts,"49_MDS_with_both_source_and_selected_context":paired,"MDS_label_overlap":stats(mds),"14_flag_label_overlap":stats(flags),"12_rain_ledger":"RECOVERED_NOT_MISSING; ACCUMULATION_TIME_STILL_HOLD","49_MDS_scientific_release":"HOLD; source windows and QC metadata not independent true-sensor proof","14_flags_scientific_release":"HOLD; overlap with edited labels is NOT independent clearance","PFT_soil_runtime_binding_release":False,"flags_PRIVATE":[{"time":x.get("start_or_time"),"end":x.get("end"),"class":mark(x),"original_decision":x.get("legacy_decision")} for x in flags]}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--self-test",action="store_true")
    for k in ("stage03c","stage03d","stage03v","stage03u"):p.add_argument("--"+k,type=Path)
    p.add_argument("--out",type=Path)
    a=p.parse_args()
    if a.self_test:
        assert mark({"start_or_time":"2011-06-13 07:00:00"})=="OVERLAP_2011_NOT_PROVEN_FIXED"
        assert mark({"start_or_time":"2024-07-04 05:00:00"})=="OVERLAP_2024_NOT_PROVEN_FIXED"
        assert mark({"start_or_time":"2022-01-01 00:00:00"})=="OUTSIDE_EDIT_WINDOWS"
        assert mark({"start_or_time":"??"})=="UNKNOWN_TIME"
        print("STAGE03W SELF-TEST PASS | exact labels only, NO RELEASE");return
    paths=[a.stage03c,a.stage03d,a.stage03v,a.stage03u]
    if any(x is None or not x.is_file() for x in paths):p.error("Four prior reports must exist")
    if a.out is None or a.out.exists() or a.out.is_symlink() or not a.out.parent.is_dir():p.error("Output must be new private file in existing directory")
    result=analyze(*[json.loads(x.read_text(encoding="utf-8")) for x in paths])
    with a.out.open("x",encoding="utf-8") as f:json.dump(result,f,indent=2,ensure_ascii=False);f.write("\n")
    print("DE-GRI STAGE03W | HOLD, NO AD5 RELEASE")
    print("YEAR INPUT 22/22 | APPROVED SENSITIVITY LABELS 2011=11, 2024=23")
    print("49 MDS SOURCE+SELECTED CONTEXT",result["49_MDS_with_both_source_and_selected_context"],"/49")
    print("49 MDS WINDOW COUNTS",json.dumps(result["MDS_label_overlap"]))
    print("14 FLAG WINDOW COUNTS",json.dumps(result["14_flag_label_overlap"]))
    print("12 RAIN LEDGER RECOVERED | RAIN CLOCK SCIENCE HOLD")
    for x in result["flags_PRIVATE"]:print("FLAG",x["time"],x["end"],x["class"],x["original_decision"])
    print("PRIVATE_REPORT",a.out)
    print("NO SOURCE/NETCDF/CIME/SLURM CHANGE")

if __name__=="__main__":main()
