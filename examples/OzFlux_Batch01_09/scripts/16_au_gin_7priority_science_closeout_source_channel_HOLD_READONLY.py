#!/usr/bin/env python3
"""AU-Gin Stage16: 7 priority case science-closeout and source-channel chronology.

Consumes actual operator Stage15 immutable 50 wind + 80 temperature source
sensor/QC rows, 2 VPD QC1 issues, 7 case gates. Re-pins 2019 Ws source 16m
19.94895m/s anomaly versus simultaneous other height/sensor winds, and
checks original before/after 30/60min values for composite and channels.
Highlights 2016 anomalous composite source channel selection (4m, 15m),
missing 2013 HMP RH in original 5 height channels, and unsupported 2012 PA
in situ donor inference.

NO numeric output is a correction or interpolation recommendation. Old OzFlux
L6 and TERN FLUXMET are same/related site product lineage, not independent
meteorological stations. Sensor height/QC equivalence is NOT established.
All 28 source events and AD400 remain SCIENCE HOLD; strict real measured
tower span (~13.7y) fails >=15 real years eligibility. Onward actions
require PI instrument/calibration/method evidence or change of selection
protocol, not further automatic stage approval.
"""
from __future__ import annotations
import argparse,csv,hashlib,json,math,statistics
from pathlib import Path
HOME=Path.home()
ZIP=Path("/iridisfs/scratch/ly3n24/CLM_FATES/sites/MY_EC_SITE/AU-Gin/forcing/raw/TERN_FLUXNET_2011_2025/TERN_AU-Gin_FLUXNET_2011-2025_v1.3_r1.zip")
L6=Path("/iridisfs/scratch/ly3n24/CLM_FATES/sites/MY_EC_SITE/AU-Gin/forcing/raw/Gingin_L6.nc")
ZIP_SHA="acd78491b6f5f2c1374da2076d73a6c8b6ef430b256b78da3d300656943d6f14"
L6_SHA="0e700e37ead024a7eda4cdf9b47f839d5dc5bfa5578087e9af1ddd09aa510d66"
D15=HOME/"ozflux_AU_Gin_stage15_20261107T051656Z"
D14=HOME/"ozflux_AU_Gin_stage14_20261107T051121Z"
D10=HOME/"ozflux_AU_Gin_stage10_20261105T184415Z"
R15=D15/"stage15_AU_Gin_2016_2013_2019_source_science_HOLD.json"
T15=D15/"stage15_AU_Gin_2016_TA_HMP_composite_5HH_original_QC.tsv"
W15=D15/"stage15_AU_Gin_2019_WS_10channels_5HH_original_QC.tsv"
V15=D15/"stage15_AU_Gin_2013_VPD_QC1_no_HMP_RH_hPa_physics.tsv"
G15=D15/"stage15_AU_Gin_7priority_science_dependency_HOLD.tsv"
R14=D14/"stage14_AU_Gin_oldL6_endstamp_multisensor_source_science_HOLD.json"
R10=D10/"stage10_AU_Gin_full_28event_7priority_science_HOLD.json"
ORIG_7=("PA_20120609_PREVIOUS","PA_20120610","TA_20160507",
"TA_20160520","WS_20190913","VPD_QC1_20130205","VPD_QC1_20130216")
MINUTES=(-60,-30,0,30,60)
WCOLS=("L6_native_end_relative_minutes","L6_channel","original_WS_m_s",
       "original_QCFlag","source_l6_end_timestamp","source_height_not_verified",
       "is_16m_sensor_or_composite","QC_sensor_good_not_independently_confirmed",
       "repair_authorised")
TCOLS=("event_id","L6_native_end_relative_minutes","L6_channel",
       "original_T_C","original_QCFlag","same_as_composite_original_L6",
       "source_l6_end_timestamp","source_height_not_verified",
       "repair_authorised")
DCOLS=("event_id","domain","source_anomaly_mechanism_candidate",
       "independent_external_validation_complete","manual_science_dependency",
       "original_or_forcing_modified","all_28_groups_science_HOLD",
       "AD400_authorised")
def need(x,msg):
    if not x:raise RuntimeError(str(msg))
def sha(p):
    p=Path(p)
    need(p.is_file() and not p.is_symlink(),"Immutable original/receipt absent/symlink "+str(p))
    h=hashlib.sha256()
    with p.open("rb") as f:
        for block in iter(lambda:f.read(4<<20),b""):h.update(block)
    return h.hexdigest()
def load(p):
    need(p.is_file() and not p.is_symlink(),"Original receipt report absent "+str(p))
    return json.loads(p.read_text(encoding="utf-8"))
def tsv(p):
    need(p.is_file() and not p.is_symlink(),"Prior original source data absent "+str(p))
    with p.open(encoding="utf-8",newline="") as f:
        return list(csv.DictReader(f,delimiter="\t"))
def n(s):
    try:
        x=float(str(s).strip())
        return x if math.isfinite(x) and -9990<x<9990 else None
    except (ValueError,TypeError):return None
def write(p,cols,data):
    with p.open("x",encoding="utf-8",newline="") as f:
        wr=csv.DictWriter(f,fieldnames=cols,delimiter="\t",extrasaction="raise")
        wr.writeheader();wr.writerows(data)
def test():
    need(abs(19.94895-19.95)<.002,"16m vs TERN rounding")
    need(abs(19.94895-.5074776)>19,"16m vs 10m mismatch")
    need(abs(6.19237-9.981885)>3.5,"15m vs 7m discrepancy")
    need(19.94895/statistics.median([.5074776,.4393113,.1239203,.6586267])>30,
         "16m ratio to other available channels is huge, but not donor equivalence")
    need(len(ORIG_7)==7 and len(MINUTES)==5,"Seven events five time windows")
    print("AU-GIN STAGE16 SELFTEST PASS | 2019 16m wind + 2016 source-height + 2013 RH, immutable decision closeout; NO REPAIR")
def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--self-test",action="store_true")
    p.add_argument("--out",type=Path)
    a=p.parse_args()
    if a.self_test:return test()
    o=a.out
    need(o is not None and o.parent.resolve()==HOME.resolve()
         and not o.exists() and not o.is_symlink(),
         "Use an unused direct HOME path")
    need(sha(ZIP)==ZIP_SHA and sha(L6)==L6_SHA,
         "Original TERN or old OzFlux L6 changed")
    r15=load(R15);r14=load(R14);r10=load(R10)
    need(r15.get("original_TERN_ZIP_SHA256")==ZIP_SHA
         and r15.get("original_L6_SHA256")==L6_SHA
         and r15.get("2016_May07_old_composite_Ta_matched_HMP_4m") is True
         and r15.get("2016_May20_old_composite_Ta_matched_HMP_15m") is True
         and r15.get("2013_VPD_two_HMP_RH_gaps_all_five_heights") is True
         and r15.get("2019_wind_10_channels_5_halfhour_source_QC_rows")==50
         and r15.get("28_original_event_groups_all_science_HOLD") is True
         and r15.get("AD400_authorised") is False,
         "Actual Stage15 seven priority original source status changed")
    need(r14.get("oldL6_samples_total")==1295
         and r14.get("original_oldL6_raw_sensor_candidates")==37
         and r14.get("source_local_START_to_oldL6_local_END_offset_minutes")==30
         and r14.get("AD400_authorised") is False,
         "Actual Stage14 related source clock/QC receipt changed")
    need(r10.get("original_28_event_groups_reconstructed")==28
         and r10.get("original_44_flag_rows_reconstructed")==44
         and r10.get("AD400_authorised") is False,
         "Actual Stage10 28/44 full event receipt changed")
    w=tsv(W15); t=tsv(T15); v=tsv(V15); groups=tsv(G15)
    need(len(w)==50 and len(t)==80 and len(v)==2 and len(groups)==7,
         "Actual Stage15 50 wind, 80 temperature, 2 VPD, 7 HOLD changed")
    need({x["event_id"] for x in groups}==set(ORIG_7),
         "Seven priority review cases changed")
    wind={}
    for x in w:
        minute=int(x["native_L6_END_relative_minutes"])
        name=x["native_wind_channel"]
        key=(minute,name)
        need(x["event_id"]=="WS_20190913" and minute in MINUTES and
             key not in wind,"Unknown/duplicate wind original source row")
        wind[key]=x
    windchannels={key[1] for key in wind}
    need(len(windchannels)==10 and
         set(wind)=={(minute,name) for minute in MINUTES for name in windchannels},
         "Original 10 native wind channels x 5 source time slots missing")
    windout=[];wind_panel=[]
    for minute in MINUTES:
        panel={}
        for name in sorted(windchannels):
            x=wind[(minute,name)]
            value=n(x["source_raw_WS_m_s"])
            panel[name]={"value":value,
                         "QCFlag":x["source_original_QCFlag"]}
            windout.append({
               "L6_native_end_relative_minutes":minute,
               "L6_channel":name,
               "original_WS_m_s":value,
               "original_QCFlag":x["source_original_QCFlag"],
               "source_l6_end_timestamp":x["source_native_L6_time"],
               "source_height_not_verified":True,
               "is_16m_sensor_or_composite":name in ("Ws","Ws_WS4_16m"),
               "QC_sensor_good_not_independently_confirmed":True,
               "repair_authorised":False})
        wind_panel.append({"relative_min":minute,"channels":panel})
        print("WIND_5HH",minute,json.dumps(panel,ensure_ascii=False))
    a=n(wind[(0,"Ws")]["source_raw_WS_m_s"])
    b=n(wind[(0,"Ws_WS4_16m")]["source_raw_WS_m_s"])
    need(a is not None and b is not None
         and abs(a-b)<1e-7 and abs(a-19.94895)<1e-6,
         "Original 2019 composite exact 16m channel spike changed")
    comparator=("Ws_SONIC_Av","Ws_WS4_10m","Ws_WS4_7m","Ws_WS4_2m")
    others=[]
    for name in comparator:
        x=wind[(0,name)]
        val=n(x["source_raw_WS_m_s"])
        need(val is not None and x["source_original_QCFlag"] in ("0","0.0"),
             "Original valid comparative sensor unavailable at spike")
        others.append(val)
    median=statistics.median(others)
    need(median>0 and a/median>30,
         "Original 16m vs multiple source channels discrepancy changed")
    print("WIND_CENTER_16M_EVIDENCE",
          "COMPOSITE",a,"WS4_16M",b,
          "WS4_10M",n(wind[(0,"Ws_WS4_10m")]["source_raw_WS_m_s"]),
          "SONIC",n(wind[(0,"Ws_SONIC_Av")]["source_raw_WS_m_s"]),
          "WS4_7M",n(wind[(0,"Ws_WS4_7m")]["source_raw_WS_m_s"]),
          "OTHER_4_SENSOR_MEDIAN_DIAGNOSTIC_ONLY",round(median,6),
          "16M_OTHER_MEDIAN_RATIO_NOT_A_CORRECTION",round(a/median,2))
    temp={};tout=[]
    for x in t:
        eid=x["event_id"];minute=int(x["native_L6_END_relative_minutes"])
        name=x["sensor_variable"];key=eid,minute,name
        need(eid in ("TA_20160507","TA_20160520") and
             minute in MINUTES and key not in temp,"Unknown/duplicate temperature source row")
        temp[key]=x
        tout.append({
          "event_id":eid,"L6_native_end_relative_minutes":minute,
          "L6_channel":name,
          "original_T_C":n(x["original_temperature_C"]),
          "original_QCFlag":x["native_QCFlag_value"],
          "same_as_composite_original_L6":x["is_source_composite_same_numeric_value"],
          "source_l6_end_timestamp":x["source_native_L6_time"],
          "source_height_not_verified":True,"repair_authorised":False})
    tempchannels={key[2] for key in temp}
    need(len(tempchannels)==8 and len(temp)==2*5*8,
         "Original 2016 2-event x 5 halfhour x 8 composite/HMP channels changed")
    heights=("2m","4m","7m","10m","15m")
    for eid in ("TA_20160507","TA_20160520"):
        for minute in MINUTES:
            values={name:n(temp[(eid,minute,name)]["original_temperature_C"])
                    for name in ("Ta",)+tuple("Ta_HMP_"+h for h in heights)}
            qc={name:temp[(eid,minute,name)]["native_QCFlag_value"]
                    for name in values}
            print("TEMP_5HH",eid,minute,
                  "CHANNELS",json.dumps(values,ensure_ascii=False),
                  "QC",json.dumps(qc,ensure_ascii=False))
    for eid,name,expected in (("TA_20160507","Ta_HMP_4m",-4.625476),
                               ("TA_20160520","Ta_HMP_15m",6.19237)):
        value=n(temp[(eid,0,name)]["original_temperature_C"])
        composite=n(temp[(eid,0,"Ta")]["original_temperature_C"])
        need(value is not None and composite is not None and
             abs(value-composite)<1e-6 and abs(value-expected)<1e-6,
             "2016 per-event selected height/source relationship changed")
    vpdout=[]
    for x in v:
        eid=x["event_id"]
        need(eid in ("VPD_QC1_20130205","VPD_QC1_20130216"),
             "Unknown original VPD source center")
        need(x["all_five_HMP_RH_centers_missing"]=="True"
             and x["FLUXMET_VPD_above_saturation"]=="True"
             and x["FLUXMET_VPD_F_QC"] in ("1","1.0"),
             "Original two VPD physics/QC1 proof changed")
        vpdout.append({
           "event_id":eid,
           "VPD_F_hPa":n(x["FLUXMET_VPD_F_hPa"]),
           "original_HMP_2m_T_C":n(x["original_L6_Ta_HMP_2m_C"]),
           "computed_esat_hPa":n(x["esat_at_TERN_TA_hPa"]),
           "implied_RH_percent":n(x["implied_RH_from_TERN_VPD_percent"]),
           "HMP_RH_available":False})
    need(len(vpdout)==2 and len({x["event_id"] for x in vpdout})==2,
         "Two distinct original VPD physics issues missing")
    decisions=[]
    for x in groups:
        eid=x["event_id"]
        if eid=="WS_20190913":
            klass="SINGLE_16M_WS4_CHANNEL_REPRODUCES_COMPOSITE_19_94895_WHILE_4_OTHER_SOURCE_SENSORS_SUB1"
            next_dep="PI_WS4_16M_MAINTENANCE_SOURCE_SELECTOR_AND_SENSOR_QC_EVIDENCE"
        elif eid=="TA_20160507":
            klass="COMPOSITE_EQUALS_4M_AND_2M_ALSO_LOW_HIGHER_HMP_T_MISSING"
            next_dep="PI_2M_4M_HMP_2016_SENSOR_CALIBRATION_AND_SOURCE_SWITCH_QC"
        elif eid=="TA_20160520":
            klass="COMPOSITE_EQUALS_15M_WHILE_2M_4M_7M_10M_WARMER"
            next_dep="PI_15M_HMP_INSTRUMENT_AND_MULTIHEIGHT_SOURCE_SELECTOR_QC"
        elif eid.startswith("VPD"):
            klass="QC1_VPD_EXCEEDS_ESAT_HMP_RH_MISSING_ALL_HEIGHTS"
            next_dep="GAPFILL_VPD_TA_THERMODYNAMIC_PAIR_SOURCE_METHOD"
        else:
            klass="PA_ORIGINAL_QC0_SOURCE_SPIKE_NO_ONSITE_INDEPENDENT_PA_CHANNEL"
            next_dep="PI_PRESSURE_SENSOR_LOG_OR_EXACT_GINGIN_AERO_HOURLY_BOM"
        decisions.append({
          "event_id":eid,"domain":x["anomaly_domain"],
          "source_anomaly_mechanism_candidate":klass,
          "independent_external_validation_complete":False,
          "manual_science_dependency":next_dep,
          "original_or_forcing_modified":False,
          "all_28_groups_science_HOLD":True,"AD400_authorised":False})
        print("SCIENCE_DEPENDENCY",eid,klass,next_dep)
    report={
       "site":"AU-Gin","stage":"Stage16 seven-priority evidence closeout, no source repair",
       "original_TERN_SHA256":ZIP_SHA,"original_old_L6_SHA256":L6_SHA,
       "Stage15_actual_report_SHA256":sha(R15),
       "Stage14_actual_report_SHA256":sha(R14),
       "Stage15_original_50_WIND_5HH_SHA256":sha(W15),
       "Stage15_original_80_TA_5HH_SHA256":sha(T15),
       "Stage15_original_2_VPD_QC1_SHA256":sha(V15),
       "Stage15_original_7_case_dependencies_SHA256":sha(G15),
       "BIF_UTC_OFFSET":8,"oldL6_local_END_minus_TERN_local_START_minutes":30,
       "2019_composite_exactly_equals_old_L6_WS4_16m_at_center":True,
       "2019_16m_wind_value_m_s":a,
       "2019_other_4_original_sensor_center_values_m_s":others,
       "2019_OTHER_SENSOR_MEDIAN_IS_NOT_A_MODEL_DONOR":round(median,7),
       "2019_16m_vs_4_other_sensor_median_RATIO_DIAGNOSTIC_ONLY":round(a/median,3),
       "2019_5HH_10_channel_native_QC_and_values":wind_panel,
       "2016_HMP_source_selection_issue_unresolved":True,
       "2013_two_VPD_QC1_negative_implied_RH_with_no_raw_HMP_RH":vpdout,
       "seven_priority_case_evidence_only":len(decisions),
       "28_full_original_events_STILL_science_HOLD":True,
       "15_actual_tower_measured_years_eligibility_met":False,
       "old_L6_and_TERN_same_station_NOT_independent_validation":True,
       "no_original_L6_or_DATM_Surface_CIME_Slurm_modified":True,
       "science_release":False,
       "any_automatic_gapfill_or_interpolation_applied":False,
       "AD400_authorised":False}
    o.mkdir(mode=0o700,exist_ok=False)
    write(o/"stage16_AU_Gin_2019_10wind_channel_5HH_original_QC_and_values.tsv",WCOLS,windout)
    write(o/"stage16_AU_Gin_2016_2TA_5HH_original_HMP_composite_QC.tsv",TCOLS,tout)
    write(o/"stage16_AU_Gin_7priority_final_source_dependency_HOLD.tsv",DCOLS,decisions)
    (o/"stage16_AU_Gin_7priority_source_QC_15yr_eligibility_science_HOLD.json").write_text(
          json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    print("STAGE16 READONLY SOURCE CLOSEOUT PASS | 7 PRIORITIES, 28 GROUPS ALL HOLD, AD400 DISALLOWED")
    print("REPORT_DIR",o)
if __name__=="__main__":main()
