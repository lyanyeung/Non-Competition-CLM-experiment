#!/usr/bin/env python3
"""ICOS Batch04 DE-Gri Stage03Y: verify repaired DATM at two flagged times.

Read only; 12 other Stage28 flagged times are original QC0 precipitation,
not candidates for automatic clipping. No science/model release.
"""
import argparse
import hashlib
import json
import math
from datetime import datetime, timedelta
from pathlib import Path

STAGE = "INPUT_PLAN_ONLY_NOT_MODEL_RELEASE"
EVENTS = {2011: datetime(2011, 6, 13, 7, 0),
          2024: datetime(2024, 7, 4, 7, 30)}
START = {2011: datetime(2011, 6, 13, 7, 0),
         2024: datetime(2024, 7, 4, 5, 0)}
COUNT = {2011: 11, 2024: 23}
TEMP_MIN, TEMP_MAX = -80.0, 65.0

def digest(p):
    h = hashlib.sha256()
    with p.open("rb") as f:
        for part in iter(lambda: f.read(1048576), b""):
            h.update(part)
    return h.hexdigest()

def check(condition, message):
    if not condition:
        raise ValueError(message)

def physical(t, q, pressure):
    check(math.isfinite(t) and TEMP_MIN <= t <= TEMP_MAX, "Nonphysical air temperature")
    check(math.isfinite(q) and 0 <= q < .1, "Nonphysical specific humidity")
    check(math.isfinite(pressure) and 50000 <= pressure <= 115000, "Nonphysical pressure")
    e = (q * pressure / (0.622 + 0.378*q))/100.0
    es = 6.112 * math.exp(17.67*t/(t+243.5))
    vpd = es - e
    rh = e / es * 100.0
    check(-0.05 <= vpd <= es + 0.05 and -0.3 <= rh <= 100.3, "Nonphysical humidity at candidate time")
    return {"T_C":round(t,4), "QBOT_kgkg":round(q,8),
            "VPD_hPa":round(vpd,4), "RH_water_pct":round(rh,4),
            "PSRF_Pa":round(pressure,2)}

def at(ds, stamp):
    from netCDF4 import date2num
    import numpy as np
    coord = ds.variables["time"]
    check(len(coord) == 17520 and getattr(coord, "calendar", None) in ("noleap","365_day"), "Wrong no-leap annual time axis")
    n = float(date2num(stamp, units=coord.units, calendar=coord.calendar))
    hits = np.flatnonzero(np.isclose(np.ma.filled(coord[:], np.nan), n, atol=1e-9, rtol=0))
    check(len(hits) == 1, "Timestamp not unique: "+str(stamp))
    k = int(hits[0])
    t = float(ds.variables["TBOT"][k,0,0])-273.15
    q = float(ds.variables["QBOT"][k,0,0])
    p = float(ds.variables["PSRF"][k,0,0])
    return physical(t,q,p)

def run(v,u,x,w):
    from netCDF4 import Dataset
    check(v.get("site")=="DE-Gri" and v.get("status")==STAGE
          and v.get("source_science_or_soil_release") is False, "Stage03V is not a science HOLD")
    check(u.get("site")=="DE-Gri" and u.get("status")=="DETACHED_SENSITIVITY_NOT_RELEASED", "Stage03U is not detached")
    check(x.get("site")=="DE-Gri" and x.get("science_release") is False
          and x.get("stage28_forcing_sha_verified") is True, "Stage03X not source verified")
    check(w.get("site")=="DE-Gri" and w.get("science_release") is False, "Stage03W not a science HOLD")
    annual = v.get("annual_inputs", [])
    check(len(annual)==22 and {int(t["year"]) for t in annual}==set(range(2004,2026)), "Annual plan incomplete")
    check({int(t["year"]) for t in annual if t["kind"]=="approved_sensitivity"}=={2011,2024}, "Wrong sensitivity years")
    flags=x.get("14_flags",[])
    check(len(flags)==14 and len(w.get("flags_PRIVATE",[]))==14, "Wrong number of historical flags")
    check(sum(a.get("source_T_QC")==0 and a.get("source_VPD_QC")==0 for a in flags)==12, "Not 12 QC0/QC0 baseline flags")
    check({a["time"] for a in flags}=={r["time"] for r in w["flags_PRIVATE"]}, "Flag identity mismatch")
    override={int(z["year"]):z for z in u.get("annual_files",[])}
    check(set(override)=={2011,2024}, "Stage03U missing annual candidates")
    result=[]
    for year in (2011,2024):
        annual_entry=next(z for z in annual if z["year"]==year)
        rec=override[year]
        check(rec["edits"]==COUNT[year] and rec.get("logical_all_variables_verified") is True,
              "Wrong change scope "+str(year))
        path=Path(rec["candidate_path"]); original=Path(rec["baseline_path"])
        check(str(path)==annual_entry["path"] and rec["candidate_sha256"]==annual_entry["sha256"],
              "Stage03U/V candidate mismatch")
        check(path.is_file() and original.is_file(), "Candidate or original missing")
        check(digest(path)==rec["candidate_sha256"] and digest(original)==rec["baseline_sha256"],
              "Changed baseline/candidate SHA "+str(year))
        with Dataset(original,"r") as b, Dataset(path,"r") as c:
            check(set(b.variables)==set(c.variables), "NetCDF variables differ")
            scope=[]
            for i in range(COUNT[year]):
                stamp=START[year]+timedelta(minutes=30*i)
                old=at(b,stamp); new=at(c,stamp)
                if year==2011:check(abs(old["T_C"]-new["T_C"])>.00001 or abs(old["QBOT_kgkg"]-new["QBOT_kgkg"])>1e-8,
                   "2011 intended edit not present "+str(stamp))
                if year==2024:check(abs(old["T_C"]-new["T_C"])<0.0002,
                   "2024 original QC0 air temperature not retained")
                scope.append({"time":str(stamp),"baseline":old,"candidate":new})
            stamp=EVENTS[year]
            t=next(z for z in flags if z["time"]==str(stamp))
            old=at(b,stamp); new=at(c,stamp)
            check(abs(old["T_C"]-float(t["forcing_T_C"]))<0.01, "Baseline T not Stage03X")
            check(abs(old["VPD_hPa"]-float(t["forcing_VPD_hPa"]))<0.05, "Baseline VPD not Stage03X")
            if year==2011:
                check(abs(new["T_C"]-float(t["source_TA_ERA_C"]))<0.01, "2011 candidate not ERA T")
            else:
                check(abs(new["T_C"]-float(t["source_T_C"]))<0.01, "2024 candidate did not retain observed QC0 T")
            check(abs(new["VPD_hPa"]-float(t["source_VPD_ERA_hPa"]))<0.05,
                  str(year)+" candidate does not reflect intended ERA VPD")
            around={}
            for offset in (-1,0,1):
                ss=stamp+timedelta(minutes=30*offset)
                around[str(ss)]={"baseline":at(b,ss),"candidate":at(c,ss)}
            result.append({"year":year,"target_halfhours":COUNT[year],
                           "baseline_sha256":rec["baseline_sha256"],
                           "candidate_sha256":rec["candidate_sha256"],
                           "old_flag_state":old,"new_flag_state":new,
                           "flag_and_neighbors":around,"scope":scope,
                           "candidate_still_humidity_physical":True})
    return {"site":"DE-Gri","stage":"STAGE03Y_DE_GRI_VERIFIED_CANDIDATE_FLAG_PHYSICS",
            "read_only":True,"science_release":False,"AD400_submission_authorized":False,
            "operator_requested_direct_AD400_without_separate_AD5":True,
            "years":result,
            "12_other_source_QC0_precipitation_flags":"PRESERVE; RAIN_ACCUMULATION_CLOCK_UNVERIFIED",
            "49_historical_MDS_blocks":"HOLD; OVERLAP_DOES_NOT_CLEAR_OBSERVATIONAL_QC",
            "remaining_release_gates":["rain accumulation clock and original source science",
              "remaining MDS event science decisions", "soil/PFT science",
              "new case active DATM stream and private surface FATES binding",
              "AD400 controller and restart validation"],
            "source_case_slurm_modified":False}

def selftest():
    assert round(physical(20,.0,100000)["RH_water_pct"],4)==0
    assert round(physical(20,.0147,100000)["RH_water_pct"])>0
    try: physical(12,-.1,100000)
    except ValueError: pass
    else: raise AssertionError("Bad humidity not rejected")
    assert START[2011]+timedelta(minutes=30*10)==datetime(2011,6,13,12)
    assert START[2024]+timedelta(minutes=30*22)==datetime(2024,7,4,16)
    print("STAGE03Y SELF-TEST PASS | original vs corrected physical checks, no writes")

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--self-test",action="store_true")
    for key in ("stage03v","stage03u","stage03x","stage03w"):p.add_argument("--"+key,type=Path)
    p.add_argument("--out",type=Path)
    a=p.parse_args()
    if a.self_test:selftest();return
    paths=[a.stage03v,a.stage03u,a.stage03x,a.stage03w]
    if any(q is None or not q.is_file() for q in paths):p.error("Stage03V/U/X/W inputs required")
    if a.out is None or not a.out.parent.is_dir() or a.out.is_symlink() or a.out.exists():p.error("Output path must be NEW in an existing directory")
    data=[json.loads(q.read_text(encoding="utf-8")) for q in paths]
    result=run(*data)
    with a.out.open("x",encoding="utf-8") as f:json.dump(result,f,indent=2,ensure_ascii=False);f.write("\n")
    print("STAGE03Y | DE-GRI 2011/2024 VERIFIED CANDIDATES; NOT SCIENCE RELEASE")
    for y in result["years"]:
        print("YEAR",y["year"],"HH",y["target_halfhours"],
              "T_C BEFORE/AFTER",y["old_flag_state"]["T_C"],y["new_flag_state"]["T_C"],
              "VPD_hPa BEFORE/AFTER",y["old_flag_state"]["VPD_hPa"],y["new_flag_state"]["VPD_hPa"],
              "RH_pct BEFORE/AFTER",y["old_flag_state"]["RH_water_pct"],y["new_flag_state"]["RH_water_pct"])
    print("12 QC0 precipitation flags PRESERVE | original rain-gauge clock HOLD")
    print("49 legacy MDS episodes STILL HOLD | no blanket ERA replacement")
    print("DIRECT AD400 REQUEST RECORDED | NO AD5 | NO SLURM OR CIME")
    print("PRIVATE_REPORT",a.out)

if __name__=="__main__":main()
