#!/usr/bin/env python3
"""OzFlux NC AU-ASM Stage12: independent-looking source evidence review, READ ONLY.

Re-evaluate native 2018-03-10 20:30 wind QC0 spike, QC410 AWS-meteorology
intervals and QC420/440 radiation replacements, with full 7-variable context,
source variable/clock metadata and candidate donor inventory. Do not equate
a matching name or QC0 with an independently verified sensor. No netCDF/model
source, PFT surface, case, Slurm or GitHub edits; report only.
"""
from __future__ import annotations
import argparse,csv,datetime as dt,hashlib,json,math,sys
from collections import Counter
from pathlib import Path
import numpy as np
from netCDF4 import Dataset,date2num,num2date

HOME=Path.home()
SRC=Path("/iridisfs/scratch/ly3n24/CLM_FATES/sites/MY_EC_SITE/AU-ASM/forcing/raw/AliceSpringsMulga1_20100903T0000_to_20230308T0900_L6.nc")
SRC_SHA="b9381c4ed0744d03ae609cfbf3805e30bbb9223851a05f4e5b63b149dd0b10eb"
S11=HOME/"ozflux_nc_stage11_20261103T073019Z"/"stage11_AU_ASM_SOURCE_SCIENCE_HOLD.json"
FIELDS=("Ta","SH","ps","Fsd","Fld","Ws","Precip")
HALF_HOUR_FIELDS=("native_label","offset_halfhours","Ta","Ta_QCFlag","SH","SH_QCFlag",
   "ps","ps_QCFlag","Fsd","Fsd_QCFlag","Fld","Fld_QCFlag",
   "Ws","Ws_QCFlag","Precip","Precip_QCFlag","other_sensor_json")
SPIKE_FIELDS=("native_label","wind_ms","wind_QCFlag","prior_ms","next_ms",
              "local_neighbor_median_ms","isolated_excess_ms","ratio_to_neighbors",
              "delta_prev_ms","delta_next_ms","isolation_review_only")
JOIN_FIELDS=("event","start_native","end_native","hours","source_QCFlag_by_var",
             "pre_Ta","at_Ta","post_Ta","jump_entry_Ta","jump_exit_Ta",
             "pre_Ws","at_Ws","post_Ws","jump_entry_Ws","jump_exit_Ws",
             "pre_Fld","at_Fld","post_Fld","jump_entry_Fld","jump_exit_Fld")
def need(flag,msg):
    if not flag:raise ValueError(str(msg))

def sha(p):
    need(p.is_file() and not p.is_symlink(),"Missing immutable source "+str(p))
    h=hashlib.sha256()
    with p.open("rb") as f:
        for block in iter(lambda:f.read(4*1024*1024),b""):h.update(block)
    return h.hexdigest()

def arr(v):
    a=np.ma.asarray(v[:],dtype=float).filled(np.nan).ravel()
    return a

def label(t,x):
    z=num2date(float(x),t.units,calendar=getattr(t,"calendar","standard"))
    return f"{z.year:04d}-{z.month:02d}-{z.day:02d} {z.hour:02d}:{z.minute:02d}:{z.second:02d}"

def index(t,alltime,s):
    x=date2num(dt.datetime.fromisoformat(s),t.units,calendar=getattr(t,"calendar","standard"))
    j=int(np.searchsorted(alltime,x))
    need(j<len(alltime) and abs(alltime[j]-x)<1e-7,"Source native label not found "+s)
    return j

def scalar(x):return float(x) if np.isfinite(x) else None
def jump(x,a,b):
    if min(a,b)<0 or max(a,b)>=len(x):return None
    if not np.isfinite(x[a]) or not np.isfinite(x[b]):return None
    return float(x[b]-x[a])
def cols_write(p,columns,rows):
    with p.open("x",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=columns,extrasaction="raise",delimiter="\t")
        w.writeheader();w.writerows(rows)
def meta(v):
    result={}
    for name in ("units","long_name","height","instrument","statistic_type",
                 "source","description_L2","description_L3","description_L4",
                 "description_L5","description_L6"):
        if name in v.ncattrs():
            val=v.getncattr(name)
            if hasattr(val,"tolist"):val=val.tolist()
            result[name]=str(val)[:1200]
    return result
def maybe_time(v,td,n,a,b):
    if not np.issubdtype(v.dtype,np.number) or v.dimensions.count(td)!=1:
        return None
    pos=v.dimensions.index(td)
    if v.shape[pos]!=n or any(k!=pos and v.shape[k]!=1 for k in range(v.ndim)):
        return None
    sel=tuple(slice(a,b) if k==pos else slice(None) for k in range(v.ndim))
    data=np.ma.asarray(v[sel],dtype=float).filled(np.nan).ravel()
    return data if len(data)==b-a else None
def source_data(ds,td,n,a,b):
    data={}
    for v in FIELDS:
        need(v in ds.variables and v+"_QCFlag" in ds.variables,
             "Missing original L6 field "+v)
        x=maybe_time(ds.variables[v],td,n,a,b)
        q=maybe_time(ds.variables[v+"_QCFlag"],td,n,a,b)
        need(x is not None and q is not None,"source field not scalar halfhour "+v)
        data[v]=(x,q)
    return data

def scope(ds,t,alltime,start,end):
    a=index(t,alltime,start);b=index(t,alltime,end)
    need(b>a,"Invalid source scope")
    return a,b
def runs(mask):
    a=np.asarray(mask,bool)
    cuts=np.flatnonzero(np.diff(np.r_[False,a,False].astype(np.int8)))
    return [(int(i),int(j)) for i,j in zip(cuts[::2],cuts[1::2])]

def build_other_sensor_inventory(ds,td,n,a,b,i):
    # Catalog rather than assume donor independence or even that "Ws_" exists.
    candidates={}
    for name,v in ds.variables.items():
        low=name.lower()
        if not (name.startswith("Ws_") or "gust" in low or "wind" in low
           or name.startswith("Wd") or name.startswith("Ta_") or name.startswith("Fld_")
           or "aws" in low or "access" in low):
            continue
        if name in FIELDS or name.endswith("_QCFlag") or name in
                ("Ws_QCFlag","Ta_QCFlag","Fld_QCFlag"):continue
        if len(candidates)>=90:break
        x=maybe_time(v,td,n,a,b)
        if x is None:continue
        candidates[name]={"at_wind_peak":scalar(x[i]),"metadata":meta(v),
                 "nonfinite_or_missing":int(np.sum(~np.isfinite(x)|(x<=-9990))),
                 "does_NOT_imply_independent_sensor":True}
    return candidates

def main():
    if sys.argv[1:]==["--self-test"]:
        need(runs([False,True,True,False,True])==[(1,3),(4,5)],"QC run split")
        print("AU-ASM STAGE12 SELF TEST PASS | original wind + AWS/ACCESS source science HOLD")
        return
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out",type=Path,required=True)
    o=ap.parse_args().out
    need(not o.exists() and not o.is_symlink() and o.parent.resolve()==HOME.resolve(),
         "Reports must be an unused immediate HOME directory")
    need(sha(SRC)==SRC_SHA,"AU-ASM original L6 SHA256 changed")
    need(S11.is_file(),"Expected Stage11 operator receipt missing")
    old=json.loads(S11.read_text(encoding="utf-8"))
    need(old.get("science_release") is False and old.get("AD400_authorised") is False
        and old["2018_peak_wind"]["value"]==16.29613
        and old["2018_peak_wind"]["source_QCFlag"]==0.0
        and old["2018_87p5hour_joint_episode"]["hours"]==87.5,
         "Stage11 original operator evidence mismatch")
    with Dataset(str(SRC),"r") as ds:
        t=ds.variables["time"]
        native=arr(t)
        need(t.ndim==1 and np.isfinite(native).all() and np.all(np.diff(native)>0),
             "Native source time invalid")
        a=index(t,native,"2013-01-01 00:00:00")
        b=index(t,native,"2019-01-01 00:00:00")
        need(b-a==105168,"Six native source years mismatch")
        vals=source_data(ds,t.dimensions[0],len(native),a,b)
        time=native[a:b]
        ip=index(t,native,"2018-03-10 20:30:00")-a
        w,q=vals["Ws"]
        need(abs(w[ip]-16.29613)<1e-6 and q[ip]==0.0,
             "Original QC0 2018 wind spike differs")
        neighbor=np.r_[w[ip-8:ip],w[ip+1:ip+9]]
        valid=neighbor[np.isfinite(neighbor)]
        med=float(np.median(valid))
        spike={"source_label":label(t,time[ip]),"wind_peak_ms":float(w[ip]),
               "native_QCFlag":float(q[ip]),"neighbor_4h_median_ms":med,
               "ratio_to_neighbor_median":float(w[ip]/med),
               "delta_prior_ms":float(w[ip]-w[ip-1]),
               "delta_next_ms":float(w[ip+1]-w[ip]),
               "QC0_can_be_outlier":True,
               "statistic_type":meta(ds.variables["Ws"]).get("statistic_type","NOT_DECLARED")}
        # Top isolated high-QC0 source wind points across all six years.
        records=[]
        for i in range(8,len(w)-8):
            if q[i]!=0 or not np.isfinite(w[i]):continue
            nei=np.r_[w[i-8:i],w[i+1:i+9]]
            use=nei[np.isfinite(nei)&(nei>-9990)]
            if len(use)<12:continue
            local=float(np.median(use))
            if local<=0 or w[i]-local<6 or w[i]/local<2.5:continue
            records.append({
              "native_label":label(t,time[i]),"wind_ms":float(w[i]),
              "wind_QCFlag":float(q[i]),"prior_ms":scalar(w[i-1]),
              "next_ms":scalar(w[i+1]),
              "local_neighbor_median_ms":local,
              "isolated_excess_ms":float(w[i]-local),
              "ratio_to_neighbors":float(w[i]/local),
              "delta_prev_ms":jump(w,i-1,i),
              "delta_next_ms":jump(w,i,i+1),
              "isolation_review_only":True})
        records.sort(key=lambda r:-r["isolated_excess_ms"])
        # Events: source labels and raw all-seven-field boundaries.
        specs=[
            ("2017_FLD_ACCESS", "Fld","2017-08-17 22:00:00","2017-09-03 08:30:00",420),
            ("2018_JOINT_AWS_87H", "Ta","2018-06-09 18:00:00","2018-06-13 09:00:00",410),
            ("2014_PS_ALT_96H", "ps","2014-08-26 17:30:00","2014-08-30 17:00:00",None)
        ]
        joints=[];windows=[]
        donor=build_other_sensor_inventory(ds,t.dimensions[0],len(native),a,b,ip)
        for en,var,begin,end,code in specs:
            ia=index(t,native,begin)-a
            ib=index(t,native,end)-a+1
            need(ib>ia,"Event chronology "+en)
            if code is not None:
                need(np.all(vals[var][1][ia:ib]==code),
                     "Reported native QC does not match "+en)
            qc_by={}
            for k in FIELDS:
                hist=Counter(int(v) for v in vals[k][1][ia:ib] if np.isfinite(v))
                qc_by[k]={str(c):int(n) for c,n in sorted(hist.items())}
            event={"event":en,"start_native":begin,"end_native":end,
                   "hours":(ib-ia)*.5,"source_QCFlag_by_var":json.dumps(qc_by,sort_keys=True)}
            for k in ("Ta","Ws","Fld"):
                x=vals[k][0]
                event["pre_"+k]=scalar(x[ia-1]) if ia else None
                event["at_"+k]=scalar(x[ia])
                event["post_"+k]=scalar(x[ib]) if ib<len(x) else None
                event["jump_entry_"+k]=jump(x,ia-1,ia)
                event["jump_exit_"+k]=jump(x,ib-1,ib)
            joints.append(event)
            for name,anchor in ((en+"_ENTRY",ia),(en+"_EXIT",ib)):
                for i in range(max(0,anchor-8),min(len(time),anchor+9)):
                    row={"native_label":label(t,time[i]),"offset_halfhours":i-anchor,
                         "other_sensor_json":json.dumps(
                          {k:v["at_wind_peak"] for k,v in donor.items()} if en=="WIND_PEAK" else {},
                          sort_keys=True)}
                    for k in FIELDS:
                        row[k]=scalar(vals[k][0][i])
                        row[k+"_QCFlag"]=scalar(vals[k][1][i])
                    windows.append(row)
        for i in range(max(0,ip-8),min(len(time),ip+9)):
            row={"native_label":label(t,time[i]),"offset_halfhours":i-ip,
                 "other_sensor_json":json.dumps(
                    {k:v["at_wind_peak"] if i==ip else None for k,v in donor.items()},
                    sort_keys=True)}
            for k in FIELDS:
                row[k]=scalar(vals[k][0][i]);row[k+"_QCFlag"]=scalar(vals[k][1][i])
            windows.append(row)
        global_meta={k:str(ds.getncattr(k))[:600] for k in ds.ncattrs()
                     if any(n in k.lower() for n in ("time","zone","interval","site","instrument","description"))}
        windmeta=meta(ds.variables["Ws"])
        # Derive the 2018 AWS span from native QC rather than hard-coding
        # a gap-fill donor identity or approving it from its flag code.
        y0=index(t,native,"2018-01-01 00:00:00")-a
        y1=index(t,native,"2019-01-01 00:00:00")-a
        aws={k:{"n_410":int(np.sum(vals[k][1][y0:y1]==410)),
                "n_qc0":int(np.sum(vals[k][1][y0:y1]==0))} for k in FIELDS}
        need(aws["Ws"]["n_410"]==1416 and aws["Precip"]["n_410"]==1425
             and aws["Fsd"]["n_410"]==0,
             "2018 original PyFluxPro provenance codes changed")
        q2018=vals["Ws"][1][y0:y1]
        fillwind=vals["Ws"][0][y0:y1]
        aws_wind=fillwind[q2018==410]
        orig_wind=fillwind[q2018==0]
        metadata={"raw_L6_SHA256":SRC_SHA,"source_time_units":t.units,
                  "time_calendar":getattr(t,"calendar","standard"),
                  "native_clock_scientifically_certified":False,
                  "time_related_global_attributes":global_meta,
                  "Ws_metadata":windmeta,
                  "possible_wind_or_alternate_donor_variable_catalogue":donor,
                  "source_2018_original_QC410_counts":aws,
                  "2018_Ws_QC410_source_distribution":{
                    "mean":float(np.nanmean(aws_wind)),"median":float(np.nanmedian(aws_wind)),
                    "max":float(np.nanmax(aws_wind))},
                  "2018_Ws_QC0_source_distribution":{
                    "mean":float(np.nanmean(orig_wind)),"median":float(np.nanmedian(orig_wind)),
                    "max":float(np.nanmax(orig_wind))},
                  "2018_single_point_wind_outlier_diagnostic":spike,
                  "six_year_isolated_QC0_wind_review_count":len(records),
                  "source_forcing_errors_confirmed":False,
                  "science_release":False,"AD400_authorised":False,
                  "no_Slurm_CIME_Surface_forcing_writes":True}
    o.mkdir(mode=0o700,parents=False,exist_ok=False)
    cols_write(o/"stage12_native_all7_met_event_boundaries.tsv",HALF_HOUR_FIELDS,windows)
    cols_write(o/"stage12_original_QC0_wind_isolated_candidate_review.tsv",
               SPIKE_FIELDS,records)
    cols_write(o/"stage12_original_long_model_fill_source_joins.tsv",JOIN_FIELDS,joints)
    (o/"stage12_native_sensor_time_AWS_ACCESS_science_HOLD.json").write_text(
        json.dumps(metadata,indent=2,ensure_ascii=False),encoding="utf-8")
    print("AU-ASM STAGE12 ORIGINAL L6 SOURCE SHA VERIFIED")
    print("WIND PEAK",json.dumps(spike))
    print("ISOLATED SIX-YEAR QC0 WIND CANDIDATES",len(records))
    print("2018 AWS SOURCE QC COUNTS",json.dumps(aws))
    for r in joints:print("EVENT",r["event"],r["hours"],"hours",r["source_QCFlag_by_var"][:250])
    print("ALTERNATE/WIND VARIABLE CATALOGUE",list(donor))
    print("SCIENCE HOLD; AD400_NOT_AUTHORISED; NO FORCING/SURFACE/CIME/SLURM WRITES")
    print("REPORT_DIR",o)
if __name__=="__main__":main()
