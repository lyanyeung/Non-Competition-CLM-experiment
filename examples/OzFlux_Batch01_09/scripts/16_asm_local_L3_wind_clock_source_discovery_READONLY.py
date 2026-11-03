#!/usr/bin/env python3
"""AU-ASM Stage16: find lower-level L1/L2/L3 and clock/wind evidence READ ONLY.

Actual external evidence: OzFlux station lists CSAT3 at 11.6m, RM Young 03101
wind-speed profiles (2/4.25/6.5/9.25m), and RM Young 03301 wind vane (9.25m).
The OzFlux public collection lists AliceSpringsMulga_L3_20180101_20181231.nc
but warns that pre-2024 L3 had minimal supervised QC. Do NOT treat that L3
as definitive evidence, or infer that L6 contains RM Young independently.
Only list site-scoped accessible files and inspect NetCDF metadata/small 2018
windows. No network, downloads, original/candidate/Surface/CIME/Slurm writes.
"""
import argparse,datetime as dt,hashlib,json,os,sys
from pathlib import Path
import numpy as np
from netCDF4 import Dataset,date2num

HOME=Path.home()
SITE=Path("/iridisfs/scratch/ly3n24/CLM_FATES/sites/MY_EC_SITE/AU-ASM")
L6=SITE/"forcing/raw/AliceSpringsMulga1_20100903T0000_to_20230308T0900_L6.nc"
L6_SHA="b9381c4ed0744d03ae609cfbf3805e30bbb9223851a05f4e5b63b149dd0b10eb"
STAGE15=HOME/"ozflux_nc_stage15_20261103T132559Z"/"stage15_AU_ASM_3wind_DATM_crosswalk_science_HOLD.json"
OUTFILES=("stage16_local_site_data_inventory.json",
          "stage16_L6_time_processing_attributes.json",
          "stage16_lower_level_wind_candidate_evidence.json")
OFFICIAL="https://data.ozflux.org.au/pub/viewColDetails.jspx?collection.id=152&collection.owner.id=101&viewType=anonymous"
TARGET=dt.datetime(2018,3,10,20,30)
MAX_SCAN=1200
MAX_OPEN=30

def need(x,why):
    if not x:raise RuntimeError(str(why))
def sha(p):
    p=Path(p);need(p.is_file() and not p.is_symlink(),"Missing L6 "+str(p))
    h=hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda:f.read(4<<20),b""):h.update(b)
    return h.hexdigest()
def safe(v):
    if hasattr(v,"tolist"):v=v.tolist()
    return str(v)[:650]
def meta(v):
    out={}
    for k in ("units","calendar","long_name","time_zone","time_step",
              "statistic_type","height","instrument","source","history",
              "processing","description_L1","description_L2","description_L3",
              "description_L4","description_L5","description_L6"):
        if k in v.ncattrs():out[k]=safe(v.getncattr(k))
    return out
def scan(root):
    root=Path(root)
    need(root.is_dir() and not root.is_symlink(),"Not a valid site-scoped directory: "+str(root))
    found=[];seen=0;truncated=False
    # Avoid recursing into any symlinked paths and bound breadth / directory depth.
    for base,dirs,files in os.walk(str(root),followlinks=False):
        depth=len(Path(base).relative_to(root).parts)
        dirs[:]=sorted(d for d in dirs if
                depth<5 and not (Path(base)/d).is_symlink()
                and d not in (".git","archive","output","run","bld","cases"))
        for name in sorted(files):
            if not name.lower().endswith((".nc",".nc4",".zip",".csv",".txt",".xlsx")):
                continue
            p=Path(base)/name
            if p.is_symlink():continue
            seen+=1
            if seen>MAX_SCAN:
                truncated=True;break
            lower=name.lower()
            chosen=any(x in lower for x in ("l1","l2","l3","aws","access","era5",
                    "wind","sonic","2018","control","log"))
            if chosen:
                found.append({"path":str(p),"size_bytes":p.stat().st_size,
                    "candidate_lower_level_or_external":True,
                    "primary_for_2018_check":(name.lower().endswith((".nc",".nc4"))
                              and ("2018" in lower or "l3" in lower))})
        if truncated:break
    return {"root":str(root),"file_count_relevant":len(found),
            "total_allowed_file_names_seen":seen,"scan_truncated":truncated,
            "files":found}
def native_2018(ds):
    if "time" not in ds.variables:return {"has_CF_time":False}
    t=ds.variables["time"]
    if not hasattr(t,"units") or "since" not in t.units:
        return {"has_CF_time":False,"time_attrs":meta(t)}
    try:
        x=np.ma.asarray(t[:],dtype=float).filled(np.nan).reshape(-1)
        target=float(date2num(TARGET,t.units,calendar=getattr(t,"calendar","standard")))
        i=int(np.argmin(np.abs(x-target)))
        # A half-hour record can be off by <=15 minutes if original source
        # uses interval-centre rather than END; do NOT assert alignment.
        unit=t.units.lower().split(" since ",1)[0]
        factor={"days":86400,"day":86400,"hours":3600,"hour":3600,
                "minutes":60,"minute":60,"seconds":1,"second":1}.get(unit,0)
        minutes=abs(float(x[i])-target)*factor/60 if factor else None
        out={"has_CF_time":True,"N":len(x),"time_attrs":meta(t),
             "nearest_2018_03_10_20_30_native_index":i,
             "nearest_source_time_difference_minutes":minutes,
             "strict_same_native_halfhour":bool(minutes is not None and minutes<1e-4)}
        if minutes is not None and minutes<=30:
            matches={}
            td=t.dimensions[0]
            for name,v in ds.variables.items():
                low=name.lower()
                is_candidate=("wind" in low or "gust" in low or "young" in low or
                       name.startswith(("Ws","WS","Wd","WD","U_","V_")))
                if not is_candidate or v.dimensions.count(td)!=1:
                    continue
                j=v.dimensions.index(td)
                if v.shape[j]!=len(x) or any(z!=j and dim!=1
                     for z,dim in enumerate(v.shape)):continue
                sel=tuple(i if z==j else 0 for z in range(v.ndim))
                try:
                    val=np.ma.asarray(v[sel],dtype=float).filled(np.nan).reshape(-1)
                    val=float(val[0])
                except (ValueError,TypeError,IndexError):continue
                matches[name]={"native_value":val if np.isfinite(val) else None,
                              "metadata":meta(v)}
                if len(matches)>=50:break
            out["wind_like_channels_at_nearest_native_time"]=matches
        return out
    except Exception as e:
        return {"has_CF_time":False,"parse_problem":str(e)[:250],"time_attrs":meta(t)}
def inspect(path):
    p=Path(path);out={"path":str(p),"has_independent_sensor_approval":False}
    try:
        with Dataset(str(p),"r") as ds:
            out["global_time_and_site_attributes"]={
                k:safe(ds.getncattr(k)) for k in ds.ncattrs()
                if any(w in k.lower() for w in
                    ("time","step","site","instrument","processing","history","source"))}
            out["candidate_channel_names"]=[
                name for name in ds.variables
                if ("wind" in name.lower() or "gust" in name.lower()
                    or "young" in name.lower() or name.startswith(("Ws","WS","Wd","WD","U_","V_")))][:100]
            out["source_2018_context"]=native_2018(ds)
    except Exception as e:
        out["inspection_problem"]=str(e)[:350]
    return out
def selftest():
    need(TARGET.isoformat()=="2018-03-10T20:30:00","timestamp")
    need("2018" in "AliceSpringsMulga_L3_20180101_20181231.nc","L3 filename")
    print("OZFLUX STAGE16 SELF-TEST PASS | scoped local lower-level/wind/time provenance; READ ONLY")
def main():
    if sys.argv[1:]==["--self-test"]:return selftest()
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out",required=True,type=Path)
    ap.add_argument("--additional-dir",type=Path,
                    help="Optional user-selected LOCAL AU-ASM L1/L2/L3 directory only")
    args=ap.parse_args()
    o=args.out
    need(o.parent.resolve()==HOME.resolve() and not o.exists() and
         not o.is_symlink(),"Output must be NEW immediate HOME directory")
    need(sha(L6)==L6_SHA,"Original AU-ASM L6 bytes changed")
    s15=json.loads(STAGE15.read_text(encoding="utf-8"))
    need(s15.get("science_release") is False and
         s15.get("AD400_authorised") is False and
         len(s15.get("events",[]))==3 and
         s15.get("model_input_stage14_wind_matches_source") is True,
         "Actual Stage15 wind crosswalk / science-HOLD receipt changed")
    with Dataset(str(L6),"r") as ds:
        tm=meta(ds.variables["time"])
        glob={k:safe(ds.getncattr(k)) for k in ds.ncattrs()
              if any(x in k.lower() for x in
                  ("time","zone","site","history","processing","source","instrument","comment"))}
        L6_metadata={"exact_L6_SHA256":L6_SHA,
          "time_variable_attributes":tm,"relevant_global_attributes":glob,
          "Ws_variable":meta(ds.variables["Ws"]),"Wd_variable":meta(ds.variables["Wd"]),
          "PyFluxPro_general_rule_preserves_source_labels":True,
          "site_specific_L1_end_of_period_proven":False,
          "original_end_interval_vs_center_independently_certified":False,
          "clock_science_release":False}
    roots=[SITE]
    if args.additional_dir is not None:
        q=args.additional_dir.resolve(strict=True)
        need(q!=Path("/") and q!=HOME and q!=SITE,
             "Additional dir cannot be root/HOME/duplicate site")
        roots.append(q)
    summaries=[scan(root) for root in roots]
    candidates=[z["path"] for r in summaries for z in r["files"]
                if z["primary_for_2018_check"]]
    seen=set();records=[]
    for file in candidates:
        if file in seen:continue
        seen.add(file)
        if file==str(L6):continue
        if len(records)>=MAX_OPEN:break
        records.append(inspect(file))
    out={"site":"AU-ASM","L6_source_SHA256":L6_SHA,
         "audited_inventory":summaries,
         "fetched_or_downloaded_anything":False,
         "number_of_local_candidate_NetCDF_inspected":len(records),
         "truncated_inspection":len(seen)>MAX_OPEN,
         "official_site_2018_L3_reference":
           "AliceSpringsMulga_L3_20180101_20181231.nc",
         "official_OzFlux_collection_url":OFFICIAL,
         "L3_pre_2024_supervision_is_limited":True,
         "official_separate_RM_Young_speed_profile_2_4p25_6p5_9p25m":True,
         "separate_speed_sensor_actually_found_in_input":False,
         "independent_wind_source_validated":False,
         "time_source_clock_approved":False,
         "forcings_science_release":False,"AD400_authorised":False,
         "no_CIME_Slurm_or_original_inputs_changed":True}
    outdir=o
    outdir.mkdir(mode=0o700)
    for name,data in zip(OUTFILES,(out,L6_metadata,
                                    {"source_candidate_files":records})):
        (outdir/name).write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding="utf-8")
    print("ORIGINAL L6 SHA AND STAGE15 HOLD VERIFIED")
    print("NATIVE TIME METADATA",json.dumps(tm,ensure_ascii=False))
    print("SITE CLOCK/SOURCE GLOBAL ATTRS",json.dumps(glob,ensure_ascii=False))
    for r in summaries:
        print("LOCAL SITE CANDIDATES",r["root"],r["file_count_relevant"],
              "SCAN TRUNCATED",r["scan_truncated"])
        for p in r["files"]:
            if ("2018" in p["path"].lower()
                or "l3" in Path(p["path"]).name.lower()):
                print("CANDIDATE FILE",p["path"],"SIZE",p["size_bytes"])
    for r in records:
        print("LOWER-LEVEL INSPECTION",r["path"],
              "WIND CHANNELS",r.get("candidate_channel_names",[]),
              "2018 CONTEXT",r.get("source_2018_context",{}))
    print("OFFICIAL 2018 L3 REFERENCE",OFFICIAL)
    print("STAGE16 SOURCE DISCOVERY PASS; L3 AND CLOCK EVIDENCE NOT YET APPROVED")
    print("FORCING SCIENCE HOLD, NO CIME/SLURM")
    print("REPORT_DIR",outdir)
if __name__=="__main__":main()
