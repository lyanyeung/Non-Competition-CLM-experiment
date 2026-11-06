#!/usr/bin/env python3
"""AU-Gin Stage11 | exact source seven-priority multivariate and RH/VPD physics.

Real operator Stage10 PASS: 28 groups, 44 flagged HH, 91 original half-hours
for 7 priorities. Audit those immutable rows, retaining source F/QC/ERA and
raw RH/PA/WS/P. No edits, no extrapolation, no automatic scientific release.

Two 2013 VPD_F QC1 values imply negative RH when combined with TA_F.
Check ORIGINAL raw RH if present, distinguish observed RH source from F
gap-fill, and assess duration of physical mismatch in +/-3hr intervals.

Five suspect single-halfhour 2012 PA/2016 TA/2019 WS observations: recheck
source F vs same-product raw, neighboring QC, contemporaneous TA/VPD, PA,
WS, SW and LW radiation. Candidate shadow arithmetic remains NOT APPLIED.
2012-06-09 08:00 PA left neighbor is QC2, blocking two-QC0 interpolation.

No new external source download or model run. Every flag/28 groups HOLD.
"""
from __future__ import annotations
import argparse,csv,datetime as dt,hashlib,json,math
from collections import Counter
from pathlib import Path

HOME=Path.home()
ORIGINAL=Path("/iridisfs/scratch/ly3n24/CLM_FATES/sites/MY_EC_SITE/AU-Gin/forcing/raw/TERN_FLUXNET_2011_2025/TERN_AU-Gin_FLUXNET_2011-2025_v1.3_r1.zip")
ORIGINAL_SHA="acd78491b6f5f2c1374da2076d73a6c8b6ef430b256b78da3d300656943d6f14"
STAGE10=HOME/"ozflux_AU_Gin_stage10_20261105T184415Z"
RECEIPT=STAGE10/"stage10_AU_Gin_full_28event_7priority_science_HOLD.json"
CONTEXT=STAGE10/"stage10_AU_Gin_7priority_91HH_original_multivar_context.tsv"
SHADOW=STAGE10/"stage10_AU_Gin_5shadow_nonapplied_decision_register.tsv"
GROUPS=STAGE10/"stage10_AU_Gin_28event_all_science_triage.tsv"
ORIGINAL_FLAGS=STAGE10/"stage10_AU_Gin_44flag_original_neighbour_source_QC.tsv"
FOCUS={
 "PA_20120609_PREVIOUS":("2012-06-09 08:00:00","PA"),
 "PA_20120610":("2012-06-10 13:30:00","PA"),
 "TA_20160507":("2016-05-07 16:00:00","TA"),
 "TA_20160520":("2016-05-20 18:00:00","TA"),
 "WS_20190913":("2019-09-13 03:00:00","WS"),
 "VPD_QC1_20130205":("2013-02-05 06:30:00","VPD"),
 "VPD_QC1_20130216":("2013-02-16 07:00:00","VPD")}
SPIKES=tuple(x for x in FOCUS if not x.startswith("VPD_QC1"))
VPDS=tuple(x for x in FOCUS if x.startswith("VPD_QC1"))
VPD_COLS=("focus_id","original_native_AWST","QC1_center_TA_F",
          "QC1_center_TA_F_QC","QC1_center_VPD_F",
          "QC1_center_VPD_F_QC","QC1_center_VPD_ERA",
          "source_raw_RH_at_center","source_raw_RH_is_0_to_100",
          "saturation_vapor_pressure_hPa","RH_implied_from_F_TA_VPD_percent",
          "VPD_from_raw_RH_and_F_TA_hPa_DIAGNOSTIC_ONLY",
          "F_VPD_minus_RH_constrained_DIAGNOSTIC_hPa",
          "QC1_VPD_halfhours_within_3h",
          "negative_implied_RH_halfhours_within_3h",
          "RH_raw_valid_halfhours_within_3h",
          "TA_F_QC0_halfhours_within_3h",
          "classification","raw_RH_is_independent_truth",
          "scientific_repair_approved")
SPIKE_COLS=("focus_id","original_native_AWST","variable",
            "original_prev_F","original_prev_QC",
            "original_center_F","original_center_QC",
            "original_next_F","original_next_QC",
            "source_original_RAW_same_variable_at_center",
            "original_RAW_and_F_match_at_center",
            "diagnostic_neighbour_mean_NOT_APPLIED",
            "neighbor_both_original_QC0",
            "NOAA_Pearce_reference_for_prior_review_ONLY",
            "source_center_TA_F","source_center_TA_F_QC",
            "source_center_VPD_F","source_center_VPD_F_QC",
            "source_center_PA_F","source_center_PA_F_QC",
            "source_center_WS_F","source_center_WS_F_QC",
            "source_center_SW_IN_F","source_center_SW_IN_F_QC",
            "source_center_LW_IN_F","source_center_LW_IN_F_QC",
            "source_center_raw_RH",
            "source_center_RH_implied_pct",
            "source_center_P_F","source_center_P_F_QC",
            "three_point_range","source_screen_classification",
            "science_repair_approved","forcing_or_original_writes")
SUMMARY_COLS=("group","source_records","matched_28_groups",
              "operator_44_flags","priority_context_HH",
              "scientific_release","AD400_authorised")
def require(cond,why):
    if not cond:raise ValueError(str(why))
def digest(p):
    p=Path(p)
    require(p.is_file() and not p.is_symlink(),"Protected input missing or symlink "+str(p))
    h=hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda:f.read(4<<20),b""):h.update(chunk)
    return h.hexdigest()
def rows(p):
    require(p.is_file() and not p.is_symlink(),"Missing original science TSV "+str(p))
    with p.open(encoding="utf-8",newline="") as f:
        return list(csv.DictReader(f,delimiter="\t"))
def num(s):
    try:
        x=float(str(s).strip())
        if not math.isfinite(x) or x<=-9990 or x>=9990:return None
        return x
    except (TypeError,ValueError):return None
def esat(t):
    return 6.112*math.exp(17.67*t/(t+243.5)) if t is not None and -65<t<70 else None
def physical_rh(t,vpd):
    es=esat(t)
    return 100*(1-vpd/es) if es is not None and vpd is not None else None
def valid_rh(rh):
    return rh is not None and 0<=rh<=100
def fullstamp(x):
    return dt.datetime.fromisoformat(x)
def tsv(path,columns,records):
    with path.open("x",encoding="utf-8",newline="") as f:
        w=csv.DictWriter(f,fieldnames=columns,delimiter="\t",extrasaction="raise")
        w.writeheader();w.writerows(records)
def selftest():
    require(len(FOCUS)==7 and len(SPIKES)==5 and len(VPDS)==2,"7 priorities")
    require(abs(esat(20)-23.369)<0.02,"VPD saturation hPa")
    require(physical_rh(13.61,22.071)<-40,"2013 recorded VPD impossible")
    require(valid_rh(0) and valid_rh(100) and not valid_rh(-1),"raw RH validity")
    require(num("-9999") is None and num("0") == 0,"missing data parsing")
    print("AU-GIN STAGE11 SELFTEST PASS | Stage10 91 HH, 5 spikes, 2 VPD QC1 RH physics; READ ONLY")
def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--self-test",action="store_true")
    p.add_argument("--out",type=Path)
    a=p.parse_args()
    if a.self_test:return selftest()
    out=a.out
    require(out is not None and out.parent.resolve()==HOME.resolve()
            and not out.exists() and not out.is_symlink(),
            "Output must be a NEW direct HOME directory")
    require(digest(ORIGINAL)==ORIGINAL_SHA,"Original TERN ZIP SHA256 changed")
    r=json.loads(RECEIPT.read_text(encoding="utf-8"))
    require(r.get("original_TERN_zip_SHA256")==ORIGINAL_SHA
            and r.get("original_28_event_groups_reconstructed")==28
            and r.get("original_44_flag_rows_reconstructed")==44
            and r.get("priority_source_context_HH")==91
            and r.get("priority_shadow_candidates")==5
            and r.get("two_VPD_QC1_implied_negative_RH_source_issues")==2
            and r.get("BIF_UTC_OFFSET")==8
            and r.get("source_science_release") is False
            and r.get("AD400_authorised") is False,
            "Actual Stage10 28/44/91/5/2 science receipt changed")
    context=rows(CONTEXT)
    shadows=rows(SHADOW)
    allgroups=rows(GROUPS)
    flags=rows(ORIGINAL_FLAGS)
    require(len(context)==91 and len(shadows)==5
            and len(allgroups)==28 and len(flags)==44,
            "Original Stage10 source output counts changed")
    priority={}
    for c in context:
        ident=c.get("focus_id")
        require(ident in FOCUS,"Unrecognized original source focus")
        require(c.get("source_local_AWST")==FOCUS[ident][0]
                and c.get("focus_variable")==FOCUS[ident][1],
                "Source focus variables/time changed")
        priority.setdefault(ident,[]).append(c)
    require(set(priority)==set(FOCUS),"Seven priority source contexts missing")
    for ident,items in priority.items():
        items.sort(key=lambda z:z["native_time"])
        require(len(items)==13 and
                sum(z["is_focus_half_hour"]=="True" for z in items)==1 and
                [int(z["relative_minutes"]) for z in items]==list(range(-180,181,30)),
                "Original 13 halfhours around "+ident+" no longer regular")
    shadows_by_id={x["candidate_id"]:x for x in shadows}
    require(len(shadows_by_id)==5 and set(shadows_by_id)==set(SPIKES),
            "Original five source spike decision groups changed")
    vpd_out=[]
    for ident in VPDS:
        items=priority[ident]
        c=next(x for x in items if x["is_focus_half_hour"]=="True")
        t=num(c["TA_F"]);v=num(c["VPD_F"])
        require(t is not None and v is not None and
                c["VPD_F_QC"] in ("1","1.0"),"Original VPD QC1 center lost")
        e=esat(t);rh=physical_rh(t,v)
        require(e is not None and rh is not None and rh<-1,
                "Original 2013 TA/VPD physical conflict changed")
        raw=num(c["RH_raw"]);valid=valid_rh(raw)
        from_raw=e*(1-raw/100) if valid else None
        neighboring=[]
        for x in items:
            tx=num(x["TA_F"]);vx=num(x["VPD_F"])
            neighboring.append(physical_rh(tx,vx))
        vpdq=sum(x["VPD_F_QC"] in ("1","1.0") for x in items)
        bad=sum(y is not None and y<-0.05 for y in neighboring)
        raw_count=sum(valid_rh(num(x["RH_raw"])) for x in items)
        taq=sum(x["TA_F_QC"] in ("0","0.0") for x in items)
        vpd_out.append({
          "focus_id":ident,
          "original_native_AWST":FOCUS[ident][0],
          "QC1_center_TA_F":t,"QC1_center_TA_F_QC":c["TA_F_QC"],
          "QC1_center_VPD_F":v,"QC1_center_VPD_F_QC":c["VPD_F_QC"],
          "QC1_center_VPD_ERA":c["VPD_ERA"],
          "source_raw_RH_at_center":raw,
          "source_raw_RH_is_0_to_100":valid,
          "saturation_vapor_pressure_hPa":round(e,5),
          "RH_implied_from_F_TA_VPD_percent":round(rh,4),
          "VPD_from_raw_RH_and_F_TA_hPa_DIAGNOSTIC_ONLY":
                 round(from_raw,5) if from_raw is not None else None,
          "F_VPD_minus_RH_constrained_DIAGNOSTIC_hPa":
                 round(v-from_raw,5) if from_raw is not None else None,
          "QC1_VPD_halfhours_within_3h":vpdq,
          "negative_implied_RH_halfhours_within_3h":bad,
          "RH_raw_valid_halfhours_within_3h":raw_count,
          "TA_F_QC0_halfhours_within_3h":taq,
          "classification":("QC1_VPD_PHYSICS_MISMATCH_RAW_RH_AVAILABLE_REVIEW"
                   if valid else "QC1_VPD_PHYSICS_MISMATCH_RAW_RH_UNAVAILABLE_HOLD"),
          "raw_RH_is_independent_truth":False,
          "scientific_repair_approved":False})
    spike_out=[]
    for ident in SPIKES:
        c=next(x for x in priority[ident] if x["is_focus_half_hour"]=="True")
        sh=shadows_by_id[ident]
        v=FOCUS[ident][1]
        rawmap={"PA":"PA_raw","WS":"WS_raw"}
        targetval=num(c[v+"_F"])
        prev=num(sh["preceding_F"]);nxt=num(sh["following_F"])
        require(targetval is not None and prev is not None and nxt is not None
                and abs(targetval-num(sh["original_F"]))<=1e-9,
                "Original Stage09/10 shadow source changed")
        raw=num(c[rawmap[v]]) if v in rawmap else None
        matching=(abs(raw-targetval)<1e-7) if raw is not None else None
        qc_pair=(sh["preceding_QC"] in ("0","0.0")
                 and sh["following_QC"] in ("0","0.0"))
        require(qc_pair==(ident!="PA_20120609_PREVIOUS"),
                "Actual PA left QC2 or four QC0 neighbor gates changed")
        ta=num(c["TA_F"]);vpd=num(c["VPD_F"])
        spike_out.append({
         "focus_id":ident,"original_native_AWST":FOCUS[ident][0],
         "variable":v,"original_prev_F":prev,
         "original_prev_QC":sh["preceding_QC"],
         "original_center_F":targetval,"original_center_QC":c[v+"_F_QC"],
         "original_next_F":nxt,"original_next_QC":sh["following_QC"],
         "source_original_RAW_same_variable_at_center":raw,
         "original_RAW_and_F_match_at_center":matching,
         "diagnostic_neighbour_mean_NOT_APPLIED":
              sh["shadow_neighbor_average_NOT_APPLIED"],
         "neighbor_both_original_QC0":qc_pair,
         "NOAA_Pearce_reference_for_prior_review_ONLY":
              sh["original_independent_Pearce_QC0_reference"],
         "source_center_TA_F":ta,"source_center_TA_F_QC":c["TA_F_QC"],
         "source_center_VPD_F":vpd,"source_center_VPD_F_QC":c["VPD_F_QC"],
         "source_center_PA_F":num(c["PA_F"]),
         "source_center_PA_F_QC":c["PA_F_QC"],
         "source_center_WS_F":num(c["WS_F"]),
         "source_center_WS_F_QC":c["WS_F_QC"],
         "source_center_SW_IN_F":num(c["SW_IN_F"]),
         "source_center_SW_IN_F_QC":c["SW_IN_F_QC"],
         "source_center_LW_IN_F":num(c["LW_IN_F"]),
         "source_center_LW_IN_F_QC":c["LW_IN_F_QC"],
         "source_center_raw_RH":num(c["RH_raw"]),
         "source_center_RH_implied_pct":physical_rh(ta,vpd),
         "source_center_P_F":num(c["P_F"]),
         "source_center_P_F_QC":c["P_F_QC"],
         "three_point_range":max(prev,targetval,nxt)-min(prev,targetval,nxt),
         "source_screen_classification":
             ("QC2_FLANK_AND_ORIGINAL_INSTRUMENT_REVIEW_HOLD"
              if not qc_pair else "TWO_QC0_FLANKS_NO_AUTOMATIC_REPAIR"),
         "science_repair_approved":False,"forcing_or_original_writes":False})
    report={"site":"AU-Gin","stage":"Stage11 seven-priority physical consistency and raw RH source",
       "original_zip_SHA256":ORIGINAL_SHA,
       "actual_Stage10_receipt_SHA256":digest(RECEIPT),
       "actual_Stage10_91HH_multivariate_context_SHA256":digest(CONTEXT),
       "actual_Stage10_28groups_SHA256":digest(GROUPS),
       "actual_Stage10_44flags_SHA256":digest(ORIGINAL_FLAGS),
       "BIF_site_UTC_OFFSET":8,
       "priority_single_sample_spike_source_reviews":len(spike_out),
       "VPD_QC1_physics_conflicts":len(vpd_out),
       "raw_RH_is_not_automatic_independent_truth":True,
       "manual_science_review_needed_even_for_QC0_pair":True,
       "2012_06_09_left_neighbor_QC2_hard_hold":True,
       "PA_from_original_F_kPa_not_mixed_with_MSL_pressure":True,
       "all_28_event_groups_remain_science_HOLD":True,
       "site_fails_strict_15_full_observed_year_criterion":True,
       "no_original_F_NOAA_DATM_surface_CIME_Slurm_writes":True,
       "any_science_correction_authorised":False,
       "AD400_authorised":False}
    out.mkdir(mode=0o700,exist_ok=False)
    tsv(out/"stage11_AU_Gin_2VPD_QC1_source_RH_physics.tsv",VPD_COLS,vpd_out)
    tsv(out/"stage11_AU_Gin_5spike_multivar_source_gate.tsv",SPIKE_COLS,spike_out)
    tsv(out/"stage11_AU_Gin_28group_HOLD_receipt.tsv",SUMMARY_COLS,[{
        "group":"ALL_28_SOURCE_ANOMALY_GROUPS","source_records":91,
        "matched_28_groups":len(allgroups),"operator_44_flags":len(flags),
        "priority_context_HH":len(context),"scientific_release":False,
        "AD400_authorised":False}])
    (out/"stage11_AU_Gin_7priority_source_science_HOLD.json").write_text(
         json.dumps(report,indent=2,ensure_ascii=False),encoding="utf-8")
    print("STAGE11 ORIGINAL TERN ZIP & ACTUAL STAGE10 SOURCE SHA256 VERIFIED")
    print("BIF_UTC_OFFSET",8,"GROUPS",len(allgroups),"FLAGS",len(flags),
          "PRIORITY_SOURCE_HH",len(context))
    for x in spike_out:
        print("SPIKE_SOURCE",x["focus_id"],"VALUE",x["original_center_F"],
              "QC",x["original_center_QC"],"RAW",x["source_original_RAW_same_variable_at_center"],
              "RAW_EQUALS_F",x["original_RAW_and_F_match_at_center"],
              "T",x["source_center_TA_F"],"VPD",x["source_center_VPD_F"],
              "WS",x["source_center_WS_F"],"PA",x["source_center_PA_F"],
              "SW_IN",x["source_center_SW_IN_F"],
              "RH_RAW",x["source_center_raw_RH"],
              "QC0_BOTH_NEIGHBORS",x["neighbor_both_original_QC0"],
              "GATE",x["source_screen_classification"])
    for x in vpd_out:
        print("VPD_PHYSICS",x["original_native_AWST"],
              "TA",x["QC1_center_TA_F"],"TA_QC",x["QC1_center_TA_F_QC"],
              "VPD",x["QC1_center_VPD_F"],"VPD_QC",x["QC1_center_VPD_F_QC"],
              "RH_RAW",x["source_raw_RH_at_center"],
              "RH_IMPLIED",x["RH_implied_from_F_TA_VPD_percent"],
              "VPD_FROM_RAW_RH",x["VPD_from_raw_RH_and_F_TA_hPa_DIAGNOSTIC_ONLY"],
              "QC1_3HR",x["QC1_VPD_halfhours_within_3h"],
              "NEG_RH_3HR",x["negative_implied_RH_halfhours_within_3h"],
              "GATE",x["classification"])
    print("STAGE11 READONLY SCIENCE TRIAGE PASS | 28 GROUPS HOLD; NO REPAIR/AD400")
    print("REPORT_DIR",out)
if __name__=="__main__":main()
