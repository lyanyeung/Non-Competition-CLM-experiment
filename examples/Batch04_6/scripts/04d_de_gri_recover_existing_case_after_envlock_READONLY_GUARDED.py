#!/usr/bin/env python3
"""Stage04D: guarded salvage of existing DE-Gri Batch04 AD400 case after XML-lock error.

Never reclones, changes original template, launches CIME or submits Slurm.
The ONLY new-case file restored is env_case.xml, from its own LockedFiles copy,
and only if all other semantically relevant XML content matches.
Then verifies original Stage04C expected CIME, DATM and FATES inputs.
Writes an auditable receipt only on full technical validation; science HOLD persists.
"""
from __future__ import annotations
import argparse,copy,hashlib,importlib.util,json,os,shutil,subprocess,tempfile
import xml.etree.ElementTree as ET
from datetime import datetime,timezone
from pathlib import Path

B=Path("/iridisfs/scratch/ly3n24/CLM_FATES")
CASE=B/"cases/DE-Gri_ICOS_B04_FIXNC_AD400_DIRECT"
TEMPLATE=B/"cases/DE-Gri_FATES_SPINUP1000_S30SHARED"
ROOT=B/"experiments/Batch04_DE_Gri_AD400_DIRECT_preparation"
LEDGER=ROOT/"stage04c_prepare_state.json"
ORIGINAL_BLOB="0e6e5ab0d8469f4d2261555a0773b87bc178e5ba"
EXPECTED_STAGE="STAGE04A_BATCH04_DE_GRI_DIRECT_AD400_TECHNICAL_PREFLIGHT"
ACK="RECOVER_DE_GRI_STAGE04C_EXISTING_CASE_NO_SLURM"
def need(v,m):
    if not v:raise RuntimeError(m)
def digest(path):
    h=hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda:f.read(1048576),b""):h.update(chunk)
    return h.hexdigest()
def gitblob(path):
    b=Path(path).read_bytes()
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()
def load_module(path):
    need(Path(path).is_file() and gitblob(path)==ORIGINAL_BLOB,"Source Stage04C SHA not verified")
    spec=importlib.util.spec_from_file_location("stage04c_pinned",path)
    m=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    need(m.CASE==CASE and m.LEDGER==LEDGER and m.TEMPLATE==TEMPLATE,"Stage04C source targets changed")
    return m
def getentry(root,key):
    found=[x for x in root.iter("entry") if x.get("id")==key]
    need(len(found)==1,"XML entry missing/ambiguous "+key)
    return found[0].get("value","")
def signature(x):
    return (x.tag,tuple(sorted(x.attrib.items())),(x.text or "").strip(),
            tuple(signature(c) for c in x))
def without_lnd(root):
    root=copy.deepcopy(root)
    removed=[]
    def go(parent):
        for c in list(parent):
            if c.tag=="entry" and c.attrib.get("id")=="COMP_ROOT_DIR_LND":
                parent.remove(c);removed.append(1)
            else:go(c)
    go(root)
    need(len(removed)==1,"Unexpected COMP_ROOT_DIR_LND XML structure")
    return signature(root)
def differences(env,lock):
    left={x.attrib["id"]:x.attrib.get("value") for x in env.iter("entry") if x.get("id")}
    right={x.attrib["id"]:x.attrib.get("value") for x in lock.iter("entry") if x.get("id")}
    return [{"key":k,"new_case":left.get(k),"locked":right.get(k)}
            for k in sorted(set(left)|set(right)) if left.get(k)!=right.get(k)]
def inspect(stage04a,mod):
    stage=Path(stage04a).resolve(strict=True)
    r=json.loads(stage.read_text())
    need(r.get("stage")==EXPECTED_STAGE and r.get("site")=="DE-Gri"
         and r.get("science_release") is False and r.get("AD400_submission_authorized") is False,
         "Stage04A not original science-HOLD evidence")
    need(LEDGER.is_file() and not LEDGER.is_symlink(),"Stage04C original ledger absent")
    led=json.loads(LEDGER.read_text(encoding="utf-8"))
    need(led.get("phase")=="PREPARATION_ATTEMPT_UNCERTAIN",
         "Stage04C ledger is not original uncertain preparation: "+str(led.get("phase")))
    need(Path(led.get("case",""))==CASE
         and Path(led.get("source_stage04a","")).resolve()==stage,
         "Original attempted case/evidence mismatch")
    need(CASE.is_dir() and not CASE.is_symlink(),"Expected cloned case missing")
    e=CASE/"env_case.xml"; l=CASE/"LockedFiles/env_case.xml"
    need(all(p.is_file() and not p.is_symlink() for p in (e,l)),
         "New case env_case or lock missing/symlink")
    en=ET.parse(e).getroot();lock=ET.parse(l).getroot()
    root=getentry(lock,"COMP_ROOT_DIR_LND")
    need(root=="$SRCROOT" or (Path(root).is_absolute() and Path(root).resolve()==mod.CTSM.resolve()),
         "Locked COMP_ROOT_DIR_LND not original CTSM root: "+root)
    diff=differences(en,lock)
    sem=without_lnd(en)==without_lnd(lock)
    status=CASE/"CaseStatus"
    if status.is_file():
        stat=status.read_text(errors="replace").lower()
        need("case.submit starting" not in stat and "case.run starting" not in stat,
             "NEW CASE already has a CIME submit/run attempt: stop")
    need(mod.xq(CASE,"RESUBMIT")=="0","RESUBMIT unexpectedly not zero")
    run=mod.RUN
    need(not list(run.glob("rpointer*")) and not list(run.glob("*.r.*.nc")),
         "New case has restart; possible previous run")
    # Config-only XML compare; never copy lock if non-LND content differs.
    result={"stage":"STAGE04D_DE_GRI_RECOVER_CIME_LOCK_DIAGNOSTIC",
        "case":str(CASE),"stage04a":str(stage),"phase_before":led["phase"],
        "env_sha":digest(e),"lock_sha":digest(l),"lock_root":root,
        "xml_attribute_entry_differences":diff,
        "all_other_XML_elements_semantically_identical":sem,
        "repair_eligible":sem,"science_release":False,"Slurm_submitted":False,
        "note":"Only restore env_case.xml from its own locked copy, never alter LockedFiles"}
    print("STAGE04D LOCK FORENSICS: env_hash",result["env_sha"],"locked_hash",result["lock_sha"])
    print("  LOCK_COMP_ROOT_DIR_LND",root)
    for d in diff[:20]:print("  XML_VALUE_DIFF",json.dumps(d,ensure_ascii=False))
    print("  ALL_OTHER_XML_SEMANTICS_IDENTICAL",sem)
    print("  RECOVER_ELIGIBLE",sem,"STAGE04C_PHASE",led["phase"])
    return result,r,led
def recover(stage04a,code,confirm):
    need(confirm==ACK,"Explicit recovery confirmation missing")
    mod=load_module(code)
    facts,r,old=inspect(stage04a,mod)
    need(facts["repair_eligible"],"Other env_case.xml fields differ; manual forensic review required, NO EDIT")
    e=CASE/"env_case.xml"; lock=CASE/"LockedFiles/env_case.xml"
    # Keep independent evidence copies, never delete a partially prepared case.
    proof=Path(tempfile.mkdtemp(prefix="ICOS_Batch04_stage04d_recovery_",dir=Path.home()))
    for name,path in (("env_case_before.xml",e),("env_case_locked.xml",lock),("prepare_ledger_before.json",LEDGER)):
        shutil.copy2(path,proof/name)
    report=proof/"stage04d_private_evidence.json"
    facts["private_evidence_dir"]=str(proof)
    with report.open("x",encoding="utf-8") as f:json.dump(facts,f,indent=2);f.write("\n")
    if digest(e)!=digest(lock):
        # Atomic restore ONLY in new isolated case; locked config already validated.
        temp=e.with_name("env_case.xml.stage04d_restore_tmp")
        need(not temp.exists() and not temp.is_symlink(),"Unexpected temporary recovery file")
        try:
            with temp.open("xb") as f:
                f.write(lock.read_bytes());f.flush();os.fsync(f.fileno())
            os.replace(temp,e)
        finally:
            if temp.exists():temp.unlink()
    need(digest(e)==digest(lock),"Exact CIME XML lock restore FAILED")
    # Reuse the exact old code's Stage04C verification; no CIME preview or case.submit.
    context={
      "expected_inputs":r["annual_DATM_22_path_list"],
      "surface":r["candidate_surface"],
      "surface_sha256":r["candidate_surface_sha256"],
      "param":str(mod.source_param()),
      "param_sha256":digest(mod.source_param()),
      "executable":mod.xq(TEMPLATE,"EXEROOT")+"/cesm.exe"
    }
    result=mod.verify(context)
    result.update({"phase":"PREPARED_VERIFIED_NOT_SUBMITTED",
        "source_stage04a":str(Path(stage04a).resolve()),"template":str(TEMPLATE),
        "source_science_HOLD":True,"run_target":"DIRECT_AD400_80x5_NO_AD5",
        "PFT_surface":context["surface"],"FATES_param":context["param"],
        "PFT_surface_sha256":context["surface_sha256"],
        "FATES_param_sha256":context["param_sha256"],
        "recovered_from":"STAGE04C_XML_LOCK_AFTER_PREVIEW",
        "recovery_evidence":str(proof),"recovery_utc":datetime.now(timezone.utc).isoformat(),
        "manual_science_decisions":["49 MDS source HOLD episodes","12 precipitation accumulation semantics",
                                    "independent soil representativeness","constant CO2 selection"],
        "Slurm_submitted":False,"science_release":False})
    # Durable ledger must only be marked verified when ALL checks have passed.
    tmp=LEDGER.with_name("stage04c_prepare_state.json.stage04d_write_tmp")
    need(not tmp.exists() and not tmp.is_symlink(),"Unexpected ledger temporary file")
    try:
        with tmp.open("x",encoding="utf-8") as f:
            json.dump(result,f,indent=2);f.write("\n");f.flush();os.fsync(f.fileno())
        os.replace(tmp,LEDGER)
    finally:
        if tmp.exists():tmp.unlink()
    print("STAGE04D RECOVERY PASS | NEW CASE VERIFIED, NO SLURM, NO AD5")
    print("  CASE",CASE)
    print("  22 DATM INPUT PATHS VERIFIED IN GENERATED STREAM (includes corrected 2011/2024)")
    print("  FATES AD state verified, CIME env lock restored")
    print("  STATE",LEDGER,"PREPARED_VERIFIED_NOT_SUBMITTED")
    print("  PRIVATE_BACKUP",proof)
    print("  SCIENCE HOLD persists; AD400 submission not authorized by this stage")
def selftest():
    a=ET.fromstring('<root><entry id="a" value="1"/><entry id="COMP_ROOT_DIR_LND" value="x"/></root>')
    b=ET.fromstring('<root><entry id="a" value="1"/><entry id="COMP_ROOT_DIR_LND" value="y"/></root>')
    assert without_lnd(a)==without_lnd(b)
    assert len(differences(a,b))==1
    b.find("entry").set("value","2")
    assert without_lnd(a)!=without_lnd(b)
    assert not all(x.get("value") is None for x in a.iter("entry"))
    print("STAGE04D SELF-TEST PASS | unrelated XML changes rejected, NO CASE CHANGES")
def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("action",choices=("self-test","diagnose","recover"))
    p.add_argument("--stage04a",type=Path)
    p.add_argument("--stage04c-code",type=Path)
    p.add_argument("--confirm")
    a=p.parse_args()
    if a.action=="self-test":selftest();return
    need(a.stage04a is not None and a.stage04c_code is not None,
         "--stage04a and --stage04c-code required")
    if a.action=="diagnose":
        mod=load_module(a.stage04c_code)
        inspect(a.stage04a,mod)
    else:recover(a.stage04a,a.stage04c_code,a.confirm)
if __name__=="__main__":main()
