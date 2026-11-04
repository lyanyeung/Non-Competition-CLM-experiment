#!/usr/bin/env python3
"""AU-ASM Stage19: explain EXACT 235 L6 QC0 without L3 measured-QC0.

Read immutable TERN 2026_v3 L3 and original L6, provenance Stage18 receipt.
Enumerate every exception, distinguish L3 source QCFlag, missing numeric values
versus valid-but-flagged values, unchanged versus different numeric contents,
group by year, var, exact QC, and review each +/-2 native half-hour context.
Full source-vs-source QC0 matches are unchanged. This is READ ONLY and does
not assume that the 2026 L3 must be more authoritative than the older L6.
No automatic QC repair, no source/Surface/DATM/CASE/Slurm writes.
"""
from __future__ import annotations
import argparse,csv,datetime as dt,hashlib,json,sys
from collections import Counter
from pathlib import Path
import numpy as np
from netCDF4 import Dataset,date2num
H=Path.home()
L3=H/"ozflux_ASM_TERN_2026v3_L3_source/AliceSpringsMulga_20100903T0000_to_20230308T0900_L3.nc"
L3_SHA="8faa211fe95aa9f0382bf8d3848cb3245d6c8a25bf4ac440e6e92a77c8759076"
L6=Path("/iridisfs/scratch/ly3n24/CLM_FATES/sites/MY_EC_SITE/AU-ASM/forcing/raw/AliceSpringsMulga1_20100903T0000_to_20230308T0900_L6.nc")
L6_SHA="b9381c4ed0744d03ae609cfbf3805e30bbb9223851a05f4e5b63b149dd0b10eb"
S18=H/"ozflux_nc_stage18_20261103T180258Z"/"stage18_AU_ASM_6year_forcing_science_HOLD.json"
MET=("Ta","SH","ps","Fsd","Fld","Ws","Precip")
FIELDS=("variable","native_time","year","L3_original_QCFlag","L3_original_value",
        "L3_numeric_valid","L6_QCFlag","L6_value","L3_L6_same_numeric",
        "absolute_numeric_delta","L6_source_metadata","review_class",
        "operator_decision","independent_source_confirmed")
CONTEXT=("variable","native_time","offset_HH","L3_value","L3_QCFlag",
         "L6_value","L6_QCFlag","L3_numeric_valid","L6_numeric_valid")
def req(ok,msg):
    if not ok:raise ValueError(str(msg))
def sha(p):
    req(p.is_file() and not p.is_symlink(),"Input absent or symlink "+str(p))
    h=hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda:f.read(4<<20),b""):h.update(b)
    return h.hexdigest()
def array(v,start,end):
    x=np.ma.asarray(v[start:end],dtype=np.float64).filled(np.nan).reshape(-1)
    req(len(x)==end-start,"Unexpected array length "+v.name)
    return x
def idx(v,tt,year):
    t=float(date2num(dt.datetime(year,1,1),v.units,calendar=getattr(v,"calendar","standard")))
    i=int(np.searchsorted(tt,t))
    req(i<len(tt) and abs(tt[i]-t)*86400<0.1,"Native source year missing "+str(year))
    return i
def valid(a):
    return np.isfinite(a) & (a>-9990)
def value(a):
    return float(a) if np.isfinite(a) else None
def stamp(x):
    return np.datetime_as_string(x,unit="s").replace("T"," ")
def save(p,keys,r):
    with p.open("x",encoding="utf-8",newline="") as f:
        w=csv.DictWriter(f,fieldnames=keys,delimiter="\t",extrasaction="raise")
        w.writeheader();w.writerows(r)
def classify(l3flag,l3val,l6val):
    if not np.isfinite(l3flag):return "L3_FLAG_MISSING_L6_QC0"
    if not valid(l3val):return "L3_NUMERIC_MISSING_L6_QC0"
    if abs(l3val-l6val)<=1e-5:return "L3_FINITE_NONQC0_REFLAGGED_QC0_IDENTICAL"
    return "L3_FINITE_NONQC0_L6_QC0_DIFFERENT_VALUE"
def selftest():
    req(classify(1,np.nan,4)=="L3_NUMERIC_MISSING_L6_QC0","missing")
    req(classify(10,4,4)=="L3_FINITE_NONQC0_REFLAGGED_QC0_IDENTICAL","reflag")
    req(classify(10,4,5)=="L3_FINITE_NONQC0_L6_QC0_DIFFERENT_VALUE","difference")
    print("OZFLUX STAGE19 SELF-TEST PASS | exact 235 L3→L6 QC0 exceptions, READ ONLY")
def main():
    if sys.argv[1:]==["--self-test"]:return selftest()
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out",type=Path,required=True)
    out=parser.parse_args().out
    req(out.parent.resolve()==H.resolve() and not out.exists() and not out.is_symlink(),
        "Output must be new immediate HOME child")
    req(sha(L3)==L3_SHA and sha(L6)==L6_SHA,"Immutable two-source SHA drift")
    receipt=json.loads(S18.read_text(encoding="utf-8"))
    req(receipt.get("source_QC0_pairwise_numeric_mismatches")==0
        and receipt.get("L6_QC0_not_supported_by_L3_QC0")==235
        and receipt.get("year_variable_groups")==42
        and receipt.get("all_contiguous_alt_source_spells")==935
        and receipt.get("science_release") is False
        and receipt.get("AD400_authorised") is False,
        "Stage18 operator QC count/science receipt mismatch")
    exceptions=[];contexts=[];tally=Counter();review=Counter()
    with Dataset(str(L3),"r") as ds3,Dataset(str(L6),"r") as ds6:
        t3=ds3.variables["time"];t6=ds6.variables["time"]
        req(t3.units==t6.units and "days since 1800-01-01" in t3.units,
            "Source time units mismatch")
        all3=np.ma.asarray(t3[:],dtype=float).filled(np.nan)
        all6=np.ma.asarray(t6[:],dtype=float).filled(np.nan)
        a,b=idx(t3,all3,2013),idx(t3,all3,2019)
        c,d=idx(t6,all6,2013),idx(t6,all6,2019)
        req(b-a==d-c==105168 and
            np.max(np.abs(all3[a:b]-all6[c:d]))*86400<.1,
            "Six years not matching exact native source time")
        times=(np.datetime64("1800-01-01T00:00:00","s")
               +np.rint(all3[a:b]*86400).astype("timedelta64[s]"))
        year=times.astype("datetime64[Y]").astype(int)+1970
        for var in MET:
            v3=array(ds3.variables[var],a,b);q3=array(ds3.variables[var+"_QCFlag"],a,b)
            v6=array(ds6.variables[var],c,d);q6=array(ds6.variables[var+"_QCFlag"],c,d)
            original=(q3==0)&valid(v3)
            current=(q6==0)&valid(v6)
            hit=np.flatnonzero(current&~original)
            metadata={name:str(ds6.variables[var].getncattr(name))[:140]
                 for name in ("source","description_L3","description_L4",
                              "description_L5","description_L6","units","statistic_type")
                 if name in ds6.variables[var].ncattrs()}
            for i in hit:
                k=classify(q3[i],v3[i],v6[i])
                matched=valid(v3[i]) and abs(v3[i]-v6[i])<=1e-5
                e={"variable":var,"native_time":stamp(times[i]),
                   "year":int(year[i]),
                   "L3_original_QCFlag":value(q3[i]),
                   "L3_original_value":value(v3[i]),
                   "L3_numeric_valid":bool(valid(v3[i])),
                   "L6_QCFlag":value(q6[i]),
                   "L6_value":value(v6[i]),
                   "L3_L6_same_numeric":bool(matched),
                   "absolute_numeric_delta":float(abs(v3[i]-v6[i]))
                           if valid(v3[i]) else None,
                   "L6_source_metadata":json.dumps(metadata,sort_keys=True),
                   "review_class":k,"operator_decision":"SCIENCE_HOLD_NOT_AN_AUTOMATIC_REPAIR",
                   "independent_source_confirmed":False}
                exceptions.append(e)
                key=(int(year[i]),var,str(value(q3[i])),k)
                tally[key]+=1;review[k]+=1
                for j in range(max(0,i-2),min(len(times),i+3)):
                    contexts.append({"variable":var,"native_time":stamp(times[j]),
                      "offset_HH":j-i,"L3_value":value(v3[j]),
                      "L3_QCFlag":value(q3[j]),"L6_value":value(v6[j]),
                      "L6_QCFlag":value(q6[j]),
                      "L3_numeric_valid":bool(valid(v3[j])),
                      "L6_numeric_valid":bool(valid(v6[j]))})
    req(len(exceptions)==235,"Expected 235 exact L3-L6 source exceptions")
    summaries=[{"year":y,"variable":v,"L3_QCFlag":flag,"class":kind,"n":n}
               for (y,v,flag,kind),n in sorted(tally.items())]
    out.mkdir(mode=0o700,parents=False)
    save(out/"stage19_exact_235_L6_QC0_L3_nonQC0_records.tsv",FIELDS,exceptions)
    save(out/"stage19_exact_235_before_after_2HH.tsv",CONTEXT,contexts)
    save(out/"stage19_by_year_variable_original_QC_class.tsv",
         ("year","variable","L3_QCFlag","class","n"),summaries)
    report={"site":"AU-ASM","original_L3_SHA256":L3_SHA,"original_L6_SHA256":L6_SHA,
       "stage18_parent":str(S18),"n_original_QC0_mismatches":235,
       "six_year_all_other_joint_QC0_numeric_differences":0,
       "classification_counts":dict(review),"full_235_records":str(out/"stage19_exact_235_L6_QC0_L3_nonQC0_records.tsv"),
       "exact_before_after_2HH_rows":len(contexts),
       "scientifically_validated_numeric_repairs":0,
       "instrument_source_independently_verified":False,
       "existing_2018_QC0_wind_spike_still_unresolved":True,
       "source_clock_interval_END_vs_CENTER_unresolved":True,
       "science_release":False,"AD400_authorised":False,
       "no_forcing_surface_CIME_or_Slurm_writes":True}
    (out/"stage19_235_L3_L6_QC0_provenance_SCIENCE_HOLD.json").write_text(
       json.dumps(report,indent=2,ensure_ascii=False),encoding="utf-8")
    print("STAGE19 235 SOURCE QC0 EXCEPTIONS EXACTLY REPRODUCED")
    print("QC CLASS COUNTS",json.dumps(dict(review),sort_keys=True))
    print("ANNUAL/SOURCE FLAG GROUPS",len(summaries))
    for x in sorted(summaries,key=lambda x:-x["n"])[:35]:
        print("SOURCE_CLASS",x["year"],x["variable"],
              "L3FLAG",x["L3_QCFlag"],"CLASS",x["class"],"N",x["n"])
    for x in exceptions[:18]:
        print("EXAMPLE",x["variable"],x["native_time"],
              "L3_FLAG",x["L3_original_QCFlag"],"L3_VALUE",x["L3_original_value"],
              "L6",x["L6_value"],x["review_class"])
    print("STAGE19 READONLY SCIENCE HOLD; NO FORCING/SURFACE/CIME/SLURM WRITES")
    print("REPORT_DIR",out)
if __name__=="__main__":main()
