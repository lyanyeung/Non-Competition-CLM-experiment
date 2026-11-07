#!/usr/bin/env python3
"""OzFlux AU-How and AU-Tum REUSE earlier Stage07/08 ORIGINAL source QC.

Do not repeat the 10-site NetCDF scan, reupload HowardSprings/Tumbarumba
originals, rebuild the 9/9 already-created FIXNC surface candidates, or
touch the previously successful AU-How competition case.

Input original operator Stage07: 169 file-years, 67 structural-only, 102
hold; AU-How 2/25 native strict structural candidates, AU-Tum 7/21;
AU-Tum native L6 is hourly, AU-How half-hourly. These are *structural*
standards, not source-certified ≥15 tower-measured years.

Use existing Stage07 year/variable/file reports and optional existing
Stage08 year-reason reports, no data/forcing/model changes or Slurm.
"""
from __future__ import annotations
import argparse,csv,json,collections,os
from pathlib import Path
HOME=Path.home()
ROOT=Path("/iridisfs/scratch/ly3n24/CLM_FATES/sites/MY_EC_SITE")
ST07=HOME/"ozflux_stage07_20261101T062633Z"
F07=ST07/"stage07_file_summary.tsv"
Y07=ST07/"stage07_year_status.tsv"
V07=ST07/"stage07_year_variable_qc.tsv"
J07=ST07/"stage07_native_year_provenance.json"
SITES={"AU-How":("HowardSprings_L6.nc",25,2,1800),
       "AU-Tum":("Tumbarumba1_L6.nc",21,7,3600)}
MET=("Ta","SH","ps","Fsd","Fld","Ws","Precip")
STATUS_CAND="STRUCTURAL_CANDIDATE_ONLY_QC_UNAPPROVED"
STATUS_COLS=("site","year","native_records","expected_records",
 "count_matches","native_boundary_matches","missing_7_met_cells",
 "physics_alarm_7_met_cells","nonzero_QC_met_cells",
 "stage07_structural_status","science_approved","AD400_authorised")
QC_COLS=("site","variable","original_QC0_cells","all_source_cells",
 "native_QC0_fraction_NOT_PROVEN_INSTRUMENT_MEASURED",
 "missing_data_cells","physical_alarm_cells",
 "native_QC10","native_QC50","native_QC400","native_QC410",
 "native_QC420","native_QC430","native_QC440",
 "source_QC_semantics_operator_verified","science_approved")
def need(ok,msg):
    if not ok:raise RuntimeError(str(msg))
def table(path):
    need(path.is_file() and not path.is_symlink(),"Required operator report missing or symlink: "+str(path))
    with path.open(encoding="utf-8-sig",newline="") as f:
        return list(csv.DictReader(f,delimiter="\t"))
def integer(value):
    return int(float(value))
def boolean(value):
    return str(value).strip().lower() in ("true","1")
def print_stats(site,summary,years,variables):
    src=SITES[site][0]
    file=next(r for r in summary if r["site"]==site)
    print("SITE",site,"SOURCE",src,
          "START",file["first_native_time"],
          "END",file["last_native_time"],
          "RECORDS",file["n_records"],
          "NATIVE_MEDIAN_STEP_SEC",file["median_step_seconds"],
          "NONSTANDARD_STEPS",file["nonstandard_steps"],
          "TIME_ZONE_METADATA",file["timezone_metadata"])
    candidate=[int(x["year"]) for x in years if x["candidate_status"]==STATUS_CAND]
    print("STRUCTURAL_ONLY_YEARS",site,candidate,
          "N",len(candidate),"OF",len(years),
          "NOT_TOWER_SCIENCE_APPROVAL")
    rs=collections.Counter(x["candidate_status"] for x in years)
    print("ANNUAL_STAGE07_STATUS",site,dict(rs))
    for var in MET:
        vv=[r for r in variables if r["variable"]==var]
        total=sum(integer(x["records"]) for x in vv)
        q0=sum(integer(x["qc0"]) for x in vv)
        missing=sum(integer(x["missing"]) for x in vv)
        print("SOURCE_MET_QC",site,var,
              "N",total,"QC0",q0,
              "QC0_FRAC_NOT_SOURCE_CERTIFIED",
              f"{q0/total:.5f}" if total else "NA",
              "MISSING",missing)
    for y in years:
        if y["candidate_status"]!=STATUS_CAND:
            print("YEAR_HOLD",site,y["year"],
                  "STATUS",y["candidate_status"],
                  "N",y["native_year_count"],
                  "EXPECTED",y["expected_count"],
                  "BOUNDARY",y["native_label_boundaries_match"],
                  "MISSING_MET_CELLS",y["missing_met_rows_across_fields"],
                  "PHYS_ALARM_CELLS",y["physical_alarm_met_rows_across_fields"])
def save(path,cols,rows):
    with path.open("x",encoding="utf-8",newline="") as f:
        w=csv.DictWriter(f,delimiter="\t",fieldnames=cols,extrasaction="raise")
        w.writeheader();w.writerows(rows)
def test():
    assert len(SITES)==2 and len(MET)==7
    assert SITES["AU-How"][2]==2 and SITES["AU-Tum"][3]==3600
    assert not boolean("False") and boolean("True")
    assert integer("17520")==17520
    print("OZFLUX AU-HOW/TUM SOURCE REUSE SELFTEST PASS | previous Stage07/08, no L6 scan or case changes")
def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--self-test",action="store_true")
    p.add_argument("--out",type=Path)
    args=p.parse_args()
    if args.self_test:return test()
    out=args.out
    need(out is not None and out.parent.resolve()==HOME.resolve()
         and not out.exists() and not out.is_symlink(),
         "Use unused direct HOME result folder only")
    need(J07.is_file() and not J07.is_symlink(),
         "Original Stage07 receipt missing")
    original_j=json.loads(J07.read_text(encoding="utf-8"))
    # Only trust measured source/year rows in the original TSVs. Do NOT claim
    # the Stage07 receipt schema is immutable: guarded raw TSV row counts and
    # site/source names below provide the boundary, not a fabricated key.
    summary=table(F07);yrs=table(Y07);vrs=table(V07)
    need(len(summary)==10 and len(yrs)==169 and len(vrs)==169*7,
         "Original 10/169/1183 Stage07 row totals changed")
    cand_total=sum(r["candidate_status"]==STATUS_CAND for r in yrs)
    need(cand_total==67,"Original Stage07 67 structural-only candidates changed")
    known={x["site"]:x for x in summary}
    need(set(SITES)<=set(known),"Two original OzFlux source summary rows missing")
    annual=[];qcrows=[];overview={};optional_stage08=[]
    for site,(name,nyear,ncand,step) in SITES.items():
        f=known[site]
        need(f["filename"]==name,"Source identity differs from original 10-file OzFlux manifest")
        path=ROOT/site/"forcing"/"raw"/name
        need(path.is_file() and not path.is_symlink(),
             "Original old L6 missing or symbolic link (no rewrite): "+str(path))
        if site=="AU-How":
            need(path.stat().st_size==466671090,
                 "User-verified AU-How 466671090 source bytes changed")
        actual_step=float(f["median_step_seconds"])
        need(abs(actual_step-step)<1.0,
             "Original AU-How halfhour or AU-Tum hourly step changed")
        yy=sorted((x for x in yrs if x["site"]==site),key=lambda r:integer(r["year"]))
        vv=[x for x in vrs if x["site"]==site]
        need(len(yy)==nyear and len(vv)==nyear*7
             and sum(x["candidate_status"]==STATUS_CAND for x in yy)==ncand,
             "Actual Stage07 25/2 AU-How or 21/7 AU-Tum original gate changed")
        need({(x["year"],x["variable"]) for x in vv}==
             {(x["year"],v) for x in yy for v in MET},
             "Original seven per-variable QC source records for years missing")
        print_stats(site,summary,yy,vv)
        for x in yy:
            annual.append({
              "site":site,"year":x["year"],
              "native_records":x["native_year_count"],
              "expected_records":x["expected_count"],
              "count_matches":x["time_count_matches"],
              "native_boundary_matches":x["native_label_boundaries_match"],
              "missing_7_met_cells":x["missing_met_rows_across_fields"],
              "physics_alarm_7_met_cells":x["physical_alarm_met_rows_across_fields"],
              "nonzero_QC_met_cells":x["flagged_nonzero_met_cell_count"],
              "stage07_structural_status":x["candidate_status"],
              "science_approved":False,"AD400_authorised":False})
        for var in MET:
            varrows=[x for x in vv if x["variable"]==var]
            total=sum(integer(x["records"]) for x in varrows)
            q0=sum(integer(x["qc0"]) for x in varrows)
            qcrows.append({
              "site":site,"variable":var,
              "original_QC0_cells":q0,"all_source_cells":total,
              "native_QC0_fraction_NOT_PROVEN_INSTRUMENT_MEASURED":round(q0/total,6),
              "missing_data_cells":sum(integer(x["missing"]) for x in varrows),
              "physical_alarm_cells":sum(integer(x["physical_alarm"] or 0) for x in varrows),
              **{"native_QC"+str(flag):sum(integer(x["qc"+str(flag)]) for x in varrows)
                 for flag in (10,50,400,410,420,430,440)},
              "source_QC_semantics_operator_verified":False,"science_approved":False})
        overview[site]={
         "source_path":str(path),"original_native_file_bytes":path.stat().st_size,
         "previous_Stage07_source_first_native":f["first_native_time"],
         "previous_Stage07_source_last_native":f["last_native_time"],
         "previous_Stage07_source_step_seconds":actual_step,
         "previous_Stage07_native_annual_years":nyear,
         "Stage07_structural_years_NOT_science_approved":ncand,
         "structural_only_year_labels":[int(x["year"]) for x in yy if x["candidate_status"]==STATUS_CAND],
         "original_Stage07_missing_cells_seven_met":sum(integer(x["missing_met_rows_across_fields"]) for x in yy),
         "strict_15_year_sufficient_measured_met_coverage_approved":False,
         "new_FIXNC_AD400_authorised":False}
    summaries=sorted(HOME.glob("ozflux_stage08_*/stage08_review_summary.json"))
    ledgerpaths=sorted(HOME.glob("ozflux_stage08_*/stage08_year_reason_ledger.tsv"))
    if summaries:
        print("PRIOR_STAGE08_SUMMARY_FILES",len(summaries))
        for p0 in summaries[-4:]:print("STAGE08_PRIOR_SUMMARY",p0)
    if ledgerpaths:
        latest=ledgerpaths[-1]
        lr=table(latest)
        selected=[row for row in lr if row.get("site") in SITES]
        print("PRIOR_STAGE08_LEDGER",latest,"SELECTED_ROWS",len(selected))
        optional_stage08=selected
    else:
        print("PRIOR_STAGE08_LEDGER_NOT_FOUND | using validated Stage07 outputs only")
    out.mkdir(mode=0o700,exist_ok=False)
    save(out/"au_how_tum_existing_Stage07_year_causes_READONLY.tsv",STATUS_COLS,annual)
    save(out/"au_how_tum_existing_Stage07_seven_met_QC_readonly.tsv",QC_COLS,qcrows)
    if optional_stage08:
        original_fields=list(optional_stage08[0].keys())
        save(out/"au_how_tum_existing_Stage08_year_reasons_untouched.tsv",
             original_fields,optional_stage08)
    report={
        "scope":"AU-How + AU-Tum existing OzFlux source science gate",
        "source_previous_operator_Stage07_folder":str(ST07),
        "previous_Stage07_file_year_rows":len(yrs),
        "previous_Stage07_total_structural_candidate_only":cand_total,
        "previous_Stage07_file_year_hold":len(yrs)-cand_total,
        "previous_Stage07_receipt_file":str(J07),
        "original_receipt_was_parsed_NOT_mutated":bool(original_j),
        "Stage08_prior_existing_ledgers_found":len(ledgerpaths),
        "sites":overview,
        "previous_successful_AU_How_competition_run_DO_NOT_modify":True,
        "AU_Tum_old_native_hourly_must_not_force_halfhour_DATM":True,
        "nine_existing_fixed_PFT_Surface_candidates_must_not_rebuild":True,
        "QCFlag0_is_NOT_automatically_verified_instrument_observation":True,
        "stage07_structural_candidate_IS_NOT_source_approval":True,
        "new_noncompetition_AD5_or_AD400_submission_independently_checked":False,
        "future_model_run_authorised":False,
        "no_original_or_surface_or_forcing_or_cime_or_slurm_changes":True}
    (out/"au_how_tum_prior_work_reuse_and_source_eligibility_HOLD.json").write_text(
           json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    print("AU-HOW/TUM PREVIOUS STAGE07 REPORT REUSE PASS | source-only, NO original L6 rescan")
    print("NEW FIXNC MODELS BOTH SCIENCE HOLD | no AD5/AD400, no surface or CIME changes")
    print("REPORT_DIR",out)
if __name__=="__main__":main()
