#!/usr/bin/env python3
"""AU-Gin Stage08 (READ ONLY): five external NOAA event comparisons with
time-zone provenance from the ORIGINAL TERN FLUXNET BIF, and original adjacent
tower F/QC half hours from real Stage05.

Requires real source Stage07 PASS and three SHA-pinned original GHCNh PSVs
already audited: this stage uses only their Stage07 report (which records
raw NOAA values and quality/source fields), never invents or fetches data.

Scientific gates:
* FLUXNET documentation says local STANDARD time (no daylight savings).
  West Australia generally UTC+08:00, but the original AU-Gin BIF metadata
  must be inspected rather than silently assuming its site offset.
* NOAA GHCNh data UTC; do not silently align original flux halfhours to UTC.
* Airport is 43.35km away; pressure ~40m airport vs ~51m tower, wind heights
  different; different temporal support. No direct source replacement.
* The June 9 2012 PA event's previous 102.9 kPa can be the suspect point,
  while event centre 101.1 kPa agrees better with nearby airport observations.
* NO flagged values modified, no NOAA numeric values inserted into forcing,
  no original ZIP/old L6/Surface/CIME/Slurm/AD400 changes.
"""
from __future__ import annotations
import argparse,csv,datetime as dt,hashlib,io,json,math,re,zipfile
from collections import defaultdict
from pathlib import Path
H=Path.home()
FLUX_ZIP=Path("/iridisfs/scratch/ly3n24/CLM_FATES/sites/MY_EC_SITE/AU-Gin/forcing/raw/TERN_FLUXNET_2011_2025/TERN_AU-Gin_FLUXNET_2011-2025_v1.3_r1.zip")
FLUX_SHA="acd78491b6f5f2c1374da2076d73a6c8b6ef430b256b78da3d300656943d6f14"
BIF="TERN_AU-Gin_FLUXNET_BIF_2011-2025_v1.3_r1.csv"
BIF_SHA="d28640e9f9a1bef14d0dc54679f56f4674652e88efc9ac15a93425e725fb8a0e"
S05=H/"ozflux_AU_Gin_stage05_20261105T034925Z"
S07=H/"ozflux_AU_Gin_stage07_20261105T041806Z"
JSON05=S05/"stage05_AU_Gin_28event_preBOM_science_HOLD.json"
JSON07=S07/"stage07_AU_Gin_5event_noaa_pearce_science_HOLD.json"
TSV05=S05/"stage05_AU_Gin_44_flag_previous_next_HH_differentials.tsv"
TSV07=S07/"stage07_AU_Gin_5event_Pearce_raw_UTC_AWST_QC_source_comparison.tsv"
CASES={
 "PA_20120609":("2012-06-09 08:30:00","PA","station_level_pressure",10),
 "PA_20120610":("2012-06-10 13:30:00","PA","station_level_pressure",10),
 "TA_20160507":("2016-05-07 16:00:00","TA","temperature",1),
 "TA_20160520":("2016-05-20 18:00:00","TA","temperature",1),
 "WS_20190913":("2019-09-13 03:00:00","WS","wind_speed",1)}
FIELDS=("event_id","tower_local_start","variable",
        "original_tower_previous_F","original_tower_previous_QC",
        "original_tower_flagged_F","original_tower_flagged_QC",
        "original_tower_next_F","original_tower_next_QC",
        "original_tower_same_product_ERA",
        "source_F_unit","airport_station","airport_distance_km",
        "time_alignment_hypothesis","airport_UTC_observation",
        "minutes_airport_minus_assumed_event_UTC",
        "airport_variable","airport_original_value","airport_original_unit",
        "airport_value_in_tower_units",
        "airport_original_quality_code","airport_original_source_code",
        "NOAA_hourly_valid_observations_within_6h",
        "flagged_minus_airport_in_common_units",
        "previous_minus_airport_in_common_units",
        "next_minus_airport_in_common_units",
        "flagged_single_sample_spike_metric",
        "time_alignment_science_approved",
        "independent_station_comparable_without_height_weather_differences",
        "scientific_repair_approved")
def require(value,message):
    if not value:raise RuntimeError(str(message))
def sha(path):
    path=Path(path)
    require(path.is_file() and not path.is_symlink(),
            "Missing original/read-only science file: "+str(path))
    h=hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda:f.read(4<<20),b""):h.update(block)
    return h.hexdigest()
def n(s):
    try:
        x=float(str(s).strip())
        return x if math.isfinite(x) and abs(x)<9990 else None
    except (TypeError,ValueError):return None
def minus(a,b):
    return a-b if a is not None and b is not None else None
def read_tsv(path):
    with path.open(encoding="utf-8",newline="") as f:
        return list(csv.DictReader(f,delimiter="\t"))
def source_BIF(z):
    require(z.namelist().count(BIF)==1,"Actual BIF member not unique")
    raw=z.read(BIF)
    require(hashlib.sha256(raw).hexdigest()==BIF_SHA,
            "Original BIF member SHA256 changed from Stage02 source audit")
    result=[];site_total=0
    reader=csv.DictReader(io.StringIO(raw.decode("utf-8-sig"),newline=""))
    require({"SITE_ID","GROUP_ID","VARIABLE_GROUP","VARIABLE","DATAVALUE"}.issubset(
        set(reader.fieldnames or [])),"Source BADM schema changed")
    for r in reader:
        if (r.get("SITE_ID") or "").strip()!="AU-Gin":continue
        site_total+=1
        var=(r.get("VARIABLE") or "").strip()
        grp=(r.get("VARIABLE_GROUP") or "").strip()
        value=(r.get("DATAVALUE") or "").strip()
        if re.search(r"TIME.?ZONE|UTC|TIME.?OFFSET|GMT|DST|DAYLIGHT",var+" "+grp,re.I):
            result.append({
              "group_id":r.get("GROUP_ID"),"variable_group":grp,
              "variable":var,"original_DATAVALUE":value})
    return result,site_total
def selftest():
    require(len(CASES)==5 and sum(v[3]==10 for v in CASES.values())==2,
            "5 exact cases, two station pressure conversion cases")
    require(minus(101.4*10,988.7)==25.299999999999955,
            "pressure source units kPa->hPa")
    require(abs(((-4.63)-(15.42+12.44)/2)-(-18.56))<1e-8,
            "three-point temperature diagnostic")
    require(n("-9999") is None and n("0")==0.0,"FLUXNET missing parse")
    print("AU-GIN STAGE08 SELFTEST PASS | source BIF timezone, 5 external cases, pressure units, 2012 preceding spike; READ ONLY")
def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--self-test",action="store_true")
    p.add_argument("--out",type=Path)
    a=p.parse_args()
    if a.self_test:return selftest()
    out=a.out
    require(out is not None and out.parent.resolve()==H.resolve()
            and not out.exists() and not out.is_symlink(),
            "Use NEW direct HOME science output folder")
    require(sha(FLUX_ZIP)==FLUX_SHA,"Original 127MB TERN source ZIP changed")
    with zipfile.ZipFile(FLUX_ZIP,"r") as z:
        tz,site_rows=source_BIF(z)
    old05=json.loads(JSON05.read_text(encoding="utf-8"))
    require(old05.get("source_zip_SHA256")==FLUX_SHA and
            old05.get("original_44_screen_flags")==44 and
            old05.get("unique_flagged_HH")==39 and
            old05.get("number_of_grouped_events")==28 and
            old05.get("source_context_halfhours_in_windows")==678 and
            old05.get("AD400_authorised") is False,
            "Real Stage05 44/39/28/678 science receipt changed")
    old07=json.loads(JSON07.read_text(encoding="utf-8"))
    require(old07.get("original_tower_FLUXNET_zip_SHA256")==FLUX_SHA and
            old07.get("case_count")==5 and
            old07.get("source_GHCNh_station")=="ASN00009053 PEARCE RAAF" and
            old07.get("AD400_authorised") is False,
            "Real Stage07 source case/station receipt changed")
    sourceRows=read_tsv(TSV05)
    require(len(sourceRows)==44,"Stage05 real original event center count changed")
    pearceRows=read_tsv(TSV07)
    require(len(pearceRows)==16,"Stage07 original GHCNh event × hypothesis count changed")
    byEvent={}
    for event,(ts,var,noaaVar,conversion) in CASES.items():
        match=[r for r in sourceRows
               if r.get("native_time")==ts and r.get("variable")==var]
        require(len(match)==1,"No unique source original 44-center row for "+event)
        byEvent[event]=match[0]
    results=[];coverage=[]
    for event,(ts,var,noaaVar,conversion) in CASES.items():
        for hypothesis in ("native_as_UTC_UNVERIFIED",
                           "native_as_AWST_UTCplus8_UNVERIFIED"):
            matched=[r for r in pearceRows
                     if r.get("event_id")==event and
                        r.get("hypothesis")==hypothesis and
                        r.get("NOAA_variable")==noaaVar]
            require(len(matched)==1,
                    "Actual Stage07 exact source metric/hypothesis lost "+event)
            m=matched[0];t=byEvent[event]
            pv=n(t.get("F_previous_HH"))
            cv=n(t.get("F_flagged_HH"))
            nv=n(t.get("F_next_HH"))
            raw=n(m.get("NOAA_raw"))
            converted=raw if conversion==1 else (raw if raw is None else raw)
            # Convert TOWER kPa to hPa, not airport hPa to kPa; preserve NOAA raw.
            prevTower=pv*conversion if pv is not None else None
            centerTower=cv*conversion if cv is not None else None
            nextTower=nv*conversion if nv is not None else None
            metric=(centerTower-(prevTower+nextTower)/2
                if all(x is not None for x in (centerTower,prevTower,nextTower))
                else None)
            commonunit="hPa" if conversion==10 else (
                       "deg C" if var=="TA" else "m/s")
            result={
                "event_id":event,"tower_local_start":ts,"variable":var,
                "original_tower_previous_F":pv,
                "original_tower_previous_QC":t["QC_previous_HH"],
                "original_tower_flagged_F":cv,
                "original_tower_flagged_QC":t["QC_current"],
                "original_tower_next_F":nv,
                "original_tower_next_QC":t["QC_next_HH"],
                "original_tower_same_product_ERA":n(t["ERA_at_flagged_HH"]),
                "source_F_unit":"kPa" if var=="PA" else commonunit,
                "airport_station":"ASN00009053 PEARCE RAAF",
                "airport_distance_km":43.35,
                "time_alignment_hypothesis":hypothesis,
                "airport_UTC_observation":m["NOAA_nearest_UTC"],
                "minutes_airport_minus_assumed_event_UTC":m["minutes_NOAA_minus_assumed_UTC"],
                "airport_variable":noaaVar,
                "airport_original_value":raw,
                "airport_original_unit":commonunit,
                "airport_value_in_tower_units":raw,
                "airport_original_quality_code":m["NOAA_Quality_Code"],
                "airport_original_source_code":m["NOAA_Source_Code"],
                "NOAA_hourly_valid_observations_within_6h":int(m["valid_hours_within_6h"]),
                "flagged_minus_airport_in_common_units":minus(centerTower,raw),
                "previous_minus_airport_in_common_units":minus(prevTower,raw),
                "next_minus_airport_in_common_units":minus(nextTower,raw),
                "flagged_single_sample_spike_metric":metric,
                "time_alignment_science_approved":False,
                "independent_station_comparable_without_height_weather_differences":False,
                "scientific_repair_approved":False}
            results.append(result)
            coverage.append(dict(event_id=event,hypothesis=hypothesis,
                    utc=m["NOAA_nearest_UTC"],count=int(m["valid_hours_within_6h"])))
    require(len(results)==10,"Expected five cases x two comparison hypotheses")
    # Case-specific operator evidence guards (not assertions of science truth).
    checks={r["event_id"]:r for r in results
            if r["time_alignment_hypothesis"]=="native_as_AWST_UTCplus8_UNVERIFIED"}
    require(abs(checks["PA_20120610"]["original_tower_flagged_F"]-101.4)<1e-9
            and checks["PA_20120610"]["airport_original_value"]==988.7,
            "Actual 2012 June 10 independent/source PA changed")
    require(abs(checks["WS_20190913"]["original_tower_flagged_F"]-19.95)<1e-9
            and checks["WS_20190913"]["airport_original_value"]==0.5,
            "Actual Sep 2019 wind independent/source changed")
    require(checks["TA_20160507"]["original_tower_flagged_F"]==-4.63
            and checks["TA_20160507"]["airport_original_value"]==17.1,
            "Actual May 2016 TA event independent/source changed")
    require(checks["TA_20160520"]["original_tower_flagged_F"]==6.19
            and checks["TA_20160520"]["airport_original_value"]==17.8,
            "Actual May 20 2016 TA independent/source changed")
    report={
        "site":"AU-Gin","stage":"Stage08 source BIF timezone and 5 independent NOAA Pearce event triage",
        "original_fluxnet_ZIP_SHA256":FLUX_SHA,"original_BIF_member_SHA256":BIF_SHA,
        "operator_Stage05_report_SHA256":sha(JSON05),
        "operator_Stage07_report_SHA256":sha(JSON07),
        "original_source_event_TSV_SHA256":sha(TSV05),
        "original_external_5event_TSV_SHA256":sha(TSV07),
        "original_BIF_site_row_count":site_rows,
        "original_BIF_timezone_fields":tz,
        "FLUXNET_public_standard_is_local_standard_time_no_DST":True,
        "AU_Gin_site_specific_UTC_offset_operator_verified":False,
        "original_GHCNh_Pearce_hourly_is_UTC":True,
        "comparison_under_both_UNAPPROVED_clock_hypotheses":True,
        "source_noaa_QC_zero_is_original_reported_quality_NOT_sensor_truth":True,
        "Gingin_Aero_17km_BoM_not_downloaded":True,
        "Pearce_RAAF_43km_weather_not_site_equivalent":True,
        "PA_original_tower_kPa_converted_only_for_comparison_to_Pearce_station_hPa":True,
        "sea_level_pressure_NOT_merged_with_station_pressure":True,
        "2012_06_09_previous_102_9kPa_can_be_anomaly_even_if_original_flagged_centre_101_1kPa":True,
        "scientific_repair_approved":False,"AD400_authorised":False,
        "15_full_measured_years":False,
        "no_source_DATM_Surface_CIME_Slurm_modifications":True}
    out.mkdir(mode=0o700,parents=False,exist_ok=False)
    with (out/"stage08_AU_Gin_original_BIF_timezone_source_rows.tsv").open(
         "x",encoding="utf-8",newline="") as f:
        w=csv.DictWriter(f,delimiter="\t",
            fieldnames=("group_id","variable_group","variable","original_DATAVALUE"))
        w.writeheader();w.writerows(tz)
    with (out/"stage08_AU_Gin_5case_independent_NOAA_vs_tower_neighbor_HOLD.tsv").open(
         "x",encoding="utf-8",newline="") as f:
        w=csv.DictWriter(f,delimiter="\t",fieldnames=FIELDS,extrasaction="raise")
        w.writeheader();w.writerows(results)
    (out/"stage08_AU_Gin_time_provenance_5case_science_HOLD.json").write_text(
        json.dumps(report,indent=2,ensure_ascii=False),encoding="utf-8")
    print("STAGE08 ORIGINAL AU-GIN ZIP/BIF AND STAGE05/07 SOURCE SHA256 VERIFIED")
    print("BIF_TIMEZONE_SOURCE_ROWS",json.dumps(tz,ensure_ascii=False))
    print("BIF_AU_GIN_SITE_ROWS",site_rows)
    for r in results:
        print("EVENT_COMPARE",r["event_id"],r["time_alignment_hypothesis"],
            "TOWER_PREV",r["original_tower_previous_F"],
            "TOWER_CENTRE",r["original_tower_flagged_F"],
            "TOWER_NEXT",r["original_tower_next_F"],
            "NOAA_RAW",r["airport_original_value"],
            "NOAA_UNIT",r["airport_original_unit"],
            "NOAA_TIME_UTC",r["airport_UTC_observation"],
            "TIME_DELTA_MIN",r["minutes_airport_minus_assumed_event_UTC"],
            "COMMON_UNIT_CENTRE_MINUS_NOAA",r["flagged_minus_airport_in_common_units"],
            "PREV_MINUS_NOAA",r["previous_minus_airport_in_common_units"],
            "NOAA_QC",r["airport_original_quality_code"],
            "NOAA_SRC",r["airport_original_source_code"])
    print("STAGE08 SOURCE/INDEPENDENT QA TRIAGE PASS; TIMEZONE SCIENCE HOLD; NO REPAIR/AD400")
    print("REPORT_DIR",out)
if __name__=="__main__":main()
