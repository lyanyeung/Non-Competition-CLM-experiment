#!/usr/bin/env python3
"""AU-ASM original OzFlux L6 meteorology event science audit, READ ONLY.
AmeriFlux/ICOS style: raw QC, model fills, thermodynamics, before/during/after,
source donor evidence and explicit science HOLD. No Slurm or model-file writes.
"""
import argparse,csv,datetime as dt,hashlib,json,sys
from pathlib import Path
import netCDF4
import numpy as np

HOME=Path.home()
ROOT=Path("/iridisfs/scratch/ly3n24/CLM_FATES/sites/MY_EC_SITE/AU-ASM/forcing/raw")
SOURCE=ROOT/"AliceSpringsMulga1_20100903T0000_to_20230308T0900_L6.nc"
SOURCE_SHA="b9381c4ed0744d03ae609cfbf3805e30bbb9223851a05f4e5b63b149dd0b10eb"
S5=HOME/"ozflux_nc_stage05_20261102T224556Z_FIX"
VARS=("Ta","SH","ps","Fsd","Fld","Ws","Precip")
CODE=(0,10,50,400,410,420,430,440)
LIMITS={"Ta":(-55,65),"SH":(0,.055),"ps":(45,115),"Fsd":(-50,1600),
        "Fld":(0,850),"Ws":(-.1,65),"Precip":(0,None)}
JUMPS={"Ta":6,"SH":.003,"ps":2.5,"Fsd":500,"Fld":120,"Ws":10}
YRS=range(2013,2019)
A=["site","year","variable","native_rows","QC0","QC10","QC50","QC400",
   "QC410","QC420","QC430","QC440","other","missing_QC","missing_met",
   "broad_physical_alarms","step_jump_review"]
E=["site","variable","QC_class","first_native","last_native","hours",
   "count","first_index","last_index","before","first","last","after",
   "jump_into","jump_out","human_review"]
C=["focus","native_time","source_row","primary_variable","Ta","Ta_QCFlag",
   "SH","SH_QCFlag","ps","ps_QCFlag","Fsd","Fsd_QCFlag","Fld","Fld_QCFlag",
   "Ws","Ws_QCFlag","Precip","Precip_QCFlag","alternate_sensor_json"]

def check(b,msg):
    if not b:raise ValueError(msg)

def sha(p):
    check(p.is_file() and not p.is_symlink(),"Missing original source "+str(p))
    h=hashlib.sha256()
    with p.open("rb") as f:
        for x in iter(lambda:f.read(4<<20),b""):h.update(x)
    return h.hexdigest()

def table(p):
    with p.open(encoding="utf-8-sig",newline="") as f:return list(csv.DictReader(f,delimiter="\t"))

def write(p,fields,rows):
    with p.open("x",encoding="utf-8",newline="") as f:
        w=csv.DictWriter(f,fields,delimiter="\t");w.writeheader();w.writerows(rows)

def read(ds,name,td,n,a,b):
    check(name in ds.variables,"Missing native source variable "+name)
    v=ds.variables[name]
    check(np.issubdtype(v.dtype,np.number) and v.dimensions.count(td)==1,
          "Wrong time dimension "+name)
    t=v.dimensions.index(td)
    check(v.shape[t]==n and all(i==t or x==1 for i,x in enumerate(v.shape)),
          "Non-singleton source "+name)
    ix=tuple(slice(a,b) if i==t else slice(None) for i in range(v.ndim))
    x=np.ma.asarray(v[ix],dtype=float).filled(np.nan).reshape(-1)
    check(len(x)==b-a,"Source length "+name)
    return x

def spans(mask):
    v=np.asarray(mask,dtype=bool)
    cuts=np.flatnonzero(np.diff(np.r_[False,v,False].astype(np.int8)))
    return [(int(a),int(b)) for a,b in zip(cuts[::2],cuts[1::2])]

def label(t,value):
    d=netCDF4.num2date(float(value),t.units,calendar=getattr(t,"calendar","standard"))
    return f"{d.year:04d}-{d.month:02d}-{d.day:02d} {d.hour:02d}:{d.minute:02d}:{d.second:02d}"

def xc(x):return float(x) if np.isfinite(x) else None

def qc_count(q):
    h={str(k):int(np.sum(q==k)) for k in CODE}
    h["other"]=int(np.sum(np.isfinite(q)&~np.isin(q,CODE)))
    h["NA"]=int(np.sum(~np.isfinite(q)))
    check(sum(h.values())==len(q),"QC partition")
    return h

def selftest():
    check(spans([0,1,1,0,1])==[(1,3),(4,5)],"run spans")
    check(qc_count(np.array([0,50,420,440,400,430,410,10,9,np.nan]))["other"]==1,"QC 400-440")
    print("OZFLUX STAGE09 SELF TEST PASS; READ ONLY; FORCING SCIENCE HOLD")

def main():
    if sys.argv[1:]==["--self-test"]:return selftest()
    p=argparse.ArgumentParser();p.add_argument("--out",type=Path,required=True)
    out=p.parse_args().out
    check(not out.exists() and not out.is_symlink() and out.parent.resolve()==HOME.resolve(),
          "Reports only in an UNUSED direct HOME child")
    check(sha(SOURCE)==SOURCE_SHA,"Original OzFlux L6 SHA changed")
    status=json.loads((S5/"stage05_three_site_priority_summary.json").read_text())
    check(status.get("stage08_196_variable_years_reconciled") is True
          and status.get("AD400_authorised") is False,"Stage05 QC lineage not verified")
    reference={}
    for row in table(S5/"stage05_three_site_year_variable_QC.tsv"):
        if row["site"]=="AU-ASM":reference[(int(row["year"]),row["variable"])]=row
    check(len(reference)==42,"Expected 42 AU-ASM Stage05 year-variable rows")
    yearly=[];events=[];context=[];donor_meta={}
    with netCDF4.Dataset(str(SOURCE),"r") as ds:
        time=ds.variables["time"];check(time.ndim==1,"Time not one-dimensional")
        alltime=np.ma.asarray(time[:],dtype=float).filled(np.nan)
        cal=getattr(time,"calendar","standard")
        ia=int(np.searchsorted(alltime,netCDF4.date2num(dt.datetime(2013,1,1),time.units,calendar=cal)))
        ib=int(np.searchsorted(alltime,netCDF4.date2num(dt.datetime(2019,1,1),time.units,calendar=cal)))
        native=alltime[ia:ib]
        check(len(native)==105168 and np.all(np.diff(native)>0),
              "Six native 2013-18 years incl leap day must have 105168 halfhours")
        data={}; qc={}; donor={}
        for v in VARS:
            data[v]=read(ds,v,time.dimensions[0],len(alltime),ia,ib)
            qc[v]=read(ds,v+"_QCFlag",time.dimensions[0],len(alltime),ia,ib)
            donor[v]={}
            for name in ds.variables:
                if not name.startswith(v+"_") or name.endswith("_QCFlag"):continue
                tail=name[len(v)+1:]
                if any(z.lower() in ("qc","qcflag","sd","se","std","source","coverage","flag","variance")
                       for z in tail.split("_")):continue
                try:donor[v][name]=read(ds,name,time.dimensions[0],len(alltime),ia,ib)
                except (ValueError,KeyError):continue
                if len(donor[v])>=15:break
            donor_meta[v]=list(donor[v])
        for y in YRS:
            start=int(np.searchsorted(native,netCDF4.date2num(dt.datetime(y,1,1),time.units,calendar=cal)))
            stop=int(np.searchsorted(native,netCDF4.date2num(dt.datetime(y+1,1,1),time.units,calendar=cal)))
            check(stop-start==(17568 if y==2016 else 17520),"Year source count "+str(y))
            for v in VARS:
                x=data[v][start:stop];q=qc[v][start:stop]
                z=qc_count(q);r=reference[(y,v)]
                check(int(r["records"])==len(x),"Stage05 records mismatch")
                for code,col in (("50","qc50"),("420","qc420"),("440","qc440"),
                                 ("other","other_qc"),("NA","qc_unavailable")):
                    check(z[code]==int(r[col]),f"Stage05 mismatch {y} {v} {code}")
                ok=np.isfinite(x)&(x>-9990)
                low,high=LIMITS[v]
                alarm=(~ok)|(x<low)
                if high is not None:alarm|=x>high
                jump=int(np.sum((np.abs(np.diff(x))>JUMPS[v])&ok[1:]&ok[:-1])) if v in JUMPS else 0
                yearly.append(dict(site="AU-ASM",year=y,variable=v,native_rows=len(x),
                   **{"QC"+str(k):z[str(k)] for k in CODE},other=z["other"],
                   missing_QC=z["NA"],missing_met=int((~ok).sum()),
                   broad_physical_alarms=int(alarm.sum()),step_jump_review=jump))
        focus={}
        for v in VARS:
            x=data[v];q=qc[v]
            masks={"ACCESS_420":q==420,"ERA5_440":q==440,
                   "OTHER_ALT_400_410_430":np.isin(q,(400,410,430)),
                   "INTERPOLATION_50":q==50,
                   "ANY_NON_QC0":(~np.isfinite(q))|(q!=0)}
            for cls,mask in masks.items():
                allspans=spans(mask)
                for a,b in allspans:
                    bef=xc(x[a-1]) if a else None
                    aft=xc(x[b]) if b<len(x) else None
                    first,last=xc(x[a]),xc(x[b-1])
                    events.append(dict(site="AU-ASM",variable=v,QC_class=cls,
                         first_native=label(time,native[a]),last_native=label(time,native[b-1]),
                         hours=(b-a)*.5,count=b-a,first_index=ia+a,last_index=ia+b-1,
                         before=bef,first=first,last=last,after=aft,
                         jump_into=first-bef if first is not None and bef is not None else "",
                         jump_out=aft-last if aft is not None and last is not None else "",
                         human_review=True))
                if cls in ("ACCESS_420","ERA5_440","INTERPOLATION_50"):
                    for a,b in sorted(allspans,key=lambda ab:-(ab[1]-ab[0]))[:6]:
                        focus[f"{v}_{cls}_{label(time,native[a])}"]=(v,a,b)
        # 2017 exact 395-hour Fld ACCESS episode must be reproduced.
        wanted=[(a,b) for a,b in spans(qc["Fld"]==420)
           if b-a==790 and label(time,native[a])=="2017-08-17 22:00:00"
             and label(time,native[b-1])=="2017-09-03 08:30:00"]
        check(len(wanted)==1,"2017 original 395-hour Fld ACCESS source differs")
        focus["2017_Fld_395H_FULL_SOURCE_CONTEXT"]=("Fld",*wanted[0])
        # Additional raw negative shortwave and peak wind require review.
        neg=np.flatnonzero((data["Fsd"]<0)&np.isfinite(data["Fsd"]))
        for j in neg:focus[f"NEGATIVE_Fsd_{j}"]=("Fsd",int(j),int(j)+1)
        j=int(np.nanargmax(data["Ws"]))
        focus["PEAK_WIND_SOURCE"]=("Ws",j,j+1)
        for key,(v,a,b) in focus.items():
            ids=range(max(0,a-8),min(len(native),b+8))
            for i in ids:
                row={"focus":key,"native_time":label(time,native[i]),
                     "source_row":ia+i,"primary_variable":v,
                     "alternate_sensor_json":json.dumps(
                         {n:xc(z[i]) for n,z in donor[v].items()})}
                for x in VARS:
                    row[x]=xc(data[x][i]);row[x+"_QCFlag"]=xc(qc[x][i])
                context.append(row)
        T=data["Ta"];Q=data["SH"];P=data["ps"]
        ehpa=10*Q*P/(.622+.378*Q)
        es=6.112*np.exp(np.clip(17.67*T/(T+243.5),-20,20))
        RH=100*ehpa/es
        phys={"RH_water_over100":int(np.sum(RH>100)),
              "RH_water_over105":int(np.sum(RH>105)),
              "VPD_below_minus0p1hPa":int(np.sum(es-ehpa<-.1)),
              "RH_water_max":float(np.nanmax(RH)),
              "source_Fsd_negative":int(len(neg)),
              "peak_wind_source":float(data["Ws"][j]),
              "peak_wind_native":label(time,native[j])}
    out.mkdir(mode=0o700,parents=False,exist_ok=False)
    write(out/"stage09_year_variable_original_QC.tsv",A,yearly)
    write(out/"stage09_ALL_native_QC_spells.tsv",E,events)
    write(out/"stage09_before_during_after_met_and_sensor_candidates.tsv",C,context)
    report={"site":"AU-ASM","status":"FORCING_SCIENCE_HOLD",
      "native_L6_source_SHA256":SOURCE_SHA,"year_variable_reconciled":42,
      "QC_spells":len(events),"context_rows":len(context),
      "2017_395h_Fld_ACCESS_source_reproduced":True,
      "source_alternate_sensor_name_candidates_NOT_verified_tower":donor_meta,
      "physics":phys,"science_release":False,"AD400_authorised":False,
      "operator_decision_pending":True,
      "source_timestamp_UTC_semantics_independently_approved":False,
      "notes":["PyFluxPro QC420 ACCESS and 440 ERA5 are NOT independent tower observations",
               "PyFluxPro QC0 is NOT equivalent to FLUXNET ONEFlux original QC0",
               "Review ALL source model-fill episodes and before-after boundary jumps",
               "Review actual donor sensor provenance; 2018 wind; rain extremes",
               "Original Stage14 six DATM and GitHub Surface unchanged"],
      "no_CIME_or_Slurm_submitted":True}
    (out/"stage09_FORCING_SCIENCE_HOLD.json").write_text(
        json.dumps(report,indent=2,ensure_ascii=False),encoding="utf-8")
    print("STAGE09 42 ORIGINAL QC YEAR-VAR RECONCILED",flush=True)
    print("2017 Fld 395h ACCESS FULL SOURCE CONTEXT REPRODUCED",flush=True)
    print("QC SPELLS",len(events),"CONTEXT",len(context),flush=True)
    print("THERMODYNAMICS",json.dumps(phys),flush=True)
    print("STAGE09 FORCING SCIENCE HOLD, NOT RELEASED; NO SLURM",flush=True)
    print("REPORT_DIR",out,flush=True)

if __name__=="__main__":main()
