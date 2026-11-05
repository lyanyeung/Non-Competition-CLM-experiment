#!/usr/bin/env python3
"""AU-Gin Stage05: replay Stage04 actual 28 groups with original source QA.

Actual Stage03 PASS identified 18 TA QC0 jumps, 17 VPD QC0 jumps,
3 PA QC0 jumps, 2 WS QC0 jumps, 2 QC0 VPD upper-screen values and
2 QC1 VPD>Tetens saturation comparisons. This script verifies original
Stage03 JSON/TSV and exact 127MB TERN ZIP SHA, groups overlapping flagged
times and prints +/-6h original tower F/QC and same-product ERA context.

The FLUXNET *_ERA columns are SAME product lineage and are NOT independent
external validation. Source-local labels may not be UTC; no wind height,
pressure datum, timestep convention, NOAA/BoM station or independent
radiation sensor assumed. A QC0 step change may be real. No edits.
"""
from __future__ import annotations
import argparse,csv,datetime as dt,hashlib,io,json,math,re,zipfile
from collections import Counter,defaultdict
from pathlib import Path

HOME=Path.home()
ZIP=Path("/iridisfs/scratch/ly3n24/CLM_FATES/sites/MY_EC_SITE/AU-Gin/forcing/raw/TERN_FLUXNET_2011_2025/TERN_AU-Gin_FLUXNET_2011-2025_v1.3_r1.zip")
ZIP_SHA="acd78491b6f5f2c1374da2076d73a6c8b6ef430b256b78da3d300656943d6f14"
PREV_DIR=HOME/"ozflux_AU_Gin_stage03_20261104T164334Z"
STAGE04=HOME/"ozflux_AU_Gin_stage04_20261105T030539Z/stage04_AU_Gin_44_flag_events_external_evidence_HOLD.json"
PREV=PREV_DIR/"stage03_AU_Gin_QC0_transition_and_raw_channels_SCIENCE_HOLD.json"
EVENTS=PREV_DIR/"stage03_AU_Gin_original_source_physics_alarm_examples.tsv"
MEMBER="TERN_AU-Gin_FLUXNET_FLUXMET_HH_2011-2025_v1.3_r1.csv"
VARS=("TA","VPD","PA","WS","SW_IN","LW_IN","P")
RAWS=("PA","WS","P","RH","WD")
COUNTS={
 "VPD/QC0_TO_QC0_30MIN_JUMP/0":17,
 "TA/QC0_TO_QC0_30MIN_JUMP/0":18,
 "PA/QC0_TO_QC0_30MIN_JUMP/0":3,
 "VPD/VPD_GT_SATURATION_ES/1":2,
 "WS/QC0_TO_QC0_30MIN_JUMP/0":2,
 "VPD/ABOVE_SCREEN/0":2
}
CONTEXT_FIELDS=("event_groups","native_time","is_flagged_time",
      "source_met_context_NOT_independent_NOAA","TA_F","TA_F_QC","TA_ERA",
      "VPD_F","VPD_F_QC","VPD_ERA","VPD_derived_RH_pct",
      "PA","PA_F","PA_F_QC","PA_ERA",
      "WS","WS_F","WS_F_QC","WS_ERA",
      "P","P_F","P_F_QC","P_ERA",
      "SW_IN_F","SW_IN_F_QC","SW_IN_ERA",
      "LW_IN_F","LW_IN_F_QC","LW_IN_ERA","RH","WD")
EVENT_FIELDS=("group_id","first_flag_native","last_flag_native",
      "n_unique_flag_times","n_flag_categories",
      "n_flag_rows","first_context","last_context",
      "variables","categories","needs_external_evidence",
      "independent_source_verified","authorised_repair")
CENTER_FIELDS=("group_id","native_time","variable","flag_type","source_QC",
      "F_value","ERA_value","diagnostic_strength",
      "original_event_TA_F","original_event_TA_F_QC",
      "original_event_VPD_F","original_event_VPD_F_QC",
      "original_event_PA_F","original_event_PA_F_QC",
      "original_event_WS_F","original_event_WS_F_QC",
      "orig_PA","orig_WS","orig_P",
      "event_derived_RH_pct","NOAA_or_BoM_independently_verified",
      "repair_authorised")
def need(v,msg):
    if not v:raise ValueError(str(msg))
def sha(path):
    p=Path(path)
    need(p.is_file() and not p.is_symlink(),"Missing file/symlink "+str(p))
    h=hashlib.sha256()
    with p.open("rb") as f:
        for x in iter(lambda:f.read(4<<20),b""):h.update(x)
    return h.hexdigest()
def date(v):
    return dt.datetime.fromisoformat(str(v).strip())
def parseHH(v):
    v=str(v).strip()
    need(re.fullmatch(r"\d{12}",v) is not None,
         "Malformed original HH timestamp "+str(v))
    return dt.datetime.strptime(v,"%Y%m%d%H%M")
def num(v):
    try:
        x=float(str(v).strip())
        return x if math.isfinite(x) and x>-9990 else None
    except (ValueError,TypeError):return None
def rh(ta,vpd):
    # Source diagnostic only: do not infer independent humidity truth.
    if ta is None or vpd is None or ta<=-70 or ta>=75:return None
    es=6.112*math.exp(max(-50,min(30,17.67*ta/(ta+243.5))))
    if es<=0:return None
    return 100*(es-vpd)/es
def parse_events(path):
    data=[]
    with path.open("r",encoding="utf-8",newline="") as f:
        reader=csv.DictReader(f,delimiter="\t")
        required={"native_time","variable","value_F","QC_F",
                  "ERA_value","alarm","score"}
        need(required.issubset(reader.fieldnames or []),
             "Actual Stage03 event TSV schema changed")
        for row in reader:
            t=date(row["native_time"])
            need(t.year in range(2011,2026) and
                 row["variable"] in VARS,
                 "Unexpected event time/variable")
            key="/".join([row["variable"],row["alarm"],row["QC_F"]])
            need(key in COUNTS,"Unexpected original Stage03 event category "+key)
            data.append({"time":t,"key":key,"var":row["variable"],
               "alarm":row["alarm"],"qc":row["QC_F"],
               "val":num(row["value_F"]),"era":num(row["ERA_value"]),
               "score":num(row["score"])})
    need(len(data)==sum(COUNTS.values())==44,
         "Stage03 anomalies not exact 44 source flags")
    actual=Counter(x["key"] for x in data)
    need(actual==Counter(COUNTS),"Stage03 source anomaly category counts changed")
    # No duplicate exact category/time copies.
    need(len(set((x["time"],x["key"]) for x in data))==len(data),
         "Duplicate category/timestamp in original Stage03 list")
    return data
def clusters(events):
    sorted_times=sorted(set(x["time"] for x in events))
    groups=[]
    for t in sorted_times:
        if not groups or (t-groups[-1][-1])>dt.timedelta(hours=2):
            groups.append([t])
        else:groups[-1].append(t)
    return groups
def as_time(t):
    return t.strftime("%Y-%m-%d %H:%M:%S")
def write(path,cols,rows):
    with path.open("x",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=cols,delimiter="\t",
                         extrasaction="raise")
        w.writeheader();w.writerows(rows)
def selftest():
    need(sum(COUNTS.values())==44 and len(COUNTS)==6,"44/6")
    a=[{"time":date("2019-01-01 01:00:00")},
       {"time":date("2019-01-01 01:30:00")},
       {"time":date("2019-01-01 05:00:00")}]
    need(len(clusters(a))==2,"grouping 2h")
    need(abs(rh(25,12)-(100*(1-12/(6.112*math.exp(17.67*25/(25+243.5))))))<1e-7,
         "VPD and TA inferred RH")
    print("OZFLUX AU-GIN STAGE05 SELF-TEST PASS | 44 flags, grouped source context, no external station claims; READ ONLY")
def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--self-test",action="store_true")
    p.add_argument("--out",type=Path)
    a=p.parse_args()
    if a.self_test:return selftest()
    o=a.out
    need(o is not None and o.parent.resolve()==HOME.resolve()
         and not o.exists() and not o.is_symlink(),
         "Use new direct HOME report directory")
    need(sha(ZIP)==ZIP_SHA,"Original TERN source ZIP changed")
    prev=json.loads(PREV.read_text(encoding="utf-8"))
    need(prev.get("source_zip_sha256")==ZIP_SHA and
         prev.get("total_source_HH")==262992 and
         prev.get("original_QC0_2011_JAN_MAY_verified_zero") is True and
         prev.get("science_release") is False and
         prev.get("AD400_authorised") is False,
         "Actual Stage03 immutable source/HOLD receipt changed")
    need(prev.get("physical_alarm_counts")==COUNTS,
         "Stage03 actual physical alarm counts changed")
    old04=json.loads(STAGE04.read_text(encoding="utf-8"))
    need(old04.get("source_zip_SHA256")==ZIP_SHA and
         old04.get("stage03_original_report_SHA256")==sha(PREV) and
         old04.get("stage03_original_alarm_examples_SHA256")==sha(EVENTS) and
         old04.get("original_44_screen_flags")==44 and
         old04.get("unique_flagged_HH")==39 and
         old04.get("number_of_grouped_events")==28 and
         old04.get("source_context_halfhours_in_windows")==678 and
         old04.get("AD400_authorised") is False,
         "Actual operator Stage04 44/39/28/678 source receipt changed")
    rows=parse_events(EVENTS)
    grps=clusters(rows)
    need(len(grps)==28 and len(set(x["time"] for x in rows))==39,
         "Actual operator 28 groups / 39 source HH no longer reproducible")
    refs={}
    metadata=[]
    for i,group in enumerate(grps,1):
        label="AU_GIN_QC_EVENT_"+str(i).zfill(3)
        eventrows=[x for x in rows if x["time"] in set(group)]
        need(len(eventrows)>0,"Unmapped event group")
        w0=group[0]-dt.timedelta(hours=6)
        w1=group[-1]+dt.timedelta(hours=6)
        refs[label]={"first":group[0],"last":group[-1],"left":w0,"right":w1}
        metadata.append({"group_id":label,
           "first_flag_native":as_time(group[0]),
           "last_flag_native":as_time(group[-1]),
           "n_unique_flag_times":len(group),
           "n_flag_categories":len(set(x["key"] for x in eventrows)),
           "n_flag_rows":len(eventrows),
           "first_context":as_time(w0),"last_context":as_time(w1),
           "variables":";".join(sorted(set(x["var"] for x in eventrows))),
           "categories":";".join(sorted(set(x["key"] for x in eventrows))),
           "needs_external_evidence":True,
           "independent_source_verified":False,"authorised_repair":False})
    tagged={t:[] for t in sorted(set(x["time"] for x in rows))}
    for label,r in refs.items():
        for t in tagged:
            if r["first"]<=t<=r["last"]:tagged[t].append(label)
    selected={};start_end=None
    with zipfile.ZipFile(ZIP,"r") as z:
        need(z.namelist().count(MEMBER)==1,"Original source HH member unavailable")
        with z.open(MEMBER,"r") as f:
            reader=csv.DictReader(io.TextIOWrapper(f,encoding="utf-8-sig",newline=""))
            required={"TIMESTAMP_START","TIMESTAMP_END"}
            for v in VARS:required.update([v+"_F",v+"_F_QC",v+"_ERA"])
            need(required.issubset(reader.fieldnames or []),
                 "Missing actual source met columns")
            for line in reader:
                t=parseHH(line["TIMESTAMP_START"])
                if t not in selected and any(
                       r["left"]<=t<=r["right"] for r in refs.values()):
                    selected[t]=line
    need(set(tagged).issubset(selected),
         "One or more exact original event timestamps not found in source ZIP")
    need(len(selected)==678,
         "Actual Stage04 exact 678 unique +/-6h native context rows changed")
    contexts=[];center_rows=[]
    for t,line in sorted(selected.items()):
        tags=[label for label,r in refs.items()
              if r["left"]<=t<=r["right"]]
        vals={v:num(line[v+"_F"]) for v in VARS}
        context={"event_groups":";".join(tags),"native_time":as_time(t),
          "is_flagged_time":t in tagged,
          "source_met_context_NOT_independent_NOAA":True,
          "VPD_derived_RH_pct":rh(vals["TA"],vals["VPD"])}
        for v in VARS:
            context[v+"_F"]=line[v+"_F"]
            context[v+"_F_QC"]=line[v+"_F_QC"]
            context[v+"_ERA"]=line[v+"_ERA"]
        for v in RAWS:context[v]=line.get(v)
        contexts.append(context)
    for event in sorted(rows,key=lambda x:(x["time"],x["key"])):
        t=event["time"]
        line=selected[t]
        ta=num(line["TA_F"]);vpd=num(line["VPD_F"])
        center={
           "group_id":";".join(tagged[t]),
           "native_time":as_time(t),"variable":event["var"],
           "flag_type":event["alarm"],"source_QC":event["qc"],
           "F_value":event["val"],"ERA_value":event["era"],
           "diagnostic_strength":event["score"],
           "event_derived_RH_pct":rh(ta,vpd),
           "NOAA_or_BoM_independently_verified":False,"repair_authorised":False}
        for v in ("TA","VPD","PA","WS"):
            center["original_event_"+v+"_F"]=line[v+"_F"]
            center["original_event_"+v+"_F_QC"]=line[v+"_F_QC"]
        for v in ("PA","P","WS"):center["orig_"+v]=line.get(v)
        center_rows.append(center)
    # Highest external priority is simultaneous multi-variable or pressure/wind,
    # but no alarm is by itself approval to alter source.
    priority=sorted(metadata,key=lambda x:(
        -int(("PA/" in x["categories"]) or ("WS/" in x["categories"])),
        -x["n_flag_rows"],x["first_flag_native"]))
    report={"site":"AU-Gin",
      "source_zip_SHA256":ZIP_SHA,
      "stage03_original_report_SHA256":sha(PREV),
      "actual_stage04_report_SHA256":sha(STAGE04),
      "actual_stage04_28groups_39HH_678context_strict_verified":True,
      "stage03_original_alarm_examples_SHA256":sha(EVENTS),
      "source_F_and_ERA_same_FLUXNET_package":True,
      "original_44_screen_flags":44,
      "original_category_counts":COUNTS,
      "unique_flagged_HH":len(tagged),
      "number_of_grouped_events":len(grps),
      "source_context_halfhours_in_windows":len(contexts),
      "external_priority_event_groups":priority,
      "independent_NOAA_or_BoM_not_used_or_proven":True,
      "station_heights_pressure_datum_UTC_local_not_verified":True,
      "external_BoM_candidate":"GINGIN AERO (Bureau site 009178, WMO 95612)",
      "external_BoM_candidate_lat_lon":[-31.4628,115.8642],
      "original_AU_Gin_lat_lon":[-31.3764,115.7139],
      "external_BoM_historical_data_aligned_or_downloaded":False,
      "fourteen_plus_year_F_source_QC_does_not_equal_15_measured_years":True,
      "AUDIT_ORIGINALS_UNCHANGED":True,
      "source_science_release":False,"AD400_authorised":False,
      "no_originals_DATM_Surface_CIME_Slurm_modified":True}
    o.mkdir(mode=0o700,parents=False,exist_ok=False)
    write(o/"stage05_AU_Gin_44_flag_centres_original_F_ERA_raw.tsv",
          CENTER_FIELDS,center_rows)
    write(o/"stage05_AU_Gin_28group_priorities.tsv",
          EVENT_FIELDS,priority)
    write(o/"stage05_AU_Gin_6h_source_QC_ERA_context.tsv",
          CONTEXT_FIELDS,contexts)
    (o/"stage05_AU_Gin_28event_preBOM_science_HOLD.json").write_text(
       json.dumps(report,indent=2,ensure_ascii=False),encoding="utf-8")
    print("STAGE05 SOURCE ZIP SHA256 VERIFIED",ZIP_SHA)
    print("STAGE03 AND ACTUAL STAGE04 RECEIPT + EVENT-LIST SHA256 VERIFIED")
    print("ORIGINAL_ALARM_FLAGS",44,"UNIQUE_TIMESTAMPS",len(tagged),
          "GROUPED_EVENTS",len(grps),"SOURCE_CONTEXT_HH",len(contexts))
    for event in priority:
        print("EVENT_PRIORITY",event["group_id"],
              event["first_flag_native"],"to",event["last_flag_native"],
              "FLAGS",event["n_flag_rows"],"TIMES",event["n_unique_flag_times"],
              "VARS",event["variables"],"TYPES",event["categories"])
    for row in center_rows[:15]:
        print("FLAG_SOURCE",row["native_time"],row["variable"],
              row["flag_type"],"F",row["F_value"],"QC",row["source_QC"],
              "ERA",row["ERA_value"],"RH_IMPLIED",row["event_derived_RH_pct"])
    print("STAGE05 READONLY SOURCE FORENSICS PASS; NO SCIENCE APPROVAL/REPAIR/AD400")
    print("REPORT_DIR",o)
if __name__=="__main__":main()
