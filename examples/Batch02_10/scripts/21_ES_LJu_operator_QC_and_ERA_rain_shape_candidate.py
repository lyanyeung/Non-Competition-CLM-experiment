#!/usr/bin/env python3
"""ES-LJu Stage21: operator-approved targeted meteorology + same-day ERA5 precipitation shape.
ISOLATED PREVIEW ONLY. Does not alter originals, selected Stage28, active DATM or Slurm.
Timestamp equality means same dataset label; original gauge accumulation day/time is not
independently established. Daily precipitation totals stay the original tower totals.
"""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path("/iridisfs/scratch/ly3n24/CLM_FATES/experiments/NonCompetitionObserved22/Batch02_10")
STAGE16 = ROOT / "stage16_ES_LJu_manual_review_v1_20261025"
PINNED_SELECTED_SHA = "a9c0d441e5e4b02b310158891d040ebe14c7ff50172a64ee250c0b4aaf05df1"

# Exact time windows that the operator has authorized; do not broaden automatically.
PAIRED_ERA_WINDOWS = [
    ("2009-09-27 14:30", "2009-09-27 18:30", "APPROVED_2009_ERA_TA_RH"),
    ("2017-08-08 20:30", "2017-08-08 23:30", "APPROVED_2017_ERA_TA_RH_INCLUDES_QC0_2330"),
    ("2023-10-18 16:00", "2023-10-18 16:30", "APPROVED_2023_ERA_TA_RH"),
]
# Approved previously listed LOW-RH events: paired ERA5 data across full contiguous
# RH<5% episodes, rather than patching just a single half-hour at each row.
LOW_RH_ERA_WINDOWS = [
    ("2005-07-29 17:00", "2005-07-29 19:00"),
    ("2005-08-12 21:00", "2005-08-12 21:30"),
    ("2015-11-10 20:30", "2015-11-11 02:00"),
    ("2015-12-01 00:00", "2015-12-01 01:30"),
    ("2017-08-08 19:00", "2017-08-08 19:00"),
    ("2019-06-30 01:00", "2019-06-30 06:30"),
    ("2023-01-15 01:30", "2023-01-15 07:30"),
]
TA2006_TIMES = [
    "2006-05-31 19:30", "2006-05-31 22:00", "2006-05-31 22:30",
    "2006-05-31 23:00", "2006-05-31 23:30",
]
BIAS2006_ANCHORS = [
    "2006-05-31 18:00", "2006-05-31 18:30", "2006-05-31 19:00",
    "2006-05-31 20:00", "2006-05-31 20:30",
    "2006-05-31 21:00", "2006-05-31 21:30",
]

def fingerprint(p):
    digest=hashlib.sha256()
    with Path(p).open("rb") as f:
        for chunk in iter(lambda:f.read(1024*1024),b""):
            digest.update(chunk)
    return digest.hexdigest()

def require(ok,info):
    if not bool(ok):
        raise RuntimeError(str(info))

def es_hpa(t):
    t=np.asarray(t,dtype=float)
    return 6.112*np.exp(np.clip(17.67*t/(t+243.5),-20,20))

def thermodynamics(ta,vpd,p):
    e=(es_hpa(ta)-vpd)*100
    q=.622*e/(p-.378*e)
    rh=100*e/(100*es_hpa(ta))
    return float(q),float(rh)

def parse_time(s):
    return pd.to_datetime(s.astype(str).str.replace(r"\.0$","",regex=True),
                          format="%Y%m%d%H%M",errors="raise")

def load_hh(p,fields,years=(2004,2024)):
    headers=set(pd.read_csv(p,nrows=0).columns)
    require("TIMESTAMP_START" in headers,f"{p}: no TIMESTAMP_START")
    columns=["TIMESTAMP_START"]+[k for k in fields if k in headers]
    d=pd.read_csv(p,usecols=columns,dtype={"TIMESTAMP_START":"str"},low_memory=False)
    d["time"]=parse_time(d.TIMESTAMP_START)
    d=d.loc[d.time.dt.year.between(*years)].copy()
    d=d.loc[~((d.time.dt.month==2)&(d.time.dt.day==29))]
    require(not d.time.duplicated().any(),f"{p}: duplicated time")
    for k in columns[1:]:
        d[k]=pd.to_numeric(d[k],errors="coerce")
        d.loc[(d[k]<=-9990)|(~np.isfinite(d[k])),k]=np.nan
    return d.set_index("time").sort_index()

def test_math():
    a=np.array([0.,.2,.4,.1])
    daily=21.357
    split=daily*a/a.sum()
    require(abs(float(split.sum())-daily)<1e-10,"precip conservation self test")
    x=np.array([.7,1.,1.4,.8,1.1])
    require(abs(np.median(x)-1.)<1e-12,"robust bias self test")
    q,rh=thermodynamics(21.5765,20.225,100000)
    require(0<q<.05 and 1<rh<100,"thermodynamic consistency self test")
    print("STAGE21 SELF-TEST PASS: ERA fractions, median bias and paired TA/VPD/RH/QBOT")

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--self-test",action="store_true")
    ap.add_argument("--out",type=Path,help="New isolated output directory; never overwrite")
    opt=ap.parse_args()
    test_math()
    if opt.self_test:
        return
    require(opt.out is not None,"--out is required for candidate generation")
    out=opt.out.expanduser().resolve()
    require(not out.exists() and not out.is_symlink(),
            "Output already exists; never overwrite: "+str(out))
    manifest=json.loads((STAGE16/"00_science_lineage_and_review_questions.json").read_text())
    selected_info=manifest["stage28_source"]
    src=Path(selected_info["path"])
    require(src.is_file(),"Pinned Stage28 selected CSV missing")
    require(selected_info["sha256"]==PINNED_SELECTED_SHA,"Stage16 expected Stage28 SHA changed")
    require(fingerprint(src)==PINNED_SELECTED_SHA,"Selected Stage28 forcing SHA mismatch")
    raw=Path(manifest["original_fluxmet_hourly"]["raw_path"])
    require(raw.is_file(),"Original FLUXMET missing")
    require(fingerprint(raw)==manifest["original_fluxmet_hourly"]["sha256"],
            "Original FLUXMET SHA mismatch")
    eras=sorted(raw.parent.glob("*ERA5_HH*.csv"))
    require(len(eras)==1,"One ES-LJu FLUXNET companion ERA5_HH required")
    era_path=eras[0]
    data=pd.read_csv(src,low_memory=False)
    required={"time","TA_USE","VPD_USE","TBOT","QBOT","PSRF","PRECTmms"}
    require(required.issubset(data.columns),"Selected CSV missing: "+str(required-set(data)))
    data["time"]=pd.to_datetime(data.time,errors="raise")
    require(len(data)==21*365*48 and data.time.is_unique,"Stage28 21-year NOLEAP invariant")
    require(data.time.is_monotonic_increasing,"Stage28 time order is not ascending")
    require(not ((data.time.dt.month==2)&(data.time.dt.day==29)).any(),
            "Stage28 unexpectedly has leap day")
    idx=pd.Index(data.time,name="time")
    require(np.isfinite(data[list(required-{"time"})].to_numpy(dtype=float)).all(),
            "Selected variables contain nonfinite values")
    rawdf=load_hh(raw,["TA_F","VPD_F","P_F","P_F_QC","TA_F_QC","VPD_F_QC"])
    eraf=load_hh(era_path,["TA_ERA","VPD_ERA","P_ERA"])
    for k in ["TA_ERA","VPD_ERA","P_ERA"]:
        if k not in eraf.columns and k in load_hh(raw,[k]).columns:
            eraf[k]=load_hh(raw,[k])[k]
    require({"TA_ERA","VPD_ERA","P_ERA"}.issubset(eraf.columns),
            "Companion ERA or embedded FLUXMET missing TA_ERA, VPD_ERA, P_ERA")
    require({"TA_F","VPD_F","TA_F_QC","VPD_F_QC","P_F","P_F_QC"}.issubset(rawdf.columns),
            "Original missing mandatory FLUXMET columns")
    require(rawdf.index.equals(idx) and eraf.index.equals(idx),
            "Source/ERA/selected 21-year timeline labels mismatch; stop rather than shift")
    require(not eraf[["TA_ERA","VPD_ERA"]].isna().any().any(),
            "ERA temperature/VPD gap; cannot generate complete paired repair")
    require(not (eraf.P_ERA.loc[eraf.index.year<=2009]<0).any(),
            "Negative ERA precipitation present")

    # Work only in memory, keyed by exact validated row index.
    lut={t:i for i,t in enumerate(idx)}
    changes=[]
    def where(t):
        ts=pd.Timestamp(t)
        require(ts in lut,f"Half-hour not found: {ts}")
        return lut[ts]
    def patch(t,ta,vpd,kind):
        k=where(t)
        old_t=float(data.at[k,"TA_USE"])
        old_v=float(data.at[k,"VPD_USE"])
        old_q=float(data.at[k,"QBOT"])
        new_q,new_rh=thermodynamics(float(ta),float(vpd),float(data.at[k,"PSRF"]))
        require(np.isfinite(new_q) and np.isfinite(new_rh) and .000001<new_q<.05 and 1<=new_rh<=100,
                f"{t}: bad new QBOT/RH {new_q} {new_rh}")
        data.at[k,"TA_USE"]=float(ta)
        data.at[k,"VPD_USE"]=float(vpd)
        data.at[k,"TBOT"]=float(ta)+273.15
        data.at[k,"QBOT"]=new_q
        changes.append(dict(time=str(pd.Timestamp(t)),method=kind,
               before_TA_C=old_t,after_TA_C=float(ta),
               before_VPD_hPa=old_v,after_VPD_hPa=float(vpd),
               before_QBOT_kgkg=old_q,after_QBOT_kgkg=new_q,
               after_RH_pct=new_rh))
    def use_era(t,kind):
        r=eraf.loc[pd.Timestamp(t)]
        patch(t,float(r["TA_ERA"]),float(r["VPD_ERA"]),kind)
    def patch_era_span(a,b,tag):
        ts=pd.date_range(a,b,freq="30min")
        require(len(ts)>0,"Empty patch span")
        for t in ts: use_era(t,tag)

    # Previously approved decision: 2015-09-16 isolated half-hour interpolation.
    i=where("2015-09-16 15:00")
    require(abs(float(data.at[i,"TA_USE"])-8.960)<.003,"2015 point original anchor drift")
    lo=where("2015-09-16 14:30");hi=where("2015-09-16 15:30")
    patch("2015-09-16 15:00",
          (float(data.at[lo,"TA_USE"])+float(data.at[hi,"TA_USE"]))/2,
          (float(data.at[lo,"VPD_USE"])+float(data.at[hi,"VPD_USE"]))/2,
          "APPROVED_2015_TA_VPD_LINEAR_INTERPOLATION")

    # Previous 2023 decision + boundary (the 15:30 bridge remains explicitly marked).
    patch_era_span("2023-10-18 16:00","2023-10-18 16:30",
                   "APPROVED_2023_16_00_16_30_ERA_PAIR")
    j0=where("2023-10-18 15:00");j1=where("2023-10-18 16:00")
    patch("2023-10-18 15:30",
          (float(data.at[j0,"TA_USE"])+float(data.at[j1,"TA_USE"]))/2,
          (float(data.at[j0,"VPD_USE"])+float(data.at[j1,"VPD_USE"]))/2,
          "PROVISIONAL_2023_15_30_BRIDGE_FOR_CONTINUITY")

    # 2006 explicit TA-only correction:
    # median over seven normal QC1 tower-minus-ERA temperatures; measured
    # VPD_F remains smooth across 19:30 and 22:00, so preserve VPD_USE.
    biases=[]
    for t in BIAS2006_ANCHORS:
        k=where(t)
        require(float(rawdf.iloc[k]["TA_F_QC"])==1,f"2006 anchor must be QC1: {t}")
        biases.append(float(rawdf.iloc[k]["TA_F"])-float(eraf.iloc[k]["TA_ERA"]))
    offset=float(np.median(biases))
    require(abs(offset)<5,"2006 nearby tower-minus-ERA median offset unexpectedly large")
    for t in TA2006_TIMES:
        k=where(t)
        require(float(rawdf.iloc[k]["TA_F_QC"])==0,f"2006 edited TA not original QC0: {t}")
        ta=float(eraf.iloc[k]["TA_ERA"])+offset
        patch(t,ta,float(data.at[k,"VPD_USE"]),
              "APPROVED_2006_ERA_TA_PLUS_QC1_MEDIAN_OFFSET_KEEP_EXISTING_VPD")

    # New operator-approved paired TA and ERA-derived RH (same VPD_ERA pair).
    for a,b,tag in PAIRED_ERA_WINDOWS:
        if tag=="APPROVED_2023_ERA_TA_RH":continue # already handled above
        patch_era_span(a,b,tag)
    for a,b in LOW_RH_ERA_WINDOWS:
        for t in pd.date_range(a,b,freq="30min"):
            if t in [pd.Timestamp("2017-08-08 19:00")]:
                # Already QC2 => ERA5 in original; record as an explicit no-op.
                k=where(t)
                require(abs(float(data.at[k,"TA_USE"])-float(eraf.iloc[k]["TA_ERA"]))<1e-5,
                        "2017 QC2 should already equal ERA, do not rewrite")
                continue
            require(not ((t>=pd.Timestamp("2009-09-27 14:30") and t<=pd.Timestamp("2009-09-27 18:30")) or
                        (t>=pd.Timestamp("2017-08-08 20:30") and t<=pd.Timestamp("2017-08-08 23:30"))),
                    "Unexpected overlapping event scopes")
            use_era(t,"APPROVED_NAMED_LOW_RH_CONTIGUOUS_EPISODE_ERA_PAIR")

    # Daily rain reconstruction, 2005–2008 at one 23:00/23:30 sample, and
    # 2009 only on dates with an isolated 23:00 single wet half-hour.
    rain_changes=[]
    daily_ledger=[]
    rain_holds=[]
    n_eligible=0
    for y in range(2005,2010):
        dates=idx[(idx.year==y)].normalize().unique()
        for day in dates:
            start=lut.get(pd.Timestamp(day))
            require(start is not None,f"Daily date missing: {day}")
            positions=np.arange(start,start+48)
            require(len(positions)==48 and positions[-1]<len(idx) and
                    (idx[positions].normalize()==pd.Timestamp(day)).all(),
                    f"Daily 48HH noleap failure {day}")
            rv=rawdf.iloc[positions]["P_F"].to_numpy(float)
            qcv=rawdf.iloc[positions]["P_F_QC"].to_numpy(float)
            ev=eraf.iloc[positions]["P_ERA"].to_numpy(float)
            original_selected=data.iloc[positions]["PRECTmms"].to_numpy(float)*1800
            # Only reconstruct TRUE single-record wet days. No changes to dry
            # dates nor to 2009 dates that have actual subdaily measurements.
            if not np.isfinite(rv).all():raise RuntimeError(f"{day}: raw P_F has nonfinite HH")
            positive=np.flatnonzero(rv>1e-10)
            if len(positive)==0:continue
            if y<=2008:
                require(len(positive)==1 and
                        idx[positions[int(positive[0])]].strftime("%H:%M")==("23:30" if y==2005 else "23:00"),
                        f"{day}: unexpected 2005–08 rainfall timestamp; stop")
            else:
                if len(positive)!=1 or idx[positions[int(positive[0])]].strftime("%H:%M")!="23:00":
                    continue
            n_eligible+=1
            require(float(qcv[positive[0]])==0,
                    f"{day}: one-time tower rainfall must be QC0")
            require(np.allclose(rv,original_selected,rtol=0,atol=0.0005),
                    f"{day}: source vs selected Stage28 precip differs; stop")
            P=float(rv.sum())
            if not np.isfinite(ev).all() or np.any(ev<0) or ev.sum()<=0:
                rain_holds.append(dict(day=str(day.date()),source_P_mm=P,
                                       reason="ZERO_OR_MISSING_ERA_DAILY_PRECIP_NO_REDISPERSION"))
                continue
            remade=P*(ev/float(ev.sum()))
            # Exact total preserved to rounding precision of double-precision.
            require(abs(float(remade.sum())-P)<=max(1e-8,P*1e-10),
                    f"{day}: rain conservation failed")
            for offsetHH,k in enumerate(positions):
                old=float(data.at[k,"PRECTmms"])*1800
                new=float(remade[offsetHH])
                data.at[k,"PRECTmms"]=new/1800
                if abs(old-new)>1e-10:
                    rain_changes.append(dict(day=str(day.date()),
                           time=str(idx[k]),old_tower_mm=old,
                           new_redistributed_mm=new,ERA_P_ERA_mm=float(ev[offsetHH]),
                           ERA_daily_fraction=float(ev[offsetHH]/ev.sum()),
                           original_daily_tower_total_mm=P))
            after=float(data.iloc[positions]["PRECTmms"].sum()*1800)
            require(abs(after-P)<=1e-7,f"{day}: regenerated forcing mass nonconservation")
            daily_ledger.append(dict(day=str(day.date()),source_total_mm=P,
                  ERA_daily_total_mm=float(ev.sum()),new_total_mm=after,
                  new_wet_halfhours=int((remade>1e-12).sum()),
                  original_wet_halfhours=1,
                  ERA_23h_share_pct=float(ev[46:].sum()/ev.sum()*100)))

    # Audit all modified TA/VPD changes; unchanged inputs remain exact.
    ledger=pd.DataFrame(changes)
    require(not ledger.time.duplicated().any(),"Multiple changes to same half-hour")
    require(len(ledger)==
            1+2+1+len(TA2006_TIMES)+9+7+
            sum(len(pd.date_range(a,b,freq="30min")) for a,b in LOW_RH_ERA_WINDOWS)-1,
            "Unexpected number of meteorological targeted edits")
    T=data.TA_USE.to_numpy(float)
    V=data.VPD_USE.to_numpy(float)
    PS=data.PSRF.to_numpy(float)
    Q=data.QBOT.to_numpy(float)
    tb=data.TBOT.to_numpy(float)
    require(np.allclose(tb,T+273.15,rtol=0,atol=1e-5),"TA/TBOT inconsistency")
    require(np.isfinite(Q).all() and (Q>=0).all() and (Q<0.05).all(),
            "Invalid QBOT in resulting all-year candidate")
    es=es_hpa(T)
    ea=Q*PS/(.622+.378*Q)
    RH=100*ea/(es*100)
    require(np.isfinite(RH).all() and (RH>=1-1e-3).all() and (RH<=100.05).all(),
            "Candidate includes physically invalid RH; abort")
    require(np.all(np.isfinite(data.PRECTmms)) and (data.PRECTmms>=0).all(),
            "Negative or nonfinite precipitation in candidate")
    report=[]
    for i,row in ledger.iterrows():
        pos=where(row.time)
        for j in (pos-1,pos):
            if 0<=j<len(data)-1 and idx[j+1]-idx[j]==pd.Timedelta(minutes=30):
                delta=abs(T[j+1]-T[j])
                if delta>5:
                    report.append(dict(time_left=str(idx[j]),time_right=str(idx[j+1]),
                               delta_T_C=round(float(delta),3),
                               tag=row.method))
    edges=pd.DataFrame(report).drop_duplicates(subset=["time_left","time_right"]) if report else pd.DataFrame(columns=["time_left","time_right","delta_T_C","tag"])
    low_total=int((RH<5).sum())
    print("STAGE21 INPUT LOCK PASS | SHA256 originals, exact 21 years, NOLEAP")
    print("2006 QC1 tower-minus-ERA normal deltas C:",[round(v,3) for v in biases])
    print("2006 robust MEDIAN temperature correction offset C:",round(offset,3))
    print("Approved/bridge met edits:",len(ledger))
    print("Eligible daily single-record rain days:",n_eligible)
    print("Redistributed days:",len(daily_ledger),"HOLD (ERA zero or missing):",len(rain_holds))
    print("Remaining RH<5 in overall 21-year candidate:",low_total)
    print("Adjacent >5C jumps AT edited regions:",len(edges))
    print("\nTEMPERATURE / VPD EDIT LEDGER")
    print(ledger.round(5).to_string(index=False))
    if len(edges):print("\nBOUNDARY WARNINGS\n",edges.to_string(index=False))
    if rain_holds:print("\nRAIN HOLD DAYS\n",pd.DataFrame(rain_holds).to_string(index=False))
    print("\nRAIN CONSERVATION BY YEAR")
    daily_df=pd.DataFrame(daily_ledger)
    if not daily_df.empty:
        daily_df["year"]=pd.to_datetime(daily_df.day).dt.year
        print(daily_df.groupby("year")[["source_total_mm","new_total_mm"]].sum().round(5).to_string())
    require(not out.exists() and not out.is_symlink(),
            "Output unexpectedly appeared while validating; never overwrite")
    out.mkdir(parents=True,exist_ok=False)
    data["time"]=data.time.dt.strftime("%Y-%m-%d %H:%M:%S")
    data.to_csv(out/"ES-LJu_stage21_full21yr_provisional_forcing.csv",index=False)
    ledger.to_csv(out/"01_exact_TA_VPD_RH_QBOT_edit_ledger.csv",index=False)
    daily_df.to_csv(out/"02_daily_precip_mass_conservation.csv",index=False)
    pd.DataFrame(rain_changes).to_csv(out/"03_halfhour_precip_redistribution_ledger.csv",index=False)
    pd.DataFrame(rain_holds,columns=["day","source_P_mm","reason"]).to_csv(
        out/"04_ERA_dry_or_missing_rain_HOLD.csv",index=False)
    edges.to_csv(out/"05_modified_temperature_boundary_warnings.csv",index=False)
    (out/"06_manifest.json").write_text(json.dumps({
       "selected_stage28_original":str(src),"original_sha256":fingerprint(src),
       "tower_raw_source":str(raw),"tower_original_sha256":fingerprint(raw),
       "ERA5_companion":str(era_path),"ERA5_sha256":fingerprint(era_path),
       "2006_QC1_median_T_minus_ERA_C":offset,
       "met_edit_rows":len(ledger),"rain_eligible_days":n_eligible,
       "rain_reconstructed_days":len(daily_ledger),
       "rain_HOLD_days":len(rain_holds),"candidate_remaining_RH_below5":low_total,
       "warnings_GT5C_near_patches":len(edges),
       "scope":"2005-2008 one end-of-day rain record, 2009 single-23h wet days only; same-calendar-date ERA proportions",
       "status":"PROVISIONAL_DO_NOT_USE_FOR_DATM_UNTIL_BOUNDARY_AND_RAIN_HOLDS_APPROVED",
       "active_DATM_changes":0,"SLURM_jobs_submitted":0,
       "warnings":["Tower/ERA timestamp labels are joined, not independently checked for instrument daily accumulation boundaries",
                   "ERA5 site-downscaled values are not independent tower ground truth",
                   "2023 15:30 bridging is an explicitly marked candidate",
                   "All other RH<5 episodes not named by operator remain for science review"]
    },indent=2)+"\n")
    print("\nPROVISIONAL OUTPUT:",out)
    print("NO ACTIVE DATM/CASE/SLURM CHANGES; science boundary/rain HOLD remains.")

if __name__=="__main__":
    main()
