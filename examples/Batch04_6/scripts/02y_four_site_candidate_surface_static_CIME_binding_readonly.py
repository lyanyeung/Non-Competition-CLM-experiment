#!/usr/bin/env python3
"""ICOS Batch04 Stage02Y — four candidate surface receipts and static CIME binding audit.

READ ONLY. Checks the exact 4 successful Stage02X GitHub-model PFT candidate
NetCDF SHA256 hashes, matching receipts and unchanged original source/soil;
then inspects eight original S30EXCL/S30SHARED CIME cases' generated land
and DATM input documents. Uses saved Stage02V source-path matching evidence.

Static CaseDocs/input lists do NOT prove which streams an executable opens,
nor approve native tower meteorology, soil, AD5/AD400 or FATES run behavior.
Only writes a JSON and CSV inside a NEW EXISTING EMPTY --out-dir; no source,
FATES, CIME, NC, Slurm or Git worktree writes.
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
import math
import re
from pathlib import Path

STAGE_V="STAGE02V_BATCH04_FOUR_SITE_DATM_PATH_PARSER_AND_LANDUNIT_TRIAGE"
STAGE_C="STAGE02C_SITE_DATM_CANDIDATE_YEAR_AND_SAMPLE_QC"
SITES=("DE-Gri","DE-RuR","IT-Tor","ES-Agu")
COUNT={"DE-Gri":22,"DE-RuR":15,"IT-Tor":18,"ES-Agu":19}
PFT={"DE-Gri":{13:100.0},"DE-RuR":{13:100.0},
     "IT-Tor":{13:100.0},"ES-Agu":{0:49.0,9:22.0,13:29.0}}
EXPECTED_SHA={
    "DE-Gri":"08887d2daf5d529b5fed89ca21c8094e19dd471ff3387a758ce23b471211ed2b",
    "DE-RuR":"2a4685ae3a43323fcff829bd3fdb5d998d58b4e077923a991ee4afd727767414",
    "IT-Tor":"908b73f67f74333fa70fcd3b07d8500de14c70b4efdd1e6f36ea23bb4f8b7c7b",
    "ES-Agu":"067722b0dc1440abc2e6aef30ca443b04198f697f16e5ba70344e41f89638fa6",
}
FIELDS=("site","original_case","candidate_SHA256_verified",
        "source_surface_SHA256_verified","soil_arrays_unchanged",
        "candidate_natveg100_crop0_PFT_verified","current_static_fsurdat",
        "fsurdat_is_original_not_candidate","static_lnd_in_present",
        "static_datm_in_present","static_datm_input_list_present",
        "static_datm_input_list_verified_stage02v",
        "static_datm_named_streams","stream_docs_with_site_names",
        "source_soil_science_HOLD","native_tower_source_QC_HOLD",
        "runtime_binding_VERIFIED","new_case_created","AD5_authorized")
SITE_ROOT="/iridisfs/scratch/ly3n24/CLM_FATES"
CIME_NC_RE=re.compile(r"(?<![A-Za-z0-9_.])/[A-Za-z0-9_.+~:%@/=-]+\.nc(?:4)?(?=$|[\s'\"<>,;])",re.I)

def sha(path):
    h=hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda:f.read(1<<20),b""):
            h.update(b)
    return h.hexdigest()

def target_vec(site):
    return [PFT[site].get(i,0) for i in range(15)]

def require_stage(v):
    if v.get("stage")!=STAGE_V or v.get("read_only") is not True or \
       v.get("science_release") is not False:
        raise ValueError("Saved Stage02V original science-HOLD evidence missing")
    cases=v.get("cases")
    if not isinstance(cases,list) or len(cases)!=8:
        raise ValueError("Stage02V must contain 8 original cases")
    bysite={}
    for x in cases:
        site=x.get("site")
        name=x.get("case","")
        if site not in SITES or not name.startswith(site+"_FATES_SPINUP1000_S30") or \
           not name.endswith(("S30SHARED","S30EXCL")) or \
           x.get("stage02b_exact_source_path_match") is not True or \
           x.get("canonical_source_path_match") is not True or \
           x.get("all_candidate_NC_exist") is not True or \
           x.get("science_release")!="HOLD":
            raise ValueError("Unexpected Stage02V source/CIME/approval state "+str(name))
        bysite.setdefault(site,[]).append(x)
    if set(bysite)!=set(SITES) or \
       any({c["case"].rsplit("_",1)[-1] for c in bysite[site]}!={"S30EXCL","S30SHARED"}
           for site in SITES):
        raise ValueError("Missing/duplicate S30EXCL-S30SHARED case pair")
    return bysite

def require_stage02c(c):
    if c.get("stage")!=STAGE_C or c.get("read_only") is not True or \
       c.get("science_release") is not False:
        raise ValueError("Saved original Stage02C all-six source register required")
    bysite={r.get("site"):r for r in c.get("sites",[])}
    if len(bysite)!=6:
        raise ValueError("Stage02C original inventory not six sites")
    records={}
    for site in SITES:
        rows=bysite[site].get("cases",[])
        if len(rows)!=2 or bysite[site].get("distinct_site_datm_files")!=COUNT[site]:
            raise ValueError(site+" source Stage02C years/cases changed")
        reg={}
        for x in rows:
            vals={e.get("path") for e in x.get("site_datm",[])}
            if len(vals)!=COUNT[site] or any(not isinstance(q,str) for q in vals):
                raise ValueError(site+" source original file paths missing")
            reg[x["case"]]=vals
        if len(reg)!=2:
            raise ValueError(site+" duplicate original CIME case")
        records[site]=reg
    return records

def actual_site_input_paths(content,site):
    names=re.compile("^"+re.escape(site)+r"_DATM_(?:19|20)\d{2}(?:[_.-]|$)",re.I)
    return {m.group(0) for line in content.splitlines()
            for m in CIME_NC_RE.finditer(line)
            if names.match(Path(m.group(0)).name)}

def require_surface(site,root):
    import numpy as np
    from netCDF4 import Dataset
    source=root/(site+"_B04_GITHUBPFT_POINT_CANDIDATE.nc")
    receipt=root/(site+"_B04_surface_manifest.json")
    if not source.is_file() or not receipt.is_file() or \
       source.is_symlink() or receipt.is_symlink() or receipt.stat().st_size>32768:
        raise ValueError(site+" missing/untrusted candidate surface/receipt")
    if sha(source)!=EXPECTED_SHA[site]:
        raise ValueError(site+" candidate SHA256 differs from operator-verified build")
    info=json.loads(receipt.read_text(encoding="utf-8"))
    if info.get("site")!=site or info.get("candidate_surface")!=str(source) or \
       info.get("candidate_sha256")!=EXPECTED_SHA[site] or \
       info.get("model_proxy_GitHub_approved") is not True or \
       info.get("meteorology_QC_approved") is not False or \
       info.get("runtime_case_approved") is not False or \
       info.get("slurm_submitted") is not False:
        raise ValueError(site+" candidate receipt contradicts approved inputs/HOLD")
    old=Path(info.get("source_surface",""))
    if old.name!=f"surfdata_{site}_hist_2000_16pfts_c261014.nc" or \
       old.parent.name!="subset_data" or old.parent.parent.name!=site or \
       not old.is_file() or old.is_symlink() or sha(old)!=info.get("source_sha256"):
        raise ValueError(site+" original surface provenance/hash mismatch")
    prescribed={int(k):float(v) for k,v in info.get("PCT_NAT_PFT_target",{}).items()}
    if prescribed!=PFT[site]:
        raise ValueError(site+" receipt changed official GitHub host PFT shares")
    with Dataset(str(old),"r") as a,Dataset(str(source),"r") as b:
        for x in ("PCT_NATVEG","PCT_CROP"):
            v=np.ma.filled(b.variables[x][:],np.nan).reshape(-1)
            expected=100 if x=="PCT_NATVEG" else 0
            if v.size!=1 or not np.allclose(v,[expected],atol=1e-5):
                raise ValueError(site+" candidate landunit "+x+" not model point")
        p=np.ma.filled(b.variables["PCT_NAT_PFT"][:],np.nan).reshape(-1)
        if len(p)!=15 or not np.allclose(p,target_vec(site),atol=1e-5):
            raise ValueError(site+" candidate PCT_NAT_PFT differs")
        keep=("PCT_SAND","PCT_CLAY","ORGANIC","LATIXY","LONGXY")
        for field in keep:
            if field not in a.variables or field not in b.variables or \
               not np.ma.allequal(a.variables[field][:],b.variables[field][:]):
                raise ValueError(site+" protected soil/site variable diverged: "+field)
        organic=np.ma.filled(b.variables["ORGANIC"][:],np.nan).reshape(-1)
        if organic.size!=10 or not np.isfinite(organic).all():
            raise ValueError(site+" ten-layer organic not finite")
    return {
        "candidate_path":str(source),"candidate_sha":EXPECTED_SHA[site],
        "receipt_path":str(receipt),"source_path":str(old),
        "source_sha":info["source_sha256"],"source_soil_unchanged":True,
        "soil_organic_min":float(organic.min()),
        "soil_organic_max":float(organic.max()),
        "soil_flag":"IT_TOR_ALL_TEN_ORGANIC_ZERO_SOURCE_REVIEW" if site=="IT-Tor" else
                    "INHERITED_SOIL_NOT_MEASURED_SOURCE_VERIFIED",
    }

def assignments(path):
    if not path.is_file() or path.is_symlink() or path.stat().st_size>2_000_000:
        return {"status":"MISSING_OR_OVER2MB_OR_SYMLINK"}
    content=path.read_text(encoding="utf-8",errors="replace")
    vals={}
    for key in ("fsurdat","fates_paramfile","streams","year_first",
                "year_last","year_align","taxmode","mapalgo"):
        rows=re.findall(r"(?im)^[ \t]*"+re.escape(key)+r"[ \t]*=[ \t]*(.+)$",content)
        if rows:
            vals[key]=[x.split("!")[0].strip().rstrip(",")[:1200] for x in rows[:20]]
    return {"status":"PRESENT","fields":vals,
            "stream_relevant_line_examples":[x.strip()[:480] for x in content.splitlines()
                 if any(word in x.lower() for word in ("streams","taxmode","year_first",
                     "year_last","year_align","fsurdat","fates_paramfile"))][:20]}

def one_case(base,site,entry,surface,expected_paths):
    name=entry["case"]
    case=base/"cases"/name
    if case.name!=name or case.is_symlink() or not case.is_dir():
        raise ValueError("Expected original CIME case missing: "+name)
    docs=case/"CaseDocs"
    land=assignments(docs/"lnd_in")
    datm=assignments(docs/"datm_in")
    original=surface["source_path"]
    land_f=land.get("fields",{}).get("fsurdat",[])
    if not land_f:
        raise ValueError(name+" has no static fsurdat in original CaseDocs")
    recorded=land_f[0].strip("'\"")
    if recorded!=original:
        raise ValueError(name+" original CaseDocs fsurdat changed; source pin failed")
    inputfile=case/"Buildconf/datm.input_data_list"
    if not inputfile.is_file() or inputfile.is_symlink() or \
       inputfile.stat().st_size>4_000_000:
        raise ValueError(name+" original source DATM input list missing")
    datm_input=inputfile.read_text(encoding="utf-8",errors="replace")
    found=actual_site_input_paths(datm_input,site)
    if found!=expected_paths or len(found)!=COUNT[site] or \
       any(not Path(q).is_file() for q in found):
        raise ValueError(name+" current original DATM source list diverged from Stage02C")
    count=sum(1 for line in datm_input.splitlines() if site+"_DATM_" in line)
    streamfiles=sorted(p for p in docs.glob("*stream*") if p.is_file() and not p.is_symlink())[:24]
    stream_records=[]
    for p in streamfiles:
        if p.stat().st_size>500_000:raise ValueError("Unexpected huge CIME stream document "+str(p))
        t=p.read_text(encoding="utf-8",errors="replace")
        stream_records.append({"path":str(p),
                               "sha256":sha(p),
                               "mentions_site_DATM":site+"_DATM_" in t,
                               "mentions_site":site in t,
                               "site_lines":[x.strip()[:450] for x in t.splitlines() if site in x][:12]})
    return {
        "site":site,"case":name,"original_case_fsourced":recorded,
        "land_in":land,"datm_in":datm,
        "DATM_input_file":str(inputfile),
        "DATM_input_file_sha256":sha(inputfile),
        "DATM_site_mentioned_lines":count,
        "Stage02V_exact_site_file_references":entry.get("parser_stage02b_count"),
        "Stage02V_static_path_match":True,
        "stream_documents":stream_records,
        "static_streams_present":bool(datm.get("fields",{}).get("streams")),
        "candidate_surface_not_yet_bound":recorded!=surface["candidate_path"],
        "active_runtime_stream_binding_approved":False,
        "native_tower_QC_approved":False,
        "soil_source_approved":False,
        "model_release":"HOLD",
    }

def self_test():
    assert len(SITES)==4 and sum(COUNT.values())==74
    assert all(len(v)==64 and all(c in "0123456789abcdef" for c in v)
               for v in EXPECTED_SHA.values())
    assert sum(target_vec("ES-Agu"))==100
    assert target_vec("ES-Agu")[0]==49
    assert target_vec("ES-Agu")[9]==22
    assert target_vec("ES-Agu")[13]==29
    assert sum(target_vec("IT-Tor"))==100
    toy="first='/tmp/DE-Gri_DATM_2004.nc'\nsecond=/tmp/DE-Gri_DATM_2005.nc4\nother=/tmp/ES-Agu_DATM_2004.nc"
    assert len(actual_site_input_paths(toy,"DE-Gri"))==2
    assert not actual_site_input_paths(toy,"IT-Tor")
    print("STAGE02Y SELF-TEST PASS: four fixed SHA surfaces, receipts, 8 original-case static CIME streams and soil QC HOLD; NO WRITES")

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--self-test",action="store_true")
    p.add_argument("--stage02v",type=Path)
    p.add_argument("--stage02c",type=Path)
    p.add_argument("--candidate-dir",type=Path)
    p.add_argument("--base",type=Path,default=Path(SITE_ROOT))
    p.add_argument("--out-dir",type=Path)
    args=p.parse_args()
    if args.self_test:self_test();return
    if not args.stage02v or not args.stage02v.is_file() or \
       not args.stage02c or not args.stage02c.is_file():
        p.error("Original saved Stage02V and Stage02C JSONs required")
    if args.candidate_dir is None or not args.candidate_dir.is_dir() or \
       args.candidate_dir.name!="Batch04_GitHub_PFT_Gz7kLAkn":
        p.error("Use exact operator-verified Stage02X four-surface output directory")
    if args.out_dir is None or not args.out_dir.is_dir() or \
       args.out_dir.is_symlink() or any(args.out_dir.iterdir()):
        p.error("--out-dir must be an existing EMPTY directory")
    if args.base.name!="CLM_FATES" or not args.base.is_dir():
        p.error("Original case root not CLM_FATES")
    v=json.loads(args.stage02v.read_text(encoding="utf-8"))
    original=require_stage(v)
    registered=require_stage02c(json.loads(args.stage02c.read_text(encoding="utf-8")))
    report=[]
    matrix=[]
    for site in SITES:
        surface=require_surface(site,args.candidate_dir)
        print("SURFACE",site,"SHA256 PASS","MODEL_PFT",PFT[site],
              "ORIGINAL_SOIL_UNCHANGED",surface["source_soil_unchanged"],
              "ORGANIC_RANGE",[surface["soil_organic_min"],surface["soil_organic_max"]],
              "SOIL_GATE",surface["soil_flag"])
        cases=[one_case(args.base,site,row,surface,registered[site][row["case"]]) for row in original[site]]
        if len(cases)!=2:
            raise ValueError("Missing original pair for "+site)
        for case in cases:
            print("CASE",case["case"],"STATIC_DATM_FILES",case["Stage02V_exact_site_file_references"],
                  "STATIC_INPUT_SITE_LINES",case["DATM_site_mentioned_lines"],
                  "CASE_FSURDAT_IS_ORIGINAL",case["original_case_fsourced"]==surface["source_path"],
                  "NEW_PFT_SURFACE_NOT_BOUND",case["candidate_surface_not_yet_bound"],
                  "DATM_STREAM_FIELD",case["datm_in"].get("fields",{}).get("streams","MISSING"),
                  "STREAM_DOCS",len(case["stream_documents"]))
            matrix.append({
                "site":site,"original_case":case["case"],
                "candidate_SHA256_verified":True,
                "source_surface_SHA256_verified":True,
                "soil_arrays_unchanged":True,
                "candidate_natveg100_crop0_PFT_verified":True,
                "current_static_fsurdat":case["original_case_fsourced"],
                "fsurdat_is_original_not_candidate":case["candidate_surface_not_yet_bound"],
                "static_lnd_in_present":case["land_in"]["status"]=="PRESENT",
                "static_datm_in_present":case["datm_in"]["status"]=="PRESENT",
                "static_datm_input_list_present":True,
                "static_datm_input_list_verified_stage02v":True,
                "static_datm_named_streams":json.dumps(case["datm_in"].get("fields",{}).get("streams",[])),
                "stream_docs_with_site_names":sum(int(x["mentions_site"]) for x in case["stream_documents"]),
                "source_soil_science_HOLD":True,
                "native_tower_source_QC_HOLD":True,
                "runtime_binding_VERIFIED":False,
                "new_case_created":False,"AD5_authorized":False,
            })
        report.append({"site":site,"surface":surface,"cases":cases,
                       "PFT_selection_approved":True,
                       "candidate_surface_source_approved_only":True,
                       "native_tower_QC_approved":False,
                       "site_soil_QC_approved":False,
                       "IT_Tor_organic_zero_HOLD":site=="IT-Tor",
                       "runtime_CIME_stream_loaded_proved":False,
                       "AD5_authorized":False})
    result={
        "stage":"STAGE02Y_BATCH04_FOUR_SITE_CANDIDATE_SURFACE_STATIC_CIME_BINDING_AUDIT",
        "read_only":True,"science_release":False,
        "source_stage02v":str(args.stage02v),
        "source_stage02c":str(args.stage02c),
        "candidate_directory":str(args.candidate_dir),
        "source_or_case_modified":False,"slurm_submitted":False,
        "sites":report,
        "caution":"Original eight cases retain original fsurdat, not the four new PFT candidates. Static CaseDocs/Buildconf text cannot prove runtime DATM loading or native tower met QC; soil inherited with IT-Tor 10-layer ORGANIC=0. No AD5/AD400 approval.",
    }
    j=args.out_dir/"stage02y_four_site_candidate_surface_case_binding_audit.json"
    c=args.out_dir/"stage02y_eight_case_static_binding_matrix.csv"
    with j.open("x",encoding="utf-8") as f:
        json.dump(result,f,indent=2,ensure_ascii=False);f.write("\n")
    with c.open("x",encoding="utf-8",newline="") as f:
        writer=csv.DictWriter(f,fieldnames=FIELDS);writer.writeheader();writer.writerows(matrix)
    print("SURFACE_HASH_AND_SOIL_PROVENANCE_PASS 4/4")
    print("ORIGINAL_CASES_INSPECTED 8/8; NEW_CANDIDATE_BOUND_IN_ORIGINAL_CASE 0/8")
    print("JSON",j)
    print("CSV",c)
    print("SCIENCE_HOLD: NATIVE_MET_QC, SOIL SOURCE, FATES ACTUAL RUNTIME / DATM STREAM; NO SLURM")

if __name__=="__main__":
    main()
