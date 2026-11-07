#!/usr/bin/env python3
"""AU-Gin Stage13: OLD OzFlux L6 sensor values at seven first-party flux events.

Actual TERN Stage12 identified no explicit raw TA in the new ZIP, one RH
field with no RH at two 2013 VPD QC1 anomalies, and 358 candidate Old L6
variable headers (many are QCFlag, NOT 358 confirmed sensors).

This is a SOURCE-FORENSIC READ, not comparison of equivalent datasets.
Old L6 time uses days since 1800; its original timezone and interval
label semantics are not yet authoritatively reconciled with TERN FLUXNET
TIMESTAMP_START in local AWST +8. Preserve FOUR clock interpretations:
  (1) Old L6 clock local start label = FLUXNET START;
  (2) Old L6 clock local END label = FLUXNET START + 30 minutes;
  (3) Old L6 clock UTC start label = FLUXNET START - 8 hours;
  (4) Old L6 clock UTC END label = FLUXNET START - 8h + 30 minutes.
These are alternatives, not alignment approvals. Sample only time-matched
candidate TA/RH/AH/VPD/WS/PA sensors (including old L6 QCFlag values),
never blend or overwrite originals.

Original raw files are SHA256-pinned, stage12 operator report is used to
establish lineage, and all outputs are new HOME-only reports. No original,
forcing, DATM, Surface, CIME, Slurm or AD400 changes.
"""
from __future__ import annotations
import argparse,csv,datetime as dt,hashlib,json,math,re
from collections import Counter
from pathlib import Path

HOME=Path.home()
ZIP=Path("/iridisfs/scratch/ly3n24/CLM_FATES/sites/MY_EC_SITE/AU-Gin/forcing/raw/TERN_FLUXNET_2011_2025/TERN_AU-Gin_FLUXNET_2011-2025_v1.3_r1.zip")
ZIP_SHA="acd78491b6f5f2c1374da2076d73a6c8b6ef430b256b78da3d300656943d6f14"
L6=Path("/iridisfs/scratch/ly3n24/CLM_FATES/sites/MY_EC_SITE/AU-Gin/forcing/raw/Gingin_L6.nc")
L6_SHA="0e700e37ead024a7eda4cdf9b47f839d5dc5bfa5578087e9af1ddd09aa510d66"
D12=HOME/"ozflux_AU_Gin_stage12_20261107T045708Z"
D11=HOME/"ozflux_AU_Gin_stage11_20261107T044259Z"
S12=D12/"stage12_AU_Gin_source_identity_TA_RH_VPD_2016_2013_science_HOLD.json"
L6HEAD=D12/"stage12_AU_Gin_older_L6_channel_metadata_not_equivalent.tsv"
BIF=D12/"stage12_AU_Gin_original_BIF_sensor_QC_height_provenance.tsv"
S11=D11/"stage11_AU_Gin_7priority_source_science_HOLD.json"
T11=D11/"stage11_AU_Gin_2VPD_QC1_source_RH_physics.tsv"
SPIKES=D11/"stage11_AU_Gin_5spike_multivar_source_gate.tsv"
FOCUS={
 "PA_20120609_PREVIOUS":("2012-06-09 08:00:00","PA"),
 "PA_20120610":("2012-06-10 13:30:00","PA"),
 "TA_20160507":("2016-05-07 16:00:00","TA"),
 "TA_20160520":("2016-05-20 18:00:00","TA"),
 "WS_20190913":("2019-09-13 03:00:00","WS"),
 "VPD_QC1_20130205":("2013-02-05 06:30:00","VPD"),
 "VPD_QC1_20130216":("2013-02-16 07:00:00","VPD")}
CLOCKS=(
 ("L6_LOCAL_TIME_MATCH_FLUXMET_START",0),
 ("L6_LOCAL_END_MATCH_FLUXMET_START_PLUS_30MIN",30),
 ("L6_UTC_TIME_MATCH_AWST_START_MINUS_8H",-480),
 ("L6_UTC_END_MATCH_AWST_START_MINUS_8H_PLUS_30MIN",-450))
CAND_COLS=("variable_name","variable_class","original_units","original_long_name",
 "original_dimensions","original_shape","metadata_height_field",
 "possible_height_token_in_name_NOT_VERIFIED","paired_QCFlag_variable",
 "is_auxiliary_or_alternate_sensor_lineage","is_noaa_or_FLUXMET_equivalent",
 "source_meaning_or_height_science_approved")
CLOCK_COLS=("focus_id","source_TERN_AWST_FLUXMET_TIMESTAMP_START",
 "L6_time_hypothesis_NOT_APPROVED","target_L6_numeric_time",
 "old_L6_index_if_within_35min","nearest_L6_original_native_time",
 "native_time_delta_from_hypothesis_min",
 "match_within_1min","original_clock_alignment_approved")
VALUE_COLS=("focus_id","source_TERN_AWST_timestamp","source_variable",
 "L6_time_hypothesis_NOT_APPROVED","L6_nearest_native_timestamp",
 "minutes_L6_from_hypothesis","L6_candidate_name","L6_candidate_class",
 "L6_original_value","L6_original_units","L6_original_QCFlag_variable",
 "L6_original_QCFlag_value","measurement_height_original_attribute",
 "L6_original_source_value_is_not_TERN_QC0_proof",
 "L6_time_zone_or_timestamp_definition_verified",
 "sensor_calibration_and_height_equivalent","repair_approved")
def need(yes,msg):
    if not yes:raise RuntimeError(str(msg))
def sha(p):
    p=Path(p)
    need(p.is_file() and not p.is_symlink(),"Protected source missing or symlink "+str(p))
    h=hashlib.sha256()
    with p.open("rb") as f:
        for part in iter(lambda:f.read(4<<20),b""):h.update(part)
    return h.hexdigest()
def data(p):
    need(p.is_file() and not p.is_symlink(),"Prior receipt missing "+str(p))
    return json.loads(p.read_text(encoding="utf-8"))
def rows(p):
    need(p.is_file() and not p.is_symlink(),"Prior original TSV missing "+str(p))
    with p.open(encoding="utf-8",newline="") as f:return list(csv.DictReader(f,delimiter="\t"))
def save(p,cols,items):
    with p.open("x",encoding="utf-8",newline="") as f:
        wr=csv.DictWriter(f,fieldnames=cols,delimiter="\t",extrasaction="raise")
        wr.writeheader();wr.writerows(items)
def classify(name):
    s=name.upper().replace("-","_")
    if "QCFLAG" in s or re.search(r"(^|_)QC($|_)",s):return None
    if re.match(r"^(TA|TAIR|T_AIR|AIR_TEMP|AIRTEMP)(_|$)",s):return "TA"
    if re.match(r"^(RH|RELHUM|RELATIVE_HUMIDITY)(_|$)",s):return "RH"
    if re.match(r"^(AH|ABS_HUM|ABSOLUTE_HUMIDITY|H2O)(_|$)",s):return "AH"
    if re.match(r"^(VPD|VAPOR_PRESSURE_DEFICIT)(_|$)",s):return "VPD"
    if re.match(r"^(WS|WSPD|WINDSPEED|WIND_SPEED)(_|$)",s):return "WS"
    if re.match(r"^(PA|PS|PRESS|PRESSURE|ATM_PRESS|AIR_PRESS)(_|$)",s):return "PA"
    return None
def scalar(v,index):
    import numpy as np
    if not v.dimensions or v.dimensions[0]!="time":return None
    if any(int(x)!=1 for x in v.shape[1:]):return None
    cell=v[(int(index),)+(0,)*(v.ndim-1)]
    if np.ma.is_masked(cell):return None
    try:
        x=float(np.asarray(cell).item())
        if not math.isfinite(x) or abs(x)>=9990:return None
        for n in ("_FillValue","missing_value"):
            if n in v.ncattrs():
                fill=np.asarray(v.getncattr(n)).ravel()
                if any(math.isclose(x,float(y),rel_tol=0,abs_tol=1e-6)
                       for y in fill if np.isfinite(float(y))):
                    return None
        return x
    except (ValueError,TypeError,OverflowError):return None
def height_from_name(name):
    m=re.search(r"(?i)(?:^|_)(\d+(?:\.\d+)?)(m|cm)(?:_|$)",name)
    return (m.group(1)+m.group(2)) if m else ""
def source_time(tc):
    if hasattr(tc,"strftime"):return tc.strftime("%Y-%m-%d %H:%M:%S")
    return str(tc)
def test():
    need(classify("Ta_HMP_10m_Av")=="TA","Actual OzFlux TA name")
    need(classify("RH_HMP_2m_Av")=="RH","Humidity name")
    need(classify("AH_HMP_10m_Av")=="AH","Absolute humidity name")
    need(classify("Ws_SENTRY_200cm_Av")=="WS","Wind name")
    need(classify("Ta_HMP_2m_Av_QCFlag") is None,"QCFlag not a sensor")
    need(height_from_name("AH_HMP_10m_Av")=="10m","Name height is only hint")
    need(len(FOCUS)==7 and len(CLOCKS)==4,"Seven source times/four clock hypotheses")
    need(dt.datetime.fromisoformat("2013-02-05 06:30:00")+dt.timedelta(minutes=-480)==
         dt.datetime(2013,2,4,22,30),"AWST UTC -8")
    print("AU-GIN STAGE13 SELFTEST PASS | old L6 native sensor and 4 clock hypotheses; READ ONLY")
def main():
    import numpy as np
    import netCDF4
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--self-test",action="store_true")
    p.add_argument("--out",type=Path)
    a=p.parse_args()
    if a.self_test:return test()
    o=a.out
    need(o is not None and o.parent.resolve()==HOME.resolve() and not o.exists()
         and not o.is_symlink(),"New direct HOME output directory only")
    need(sha(ZIP)==ZIP_SHA and sha(L6)==L6_SHA,"Original new TERN or old OzFlux L6 bytes changed")
    r12=data(S12);r11=data(S11)
    need(r12.get("original_TERN_zip_SHA256")==ZIP_SHA
         and r12.get("FLUXMET_HH_column_count")==221
         and r12.get("ZIP_members_with_raw_like_TA")==0
         and r12.get("ZIP_members_with_raw_like_RH")==1
         and r12.get("older_L6_metadata_status",{}).get("old_L6_SHA256")==L6_SHA
         and r12.get("AD400_authorised") is False,
         "Actual operator Stage12 source count/hash/HOLD receipt changed")
    need(r11.get("original_zip_SHA256")==ZIP_SHA
         and r11.get("priority_single_sample_spike_source_reviews")==5
         and r11.get("VPD_QC1_physics_conflicts")==2
         and r11.get("AD400_authorised") is False,
         "Operator Stage11 original seven-priority receipt changed")
    oldmeta=rows(L6HEAD);bif=rows(BIF)
    need(len(oldmeta)==358 and len(bif)==334,
         "Original Stage12 actual L6 358 headers / BIF 334 metadata changed")
    need(len(rows(T11))==2 and len(rows(SPIKES))==5,
         "Original Stage11 RH-QC1 and spike center data changed")
    candidates=[]; time_summ=[];samples=[];time_context={}
    with netCDF4.Dataset(str(L6),"r") as ds:
        need("time" in ds.variables,"Original L6 missing time axis")
        tim=ds.variables["time"]
        need(tim.ndim==1 and tim.dimensions==("time",),"Old L6 primary time not one-dimensional")
        units=str(getattr(tim,"units",""))
        calendar=str(getattr(tim,"calendar","standard"))
        time_context={
          "old_L6_time_variable_original_attributes":{
            k:str(tim.getncattr(k))[:450] for k in tim.ncattrs()},
          "old_L6_global_time_site_original_attributes":{
            k:str(ds.getncattr(k))[:450] for k in ds.ncattrs()
            if any(w in k.lower() for w in
                  ("time","utc","zone","offset","site","period","interval",
                   "start","end","height","latitude","longitude"))}}
        need("days since 1800-01-01" in units and len(tim)==250821,
             "Old L6 actual Stage12 250821 CF-date axis changed")
        rawtime=np.ma.filled(tim[:],np.nan).astype(float)
        need(np.all(np.isfinite(rawtime)) and np.all(np.diff(rawtime)>0),
             "Old L6 time axis invalid/nonmonotonic; no automatic sorting permitted")
        allmeta={x["variable_name"]:x for x in oldmeta}
        # Read source metadata, not full arrays. Include every plausible raw
        # meteorology sensor value; skip QCFlags as standalone observations.
        for name,v in ds.variables.items():
            typ=classify(name)
            if typ is None:continue
            if (not v.dimensions or v.dimensions[0]!="time"
                    or any(int(q)!=1 for q in v.shape[1:])):
                continue
            if name not in allmeta:
                continue
            qcname=next((q for q in (
                 name+"_QCFlag",
                 name.replace("_Av","_QCFlag"),
                 name.replace("_Av","")+"_QCFlag")
                 if q in ds.variables),None)
            attrheight=str(getattr(v,"height",""))[:140]
            candidates.append({
             "variable_name":name,"variable_class":typ,
             "original_units":str(getattr(v,"units",""))[:150],
             "original_long_name":str(getattr(v,"long_name",""))[:180],
             "original_dimensions":",".join(v.dimensions),
             "original_shape":str(tuple(int(q) for q in v.shape)),
             "metadata_height_field":attrheight,
             "possible_height_token_in_name_NOT_VERIFIED":height_from_name(name),
             "paired_QCFlag_variable":qcname or "",
             "is_auxiliary_or_alternate_sensor_lineage":True,
             "is_noaa_or_FLUXMET_equivalent":False,
             "source_meaning_or_height_science_approved":False})
        need(candidates,"Old L6 has no source-matched TA/RH/AH/VPD/WS/PA candidates")
        indices={}
        for ident,(native,focusvariable) in FOCUS.items():
            base=dt.datetime.fromisoformat(native)
            for label,offset in CLOCKS:
                target=base+dt.timedelta(minutes=offset)
                tn=float(netCDF4.date2num(target,units=units,calendar=calendar))
                ix=int(np.searchsorted(rawtime,tn,side="left"))
                feasible=[j for j in (ix-1,ix) if 0<=j<len(rawtime)]
                best=min(feasible,key=lambda j:abs(rawtime[j]-tn))
                delta=(rawtime[best]-tn)*24*60
                if abs(delta)>35:
                    indices[(ident,label)]=None
                    matched=""
                else:
                    indices[(ident,label)]=best
                    matched=str(best)
                sourcevalue=netCDF4.num2date(rawtime[best],units=units,calendar=calendar)
                time_summ.append({
                   "focus_id":ident,
                   "source_TERN_AWST_FLUXMET_TIMESTAMP_START":native,
                   "L6_time_hypothesis_NOT_APPROVED":label,
                   "target_L6_numeric_time":repr(tn),
                   "old_L6_index_if_within_35min":matched,
                   "nearest_L6_original_native_time":source_time(sourcevalue),
                   "native_time_delta_from_hypothesis_min":round(float(delta),4),
                   "match_within_1min":abs(delta)<=1,
                   "original_clock_alignment_approved":False})
        for c in candidates:
            var=ds.variables[c["variable_name"]]
            qcname=c["paired_QCFlag_variable"]
            qc=ds.variables[qcname] if qcname else None
            for ident,(native,focusvariable) in FOCUS.items():
                for label,_ in CLOCKS:
                    ix=indices[(ident,label)]
                    if ix is None:continue
                    v=scalar(var,ix)
                    if v is None:continue
                    qv=scalar(qc,ix) if qc is not None else None
                    timekey=next(r for r in time_summ if
                         r["focus_id"]==ident and
                         r["L6_time_hypothesis_NOT_APPROVED"]==label)
                    samples.append({
                      "focus_id":ident,"source_TERN_AWST_timestamp":native,
                      "source_variable":focusvariable,
                      "L6_time_hypothesis_NOT_APPROVED":label,
                      "L6_nearest_native_timestamp":
                           timekey["nearest_L6_original_native_time"],
                      "minutes_L6_from_hypothesis":
                           timekey["native_time_delta_from_hypothesis_min"],
                      "L6_candidate_name":c["variable_name"],
                      "L6_candidate_class":c["variable_class"],
                      "L6_original_value":v,
                      "L6_original_units":c["original_units"],
                      "L6_original_QCFlag_variable":qcname,
                      "L6_original_QCFlag_value":qv,
                      "measurement_height_original_attribute":c["metadata_height_field"],
                      "L6_original_source_value_is_not_TERN_QC0_proof":True,
                      "L6_time_zone_or_timestamp_definition_verified":False,
                      "sensor_calibration_and_height_equivalent":False,
                      "repair_approved":False})
    check_2013=[r for r in samples if
         r["focus_id"] in ("VPD_QC1_20130205","VPD_QC1_20130216")
         and r["L6_candidate_class"] in ("TA","RH","AH","VPD")]
    report={
     "site":"AU-Gin","stage":"Stage13 old OzFlux Gingin L6 first-party RH/TA physical source inspection",
     "new_TERN_original_ZIP_SHA256":ZIP_SHA,
     "old_L6_original_SHA256":L6_SHA,
     "Stage12_source_receipt_SHA256":sha(S12),
     "Stage11_source_receipt_SHA256":sha(S11),
     "old_L6_calendar":calendar,
     "old_L6_time_units":units,
     "old_L6_native_time_metadata_NOT_automatically_reconciled":time_context,
     "old_L6_time_length":len(rawtime),
     "old_L6_source_sensor_candidate_count":len(candidates),
     "old_L6_candidate_class_counts":dict(Counter(x["variable_class"] for x in candidates)),
     "original_four_clock_hypotheses":list(x[0] for x in CLOCKS),
     "old_L6_clock_alignment_approved":False,
     "old_L6_timezone_and_interval_end_ambiguity_unresolved":True,
     "old_L6_variable_or_QC_semantics_verified":False,
     "seven_original_source_focus_times":7,
     "source_sensor_raw_nonmissing_records":len(samples),
     "2013_two_VPD_source_times_possible_TA_RH_AH_records":len(check_2013),
     "all_28_original_TERN_event_groups_science_HOLD":True,
     "2012_PA_left_original_QC2_neighbor_hard_hold":True,
     "station_duration_strict_15_real_measurement_years_met":False,
     "no_original_or_forcing_DATM_Surface_CIME_Slurm_changes":True,
     "scientific_repair_approved":False,"AD400_authorised":False}
    o.mkdir(mode=0o700,exist_ok=False)
    save(o/"stage13_AU_Gin_old_L6_raw_like_sensor_inventory.tsv",CAND_COLS,candidates)
    save(o/"stage13_AU_Gin_7event_old_L6_4unapproved_clock_matches.tsv",CLOCK_COLS,time_summ)
    save(o/"stage13_AU_Gin_7event_old_L6_source_TA_RH_AH_VPD_WS_PA_QC_samples.tsv",VALUE_COLS,samples)
    (o/"stage13_AU_Gin_oldL6_sensor_source_2013_2016_HOLD.json").write_text(
        json.dumps(report,indent=2,ensure_ascii=False),encoding="utf-8")
    print("STAGE13 ORIGINAL TERN ZIP, OLD L6, ACTUAL STAGE11/STAGE12 SHA256 VERIFIED")
    print("OLD_L6_TIME",units,"CALENDAR",calendar,
          "N",len(rawtime))
    print("OLD_L6_TIME_PROVENANCE",json.dumps(time_context,ensure_ascii=False)[:4500])
    print("OLD_L6_SENSOR_CANDIDATES",len(candidates),
          "BY_CLASS",dict(Counter(x["variable_class"] for x in candidates)))
    for x in candidates[:70]:
        print("L6_SENSOR_HEADER",x["variable_name"],
              "CLASS",x["variable_class"],
              "UNIT",x["original_units"],
              "QC_VAR",x["paired_QCFlag_variable"],
              "HEIGHT_HINT",x["possible_height_token_in_name_NOT_VERIFIED"])
    for x in time_summ:
        print("TIME_HYPOTHESIS",x["focus_id"],
              x["L6_time_hypothesis_NOT_APPROVED"],
              "L6_NATIVE",x["nearest_L6_original_native_time"],
              "DELTA_MIN",x["native_time_delta_from_hypothesis_min"],
              "MATCH_1MIN",x["match_within_1min"])
    count=0
    for x in samples:
        if (x["focus_id"] in ("VPD_QC1_20130205","VPD_QC1_20130216",
                              "TA_20160507","TA_20160520")
            and x["L6_candidate_class"] in ("TA","RH","AH","VPD")):
            print("TARGET_L6_SENSOR",x["focus_id"],
                 x["L6_time_hypothesis_NOT_APPROVED"],
                 x["L6_candidate_name"],"VALUE",x["L6_original_value"],
                 "UNIT",x["L6_original_units"],
                 "ORIGINAL_QC",x["L6_original_QCFlag_value"],
                 "TIME_DELTA_MIN",x["minutes_L6_from_hypothesis"])
            count+=1
            if count>=90:break
    print("STAGE13 READONLY L6 PROVENANCE PASS; L6 TIMESTAMP/QC SCIENCE HOLD, NO FORCING/AD400")
    print("REPORT_DIR",o)
if __name__=="__main__":main()
