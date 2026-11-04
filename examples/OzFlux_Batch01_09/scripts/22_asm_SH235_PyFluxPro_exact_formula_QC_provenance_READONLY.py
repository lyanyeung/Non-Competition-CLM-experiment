#!/usr/bin/env python3
"""AU-ASM Stage22: reproduce 235 L6 SH-QC0 "source exceptions" using PyFluxPro.

Actual public source functions on pinned OzFlux/PyFluxPro main commit:
e0fc5f4690c2cabb56831573fb08e5e7b012b2b8
  scripts/meteorologicalfunctions.py: VPsat, vapourpressure,
    relativehumidityfromabsolutehumidity, specifichumidityfromRH
  scripts/constants.py: R=8.314, Mv=0.01802, Md=0.02897
  scripts/pfp_ts.py: SpecificHumidityFromAbsoluteHumidity()
  scripts/pfp_utils.py: MergeQCFlag() treating later argument QC410
    (ends in 0) as "good" when propagating derived humidity QC.

Reproduce actual old L6 SH from actual (AH,Ta,ps); reconstruct expected
derived SH flag from actual (Ta_QC,ps_QC,AH_QC) under public algorithm.
Compare by source episodes to more complete mixing-ratio formula to
explain Stage20–21 differential rather than inventing pressure errors.

We have not independently pinned the source code used in the original
PyFluxPro V3.4.24 build, though original 235 numerical equality can
strongly support matching implementation. A source QCFlag of 0 in
derived SH does NOT prove ps 410 was originally measured at the tower.
This script writes reports only; NO netCDF/data, surface, CIME or Slurm.
"""
from __future__ import annotations
import argparse,csv,datetime as dt,hashlib,json,math,sys
from pathlib import Path
import numpy as np
from netCDF4 import Dataset,date2num

HOME=Path.home()
L3=HOME/"ozflux_ASM_TERN_2026v3_L3_source/AliceSpringsMulga_20100903T0000_to_20230308T0900_L3.nc"
L3_SHA="8faa211fe95aa9f0382bf8d3848cb3245d6c8a25bf4ac440e6e92a77c8759076"
L6=Path("/iridisfs/scratch/ly3n24/CLM_FATES/sites/MY_EC_SITE/AU-ASM/forcing/raw/AliceSpringsMulga1_20100903T0000_to_20230308T0900_L6.nc")
L6_SHA="b9381c4ed0744d03ae609cfbf3805e30bbb9223851a05f4e5b63b149dd0b10eb"
STAGE21=HOME/"ozflux_nc_stage21_20261104T025736Z"/"stage21_43vs192_SH_formula_pressure_QC_science_HOLD.json"
PFPCOMMIT="e0fc5f4690c2cabb56831573fb08e5e7b012b2b8"
EPISODES=(("AUG192","2014-08-26 17:30:00","2014-08-30 17:00:00",192),
          ("NOV43","2014-11-30 15:00:00","2014-12-01 12:00:00",43))
COLUMNS=("episode","native_time","L3_SH_QCFlag","L3_SH_value","L6_SH_QCFlag",
    "L6_SH_kgkg","L3_AH_QCFlag","L6_AH_QCFlag","L6_AH_g_m3",
    "L6_Ta_QCFlag","L6_Ta_degC","L3_ps_QCFlag","L6_ps_QCFlag","L6_ps_kPa",
    "predicted_PyFluxPro_SH_QCFlag","predicted_PyFluxPro_SH_kgkg",
    "actual_minus_PFP_kgkg","actual_minus_PFP_gkg",
    "complete_SH_formula_kgkg","actual_minus_complete_gkg")

R=8.314
MV=.01802
MD=.02897
def check(ok,why):
    if not ok:raise ValueError(str(why))
def sha(path):
    p=Path(path)
    check(p.is_file() and not p.is_symlink(),"Immutable input absent/symlink "+str(p))
    h=hashlib.sha256()
    with p.open("rb") as f:
        for a in iter(lambda:f.read(4<<20),b""):h.update(a)
    return h.hexdigest()
def data(ds,var,l,r):
    v=ds.variables[var]
    td=ds.variables["time"].dimensions[0]
    check(v.dimensions.count(td)==1,"Unexpected time dimension "+var)
    ax=v.dimensions.index(td)
    check(all(i==ax or x==1 for i,x in enumerate(v.shape)),"Nonpoint array "+var)
    sl=tuple(slice(l,r) if k==ax else 0 for k in range(v.ndim))
    x=np.ma.asarray(v[sl],dtype=float).filled(np.nan).reshape(-1)
    check(len(x)==r-l,"Source array size "+var)
    return x
def time_index(v,time,datestr):
    n=date2num(dt.datetime.fromisoformat(datestr),v.units,
               calendar=getattr(v,"calendar","standard"))
    i=int(np.searchsorted(time,n))
    check(0<=i<len(time) and abs(time[i]-n)*86400<.1,
          "Original native source label missing "+datestr)
    return i
def valid(x):
    return np.isfinite(x)&(x>-9990)
def pfp_sh(AH,T,ps):
    # Exactly the cited PyFluxPro functions, even when they employ
    # a simplified humidity expression rather than full mixing ratio.
    vapour_kpa=1e-6*AH*(T+273.15)*R/MV
    saturation_kpa=.6106*np.exp(17.27*T/(T+237.3))
    RH=100*vapour_kpa/saturation_kpa
    return (MV/MD)*(.01*RH*saturation_kpa/ps)
def full_sh(AH,T,ps):
    vapor=1e-6*AH*(T+273.15)*R/MV
    return .622*vapor/(ps-.378*vapor)
def merge_flags_like_pfp(first,second,third):
    # PyFluxPro MergeQCFlag: take first flag, for *subsequent*
    # arrays set all values ending in zero to zero, then max().
    flag=first.copy()
    for other in (second,third):
        temp=other.copy()
        temp[np.mod(temp,10)==0]=0
        flag=np.maximum(flag,temp)
    return flag
def stats(x):
    z=np.asarray(x,dtype=float)
    z=z[np.isfinite(z)]
    return {"n":int(len(z)),
            "mean":float(z.mean()) if len(z) else None,
            "median":float(np.median(z)) if len(z) else None,
            "min":float(z.min()) if len(z) else None,
            "max":float(z.max()) if len(z) else None,
            "max_absolute":float(np.max(np.abs(z))) if len(z) else None}
def save(path,lines):
    with path.open("x",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=COLUMNS,delimiter="\t",extrasaction="raise")
        w.writeheader();w.writerows(lines)
def selftest():
    AH=9.377013;Ta=35.33015;ps=93.57956665399436
    expected=.008870993003645255
    check(abs(pfp_sh(AH,Ta,ps)-expected)<1e-15,
          "PyFluxPro first NOV43 original source numeric equality failed")
    flags=merge_flags_like_pfp(np.array([0.,0.]),np.array([410.,1.]),
                              np.array([0.,0.]))
    check(np.array_equal(flags,[0.,1.]),"QC provenance last-digit propagation")
    check(abs(pfp_sh(AH,Ta,ps)-full_sh(AH,Ta,ps))>1e-5,
          "More-complete humidity formula must differ for humid test")
    print("OZFLUX STAGE22 SELF-TEST PASS: exact PFP SH formula and QC410 propagation; READ ONLY")
def main():
    if sys.argv[1:]==["--self-test"]:return selftest()
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out",type=Path,required=True)
    o=ap.parse_args().out
    check(o.parent.resolve()==HOME.resolve() and not o.exists() and not o.is_symlink(),
          "Output must be NEW direct HOME folder")
    check(sha(L3)==L3_SHA and sha(L6)==L6_SHA,
          "Original L3 or L6 immutable bytes changed")
    previous=json.loads(STAGE21.read_text(encoding="utf-8"))
    check(previous.get("science_release") is False
      and previous.get("AD400_authorised") is False
      and previous.get("n_source_exceptions")==235
      and previous.get("L3_SHA256")==L3_SHA
      and previous.get("L6_SHA256")==L6_SHA,
      "Actual Stage21 operator 235/QC science HOLD changed")
    output=[];results={}
    with Dataset(str(L3),"r") as d3,Dataset(str(L6),"r") as d6:
        t3=d3.variables["time"];t6=d6.variables["time"]
        check(t3.units==t6.units and "days since 1800-01-01" in t3.units,
              "Original native time source changed")
        all3=np.ma.asarray(t3[:],dtype=float).filled(np.nan)
        all6=np.ma.asarray(t6[:],dtype=float).filled(np.nan)
        for key,start,end,expected in EPISODES:
            a=time_index(t3,all3,start)
            b=time_index(t3,all3,end)+1
            c=time_index(t6,all6,start)
            d=time_index(t6,all6,end)+1
            check(b-a==d-c==expected and
                  np.max(np.abs(all3[a:b]-all6[c:d]))*86400<.1,
                  "2014 source episode clock drift "+key)
            old_sh=data(d3,"SH",a,b)
            old_q=data(d3,"SH_QCFlag",a,b)
            old_ah_q=data(d3,"AH_QCFlag",a,b)
            old_ps_q=data(d3,"ps_QCFlag",a,b)
            AH=data(d6,"AH",c,d)
            Ta=data(d6,"Ta",c,d)
            ps=data(d6,"ps",c,d)
            SH=data(d6,"SH",c,d)
            sh_q=data(d6,"SH_QCFlag",c,d)
            ah_q=data(d6,"AH_QCFlag",c,d)
            ta_q=data(d6,"Ta_QCFlag",c,d)
            ps_q=data(d6,"ps_QCFlag",c,d)
            check(np.all(old_q==1) and np.all(~valid(old_sh)) and
                  np.all(old_ah_q==0) and np.all(old_ps_q==1) and
                  np.all(sh_q==0) and np.all(ah_q==0) and np.all(ta_q==0)
                  and np.all(ps_q==410)
                  and np.all(valid(SH)&valid(AH)&valid(Ta)&valid(ps)),
                  "Original 235-source SH/AH/ps QC conditions changed "+key)
            model=pfp_sh(AH,Ta,ps)
            flag=merge_flags_like_pfp(ta_q,ps_q,ah_q)
            check(np.all(flag==0),"Simulated PFP derived SH QC mismatch "+key)
            residual=SH-model
            physical=SH-full_sh(AH,Ta,ps)
            n_exact=int(np.sum(np.abs(residual)<=1e-12))
            for k in range(expected):
                stamp=(np.datetime64("1800-01-01T00:00:00","s")+
                        np.timedelta64(int(round(all3[a+k]*86400)),"s"))
                output.append({
                  "episode":key,"native_time":np.datetime_as_string(stamp,unit="s").replace("T"," "),
                  "L3_SH_QCFlag":old_q[k],"L3_SH_value":old_sh[k],
                  "L6_SH_QCFlag":sh_q[k],"L6_SH_kgkg":SH[k],
                  "L3_AH_QCFlag":old_ah_q[k],
                  "L6_AH_QCFlag":ah_q[k],"L6_AH_g_m3":AH[k],
                  "L6_Ta_QCFlag":ta_q[k],"L6_Ta_degC":Ta[k],
                  "L3_ps_QCFlag":old_ps_q[k],
                  "L6_ps_QCFlag":ps_q[k],"L6_ps_kPa":ps[k],
                  "predicted_PyFluxPro_SH_QCFlag":flag[k],
                  "predicted_PyFluxPro_SH_kgkg":model[k],
                  "actual_minus_PFP_kgkg":residual[k],
                  "actual_minus_PFP_gkg":residual[k]*1000,
                  "complete_SH_formula_kgkg":full_sh(AH[k],Ta[k],ps[k]),
                  "actual_minus_complete_gkg":physical[k]*1000})
            results[key]={"start_native":start,"end_native":end,"HH":expected,
                "source_L3_SH_missing_QC1":int(np.sum(old_q==1)),
                "source_L3_AH_QC0":int(np.sum(old_ah_q==0)),
                "L6_ps_AWS_QC410":int(np.sum(ps_q==410)),
                "predicted_SH_source_QC0":int(np.sum(flag==0)),
                "PyFluxPro_formula_exact_within_1e_12_kgkg":n_exact,
                "PyFluxPro_SH_residual_gkg":stats(residual*1000),
                "more_complete_SH_formula_difference_gkg":stats(physical*1000)}
    check(len(output)==235,"Full 235 original QC source exception count mismatch")
    report={"stage":"AU-ASM Stage22 PyFluxPro source-exact SH reconstruction and derived QC provenance",
       "L3_SHA256":L3_SHA,"L6_SHA256":L6_SHA,
       "PyFluxPro_public_source_commit":PFPCOMMIT,
       "public_version_may_differ_from_original_V3_4_24":True,
       "original_processing_control_file_verified":False,
       "source_QC0_means_tower_observed_for_derived_SH":False,
       "L6_2014_SH_origins_are_explainable_without_numerical_repair":
           sum(x["PyFluxPro_formula_exact_within_1e_12_kgkg"] for x in results.values())==235,
       "episodes":results,"annual_SH_exception_HH_total":235,
       "scientific_QCLineage_approved":False,
       "AWS_ps_donor_bias_verified":False,
       "source_clock_END_vs_CENTER_approved":False,
       "science_release":False,"AD400_authorised":False,
       "no_original_source_DATM_Surface_CIME_Slurm_writes":True}
    o.mkdir(mode=0o700,parents=False,exist_ok=False)
    save(o/"stage22_exact_235_SH_PFP_formula_and_QC_reproduction.tsv",output)
    (o/"stage22_2014_SH_235_PFP_source_QC_science_HOLD.json").write_text(
       json.dumps(report,indent=2,ensure_ascii=False),encoding="utf-8")
    print("AU-ASM STAGE22 ORIGINAL SOURCE L3/L6 / STAGE21 RECEIPT SHAS VERIFIED")
    for k,v in results.items():
        print("SOURCE",k,"HH",v["HH"],"PFP_Q_EXACT_1e-12",
              v["PyFluxPro_formula_exact_within_1e_12_kgkg"],
              "DERIVED_PFP_QC0",v["predicted_SH_source_QC0"])
        print("PFP_RESIDUAL_gkg",k,json.dumps(v["PyFluxPro_SH_residual_gkg"]))
        print("COMPLETE_FORMULA_MINUS_ACTUAL_gkg",k,
              json.dumps(v["more_complete_SH_formula_difference_gkg"]))
    print("STAGE22 EXACT SOURCE MODEL AUDITED; SCIENCE HOLD; NO MODEL/AD400 SUBMISSION")
    print("REPORT_DIR",o)

if __name__=="__main__":main()
