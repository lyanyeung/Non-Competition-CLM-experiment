#!/usr/bin/env python3
"""AU-ASM Stage23: inspect actual official TERN 2026_v3 L4 donor provenance.

Two modes:
  --catalog XML --list: parse operator-downloaded THREDDS catalogue XML,
    print EXACT source fileServer URL, do not fabricate L4 filename.
  --catalog XML --l4 downloaded.nc --out NEW_HOME_FOLDER: retain immutable
    old L6 and Stage22 science HOLD, hash downloaded L4, inspect L4 variables,
    original 2013–2018 QC fill flags, key long gaps and donor intermediate
    names. Only metadata/selected NetCDF time points are read. No source
    replacement, case/Surface updates, auto meteorology QC release or Slurm.

L4 from same TERN release is a distinct processing level, NOT independent
instrument validation, and L4 may omit model/AWS intermediate driver series.
Fit quality cannot be proven if donor series/workbook are not available.
"""
from __future__ import annotations
import argparse,datetime as dt,hashlib,json,math,sys
from pathlib import Path
from xml.etree import ElementTree as ET
import numpy as np
from netCDF4 import Dataset,date2num

HOME=Path.home()
L6=Path("/iridisfs/scratch/ly3n24/CLM_FATES/sites/MY_EC_SITE/AU-ASM/forcing/raw/AliceSpringsMulga1_20100903T0000_to_20230308T0900_L6.nc")
L6_SHA="b9381c4ed0744d03ae609cfbf3805e30bbb9223851a05f4e5b63b149dd0b10eb"
L3=HOME/"ozflux_ASM_TERN_2026v3_L3_source/AliceSpringsMulga_20100903T0000_to_20230308T0900_L3.nc"
L3_SHA="8faa211fe95aa9f0382bf8d3848cb3245d6c8a25bf4ac440e6e92a77c8759076"
S22=HOME/"ozflux_nc_stage22_20261104T031037Z/stage22_2014_SH_235_PFP_source_QC_science_HOLD.json"
CATALOG="https://dap.tern.org.au/thredds/catalog/ecosystem_process/ozflux/AliceSpringsMulga/2026_v3/L4/default/catalog.xml"
PREFIX="ecosystem_process/ozflux/AliceSpringsMulga/2026_v3/L4/default/"
SERVER="https://dap.tern.org.au/thredds/fileServer/"
KEYS=("2018-03-10 20:30:00","2017-08-17 22:00:00",
      "2017-09-03 08:30:00","2018-06-09 18:00:00",
      "2018-06-13 09:00:00","2014-08-26 17:30:00",
      "2014-11-30 15:00:00")
VARS=("Ta","SH","AH","RH","ps","Fsd","Fld","Ws","Precip")
ALTS=("aws","access","era5","era","clim","alternate","gap","donor")
def need(b,s):
    if not b:raise ValueError(s)
def sha(path):
    p=Path(path)
    need(p.is_file() and not p.is_symlink(),"Missing source or symlink "+str(p))
    h=hashlib.sha256()
    with p.open("rb") as f:
        for part in iter(lambda:f.read(4<<20),b""):h.update(part)
    return h.hexdigest()
def catalog_urls(xmlpath):
    root=ET.parse(xmlpath).getroot()
    allpaths=[]
    for x in root.iter():
        if x.tag.split("}")[-1]!="dataset":continue
        raw=x.attrib.get("urlPath","")
        if not raw or not raw.startswith(PREFIX):continue
        fname=raw.rsplit("/",1)[-1]
        if not (fname.startswith("AliceSpringsMulga") and
                fname.endswith("_L4.nc") and
                "20100903" in fname and "20230308" in fname):
            continue
        need(".." not in raw and "?" not in raw and "#" not in raw,
             "Unexpected dataset path")
        allpaths.append({"filename":fname,"source_url":SERVER+raw,
           "THREDDS_urlPath":raw})
    unique={x["source_url"]:x for x in allpaths}
    return list(unique.values())
def meta(v):
    return {name:str(v.getncattr(name))[:500] for name in
          ("units","long_name","source","instrument","statistic_type",
           "description_L3","description_L4","description_L5","description_L6")
           if name in v.ncattrs()}
def gmeta(ds):
    return {k:str(ds.getncattr(k))[:500] for k in ds.ncattrs()
           if any(y in k.lower() for y in
              ("time","source","version","history","processing","site"))}
def point(ds,vname,index):
    if index is None or vname not in ds.variables:return None
    v=ds.variables[vname]
    td=ds.variables["time"].dimensions[0]
    if v.dimensions.count(td)!=1:return None
    ax=v.dimensions.index(td)
    if any(i!=ax and n!=1 for i,n in enumerate(v.shape)):return None
    selector=tuple(index if k==ax else 0 for k in range(v.ndim))
    try:
        x=np.ma.asarray(v[selector],dtype=float).filled(np.nan).reshape(-1)
        f=float(x[0])
        return f if math.isfinite(f) and f>-9990 else None
    except (TypeError,ValueError,IndexError):return None
def i_at(ds,time):
    t=ds.variables["time"]
    need("days since 1800-01-01" in t.units,
         "Unexpected original source time units in "+str(ds.filepath()))
    v=date2num(dt.datetime.fromisoformat(time),t.units,
               calendar=getattr(t,"calendar","standard"))
    a=np.ma.asarray(t[:],dtype=float).filled(np.nan).reshape(-1)
    j=int(np.searchsorted(a,v))
    cand=[k for k in (j-1,j) if 0<=k<len(a)]
    if not cand:return None
    idx=min(cand,key=lambda k:abs(a[k]-v))
    return idx if abs(a[idx]-v)*86400<1 else None
def sourcecheck():
    need(sha(L3)==L3_SHA and sha(L6)==L6_SHA,
         "Immutable original L3/L6 changed")
    r=json.loads(S22.read_text(encoding="utf-8"))
    need(r.get("science_release") is False and
         r.get("AD400_authorised") is False and
         r.get("annual_SH_exception_HH_total")==235 and
         r.get("L3_SHA256")==L3_SHA and r.get("L6_SHA256")==L6_SHA,
         "Actual Stage22 source and science-HOLD receipt changed")
def selftest():
    fake='''<catalog xmlns="http://www.unidata.ucar.edu/namespaces/thredds/InvCatalog/v1.0"><dataset name="AliceSpringsMulga_20100903T0000_to_20230308T0900_L4.nc" urlPath="ecosystem_process/ozflux/AliceSpringsMulga/2026_v3/L4/default/AliceSpringsMulga_20100903T0000_to_20230308T0900_L4.nc"/></catalog>'''
    xml=ET.fromstring(fake)
    elements=[x.attrib["urlPath"] for x in xml.iter() if
         x.tag.split("}")[-1]=="dataset" and x.attrib.get("urlPath","").startswith(PREFIX)]
    need(len(elements)==1 and elements[0].endswith("_L4.nc"),"catalogue parser")
    print("OZFLUX STAGE23 SELF-TEST PASS | exact catalog L4 discovery and immutable source gates; READ ONLY")
def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--self-test",action="store_true")
    ap.add_argument("--catalog",type=Path)
    ap.add_argument("--list",action="store_true")
    ap.add_argument("--l4",type=Path)
    ap.add_argument("--out",type=Path)
    a=ap.parse_args()
    if a.self_test:return selftest()
    need(a.catalog is not None and a.catalog.is_file() and
         not a.catalog.is_symlink(),"Requires downloaded THREDDS L4 catalog XML")
    matches=catalog_urls(a.catalog)
    print("CATALOG_SHA256",sha(a.catalog),"CANDIDATE_L4_NC",len(matches))
    for x in matches:print("OFFICIAL_EXACT_L4_URL",x["source_url"])
    need(len(matches)==1,
         "Expected exactly one matching official 2010-2023 L4. Inspect catalog manually, no invented file download.")
    if a.list:
        need(a.l4 is None and a.out is None,
             "--list only; no L4 inspection or output directory")
        print("STAGE23 L4 CATALOGUE SOURCE DISCOVERY COMPLETE, NO DOWNLOAD/SCIENCE APPROVAL")
        return
    need(a.l4 is not None and a.out is not None,
         "Provide --l4 exact downloaded NetCDF and --out")
    l4=a.l4;o=a.out
    need(l4.is_file() and not l4.is_symlink() and
         l4.name==matches[0]["filename"] and l4.stat().st_size>1000000,
         "Official exact L4 file not present or is too small")
    need(o.parent.resolve()==HOME.resolve() and not o.exists() and
         not o.is_symlink(),"Use NEW immediate HOME output directory")
    sourcecheck()
    hash4=sha(l4)
    result={"site":"AU-ASM","source_catalog_url":CATALOG,
            "source_catalog_sha256":sha(a.catalog),
            "L4_source_url":matches[0]["source_url"],
            "L4_downloaded_SHA256":hash4,
            "L4_size_bytes":l4.stat().st_size,
            "original_L3_SHA256":L3_SHA,"original_L6_SHA256":L6_SHA,
            "event_wind_can_be_independently_verified_by_L4":False,
            "L4_is_same_PyFluxPro_pipeline_not_independent_instrument":True,
            "L4_same_as_L6_does_not_verify_AWS_or_ACCESS_skill":True,
            "L4_control_file_and_bias_regression_workbook_verified":False,
            "source_END_vs_CENTER_proven":False,
            "scientific_release":False,"AD400_authorised":False,
            "no_originals_DATM_surface_CIME_Slurm_changed":True}
    with Dataset(str(l4),"r") as d4,Dataset(str(L6),"r") as d6:
        need(d4.getncattr("processing_level")=="L4",
             "Downloaded L4 processing_level not L4")
        need(d4.getncattr("time_zone")=="Australia/Darwin" and
             d6.getncattr("time_zone")=="Australia/Darwin",
             "L4 source timezone drift")
        sourcevars=set(d4.variables)
        donors=sorted(v for v in sourcevars if
                      any(z in v.lower() for z in ALTS))
        result["L4_metadata"]=gmeta(d4)
        result["L4_variable_count"]=len(sourcevars)
        result["L4_intermediate_candidate_variable_names"]=donors
        result["L4_intermediate_candidate_metadata"]={
            x:meta(d4.variables[x]) for x in donors[:120]}
        result["L4_has_donor_intermediate_series"]=len(donors)>0
        result["L4_key_event_rows"]=[]
        for label in KEYS:
            x=i_at(d4,label);y=i_at(d6,label)
            need(x is not None and y is not None,
                 "Original L4 versus L6 cannot align source native time: "+label)
            record={"native_time":label,"L4_index":x,"L6_index":y,
                    "variables":{}}
            for v in VARS:
                record["variables"][v]={
                  "L4":point(d4,v,x),"L4_QC":point(d4,v+"_QCFlag",x),
                  "L6":point(d6,v,y),"L6_QC":point(d6,v+"_QCFlag",y)}
            result["L4_key_event_rows"].append(record)
    o.mkdir(mode=0o700,parents=False,exist_ok=False)
    (o/"stage23_official_TERN_L4_donor_catalog_provenance_science_HOLD.json").write_text(
       json.dumps(result,indent=2,ensure_ascii=False),encoding="utf-8")
    print("STAGE23 EXACT L4 SHA",hash4,"SIZE",result["L4_size_bytes"])
    print("L4 SOURCE METADATA",json.dumps(result["L4_metadata"]))
    print("L4 VARIABLES",result["L4_variable_count"])
    print("L4 DONOR INTERMEDIATE CANDIDATES",json.dumps(donors))
    for row in result["L4_key_event_rows"]:
        print("EVENT",row["native_time"],json.dumps(row["variables"]))
    print("STAGE23 FULL L4 PROVENANCE READONLY PASS; FORCING SCIENCE HOLD, NO SLURM")
    print("REPORT_DIR",o)
if __name__=="__main__":main()
