#!/usr/bin/env python3
"""AU-ASM Stage15 source-L6 -> immutable provisional DATM wind crosswalk.

Only three exactly operator-observed original PyFluxPro QC0 candidates.
Reads immutable original L6, Stage14 wind evidence, Stage13 soil-v2 receipt,
and six source-SHA-pinned Stage14 DATM files. Proves native END->UTC CENTER
wind data mapping at those 3 native labels, while keeping clock science
interpretation PROVISIONAL. Computes hypothetical *not applied* one-sample
linear replacement at the 2018 peak for comparison only. No writes to any
NetCDF, old/new Surface, model case, DATM stream, Slurm, or approval state.
"""
from __future__ import annotations
import argparse,datetime as dt,hashlib,json,sys
from pathlib import Path
import numpy as np
from netCDF4 import Dataset,date2num

HOME=Path.home()
L6=Path("/iridisfs/scratch/ly3n24/CLM_FATES/sites/MY_EC_SITE/AU-ASM/forcing/raw/AliceSpringsMulga1_20100903T0000_to_20230308T0900_L6.nc")
L6_SHA="b9381c4ed0744d03ae609cfbf3805e30bbb9223851a05f4e5b63b149dd0b10eb"
DATM=HOME/"ozflux_stage14_FSDS0_20261102T012038Z"
SHA14={
2013:"0e722aec1d73d35ff4671ccd1c72fbf02c7e3af8f9fdd6cae291834741b2bffe",
2014:"54345a6ae15ba8091b118dc62c891cff1fb851eda895178a47c8d3a23143871b",
2015:"6d7b9cc4f0e24d6395f1f6d1ae3217f9fd70a67d93f41969eb6cdafe283447bf",
2016:"8b5576e424625a0bf62f0fb0fa552230ff7c01e26e440a565242e169fe455c7f",
2017:"634d8d395e95331cf9f13dcbf5d48edbc2e881af4ca913acb75abe1333032951",
2018:"8ce901670486469358525c95f6a78db82698a5712312c4b1bf610aff744be55d"}
S14=HOME/"ozflux_nc_stage14_wind_20261103T130621Z"/"stage14_source_wind_science_HOLD.json"
S13=HOME/"ozflux_nc_stage13_soil_20261103T130125Z"/"stage13_AU_ASM_v2_SITE_SOIL_candidate_NOT_MODEL_APPROVED.json"
SURF_SHA="2c3de9a54b11189ab4d6413eb29fe91fe36b6ec0f87b9a3ae999d6a7a3a7e8a1"
SHIFT=dt.timedelta(minutes=585)
NATIVE_TIMES=("2018-03-10 20:30:00","2013-01-05 18:00:00","2014-11-23 01:00:00")
WIND=(16.29613,9.747453,7.483473)

def need(c,why):
    if not c:raise ValueError(str(why))

def sha(p):
    p=Path(p)
    need(p.is_file() and not p.is_symlink(),"Input missing/symlink "+str(p))
    h=hashlib.sha256()
    with p.open("rb") as f:
        for a in iter(lambda:f.read(4<<20),b""):h.update(a)
    return h.hexdigest()

def raw(v):
    return np.ma.asarray(v[:],dtype=float).filled(np.nan).reshape(-1)

def one_index(t,arr,when,label):
    n=date2num(when,t.units,calendar=getattr(t,"calendar","standard"))
    i=int(np.searchsorted(arr,n))
    need(0<=i<len(arr) and abs(arr[i]-n)<1e-8,"Target "+label+" not in stream")
    return i

def source_evidence():
    need(sha(L6)==L6_SHA,"Original L6 changed")
    prior=json.loads(S14.read_text(encoding="utf-8"))
    soil=json.loads(S13.read_text(encoding="utf-8"))
    need(prior.get("science_release") is False
         and prior.get("AD400_authorised") is False
         and len(prior.get("events",[]))==3,
         "Stage14 actual three wind science evidence changed")
    need(soil.get("candidate_sha256")==SURF_SHA
         and soil.get("science_approved") is False
         and soil.get("AD400_authorised") is False
         and sha(Path(soil["candidate_path"]))==SURF_SHA,
         "Stage13 site-soil v2 actual SOURCE SHA changed")
    return prior

def check_model(year):
    p=DATM/f"AU-ASM_FSDS0_PROVISIONAL_DATM_{year}.nc"
    need(sha(p)==SHA14[year],"Immutable DATM source SHA changed "+str(year))
    return p

def selftest():
    need(dt.datetime(2018,3,10,20,30)-SHIFT == dt.datetime(2018,3,10,10,45),"UTC midpoint hypothesis")
    need(dt.datetime(2014,11,23,1,0)-SHIFT == dt.datetime(2014,11,22,15,15),"day boundary shift")
    need(0.5*(3.671959+3.970067)==3.8210130000000002,"Hypothetical interpolation")
    need(len(SHA14)==6 and 80*5==400,"Direct400 protocol")
    print("OZFLUX STAGE15 SELF-TEST PASS | source→DATM 3-event crosswalk, no edits or AD400 release")

def main():
    if sys.argv[1:]==["--self-test"]:return selftest()
    a=argparse.ArgumentParser(description=__doc__)
    a.add_argument("--out",type=Path,required=True)
    out=a.parse_args().out
    need(out.parent.resolve()==HOME.resolve() and not out.exists() and not out.is_symlink(),
         "Output requires new immediate HOME child")
    evidence=source_evidence()
    model_files={year:check_model(year) for year in (2013,2014,2018)}
    # Three selected annual files suffice to prove three source events;
    # the remaining three are SHA-guarded too before any report.
    for year in (2015,2016,2017):check_model(year)
    results=[]
    with Dataset(str(L6),"r") as ds:
        time=ds.variables["time"]
        t=raw(time)
        ws=raw(ds.variables["Ws"])
        qc=raw(ds.variables["Ws_QCFlag"])
        need(len(t)==len(ws)==len(qc),"Source time/WS/QC mismatch")
        for label,expected in zip(NATIVE_TIMES,WIND):
            native=dt.datetime.fromisoformat(label)
            i=one_index(time,t,native,"native "+label)
            need(abs(ws[i]-expected)<1e-5 and qc[i]==0.,
                 "Actual original QC0 wind no longer matches "+label)
            hypothesis_utc=native-SHIFT
            year=hypothesis_utc.year
            with Dataset(str(model_files[year]),"r") as model:
                mt=model.variables["time"]
                v=raw(mt)
                j=one_index(mt,v,hypothesis_utc,"model "+label)
                wind=raw(model.variables["WIND"])
                need(len(wind)==len(v),"WIND size != time")
                within=float(wind[j])
                need(abs(within-ws[i])<1e-4,
                     "Source-to-DATM wind NOT identical at "+label)
                left=float(wind[j-1]) if j>0 else None
                right=float(wind[j+1]) if j+1<len(v) else None
                if left is not None and right is not None:
                    need(abs(left-ws[i-1])<1e-4 and abs(right-ws[i+1])<1e-4,
                         "Adjacent source→DATM wind mapping mismatch at "+label)
                is_spike=(label==NATIVE_TIMES[0])
                proposal=0.5*(left+right) if is_spike else None
                results.append({"native_source_label":label,"provisional_model_UTC_midpoint":hypothesis_utc.isoformat(sep=" "),
                   "original_source_wind_ms":float(ws[i]),"original_source_QCFlag":float(qc[i]),
                   "current_DATM_wind_ms":within,"model_year":year,"model_record_0_based":j,
                   "source_to_DATM_exact_wind_value":True,
                   "source_to_DATM_exact_adjacent_wind_values":True,
                   "neighbor_before_ms":left,"neighbor_after_ms":right,
                   "review_class":next((x["classification"] for x in evidence["events"]
                                       if x["native_time"]==label),"UNSPECIFIED"),
                   "hypothetical_2018_single_HH_linear_ms_NOT_APPLIED":proposal,
                   "hypothetical_change_ms_NOT_APPLIED":proposal-within if is_spike else None})
    out.mkdir(mode=0o700,parents=False,exist_ok=False)
    report={"site":"AU-ASM","stage":"Stage15 source→DATM exact native wind event audit",
       "source_L6_SHA256":L6_SHA,"stage14_source":str(S14),
       "soil_v2_SHA256":SURF_SHA,"model_input_stage14_wind_matches_source":True,
       "native_END_minus_585min_to_UTC_midpoint_IS_HYPOTHESIS":True,
       "clock_science_approved":False,
       "hypothetical_one_HH_interp_is_NOT_SCIENTIFICALLY_APPROVED":True,
       "FLDS_ACCESS_AWS_forcing_QC_approved":False,
       "science_release":False,"AD400_authorised":False,
       "no_original_or_candidate_NC_writes":True,
       "no_CIME_or_Slurm_jobs":True,"events":results}
    (out/"stage15_AU_ASM_3wind_DATM_crosswalk_science_HOLD.json").write_text(
       json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    for x in results:
        print("EVENT",x["native_source_label"],
              "UTC_CENTER_HYPOTHESIS",x["provisional_model_UTC_midpoint"],
              "SRC_WIND",x["original_source_wind_ms"],
              "DATM_WIND",x["current_DATM_wind_ms"],
              "PREV",x["neighbor_before_ms"],"NEXT",x["neighbor_after_ms"])
        if x["hypothetical_2018_single_HH_linear_ms_NOT_APPLIED"] is not None:
            print("2018 SENSITIVITY ONLY INTERPOLATION",
                  x["hypothetical_2018_single_HH_linear_ms_NOT_APPLIED"],
                  "NOT APPLIED, NO APPROVAL")
    print("STAGE15 EXACT WIND CROSSWALK PASS; SCIENCE HOLD; NO MODEL SUBMISSION")
    print("REPORT_DIR",out)
if __name__=="__main__":main()
