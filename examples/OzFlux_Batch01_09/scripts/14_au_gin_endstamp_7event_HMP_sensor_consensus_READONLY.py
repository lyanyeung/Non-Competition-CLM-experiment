#!/usr/bin/env python3
"""AU-Gin Stage14: L6 native END vs FLUXMET START and seven source-event sensor consensus.

Actual operator Stage13 verified Gingin L6 37 native RH/TA/VPD/WS variables,
including multiple HMP heights, at 7 anomaly times under 4 clock hypotheses.
L6 global 'time_zone=Australia/Perth', native 30-min step, old time coverage
2011-10-13 14:00 through 2026-02-02; FLUXMET BIF UTC_OFFSET=8 and
TIMESTAMP_START. Four existing exact old L6 Ta matches to new FLUXMET TA_F
appear at old L6 local time = TERN native START + 30min.

This source-only stage (1) verifies all 4 original event Ta matches, (2)
reads +/-60min around matched L6 END labels for all 37 original sensor
variables and their raw QCFlags, (3) checks paired same-height HMP TA/RH
against thermodynamic VPD as a read-only diagnostic, and (4) leaves
unverified sensor/processing/QC conventions explicitly held.

L6 and TERN are RELATED site products, NOT independent meteorological
verification. No input edits, no candidate correction file, no DATM/Slurm.
"""
from __future__ import annotations
import argparse,csv,datetime as dt,hashlib,json,math,re
from collections import Counter,defaultdict
from pathlib import Path
H=Path.home()
ZIP=Path("/iridisfs/scratch/ly3n24/CLM_FATES/sites/MY_EC_SITE/AU-Gin/forcing/raw/TERN_FLUXNET_2011_2025/TERN_AU-Gin_FLUXNET_2011-2025_v1.3_r1.zip")
OLD=Path("/iridisfs/scratch/ly3n24/CLM_FATES/sites/MY_EC_SITE/AU-Gin/forcing/raw/Gingin_L6.nc")
ZIP_SHA="acd78491b6f5f2c1374da2076d73a6c8b6ef430b256b78da3d300656943d6f14"
OLD_SHA="0e700e37ead024a7eda4cdf9b47f839d5dc5bfa5578087e9af1ddd09aa510d66"
D13=H/"ozflux_AU_Gin_stage13_20261107T050509Z"
D12=H/"ozflux_AU_Gin_stage12_20261107T045708Z"
D10=H/"ozflux_AU_Gin_stage10_20261105T184415Z"
REP13=D13/"stage13_AU_Gin_oldL6_sensor_source_2013_2016_HOLD.json"
INV13=D13/"stage13_AU_Gin_old_L6_raw_like_sensor_inventory.tsv"
VAL13=D13/"stage13_AU_Gin_7event_old_L6_source_TA_RH_AH_VPD_WS_PA_QC_samples.tsv"
REP12=D12/"stage12_AU_Gin_source_identity_TA_RH_VPD_2016_2013_science_HOLD.json"
CTX10=D10/"stage10_AU_Gin_7priority_91HH_original_multivar_context.tsv"
F={
"PA_20120609_PREVIOUS":("2012-06-09 08:00:00","PA"),
"PA_20120610":("2012-06-10 13:30:00","PA"),
"TA_20160507":("2016-05-07 16:00:00","TA"),
"TA_20160520":("2016-05-20 18:00:00","TA"),
"WS_20190913":("2019-09-13 03:00:00","WS"),
"VPD_QC1_20130205":("2013-02-05 06:30:00","VPD"),
"VPD_QC1_20130216":("2013-02-16 07:00:00","VPD")}
CLOCK="L6_LOCAL_END_MATCH_FLUXMET_START_PLUS_30MIN"
REL=(-60,-30,0,30,60)
ALIGN_COLS=("event_id","TERN_local_timestamp_START","L6_local_timestamp_END",
"TERN_TA_F_C","TERN_TA_F_QC","old_L6_Ta_C","old_L6_Ta_QCFlag",
"abs_difference_degC","L6_time_zone_metadata","match_less_than_0_005C",
"same_or_related_product_not_independent_source","clock_and_QC_science_release")
SENSOR_COLS=("event_id","TERN_AWST_start","L6_native_end_center",
"minutes_from_event_CENTER","original_L6_native_time","original_L6_channel",
"class","height_token_name_only","units","original_L6_numeric_value",
"original_L6_QCFlag_name","original_L6_QCFlag_original_code",
"source_sensor_QC_interpretation_approved","any_repair_applied")
PAIR_COLS=("event_id","TERN_AWST_START","L6_end_center",
"height_token_HMP","old_Ta_HMP_channel","old_Ta_HMP_C",
"old_Ta_HMP_QC_raw_code","old_RH_HMP_channel","old_RH_HMP_percent",
"old_RH_HMP_QC_raw_code","es_from_old_HMP_temperature_hPa",
"VPD_HMP_pair_diagnostic_hPa_NOT_APPLIED",
"TERN_VPD_F_hPa","TERN_VPD_F_QC",
"pair_sameheight_source_not_independent_QC")
def need(x,msg):
    if not x:raise RuntimeError(str(msg))
def sha(p):
    p=Path(p)
    need(p.is_file() and not p.is_symlink(),"Original file absent/symlink "+str(p))
    h=hashlib.sha256()
    with p.open("rb") as f:
        for block in iter(lambda:f.read(4<<20),b""):h.update(block)
    return h.hexdigest()
def read(p):
    need(p.is_file() and not p.is_symlink(),"Source TSV missing "+str(p))
    with p.open(encoding="utf-8",newline="") as f:
        return list(csv.DictReader(f,delimiter="\t"))
def write(p,cols,records):
    with p.open("x",encoding="utf-8",newline="") as f:
        w=csv.DictWriter(f,fieldnames=cols,delimiter="\t",extrasaction="raise")
        w.writeheader();w.writerows(records)
def n(s):
    try:
        x=float(str(s).strip())
        return x if math.isfinite(x) and -9990<x<9990 else None
    except (ValueError,TypeError):return None
def measure(v,index):
    import numpy as np
    if not v.dimensions or v.dimensions[0]!="time" or any(x!=1 for x in v.shape[1:]):
        return None
    cell=v[(index,)+(0,)*(v.ndim-1)]
    if np.ma.is_masked(cell):return None
    try:
        z=float(np.asarray(cell).item())
        return z if math.isfinite(z) and -9990<z<9990 else None
    except (TypeError,ValueError,OverflowError):return None
def esat(t):
    return 6.112*math.exp(17.67*t/(t+243.5)) if t is not None and -65<t<70 else None
def sensor_hmp(var,height):
    # Only original HMP stem variable with same explicitly tokenized
    # height. Do not conflate 15m vs 15mb or 2m vs 2mb.
    return var+"_HMP_"+height
def stamp(d):return d.strftime("%Y-%m-%d %H:%M:%S")
def test():
    need(len(F)==7 and len(REL)==5 and REL[2]==0,"Seven source events, five halfhours")
    need(abs(-4.625476-(-4.63))<.005 and abs(6.19237-6.19)<.005,
        "2016 same-source anomaly L6 END matches TERN START")
    need(abs(13.60853-13.61)<.005 and abs(19.09408-19.09)<.005,
        "2013 same-source T matches")
    need(esat(13.61)>15 and esat(13.61)<16.5,"Tetens hPa")
    need(sensor_hmp("Ta","10m")=="Ta_HMP_10m","HMP height")
    print("AU-GIN STAGE14 SELFTEST PASS | four L6-END to TERN-START source matches, HMP 5-height audit; READ ONLY")
def main():
    import numpy as np
    import netCDF4
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--self-test",action="store_true")
    p.add_argument("--out",type=Path)
    args=p.parse_args()
    if args.self_test:return test()
    out=args.out
    need(out is not None and out.parent.resolve()==H.resolve() and
         not out.exists() and not out.is_symlink(),
         "New HOME-only result path required")
    need(sha(ZIP)==ZIP_SHA and sha(OLD)==OLD_SHA,"Original TERN/L6 checksum changed")
    r13=json.loads(REP13.read_text(encoding="utf-8"))
    r12=json.loads(REP12.read_text(encoding="utf-8"))
    need(r13.get("new_TERN_original_ZIP_SHA256")==ZIP_SHA and
         r13.get("old_L6_original_SHA256")==OLD_SHA and
         r13.get("old_L6_source_sensor_candidate_count")==37 and
         r13.get("seven_original_source_focus_times")==7 and
         r13.get("AD400_authorised") is False,
         "Real Stage13 source/37 sensors/7 priorities HOLD changed")
    need(r12.get("original_TERN_zip_SHA256")==ZIP_SHA and
         r12.get("ZIP_members_with_raw_like_TA")==0 and
         r12.get("AD400_authorised") is False,
         "Real Stage12 source SHA and no raw TA changed")
    inv=read(INV13)
    oldvalues=read(VAL13)
    source=read(CTX10)
    need(len(inv)==37 and oldvalues and len(source)==91,
         "Real source stage13/10 tabular evidence missing")
    centers={}
    for x in source:
        if x.get("is_focus_half_hour")=="True":
            centers[x["focus_id"]]=x
    need(set(centers)==set(F),"7 source stage10 center timestamps changed")
    oldend={}
    for x in oldvalues:
        if x["L6_time_hypothesis_NOT_APPROVED"]!=CLOCK:continue
        key=(x["focus_id"],x["L6_candidate_name"])
        need(key not in oldend,"Stage13 duplicate original L6 sensor sampled")
        oldend[key]=x
    # A matching time coordinate exists for four expected center T observations.
    paired=[("TA_20160507",-4.63),("TA_20160520",6.19),
            ("VPD_QC1_20130205",13.61),("VPD_QC1_20130216",19.09)]
    align=[]
    for eid,expected in paired:
        c=centers[eid];new=n(c["TA_F"])
        need(new is not None and abs(new-expected)<1e-7,
             "New FLUXMET exact original event TA changed")
        old=oldend.get((eid,"Ta"))
        need(old is not None,"Stage13 native local-END old L6 Ta evidence missing")
        ov=n(old["L6_original_value"])
        need(ov is not None and abs(ov-new)<.005,
             "Old L6 END Ta fails exact source lineage matching")
        align.append({"event_id":eid,
            "TERN_local_timestamp_START":F[eid][0],
            "L6_local_timestamp_END":stamp(dt.datetime.fromisoformat(F[eid][0])+dt.timedelta(minutes=30)),
            "TERN_TA_F_C":new,"TERN_TA_F_QC":c["TA_F_QC"],
            "old_L6_Ta_C":ov,"old_L6_Ta_QCFlag":old["L6_original_QCFlag_value"],
            "abs_difference_degC":round(abs(ov-new),7),
            "L6_time_zone_metadata":"Australia/Perth",
            "match_less_than_0_005C":True,
            "same_or_related_product_not_independent_source":True,
            "clock_and_QC_science_release":False})
    # Read actual original L6 raw HMP components at +/-60 min around
    # the source-identified local END label, not source guessing.
    results=[];pairedrows=[];report_counts=Counter()
    with netCDF4.Dataset(str(OLD),"r") as ds:
        t=ds.variables["time"]
        unit=str(getattr(t,"units",""))
        cal=str(getattr(t,"calendar","gregorian"))
        zone=str(getattr(ds,"time_zone",""))
        need(zone=="Australia/Perth" and
             "days since 1800-01-01" in unit and len(t)==250821,
             "Old L6 original local clock metadata changed")
        time=np.ma.filled(t[:],np.nan).astype(float)
        need(np.all(np.isfinite(time)) and np.all(np.diff(time)>0),
             "Old L6 native time is not complete strictly increasing")
        for eid,(native,domain) in F.items():
            center=dt.datetime.fromisoformat(native)+dt.timedelta(minutes=30)
            eventvals=defaultdict(dict)
            for rel in REL:
                q=center+dt.timedelta(minutes=rel)
                target=float(netCDF4.date2num(q,units=unit,calendar=cal))
                i=int(np.searchsorted(time,target))
                options=[j for j in (i-1,i) if 0<=j<len(time)]
                need(options,"Old L6 time unexpectedly absent")
                index=min(options,key=lambda j:abs(time[j]-target))
                delta=abs((time[index]-target)*1440)
                need(delta<0.01,"Old L6 lacks exact 30-min center/neighbors "+eid)
                for meta in inv:
                    name=meta["variable_name"]
                    if name not in ds.variables:continue
                    v=ds.variables[name]
                    val=measure(v,index)
                    qcname=meta["paired_QCFlag_variable"]
                    qv=measure(ds.variables[qcname],index) if qcname in ds.variables else None
                    eventvals[rel][name]=(val,qv)
                    report_counts[(meta["variable_class"],rel,"finite")]+=int(val is not None)
                    results.append({"event_id":eid,"TERN_AWST_start":native,
                      "L6_native_end_center":stamp(center),
                      "minutes_from_event_CENTER":rel,
                      "original_L6_native_time":stamp(q),
                      "original_L6_channel":name,
                      "class":meta["variable_class"],
                      "height_token_name_only":meta["possible_height_token_in_name_NOT_VERIFIED"],
                      "units":meta["original_units"],
                      "original_L6_numeric_value":val,
                      "original_L6_QCFlag_name":qcname,
                      "original_L6_QCFlag_original_code":qv,
                      "source_sensor_QC_interpretation_approved":False,
                      "any_repair_applied":False})
            center_vals=eventvals[0]
            # Original height-matched multi-height HMP pairs.
            for height in ("2m","4m","7m","10m","15m"):
                tn=sensor_hmp("Ta",height);rn=sensor_hmp("RH",height)
                tv,tqc=center_vals.get(tn,(None,None))
                rv,rqc=center_vals.get(rn,(None,None))
                e=esat(tv)
                vpd=e*(1-rv/100) if e is not None and rv is not None and 0<=rv<=100 else None
                c=centers[eid]
                pairedrows.append({
                    "event_id":eid,"TERN_AWST_START":native,
                    "L6_end_center":stamp(center),
                    "height_token_HMP":height,
                    "old_Ta_HMP_channel":tn,"old_Ta_HMP_C":tv,
                    "old_Ta_HMP_QC_raw_code":tqc,
                    "old_RH_HMP_channel":rn,"old_RH_HMP_percent":rv,
                    "old_RH_HMP_QC_raw_code":rqc,
                    "es_from_old_HMP_temperature_hPa":round(e,5) if e is not None else None,
                    "VPD_HMP_pair_diagnostic_hPa_NOT_APPLIED":round(vpd,5) if vpd is not None else None,
                    "TERN_VPD_F_hPa":n(c["VPD_F"]),
                    "TERN_VPD_F_QC":c["VPD_F_QC"],
                    "pair_sameheight_source_not_independent_QC":True})
    need(len(results)==len(F)*len(REL)*len(inv) and len(pairedrows)==len(F)*5,
         "Seven times x five interval x all 37 original L6 sensors not preserved")
    diag=[]
    for eid in F:
        row=[x for x in results if x["event_id"]==eid and x["minutes_from_event_CENTER"]==0]
        def relevant(k):
            return [x for x in row if x["class"]==k and x["original_L6_numeric_value"] is not None]
        temp=[x for x in relevant("TA") if x["original_L6_channel"].startswith("Ta_HMP_")]
        hum=[x for x in relevant("RH") if x["original_L6_channel"].startswith("RH_HMP_")]
        ws=[x for x in relevant("WS") if x["original_L6_channel"].startswith("Ws_")]
        pairs=[x for x in pairedrows if x["event_id"]==eid]
        report_counts[("event",eid,"T_HMP_count")]=len(temp)
        report_counts[("event",eid,"RH_HMP_count")]=len(hum)
        report_counts[("event",eid,"HMP_valid_sameheight_pair_count")]=sum(x["VPD_HMP_pair_diagnostic_hPa_NOT_APPLIED"] is not None for x in pairs)
        diag.append({"event_id":eid,"source_AWST_START":F[eid][0],
             "HMP_TA_N":len(temp),
             "HMP_TA_range_C":[min(x["original_L6_numeric_value"] for x in temp),max(x["original_L6_numeric_value"] for x in temp)] if temp else [],
             "HMP_RH_N":len(hum),
             "HMP_RH_range_pct":[min(x["original_L6_numeric_value"] for x in hum),max(x["original_L6_numeric_value"] for x in hum)] if hum else [],
             "HMP_T_RH_sameheight_valid_pairs":report_counts[("event",eid,"HMP_valid_sameheight_pair_count")],
             "HMP_pairs":pairs})
    report={"site":"AU-Gin","stage":"Stage14 L6 END-stamped same-source Ta lineage and multi-height sensor physical review",
      "original_TERN_ZIP_SHA256":ZIP_SHA,"original_Gingin_L6_SHA256":OLD_SHA,
      "actual_Stage13_receipt_SHA256":sha(REP13),
      "actual_Stage13_sensor_inventory_SHA256":sha(INV13),
      "actual_Stage13_7event_allclock_samples_SHA256":sha(VAL13),
      "actual_Stage12_receipt_SHA256":sha(REP12),
      "original_oldL6_time_zone":"Australia/Perth",
      "BIF_UTC_OFFSET":8,
      "source_local_START_to_oldL6_local_END_offset_minutes":30,
      "four_explicit_TA_F_equals_old_Ta_within_0_005_C":True,
      "clock_alignment_evidence":"NUMERIC_MATCH_AND_METADATA_END_LABEL_PROBABLE_NOT_OFFICIAL_SOURCE_RELEASE",
      "oldL6_is_same_station_product_NOT_independent_weather_confirmation":True,
      "seven_original_events":7,"five_oldL6_halfhours_per_event":5,
      "original_oldL6_raw_sensor_candidates":len(inv),
      "oldL6_samples_total":len(results),
      "source_multilevel_center_sensor_evidence":diag,
      "2013_VPD_QC1_thermodynamic_problem_still_HOLD":True,
      "28_original_AU_Gin_event_groups_all_HOLD":True,
      "science_repair_authorised":False,
      "meets_strict_15_real_measurement_years":False,
      "any_original_zip_L6_NOAA_DATM_Surface_CIME_or_Slurm_write":False,
      "AD400_authorised":False}
    out.mkdir(mode=0o700,exist_ok=False)
    write(out/"stage14_AU_Gin_four_TA_L6END_FLUXMETSTART_lineage_matches.tsv",ALIGN_COLS,align)
    write(out/"stage14_AU_Gin_7event_5HH_all37_L6_sensors_original_QC.tsv",SENSOR_COLS,results)
    write(out/"stage14_AU_Gin_7event_5height_HMP_T_RH_VPD_source_physics.tsv",PAIR_COLS,pairedrows)
    (out/"stage14_AU_Gin_oldL6_endstamp_multisensor_source_science_HOLD.json").write_text(
      json.dumps(report,indent=2,ensure_ascii=False),encoding="utf-8")
    print("STAGE14 ORIGINAL TERN ZIP/L6 AND STAGE12/13 SOURCE SHA256 VERIFIED")
    for a in align:
        print("ENDSTAMP_MATCH",a["event_id"],
              "TERN_START",a["TERN_local_timestamp_START"],
              "OLD_L6_END",a["L6_local_timestamp_END"],
              "TERN_TA",a["TERN_TA_F_C"],
              "OLD_L6_TA",a["old_L6_Ta_C"],
              "ABS_DIFF_C",a["abs_difference_degC"])
    for d in diag:
        print("EVENT_MULTISENSOR",d["event_id"],
              "HMP_T_N",d["HMP_TA_N"],"HMP_T_RANGE_C",d["HMP_TA_range_C"],
              "HMP_RH_N",d["HMP_RH_N"],"HMP_RH_RANGE",d["HMP_RH_range_pct"],
              "MATCHED_T_RH_PAIRS",d["HMP_T_RH_sameheight_valid_pairs"])
    for x in pairedrows:
        if x["event_id"] in ("VPD_QC1_20130205","VPD_QC1_20130216",
                             "TA_20160507","TA_20160520"):
            print("HMP_HEIGHT",x["event_id"],x["height_token_HMP"],
                  "T",x["old_Ta_HMP_C"],"TA_QC",x["old_Ta_HMP_QC_raw_code"],
                  "RH",x["old_RH_HMP_percent"],"RH_QC",x["old_RH_HMP_QC_raw_code"],
                  "SOURCE_PAIR_VPD_HPA",x["VPD_HMP_pair_diagnostic_hPa_NOT_APPLIED"],
                  "TERN_VPD_F",x["TERN_VPD_F_hPa"])
    print("STAGE14 READONLY MULTISENSOR AUDIT PASS; NO SCIENCE REPAIR / FORCING / AD400")
    print("REPORT_DIR",out)
if __name__=="__main__":main()
