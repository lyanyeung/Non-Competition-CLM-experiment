#!/usr/bin/env python3
"""AU-ASM Stage18 read-only complete six-year L3/L6 source science screen.
Original L3 is processed tower data, NOT an independent wind instrument.
Inspect QC0 retention, gap-fill sources, all source runs, physical alarms,
and solar clock hypotheses. END vs CENTER remains unproven. No data writes.
"""
import argparse, csv, datetime as dt, hashlib, json, sys
from pathlib import Path
import numpy as np
from netCDF4 import Dataset, date2num

H=Path.home()
L3=H/"ozflux_ASM_TERN_2026v3_L3_source/AliceSpringsMulga_20100903T0000_to_20230308T0900_L3.nc"
L3SHA="8faa211fe95aa9f0382bf8d3848cb3245d6c8a25bf4ac440e6e92a77c8759076"
L6=Path("/iridisfs/scratch/ly3n24/CLM_FATES/sites/MY_EC_SITE/AU-ASM/forcing/raw/AliceSpringsMulga1_20100903T0000_to_20230308T0900_L6.nc")
L6SHA="b9381c4ed0744d03ae609cfbf3805e30bbb9223851a05f4e5b63b149dd0b10eb"
S17=H/"ozflux_nc_stage17_20261103T135445Z/stage17_TERN_2026v3_L3_vs_original_L6_science_HOLD.json"
VARS=("Ta","SH","ps","Fsd","Fld","Ws","Precip")
CODES=(0,1,10,50,400,410,420,430,440)
ALT=(50,400,410,420,430,440)
BOUNDS={"Ta":(-55,65),"SH":(0,.055),"ps":(45,115),
        "Fsd":(-50,1600),"Fld":(0,850),"Ws":(-.1,65),"Precip":(0,None)}
COLS=("year","var","n","l3_qc0","l6_qc0","l6_qc50","l6_qc410",
      "l6_qc420","l6_qc440","l6_other","l6_missing","retained_joint_qc0",
      "joint_qc0_numeric_mismatches","l6_qc0_without_l3_qc0",
      "alternate_fill_over_l3_gap","alternate_fill_while_l3_qc0",
      "broad_physical_alarms")
RUNS=("var","qc","first","last","n","hours","jump_in","jump_out",
      "source_status","review_decision")
def check(b,s):
    if not b: raise RuntimeError(s)
def digest(p):
    check(p.is_file() and not p.is_symlink(),"source missing: "+str(p))
    h=hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda:f.read(4<<20),b""): h.update(b)
    return h.hexdigest()
def vread(ds,k,a,b):
    t=ds.variables["time"]
    v=ds.variables[k]
    ax=v.dimensions.index(t.dimensions[0])
    check(all(j==ax or v.shape[j]==1 for j in range(v.ndim)),
          "non-singleton source "+k)
    sl=tuple(slice(a,b) if j==ax else 0 for j in range(v.ndim))
    x=np.ma.asarray(v[sl],dtype=float).filled(np.nan).reshape(-1)
    check(len(x)==b-a,"source length: "+k)
    return x
def idx(t,x,y):
    n=date2num(dt.datetime(y,1,1),t.units,calendar=getattr(t,"calendar","standard"))
    j=int(np.searchsorted(x,n))
    check(j<len(x) and abs(x[j]-n)*86400<.1,"native year absent "+str(y))
    return j
def good(x):return np.isfinite(x)&(x>-9990)
def steps(mask):
    x=np.asarray(mask,bool)
    e=np.flatnonzero(np.diff(np.r_[False,x,False].astype(np.int8)))
    return [(int(a),int(b)) for a,b in zip(e[::2],e[1::2])]
def label(stamp):return np.datetime_as_string(stamp,unit="s").replace("T"," ")
def jump(x,i,j):
    if i<0 or j>=len(x) or not (good(x[i]) and good(x[j])): return None
    return float(x[j]-x[i])
def counts(q):
    h={str(c):int((q==c).sum()) for c in CODES}
    h["other"]=int((np.isfinite(q)&~np.isin(q,CODES)).sum())
    h["missing"]=int((~np.isfinite(q)).sum())
    check(sum(h.values())==len(q),"QC codes not exhaustive")
    return h
def write(p,keys,body):
    with p.open("x",encoding="utf-8",newline="") as f:
        w=csv.DictWriter(f,fieldnames=keys,delimiter="\t")
        w.writeheader(); w.writerows(body)
def solar_angle(stamps,mode):
    # Approximate solar elevation; effective only as day/night diagnostic.
    shift={"local_END":-15,"local_CENTER":0,
           "UTC_END":555,"UTC_CENTER":570}[mode]
    center=stamps+np.timedelta64(shift,"m")
    day=center.astype("datetime64[D]")
    yr=day.astype("datetime64[Y]").astype("datetime64[D]")
    doy=(day-yr).astype("timedelta64[D]").astype(float)+1
    tod=(center-day.astype("datetime64[s]")).astype("timedelta64[s]").astype(float)/60
    g=2*np.pi/365*(doy-1+(tod/60-12)/24)
    eot=229.18*(.000075+.001868*np.cos(g)-.032077*np.sin(g)
         -.014615*np.cos(2*g)-.040849*np.sin(2*g))
    dec=(.006918-.399912*np.cos(g)+.070257*np.sin(g)
         -.006758*np.cos(2*g)+.000907*np.sin(2*g)
         -.002697*np.cos(3*g)+.00148*np.sin(3*g))
    ha=np.deg2rad(((tod+eot+4*133.2493-570)/4)%360-180)
    lat=np.deg2rad(-22.2828)
    sine=np.sin(lat)*np.sin(dec)+np.cos(lat)*np.cos(dec)*np.cos(ha)
    return np.rad2deg(np.arcsin(np.clip(sine,-1,1)))
def solar_screen(stamps,fsd,qc):
    obs=(qc==0)&good(fsd)
    hi=obs&(fsd>50)
    result={}
    for mode in ("local_END","local_CENTER","UTC_END","UTC_CENTER"):
        night=solar_angle(stamps,mode)<-4
        n=int((hi&night).sum())
        result[mode]={"QC0_Fsd_above50":int(hi.sum()),
            "above50_Wm2_at_night":n,
            "night_fraction":float(n/max(int(hi.sum()),1))}
    return result
def selftest():
    check(steps([0,1,1,0,1])==[(1,3),(4,5)],"runs")
    check(counts(np.array([0,1,410,420,440,99,np.nan]))["other"]==1,"qc")
    times=np.array(["2018-01-01T13:00","2018-01-01T00:00"],dtype="datetime64[m]")
    sun=solar_angle(times,"local_CENTER")
    check(sun[0]>0 and sun[1]<0,"solar day/night")
    print("STAGE18 SELFTEST PASS: L3-L6 source QC + 2013-18 solar screen, READ ONLY")
def main():
    if sys.argv[1:]==["--self-test"]:return selftest()
    ap=argparse.ArgumentParser()
    ap.add_argument("--out",type=Path,required=True)
    out=ap.parse_args().out
    check(out.parent.resolve()==H.resolve() and not out.exists() and not out.is_symlink(),
          "Need a NEW direct-HOME output folder")
    check(digest(L3)==L3SHA,"Official TERN L3 source SHA changed")
    check(digest(L6)==L6SHA,"Original frozen L6 source SHA changed")
    s17=json.loads(S17.read_text())
    check(s17.get("official_L3_SHA256_actual")==L3SHA
          and s17.get("science_release") is False
          and s17.get("AD400_authorised") is False,
          "Stage17 source lineage/science hold changed")
    annual=[];runs=[];mismatches=[];screen={}
    with Dataset(str(L3),"r") as a,Dataset(str(L6),"r") as b:
        ta=a.variables["time"];tb=b.variables["time"]
        check(ta.units==tb.units and "days since 1800-01-01" in ta.units,
              "Incompatible time units")
        check(a.getncattr("time_zone")=="Australia/Darwin"
              and b.getncattr("time_zone")=="Australia/Darwin","Time zone changed")
        ca=np.ma.asarray(ta[:],dtype=float).filled(np.nan).ravel()
        cb=np.ma.asarray(tb[:],dtype=float).filled(np.nan).ravel()
        l,r=idx(ta,ca,2013),idx(ta,ca,2019)
        j,k=idx(tb,cb,2013),idx(tb,cb,2019)
        check(r-l==k-j==105168,"Six-year record count mismatch")
        check(np.all(np.isfinite(ca[l:r]))
              and np.max(np.abs(ca[l:r]-cb[j:k]))*86400<.1,
              "2013-18 L3 versus L6 time labels do not align")
        stamps=(np.datetime64("1800-01-01T00:00:00","s")
                +np.rint(ca[l:r]*86400).astype("timedelta64[s]"))
        year=stamps.astype("datetime64[Y]").astype(int)+1970
        for v in VARS:
            a_val=vread(a,v,l,r);b_val=vread(b,v,j,k)
            qa=vread(a,v+"_QCFlag",l,r);qb=vread(b,v+"_QCFlag",j,k)
            original=(qa==0)&good(a_val)
            retained=(qb==0)&good(b_val)
            modeled=np.isin(qb,ALT)&good(b_val)
            both=original&retained
            numeric=both&(np.abs(a_val-b_val)>1e-5)
            for y in range(2013,2019):
                sel=year==y; qs=counts(qb[sel])
                z=b_val[sel];lo,hi=BOUNDS[v]
                phys=~good(z)|(z<lo)
                if hi is not None:phys|=z>hi
                annual.append(dict(year=y,var=v,n=int(sel.sum()),
                  l3_qc0=int((original&sel).sum()),
                  l6_qc0=int((retained&sel).sum()),
                  l6_qc50=qs["50"],l6_qc410=qs["410"],
                  l6_qc420=qs["420"],l6_qc440=qs["440"],
                  l6_other=int(sel.sum()-sum(qs[str(c)] for c in (0,50,410,420,440))),
                  l6_missing=int((~good(z)).sum()),
                  retained_joint_qc0=int((both&sel).sum()),
                  joint_qc0_numeric_mismatches=int((numeric&sel).sum()),
                  l6_qc0_without_l3_qc0=int((retained&~original&sel).sum()),
                  alternate_fill_over_l3_gap=int((modeled&~original&sel).sum()),
                  alternate_fill_while_l3_qc0=int((modeled&original&sel).sum()),
                  broad_physical_alarms=int(phys.sum())))
            for c in ALT:
                for lo,hi in steps(qb==c):
                    runs.append(dict(var=v,qc=c,first=label(stamps[lo]),
                     last=label(stamps[hi-1]),n=hi-lo,hours=(hi-lo)*.5,
                     jump_in=jump(b_val,lo-1,lo),
                     jump_out=jump(b_val,hi-1,hi),
                     source_status="L3_ONLY_NOT_VALIDATED_DONOR",
                     review_decision="FORCING_SCIENCE_HOLD"))
            if numeric.any():
                ids=np.flatnonzero(numeric)[:20]
                mismatches.append({"var":v,"count":int(numeric.sum()),
                   "first20":[{"native":label(stamps[i]),"L3":float(a_val[i]),
                        "L6":float(b_val[i])} for i in ids]})
            if v=="Fsd":screen=solar_screen(stamps,a_val,qa)
    check(len(annual)==42,"Wrong annual group count")
    runs.sort(key=lambda x:(-x["n"],x["var"],x["first"]))
    total=sum(z["joint_qc0_numeric_mismatches"] for z in annual)
    unexplained=sum(z["l6_qc0_without_l3_qc0"] for z in annual)
    out.mkdir(mode=0o700)
    write(out/"stage18_42_original_QC_crosswalk.tsv",COLS,annual)
    write(out/"stage18_all_source_fill_spells.tsv",RUNS,runs)
    summary={"site":"AU-ASM","L3_SHA256":L3SHA,"L6_SHA256":L6SHA,
       "six_year_HH_per_var":105168,"year_variable_groups":42,
       "native_L3_L6_clock_aligned":True,
       "original_interval_end_vs_center_independently_proven":False,
       "source_QC0_pairwise_numeric_mismatches":total,
       "L6_QC0_not_supported_by_L3_QC0":unexplained,
       "all_contiguous_alt_source_spells":len(runs),
       "solar_clock_sanity_only":screen,
       "joint_QC0_mismatch_sample":mismatches,
       "longest_fills":runs[:25],
       "science_release":False,"AD400_authorised":False,
       "independent_wind_sensor_verified":False,
       "L4_AWS_ACCESS_ERA5_overlap_calibration_verified":False,
       "old_L6_and_all_DATM_unchanged":True,
       "no_surface_CIME_or_Slurm_writes":True}
    (out/"stage18_AU_ASM_6year_forcing_science_HOLD.json").write_text(
       json.dumps(summary,indent=2),encoding="utf-8")
    print("STAGE18 SIX-YEAR L3-L6 42 ORIGINAL QC SOURCE GROUPS")
    print("JOINT L3/L6 QC0 NUMERIC MISMATCHES",total)
    print("L6 QC0 WITHOUT ORIGINAL L3 QC0",unexplained)
    print("ALTERNATE FILL CONTIGUOUS EPISODES",len(runs))
    for z in annual:
        if z["year"]==2018 or z["year"]==2017 and z["var"]=="Fld":
            print("YEAR",z["year"],z["var"],"L3_QC0",z["l3_qc0"],
                  "L6_QC0",z["l6_qc0"],"AWS410",z["l6_qc410"],
                  "ACCESS420",z["l6_qc420"],"ERA5_440",z["l6_qc440"],
                  "FILLS_OVER_GAP",z["alternate_fill_over_l3_gap"],
                  "QC0_DIFFERENCES",z["joint_qc0_numeric_mismatches"])
    for z in runs[:12]:
        print("LONGEST",z["var"],z["qc"],z["first"],z["last"],
              z["hours"],"h","ENTRY",z["jump_in"],"EXIT",z["jump_out"])
    print("SOLAR NIGHT-LIGHT PROVENANCE",json.dumps(screen))
    print("STAGE18 READ ONLY QC SCREEN; FORCING SCIENCE HOLD; NO AD400/SLURM")
    print("REPORT_DIR",out)
if __name__=="__main__":main()
