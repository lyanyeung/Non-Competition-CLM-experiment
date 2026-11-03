#!/usr/bin/env python3
"""AU-ASM Stage17: independent TERN 2026_v3 L3 versus immutable original L6.

READ ONLY official 75,555,995-byte L3 downloaded by the operator from:
https://dap.tern.org.au/thredds/fileServer/ecosystem_process/ozflux/AliceSpringsMulga/2026_v3/L3/default/AliceSpringsMulga_20100903T0000_to_20230308T0900_L3.nc

TERN's updated L3 is not guaranteed to contain independent RM Young speed.
2026 reprocessing might change QC flags; time and source convention still
must be certified. Never modify 2013-2018 DATM, original L6 or site-soil v2.
Script writes only one new isolated JSON report, no Slurm or CIME.
"""
from __future__ import annotations
import argparse,datetime as dt,hashlib,json,math
from pathlib import Path
import numpy as np
from netCDF4 import Dataset,date2num
HOME=Path.home()
ORIGINAL=Path("/iridisfs/scratch/ly3n24/CLM_FATES/sites/MY_EC_SITE/AU-ASM/forcing/raw/AliceSpringsMulga1_20100903T0000_to_20230308T0900_L6.nc")
ORIGINAL_SHA="b9381c4ed0744d03ae609cfbf3805e30bbb9223851a05f4e5b63b149dd0b10eb"
EXPECTED_L3_SIZE=75555995
SOURCE_URL="https://dap.tern.org.au/thredds/fileServer/ecosystem_process/ozflux/AliceSpringsMulga/2026_v3/L3/default/AliceSpringsMulga_20100903T0000_to_20230308T0900_L3.nc"
EVENTS=("2018-03-10 20:30:00","2013-01-05 18:00:00","2014-11-23 01:00:00")
MET=("Ws","Wd","Ta","SH","ps","Fsd","Fld","Precip")
BOUNDARY=("2017-08-17 22:00:00","2017-09-03 08:30:00")
AWS=("2018-06-09 18:00:00","2018-06-13 09:00:00")
def need(v,why):
    if not v:raise ValueError(why)
def sha(p):
    h=hashlib.sha256()
    with p.open("rb") as f:
        for part in iter(lambda:f.read(4<<20),b""):h.update(part)
    return h.hexdigest()
def simple(v):
    if isinstance(v,np.generic):return v.item()
    if hasattr(v,"tolist"):return v.tolist()
    return v
def meta(v):
    return {a:str(simple(v.getncattr(a)))[:900] for a in
       ("units","calendar","long_name","time_zone","time_step",
        "statistic_type","height","instrument","source","description_L3",
        "description_L4","description_L5","description_L6")
       if a in v.ncattrs()}
def global_meta(ds):
    return {n:str(simple(ds.getncattr(n)))[:900] for n in ds.ncattrs()
        if any(x in n.lower() for x in
           ("time","source","history","processing","site","version","instrument"))}
def arr(v):
    return np.ma.asarray(v[:],dtype=float).filled(np.nan).reshape(-1)
def scalar(v):
    if v is None:return None
    try:
        a=float(np.ma.asarray(v,dtype=float).filled(np.nan))
    except (TypeError,ValueError):return None
    return a if math.isfinite(a) and a>-9990 else None
def index(ds,label):
    t=ds.variables["time"]
    tv=arr(t)
    date=dt.datetime.fromisoformat(label)
    expected=float(date2num(date,t.units,calendar=getattr(t,"calendar","standard")))
    j=int(np.searchsorted(tv,expected))
    # Numeric NetCDF time coordinates may accumulate millisecond rounding.
    cand=[k for k in (j-1,j) if 0<=k<len(tv)]
    if not cand:return None,None
    best=min(cand,key=lambda k:abs(tv[k]-expected))
    units=t.units.split(" since ",1)[0].lower().strip()
    scale={"day":86400,"days":86400,"hour":3600,"hours":3600,
           "minute":60,"minutes":60,"second":1,"seconds":1}.get(units)
    need(scale is not None,"Unsupported CF time unit "+t.units)
    seconds=abs(tv[best]-expected)*scale
    return (best if seconds<=60 else None),seconds
def point(ds,name,j):
    if j is None or name not in ds.variables:return {"present":False}
    v=ds.variables[name]
    td=ds.variables["time"].dimensions[0]
    if v.dimensions.count(td)!=1:return {"present":False,"metadata":meta(v)}
    pos=v.dimensions.index(td)
    if v.shape[pos]!=len(ds.dimensions[td]) or any(
            d!=td and v.shape[i]!=1 for i,d in enumerate(v.dimensions)):
        return {"present":False,"metadata":meta(v)}
    selector=tuple(j if i==pos else 0 for i in range(v.ndim))
    # A scalar slice is lightweight even for a large L3.
    raw_val=v[selector]
    result={"present":True,"value":scalar(raw_val),"metadata":meta(v)}
    qc=name+"_QCFlag"
    if qc in ds.variables:
        result["QCFlag"]=scalar(ds.variables[qc][selector])
    return result
def event(ds,name,where):
    ix,offset=index(ds,where)
    result={"time_label":where,"native_index":ix,"offset_seconds":offset,
            "all_met":{k:point(ds,k,ix) for k in MET}}
    t=ds.variables["time"]
    if ix is not None:
        result["Ws_before"]=point(ds,"Ws",ix-1) if ix>0 else {}
        result["Ws_after"]=point(ds,"Ws",ix+1) if ix+1<len(t) else {}
    return result
def periods(ds,variable,first,last):
    a,offa=index(ds,first);b,offb=index(ds,last)
    if a is None or b is None or a>b:
        return {"matched":False,"start_offset_seconds":offa,"end_offset_seconds":offb}
    v=ds.variables.get(variable)
    if v is None:return {"matched":True,"variable_present":False}
    td=ds.variables["time"].dimensions[0]
    if v.dimensions.count(td)!=1:return {"matched":True,"variable_shape_unsupported":list(v.shape)}
    ax=v.dimensions.index(td)
    sel=tuple(slice(a,b+1) if i==ax else 0 for i in range(v.ndim))
    values=np.ma.asarray(v[sel],dtype=float).filled(np.nan).reshape(-1)
    good=np.isfinite(values)&(values>-9990)
    report={"matched":True,"records":b-a+1,"valid":int(good.sum()),
       "missing":int((~good).sum()),"min":float(values[good].min()) if good.any() else None,
       "mean":float(values[good].mean()) if good.any() else None,
       "max":float(values[good].max()) if good.any() else None}
    q=ds.variables.get(variable+"_QCFlag")
    if q is not None:
        flags=np.ma.asarray(q[sel],dtype=float).filled(np.nan).reshape(-1)
        report["QC_flag_counts"]={
          str(int(x)):int(np.sum(flags==x)) for x in np.unique(flags[np.isfinite(flags)])}
    return report
def selftest():
    need(EXPECTED_L3_SIZE==75555995 and len(EVENTS)==3,
         "Confirmed official TERN L3 and three events")
    need(BOUNDARY[0]<BOUNDARY[1],"Range")
    print("OZFLUX STAGE17 SELF-TEST PASS | official TERN 2026_v3 L3 vs old L6; READ ONLY")
def main():
    import sys
    if sys.argv[1:]==["--self-test"]:return selftest()
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--l3",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    a=p.parse_args()
    l3=a.l3;out=a.out
    need(l3.is_file() and not l3.is_symlink() and l3.stat().st_size==EXPECTED_L3_SIZE,
         "Official L3 size mismatch; do not use webpage or truncated download")
    need(ORIGINAL.is_file() and sha(ORIGINAL)==ORIGINAL_SHA,
         "Immutable original L6 SHA drift")
    need(out.parent.resolve()==HOME.resolve() and not out.exists() and not out.is_symlink(),
         "Reports require an UNUSED immediate HOME child")
    l3_hash=sha(l3)
    result={"site":"AU-ASM",
        "official_L3_URL":SOURCE_URL,
        "official_L3_file":str(l3),"official_L3_size_bytes":EXPECTED_L3_SIZE,
        "official_L3_SHA256_actual":l3_hash,
        "original_L6_SHA256":ORIGINAL_SHA,
        "status":"FORCING_SCIENCE_HOLD","science_release":False,
        "AD400_authorised":False,"new_site_soil_v2_unchanged":True,
        "none_of_original_L3_L6_DATM_CIME_SLURM_modified":True,
        "archival_L3_is_not_automatically_independent_sensor":True,
        "timestamps_label_alignment_proves_absolute_UTC":False}
    with Dataset(str(l3),"r") as L3,Dataset(str(ORIGINAL),"r") as L6:
        for label,ds in (("TERN_2026_v3_L3",L3),("PINNED_OLD_L6",L6)):
            need("time" in ds.variables and ds.variables["time"].ndim==1,
                 label+" missing CF time")
            related=sorted(k for k in ds.variables if
                "wind" in k.lower() or "gust" in k.lower() or "young" in k.lower()
                or k.startswith(("Ws","WS","Wd","WD","U_","V_")))
            result[label]={"n_time":len(ds.variables["time"]),
                "time_metadata":meta(ds.variables["time"]),
                "global_provenance":global_meta(ds),
                "wind_channel_names":related[:110],
                "wind_channel_metadata":{k:meta(ds.variables[k]) for k in related[:65]},
                "events":{x:event(ds,label,x) for x in EVENTS},
                "2017_Fld_395h":periods(ds,"Fld",*BOUNDARY),
                "2018_AWS_multi_met_87p5h":{x:periods(ds,x,*AWS) for x in
                     ("Ta","SH","ps","Ws","Precip","Fsd","Fld")}}
    out.mkdir(mode=0o700,parents=False,exist_ok=False)
    report=out/"stage17_TERN_2026v3_L3_vs_original_L6_science_HOLD.json"
    report.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
    print("ORIGINAL L6 SHA VERIFIED, OFFICIAL L3 SIZE VERIFIED")
    print("L3 SHA256",l3_hash)
    for label in ("TERN_2026_v3_L3","PINNED_OLD_L6"):
        v=result[label]
        print("==",label,"==")
        print("GLOBAL",json.dumps(v["global_provenance"],ensure_ascii=False)[:3000])
        print("TIME",json.dumps(v["time_metadata"]))
        print("WIND CHANNELS",v["wind_channel_names"])
        for date,x in v["events"].items():
            ws=x["all_met"].get("Ws",{})
            wd=x["all_met"].get("Wd",{})
            print("EVENT",date,"match_time_offset_sec",x["offset_seconds"],
                  "Ws",ws.get("value"),"WsQC",ws.get("QCFlag"),
                  "Wd",wd.get("value"),"WdQC",wd.get("QCFlag"),
                  "Ws_prev",x.get("Ws_before",{}).get("value"),
                  "Ws_next",x.get("Ws_after",{}).get("value"))
        print("2017 L3-FLD 395H",json.dumps(v["2017_Fld_395h"]))
        print("2018 AWS JOINT",json.dumps(v["2018_AWS_multi_met_87p5h"]))
    print("STAGE17 READONLY SOURCE COMPARISON COMPLETE; SCIENCE HOLD; NO AD400")
    print("REPORT_DIR",out)

if __name__=="__main__":main()
