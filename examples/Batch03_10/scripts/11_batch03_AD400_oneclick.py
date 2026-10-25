#!/usr/bin/env python3
"""Batch03 10-site surface builder and validated AD5 submit/status controller.

Same operational method as the successful Batch01 Stage11
(examples/Batch01_10/scripts/11_batch10_AD400_oneclick.py), adapted to the
third ICOS/European cohort. Differences from Batch01, all deliberate:

- Site list, template cases and output root are Batch03-specific
  (case names <site>_B03_FIXNC_AD400; nothing from Batch01 is touched).
- The source surface is NOT hard-coded by date: it is read from the
  template case's generated CaseDocs/lnd_in `fsurdat` (actual-input trace),
  and must be a regular file named surfdata_<site>_*.nc.
- Supported PFT classes are extended with tropical EBF (HLM 4) for GF-Guy
  and cool C3 grass (HLM 13) for the two managed grasslands. Every used
  class must map to exactly one expected FATES PFT in the pinned JSON.
- Soil choices are read from data/batch03_10_soil_input_decisions.csv:
  SITE_LITERATURE_UNIFORM_10_LAYER_PROXY replaces PCT_SAND/PCT_CLAY;
  SOIL_TEXTURE_GRID_FALLBACK keeps the original layers (labelled, not observed).
- submit-smoke parses and stores the run/st_archive Slurm job IDs in each
  site ledger, so Stage13 never needs hard-coded job IDs.

Actions:
  self-test       parse CSVs and helpers; no HPC access, no writes
  plan            show choices and discovered inputs; never writes
  surfaces        create 10 versioned independent site surface NetCDFs
  submit-smoke    submit 10 x FIRST FIVE YEARS ONLY, then STOP
  status          summarize 10 case paths and scheduler jobs (read only)

Run 'surfaces' once, then Stage12 private-overlay recovery, then
'submit-smoke'. Never overwrites an existing target and never submits a
duplicate job. Sites are handled separately; failures are reported at the end.

Scientific modelling assumptions (see README and data/ CSVs):
- 100% NATVEG, zero crop/other landunits; PFT fractions are named proxies,
  NOT measured whole-footprint ground-area fractions.
- A site texture, where published, is replicated over the 10 texture input
  layers as a PROXY; grid-fallback sites keep the template layers unchanged.
- Technical first-five-year AD spin-up test, not a convergence validation.
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path

REPO=Path(__file__).resolve().parents[3]
BASE=Path("/iridisfs/scratch/ly3n24/CLM_FATES")
CTSM=BASE/"CTSM"
CIMESCRIPTS=CTSM/"cime/scripts"
PFT_CSV=REPO/"data/batch03_10_pft_scenarios.csv"
SOIL_DECISION=REPO/"data/batch03_10_soil_input_decisions.csv"
SITES_CSV=REPO/"data/batch03_10_sites.csv"
PARAM=CTSM/"src/fates/parameter_files/fates_params_default.json"
OUTPUTS=Path("/scratch/ly3n24/CTSM_FATES_OUTPUTS")
OUT_BASE=BASE/"experiments/NonCompetitionObserved22/Batch03_10"
SITE_TAG="B03"
SLURM_USER="ly3n24"
SITE_ORDER=("IT-Lav","FI-Let","IL-Yat","DE-Obe","CZ-Stn",
            "DE-Lnf","DE-Hzd","GF-Guy","AT-Neu","CH-Cha")
# Existing, already built original FATES cases (read-only templates for
# create_clone --keepexe). Names match the six/eight/eleven/thirteen-site
# campaigns in lyanyeung/CLM-FATES-single-site-workflows.
OLD_CASES={
 "IT-Lav":"IT-Lav_FATES_SPINUP500",
 "FI-Let":"FI-Let_FATES_SPINUP1000_S30SHARED",
 "IL-Yat":"IL-Yat_FATES_SPINUP500",
 "DE-Obe":"DE-Obe_FATES_SPINUP1000_S30SHARED",
 "CZ-Stn":"CZ-Stn_FATES_SPINUP500_11P",
 "DE-Lnf":"DE-Lnf_FATES_SPINUP1000_S30SHARED",
 "DE-Hzd":"DE-Hzd_FATES_SPINUP500",
 "GF-Guy":"GF-Guy_FATES_SPINUP1000_S30SHARED",
 "AT-Neu":"AT-Neu_FATES_SPINUP500_11P",
 "CH-Cha":"CH-Cha_FATES_SPINUP500_11P",
}
# HLM natpft indices (index0 bare): 1 NET temperate, 3 NDT boreal,
# 4 BET tropical, 5 BET temperate, 7 BDT temperate, 13 C3 non-arctic grass.
PFT_IDX={"ENF":1,"DNF":3,"EBF_TROP":4,"EBF":5,"DBF":7,"C3_GRASS":13}
PFT_EXPECT={
 "ENF":"needleleaf_evergreen_extratrop_tree",
 "DNF":"needleleaf_colddecid_extratrop_tree",
 "EBF_TROP":"broadleaf_evergreen_tropical_tree",
 "EBF":"broadleaf_evergreen_extratrop_tree",
 "DBF":"broadleaf_colddecid_extratrop_tree",
 "C3_GRASS":"cool_c3_grass",
}
NATPFT=15
SOIL_LAYERS=10
SOIL_LITERATURE="SITE_LITERATURE_UNIFORM_10_LAYER_PROXY"
SOIL_GRID="SOIL_TEXTURE_GRID_FALLBACK"
LAND_OTHER=("PCT_LAKE","PCT_WETLAND","PCT_GLACIER","PCT_URBAN")
BGC_OPTS="--bgc fates --no-megan --no-drydep --no-fire_emis"
ACK_SUBMIT="SUBMIT_BATCH03_TEN_FIRST_FIVE_YEAR_AD_SMOKES"
HISTORY=("TOTSOMC","TOTSOMN","TLAI","FATES_GPP","FATES_NPP","TWS","H2OSNO")
RUN_RE=re.compile(r"Submitted job case\.run with id (\d+)")
ARCH_RE=re.compile(r"Submitted job case\.st_archive with id (\d+)")


def fail(s):
    raise RuntimeError(str(s))


def read_csv(p):
    with p.open(newline="",encoding="utf-8-sig") as f:
        return {r["site"]:r for r in csv.DictReader(f)}


def digest(path):
    h=hashlib.sha256()
    with path.open("rb") as f:
        for x in iter(lambda:f.read(1<<20),b""):
            h.update(x)
    return h.hexdigest()


def case_name(site):
    return f"{site}_{SITE_TAG}_FIXNC_AD400"


def case_path(site):
    return BASE/"cases"/case_name(site)


def template_case(site):
    return BASE/"cases"/OLD_CASES[site]


def surface(site):
    return OUT_BASE/site/"surface"/f"surfdata_{site}_{SITE_TAG}_FIXNC_AD400_v1.nc"


def receipt(site):
    return surface(site).with_suffix(".json")


def run_path(site):
    return OUTPUTS/case_name(site)/"run"


def archive_path(site):
    return OUTPUTS/"archive"/case_name(site)


def ledger_path(site):
    return OUT_BASE/site/"AD400_case_state.json"


def cmd(argv,cwd=None,timeout=300):
    p=subprocess.run([str(x) for x in argv],cwd=cwd,
                     text=True,stdout=subprocess.PIPE,
                     stderr=subprocess.STDOUT,timeout=timeout)
    if p.returncode!=0:
        fail("FAILED "+str(argv)+"\n"+p.stdout[-3200:])
    return p.stdout


def xmlquery(case,key):
    return cmd(["./xmlquery",key,"--value"],cwd=case,timeout=90).strip()


def nml_set(text,key,value):
    pattern=r"(?im)^[ \t]*"+re.escape(key)+r"[ \t]*=[^\r\n]*$"
    matches=list(re.finditer(pattern,text))
    if len(matches)>1:
        fail("Duplicated namelist key "+key)
    repl=key+" = "+value
    return ((text[:matches[0].start()]+repl+text[matches[0].end():])
            if matches else text.rstrip()+"\n"+repl+"\n")


def nml_get(text,key):
    found=re.findall(r"(?im)^\s*"+re.escape(key)+r"\s*=\s*([^\r\n!]*)",text)
    if len(found)>1:
        fail("Ambiguous "+key)
    return found[0].strip().strip("'\"").strip() if found else None


def original(site):
    """Source point surface actually used by the built template case."""
    lnd=template_case(site)/"CaseDocs/lnd_in"
    if not lnd.is_file():
        fail(site+": template case has no CaseDocs/lnd_in: "+str(lnd))
    value=nml_get(lnd.read_text(errors="replace"),"fsurdat")
    if not value:
        fail(site+": template lnd_in has no fsurdat")
    src=Path(value)
    if not src.name.startswith(f"surfdata_{site}_") or src.suffix!=".nc":
        fail(site+": template fsurdat is not a site point surface: "+value)
    if "_B0" in src.name or "FIXNC" in src.name:
        fail(site+": template already points to a FIXNC surface; refuse: "+value)
    return src


def mix(site):
    vals=read_csv(PFT_CSV).get(site)
    if vals is None:
        fail("Missing station PFT "+site)
    shares={k:float(vals[k]) for k in PFT_IDX}
    if abs(sum(shares.values())-100)>1e-6 or any(v<0 for v in shares.values()):
        fail("Invalid PFT composition "+site)
    return shares


def soil_choice(site):
    d=read_csv(SOIL_DECISION).get(site)
    if d is None:
        fail("Missing soil decision "+site)
    mode=d["soil_texture_decision"]
    if mode==SOIL_GRID:
        return {"mode":SOIL_GRID,"note":d["decision_note"],
                "attempted_sources":d["attempted_sources_25Oct2026"],
                "observed":False}
    if mode!=SOIL_LITERATURE:
        fail(site+": unsupported soil decision "+mode)
    sand,silt,clay=(float(d[k+"_pct_reported"]) for k in ("sand","silt","clay"))
    total=sand+silt+clay
    if total<=0 or min(sand,silt,clay)<0:
        fail("Invalid texture "+site)
    return {"mode":SOIL_LITERATURE,
            "sand":100*sand/total,"silt":100*silt/total,"clay":100*clay/total,
            "published_sand_silt_clay":[sand,silt,clay],
            "published_total":total,"source":d["source"],
            "depth_scope":d["depth_scope"],"note":d["decision_note"],
            "vertical_assumption":"same representative texture used at each of 10 model input layers; not independently measured at depth"}


def fates_map():
    data=json.loads(PARAM.read_text(encoding="utf8"))["parameters"]
    names=data["fates_pftname"]["data"]
    import numpy as np
    m=np.asarray(data["fates_hlm_pft_map"]["data"],dtype=float)
    if m.shape[0]<max(PFT_IDX.values()):
        fail("FATES HLM mapping too short")
    table={}
    for cls,idx in PFT_IDX.items():
        row=m[idx-1]
        table[cls]=[str(names[int(i)]).strip() for i in np.flatnonzero(row>0)]
    return table


def expected_map(site,table):
    for cls,value in mix(site).items():
        if value and table[cls]!=[PFT_EXPECT[cls]]:
            fail(f"{site} incompatible host-FATES mapping {cls}: {table[cls]}")
    return True


def target_pft(site):
    import numpy as np
    target=np.zeros(NATPFT)
    for cl,p in mix(site).items():
        target[PFT_IDX[cl]]=p
    return target


def validate_surface(site,path,source=None):
    import numpy as np
    from netCDF4 import Dataset
    with Dataset(str(path),"r") as ds:
        for k,val in (("PCT_NATVEG",100.),("PCT_CROP",0.)):
            a=np.ma.filled(ds.variables[k][:],np.nan)
            if a.size!=1 or not np.isclose(float(a.ravel()[0]),val,atol=1e-4):
                fail(site+" wrong "+k)
        for field in LAND_OTHER:
            if field in ds.variables:
                a=np.ma.filled(ds.variables[field][:],np.nan)
                if not np.isfinite(a).all() or not np.allclose(a,0,atol=1e-4):
                    fail(site+" landunit nonzero "+field)
        arr=np.ma.filled(ds.variables["PCT_NAT_PFT"][:],np.nan).ravel()
        if arr.size!=NATPFT or not np.allclose(arr,target_pft(site),atol=1e-4):
            fail(site+" wrong PFT shares")
        choice=soil_choice(site)
        got={}
        for key in ("PCT_SAND","PCT_CLAY"):
            a=np.ma.filled(ds.variables[key][:],np.nan)
            if a.size!=SOIL_LAYERS or not np.isfinite(a).all():
                fail(site+" missing 10 soil texture layers "+key)
            got[key]=a
            if choice["mode"]==SOIL_LITERATURE:
                wanted=choice["sand"] if key=="PCT_SAND" else choice["clay"]
                if not np.allclose(a,wanted,atol=1e-4):
                    fail(site+" wrong texture "+key)
    if choice["mode"]==SOIL_GRID and source is not None:
        with Dataset(str(source),"r") as ds:
            for key in ("PCT_SAND","PCT_CLAY"):
                if not np.array_equal(np.ma.filled(ds.variables[key][:],np.nan),got[key]):
                    fail(site+" grid-fallback texture differs from source "+key)


def plan():
    table=fates_map()
    print("BATCH03 TEN-SITE AD400: UNIFIED SCIENTIFIC INPUT PLAN")
    print("FATES HLM PFT MAPPING:",table)
    for site in SITE_ORDER:
        expected_map(site,table)
        c=template_case(site)
        try:
            src=original(site)
            schema="OK" if src.is_file() and not src.is_symlink() else "MISSING"
        except Exception as exc:
            src,schema=None,"HOLD("+str(exc)[-120:]+")"
        choice=soil_choice(site)
        used={k:v for k,v in mix(site).items() if v}
        print(f"{site:7} PFT={used} soil={choice['mode']}"
              f" sand={choice.get('sand','GRID')} clay={choice.get('clay','GRID')}"
              f" template={'OK' if c.is_dir() else 'MISSING'}"
              f" fsurdat={src} schema={schema}")
    print("No forcing file rechecks. First AD segment 5 years only.")
    print("No CIME/NetCDF/Slurm writes in 'plan'.")


def one_surface(site):
    import numpy as np
    from netCDF4 import Dataset
    src=original(site)
    dst=surface(site)
    rec=receipt(site)
    if dst.exists() or dst.is_symlink() or rec.exists():
        if dst.is_file() and rec.is_file():
            saved=json.loads(rec.read_text())
            if saved.get("surface_sha256")==digest(dst):
                validate_surface(site,dst)
                print(site,"SURFACE EXISTS VERIFIED; no overwrite")
                return
        fail("Existing surface or receipt cannot be safely overwritten: "+str(dst))
    if not src.is_file() or src.is_symlink():
        fail("Original schema not present or is a symlink "+str(src))
    table=fates_map()
    expected_map(site,table)
    choice=soil_choice(site)
    dst.parent.mkdir(parents=True,exist_ok=True)
    fd,temp=tempfile.mkstemp(prefix="."+site+"-",suffix=".nc",dir=dst.parent)
    os.close(fd)
    tmp=Path(temp)
    original_sha=digest(src)
    try:
        shutil.copyfile(src,tmp)
        with Dataset(str(tmp),"r+") as ds:
            for name,target in (("PCT_NATVEG",100.),("PCT_CROP",0.)):
                if ds.variables[name].size!=1:
                    fail("Not a point landunit "+name)
                ds.variables[name][:]=target
            for name in LAND_OTHER:
                if name in ds.variables:
                    ds.variables[name][:]=0.
            v=ds.variables["PCT_NAT_PFT"]
            if v.size!=NATPFT or "natpft" not in v.dimensions:
                fail("Unexpected CLM PFT layout "+site)
            vals=np.zeros(v.shape)
            axis=v.dimensions.index("natpft")
            for cl,pct in mix(site).items():
                sl=[0]*vals.ndim
                sl[axis]=PFT_IDX[cl]
                vals[tuple(sl)]=pct
            v[:]=vals
            for key in ("PCT_SAND","PCT_CLAY"):
                v=ds.variables[key]
                if v.size!=SOIL_LAYERS:
                    fail("Expected exactly ten texture input layers "+site+" "+key)
                if choice["mode"]==SOIL_LITERATURE:
                    v[:]=(choice["sand"] if key=="PCT_SAND" else choice["clay"])
        validate_surface(site,tmp,source=src)
        if digest(src)!=original_sha:
            fail("Source surface modified during build; STOP")
        res={
            "site":site,"source":str(src),"source_sha256":original_sha,
            "source_discovered_from":str(template_case(site)/"CaseDocs/lnd_in"),
            "surface":str(dst),"surface_sha256":digest(tmp),
            "case_template":OLD_CASES[site],
            "site_pft_pct":{k:v for k,v in mix(site).items() if v},
            "soil_selection":choice,
            "point_assumption":{"PCT_NATVEG":100,"PCT_CROP":0},
            "fates_hlm_map":{cl:table[cl] for cl in PFT_IDX},
            "unchanged_fields":"Inherited as binary surface schema; not site-observed evidence",
            "source_files_modified":False,"CIME_cases_created":False,
            "Slurm_submitted":False,
            "created_utc":datetime.now(timezone.utc).isoformat()
        }
        os.link(tmp,dst)
        with rec.open("x",encoding="utf8") as file:
            json.dump(res,file,indent=2,ensure_ascii=False)
            file.write("\n")
        print(site,"SURFACE CREATED",dst)
    finally:
        if tmp.exists():
            tmp.unlink()


def old_executable(site):
    orig=template_case(site)
    if not orig.is_dir():
        fail("Missing original CIME case: "+str(orig))
    if xmlquery(orig,"BUILD_COMPLETE").lower()!="true":
        fail("Original case not BUILT; cannot reuse executable: "+str(orig))
    exe=Path(xmlquery(orig,"EXEROOT"))/"cesm.exe"
    if not exe.is_file():
        fail("Missing original executable: "+str(exe))
    return orig,exe


def case_settings(site):
    original_case,_=old_executable(site)
    start=xmlquery(original_case,"RUN_STARTDATE")
    if not re.fullmatch(r"\d{4}-01-01",start):
        fail(site+": template RUN_STARTDATE is not Jan-01: "+start)
    return {
        "RUN_TYPE":"startup",
        "RUN_STARTDATE":start,
        "CONTINUE_RUN":"FALSE",
        "CLM_FORCE_COLDSTART":"on",
        "CLM_ACCELERATED_SPINUP":"on",
        "CLM_BLDNML_OPTS":BGC_OPTS,
        "STOP_OPTION":"nyears","STOP_N":"5",
        "REST_OPTION":"nyears","REST_N":"5",
        "RESUBMIT":"0","DOUT_S":"TRUE",
        "RUNDIR":str(run_path(site)),
        "DOUT_S_ROOT":str(archive_path(site)),
        "MPI_RUN_COMMAND":"srun --mpi=pmix --ntasks=1 --cpus-per-task=1 --cpu-bind=cores",
    }


def desired_namelist(site):
    return {
        "fsurdat":"'"+str(surface(site))+"'",
        "use_fates":".true.",
        "use_fates_sp":".false.",
        "use_fates_fixed_biogeog":".true.",
        "use_fates_nocomp":".true.",
        "spinup_state":"2",
        "hist_fincl1":",".join("'"+x+"'" for x in HISTORY)
    }


def dispatch(name,method):
    problems=[]
    for site in SITE_ORDER:
        try:
            method(site)
        except Exception as exc:
            print(site,"ERROR",str(exc)[-900:],flush=True)
            problems.append((site,str(exc)[-400:]))
    print(name.upper(),"SUMMARY success=",len(SITE_ORDER)-len(problems),
          "issues=",len(problems))
    if problems:
        for s,detail in problems:
            print("HOLD",s,detail)
        raise SystemExit(2)


def parse_job_ids(out):
    r=RUN_RE.search(out)
    a=ARCH_RE.search(out)
    return (r.group(1) if r else None),(a.group(1) if a else None)


def all_submit(ack):
    if ack!=ACK_SUBMIT:
        fail("submit-smoke requires --confirm "+ACK_SUBMIT)
    records={}
    for site in SITE_ORDER:
        state=ledger_path(site)
        if not state.is_file():
            fail("Do not submit incomplete batch: ledger missing "+site)
        obj=json.loads(state.read_text())
        if obj.get("phase")!="PREPARED_NOT_SUBMITTED":
            fail("Submission already attempted for "+site+"; no duplicate attempts")
        if not obj.get("CIME_env_case_lock_restored") or not obj.get("private_overlay"):
            fail("Missing private-overlay AD recovery receipt "+site)
        case=case_path(site)
        if not case.is_dir():
            fail("Case absent "+site)
        if digest(surface(site))!=obj["surface_sha256"]:
            fail("Surface changed "+site)
        if xmlquery(case,"RESUBMIT")!="0":
            fail("Case resubmit setting changed "+site)
        if xmlquery(case,"STOP_N")!="5":
            fail("Case stop changed "+site)
        if xmlquery(case,"CLM_ACCELERATED_SPINUP").lower()!="on":
            fail("Case not AD "+site)
        if xmlquery(case,"CLM_BLDNML_OPTS").split()!=BGC_OPTS.split():
            fail("Case does not use FATES BGC options "+site)
        lnd=case/"CaseDocs/lnd_in"
        if not lnd.is_file():
            fail("Generated effective CLM namelist missing "+site)
        nml=lnd.read_text()
        for key,value in desired_namelist(site).items():
            if key=="hist_fincl1":
                continue
            if nml_get(nml,key)!=value.strip("'\\\""):
                fail("AD5 generated namelist mismatch "+site+" "+key)
        records[site]=obj
    queue=cmd(["squeue","-u",SLURM_USER,"-h","-o","%j"],timeout=35)
    for site in SITE_ORDER:
        if any(case_name(site) in line for line in queue.splitlines()):
            fail("A matching job is already in queue; STOP "+site)
    print("ALL TEN STAGED. SUBMITTING EXACTLY ONE 5-YEAR AD SMOKE PER SITE.")
    failed=[]
    for site in SITE_ORDER:
        ledger=ledger_path(site)
        obj=records[site]
        obj["phase"]="SUBMISSION_ATTEMPTED_UNCERTAIN"
        obj["attempt_utc"]=datetime.now(timezone.utc).isoformat()
        ledger.write_text(json.dumps(obj,indent=2)+"\n")
        try:
            out=cmd([case_path(site)/"case.submit","--skip-preview-namelist"],
                    cwd=case_path(site),timeout=360)
            runid,archid=parse_job_ids(out)
            obj["phase"]="FIRST_5Y_SUBMITTED"
            obj["cime_submit_output_tail"]=out[-850:]
            obj["AD5_run_job"]=runid
            obj["AD5_archive_job"]=archid
            ledger.write_text(json.dumps(obj,indent=2)+"\n")
            print(site,"SUBMITTED FIRST 5 AD YEARS ONLY run=",runid,"archive=",archid)
            if not runid or not archid:
                print(site,"WARNING: job IDs not parsed; record them in the ledger by hand before Stage13")
        except Exception as err:
            print(site,"SUBMISSION UNCERTAIN; inspect squeue and CaseStatus",str(err)[-800:])
            failed.append(site)
    print("SUBMISSION SUMMARY submitted=",len(SITE_ORDER)-len(failed),
          "uncertain=",failed)
    if failed:
        raise SystemExit(3)
    print("10 x AD5 only. AD395 NOT AUTO-SUBMITTED. Check run+archive success.")


def status():
    try:
        queue=cmd(["squeue","-u",SLURM_USER,"-h","-o","%j|%T|%i"],timeout=35)
    except Exception as exc:
        queue="scheduler unavailable "+str(exc)
    for site in SITE_ORDER:
        state=ledger_path(site)
        obj=json.loads(state.read_text()) if state.is_file() else {}
        jobs=[ln for ln in queue.splitlines() if case_name(site) in ln]
        print(f"{site:7} SURF={surface(site).exists()} "
              f"CASE={case_path(site).is_dir()} "
              f"PHASE={obj.get('phase','NOT_STAGED')} "
              f"AD5={obj.get('AD5_run_job','-')}/{obj.get('AD5_archive_job','-')} "
              f"QUEUE={'; '.join(jobs) or '-'}")


def self_test():
    """Parse the repository's ten-site CSVs and namelist helpers (no HPC)."""
    import codecs
    codecs.lookup("utf-8-sig")
    assert BGC_OPTS=="--bgc fates --no-megan --no-drydep --no-fire_emis"
    pt=read_csv(PFT_CSV)
    d=read_csv(SOIL_DECISION)
    s=read_csv(SITES_CSV)
    for name,table in (("PFT",pt),("soil",d),("site register",s)):
        assert set(table)==set(SITE_ORDER), name+" site IDs mismatch"
    assert set(OLD_CASES)==set(SITE_ORDER)
    for site in SITE_ORDER:
        assert s[site]["template_case"]==OLD_CASES[site], site
        sh=mix(site)
        assert abs(sum(sh.values())-100)<1e-9, site
        x=soil_choice(site)
        if x["mode"]==SOIL_LITERATURE:
            assert abs(x["sand"]+x["silt"]+x["clay"]-100)<1e-8,site
        for name in ("use_fates","use_fates_sp","use_fates_nocomp",
                     "use_fates_fixed_biogeog","spinup_state"):
            assert name in desired_namelist(site), (site,name)
        assert case_name(site).endswith("_B03_FIXNC_AD400")
    assert nml_get("use_fates_nocomp = .true.\n","use_fates_nocomp")==".true."
    assert nml_set("use_fates = .false.\n","use_fates",".true.").strip()=="use_fates = .true."
    sample=("Submitted job case.run with id 4800001\n"
            "Submitted job case.st_archive with id 4800002\n")
    assert parse_job_ids(sample)==("4800001","4800002")
    print("SELF-TEST PASS | 10 station PFT/soil/site CSVs and CIME namelist helpers")
    print("NO netCDF writes, no CIME case creation, no Slurm jobs.")


def main():
    parser=argparse.ArgumentParser(description=__doc__,
                                   formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("action",choices=("self-test","plan","surfaces","submit-smoke","status"))
    parser.add_argument("--confirm",default="")
    args=parser.parse_args()
    if args.action=="self-test":
        self_test()
    elif args.action=="plan":
        plan()
    elif args.action=="surfaces":
        dispatch("surfaces",one_surface)
    elif args.action=="submit-smoke":
        all_submit(args.confirm)
    else:
        status()


if __name__=="__main__":
    main()
