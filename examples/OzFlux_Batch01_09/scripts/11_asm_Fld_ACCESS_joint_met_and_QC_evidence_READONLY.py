#!/usr/bin/env python3
"""AU-ASM Stage11 original native meteorology science forensic; READ ONLY.

Selected L6 data only. Test 2017 395-hour Fld ACCESS vs surrounding QC0
meteorology, 2018 shared 5-variable non-QC0 provenance, pressure model-fill
boundary, 2018 peak wind context and annual 2018 full QCFlag breakdown.
A source model replacement is not automatically an error, a plausible
boundary is not proof, and no science release/AD400 follows automatically.
No candidate, source, CIME, GitHub Surface or Slurm mutations.
"""
from __future__ import annotations
import argparse, csv, datetime as dt, hashlib, json, sys
from collections import Counter
from pathlib import Path
import numpy as np
from netCDF4 import Dataset,date2num,num2date

HOME=Path.home()
SRC=Path("/iridisfs/scratch/ly3n24/CLM_FATES/sites/MY_EC_SITE/AU-ASM/forcing/raw/AliceSpringsMulga1_20100903T0000_to_20230308T0900_L6.nc")
SHA="b9381c4ed0744d03ae609cfbf3805e30bbb9223851a05f4e5b63b149dd0b10eb"
S09=HOME/"ozflux_nc_stage09_20261103T070958Z"
S10=HOME/"ozflux_nc_stage10_20261103T072400Z"
VARS=("Ta","SH","ps","Fsd","Fld","Ws","Precip")
CODES=(0,10,50,400,410,420,430,440)
B_FIELDS=["focus","native_source_time","offset_HH","Ta","Ta_QCFlag","SH","SH_QCFlag",
          "ps","ps_QCFlag","Fsd","Fsd_QCFlag","Fld","Fld_QCFlag",
          "Ws","Ws_QCFlag","Precip","Precip_QCFlag"]
J_FIELDS=["start_native","end_native","hours","rows","distinct_QCFlag_by_variable",
          "entry_jump_Ta_C","exit_jump_Ta_C","entry_jump_SH_kgkg",
          "exit_jump_SH_kgkg","entry_jump_ps_kPa","exit_jump_ps_kPa",
          "entry_jump_Ws_mps","exit_jump_Ws_mps"]
def need(c,s):
    if not c:raise ValueError(str(s))
def digest(p):
    need(p.is_file() and not p.is_symlink(),"Missing original file "+str(p))
    h=hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda:f.read(4<<20),b""):h.update(b)
    return h.hexdigest()
def report(p):
    need(p.is_file() and not p.is_symlink(),"Missing actual Stage09/10 report "+str(p))
    return json.loads(p.read_text())
def arr(v):
    a=np.ma.asarray(v[:],dtype=float).filled(np.nan).reshape(-1)
    return a
def qc_hist(x):
    counts={str(k):int(np.sum(x==k)) for k in CODES}
    counts["QC_other"]=int(np.sum(np.isfinite(x)&~np.isin(x,CODES)))
    counts["QC_missing"]=int(np.sum(~np.isfinite(x)))
    need(sum(counts.values())==len(x),"QC histogram did not close")
    return counts
def spans(a):
    x=np.asarray(a,bool)
    edges=np.flatnonzero(np.diff(np.r_[False,x,False].astype("i1")))
    return list(zip(edges[::2].tolist(),edges[1::2].tolist()))
def ts(v,x):
    z=num2date(float(x),v.units,calendar=getattr(v,"calendar","standard"))
    return f"{z.year:04d}-{z.month:02d}-{z.day:02d} {z.hour:02d}:{z.minute:02d}:{z.second:02d}"
def at(v,label,x):
    n=date2num(dt.datetime.fromisoformat(label),v.units,calendar=getattr(v,"calendar","standard"))
    ix=int(np.searchsorted(x,n))
    need(ix<len(x) and abs(x[ix]-n)<1e-7,"Source native time missing "+label)
    return ix
def fmt(x):return float(x) if np.isfinite(x) else None
def stats(a):
    x=np.asarray(a,dtype=float)
    x=x[np.isfinite(x)&(x>-9990)]
    if not len(x):return {"n":0}
    return {"n":int(len(x)),"min":float(x.min()),"p05":float(np.percentile(x,5)),
            "median":float(np.median(x)),"mean":float(x.mean()),
            "p95":float(np.percentile(x,95)),"max":float(x.max()),
            "std":float(np.std(x))}
def write_tsv(path,fields,rows):
    with path.open("x",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=fields,delimiter="\t",extrasaction="raise")
        w.writeheader();w.writerows(rows)
def context(name,indices,t,time,values,qcs,center):
    rows=[]
    for k in indices:
        row={"focus":name,"native_source_time":ts(t,time[k]),
             "offset_HH":k-center}
        for v in VARS:
            row[v]=fmt(values[v][k]);row[v+"_QCFlag"]=fmt(qcs[v][k])
        rows.append(row)
    return rows
def jump(values,var,left,right):
    z=values[var]
    if min(left,right)<0 or max(left,right)>=len(z):return None
    if not (np.isfinite(z[left]) and np.isfinite(z[right])):return None
    return float(z[right]-z[left])
def selftest():
    need(spans([False,True,True,False,True])==[(1,3),(4,5)],"spans")
    h=qc_hist(np.array([0,0,50,420,440,400,410,430,10,np.nan,7]))
    need(sum(h.values())==11 and h["QC_other"]==1,"QC codes")
    print("OZFLUX STAGE11 SELF-TEST PASS; read-only multivariate QC and source context")
def main():
    if sys.argv[1:]==["--self-test"]:return selftest()
    p=argparse.ArgumentParser();p.add_argument("--out",type=Path,required=True)
    args=p.parse_args();out=args.out
    need(not out.exists() and not out.is_symlink() and out.parent.resolve()==HOME.resolve(),
         "Output must be unused direct HOME child")
    need(digest(SRC)==SHA,"Native AU-ASM L6 source SHA drift")
    s09=report(S09/"stage09_FORCING_SCIENCE_HOLD.json")
    s10=report(S10/"stage10_AU_ASM_SCIENCE_REVIEW_HOLD.json")
    need(s09["status"]=="FORCING_SCIENCE_HOLD" and s09["science_release"] is False
         and s09["AD400_authorised"] is False
         and s09["year_variable_reconciled"]==42
         and s09["2017_395h_Fld_ACCESS_source_reproduced"] is True
         and s10["source_events_inherited"]==1860
         and s10["priority_high"]==3 and s10["science_release"] is False,
         "Stage09/10 original QC evidence changed")
    with Dataset(str(SRC),"r") as ds:
        t=ds.variables["time"];time=arr(t)
        need(t.ndim==1 and np.all(np.isfinite(time)) and np.all(np.diff(time)>0),
             "Native source clock invalid")
        n=len(time)
        values={};qc={}
        for var in VARS:
            values[var]=arr(ds.variables[var])
            qc[var]=arr(ds.variables[var+"_QCFlag"])
            need(len(values[var])==n and len(qc[var])==n,"source field size "+var)
        begin=at(t,"2013-01-01 00:00:00",time)
        end=at(t,"2019-01-01 00:00:00",time)
        need(end-begin==105168,"2013-18 6y source scope changed")
        a=at(t,"2017-08-17 22:00:00",time)
        b=at(t,"2017-09-03 08:30:00",time)+1
        need(b-a==790 and np.all(qc["Fld"][a:b]==420),
             "2017 original contiguous 395h ACCESS not reproduced")
        a18=at(t,"2018-01-01 00:00:00",time)
        b18=at(t,"2019-01-01 00:00:00",time)
        original_2018={var:qc_hist(qc[var][a18:b18]) for var in VARS}
        annual={var:{"N":b18-a18,"QC0_percent":
            round(100*original_2018[var]["0"]/(b18-a18),5),
            "QC_by_exact_PyFluxPro_flag":original_2018[var]} for var in VARS}
        # 2017 Fld model-filled interval versus 30-day shoulders restricted to
        # QC0. This is climate-context comparison, NOT actual validation of fill.
        shoulder=30*48
        left=np.arange(max(begin,a-shoulder),a,dtype=int)
        right=np.arange(b,min(end,b+shoulder),dtype=int)
        controls=np.r_[left,right]
        controls=controls[(qc["Fld"][controls]==0)&
                          np.isfinite(values["Fld"][controls])]
        sigma=5.670374419e-8
        def emissivity(ids):
            T=values["Ta"][ids]+273.15
            return values["Fld"][ids]/(sigma*T**4)
        filled=np.arange(a,b,dtype=int)
        cloud=values["Fsd"][filled]
        fld_obs_baseline={
           "modeled_2017_ACCESS_395h_Fld_Wm2":stats(values["Fld"][filled]),
           "QC0_observed_class_Fld_30day_shoulders_Wm2":stats(values["Fld"][controls]),
           "ACCESS_sky_emissivity_using_air_T_diagnostic":stats(emissivity(filled)),
           "QC0_shoulder_sky_emissivity_using_air_T_diagnostic":stats(emissivity(controls)),
           "ACCESS_air_temperature_C":stats(values["Ta"][filled]),
           "ACCESS_SH_kgkg":stats(values["SH"][filled]),
           "SOURCE_Fsd_contemporaneous_Wm2":stats(cloud),
           "entry_Fld_step_Wm2":jump(values,"Fld",a-1,a),
           "exit_Fld_step_Wm2":jump(values,"Fld",b-1,b),
           "filled_period_has_independent_Fld_tower_measurements":False
        }
        events=[("2017_Fld_ACCESS_ENTRY",a),
                ("2017_Fld_ACCESS_EXIT",b),
                ("2018_WIND_PEAK",at(t,"2018-03-10 20:30:00",time)),
                ("2014_PS_ALT_96H_ENTRY",at(t,"2014-08-26 17:30:00",time)),
                ("2014_PS_ALT_96H_EXIT",at(t,"2014-08-30 17:00:00",time)),
                ("2018_MULTI_ALT_START",at(t,"2018-06-09 18:00:00",time)),
                ("2018_MULTI_ALT_END",at(t,"2018-06-13 09:00:00",time))]
        windows=[]
        for name,i in events:
            windows+=context(name,range(max(begin,i-8),min(end,i+9)),
                             t,time,values,qc,i)
        windidx=at(t,"2018-03-10 20:30:00",time)
        wind={"value":fmt(values["Ws"][windidx]),
              "source_QCFlag":fmt(qc["Ws"][windidx]),
              "native_time":ts(t,time[windidx]),
              "neighbor_4h_Ws_mps":[fmt(x) for x in
                 values["Ws"][windidx-8:windidx+9]]}
        # Check 2018 five-variable simultaneous nonzero flags, not assumption
        # that QC 400 == 410, nor that a common QC proves source independence.
        f=("Ta","SH","ps","Ws","Precip")
        joint=np.logical_and.reduce([qc[v][a18:b18]!=0 for v in f])
        joint_spans=spans(joint);joint_rows=[]
        for l,r in joint_spans:
            ii=a18+l;jj=a18+r
            codes={v:sorted(set(int(x) for x in qc[v][ii:jj]
                   if np.isfinite(x))) for v in f}
            joint_rows.append({
                "start_native":ts(t,time[ii]),"end_native":ts(t,time[jj-1]),
                "hours":(jj-ii)*.5,"rows":jj-ii,
                "distinct_QCFlag_by_variable":json.dumps(codes,sort_keys=True),
                "entry_jump_Ta_C":jump(values,"Ta",ii-1,ii),
                "exit_jump_Ta_C":jump(values,"Ta",jj-1,jj),
                "entry_jump_SH_kgkg":jump(values,"SH",ii-1,ii),
                "exit_jump_SH_kgkg":jump(values,"SH",jj-1,jj),
                "entry_jump_ps_kPa":jump(values,"ps",ii-1,ii),
                "exit_jump_ps_kPa":jump(values,"ps",jj-1,jj),
                "entry_jump_Ws_mps":jump(values,"Ws",ii-1,ii),
                "exit_jump_Ws_mps":jump(values,"Ws",jj-1,jj)})
        joint_rows.sort(key=lambda x:-x["hours"])
        # The exact previously reported 87.5h five-var source nonzero run.
        known_start="2018-06-09 18:00:00"
        known_end="2018-06-13 09:00:00"
        matches=[x for x in joint_rows if x["start_native"]==known_start
                 and x["end_native"]==known_end and x["hours"]==87.5]
        need(len(matches)==1,
             "2018 87.5h source all-five alternate episode not matched")
        out.mkdir(mode=0o700,parents=False,exist_ok=False)
        write_tsv(out/"stage11_seven_event_original_before_after_HH.tsv",B_FIELDS,windows)
        write_tsv(out/"stage11_2018_joint_5variable_nonQC0_runs.tsv",J_FIELDS,joint_rows)
        summary={
         "stage":"AU-ASM Stage11 independent source meteorology scientific evaluation",
         "source_SHA256":SHA,"stage09":str(S09),"stage10":str(S10),
         "source_time_clock_approved":False,
         "2017_Fld_395h_model_fill_and_QC0_shoulders":fld_obs_baseline,
         "2018_original_QC_exact_code_percentages":annual,
         "2018_all_five_nonQC0_total_HH":int(joint.sum()),
         "2018_all_five_nonQC0_runs":len(joint_rows),
         "2018_87p5hour_joint_episode":matches[0],
         "2018_peak_wind":wind,
         "report_before_after_rows":len(windows),
         "science_release":False,"AD400_authorised":False,
         "Surface_modified":False,"forcing_modified":False,
         "CIME_case_created":False,"Slurm_submitted":False,
         "human_review":"Evaluate 2017 ACCESS radiation climatology vs QC0 shoulder distributions; 2018 exact PyFluxPro QC source codes and multivariable joins; 2018 wind peak QC, provenance and time convention. Do not auto-approve from this screen."
        }
        (out/"stage11_AU_ASM_SOURCE_SCIENCE_HOLD.json").write_text(
            json.dumps(summary,indent=2,ensure_ascii=False),encoding="utf-8")
    print("AU-ASM SOURCE SHA VERIFIED; STAGE09/10 SCIENCE HOLD VERIFIED")
    print("2017 Fld ACCESS",json.dumps(fld_obs_baseline))
    print("2018 ORIGINAL QC CODE COUNTS",json.dumps(annual))
    print("2018 JOINT 5-MET NON-QC0",len(joint_rows),"RUNS",int(joint.sum()),"HALF HOURS")
    print("2018 87.5H SHARED NON-QC0 FLAGS",json.dumps(matches[0]["distinct_QCFlag_by_variable"]))
    print("2018 WIND QC",wind["source_QCFlag"],"VALUE",wind["value"])
    print("AU-ASM STAGE11 READONLY SOURCE FORENSICS PASS; SCIENCE RELEASE FALSE; AD400 HOLD")
    print("REPORT_DIR",out)
if __name__=="__main__":main()
