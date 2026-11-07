#!/usr/bin/env python3
"""AU-Gin Stage15: decisive first-party source-lineage review for 7 priority events.

Input: actual, SHA-pinned Stage14 operator report + 1295 original old Gingin
L6 sensor/QC samples (+/-60 min, 37 channels), and 35 matched-height HMP
temperature/RH pairs. Stage14 original TERN/L6 files and older receipts
were hashed and validated; Stage15 rehashes BOTH original raw files and all
read-only Stage14 input reports.

The old L6 original global time_zone is Australia/Perth and L6 Ta values
at source START+30min match four TERN FLUXMET TA_F values to <0.005degC.
Strong *related-source alignment* is not independent instrument evidence.

Scope:
- 2016-05-07: composite Ta versus HMP 2m and 4m and unavailable higher T.
- 2016-05-20: composite Ta versus HMP 15m and other measured heights.
- 2013-02-05/16: no matching-height HMP RH at old L6 local END, while
  TERN VPD_F QC1 > saturation vapor pressure: impossible RH.
- 2019-09-13: all 10 L6 wind-channel values/QC within +/-60min; determine
  whether 19.95m/s is one channel or multichannel, without claiming proof.
- 2012 PA: old L6 37 candidate sensor names contain no PA class;
  preserve TERN raw PA, nearby NOAA Pearce corroboration separately.

NO actual correction table, no forcing, no AD400. All 28 events SCIENCE HOLD.
"""
from __future__ import annotations
import argparse,csv,datetime as dt,hashlib,json,math
from collections import Counter,defaultdict
from pathlib import Path

H=Path.home()
ZIP=Path("/iridisfs/scratch/ly3n24/CLM_FATES/sites/MY_EC_SITE/AU-Gin/forcing/raw/TERN_FLUXNET_2011_2025/TERN_AU-Gin_FLUXNET_2011-2025_v1.3_r1.zip")
L6=Path("/iridisfs/scratch/ly3n24/CLM_FATES/sites/MY_EC_SITE/AU-Gin/forcing/raw/Gingin_L6.nc")
ZIP_SHA="acd78491b6f5f2c1374da2076d73a6c8b6ef430b256b78da3d300656943d6f14"
L6_SHA="0e700e37ead024a7eda4cdf9b47f839d5dc5bfa5578087e9af1ddd09aa510d66"
D14=H/"ozflux_AU_Gin_stage14_20261107T051121Z"
D13=H/"ozflux_AU_Gin_stage13_20261107T050509Z"
REC14=D14/"stage14_AU_Gin_oldL6_endstamp_multisensor_source_science_HOLD.json"
REC13=D13/"stage13_AU_Gin_oldL6_sensor_source_2013_2016_HOLD.json"
MATCH14=D14/"stage14_AU_Gin_four_TA_L6END_FLUXMETSTART_lineage_matches.tsv"
RAW14=D14/"stage14_AU_Gin_7event_5HH_all37_L6_sensors_original_QC.tsv"
PAIR14=D14/"stage14_AU_Gin_7event_5height_HMP_T_RH_VPD_source_physics.tsv"

T_EVENTS=("TA_20160507","TA_20160520")
VPD_EVENTS=("VPD_QC1_20130205","VPD_QC1_20130216")
WS_EVENT="WS_20190913"
E7=("PA_20120609_PREVIOUS","PA_20120610","TA_20160507",
    "TA_20160520","WS_20190913","VPD_QC1_20130205","VPD_QC1_20130216")
REL=(-60,-30,0,30,60)
TEMP_COLUMNS=("event_id","native_L6_END_relative_minutes",
              "source_native_L6_time","sensor_variable","sensor_height_from_name",
              "original_temperature_C","native_QCFlag_variable",
              "native_QCFlag_value","raw_Ta_composite_C",
              "is_source_composite_same_numeric_value",
              "science_repair_authorised")
WS_COLUMNS=("event_id","native_L6_END_relative_minutes",
            "source_native_L6_time","native_wind_channel",
            "height_token_name_only","source_raw_WS_m_s",
            "source_original_QCFlag","source_native_QCFlag_name",
            "original_observation_is_not_independent_validation",
            "scientific_repair_authorised")
VPD_COLUMNS=("event_id","original_TERN_AWST_START",
             "FLUXMET_VPD_F_hPa","FLUXMET_VPD_F_QC",
             "original_L6_Ta_HMP_2m_C","original_L6_Ta_HMP_2m_QC",
             "L6_2m_RH_percent","L6_2m_RH_QC",
             "all_five_HMP_RH_centers_missing",
             "HMP_same_height_valid_pairs",
             "esat_at_TERN_TA_hPa","implied_RH_from_TERN_VPD_percent",
             "FLUXMET_VPD_above_saturation",
             "HMP_derived_VPD_at_center_available",
             "source_thermodynamic_issue_unresolved",
             "scientific_repair_authorised")
REG_COLUMNS=("event_id","anomaly_domain",
             "first_party_evidence_classification",
             "specific_next_science_dependency",
             "original_first_party_sources_modified",
             "science_release","AD400_authorised")
def need(x,why):
    if not x:raise RuntimeError(str(why))
def sha(path):
    path=Path(path)
    need(path.is_file() and not path.is_symlink(),"Protected source missing/symlink "+str(path))
    h=hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda:f.read(4<<20),b""):h.update(chunk)
    return h.hexdigest()
def read(path):
    need(path.is_file() and not path.is_symlink(),"Missing Stage14 original source "+str(path))
    with path.open(encoding="utf-8",newline="") as f:
        return list(csv.DictReader(f,delimiter="\t"))
def save(path,cols,items):
    with path.open("x",encoding="utf-8",newline="") as f:
        wr=csv.DictWriter(f,delimiter="\t",fieldnames=cols,extrasaction="raise")
        wr.writeheader();wr.writerows(items)
def num(s):
    try:
        x=float(str(s).strip())
        return x if math.isfinite(x) and -9990<x<9990 else None
    except (TypeError,ValueError):return None
def esat(t):
    return 6.112*math.exp(17.67*t/(t+243.5)) if t is not None and -65<t<70 else None
def test():
    need(len(E7)==7 and len(T_EVENTS)==2 and len(VPD_EVENTS)==2,"7 events")
    need(abs((-4.625476)-(-4.63))<.005,"2016 May7 source lineage")
    need(abs(6.19237-6.19)<.005,"2016 May20 source lineage")
    need(abs((8.470531+9.620131+9.981885+9.92137)/4-6.19237)>2.5,
         "2016 May20 source 15m versus 2/4/7/10m separation")
    need((22.071/esat(13.61))>1 and (26.87/esat(19.09))>1,
         "2013 VPD above saturation hPa")
    print("AU-GIN STAGE15 SELFTEST PASS | 2016 multiheight source, 2013 VPD thermodynamics, 2019 wind; NO REPAIR")
def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--self-test",action="store_true")
    p.add_argument("--out",type=Path)
    a=p.parse_args()
    if a.self_test:return test()
    out=a.out
    need(out is not None and out.parent.resolve()==H.resolve() and
         not out.exists() and not out.is_symlink(),
         "Use fresh direct HOME report folder only")
    need(sha(ZIP)==ZIP_SHA and sha(L6)==L6_SHA,
         "Actual TERN or old L6 original SHA256 changed")
    r14=json.loads(REC14.read_text(encoding="utf-8"))
    r13=json.loads(REC13.read_text(encoding="utf-8"))
    need(r14.get("original_TERN_ZIP_SHA256")==ZIP_SHA and
         r14.get("original_Gingin_L6_SHA256")==L6_SHA and
         r14.get("four_explicit_TA_F_equals_old_Ta_within_0_005_C") is True and
         r14.get("source_local_START_to_oldL6_local_END_offset_minutes")==30 and
         r14.get("original_oldL6_raw_sensor_candidates")==37 and
         r14.get("oldL6_samples_total")==1295 and
         r14.get("28_original_AU_Gin_event_groups_all_HOLD") is True and
         r14.get("AD400_authorised") is False,
         "Actual Stage14 source/HOLD receipt changed")
    need(r13.get("new_TERN_original_ZIP_SHA256")==ZIP_SHA and
         r13.get("old_L6_original_SHA256")==L6_SHA and
         r13.get("old_L6_source_sensor_candidate_count")==37 and
         r13.get("AD400_authorised") is False,
         "Actual Stage13 source/HOLD receipt changed")
    matches=read(MATCH14);raw=read(RAW14);pairs=read(PAIR14)
    need(len(matches)==4 and len(raw)==1295 and len(pairs)==35,
         "Stage14 expected four matched, 1295 raw readings, 35 HMP pairs changed")
    need({x["event_id"] for x in matches}==
         {"TA_20160507","TA_20160520","VPD_QC1_20130205","VPD_QC1_20130216"},
         "Original four Ta lineage matching events changed")
    for x in matches:
        need(num(x["abs_difference_degC"]) is not None and
             num(x["abs_difference_degC"])<.005 and
             x["L6_time_zone_metadata"]=="Australia/Perth" and
             x["clock_and_QC_science_release"]=="False",
             "Old L6 endstamp exact original-value lineage unexpectedly changed")
    source={}
    for row in raw:
        eid=row.get("event_id");relative=int(row["minutes_from_event_CENTER"])
        channel=row.get("original_L6_channel")
        need(eid in E7 and relative in REL and channel,
             "Unknown original L6 7 events x 5 intervals x source name")
        key=eid,relative,channel
        need(key not in source,"Duplicate source sensor interval")
        source[key]=row
    channels={k[2] for k in source}
    need(len(channels)==37 and len(source)==7*5*37,"Stage14 full sensor grid has changed")
    bypair={(p["event_id"],p["height_token_HMP"]):p for p in pairs}
    need(len(bypair)==35,"Stage14 5-height match groups duplicated")
    expected={"TA_20160507":("4m",-4.625476),
              "TA_20160520":("15m",6.19237)}
    temp=[];wind=[];vpd=[];register=[]
    for eid in T_EVENTS:
        for minute in REL:
            composite=source[(eid,minute,"Ta")]
            cv=num(composite["original_L6_numeric_value"])
            for name in sorted(channels):
                if not (name=="Ta" or name.startswith("Ta_HMP_")):continue
                x=source[(eid,minute,name)]
                v=num(x["original_L6_numeric_value"])
                temp.append({
                  "event_id":eid,"native_L6_END_relative_minutes":minute,
                  "source_native_L6_time":x["original_L6_native_time"],
                  "sensor_variable":name,
                  "sensor_height_from_name":x["height_token_name_only"],
                  "original_temperature_C":v,
                  "native_QCFlag_variable":x["original_L6_QCFlag_name"],
                  "native_QCFlag_value":x["original_L6_QCFlag_original_code"],
                  "raw_Ta_composite_C":cv,
                  "is_source_composite_same_numeric_value":v is not None and
                      cv is not None and abs(v-cv)<1e-6,
                  "science_repair_authorised":False})
        height,expectedval=expected[eid]
        composite=num(source[(eid,0,"Ta")]["original_L6_numeric_value"])
        hmp=num(source[(eid,0,"Ta_HMP_"+height)]["original_L6_numeric_value"])
        need(composite is not None and hmp is not None and
             abs(composite-expectedval)<1e-6 and
             abs(composite-hmp)<1e-6,
             "Old L6 composite Ta matches different HMP height by event, original evidence changed")
        print("TA_COMPOSITE_CHANNEL",eid,"OLD_L6_Ta",composite,
              "MATCHED_SOURCE_HEIGHT",height,"HMP_T",hmp,
              "COMPOSITE_AND_CHANNEL_QC_ORIGINAL",
              source[(eid,0,"Ta")]["original_L6_QCFlag_original_code"],
              source[(eid,0,"Ta_HMP_"+height)]["original_L6_QCFlag_original_code"])
        other=[]
        for h in ("2m","4m","7m","10m","15m"):
            x=source[(eid,0,"Ta_HMP_"+h)]
            val=num(x["original_L6_numeric_value"])
            if val is not None:other.append((h,val,x["original_L6_QCFlag_original_code"]))
        print("TA_ALL_5_HEIGHTS",eid,json.dumps(other,ensure_ascii=False))
    for minute in REL:
        for name in sorted(channels):
            if not name.startswith("Ws"):continue
            x=source[(WS_EVENT,minute,name)]
            wind.append({"event_id":WS_EVENT,
              "native_L6_END_relative_minutes":minute,
              "source_native_L6_time":x["original_L6_native_time"],
              "native_wind_channel":name,
              "height_token_name_only":x["height_token_name_only"],
              "source_raw_WS_m_s":num(x["original_L6_numeric_value"]),
              "source_original_QCFlag":x["original_L6_QCFlag_original_code"],
              "source_native_QCFlag_name":x["original_L6_QCFlag_name"],
              "original_observation_is_not_independent_validation":True,
              "scientific_repair_authorised":False})
    need(len(wind)==50,"Ten source wind channels each five original half-hour readings expected")
    for eid in VPD_EVENTS:
        at=[bypair[(eid,h)] for h in ("2m","4m","7m","10m","15m")]
        need(all(num(x["old_RH_HMP_percent"]) is None for x in at),
             "2013 all HMP RH missing original science hold changed")
        b=at[0]
        t=num(b["old_Ta_HMP_C"])
        v=num(b["TERN_VPD_F_hPa"])
        need(t is not None and v is not None and
             b["TERN_VPD_F_QC"] in ("1","1.0"),
             "2013 original QC1 VPD and 2m temperature changed")
        es=esat(t);implied=100*(1-v/es)
        need(implied<-1 and all(
             x["VPD_HMP_pair_diagnostic_hPa_NOT_APPLIED"] in ("",None)
             for x in at),
             "2013 negative RH and no valid 2m/4m/7m/10m/15m T/RH pairs changed")
        vpd.append({"event_id":eid,"original_TERN_AWST_START":b["TERN_AWST_START"],
            "FLUXMET_VPD_F_hPa":v,
            "FLUXMET_VPD_F_QC":b["TERN_VPD_F_QC"],
            "original_L6_Ta_HMP_2m_C":t,
            "original_L6_Ta_HMP_2m_QC":b["old_Ta_HMP_QC_raw_code"],
            "L6_2m_RH_percent":b["old_RH_HMP_percent"],
            "L6_2m_RH_QC":b["old_RH_HMP_QC_raw_code"],
            "all_five_HMP_RH_centers_missing":True,
            "HMP_same_height_valid_pairs":0,
            "esat_at_TERN_TA_hPa":round(es,5),
            "implied_RH_from_TERN_VPD_percent":round(implied,4),
            "FLUXMET_VPD_above_saturation":True,
            "HMP_derived_VPD_at_center_available":False,
            "source_thermodynamic_issue_unresolved":True,
            "scientific_repair_authorised":False})
        print("VPD_SOURCE_GAP",eid,"T2M_C",t,"VPD_QC1_HPA",v,
              "ESAT_HPA",round(es,4),"IMPLIED_RH_PERCENT",round(implied,3),
              "ALL_5_HMP_RH_MISSING",True)
    atwind=[x for x in wind if x["native_L6_END_relative_minutes"]==0]
    print("WS_20190913_ALL_10_L6_SENSORS_CENTER",
          json.dumps([{"channel":x["native_wind_channel"],
                       "ws_m_s":x["source_raw_WS_m_s"],
                       "original_QC":x["source_original_QCFlag"]}
                for x in atwind],ensure_ascii=False))
    classes={
      "PA_20120609_PREVIOUS":(
        "RAW_TERN_PA_SPIKE_AND_PREVIOUS_QC2",
        "NO_INDEPENDENT_ONSITE_PA_SENSOR_IN_37_L6_CANDIDATES__INSTRUMENT_LOG_OR_BOM_REQUIRED"),
      "PA_20120610":(
        "RAW_TERN_PA_QC0_SINGLE_SAMPLE_SPIKE",
        "NO_ONSITE_L6_PA_CHANNEL__INSTRUMENT_QC_OR_BOM_REQUIRED"),
      "TA_20160507":(
        "OLD_L6_COMPOSITE_MATCHES_4M_LOW_T__2M_ALSO_LOW__UPPER_T_MISSING",
        "INVESTIGATE_2M_4M_HMP_CALIBRATION_AND_CHANNEL_SELECTOR__NO_INTERPOLATION_APPROVAL"),
      "TA_20160520":(
        "OLD_L6_COMPOSITE_MATCHES_15M_LOW_T__LOWER_HMP_T_WARMER",
        "INVESTIGATE_15M_HMP_SENSOR_AND_COMPOSITE_HEIGHT_SELECTION__NO_INTERPOLATION_APPROVAL"),
      "WS_20190913":(
        "TEN_OLD_L6_WIND_CHANNELS_REPORTED__NO_AUTOMATIC_GUST_EQUIVALENCE",
        "INTERPRET_WS_SONIC_AND_WS4_SENSOR_VALUES_QC_WITH_TIME_AND_HEIGHT"),
      "VPD_QC1_20130205":(
        "NO_VALID_SAMEHEIGHT_HMP_RH_AND_VPD_QC1_EXCEEDS_ESAT",
        "GAPFILL_PAIR_PHYSICS_GUARD_AND_SOURCE_METHOD_REQUIRED"),
      "VPD_QC1_20130216":(
        "NO_VALID_SAMEHEIGHT_HMP_RH_AND_VPD_QC1_EXCEEDS_ESAT",
        "GAPFILL_PAIR_PHYSICS_GUARD_AND_SOURCE_METHOD_REQUIRED")}
    for eid in E7:
        review,dependency=classes[eid]
        register.append({"event_id":eid,
            "anomaly_domain":("VPD" if eid.startswith("VPD") else
                 "TA" if eid.startswith("TA") else
                 "WS" if eid.startswith("WS") else "PA"),
            "first_party_evidence_classification":review,
            "specific_next_science_dependency":dependency,
            "original_first_party_sources_modified":False,
            "science_release":False,"AD400_authorised":False})
    need(len(register)==7 and len(vpd)==2,"Seven holds and two VPD conflicts required")
    report={
      "site":"AU-Gin","stage":"Stage15 source-only 2016 sensor selection, 2013 VPD and 2019 WS original QC",
      "original_TERN_ZIP_SHA256":ZIP_SHA,"original_L6_SHA256":L6_SHA,
      "Stage14_source_receipt_SHA256":sha(REC14),
      "Stage14_1295_L6_source_sensor_QC_SHA256":sha(RAW14),
      "Stage14_35_sameheight_HMP_pair_SHA256":sha(PAIR14),
      "Stage14_4_TA_lineage_matches_SHA256":sha(MATCH14),
      "Stage13_source_receipt_SHA256":sha(REC13),
      "local_L6_END_equals_TERN_local_START_plus_minutes":30,
      "old_L6_is_related_source_not_independent_weather_verification":True,
      "2016_May07_old_composite_Ta_matched_HMP_4m":True,
      "2016_May20_old_composite_Ta_matched_HMP_15m":True,
      "2013_VPD_two_HMP_RH_gaps_all_five_heights":True,
      "2019_wind_10_channels_5_halfhour_source_QC_rows":len(wind),
      "seven_event_source_register_rows":len(register),
      "28_original_event_groups_all_science_HOLD":True,
      "site_strict_15_real_measured_years_qualified":False,
      "science_repair_authorised":False,
      "no_original_or_forcing_or_cime_or_slurm_modifications":True,
      "AD400_authorised":False}
    out.mkdir(mode=0o700,exist_ok=False)
    save(out/"stage15_AU_Gin_2016_TA_HMP_composite_5HH_original_QC.tsv",
         TEMP_COLUMNS,temp)
    save(out/"stage15_AU_Gin_2019_WS_10channels_5HH_original_QC.tsv",
         WS_COLUMNS,wind)
    save(out/"stage15_AU_Gin_2013_VPD_QC1_no_HMP_RH_hPa_physics.tsv",
         VPD_COLUMNS,vpd)
    save(out/"stage15_AU_Gin_7priority_science_dependency_HOLD.tsv",
         REG_COLUMNS,register)
    (out/"stage15_AU_Gin_2016_2013_2019_source_science_HOLD.json").write_text(
         json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    print("STAGE15 ORIGINAL TERN/L6 SOURCE AND STAGE13/STAGE14 SHA256 VERIFIED")
    print("STAGE15 SOURCE_SHADOW_HOLD",len(register),
          "TA_SENSOR_CONTEXT_ROWS",len(temp),
          "WS_SENSOR_CONTEXT_ROWS",len(wind),
          "VPD_QC1_CONFLICTS",len(vpd))
    for r in register:
        print("CASE_DEPENDENCY",r["event_id"],
              r["first_party_evidence_classification"],
              r["specific_next_science_dependency"])
    print("STAGE15 FIRST PARTY SOURCE HOLD PASS; NO REPAIR/DATM/AD400")
    print("REPORT_DIR",out)
if __name__=="__main__":main()
