#!/usr/bin/env python3
"""AU-How/AU-Tum Stage06: SOURCE report reuse, annual QC provenance and gap triage.

Actual Stage05 operator PASS 2026-11-07 05:34 UTC:
  AU-How native time: 2002–2026; 23 fully time-labelled calendar years
    2003–2025, 2/25 strictly zero-gap structural candidates, 351 missing
    source cells (345 Ws, 6 Fsd), 0 broad physics alarm.
  AU-Tum native time: 2002–2022, hourly; 19 fully time-labelled calendar
    years 2003–2021, 7/21 strictly zero-gap structural candidates, 658
    missing SH source cells total (44 start-year, 417 end-year, 197
    in the 19 full time-labelled years), 0 broad physics alarm.

These facts DO NOT prove 15 scientifically verified *measured* tower years.
Native QCFlag0 is original pipeline category not verified instrument provenance.
A year containing any missing met cell failed Stage07 conservative gate, but
few original gaps do NOT imply the full year is unobserved.

Read existing Stage07/08 immutable operator reports, Stage05 receipt and source
L6 path identities, but do NOT re-read any original NetCDF variable data. This
script creates ONLY fresh HOME TSV and JSON science-HOLD reports. It does not
modify original data, existing AU-How competition case, FIXNC PFT surfaces,
CIME, forcing, Slurm or the seven-variable QCFlag records.
"""
from __future__ import annotations
import argparse,csv,json,math,collections
from pathlib import Path

HOME=Path.home()
ROOT=Path("/iridisfs/scratch/ly3n24/CLM_FATES/sites/MY_EC_SITE")
D07=HOME/"ozflux_stage07_20261101T062633Z"
D08=HOME/"ozflux_stage08_20261101T063058Z"
D05=HOME/"ozflux_how_tum_reuse_20261107T053429Z"
ORIGINALS={
 "AU-How":{"file":"HowardSprings_L6.nc","years":25,"strict":2,
           "full_year_range":list(range(2003,2026)),"step":1800,
           "total_missing":351,"complete_native_year_missing":351,
           "QC0_weak_variable":"Precip"},
 "AU-Tum":{"file":"Tumbarumba1_L6.nc","years":21,"strict":7,
           "full_year_range":list(range(2003,2022)),"step":3600,
           "total_missing":658,"complete_native_year_missing":197,
           "QC0_weak_variable":"Fld"}}
MET=("Ta","SH","ps","Fsd","Fld","Ws","Precip")
STATUS_CAND="STRUCTURAL_CANDIDATE_ONLY_QC_UNAPPROVED"
YEAR_COLS=("site","year","original_time_count","expected_time_count",
 "native_calendar_time_axis_full","Stage07_original_status",
 "Stage08_original_reason_codes","missing_Ta","missing_SH","missing_ps",
 "missing_Fsd","missing_Fld","missing_Ws","missing_Precip",
 "all_seven_met_missing_cells","broad_physics_alarm_cells",
 "unscreened_broad_physics_variable_names",
 "all_met_variables_no_data_gaps","minimum_original_QC0_fraction_7_met",
 "minimum_original_QC0_variable","mean_original_QC0_fraction_7_met",
 "source_observation_15years_scientifically_verified",
 "forcing_and_AD400_approved")
VAR_COLS=("site","year","variable","native_data_cells",
 "original_QC0_cells","original_QC0_fraction_NOT_verified_observation",
 "missing_original_data_cells","original_broad_physics_alarm_cells",
 "native_QC10_cells","native_QC50_cells","native_QC400_cells",
 "native_QC410_cells","native_QC420_cells","native_QC430_cells",
 "native_QC440_cells","original_QC0_instrument_provenance_verified",
 "forcing_repair_approved")
def need(ok,msg):
    if not ok:raise RuntimeError(str(msg))
def read(p):
    need(p.is_file() and not p.is_symlink(),
         "Existing read-only operator report missing or symlink: "+str(p))
    with p.open(encoding="utf-8-sig",newline="") as h:
        return list(csv.DictReader(h,delimiter="\t"))
def jread(p):
    need(p.is_file() and not p.is_symlink(),
         "Existing prior receipt missing or symlink "+str(p))
    return json.loads(p.read_text(encoding="utf-8"))
def val(r,k):
    x=r.get(k)
    need(x not in (None,""),"Prior source report missing "+k+" in "+str(r)[:180])
    return int(float(x))
def nullable_alarm(r):
    x=r.get("physical_alarm")
    if x in ("",None):return None
    z=int(float(x))
    need(z>=0,"Negative original alarm count")
    return z
def truth(r,k):
    x=r.get(k)
    need(x in ("True","False"),"Prior source report boolean "+k+" invalid")
    return x=="True"
def table(path,cols,items):
    with path.open("x",encoding="utf-8",newline="") as h:
        w=csv.DictWriter(h,delimiter="\t",fieldnames=cols,extrasaction="raise")
        w.writeheader();w.writerows(items)
def selftest():
    need(sum([345,6])==351 and 658-44-417==197,
         "Original AU-How/Tum source missing-count separation")
    need(len(ORIGINALS["AU-How"]["full_year_range"])==23
         and len(ORIGINALS["AU-Tum"]["full_year_range"])==19,
         "23/19 full calendar native time-year discovery")
    need(val({"x":"17568"},"x")==17568
         and truth({"x":"True"},"x"),"Exact Stage07 source code parsing")
    print("OZFLUX HOW/TUM STAGE06 SELFTEST PASS | annual QC0 vs 23/19 full time years distinct from strict no-gap 2/7; READ ONLY")
def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--self-test",action="store_true")
    p.add_argument("--out",type=Path)
    args=p.parse_args()
    if args.self_test:return selftest()
    dest=args.out
    need(dest is not None and dest.parent.resolve()==HOME.resolve()
         and not dest.exists() and not dest.is_symlink(),
         "Use an unused new direct HOME report directory only")
    j5=jread(D05/"au_how_tum_prior_work_reuse_and_source_eligibility_HOLD.json")
    need(j5.get("previous_Stage07_file_year_rows")==169
         and j5.get("previous_Stage07_total_structural_candidate_only")==67
         and j5.get("previous_Stage07_file_year_hold")==102
         and j5.get("future_model_run_authorised") is False
         and j5.get("no_original_or_surface_or_forcing_or_cime_or_slurm_changes") is True,
         "Actual operator Stage05 receipt identity/status changed")
    old7=jread(D07/"stage07_native_year_provenance.json")
    old8=jread(D08/"stage08_review_summary.json")
    f7=read(D07/"stage07_file_summary.tsv")
    y7=read(D07/"stage07_year_status.tsv")
    v7=read(D07/"stage07_year_variable_qc.tsv")
    ledger=read(D08/"stage08_year_reason_ledger.tsv")
    qc8=read(D08/"stage08_source_qc_per_year.tsv")
    need(len(f7)==10 and len(y7)==169 and len(v7)==1183
         and len(ledger)==169 and len(qc8)==1183,
         "Original 10-file/169 annual/1183 variable rows not preserved")
    need(sum(x["candidate_status"]==STATUS_CAND for x in y7)==67,
         "Actual Stage07 candidate/HOLD classification changed")
    yindex={(r["site"],r["filename"],r["year"]):r for r in y7}
    vindex={(r["site"],r["filename"],r["year"],r["variable"]):r for r in v7}
    lindex={(r["site"],r["filename"],r["year"]):r for r in ledger}
    qindex={(r["site"],r["filename"],r["year"],r["variable"]):r for r in qc8}
    need(len(yindex)==len(lindex)==169 and
         len(vindex)==len(qindex)==1183 and set(yindex)==set(lindex)
         and set(vindex)==set(qindex),
         "Prior Stage07/08 source keys duplicate or differ")
    need(sum(len([x for x in y7 if x["site"]==site]) for site in ORIGINALS)==46,
         "Original 46 AU-How/AU-Tum source file-years changed")
    year_out=[];var_out=[];results={}
    for site,meta in ORIGINALS.items():
        name=meta["file"]
        frow=next((x for x in f7 if x["site"]==site and x["filename"]==name),None)
        need(frow is not None,"Original Stage07 site/source identity missing "+site)
        src=ROOT/site/"forcing"/"raw"/name
        need(src.is_file() and not src.is_symlink(),
             "Existing L6 source missing or symlink "+str(src))
        need(abs(float(frow["median_step_seconds"])-meta["step"])<1,
             "Original old-L6 30min/60min native sampling has changed")
        oldys=sorted((r for r in y7 if r["site"]==site),key=lambda r:int(r["year"]))
        need(len(oldys)==meta["years"] and
             sum(r["candidate_status"]==STATUS_CAND for r in oldys)==meta["strict"],
             "Original Stage07 "+site+" 25/2 or 21/7 source classification changed")
        full=[];year_missing=0;all_missing=0;counts=collections.Counter()
        for y in oldys:
            year=y["year"]
            ky=site,name,year
            l=lindex[ky]
            need(l["status"]==y["candidate_status"] and
                 val(l,"met_missing_cells")==val(y,"missing_met_rows_across_fields"),
                 "Stage08 and Stage07 annual event count/status diverged "+str(ky))
            isfull=truth(y,"time_count_matches") and truth(y,"native_label_boundaries_match")
            if isfull:full.append(int(year))
            counts[y["candidate_status"]]+=1
            varrows=[vindex[(site,name,year,v)] for v in MET]
            allmissing=sum(val(r,"missing") for r in varrows)
            need(allmissing==val(y,"missing_met_rows_across_fields"),
                 "Annual seven-variable source-gap accounting mismatch "+str(ky))
            unchecked=[variable for variable,row in zip(MET,varrows)
                       if nullable_alarm(row) is None]
            totalalarms=sum(nullable_alarm(r) or 0 for r in varrows)
            need(totalalarms==val(y,"physical_alarm_met_rows_across_fields")
                 and totalalarms==0,"Unexpected original source physics alarms "+str(ky))
            all_missing+=allmissing
            if isfull:year_missing+=allmissing
            fractions=[]
            for variable,row in zip(MET,varrows):
                k=site,name,year,variable
                other=qindex[k]
                n=val(row,"records")
                q0=val(row,"qc0")
                need(q0<=n and
                     val(other,"native_qc0")==q0 and
                     val(other,"missing")==val(row,"missing"),
                     "Original Stage07/08 per-year QC0/met missing totals diverged "+str(k))
                frac=q0/n if n else 0.0
                fractions.append((variable,frac))
                var_out.append({
                  "site":site,"year":year,"variable":variable,
                  "native_data_cells":n,"original_QC0_cells":q0,
                  "original_QC0_fraction_NOT_verified_observation":round(frac,6),
                  "missing_original_data_cells":val(row,"missing"),
                  "original_broad_physics_alarm_cells":nullable_alarm(row),
                  **{"native_QC"+str(flag)+"_cells":val(row,"qc"+str(flag))
                     for flag in (10,50,400,410,420,430,440)},
                  "original_QC0_instrument_provenance_verified":False,
                  "forcing_repair_approved":False})
            minvar,minfrac=min(fractions,key=lambda t:t[1])
            avg=sum(x for _,x in fractions)/len(fractions)
            year_out.append({
              "site":site,"year":year,
              "original_time_count":val(y,"native_year_count"),
              "expected_time_count":val(y,"expected_count"),
              "native_calendar_time_axis_full":isfull,
              "Stage07_original_status":y["candidate_status"],
              "Stage08_original_reason_codes":l["reason_codes"],
              **{"missing_"+v:val(vindex[(site,name,year,v)],"missing") for v in MET},
              "all_seven_met_missing_cells":allmissing,
              "broad_physics_alarm_cells":totalalarms,
              "unscreened_broad_physics_variable_names":";".join(unchecked),
              "all_met_variables_no_data_gaps":allmissing==0,
              "minimum_original_QC0_fraction_7_met":round(minfrac,6),
              "minimum_original_QC0_variable":minvar,
              "mean_original_QC0_fraction_7_met":round(avg,6),
              "source_observation_15years_scientifically_verified":False,
              "forcing_and_AD400_approved":False})
            print("YEAR_SOURCE_GATE",site,year,"FULL_NATIVE_CALENDAR",isfull,
                  "MISSING_CELLS",allmissing,
                  "MISSING_VARS",
                  {v:val(vindex[(site,name,year,v)],"missing")
                   for v in MET if val(vindex[(site,name,year,v)],"missing")>0},
                  "WEAKEST_QC0",minvar,round(minfrac,4),
                  "UNSCREENED_UNITS",unchecked,
                  "STAGE08_REASONS",l["reason_codes"])
        need(full==meta["full_year_range"],"Original "+site+" complete-year native chronology altered")
        need(all_missing==meta["total_missing"] and
             year_missing==meta["complete_native_year_missing"],
             "Original "+site+" total (and in-full-year) missing seven-met changed")
        print("SITE_NATIVE_FULL_YEARS",site,full[0],full[-1],
              "YEARS",len(full),
              "ALL_FULL_YEAR_MISSING_SOURCE_CELLS",year_missing,
              "ZERO_MISSING_STRUCTURAL_CANDIDATES",meta["strict"],
              "NOT_15Y_SCIENCE_APPROVAL")
        results[site]={
          "old_original_L6_path":str(src),
          "L6_byte_count":src.stat().st_size,
          "native_time_zone":frow["timezone_metadata"],
          "native_step_seconds":meta["step"],
          "source_full_calendar_time_axis_years":len(full),
          "source_full_calendar_year_labels":full,
          "Stage07_no_missing_structural_only_year_count":meta["strict"],
          "Stage07_annual_status_counts":dict(counts),
          "full_year_original_missing_met_cells":year_missing,
          "all_source_year_missing_met_cells":all_missing,
          "QC0_is_not_instrument_measurement_provenance":True,
          "strict_15_real_measured_years_approved":False,
          "forcing_and_AD400_authorised":False}
    need(len(year_out)==46 and len(var_out)==46*7,
         "AU-How/Tum 46 years/322 per-variable rows not complete")
    dest.mkdir(mode=0o700,exist_ok=False)
    table(dest/"stage06_AU_How_Tum_46year_source_gap_and_QC0_gate.tsv",
          YEAR_COLS,year_out)
    table(dest/"stage06_AU_How_Tum_322year_variable_original_QC0_provenance.tsv",
          VAR_COLS,var_out)
    report={
       "stage":"AU-How/Tum annual SOURCE coverage triage reusing prior Stage07/08",
       "source_Stage05_receipt_path":str(D05),
       "old_Stage07_file_years":169,
       "old_Stage08_original_file_years":169,
       "old_Stage07_original_source_variable_years":1183,
       "old_Stage08_original_source_variable_years":1183,
       "old_Stage07_receipt_exists":bool(old7),
       "old_Stage08_receipt_exists":bool(old8),
       "two_sites_original_year_rows":len(year_out),
       "two_sites_original_QC_provenance_rows":len(var_out),
       "sites":results,
       "23_19_full_time_years_do_not_equate_to_15_measured_year_approval":True,
       "no_original_data_rewrite_or_L6_full_rescan":True,
       "original_OLD_AU_How_competition_case_protected":True,
       "existing_9_FIXED_PFT_surface_candidates_protected":True,
       "AU_Tum_hourly_requires_independent_ATM_NCPL":True,
       "science_source_QC0_certified":False,
       "science_fix_or_DATM_writes":False,
       "CIME_Slurm_model_submit":False,
       "AD400_authorised":False}
    (dest/"stage06_AU_How_Tum_annual_QC0_15yr_source_HOLD.json").write_text(
          json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    print("OZFLUX HOW/TUM STAGE06 ANNUAL SOURCE/QC REUSE PASS | 46 YEARS; NO NEW L6 SCAN")
    print("STRICT 15Y TOWER-MEASURED SOURCE SCIENCE HOLD | NO REPAIRS, NO DATM/CIME/AD400")
    print("REPORT_DIR",dest)
if __name__=="__main__":main()
