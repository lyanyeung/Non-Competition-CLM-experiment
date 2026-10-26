#!/usr/bin/env python3
"""Stage21: AmeriFlux Batch01 Lane A AD5 -> AD395 -> NORMAL400 controller.

Sites: the four Stage20 PTS-corrected cases CA-TP4, BR-Ma2, CA-Ca3, CA-LP1.
CA-TP4 AD5 (4732088/4732089) already completed; the other three have only
verified previews.

This ports the Batch03 workflow that completed AD400 10/10 and verified
Normal5 10/10 on IRIDIS6 (examples/Batch03_10/scripts/13_..., 14_...):

* PFT gate (every stateful action): the case's actual fsurdat must reproduce
  data/amf_batch01_recommended_pft_20261026.csv (from the CLM-FATES-single-
  site-workflows RECOMMENDED_50_SITE_CLM_FATES_INPUT_PFT_20261026.csv) once
  host PCT_NAT_PFT is mapped through the pinned fates_hlm_pft_map; host bare
  (index 0) must equal bare_percent; NATVEG=100, CROP=0.
* Stack guard (every submission): the submitting shell's stack soft limit must
  be >= 65536 KB. Slurm here propagates it, and the Leung_2023 dust Prigent
  0.25-degree ESMF mesh read segfaults with the common 8 MB default.
* Attempt-before-submit ledgers; never rerun a stateful action after an
  attempt. AD source cases are never modified by the Normal stages.

Actions (--sites limits; defaults shown):
  self-test
  pft-check            READ ONLY, all four
  submit-ad5           BR-Ma2 CA-Ca3 CA-LP1 (CA-TP4 is refused: already done)
  audit-ad5            READ ONLY
  continue-ad395       79 x 5 years, RESUBMIT=78
  audit-ad400          READ ONLY: 80+80 jobs, restart Y+400, spinup_state=2
  stage-normal         independent hybrid <..._NORMAL400_...> cases, no Slurm
  submit-normal5
  audit-normal5        READ ONLY: restart Y+405, spinup_state=0
  continue-normal395
  audit-normal400      READ ONLY: restart Y+800, spinup_state=0
  status               READ ONLY
"""
from __future__ import annotations
import argparse, configparser, csv, hashlib, json, re, shutil, subprocess
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

REPO=Path(__file__).resolve().parents[3]
BASE=Path("/iridisfs/scratch/ly3n24/CLM_FATES")
CTSM=BASE/"CTSM"
CIMESCRIPTS=CTSM/"cime/scripts"
OUT=Path("/scratch/ly3n24/CTSM_FATES_OUTPUTS")
ROOT=BASE/"experiments/NonCompetitionObserved22/AmeriFlux_Batch01_10"
D20=ROOT/"LaneA_Stage20_correct_PTS_from_surface"
D21=ROOT/"Stage21_AD400_NORMAL400"
PARAM=CTSM/"src/fates/parameter_files/fates_params_default.json"
PFT_CSV=REPO/"data/amf_batch01_recommended_pft_20261026.csv"
USER="ly3n24"
MIN_STACK_KB=65536
SACCT_START="2026-10-24"
SEGMENTS=80
CASES={
 "CA-TP4":"CA-TP4_AMF_FIXNC_AD400_UTC_V3_PTS_AD5",
 "BR-Ma2":"BR-Ma2_AMF_FIXNC_AD400_UTC_V2_PTS_AD5",
 "CA-Ca3":"CA-Ca3_AMF_FIXNC_AD400_UTC_V2_PTS_AD5",
 "CA-LP1":"CA-LP1_AMF_FIXNC_AD400_UTC_V2_PTS_AD5",
}
SITE_ORDER=tuple(CASES)
CATP4_STAMP=D20/"CA-TP4_PTS_V3_AD5_SUBMISSION_ATTEMPT.json"
POINTERS=(("rpointer.lnd","clm2"),("rpointer.atm","datm"),("rpointer.cpl","cpl"))
AD_FLAGS={"use_fates":".true.","use_fates_sp":".false.","use_fates_fixed_biogeog":".true.",
          "use_fates_nocomp":".true.","use_cn":".false."}
LAND_OTHER=("PCT_CROP","PCT_LAKE","PCT_WETLAND","PCT_GLACIER","PCT_URBAN")
ACK_AD5="SUBMIT_AMF_LANEA_AD5_SMOKES_WITH_STACK_GUARD"
ACK_AD395="CONTINUE_AMF_LANEA_VERIFIED_AD5_BY_395_YEARS"
ACK_STAGE="STAGE_AMF_LANEA_NORMAL400_HYBRID_CASES_NO_SLURM"
ACK_N5="SUBMIT_AMF_LANEA_NORMAL5_SMOKES"
ACK_N395="CONTINUE_AMF_LANEA_VERIFIED_NORMAL5_BY_395_YEARS"
ACK_RESTAGE="QUARANTINE_INTERRUPTED_NORMAL_STAGE_AND_RESTAGE_NO_SLURM"
RUN_RE=re.compile(r"Submitted job case\.run with id (\d+)")
ARCH_RE=re.compile(r"Submitted job case\.st_archive with id (\d+)")


def fail(s): raise RuntimeError(str(s))
def utc(): return datetime.now(timezone.utc).isoformat()


def digest(p):
    h=hashlib.sha256()
    with Path(p).open("rb") as f:
        for b in iter(lambda:f.read(1<<20),b""): h.update(b)
    return h.hexdigest()


def cmd(argv,cwd=None,timeout=300):
    p=subprocess.run([str(x) for x in argv],cwd=cwd,text=True,stdout=subprocess.PIPE,
                     stderr=subprocess.STDOUT,timeout=timeout)
    if p.returncode: fail("FAILED "+str(argv)+"\n"+p.stdout[-3000:])
    return p.stdout


def xq(case,key): return cmd(["./xmlquery",key,"--value"],cwd=case,timeout=90).strip()
def xc(case,key,val): cmd([Path(case)/"xmlchange",f"{key}={val}"],cwd=case,timeout=90)


def nml_get(text,key):
    found=re.findall(r"(?im)^\s*"+re.escape(key)+r"\s*=\s*([^\r\n!]*)",text)
    if len(found)>1: fail("Ambiguous "+key)
    return found[0].strip().strip("'\"").strip() if found else None


def nml_raw(text,key):
    found=re.findall(r"(?im)^\s*"+re.escape(key)+r"\s*=\s*([^\r\n]*)",text)
    return found[0].strip() if found else None


def nml_set(text,key,value):
    pat=r"(?im)^[ \t]*"+re.escape(key)+r"[ \t]*=[^\r\n]*$"
    m=list(re.finditer(pat,text))
    if len(m)>1: fail("Duplicated key "+key)
    rep=key+" = "+value
    return text[:m[0].start()]+rep+text[m[0].end():] if m else text.rstrip()+"\n"+rep+"\n"


def nml_del(text,key):
    pat=r"(?im)^[ \t]*"+re.escape(key)+r"[ \t]*=[^\r\n]*(\r?\n)?"
    if len(re.findall(pat,text))>1: fail("Duplicated key "+key)
    return re.sub(pat,"",text)


def pick(sites,default=SITE_ORDER):
    if not sites: return list(default)
    bad=[s for s in sites if s not in CASES]
    if bad: fail("Unknown Lane A site(s): "+",".join(bad))
    return [s for s in SITE_ORDER if s in sites]


def stamp(y): return f"{y:04d}-01-01-00000"


# ------------------------------------------------------------- names / paths
def ad_name(s): return CASES[s]
def ad_case(s): return BASE/"cases"/ad_name(s)
def ad_run(s): return OUT/ad_name(s)/"run"
def ad_arch(s): return OUT/"archive"/ad_name(s)
def ad_ledger(s): return D21/f"{s}_AD400_state.json"
def n_name(s):
    n=ad_name(s)
    if "_FIXNC_AD400_" not in n or not n.endswith("_AD5"): fail("unexpected AD case name "+n)
    return n.replace("_FIXNC_AD400_","_FIXNC_NORMAL400_")[:-len("_AD5")]
def n_case(s): return BASE/"cases"/n_name(s)
def n_run(s): return OUT/n_name(s)/"run"
def n_arch(s): return OUT/"archive"/n_name(s)
def n_ledger(s): return D21/f"{s}_NORMAL400_state.json"


def start_year(s):
    d=xq(ad_case(s),"RUN_STARTDATE")
    if not re.fullmatch(r"\d{4}-01-01",d): fail(s+": RUN_STARTDATE not Jan-01: "+d)
    return int(d[:4])


# ------------------------------------------------------------- guards
def stack_guard():
    import resource
    soft,hard=resource.getrlimit(resource.RLIMIT_STACK)
    kb=lambda v:"unlimited" if v==resource.RLIM_INFINITY else v//1024
    if kb(soft)!="unlimited" and kb(soft)<MIN_STACK_KB:
        fail(f"Stack soft limit {kb(soft)} KB < {MIN_STACK_KB} KB. Run `ulimit -s unlimited` "
             "(or `ulimit -s 300000`) in THIS shell, then rerun; jobs inherit it.")
    print("STACK GUARD PASS: soft =",kb(soft),"KB, hard =",kb(hard),"KB")
    return {"soft_kb":kb(soft),"hard_kb":kb(hard)}


def recommended(s):
    rows={r["site"]:r for r in csv.DictReader(PFT_CSV.open(encoding="utf-8"))}
    if s not in rows: fail(s+": not in "+PFT_CSV.name)
    r=rows[s]
    return {int(k):float(v) for k,v in json.loads(r["fates_natland_percent_json"]).items()},float(r["bare_percent"]),r


def fates_map():
    data=json.loads(PARAM.read_text(encoding="utf-8"))["parameters"]
    import numpy as np
    return list(data["fates_pftname"]["data"]),np.asarray(data["fates_hlm_pft_map"]["data"],dtype=float)


def surface_fates(surf):
    """Host PCT_NAT_PFT -> FATES 1-based slot percentages of the natural landunit, plus bare."""
    import numpy as np
    from netCDF4 import Dataset
    names,m=fates_map()
    with Dataset(str(surf),"r") as ds:
        nat=float(np.ma.filled(ds.variables["PCT_NATVEG"][:],np.nan).ravel()[0])
        other={k:float(np.ma.filled(ds.variables[k][:],np.nan).ravel()[0]) for k in LAND_OTHER if k in ds.variables}
        pft=np.ma.filled(ds.variables["PCT_NAT_PFT"][:],np.nan).ravel()
    out={}
    for host in range(1,len(pft)):
        if pft[host]>0:
            for slot,w in enumerate(m[host-1]):
                if w>0: out[slot+1]=round(out.get(slot+1,0.0)+float(pft[host])*float(w),6)
    return {"natveg":nat,"other":other,"bare":float(pft[0]),"fates":out,"host":{i:float(v) for i,v in enumerate(pft) if v>0}}


def pft_gate(s,case=None):
    case=case or ad_case(s)
    surf=Path(nml_get((case/"CaseDocs/lnd_in").read_text(),"fsurdat"))
    want,bare,row=recommended(s)
    got=surface_fates(surf)
    if abs(got["natveg"]-100)>1e-4 or any(abs(v)>1e-4 for v in got["other"].values()):
        fail(f"{s}: landunits not NATVEG100/others0: {got['natveg']} {got['other']}")
    if abs(got["bare"]-bare)>1e-4:
        fail(f"{s}: host bare {got['bare']} != recommended {bare}")
    keys=set(want)|set(got["fates"])
    if any(abs(want.get(k,0)-got["fates"].get(k,0))>1e-3 for k in keys):
        fail(f"{s}: FATES fractions {got['fates']} != recommended {want} ({row['recommended_percent']})")
    return {"surface":str(surf),"host":got["host"],"fates":got["fates"],"bare":got["bare"],
            "recommended":row["recommended_percent"]}


def queued(name):
    out=cmd(["squeue","-u",USER,"-h","-o","%i|%j|%T"],timeout=45)
    rows=[ln.split("|") for ln in out.splitlines() if len(ln.split("|"))>=3]
    return [r for r in rows if r[1] in ("run."+name,"st_archive."+name)]


def sacct_name(name):
    out=cmd(["sacct","-X","-n","-P","-u",USER,"-S",SACCT_START,"--name","run."+name+",st_archive."+name,
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
            if a.size!=1: fail("bad spinup_state shape "+str(path))
            return int(a[0])
        if "spinup_state" in ds.ncattrs(): return int(ds.getncattr("spinup_state"))
    return None


def triplet(name,arch,y):
    folder=arch/"rest"/stamp(y)
    if not folder.is_dir(): fail(name+": archived restart folder missing "+str(folder))
    files={}
    for _,c in POINTERS:
        p=folder/f"{name}.{c}.r.{stamp(y)}.nc"
        if not p.is_file() or p.is_symlink() or p.stat().st_size<1024: fail(name+": missing "+str(p))
        files[c]=p
    return files


def latest(arch):
    r=arch/"rest"
    n=sorted(x.name for x in r.iterdir() if x.is_dir()) if r.is_dir() else []
    return (n[-1] if n else None),len(n)


def submit_options_ok(case):
    cp=configparser.RawConfigParser(); cp.read(case/".submit_options")
    return cp.has_section("SubmitOptions") and cp.getboolean("SubmitOptions","skip_pnl",fallback=False)


def submit(case):
    out=cmd([case/"case.submit","--skip-preview-namelist"],cwd=case,timeout=650)
    r,a=RUN_RE.search(out),ARCH_RE.search(out)
    return out,(r.group(1) if r else None),(a.group(1) if a else None)


def load(p): return json.loads(p.read_text()) if p.is_file() else {}
def save(p,obj):
    p.parent.mkdir(parents=True,exist_ok=True); p.write_text(json.dumps(obj,indent=2)+"\n")


def table(title,sites,fn):
    ok,held={},{}
    print(title)
    for s in sites:
        try:
            r=fn(s); ok[s]=r
            print(f"  PASS {s:7} {r.get('case','')} "+" ".join(f"{k}={r[k]}" for k in ("runs","archives","final","spinup_state","rest_dirs","recommended","fates","bare") if k in r))
        except Exception as e:
            held[s]=str(e); print(f"  HOLD {s:7} {str(e)[-320:]}")
    print(f"SUMMARY pass={len(ok)} hold={len(held)}",("HOLD: "+",".join(held)) if held else "")
    return ok,held


def batch(label,sites,fn,stack):
    bad=[]
    for s in sites:
        try: fn(s,stack)
        except Exception as e:
            print(s,label,"HOLD — DO NOT RETRY BLINDLY:",str(e)[-1200:],flush=True); bad.append(s)
    print(label,"SUMMARY ok=",len(sites)-len(bad),"hold=",bad)
    if bad: raise SystemExit(2)


# ------------------------------------------------------------- AD5
def ad5_ids(s):
    obj=load(ad_ledger(s))
    if obj.get("AD5_run_job") and obj.get("AD5_archive_job"):
        return str(obj["AD5_run_job"]),str(obj["AD5_archive_job"])
    if s=="CA-TP4":
        st=load(CATP4_STAMP)
        if st.get("state")!="CIME_SUBMIT_RETURNED_SUCCESS_MODEL_UNVERIFIED": fail("CA-TP4 Stage20 stamp state "+str(st.get("state")))
        r,a=RUN_RE.search(st.get("output_tail","")),ARCH_RE.search(st.get("output_tail",""))
        if not r or not a: fail("CA-TP4 job IDs not in Stage20 stamp output_tail")
        return r.group(1),a.group(1)
    fail(s+": no recorded AD5 job IDs")


def submit_ad5_one(s,stack):
    if s=="CA-TP4": fail("CA-TP4 AD5 already submitted and completed via Stage20; refused")
    led=ad_ledger(s)
    if led.exists(): fail(s+": Stage21 ledger exists ("+str(load(led).get("phase"))+"); no duplicate")
    att=load(D20/f"{s}_new_PTS_case_attempt.json")
    if att.get("status")!="PREVIEW_VERIFIED_NOT_SUBMITTED": fail(s+": Stage20 attempt status "+str(att.get("status")))
    case=ad_case(s)
    for k,v in (("CONTINUE_RUN","false"),("RESUBMIT","0"),("STOP_N","5"),("REST_N","5"),("CLM_ACCELERATED_SPINUP","on")):
        if xq(case,k).lower()!=v: fail(f"{s}: {k} != {v}")
    lnd=(case/"CaseDocs/lnd_in").read_text()
    for k,v in {**AD_FLAGS,"spinup_state":"2"}.items():
        if nml_get(lnd,k)!=v: fail(f"{s}: generated lnd_in {k}={nml_get(lnd,k)}")
    if (case/"CaseStatus").is_file() and re.search(r"case\.submit starting|case\.run starting|model execution starting",(case/"CaseStatus").read_text(errors="replace")):
        fail(s+": CaseStatus shows earlier submission")
    if ad_run(s).is_dir() and (any(ad_run(s).glob("rpointer*")) or any(ad_run(s).glob("*.r.*.nc"))):
        fail(s+": run directory holds restart artifacts")
    if queued(ad_name(s)): fail(s+": jobs already queued")
    pft=pft_gate(s)
    obj={"site":s,"case":str(case),"phase":"AD5_SUBMISSION_ATTEMPTED_UNCERTAIN","pft_gate":pft,
         "stack_limit_at_submit":stack,"attempt_utc":utc()}
    save(led,obj)
    out,r,a=submit(case)
    obj.update(phase="AD5_SUBMITTED",AD5_run_job=r,AD5_archive_job=a,cime_submit_output_tail=out[-850:])
    save(led,obj)
    print(s,"AD5 SUBMITTED run=",r,"archive=",a)
    if not r or not a: print(s,"WARNING: job IDs not parsed; record them in",led)


def ad5_one(s):
    run_id,arch_id=ad5_ids(s); name=ad_name(s); case=ad_case(s)
    if queued(name): fail(s+": AD jobs still queued")
    got={r[0]:r for r in sacct_name(name)}
    for jid,jn in ((run_id,"run."+name),(arch_id,"st_archive."+name)):
        r=got.get(int(jid))
        if not r or (r[1],r[2],r[3])!=(jn,"COMPLETED","0:0"): fail(f"{s}: {jid} not COMPLETED 0:0: {r}")
    cs=(case/"CaseStatus").read_text(errors="replace")
    if not re.search(r"case\.run success",cs) or not re.search(r"st_archive success",cs): fail(s+": CaseStatus success missing")
    for k,v in (("CONTINUE_RUN","false"),("RESUBMIT","0"),("CLM_ACCELERATED_SPINUP","on"),("STOP_N","5"),("REST_N","5"),("RESUBMIT_SETS_CONTINUE_RUN","true")):
        if xq(case,k).lower()!=v: fail(f"{s}: CIME {k} != {v}")
    if not submit_options_ok(case): fail(s+": skip-preview-namelist not persisted")
    lnd=(case/"CaseDocs/lnd_in").read_text()
    for k,v in {**AD_FLAGS,"spinup_state":"2"}.items():
        if nml_get(lnd,k)!=v: fail(f"{s}: lnd_in {k}")
    y=start_year(s)+5
    files=triplet(name,ad_arch(s),y)
    st=restart_state(files["clm2"])
    if st!=2: fail(f"{s}: AD5 land restart spinup_state={st}")
    if (D21/f"{s}_AD395_handoff").exists(): fail(s+": AD395 handoff already exists")
    for ptr,c in POINTERS:
        p=ad_run(s)/ptr
        if p.exists():
            lines=[x.strip() for x in p.read_text().splitlines() if x.strip()]
            if lines!=[files[c].name]: fail(f"{s}: {ptr} not at AD5 checkpoint {lines}")
    pft=pft_gate(s)
    return {"case":name,"runs":1,"archives":1,"final":stamp(y),"spinup_state":st,"files":files,
            "year":y,"run_id":run_id,"arch_id":arch_id,"recommended":pft["recommended"]}


def continue_ad395(s,r,stack):
    led=ad_ledger(s); obj=load(led)
    if obj.get("phase") not in (None,"AD5_SUBMITTED"): fail(s+": ledger phase "+str(obj.get("phase")))
    case=ad_case(s); run=ad_run(s); y=r["year"]
    if not run.is_dir(): fail(s+": AD RUNDIR missing "+str(run))
    obj.update(site=s,case=str(case),AD5_run_job=r["run_id"],AD5_archive_job=r["arch_id"],
               phase="AD395_ATTEMPTED_UNCERTAIN",AD5_verified_year=y,intended_final_year=y+395,
               stack_limit_at_submit=stack,continuation_started_utc=utc())
    save(led,obj)
    hand=D21/f"{s}_AD395_handoff"; hand.mkdir(parents=True,exist_ok=False)
    man={"site":s,"checkpoint":stamp(y),"files":{}}
    for ptr,c in POINTERS:
        p=run/ptr; man["files"][ptr]={"source":str(r["files"][c]),"sha256":digest(r["files"][c]),
                                      "prior":p.read_text() if p.is_file() else None}
        if p.is_file(): shutil.copy2(p,hand/(ptr+".before"))
    (hand/"manifest.json").write_text(json.dumps(man,indent=2)+"\n")
    for ptr,c in POINTERS:
        src=r["files"][c]; dst=run/src.name
        if not dst.exists(): shutil.copy2(src,dst)
        if digest(dst)!=man["files"][ptr]["sha256"]: fail(f"{s}: staged restart differs {c}")
        tmp=run/(ptr+".tmp21"); tmp.write_text(src.name+"\n"); tmp.replace(run/ptr)
    xc(case,"CONTINUE_RUN","TRUE"); xc(case,"RESUBMIT","78")
    if xq(case,"CONTINUE_RUN").lower()!="true" or xq(case,"RESUBMIT")!="78": fail(s+": continuation settings not applied")
    out,rid,aid=submit(case)
    if not rid or not aid: fail(s+": case.submit unparseable; DO NOT RETRY. "+out[-600:])
    obj.update(phase="AD395_SUBMITTED",AD395_run_job=rid,AD395_archive_job=aid); save(led,obj)
    print(s,"AD395 SUBMITTED",stamp(y),"->",stamp(y+395),"run=",rid,"archive=",aid)


def chain(s,name,case,arch,first,final,want):
    if queued(name): fail(name+": jobs still queued")
    rows=[r for r in sacct_name(name) if r[0]>=int(first)]
    bad=[r for r in rows if (r[2],r[3])!=("COMPLETED","0:0")]
    if bad: fail(name+": non-COMPLETED jobs since "+str(first)+": "+repr(bad[:4]))
    runs=[r for r in rows if r[1].startswith("run.")]; arcs=[r for r in rows if r[1].startswith("st_archive.")]
    if len(runs)<SEGMENTS or len(arcs)<SEGMENTS: fail(f"{name}: {len(runs)} run / {len(arcs)} archive COMPLETED; need {SEGMENTS}")
    cs=(case/"CaseStatus").read_text(errors="replace")
    lr=re.findall(r"case\.run (success|error)",cs); la=re.findall(r"st_archive (success|error)",cs)
    if not lr or lr[-1]!="success" or not la or la[-1]!="success": fail(name+": last CaseStatus event not success")
    if xq(case,"RESUBMIT")!="0": fail(name+": RESUBMIT not exhausted")
    l,n=latest(arch)
    if l!=stamp(final): fail(f"{name}: latest restart {l}, expected {stamp(final)}")
    files=triplet(name,arch,final); st=restart_state(files["clm2"])
    if st!=want: fail(f"{name}: final spinup_state={st}, expected {want}")
    return {"case":name,"runs":len(runs),"archives":len(arcs),"final":stamp(final),"rest_dirs":n,"spinup_state":st,"files":files}


def ad400_one(s):
    obj=load(ad_ledger(s))
    if obj.get("phase")!="AD395_SUBMITTED": fail(s+": AD ledger phase "+str(obj.get("phase")))
    y=start_year(s)
    r=chain(s,ad_name(s),ad_case(s),ad_arch(s),obj["AD5_run_job"],y+400,2); r["start_year"]=y
    return r


# ------------------------------------------------------------- Normal400
def stage_normal_one(s,adr):
    name=n_name(s); case=n_case(s); led=n_ledger(s); adc=ad_case(s)
    for p in (case,n_run(s),n_arch(s),led):
        if p.exists() or p.is_symlink(): fail(s+": Normal path exists; no overwrite: "+str(p))
    if queued(name): fail(s+": Normal jobs queued")
    y=adr["start_year"]+400; files=adr["files"]
    exe=Path(xq(adc,"EXEROOT"))/"cesm.exe"; exe_sha=digest(exe)
    src_sha={c:digest(p) for c,p in files.items()}
    pft=pft_gate(s)
    save(led,{"site":s,"case":str(case),"phase":"STAGE_ATTEMPTED_UNCERTAIN","at":utc()})
    cmd([CIMESCRIPTS/"create_clone","--case",case,"--clone",adc,"--keepexe"],cwd=CIMESCRIPTS,timeout=420)
    if xq(case,"CASE")!=name: fail(s+": clone identity")
    if xq(case,"EXEROOT")!=str(exe.parent) or digest(exe)!=exe_sha: fail(s+": executable differs")
    if Path(xq(case,"COMP_ROOT_DIR_LND")).resolve()!=CTSM.resolve(): fail(s+": land root is not shared CTSM")
    date=f"{y:04d}-01-01"
    for k,v in {"RUN_TYPE":"hybrid","RUN_STARTDATE":date,"RUN_REFCASE":ad_name(s),"RUN_REFDATE":date,
                "RUN_REFTOD":"00000","GET_REFCASE":"FALSE","CONTINUE_RUN":"FALSE",
                "CLM_FORCE_COLDSTART":"off","CLM_ACCELERATED_SPINUP":"off",
                "STOP_OPTION":"nyears","STOP_N":"5","REST_OPTION":"nyears","REST_N":"5","RESUBMIT":"0",
                "DOUT_S":"TRUE","RUNDIR":str(n_run(s)),"DOUT_S_ROOT":str(n_arch(s))}.items():
        xc(case,k,v)
    for k in ("PTS_LAT","PTS_LON","PTS_DOMAINFILE","CCSM_CO2_PPMV","CLM_BLDNML_OPTS"):
        if xq(case,k)!=xq(adc,k): fail(f"{s}: Normal {k} differs from AD case")
    n_run(s).mkdir(parents=True,exist_ok=False)
    for c,src in files.items():
        dst=n_run(s)/src.name; shutil.copy2(src,dst)
        if digest(dst)!=src_sha[c]: fail(f"{s}: copied restart differs {c}")
    for ptr,c in POINTERS: (n_run(s)/ptr).write_text(files[c].name+"\n")
    u=case/"user_nl_clm"; t=nml_del(u.read_text(),"spinup_state")
    if nml_get(t,"reseed_dead_plants") is not None: fail(s+": reseed_dead_plants in user_nl_clm")
    t=nml_set(t,"finidat","'"+str(n_run(s)/files["clm2"].name)+"'")
    # Pin the exact FATES parameter file used by the AD case. The AD namelist was generated with the
    # private CTSM overlay; the Normal namelist uses the shared CTSM, whose default may differ.
    pf=nml_get((adc/"CaseDocs/lnd_in").read_text(),"fates_paramfile")
    if not pf or not Path(pf).is_file(): fail(s+": AD fates_paramfile missing: "+str(pf))
    t=nml_set(t,"fates_paramfile","'"+pf+"'")
    u.write_text(t)
    if not (case/".case.run").is_file(): cmd([case/"case.setup"],cwd=case,timeout=300)
    cmd([case/"preview_namelists"],cwd=case,timeout=600)
    validate_normal(s,files)
    save(led,{"site":s,"case":str(case),"phase":"PREPARED_NOT_SUBMITTED","source_ad_case":ad_name(s),
              "source_ad_restart":stamp(y),"source_restart_sha256":src_sha,"ad_start_year":adr["start_year"],
              "normal_start_year":y,"normal5_target_year":y+5,"normal400_target_year":y+400,
              "executable_sha256":exe_sha,"pft_gate":pft,"fates_paramfile":pf,"fates_paramfile_sha256":digest(pf),
              "generated_lnd_in_sha256":digest(case/"CaseDocs/lnd_in"),"created_utc":utc()})
    print(s,"NORMAL CASE STAGED",name,"start",date,"| NO SLURM")


def interrupted_one(s):
    """READ ONLY: an interrupted stage-normal (e.g. SSH drop) leaves ledger phase
    STAGE_ATTEMPTED_UNCERTAIN and a partial case/run. Report it and prove that no
    Normal job was ever queued or accounted for this case name."""
    led=n_ledger(s); obj=load(led); name=n_name(s)
    if obj.get("phase")!="STAGE_ATTEMPTED_UNCERTAIN":
        fail(s+": Normal ledger phase "+str(obj.get("phase"))+" (only STAGE_ATTEMPTED_UNCERTAIN is recoverable here)")
    if queued(name): fail(s+": Normal jobs queued: "+str(queued(name)))
    hist=sacct_name(name)
    if hist: fail(s+": Slurm accounting exists for Normal case; manual review: "+str(hist[:4]))
    if n_arch(s).exists(): fail(s+": Normal archive exists "+str(n_arch(s)))
    case,run=n_case(s),n_run(s)
    if (case/"CaseStatus").is_file() and re.search(r"case\.submit|case\.run starting",(case/"CaseStatus").read_text(errors="replace")):
        fail(s+": partial case CaseStatus shows a submission")
    info={"case_exists":case.is_dir(),"case_setup":(case/".case.run").is_file(),
          "casedocs_lnd_in":(case/"CaseDocs/lnd_in").is_file(),"run_exists":run.is_dir(),
          "run_files":sorted(x.name for x in run.iterdir())[:12] if run.is_dir() else [],"attempt_at":obj.get("at")}
    print(f"  {s}: interrupted stage {info}")
    return info


def restage_interrupted_one(s,adr):
    interrupted_one(s)
    q=D21/"quarantine_interrupted_stage"/f"{s}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    q.mkdir(parents=True,exist_ok=False)
    moved={}
    for tag,p in (("case",n_case(s)),("run_parent",n_run(s).parent),("ledger",n_ledger(s))):
        if p.exists():
            dst=q/tag; shutil.move(str(p),str(dst)); moved[tag]={"from":str(p),"to":str(dst)}
    (q/"QUARANTINE_RECEIPT.json").write_text(json.dumps({"site":s,"reason":"interrupted stage-normal (no Slurm job ever submitted)",
                                                         "moved":moved,"utc":utc()},indent=2)+"\n")
    print(f"  {s}: partial Normal stage quarantined to {q}")
    stage_normal_one(s,adr)


def validate_normal(s,files=None):
    case=n_case(s); adc=ad_case(s)
    if files is None:
        y=load(n_ledger(s))["normal_start_year"]
        files={c:ad_arch(s)/"rest"/stamp(y)/f"{ad_name(s)}.{c}.r.{stamp(y)}.nc" for _,c in POINTERS}
    y=int(files["clm2"].name.split(".r.")[1][:4]); date=f"{y:04d}-01-01"
    for k,v in {"RUN_TYPE":"hybrid","RUN_STARTDATE":date,"RUN_REFCASE":ad_name(s),"RUN_REFDATE":date,
                "GET_REFCASE":"FALSE","CONTINUE_RUN":"FALSE","CLM_ACCELERATED_SPINUP":"off",
                "CLM_FORCE_COLDSTART":"off","RESUBMIT":"0","STOP_N":"5","REST_N":"5","DOUT_S":"TRUE",
                "RUNDIR":str(n_run(s)),"DOUT_S_ROOT":str(n_arch(s))}.items():
        if xq(case,k).lower()!=v.lower(): fail(f"{s}: Normal XML {k}={xq(case,k)}")
    doc,run=case/"CaseDocs/lnd_in",n_run(s)/"lnd_in"
    if not doc.is_file() or not run.is_file() or digest(doc)!=digest(run): fail(s+": Normal lnd_in missing/differs")
    t=doc.read_text(); a=(adc/"CaseDocs/lnd_in").read_text()
    for k,v in AD_FLAGS.items():
        if nml_get(t,k)!=v: fail(f"{s}: Normal lnd_in {k}={nml_get(t,k)}")
    for k in ("fsurdat","fates_paramfile","use_crop","co2_ppmv","fates_spitfire_mode"):
        if nml_get(t,k)!=nml_get(a,k): fail(f"{s}: Normal {k} differs from AD: {nml_get(t,k)} vs {nml_get(a,k)}")
    if nml_raw(t,"hist_fincl1")!=nml_raw(a,"hist_fincl1"): fail(s+": Normal history fields differ from AD")
    if nml_get(t,"finidat")!=str(n_run(s)/files["clm2"].name): fail(s+": Normal finidat "+str(nml_get(t,"finidat")))
    if nml_get(t,"spinup_state") not in (None,"0"): fail(s+": Normal spinup_state must be 0/absent")
    if nml_get(t,"reseed_dead_plants") is not None: fail(s+": reseed_dead_plants present")
    sem=lambda e:(e.tag,tuple(sorted(e.attrib.items())),(e.text or "").strip(),tuple(sem(k) for k in e))
    if sem(ET.parse(case/"CaseDocs/datm.streams.xml").getroot())!=sem(ET.parse(adc/"CaseDocs/datm.streams.xml").getroot()):
        fail(s+": Normal DATM streams differ from AD case")
    for ptr,c in POINTERS:
        src=files[c]; dst=n_run(s)/src.name
        if not dst.is_file() or digest(dst)!=digest(src): fail(f"{s}: staged restart mismatch {c}")
        if (n_run(s)/ptr).read_text().strip()!=src.name: fail(f"{s}: rpointer {ptr}")
    print(s,"VALIDATE PASS: hybrid Normal from",stamp(y),"| spinup_state",nml_get(t,"spinup_state") or "absent","| DATM = AD | no AD edits")


def submit_normal5(s,stack):
    led=n_ledger(s); obj=load(led)
    if obj.get("phase")!="PREPARED_NOT_SUBMITTED": fail(s+": Normal ledger phase "+str(obj.get("phase")))
    case=n_case(s)
    if (case/"CaseStatus").is_file() and re.search(r"case\.submit starting|case\.run starting",(case/"CaseStatus").read_text(errors="replace")):
        fail(s+": Normal CaseStatus shows submission")
    if queued(n_name(s)): fail(s+": Normal jobs queued")
    validate_normal(s); pft_gate(s,case)
    obj.update(phase="NORMAL5_SUBMISSION_ATTEMPTED_UNCERTAIN",attempt_utc=utc(),stack_limit_at_submit=stack); save(led,obj)
    out,r,a=submit(case)
    obj.update(phase="NORMAL5_SUBMITTED",NORMAL5_run_job=r,NORMAL5_archive_job=a,cime_submit_output_tail=out[-850:]); save(led,obj)
    print(s,"NORMAL5 SUBMITTED run=",r,"archive=",a)


def normal5_one(s):
    obj=load(n_ledger(s))
    if obj.get("phase")!="NORMAL5_SUBMITTED": fail(s+": Normal ledger phase "+str(obj.get("phase")))
    name=n_name(s); case=n_case(s)
    r_id,a_id=str(obj.get("NORMAL5_run_job")),str(obj.get("NORMAL5_archive_job"))
    if queued(name): fail(s+": Normal5 still queued")
    got={r[0]:r for r in sacct_name(name)}
    for jid,jn in ((r_id,"run."+name),(a_id,"st_archive."+name)):
        r=got.get(int(jid)) if jid.isdigit() else None
        if not r or (r[1],r[2],r[3])!=(jn,"COMPLETED","0:0"): fail(f"{s}: {jid} not COMPLETED 0:0: {r}")
    cs=(case/"CaseStatus").read_text(errors="replace")
    if not re.search(r"case\.run success",cs) or not re.search(r"st_archive success",cs): fail(s+": Normal CaseStatus")
    for k,v in (("CONTINUE_RUN","false"),("RESUBMIT","0"),("CLM_ACCELERATED_SPINUP","off"),("RESUBMIT_SETS_CONTINUE_RUN","true")):
        if xq(case,k).lower()!=v: fail(f"{s}: Normal {k} != {v}")
    if not submit_options_ok(case): fail(s+": skip_pnl not persisted")
    if (D21/f"{s}_NORMAL395_handoff").exists(): fail(s+": Normal395 handoff exists")
    y=obj["normal5_target_year"]; files=triplet(name,n_arch(s),y); st=restart_state(files["clm2"])
    if st!=0: fail(f"{s}: Normal5 spinup_state={st}, expected 0")
    return {"case":name,"runs":1,"archives":1,"final":stamp(y),"spinup_state":st,"files":files,"obj":obj,"year":y}


def continue_normal395(s,r,stack):
    obj=r["obj"]; led=n_ledger(s); case=n_case(s); run=n_run(s); y=r["year"]
    if not run.is_dir(): fail(s+": Normal RUNDIR missing "+str(run))
    obj.update(phase="NORMAL395_ATTEMPTED_UNCERTAIN",continuation_started_utc=utc(),stack_limit_at_submit=stack,intended_final_year=y+395)
    save(led,obj)
    hand=D21/f"{s}_NORMAL395_handoff"; hand.mkdir(parents=True,exist_ok=False)
    for ptr,c in POINTERS:
        if (run/ptr).is_file(): shutil.copy2(run/ptr,hand/(ptr+".before"))
        src=r["files"][c]; dst=run/src.name
        if not dst.exists(): shutil.copy2(src,dst)
        if digest(dst)!=digest(src): fail(f"{s}: staged Normal restart differs {c}")
        tmp=run/(ptr+".tmp21"); tmp.write_text(src.name+"\n"); tmp.replace(run/ptr)
    xc(case,"CONTINUE_RUN","TRUE"); xc(case,"RESUBMIT","78")
    if xq(case,"CONTINUE_RUN").lower()!="true" or xq(case,"RESUBMIT")!="78": fail(s+": settings not applied")
    out,rid,aid=submit(case)
    if not rid or not aid: fail(s+": unparseable submit; DO NOT RETRY. "+out[-600:])
    obj.update(phase="NORMAL395_SUBMITTED",NORMAL395_run_job=rid,NORMAL395_archive_job=aid); save(led,obj)
    print(s,"NORMAL395 SUBMITTED",stamp(y),"->",stamp(y+395),"run=",rid,"archive=",aid)


def normal400_one(s):
    obj=load(n_ledger(s))
    if obj.get("phase")!="NORMAL395_SUBMITTED": fail(s+": Normal ledger phase "+str(obj.get("phase")))
    return chain(s,n_name(s),n_case(s),n_arch(s),obj["NORMAL5_run_job"],obj["normal400_target_year"],0)


def status(sites):
    for s in sites:
        a,n=load(ad_ledger(s)),load(n_ledger(s))
        try: q="; ".join("|".join(r) for r in queued(ad_name(s))+queued(n_name(s))) or "-"
        except Exception: q="scheduler unavailable"
        print(f"{s:7} AD={a.get('phase','-')} AD_latest={latest(ad_arch(s))[0]} "
              f"NORMAL={n.get('phase','-')} N_latest={latest(n_arch(s))[0]} QUEUE={q}")


def self_test():
    assert n_name("CA-TP4")=="CA-TP4_AMF_FIXNC_NORMAL400_UTC_V3_PTS"
    assert n_name("BR-Ma2")=="BR-Ma2_AMF_FIXNC_NORMAL400_UTC_V2_PTS"
    assert ad_ledger("CA-Ca3")!=n_ledger("CA-Ca3")
    rows={r["site"] for r in csv.DictReader(PFT_CSV.open(encoding="utf-8"))}
    assert len(rows)==10 and set(SITE_ORDER)<=rows
    for s in SITE_ORDER:
        w,b,_=recommended(s); assert abs(sum(w.values())+b-100)<1e-6,s
    assert recommended("CA-LP1")[0]=={2:100.0} and recommended("CA-TP4")[0]=={2:93.0,6:7.0}
    t="a = 1\n spinup_state = 2\nb = 2\n"; assert nml_get(nml_del(t,"spinup_state"),"spinup_state") is None
    assert RUN_RE.search("Submitted job case.run with id 4732088").group(1)=="4732088"
    assert len({ACK_AD5,ACK_AD395,ACK_STAGE,ACK_N5,ACK_N395})==5
    print("AMERIFLUX STAGE21 SELF-TEST PASS (no HPC access, no writes)")


def main():
    ap=argparse.ArgumentParser(description=__doc__,formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("action",choices=("self-test","pft-check","submit-ad5","audit-ad5","continue-ad395","audit-ad400",
                                      "inspect-interrupted","restage-interrupted",
                                      "stage-normal","submit-normal5","audit-normal5","continue-normal395","audit-normal400","status"))
    ap.add_argument("--sites",nargs="+"); ap.add_argument("--confirm",default="")
    a=ap.parse_args()
    if a.action=="self-test": return self_test()
    if a.action=="status": return status(pick(a.sites))
    if a.action=="pft-check":
        _,h=table("LANE A PFT GATE vs RECOMMENDED_50 (read only)",pick(a.sites),lambda s:pft_gate(s)); raise SystemExit(2 if h else 0)
    if a.action=="audit-ad5":
        _,h=table("LANE A AD5 AUDIT (read only)",pick(a.sites),ad5_one); raise SystemExit(2 if h else 0)
    if a.action=="audit-ad400":
        _,h=table("LANE A AD400 AUDIT (read only)",pick(a.sites),ad400_one); raise SystemExit(2 if h else 0)
    if a.action=="audit-normal5":
        _,h=table("LANE A NORMAL5 AUDIT (read only)",pick(a.sites),normal5_one); raise SystemExit(2 if h else 0)
    if a.action=="audit-normal400":
        _,h=table("LANE A NORMAL400 AUDIT (read only)",pick(a.sites),normal400_one); raise SystemExit(2 if h else 0)
    if a.action=="inspect-interrupted":
        _,h=table("INTERRUPTED NORMAL STAGE INSPECTION (read only)",pick(a.sites),interrupted_one); raise SystemExit(2 if h else 0)
    if a.action=="restage-interrupted":
        if a.confirm!=ACK_RESTAGE: fail("requires --confirm "+ACK_RESTAGE)
        if not a.sites: fail("restage-interrupted requires explicit --sites")
        sites=pick(a.sites); ok,h=table("PREFLIGHT AD400",sites,ad400_one)
        if h: fail("AD400 incomplete for "+",".join(h))
        _,h2=table("PREFLIGHT INTERRUPTED STAGE",sites,interrupted_one)
        if h2: fail("not a recoverable interrupted stage: "+",".join(h2))
        return batch("RESTAGE-INTERRUPTED",sites,lambda s,_:restage_interrupted_one(s,ok[s]),None)
    if a.action=="stage-normal":
        if a.confirm!=ACK_STAGE: fail("requires --confirm "+ACK_STAGE)
        sites=pick(a.sites); ok,h=table("PREFLIGHT AD400",sites,ad400_one)
        if h: fail("AD400 incomplete for "+",".join(h)+"; use --sites with PASS sites only")
        return batch("STAGE-NORMAL",sites,lambda s,_:stage_normal_one(s,ok[s]),None)
    stack=stack_guard()
    if a.action=="submit-ad5":
        if a.confirm!=ACK_AD5: fail("requires --confirm "+ACK_AD5)
        return batch("SUBMIT-AD5",pick(a.sites,("BR-Ma2","CA-Ca3","CA-LP1")),submit_ad5_one,stack)
    if a.action=="continue-ad395":
        if a.confirm!=ACK_AD395: fail("requires --confirm "+ACK_AD395)
        sites=pick(a.sites); ok,h=table("PREFLIGHT AD5",sites,ad5_one)
        if h: fail("AD5 not verified for "+",".join(h)+"; use --sites with PASS sites only")
        return batch("CONTINUE-AD395",sites,lambda s,st:continue_ad395(s,ok[s],st),stack)
    if a.action=="submit-normal5":
        if a.confirm!=ACK_N5: fail("requires --confirm "+ACK_N5)
        return batch("SUBMIT-NORMAL5",pick(a.sites),submit_normal5,stack)
    if a.action=="continue-normal395":
        if a.confirm!=ACK_N395: fail("requires --confirm "+ACK_N395)
        sites=pick(a.sites); ok,h=table("PREFLIGHT NORMAL5",sites,normal5_one)
        if h: fail("Normal5 not verified for "+",".join(h))
        return batch("CONTINUE-NORMAL395",sites,lambda s,st:continue_normal395(s,ok[s],st),stack)


if __name__=="__main__":
    main()
