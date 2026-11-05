#!/usr/bin/env python3
"""Stage09: AU-Gin original UTC_OFFSET + 5 spikes + 2 QC1 VPD reviews.

Read-only science evidence only. 7 priority individual timestamps are NOT
approved corrections; interpolation is a labelled, un-applied diagnostic,
not a proposed future forcing dataset. All original source and cases held.
"""
from __future__ import annotations
import argparse,csv,datetime as dt,hashlib,json,math
from pathlib import Path
H=Path.home()
S05=H/"ozflux_AU_Gin_stage05_20261105T034925Z"
S07=H/"ozflux_AU_Gin_stage07_20261105T041806Z"
S08=H/"ozflux_AU_Gin_stage08_20261105T042541Z"
ZIP=Path("/iridisfs/scratch/ly3n24/CLM_FATES/sites/MY_EC_SITE/AU-Gin/forcing/raw/TERN_FLUXNET_2011_2025/TERN_AU-Gin_FLUXNET_2011-2025_v1.3_r1.zip")
ZIP_SHA="acd78491b6f5f2c1374da2076d73a6c8b6ef430b256b78da3d300656943d6f14"
AUD05=S05/"stage05_AU_Gin_28event_preBOM_science_HOLD.json"
AUD07=S07/"stage07_AU_Gin_5event_noaa_pearce_science_HOLD.json"
AUD08=S08/"stage08_AU_Gin_time_provenance_5case_science_HOLD.json"
CONTEXT=S05/"stage05_AU_Gin_6h_source_QC_ERA_context.tsv"
EVENTS=S05/"stage05_AU_Gin_28group_priorities.tsv"
SOURCE=S08/"stage08_AU_Gin_original_BIF_timezone_source_rows.tsv"
INDEPENDENT=S08/"stage08_AU_Gin_5case_independent_NOAA_vs_tower_neighbor_HOLD.tsv"
SPIKES=(
 ("PA_20120609_PREVIOUS","2012-06-09 08:00:00","PA","PA_20120609",1.5,0.8),
 ("PA_20120610","2012-06-10 13:30:00","PA","PA_20120610",1.5,0.8),
 ("TA_20160507","2016-05-07 16:00:00","TA","TA_20160507",8.0,5.0),
 ("TA_20160520","2016-05-20 18:00:00","TA","TA_20160520",8.0,5.0),
 ("WS_20190913","2019-09-13 03:00:00","WS","WS_20190913",10.0,5.0))
VPD=(
 ("VPD_QC1_20130205","2013-02-05 06:30:00"),
 ("VPD_QC1_20130216","2013-02-16 07:00:00"))
FIELDS=("candidate_id","tower_local_standard_time","variable",
  "source_before_F","source_before_QC","source_center_F","source_center_QC",
  "source_after_F","source_after_QC","source_center_ERA",
  "diagnostic_linear_neighbor_mean_NOT_FORCING",
  "diagnostic_center_minus_neighbor_mean",
  "neighbor_two_point_difference",
  "candidate_interpolation_science_gate",
  "interpolation_written_to_original_or_model",
  "independent_station","independent_hourly_UTC","independent_QC",
  "independent_Pearce_value_in_same_units",
  "independent_vs_tower_center_difference",
  "external_minutes_from_actual_candidate_UTC",
  "external_site_equivalent_to_flux_tower",
  "scientific_repair_approved")
VPD_FIELDS=("event_id","tower_native_time","TA_F","TA_F_QC","VPD_F",
            "VPD_F_QC","VPD_ERA_same_product","saturation_es_hPa",
            "RH_implied_percent","source_pair_physics_inconsistent",
            "remediation_approved")
def check(cond,msg):
    if not cond:raise RuntimeError(str(msg))
def sha(p):
    p=Path(p)
    check(p.is_file() and not p.is_symlink(),"Original input missing or symlink "+str(p))
    h=hashlib.sha256()
    with p.open("rb") as f:
        for data in iter(lambda:f.read(4<<20),b""):h.update(data)
    return h.hexdigest()
def read(path):
    with path.open(encoding="utf-8",newline="") as f:
        return list(csv.DictReader(f,delimiter="\t"))
def num(x):
    try:
        v=float(str(x).strip())
        return v if math.isfinite(v) and -9990<v<9990 else None
    except (TypeError,ValueError):return None
def date(x):return dt.datetime.fromisoformat(str(x).strip())
def ts(x):return x.strftime("%Y-%m-%d %H:%M:%S")
def as_c(x,unit):
    return x/10 if unit=="PA" else x
def save(p,names,rows):
    with p.open("x",encoding="utf-8",newline="") as f:
        w=csv.DictWriter(f,delimiter="\t",fieldnames=names,extrasaction="raise")
        w.writeheader();w.writerows(rows)
def unit_of(var):
    return "hPa" if var=="PA" else ("degC" if var=="TA" else "m/s")
def selftest():
    check(abs((99.0+99.6)/2-99.3)<1e-12,"pressure candidate")
    check(abs((15.42+12.44)/2-13.93)<1e-12,"temperature candidate")
    check(abs((.43+.45)/2-.44)<1e-12,"wind candidate")
    check(len(SPIKES)==5 and len(VPD)==2,"priority 5+2")
    check(date("2012-06-09 08:00:00")-dt.timedelta(hours=8)
          ==date("2012-06-09 00:00:00"),"AWST offset")
    print("AU-GIN STAGE09 SELFTEST PASS | 5 spike + 2 QC1 VPD source shadow, BIF UTC+8; READ ONLY")
def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--self-test",action="store_true")
    ap.add_argument("--out",type=Path)
    a=ap.parse_args()
    if a.self_test:return selftest()
    o=a.out
    check(o is not None and o.parent.resolve()==H.resolve() and
          not o.exists() and not o.is_symlink(),"New direct HOME directory required")
    check(sha(ZIP)==ZIP_SHA,"Original AU-Gin TERN source ZIP changed")
    old05=json.loads(AUD05.read_text(encoding="utf-8"))
    old07=json.loads(AUD07.read_text(encoding="utf-8"))
    old08=json.loads(AUD08.read_text(encoding="utf-8"))
    check(old05.get("source_zip_SHA256")==ZIP_SHA
          and old05.get("original_44_screen_flags")==44
          and old05.get("number_of_grouped_events")==28
          and old05.get("source_context_halfhours_in_windows")==678
          and old05.get("AD400_authorised") is False,
          "Stage05 real original science receipt changed")
    check(old07.get("original_tower_FLUXNET_zip_SHA256")==ZIP_SHA
          and old07.get("case_count")==5
          and old07.get("AD400_authorised") is False,
          "Stage07 independently obtained source receipt changed")
    check(old08.get("original_fluxnet_ZIP_SHA256")==ZIP_SHA
          and old08.get("original_BIF_member_SHA256")==
          "d28640e9f9a1bef14d0dc54679f56f4674652e88efc9ac15a93425e725fb8a0e"
          and old08.get("AD400_authorised") is False,
          "Stage08 BIF and event receipt changed")
    zoneRows=read(SOURCE)
    check(len(zoneRows)==1 and
          zoneRows[0].get("variable_group")=="UTC_OFFSET"
          and zoneRows[0].get("variable")=="UTC_OFFSET"
          and zoneRows[0].get("original_DATAVALUE")=="8",
          "AU-Gin original BIF UTC_OFFSET=8 missing or changed")
    check(old08.get("original_BIF_timezone_fields")==[
          {"group_id":"4669","variable_group":"UTC_OFFSET",
           "variable":"UTC_OFFSET","original_DATAVALUE":"8"}],
          "Original Stage08 BIF exact time zone provenance changed")
    source=read(CONTEXT)
    check(len(source)==678,"Stage05 678 original halfhour contexts changed")
    byTime={}
    for r in source:
        t=date(r["native_time"])
        check(t not in byTime,"Duplicate original source HH context")
        byTime[t]=r
    ev=read(EVENTS)
    check(len(ev)==28,"28 grouped original events changed")
    independent=read(INDEPENDENT)
    check(len(independent)==10,"Five events x two time hypotheses changed")
    compare={}
    for row in independent:
        if row["time_alignment_hypothesis"]=="native_as_AWST_UTCplus8_UNVERIFIED":
            k=row["event_id"]
            check(k not in compare,"Multiple original NOAA AWST match "+k)
            compare[k]=row
    check(len(compare)==5,"Missing NOAA AWST five original comparisons")
    out=[]
    for identifier,localtime,var,case,screen,neighborScreen in SPIKES:
        t=date(localtime)
        a0=byTime.get(t-dt.timedelta(minutes=30))
        a1=byTime.get(t)
        a2=byTime.get(t+dt.timedelta(minutes=30))
        check(a0 is not None and a1 is not None and a2 is not None,
              "Original before/after source missing for "+identifier)
        pv=num(a0[var+"_F"]);cv=num(a1[var+"_F"]);nv=num(a2[var+"_F"])
        pq=a0[var+"_F_QC"];cq=a1[var+"_F_QC"];nq=a2[var+"_F_QC"]
        check(all(x is not None for x in (pv,cv,nv)) and cq in ("0","0.0"),
              "Original source center QC0 and numeric evidence changed")
        midpoint=(pv+nv)/2
        prominence=cv-midpoint
        stable_neighbor=(
            pq in ("0","0.0") and nq in ("0","0.0") and
            abs(pv-nv)<=neighborScreen)
        candidate_gate=("DIAGNOSTIC_SHADOW_ONLY_HOLD" if
           stable_neighbor and abs(prominence)>=screen else
           "NEIGHBOR_SCOPE_OR_SPIKE_SCREEN_HOLD")
        ext=compare[case]
        check(ext["variable"]==var,"Independent source event variable changed")
        extvalue=num(ext["airport_original_value"])
        check(extvalue is not None and ext["airport_original_quality_code"]=="0",
              "Original NOAA independent reference/QC changed")
        ec=extvalue/10 if var=="PA" else extvalue
        noaaTime=date(ext["airport_UTC_observation"])
        expectedUtc=t-dt.timedelta(hours=8)
        rows={
           "candidate_id":identifier,"tower_local_standard_time":localtime,
           "variable":var,"source_before_F":pv,"source_before_QC":pq,
           "source_center_F":cv,"source_center_QC":cq,
           "source_after_F":nv,"source_after_QC":nq,
           "source_center_ERA":a1[var+"_ERA"],
           "diagnostic_linear_neighbor_mean_NOT_FORCING":round(midpoint,6),
           "diagnostic_center_minus_neighbor_mean":round(prominence,6),
           "neighbor_two_point_difference":round(nv-pv,6),
           "candidate_interpolation_science_gate":candidate_gate,
           "interpolation_written_to_original_or_model":False,
           "independent_station":"ASN00009053 PEARCE RAAF, 43.35 km",
           "independent_hourly_UTC":ext["airport_UTC_observation"],
           "independent_QC":ext["airport_original_quality_code"],
           "independent_Pearce_value_in_same_units":ec,
           "independent_vs_tower_center_difference":round(cv-ec,6),
           "external_minutes_from_actual_candidate_UTC":
                (noaaTime-expectedUtc).total_seconds()/60,
           "external_site_equivalent_to_flux_tower":False,
           "scientific_repair_approved":False}
        out.append(rows)
    check(len(out)==5,"Five candidates not fully reconstructed")
    physics=[]
    for ident,native in VPD:
        t=date(native)
        rr=byTime.get(t)
        check(rr is not None,"2013 QC1 source context missing")
        ta=num(rr["TA_F"]);vpd=num(rr["VPD_F"])
        check(ta is not None and vpd is not None,"2013 physical source values missing")
        es=6.112*math.exp(max(-50,min(30,17.67*ta/(ta+243.5))))
        derived=100*(es-vpd)/es
        check(rr["VPD_F_QC"] in ("1","1.0") and derived<-1,
              "2013 VPD_QC1 negative RH evidence changed")
        physics.append({
          "event_id":ident,"tower_native_time":native,
          "TA_F":ta,"TA_F_QC":rr["TA_F_QC"],
          "VPD_F":vpd,"VPD_F_QC":rr["VPD_F_QC"],
          "VPD_ERA_same_product":rr["VPD_ERA"],
          "saturation_es_hPa":round(es,6),
          "RH_implied_percent":round(derived,4),
          "source_pair_physics_inconsistent":True,
          "remediation_approved":False})
    report={
      "site":"AU-Gin","stage":"Stage09 BIF verified UTC+08 source-context shadow only",
      "original_tern_source_zip_sha256":ZIP_SHA,
      "Stage05_receipt_sha256":sha(AUD05),
      "Stage07_receipt_sha256":sha(AUD07),
      "Stage08_receipt_sha256":sha(AUD08),
      "Stage05_678_source_context_SHA256":sha(CONTEXT),
      "Stage08_5case_NOAA_source_comparison_SHA256":sha(INDEPENDENT),
      "BIF_UTC_OFFSET_metadata_verified":8,
      "BIF_operator_native_timestamp_start_end_semantics_not_independently_verified":True,
      "AWST_primary_alignment_due_to_BIF_and_FLUXNET_local_standard_time":True,
      "NOAA_station_separation_km":43.35,
      "five_reconstructed_priority_source_points":out,
      "two_original_VPD_QC1_physics_source_conflicts":physics,
      "original_28_events_all_unresolved":True,
      "interpolation_never_written_and_NOT_approved_for_model":True,
      "15_complete_calendar_years_filled_product":True,
      "15_true_measured_tower_years_available":False,
      "science_release":False,"AD400_authorised":False,
      "no_source_NOAA_DATM_Surface_CIME_Slurm_modifications":True}
    o.mkdir(mode=0o700,exist_ok=False)
    save(o/"stage09_AU_Gin_five_spike_nonapplied_shadow_decision.tsv",FIELDS,out)
    save(o/"stage09_AU_Gin_two_VPD_QC1_physics_inconsistencies.tsv",
         VPD_FIELDS,physics)
    (o/"stage09_AU_Gin_BIF_AWST_7priority_source_science_HOLD.json").write_text(
       json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    print("STAGE09 ORIGINAL TERN ZIP & REAL STAGE05/07/08 SOURCE SHA256 VERIFIED")
    print("BIF_EXACT_SITE_UTC_OFFSET",8,"FLUXNET_NATIVE_STANDARD_TIME_AWST_SUPPORTED")
    print("28_EVENTS_ALL_SCIENCE_HOLD",len(ev),
          "FIVE_PRIORITY_HH",len(out),"VPD_QC1_PHYSICS",len(physics))
    for r in out:
        print("SHADOW_REVIEW",r["candidate_id"],
           "PREV",r["source_before_F"],"QC",r["source_before_QC"],
           "CENTER",r["source_center_F"],"QC",r["source_center_QC"],
           "NEXT",r["source_after_F"],"QC",r["source_after_QC"],
           "NEIGHBOR_MEAN_NOT_APPLIED",r["diagnostic_linear_neighbor_mean_NOT_FORCING"],
           "GATE",r["candidate_interpolation_science_gate"],
           "NOAA",r["independent_Pearce_value_in_same_units"],
           "OFFSET_MIN",r["external_minutes_from_actual_candidate_UTC"])
    for r in physics:
        print("VPD_QC1_PHYSICS",r["tower_native_time"],
              "TA",r["TA_F"],"VPD",r["VPD_F"],
              "DERIVED_RH",r["RH_implied_percent"])
    print("STAGE09 READONLY ORIGINALS; ZERO SCIENCE RELEASE/REPAIR/AD400")
    print("REPORT_DIR",o)
if __name__=="__main__":main()
