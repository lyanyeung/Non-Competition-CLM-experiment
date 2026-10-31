#!/usr/bin/env python3
"""ICOS Batch04 Stage02I — CH-Aws native/ERA candidate CSV schema and event rows.

Read-only forensic discovery. Reads the saved Stage02H JSON manifest; examines
CSV headers and scans for exact or +/- 60 min candidate timestamps around the
most severe QBOT-change events. Includes revision ledgers and merged multisource
candidate tables without treating them as verified tower observations.

No timezone conversion is inferred; time label/start/end semantics must be
reviewed. Rows are *potential source matches*, not scientific approvals.
Only writes a new JSON and CSV into an already-existing EMPTY output folder.
Does not change NetCDF, raw tower data, ERA, CIME, Git, or Slurm.
"""
from __future__ import annotations
import argparse
import collections
import csv
import datetime as dt
import io
import json
import re
from pathlib import Path

STAGE = "STAGE02H_CH_AWS_SOURCE_DISCOVERY_AND_EVENT_PRIORITISATION"
MAX_SOURCE_FILES = 80
MAX_SCAN_MB = 90
MAX_MATCH_ROWS_PER_CSV = 1200
MAX_SELECTED_COLS = 40
MAX_STRING = 300
OFFSETS = (-60, -30, 0, 30, 60)
SUMMARY_FIELDS = ("event_id", "event_time_DATM", "source_csv", "row_number",
                  "matched_time_column", "raw_time_value",
                  "matched_offset_minutes", "candidate_record_fields_json",
                  "source_status", "time_basis_status", "tower_QC_status",
                  "ERA5_status")


def parse_time(text):
    if text is None:
        return None
    s = str(text).strip().strip('"').strip("'")
    if not s or s.lower() in ("nan", "-9999", "none"):
        return None
    if re.fullmatch(r"\d{12}", s):
        try: return dt.datetime.strptime(s, "%Y%m%d%H%M")
        except ValueError: return None
    if re.fullmatch(r"\d{14}", s):
        try: return dt.datetime.strptime(s, "%Y%m%d%H%M%S")
        except ValueError: return None
    if re.fullmatch(r"\d{8}", s):
        # Date-only is NOT a half-hour timestamp.
        return None
    try:
        parsed = dt.datetime.fromisoformat(s.replace("Z", "+00:00"))
        if parsed.tzinfo is not None:
            # Never silently coerce timezone-aware and naive date-times.
            return None
        if not (1990 <= parsed.year <= 2035):
            return None
        return parsed
    except (TypeError, ValueError):
        return None


def is_time_column(name):
    norm = re.sub(r"[^a-z0-9]", "", str(name).lower())
    return (norm in {"timestamp", "timestampstart", "timestampend",
                     "datetime", "datetimeutc", "datetimelocal", "dateandtime",
                     "time", "timeutc", "timelocal", "isotime", "dateutc"}
            or norm.startswith("timestamp"))


def select_columns(headers):
    cols = []
    for col in headers:
        label = str(col).lower()
        if (is_time_column(col) or
            re.search(r"(^|[^a-z])(rh|vpd|qc|era|ta|temp|press|humidity|qbot|tbot|source|method|provenance|flag|qual|dewpoint)([^a-z]|$)",
                      label)):
            cols.append(col)
    return cols[:MAX_SELECTED_COLS]


def verify_input(data):
    if not isinstance(data, dict) or data.get("stage") != STAGE:
        raise ValueError("Expected Stage02H source and ranked-events JSON")
    if data.get("read_only") is not True or data.get("scientific_release") is not False:
        raise ValueError("Stage02H science remains on HOLD")
    m = data.get("source_manifest")
    if not isinstance(m, dict) or not isinstance(m.get("candidate_source_or_metadata_files"), list):
        raise ValueError("Stage02H source manifest incomplete")
    events = data.get("qbot_top_events")
    if not isinstance(events, list) or not events:
        raise ValueError("Stage02H has no ranked QBOT events")
    return m, events


def event_targets(events, limit):
    chosen = []
    by_dt = collections.defaultdict(list)
    seen = set()
    for item in events:
        time = parse_time(item.get("time"))
        year = item.get("year")
        if time is None or year != time.year:
            continue
        marker = (int(year), time)
        if marker in seen:
            continue
        seen.add(marker)
        eid = "E%03d" % (len(chosen) + 1)
        chosen.append({
            "event_id": eid, "event_time_DATM": str(time),
            "max_abs_delta_QBOT_gkg": item.get("qbot_abs_delta_gkg"),
            "max_abs_delta_vapor_hPa": item.get("vapour_pressure_abs_delta_hPa"),
            "candidate_cases": item.get("candidate_cases", ""),
            "candidate_file": item.get("candidate_file", ""),
            "source_verified": False,
        })
        for offset in OFFSETS:
            by_dt[time + dt.timedelta(minutes=offset)].append((eid, offset))
        if len(chosen) >= limit:
            break
    if not chosen:
        raise ValueError("No parseable Stage02H ranked event time")
    return chosen, by_dt


def safe_files(manifest, forcing_root):
    declared = Path(manifest["root"]).resolve()
    root = forcing_root.resolve()
    if root != declared:
        raise ValueError("Forcing root differs from source-pinned Stage02H manifest")
    if "CH-Aws" not in root.parts or not root.name == "forcing":
        raise ValueError("Refusing to scan a non-CH-Aws forcing root")
    if not root.is_dir():
        raise FileNotFoundError(root)
    result = []
    for item in manifest["candidate_source_or_metadata_files"]:
        rel = item.get("relative_path")
        if not isinstance(rel, str) or not rel:
            continue
        path = root / rel
        try:
            resolved = path.resolve(strict=True)
        except (OSError, RuntimeError):
            continue
        if not resolved.is_relative_to(root) or path.is_symlink() or not path.is_file():
            raise ValueError("Source path unsafe or not a normal file: " + str(path))
        if path.suffix.lower() not in (".csv", ".json"):
            continue
        if len(result) >= MAX_SOURCE_FILES:
            raise ValueError("Source candidate limit exceeded")
        result.append((path, item))
    return result


def scan_reader(reader, path_label, lookup, max_matches=MAX_MATCH_ROWS_PER_CSV):
    header = reader.fieldnames or []
    timecols = [h for h in header if is_time_column(h)]
    selected = select_columns(header)
    matched = []
    rows_read = 0
    dropped = 0
    for row in reader:
        rows_read += 1
        if not timecols:
            # No unambiguous HH time field, so do not infer row alignment.
            break
        for name in timecols:
            raw = row.get(name)
            match_time = parse_time(raw)
            if match_time is None:
                continue
            target_matches = lookup.get(match_time, [])
            if not target_matches:
                continue
            observed = {str(k): str(row.get(k, ""))[:MAX_STRING]
                        for k in selected if row.get(k) not in (None, "")}
            for eid, minutes in target_matches:
                if len(matched) >= max_matches:
                    dropped += 1
                    continue
                matched.append({
                    "event_id": eid,
                    "source_csv": path_label,
                    "row_number": rows_read + 1,  # header line is row 1
                    "matched_time_column": str(name),
                    "raw_time_value": str(raw)[:MAX_STRING],
                    "matched_offset_minutes": int(minutes),
                    "candidate_record_fields": observed,
                    "source_status": "CANDIDATE_RECORD_NOT_VERIFIED",
                    "time_basis_status": "UNVERIFIED_NATIVE_START_END_UTC_OR_LOCAL",
                    "tower_QC_status": "NOT_VERIFIED",
                    "ERA5_status": "NOT_VERIFIED",
                })
    return {
        "header_columns": [str(h) for h in header[:160]],
        "candidate_time_columns": [str(h) for h in timecols],
        "selected_source_fields": [str(h) for h in selected],
        "rows_read": rows_read,
        "matched_rows": matched,
        "matching_truncated": dropped > 0,
        "matching_rows_not_saved": dropped,
    }


def scan_csv(path, lookup, max_mb):
    result = {
        "path": str(path), "bytes": path.stat().st_size, "status": "NOT_READ",
    }
    if path.stat().st_size > max_mb * 1_000_000:
        result["status"] = "SKIP_OVER_MAX_MB"
        return result
    try:
        csv.field_size_limit(2_000_000)
        with path.open("r", encoding="utf-8-sig", errors="replace", newline="") as f:
            first = f.read(8192)
            f.seek(0)
            try: dialect = csv.Sniffer().sniff(first, delimiters=",;\t")
            except csv.Error: dialect = csv.excel
            reader = csv.DictReader(f, dialect=dialect)
            scan = scan_reader(reader, str(path), lookup)
        result.update(scan)
        result["status"] = "CSV_SCANNED"
        if not scan["candidate_time_columns"]:
            result["status"] = "NO_RECOGNISED_TIME_COLUMN"
    except Exception as exc:
        result["status"] = "CSV_READ_ERROR"
        result["error"] = type(exc).__name__ + ": " + str(exc)
    return result


def scan_json(path):
    record = {"path": str(path), "bytes": path.stat().st_size}
    if path.stat().st_size > 1_000_000:
        record["status"] = "SKIP_JSON_OVER_1MB"
        return record
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        record["status"] = "PARSED_METADATA"
        record["top_level_type"] = type(value).__name__
        if isinstance(value, dict):
            record["top_level_keys"] = list(value)[:90]
            result = {}
            for k, v in value.items():
                if (re.search(r"source|era|qc|rh|repair|stage|method|hold|time|version|status|input|sha", k, re.I)
                    and isinstance(v, (str, int, float, bool, type(None)))):
                    result[k] = str(v)[:200]
                if len(result) >= 35:
                    break
            record["candidate_metadata_values"] = result
    except Exception as exc:
        record["status"] = "JSON_READ_ERROR"
        record["error"] = type(exc).__name__ + ": " + str(exc)
    return record


def selftest():
    assert parse_time("200707220730") == dt.datetime(2007, 7, 22, 7, 30)
    assert parse_time("2007-07-22 07:30:00") == dt.datetime(2007, 7, 22, 7, 30)
    assert parse_time("2007-07-22T07:30:00Z") is None
    assert parse_time("20070722") is None
    events, lookup = event_targets([
        {"year": 2007, "time": "2007-07-22 07:30:00",
         "qbot_abs_delta_gkg": 8.6, "vapour_pressure_abs_delta_hPa": 11.05}
    ], 10)
    assert len(events) == 1
    fixture = "TIMESTAMP_START,TA_F,RH_F,RH_QC,ERA_RH\n200707220700,12,65,0,70\n200707220730,14,66,1,68\n200707220800,15,65,0,67\n"
    result = scan_reader(csv.DictReader(io.StringIO(fixture)), "synthetic.csv", lookup)
    assert result["rows_read"] == 3 and len(result["matched_rows"]) == 3
    assert any(x["matched_offset_minutes"] == 0 for x in result["matched_rows"])
    assert all(x["tower_QC_status"] == "NOT_VERIFIED" for x in result["matched_rows"])
    fake = {"stage": STAGE, "read_only": True, "scientific_release": False,
            "source_manifest": {"root": "/dummy/CH-Aws/forcing",
                                "candidate_source_or_metadata_files": []},
            "qbot_top_events": [{"year": 2007, "time": "2007-07-22 07:30:00"}]}
    verify_input(fake)
    print("STAGE02I SELF-TEST PASS: decoded Stage02H, UTC-safe timestamp parser, 5-HH event matching; NO WRITES")


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--self-test", action="store_true")
    p.add_argument("--stage02h", type=Path)
    p.add_argument("--forcing-root", type=Path,
                   default=Path("/iridisfs/scratch/ly3n24/CLM_FATES/sites/MY_EC_SITE/CH-Aws/forcing"))
    p.add_argument("--out-dir", type=Path)
    p.add_argument("--event-limit", type=int, default=20)
    p.add_argument("--max-csv-mb", type=int, default=MAX_SCAN_MB)
    args = p.parse_args()
    if args.self_test:
        selftest()
        return
    if not args.stage02h or not args.stage02h.is_file():
        p.error("Stage02H JSON missing")
    if not args.out_dir or not args.out_dir.is_dir() or any(args.out_dir.iterdir()):
        p.error("--out-dir must exist and be EMPTY")
    if not 1 <= args.event_limit <= 80 or not 1 <= args.max_csv_mb <= 120:
        p.error("Invalid bounded file scan limits")
    data = json.loads(args.stage02h.read_text(encoding="utf-8"))
    manifest, ranked = verify_input(data)
    chosen, lookup = event_targets(ranked, args.event_limit)
    paths = safe_files(manifest, args.forcing_root)
    csv_reports, json_reports, match_rows = [], [], []
    for path, item in paths:
        if path.suffix.lower() == ".csv":
            report = scan_csv(path, lookup, args.max_csv_mb)
            csv_reports.append({
                **{k: v for k, v in report.items() if k != "matched_rows"},
                "matched_row_count": len(report.get("matched_rows", [])),
            })
            for row in report.get("matched_rows", []):
                row["event_time_DATM"] = next(
                    x["event_time_DATM"] for x in chosen if x["event_id"] == row["event_id"])
                match_rows.append(row)
            print("CSV", path.relative_to(args.forcing_root),
                  "STATUS", report["status"],
                  "ROWS", report.get("rows_read", "NA"),
                  "TIME_COLUMNS", ",".join(report.get("candidate_time_columns", [])) or "NONE",
                  "MATCHES", len(report.get("matched_rows", [])))
        else:
            record = scan_json(path)
            json_reports.append(record)
            print("META", path.relative_to(args.forcing_root),
                  "STATUS", record["status"],
                  "KEYS", ",".join(record.get("top_level_keys", [])[:12]))
    summary = {
        "stage": "STAGE02I_CH_AWS_SOURCE_CSV_EVENT_SCHEMA_READONLY",
        "read_only": True, "scientific_release": False,
        "source_modified": False, "CIME_modified": False, "Slurm_submitted": False,
        "stage02h": str(args.stage02h),
        "selected_ranked_events": chosen,
        "candidate_csv_inspections": csv_reports,
        "candidate_json_manifests": json_reports,
        "candidate_matched_rows": match_rows,
        "interpretation": ("Matching raw strings to event times with +/-1h context is NOT "
                           "verified tower observation/ERA5 timing. Time start/end and UTC/local "
                           "must be independently established; no source quality decision."),
    }
    dest_json = args.out_dir / "stage02i_source_event_matches.json"
    dest_csv = args.out_dir / "stage02i_source_event_matches.csv"
    with dest_json.open("x", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
        f.write("\n")
    with dest_csv.open("x", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=SUMMARY_FIELDS)
        writer.writeheader()
        for item in match_rows:
            writer.writerow({
                "event_id": item["event_id"],
                "event_time_DATM": item["event_time_DATM"],
                "source_csv": item["source_csv"],
                "row_number": item["row_number"],
                "matched_time_column": item["matched_time_column"],
                "raw_time_value": item["raw_time_value"],
                "matched_offset_minutes": item["matched_offset_minutes"],
                "candidate_record_fields_json": json.dumps(item["candidate_record_fields"]),
                "source_status": item["source_status"],
                "time_basis_status": item["time_basis_status"],
                "tower_QC_status": item["tower_QC_status"],
                "ERA5_status": item["ERA5_status"],
            })
    print("CANDIDATE_CSV_FILES", len(csv_reports),
          "CANDIDATE_METADATA_JSON", len(json_reports),
          "MATCHED_CSV_ROWS_UNVERIFIED", len(match_rows))
    print("JSON", dest_json)
    print("CSV", dest_csv)
    print("ALL TOWER/ERA/SLURM SCIENCE GATES HOLD; NO SOURCE MODIFICATIONS")


if __name__ == "__main__":
    main()
