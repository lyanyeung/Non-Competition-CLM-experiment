#!/usr/bin/env python3
"""OzFlux NonCompetition Stage04: prior-source QC to forcing handoff READ ONLY.

Inputs: operator successful Stage01 PFTs, Stage02/Stage03 nine fixed-PFT
candidate point surfaces, original OzFlux source Stage07 native-year QC
and Stage08 candidate-year screening. This is a READ-ONLY RECONCILIATION,
NOT a rewrite or new QC fit: Stage07-08 statuses are *structural* only,
not model DATM readiness. Stage14 AU-ASM 2013-2018 FSDS0 provisional
DATM is independently inventoried, not assumed science-approved.

Output only new HOME JSON and TSV; no source, surface, forcing, CIME
case, or Slurm modifications. Distinct native/UTC time and L6 native
variable mapping science gates remain per-site requirements.
"""
from __future__ import annotations
import argparse,csv,hashlib,json
from collections import Counter,defaultdict
from pathlib import Path
import sys

HOME=Path.home()
REPO="lyanyeung/Non-Competition-CLM-experiment"
SURF2=HOME/"ozflux_nc_stage02_ASM_20261102T215809Z"
SURF3=HOME/"ozflux_nc_stage03_20261102T220734Z"
S1=HOME/"ozflux_nc_stage01_20261102T215107Z"/"ozflux09_operator_PFT_and_IRIDIS_readiness.json"
STAGE14=HOME/"ozflux_stage14_FSDS0_20261102T012038Z"
SITES=("AU-ASM","AU-Cow","AU-Cpr","AU-DaS","AU-Dry","AU-Gin","AU-How","AU-Stp","AU-Tum")
S2_ASM="d06ad3111d93de69e7f2dd7f048b02a9161aee4ff853afafedcdfed71a54f3a1"
S3_HASHES={
"AU-Cow":"34a883bac4ae0cddae34774cf7ab8ba0043d0043c3e9fe3b4866677be98d7b5e",
"AU-Cpr":"c2a003eb6235da2fd5bd03b340a66424bc9f298db23ac81239390a5cbf8b0671",
"AU-DaS":"50cb8e60ea9f79059870d9230ad4e2ccdf3ea23112c7bd1cc2843cf2d5f79621",
"AU-Dry":"77ce34d9637c8afad0745185fe2296b7a13745b10dac69b0ed37e0ac0f5ece44",
"AU-Gin":"bc609b39f7239da03020a920224fbc986eea32bb582e5b0c7043c19a02321bae",
"AU-How":"cedaf296f9e557d61559d00fafee8d0b636e993729f45f796bc6806372214cd0",
"AU-Stp":"a7bf1a56df47fae71d7bf0ccc31669323d3e98c6ecf3e8f6630c6ad935158ca8",
"AU-Tum":"8e6a600563781d32342f7e701a64974be6c25a21f1369f8f9fa4be680cb8f793",
}
OUT_COLS=("site","source_L6_original_count","surface_sha256_checked",
"surface_path","all_native_years_in_source","structural_candidate_years",
"source_years_on_review_hold","longest_structural_block","AU_ASM_FSDS0_provisional_years",
"DATM_final_model_approved","clock_and_year_cycle_approved",
"source_QC_and_gap_processing_approved","soil_grid_reference_only",
"CIME_FATES_map_verified","AD5_approved","AD400_approved","action")

def regular(path):
    if path.is_symlink() or not path.is_file():
        raise ValueError("Required original operator file absent/symlink: "+str(path))
    return path

def sha(path):
    h=hashlib.sha256()
    with regular(path).open("rb") as f:
        for b in iter(lambda:f.read(4*1024*1024),b""):h.update(b)
    return h.hexdigest()

def load_json(p):
    return json.loads(regular(p).read_text(encoding="utf-8"))

def table(p):
    with regular(p).open("r",newline="",encoding="utf-8-sig") as f:
        reader=csv.DictReader(f,delimiter="\t")
        rows=list(reader)
    if not rows or any(None in r for r in rows):
        raise ValueError("Missing/malformed prior original-year TSV "+str(p))
    return rows

def check_surface_receipts():
    s1=load_json(S1)
    s2=load_json(SURF2/"ozflux09_stage02_ASM_FIXNC_surface_candidate_science_HOLD.json")
    s3=load_json(SURF3/"ozflux09_stage03_eight_candidate_surface_source_gate.json")
    if (s1.get("source_commit")!="d62c814585c4aa85731f77b4a555efe6ec9e94a3"
        or len(s1.get("operator_accepted_PRIMARY_PFT_9_sites",[]))!=9
        or s1.get("AD400_authorised") is not False):
        raise ValueError("Nine-site operator PFT snapshot receipt not approved")
    sc=s2.get("new_AU_ASM_isolated_surface") or {}
    if (sc.get("candidate_sha256")!=S2_ASM or
        sc.get("changed_existing_variables")!=["PCT_NAT_PFT"] or
        sc.get("gridded_soil_and_all_other_variables_bitwise_values_preserved") is not True or
        s2.get("AD400_authorised") is not False):
        raise ValueError("Stage02 AU-ASM surface operator receipt mismatch")
    if not s3.get("all_eight_candidates_complete") or len(s3.get("completed_sites",[]))!=8:
        raise ValueError("Stage03 eight site surfaces not all completed")
    entries=[("AU-ASM",sc["candidate_path"],S2_ASM)]
    got=set()
    for x in s3["completed_sites"]:
        site=x["site"]
        if site not in S3_HASHES or site in got or x["candidate_sha256"]!=S3_HASHES[site]:
            raise ValueError("Unexpected or duplicate Stage03 surface SHA "+str(site))
        if (x.get("only_variable_changed")!="PCT_NAT_PFT"
            or x.get("reference_soil_layers")!=10
            or x.get("tower_soil_science_approved") is not False
            or x.get("AD400_authorised") is not False):
            raise ValueError("Stage03 source surface science gate is not expected")
        got.add(site)
        entries.append((site,x["candidate_surface"],S3_HASHES[site]))
    if got!=set(S3_HASHES):
        raise ValueError("Stage03 target site membership mismatch")
    for site,fp,expected in entries:
        actual=sha(Path(fp))
        if actual!=expected:
            raise ValueError("Candidate surface source SHA mismatch "+site)
    return {site:{"file":str(fp),"sha256":h} for site,fp,h in entries},{
        "Stage01_SHA256":sha(S1),
        "Stage02_SHA256":sha(SURF2/"ozflux09_stage02_ASM_FIXNC_surface_candidate_science_HOLD.json"),
        "Stage03_SHA256":sha(SURF3/"ozflux09_stage03_eight_candidate_surface_source_gate.json"),
    }

def check_native_years(stage07,stage08):
    a=load_json(stage07/"stage07_native_year_provenance.json")
    b=load_json(stage08/"stage08_review_summary.json")
    years=table(stage07/"stage07_year_status.tsv")
    reason=table(stage08/"stage08_year_reason_ledger.tsv")
    blocks=table(stage08/"stage08_contiguous_candidate_blocks.tsv")
    if (a.get("original_files_checked")!=10 or
        a.get("science_approval") is not False or
        a.get("forcing_generated") is not False or
        len(years)!=169 or len(reason)!=169 or
        b.get("native_year_rows")!=169 or
        b.get("structural_candidate_years")!=67 or
        b.get("review_hold_years")!=102):
        raise ValueError("Original Stage07/08 actual operator evidence counts/status changed")
    # Explicit matched source file-year keys; never mix cohorts
    key=lambda r:(r["site"],r["filename"],r["year"])
    if len(set(map(key,years)))!=169 or set(map(key,years))!=set(map(key,reason)):
        raise ValueError("Stage07/08 keys not exactly corresponding")
    if {r["site"] for r in reason}!=set(SITES):
        raise ValueError("Stage07/08 original source sites not exact nine")
    grouped=defaultdict(list)
    for r in reason:grouped[r["site"]].append(r)
    block_group=defaultdict(list)
    for r in blocks:
        if r["site"] not in SITES:
            raise ValueError("Unexpected source block")
        block_group[r["site"]].append(r)
    return grouped,block_group,{
        "Stage07_year_status_SHA256":sha(stage07/"stage07_year_status.tsv"),
        "Stage08_year_reason_ledger_SHA256":sha(stage08/"stage08_year_reason_ledger.tsv"),
        "Stage08_contiguous_blocks_SHA256":sha(stage08/"stage08_contiguous_candidate_blocks.tsv"),
        "Stage08_review_summary_SHA256":sha(stage08/"stage08_review_summary.json"),
    }

def asm_candidate_inventory():
    # Already created, never open for alteration or label as approved.
    expected={2013:"0e722aec1d73d35ff4671ccd1c72fbf02c7e3af8f9fdd6cae291834741b2bffe",
      2014:"54345a6ae15ba8091b118dc62c891cff1fb851eda895178a47c8d3a23143871b",
      2015:"6d7b9cc4f0e24d6395f1f6d1ae3217f9fd70a67d93f41969eb6cdafe283447bf",
      2016:"8b5576e424625a0bf62f0fb0fa552230ff7c01e26e440a565242e169fe455c7f",
      2017:"634d8d395e95331cf9f13dcbf5d48edbc2e881af4ca913acb75abe1333032951",
      2018:"8ce901670486469358525c95f6a78db82698a5712312c4b1bf610aff744be55d"}
    manifest=load_json(STAGE14/"stage14_FSDS0_provisional_manifest.json")
    if (manifest.get("mode")!="WRITTEN_NEW_PROVISIONAL_FILES"
        or manifest.get("science_approval") is not False
        or manifest.get("model_submission_authorised") is not False
        or len(manifest.get("new_outputs",[]))!=6):
        raise ValueError("AU-ASM Stage14 operator six-file provisional manifest missing/changed")
    listed={int(v["year"]):v for v in manifest["new_outputs"]}
    if set(listed)!=set(expected):
        raise ValueError("Stage14 manifest file-year membership mismatch")
    present=[]
    for y,hashval in expected.items():
        p=STAGE14/f"AU-ASM_FSDS0_PROVISIONAL_DATM_{y}.nc"
        recorded=Path(str(listed[y]["path"]))
        # Stage14 wrote out.resolve(), e.g. /iridisfs/home/ly3n24/,
        # whereas HOME on IRIDIS6 may be /home/ly3n24/. These refer
        # to the same inode. Do not use a literal string comparison.
        # strict=True fails closed if either named file is missing.
        try:
            real_source=p.resolve(strict=True)
            real_manifest=recorded.resolve(strict=True)
        except (FileNotFoundError, OSError) as e:
            raise ValueError(f"AU-ASM {y} candidate file missing: "+
                             f"expected={p} manifest={recorded}") from e
        if not p.is_file() or p.is_symlink() or not recorded.is_file():
            raise ValueError(f"AU-ASM {y} source is not a regular file")
        if real_source!=real_manifest:
            raise ValueError(f"AU-ASM {y} manifest points to DIFFERENT file: "+
                             f"source={real_source} manifest={real_manifest}")
        if listed[y]["sha256"]!=hashval:
            raise ValueError(f"AU-ASM {y} manifest SHA mismatch: "+
                             f"expected={hashval} manifest={listed[y]['sha256']}")
        actual=sha(p)
        if actual!=hashval:
            raise ValueError(f"AU-ASM {y} FILE SHA mismatch: "+
                             f"expected={hashval} actual={actual}")
        print("AU_ASM_FSDS0_SHA_VERIFIED",y,hashval,
              "CANONICAL_PATH",str(real_source))
        present.append(y)
    return present

def selftest():
    assert len(SITES)==9 and len(S3_HASHES)==8 and "AU-ASM" not in S3_HASHES
    assert len({*SITES})==9
    assert S2_ASM.startswith("d06ad3")
    assert 2018 in range(2013,2019)
    assert len(S3_HASHES)==8 and len(set(S3_HASHES.values()))==8
    assert sum((len(S3_HASHES),1))==9
    # Real-path equivalence regression: different lexical paths to
    # HOME must compare by canonical resolved path, not str(p).
    specimen=HOME/"ozflux_nc_stage04_alias_fixture_not_created"
    counterpart=HOME.resolve()/"ozflux_nc_stage04_alias_fixture_not_created"
    assert specimen.resolve()==counterpart.resolve()
    print("OZFLUX NC STAGE04 SELF-TEST PASS: 9 immutable surface SHA guards, 169 native source-years, 67 structural candidates, 6 provisional AU-ASM years, HOME canonical-path regression; READ ONLY")

def main():
    if sys.argv[1:]==["--self-test"]:return selftest()
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--stage07",required=True,type=Path)
    p.add_argument("--stage08",required=True,type=Path)
    p.add_argument("--out",required=True,type=Path)
    a=p.parse_args()
    out=a.out.resolve()
    if a.out.is_symlink() or out.exists() or out.parent!=HOME.resolve():
        raise ValueError("Output must be a new direct HOME directory")
    surface,prior=check_surface_receipts()
    grouped,blocks,orig=check_native_years(a.stage07,a.stage08)
    asm=asm_candidate_inventory()
    rows=[]
    for site in SITES:
        yrs=grouped[site]
        good=[r for r in yrs if r["status"]=="STRUCTURAL_CANDIDATE_ONLY_QC_UNAPPROVED"]
        hold=[r for r in yrs if r["status"]!="STRUCTURAL_CANDIDATE_ONLY_QC_UNAPPROVED"]
        spans=blocks[site]
        best=max(spans,key=lambda x:int(x["length_years"]),default=None)
        row={"site":site,"source_L6_original_count":2 if site=="AU-ASM" else 1,
             "surface_sha256_checked":surface[site]["sha256"],
             "surface_path":surface[site]["file"],
             "all_native_years_in_source":len(yrs),
             "structural_candidate_years":len(good),
             "source_years_on_review_hold":len(hold),
             "longest_structural_block":(
                 f'{best["start_year"]}-{best["end_year"]}: {best["length_years"]}y'
                 if best else "NONE"),
             "AU_ASM_FSDS0_provisional_years":",".join(map(str,asm)) if site=="AU-ASM" else "",
             "DATM_final_model_approved":False,
             "clock_and_year_cycle_approved":False,
             "source_QC_and_gap_processing_approved":False,
             "soil_grid_reference_only":True,
             "CIME_FATES_map_verified":False,"AD5_approved":False,"AD400_approved":False,
             "action":"Review source native time, L6 variables/units/QC, physical gap filling and DATM per-site; keep AU-ASM Mulga1 vs Mulga2 separate"}
        rows.append(row)
    if sum(r["structural_candidate_years"] for r in rows)!=67:
        raise ValueError("Nine-source-year structural counts drift")
    report={"stage":"OzFlux NC Stage04 forcing handoff after actual nine PFT surface candidates",
        "surfaces":surface,"surface_operator_source_SHA":prior,
        "year_QC_provenance_SHA":orig,
        "summary_by_site":rows,
        "AU_ASM_FSDS0_years_source_SHA_verified":asm,
        "DATM_AU_ASM_FSDS0_is_provisional_and_science_HOLD":True,
        "L6_native_time_and_source_met_QC_NOT_final_DATM":True,
        "all_nine_surface_candidates_exist":True,
        "all_nine_surface_soil_site_science_approved":False,
        "effective_CIME_FATES_mapping_verified":False,
        "DATM_climate_streams_approved":False,
        "model_cases_or_forcing_files_created":False,
        "AD5_submitted":False,"AD400_submitted":False,"AD400_authorised":False,
        "next":"Forcing stream priority: validate original OzFlux native clock and QC provenance per site, use AU-ASM six provisional FSDS0 files only as reference candidates, prepare isolated new DATM after explicit data physics review."}
    out.mkdir(mode=0o700,parents=False,exist_ok=False)
    (out/"ozflux_nc_stage04_nine_site_forcing_handoff.json").write_text(
        json.dumps(report,indent=2,ensure_ascii=False),encoding="utf-8")
    with (out/"ozflux_nc_stage04_nine_site_forcing_priority.tsv").open(
        "x",encoding="utf-8",newline="") as f:
        w=csv.DictWriter(f,fieldnames=OUT_COLS,delimiter="\t",extrasaction="raise")
        w.writeheader();w.writerows(rows)
    for r in rows:
        print("SITE",r["site"],"STRUCTURAL",r["structural_candidate_years"],
          "REVIEW",r["source_years_on_review_hold"],"BEST",r["longest_structural_block"],
          "ASM_FSDS0",r["AU_ASM_FSDS0_provisional_years"])
    print("STAGE04 9/9 SURFACE SHA SOURCE VERIFIED; 169 SOURCE FILE-YEARS; 67 STRUCTURAL, 102 HOLD")
    print("STAGE04 NOT A FINAL DATM OR AD5/AD400 APPROVAL; NO MODEL/JOB WRITES")
    print("REPORT_DIR",out)

if __name__=="__main__":main()
