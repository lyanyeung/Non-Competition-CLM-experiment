#!/usr/bin/env python3
"""AU-Gin Stage07: actual NOAA Pearce raw values vs five FLUXNET source spikes.

Authoritative inputs:
 - operator original Stage05 source/neighbor TSV and science HOLD JSON;
 - operator original Stage06v3 GHCNh station-and-year source receipt;
 - independently downloaded GHCNh ASN00009053 2012/2016/2019 PSV (SHA pinned).
No guessed Gingin Aero identifier, and no future NOAA/BoM fetches.

Output both source-native-as-UTC and source-native-as-WST(UTC+8) hypotheses,
not a winner. Airport ~43 km away: no station-pressure altitude correction,
wind-height equivalence, or assumptions about FLUXNET time zone. Never
combine SEA_LEVEL_PRESSURE with STATION_LEVEL_PRESSURE as if equal.
All source and model data read-only. All event assessments SCIENCE HOLD.
"""
from __future__ import annotations
import argparse,csv,datetime as dt,hashlib,json,math,re
from collections import Counter
from pathlib import Path
H=Path.home()
S05=H/"ozflux_AU_Gin_stage05_20261105T034925Z"
S06=H/"ozflux_AU_Gin_stage06v3_20261105T041031Z"
SRC=H/"ozflux_AU_Gin_NOAA_GHCNh_original"
GH="ASN00009053"
FILESHA={2012:"e570f28819cc144c308c60e9faaefa39cb2dd48db779adc3552e868a74f8197f",
         2016:"7a13f3cc7d528c1e64cee6b4611575b426a3a99be595f57789d9397db924613e",
         2019:"9c611d531d005f20aeed625c489e5d60155a03913f42b0e5323c0d8915f5a417"}
ROWS={2012:2916,2016:4893,2019:8760}
ZIP_SHA="acd78491b6f5f2c1374da2076d73a6c8b6ef430b256b78da3d300656943d6f14"
EVENTS=[
 ("PA_20120609","2012-06-09 08:30:00","PA"),
 ("PA_20120610","2012-06-10 13:30:00","PA"),
 ("TA_20160507","2016-05-07 16:00:00","TA"),
 ("TA_20160520","2016-05-20 18:00:00","TA"),
 ("WS_20190913","2019-09-13 03:00:00","WS")]
# NOAA GHCNh PSV values per NOAA documentation; preserve source units.
NOAA={"PA":("station_level_pressure","hPa",850,1100),
      "TA":("temperature","degC",-60,65),
      "WS":("wind_speed","m/s",0,80)}
EXTRA={"PA":("sea_level_pressure","hPa",850,1100),
       "WS":("wind_gust","m/s",0,100)}
OUTFIELDS=("event_id","tower_native_timestamp","tower_variable","tower_F_value",
           "tower_F_QC","tower_ERA_same_product",
           "NOAA_station","station_distance_km","hypothesis",
           "NOAA_variable","NOAA_variable_unit","NOAA_nearest_UTC",
           "minutes_NOAA_minus_assumed_UTC","NOAA_raw",
           "NOAA_numeric_within_physical_screen",
           "NOAA_Quality_Code","NOAA_Measurement_Code",
           "NOAA_Report_Type","NOAA_Source_Code","NOAA_Source_Station_ID",
           "valid_hours_within_6h","NOAA_pressure_is_station_level",
           "NOAA_pressure_or_wind_is_NOT_tower_equivalent",
           "source_alignment_approved","scientific_repair_approved")
HEADER_FIELDS=("source_year","NOAA_records","NOAA_year_first_UTC",
               "NOAA_year_last_UTC","temperature_n_plausible",
               "station_level_pressure_n_plausible",
               "sea_level_pressure_n_plausible",
               "wind_speed_n_plausible","wind_gust_n_plausible",
               "NOAA_source_original_PSV_sha256")
def need(x,msg):
    if not x:raise RuntimeError(str(msg))
def sha(p):
    p=Path(p)
    need(p.is_file() and not p.is_symlink(),"Original input missing/symlink: "+str(p))
    h=hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda:f.read(4<<20),b""):h.update(b)
    return h.hexdigest()
def norm(x):return re.sub("[^a-zA-Z0-9]","",str(x)).lower()
def field(row,name):
    key=norm(name)
    for k,v in row.items():
        if k and norm(k)==key:return str(v or "").strip()
    return ""
def maybe_num(s):
    try:
        n=float(str(s).strip())
        if not math.isfinite(n) or abs(n)>=9990:return None
        return n
    except (TypeError,ValueError):return None
def plausible(s,lo,hi):
    v=maybe_num(s)
    return v if v is not None and lo<=v<=hi else None
def utc(s):
    s=str(s or "").strip()
    if not s:return None
    if s.endswith("Z"):s=s[:-1]+"+00:00"
    try:
        a=dt.datetime.fromisoformat(s)
        return a.astimezone(dt.timezone.utc).replace(tzinfo=None) if a.tzinfo else a
    except ValueError:return None
def save(path,cols,rows):
    with path.open("x",encoding="utf-8",newline="") as f:
        w=csv.DictWriter(f,delimiter="\t",fieldnames=cols,extrasaction="raise")
        w.writeheader();w.writerows(rows)
def read_previous_centers():
    original=S05/"stage05_AU_Gin_44_flag_previous_next_HH_differentials.tsv"
    with original.open(encoding="utf-8",newline="") as f:
        rows=list(csv.DictReader(f,delimiter="\t"))
    need(len(rows)==44,"Operator exact Stage05 44 flags changed")
    selected={}
    for e,t,v in EVENTS:
        m=[r for r in rows if r.get("native_time")==t and r.get("variable")==v]
        need(len(m)==1,"No unique actual tower center: "+e)
        selected[e]=m[0]
        need(m[0].get("QC_current") in ("0","0.0"),"Event QC0 changed: "+e)
    return selected,sha(original)
def records_and_meta(p,year):
    raw=[];N=0;first=last=None
    ns=Counter()
    with p.open(encoding="utf-8-sig",newline="") as f:
        head=f.readline()
        need("|" in head and "<html" not in head.lower(),"Original NOAA PSV is malformed")
        f.seek(0)
        reader=csv.DictReader(f,delimiter="|")
        cols=reader.fieldnames
        need(cols and len(cols)>=30,"NOAA original PSV lacks headers")
        timestamp_key=next((k for k in cols if norm(k) in ("date","datetime","timestamp","observationtime")),None)
        need(timestamp_key is not None,"NOAA PSV no UTC timestamp field")
        ids=[k for k in cols if norm(k) in ("stationid","station")]
        for row in reader:
            N+=1
            if ids and row.get(ids[0],"").strip():
                need(row[ids[0]].strip()==GH,"NOAA source station changed")
            t=utc(row[timestamp_key])
            need(t is not None,"NOAA invalid UTC timestamp row "+str(N))
            if first is None:first=t
            last=t
            if t.year==year:
                record={"utc":t,"data":row}
                raw.append(record)
            for key,(unit,lower,upper) in {
                "temperature":("C",-60,65),"station_level_pressure":("hPa",850,1100),
                "sea_level_pressure":("hPa",850,1100),
                "wind_speed":("m/s",0,80),"wind_gust":("m/s",0,100)}.items():
                if plausible(field(row,key),lower,upper) is not None:ns[key]+=1
    need(N==ROWS[year],"NOAA year raw row count differs from operator Stage06v3")
    raw.sort(key=lambda r:r["utc"])
    return raw,{"source_year":year,"NOAA_records":N,
        "NOAA_year_first_UTC":str(first),"NOAA_year_last_UTC":str(last),
        "temperature_n_plausible":ns["temperature"],
        "station_level_pressure_n_plausible":ns["station_level_pressure"],
        "sea_level_pressure_n_plausible":ns["sea_level_pressure"],
        "wind_speed_n_plausible":ns["wind_speed"],
        "wind_gust_n_plausible":ns["wind_gust"],
        "NOAA_source_original_PSV_sha256":FILESHA[year]}
def match_event(case,t,v,center,series,hyp,offset,noaa,secondary=False):
    base,units,low,high=noaa
    t0=dt.datetime.fromisoformat(t)-dt.timedelta(hours=offset)
    nearby=[r for r in series if abs((r["utc"]-t0).total_seconds())<=6*3600]
    usable=[]
    for rec in nearby:
        n=plausible(field(rec["data"],base),low,high)
        if n is not None:usable.append((rec,n))
    usable.sort(key=lambda x:(abs((x[0]["utc"]-t0).total_seconds()),x[0]["utc"]))
    rec,value=usable[0] if usable else (None,None)
    r=rec["data"] if rec else {}
    o={"event_id":case,"tower_native_timestamp":t,
       "tower_variable":v,"tower_F_value":center.get("F_flagged_HH"),
       "tower_F_QC":center.get("QC_current"),
       "tower_ERA_same_product":center.get("ERA_at_flagged_HH"),
       "NOAA_station":"ASN00009053 PEARCE RAAF",
       "station_distance_km":43.35,"hypothesis":hyp,
       "NOAA_variable":base,"NOAA_variable_unit":units,
       "NOAA_nearest_UTC":str(rec["utc"]) if rec else "",
       "minutes_NOAA_minus_assumed_UTC":round((rec["utc"]-t0).total_seconds()/60,1) if rec else "",
       "NOAA_raw":field(r,base) if rec else "",
       "NOAA_numeric_within_physical_screen":value if rec else "",
       "NOAA_Quality_Code":field(r,base+"_Quality_Code") if rec else "",
       "NOAA_Measurement_Code":field(r,base+"_Measurement_Code") if rec else "",
       "NOAA_Report_Type":field(r,base+"_Report_Type") if rec else "",
       "NOAA_Source_Code":field(r,base+"_Source_Code") if rec else "",
       "NOAA_Source_Station_ID":field(r,base+"_Source_Station_ID") if rec else "",
       "valid_hours_within_6h":len(usable),
       "NOAA_pressure_is_station_level":(base=="station_level_pressure"),
       "NOAA_pressure_or_wind_is_NOT_tower_equivalent":True,
       "source_alignment_approved":False,"scientific_repair_approved":False}
    return o
def test():
    need(utc("2016-05-07T08:00:00Z")==dt.datetime(2016,5,7,8),"utc time")
    need(plausible("1012.5",850,1100)==1012.5 and
         plausible("-9999",850,1100) is None,"original hPa")
    need(norm("station_level_pressure_Quality_Code")=="stationlevelpressurequalitycode",
         "NOAA original column")
    need(len(EVENTS)==5 and len(FILESHA)==3,"5 cases 3 years")
    need(2*sum(2 if v in EXTRA else 1 for _,_,v in EVENTS)==16,
         "5 event / two alignment / ancillary row-count invariant")
    print("AU-GIN STAGE07 SELF-TEST PASS | GHCNh raw QC/UTC, 5 events x 2 hypotheses; READ ONLY")
def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--self-test",action="store_true")
    ap.add_argument("--out",type=Path)
    args=ap.parse_args()
    if args.self_test:return test()
    o=args.out
    need(o is not None and o.parent.resolve()==H.resolve() and
         not o.exists() and not o.is_symlink(),
         "Only new immediate HOME output directory is permitted")
    p05=json.loads((S05/"stage05_AU_Gin_28event_preBOM_science_HOLD.json").read_text())
    need(p05.get("source_zip_SHA256")==ZIP_SHA and
         p05.get("original_44_screen_flags")==44 and
         p05.get("unique_flagged_HH")==39 and
         p05.get("number_of_grouped_events")==28 and
         p05.get("AD400_authorised") is False,
         "Operator Stage05 provenance guard changed")
    p06=json.loads((S06/"stage06_AU_Gin_official_NOAA_station_and_2012_2016_2019_SCIENCE_HOLD.json").read_text())
    need(p06.get("station_selection_status")==
         "SECONDARY_PEARCE_RAAF_VERIFIED_NOT_GINGIN_AERO" and
         p06.get("noaa_Gingin_Aero_GHCNh_exact_match_count")==0 and
         p06.get("AD400_authorised") is False,
         "Operator Stage06v3 Pearce-only discovery guard changed")
    evidence=p06.get("original_NOAA_PSV_source_years",[])
    need(len(evidence)==3 and all(x.get("status")=="ORIGINAL_PSV_AVAILABLE" for x in evidence),
         "Operator 2012/2016/2019 NOAA real years missing")
    need({x.get("year"):x.get("file_sha256") for x in evidence}==FILESHA,
         "NOAA Stage06v3 original PSV year source hashes changed")
    original,center_sha=read_previous_centers()
    out=[];yearmeta=[]
    for y in sorted(FILESHA):
        file=SRC/("GHCNh_"+GH+"_"+str(y)+".psv")
        need(sha(file)==FILESHA[y],"NOAA original year PSV SHA mismatch: "+str(y))
        series,meta=records_and_meta(file,y)
        yearmeta.append(meta)
        for case,t,v in EVENTS:
            if dt.datetime.fromisoformat(t).year!=y:continue
            for hyp,offset in (("native_as_UTC_UNVERIFIED",0),
                               ("native_as_AWST_UTCplus8_UNVERIFIED",8)):
                out.append(match_event(case,t,v,original[case],series,hyp,offset,NOAA[v]))
                if v=="PA":
                    out.append(match_event(case,t,v,original[case],series,hyp,offset,EXTRA["PA"],True))
                if v=="WS":
                    out.append(match_event(case,t,v,original[case],series,hyp,offset,EXTRA["WS"],True))
    need(len(out)==16,"Expected 5 main events x 2 alignments + 2 PA MSL + 1 WS gust times 2 = 16 rows")
    report={"site":"AU-Gin","stage":"Stage07 NOAA Pearce five original event QC/clock evidence",
        "source_GHCNh_station":"ASN00009053 PEARCE RAAF", "not_Gingin_Aero":True,
        "source_GHCNh_verified_distance_km":43.35,
        "original_tower_FLUXNET_zip_SHA256":ZIP_SHA,
        "actual_Stage05_report_SHA256":sha(S05/"stage05_AU_Gin_28event_preBOM_science_HOLD.json"),
        "actual_Stage05_44_neighbour_F_QC_SHA256":center_sha,
        "actual_Stage06v3_report_SHA256":sha(S06/"stage06_AU_Gin_official_NOAA_station_and_2012_2016_2019_SCIENCE_HOLD.json"),
        "original_NOAA_PSV_years":yearmeta,
        "case_count":5,"two_UNAPPROVED_clock_hypotheses":True,
        "NOAA_nearest_values_within_6h_not_exact_halfhour_pairs":True,
        "NOAA_QC_source_codes_retained_without_quality_interpretation":True,
        "measured_station_pressure_hPa_not_QNH_sea_level":True,
        "airport_tower_station_separation_precludes_direct_repair":True,
        "Gingin_Aero_historical_BoM_data_still_not_acquired":True,
        "AU_Gin_15_full_year_measured_tower_requirement_met":False,
        "source_science_release":False,"AD400_authorised":False,
        "all_sources_and_CIME_Surface_Slurm_untouched":True}
    o.mkdir(mode=0o700,exist_ok=False)
    save(o/"stage07_AU_Gin_5event_Pearce_raw_UTC_AWST_QC_source_comparison.tsv",OUTFIELDS,out)
    save(o/"stage07_AU_Gin_NOAA_3year_source_variable_coverage.tsv",HEADER_FIELDS,yearmeta)
    (o/"stage07_AU_Gin_5event_noaa_pearce_science_HOLD.json").write_text(
        json.dumps(report,indent=2,ensure_ascii=False),encoding="utf-8")
    print("STAGE07 INDEPENDENT NOAA ORIGINAL PSVs 3/3 SHA256 VERIFIED")
    for meta in yearmeta:
        print("NOAA_SOURCE_YEAR",meta["source_year"],"N",meta["NOAA_records"],
              "UTC_FIRST",meta["NOAA_year_first_UTC"],
              "UTC_LAST",meta["NOAA_year_last_UTC"],
              "TEMPERATURE_FINITE",meta["temperature_n_plausible"],
              "STATION_PRESSURE_FINITE",meta["station_level_pressure_n_plausible"],
              "SEA_LEVEL_PRESSURE_FINITE",meta["sea_level_pressure_n_plausible"],
              "WIND_SPEED_FINITE",meta["wind_speed_n_plausible"],
              "WIND_GUST_FINITE",meta["wind_gust_n_plausible"])
    for r in out:
        print("EVENT_NOAA",r["event_id"],r["hypothesis"],
              "TOWER",r["tower_F_value"],r["tower_variable"],
              "NOAA_VAR",r["NOAA_variable"],"NOAA_RAW",r["NOAA_raw"],
              "NOAA_UTC",r["NOAA_nearest_UTC"],
              "DELTA_MIN",r["minutes_NOAA_minus_assumed_UTC"],
              "VALID_IN_6H",r["valid_hours_within_6h"],
              "NOAA_QC",r["NOAA_Quality_Code"],
              "NOAA_SRC",r["NOAA_Source_Code"])
    print("STAGE07 READONLY INDEPENDENT SOURCE TRIAGE PASS; CLOCK/QA SCIENCE HOLD")
    print("REPORT_DIR",o)
if __name__=="__main__":main()
