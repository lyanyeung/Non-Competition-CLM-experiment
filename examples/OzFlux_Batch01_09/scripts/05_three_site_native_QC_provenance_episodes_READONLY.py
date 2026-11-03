#!/usr/bin/env python3
"""OzFlux NC Stage05: independent native L6 QC and longest episode checks.

READ ONLY: verifies Stage04/08 receipts, re-counts all seven original variable
QC flags per native source-year and extracts contiguous model-sourced runs.
No NetCDF writes, gap filling, science approval, CIME cases or Slurm jobs.
"""
from __future__ import annotations
import argparse,csv,datetime as dt,hashlib,json
from pathlib import Path
import sys
import netCDF4
import numpy as np

HOME=Path.home()
ROOT=Path("/iridisfs/scratch/ly3n24/CLM_FATES/sites/MY_EC_SITE")
SITES={
    "AU-ASM":("AliceSpringsMulga1_20100903T0000_to_20230308T0900_L6.nc",2013,2018),
    "AU-DaS":("DalyUncleared_20080101T0000_to_20260423T0000_L6.nc",2009,2021),
    "AU-Dry":("DryRiver_L6.nc",2010,2018)}
VARS=("Ta","SH","ps","Fsd","Fld","Ws","Precip")
CODES=(0,10,50,410,420,430,440)
QC_MAP={"410":"AWS","420":"ACCESS","430":"ERA-Interim","440":"ERA5"}
YEAR_COLUMNS=("site","year","variable","records","qc0_pct","qc50","qc410",
              "qc420","qc430","qc440","other_qc","qc_unavailable")
RUN_COLUMNS=("site","variable","class","first_native","last_native",
             "records","hours","start_index","end_index")

def regular(p):
    if p.is_symlink() or not p.is_file():
        raise ValueError("Missing original regular file, or symlink: "+str(p))
    return p

def sha(p):
    h=hashlib.sha256()
    with regular(p).open("rb") as f:
        for block in iter(lambda:f.read(4*1024*1024),b""):
            h.update(block)
    return h.hexdigest()

def table(p):
    with regular(p).open(encoding="utf-8-sig",newline="") as f:
        return list(csv.DictReader(f,delimiter="\t"))

def write_tsv(p,columns,rows):
    with p.open("x",encoding="utf-8",newline="") as f:
        w=csv.DictWriter(f,fieldnames=columns,delimiter="\t",extrasaction="raise")
        w.writeheader();w.writerows(rows)

def units_seconds(units):
    return {"days":86400,"day":86400,"hours":3600,"hour":3600,
            "minutes":60,"minute":60,"seconds":1,"second":1}[
            units.lower().split(" since ",1)[0].strip()]

def time_bound(t,year):
    return float(netCDF4.date2num(dt.datetime(year,1,1),t.units,
                       calendar=getattr(t,"calendar","standard")))

def time_label(t,values,index):
    return str(netCDF4.num2date(float(values[index]),t.units,
                       calendar=getattr(t,"calendar","standard")))

def contiguous(mask):
    x=np.asarray(mask,dtype=bool)
    if x.ndim!=1:raise ValueError("non-1D QC mask")
    cuts=np.flatnonzero(np.diff(np.r_[False,x,False].astype(np.int8)))
    return [(int(a),int(b)) for a,b in zip(cuts[::2],cuts[1::2])]

def count_codes(q):
    finite=np.isfinite(q);known=np.zeros(len(q),dtype=bool);out={}
    for code in CODES:
        k=finite&(q==code)
        out[str(code)]=int(k.sum());known|=k
    out["other"]=int((finite&(~known)).sum())
    out["unavailable"]=int((~finite).sum())
    assert sum(out.values())==len(q)
    return out

def evidence(stage04,stage08):
    report=json.loads(regular(stage04/"ozflux_nc_stage04_nine_site_forcing_handoff.json").read_text())
    if (report.get("all_nine_surface_candidates_exist") is not True
        or report.get("AD400_authorised") is not False
        or report.get("DATM_climate_streams_approved") is not False
        or report.get("AU_ASM_FSDS0_years_source_SHA_verified")!=list(range(2013,2019))):
        raise ValueError("Stage04 full SUCCESS / science HOLD guard missing")
    pinned=report["year_QC_provenance_SHA"]
    for key,file in (("Stage08_year_reason_ledger_SHA256","stage08_year_reason_ledger.tsv"),
                     ("Stage08_contiguous_blocks_SHA256","stage08_contiguous_candidate_blocks.tsv"),
                     ("Stage08_review_summary_SHA256","stage08_review_summary.json")):
        if sha(stage08/file)!=pinned[key]:
            raise ValueError("Stage08 source receipt changed: "+key)
    summary=json.loads(regular(stage08/"stage08_review_summary.json").read_text())
    if (summary["native_year_rows"],summary["structural_candidate_years"],
        summary["review_hold_years"])!=(169,67,102):
        raise ValueError("Unexpected Stage08 year status counts")
    indexed={}
    for row in table(stage08/"stage08_source_qc_per_year.tsv"):
        key=(row["site"],row["filename"],int(row["year"]),row["variable"])
        if key in indexed:raise ValueError("Duplicate Stage08 QC variable-year key")
        indexed[key]=row
    return indexed

def compare(q,ref,site,year,var):
    counts=count_codes(q)
    columns={"records":len(q),"native_qc0":counts["0"],
             "native_qc10":counts["10"],"native_qc50":counts["50"],
             "native_qc410":counts["410"],"native_qc420":counts["420"],
             "native_qc430":counts["430"],"native_qc440":counts["440"],
             "other_qc":counts["other"],"qc_not_available":counts["unavailable"]}
    for key,actual in columns.items():
        if int(ref[key])!=actual:
            raise ValueError(f"NATIVE QC != STAGE08 {site} {year} {var} "
                             f"{key}: native={actual} stage08={ref[key]}")
    return counts

def read_native_qc(ds,name,time_dim,total,start,end):
    """Read original numeric QCFlag using the exact Stage07 singleton-axis rule.

    Exactly one time axis, full source time length, and every other axis
    singleton. Slice on the actual time axis and flatten only after checks.
    """
    if name not in ds.variables:
        raise ValueError("Original QC variable missing: "+name)
    v=ds.variables[name]
    if (not np.issubdtype(v.dtype,np.number)
        or v.dimensions.count(time_dim)!=1):
        raise ValueError("Original QC numeric/time dimension invalid: "+
                         name+" dims="+repr(v.dimensions))
    idx=v.dimensions.index(time_dim)
    if (v.shape[idx]!=total
        or any(size!=1 for j,size in enumerate(v.shape) if j!=idx)):
        raise ValueError("Original QC time length/non-singleton shape: "+
                         name+" shape="+repr(v.shape))
    selector=tuple(slice(start,end) if j==idx else slice(None)
                   for j in range(v.ndim))
    q=np.ma.asarray(v[selector],dtype=np.float64).filled(np.nan).reshape(-1)
    if len(q)!=end-start:
        raise ValueError("Original QC slice length mismatch: "+name)
    return q


def inspect(site,filename,y0,y1,source,index):
    yearly=[];episodes=[];episode_counts={};metadata={}
    with netCDF4.Dataset(str(source),mode="r") as ds:
        t=ds.variables["time"]
        if t.ndim!=1:raise ValueError(site+" source time axis not 1-D")
        time_dim=t.dimensions[0]
        native=np.ma.asarray(t[:],dtype=np.float64).filled(np.nan).reshape(-1)
        if len(native)<2 or not np.isfinite(native).all() or not np.all(np.diff(native)>0):
            raise ValueError(site+" invalid original time")
        step=float(np.median(np.diff(native)))*units_seconds(str(t.units))
        if abs(step-1800)>1:raise ValueError(site+" source is not half-hourly")
        lo=int(np.searchsorted(native,time_bound(t,y0),"left"))
        hi=int(np.searchsorted(native,time_bound(t,y1+1),"left"))
        if lo>=hi:raise ValueError(site+" missing selected original years")
        selected=native[lo:hi]
        if not np.allclose(np.diff(selected)*units_seconds(str(t.units)),step,rtol=0,atol=1):
            raise ValueError(site+" irregular selected original interval")
        metadata={"filename":filename,"native_years":f"{y0}-{y1}",
                  "source_SHA256":sha(source),
                  "time_units":str(t.units),"interval_seconds":step,
                  "native_first":time_label(t,native,lo),
                  "native_last":time_label(t,native,hi-1)}
        for var in VARS:
            key=var+"_QCFlag"
            q=read_native_qc(ds,key,time_dim,len(native),lo,hi)
            for year in range(y0,y1+1):
                start=int(np.searchsorted(selected,time_bound(t,year),"left"))
                end=int(np.searchsorted(selected,time_bound(t,year+1),"left"))
                k=(site,filename,year,var)
                if k not in index:raise ValueError("Stage08 variable-year missing "+str(k))
                d=compare(q[start:end],index[k],site,year,var)
                yearly.append({"site":site,"year":year,"variable":var,
                               "records":end-start,
                               "qc0_pct":round(100*d["0"]/(end-start),4),
                               "qc50":d["50"],"qc410":d["410"],"qc420":d["420"],
                               "qc430":d["430"],"qc440":d["440"],
                               "other_qc":d["other"],"qc_unavailable":d["unavailable"]})
            classes={"ACCESS_420":q==420,"ERA5_440":q==440,
                     "ACCESS_OR_ERA5":np.isin(q,(420,440)),
                     "INTERPOLATION_50":q==50,
                     "ANY_NON_QC0":(~np.isfinite(q))|(q!=0)}
            for category,mask in classes.items():
                spans=contiguous(mask)
                episode_counts[f"{var}/{category}"]=len(spans)
                for start,end in sorted(spans,key=lambda z:(-(z[1]-z[0]),z[0]))[:20]:
                    episodes.append({"site":site,"variable":var,"class":category,
                                     "first_native":time_label(t,native,lo+start),
                                     "last_native":time_label(t,native,lo+end-1),
                                     "records":end-start,"hours":(end-start)*step/3600,
                                     "start_index":lo+start,"end_index":lo+end-1})
    metadata["full_episode_counts"]=episode_counts
    return yearly,episodes,metadata

def selftest():
    assert contiguous([False,True,True,False,True])==[(1,3),(4,5)]
    assert contiguous([])==[] and contiguous([True,True])==[(0,2)]
    assert count_codes(np.array([0,0,50,410,420,440,470,np.nan]))=={
        "0":2,"10":0,"50":1,"410":1,"420":1,"430":0,"440":1,
        "other":1,"unavailable":1}
    class FakeVar:
        def __init__(self,arr,dims):
            self.data=np.asarray(arr)
            self.dimensions=tuple(dims)
            self.shape=self.data.shape
            self.dtype=self.data.dtype
            self.ndim=self.data.ndim
        def __getitem__(self,item):
            return self.data[item]
    class FakeDS:
        def __init__(self,v):self.variables={"Ta_QCFlag":v}
    sample=np.array([0,10,420,440,0,50])
    shapes=((sample,("time",)),(sample.reshape(6,1),("time","x")),
            (sample.reshape(1,6,1),("lat","time","lon")),
            (sample.reshape(1,1,6),("lat","lon","time")))
    for arr,dims in shapes:
        q=read_native_qc(FakeDS(FakeVar(arr,dims)),
                         "Ta_QCFlag","time",6,1,5)
        assert np.array_equal(q,sample[1:5])
    for arr,dims in ((np.zeros((6,2)),("time","x")),
                     (np.zeros((6,)),("other",)),
                     (np.zeros((6,6)),("time","time"))):
        try:
            read_native_qc(FakeDS(FakeVar(arr,dims)),
                           "Ta_QCFlag","time",6,0,6)
        except ValueError:
            pass
        else:
            raise AssertionError("Non-singleton/missing/repeated time axis accepted")
    print("OZFLUX STAGE05 SELF-TEST PASS | Stage07 singleton QC dimensions, native counts & episodes; READ ONLY")

def main():
    if sys.argv[1:]==["--self-test"]:return selftest()
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--stage04",required=True,type=Path)
    ap.add_argument("--stage08",required=True,type=Path)
    ap.add_argument("--out",required=True,type=Path)
    ap.add_argument("--root",type=Path,default=ROOT)
    a=ap.parse_args()
    out=a.out.resolve()
    if a.out.is_symlink() or out.exists() or out.parent!=HOME.resolve():
        raise ValueError("Report path must be unused direct HOME directory")
    index=evidence(a.stage04,a.stage08)
    yr=[];ep=[];meta={}
    for site,(filename,y0,y1) in SITES.items():
        path=regular(a.root/site/"forcing"/"raw"/filename)
        rows,episodes,m=inspect(site,filename,y0,y1,path,index)
        yr.extend(rows);ep.extend(episodes);meta[site]=m
        model=[x for x in episodes if x["class"]=="ACCESS_OR_ERA5"]
        print("SITE",site,"NATIVE_QC_RECONCILED",len(rows),
              "LONGEST_ACCESS_OR_ERA5_HOURS",
              max((x["hours"] for x in model),default=0.0))
    if len(yr)!=196:raise AssertionError("Expected 6+13+9 source years x7 variables")
    ep.sort(key=lambda x:(-x["records"],x["site"],x["variable"]))
    out.mkdir(mode=0o700,parents=False,exist_ok=False)
    write_tsv(out/"stage05_three_site_year_variable_QC.tsv",YEAR_COLUMNS,yr)
    write_tsv(out/"stage05_three_site_longest_QC_episodes.tsv",RUN_COLUMNS,ep)
    report={"stage":"OzFlux NC Stage05 native QC provenance, read only",
            "source_L6_unchanged":True,"stage04_receipts_verified":True,
            "stage08_196_variable_years_reconciled":True,
            "native_source_metadata":meta,
            "top_episodes":ep[:20],
            "full_run_counts_in_source_metadata":True,
            "only_top_20_per_variable_and_category_written":True,
            "standard_PyFluxPro_source_flag_map":QC_MAP,
            "AU_DaS_885_SH_events_prior_science_HOLD":True,
            "clock_DATM_streams_science_approved":False,
            "AD5_authorised":False,"AD400_authorised":False,
            "next":"Review contiguous source-filled periods; original clock, NOLEAP, precip units, ZBOT, humidity and CIME stream gates independently"}
    (out/"stage05_three_site_priority_summary.json").write_text(
        json.dumps(report,indent=2,ensure_ascii=False),encoding="utf-8")
    for r in ep[:15]:
        print("EPISODE",r["site"],r["variable"],r["class"],
              r["first_native"],r["last_native"],r["hours"],"hours")
    print("STAGE05 READONLY THREE SITE SOURCE-QC RECONCILIATION PASS")
    print("NO DATM, SOURCE, SURFACE, CASE OR SLURM WRITES; NO AD5/AD400 APPROVAL")
    print("REPORT_DIR",out)

if __name__=="__main__":main()
