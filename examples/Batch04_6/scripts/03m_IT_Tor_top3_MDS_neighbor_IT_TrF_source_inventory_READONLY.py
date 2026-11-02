#!/usr/bin/env python3
"""Batch04 Stage03M: IT-Tor severe MDS cold episodes + independent 2025 evidence INVENTORY.

Read ONLY completed Stage03L private priority reports. Inspect shallow,
explicit IT-TrF/Torgnon-LD station package folders for possibly available
2025 data without opening any meteorological values, re-running earlier QC,
downloading from ICOS, or replacing source/model forcing.

IT-TrF is a DISTINCT larch-forest station, not IT-Tor grassland. A station
dataset with measured QC0 and verified local/UTC clock can be useful as
nearby evidence, but is not tower ground truth; ERA-filled QC2 is NOT
independent observations. Stage03M does not compare timestamps or science
values until a future explicitly documented measurement/clock gate.
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
from pathlib import Path
from datetime import datetime, timedelta

STAGE="STAGE03L_IT_TOR_RANK_EXISTING_QC1_MDS_ERA_DIFFERENCE_EPISODES"
START=("2025-11-15 17:00:00","2025-11-13 17:30:00","2025-11-13 14:30:00")
HOURS=(125,28,3)
GT10=(67,28,3)
GT5=(107,28,3)
SITE_ROOT=Path("/iridisfs/scratch/ly3n24/CLM_FATES/sites/MY_EC_SITE")
SEARCH_SUBDIRS=("IT-TrF/forcing/packages","IT-TrF/forcing",
                "IT-TrF","IT-Trf/forcing/packages","IT-Trf",
                "IT-TrF/forcing/raw")
CANDIDATE_NAMES=("it-trf","it_trf","torgnon-ld","torgnon_ld")
EXTS=(".zip",".csv",".nc",".nc4")
LIMIT=2000
OFFICIAL="https://meta.icos-cp.eu/objects/EUCf30NjOFzu2N1by918KJPF"

def ck(cond,msg):
    if not cond:raise ValueError(msg)

def sha(path):
    h=hashlib.sha256()
    with path.open("rb") as f:
        for piece in iter(lambda:f.read(1<<20),b""):h.update(piece)
    return h.hexdigest()

def read_reports(j,c):
    ck(j.is_file() and c.is_file() and not j.is_symlink() and
       not c.is_symlink(),"Original Stage03L files must exist, without symlinks")
    ck(j.stat().st_size<2_000_000 and c.stat().st_size<2_000_000,
       "Unexpected huge original Stage03L report")
    data=json.loads(j.read_text(encoding="utf-8"))
    ck(data.get("stage")==STAGE and data.get("read_only") is True and
       data.get("science_release") is False and
       data.get("slurm_submitted") is False and
       data.get("source_or_model_modified") is False and
       data.get("subintervals_total")==10,
       "Original Stage03L science HOLD and exact subinterval count missing")
    with c.open("r",encoding="utf-8-sig",newline="") as f:
        r=csv.DictReader(f)
        required={"rank","run","start","end","QC1_halfhours",
                  "MDS_colder_than_ERA_gt5C_HH",
                  "MDS_colder_than_ERA_gt10C_HH"}
        ck(required<=set(r.fieldnames or []),"Stage03L priority CSV schema changed")
        rows=list(r)
    ck(len(rows)==10 and {int(r["rank"]) for r in rows}==set(range(1,11)),
       "Stage03L ranks must be unique 1..10")
    rows.sort(key=lambda r:int(r["rank"]))
    for i,r in enumerate(rows[:3]):
        ck(r["run"]=="LONG_1458" and r["start"]==START[i] and
           int(r["QC1_halfhours"])==HOURS[i] and
           int(r["MDS_colder_than_ERA_gt5C_HH"])==GT5[i] and
           int(r["MDS_colder_than_ERA_gt10C_HH"])==GT10[i],
           "Priority first-three original Stage03L source identities changed")
        t0=datetime.fromisoformat(r["start"])
        t1=datetime.fromisoformat(r["end"])
        ck(t1==t0+timedelta(minutes=30*(HOURS[i]-1)),
           "Invalid original source-label 30-minute interval")
    ck(sum(int(r["MDS_colder_than_ERA_gt10C_HH"]) for r in rows)==98 and
       sum(int(r["MDS_colder_than_ERA_gt5C_HH"]) for r in rows)==183,
       "Original Stage03K 98/183 threshold counts not preserved")
    ck(sum(int(r["QC1_halfhours"]) for r in rows)==587,
       "Original Stage03L ten QC1 subruns no longer total 587")
    return data,rows

def candidates(root,additional):
    """Inspect only immediate children of exact site folders, never rglob scratch."""
    directories=[root/sub for sub in SEARCH_SUBDIRS]
    if additional:
        directories.append(additional)
    seen=set();out=[];scanned=[]
    for directory in directories:
        if not directory.is_dir() or directory.is_symlink():continue
        if directory in seen:continue
        seen.add(directory)
        n=0
        for p in directory.iterdir():
            n+=1
            ck(n<=LIMIT,
               "Targeted station folder exceeds 2,000 immediate files; specify narrower --neighbor-dir")
            if p.is_symlink() or not p.is_file():continue
            text=p.name.lower()
            if p.suffix.lower() not in EXTS:continue
            if not any(k in text for k in CANDIDATE_NAMES):continue
            # Filename alone does not prove 2025 data coverage or native QC0.
            out.append({"path":str(p),"filename":p.name,
                        "bytes":p.stat().st_size,
                        "filename_mentions_2025":"2025" in text,
                        "source_station":"IT-TrF",
                        "file_contents_or_measurement_QC_examined":False,
                        "2025_coverage_independently_verified":False})
        scanned.append({"directory":str(directory),"shallow_entries":n})
    out.sort(key=lambda x:(not x["filename_mentions_2025"],x["path"]))
    return scanned,out

def selftest():
    from tempfile import TemporaryDirectory
    with TemporaryDirectory() as d:
        base=Path(d)
        (base/"IT-TrF/forcing/packages").mkdir(parents=True)
        (base/"IT-TrF/forcing/packages/ICOS_IT-TrF_FLUXMET_2012-2025_v1.zip").write_bytes(b"x")
        (base/"IT-TrF/forcing/packages/ICOS_IT-Tor_FLUXMET_2008-2025_v1.zip").write_bytes(b"x")
        (base/"IT-TrF/forcing/packages/notes.txt").write_bytes(b"x")
        scanned,found=candidates(base,None)
        assert len(found)==1 and found[0]["source_station"]=="IT-TrF"
        assert found[0]["filename_mentions_2025"] is True
        assert found[0]["2025_coverage_independently_verified"] is False
        assert sum(GT10)==98 and sum(GT5)==138
    print("STAGE03M SELF-TEST PASS: three priority subruns, site identity guard IT-TrF != IT-Tor, shallow inventory, no source/NetCDF reads or writes")

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--self-test",action="store_true")
    p.add_argument("--stage03l",type=Path)
    p.add_argument("--ranking",type=Path)
    p.add_argument("--site-root",type=Path,default=SITE_ROOT)
    p.add_argument("--neighbor-dir",type=Path)
    p.add_argument("--out-dir",type=Path)
    args=p.parse_args()
    if args.self_test:selftest();return
    ck(args.stage03l is not None and args.ranking is not None and
       args.out_dir is not None and args.out_dir.is_dir() and
       not args.out_dir.is_symlink() and not any(args.out_dir.iterdir()),
       "Require two completed Stage03L reports plus NEW EMPTY private output dir")
    data,ranked=read_reports(args.stage03l,args.ranking)
    scanned,found=candidates(args.site_root,args.neighbor_dir)
    review=[]
    for r in ranked[:3]:
        review.append({"priority_rank":int(r["rank"]),"source_site":"IT-Tor",
           "start":r["start"],"end":r["end"],
           "source_label_UTC_independently_verified":False,
           "QC1_MDS_half_hours":int(r["QC1_halfhours"]),
           "MDS_colder_than_packaged_ERA_gt5C":
                int(r["MDS_colder_than_ERA_gt5C_HH"]),
           "MDS_colder_than_packaged_ERA_gt10C":
                int(r["MDS_colder_than_ERA_gt10C_HH"]),
           "independent_neighbor_measured_QC0_comparison":None,
           "science_gate":"HOLD"})
    report={"stage":"STAGE03M_IT_TOR_HIGH_PRIORITY_MDS_INDEPENDENT_REFERENCE_INVENTORY",
       "read_only":True,"science_release":False,
       "source_or_model_modified":False,"slurm_submitted":False,
       "original_stage03l":str(args.stage03l),
       "original_ranked_source_SHA256":sha(args.ranking),
       "priority_intervals":review,
       "independent_station_candidate":"IT-TrF",
       "independent_station_description":"Torgnon-LD nearby larch-forest, different ecosystem from IT-Tor grassland; measured QC0 only can be compared after clock validation",
       "ICOS_2025_reference":OFFICIAL,
       "directories_shallow_scanned":scanned,
       "candidate_files_by_filename_only":found,
       "unverified_requirements":[
         "Confirm candidate is actually IT-TrF and covers Nov 2025 by inspecting ICOS metadata and archive",
         "Verify timestamp convention (IT-Tor source TIMESTAMP_START vs IT-TrF UTC/local non-DST) before alignment",
         "Verify IT-TrF TA_F_QC=0 means direct measured tower T at exact target times; do not use QC2 ERA as independent evidence",
         "Inspect station sensor height/microclimate differences before comparing grassland and forest temperature",
         "No meteorological repair authorized without independent evidence and explicit decision"
       ]}
    j=args.out_dir/"stage03m_IT_Tor_top3_neighbor_independent_source_inventory_PRIVATE.json"
    with j.open("x",encoding="utf-8") as f:
        json.dump(report,f,indent=2,ensure_ascii=False);f.write("\n")
    print("PRIORITY_3_SUBRUNS",len(review),"QC1_HH",sum(r["QC1_MDS_half_hours"] for r in review),
          "GT10_HH",sum(r["MDS_colder_than_packaged_ERA_gt10C"] for r in review),
          "GT5_HH",sum(r["MDS_colder_than_packaged_ERA_gt5C"] for r in review))
    for r in review:
        print("TARGET",r["priority_rank"],r["start"],r["end"],
              "QC1",r["QC1_MDS_half_hours"],
              "GT10",r["MDS_colder_than_packaged_ERA_gt10C"])
    print("IT_TRF_CANDIDATES",len(found))
    for r in found[:25]:
        print("CANDIDATE_FILENAME_ONLY",r["path"],
              "MENTIONS_2025",r["filename_mentions_2025"])
    print("TARGET_DIRECTORIES_SHALLOW_SCANNED",len(scanned))
    print("PRIVATE_JSON",j)
    print("STAGE03M COMPLETE: INVENTORY ONLY; NO MEASUREMENT COMPARED, NO FORCING/NC/CIME/SLURM")

if __name__=="__main__":
    main()
