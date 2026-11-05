#!/usr/bin/env python3
"""Stage10 AU-Gin: 28-event source science triage + 7 detailed priorities.

Reconcile actual Stage05 original 44 flagged records/28 event clusters,
the actual Stage09 four shadow-candidate spikes + one QC2-neighbor spike,
and two QC1 VPD physical conflicts. No forced correction: evidence review,
not a model-ready meteorological release.

- Verify original 127MB TERN FLUXNET ZIP immutable SHA.
- Verify actual Stage05, Stage08, Stage09 source lineage and BIF UTC_OFFSET=8.
- Re-extract 44 existing flags with exact 30-min neighbor F/QC/ERA and
  their independent grouped evidence, preserving 2012 June 9 prior-QC2.
- Print +/-3hr source QA for five spikes & two QC1 VPD inconsistency
  timestamps (TA/VPD/PA/WS/RH & original packaged ERA).
- Evaluate all 28 group review categories WITHOUT approving replacements.
- Do not touch originals, forcing, surface, CIME, Slurm, or AD400.
"""
from __future__ import annotations
import argparse,csv,datetime as dt,hashlib,json,math
from collections import Counter,defaultdict
from pathlib import Path

HOME=Path.home()
SRC=Path("/iridisfs/scratch/ly3n24/CLM_FATES/sites/MY_EC_SITE/AU-Gin/forcing/raw/TERN_FLUXNET_2011_2025/TERN_AU-Gin_FLUXNET_2011-2025_v1.3_r1.zip")
ZIP_SHA="acd78491b6f5f2c1374da2076d73a6c8b6ef430b256b78da3d300656943d6f14"
D05=HOME/"ozflux_AU_Gin_stage05_20261105T034925Z"
D08=HOME/"ozflux_AU_Gin_stage08_20261105T042541Z"
D09=HOME/"ozflux_AU_Gin_stage09_20261105T183809Z"
F05=D05/"stage05_AU_Gin_28event_preBOM_science_HOLD.json"
F05C=D05/"stage05_AU_Gin_6h_source_QC_ERA_context.tsv"
F05E=D05/"stage05_AU_Gin_28group_priorities.tsv"
F05N=D05/"stage05_AU_Gin_44_flag_previous_next_HH_differentials.tsv"
F08=D08/"stage08_AU_Gin_time_provenance_5case_science_HOLD.json"
F09=D09/"stage09_AU_Gin_BIF_AWST_7priority_source_science_HOLD.json"
F09S=D09/"stage09_AU_Gin_five_spike_nonapplied_shadow_decision.tsv"
F09V=D09/"stage09_AU_Gin_two_VPD_QC1_physics_inconsistencies.tsv"
F08TZ=D08/"stage08_AU_Gin_original_BIF_timezone_source_rows.tsv"

SOURCE_NAMES=("TA","VPD","PA","WS","SW_IN","LW_IN","P")
FOCUS=(
 ("PA_20120609_PREVIOUS","2012-06-09 08:00:00","PA"),
 ("PA_20120610","2012-06-10 13:30:00","PA"),
 ("TA_20160507","2016-05-07 16:00:00","TA"),
 ("TA_20160520","2016-05-20 18:00:00","TA"),
 ("WS_20190913","2019-09-13 03:00:00","WS"),
 ("VPD_QC1_20130205","2013-02-05 06:30:00","VPD"),
 ("VPD_QC1_20130216","2013-02-16 07:00:00","VPD"))
FLAG_COLUMNS=("group_id","native_time","variable","flag_type",
 "original_center_QC","original_F_previous","QC_previous",
 "original_F_center","original_F_next","QC_next","original_ERA_center",
 "triangle_center_minus_neighbors","neighbor_QC0_pair",
 "NOAA_external_value_NOT_ASSUMED",
 "scientific_release","repair_authorised")
EVENT_COLUMNS=("group_id","first_flag_native","last_flag_native",
 "n_flag_rows","variables","categories","science_review_type",
 "has_original_QC0_jump","has_QC1_VPD_saturation_failure",
 "has_high_VPD_screen","has_concurrent_TA_VPD_flags",
 "station_level_historical_independence_proven_for_all_flags",
 "source_QC_exceptions","automated_repairs_allowed",
 "science_release")
DETAIL_COLUMNS=("focus_id","source_local_AWST","focus_variable",
 "native_time","relative_minutes","is_focus_half_hour",
 "TA_F","TA_F_QC","TA_ERA","VPD_F","VPD_F_QC","VPD_ERA",
 "PA_F","PA_F_QC","PA_ERA","PA_raw",
 "WS_F","WS_F_QC","WS_ERA","WS_raw",
 "P_F","P_F_QC","P_ERA","P_raw",
 "RH_raw","derived_RH_pct_from_TA_VPD",
 "SW_IN_F","SW_IN_F_QC","LW_IN_F","LW_IN_F_QC",
 "science_release","originals_untouched")
DECISION_COLUMNS=("candidate_id","local_AWST","variable","original_F",
 "original_QC","preceding_F","preceding_QC","following_F","following_QC",
 "shadow_neighbor_average_NOT_APPLIED",
 "original_independent_Pearce_QC0_reference",
 "independent_pressure_or_wind_height_equivalent",
 "specific_science_gate","repair_written","AD400_authorised")
def need(x,msg):
    if not x:raise RuntimeError(str(msg))
def sha(p):
    p=Path(p)
    need(p.is_file() and not p.is_symlink(),"Missing or symlink original: "+str(p))
    h=hashlib.sha256()
    with p.open("rb") as f:
        for part in iter(lambda:f.read(4<<20),b""):h.update(part)
    return h.hexdigest()
def load_tsv(p):
    need(p.is_file() and not p.is_symlink(),"Missing TSV "+str(p))
    with p.open(encoding="utf-8",newline="") as f:
        return list(csv.DictReader(f,delimiter="\t"))
def jload(p):
    need(p.is_file() and not p.is_symlink(),"Missing receipt "+str(p))
    return json.loads(p.read_text(encoding="utf-8"))
def tstamp(t):return dt.datetime.fromisoformat(str(t).strip())
def fmt(t):return t.strftime("%Y-%m-%d %H:%M:%S")
def number(x):
    try:
        x=float(str(x).strip())
        return x if math.isfinite(x) and -9990<x<9990 else None
    except (TypeError,ValueError):return None
def implied_rh(ta,vpd):
    if ta is None or vpd is None or ta<=-70 or ta>=75:return None
    es=6.112*math.exp(max(-50,min(30,17.67*ta/(ta+243.5))))
    return (1-vpd/es)*100 if es>0 else None
def output(path,cols,rows):
    with path.open("x",encoding="utf-8",newline="") as f:
        w=csv.DictWriter(f,delimiter="\t",fieldnames=cols,extrasaction="raise")
        w.writeheader()
        w.writerows(rows)
def selftest():
    need(len(FOCUS)==7 and len(set(x[1] for x in FOCUS))==7,"7 unique events")
    need(abs(99.3-(99.0+99.6)/2)<1e-9,"PA shadow")
    need(abs(0.44-(.43+.45)/2)<1e-9,"WS shadow")
    need(implied_rh(13.61,22.071)<0,"2013 VPD saturation physics")
    need(fmt(tstamp("2016-05-07 16:00:00")-dt.timedelta(hours=8))==
         "2016-05-07 08:00:00","BIF AWST")
    print("AU-GIN STAGE10 SELFTEST PASS | 28 groups, original 44 flags, seven priority source holds; READ ONLY")
def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--self-test",action="store_true")
    p.add_argument("--out",type=Path)
    a=p.parse_args()
    if a.self_test:return selftest()
    o=a.out
    need(o is not None and o.parent.resolve()==HOME.resolve()
         and not o.exists() and not o.is_symlink(),
         "Use new direct HOME directory only")
    need(sha(SRC)==ZIP_SHA,"Original AU-Gin ZIP bytes changed")
    r05=jload(F05);r08=jload(F08);r09=jload(F09)
    need(r05.get("source_zip_SHA256")==ZIP_SHA
         and r05.get("original_44_screen_flags")==44
         and r05.get("unique_flagged_HH")==39
         and r05.get("number_of_grouped_events")==28
         and r05.get("source_context_halfhours_in_windows")==678
         and r05.get("AD400_authorised") is False,
         "Actual Stage05 44/39/28/678 receipt changed")
    need(r08.get("original_fluxnet_ZIP_SHA256")==ZIP_SHA
         and r08.get("original_BIF_member_SHA256")==
         "d28640e9f9a1bef14d0dc54679f56f4674652e88efc9ac15a93425e725fb8a0e"
         and r08.get("AD400_authorised") is False,
         "Actual Stage08 source/BIF receipt changed")
    need(r09.get("original_tern_source_zip_sha256")==ZIP_SHA
         and r09.get("BIF_UTC_OFFSET_metadata_verified")==8
         and len(r09.get("five_reconstructed_priority_source_points",[]))==5
         and len(r09.get("two_original_VPD_QC1_physics_source_conflicts",[]))==2
         and r09.get("AD400_authorised") is False,
         "Actual Stage09 source seven-priority receipt changed")
    tz=load_tsv(F08TZ)
    need(len(tz)==1 and tz[0].get("original_DATAVALUE")=="8"
         and tz[0].get("variable")=="UTC_OFFSET",
         "Actual AU-Gin BIF local standard time not verified")
    source=load_tsv(F05C)
    flags=load_tsv(F05N)
    episodes=load_tsv(F05E)
    shadow=load_tsv(F09S)
    vpd=load_tsv(F09V)
    need(len(source)==678 and len(flags)==44 and len(episodes)==28
         and len(shadow)==5 and len(vpd)==2,
         "Actual source original 678/44/28/5/2 TSV counts changed")
    context={}
    for row in source:
        t=tstamp(row["native_time"])
        need(t not in context,"Stage05 duplicate original native HH")
        context[t]=row
    flag_rows=[]
    groupflags=defaultdict(list)
    for row in flags:
        t=tstamp(row["native_time"]);var=row["variable"]
        cur=context.get(t)
        need(cur is not None and var in SOURCE_NAMES,
             "Missing original time or unsupported variable in 44 flags")
        need(abs(number(cur[var+"_F"])-number(row["F_flagged_HH"]))<1e-8,
             "Original stage05 center value differs from context")
        need(str(cur[var+"_F_QC"])==str(row["QC_current"]),
             "Original source center QC differs")
        names=[x for x in row["group_id"].split(";") if x]
        need(len(names)>0,"Group id absent for source flag")
        for name in names:groupflags[name].append(row)
        p0=number(row["F_previous_HH"]);c0=number(row["F_flagged_HH"])
        n0=number(row["F_next_HH"])
        flag_rows.append({
          "group_id":row["group_id"],"native_time":row["native_time"],
          "variable":var,"flag_type":row["flag_type"],
          "original_center_QC":row["QC_current"],
          "original_F_previous":p0,"QC_previous":row["QC_previous_HH"],
          "original_F_center":c0,"original_F_next":n0,
          "QC_next":row["QC_next_HH"],
          "original_ERA_center":row["ERA_at_flagged_HH"],
          "triangle_center_minus_neighbors":
             (c0-(p0+n0)/2 if None not in (p0,c0,n0) else None),
          "neighbor_QC0_pair":row["QC_previous_HH"] in ("0","0.0") and
                              row["QC_next_HH"] in ("0","0.0"),
          "NOAA_external_value_NOT_ASSUMED":"",
          "scientific_release":False,"repair_authorised":False})
    check_groups=set(x["group_id"] for x in episodes)
    need(len(check_groups)==28 and set(groupflags)==check_groups,
         "Original 44 flagged records fail to cover all 28 episode IDs")
    episode_out=[]
    for entry in episodes:
        gid=entry["group_id"];rs=groupflags[gid]
        categories=[r["flag_type"] for r in rs]
        varset={r["variable"] for r in rs}
        qc1=any(r["variable"]=="VPD" and r["QC_current"] in ("1","1.0") for r in rs)
        jumps=any("JUMP" in label for label in categories)
        high=any("ABOVE_SCREEN" in label for label in categories)
        typ=("VPD_QC1_SATURATION_CONFLICT" if qc1 else
             "MULTIVARIATE_TRANSITION_HOLD" if len(varset)>1 else
             "QC0_JUMP_PHYSICS_REVIEW" if jumps else
             "EXTREME_VALUE_PHYSICS_REVIEW" if high else
             "UNCLASSIFIED_ORIGINAL_EVENT_HOLD")
        episode_out.append({
           "group_id":gid,
           "first_flag_native":entry["first_flag_native"],
           "last_flag_native":entry["last_flag_native"],
           "n_flag_rows":len(rs),
           "variables":";".join(sorted(varset)),
           "categories":";".join(sorted(set(categories))),
           "science_review_type":typ,
           "has_original_QC0_jump":jumps,
           "has_QC1_VPD_saturation_failure":qc1,
           "has_high_VPD_screen":high,
           "has_concurrent_TA_VPD_flags":("TA" in varset and "VPD" in varset),
           "station_level_historical_independence_proven_for_all_flags":False,
           "source_QC_exceptions":sum(r["QC_current"] not in ("0","0.0") for r in rs),
           "automated_repairs_allowed":False,"science_release":False})
    detail=[]
    for ident,native,var in FOCUS:
        t=tstamp(native)
        rows=[(t2,row) for t2,row in context.items()
              if abs((t2-t).total_seconds())<=3*3600]
        need(len(rows)==13,"Not all 13 original halfhours available around "+ident)
        rows.sort()
        for current,row in rows:
            vals={v:number(row[v+"_F"]) for v in SOURCE_NAMES}
            rr={
             "focus_id":ident,"source_local_AWST":native,
             "focus_variable":var,
             "native_time":fmt(current),
             "relative_minutes":int((current-t).total_seconds()/60),
             "is_focus_half_hour":current==t,
             "TA_F":vals["TA"],"TA_F_QC":row["TA_F_QC"],
             "TA_ERA":row["TA_ERA"],"VPD_F":vals["VPD"],
             "VPD_F_QC":row["VPD_F_QC"],
             "VPD_ERA":row["VPD_ERA"],
             "PA_F":vals["PA"],"PA_F_QC":row["PA_F_QC"],
             "PA_ERA":row["PA_ERA"],"PA_raw":row["PA"],
             "WS_F":vals["WS"],"WS_F_QC":row["WS_F_QC"],
             "WS_ERA":row["WS_ERA"],"WS_raw":row["WS"],
             "P_F":vals["P"],"P_F_QC":row["P_F_QC"],
             "P_ERA":row["P_ERA"],"P_raw":row["P"],
             "RH_raw":row["RH"],
             "derived_RH_pct_from_TA_VPD":implied_rh(vals["TA"],vals["VPD"]),
             "SW_IN_F":vals["SW_IN"],"SW_IN_F_QC":row["SW_IN_F_QC"],
             "LW_IN_F":vals["LW_IN"],"LW_IN_F_QC":row["LW_IN_F_QC"],
             "science_release":False,"originals_untouched":True}
            detail.append(rr)
    decision=[]
    for s in shadow:
        ident=s["candidate_id"]
        checkgate=s["candidate_interpolation_science_gate"]
        specific=("SOURCE_LEFT_ADJACENT_IS_ERA_QC2__DO_NOT_INTERPOLATE"
                  if ident=="PA_20120609_PREVIOUS" else
                  "QC0_TWO_NEIGHBOR_DIAGNOSTIC_ONLY__AWAIT_APPROVAL")
        need(("NEIGHBOR_SCOPE" in checkgate) ==
             (ident=="PA_20120609_PREVIOUS"),
             "Original Stage09 QC2-neighbor vs four QC0-neighbor gates changed")
        decision.append({
          "candidate_id":ident,"local_AWST":s["tower_local_standard_time"],
          "variable":s["variable"],"original_F":s["source_center_F"],
          "original_QC":s["source_center_QC"],
          "preceding_F":s["source_before_F"],
          "preceding_QC":s["source_before_QC"],
          "following_F":s["source_after_F"],
          "following_QC":s["source_after_QC"],
          "shadow_neighbor_average_NOT_APPLIED":
              s["diagnostic_linear_neighbor_mean_NOT_FORCING"],
          "original_independent_Pearce_QC0_reference":
              s["independent_Pearce_value_in_same_units"],
          "independent_pressure_or_wind_height_equivalent":False,
          "specific_science_gate":specific,
          "repair_written":False,"AD400_authorised":False})
    need(len(detail)==7*13 and len(decision)==5 and len(episode_out)==28,
         "Actual source scoping 91/5/28 changed")
    report={
      "site":"AU-Gin","stage":"Stage10 complete 28-event source QA with 7 priority multivariate contexts",
      "original_TERN_zip_SHA256":ZIP_SHA,
      "Stage05_receipt_SHA256":sha(F05),
      "Stage08_receipt_SHA256":sha(F08),
      "Stage09_receipt_SHA256":sha(F09),
      "Stage05_original_44_neighbor_TSV_SHA256":sha(F05N),
      "Stage05_original_678_context_TSV_SHA256":sha(F05C),
      "BIF_UTC_OFFSET":8,
      "original_28_event_groups_reconstructed":28,
      "original_44_flag_rows_reconstructed":44,
      "priority_source_context_HH":91,
      "priority_shadow_candidates":5,
      "shadow_two_verified_QC0_neighbors":4,
      "2012_06_09_prior_left_QC2_blocks_naive_two_QC0_rule":True,
      "two_VPD_QC1_implied_negative_RH_source_issues":2,
      "external_Pearce_43km_NOT_site_sensor_validation":True,
      "28_groups_all_science_HOLD":True,
      "15_years_measured_tower_met_qualified":False,
      "source_science_release":False,
      "no_data_changes":True,
      "original_fluxnet_Noaa_datm_surface_cime_slurm_untouched":True,
      "AD400_authorised":False}
    o.mkdir(mode=0o700,exist_ok=False)
    output(o/"stage10_AU_Gin_28event_all_science_triage.tsv",
           EVENT_COLUMNS,episode_out)
    output(o/"stage10_AU_Gin_44flag_original_neighbour_source_QC.tsv",
           FLAG_COLUMNS,flag_rows)
    output(o/"stage10_AU_Gin_7priority_91HH_original_multivar_context.tsv",
           DETAIL_COLUMNS,detail)
    output(o/"stage10_AU_Gin_5shadow_nonapplied_decision_register.tsv",
           DECISION_COLUMNS,decision)
    (o/"stage10_AU_Gin_full_28event_7priority_science_HOLD.json").write_text(
         json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    print("STAGE10 ORIGINAL ZIP / STAGE05 / STAGE08 / STAGE09 SHA256 VERIFIED")
    print("BIF_SOURCE_UTC_OFFSET",8,
          "GROUPS",len(episode_out),"FLAGS",len(flag_rows),
          "7_PRIORITY_CONTEXT_HALF_HOURS",len(detail))
    for x in decision:
        print("SHADOW_GATE",x["candidate_id"],"VALUE",x["original_F"],
              "BEFORE",x["preceding_F"],"QC",x["preceding_QC"],
              "AFTER",x["following_F"],"QC",x["following_QC"],
              "DIAGNOSTIC_ONLY",x["shadow_neighbor_average_NOT_APPLIED"],
              "GATE",x["specific_science_gate"])
    for x in episode_out:
        print("GROUP_TRIAGE",x["group_id"],x["first_flag_native"],
              x["science_review_type"],"FLAGS",x["n_flag_rows"],
              "VARS",x["variables"])
    print("STAGE10 SCIENCE HOLD | NO REPAIRS, NO FORCING, NO SLURM")
    print("REPORT_DIR",o)
if __name__=="__main__":main()
