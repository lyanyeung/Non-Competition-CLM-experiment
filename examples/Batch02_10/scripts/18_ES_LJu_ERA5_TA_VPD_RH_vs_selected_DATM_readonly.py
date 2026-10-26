#!/usr/bin/env python3
"""ES-LJu Stage18: source-vs-companion-ERA5-vs-selected-DATM TA/VPD/RH audit.
READ ONLY: never edits original forcing, Stage28, CIME case, or Slurm.
Comparisons use identical timestamp *labels* only; original/source vs model
clock offset/timezone is not independently established. No auto approvals.
"""
from pathlib import Path
import argparse
import json
import numpy as np
import pandas as pd

R = Path("/iridisfs/scratch/ly3n24/CLM_FATES/experiments/NonCompetitionObserved22/Batch02_10/stage16_ES_LJu_manual_review_v1_20261025")
EVENTS = [
    ("2006_QC0_QC1_boundary", "2006-05-31 18:00", "2006-05-31 23:30"),
    ("2009_large_T_RH_jump", "2009-09-27 13:30", "2009-09-27 18:30"),
    ("2015_single_T_spike", "2015-09-16 13:30", "2015-09-16 16:30"),
    ("2017_QC2_QC1_boundary", "2017-08-08 18:00", "2017-08-08 23:30"),
    ("2023_T_patch_boundary", "2023-10-18 14:30", "2023-10-18 20:30"),
    ("2023_minus40_block", "2023-10-19 18:30", "2023-10-20 11:30"),
    ("2005_RH_abrupt", "2005-07-29 15:30", "2005-07-29 21:30"),
    ("2005_RH_1pct", "2005-08-12 19:00", "2005-08-12 23:30"),
    ("2015_RH_nov", "2015-11-10 19:00", "2015-11-11 04:00"),
    ("2015_RH_dec", "2015-11-30 21:00", "2015-12-01 04:00"),
    ("2019_RH_long", "2019-06-29 23:00", "2019-06-30 08:00"),
    ("2023_RH_long", "2023-01-15 00:00", "2023-01-15 09:00"),
]
def stop(s):
    raise RuntimeError(str(s))
def header_cols(p):
    return list(pd.read_csv(p, nrows=0).columns)
def stamp(col):
    return pd.to_datetime(col.astype(str).str.replace(r"\.0$", "", regex=True).str.strip(),
                          format="%Y%m%d%H%M", errors="raise")
def cleanup(df, source_timestamp=True):
    df = df.copy()
    df["time"] = stamp(df["TIMESTAMP_START"]) if source_timestamp else pd.to_datetime(df["time"], errors="raise")
    df = df[df.time.dt.year.between(2004, 2024)].copy()
    df = df[~((df.time.dt.month == 2) & (df.time.dt.day == 29))]
    if df["time"].duplicated().any():
        stop("Duplicate half-hour time labels in input")
    df = df.sort_values("time").reset_index(drop=True)
    for k in df.columns:
        if k in ("time", "TIMESTAMP_START"):
            continue
        df[k] = pd.to_numeric(df[k], errors="coerce")
        if k not in ("TA_F_QC", "VPD_F_QC"):
            df.loc[df[k] <= -9990, k] = np.nan
    return df
def saturation_hpa(T):
    return 6.112 * np.exp(np.clip(17.67 * T / (T + 243.5), -20, 20))
def rh_vpd(T, V):
    es = saturation_hpa(T)
    return 100 * (es - V) / es
def rh_qbot(T, q, p):
    e = q * p / (0.622 + 0.378 * q)
    return 100 * e / (100 * saturation_hpa(T))
def q_from_vpd(T, V, p):
    ea = 100 * (saturation_hpa(T) - V)
    return 0.622 * ea / (p - 0.378 * ea)
def fmt(df, cols, label):
    print("\n" + "=" * 100 + "\n" + label)
    print(df[cols].round(3).to_string(index=False, na_rep="NA"))
def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, help="OPTIONAL NEW output directory for review CSVs; never overwrite")
    a = ap.parse_args()
    receipt = json.loads((R / "00_science_lineage_and_review_questions.json").read_text())
    path_raw = Path(receipt["original_fluxmet_hourly"]["raw_path"])
    path_sel = Path(receipt["stage28_source"]["path"])
    companions = sorted(path_raw.parent.glob("*ERA5_HH*.csv"))
    if not path_raw.is_file() or not path_sel.is_file():
        stop("Pinned Stage16 source or selected Stage28 CSV missing; no fallback")
    if len(companions) != 1:
        stop("Expected exactly ONE local ES-LJu ERA5_HH companion: " + str(companions))
    path_era = companions[0]
    print("STAGE18 READ ONLY | NO CASE, FORCING, OR SLURM MODIFICATION")
    print("RAW:", path_raw)
    print("ERA companion:", path_era)
    print("STAGE28 selected:", path_sel)
    print("CAUTION: label matching is not independent timezone/interval verification")
    cols = header_cols(path_raw)
    required = {"TIMESTAMP_START", "TA_F", "VPD_F", "TA_F_QC", "VPD_F_QC", "PA_F"}
    if not required.issubset(cols):
        stop("Missing FLUXMET source columns " + str(required-set(cols)))
    src = cleanup(pd.read_csv(path_raw, usecols=list(required | ({"TA_ERA", "VPD_ERA"} & set(cols))), dtype={"TIMESTAMP_START":str}, low_memory=False))
    ecols = header_cols(path_era)
    fromcomp = {"TA_ERA", "VPD_ERA"} & set(ecols)
    if not {"TA_ERA", "VPD_ERA"}.issubset(fromcomp | set(src.columns)):
        stop("TA_ERA/VPD_ERA missing from both sources")
    era = cleanup(pd.read_csv(path_era, usecols=["TIMESTAMP_START", *sorted(fromcomp)],
                              dtype={"TIMESTAMP_START":str}, low_memory=False))
    src = src.rename(columns={k:k+"_IN_FLUXMET" for k in fromcomp if k in src.columns})
    s = src.merge(era[["time", *fromcomp]], on="time", how="left", validate="one_to_one")
    for col in ("TA_ERA", "VPD_ERA"):
        if col not in s:
            s[col] = s[col+"_IN_FLUXMET"]
            print(col+": companion column absent; using FLUXMET embedded column")
        elif col+"_IN_FLUXMET" in s:
            x = s[col].to_numpy(dtype=float)
            y = s[col+"_IN_FLUXMET"].to_numpy(dtype=float)
            both = np.isfinite(x) & np.isfinite(y)
            print(col+" companion-vs-embedded max absolute diff:",
                  float(np.max(np.abs(x[both]-y[both]))) if both.any() else "NO_OVERLAP")
    scols = header_cols(path_sel)
    needed = {"time", "TBOT", "QBOT", "PSRF"}
    if not needed.issubset(scols):
        stop("Missing Stage28 selected columns " + str(needed-set(scols)))
    extras = {"TA_USE", "VPD_USE"} & set(scols)
    sel = cleanup(pd.read_csv(path_sel, usecols=list(needed | extras), low_memory=False),
                  source_timestamp=False)
    sel = sel.rename(columns={"TBOT":"selected_TBOT_K", "QBOT":"selected_QBOT",
                              "PSRF":"selected_PSRF_Pa", "TA_USE":"selected_TA_USE_C",
                              "VPD_USE":"selected_VPD_USE_hPa"})
    assert sel.time.is_unique and s.time.is_unique
    if len(sel)!=len(s) or not np.array_equal(sel.time.values, s.time.values):
        stop("Stage28 vs FLUXMET timestamp label sequences differ; abort matching, do NOT time-shift")
    z = s.merge(sel,on="time",how="inner",validate="one_to_one")
    z["original_RH_pct"] = rh_vpd(z.TA_F, z.VPD_F)
    z["ERA_RH_pct"] = rh_vpd(z.TA_ERA, z.VPD_ERA)
    z["selected_T_C"] = z.selected_TBOT_K - 273.15
    z["selected_RH_pct"] = rh_qbot(z.selected_T_C,z.selected_QBOT,z.selected_PSRF_Pa)
    z["delta_selected_minus_ERA_T_C"] = z.selected_T_C - z.TA_ERA
    z["delta_original_minus_ERA_T_C"] = z.TA_F - z.TA_ERA
    z["ERA_QBOT_at_selected_Pa"] = q_from_vpd(z.TA_ERA,z.VPD_ERA,z.selected_PSRF_Pa)
    z["raw_RH_physically_invalid"] = (~np.isfinite(z.original_RH_pct)) | (z.original_RH_pct<0) | (z.original_RH_pct>100)
    z["ERA_RH_physically_invalid"] = (~np.isfinite(z.ERA_RH_pct)) | (z.ERA_RH_pct<0) | (z.ERA_RH_pct>100)
    z["2023_T_discrepancy_ge15"] = (z.time.dt.year==2023) & (z.delta_original_minus_ERA_T_C.abs()>=15)
    z["raw_T_below_minus20"] = z.TA_F < -20
    z["raw_T_above40"] = z.TA_F > 40
    z["ERA_pair_sanity"] = z.TA_ERA.between(-20,45) & z.VPD_ERA.ge(0) & z.ERA_RH_pct.between(1,100)
    print("\nFULL 2004-2024 (no leap) comparison:",len(z),"half-hours")
    print("2023 original TA_F min:",z.loc[z.time.dt.year==2023,"TA_F"].min())
    print("2023 source ERA TA_ERA min:",z.loc[z.time.dt.year==2023,"TA_ERA"].min())
    for col in ["raw_T_below_minus20","raw_T_above40","2023_T_discrepancy_ge15","raw_RH_physically_invalid","ERA_RH_physically_invalid"]:
        print(col,int(z[col].sum()))
    display = ["time","TA_F","TA_F_QC","VPD_F","VPD_F_QC",
               "TA_ERA","VPD_ERA","ERA_RH_pct","original_RH_pct",
               "selected_T_C","selected_RH_pct","selected_QBOT",
               "delta_selected_minus_ERA_T_C"]
    union = []
    for label,start,end in EVENTS:
        part = z[z.time.between(start,end)].copy()
        if part.empty:
            stop("Missing event window "+label)
        fmt(part,display,label+" | SAME-LABEL PROVISIONAL source/ERA/Stage28 comparison")
        union.append(part.assign(event=label))
    selected = pd.concat(union,ignore_index=True)
    low = pd.read_csv(R/"06_all_approx_RH_below5_halfhours.csv",usecols=["year","model_time"])
    low["time"] = pd.to_datetime(low["model_time"])
    low = low.merge(z[["time","TA_F","VPD_F","TA_ERA","VPD_ERA",
                       "ERA_RH_pct","selected_RH_pct","delta_selected_minus_ERA_T_C",
                       "ERA_pair_sanity"]],on="time",how="left",validate="one_to_one")
    if low.ERA_RH_pct.isna().all():
        stop("No model low-RH entries matched ERA companion! Check timestamps")
    print("\n" + "="*100 + "\nALL Stage16 460 model RH<5% records: source ERA RH comparison")
    summary = low.groupby("year").agg(
        flagged_HH=("time","size"),ERA_RH_min_pct=("ERA_RH_pct","min"),
        ERA_RH_median_pct=("ERA_RH_pct","median"),
        ERA_RH_ge10_HH=("ERA_RH_pct",lambda s:int((s>=10).sum())),
        ERA_RH_invalid_HH=("ERA_pair_sanity",lambda s:int((~s.fillna(False)).sum()))
    ).reset_index()
    print(summary.round(3).to_string(index=False))
    top = low.nsmallest(25,"selected_RH_pct")
    fmt(top,["time","selected_RH_pct","ERA_RH_pct","TA_ERA","VPD_ERA",
             "delta_selected_minus_ERA_T_C"],"25 LOWEST MODEL RH RECORDS VS COMPANION ERA5")
    if a.out:
        dest = a.out.expanduser().resolve()
        if dest.exists() or dest.is_symlink():
            stop("Output exists, never overwrite: "+str(dest))
        dest.mkdir(parents=True,exist_ok=False)
        selected.to_csv(dest/"01_event_windows_raw_ERA_stage28_T_RH.csv",index=False)
        low.to_csv(dest/"02_all460_RHlt5_raw_ERA_comparison.csv",index=False)
        summary.to_csv(dest/"03_RHlt5_annual_ERA_summary.csv",index=False)
        (dest/"README.txt").write_text(
            "READ-ONLY Stage18 scientific review; original/source and DATM timestamp labels matched without independently confirmed timezone. "
            "ERA5 is downscaled reanalysis, not truth. No scientific repair approval.\n"
        )
        print("\nREPORTS:",dest)
    print("\nSTAGE18 COMPLETE — no forcing, cases or Slurm modified; no replacement approved")
if __name__ == "__main__":
    main()
