#!/usr/bin/env python3
"""Batch02 four verified sites: verify AD400 completion, then Normal400 hybrid.

Method: the proven DE-Tha Stage14 AD->Normal branch
(examples/DE-Tha/scripts/14_AD_to_Normal_independent_branch.py), adapted to
the four Batch02 cases, using Stage09 AD5 and Stage10 AD395 receipts.

For each site with AD start year Y (AD case RUN_STARTDATE):
  AD400 complete  = 80 run + 80 st_archive successes since the recorded AD5
                    job, final archived restart Y+400 (clm2+datm+cpl), land
                    spinup_state = 2, nothing queued, RESUBMIT exhausted.
  NORMAL5         = NEW case <AD case with _AD400 -> _NORMAL400>, cloned from
                    the AD case with --keepexe; RUN_TYPE=hybrid, RUN_REFCASE=
                    AD case, RUN_STARTDATE=RUN_REFDATE=Y+400-01-01,
                    CLM_ACCELERATED_SPINUP=off; the three AD restarts are
                    COPIED (sha-checked) into the new RUNDIR with rpointers;
                    finidat points at the copied land restart; explicit
                    spinup_state is REMOVED from user_nl_clm (the pinned CTSM
                    rejects an explicit value for FATES; Normal must generate
                    0 or absent). Namelists are generated with the UNPATCHED
                    shared CTSM, exactly as DE-Tha did.
  NORMAL395       = after verified Normal5 (restart Y+405, spinup_state = 0),
                    CONTINUE_RUN=TRUE, RESUBMIT=78, submit once.
  NORMAL400 done  = 80 + 80 successes, final restart Y+800, spinup_state = 0.

The AD400 case, its run/archive, surfaces, forcing, executable and shared CTSM
are only read. Every submission requires the stack guard (ulimit -s >= 65536 KB)
and is marked ATTEMPTED in the ledger before case.submit. Never rerun a
stateful action after an attempt; inspect the ledger instead.

Actions (all accept --sites; default FI-Hyy, FR-Hes, CH-Fru, IT-MBo):
  self-test                   no HPC access
  audit-ad400                 READ ONLY: per-site AD400 completion table
  stage-normal                create + preview new Normal cases (no Slurm)
  submit-normal5              submit the first 5 Normal years per site
  audit-normal5               READ ONLY
  continue-normal395          submit the remaining 395 Normal years per site
  audit-normal400             READ ONLY: final Normal400 completion table
  status                      READ ONLY summary

800 model years is the design, not proof of equilibrium.
"""
from __future__ import annotations
import argparse
import configparser
import importlib.util
import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path

# Standalone Batch02 adapter; never import or mutate Batch02.
import hashlib
import subprocess
import resource
import os

class B:
    BASE=Path("/iridisfs/scratch/ly3n24/CLM_FATES")
    CTSM=BASE/"CTSM"
    CIMESCRIPTS=CTSM/"cime/scripts"
    OUTPUTS=Path("/scratch/ly3n24/CTSM_FATES_OUTPUTS")
    OUT_BASE=BASE/"experiments/NonCompetitionObserved22/Batch02_10"
    SLURM_USER="ly3n24"
    VARIANTS={}
    SITE_ORDER=("FI-Hyy","FR-Hes","CH-Fru","IT-MBo")
    HISTORY=("TOTSOMC","TOTSOMN","TLAI","FATES_GPP","FATES_NPP","TWS","H2OSNO")
    BGC_OPTS="--bgc fates --no-megan --no-drydep --no-fire_emis"
    @staticmethod
    def case_name(site): return site+"_B02_FIXNC_AD400"
    @staticmethod
    def case_path(site): return B.BASE/"cases"/B.case_name(site)
    @staticmethod
    def archive_path(site): return B.OUTPUTS/"archive"/B.case_name(site)
    @staticmethod
    def ledger_path(site): return B.OUT_BASE/site/"AD5_case_state.json"
    @staticmethod
    def surface(site):
        d=json.loads(B.ledger_path(site).read_text())
        return Path(d["surface"])
    @staticmethod
    def digest(path):
        h=hashlib.sha256()
        with Path(path).open("rb") as f:
            for buf in iter(lambda:f.read(1048576),b""):h.update(buf)
        return h.hexdigest()
    @staticmethod
    def cmd(argv,cwd=None,timeout=300):
        p=subprocess.run([str(q) for q in argv],cwd=cwd,stdout=subprocess.PIPE,
                         stderr=subprocess.STDOUT,text=True,timeout=timeout)
        if p.returncode:raise RuntimeError("Command failed "+repr(argv)+"\n"+p.stdout[-3000:])
        return p.stdout.strip()
    @staticmethod
    def xmlquery(case,key):return B.cmd([case/"xmlquery",key,"--value"],cwd=case,timeout=60).strip()
    @staticmethod
    def nml_set(text,key,value):
        match=list(re.finditer(r"(?im)^[ \t]*"+re.escape(key)+r"\s*=[^\r\n]*$",text))
        if len(match)>1:raise RuntimeError("Duplicate namelist key "+key)
        value=key+" = "+str(value)
        if match:
            m=match[0]
            return text[:m.start()]+value+text[m.end():]
        return text.rstrip()+"\n"+value+"\n"
    @staticmethod
    def nml_get(text,key):
        hits=re.findall(r"(?im)^\s*"+re.escape(key)+r"\s*=\s*([^\r\n!]*)",text)
        if len(hits)>1:raise RuntimeError("Duplicate namelist "+key)
        return hits[0].strip().rstrip(",").strip().strip("'\"") if hits else None
    @staticmethod
    def desired_namelist(site):
        d={"fsurdat":"'"+str(B.surface(site))+"'",
           "use_fates":".true.","use_fates_sp":".false.",
           "use_fates_fixed_biogeog":".true.","use_fates_nocomp":".true.",
           "spinup_state":"2",
           "hist_fincl1":",".join("'"+x+"'" for x in B.HISTORY)}
        return d
    @staticmethod
    def pick_sites(sites):
        if not sites:return list(B.SITE_ORDER)
        if not set(sites).issubset(set(B.SITE_ORDER)) or len(set(sites))!=len(sites):
            raise RuntimeError("Unknown or duplicate Batch02 sites: "+repr(sites))
        return [s for s in B.SITE_ORDER if s in sites]
    @staticmethod
    def parse_job_ids(out):
        r=re.findall(r"Submitted job case\.run with id (\d+)",out)
        a=re.findall(r"Submitted job case\.st_archive with id (\d+)",out)
        if len(r)!=1 or len(a)!=1:raise RuntimeError("Ambiguous Slurm submission; no retry")
        return r[0],a[0]
    @staticmethod
    def stack_guard():
        soft,hard=resource.getrlimit(resource.RLIMIT_STACK)
        if soft!=resource.RLIM_INFINITY and soft<64*1024*1024:
            if hard!=resource.RLIM_INFINITY and hard<64*1024*1024:
                raise RuntimeError("Stack hard limit below 64MiB; no submit")
            target=resource.RLIM_INFINITY if hard==resource.RLIM_INFINITY else min(hard,300000*1024)
            resource.setrlimit(resource.RLIMIT_STACK,(target,hard))
        print("BATCH02 NORMAL STACK",resource.getrlimit(resource.RLIMIT_STACK))
        return {"soft_kb":str(resource.getrlimit(resource.RLIMIT_STACK)[0]//1024),
                "hard_kb":str(resource.getrlimit(resource.RLIMIT_STACK)[1]//1024)}

ACK_STAGE="STAGE_BATCH02_NORMAL400_HYBRID_CASES_NO_SLURM"
ACK_N5="SUBMIT_BATCH02_NORMAL5_SMOKES"
ACK_N395="CONTINUE_BATCH02_VERIFIED_NORMAL5_BY_395_YEARS"
POINTERS=(("rpointer.lnd","clm2"),("rpointer.atm","datm"),("rpointer.cpl","cpl"))
SEGMENTS=80          # 1 x 5-year smoke + 79 x 5-year continuation segments
SACCT_START="2026-10-24"


def fail(s):
    raise RuntimeError(str(s))


def utc():
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------- names
def ncase_name(site):
    name=B.case_name(site)
    if not name.endswith("_AD400"):
        fail(site+": unexpected AD case name "+name)
    return name[:-len("_AD400")]+"_NORMAL400"


def ncase_path(site):
    return B.BASE/"cases"/ncase_name(site)


def nrun_path(site):
    return B.OUTPUTS/ncase_name(site)/"run"


def narchive_path(site):
    return B.OUTPUTS/"archive"/ncase_name(site)


def nledger_path(site):
    v=B.VARIANTS.get(site)
    return B.OUT_BASE/site/(f"NORMAL400_{v}_case_state.json" if v else "NORMAL400_case_state.json")


def nhandoff_path(site):
    v=B.VARIANTS.get(site)
    return B.OUT_BASE/site/(f"NORMAL395_restart_handoff_{v}" if v else "NORMAL395_restart_handoff")


def stamp(year):
    return f"{year:04d}-01-01-00000"


def ad_start_year(site):
    d=B.xmlquery(B.case_path(site),"RUN_STARTDATE")
    if not re.fullmatch(r"\d{4}-01-01",d):
        fail(site+": AD RUN_STARTDATE is not Jan-01: "+d)
    return int(d[:4])


# ---------------------------------------------------------------- helpers
def nml_del(text,key):
    pattern=r"(?im)^[ \t]*"+re.escape(key)+r"[ \t]*=[^\r\n]*(\r?\n)?"
    hits=re.findall(pattern,text)
    if len(hits)>1:
        fail("Duplicated namelist key "+key)
    return re.sub(pattern,"",text)


def queued(name):
    out=B.cmd(["squeue","-u",B.SLURM_USER,"-h","-o","%i|%j|%T"],timeout=45)
    rows=[ln.split("|") for ln in out.splitlines() if len(ln.split("|"))>=3]
    return [r for r in rows if r[1] in ("run."+name,"st_archive."+name)]


def sacct_by_name(name):
    out=B.cmd(["sacct","-X","-n","-P","-u",B.SLURM_USER,"-S",SACCT_START,
               "--name","run."+name+",st_archive."+name,
               "--format=JobIDRaw,JobName%100,State,ExitCode"],timeout=90)
    rows=[]
    for ln in out.splitlines():
        p=[x.strip() for x in ln.split("|")]
        if len(p)>=4 and p[0].isdigit() and p[1] in ("run."+name,"st_archive."+name):
            rows.append((int(p[0]),p[1],p[2],p[3]))
    return rows


def restart_state(path):
    import numpy as np
    from netCDF4 import Dataset
    with Dataset(str(path),"r") as ds:
        if "spinup_state" in ds.variables:
            a=np.asarray(ds.variables["spinup_state"][:]).ravel()
            if a.size!=1:
                fail("invalid spinup_state shape in "+str(path))
            return int(a[0])
        if "spinup_state" in ds.ncattrs():
            return int(ds.getncattr("spinup_state"))
    return None


def restart_triplet(name,archive,year):
    folder=archive/"rest"/stamp(year)
    if not folder.is_dir():
        fail(name+": archived restart folder missing "+str(folder))
    files={}
    for _,comp in POINTERS:
        p=folder/f"{name}.{comp}.r.{stamp(year)}.nc"
        if not p.is_file() or p.is_symlink() or p.stat().st_size<1024:
            fail(name+": missing archived "+comp+" restart "+str(p))
        files[comp]=p
    return files


def latest_rest(archive):
    rest=archive/"rest"
    names=sorted(x.name for x in rest.iterdir() if x.is_dir()) if rest.is_dir() else []
    return names[-1] if names else None, len(names)


def chain_audit(site,name,case,archive,first_job,final_year,want_state):
    """Read-only audit of a full 80-segment CIME chain. Returns dict; raises on failure."""
    if queued(name):
        fail(name+": jobs still queued: "+repr(queued(name)))
    rows=[r for r in sacct_by_name(name) if r[0]>=int(first_job)]
    runs=[r for r in rows if r[1].startswith("run.")]
    arcs=[r for r in rows if r[1].startswith("st_archive.")]
    bad=[r for r in rows if (r[2],r[3])!=("COMPLETED","0:0")]
    if bad:
        fail(name+": non-COMPLETED jobs in chain since "+str(first_job)+": "+repr(bad[:4]))
    if len(runs)<SEGMENTS or len(arcs)<SEGMENTS:
        fail(f"{name}: only {len(runs)} run / {len(arcs)} st_archive COMPLETED since job {first_job}; need {SEGMENTS}")
    status=(case/"CaseStatus").read_text(errors="replace")
    last_run=re.findall(r"case\.run (success|error)",status)
    last_arc=re.findall(r"st_archive (success|error)",status)
    if not last_run or last_run[-1]!="success" or not last_arc or last_arc[-1]!="success":
        fail(name+": last CaseStatus run/archive event is not success")
    if B.xmlquery(case,"RESUBMIT")!="0":
        fail(name+": RESUBMIT not exhausted ("+B.xmlquery(case,"RESUBMIT")+")")
    latest,count=latest_rest(archive)
    if latest!=stamp(final_year):
        fail(f"{name}: latest archived restart {latest}, expected {stamp(final_year)}")
    files=restart_triplet(name,archive,final_year)
    st=restart_state(files["clm2"])
    if st!=want_state:
        fail(f"{name}: final land restart spinup_state={st}, expected {want_state}")
    return {"site":site,"case":name,"runs":len(runs),"archives":len(arcs),
            "final":stamp(final_year),"rest_dirs":count,"spinup_state":st,"files":files}


# ---------------------------------------------------------------- AD400 audit
def ad_ledger(site):
    # Batch02 Stage10 updates the AD5_case_state.json in place; it retains
    # the original Stage09 AD5 job and stores continuation receipts separately.
    p=B.ledger_path(site)
    if not p.is_file():fail(site+": AD5/AD395 ledger missing")
    obj=json.loads(p.read_text())
    if obj.get("phase")!="AD395_CONTINUATION_SUBMITTED":
        fail(site+": Stage10 AD395 submission incomplete: "+str(obj.get("phase")))
    first=str(obj.get("active_run_job",""))
    expected={"FI-Hyy":"4728292","FR-Hes":"4728294",
              "CH-Fru":"4728296","IT-MBo":"4728298"}[site]
    if first!=expected:fail(site+": source Stage09 AD5 ID changed: "+first)
    c=str(obj.get("continuation_run_job",""))
    continuation={"FI-Hyy":"4732398","FR-Hes":"4732400",
                  "CH-Fru":"4732402","IT-MBo":"4732404"}[site]
    if c!=continuation:fail(site+": Stage10 continuation ID mismatch "+c)
    manifest=B.OUT_BASE/site/"AD395_continuation_attempt.json"
    if not manifest.is_file():fail(site+": Stage10 continuation attempt manifest missing")
    m=json.loads(manifest.read_text())
    if m.get("phase")!="AD395_CONTINUATION_SUBMITTED" or str(m.get("run_job"))!=continuation:
        fail(site+": Stage10 continuation receipt mismatch")
    obj["AD5_run_job"]=first
    return obj

def ad400_one(site):
    obj=ad_ledger(site)
    y=ad_start_year(site)
    if obj.get("intended_final_year") not in (None,y+400):
        fail(f"{site}: ledger intended_final_year {obj.get('intended_final_year')} != {y+400}")
    if B.xmlquery(B.case_path(site),"CLM_ACCELERATED_SPINUP").lower()!="on":
        fail(site+": AD case is not in accelerated mode")
    r=chain_audit(site,B.case_name(site),B.case_path(site),B.archive_path(site),
                  obj["AD5_run_job"],y+400,2)
    r["start_year"]=y
    return r


def table(title,sites,fn):
    ok,held={},{}
    print(title)
    for site in sites:
        try:
            r=fn(site)
            ok[site]=r
            print(f"  PASS {site:7} {r['case']:34} runs={r['runs']} archives={r['archives']} "
                  f"final={r['final']} spinup_state={r['spinup_state']} rest_dirs={r['rest_dirs']}")
        except Exception as exc:
            held[site]=str(exc)
            print(f"  HOLD {site:7} {str(exc)[-300:]}")
    print(f"SUMMARY pass={len(ok)} hold={len(held)}",("HOLD: "+",".join(held)) if held else "")
    return ok,held


# ---------------------------------------------------------------- Normal staging
def expected_normal_nml(site,src_land):
    d=B.desired_namelist(site)
    d.pop("spinup_state")
    d["finidat"]="'"+str(nrun_path(site)/src_land.name)+"'"
    return d


def stage_one(site,adr):
    name=ncase_name(site)
    case=ncase_path(site)
    led=nledger_path(site)
    for p in (case,nrun_path(site),narchive_path(site),led):
        if p.exists() or p.is_symlink():
            fail(site+": Normal case/run/archive/ledger already exists; no overwrite: "+str(p))
    if queued(name):
        fail(site+": Normal case already has queued jobs")
    adcase=B.case_path(site)
    y=adr["start_year"]+400
    exe=Path(B.xmlquery(adcase,"EXEROOT"))/"cesm.exe"
    if not exe.is_file():
        fail(site+": AD executable missing "+str(exe))
    exe_sha=B.digest(exe)
    files=adr["files"]
    src_sha={c:B.digest(p) for c,p in files.items()}
    led.parent.mkdir(parents=True,exist_ok=True)
    led.write_text(json.dumps({"site":site,"case":str(case),"phase":"STAGE_ATTEMPTED_UNCERTAIN",
                               "at":utc()},indent=2)+"\n")
    B.cmd([B.CIMESCRIPTS/"create_clone","--case",case,"--clone",adcase,"--keepexe"],
          cwd=B.CIMESCRIPTS,timeout=420)
    if B.xmlquery(case,"CASE")!=name:
        fail(site+": cloned case identity wrong")
    if B.xmlquery(case,"EXEROOT")!=str(exe.parent) or B.digest(exe)!=exe_sha:
        fail(site+": Normal case executable differs from AD400 executable")
    if Path(B.xmlquery(case,"COMP_ROOT_DIR_LND")).resolve()!=B.CTSM.resolve():
        fail(site+": Normal case land root is not the shared CTSM (overlay must not be used)")
    date=f"{y:04d}-01-01"
    for key,val in {
        "RUN_TYPE":"hybrid","RUN_STARTDATE":date,
        "RUN_REFCASE":B.case_name(site),"RUN_REFDATE":date,"RUN_REFTOD":"00000",
        "GET_REFCASE":"FALSE","CONTINUE_RUN":"FALSE",
        "CLM_FORCE_COLDSTART":"off","CLM_ACCELERATED_SPINUP":"off",
        "STOP_OPTION":"nyears","STOP_N":"5","REST_OPTION":"nyears","REST_N":"5",
        "RESUBMIT":"0","DOUT_S":"TRUE",
        "RUNDIR":str(nrun_path(site)),"DOUT_S_ROOT":str(narchive_path(site)),
        "MPI_RUN_COMMAND":"srun --mpi=pmix --ntasks=1 --cpus-per-task=1 --cpu-bind=cores",
    }.items():
        B.cmd([case/"xmlchange",f"{key}={val}"],cwd=case,timeout=90)
    if B.xmlquery(case,"CLM_BLDNML_OPTS").split()!=B.BGC_OPTS.split():
        fail(site+": Normal case lost FATES build-namelist options")
    nrun_path(site).mkdir(parents=True,exist_ok=False)
    for comp,src in files.items():
        dst=nrun_path(site)/src.name
        shutil.copy2(src,dst)
        if B.digest(dst)!=src_sha[comp]:
            fail(site+": copied AD restart differs "+comp)
    for ptr,comp in POINTERS:
        (nrun_path(site)/ptr).write_text(files[comp].name+"\n")
    user=case/"user_nl_clm"
    txt=user.read_text()
    txt=nml_del(txt,"spinup_state")
    if B.nml_get(txt,"reseed_dead_plants") is not None:
        fail(site+": CN-only reseed_dead_plants in user_nl_clm")
    for key,val in expected_normal_nml(site,files["clm2"]).items():
        txt=B.nml_set(txt,key,val)
    user.write_text(txt)
    if not (case/".case.run").is_file():
        B.cmd([case/"case.setup"],cwd=case,timeout=300)
    B.cmd([case/"preview_namelists"],cwd=case,timeout=600)
    validate_one(site,files)
    led.write_text(json.dumps({
        "site":site,"case":str(case),"phase":"PREPARED_NOT_SUBMITTED",
        "source_ad_case":B.case_name(site),"source_ad_restart":stamp(y),
        "source_restart_sha256":src_sha,"ad_start_year":adr["start_year"],
        "normal_start_year":y,"normal5_target_year":y+5,"normal400_target_year":y+400,
        "surface":str(B.surface(site)),"surface_sha256":B.digest(B.surface(site)),
        "executable":str(exe),"executable_sha256":exe_sha,
        "generated_lnd_in_sha256":B.digest(case/"CaseDocs/lnd_in"),
        "created_utc":utc()},indent=2)+"\n")
    print(site,"NORMAL CASE STAGED",name,"start",date,"| NO SLURM")


def validate_one(site,files=None):
    case=ncase_path(site)
    led=nledger_path(site)
    if files is None:
        obj=json.loads(led.read_text())
        y=obj["normal_start_year"]
        files={c:B.archive_path(site)/"rest"/stamp(y)/f"{B.case_name(site)}.{c}.r.{stamp(y)}.nc"
               for _,c in POINTERS}
    y=int(files["clm2"].name.split(".r.")[1][:4])
    date=f"{y:04d}-01-01"
    for key,val in {"RUN_TYPE":"hybrid","RUN_STARTDATE":date,"RUN_REFCASE":B.case_name(site),
                    "RUN_REFDATE":date,"GET_REFCASE":"FALSE","CONTINUE_RUN":"FALSE",
                    "CLM_ACCELERATED_SPINUP":"off","CLM_FORCE_COLDSTART":"off",
                    "RESUBMIT":"0","STOP_N":"5","REST_N":"5","DOUT_S":"TRUE",
                    "RUNDIR":str(nrun_path(site)),"DOUT_S_ROOT":str(narchive_path(site))}.items():
        got=B.xmlquery(case,key)
        if got.lower()!=val.lower():
            fail(f"{site}: Normal XML {key}={got}, expected {val}")
    doc=case/"CaseDocs/lnd_in"
    run=nrun_path(site)/"lnd_in"
    if not doc.is_file() or not run.is_file() or B.digest(doc)!=B.digest(run):
        fail(site+": generated Normal lnd_in missing or CaseDocs/RUNDIR differ")
    txt=doc.read_text()
    for key,val in expected_normal_nml(site,files["clm2"]).items():
        if key=="hist_fincl1":
            got=tuple(re.findall(r"'([^']+)'",txt.split("hist_fincl1",1)[-1].split("\n",1)[0]))
            if got!=B.HISTORY:
                fail(site+": Normal history fields wrong "+repr(got))
            continue
        if B.nml_get(txt,key)!=val.strip("'\""):
            fail(f"{site}: Normal lnd_in {key}={B.nml_get(txt,key)!r}")
    if B.nml_get(txt,"spinup_state") not in (None,"0"):
        fail(site+": Normal lnd_in spinup_state must be 0 or absent")
    if B.nml_get(txt,"reseed_dead_plants") is not None:
        fail(site+": Normal lnd_in contains reseed_dead_plants")
    for ptr,comp in POINTERS:
        src=files[comp]
        dst=nrun_path(site)/src.name
        if not dst.is_file() or B.digest(dst)!=B.digest(src):
            fail(site+": staged restart does not match archived AD "+comp)
        if (nrun_path(site)/ptr).read_text().strip()!=src.name:
            fail(site+": rpointer wrong "+ptr)
    print(site,"VALIDATE PASS: hybrid Normal from",stamp(y),"| spinup_state",
          B.nml_get(txt,"spinup_state") or "absent","| no AD edits")


# ---------------------------------------------------------------- submissions
def submit_cmd(case):
    out=B.cmd([case/"case.submit","--skip-preview-namelist"],cwd=case,timeout=360)
    runid,archid=B.parse_job_ids(out)
    return out,runid,archid


def submit_normal5(site,stack):
    led=nledger_path(site)
    obj=json.loads(led.read_text())
    if obj.get("phase")!="PREPARED_NOT_SUBMITTED":
        fail(site+": Normal ledger phase "+str(obj.get("phase"))+"; no duplicate submission")
    case=ncase_path(site)
    cs=(case/"CaseStatus").read_text(errors="replace") if (case/"CaseStatus").is_file() else ""
    if re.search(r"case\.submit starting|case\.run starting",cs):
        fail(site+": Normal CaseStatus shows an earlier submission")
    if queued(ncase_name(site)):
        fail(site+": Normal jobs already queued")
    validate_one(site)
    obj["phase"]="NORMAL5_SUBMISSION_ATTEMPTED_UNCERTAIN"
    obj["attempt_utc"]=utc(); obj["stack_limit_at_submit"]=stack
    led.write_text(json.dumps(obj,indent=2)+"\n")
    out,runid,archid=submit_cmd(case)
    obj["phase"]="NORMAL5_SUBMITTED"
    obj["NORMAL5_run_job"]=runid; obj["NORMAL5_archive_job"]=archid
    obj["cime_submit_output_tail"]=out[-850:]
    led.write_text(json.dumps(obj,indent=2)+"\n")
    print(site,"NORMAL5 SUBMITTED run=",runid,"archive=",archid)
    if not runid or not archid:
        print(site,"WARNING: job IDs not parsed; record them in the ledger by hand")


def normal5_one(site):
    obj=json.loads(nledger_path(site).read_text())
    if obj.get("phase")!="NORMAL5_SUBMITTED":
        fail(site+": Normal ledger phase "+str(obj.get("phase")))
    name=ncase_name(site); case=ncase_path(site)
    runid,archid=str(obj.get("NORMAL5_run_job")),str(obj.get("NORMAL5_archive_job"))
    if not (runid.isdigit() and archid.isdigit()):
        fail(site+": Normal5 job IDs missing")
    if queued(name):
        fail(site+": Normal5 still queued")
    got={r[0]:r for r in sacct_by_name(name)}
    for jid,jn in ((runid,"run."+name),(archid,"st_archive."+name)):
        r=got.get(int(jid))
        if not r or (r[1],r[2],r[3])!=(jn,"COMPLETED","0:0"):
            fail(f"{site}: {jid} not COMPLETED 0:0: {r}")
    cs=(case/"CaseStatus").read_text(errors="replace")
    if not re.search(r"case\.run success",cs) or not re.search(r"st_archive success",cs):
        fail(site+": Normal CaseStatus run/archive success missing")
    for key,want in (("CONTINUE_RUN","false"),("RESUBMIT","0"),("CLM_ACCELERATED_SPINUP","off"),
                     ("STOP_N","5"),("REST_N","5"),("RESUBMIT_SETS_CONTINUE_RUN","true")):
        if B.xmlquery(case,key).lower()!=want:
            fail(f"{site}: Normal CIME {key} != {want}")
    cfg=case/".submit_options"
    cp=configparser.RawConfigParser(); cp.read(cfg)
    if not cp.has_section("SubmitOptions") or not cp.getboolean("SubmitOptions","skip_pnl",fallback=False):
        fail(site+": skip-preview-namelist not persisted")
    if nhandoff_path(site).exists():
        fail(site+": Normal395 handoff already exists")
    y=obj["normal5_target_year"]
    files=restart_triplet(name,narchive_path(site),y)
    st=restart_state(files["clm2"])
    if st not in (0,):
        fail(f"{site}: Normal5 land restart spinup_state={st}, expected 0")
    return {"site":site,"case":name,"runs":1,"archives":1,"final":stamp(y),
            "rest_dirs":latest_rest(narchive_path(site))[1],"spinup_state":st,"files":files,"obj":obj}


def continue_normal395(site,r,stack):
    obj=r["obj"]; led=nledger_path(site); case=ncase_path(site); run=nrun_path(site)
    y=obj["normal5_target_year"]
    obj["phase"]="NORMAL395_ATTEMPTED_UNCERTAIN"; obj["continuation_started_utc"]=utc()
    obj["stack_limit_at_submit"]=stack; obj["intended_final_year"]=y+395
    led.write_text(json.dumps(obj,indent=2)+"\n")
    hand=nhandoff_path(site); hand.mkdir(parents=True,exist_ok=False)
    man={"site":site,"checkpoint":stamp(y),"files":{}}
    for ptr,comp in POINTERS:
        p=run/ptr
        man["files"][ptr]={"source":str(r["files"][comp]),"sha256":B.digest(r["files"][comp]),
                           "prior_pointer":p.read_text() if p.is_file() else None}
        if p.is_file():
            shutil.copy2(p,hand/(ptr+".before"))
    (hand/"manifest.json").write_text(json.dumps(man,indent=2)+"\n")
    for ptr,comp in POINTERS:
        src=r["files"][comp]; dst=run/src.name
        if not dst.exists():
            shutil.copy2(src,dst)
        if B.digest(dst)!=man["files"][ptr]["sha256"]:
            fail(site+": staged Normal restart differs "+comp)
        tmp=run/(ptr+".N395_tmp"); tmp.write_text(src.name+"\n"); tmp.replace(run/ptr)
    B.cmd([case/"xmlchange","CONTINUE_RUN=TRUE"],cwd=case,timeout=90)
    B.cmd([case/"xmlchange","RESUBMIT=78"],cwd=case,timeout=90)
    if B.xmlquery(case,"CONTINUE_RUN").lower()!="true" or B.xmlquery(case,"RESUBMIT")!="78":
        fail(site+": continuation settings not applied")
    out,runid,archid=submit_cmd(case)
    if not runid or not archid:
        fail(site+": case.submit output unparseable; DO NOT RETRY. "+out[-600:])
    obj["phase"]="NORMAL395_SUBMITTED"
    obj["NORMAL395_run_job"]=runid; obj["NORMAL395_archive_job"]=archid
    led.write_text(json.dumps(obj,indent=2)+"\n")
    print(site,"NORMAL395 SUBMITTED",stamp(y),"->",stamp(y+395),"run=",runid,"archive=",archid)


def normal400_one(site):
    obj=json.loads(nledger_path(site).read_text())
    if obj.get("phase")!="NORMAL395_SUBMITTED":
        fail(site+": Normal ledger phase "+str(obj.get("phase")))
    return chain_audit(site,ncase_name(site),ncase_path(site),narchive_path(site),
                       obj["NORMAL5_run_job"],obj["normal400_target_year"],0)


# ---------------------------------------------------------------- driver
def run_batch(label,sites,fn,stack):
    bad=[]
    for site in sites:
        try:
            fn(site,stack)
        except Exception as exc:
            print(site,label,"HOLD — DO NOT RETRY BLINDLY:",str(exc)[-1200:],flush=True)
            bad.append(site)
    print(label,"SUMMARY ok=",len(sites)-len(bad),"hold=",bad)
    if bad:
        raise SystemExit(2)


def status(sites):
    for site in sites:
        ad=json.loads(B.ledger_path(site).read_text()).get("phase") if B.ledger_path(site).is_file() else "-"
        no=json.loads(nledger_path(site).read_text()) if nledger_path(site).is_file() else {}
        try:
            q="; ".join("|".join(r) for r in queued(B.case_name(site))+queued(ncase_name(site))) or "-"
        except Exception as exc:
            q="scheduler unavailable"
        print(f"{site:7} AD={ad} AD_latest={latest_rest(B.archive_path(site))[0]} "
              f"NORMAL={no.get('phase','-')} N_latest={latest_rest(narchive_path(site))[0]} QUEUE={q}")


def self_test():
    assert ncase_name("FI-Hyy")=="FI-Hyy_B02_FIXNC_NORMAL400"
    assert ncase_name("IT-MBo")=="IT-MBo_B02_FIXNC_NORMAL400"
    assert nledger_path("FI-Hyy")!=B.ledger_path("FI-Hyy")
    assert stamp(2397)=="2397-01-01-00000"
    assert stamp(2405)=="2405-01-01-00000"
    t="a = 1\n spinup_state = 2\nb = 2\n"
    assert B.nml_get(nml_del(t,"spinup_state"),"spinup_state") is None
    assert all(ncase_path(z)!=B.case_path(z) for z in B.SITE_ORDER)
    assert len({ACK_STAGE,ACK_N5,ACK_N395})==3 and SEGMENTS==80
    print("BATCH02 STAGE27 SELF-TEST PASS: exact four sites, isolated Normal cases, no writes")

def main():
    ap=argparse.ArgumentParser(description=__doc__,formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("action",choices=("self-test","audit-ad400","stage-normal","submit-normal5",
                                      "audit-normal5","continue-normal395","audit-normal400","status"))
    ap.add_argument("--sites",nargs="+",default=None)
    ap.add_argument("--confirm",default="")
    a=ap.parse_args()
    if a.action=="self-test":
        return self_test()
    sites=B.pick_sites(a.sites)
    if a.action=="status":
        return status(sites)
    if a.action=="audit-ad400":
        _,held=table("BATCH02 AD400 COMPLETION AUDIT (read only)",sites,ad400_one)
        raise SystemExit(2 if held else 0)
    if a.action=="audit-normal5":
        _,held=table("BATCH02 NORMAL5 AUDIT (read only)",sites,normal5_one)
        raise SystemExit(2 if held else 0)
    if a.action=="audit-normal400":
        _,held=table("BATCH02 NORMAL400 COMPLETION AUDIT (read only)",sites,normal400_one)
        raise SystemExit(2 if held else 0)
    if a.action=="stage-normal":
        if a.confirm!=ACK_STAGE:
            fail("stage-normal requires --confirm "+ACK_STAGE)
        ok,held=table("PREFLIGHT: AD400 must be complete for every listed site",sites,ad400_one)
        if held:
            fail("AD400 not complete for "+",".join(held)+"; rerun with --sites limited to PASS sites")
        return run_batch("STAGE-NORMAL",sites,lambda s,_:stage_one(s,ok[s]),None)
    stack=B.stack_guard()
    if a.action=="submit-normal5":
        if a.confirm!=ACK_N5:
            fail("submit-normal5 requires --confirm "+ACK_N5)
        return run_batch("SUBMIT-NORMAL5",sites,submit_normal5,stack)
    if a.action=="continue-normal395":
        if a.confirm!=ACK_N395:
            fail("continue-normal395 requires --confirm "+ACK_N395)
        ok,held=table("PREFLIGHT: Normal5 must be verified for every listed site",sites,normal5_one)
        if held:
            fail("Normal5 not verified for "+",".join(held))
        return run_batch("CONTINUE-NORMAL395",sites,lambda s,st:continue_normal395(s,ok[s],st),stack)


if __name__=="__main__":
    main()
