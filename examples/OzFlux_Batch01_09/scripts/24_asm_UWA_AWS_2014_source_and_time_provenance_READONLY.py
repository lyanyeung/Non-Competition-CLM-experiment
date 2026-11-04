#!/usr/bin/env python3
"""Stage24 AU-ASM: inspect 2014 AWS donor archive and time/pressure provenance.

Actual public UWA 2020 dataset: Mahabbati et al.,
DOI 10.26182/5f292ee80a0c0, AliceSpringsMulga_AWS.nc
(2010-08-01 to 2015-10-21 dataset-period, source file coverage unverified).
Historical UWA AWS can independently inform 2014 Aug/Nov pressure gaps,
NOT 2017 Fld/2018 AWS ACCESS episodes. AWS archive identity as exact
2026 L4 donor is NOT proven. No automatic timestamp/unit calibration.

Two modes: with --aws downloaded NetCDF inspect source and 2014 pressure
versus old L6 under three explicitly alternative time-label hypotheses;
without --aws create exact donor provenance request and source-hold report.
No source edits, interpolation, CIME, Site-Soil, Slurm or AD400 release.
"""
from __future__ import annotations
import argparse,datetime as dt,hashlib,json,math,re,sys
from pathlib import Path
from collections import Counter
import numpy as np
from netCDF4 import Dataset,date2num
HOME=Path.home()
L3=HOME/"ozflux_ASM_TERN_2026v3_L3_source/AliceSpringsMulga_20100903T0000_to_20230308T0900_L3.nc"
L3SHA="8faa211fe95aa9f0382bf8d3848cb3245d6c8a25bf4ac440e6e92a77c8759076"
L4=HOME/"ozflux_ASM_TERN_2026v3_L4_source/AliceSpringsMulga_20100903T0000_to_20230308T0900_L4.nc"
L4SHA="120b1f3b800d8f1a1d1970e94573084a59d48b87e8d4db5b582157e377c530c8"
L6=Path("/iridisfs/scratch/ly3n24/CLM_FATES/sites/MY_EC_SITE/AU-ASM/forcing/raw/AliceSpringsMulga1_20100903T0000_to_20230308T0900_L6.nc")
L6SHA="b9381c4ed0744d03ae609cfbf3805e30bbb9223851a05f4e5b63b149dd0b10eb"
ST23=HOME/"ozflux_nc_stage23_20261104T032231Z/stage23_official_TERN_L4_donor_catalog_provenance_science_HOLD.json"
UWA="https://research-repository.uwa.edu.au/files/88640262/AliceSpringsMulga_AWS.nc"
DOI="https://doi.org/10.26182/5f292ee80a0c0"
EVENTS=(("AUG192","2014-08-26 17:30:00","2014-08-30 17:00:00",192),
        ("NOV43","2014-11-30 15:00:00","2014-12-01 12:00:00",43))
CLOCK={"assume_same_source_labels":0,
       "assume_AWS_UTC_and_L6_local":-570,
       "assume_AWS_local_and_L6_UTC":570}
def need(cond,msg):
    if not cond:raise RuntimeError(str(msg))
def sha(p):
    p=Path(p)
    need(p.is_file() and not p.is_symlink(),"Missing/nonregular input "+str(p))
    h=hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda:f.read(4<<20),b""):h.update(b)
    return h.hexdigest()
def attrs(v):
    return {s:str(v.getncattr(s))[:420] for s in
            ("units","long_name","standard_name","height","instrument",
             "statistic_type","source","time_zone","description","description_L4")
            if s in v.ncattrs()}
def globalattrs(ds):
    return {s:str(ds.getncattr(s))[:550] for s in ds.ncattrs()
            if any(x in s.lower() for x in
              ("site","station","source","instrument","time","history","latitude",
               "longitude","lat","lon","model","version","processing"))}
def numeric_point(v,i,tname):
    if v is None:return None
    try:
        dim=v.dimensions.index(tname)
    except ValueError:return None
    if any(j!=dim and n!=1 for j,n in enumerate(v.shape)):return None
    sl=tuple(i if j==dim else 0 for j in range(v.ndim))
    try:
        a=np.ma.asarray(v[sl],dtype=float).filled(np.nan).reshape(-1)
        val=float(a[0])
        return val if math.isfinite(val) and val>-9990 else None
    except (ValueError,TypeError,IndexError):return None
def normalize_pressure(raw,units):
    if raw is None:return None
    unit=(units or "").lower().replace(" ","")
    if unit in ("kpa","kilopascal","kilopascals"):return raw
    if unit in ("pa","pascal","pascals"):return raw/1000
    if unit in ("hpa","mbar","millibar","millibars"):return raw/10
    return None
def near(t,ts):
    # numeric time axis sorted ascending and CF units independently verified.
    i=int(np.searchsorted(t,ts))
    js=[j for j in (i-1,i) if 0<=j<len(t)]
    if not js:return None,None
    j=min(js,key=lambda k:abs(t[k]-ts))
    return j,abs(float(t[j]-ts))
def selftest():
    need(len(EVENTS)==2 and sum(e[3] for e in EVENTS)==235,"235 cohort")
    need(normalize_pressure(94600,"Pa")==94.6 and
         normalize_pressure(946,"hPa")==94.6,"pressure")
    need(CLOCK["assume_AWS_UTC_and_L6_local"]==-570,"source clock")
    print("OZFLUX STAGE24 SELF-TEST PASS | UWA AWS 2014 source/time/pressure provenance; READ ONLY")
def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--self-test",action="store_true")
    p.add_argument("--aws",type=Path,default=None)
    p.add_argument("--out",type=Path)
    a=p.parse_args()
    if a.self_test:return selftest()
    dest=a.out
    need(dest is not None and dest.parent.resolve()==HOME.resolve() and
         not dest.exists() and not dest.is_symlink(),
         "Use new immediate HOME output directory")
    need(sha(L3)==L3SHA and sha(L4)==L4SHA and sha(L6)==L6SHA,
         "Immutable TERN original L3/L4/L6 source SHA changed")
    prev=json.loads(ST23.read_text(encoding="utf-8"))
    need(prev.get("L4_downloaded_SHA256")==L4SHA and
         prev.get("L4_has_donor_intermediate_series") is False and
         prev.get("scientific_release") is False and
         prev.get("AD400_authorised") is False,
         "Stage23 actual L4 source and science-HOLD receipt changed")
    r={"site":"AU-ASM","audit":"Stage24 historical UWA AWS alternative donor provenance",
       "UWA_DOI":DOI,"public_archive_link":UWA,
       "public_archive_data_period":"2010-08-01 to 2015-10-21 (collection metadata, not verified exact file)",
       "UWA_file_exactly_same_as_2026_TERN_L4_donor":False,
       "L3_SHA256":L3SHA,"L4_SHA256":L4SHA,"L6_SHA256":L6SHA,
       "target_periods":list(EVENTS),
       "alternative_time_interpretations_tested_NOT_APPROVED":CLOCK,
       "source_clock_END_vs_CENTER_approved":False,
       "2017_2018_can_be_evaluated_by_this_2010_2015_source":False,
       "L4_bias_fit_workbook_verified":False,
       "historical_AWS_donor_science_approved":False,
       "source_wind_independent_approved":False,
       "science_release":False,"AD400_authorised":False,
       "no_originals_DATM_surface_CIME_or_Slurm_modified":True}
    if a.aws is None:
        r["AWS_access_status"]="not_provided"
        print("UWA AWS FILE NOT PROVIDED; RECORD SOURCE REQUEST, NO NUMERIC DONOR CLAIMS")
    else:
        f=a.aws
        need(f.is_file() and not f.is_symlink() and
             f.name=="AliceSpringsMulga_AWS.nc" and
             f.stat().st_size>1000000,
             "UWA AWS file absent/too small/name mismatch")
        with f.open("rb") as h:
            magic=h.read(8)
        need(magic.startswith((b"CDF\x01",b"CDF\x02",b"CDF\x05",
                 b"\x89HDF\r\n\x1a\n")),"Not actual NetCDF magic")
        r["AWS_access_status"]="provided"
        r["AWS_SHA256_computed"]=sha(f)
        r["AWS_size_bytes"]=f.stat().st_size
        with Dataset(str(f),"r") as ds:
            r["AWS_global_metadata"]=globalattrs(ds)
            names=sorted(ds.variables)
            r["AWS_variable_names"]=names[:400]
            pnames=[n for n in names if
                 ("press" in n.lower() or "baro" in n.lower() or
                  re.search(r"(^|[_])ps([_]|$)",n.lower()))
                 and not re.search(r"qc|flag",n,re.I)]
            r["AWS_possible_pressure_channels"]={
                n:{"attrs":attrs(ds.variables[n]),
                   "shape":list(ds.variables[n].shape),
                   "dimensions":list(ds.variables[n].dimensions)}
                for n in pnames[:80]}
            r["AWS_numeric_comparison_is_not_a_fit_validation"]=True
            r["AWS_archive_station_location_and_datum_verified"]=False
            if "time" not in ds.variables or not hasattr(ds.variables["time"],"units"):
                r["AWS_time_schema_status"]="no_CF_time_or_missing_units"
            else:
                tt=ds.variables["time"]
                r["AWS_time_attrs"]=attrs(tt)
                r["AWS_time_calendar"]=str(getattr(tt,"calendar","standard"))
                if "since" not in tt.units:
                    r["AWS_time_schema_status"]="CF_units_unsupported"
                else:
                    t=np.ma.asarray(tt[:],dtype=float).filled(np.nan).reshape(-1)
                    need(len(t)>0 and np.all(np.isfinite(t)) and
                         np.all(np.diff(t)>0),"UWA AWS native time invalid")
                    r["AWS_time_schema_status"]="CF_time_ordered"
                    r["AWS_n_times"]=len(t)
                    r["AWS_comparison_proposals"]=[]
                    for name in pnames[:30]:
                        v=ds.variables[name]
                        if tt.dimensions[0] not in v.dimensions:continue
                        if any(z!=v.dimensions.index(tt.dimensions[0])
                                and dim!=1 for z,dim in enumerate(v.shape)):continue
                        units=str(getattr(v,"units",""))
                        for tag,first,last,N in EVENTS:
                            for hypothesis,delta_minutes in CLOCK.items():
                                matches=[];finite=[];p_kpa=[]
                                for k in range(N):
                                    tower_dt=(dt.datetime.fromisoformat(first)+
                                         dt.timedelta(minutes=30*k))
                                    expected=date2num(tower_dt+
                                        dt.timedelta(minutes=delta_minutes),
                                        tt.units,calendar=getattr(tt,"calendar","standard"))
                                    j,du=near(t,float(expected))
                                    # Calculate difference in seconds to robustly
                                    # avoid accepting a nearby hour as an exact HH.
                                    unit=tt.units.split(" since ",1)[0].lower().strip()
                                    scale={"days":86400,"day":86400,"hours":3600,
                                      "hour":3600,"minutes":60,"minute":60,
                                      "seconds":1,"second":1}.get(unit)
                                    if scale is None:continue
                                    if j is None or du*scale>1:continue
                                    val=numeric_point(v,j,tt.dimensions[0])
                                    matches.append(j)
                                    if val is not None:
                                        finite.append(val)
                                        converted=normalize_pressure(val,units)
                                        if converted is not None:p_kpa.append(converted)
                                r["AWS_comparison_proposals"].append({
                                  "var":name,"event":tag,"source_label_hypothesis":hypothesis,
                                  "expected_HH":N,"exact_label_matching_HH":len(matches),
                                  "finite_matching_source_values":len(finite),
                                  "units_as_published":units,
                                  "pressure_kPa_if_recognised":{
                                     "n":len(p_kpa),
                                     "min":min(p_kpa) if p_kpa else None,
                                     "median":float(np.median(p_kpa)) if p_kpa else None,
                                     "max":max(p_kpa) if p_kpa else None},
                                  "no_source_clock_or_datum_calibration_applied":True})
    dest.mkdir(mode=0o700,parents=False,exist_ok=False)
    path=dest/"stage24_UWA_AWS_2014_ps_raw_source_provenance_HOLD.json"
    path.write_text(json.dumps(r,indent=2,ensure_ascii=False),encoding="utf-8")
    print("STAGE24 SOURCE STATUS",r["AWS_access_status"])
    if a.aws is not None:
        print("UWA AWS SHA256",r["AWS_SHA256_computed"])
        print("UWA GLOBAL METADATA",json.dumps(r["AWS_global_metadata"],ensure_ascii=False))
        print("UWA AWS PRESSURE-LIKE VARIABLES",json.dumps(r["AWS_possible_pressure_channels"]))
        print("UWA TIME SCHEMA",r.get("AWS_time_schema_status"))
        for z in r.get("AWS_comparison_proposals",[]):
            if z["exact_label_matching_HH"]>0:
                print("PRESSURE_TIME_CANDIDATE",json.dumps(z))
    print("STAGE24 READ ONLY; TIME/RAW DONOR ACCURACY NOT APPROVED; SCIENCE HOLD; NO AD400")
    print("REPORT_DIR",dest)
if __name__=="__main__":main()
