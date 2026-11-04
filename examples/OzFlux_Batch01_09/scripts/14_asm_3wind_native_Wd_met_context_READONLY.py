#!/usr/bin/env python3
"""AU-ASM Stage14, 3 native PyFluxPro QC0 wind events. READ ONLY.
Use original SHA-locked L6; output wind-direction and all seven original
meteorology/QC flags +/- 24h. No approval, repair, CIME, Surface or Slurm.
"""
import argparse,csv,datetime as dt,hashlib,json,sys
from pathlib import Path
import numpy as np
from netCDF4 import Dataset,date2num,num2date

HOME=Path.home()
SOURCE=Path("/iridisfs/scratch/ly3n24/CLM_FATES/sites/MY_EC_SITE/AU-ASM/forcing/raw/AliceSpringsMulga1_20100903T0000_to_20230308T0900_L6.nc")
SHA="b9381c4ed0744d03ae609cfbf3805e30bbb9223851a05f4e5b63b149dd0b10eb"
RECEIPT=HOME/"ozflux_nc_stage12_20261103T074301Z/stage12_native_sensor_time_AWS_ACCESS_science_HOLD.json"
EVENTS=[("2018-03-10 20:30:00",16.29613),("2013-01-05 18:00:00",9.747453),("2014-11-23 01:00:00",7.483473)]
MET=["Ws","Ta","SH","ps","Fsd","Fld","Precip"]
FIELDS=["event","native_time","offset_HH"]+[v+k for v in MET+["Wd"] for k in ("","_QCFlag")]
def req(x,msg):
    if not x:raise ValueError(msg)
def sha(p):
    h=hashlib.sha256()
    with p.open("rb") as f:
        for x in iter(lambda:f.read(4<<20),b""):h.update(x)
    return h.hexdigest()
def vdata(ds,name,n):
    if name not in ds.variables:return None
    v=ds.variables[name]
    a=np.ma.asarray(v[:],dtype=float).filled(np.nan).ravel()
    return a if len(a)==n else None
def vf(x):
    return None if x is None or not np.isfinite(x) else float(x)
def classify(p,a,b):
    if p-max(a,b)>6 and p/max(a,b)>2.5:return "SINGLE_SAMPLE_SPIKE_REVIEW"
    if max(a,b)>=.75*p:return "CONTIGUOUS_HIGH_WIND"
    return "TRANSITION_OR_VARIABILITY_REVIEW"
def angle(x,y):
    return None if x is None or y is None else (x-y+180)%360-180
def selftest():
    req(classify(16.29613,3.671959,3.970067)=="SINGLE_SAMPLE_SPIKE_REVIEW","spike")
    req(classify(9.747453,2.697516,7.202567)=="TRANSITION_OR_VARIABILITY_REVIEW","transition")
    req(classify(7.483473,7.258892,6.650625)=="CONTIGUOUS_HIGH_WIND","sustained")
    req(angle(5,355)==10,"circular wrap")
    print("OZFLUX STAGE14 SELF-TEST PASS | 3 wind event categories; READ ONLY")
def main():
    if sys.argv[1:]==["--self-test"]:return selftest()
    ap=argparse.ArgumentParser()
    ap.add_argument("--out",type=Path,required=True)
    out=ap.parse_args().out
    req(out.parent.resolve()==HOME.resolve() and not out.exists() and not out.is_symlink(),
        "Use a NEW immediate HOME output directory")
    req(SOURCE.is_file() and sha(SOURCE)==SHA,"Original L6 SHA mismatch")
    r=json.loads(RECEIPT.read_text())
    req(r.get("science_release") is False and r.get("AD400_authorised") is False
        and r.get("six_year_isolated_QC0_wind_review_count")==3,
        "Stage12 science hold or original three-event receipt changed")
    reports=[];rows=[]
    with Dataset(str(SOURCE),"r") as ds:
        t=ds.variables["time"]
        raw=np.ma.asarray(t[:],dtype=float).filled(np.nan).ravel()
        req(t.ndim==1 and np.isfinite(raw).all() and np.all(np.diff(raw)>0),
            "Original time irregular")
        val={k:vdata(ds,k,len(raw)) for k in MET+["Wd"]}
        flag={k:vdata(ds,k+"_QCFlag",len(raw)) for k in MET+["Wd"]}
        req(all(val[k] is not None and flag[k] is not None for k in MET),
            "Original seven meteorological columns missing")
        attrs={}
        for k in ("Ws","Wd"):
            if k in ds.variables:
                v=ds.variables[k]
                attrs[k]={a:str(v.getncattr(a))[:500] for a in
                  ("statistic_type","units","height","long_name","instrument","source")
                  if a in v.ncattrs()}
        for date,expected in EVENTS:
            native=date2num(dt.datetime.fromisoformat(date),t.units,
                            calendar=getattr(t,"calendar","standard"))
            i=int(np.searchsorted(raw,native))
            req(i>48 and i<len(raw)-49 and abs(raw[i]-native)<1e-7,
                "Native event timestamp unavailable "+date)
            w=val["Ws"]
            req(abs(w[i]-expected)<1e-5 and flag["Ws"][i]==0,
                "Original QC0 wind changed "+date)
            a,b,p=map(float,(w[i-1],w[i+1],w[i]))
            direction=val["Wd"]
            wd=vf(direction[i]) if direction is not None else None
            dprev=vf(direction[i-1]) if direction is not None else None
            dnext=vf(direction[i+1]) if direction is not None else None
            met={k:{"value":vf(val[k][i]),"QCFlag":vf(flag[k][i]),
                    "jump_in":vf(val[k][i]-val[k][i-1]),
                    "jump_out":vf(val[k][i+1]-val[k][i])} for k in MET}
            reports.append({"native_time":date,"Ws_ms":p,"Ws_QC0":True,
              "previous_Ws_ms":a,"next_Ws_ms":b,
              "classification":classify(p,a,b),
              "excess_above_stronger_immediate_neighbor_ms":p-max(a,b),
              "Wd_degrees":wd,
              "Wd_QCFlag":vf(flag["Wd"][i]) if flag["Wd"] is not None else None,
              "Wd_change_from_previous_deg":angle(wd,dprev),
              "Wd_change_to_next_deg":angle(dnext,wd),
              "same_timestamp_source_met":met,
              "instrument_error_confirmed":False,
              "independent_wind_speed_donor_approved":False})
            for j in range(i-48,i+49):
                z=num2date(float(raw[j]),t.units,
                          calendar=getattr(t,"calendar","standard"))
                timestamp=f"{z.year:04d}-{z.month:02d}-{z.day:02d} {z.hour:02d}:{z.minute:02d}:{z.second:02d}"
                row={"event":date,"native_time":timestamp,"offset_HH":j-i}
                for k in MET+["Wd"]:
                    row[k]=vf(val[k][j]) if val[k] is not None else None
                    row[k+"_QCFlag"]=vf(flag[k][j]) if flag[k] is not None else None
                rows.append(row)
    out.mkdir(mode=0o700)
    with (out/"stage14_original_3wind_7met_Wd_24h_context.tsv").open("x",newline="",encoding="utf-8") as f:
        writer=csv.DictWriter(f,fieldnames=FIELDS,delimiter="\t")
        writer.writeheader();writer.writerows(rows)
    summary={"site":"AU-ASM","original_L6_sha256":SHA,
             "original_sensor_metadata":attrs,"events":reports,
             "source_clock_scientifically_approved":False,
             "science_release":False,"AD400_authorised":False,
             "original_forcing_changed":False,"site_soil_surface_changed":False,
             "CIME_case_created":False,"Slurm_submitted":False}
    (out/"stage14_source_wind_science_HOLD.json").write_text(
       json.dumps(summary,indent=2,ensure_ascii=False),encoding="utf-8")
    print("ORIGINAL L6 SHA + STAGE12 HOLD VERIFIED")
    print("WIND SOURCE METADATA",json.dumps(attrs))
    for q in reports:
        print("EVENT",q["native_time"],"Ws",q["Ws_ms"],"PREV",q["previous_Ws_ms"],
              "NEXT",q["next_Ws_ms"],"WD",q["Wd_degrees"],
              "WD_IN",q["Wd_change_from_previous_deg"],
              "WD_OUT",q["Wd_change_to_next_deg"],"CLASS",q["classification"])
        print("SAME-TIME MET",json.dumps(q["same_timestamp_source_met"]))
    print("READ ONLY AUDIT PASS; FORCING SCIENCE HOLD; AD400 BLOCKED; NO SLURM")
    print("REPORT_DIR",out)
if __name__=="__main__":main()
