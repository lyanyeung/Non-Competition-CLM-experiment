#!/usr/bin/env python3
"""AU-Gin Stage06v2: independent NOAA GHCNh station identity and source observations.

Two phases:
 discover: original official NOAA GHCNh station-list CSV => exact WMO 95612
    AND plausible GINGIN AERO location/name. Only a uniquely matched actual
    GHCN station ID is accepted. Do not invent source IDs.
 audit: read exact official GHCNh year-PSV files for 2012, 2016, 2019,
    source SHA each file, validate header/time and print original hourly
    observations at ±8h/local-versus-UTC alternative alignments around the
    source-flagged PA/TA/WS events. Preserve original NOAA QC/source codes.

NOAA docs: https://www.ncei.noaa.gov/oa/global-historical-climatology-network/hourly/doc/ghcnh_DOCUMENTATION.pdf
Station list: https://www.ncei.noaa.gov/oa/global-historical-climatology-network/hourly/doc/ghcnh-station-list.csv
2012 source candidate: https://www.ncei.noaa.gov/oa/global-historical-climatology-network/hourly/access/by-year/2012/psv/GHCNh_<grounded_id>_2012.psv

Independent airport is ~17 km from AU-Gin tower, differs in elevation
73m versus ~51m: field observations are independent but not interchangeable.
Do NOT infer a corrected station pressure using MSL or QNH; do NOT equate
hourly wind speed/gust with 30min tower sonic wind. UTC vs WST (+8) source
convention is not yet established; output TWO alternative windows.
No files are downloaded by this Python script. No edits, DATM, AD400/Slurm.
"""
from __future__ import annotations
import argparse,csv,datetime as dt,hashlib,json,math,re
from pathlib import Path
from collections import Counter
HOME=Path.home()
STAGE05=HOME/"ozflux_AU_Gin_stage05_20261105T034925Z/stage05_AU_Gin_28event_preBOM_science_HOLD.json"
SRC_SHA="acd78491b6f5f2c1374da2076d73a6c8b6ef430b256b78da3d300656943d6f14"
AERO=(-31.4628,115.8642)
TOWER=(-31.3764,115.7139)
YEARS=(2012,2016,2019)
CASES=(("2012_PA_1","2012-06-09 08:30:00","PA"),
       ("2012_PA_2","2012-06-10 13:30:00","PA"),
       ("2016_TA_1","2016-05-07 16:00:00","TA"),
       ("2016_TA_2","2016-05-20 18:00:00","TA"),
       ("2019_WS_1","2019-09-13 03:00:00","WS"))
DOCBASE="https://www.ncei.noaa.gov/oa/global-historical-climatology-network/hourly/access/by-year"
CSVURL="https://www.ncei.noaa.gov/oa/global-historical-climatology-network/hourly/doc/ghcnh-station-list.csv"
REPORT_COLS=("event_id","source_native_time_NOT_YET_UTC",
             "hypothesis","NOAA_UTC_timestamp",
             "NOAA_station_id","NOAA_station_name",
             "hourly_vs_30min_unaligned",
             "NOAA_raw_temperature","NOAA_temperature_Quality_Code",
             "NOAA_raw_wind_speed","NOAA_wind_speed_Quality_Code",
             "NOAA_raw_wind_gust","NOAA_wind_gust_Quality_Code",
             "NOAA_raw_station_level_pressure","NOAA_station_level_pressure_Quality_Code",
             "NOAA_raw_sea_level_pressure","NOAA_sea_level_pressure_Quality_Code",
             "NOAA_raw_dew_point_temperature",
             "NOAA_dew_point_temperature_Quality_Code",
             "NOAA_raw_relative_humidity",
             "NOAA_relative_humidity_Quality_Code",
             "NOAA_original_row_source_codes","independent_station_date_is_UTC",
             "source_time_zone_alignment_APPROVED",
             "source_pressures_are_not_interchangeable",
             "independent_reference_is_not_a_repair")
def need(ok,reason):
    if not ok:raise RuntimeError(str(reason))
def digest(p):
    p=Path(p)
    need(p.is_file() and not p.is_symlink(),"Source missing/linked "+str(p))
    h=hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda:f.read(4<<20),b""):h.update(chunk)
    return h.hexdigest()
def distance(a,b):
    p,q=map(math.radians,(a[0],b[0]))
    lat=q-p
    lon=math.radians(b[1]-a[1])
    h=math.sin(lat/2)**2+math.cos(p)*math.cos(q)*math.sin(lon/2)**2
    return 6371*2*math.asin(math.sqrt(h))
def num(v):
    try:return float(str(v).strip())
    except (TypeError,ValueError):return None
def norm(k):
    return re.sub(r"[^A-Za-z0-9]","",str(k)).upper()
def prop(r,*keys):
    d={norm(k):str(v or "").strip() for k,v in r.items() if k is not None}
    for k in keys:
        if d.get(norm(k)):return d[norm(k)]
    return ""
def official_stations(path):
    result=[];near=[]
    with path.open(encoding="utf-8-sig",newline="") as f:
        reader=csv.DictReader(f)
        need(reader.fieldnames and
             {"LATITUDE","LONGITUDE"}.issubset(set(norm(x) for x in reader.fieldnames)),
             "NOAA GHCNh official station-list CSV not recognised")
        need("ID" in set(norm(x) for x in reader.fieldnames) or
             "GHCNID" in set(norm(x) for x in reader.fieldnames),
             "NOAA CSV lacks station identifier")
        for r in reader:
            sid=prop(r,"ID","GHCN_ID")
            if not re.fullmatch("[A-Za-z0-9]{11}",sid):continue
            lat=num(prop(r,"LATITUDE"));lon=num(prop(r,"LONGITUDE"))
            if lat is None or lon is None:continue
            if not(-90<=lat<=90 and -180<=lon<=180):continue
            name=prop(r,"NAME")
            wmo=prop(r,"WMO_ID","WMO ID","WMO")
            km=distance((lat,lon),TOWER)
            candidate={"id":sid,"name":name,"wmo":wmo,"lat":lat,"lon":lon,
                      "elevation":num(prop(r,"ELEVATION")),
                      "distance_to_tower_km":round(km,3),
                      "distance_to_BoM_aero_km":round(distance((lat,lon),AERO),3)}
            if km<=80:near.append(candidate)
            if (wmo=="95612" and distance((lat,lon),AERO)<8
                    and "GINGIN" in name.upper()):
                result.append(candidate)
    near.sort(key=lambda x:x["distance_to_tower_km"])
    need(len(near)>=1,"No valid stations within 80km; likely wrong station CSV")
    return result,near
def timestamp(t):
    s=str(t or "").strip()
    if not s:return None
    if s.endswith("Z"):s=s[:-1]+"+00:00"
    try:
        result=dt.datetime.fromisoformat(s)
        if result.tzinfo is not None:
            result=result.astimezone(dt.timezone.utc).replace(tzinfo=None)
        return result
    except ValueError:return None
def column(row,base,suffix=""):
    target=norm(base+suffix)
    for k,v in row.items():
        if k and norm(k)==target:return v
    return None
def serialize_station(s):
    return {"name":s["name"],"GHCN_ID":s["id"],
            "source_station_lat":s["lat"],"source_station_lon":s["lon"],
            "source_WMO":s["wmo"],"aero_elevation_m":s["elevation"],
            "distance_to_flux_tower_km":s["distance_to_tower_km"]}
def csvrows(path,year):
    # Validate raw PSV format and report original columns. Do not invent unit
    # conversions or ignore quality flags. GHCNh timestamps are UTC.
    out=[];cols=None;tscol=None;records=0
    with path.open(encoding="utf-8-sig",newline="") as f:
        first=f.readline()
        need("|" in first and "<html" not in first.lower(),
             "NOAA station-year file is not a PSV (possible HTML/HTTP error)")
        f.seek(0)
        rdr=csv.DictReader(f,delimiter="|")
        cols=rdr.fieldnames
        need(cols is not None and len(cols)>=30,
             "NOAA GHCNh year PSV has unexpected header")
        for c in cols:
            if norm(c) in ("DATETIME","DATE","TIMESTAMP","OBSERVATIONTIME"):
                tscol=c;break
        need(tscol is not None,"No documented GHCNh UTC datetime column in "+str(path))
        seen=0
        for row in rdr:
            records+=1
            t=timestamp(row.get(tscol))
            if t is None:continue
            if t.year not in (year-1,year,year+1):continue
            for label,source,variable in CASES:
                t0=dt.datetime.fromisoformat(source)
                for hypothesis,offset in (("source_native_as_UTC",0),
                                          ("source_native_WST_UTCplus8",8)):
                    center=t0-dt.timedelta(hours=offset)
                    if abs((t-center).total_seconds())>6*3600:continue
                    k={
                       "event_id":label,
                       "source_native_time_NOT_YET_UTC":source,
                       "hypothesis":hypothesis,
                       "NOAA_UTC_timestamp":t.isoformat(sep=" "),
                       "hourly_vs_30min_unaligned":True,
                       "NOAA_raw_temperature":column(row,"temperature"),
                       "NOAA_temperature_Quality_Code":column(row,"temperature","_Quality_Code"),
                       "NOAA_raw_wind_speed":column(row,"wind_speed"),
                       "NOAA_wind_speed_Quality_Code":column(row,"wind_speed","_Quality_Code"),
                       "NOAA_raw_wind_gust":column(row,"wind_gust"),
                       "NOAA_wind_gust_Quality_Code":column(row,"wind_gust","_Quality_Code"),
                       "NOAA_raw_station_level_pressure":column(row,"station_level_pressure"),
                       "NOAA_station_level_pressure_Quality_Code":column(row,"station_level_pressure","_Quality_Code"),
                       "NOAA_raw_sea_level_pressure":column(row,"sea_level_pressure"),
                       "NOAA_sea_level_pressure_Quality_Code":column(row,"sea_level_pressure","_Quality_Code"),
                       "NOAA_raw_dew_point_temperature":column(row,"dew_point_temperature"),
                       "NOAA_dew_point_temperature_Quality_Code":column(row,"dew_point_temperature","_Quality_Code"),
                       "NOAA_raw_relative_humidity":column(row,"relative_humidity"),
                       "NOAA_relative_humidity_Quality_Code":column(row,"relative_humidity","_Quality_Code"),
                       "NOAA_original_row_source_codes":str({k:v for k,v in row.items()
                          if k and norm(k).endswith("SOURCECODE") and v and v.strip()})[:700],
                       "independent_station_date_is_UTC":True,
                       "source_time_zone_alignment_APPROVED":False,
                       "source_pressures_are_not_interchangeable":True,
                       "independent_reference_is_not_a_repair":True}
                    out.append(k)
    return {"year":year,"raw_column_names":cols,"datetime_column":tscol,
            "observations_in_original_year_file":records,
            "event_nearby_record_count":len(out)},out
def save(path,cols,rows):
    with path.open("x",encoding="utf-8",newline="") as f:
        writer=csv.DictWriter(f,fieldnames=cols,delimiter="\t",
                             extrasaction="raise")
        writer.writeheader();writer.writerows(rows)
def selftest():
    need(17<distance(AERO,TOWER)<18,"BoM station distance")
    need(timestamp("2016-05-07T08:00:00Z")==dt.datetime(2016,5,7,8),"NOAA UTC")
    need(norm("wind_speed_Quality_Code")=="WINDSPEEDQUALITYCODE","NOAA metadata columns")
    need(len(YEARS)==3 and len(CASES)==5,"source cases")
    print("OZFLUX AU-GIN STAGE06 SELFTEST PASS | GHCNh source station identity, UTC dual-window and no automatic repairs")
def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--self-test",action="store_true")
    p.add_argument("--phase",choices=("discover","audit"))
    p.add_argument("--station-list",type=Path)
    p.add_argument("--years-dir",type=Path)
    p.add_argument("--out",type=Path)
    a=p.parse_args()
    if a.self_test:return selftest()
    need(a.phase and a.station_list and a.out and
         a.station_list.is_file() and not a.station_list.is_symlink(),
         "--phase, original NOAA --station-list, and --out needed")
    need(a.out.parent.resolve()==HOME.resolve() and
         not a.out.exists() and not a.out.is_symlink(),
         "New direct HOME output path required")
    prev=json.loads(STAGE05.read_text(encoding="utf-8"))
    need(prev.get("source_zip_SHA256")==SRC_SHA and
         prev.get("original_44_screen_flags")==44 and
         prev.get("unique_flagged_HH")==39 and
         prev.get("number_of_grouped_events")==28 and
         prev.get("source_context_halfhours_in_windows")==678 and
         prev.get("AD400_authorised") is False,
         "Operator Stage05 original 44/39/28/678 source/HOLD receipt changed")
    sh=digest(a.station_list)
    selected,near=official_stations(a.station_list)
    # Do not choose a nearby alternative merely by location.
    status="EXACT_WMO_NAME_COORD_MATCH" if len(selected)==1 else (
            "AMBIGUOUS_EXACT_ID" if selected else "NO_EXACT_95612_MATCH")
    report={"site":"AU-Gin",
        "stage":"Stage06 NOAA independent station and original source inspection",
        "noaa_official_station_list_source_url":CSVURL,
        "noaa_official_station_list_SHA256":sh,
        "actual_stage05_source_receipt_SHA256":digest(STAGE05),
        "Gingin_Aero_BoM_station":"009178",
        "Gingin_Aero_BoM_WMO":"95612",
        "Gingin_Aero_BoM_coordinates":AERO,
        "AU_Gin_tower_coordinates":TOWER,
        "station_selection_status":status,
        "matched_official_station_candidates":selected,
        "nearest_official_80km_stations":near[:25],
        "phase":a.phase,
        "real_source_years_downloaded_by_this_python_script":False,
        "NOAA_GHCNh_time_source_is_UTC":True,
        "original_FLUXNET_source_UTC_or_WST_NOT_YET_VERIFIED":True,
        "independent_source_approval":False,
        "no_Tower_DATM_Surface_CIME_Slurm_writes":True,
        "AD400_authorised":False}
    a.out.mkdir(mode=0o700,parents=False,exist_ok=False)
    reportrows=[]
    if a.phase=="audit":
        need(len(selected)==1,
             "Exactly one official Gingin Aero GHCNh ID needed before external year audit")
        need(a.years_dir is not None and
             a.years_dir.is_dir() and not a.years_dir.is_symlink(),
             "NOAA historical year source directory missing")
        station=selected[0]
        evidence=[]
        for year in YEARS:
            src=a.years_dir/("GHCNh_"+station["id"]+"_"+str(year)+".psv")
            if not src.exists():
                print("NOAA_HISTORICAL_YEAR_UNAVAILABLE",year,src)
                evidence.append({"year":year,"status":"NOT_DOWNLOADED"})
                continue
            need(src.stat().st_size>100 and not src.is_symlink(),
                 "Bad NOAA historical year download "+str(src))
            summary,points=csvrows(src,year)
            summary["file_sha256"]=digest(src)
            summary["status"]="ORIGINAL_PSV_AVAILABLE"
            evidence.append(summary)
            for row in points:
                row["NOAA_station_id"]=station["id"]
                row["NOAA_station_name"]=station["name"]
            reportrows.extend(points)
            print("NOAA_YEAR_READONLY",year,"RECORDS",summary["observations_in_original_year_file"],
                  "NEAR_EVENT_UTC_ROWS",len(points),"SHA256",summary["file_sha256"])
        report["original_NOAA_PSV_source_years"]=evidence
        report["event_external_original_raw_comparisons_no_time_or_unit_conversions"]=len(reportrows)
        save(a.out/"stage06_NOAA_GHCNh_original_raw_UTC_event_window_evidence.tsv",
             REPORT_COLS,reportrows)
    (a.out/"stage06_AU_Gin_official_NOAA_station_and_2012_2016_2019_SCIENCE_HOLD.json").write_text(
        json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    print("NOAA_OFFICIAL_STATION_LIST_SHA256",sh)
    print("NOAA_NEAREST_80KM",json.dumps(near[:8],ensure_ascii=False))
    print("NOAA_EXACT_GINGIN_AERO_MATCHES",json.dumps(selected,ensure_ascii=False))
    print("NOAA_STATION_SELECTION_STATUS",status)
    if len(selected)==1:
        sid=selected[0]["id"]
        print("NOAA_SELECTED_GHCN_ID",sid)
        for year in YEARS:
            print("NOAA_YEAR_URL",year,
                DOCBASE+"/"+str(year)+"/psv/GHCNh_"+sid+"_"+str(year)+".psv")
    print("STAGE06 NOAA STATION AND RAW EVENT SOURCE READONLY; NO SCIENCE RELEASE/AD400")
    print("REPORT_DIR",a.out)
if __name__=="__main__":main()
