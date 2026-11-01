#!/usr/bin/env python3
"""Stage02W: authoritatively compare Batch04 PFT proposals with GitHub registry.

READ ONLY. The authoritative source is the SHA-checked 2026-10-26 FIXNC
PFT registry in lyanyeung/CLM-FATES-single-site-workflows, not the old
gridded surface PCT_NAT_PFT and not the 2026-10-24 history table.
Compares 4 original station cases (8 case entries) to the official
registered candidate and the Stage02V original-source surface audit.

Never approves a PFT. "CANDIDATE" and "PROPOSED" need operator review.
Only creates reports in an existing EMPTY --out-dir; no changes to
source or destination surface, CIME, FATES, Slurm or Git working tree.
"""
from __future__ import annotations
import argparse
import csv
import json
import math
from pathlib import Path

STAGE_V="STAGE02V_BATCH04_FOUR_SITE_DATM_PATH_PARSER_AND_LANDUNIT_TRIAGE"
SITES=("DE-Gri","DE-RuR","IT-Tor","ES-Agu")
EXPECTED={
    "DE-Gri":{13:100.0},
    "DE-RuR":{13:100.0},
    "IT-Tor":{13:100.0},
    "ES-Agu":{0:49.0,9:22.0,13:29.0},
}
EXPECTED_REGISTRY_TEXT={
    "DE-Gri":"C3 grass 100 (candidate)",
    "DE-RuR":"C3 grass 100 (candidate)",
    "IT-Tor":"C3 grass 100 (candidate)",
    "ES-Agu":"bare 49 / C3 grass 29 / evergreen shrub 22",
}
CSV_FIELDS=("site","case","GitHub_PFT_status","GitHub_registered_proxy",
            "original_natural_landunit_pct","original_crop_landunit_pct",
            "original_NATPFT_vector_json","source_original_vs_GitHub_L1_pp",
            "GitHub_target_active_case_verified",
            "source_surface_matches_registry","PFT_science_review",
            "soil_science_review","model_submission_release")


def safe_float(x):
    try:
        f=float(x)
        return f if math.isfinite(f) else None
    except (TypeError,ValueError):return None


def validate_registry(text):
    rows=list(csv.DictReader(text.splitlines()))
    if not rows:
        raise ValueError("Missing authoritative 38-site FIXNC registry rows")
    by_site={}
    for r in rows:
        site=r.get("site")
        if site in SITES:
            if site in by_site:
                raise ValueError("Duplicate site in official PFT registry: "+site)
            by_site[site]=r
    if set(by_site)!=set(SITES):
        raise ValueError("One or more Batch04 station registry rows missing")
    for site,r in by_site.items():
        if r.get("final_PCT_NAT_PFT")!=EXPECTED_REGISTRY_TEXT[site]:
            raise ValueError(site+": official PFT proposal changed; stop for operator review")
        if r.get("fixnc_cohort")!="Not assigned":
            raise ValueError(site+": source registry says assigned; re-audit active case")
        status=r.get("status","")
        if site=="ES-Agu":
            if status!="PROPOSED":
                raise ValueError("ES-Agu no longer in PROPOSED status")
        elif not status.startswith("CANDIDATE"):
            raise ValueError(site+": qualitative PFT review status changed")
        if not r.get("evidence_basis") or not r.get("sources"):
            raise ValueError(site+": evidence URL/basis missing")
    return by_site


def validate_stage(v):
    if not isinstance(v,dict) or v.get("stage")!=STAGE_V or \
       v.get("read_only") is not True or v.get("science_release") is not False:
        raise ValueError("Expected original Stage02V scientific-HOLD report")
    rows=v.get("cases")
    if not isinstance(rows,list) or len(rows)!=8:
        raise ValueError("Expected eight Stage02V original case rows")
    grouped={}
    for row in rows:
        site=row.get("site")
        name=row.get("case")
        if site not in SITES or site not in name or name in (x.get("case") for x in grouped.get(site,[])):
            raise ValueError("Stage02V unexpected or duplicate case/site")
        if row.get("stage02b_exact_source_path_match") is not True or \
           row.get("canonical_source_path_match") is not True or \
           row.get("all_candidate_NC_exist") is not True:
            raise ValueError(site+" source DATM path no longer verified; hold PFT gate")
        if row.get("science_release")!="HOLD":
            raise ValueError("Unexpected previous science approval")
        grouped.setdefault(site,[]).append(row)
    if set(grouped)!=set(SITES) or any(len(v)!=2 for v in grouped.values()):
        raise ValueError("Expected exactly two source cases for each of four sites")
    return grouped


def original_vector(raw):
    out={}
    if not isinstance(raw,dict):
        raise ValueError("Stage02V original NATPFT is not a mapping")
    for key,value in raw.items():
        i=int(key);val=safe_float(value)
        if i not in range(15) or val is None or val<0:
            raise ValueError("Invalid original HLM NATPFT entry")
        out[i]=val
    if abs(sum(out.values())-100)>0.025:
        raise ValueError("Original PCT_NAT_PFT does not sum to 100")
    return out


def analyze(site,row,registry):
    p=row.get("static_landunit",{})
    if p.get("status")!="STATIC_SURFACE_PFT_NOT_OBSERVATION":
        raise ValueError(site+": original surface PFT numeric evidence missing")
    original=original_vector(p.get("original_conditional_natpft_pct"))
    model={int(k):float(v) for k,v in p.get("model_selected_conditional_natpft_proxy_pct",{}).items()}
    target=EXPECTED[site]
    if model!=target:
        raise ValueError(site+": Stage02V operator candidate differs from official registry")
    nat=safe_float(p.get("PCT_NATVEG"))
    crop=safe_float(p.get("PCT_CROP"))
    if nat is None or crop is None or abs(nat+crop-100)>0.02:
        raise ValueError(site+": original natural/crop landunit percentages require review")
    l1=sum(abs(original.get(i,0)-target.get(i,0)) for i in range(15))
    if abs(l1-float(p.get("L1_PFT_conditional_difference_pp")))>0.02:
        raise ValueError(site+": stage02V numerical PFT divergence differs")
    status=registry["status"]
    return {
        "site":site,"case":row["case"],
        "GitHub_PFT_status":status,
        "GitHub_registered_proxy":registry["final_PCT_NAT_PFT"],
        "GitHub_original_evidence_basis":registry["evidence_basis"],
        "GitHub_original_sources":registry["sources"],
        "original_natural_landunit_pct":nat,
        "original_crop_landunit_pct":crop,
        "original_NATPFT_vector":original,
        "registered_target_NATPFT_vector":target,
        "source_original_vs_GitHub_L1_pp":round(l1,6),
        "GitHub_target_active_case_verified":False,
        "source_surface_matches_registry":l1<0.02,
        "PFT_science_review":(
            "MANUAL_REVIEW_QUALITATIVE_GRASS_PROXY" if site!="ES-Agu"
            else "MANUAL_REVIEW_BARE_GROUND_COVER_DENOMINATOR_AND_SHRUB"),
        "soil_science_review":(
            "IT_TOR_ALL_10_SOIL_ORGANIC_ZERO_REVIEW" if site=="IT-Tor"
            else "SOIL_SOURCE_QC_NOT_INDEPENDENTLY_VERIFIED"),
        "model_submission_release":"HOLD",
    }


def self_test():
    reg="site,fixnc_cohort,final_PCT_NAT_PFT,status,evidence_basis,sources\n"
    for site in SITES:
        status="PROPOSED" if site=="ES-Agu" else "CANDIDATE (qualitative)"
        reg+=f"{site},Not assigned,{EXPECTED_REGISTRY_TEXT[site]},{status},source,https://example.org\n"
    table=validate_registry(reg)
    assert len(table)==4 and table["IT-Tor"]["status"].startswith("CANDIDATE")
    toy={"static_landunit":{
        "status":"STATIC_SURFACE_PFT_NOT_OBSERVATION",
        "PCT_NATVEG":71.46,"PCT_CROP":28.54,
        "original_conditional_natpft_pct":{0:49,9:22,13:29},
        "model_selected_conditional_natpft_proxy_pct":{0:49,9:22,13:29},
        "L1_PFT_conditional_difference_pp":0},
        "case":"ES-Agu_FATES_SPINUP1000_S30EXCL"}
    a=analyze("ES-Agu",toy,table["ES-Agu"])
    assert a["source_surface_matches_registry"] is True
    assert a["model_submission_release"]=="HOLD"
    assert sum(EXPECTED["ES-Agu"].values())==100
    print("STAGE02W SELF-TEST PASS: official GitHub 4 PFT statuses, 8-case source divergence gate, ES-Agu denominator/IT-Tor soil HOLD; NO WRITES")


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test",action="store_true")
    parser.add_argument("--stage02v",type=Path)
    parser.add_argument("--pft-register",type=Path)
    parser.add_argument("--out-dir",type=Path)
    args=parser.parse_args()
    if args.self_test:
        self_test();return
    if not args.stage02v or not args.stage02v.is_file() or \
       not args.pft_register or not args.pft_register.is_file():
        parser.error("Require original Stage02V JSON and SHA-checked GitHub 26 Oct PFT registry")
    if args.out_dir is None or not args.out_dir.is_dir() or any(args.out_dir.iterdir()):
        parser.error("--out-dir must exist and be EMPTY")
    source=json.loads(args.stage02v.read_text(encoding="utf-8"))
    groups=validate_stage(source)
    registry=validate_registry(args.pft_register.read_text(encoding="utf-8-sig"))
    records=[]
    for site in SITES:
        for case in groups[site]:
            item=analyze(site,case,registry[site])
            records.append(item)
            print("PFT_REVIEW",site,item["case"],
                  "GITHUB_PFT",item["GitHub_registered_proxy"],
                  "STATUS",item["GitHub_PFT_status"],
                  "ORIGINAL_L1_PP",item["source_original_vs_GitHub_L1_pp"],
                  "MATCHES_ORIGINAL_SURFACE",item["source_surface_matches_registry"],
                  "ORIGINAL_NATVEG",item["original_natural_landunit_pct"],
                  "ORIGINAL_CROP",item["original_crop_landunit_pct"],
                  "MANUAL",item["PFT_science_review"],
                  "SOIL",item["soil_science_review"])
    print("STATIC_DATM_PATH_VERIFIED 8/8",
          "REGISTER_TARGET_APPLIED_AT_RUNTIME NOT_VERIFIED",
          "PFT_OPERATOR_RELEASE 0/4")
    report={
        "stage":"STAGE02W_BATCH04_GITHUB_AUTHORITATIVE_PFT_VS_SOURCE_SURFACE_MANUAL_REVIEW",
        "read_only":True,"science_release":False,
        "reference_registry":str(args.pft_register),
        "source_stage02v":str(args.stage02v),
        "original_site_source_PFT_automatically_overwritten":False,
        "CIME_modified":False,"Slurm_submitted":False,
        "records":records,
        "per_site_manual_approval_pending":list(SITES),
        "important_limits":(
          "Official 26 Oct 2026 GitHub register is CANDIDATE for DE-Gri/DE-RuR/IT-Tor "
          "and PROPOSED for ES-Agu, not IN USE. Original surface PCT_NAT_PFT is "
          "conditional on NATVEG; separate crop percentages cannot be assigned "
          "to grass/bare. A static mismatch does NOT prove the actual runtime "
          "HLM-to-FATES map, which still needs active case validation."),
    }
    jp=args.out_dir/"stage02w_four_site_GitHub_PFT_manual_science_gate.json"
    cp=args.out_dir/"stage02w_four_site_GitHub_vs_original_surface.csv"
    with jp.open("x",encoding="utf-8") as f:
        json.dump(report,f,indent=2,ensure_ascii=False);f.write("\n")
    with cp.open("x",encoding="utf-8",newline="") as f:
        writer=csv.DictWriter(f,fieldnames=CSV_FIELDS)
        writer.writeheader()
        for item in records:
            row={k:item.get(k) for k in CSV_FIELDS}
            row["original_NATPFT_vector_json"]=json.dumps(item["original_NATPFT_vector"],sort_keys=True)
            writer.writerow(row)
    print("JSON",jp)
    print("CSV",cp)
    print("ALL_4_PFT_MANUAL_REVIEW; NO FORCING/SURFACE/CIME/FATES/SLURM WRITES")


if __name__=="__main__":
    main()
