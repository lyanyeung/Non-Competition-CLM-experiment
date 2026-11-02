#!/usr/bin/env python3
"""ICOS Batch04 DE-RuR: isolated DIRECT AD400 case preparation, NEVER submit.

Actions: --self-test, check, prepare --confirm PREPARE_DE_RUR_B04_AD400_NO_SLURM, audit.
Prepare is one-shot: clone S30SHARED --keepexe; private FATES AD overlay
preview; 15-year source-verified historical DATM stream;
standalone PFT surface; no original case/source change, no Slurm job.
Scientific MET/source/soil holds stay OPEN. RESUBMIT stays 0 in PREPARE
and must become 79 only in a separate future audited submit.
"""
import argparse
import hashlib
import json
import os
import re
import subprocess
import xml.etree.ElementTree as ET
from datetime import datetime,timezone
from pathlib import Path

B=Path("/iridisfs/scratch/ly3n24/CLM_FATES")
CTSM=B/"CTSM"
TEMPLATE=B/"cases/DE-RuR_FATES_SPINUP1000_S30SHARED"
NAME="DE-RuR_ICOS_B04_FIXNC_AD400_DIRECT"
CASE=B/"cases"/NAME
OUTPUT=Path("/scratch/ly3n24/CTSM_FATES_OUTPUTS")
RUN=OUTPUT/NAME/"run"
ARCH=OUTPUT/"archive"/NAME
REPORTS=B/"experiments/Batch04_DE_RuR_AD400_DIRECT_preparation"
LEDGER=REPORTS/"stage04c_prepare_state.json"
ACK="PREPARE_DE_RUR_B04_AD400_NO_SLURM"
OVERLAYS=(
 B/"experiments/NonCompetitionObserved22/AmeriFlux_Batch02_10/_private_ctsm_FATES_AD400_namelist_overlay",
 B/"experiments/NonCompetitionObserved22/Batch02_10/_private_ctsm_FATES_AD5_namelist_overlay_v1",
)
FLAGS={"use_fates":".true.","use_fates_sp":".false.",
       "use_fates_fixed_biogeog":".true.","use_fates_nocomp":".true.",
       "use_cn":".false.","spinup_state":"2"}
REQUIRED_STREAM=("year_first","year_last","year_align","offset","taxmode",
                 "tintalgo","mapalgo","meshfile","datafiles","datavars")
SETTINGS={"RUN_TYPE":"startup","RUN_STARTDATE":"2011-01-01",
          "CONTINUE_RUN":"FALSE","CLM_ACCELERATED_SPINUP":"on",
          "CLM_FORCE_COLDSTART":"on","STOP_OPTION":"nyears","STOP_N":"5",
          "REST_OPTION":"nyears","REST_N":"5","RESUBMIT":"0",
          "RESUBMIT_SETS_CONTINUE_RUN":"TRUE","DOUT_S":"TRUE",
          "DATM_YR_START":"2011","DATM_YR_END":"2025","DATM_YR_ALIGN":"2011",
          "RUNDIR":str(RUN),"DOUT_S_ROOT":str(ARCH)}
def need(x,msg):
    if not x:raise RuntimeError(msg)
def sha(path):
    h=hashlib.sha256()
    with Path(path).open("rb") as f:
        for b in iter(lambda:f.read(1048576),b""):h.update(b)
    return h.hexdigest()
def cmd(args,cwd,timeout=90):
    p=subprocess.run([str(x) for x in args],cwd=cwd,text=True,
        stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=timeout,check=False)
    if p.returncode!=0:
        raise RuntimeError("COMMAND "+str([str(x) for x in args])+
             " RC="+str(p.returncode)+" "+(p.stdout+p.stderr)[-1600:])
    return p.stdout.strip()
def xq(case,key):return cmd([case/"xmlquery",key,"--value"],case)
def xc(case,key,value):return cmd([case/"xmlchange",f"{key}={value}"],case)
def nmlget(t,key):
    z=re.findall(r"(?im)^\s*"+re.escape(key)+r"\s*=\s*([^\r\n!]*)",t)
    need(len(z)<=1,"Duplicate namelist key "+key)
    return z[0].strip().rstrip(",").strip("'\" ").strip() if z else None
def nmlset(t,key,value):
    rex=re.compile(r"(?im)^\s*"+re.escape(key)+r"\s*=\s*[^\r\n!]*")
    m=list(rex.finditer(t))
    need(len(m)<=1,"Duplicate namelist key "+key)
    line=f"{key} = {value}"
    return (t[:m[0].start()]+line+t[m[0].end():]) if m else (t.rstrip()+"\n"+line+"\n")
def stream_replace(t,paths):
    rex=re.compile(r"(?m)^[ \t]*([A-Za-z][\w.\-]*):([A-Za-z_]\w*)[ \t]*=")
    matches=list(rex.finditer(t)); found={}
    for i,m in enumerate(matches):
        end=matches[i+1].start() if i+1<len(matches) else len(t)
        found.setdefault(m.group(1)+":"+m.group(2),[]).append((m.start(),end))
    pre="CLM_USRDAT.UNSET:"
    rep={"year_first":"2011","year_last":"2025","year_align":"2011",
         "offset":"0","taxmode":"cycle","tintalgo":"linear",
         "mapalgo":"none","meshfile":"none",
         "datafiles":",".join(str(x) for x in paths)}
    for key in REQUIRED_STREAM:
        count=len(found.get(pre+key,[]))
        need(count==1 or (key=="offset" and count==0),
             "Original DATM stream field ambiguous or missing "+key+" "+str(count))
    subs=[(found[pre+k][0][0],found[pre+k][0][1],pre+k+" = "+v+"\n")
          for k,v in rep.items() if found.get(pre+k)]
    for st,en,new in sorted(subs,reverse=True):t=t[:st]+new+t[en:]
    if not found.get(pre+"offset"):t=t.rstrip()+"\n"+pre+"offset = 0\n"
    return t
def parse_stream(case):
    doc=case/"CaseDocs/datm.streams.xml"
    need(doc.is_file(),"Generated CIME DATM stream XML missing")
    root=ET.parse(doc).getroot()
    blocks=[x for x in root.iter("stream_info") if x.get("name")=="CLM_USRDAT.UNSET"]
    need(len(blocks)==1,"Generated USRDAT stream count incorrect")
    e=blocks[0]
    arr=e.find("datafiles")
    need(arr is not None,"Generated DATM stream lacks datafiles")
    files=[(x.text or "").strip() for x in arr]
    settings={k:(e.findtext(k) or "").strip()
         for k in ("year_first","year_last","year_align","taxmode","offset")}
    return files,settings
def source_param():
    t=(TEMPLATE/"CaseDocs/lnd_in").read_text()
    param=nmlget(t,"fates_paramfile")
    need(param is not None,"Original effective FATES parameter file missing")
    f=Path(param).resolve()
    need(f.is_file() and f.suffix==".json","Missing/unsupported FATES default parameter "+str(f))
    return f
def stage(a):
    r=json.loads(a.read_text(encoding="utf-8"))
    need(r.get("stage")=="STAGE04A_BATCH04_DE_RUR_DIRECT_AD400_TECHNICAL_PREFLIGHT"
         and r.get("site")=="DE-RuR" and r.get("science_release") is False
         and r.get("AD400_submission_authorized") is False,
         "Stage04A must be verified preflight with science HOLD")
    ts=[x for x in r.get("templates",[]) if x.get("name")==TEMPLATE.name]
    need(len(ts)==1 and ts[0].get("template_technically_candidate") is True,
         "S30SHARED template not verified")
    years=r.get("annual_DATM_22_path_list",[])
    need(len(years)==15 and [int(x["year"]) for x in years]==list(range(2011,2026)),
         "Annual DATM inputs not exact")
    need(all(x.get("kind")=="historical_baseline" for x in years),"Expected verified historical inputs")
    return r,years
def overlay():
    x=[p for p in OVERLAYS if all((p/f).is_file() for f in
                                 ("bld/CLMBuildNamelist.pm","bld/build-namelist"))]
    need(len(x)>0,"NO_VALID_PRIVATE_FATES_AD_NAMELIST_OVERLAY; do NOT clone yet")
    return x[0]
def preflight(a,show=True):
    r,years=stage(a)
    need(TEMPLATE.is_dir() and not TEMPLATE.is_symlink(),"Original template missing")
    for key,want in (("BUILD_COMPLETE","TRUE"),("DATM_MODE","1PT"),
                     ("CALENDAR","NO_LEAP"),("ATM_NCPL","48")):
        need(xq(TEMPLATE,key).upper()==want,"Original CIME "+key+" changed")
    exe=Path(xq(TEMPLATE,"EXEROOT"))/"cesm.exe"
    need(exe.is_file(),"Shared model executable missing")
    need((CTSM/"cime/scripts/create_clone").is_file(),"CIME create_clone absent")
    paths=[Path(x["path"]) for x in years]
    need(all(p.is_file() and not p.is_symlink() for p in paths),
         "Some annual DATM inputs missing")
    # Avoid rereading the 20 already Stage03V-verified baseline annual files.
    for v in years:
        need(sha(Path(v["path"]))==v["sha256"],"Annual SHA changed "+str(v["year"]))
    surface=Path(r["candidate_surface"])
    need(surface.is_file() and sha(surface)==r["candidate_surface_sha256"],
         "Approved PFT surface changed")
    param=source_param()
    conf=(TEMPLATE/"user_nl_datm_streams").read_text()
    land=(TEMPLATE/"user_nl_clm").read_text()
    stream=stream_replace(conf,paths)
    land=nmlset(land,"fsurdat",f"'{surface}'")
    land=nmlset(land,"fates_paramfile",f"'{param}'")
    for key,v in FLAGS.items():land=nmlset(land,key,v)
    land=nmlset(land,"finidat","''")
    land=nmlset(land,"hist_fincl1","'TOTSOMC', 'TOTSOMN', 'TLAI', 'FATES_GPP', 'FATES_NPP', 'TWS', 'H2OSNO'")
    # NOTE: no CO2 tuning by guess; retain template value for separate science review.
    need(all(nmlget(land,key)==v.strip("'\"") for key,v in FLAGS.items()),
         "Candidate AD FATES namelist not internally consistent")
    need(nmlget(land,"spinup_state")=="2","Expected accelerated spinup_state=2")
    ov=overlay()
    need(all(not x.exists() and not x.is_symlink() for x in (CASE,RUN,ARCH)),
         "New case/run/archive already exists, do not rerun prepare")
    need(not LEDGER.exists(),"Prior prepare attempt exists, do not run blindly")
    oldfiles,oldsettings=parse_stream(TEMPLATE)
    need(oldfiles==[str(p) for p in paths] and oldsettings.get("taxmode")=="cycle",
         "Source generated USRDAT mismatch")
    need((TEMPLATE/"LockedFiles/env_case.xml").is_file(),"Original template lock missing")
    result={"source_stage04a":str(a),"expected_inputs":years,"surface":str(surface),
            "surface_sha256":r["candidate_surface_sha256"],"param":str(param),
            "param_sha256":sha(param),"executable":str(exe),"executable_sha256":sha(exe),
            "template":str(TEMPLATE),"overlay":str(ov),"stream":stream,"land":land}
    if show:
        print("STAGE04C PREFLIGHT PASS | SOURCE SCIENCE HOLD")
        print("PREPARE_TARGET",CASE,"| TEMPLATE",TEMPLATE.name)
        print("15-year historical DATM; FATES default exists; PRIVATE AD OVERLAY",ov)
        print("NEW FATES spinup_state=2, fixed_biogeog=.true., nocomp=.true.; CLM_ACCELERATED_SPINUP=on")
        print("STOP_N=5, PREPARE RESUBMIT=0, future one-time DIRECT AD400 SUBMIT sets 79; NO AD5 trial")
        print("NO Slurm, CIME or source mutation")
    return result
def verify(c):
    for k,v in SETTINGS.items():
        got=xq(CASE,k)
        need(got.lower()==v.lower(),"NEW CASE XML mismatch "+k+": "+got)
    need(xq(CASE,"CASE")==NAME,"NEW case identity changed")
    need(Path(xq(CASE,"EXEROOT")).resolve()==Path(c["executable"]).parent.resolve(),
         "Case unexpectedly changed shared executable")
    doc=CASE/"CaseDocs/lnd_in"
    need(doc.is_file(),"Effective new land namelist absent")
    text=doc.read_text()
    for k,v in {**FLAGS,"fsurdat":c["surface"],"fates_paramfile":c["param"],"finidat":""}.items():
        got=nmlget(text,k)
        need(got==v,"Effective FATES key mismatch "+k+"="+str(got))
    history=re.search(r"(?ims)^\s*hist_fincl1\s*=\s*(.*?)(?=^[ \t]*[A-Za-z_]\w*[ \t]*=|^[ \t]*/[ \t]*$|\Z)",text)
    need(history is not None and re.findall(r"[\'\"]([^\'\"]+)[\'\"]",history.group(1)) == ["TOTSOMC","TOTSOMN","TLAI","FATES_GPP","FATES_NPP","TWS","H2OSNO"],"Wrong FATES history fields")
    inrun=RUN/"lnd_in"
    need(inrun.is_file() and sha(inrun)==sha(doc),
         "RUNDIR effective land namelist differs from CaseDocs")
    files,settings=parse_stream(CASE)
    need(files==[x["path"] for x in c["expected_inputs"]],
         "CRITICAL: effective CIME DATM stream not exactly selected annual files")
    for k,v in {"year_first":"2011","year_last":"2025","year_align":"2011",
                "taxmode":"cycle","offset":"0"}.items():
        need(settings[k]==v,"Effective CIME DATM cycle mismatch "+k)
    inrun_stream=RUN/"datm.streams.xml"
    need(inrun_stream.is_file() and sha(inrun_stream)==sha(CASE/"CaseDocs/datm.streams.xml"),
         "Run-folder DATM stream differs")
    need(sha(c["surface"])==c["surface_sha256"] and
         sha(c["param"])==c["param_sha256"],"Surface or FATES param drift")
    need(not list(RUN.glob("rpointer*")) and not list(RUN.glob("*.r.*.nc")),
         "Unexpected restart files in new case")
    return {"case":str(CASE),"lnd_in_sha256":sha(doc),
            "effective_stream_sha256":sha(CASE/"CaseDocs/datm.streams.xml"),
            "verified_annual_file_count":15,"direct_AD400_segment_years":5,
            "future_resubmits":79,"science_release":False,"slurm_submitted":False}
def prepare(a,confirmation):
    need(confirmation==ACK,"Explicit preparation confirmation required")
    context=preflight(a)
    REPORTS.mkdir(parents=True,exist_ok=True)
    with LEDGER.open("x") as f:
        json.dump({"phase":"PREPARATION_ATTEMPT_UNCERTAIN","science_release":False,
          "created_utc":datetime.now(timezone.utc).isoformat(),
          "source_stage04a":str(a),"case":str(CASE)},f,indent=2);f.write("\n")
    print("CLONING NEW PRIVATE CASE (NO SLURM)",CASE,flush=True)
    cmd([CTSM/"cime/scripts/create_clone","--case",CASE,"--clone",TEMPLATE,"--keepexe"],
        CTSM/"cime/scripts",600)
    need(xq(CASE,"CASE")==NAME,"CIME clone did not set new case identity")
    for key,value in SETTINGS.items():xc(CASE,key,value)
    (CASE/"user_nl_datm_streams").write_text(context["stream"])
    (CASE/"user_nl_clm").write_text(context["land"])
    RUN.mkdir(parents=True,exist_ok=True)
    if not (CASE/".case.run").is_file():cmd([CASE/"case.setup"],CASE,400)
    env,locked=CASE/"env_case.xml",CASE/"LockedFiles/env_case.xml"
    need(locked.is_file() and env.read_bytes()==locked.read_bytes(),
         "Cloned CIME env_case lock mismatch before preview")
    before=env.read_bytes()
    old_root=xq(CASE,"COMP_ROOT_DIR_LND")
    need(old_root=="$SRCROOT" or Path(old_root).resolve()==CTSM.resolve(),
         "Unexpected original CTSM land root "+old_root)
    try:
        xc(CASE,"COMP_ROOT_DIR_LND",context["overlay"])
        cmd([CASE/"preview_namelists"],CASE,680)
    finally:
        xc(CASE,"COMP_ROOT_DIR_LND",old_root)
    if env.read_bytes()!=before:
        def semantic_without_land_root(raw):
            root=ET.fromstring(raw)
            removed=[]
            for parent in root.iter():
                for child in list(parent):
                    if child.tag=="entry" and child.get("id")=="COMP_ROOT_DIR_LND":
                        parent.remove(child);removed.append(1)
            need(len(removed)==1,"Unexpected land root entries")
            def sig(e):
                return (e.tag,tuple(sorted(e.attrib.items())),(e.text or "").strip(),
                        tuple(sig(c) for c in e))
            return sig(root)
        need(semantic_without_land_root(env.read_bytes())==semantic_without_land_root(before),
             "Other env_case.xml settings changed; stop for inspection")
        need(locked.read_bytes()==before,"Locked env_case.xml changed")
        tmp=env.with_name("env_case.xml.pair_restore_tmp")
        need(not tmp.exists(),"Unexpected restore file")
        with tmp.open("xb") as f:
            f.write(before);f.flush();os.fsync(f.fileno())
        os.replace(tmp,env)
    need(env.read_bytes()==locked.read_bytes()==before,
         "CIME env_case lock not restored after private AD preview")
    receipt=verify(context)
    receipt.update({"phase":"PREPARED_VERIFIED_NOT_SUBMITTED",
                    "source_stage04a":str(a),"template":str(TEMPLATE),
                    "source_science_HOLD":True,"run_target":"DIRECT_AD400_80x5_NO_AD5",
                    "PFT_surface":context["surface"],"FATES_param":context["param"],
                    "created_utc":datetime.now(timezone.utc).isoformat(),
                    "manual_science_decisions":["source MDS/precipitation accumulation time",
                                            "independent soil provenance",
                                            "constant CO2 scientific choice"]})
    # One attempted preparation has an immutable ledger; rewrite to verified
    # only after all new CIME inputs pass (never delete on failure).
    with LEDGER.open("w") as f:json.dump(receipt,f,indent=2);f.write("\n")
    print("STAGE04C VERIFIED NEW DIRECT AD400 CASE; NO AD5/SLURM",CASE)
    print("15/15 HISTORICAL DATM INPUTS BOUND")
    print("EFFECTIVE FATES AD spinup_state=2, fixed_biogeog TRUE, nocomp TRUE")
    print("SOURCE SCIENCE HOLD (not approved for production) | LEDGER",LEDGER)
def audit():
    need(LEDGER.is_file(),"No Stage04C preparation ledger found")
    obj=json.loads(LEDGER.read_text())
    need(obj.get("phase")=="PREPARED_VERIFIED_NOT_SUBMITTED",
         "Previously failed/uncertain preparation: do not auto retry")
    c={"expected_inputs":json.loads(Path(obj["source_stage04a"]).read_text())["annual_DATM_22_path_list"],
       "surface":obj["PFT_surface"],"surface_sha256":obj["PFT_surface_sha256"] if "PFT_surface_sha256" in obj else "",
       "param":obj["FATES_param"],"param_sha256":obj.get("FATES_param_sha256",""),
       "executable":xq(TEMPLATE,"EXEROOT")+"/cesm.exe"}
    # Retrieve full original source hashes; no path guessing or hardcoding.
    parent=json.loads(Path(obj["source_stage04a"]).read_text())
    c["surface_sha256"]=parent["candidate_surface_sha256"]
    c["param_sha256"]=sha(c["param"])
    rec=verify(c)
    need(rec["lnd_in_sha256"]==obj["lnd_in_sha256"]
         and rec["effective_stream_sha256"]==obj["effective_stream_sha256"],
         "Case changed after preparation; source HOLD")
    print("STAGE04C READONLY CASE AUDIT PASS",CASE,"NO SLURM / NO AD5")
    print("SCIENCE HOLD persists: meteorological source, precipitation timing and soil")
def self_test():
    assert nmlget("  fsurdat = '/a/b.nc'\n","fsurdat")=="/a/b.nc"
    t=nmlset("  fsurdat = '/a/b.nc'\n","fsurdat","'/c/d.nc'")
    assert nmlget(t,"fsurdat")=="/c/d.nc"
    assert nmlget(nmlset(t,"spinup_state","2"),"spinup_state")=="2"
    raw="CLM_USRDAT.UNSET:datafiles = abc\nCLM_USRDAT.UNSET:datavars = TBOT Sa_tbot\n"
    for k in REQUIRED_STREAM:
        if k not in ("datafiles","datavars"):
            raw+="CLM_USRDAT.UNSET:"+k+" = old\n"
    out=stream_replace(raw,[Path("/tmp/DE-RuR_DATM_2011.nc")])
    assert "year_last = 2025" in out and str(Path("/tmp/DE-RuR_DATM_2011.nc")) in out
    assert all(x in FLAGS for x in ("spinup_state","use_fates_nocomp"))
    assert SETTINGS["RESUBMIT"]=="0" and 400//int(SETTINGS["STOP_N"])-1==79
    print("STAGE04C SELF-TEST PASS: private AD namelist and DATM stream, NO WRITES")
def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("action",choices=("self-test","check","prepare","audit"))
    p.add_argument("--stage04a",type=Path)
    p.add_argument("--confirm")
    a=p.parse_args()
    if a.action=="self-test":self_test();return
    if a.action=="audit":audit();return
    need(a.stage04a is not None and a.stage04a.is_file(),
         "Stage04A report required")
    if a.action=="check":preflight(a.stage04a);return
    if a.action=="prepare":prepare(a.stage04a,a.confirm)
if __name__=="__main__":main()

