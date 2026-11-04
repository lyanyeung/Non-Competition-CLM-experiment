#!/usr/bin/env python3
"""AU-ASM Stage20: 235 original-L3 SH gaps incorrectly or implicitly marked L6 QC0?

READ ONLY, exact L3/L6 SHA+Stage19 evidence:
- 235 2014 SH source records; spells and QC changes, L3 and L6
  ancillary humidity (AH/RH/VPD), Ta, ps, rainfall and wind.
- overlapping 2014 ps AWS QC410; no assumption of donor independence.
- recompute humidity from RH or AH only where their units are explicit
  and data are present. A match proves mathematical compatibility,
  not original independent sensor provenance or valid quality flag.
- +/-4 original halfhours around each 235 record episode boundary.
NEVER silently relabel QC0, change humidity, forcing, surface, CIME
or Slurm; science gate remains HOLD.
"""
from __future__ import annotations
import argparse,csv,datetime as dt,hashlib,json,math,sys
from collections import Counter
from pathlib import Path
import numpy as np
from netCDF4 import Dataset,date2num

HOME=Path.home()
L3=HOME/"ozflux_ASM_TERN_2026v3_L3_source/AliceSpringsMulga_20100903T0000_to_20230308T0900_L3.nc"
L3_SHA="8faa211fe95aa9f0382bf8d3848cb3245d6c8a25bf4ac440e6e92a77c8759076"
L6=Path("/iridisfs/scratch/ly3n24/CLM_FATES/sites/MY_EC_SITE/AU-ASM/forcing/raw/AliceSpringsMulga1_20100903T0000_to_20230308T0900_L6.nc")
L6_SHA="b9381c4ed0744d03ae609cfbf3805e30bbb9223851a05f4e5b63b149dd0b10eb"
S19=HOME/"ozflux_nc_stage19_20261103T181825Z/stage19_235_L3_L6_QC0_provenance_SCIENCE_HOLD.json"
MET=("SH","AH","RH","VPD","Ta","ps","Fsd","Fld","Precip","Ws")
EVENT_COLS=("native_time","offset_from_event_start_HH","L3_SH","L3_SH_QC",
 "L6_SH","L6_SH_QC","L3_AH","L3_AH_QC","L6_AH","L6_AH_QC",
 "L3_RH","L3_RH_QC","L6_RH","L6_RH_QC",
 "L3_VPD","L3_VPD_QC","L6_VPD","L6_VPD_QC",
 "L3_Ta","L3_Ta_QC","L6_Ta","L6_Ta_QC",
 "L3_ps","L3_ps_QC","L6_ps","L6_ps_QC",
 "L3_Precip","L3_Precip_QC","L6_Precip","L6_Precip_QC",
 "L6_Ws","L6_Ws_QC",
 "SH_from_L3_RH_Ta_ps","SH_from_L6_RH_Ta_ps",
 "SH_from_L3_AH_Ta_ps","SH_from_L6_AH_Ta_ps",
 "L6_SH_minus_RH_estimate","L6_SH_minus_AH_estimate")
SPELL_COLS=("start_native","end_native","n_HH","hours","L3_SH_all_missing_QC1",
 "L6_SH_all_numeric_QC0","2014_ps_AWS410_overlap_HH",
 "2014_Ta_AWS410_overlap_HH","L6_SH_min","L6_SH_max",
 "L6_SH_mean","SH_jump_in","SH_jump_out",
 "L3_AH_QC0_HH","L3_RH_QC0_HH","L6_AH_QC0_HH","L6_RH_QC0_HH",
 "SH_from_L6_RH_matches_within_1e_5_HH",
 "SH_from_L6_AH_matches_within_1e_5_HH",
 "review_decision")
def require(x,msg):
    if not x:raise ValueError(str(msg))
def sha256(path):
    p=Path(path)
    require(p.is_file() and not p.is_symlink(),"Immutable file missing or link: "+str(p))
    h=hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda:f.read(4<<20),b""):h.update(b)
    return h.hexdigest()
def valid(x):return np.isfinite(x)&(x>-9990)
def one(x):
    return float(x) if np.isfinite(x) and x>-9990 else None
def time_index(t,series,date):
    v=date2num(dt.datetime.fromisoformat(date),t.units,
              calendar=getattr(t,"calendar","standard"))
    k=int(np.searchsorted(series,v))
    require(k<len(series) and abs(series[k]-v)*86400<.1,"Source time not found "+date)
    return k
def read(ds,variable,start,stop):
    if variable not in ds.variables:return None,None
    v=ds.variables[variable]
    tdim=ds.variables["time"].dimensions[0]
    if v.dimensions.count(tdim)!=1:return None,None
    axis=v.dimensions.index(tdim)
    if any(j!=axis and v.shape[j]!=1 for j in range(v.ndim)):return None,None
    selection=tuple(slice(start,stop) if j==axis else 0 for j in range(v.ndim))
    arr=np.ma.asarray(v[selection],dtype=float).filled(np.nan).reshape(-1)
    require(len(arr)==stop-start,"Non native array "+variable)
    attrs={k:str(v.getncattr(k))[:300] for k in
           ("units","long_name","statistic_type","height","source",
           "description_L3","description_L4","description_L5","description_L6")
           if k in v.ncattrs()}
    return arr,attrs
def flags(ds,var,a,b):
    x,_=read(ds,var+"_QCFlag",a,b)
    return x
def qc(x,k):
    return bool(x is not None and np.isfinite(x[k]) and x[k]==0)
def fraction(x,k):
    return one(x[k]) if x is not None else None
def dates(series):
    return (np.datetime64("1800-01-01T00:00:00","s")
       +np.rint(np.asarray(series)*86400).astype("timedelta64[s]"))
def label(stamp):
    return np.datetime_as_string(stamp,unit="s").replace("T"," ")
def runs(mask):
    a=np.asarray(mask,bool)
    cut=np.flatnonzero(np.diff(np.r_[False,a,False].astype(np.int8)))
    return [(int(l),int(r)) for l,r in zip(cut[::2],cut[1::2])]
def normalize_pressure(value,unit):
    if value is None:return None
    u=unit.strip().lower().replace(" ","")
    if u in ("kpa","kilopascal","kilopascals"):return value*10.0
    if u in ("hpa","mbar","millibar","millibars"):return value
    if u in ("pa","pascal","pascals"):return value/100
    return None
def q_from_vapor_pressure(e_hpa,p_hpa):
    if e_hpa is None or p_hpa is None or e_hpa<0 or p_hpa<=e_hpa:return None
    return .622*e_hpa/(p_hpa-.378*e_hpa)
def q_from_RH(rh,T,p,unit_rh,unit_p):
    if rh is None or T is None or p is None:return None
    ur=unit_rh.strip().lower().replace(" ","")
    if ur in ("%","percent","percentage"):r=rh/100
    elif ur in ("fraction","1","dimensionless"):r=rh
    else:return None
    pp=normalize_pressure(p,unit_p)
    if pp is None or T<-80 or T>70 or r<0 or r>1.5:return None
    es=6.112*np.exp(17.62*T/(243.12+T))
    return q_from_vapor_pressure(r*es,pp)
def q_from_AH(ah,T,p,unit_ah,unit_p):
    if ah is None or T is None or p is None:return None
    u=unit_ah.strip().lower().replace(" ","")
    if u in ("g/m^3","g/m3","g.m-3","gm-3","g/m³"):a=ah
    elif u in ("kg/m^3","kg/m3","kgm-3"):a=ah*1000
    else:return None
    pp=normalize_pressure(p,unit_p)
    if pp is None or T<-80 or T>70 or a<0:return None
    # Absolute humidity [g m-3] = 216.7 e_hPa / T_K.
    return q_from_vapor_pressure(a*(T+273.15)/216.7,pp)
def diff(a,b):
    return a-b if a is not None and b is not None else None
def write(path,cols,data):
    with path.open("x",encoding="utf-8",newline="") as f:
        w=csv.DictWriter(f,fieldnames=cols,delimiter="\t",extrasaction="raise")
        w.writeheader();w.writerows(data)
def selftest():
    require(runs([False,True,True,False,True])==[(1,3),(4,5)],"run")
    q=q_from_RH(50,20,100,"%", "kPa")
    require(q is not None and .007<q<.008,"RH formula")
    require(normalize_pressure(94.6,"kPa")==946,"ps scale")
    print("OZFLUX STAGE20 SELF-TEST PASS | 2014 SH derived met / source-QC audit; READ ONLY")
def main():
    if sys.argv[1:]==["--self-test"]:return selftest()
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out",type=Path,required=True)
    dest=ap.parse_args().out
    require(dest.parent.resolve()==HOME.resolve() and
       not dest.exists() and not dest.is_symlink(),
       "Output must be NEW immediate HOME directory")
    require(sha256(L3)==L3_SHA and sha256(L6)==L6_SHA,
       "Original L3/L6 SHA changed")
    previous=json.loads(S19.read_text(encoding="utf-8"))
    require(previous.get("n_original_QC0_mismatches")==235
      and previous.get("classification_counts",{}).get("L3_NUMERIC_MISSING_L6_QC0")==235
      and previous.get("science_release") is False
      and previous.get("AD400_authorised") is False,
      "Stage19 actual operator evidence / HOLD changed")
    with Dataset(str(L3),"r") as old,Dataset(str(L6),"r") as filled:
        t3=old.variables["time"];t6=filled.variables["time"]
        require(t3.units==t6.units and "days since 1800-01-01" in t3.units,
          "Native clock units mismatch")
        time3=np.ma.asarray(t3[:],dtype=float).filled(np.nan).reshape(-1)
        time6=np.ma.asarray(t6[:],dtype=float).filled(np.nan).reshape(-1)
        a=time_index(t3,time3,"2014-01-01 00:00:00")
        b=time_index(t3,time3,"2015-01-01 00:00:00")
        c=time_index(t6,time6,"2014-01-01 00:00:00")
        d=time_index(t6,time6,"2015-01-01 00:00:00")
        require(b-a==d-c==17520 and
          np.max(np.abs(time3[a:b]-time6[c:d]))*86400<.1,
          "L3 and L6 2014 native year mismatch")
        stamps=dates(time3[a:b])
        met={};attributes={}
        for name,ds,lo,hi in (("L3",old,a,b),("L6",filled,c,d)):
            met[name]={}
            attributes[name]={}
            for var in MET:
                values,attrs=read(ds,var,lo,hi)
                q=flags(ds,var,lo,hi)
                met[name][var]=(values,q)
                attributes[name][var]=attrs
        sh3,qsh3=met["L3"]["SH"]
        sh6,qsh6=met["L6"]["SH"]
        require(all(x is not None for x in (sh3,qsh3,sh6,qsh6)),
            "SH source values/QC missing")
        suspect=(qsh6==0)&valid(sh6)&(~((qsh3==0)&valid(sh3)))
        ids=np.flatnonzero(suspect)
        require(len(ids)==235 and np.all(qsh3[ids]==1) and
                np.all(~valid(sh3[ids])),"235 SH source anomalies not exact")
        episodes=runs(suspect)
        # Input metadata units decide if RH / AH-derived estimates are meaningful.
        point={};vectors={}
        for name in ("L3","L6"):
            vectors[name]={}
            for var in MET:
                v,q=met[name][var]
                vectors[name][var]=v
        def derived(source,var,i):
            h=vectors[source]
            hum=h[var];t=h["Ta"];p=h["ps"]
            if any(z is None for z in (hum,t,p)):return None
            if not (valid(hum[i]) and valid(t[i]) and valid(p[i])):return None
            units=attributes[source]
            if var=="RH":
                return q_from_RH(float(hum[i]),float(t[i]),float(p[i]),
                       units[var].get("units",""),units["ps"].get("units",""))
            return q_from_AH(float(hum[i]),float(t[i]),float(p[i]),
                   units[var].get("units",""),units["ps"].get("units",""))
        allrows=[];spellrows=[];counts=Counter()
        def row(i,start):
            qrh3=derived("L3","RH",i);qrh6=derived("L6","RH",i)
            qah3=derived("L3","AH",i);qah6=derived("L6","AH",i)
            out={"native_time":label(stamps[i]),"offset_from_event_start_HH":i-start,
              "SH_from_L3_RH_Ta_ps":qrh3,"SH_from_L6_RH_Ta_ps":qrh6,
              "SH_from_L3_AH_Ta_ps":qah3,"SH_from_L6_AH_Ta_ps":qah6,
              "L6_SH_minus_RH_estimate":diff(one(sh6[i]),qrh6),
              "L6_SH_minus_AH_estimate":diff(one(sh6[i]),qah6)}
            for src in ("L3","L6"):
                for var in ("SH","AH","RH","VPD","Ta","ps","Precip","Ws"):
                    if src=="L3" and var=="Ws":continue
                    val,q=met[src][var]
                    out[src+"_"+var]=fraction(val,i)
                    out[src+"_"+var+"_QC"]=fraction(q,i)
            return {k:out.get(k) for k in EVENT_COLS}
        for start,stop in episodes:
            qq=sh6[start:stop]
            psqc=met["L6"]["ps"][1]
            taqc=met["L6"]["Ta"][1]
            overlap_ps=int(np.sum(psqc[start:stop]==410)) if psqc is not None else 0
            overlap_ta=int(np.sum(taqc[start:stop]==410)) if taqc is not None else 0
            h3a=met["L3"]["AH"][1];h3r=met["L3"]["RH"][1]
            h6a=met["L6"]["AH"][1];h6r=met["L6"]["RH"][1]
            match_r=0;match_a=0
            for i in range(start,stop):
                qr=derived("L6","RH",i);qa=derived("L6","AH",i)
                if qr is not None and abs(qr-sh6[i])<1e-5:match_r+=1
                if qa is not None and abs(qa-sh6[i])<1e-5:match_a+=1
            spellrows.append({"start_native":label(stamps[start]),
              "end_native":label(stamps[stop-1]),"n_HH":stop-start,
              "hours":(stop-start)/2,
              "L3_SH_all_missing_QC1":bool(np.all(qsh3[start:stop]==1)),
              "L6_SH_all_numeric_QC0":bool(np.all(qsh6[start:stop]==0)
                      and np.all(valid(sh6[start:stop]))),
              "2014_ps_AWS410_overlap_HH":overlap_ps,
              "2014_Ta_AWS410_overlap_HH":overlap_ta,
              "L6_SH_min":float(np.min(qq)),"L6_SH_max":float(np.max(qq)),
              "L6_SH_mean":float(np.mean(qq)),
              "SH_jump_in":float(sh6[start]-sh6[start-1]) if start else None,
              "SH_jump_out":float(sh6[stop]-sh6[stop-1]) if stop<len(sh6) else None,
              "L3_AH_QC0_HH":int(np.sum(h3a[start:stop]==0)) if h3a is not None else None,
              "L3_RH_QC0_HH":int(np.sum(h3r[start:stop]==0)) if h3r is not None else None,
              "L6_AH_QC0_HH":int(np.sum(h6a[start:stop]==0)) if h6a is not None else None,
              "L6_RH_QC0_HH":int(np.sum(h6r[start:stop]==0)) if h6r is not None else None,
              "SH_from_L6_RH_matches_within_1e_5_HH":match_r,
              "SH_from_L6_AH_matches_within_1e_5_HH":match_a,
              "review_decision":"HOLD_SOURCE_QC_LINEAGE_NOT_AUTOMATIC_REPAIR"})
            for i in range(max(0,start-4),min(len(sh6),stop+4)):
                allrows.append(row(i,start))
            counts["ps_AWS_overlap"]+=overlap_ps
            counts["Ta_AWS_overlap"]+=overlap_ta
            counts["L6_SH_matches_RH_calc"]+=match_r
            counts["L6_SH_matches_AH_calc"]+=match_a
        report={
          "site":"AU-ASM","L3_SHA256":L3_SHA,"L6_SHA256":L6_SHA,
          "stage19_receipt":str(S19),"source_exceptions_exactly":len(ids),
          "source_exceptions_year":2014,"variable":"SH",
          "n_spells":len(episodes),"source_metadata":attributes,
          "counts":dict(counts),"episodes":spellrows,
          "SH_source_reconstructed_formula_is_not_independent_data":True,
          "source_QC0_provenance_scientifically_approved":False,
          "source_time_END_vs_CENTER_scientifically_approved":False,
          "L4_AWS_ACCESS_fit_statistics_verified":False,
          "science_release":False,"AD400_authorised":False,
          "no_input_surface_CIME_or_Slurm_writes":True}
    dest.mkdir(mode=0o700,parents=False,exist_ok=False)
    write(dest/"stage20_235_SH_and_aux_humidity_source_rows.tsv",EVENT_COLS,allrows)
    write(dest/"stage20_2014_SH_source_spells_and_AWS_overlap.tsv",SPELL_COLS,spellrows)
    (dest/"stage20_2014_SH_QC0_source_science_HOLD.json").write_text(
      json.dumps(report,indent=2,ensure_ascii=False),encoding="utf-8")
    print("STAGE20 EXACT 235 SH MISSING-L3/QC0-L6 SOURCE RECORDS REPRODUCED")
    print("2014 SH SOURCE CONTIGUOUS SPELLS",len(episodes))
    print("L3/L6 HUMIDITY/SH METADATA",json.dumps({k:{v:attributes[k][v] for v in
          ("SH","AH","RH","ps","Ta","VPD")} for k in attributes},ensure_ascii=False))
    for e in spellrows:
        print("SPELL",e["start_native"],e["end_native"],"HH",e["n_HH"],
          "PS_AWS410",e["2014_ps_AWS410_overlap_HH"],
          "Ta_AWS410",e["2014_Ta_AWS410_overlap_HH"],
          "L3_AH_QC0",e["L3_AH_QC0_HH"],"L3_RH_QC0",e["L3_RH_QC0_HH"],
          "L6_SH_FROM_RH_MATCH",e["SH_from_L6_RH_matches_within_1e_5_HH"],
          "L6_SH_FROM_AH_MATCH",e["SH_from_L6_AH_matches_within_1e_5_HH"],
          "SH_MINMAX",e["L6_SH_min"],e["L6_SH_max"])
    print("STAGE20 PROVENANCE REVIEW; FORCING SCIENCE HOLD; NO AD400/SLURM")
    print("REPORT_DIR",dest)
if __name__=="__main__":main()
