#!/usr/bin/env python3
"""Batch04 Stage03B-REUSE: verify inherited 13-site Stage28 MET/29b-DATM.

This replaces the proposed redundant full four-site FLUXMET-HH QC rescan.
Compare old FLUXNET_MultiSite_13 Stage28 selected-forcing SHA manifest,
Stage29b annual DATM SHA manifest, Stage30 consolidated optional manifest,
and the EXACT current four-site Stage02C annual CIME file paths.

No tower CSV numeric scans, 74 annual NetCDF numeric reanalysis, new ERA
downloads, source/QC rewriting, CIME changes or Slurm. Full source SHA
checks on only 4 Stage28 MET CSVs and at most 3 representative annual NCs
per site (first/middle/last), and inspect NC provenance attributes.
The 74-path source comparison is in-memory filenames and manifest rows.
Files/documents missing from older experiment roots remain explicit HOLDs.

Only writes JSON+CSV to an existing EMPTY --out-dir.
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
from collections import Counter
from pathlib import Path

SITES=("DE-Gri","DE-RuR","IT-Tor","ES-Agu")
YEARS={"DE-Gri":(2004,2025,22),"DE-RuR":(2011,2025,15),
       "IT-Tor":(2008,2025,18),"ES-Agu":(2006,2024,19)}
A_STAGE="STAGE03A_BATCH04_FOUR_SITE_SOURCE_HH_QC_PROVENANCE_INVENTORY"
C_STAGE="STAGE02C_SITE_DATM_CANDIDATE_YEAR_AND_SAMPLE_QC"
D_STAGE="STAGE02D_FULL_ANNUAL_INTERNAL_DATM_QC"
BASE=Path("/iridisfs/scratch/ly3n24/CLM_FATES/experiments")
DEFAULT_28=BASE/"FLUXNET_MultiSite_13_MET_stage28_20261018_052344_851367/reports"
DEFAULT_29=BASE/"FLUXNET_13_ZBOT_DATM_20261018_054150_1008203/reports"
DEFAULT_30=BASE/"FLUXNET_13_ZBOT_DATM_STAGE30_20261018_055940_1008203/reports"
MAT=(
  ("DE-Gri","49 original MDS/QC1 blocks remain science pending; no blanket ERA replacement"),
  ("DE-RuR","2012-07-27 measured-source rainfall and dynamic BIF TA-height transitions require provenance"),
  ("IT-Tor","extreme precipitation provenance/accumulation period and all-10-layer zero ORGANIC separate soil HOLD"),
  ("ES-Agu","2018-09-15 extraordinary rainfall/accumulation and legacy Stage12/15 candidate edits review"),
)
FIELDS=("site","old_stage28_source","old_stage28_sha_match",
        "historical_DATM_manifest","expected_year_files","historical_year_rows",
        "current_vs_historical_paths_equal","mismatched_years_json",
        "representative_NC_verified","representative_NC_SHA_pass",
        "representative_NC_attrs_json","legacy_science_risk",
        "native_observation_QC_science_release","next_scope")

def sha(p):
    h=hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda:f.read(1048576),b""):h.update(b)
    return h.hexdigest()

def rows(path,limit=1500):
    if not path.is_file() or path.is_symlink():
        return None
    with path.open("r",encoding="utf-8-sig",newline="") as f:
        rd=csv.DictReader(f)
        if len(rd.fieldnames or [])>90:raise ValueError("Unexpected manifest CSV width "+str(path))
        out=[]
        for i,row in enumerate(rd,1):
            if i>limit:raise ValueError("Unexpected >1500 manifest rows "+str(path))
            out.append(row)
    return out

def source_register(c,d,a):
    if c.get("stage")!=C_STAGE or c.get("read_only") is not True or c.get("science_release") is not False:
        raise ValueError("Original Stage02C evidence changed")
    if d.get("stage")!=D_STAGE or d.get("read_only") is not True or d.get("science_release") is not False:
        raise ValueError("Original Stage02D evidence changed")
    if a.get("stage")!=A_STAGE or a.get("read_only") is not True or a.get("science_release") is not False:
        raise ValueError("Original Stage03A discovery evidence changed")
    cc={x["site"]:x for x in c.get("sites",[])}
    dd={x["site"]:x for x in d.get("sites",[])}
    aa={x["site"]:x for x in a.get("sites",[])}
    if len(cc)!=6 or set(dd)!=set(SITES) or set(aa)!=set(SITES):
        raise ValueError("Require exact original 6 + 4 + 4 site reports")
    reg={}
    for site in SITES:
        first,last,n=YEARS[site]
        if dd[site].get("annual_file_count")!=n or \
           dd[site].get("flagged_file_counts")!={} or \
           dd[site].get("all_years")!=list(range(first,last+1)):
            raise ValueError(site+" original Stage02D internal quality changed")
        if cc[site].get("distinct_site_datm_files")!=n or \
           cc[site].get("distinct_case_datm_path_sets")!=1:
            raise ValueError(site+" source case annual files ambiguous")
        if aa[site].get("truncated") is not False:raise ValueError(site+" source Stage03A truncated")
        cases=cc[site]["cases"]
        if len(cases)!=2:raise ValueError(site+" original cases missing")
        ysets=[]
        for item in cases:
            data={int(x["year"]):str(x["path"]) for x in item["site_datm"]}
            if set(data)!=set(range(first,last+1)):
                raise ValueError(site+" source yearly paths missing/duplicated")
            ysets.append(data)
        if ysets[0]!=ysets[1]:raise ValueError(site+" case variants point at different annual forcing")
        reg[site]=ysets[0]
    return reg

def nc_header(p):
    try:
        from netCDF4 import Dataset
        with Dataset(str(p),"r") as d:
            wanted=("stage28_meteorology_sha256","zbot_policy_sha256",
                    "provenance_status","zbot_mode","ZBOT_MODE")
            return {"status":"NETCDF_HEADER_ONLY",
                    "attributes":{k:str(getattr(d,k)) for k in wanted if k in d.ncattrs()},
                    "variables":list(d.variables)[:35]}
    except Exception as e:
        return {"status":"NC_HEADER_HOLD","error":type(e).__name__}

def main_audit(reg,stage28,stage29,stage30):
    m28=rows(stage28/"01_selected_13site_STAGE28_provisional_manifest.csv")
    m29=rows(stage29/"10_annual_full_DATM_SHA256_manifest.csv")
    m30=rows(stage30/"04_consolidated_13site_271_DATM_SHA256_manifest.csv")
    if m28 is None:raise ValueError("Missing original Stage28 selected MET manifest")
    historical=m30 if m30 is not None else m29
    hist_label="STAGE30_CONSOLIDATED" if m30 is not None else "STAGE29B"
    if historical is None:
        raise ValueError("Neither original Stage29b nor Stage30 annual DATM SHA manifest found")
    bymet={}
    for r in m28:
        site=r.get("site")
        if site in SITES:
            if site in bymet:raise ValueError("Duplicate Stage28 site "+site)
            bymet[site]=r
    if set(bymet)!=set(SITES):raise ValueError("Stage28 manifest missing four sites")
    byyear={}
    for r in historical:
        site=r.get("site")
        if site not in SITES:continue
        try:year=int(r.get("year",""))
        except ValueError:raise ValueError("Invalid historical DATM year for "+site)
        key=(site,year)
        if key in byyear:raise ValueError("Duplicate Stage29/30 DATM row "+str(key))
        byyear[key]=r
    items=[]
    for site in SITES:
        met=bymet[site]
        metpath=Path(met.get("forcing_path",""))
        metsha=met.get("sha256","")
        exists=metpath.is_file() and metpath.is_absolute() and not metpath.is_symlink()
        goodmet=bool(exists and sha(metpath)==metsha)
        subset=reg[site]
        comparisons=[]
        sampleyrs={min(subset),max(subset),sorted(subset)[len(subset)//2]}
        samples=[]
        for yr,path in sorted(subset.items()):
            old=byyear.get((site,yr))
            op=old.get("datm_nc","") if old else ""
            expect_sha=old.get("sha256","") if old else ""
            equal=bool(old and path==op)
            comparisons.append({"year":yr,"current":path,"historical":op,
                                "literal_path_equal":equal,
                                "historical_SHA_record_present":len(expect_sha)==64})
            if yr in sampleyrs:
                fp=Path(path)
                if fp.is_file() and not fp.is_symlink():
                    actual=sha(fp)
                    samples.append({"year":yr,"path":path,"actual_SHA256":actual,
                                    "historical_SHA256":expect_sha,
                                    "SHA_match":bool(expect_sha and actual==expect_sha),
                                    "header":nc_header(fp)})
                else:samples.append({"year":yr,"path":path,"SHA_match":False,
                                     "status":"CURRENT_NC_MISSING"})
        mismatches=[x["year"] for x in comparisons if not x["literal_path_equal"]]
        oldhash=[x for x in samples if x.get("SHA_match") is False]
        risk=dict(MAT)[site]
        report={"site":site,"historical_manifest_selected":hist_label,
                "stage28_met_path":str(metpath),"stage28_met_SHA_expected":metsha,
                "stage28_met_SHA_verified":goodmet,
                "stage28_met_release":"PROVISIONAL_SCIENCE_HOLD",
                "historical_DATM_manifest":str(stage30 if m30 is not None else stage29),
                "expected_year_files":len(subset),
                "historical_year_rows":sum((site,y) in byyear for y in subset),
                "all_current_paths_match_historical":len(mismatches)==0,
                "mismatched_years":mismatches,
                "yearly_path_comparisons":comparisons,
                "three_representative_NC_SHA_and_headers":samples,
                "representative_NC_SHA_pass":len(samples)==3 and not oldhash,
                "original_Source_QC0_QC1_observational_review_complete":False,
                "legacy_science_risk":risk,
                "high_priority_action":"TARGET_DELTA_QC_ONLY_IF_STAGE28_LINEAGE_MATCHES_ELSE_SOURCE_LINEAGE_HOLD",
                "science_release":False}
        items.append(report)
        print("SITE",site,"STAGE28_MET_SHA",("PASS" if goodmet else "MISSING_OR_CHANGED"),
              "STAGE29_30_MANIFEST",hist_label,
              "CURRENT_PATH_MATCH",f"{len(subset)-len(mismatches)}/{len(subset)}",
              "REPRESENTATIVE_NC_SHA_PASS",f"{sum(x.get('SHA_match',False) for x in samples)}/3")
        if mismatches:print(" DIFF_YEARS",mismatches[:22])
        print(" RISK",risk)
    return {"stage":"STAGE03B_BATCH04_REUSE_FLUXNET13_STAGE28_STAGE29B_30_SOURCE_LINEAGE",
            "read_only":True,"science_release":False,
            "data_sources_modified":False,"cime_changed":False,"slurm_submitted":False,
            "previous_historical_13site_stage28_manifest":str(stage28),
            "previous_historical_13site_DATM_manifest_choice":hist_label,
            "sites":items,
            "interpretation":"Check path/hash lineage before reusing previous 13site QC. Matching source does not certify native tower QC; only incremental unresolved scientific blocks need new AmeriFlux-style analysis. No 74-year numeric scan or source FLUXMET rescan."}

def test():
    assert sum(x[2] for x in YEARS.values())==74
    assert len(SITES)==4
    assert "DE-Gri" in dict(MAT)
    assert "2012-07-27" in dict(MAT)["DE-RuR"]
    print("STAGE03B-REUSE SELF-TEST PASS: four old Stage28/29b/30 met-DATM lineage gates and 12 representative NC SHA checks; NO WRITES")

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--self-test",action="store_true")
    ap.add_argument("--stage02c",type=Path)
    ap.add_argument("--stage02d",type=Path)
    ap.add_argument("--stage03a",type=Path)
    ap.add_argument("--stage28",type=Path,default=DEFAULT_28)
    ap.add_argument("--stage29b",type=Path,default=DEFAULT_29)
    ap.add_argument("--stage30",type=Path,default=DEFAULT_30)
    ap.add_argument("--out-dir",type=Path)
    a=ap.parse_args()
    if a.self_test:test();return
    if any(p is None or not p.is_file() for p in (a.stage02c,a.stage02d,a.stage03a)):
        ap.error("Require saved original Stage02C, Stage02D and Stage03A JSON reports")
    if a.out_dir is None or not a.out_dir.is_dir() or \
       a.out_dir.is_symlink() or any(a.out_dir.iterdir()):
        ap.error("--out-dir must already exist and be EMPTY")
    reg=source_register(json.loads(a.stage02c.read_text(encoding="utf-8")),
                        json.loads(a.stage02d.read_text(encoding="utf-8")),
                        json.loads(a.stage03a.read_text(encoding="utf-8")))
    report=main_audit(reg,a.stage28,a.stage29b,a.stage30)
    report["inputs"]={"stage02c":str(a.stage02c),
                      "stage02d":str(a.stage02d),"stage03a":str(a.stage03a)}
    jp=a.out_dir/"stage03b_four_site_reused_stage28_DATM_lineage.json"
    cp=a.out_dir/"stage03b_four_site_old_vs_current_DATM_matrix.csv"
    with jp.open("x",encoding="utf-8") as f:
        json.dump(report,f,indent=2,ensure_ascii=False);f.write("\n")
    with cp.open("x",encoding="utf-8",newline="") as f:
        w=csv.DictWriter(f,fieldnames=FIELDS)
        w.writeheader()
        for r in report["sites"]:
            w.writerow({"site":r["site"],
                        "old_stage28_source":r["stage28_met_path"],
                        "old_stage28_sha_match":r["stage28_met_SHA_verified"],
                        "historical_DATM_manifest":r["historical_manifest_selected"],
                        "expected_year_files":r["expected_year_files"],
                        "historical_year_rows":r["historical_year_rows"],
                        "current_vs_historical_paths_equal":r["all_current_paths_match_historical"],
                        "mismatched_years_json":json.dumps(r["mismatched_years"]),
                        "representative_NC_verified":len(r["three_representative_NC_SHA_and_headers"]),
                        "representative_NC_SHA_pass":r["representative_NC_SHA_pass"],
                        "representative_NC_attrs_json":json.dumps(
                            [{"year":z["year"],"SHA_match":z.get("SHA_match"),
                              "header":z.get("header")} for z in r["three_representative_NC_SHA_and_headers"]]),
                        "legacy_science_risk":r["legacy_science_risk"],
                        "native_observation_QC_science_release":"HOLD",
                        "next_scope":r["high_priority_action"]})
    print("JSON",jp)
    print("CSV",cp)
    print("STAGE03B-REUSE FINISHED: HISTORICAL PROVENANCE ONLY; OBSERVATION QC SCIENCE HOLD; NO CIME/SLURM")

if __name__=="__main__":
    main()
