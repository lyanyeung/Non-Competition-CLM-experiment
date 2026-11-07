#!/usr/bin/env python3
"""OzFlux AU-How/AU-Tum Stage07 | source-only annual QCFlag and 15-year sensitivity.

STRICTLY READ ONLY, reuse original Stage06 operator reports:
  AU-How: 23 complete native calendar-time years 2003–2025,
          only 2 zero-gap 7-met years; 351 source missing cells.
  AU-Tum: 19 complete native calendar-time years 2003–2021,
          only 7 zero-gap 7-met years; 197 missing source cells
          *within complete native-year time axes*.

There is a critical difference between (a) a time-axis-complete year,
(b) a year containing some native QCFlag0, and (c) a *scientifically
validated* instrument-measured year. This script ONLY assesses (a)
and (b), not (c). QCFlag codes 10/50/400/410/420/430/440 are
reported as original source codes; codebook interpretations are NOT
assumed to prove exactly which donor/metadata generated them.
15-year window percentages 0/50/80/90 are diagnostic sensitivity
cuts, NEVER new release eligibility criteria.

No original NetCDF read, no original/forcing/surface/CIME changes,
no Slurm, and no AD400 authorised.
"""
from __future__ import annotations
import argparse,csv,json,collections,math
from pathlib import Path

HOME=Path.home()
SRC=HOME/"ozflux_how_tum_stage06_20261107T054225Z"
RECEIPT=SRC/"stage06_AU_How_Tum_annual_QC0_15yr_source_HOLD.json"
YFILE=SRC/"stage06_AU_How_Tum_46year_source_gap_and_QC0_gate.tsv"
VFILE=SRC/"stage06_AU_How_Tum_322year_variable_original_QC0_provenance.tsv"
YEARS={"AU-How":list(range(2003,2026)),"AU-Tum":list(range(2003,2022))}
EXPECTED={"AU-How":(23,351,2),"AU-Tum":(19,197,7)}
MET=("Ta","SH","ps","Fsd","Fld","Ws","Precip")
FLAGS=(10,50,400,410,420,430,440)
THRESHOLDS=(0.0,0.50,0.80,0.90)
TARGETS={"AU-How":(("Precip",2003,2011),("Precip",2012,2012),
                    ("Fld",2025,2025),("Ws",2011,2011)),
         "AU-Tum":(("Fld",2003,2007),("Fsd",2015,2015),
                   ("Ws",2020,2020),("SH",2011,2011))}
ANNUAL_COLUMNS=("site","year","variable","native_records","native_QC0",
 "native_QC0_fraction_NOT_verified_tower_measurement","original_missing",
 "original_QC10","original_QC50","original_QC400",
 "original_QC410","original_QC420","original_QC430","original_QC440",
 "unlisted_or_missing_QC_codes","original_source_QC0_provenance_verified",
 "scientific_year_approved")
WINDOW_COLUMNS=("site","start_year","end_year","length_native_full_years",
 "all_native_time_axes_full","total_original_missing_7met_cells",
 "number_source_variable_years","minimum_QC0_fraction_in_15y_7met_grid",
 "minimum_QC0_site_variable_year",
 "zero_QC0_original_variable_years",
 "number_below_50pct_original_QC0_cells",
 "number_below_80pct_original_QC0_cells",
 "number_below_90pct_original_QC0_cells",
 "variable_years_with_native_missing_values",
 "diagnostic_all_variable_years_with_nonzero_QC0",
 "diagnostic_all_variable_years_with_at_least_50pct_QC0",
 "diagnostic_all_variable_years_with_at_least_80pct_QC0",
 "diagnostic_all_variable_years_with_at_least_90pct_QC0",
 "15_real_measured_years_science_approved",
 "AD400_authorised")
def need(x,s):
    if not x:raise RuntimeError(str(s))
def read(p):
    need(p.is_file() and not p.is_symlink(),"Prior operator TSV not found or symlink: "+str(p))
    with p.open(encoding="utf-8-sig",newline="") as f:
        return list(csv.DictReader(f,delimiter="\t"))
def integer(x):
    return int(float(x))
def value(x):
    return float(x)
def output(p,cols,rows):
    with p.open("x",encoding="utf-8",newline="") as f:
        w=csv.DictWriter(f,delimiter="\t",fieldnames=cols,extrasaction="raise")
        w.writeheader();w.writerows(rows)
def selftest():
    need(len(YEARS["AU-How"])==23 and len(YEARS["AU-Tum"])==19,"23/19 complete calendar native years")
    need(len(YEARS["AU-How"])-15+1==9,"9 AU-How 15-year windows")
    need(len(YEARS["AU-Tum"])-15+1==5,"5 AU-Tum 15-year windows")
    need(len(THRESHOLDS)==4 and all(THRESHOLDS[i]<THRESHOLDS[i+1]
             for i in range(len(THRESHOLDS)-1)),"Monotonic descriptive sensitivity")
    print("OZFLUX HOW/TUM STAGE07 SELFTEST PASS | 14 fifteen-year source-only windows, no QC0 instrument-source assumptions")
def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--self-test",action="store_true")
    p.add_argument("--out",type=Path)
    a=p.parse_args()
    if a.self_test:return selftest()
    dest=a.out
    need(dest is not None and dest.parent.resolve()==HOME.resolve()
         and not dest.exists() and not dest.is_symlink(),
         "New direct HOME folder only")
    need(RECEIPT.is_file() and not RECEIPT.is_symlink(),
         "Actual Stage06 receipt missing")
    receipt=json.loads(RECEIPT.read_text(encoding="utf-8"))
    need(receipt.get("two_sites_original_year_rows")==46
         and receipt.get("two_sites_original_QC_provenance_rows")==322
         and receipt.get("science_source_QC0_certified") is False
         and receipt.get("AD400_authorised") is False,
         "Original Stage06 science HOLD receipt changed")
    y=read(YFILE);v=read(VFILE)
    need(len(y)==46 and len(v)==322,"Original annual Stage06 rows changed")
    ys={(r["site"],integer(r["year"])):r for r in y}
    vs={(r["site"],integer(r["year"]),r["variable"]):r for r in v}
    need(len(ys)==46 and len(vs)==322,"Duplicate original annual-source rows")
    expectkeys={(site,year,var) for site,yrs in YEARS.items()
                for year in yrs for var in MET}
    need(expectkeys.issubset(vs),"Original complete native-year 7-meteorology sample missing")
    ann=[];windows=[];scenarios={}
    for site,full in YEARS.items():
        allsiteyears=sorted(yr for s,yr in ys if s==site)
        ny,missfull,no_missing_candidates=EXPECTED[site]
        need(len(allsiteyears)==ny+2 and len(full)==ny,
             "Source calendar number of complete/partial years changed "+site)
        subset=[ys[(site,yr)] for yr in full]
        need(all(x["native_calendar_time_axis_full"]=="True" for x in subset),
             "Previously full native calendar-year is no longer full "+site)
        need(sum(integer(x["all_seven_met_missing_cells"]) for x in subset)==missfull,
             "Original total source 7-meteorology missing cells in complete years changed")
        need(sum(x["all_met_variables_no_data_gaps"]=="True" for x in subset)==no_missing_candidates,
             "Original conservative zero-missing annual count changed")
        sv={}
        for yr in full:
            for var in MET:
                r=vs[(site,yr,var)]
                n=integer(r["native_data_cells"])
                q0=integer(r["original_QC0_cells"])
                missing=integer(r["missing_original_data_cells"])
                need(n>0 and 0<=q0<=n and 0<=missing<=n,
                     "Original QC0/missing source counts outside bound")
                counted={f:integer(r["native_QC"+str(f)+"_cells"]) for f in FLAGS}
                need(all(x>=0 for x in counted.values()) and
                     q0+sum(counted.values())<=n,
                     "Original QCFlag histogram invalid for "+site+str(yr)+var)
                other=n-q0-sum(counted.values())
                frac=q0/n
                sv[yr,var]=(frac,n,q0,missing,other,counted)
                ann.append({
                 "site":site,"year":yr,"variable":var,
                 "native_records":n,"native_QC0":q0,
                 "native_QC0_fraction_NOT_verified_tower_measurement":round(frac,6),
                 "original_missing":missing,
                 **{"original_QC"+str(f):counted[f] for f in FLAGS},
                 "unlisted_or_missing_QC_codes":other,
                 "original_source_QC0_provenance_verified":False,
                 "scientific_year_approved":False})
        print("QC_SOURCE_YEAR_PROFILE",site,"N_FULL_NATIVE_YEARS",len(full))
        for var,begin,end in TARGETS[site]:
            for yr in range(begin,end+1):
                frac,n,q0,missing,other,counts=sv[yr,var]
                print("FOCUS_QC_ORIGIN",site,yr,var,
                      "QC0",q0,"RECORDS",n,
                      "QC0_PCT",round(100*frac,3),
                      "MISSING",missing,"FLAG_CODES",json.dumps(counts),
                      "OTHER_OR_MISSING_FLAG_CODES",other,
                      "SOURCE_ORIGIN_NOT_APPROVED")
        for start in full[:len(full)-15+1]:
            sel=list(range(start,start+15))
            need(sel[-1] in full,"Window not composed of full native calendar-year labels")
            grid=[(yr,var,*sv[yr,var]) for yr in sel for var in MET]
            worst=min(grid,key=lambda r:r[2])
            floor=worst[2]
            zero=sum(x[2]==0 for x in grid)
            below={int(c*100):sum(x[2]<c for x in grid)
                   for c in (0.5,0.8,0.9)}
            gap=sum(x[5]>0 for x in grid)
            gapcells=sum(integer(ys[site,yr]["all_seven_met_missing_cells"])
                         for yr in sel)
            windows.append({
              "site":site,"start_year":start,"end_year":start+14,
              "length_native_full_years":15,
              "all_native_time_axes_full":True,
              "total_original_missing_7met_cells":gapcells,
              "number_source_variable_years":len(grid),
              "minimum_QC0_fraction_in_15y_7met_grid":round(floor,6),
              "minimum_QC0_site_variable_year":f"{worst[1]}:{worst[0]}",
              "zero_QC0_original_variable_years":zero,
              "number_below_50pct_original_QC0_cells":below[50],
              "number_below_80pct_original_QC0_cells":below[80],
              "number_below_90pct_original_QC0_cells":below[90],
              "variable_years_with_native_missing_values":gap,
              "diagnostic_all_variable_years_with_nonzero_QC0":zero==0,
              "diagnostic_all_variable_years_with_at_least_50pct_QC0":below[50]==0,
              "diagnostic_all_variable_years_with_at_least_80pct_QC0":below[80]==0,
              "diagnostic_all_variable_years_with_at_least_90pct_QC0":below[90]==0,
              "15_real_measured_years_science_approved":False,
              "AD400_authorised":False})
            print("FIFTEEN_YEAR_SOURCE_SENSITIVITY",site,start,start+14,
                  "NATIVE_YEAR_AXIS_FULL",True,
                  "N_SOURCE_CELLS_MISSING",gapcells,
                  "LOWEST_QC0",f"{worst[1]}:{worst[0]}",round(floor,6),
                  "ZERO_QC0_VAR_YEARS",zero,
                  "VAR_YEARS_QC0_LT50",below[50],
                  "LT80",below[80],"LT90",below[90],
                  "NOT_SCIENCE_APPROVAL")
        scenarios[site]={
          "full_native_years":len(full),
          "15yr_windows_examined":len(full)-15+1,
          "per_7_met_source_QC0_instrument_lineage_verified":False,
          "actual_tower_observation_duration_15yr_approved":False,
          "new_AD400_authorised":False}
    need(len(ann)==(23+19)*7 and len(windows)==9+5,
         "Original 42 annual full-year sets/14 sliding windows not preserved")
    dest.mkdir(mode=0o700,exist_ok=False)
    output(dest/"stage07_AU_How_Tum_294_full_year_variable_original_QCflag_counts.tsv",
           ANNUAL_COLUMNS,ann)
    output(dest/"stage07_AU_How_Tum_14_fifteen_year_windows_QC0_sensitivity_NO_RELEASE.tsv",
           WINDOW_COLUMNS,windows)
    report={
      "stage":"AU-How AU-Tum 15-year native-time/QCFlag sensitivity, science HOLD",
      "prior_Stage06_operator_receipt":str(RECEIPT),
      "prior_Stage06_original_46_year_source_QC_tsv":str(YFILE),
      "prior_Stage06_original_322_variable_QC_tsv":str(VFILE),
      "15year_windows":len(windows),
      "full_year_variable_rows":len(ann),
      "years_per_site":scenarios,
      "thresholds_0_50_80_90pct_ARE_DESCRIPTIVE_NOT_approval":True,
      "site_specific_QCFlag_codes_NOT_independent_measured_source":True,
      "annual_time_axis_full_NOT_equivalent_to_measured_year":True,
      "not_a_gapfill_or_D​ATM_or_approved_forcing_product":True,
      "prior_successful_AU_How_Competition_CIME_remains_untouched":True,
      "9_existing_FIXNC_surface_candidates_not_rebuilt":True,
      "AU_Tum_hourly_not_resampled":True,
      "science_release":False,"AD400_authorised":False,
      "no_source_netCDF_or_Slurm_mutation":True}
    (dest/"stage07_AU_How_Tum_15year_original_source_provenance_HOLD.json").write_text(
          json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    print("HOW/TUM STAGE07 REPORT REUSE PASS | 14 windows x 15 original time years; SOURCE QCFLAG ONLY")
    print("NO SCIENCE SOURCE APPROVAL, NO DATM, SURFACE, CIME, SLURM OR AD400")
    print("REPORT_DIR",dest)
if __name__=="__main__":main()
