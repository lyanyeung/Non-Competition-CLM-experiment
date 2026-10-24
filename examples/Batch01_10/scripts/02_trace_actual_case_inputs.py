#!/usr/bin/env python3
"""READ ONLY Stage02: trace 10 Batch01 original CIME cases' effective inputs.

Read Stage01 all_sites.json. Write a NEW HOME-only report with case metadata,
land surface path, generated DATM namelist/stream file excerpts, source
percentages, and unresolved science flags. NO Slurm, no CIME writes, no
surface/forcing edits, no automatic replacement of PFT remainder with GRA.

Example:
 python3 -B examples/Batch01_10/scripts/02_trace_actual_case_inputs.py \
    --inventory /iridisfs/home/ly3n24/Batch01_10_source_inventory_20261024T090713Z/all_sites.json
"""
import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

SITES=("CZ-BK1","IT-Ren","RU-Fyo","CH-Dav","IT-Col",
       "FR-Fon","FI-Sod","FR-Pue","DE-Hai","BE-Vie")
ROOT=Path("/iridisfs/scratch/ly3n24/CLM_FATES/cases")
DOCUMENTS=("CaseDocs/lnd_in","CaseDocs/datm_in","CaseDocs/datm.streams.xml",
           "Buildconf/datm.input_data_list","user_nl_datm_streams",
           "user_nl_clm")
PATTERN=re.compile(r"(?im)^\s*(fsurdat|finidat|spinup_state|use_fates|"
                   r"use_fates_nocomp|use_fates_fixed_biogeog|year_first|"
                   r"year_last|year_align|streams)\s*=\s*(.*)$")

def stop(s):raise RuntimeError(s)
def digest(path):
    h=hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda:f.read(1<<20),b""):
            h.update(chunk)
    return h.hexdigest()
def safe_read(path):
    if not path.is_file() or path.is_symlink() or path.stat().st_size>2000000:
        return None
    return path.read_text(encoding="utf-8",errors="replace")

def document(path):
    text=safe_read(path)
    row={"path":str(path),"present":path.is_file()}
    if text is None:
        row["status"]="NOT_READABLE_OR_ABSENT_OR_TOO_LARGE"
        return row
    row["sha256"]=digest(path)
    row["values"]={k.lower():v.strip() for k,v in PATTERN.findall(text)}
    # Keep only a tiny safe excerpt, not arbitrary raw source data.
    evidence=[]
    for line in text.splitlines():
        line=line.strip()
        if not line or line.startswith("#"):continue
        if any(t in line.lower() for t in ("password","token","private_key","secret")):
            continue
        if any(t in line.lower() for t in (
            "domain","stream","datafiles","datadir","year_first","year_last",
            "year_align",".nc","fsurdat","spinup_state","finidat")):
            evidence.append(line[:230])
        if len(evidence)>=15:break
    row["file_reference_excerpt"]=evidence
    return row

def trace_case(row,site):
    name=row.get("name","")
    path=Path(row.get("path",""))
    out={"case":name,"path":str(path),"source_case_config":row.get("xml",{}),
         "stage01_fsurdat":row.get("lnd_fsurdat"),
         "stage01_SBATCH":row.get("SBATCH_lines",[])}
    if path.parent!=ROOT or not name.startswith(site+"_") or not path.is_dir():
        out["case_path_check"]="INVALID_OR_MISSING"
        return out
    out["case_path_check"]="PASS"
    out["case_docs"]=[document(path/x) for x in DOCUMENTS]
    rd=row.get("xml",{}).get("RUNDIR")
    if isinstance(rd,str) and rd.startswith("/"):
        p=Path(rd)
        out["rundir"]=str(p)
        out["rundir_exists"]=p.is_dir()
        if p.is_dir():
            names=["lnd_in","datm_in","datm.streams.xml"]
            names+=sorted(x.name for x in p.glob("datm.streams.*")
                          if x.is_file() and not x.is_symlink())[:12]
            out["runtime_docs"]=[document(p/x) for x in dict.fromkeys(names)]
    src=row.get("lnd_fsurdat")
    if isinstance(src,str) and src.startswith("/"):
        surface=Path(src)
        out["case_fsurdat_exists"]=surface.is_file()
        if surface.is_file() and surface.stat().st_size<200000000:
            out["case_fsurdat_sha256"]=digest(surface)
    return out

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--inventory",type=Path,required=True)
    ap.add_argument("--self-test",action="store_true")
    args=ap.parse_args()
    p=args.inventory.expanduser().resolve()
    if not p.is_file() or p.is_symlink() or p.name!="all_sites.json" or not (
         p.parent.name.startswith("Batch01_10_source_inventory_")):
        stop("Expected original Stage01 all_sites.json in timestamped directory")
    data=json.loads(p.read_text(encoding="utf-8"))
    rows=data.get("sites",[])
    if len(rows)!=10 or tuple(r.get("site") for r in rows)!=SITES:
        stop("Stage01 inventory is not exactly Batch01 10-site order")
    if data.get("model_jobs_submitted") is not False or (
        data.get("original_model_files_modified") is not False):
        stop("Stage01 provenance safety flags changed")
    if args.self_test:
        print("STAGE02 SELF-TEST PASS: Stage01 provenance and ten site IDs")
        return
    results=[]
    for item in rows:
        site=item["site"]
        cases=[trace_case(c,site) for c in item.get("baseline_cases",[])]
        results.append({
          "site":site,"cases":cases,
          "stage01_candidate_surfaces":item.get("candidate_surface_files",[]),
          "stage01_processed_csv":item.get("candidate_processed_csv",[]),
          "stage01_DATM_candidate_dirs":item.get("datm_candidate_dirs",[]),
          "vegetation_evidence":item.get("cohort_evidence",{}),
          "soil_policy":"SITE_MEASURED_TEXTURE_IF_SUPPORTED_ELSE_GRID_FALLBACK",
          "PFT_remainder":"UNRESOLVED_NEVER_AUTOMATIC_GRA",
          "readiness":"HOLD_MODEL_SURFACE_UNTIL_AREA_DENOMINATOR_REVIEW",
        })
    name="Batch01_10_stage02_case_trace_"+datetime.now(timezone.utc).strftime(
         "%Y%m%dT%H%M%SZ")
    out=Path.home()/name
    out.mkdir(mode=0o700,exist_ok=False)
    report={"source_inventory":str(p),"source_sha256":digest(p),
            "files_changed_outside_new_report":False,
            "slurm_submitted":False,"sites":results}
    (out/"case_trace.json").write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n")
    lines=["# Batch01 Stage02 read-only report","",
           "Zero scanned CSVs/DATM dirs is NOT proof that no forcing exists.","",
           "| Site | CIME cases | scanned CSV count | scanned DATM dirs | Follow-up |",
           "|---|---:|---:|---:|---|"]
    print("SITE     CASES  CSV  DATM  NEXT")
    for x in results:
        n=len(x["cases"])
        csv_count=sum(y.get("count",0) for y in x["stage01_processed_csv"])
        nc=len(x["stage01_DATM_candidate_dirs"])
        flag="TRACE_DATM_OR_CASE" if n!=1 or csv_count==0 or nc==0 else "PFT_AND_SOIL"
        print(f"{x['site']:<8} {n:>5} {csv_count:>4} {nc:>5}  {flag}")
        lines.append(f"| {x['site']} | {n} | {csv_count} | {nc} | {flag} |")
        for c in x["cases"]:
            print("  CASE",c["case"],"RUNDIR",c["source_case_config"].get("RUNDIR","UNKNOWN"))
            print("  FSURDAT",c.get("stage01_fsurdat","UNKNOWN"))
    lines+=["","Every case should be reviewed by its actual generated DATM streams.",
            "PFT values reported as tree-carbon stock, tree species, or basal area are not ground-area fractions.",
            "Unknown tree percentage is not grass, and observed-soil survey depths must be checked.",
            "No Batch01 fixed PFT surface or new AD400 case has been authorized.",
            ""]
    (out/"readme.md").write_text("\n".join(lines),encoding="utf-8")
    print("REPORT:",out/"readme.md")
    print("DETAIL:",out/"case_trace.json")
    print("READ ONLY ORIGINAL INPUTS; NO SLURM OR CIME JOBS")
if __name__=="__main__":
    main()
