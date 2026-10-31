#!/usr/bin/env python3
"""Stage02N CH-Aws: audit original Stage34/38/42 repair ledgers and SHA provenance.

READ ONLY. Reads Stage02M and Stage02I saved diagnostic JSONs, then opens
only three exact, small revision CSVs and their adjacent JSON manifests in
the original CH-Aws forcing tree. Verifies original row_number/time/source
against the Stage02I exact match records and calculates ledger SHA256.
Shows original unfiltered ledger fields and manifest references for a human
science review. DOES NOT equate a ledger match or declared 'scientific_status'
with valid native tower RH/QC, independent ERA5, or an approved forcing.

Only --out-dir writes new evidence JSON and CSV in an existing EMPTY folder.
Never modify source, forcing, case, Git working tree or Slurm jobs.
"""
from __future__ import annotations
import argparse
import collections
import csv
import hashlib
import json
import re
from pathlib import Path

STAGE_M = "STAGE02M_CH_AWS_SEVEN_SOURCE_VPD_ERA_LEDGER_TRIAGE"
STAGE_I = "STAGE02I_CH_AWS_SOURCE_CSV_EVENT_SCHEMA_READONLY"
TARGET = {
    "stage34": {
        "ledger": "stage34_27_QC1_sensitivity_ledger.csv",
        "manifest": "stage34_manifest.json",
        "hash_key": "stage34_ledger_sha256",
    },
    "stage38": {
        "ledger": "stage38_21_QC1_ledger.csv",
        "manifest": "stage38_manifest.json",
        "hash_key": "ledger_sha256",
    },
    "stage42": {
        "ledger": "stage42_QC1_ledger.csv",
        "manifest": "stage42_manifest.json",
        "hash_key": "ledger_sha256",
    },
}
MAX_BYTES = 2_000_000
MAX_ROWS = 1200
FIELDS = (
    "event_id","event_time_DATM","ledger_stage","ledger_path","ledger_row_number",
    "ledger_time_column","ledger_original_time","ledger_time_matches_prior_scan",
    "ledger_sha256_matches_manifest","ledger_manifest_status",
    "ledger_QC_fields_unverified_json","ledger_full_record_json",
    "FLUXMET_START_VPD_F_raw","FLUXMET_START_VPD_ERA_raw",
    "native_tower_RH_QC_verified","ERA5_independent_provenance_verified",
    "time_basis_verified","scientific_release",
)


def validate_sources(m, i):
    if not isinstance(m, dict) or m.get("stage") != STAGE_M:
        raise ValueError("Require saved Stage02M result JSON")
    if m.get("read_only") is not True or m.get("science_release") is not False:
        raise ValueError("Stage02M source not in science-HOLD state")
    if m.get("independent_ERA5_source_verified") is not False or \
       m.get("unfilled_tower_RH_QC_verified") is not False:
        raise ValueError("Unexpected source-science approval state")
    ev=m.get("event_science_and_revision_ledgers")
    if not isinstance(ev, list) or len(ev)!=20:
        raise ValueError("Expected Stage02M twenty evaluated events")
    if not isinstance(i, dict) or i.get("stage") != STAGE_I:
        raise ValueError("Require saved Stage02I result JSON")
    if i.get("read_only") is not True or i.get("scientific_release") is not False:
        raise ValueError("Stage02I not in science-HOLD state")
    events=i.get("selected_ranked_events")
    if not isinstance(events,list) or len(events)!=20:
        raise ValueError("Stage02I must contain 20 selected events")
    clocks={e.get("event_id"):str(e.get("event_time_DATM")) for e in events}
    if len(clocks)!=20:
        raise ValueError("Stage02I selected events not unique")
    used=set()
    for entry in ev:
        eid=entry.get("event_id")
        if eid in used or clocks.get(eid)!=entry.get("time_DATM"):
            raise ValueError("Stage02M and I event identity or time mismatch")
        used.add(eid)
        if entry.get("decision")!="HOLD_NATIVE_TOWER_RH_ERA_AND_REPAIR_JUSTIFICATION":
            raise ValueError("Event science release unexpectedly changed")
    return ev


def pinned_files(i, root):
    root=root.resolve(strict=True)
    if root.name!="forcing" or root.parent.name!="CH-Aws":
        raise ValueError("Forcing root must be exact CH-Aws/forcing directory")
    csvs=i.get("candidate_csv_inspections",[])
    metas=i.get("candidate_json_manifests",[])
    if not isinstance(csvs,list) or not isinstance(metas,list):
        raise ValueError("Stage02I provenance inventory unavailable")
    result={}
    for stage, names in TARGET.items():
        ledger_entries=[x for x in csvs if Path(str(x.get("path",""))).name==names["ledger"]]
        manifest_entries=[x for x in metas if Path(str(x.get("path",""))).name==names["manifest"]]
        if len(ledger_entries)!=1 or len(manifest_entries)!=1:
            raise ValueError("Missing unique Stage02I pinned source files for "+stage)
        l=Path(ledger_entries[0]["path"])
        j=Path(manifest_entries[0]["path"])
        if l.parent!=j.parent:
            raise ValueError("Revision ledger and manifest differ in directory")
        for p in (l,j):
            if not p.is_absolute() or not p.is_file() or p.is_symlink():
                raise ValueError("Unexpected/unreadable source pin "+str(p))
            if not p.resolve(strict=True).is_relative_to(root):
                raise ValueError("Source is not within CH-Aws/forcing")
            if p.stat().st_size>MAX_BYTES:
                raise ValueError("Source exceeds small audit bounds")
        result[stage]={"ledger_path":l,"manifest_path":j,
                       "expected_rows_from_stage02i":ledger_entries[0].get("rows_read")}
    return result


def read_csv(path):
    with path.open("r",encoding="utf-8-sig",errors="replace",newline="") as handle:
        reader=csv.DictReader(handle)
        if not reader.fieldnames:
            raise ValueError("Ledger lacks header")
        headers=list(reader.fieldnames)
        records=[]
        for idx, row in enumerate(reader):
            if idx>=MAX_ROWS:
                raise ValueError("Unexpected oversized repair ledger")
            records.append({str(k):str(v) if v is not None else ""
                            for k,v in row.items() if k is not None})
    return headers,records


def sha256_file(path):
    h=hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            b=handle.read(256*1024)
            if not b:break
            h.update(b)
    return h.hexdigest()


def read_ledger(stage, pin):
    file=pin["ledger_path"]
    headers, rows=read_csv(file)
    manifest=json.loads(pin["manifest_path"].read_text(encoding="utf-8"))
    if not isinstance(manifest,dict):
        raise ValueError("Revision manifest is not an object")
    actual=sha256_file(file)
    name=TARGET[stage]["hash_key"]
    declared=manifest.get(name)
    # Some manifests may pin a different ledger serialization; do not
    # suppress a mismatch or turn it into an unearned approval.
    if not isinstance(declared,str) or not re.fullmatch(r"[a-fA-F0-9]{64}",declared):
        verification="NO_VALID_SHA256_DECLARED"
        match=False
    elif actual.lower()==declared.lower():
        verification="MATCH"
        match=True
    else:
        verification="MISMATCH_HOLD"
        match=False
    if pin.get("expected_rows_from_stage02i")!=len(rows):
        verification="ROW_COUNT_DIFFERS_FROM_STAGE02I_HOLD"
        match=False
    result={
        "stage":stage,
        "ledger_path":str(file),
        "manifest_path":str(pin["manifest_path"]),
        "ledger_csv_header":headers,
        "ledger_rows":len(rows),
        "sha256_actual":actual,"sha256_manifest":declared,
        "sha256_result":verification,"sha256_verified":match,
        "manifest_fields":manifest,
        "source_scientifically_approved":False,
        "source_tower_original_QC_verified":False,
        "ERA5_independent_provenance_verified":False,
    }
    return result,rows


def exact_time_matches(events, ledgers):
    bystage={stage:(summary,rows) for stage,(summary,rows) in ledgers.items()}
    result=[]
    out=[]
    holds=[]
    for event in events:
        eid=event["event_id"]
        exact=event.get("matched_revision_ledger_exact_time",[])
        near=event.get("matched_revision_ledger_context_only",[])
        src_era=event.get("source_FLUXMET_START_VPD_ERA_raw")
        src_f=event.get("source_FLUXMET_START_VPD_F_raw")
        for candidate in exact:
            stage=candidate.get("ledger_stage")
            if stage not in bystage:
                holds.append({"event_id":eid,"issue":"UNEXPECTED_STAGE", "value":stage})
                continue
            info, rows=bystage[stage]
            rown=candidate.get("row_number")
            if not isinstance(rown,int) or not 2<=rown<=len(rows)+1:
                holds.append({"event_id":eid,"stage":stage,"issue":"ROW_NUMBER_OUTSIDE_SOURCE"})
                continue
            row=rows[rown-2]
            col=candidate.get("source_timestamp_column")
            ts=str(candidate.get("original_time",""))
            observed=str(row.get(col,"")) if col else ""
            equal=(observed==ts and bool(observed))
            if candidate.get("offset_minutes")!=0 or not equal:
                holds.append({"event_id":eid,"stage":stage,
                              "issue":"PREVIOUS_TIME_OR_ROW_PROVENANCE_MISMATCH",
                              "saved":ts,"read":observed})
            qc_subset={
                k:v for k,v in row.items()
                if re.search(r"(QC|RH|VPD|ERA|SOURCE|METHOD|DECISION|HOLD|ORIGINAL|REFERENCE|TEMP|TA|PRESS)",k,re.I)
            }
            record={
                "event_id":eid,
                "event_time_DATM":event.get("time_DATM"),
                "ledger_stage":stage,
                "ledger_path":info["ledger_path"],
                "ledger_row_number":rown,
                "ledger_time_column":col,
                "ledger_original_time":observed,
                "ledger_time_matches_prior_scan":equal,
                "ledger_sha256_matches_manifest":info["sha256_verified"],
                "ledger_manifest_status":str(info["manifest_fields"].get("scientific_status","UNSPECIFIED")),
                "ledger_QC_fields_unverified":qc_subset,
                "ledger_full_record":row,
                "FLUXMET_START_VPD_F_raw":src_f,
                "FLUXMET_START_VPD_ERA_raw":src_era,
                "native_tower_RH_QC_verified":False,
                "ERA5_independent_provenance_verified":False,
                "time_basis_verified":False,
                "scientific_release":"HOLD",
            }
            result.append(record)
            out.append({
                "event_id":eid,
                "event_time_DATM":event.get("time_DATM"),
                "ledger_stage":stage,
                "ledger_path":info["ledger_path"],
                "ledger_row_number":rown,
                "ledger_time_column":col,
                "ledger_original_time":observed,
                "ledger_time_matches_prior_scan":equal,
                "ledger_sha256_matches_manifest":info["sha256_verified"],
                "ledger_manifest_status":record["ledger_manifest_status"],
                "ledger_QC_fields_unverified_json":json.dumps(qc_subset,ensure_ascii=False),
                "ledger_full_record_json":json.dumps(row,ensure_ascii=False),
                "FLUXMET_START_VPD_F_raw":src_f,
                "FLUXMET_START_VPD_ERA_raw":src_era,
                "native_tower_RH_QC_verified":False,
                "ERA5_independent_provenance_verified":False,
                "time_basis_verified":False,
                "scientific_release":"HOLD",
            })
        if not exact:
            holds.append({"event_id":eid,"issue":"NO_EXACT_LEDGER_MATCH"})
        if near:
            # Context is retained for science review but cannot become exact
            # evidence just because it lies +/-30-60 min from the event.
            pass
    return result,out,holds


def selftest():
    e=[{
        "event_id":"E001","time_DATM":"2007-07-22 07:30:00",
        "decision":"HOLD_NATIVE_TOWER_RH_ERA_AND_REPAIR_JUSTIFICATION",
        "source_FLUXMET_START_VPD_F_raw":"11.247",
        "source_FLUXMET_START_VPD_ERA_raw":"1.497",
        "matched_revision_ledger_exact_time":[{
            "ledger_stage":"stage34",
            "row_number":2,"source_timestamp_column":"time",
            "original_time":"2007-07-22 07:30:00","offset_minutes":0,
        }],
        "matched_revision_ledger_context_only":[],
    }]
    ledger=({
        "ledger_path":"/synthetic/stage34_27_QC1_sensitivity_ledger.csv",
        "sha256_verified":True,
        "manifest_fields":{"scientific_status":"HOLD"},
    },[{"time":"2007-07-22 07:30:00","qc_original":"1","era_rh":"UNVERIFIED"}])
    rows,formatted,holds=exact_time_matches(e,{"stage34":ledger})
    assert len(rows)==1 and len(formatted)==1 and not holds
    assert rows[0]["ledger_time_matches_prior_scan"] is True
    assert rows[0]["ledger_QC_fields_unverified"]["qc_original"]=="1"
    assert rows[0]["native_tower_RH_QC_verified"] is False
    assert len(TARGET)==3 and len(FIELDS)==len(set(FIELDS))
    m={"stage":STAGE_M,"read_only":True,"science_release":False,
       "independent_ERA5_source_verified":False,"unfilled_tower_RH_QC_verified":False,
       "event_science_and_revision_ledgers":[dict(e[0],event_id=f"E{k:03d}") for k in range(1,21)]}
    i={"stage":STAGE_I,"read_only":True,"scientific_release":False,
       "selected_ranked_events":[{"event_id":f"E{k:03d}",
           "event_time_DATM":"2007-07-22 07:30:00"} for k in range(1,21)]}
    assert len(validate_sources(m,i))==20
    print("STAGE02N SELF-TEST PASS: decoded M/I, exact row/clock QC HOLD, 3 ledger hash contracts; NO WRITES")


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--self-test",action="store_true")
    ap.add_argument("--stage02m",type=Path)
    ap.add_argument("--stage02i",type=Path)
    ap.add_argument("--forcing-root",type=Path,
        default=Path("/iridisfs/scratch/ly3n24/CLM_FATES/sites/MY_EC_SITE/CH-Aws/forcing"))
    ap.add_argument("--out-dir",type=Path)
    args=ap.parse_args()
    if args.self_test:
        selftest()
        return
    for f in (args.stage02m,args.stage02i):
        if f is None or not f.is_file():
            ap.error("Require saved Stage02M and Stage02I JSON files")
    if args.out_dir is None or not args.out_dir.is_dir() or any(args.out_dir.iterdir()):
        ap.error("--out-dir must be an existing EMPTY directory")
    m=json.loads(args.stage02m.read_text(encoding="utf-8"))
    i=json.loads(args.stage02i.read_text(encoding="utf-8"))
    events=validate_sources(m,i)
    pins=pinned_files(i,args.forcing_root)
    ledgers={stage:read_ledger(stage,pin) for stage,pin in pins.items()}
    details,rows,holds=exact_time_matches(events,ledgers)
    for stage,(summary,ledgerrows) in ledgers.items():
        print("LEDGER",stage,"ROW_COUNT",summary["ledger_rows"],
              "SHA_STATUS",summary["sha256_result"],
              "SCIENTIFIC_STATUS",summary["manifest_fields"].get("scientific_status","NA"),
              "COLUMNS",",".join(summary["ledger_csv_header"][:60]))
        for k in ("selection_rule","method","source_tag","reference_sha256",
                  "stage33_evidence_sha256","source_csv_sha256","limitations","dependency"):
            if k in summary["manifest_fields"]:
                print(" MANIFEST_FIELD",stage,k,str(summary["manifest_fields"][k])[:250])
    for row in details:
        print("EXACT_EVENT",row["event_id"],row["event_time_DATM"],
              "STAGE",row["ledger_stage"],"CSV_ROW",row["ledger_row_number"],
              "MATCH",row["ledger_time_matches_prior_scan"],
              "SHA_VERIFIED",row["ledger_sha256_matches_manifest"],
              "FIELDS",json.dumps(row["ledger_QC_fields_unverified"],ensure_ascii=False)[:1300])
    for h in holds[:40]:
        print("HOLD",json.dumps(h,ensure_ascii=False))
    sha_not_verified=[s for s,(v,_) in ledgers.items() if not v["sha256_verified"]]
    output={
        "stage":"STAGE02N_CH_AWS_ORIGINAL_REVISION_LEDGER_QC_PROVENANCE",
        "read_only":True,"science_release":False,
        "source_modified":False,"case_modified":False,"slurm_submitted":False,
        "stage02m":str(args.stage02m),"stage02i":str(args.stage02i),
        "original_ledger_provenance":[s for s,_ in ledgers.values()],
        "matched_exact_event_records":details,"reported_science_holds":holds,
        "ledger_sha_unverified_stages":sha_not_verified,
        "native_tower_RH_QC_verified":False,"ERA5_reference_verified":False,
        "source_time_basis_verified":False,
        "limitations":"Exact source row and ledger hash are provenance-only; source-native humidity/QC and real ERA remain unapproved",
    }
    jp=args.out_dir/"stage02n_CH_Aws_original_ledger_QC_provenance.json"
    cp=args.out_dir/"stage02n_CH_Aws_exact_20_event_ledger_records.csv"
    with jp.open("x",encoding="utf-8") as handle:
        json.dump(output,handle,indent=2,ensure_ascii=False);handle.write("\n")
    with cp.open("x",encoding="utf-8",newline="") as handle:
        writer=csv.DictWriter(handle,fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    print("EXACT_EVENT_RECORDS",len(details),"SOURCE_ROW_HOLDS",len(holds),
          "LEDGER_SHA_UNVERIFIED",",".join(sha_not_verified) if sha_not_verified else "NONE")
    print("REPORT",jp)
    print("CSV",cp)
    print("NO SCIENCE RELEASE, NO SOURCE/CASE/FATES/SLURM WRITES")


if __name__=="__main__":
    main()
