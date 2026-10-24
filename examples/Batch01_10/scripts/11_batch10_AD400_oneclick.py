#!/usr/bin/env python3
"""Batch01 10-site fixed-biogeography/no-competition AD400 launcher.

Reuses the working DE-Tha 'create_clone --keepexe' / new fsurdat / CIME
preview / first-5-year submit workflow. DOES NOT re-audit 22 forcing files.
The ten original DATM streams, CO2 policy, model EXEROOT and site machine
settings are inherited without altering original files.

Actions:
  plan            show choices; never writes model inputs
  surfaces        create 10 versioned independent site surface NetCDFs
  stage           create 10 independent cold-start AD400 CIME cases (no jobs)
  submit-smoke    submit 10 x FIRST FIVE YEARS ONLY, then STOP
  status          summarize 10 case paths and scheduler jobs (read only)

Always run 'surfaces' before 'stage', 'stage' before 'submit-smoke'.
Every action is idempotence-safe: never overwrite an existing target,
never submit duplicate case jobs. Each site is handled separately and
failures are reported at the end (other sites continue during surfaces/stage).

Scientific modeling assumptions:
- 100% NATVEG, zero crop/other landunits, forest PFT fractions from Batch01 CSV.
- A single most applicable published/mineral topsoil texture is replicated as
  a **uniform 10 texture input-layer PROXY**, NOT ten observed soil samples.
- RU-Fyo alone retains old point-surface PCT_SAND/PCT_CLAY layer by layer;
  this does NOT scientifically resolve its peat/organic layer treatment.
- All unchanged non-forest soil/terrain fields remain schema/template values.
- This is a technical first-five-year spin-up test, not a validation of
  ecosystem carbon equilibrium.
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

import numpy as np
from netCDF4 import Dataset

REPO=Path(__file__).resolve().parents[3]
BASE=Path("/iridisfs/scratch/ly3n24/CLM_FATES")
CTSM=BASE/"CTSM"
CIMESCRIPTS=CTSM/"cime/scripts"
PFT_CSV=REPO/"data/batch01_10_pft_scenarios.csv"
S4_CSV=REPO/"data/batch01_10_Flechard2020_TableS4_soil.csv"
SOIL_DECISION=REPO/"data/batch01_10_soil_input_decisions.csv"
PARAM=CTSM/"src/fates/parameter_files/fates_params_default.json"
OUTPUTS=Path("/scratch/ly3n24/CTSM_FATES_OUTPUTS")
OUT_BASE=BASE/"experiments/NonCompetitionObserved22/Batch01_10"
SITE_ORDER=("CZ-BK1","IT-Ren","RU-Fyo","CH-Dav","IT-Col",
            "FR-Fon","FI-Sod","FR-Pue","DE-Hai","BE-Vie")
# Actual original cases/surface dates are from the completed Stage02 inventory.
OLD_CASES={
 "CZ-BK1":"CZ-BK1_FATES_SPINUP500",
 "IT-Ren":"IT-Ren_FATES_SPINUP500",
 "RU-Fyo":"RU-Fyo_FATES_SPINUP500",
 "CH-Dav":"CH-Dav_FATES_SPINUP500",
 "IT-Col":"IT-Col_FATES_SPINUP1000_S30SHARED",
 "FR-Fon":"FR-Fon_FATES_SPINUP500_11P",
 "FI-Sod":"FI-Sod_FATES_SPINUP500_11P",
 "FR-Pue":"FR-Pue_FATES_SPINUP1000_S30SHARED",
 "DE-Hai":"DE-Hai_FATES_SPINUP500",
 "BE-Vie":"BE-Vie_FATES_SPINUP500",
}
SOURCE_DATES={
 "CZ-BK1":"261012","IT-Ren":"261012","RU-Fyo":"261011",
 "CH-Dav":"261012","IT-Col":"261014","FR-Fon":"261014",
 "FI-Sod":"261014","FR-Pue":"261014","DE-Hai":"261011",
 "BE-Vie":"261012",
}
# HLM natpft indices: CLM index0 is bare; index1 ENF, 3 DNF,
# index5 EBF, index7 DBF, as in the existing DE-Tha and NL-Loo examples.
PFT_IDX={"ENF":1,"DNF":3,"EBF":5,"DBF":7}
PFT_EXPECT={
 "ENF":"needleleaf_evergreen_extratrop_tree",
 "DNF":"needleleaf_colddecid_extratrop_tree",
 "EBF":"broadleaf_evergreen_extratrop_tree",
 "DBF":"broadleaf_colddecid_extratrop_tree",
}
# Chosen representative first mineral horizon where known; site-level proxy
# otherwise. Sand, silt, clay percentages; totals 99/101 are normalized.
SOIL={
 "CZ-BK1":(22,58,21,"Flechard2020 S4 station texture; horizon unknown; soil depth 0.55m"),
 "IT-Ren":(55,34,11,"Flechard2020 S4 Haplic Podzol site aggregate"),
 "CH-Dav":(53,25,22,"Meredith2018 Table3 upper 0-10cm mineral soil"),
 "IT-Col":(8,32,59,"Flechard2020 S4 site aggregate; conflicts with Chiesi2018; choice recorded"),
 "FR-Fon":(41.9,38.8,19.3,"Barbeau same-tower upper mineral soil; exact horizon unspecified"),
 "FI-Sod":(88.12,6.0,0.5,"FLUXNET station 0-10cm; stones 5.4% excluded through fine-earth normalization"),
 "FR-Pue":(26,32,42,"Meredith2018 upper 0-10cm; very stony site; rock physics inherited as proxy"),
 "DE-Hai":(4,49,48,"Meredith2018 upper 0-10cm; reported sum 101 due to rounding"),
 "BE-Vie":(27,55,18,"Buysse2013 Vielsalm site texture; depth unspecified"),
}
LAND_OTHER=("PCT_LAKE","PCT_WETLAND","PCT_GLACIER","PCT_URBAN")
ACK_STAGE="CREATE_TEN_INDEPENDENT_BATCH01_AD400_CASES"
ACK_SUBMIT="SUBMIT_BATCH01_TEN_FIRST_FIVE_YEAR_AD_SMOKES"
HISTORY=("TOTSOMC","TOTSOMN","TLAI","FATES_GPP","FATES_NPP","TWS","H2OSNO")


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


def original(site):
    return (BASE/"sites/MY_EC_SITE"/site/"subset_data"/
            f"surfdata_{site}_hist_2000_16pfts_c{SOURCE_DATES[site]}.nc")


def surface(site):
    return (OUT_BASE/site/"surface"/
            f"surfdata_{site}_B01_FIXNC_AD400_v1.nc")


def receipt(site):
    return surface(site).with_suffix(".json")


def case_name(site):
    return site+"_B01_FIXNC_AD400"


def case_path(site):
    return BASE/"cases"/case_name(site)


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


def mix(site):
    vals=read_csv(PFT_CSV).get(site)
    if vals is None:
        fail("Missing station PFT "+site)
    shares={k:float(vals[k]) for k in PFT_IDX}
    if abs(sum(shares.values())-100)>1e-6 or any(v<0 for v in shares.values()):
        fail("Invalid forest composition "+site)
    return shares


def soil_choice(site):
    if site=="RU-Fyo":
        d=read_csv(SOIL_DECISION)["RU-Fyo"]
        if d["soil_texture_decision"]!="ORIGINAL_FSURDAT_TEXTURE_OPERATOR_EXCEPTION":
            fail("RU soil exception is no longer selected")
        return {"mode":"INHERITED_ORIGINAL_PCT_SAND_CLAY_LAYERS_ONLY",
                "note":"NOT observational peat texture"}
    sand,silt,clay,note=SOIL[site]
    total=sand+silt+clay
    if total<=0:
        fail("Invalid texture "+site)
    if site=="CZ-BK1":
        d=read_csv(SOIL_DECISION)["CZ-BK1"]
        s4=read_csv(S4_CSV)["CZ-BK1"]
        if d["soil_texture_decision"]!="FLECHARD2020_S4_STATION_TEXTURE_SELECTED":
            fail("CZ soil decision changed")
        if tuple(float(s4[k+"_pct_reported"]) for k in ("sand","silt","clay"))!=(22.,58.,21.):
            fail("CZ source literature changed")
    return {"mode":"SITE_LITERATURE_UNIFORM_10_LAYER_PROXY",
            "sand":100*sand/total,"silt":100*silt/total,
            "clay":100*clay/total,
            "published_sand_silt_clay": [sand,silt,clay],
            "published_total":total,
            "note":note,
            "vertical_assumption":"same representative texture used at each of 10 model input layers; not independently measured at depth"}


def fates_map():
    data=json.loads(PARAM.read_text(encoding="utf8"))["parameters"]
    names=data["fates_pftname"]["data"]
    m=np.asarray(data["fates_hlm_pft_map"]["data"],dtype=float)
    if m.shape[0]<max(PFT_IDX.values()):
        fail("FATES HLM mapping too short")
    table={}
    for cls,idx in PFT_IDX.items():
        row=m[idx-1]
        pos=np.flatnonzero(row>0)
        mapped=[names[int(i)] for i in pos]
        table[cls]=mapped
    return table


def expected_map(site,table):
    for cls,value in mix(site).items():
        if not value:
            continue
        if table[cls]!=[PFT_EXPECT[cls]]:
            fail(f"{site} incompatible host-FATES mapping {cls}: {table[cls]}")
    return True


def validate_surface(site,path):
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
        target=np.zeros(15)
        for cl,p in mix(site).items():
            target[PFT_IDX[cl]]=p
        if arr.size!=15 or not np.allclose(arr,target,atol=1e-4):
            fail(site+" wrong PFT shares")
        choice=soil_choice(site)
        for key in ("PCT_SAND","PCT_CLAY"):
            a=np.ma.filled(ds.variables[key][:],np.nan)
            if a.size!=10 or not np.isfinite(a).all():
                fail(site+" missing 10 soil texture layers "+key)
            if choice["mode"]!="INHERITED_ORIGINAL_PCT_SAND_CLAY_LAYERS_ONLY":
                wanted=choice["sand"] if key=="PCT_SAND" else choice["clay"]
                if not np.allclose(a,wanted,atol=1e-4):
                    fail(site+" wrong texture "+key)


def plan():
    table=fates_map()
    print("BATCH01 TEN-SITE AD400: UNIFIED SCIENTIFIC INPUT PLAN")
    print("FATES HLM PFT MAPPING:",table)
    for site in SITE_ORDER:
        expected_map(site,table)
        p=original(site)
        c=BASE/"cases"/OLD_CASES[site]
        choice=soil_choice(site)
        print(f"{site:7} PFT={mix(site)} soil={choice['mode']}"
              f" sand={choice.get('sand','RU_SOURCE')}"
              f" clay={choice.get('clay','RU_SOURCE')}"
              f" oldCase={'OK' if c.is_dir() else 'MISSING'}"
              f" schema={'OK' if p.is_file() else 'MISSING'}")
    print("No old forcing file rechecks. First AD segment 5 years only.")
    print("No CIME/NetCDF/Slurm writes in 'plan'.")


def one_surface(site):
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
        fail("Original schema not present "+str(src))
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
            if v.size!=15 or "natpft" not in v.dimensions:
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
                if v.size!=10:
                    fail("Expected exactly ten texture input layers "+site+" "+key)
                if choice["mode"]!="INHERITED_ORIGINAL_PCT_SAND_CLAY_LAYERS_ONLY":
                    v[:]=(choice["sand"] if key=="PCT_SAND" else choice["clay"])
        validate_surface(site,tmp)
        if digest(src)!=original_sha:
            fail("Source surface modified during build; STOP")
        res={
            "site":site,"source":str(src),"source_sha256":original_sha,
            "surface":str(dst),"surface_sha256":digest(tmp),
            "case_template":OLD_CASES[site],
            "site_tree_pft_pct":mix(site),
            "soil_selection":choice,
            "forest_point_assumption":{"PCT_NATVEG":100,"PCT_CROP":0},
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


def all_surfaces():
    dispatch("surfaces",one_surface)


def old_executable(site):
    orig=BASE/"cases"/OLD_CASES[site]
    if not orig.is_dir():
        fail("Missing original CIME case: "+str(orig))
    if xmlquery(orig,"BUILD_COMPLETE").lower()!="true":
        fail("Original case not BUILT; cannot reuse executable: "+str(orig))
    root=Path(xmlquery(orig,"EXEROOT"))
    exe=root/"cesm.exe"
    if not exe.is_file():
        fail("Missing original executable: "+str(exe))
    return orig,exe


def case_settings(site):
    original_case,_=old_executable(site)
    return {
        "RUN_TYPE":"startup",
        "RUN_STARTDATE":xmlquery(original_case,"RUN_STARTDATE"),
        "CONTINUE_RUN":"FALSE",
        "CLM_FORCE_COLDSTART":"on",
        "CLM_ACCELERATED_SPINUP":"on",
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


def single_case(site):
    surf=surface(site)
    rec=receipt(site)
    if not surf.is_file() or not rec.is_file():
        fail("Run 'surfaces' first for "+site)
    saved=json.loads(rec.read_text())
    if saved.get("surface_sha256")!=digest(surf):
        fail("Surface digest does not match receipt "+site)
    validate_surface(site,surf)
    case=case_path(site)
    ledger=ledger_path(site)
    if case.exists() or ledger.exists():
        if case.is_dir() and ledger.is_file():
            print(site,"CASE EXISTS: skip creation; run 'status' / inspect if needed")
            return
        fail("Partial case/ledger present: manual resolution "+site)
    orig,exe=old_executable(site)
    if run_path(site).exists() or archive_path(site).exists():
        fail("Run/archive destination already exists "+site)
    print(site,"CLONING existing case/executable; not building a new CTSM")
    cmd([CIMESCRIPTS/"create_clone","--case",case,"--clone",orig,"--keepexe"],
        cwd=CIMESCRIPTS,timeout=420)
    if not case.is_dir():
        fail("Clone command returned but CIME case missing "+site)
    settings=case_settings(site)
    # Use the same single-key CIME xmlchange pattern as the successful DE-Tha AD case.
    for key,value in settings.items():
        cmd([case/"xmlchange",key+"="+value],cwd=case,timeout=90)
    nl=case/"user_nl_clm"
    if not nl.is_file():
        fail("Cloned user_nl_clm missing "+site)
    txt=nl.read_text()
    if nml_get(txt,"finidat") not in (None,""):
        fail("Inherited finidat must be removed explicitly, not blindly cloned: "+site)
    if nml_get(txt,"reseed_dead_plants") is not None:
        fail("CN-only reseed_dead_plants in copied source case "+site)
    for k,v in desired_namelist(site).items():
        txt=nml_set(txt,k,v)
    nl.write_text(txt,encoding="utf8")
    if not (case/".case.run").is_file():
        cmd([case/"case.setup"],cwd=case,timeout=300)
    cmd([case/"preview_namelists"],cwd=case,timeout=480)
    generated=case/"CaseDocs/lnd_in"
    if not generated.is_file():
        fail("preview_namelists created no CaseDocs/lnd_in "+site)
    text=generated.read_text()
    for k,v in desired_namelist(site).items():
        if k=="hist_fincl1":
            continue
        expected=v.strip("'\"")
        got=nml_get(text,k)
        if got!=expected:
            fail(f"{site}: generated {k}={got}, expected {expected}")
    if nml_get(text,"use_cn") not in (".false.","false"):
        fail("CIME generated non-FATES use_cn "+site)
    if nml_get(text,"finidat") not in (None,""):
        fail("CIME generated nonempty finidat "+site)
    run_lnd=run_path(site)/"lnd_in"
    if not run_lnd.is_file() or digest(run_lnd)!=digest(generated):
        fail("Generated run/lnd_in missing or differs from CaseDocs/lnd_in "+site)
    if xmlquery(case,"EXEROOT")!=str(exe.parent):
        fail("New case EXEROOT changed unexpectedly "+site)
    ledger.parent.mkdir(parents=True,exist_ok=True)
    with ledger.open("x") as file:
        json.dump({
            "site":site,"case":str(case),
            "surface":str(surf),"surface_sha256":digest(surf),
            "template_case":str(orig),"reused_executable":str(exe),
            "DATM":"INHERITED_EXISTING_TEMPLATE_STREAMS_UNMODIFIED",
            "CO2":"INHERITED_EXISTING_TEMPLATE_SETTINGS",
            "phase":"PREPARED_NOT_SUBMITTED",
            "first_five_years_only":True,
            "CLM_ACCELERATED_SPINUP":"on",
            "spinup_state":2,"RESUBMIT":0,
            "created_utc":datetime.now(timezone.utc).isoformat(),
        },file,indent=2)
        file.write("\n")
    print(site,"NEW AD400 CASE READY FOR 5-YEAR SMOKE",case)


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


def all_stage(ack):
    if ack!=ACK_STAGE:
        fail("stage requires --confirm "+ACK_STAGE)
    dispatch("stage",single_case)


def queued_case(site):
    # Exactly matching case name substring; one scheduler query per batch.
    return False


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
        if not case_path(site).is_dir():
            fail("Case absent "+site)
        if digest(surface(site))!=obj["surface_sha256"]:
            fail("Surface changed "+site)
        if xmlquery(case_path(site),"RESUBMIT")!="0":
            fail("Case resubmit setting changed "+site)
        if xmlquery(case_path(site),"STOP_N")!="5":
            fail("Case stop changed "+site)
        if xmlquery(case_path(site),"CLM_ACCELERATED_SPINUP").lower()!="on":
            fail("Case not AD "+site)
        # Do not re-run namelists or per-year forcing audits here.
        records[site]=obj
    queue=cmd(["squeue","-u","ly3n24","-h","-o","%j"],timeout=35)
    for site in SITE_ORDER:
        name=case_name(site)
        if any(name in line for line in queue.splitlines()):
            fail("A matching job is already in queue; STOP "+site)
    print("ALL TEN STAGED. SUBMITTING EXACTLY ONE 5-YEAR AD SMOKE PER SITE.")
    # Write ATTEMPTED before case.submit: never blindly duplicate on failure.
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
            obj["phase"]="FIRST_5Y_SUBMITTED"
            obj["cime_submit_output_tail"]=out[-850:]
            ledger.write_text(json.dumps(obj,indent=2)+"\n")
            print(site,"SUBMITTED FIRST 5 AD YEARS ONLY",out[-600:])
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
        queue=cmd(["squeue","-u","ly3n24","-h","-o","%j|%T|%i"],timeout=35)
    except Exception as exc:
        queue="scheduler unavailable "+str(exc)
    for site in SITE_ORDER:
        state=ledger_path(site)
        obj=json.loads(state.read_text()) if state.is_file() else {}
        jobs=[ln for ln in queue.splitlines() if case_name(site) in ln]
        print(f"{site:7} SURF={surface(site).exists()} "
              f"CASE={case_path(site).is_dir()} "
              f"PHASE={obj.get('phase','NOT_STAGED')} "
              f"QUEUE={'; '.join(jobs) or '-'}")


def self_test():
    """Actually parse the repository's ten-site CSVs and namelist helpers."""
    import codecs
    codecs.lookup("utf-8-sig")
    pt=read_csv(PFT_CSV)
    d=read_csv(SOIL_DECISION)
    s4=read_csv(S4_CSV)
    assert set(pt)==set(SITE_ORDER), "Ten PFT site IDs mismatch"
    assert set(d)==set(SITE_ORDER), "Ten soil decision site IDs mismatch"
    assert "CZ-BK1" in s4
    for site in SITE_ORDER:
        sh=mix(site)
        assert abs(sum(sh.values())-100)<1e-9, site
        x=soil_choice(site)
        if site!="RU-Fyo":
            assert abs(x["sand"]+x["silt"]+x["clay"]-100)<1e-8,site
        else:
            assert x["mode"]=="INHERITED_ORIGINAL_PCT_SAND_CLAY_LAYERS_ONLY"
        for name in ("use_fates","use_fates_sp","use_fates_nocomp",
                     "use_fates_fixed_biogeog","spinup_state"):
            assert name in desired_namelist(site), (site,name)
    assert nml_get("use_fates_nocomp = .true.\n","use_fates_nocomp")==".true."
    assert nml_set("use_fates = .false.\n","use_fates",".true.").strip()=="use_fates = .true."
    print("SELF-TEST PASS | 10 station PFT/soil CSVs and CIME namelist helpers")
    print("NO netCDF writes, no CIME case creation, no Slurm jobs.")


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action",choices=("self-test","plan","surfaces","stage","submit-smoke","status"))
    parser.add_argument("--confirm",default="")
    args=parser.parse_args()
    if args.action=="self-test":
        self_test()
    elif args.action=="plan":
        plan()
    elif args.action=="surfaces":
        all_surfaces()
    elif args.action=="stage":
        all_stage(args.confirm)
    elif args.action=="submit-smoke":
        all_submit(args.confirm)
    else:
        status()


if __name__=="__main__":
    main()
