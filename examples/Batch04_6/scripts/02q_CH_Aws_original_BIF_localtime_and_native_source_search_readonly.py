#!/usr/bin/env python3
"""ICOS Batch04 Stage02Q — CH-Aws origin metadata / time-basis provenance.

READ ONLY. Stage02P found NO independently identifiable unfilled tower RH/QC
product under the inspected CH-Aws site tree. Stage02Q reads ONLY the site
BIF/BIFVARINFO CSV metadata and historical Stage21/25 local-standard-time
revision ledgers, and makes a BOUNDED filename-only search of optional extra
roots. It checks whether ledger timestamps coincide with 20 Stage02O
high-disagreement DATM timestamps under separate 0/+/-60 and +/-30 minute
hypotheses. It does not assert UTC, tower-QC or ERA truth.

The optional external search is explicitly filename/path limited; a file
not found is NOT proof of nonexistence. No source extraction, full FLUXMET
scan, model/NC/CIME/Slurm/Git writes. Only an EMPTY --out-dir receives
new JSON+CSV.
"""
from __future__ import annotations
import argparse
import collections
import csv
import datetime as dt
import json
import io
import os
import re
from pathlib import Path

STAGE_P="STAGE02P_CH_AWS_NATIVE_TOWER_SOURCE_AVAILABILITY_DISCOVERY"
STAGE_O="STAGE02O_CH_AWS_REPAIR_EVENT_SCIENCE_TRIAGE_READONLY"
SOURCE_FILES={
    "BIF": "EUF_CH-Aws_FLUXNET_BIF_2006-2024_v1.3_r2.csv",
    "BIFVARINFO_HH": "EUF_CH-Aws_FLUXNET_BIFVARINFO_HH_2006-2024_v1.3_r2.csv",
    "STAGE21": "CH-Aws_stage21_revision_ledger.csv",
    "STAGE25": "CH-Aws_stage25_revision_ledger.csv",
}
OFFSETS=(-60,-30,0,30,60)
METADATA_KEYWORDS=("rh","vpd","ta","humidity","sensor","instrument",
                   "pressure","timezone","time_zone","utc","qc","source",
                   "height","latitude","longitude","elev","gapfill")
MAX_META_FILE=2_000_000
MAX_LEDGER_ROWS=25000
MAX_METADATA_SCAN_ROWS=100000
MAX_METADATA_EXAMPLES=80
MAX_ROW_MATCHES=240
MAX_SEARCH_FILES=15000
MAX_SEARCH_DEPTH=3
MAX_FILENAME_HITS=150
CSV_FIELDS=("event_id","DATM_event_time","ledger","source_path",
            "source_csv_row_number","ledger_time_column","ledger_original_time",
            "raw_ledger_time_minus_DATM_minutes",
            "time_hypothesis_only","original_row_fields_json",
            "source_RH_QC_verified","source_timezone_verified",
            "ERA5_independent_verified","scientific_release")


def parse_timestamp(raw):
    if raw is None: return None
    s=str(raw).strip()
    for pattern in ("%Y-%m-%d %H:%M:%S","%Y-%m-%d %H:%M",
                    "%Y%m%d%H%M","%Y%m%d%H%M%S"):
        try:return dt.datetime.strptime(s,pattern)
        except ValueError:pass
    try:
        t=dt.datetime.fromisoformat(s)
        if t.tzinfo is None and t.second==0 and t.microsecond==0:
            return t
    except ValueError:
        pass
    return None


def validate(p,o):
    if p.get("stage")!=STAGE_P or p.get("read_only") is not True or \
       p.get("science_release") is not False:
        raise ValueError("Stage02P JSON is not the original read-only source inventory")
    if o.get("stage")!=STAGE_O or o.get("read_only") is not True or \
       o.get("science_release") is not False:
        raise ValueError("Stage02O JSON not the source-pinned unresolved events")
    manifest=p.get("source_manifest",{})
    if not isinstance(manifest.get("candidate_artifacts"),list) or \
       manifest.get("truncated") is not False:
        raise ValueError("Stage02P inventory missing or truncated")
    if manifest.get("classes",{}).get("POSSIBLE_TOWER_OR_SOURCE_PRODUCT_UNVERIFIED",0):
        raise ValueError("Stage02P already identified potential native source: review separately")
    events=o.get("events_ranked")
    if not isinstance(events,list) or len(events)!=20 or \
       o.get("summary",{}).get("native_tower_RH_verified_events")!=0:
        raise ValueError("Stage02O 20-event, native-RH-HOLD population missing")
    seen=set()
    anchors=[]
    for x in events:
        eid=x.get("event_id")
        t=parse_timestamp(x.get("DATM_time"))
        if not eid or eid in seen or t is None or x.get("scientific_release")!="HOLD":
            raise ValueError("Invalid event/timestamp or unexpected science approval")
        seen.add(eid)
        anchors.append({"event_id":eid,"DATM_time":str(t),"datetime":t})
    return manifest,anchors


def pinned_paths(manifest):
    root=Path(manifest.get("site_root","")).resolve(strict=True)
    if root.name!="CH-Aws" or root.parent.name!="MY_EC_SITE":
        raise ValueError("Unapproved site-scoped source root")
    artifacts=manifest["candidate_artifacts"]
    located={}
    for label,basename in SOURCE_FILES.items():
        match=[Path(r.get("path","")) for r in artifacts
               if Path(r.get("path","")).name==basename]
        if len(match)!=1:raise ValueError("Missing/duplicate Stage02P source "+label)
        path=match[0]
        if path.is_symlink() or not path.is_file() or \
           not path.resolve(strict=True).is_relative_to(root) or \
           path.stat().st_size>MAX_META_FILE:
            raise ValueError("Source pin safety violation "+str(path))
        located[label]=path
    return root,located


def read_csv(path):
    """Small, bounded original Stage21/25 revision ledgers ONLY."""
    with path.open("r",newline="",encoding="utf-8-sig",errors="replace") as f:
        reader=csv.DictReader(f)
        headers=reader.fieldnames
        if not headers:
            raise ValueError("No Stage21/25 ledger CSV header")
        out=[]
        for i,row in enumerate(reader):
            if i>=MAX_LEDGER_ROWS:
                raise ValueError("Stage21/25 ledger unexpectedly exceeds 25000 rows")
            if None in row:
                raise ValueError("Malformed ledger CSV row/extra columns in "+str(path))
            out.append({str(k):str(v) if v is not None else "" for k,v in row.items()})
    return list(headers),out


# Exact variable tokens avoid accidentally treating 'data', 'metadata' or 'station'
# as TA/RH evidence. Grouped deterministic examples retain late rows for RH,
# VPD, time/QC and instrument provenance even in a 5000+ row BIF file.
_META_GROUP_RE = (
    ("RH", re.compile(r"(?i)(?<![A-Za-z0-9])(?:RH(?:_[A-Za-z0-9]+)*|RELATIVE[_ ]?HUMIDITY|HUMIDITY)(?![A-Za-z0-9])")),
    ("VPD", re.compile(r"(?i)(?<![A-Za-z0-9])VPD(?:_[A-Za-z0-9]+)*(?![A-Za-z0-9])")),
    ("TIME", re.compile(r"(?i)(?:TIMESTAMP|TIME[_ -]?ZONE|UTC[+-]?\d*|LOCAL[_ -]?TIME|TIME[_ -]?OFFSET)")),
    ("QC", re.compile(r"(?i)(?:QC(?:[_ -]|$)|QUALITY[_ -]?(?:CONTROL|FLAG)|GAP[_ -]?FILL|MDS)")),
    ("INSTRUMENT", re.compile(r"(?i)(?:SENSOR|INSTRUMENT|MEASUREMENT[_ -]?HEIGHT|TOWER|LOGGER|SOURCE)")),
    ("TA_PA", re.compile(r"(?i)(?<![A-Za-z0-9])(?:TA|PA|PRESSURE|TEMPERATURE)(?:_[A-Za-z0-9]+)*(?![A-Za-z0-9])")),
    ("OTHER", re.compile(r"(?i)(?:ELEVATION|ALTITUDE|LATITUDE|LONGITUDE|REANALYSIS|ERA5|ERA5-LAND)")),
)


def scan_metadata_reader(reader):
    """Stream BIF/BIFVARINFO without a 5000-row ceiling or full-file materialization.

    The source file is already size-bounded at 2 MB by pinned_paths. Full row
    counts and per-theme relevant counts are retained, while only <=80 examples
    are kept in memory for source/QC provenance inspection.
    """
    headers=reader.fieldnames
    if not headers:
        raise ValueError("Original BIF metadata has no CSV header")
    groups={name:[] for name,_ in _META_GROUP_RE}
    counts=collections.Counter()
    total=0
    relevant=0
    for idx,row in enumerate(reader,2):
        total+=1
        if total>MAX_METADATA_SCAN_ROWS:
            raise ValueError("Original BIF metadata exceeds bounded 100000 rows")
        if None in row:
            raise ValueError("Malformed original BIF metadata CSV row")
        r={str(k):str(v) if v is not None else "" for k,v in row.items()}
        evidence=" ".join(r.values())
        matched=next((name for name,regex in _META_GROUP_RE
                      if regex.search(evidence)), None)
        if matched is not None:
            relevant+=1
            counts[matched]+=1
            # Per-topic slots prevent RH/VPD rows late in a long BIF file
            # from being hidden by the earliest generic metadata entries.
            if len(groups[matched])<10:
                groups[matched].append({"row":idx,"fields":r,"matched_topic":matched})
    selected=sorted(
        (sample for entries in groups.values() for sample in entries),
        key=lambda x:x["row"]
    )[:MAX_METADATA_EXAMPLES]
    return {
        "headers":list(headers),"rows_total":total,
        "relevant_rows_total":relevant,
        "relevant_rows_examples":selected,
        "relevant_topic_counts":dict(counts),
        "example_limit":MAX_METADATA_EXAMPLES,
        "metadata_scan_complete":True,
        "metadata_sampling":"first <=10 rows per RH/VPD/TIME/QC/INSTRUMENT/TA_PA/OTHER topic, <=80 total",
    }


def describe_metadata(label,path):
    # Original BIF files may legitimately contain >5000 rows despite being
    # only 75–250 KB. Scan each CSV record without retaining all rows.
    with path.open("r",newline="",encoding="utf-8-sig",errors="replace") as f:
        result=scan_metadata_reader(csv.DictReader(f))
    return {
        "path":str(path),
        "source_kind":"FLUXNET_DISTRIBUTED_PRODUCT_METADATA_NOT_NATIVE_QC",
        **result,
        "metadata_QC_semantics_validated":False,
        "source_clock_validated":False,
    }


def match_legacy(label,path,anchors):
    headers,rows=read_csv(path)
    clock="time_local_standard_UTCplus1"
    if clock not in headers:
        raise ValueError(label+" expected explicitly named local-standard-time field missing")
    target={}
    for item in anchors:
        for off in OFFSETS:
            target.setdefault(item["datetime"]+dt.timedelta(minutes=off),[]).append((item,off))
    found=[]
    for rowno,r in enumerate(rows,2):
        t=parse_timestamp(r.get(clock))
        if t is None:continue
        for anchor,offset in target.get(t,[]):
            if len(found)>=MAX_ROW_MATCHES:
                raise ValueError("Too many ledger candidate matches; stop rather than silently truncate")
            found.append({
                "event_id":anchor["event_id"],"DATM_event_time":anchor["DATM_time"],
                "ledger":label,"source_path":str(path),
                "source_csv_row_number":rowno,"ledger_time_column":clock,
                "ledger_original_time":str(t),
                "raw_ledger_time_minus_DATM_minutes":offset,
                "time_hypothesis_only":"NO_UTC_LOCAL_CONVERSION_ASSUMED",
                "original_row_fields_json":json.dumps(r,ensure_ascii=False),
                "source_RH_QC_verified":False,"source_timezone_verified":False,
                "ERA5_independent_verified":False,"scientific_release":"HOLD",
            })
    byoff=collections.Counter(r["raw_ledger_time_minus_DATM_minutes"] for r in found)
    return {"path":str(path),"ledger_clock_column":clock,
            "original_rows":len(rows),"header_columns":headers,
            "event_context_candidate_matches":len(found),
            "offset_distribution_minutes":dict(sorted(byoff.items())),
            "time_basis_approved":False,
            "note":"Literal label UTCplus1 in source column is metadata, not proof of DATM conversion"}, found


def external_filename_scan(roots,site_root):
    checked=[]
    hits=[]
    visited=0
    truncated=False
    accepted_ext=(".csv",".csv.gz",".nc",".nc4",".zip",".gz",
                  ".json",".dat",".txt",".parquet",".xlsx")
    names=re.compile(r"(?i)(?:ch[-_]?aws|chaws|alpine[_-]?weissenstein|weissenstein)")
    for src in roots:
        p=Path(src).expanduser()
        if not p.is_dir():
            checked.append({"root":str(p),"status":"NOT_A_DIRECTORY"})
            continue
        real=p.resolve(strict=True)
        if real==site_root or real.is_relative_to(site_root):
            checked.append({"root":str(real),"status":"SKIPPED_ALREADY_INSPECTED_STAGE02P"})
            continue
        checked.append({"root":str(real),"status":"BOUNDED_FILENAME_ONLY"})
        base_depth=len(real.parts)
        for here,dirs,files in os.walk(real,topdown=True,followlinks=False):
            depth=len(Path(here).parts)-base_depth
            dirs[:]=[x for x in sorted(dirs)
                     if x not in (".git","__pycache__",".cache","node_modules","logs","archive","run")
                     and not (Path(here)/x).is_symlink()] if depth<MAX_SEARCH_DEPTH else []
            for name in sorted(files):
                visited+=1
                if visited>MAX_SEARCH_FILES:
                    truncated=True
                    break
                if len(hits)>=MAX_FILENAME_HITS:
                    truncated=True
                    break
                f=Path(here)/name
                if f.is_symlink() or not name.lower().endswith(accepted_ext):
                    continue
                if not names.search(name) and not names.search(str(f.parent)):
                    continue
                if not f.is_file():continue
                resolved=f.resolve(strict=True)
                if resolved.is_relative_to(site_root):
                    continue
                hits.append({"path":str(f),"bytes":f.stat().st_size,
                             "candidate_only":True,
                             "native_sensor_QC_verified":False})
            if truncated:break
        if truncated:break
    return {"roots":checked,"filenames_visited":visited,
            "search_truncated":truncated,
            "candidate_paths":hits,
            "limitations":"filename keyword/depth/visit bounded; no candidate implies neither absence nor validity"}


def self_test():
    p={"stage":STAGE_P,"read_only":True,"science_release":False,
       "source_manifest":{"site_root":"/fake/MY_EC_SITE/CH-Aws",
         "truncated":False,"candidate_artifacts":[],"classes":{}}}
    o={"stage":STAGE_O,"read_only":True,"science_release":False,
       "summary":{"native_tower_RH_verified_events":0},
       "events_ranked":[{"event_id":f"E{i:03d}",
         "DATM_time":f"2007-07-22 {i%24:02d}:00:00","scientific_release":"HOLD"}
        for i in range(1,21)]}
    manifest,anchors=validate(p,o)
    assert len(anchors)==20 and not manifest["classes"]
    assert parse_timestamp("2007-07-22 07:30:00")==dt.datetime(2007,7,22,7,30)
    assert parse_timestamp("200707220730")==dt.datetime(2007,7,22,7,30)
    assert parse_timestamp("bad") is None
    # Regression for the real BIF failure: source metadata can legitimately
    # exceed 5000 CSV rows; late humidity provenance must remain discoverable.
    content="VARIABLE,DESCRIPTION\n"+("GENERIC,ordinary note\n"*6001)+\
        "RH,relative humidity sensor metadata\n"+\
        "VPD_F,processed gapfill QC metadata\n"
    sample=scan_metadata_reader(csv.DictReader(io.StringIO(content)))
    assert sample["rows_total"]==6003
    assert sample["metadata_scan_complete"] is True
    assert sample["relevant_topic_counts"].get("RH",0)>=1
    assert sample["relevant_topic_counts"].get("VPD",0)>=1
    assert any(x["row"]>5000 for x in sample["relevant_rows_examples"])
    print("STAGE02Q SELF-TEST PASS: 6003-row BIF streaming, late RH/VPD samples, 20 source HOLD events; NO WRITES")


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--self-test",action="store_true")
    ap.add_argument("--stage02p",type=Path)
    ap.add_argument("--stage02o",type=Path)
    ap.add_argument("--extra-root",action="append",default=[],type=Path,
                    help="Optional small-depth filename-only search root; may repeat")
    ap.add_argument("--out-dir",type=Path)
    args=ap.parse_args()
    if args.self_test:self_test();return
    if any(p is None or not p.is_file() for p in (args.stage02p,args.stage02o)):
        ap.error("Existing Stage02P and Stage02O report JSON required")
    if args.out_dir is None or not args.out_dir.is_dir() or any(args.out_dir.iterdir()):
        ap.error("--out-dir must exist and be EMPTY")
    p=json.loads(args.stage02p.read_text(encoding="utf-8"))
    o=json.loads(args.stage02o.read_text(encoding="utf-8"))
    manifest,anchors=validate(p,o)
    site_root,files=pinned_paths(manifest)
    meta={label:describe_metadata(label,files[label]) for label in ("BIF","BIFVARINFO_HH")}
    ledgers={}
    matches=[]
    for label in ("STAGE21","STAGE25"):
        info,rows=match_legacy(label,files[label],anchors)
        ledgers[label]=info
        matches.extend(rows)
    external=external_filename_scan(args.extra_root,site_root)
    for label,info in meta.items():
        print("METADATA",label,"ROWS",info["rows_total"],
              "MATCHING_KEYWORD_ROWS",info["relevant_rows_total"],
              "TOPICS",json.dumps(info["relevant_topic_counts"],sort_keys=True),
              "COMPLETE",info["metadata_scan_complete"],
              "HEADERS",",".join(info["headers"][:25]))
        # Surface RH/VPD, QC and time metadata even when they appear late
        # in a long BIF/BIFVARINFO file; do not rely on file-order first 12.
        for topic in ("RH","VPD","TIME","QC","INSTRUMENT","TA_PA","OTHER"):
            samples=[x for x in info["relevant_rows_examples"]
                     if x["matched_topic"]==topic][:2]
            for example in samples:
                print(" META_EXCERPT",label,"TOPIC",topic,"ROW",example["row"],
                      "VALUES",json.dumps(example["fields"],ensure_ascii=False)[:900])
    for label,info in ledgers.items():
        print("LEDGER",label,"ROWS",info["original_rows"],
              "TIME_COLUMN",info["ledger_clock_column"],
              "EVENT_CONTEXT_MATCHES",info["event_context_candidate_matches"],
              "OFFSETS",json.dumps(info["offset_distribution_minutes"],sort_keys=True))
    for x in matches[:25]:
        print(" TIME_CANDIDATE",x["event_id"],x["ledger"],
              "SOURCE_TIME",x["ledger_original_time"],
              "DIFF_MIN",x["raw_ledger_time_minus_DATM_minutes"])
    print("EXTERNAL_FILENAME_SEARCH",json.dumps({
        "filenames_visited":external["filenames_visited"],
        "candidate_paths":len(external["candidate_paths"]),
        "search_truncated":external["search_truncated"]},sort_keys=True))
    for x in external["candidate_paths"][:35]:
        print(" EXTRA_POSSIBLE_SOURCE",x["path"],"BYTES",x["bytes"])
    report={
        "stage":"STAGE02Q_CH_AWS_TIME_AND_NATIVE_SOURCE_PROVENANCE_READONLY",
        "read_only":True,"science_release":False,
        "site_root":str(site_root),
        "source_stage02p":str(args.stage02p),"source_stage02o":str(args.stage02o),
        "original_distributed_metadata":meta,
        "stage21_25_original_local_standard_time_ledgers":ledgers,
        "hypothesis_only_event_matches":matches,
        "external_filename_candidates":external,
        "native_unfilled_tower_RH_QC_verified":False,
        "DATM_FLUXMET_UTC_basis_verified":False,
        "ERA5_grid_site_altitude_pressure_validated":False,
        "releases":[],"slurm_submitted":False,
        "critical_limitations":"No automatic 1-hour time conversion; evidence is raw local-standard label matches only. Metadata, filename and MDS VPD do not validate original tower observations.",
    }
    jpath=args.out_dir/"stage02q_CH_Aws_clock_and_source_provenance.json"
    cpath=args.out_dir/"stage02q_CH_Aws_stage21_25_time_hypotheses.csv"
    with jpath.open("x",encoding="utf-8") as f:json.dump(report,f,indent=2,ensure_ascii=False);f.write("\n")
    with cpath.open("x",encoding="utf-8",newline="") as f:
        writer=csv.DictWriter(f,fieldnames=CSV_FIELDS);writer.writeheader();writer.writerows(matches)
    print("REPORT",jpath)
    print("CSV",cpath)
    print("SCIENCE_HOLD: NOT NATIVE TOWER RH QC, NOT CLOCK APPROVAL, NOT ERA VALIDATION; NO SOURCE/SLURM WRITES")


if __name__=="__main__":
    main()
