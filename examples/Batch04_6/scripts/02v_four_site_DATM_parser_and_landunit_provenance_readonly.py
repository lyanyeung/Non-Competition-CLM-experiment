#!/usr/bin/env python3
"""ICOS Batch04 Stage02V: diagnose eight Stage02U DATM_STATIC_LIST_MATCH=False.

READ ONLY. Does not rerun 74 annual NetCDF scans or select active forcing.
Reparse original CIME Buildconf/datm.input_data_list with the exact Stage02B
regex and a deliberately separate conservative candidate parser. Compare
against source-pinned Stage02C annual paths, show source lines and why the
Stage02U parser may have returned False. Audit original surface NATVEG/CROP
and conditional NATPFT proxies using Stage02U saved numerical evidence.
No CIME, netCDF, source, Slurm, FATES or Git worktree changes.
Creates JSON/CSV only under a NEW EMPTY --out-dir.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import re
from pathlib import Path

STAGE_U="STAGE02U_BATCH04_FOUR_SITE_STATIC_CASE_SURFACE_SOIL_PFT_GATE"
STAGE_C="STAGE02C_SITE_DATM_CANDIDATE_YEAR_AND_SAMPLE_QC"
SITES=("DE-Gri","DE-RuR","IT-Tor","ES-Agu")
YEARS={"DE-Gri":(2004,2025,22),
       "DE-RuR":(2011,2025,15),
       "IT-Tor":(2008,2025,18),
       "ES-Agu":(2006,2024,19)}
PROXY={"DE-Gri":{13:100.0},"DE-RuR":{13:100.0},
       "IT-Tor":{13:100.0},"ES-Agu":{0:49.0,9:22.0,13:29.0}}
# Stage02B's established absolute NC source reference parser.
CIME_NC_RE=re.compile(
    r"(?<![A-Za-z0-9_.])/[A-Za-z0-9_.+~:%@/=-]+\.nc(?:4)?(?=$|[\s'\"<>,;])",re.I)
# Stage02U's original parsing contract; retained only to diagnose False.
OLD_RE_FMT=r"/[^\s,'\"=;]+?{site}_DATM_(?:19|20)\d{{2}}\.nc"
FIELDS=("site","case","case_path","source_case_input_list",
        "stage02u_reported_static_match","parser_old_count","parser_stage02b_count",
        "expected_year_count","stage02b_exact_source_path_match",
        "canonical_source_path_match","all_candidate_NC_exist",
        "missing_expected_json","unexpected_references_json",
        "source_line_examples_json","stream_reference_count",
        "original_PCT_NATVEG","original_PCT_CROP",
        "original_NAT_PFT_json","model_proxy_NAT_PFT_json",
        "original_NAT_PFT_vs_proxy_abs_diff_pp",
        "original_soil_organic_min","original_soil_organic_max",
        "PFT_footprint_verified","native_tower_QC_verified",
        "active_runtime_DATM_verified","science_release")


def read_inputs(u,c):
    if not isinstance(u,dict) or u.get("stage")!=STAGE_U or \
       u.get("read_only") is not True or u.get("science_release") is not False:
        raise ValueError("Original Stage02U HOLD result required")
    if not isinstance(c,dict) or c.get("stage")!=STAGE_C or \
       c.get("read_only") is not True or c.get("science_release") is not False:
        raise ValueError("Original Stage02C HOLD result required")
    urows=u.get("sites",[])
    if not isinstance(urows,list) or tuple(x.get("site") for x in urows)!=SITES:
        raise ValueError("Original Stage02U four-site ordering/identity changed")
    cs={x.get("site"):x for x in c.get("sites",[])}
    if len(cs)!=6:
        raise ValueError("Original Stage02C must contain six sites")
    for row in urows:
        site=row["site"]
        if row.get("science_release")!="HOLD" or \
           row.get("Stage02D_internal_annual_files")!=YEARS[site][2] or \
           row.get("Stage02D_flags")!={}:
            raise ValueError(site+": previous 74-file internal evidence/state changed")
        if len(row.get("source_case_inspections",[]))!=2 or \
           len(cs[site].get("cases",[]))!=2:
            raise ValueError(site+": missing two original case candidates")
        if cs[site].get("distinct_case_datm_path_sets")!=1 or \
           cs[site].get("distinct_site_datm_files")!=YEARS[site][2]:
            raise ValueError(site+": original Stage02C annual source paths changed")
        lhs={x.get("case") for x in row["source_case_inspections"]}
        rhs={x.get("case") for x in cs[site]["cases"]}
        if lhs!=rhs:
            raise ValueError(site+": Stage02U/Stage02C original case identity conflict")
    return urows,cs


def parsers(text,site):
    names=re.compile("^"+re.escape(site)+r"_DATM_((?:19|20)\d{2})(?:[_.-]|$)",re.I)
    # The original source scanner extracts absolute paths including '.nc4'
    # (and allowed characters such as '='), independently of the later
    # Stage02U parser which can truncate on '=' or demand '.nc'.
    stage02b={m.group(0) for line in text.splitlines()
              for m in CIME_NC_RE.finditer(line)
              if names.match(Path(m.group(0)).name)}
    old_pattern=re.compile(OLD_RE_FMT.format(site=re.escape(site)),re.I)
    old=set(old_pattern.findall(text))
    return old,stage02b


def canon(path):
    # Files are read-only; canonicalize only paths that already exist.
    p=Path(path)
    try:return str(p.resolve(strict=True))
    except (OSError,RuntimeError):
        return None


def relevant_lines(text,site):
    out=[]
    for lineno,line in enumerate(text.splitlines(),1):
        if site+"_DATM_" in line:
            out.append({"line":lineno,"text":line.strip()[:600]})
    return out[:15],len(out)


def first_value(fields,key):
    vals=fields.get(key,{}).get("values")
    return float(vals[0]) if isinstance(vals,list) and len(vals)==1 and vals[0] is not None else None


def landunit_summary(original,site):
    fields=original.get("surface_original",{}).get("fields",{})
    nat=first_value(fields,"PCT_NATVEG")
    crop=first_value(fields,"PCT_CROP")
    vec=fields.get("PCT_NAT_PFT",{}).get("HOST_PFT_vector")
    if not isinstance(vec,list) or len(vec)!=15:
        return {"status":"MISSING_OR_NOT_15_ORIGINAL_PFT"}
    if any(x is None or not math.isfinite(float(x)) or float(x)<0 for x in vec):
        return {"status":"INVALID_ORIGINAL_PFT_NUMERIC"}
    raw={i:round(float(v),6) for i,v in enumerate(vec) if float(v)>0}
    expected=PROXY[site]
    error=sum(abs(float(vec[i])-expected.get(i,0.0)) for i in range(15))
    organic=fields.get("ORGANIC",{})
    res={
        "status":"STATIC_SURFACE_PFT_NOT_OBSERVATION",
        "PCT_NATVEG":nat,"PCT_CROP":crop,
        "original_conditional_natpft_pct":raw,
        "model_selected_conditional_natpft_proxy_pct":expected,
        "L1_PFT_conditional_difference_pp":round(error,6),
        "full_gridcell_original_NAT_PFT_pct_if_natural_landunit":(
            {i:round(nat*v/100.0,6) for i,v in raw.items()} if nat is not None else None),
        "organic_min":organic.get("min"),"organic_max":organic.get("max"),
        "landunit_fractions_measured_tower_footprint":False,
        "selected_proxy_applied_in_active_model":False,
    }
    if site=="IT-Tor" and organic.get("min")==0 and organic.get("max")==0:
        res["soil_evidence_flag"]="IT_TOR_ZERO_ORGANIC_ALL_TEN_LAYERS_NEEDS_SOURCE"
    if nat is None or crop is None or abs(nat+crop-100)>0.01:
        res["landunit_evidence_flag"]="NATVEG_CROP_NOT_VERIFIED_TO_100"
    return res


def evaluate(case,source,site,base):
    case_name=case["case"]
    root=base/"cases"/case_name
    if not case_name.startswith(site+"_") or not root.is_dir() or root.is_symlink() or \
       root.name!=case_name:
        raise ValueError("Original CIME case missing/unexpected: "+case_name)
    registered={str(e["path"]) for e in source.get("site_datm",[])}
    expected_years=set(range(YEARS[site][0],YEARS[site][1]+1))
    if {int(x["year"]) for x in source.get("site_datm",[])}!=expected_years or \
       len(registered)!=YEARS[site][2]:
        raise ValueError(site+" original Stage02C source year set unexpected")
    path=root/"Buildconf/datm.input_data_list"
    if not path.is_file() or path.stat().st_size>4_000_000:
        return {"site":site,"case":case_name,
                "status":"NO_READABLE_BOUNDED_DATM_INPUT_LIST",
                "expected_year_count":len(registered),"science_release":"HOLD"}
    text=path.read_text(encoding="utf-8",errors="replace")
    old,found=parsers(text,site)
    p_canon={canon(x) for x in found}
    reg_canon={canon(x) for x in registered}
    ex=[x for x in registered if not Path(x).is_file()]
    lines,linetotal=relevant_lines(text,site)
    surf=landunit_summary(case,site)
    stream_docs=case.get("stream_documents",[])
    return {
        "site":site,"case":case_name,
        "case_path":str(root),"source_case_input_list":str(path),
        "source_list_bytes":path.stat().st_size,
        "stage02u_reported_static_match":case.get("datm_list_exact_site_path_match"),
        "parser_old_count":len(old),"parser_stage02b_count":len(found),
        "expected_year_count":len(registered),
        "stage02b_exact_source_path_match":bool(found) and found==registered,
        "canonical_source_path_match":None not in p_canon and None not in reg_canon and
            p_canon==reg_canon and len(p_canon)==len(found)==len(registered),
        "all_candidate_NC_exist":not ex,
        "missing_expected":sorted(registered-found),
        "unexpected_references":sorted(found-registered),
        "existing_file_missing":sorted(ex),
        "source_line_examples":lines,
        "source_matching_line_count":linetotal,
        "stream_reference_count":len(stream_docs),
        "static_landunit":surf,
        "PFT_footprint_verified":False,
        "native_tower_QC_verified":False,
        "active_runtime_DATM_verified":False,
        "science_release":"HOLD",
    }


def csv_row(x):
    s=x.get("static_landunit",{})
    return {
        "site":x.get("site"),"case":x.get("case"),
        "case_path":x.get("case_path"),
        "source_case_input_list":x.get("source_case_input_list"),
        "stage02u_reported_static_match":x.get("stage02u_reported_static_match"),
        "parser_old_count":x.get("parser_old_count"),
        "parser_stage02b_count":x.get("parser_stage02b_count"),
        "expected_year_count":x.get("expected_year_count"),
        "stage02b_exact_source_path_match":x.get("stage02b_exact_source_path_match"),
        "canonical_source_path_match":x.get("canonical_source_path_match"),
        "all_candidate_NC_exist":x.get("all_candidate_NC_exist"),
        "missing_expected_json":json.dumps(x.get("missing_expected",[])),
        "unexpected_references_json":json.dumps(x.get("unexpected_references",[])),
        "source_line_examples_json":json.dumps(x.get("source_line_examples",[])),
        "stream_reference_count":x.get("stream_reference_count"),
        "original_PCT_NATVEG":s.get("PCT_NATVEG"),
        "original_PCT_CROP":s.get("PCT_CROP"),
        "original_NAT_PFT_json":json.dumps(s.get("original_conditional_natpft_pct",{})),
        "model_proxy_NAT_PFT_json":json.dumps(s.get("model_selected_conditional_natpft_proxy_pct",{})),
        "original_NAT_PFT_vs_proxy_abs_diff_pp":s.get("L1_PFT_conditional_difference_pp"),
        "original_soil_organic_min":s.get("organic_min"),
        "original_soil_organic_max":s.get("organic_max"),
        "PFT_footprint_verified":False,"native_tower_QC_verified":False,
        "active_runtime_DATM_verified":False,"science_release":"HOLD",
    }


def self_test():
    assert len(SITES)==4 and sum(x[2] for x in YEARS.values())==74
    base="/iridisfs/scratch/u/CLM_FATES/experiments/FLUXNET_13"
    text=(
        "file1='"+base+"/DE-Gri/datm_annual/DE-Gri_DATM_2004.nc'\n"
        "file2='"+base+"/DE-Gri/datm_annual/DE-Gri_DATM_2005.nc4'\n"
        "aerosol=/somewhere/aerosol.nc\n")
    old,new=parsers(text,"DE-Gri")
    assert len(old)==2 and len(new)==2
    # The old regex may silently truncate a .nc4 reference to .nc
    # and then fail source-path equality despite two apparent matches.
    assert any(x.endswith("DE-Gri_DATM_2005.nc") for x in old)
    assert any(x.endswith("DE-Gri_DATM_2005.nc4") for x in new)
    assert all("DE-Gri_DATM_" in x for x in new)
    assert not parsers(text,"IT-Tor")[1]
    fake={"surface_original":{"fields":{
        "PCT_NATVEG":{"values":[71.46]},
        "PCT_CROP":{"values":[28.54]},
        "PCT_NAT_PFT":{"HOST_PFT_vector":[49,0,0,0,0,0,0,0,0,22,0,0,0,29,0]},
        "ORGANIC":{"min":2.5,"max":12}}}}
    s=landunit_summary(fake,"ES-Agu")
    assert s["L1_PFT_conditional_difference_pp"]==0
    assert abs(sum(s["full_gridcell_original_NAT_PFT_pct_if_natural_landunit"].values())-71.46)<0.0001
    assert s["landunit_fractions_measured_tower_footprint"] is False
    print("STAGE02V SELF-TEST PASS: 8-case scanner reconciliation, NC4/alias path contract, conditional NATVEG/soil HOLD; NO WRITES")


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--self-test",action="store_true")
    ap.add_argument("--stage02u",type=Path)
    ap.add_argument("--stage02c",type=Path)
    ap.add_argument("--base",type=Path,default=Path("/iridisfs/scratch/ly3n24/CLM_FATES"))
    ap.add_argument("--out-dir",type=Path)
    x=ap.parse_args()
    if x.self_test:self_test();return
    if any(f is None or not f.is_file() for f in (x.stage02u,x.stage02c)):
        ap.error("Saved actual Stage02U and Stage02C source JSONs required")
    if x.out_dir is None or not x.out_dir.is_dir() or any(x.out_dir.iterdir()):
        ap.error("--out-dir must be an existing EMPTY directory")
    if x.base.name!="CLM_FATES" or not x.base.is_dir():
        ap.error("Original CLM_FATES source case directory missing")
    u,c=read_inputs(json.loads(x.stage02u.read_text(encoding="utf-8")),
                    json.loads(x.stage02c.read_text(encoding="utf-8")))
    records=[]
    for ur in u:
        site=ur["site"]
        bycase={e["case"]:e for e in c[site]["cases"]}
        for case in ur["source_case_inspections"]:
            item=evaluate(case,bycase[case["case"]],site,x.base)
            records.append(item)
            print("CASE",site,item["case"],
                  "OLD_STAGE02U_MATCH",item.get("stage02u_reported_static_match"),
                  "OLD_PARSE",item.get("parser_old_count"),
                  "STAGE02B_PARSE",item.get("parser_stage02b_count"),
                  "EXPECTED",item.get("expected_year_count"),
                  "PATH_EXACT",item.get("stage02b_exact_source_path_match"),
                  "PATH_CANON",item.get("canonical_source_path_match"),
                  "NC_EXIST",item.get("all_candidate_NC_exist"))
            if not item.get("stage02b_exact_source_path_match"):
                for z in item.get("source_line_examples",[])[:3]:
                    print(" SOURCE_INPUT_LINE",z["line"],z["text"])
                for k in ("missing_expected","unexpected_references"):
                    for path in item.get(k,[])[:3]:
                        print(" SOURCE_DIFF",k,path)
            surf=item.get("static_landunit",{})
            print(" LAND",site,"NATVEG",surf.get("PCT_NATVEG"),
                  "CROP",surf.get("PCT_CROP"),
                  "NAT_PFT_VS_PROXY_L1_PP",surf.get("L1_PFT_conditional_difference_pp"),
                  "ORGANIC_MIN",surf.get("organic_min"),
                  "ORGANIC_MAX",surf.get("organic_max"),
                  "SOIL_FLAG",surf.get("soil_evidence_flag","NONE"))
    if len(records)!=8:raise ValueError("Expected exactly 8 original cases")
    report={
        "stage":"STAGE02V_BATCH04_FOUR_SITE_DATM_PATH_PARSER_AND_LANDUNIT_TRIAGE",
        "read_only":True,"science_release":False,
        "source_stage02u":str(x.stage02u),"source_stage02c":str(x.stage02c),
        "original_CIME_changed":False,"source_changed":False,"slurm_submitted":False,
        "cases":records,
        "limitations":"Stage02B parser reconciliation of Buildconf candidates is NOT proof of actual live DATM stream binding. Surface NATPFT is conditional on NATVEG and may not reflect EC footprint; soil values still not source-validated.",
    }
    jp=x.out_dir/"stage02v_four_site_DATM_parser_landunit_review.json"
    cp=x.out_dir/"stage02v_four_site_eight_case_DATM_PFT_comparison.csv"
    with jp.open("x",encoding="utf-8") as fh:
        json.dump(report,fh,indent=2,ensure_ascii=False);fh.write("\n")
    with cp.open("x",encoding="utf-8",newline="") as fh:
        wr=csv.DictWriter(fh,fieldnames=FIELDS);wr.writeheader()
        wr.writerows(csv_row(z) for z in records)
    print("JSON",jp)
    print("CSV",cp)
    print("SCIENCE_HOLD: REAL DATM RUNTIME, TOWER SOURCE QC, NATVEG/PFT FOOTPRINT AND SOIL PROVENANCE UNVERIFIED")


if __name__=="__main__":
    main()
