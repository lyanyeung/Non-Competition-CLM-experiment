#!/usr/bin/env python3
"""Batch01: READ-ONLY audit of ten original ICOS/FLUXNET CLM-FATES sites.

Reports existing site/forcing/surface/CIME case evidence on IRIDIS6.
NEVER edits source, netCDF, CIME, git, symlinks, restart or Slurm jobs.
Writes only a new, uniquely timestamped report directory under user's HOME.
DOES NOT make PFT allocation decisions; unknown forest species != GRA.

Run:
  python3 -B examples/Batch01_10/scripts/01_audit_iridis_batch01_sources.py --self-test
  python3 -B examples/Batch01_10/scripts/01_audit_iridis_batch01_sources.py audit
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
import os
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
import xml.etree.ElementTree as ET

REPO=Path(__file__).resolve().parents[3]
SOURCE_CSV=REPO/"data/batch01_10_sites.csv"
BASE=Path("/iridisfs/scratch/ly3n24/CLM_FATES")
SITES=BASE/"sites/MY_EC_SITE"
CASES=BASE/"cases"
SELECTED=("CZ-BK1","IT-Ren","RU-Fyo","CH-Dav","IT-Col",
          "FR-Fon","FI-Sod","FR-Pue","DE-Hai","BE-Vie")
PROTECTED=("NL-Loo","DE-Tha")
RUN_PARAMETERS=("RUN_TYPE","RUN_STARTDATE","RUN_REFCASE","RUN_REFDATE",
                "STOP_N","STOP_OPTION","REST_N","REST_OPTION",
                "CLM_ACCELERATED_SPINUP","CLM_CO2_TYPE","CCSM_CO2_PPMV",
                "CONTINUE_RUN","RESUBMIT","RUNDIR","DOUT_S_ROOT",
                "EXEROOT","COMPSET","LND_TUNING_MODE","MPI_RUN_COMMAND")
NC_PCT=("PCT_NATVEG","PCT_CROP","PCT_NAT_PFT","PCT_SAND","PCT_CLAY")

def fail(s):raise RuntimeError(str(s))

def sha256(p:Path):
    h=hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda:f.read(1048576),b""):
            h.update(b)
    return h.hexdigest()

def audit_cohort():
    if not SOURCE_CSV.is_file():fail("Batch01 CSV missing: "+str(SOURCE_CSV))
    with SOURCE_CSV.open(newline="",encoding="utf-8-sig") as f:
        rows=list(csv.DictReader(f))
    ids=[r.get("site","") for r in rows]
    if len(rows)!=10 or tuple(ids)!=SELECTED or len(set(ids))!=10:
        fail("Batch01 site order/membership not exactly 10 expected names")
    if set(ids)&set(PROTECTED):fail("Existing example sites appeared in Batch01")
    expected_fields={"site","readiness","evidence_class","denominator",
                     "reported_numeric_evidence","source_url"}
    if not expected_fields.issubset(rows[0]):
        fail("Batch01 evidence CSV schema changed; update script with review")
    if any(r["readiness"]!="EVIDENCE_ONLY_HOLD_SURFACE" for r in rows):
        fail("A Batch01 source surface was labelled approved unexpectedly")
    return rows

def xml_entries(case:Path):
    out={}
    for filename in ("env_run.xml","env_build.xml","env_case.xml","env_mach_pes.xml"):
        f=case/filename
        if not f.is_file():continue
        try:
            root=ET.parse(f).getroot()
            for ent in root.iter("entry"):
                key=ent.attrib.get("id")
                if key in RUN_PARAMETERS:
                    out[key]=ent.attrib.get("value")
        except Exception as e:
            out["ERROR_"+filename]=str(e)
    return out

def nml_value(s,key):
    found=re.findall(r"(?im)^\s*"+re.escape(key)+r"\s*=\s*(.*?)\s*(?:!.*)?$",
                     s)
    return found[-1].strip().strip("'\"") if found else None

def surface_summary(path:Path):
    out={"path":str(path),"exists":path.is_file()}
    if not path.is_file():return out
    out["bytes"]=path.stat().st_size
    if path.stat().st_size<=200_000_000:
        out["sha256"]=sha256(path)
    else:
        out["sha256"]="SKIPPED_GT_200MB"
    try:
        import numpy as np
        from netCDF4 import Dataset
        with Dataset(path,"r") as ds:
            out["available_surface_fields"]=[k for k in NC_PCT if k in ds.variables]
            for k in ("PCT_NATVEG","PCT_CROP"):
                if k in ds.variables:
                    a=np.ma.filled(ds.variables[k][:],np.nan).ravel()
                    if len(a)==1 and np.isfinite(a[0]):out[k]=float(a[0])
            if "PCT_NAT_PFT" in ds.variables:
                a=np.ma.filled(ds.variables["PCT_NAT_PFT"][:],np.nan).ravel()
                if len(a) in (15,16) and np.isfinite(a).all():
                    out["host_natpft_current_pct"]=list(map(float,a))
                    out["host_natpft_total_pct"]=float(a.sum())
                else:out["host_natpft_issue"]="unexpected missing/count"
            for k in ("PCT_SAND","PCT_CLAY"):
                if k in ds.variables:
                    a=np.ma.filled(ds.variables[k][:],np.nan).ravel()
                    if a.size and np.isfinite(a[0]):
                        out[k+"_input_layer1_pct"]=float(a[0])
                    out[k+"_input_layer_count"]=int(a.size)
    except Exception as e:
        out["surface_read_error"]=str(e)
    return out

def case_summary(path:Path):
    item={"name":path.name,"path":str(path),"xml":xml_entries(path)}
    docs=path/"CaseDocs/lnd_in"
    if docs.is_file():
        text=docs.read_text(errors="replace")
        item["generated_lnd_in_exists"]=True
        for field in ("fsurdat","finidat","spinup_state","use_fates",
                      "use_fates_nocomp","use_fates_fixed_biogeog",
                      "fates_hlm_pft_map"):
            item["lnd_"+field]=nml_value(text,field)
    else:item["generated_lnd_in_exists"]=False
    stream=path/"user_nl_datm_streams"
    item["user_nl_datm_streams_exists"]=stream.is_file()
    if stream.is_file():
        text=stream.read_text(errors="replace")
        item["datm_stream_year_first"]=nml_value(text,"year_first")
        item["datm_stream_year_last"]=nml_value(text,"year_last")
        item["datm_stream_year_align"]=nml_value(text,"year_align")
        item["datm_stream_sample_year_files"]=re.findall(r"[\w.-]+\.nc",text)[:4]
    runfile=path/".case.run"
    if runfile.is_file():
        item["SBATCH_lines"]=[x.strip() for x in runfile.read_text(errors="replace").splitlines()
                                if x.lstrip().startswith("#SBATCH")][:30]
    return item

def list_path(parent:Path,pattern:str,limit=70):
    if not parent.is_dir():return []
    xs=sorted(parent.glob(pattern),key=lambda p:p.name)
    return [{"name":p.name,"path":str(p),"bytes":p.stat().st_size if p.is_file() else None,
             "is_dir":p.is_dir()} for p in xs[:limit]],len(xs)

def audit_site(row,cases):
    site=row["site"]
    folder=SITES/site
    forcing=folder/"forcing"
    result={
      "site":site,"cohort_evidence":row,
      "site_root":str(folder),"site_exists":folder.is_dir(),
      "scientific_gate":"HOLD_PFT_AREA_DENOMINATOR_AND_SOIL_DECISION",
      "unknown_PFT_assignment":"UNRESOLVED_NEVER_AUTOMATIC_GRA",
      "source_datum_is_not_necessarily_land_area":True,
      "baseline_cases":[],
      "candidate_surface_files":[],
      "forcing_folder_names":[],
      "candidate_processed_csv":[],
      "datm_candidate_dirs":[],
      "soil_observations_found":"NOT_ASSESSED_BY_FILESYSTEM_INVENTORY",
      "jobs_started_by_audit":False
    }
    if not folder.is_dir():return result
    try:
        result["site_top_dirs"]=[x.name for x in sorted(folder.iterdir(),key=lambda p:p.name)][:80]
    except OSError as e:result["site_top_error"]=str(e)
    subset=folder/"subset_data"
    paths=[]
    if subset.is_dir():
        paths+=list(subset.glob("surfdata*.nc")) if False else []
        paths+=sorted(subset.glob("*.nc"))
    other=folder/"surface"
    if other.is_dir():paths+=sorted(other.glob("*.nc"))
    dedup={}
    for p in paths:
        dedup[str(p)]=p
    result["candidate_surface_files"]=[surface_summary(p) for p in list(dedup.values())[:16]]
    for c in cases:
        if c.is_dir():
            item=case_summary(c)
            result["baseline_cases"].append(item)
            surf=item.get("lnd_fsurdat")
            if surf and surf.startswith("/") and surf not in dedup:
                p=Path(surf)
                if p.is_file():
                    result["effective_case_surface_extra"]=surface_summary(p)
                    dedup[surf]=p
    if forcing.is_dir():
        result["forcing_folder_names"]=[x.name for x in
          sorted(forcing.iterdir(),key=lambda p:p.name)[:90]]
        for p in sorted(forcing.iterdir(),key=lambda p:p.name):
            if p.is_dir() and (p.name.startswith("processed") or
                               p.name.lower().startswith("qc")):
                files,tot=list_path(p,"*.csv")
                result["candidate_processed_csv"].append({
                    "folder":str(p),"files":files[:16],"count":tot
                })
            if p.is_dir() and any(tok in p.name.lower()
                                  for tok in ("datm","clm_forcing","annual")):
                first,_=list_path(p,"*.nc")
                second=[]
                if not first:
                    for child in sorted(p.iterdir(),key=lambda z:z.name)[:12]:
                        if child.is_dir():
                            items,n=list_path(child,"*.nc")
                            if items:second.append({"path":str(child),
                                                    "annual_nc_files":n,
                                                    "sample":items[:2]})
                result["datm_candidate_dirs"].append({
                    "path":str(p),"top_level_nc_count":len(first),
                    "top_level_sample":first[:3],"subfolder_samples":second[:6]})
    return result

def get_case_map():
    mapping={x:[] for x in SELECTED}
    if not CASES.is_dir():return mapping
    for case in CASES.iterdir():
        if not case.is_dir():continue
        for site in SELECTED:
            if case.name.startswith(site+"_FATES") or (
                case.name.startswith(site+"_") and "SPINUP" in case.name):
                mapping[site].append(case)
    for site in SELECTED:
        mapping[site]=sorted(mapping[site],key=lambda p:p.name)[:20]
    return mapping

def run():
    rows=audit_cohort()
    mapping=get_case_map()
    data=[audit_site(row,mapping[row["site"]]) for row in rows]
    stamp=datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    home=Path.home().resolve()
    out=home/("Batch01_10_source_inventory_"+stamp)
    if not out.parent.samefile(home) or out.exists():
        fail("Audit report target must be a previously nonexistent direct HOME child")
    out.mkdir(mode=0o700)
    (out/"all_sites.json").write_text(json.dumps({
      "title":"Batch01 ten-site READ-ONLY original-input inventory",
      "run_utc":datetime.now(timezone.utc).isoformat(),
      "original_model_files_modified":False,
      "model_jobs_submitted":False,
      "cohort_csv_sha256":sha256(SOURCE_CSV),
      "caveat":"PFT species/stand/basal area evidence is not automatically area; no GRA fallback",
      "sites":data
    },indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    summary=[]
    for item in data:
        names=item["candidate_surface_files"]
        case_count=len(item["baseline_cases"])
        csv_counts=sum(x["count"] for x in item["candidate_processed_csv"])
        summary.append({
            "site":item["site"],"existing_site_root":item["site_exists"],
            "original_cases":case_count,"surface_candidates":len(names),
            "processed_csv_candidates":csv_counts,
            "datm_candidate_dirs":len(item["datm_candidate_dirs"]),
            "evidence_class":item["cohort_evidence"]["evidence_class"],
            "scientific_gate":item["scientific_gate"]
        })
    with (out/"summary.csv").open("x",encoding="utf-8",newline="") as f:
        writer=csv.DictWriter(f,fieldnames=list(summary[0]))
        writer.writeheader()
        writer.writerows(summary)
    print("=== BATCH01 SOURCE INVENTORY / READ ONLY MODEL INPUTS ===")
    print("SITE     EXISTS  CASES  SURF  CSV  DATM  SCIENTIFIC")
    for x in summary:
        print(f"{x['site']:<8} {str(x['existing_site_root']):<6} "
              f"{x['original_cases']:>5} {x['surface_candidates']:>5} "
              f"{x['processed_csv_candidates']:>4} "
              f"{x['datm_candidate_dirs']:>5} HOLD")
    print("REPORT DIRECTORY:",out)
    print("JSON:",out/"all_sites.json")
    print("SUMMARY CSV:",out/"summary.csv")
    print("NO SURFACE OR FORCING MODIFIED. NO CIME OR SLURM ACTION.")
    print("NEXT: review baseline case, source soil, field PFT denominator and FATES mapping.")
    return 0

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("action",nargs="?",default="audit",choices=("audit",))
    ap.add_argument("--self-test",action="store_true")
    args=ap.parse_args()
    if args.self_test:
        rows=audit_cohort()
        print("SELF-TEST PASS: 10 exact unique Batch01 sites; NL-Loo/DE-Tha excluded")
        print("NO PFT RESIDUAL ASSIGNED TO GRA. NO WRITES.")
        return
    run()

if __name__=="__main__":main()
