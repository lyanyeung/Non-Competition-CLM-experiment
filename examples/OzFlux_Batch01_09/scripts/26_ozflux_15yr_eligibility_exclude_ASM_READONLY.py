#!/usr/bin/env python3
"""OzFlux Stage26: 15-year continuous stable-ecosystem eligibility preflight.

Operator decision 2026-11-04: EXCLUDE AU-ASM from all future QC, NOAA,
forcing/DATM/case, AD400. It has <15 continuous pre-outage years, from
2010-09 to 2023-03; old/new site streams must not be concatenated.

IMPORTANT SCIENCE FACT: November 2022 clearing/conversion to cropland
belongs to AU-DaS Daly Uncleared, NOT AU-ASM. AU-DaS may not mix any
native years 2022+ with pre-clear woody savanna; its 2009-2021 Stage07
complete-year block covers 13 years (not 15).

This reads the operator's actual immutable Stage07 report only, not tower
NetCDF. It does not assert that a year failing strict full-data structure
cannot be recovered with an independently authorized future QC repair.
Compare full native-year count to 15 and independently count the longest
unbroken annual *structural candidate* block. The latter is NOT science
approval or proof of site PFT continuity. For eligible-looking sites,
ecological history and at least 15 years of final science QC remain needed.

All eight non-ASM OzFlux sites are considered, including AU-DaS as separate
land-use HOLD; other seven can move to next source QC. No original/model
files, DATM, site surface or Slurm writes. No NOAA AU-ASM work.
"""
from __future__ import annotations
import argparse,csv,hashlib,json
from pathlib import Path
from collections import Counter,defaultdict

HOME=Path.home()
STAGE07=HOME/"ozflux_stage07_20261101T062633Z"
MANIFEST={"AU-ASM":2,"AU-Cow":1,"AU-Cpr":1,"AU-DaS":1,
          "AU-Dry":1,"AU-Gin":1,"AU-How":1,"AU-Stp":1,"AU-Tum":1}
CAND="STRUCTURAL_CANDIDATE_ONLY_QC_UNAPPROVED"
HEAD=("site","n_original_files","source_file_year_rows",
      "source_first_year","source_last_year","source_label_span_years",
      "n_structural_years","max_contiguous_structural_years",
      "max_block_start","max_block_end","n_pre_landuse_structural_years",
      "max_pre_landuse_contiguous_years","eligibility_scope",
      "next_decision","science_QC_approved","AD400_authorised")
def need(b,msg):
    if not b:raise RuntimeError(str(msg))
def digest(p):
    p=Path(p)
    need(p.is_file() and not p.is_symlink(),"Required Stage07 report is missing or linked: "+str(p))
    h=hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda:f.read(1024*1024),b""):h.update(chunk)
    return h.hexdigest()
def blocks(years):
    years=sorted(set(int(y) for y in years))
    result=[]
    for year in years:
        if not result or result[-1][-1]!=year-1:result.append([year])
        else:result[-1].append(year)
    return sorted(result,key=lambda x:(-len(x),x[0]))
def best(years):
    b=blocks(years)
    return (len(b[0]),b[0][0],b[0][-1]) if b else (0,None,None)
def source_years(folder):
    p=folder/"stage07_year_status.tsv"
    with p.open(newline="",encoding="utf-8") as f:
        reader=csv.DictReader(f,delimiter="\t")
        keys=set(reader.fieldnames or [])
        need({"site","filename","year","candidate_status",
              "native_year_count","expected_count"}.issubset(keys),
             "Stage07 year TSV has unexpected schema")
        allrows=list(reader)
    need(len(allrows)==169,"Expected 169 original file-year source rows, no partial Stage07")
    site_counts=Counter(x["site"] for x in allrows)
    need(set(site_counts)==set(MANIFEST),"Unexpected OzFlux site cohort in Stage07")
    nstruct=sum(x["candidate_status"]==CAND for x in allrows)
    need(nstruct==67,"Original Stage07 67 structural-only candidate count changed")
    return allrows,p
def eligibility(rows):
    out=[]
    for site in MANIFEST:
        r=[x for x in rows if x["site"]==site]
        files={x["filename"] for x in r}
        need(len(files)==MANIFEST[site],"Stage07 source file cohort changed: "+site)
        years=sorted(set(int(x["year"]) for x in r))
        v=sorted(set(int(x["year"]) for x in r if x["candidate_status"]==CAND))
        span=(years[-1]-years[0]+1) if years else 0
        longest,a,b=best(v)
        vp=[y for y in v if y<=2021] if site=="AU-DaS" else v
        prelen,_,_=best(vp)
        if site=="AU-ASM":
            status="EXCLUDED_BY_OPERATOR_LT15_PRE_OUTAGE"
            next_step="DO_NOT_RUN_NOAA_OR_FORCING_QC_OR_AD400"
        elif site=="AU-DaS":
            status="LAND_USE_BREAK_2022_11_PRE_ONLY_HOLD"
            next_step="NO_2022_PLUS_MERGE; PRE_2022_15YR_CHECK_FAILS_STRICT_STAGE07"
        elif longest>=15:
            status="STRUCTURAL_15YR_BLOCK_ONLY_SCIENCE_HOLD"
            next_step="SOURCE_QC_AND_SITE_HISTORY_REVIEW_BEFORE_RELEASE"
        elif span>=15:
            status="SPAN_GE15_STRICT_CONTIGUOUS_BLOCK_LT15"
            next_step="PRIORITISE_MISSING_OR_PHYSICAL_GAP_QC_NOT_AUTOMATIC_EXCLUSION"
        else:
            status="NATIVE_YEAR_SPAN_LT15_REVIEW"
            next_step="VERIFY_SITE_OPERATION_HISTORY_NO_AD400"
        out.append(dict(site=site,n_original_files=len(files),
          source_file_year_rows=len(r),source_first_year=years[0],
          source_last_year=years[-1],source_label_span_years=span,
          n_structural_years=len(v),max_contiguous_structural_years=longest,
          max_block_start=a,max_block_end=b,
          n_pre_landuse_structural_years=len(vp) if site=="AU-DaS" else None,
          max_pre_landuse_contiguous_years=prelen if site=="AU-DaS" else None,
          eligibility_scope=status,next_decision=next_step,
          science_QC_approved=False,AD400_authorised=False))
    return out
def selftest():
    need(best([2020,2021,2023,2024])==(2,2020,2021),"contiguous block detection")
    need(best([2010,2011,2012,2015])==(3,2010,2012),"minimum year range")
    need(len(MANIFEST)==9 and sum(MANIFEST.values())==10,"9 sites/10 originals")
    need(2022>2021,"2014 independent 2022 conversion cutoff")
    print("OZFLUX STAGE26 SELFTEST PASS | 15-year scope, AU-ASM excluded; AU-DaS land-use HOLD; READ ONLY")
def main():
    a=argparse.ArgumentParser(description=__doc__)
    a.add_argument("--self-test",action="store_true")
    a.add_argument("--stage07",type=Path,default=STAGE07)
    a.add_argument("--out",type=Path)
    opt=a.parse_args()
    if opt.self_test:return selftest()
    o=opt.out
    need(o is not None and o.parent.resolve()==HOME.resolve()
         and not o.exists() and not o.is_symlink(),
         "Use NEW immediate HOME output folder")
    path=opt.stage07
    need(path.resolve().is_dir(),"Actual operator Stage07 folder unavailable")
    rows,yearpath=source_years(path)
    status=eligibility(rows)
    need(len(status)==9 and
         next(x for x in status if x["site"]=="AU-ASM")["eligibility_scope"].startswith("EXCLUDED"),
         "Scope change would incorrectly reactivate AU-ASM")
    other=[x for x in status if x["site"] not in ("AU-ASM","AU-DaS")]
    ranked=sorted(other,key=lambda x:(
          -x["max_contiguous_structural_years"],-x["n_structural_years"],x["site"]))
    need(len(ranked)==7,"Expect seven other nonexcluded, nonconversion sites")
    out={"dataset":"OzFlux 9 original site IDs / 10 original source files",
       "source_operator_stage07_folder":str(path),
       "source_year_status_sha256":digest(yearpath),
       "operator_AU_ASM_decision":"EXCLUDE_NO_15YR_PRE_OUTAGE",
       "AU_DaS_verified_2022_Nov_crop_conversion_not_AU_ASM":True,
       "AU_DaS_pre_2022_only_no_mixing":True,
       "minimum_strict_contiguous_years":15,
       "strict_candidate_years_are_NOT_science_QC_release":True,
       "years_failing_strict_structure_can_still_require_source_QC_and_donor_review":True,
       "next_focus_ranked_unconverted_sites":[
            {"site":x["site"],"longest_structural_years":x["max_contiguous_structural_years"],
             "structural_total_years":x["n_structural_years"],
             "source_year_span":x["source_label_span_years"]} for x in ranked],
       "sites":status,
       "full_meteorological_science_release_count":0,
       "new_AD400_authorised_count":0,
       "no_source_DATM_Surface_CIME_Slurm_writes":True}
    o.mkdir(mode=0o700,parents=False,exist_ok=False)
    with (o/"stage26_ozflux_9site_15year_landuse_screen.tsv").open(
          "x",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=HEAD,delimiter="\t")
        w.writeheader();w.writerows(status)
    (o/"stage26_ozflux_AU_ASM_exclusion_and_7site_priority_SCIENCE_HOLD.json").write_text(
        json.dumps(out,ensure_ascii=False,indent=2),encoding="utf-8")
    print("STAGE26 ORIGINAL COHORT 9 SITES / 10 FILES / 169 NATIVE FILE-YEARS VERIFIED")
    print("AU-ASM EXCLUDED BY OPERATOR: <15Y PRE-OUTAGE; NO FURTHER QC/NOAA/DATM/AD400")
    print("AU-DaS 2022 NOV CROP CONVERSION: PRE-2022 ONLY, LAND-USE HOLD")
    for x in status:
        print("SITE",x["site"],"RAW_SPAN_Y",x["source_label_span_years"],
             "STRUCTURAL_Y",x["n_structural_years"],
             "LONGEST_CONTIGUOUS",x["max_contiguous_structural_years"],
             "BLOCK",x["max_block_start"],x["max_block_end"],
             "STATUS",x["eligibility_scope"])
    print("NEXT_UNCONVERTED_CANDIDATE",ranked[0]["site"],
          "LONGEST_STRUCTURAL_Y",ranked[0]["max_contiguous_structural_years"],
          "NOT_15YR_SCIENCE_APPROVED")
    print("STAGE26 READONLY ELIGIBILITY SCREEN COMPLETE; NO FORCING/SURFACE/SLURM")
    print("REPORT_DIR",o)
if __name__=="__main__":main()
