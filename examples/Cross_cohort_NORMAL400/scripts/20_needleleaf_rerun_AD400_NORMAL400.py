#!/usr/bin/env python3
"""Rerun AD400 -> NORMAL400 with the adopted needleleaf parameters (fix F) at every site that contains PFT 2,
and remove the old (default-parameter) model output of those sites.

Decision 2026-11-02 (docs/NEEDLELEAF_COLLAPSE_DIAGNOSIS.md, section 9): PFT 2 storage cushion 2.4, slatop 0.008.
The 41 sites below are those with a needleleaf evergreen share in the 75-site screening; each is checked again
against its surface data (PFT-2 share > 0) before anything is created.

New cases (originals are never modified; only their large .nc output is removed by purge-old):
  <AD case>_NLF       create_clone --keepexe of the original AD case; 400 years as 80 x 5-year segments; the ONLY
                      namelist change is fates_paramfile -> adopted copy (params_adopted/, script 18). lnd_in must
                      equal the original AD lnd_in on every other key; the DATM streams must equal the ones the original
                      AD run actually read (its RUNDIR copy; carried into the new case when a regenerated file differs).
  <Normal case>_NLF   create_clone --keepexe of the original Normal case, started from the year-400 restarts of
                      <AD>_NLF (copied, sha-checked, rpointers); RUN_REFCASE/finidat/fates_paramfile changed, every other
                      lnd_in key equal to the original Normal; 80 x 5 years.
Actions:
  plan                 READ ONLY: sites, case names, PFT-2 share, parameter file, cold-start check, old jobs in the queue
  ad-run [--sites]     prepare + verify each new AD case, submit only verified ones (never twice)
  normal-run [--sites] for sites whose <AD>_NLF finished 400 years: prepare + verify + submit the Normal case
  purge-old [--sites]  DRY RUN: lists the old .nc output (run + archive of the original AD and Normal cases) and size;
                       with --confirm DELETE_OLD_NEEDLELEAF_OUTPUTS it deletes exactly those files. Only for sites whose
                       new AD case is verified, and whose old cases have no queued jobs. Case directories, CaseDocs,
                       namelists, stream files, logs and every build directory (shared executables!) are kept; a file
                       list is written to the ledger before deleting.
  status
Run long actions with setsid nohup (SSH drops). Ledger: <EXP22>/Needleleaf_F_rerun/.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
import shutil
import xml.etree.ElementTree as ET
from pathlib import Path

HERE = Path(__file__).resolve().parent
SITES = {"BE-Bra": "BE-Bra_B02_FIXNC_ICOS_ENF84_DBF16_NORMAL400", "BE-Vie": "BE-Vie_B01_FIXNC_NORMAL400",
         "CA-Ca3": "CA-Ca3_AMF_FIXNC_NORMAL400_UTC_V2_PTS", "CA-LP1": "CA-LP1_AMF_FIXNC_NORMAL400_UTC_V2_PTS",
         "CA-TP4": "CA-TP4_AMF_FIXNC_NORMAL400_UTC_V3_PTS", "CH-Dav": "CH-Dav_B01_FIXNC_NORMAL400",
         "CH-Lae": "CH-Lae_B02_FIXNC_MET36_GPPNPP_HISTFIX_NORMAL400", "CZ-BK1": "CZ-BK1_B01_FIXNC_NORMAL400",
         "DE-Obe": "DE-Obe_B03_FIXNC_NORMAL400", "DE-Tha": "DE-Tha_OBSPFT_NC_V1_NORMAL400",
         "FI-Hyy": "FI-Hyy_B02_FIXNC_NORMAL400", "FI-Let": "FI-Let_B03_FIXNC_NORMAL400",
         "FI-Sod": "FI-Sod_B01_FIXNC_NORMAL400", "FR-FBn": "FR-FBn_B02_FIXNC_FOREST_GPPNPP_HISTFIX_NORMAL400",
         "FR-Fon": "FR-Fon_B01_FIXNC_NORMAL400", "IL-Yat": "IL-Yat_B03_FIXNC_BARE52_NORMAL400",
         "IT-Lav": "IT-Lav_B03_FIXNC_NORMAL400", "IT-Ren": "IT-Ren_B01_FIXNC_NORMAL400",
         "RU-Fyo": "RU-Fyo_B01_FIXNC_NORMAL400", "US-BZS": "US-BZS_AMF_B02_FIXNC_NORMAL400_DIRECT",
         "US-GLE": "US-GLE_AMF_B02_FIXNC_NORMAL400_DIRECT", "US-Ha1": "US-Ha1_AMF_B02_FIXNC_NORMAL400_DIRECT",
         "US-Ho1": "US-Ho1_AMF_B02_FIXNC_NORMAL400_DIRECT", "US-Ho2": "US-Ho2_AMF_B02_FIXNC_NORMAL400_DIRECT",
         "US-Ho3": "US-Ho3_AMF_B02_FIXNC_NORMAL400_DIRECT", "US-MOz": "US-MOz_AMF_B03_FIXNC_NORMAL400_DIRECT",
         "US-Me2": "US-Me2_AMF_B03_FIXNC_NORMAL400_DIRECT", "US-Me6": "US-Me6_AMF_B03_FIXNC_NORMAL400_DIRECT",
         "US-Mpj": "US-Mpj_AMF_B03_FIXNC_NORMAL400_DIRECT", "US-MtB": "US-MtB_AMF_B03_FIXNC_NORMAL400_DIRECT",
         "US-NC2": "US-NC2_AMF_B03_FIXNC_NORMAL400_DIRECT", "US-NR1": "US-NR1_AMF_B03_FIXNC_NORMAL400_DIRECT",
         "US-SP1": "US-SP1_AMF_B04_FIXNC_NORMAL400_BASETA_V1", "US-Slt": "US-Slt_AMF_B04_FIXNC_NORMAL400_BASETA_V1",
         "US-Syv": "US-Syv_AMF_B04_FIXNC_NORMAL400_BASETA_V1", "US-UMB": "US-UMB_AMF_B05_FIXNC_NORMAL400_DIRECT",
         "US-UMd": "US-UMd_AMF_B05_FIXNC_NORMAL400_DIRECT", "US-Uaf": "US-Uaf_AMF_B04_FIXNC_NORMAL400_BASETA_V1",
         "US-Vcm": "US-Vcm_AMF_B05_FIXNC_NORMAL400_DIRECT", "US-Vcp": "US-Vcp_AMF_B05_FIXNC_NORMAL400_DIRECT",
         "US-Wjs": "US-Wjs_AMF_B05_FIXNC_NORMAL400_DIRECT"}
SUFFIX = "_NLF"
YEARS = 400
STATE = "NLF_STATE.json"
POINTERS = (("rpointer.lnd", "clm2"), ("rpointer.atm", "datm"), ("rpointer.cpl", "cpl"))
CONFIRM = "DELETE_OLD_NEEDLELEAF_OUTPUTS"
M18 = T = R = None


def load():
    global M18, T, R
    spec = importlib.util.spec_from_file_location("adopt18", HERE / "18_adopt_needleleaf_params.py")
    M18 = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(M18)
    M18.load()
    T, R = M18.T, M18.R
    if not hasattr(M18, "ensure_adopted"):
        raise RuntimeError("18_adopt_needleleaf_params.py is too old (no ensure_adopted); download the current version")


def ledger():
    d = R.B / "experiments/NonCompetitionObserved22/Needleleaf_F_rerun"
    d.mkdir(parents=True, exist_ok=True)
    return d


def stamp(y):
    return f"{y:04d}-01-01-00000"


def ident(site):
    n0 = SITES[site]
    ad0 = R.xq(R.CASES / n0, "RUN_REFCASE")
    if not ad0:
        R.fail(f"{n0}: RUN_REFCASE empty")
    i = {"site": site, "ad0": ad0, "n0": n0, "ad": ad0 + SUFFIX, "n": n0 + SUFFIX}
    for k in ("ad0", "n0", "ad", "n"):
        i[k + "_case"] = R.CASES / i[k]
        i[k + "_run"] = R.OUT / i[k] / "run"
        i[k + "_arch"] = R.OUT / "archive" / i[k]
    return i


def jobs(name):
    """Queued/running jobs of exactly this case (run.<case>, st_archive.<case>, ...), not of cases sharing a prefix."""
    out = R.cmd(["squeue", "-u", R.USER, "-h", "-o", "%i|%j|%T"], timeout=45)
    rows = [ln.split("|") for ln in out.splitlines() if ln.count("|") >= 2]
    return [r for r in rows if r[1].split(".", 1)[-1] == name]


def read_state(case):
    p = Path(case) / STATE
    return json.loads(p.read_text()) if p.is_file() else {}


def write_state(case, **kw):
    s = read_state(case)
    s.update(kw, at=R.utc())
    (Path(case) / STATE).write_text(json.dumps(s, indent=2, default=str) + "\n")
    return s


def nml_value(text, key):
    return next((v for k, v in R.parse_nml(text).items() if k.endswith("." + key)), None)


def unq(v):
    return (v or "").strip().strip("'\"").strip()


def streams_sem(path):
    sem = lambda e: (e.tag, tuple(sorted(e.attrib.items())), (e.text or "").strip(), tuple(sem(k) for k in e))
    return sem(ET.parse(path).getroot())


def effective_streams(case):
    """The DATM stream file the run actually read: its RUNDIR copy when present, else CaseDocs."""
    run = Path(R.xq(case, "RUNDIR")) / "datm.streams.xml"
    return run if run.is_file() else case / "CaseDocs" / "datm.streams.xml"


def carry_streams(new_case, new_run, eff):
    """Make the new case read exactly the stream file the original run read; returns a record or None."""
    doc = new_case / "CaseDocs" / "datm.streams.xml"
    if streams_sem(doc) == streams_sem(eff):
        return None
    files = [e.text.strip() for e in ET.parse(eff).getroot().iter("file") if (e.text or "").strip()]
    missing = [f for f in files if not Path(f).is_file()]
    if not files or missing:
        R.fail(f"original stream file lists missing data files ({len(missing)}): {missing[:3]}")
    payload = eff.read_bytes()
    for target in (doc, new_run / "datm.streams.xml"):
        tmp = Path(str(target) + ".tmpNLF")
        tmp.write_bytes(payload)
        tmp.replace(target)
    return {"from": str(eff), "sha256": R.digest(eff), "data_files": len(files)}


def pft2_check(lnd_text):
    base = unq(nml_value(lnd_text, "fates_paramfile"))
    fsur = unq(nml_value(lnd_text, "fsurdat"))
    if not base or not Path(base).is_file():
        R.fail(f"fates_paramfile missing: {base!r}")
    share, how = M18.pft2_share(M18.read_pct(fsur), json.loads(Path(base).read_text()))
    return base, fsur, share, how


def settings(rundir, arch):
    return {"CONTINUE_RUN": "FALSE", "STOP_OPTION": "nyears", "STOP_N": str(R.SEG), "REST_OPTION": "nyears",
            "REST_N": str(R.SEG), "RESUBMIT": str(YEARS // R.SEG - 1), "RESUBMIT_SETS_CONTINUE_RUN": "TRUE",
            "DOUT_S": "TRUE", "RUNDIR": str(rundir), "DOUT_S_ROOT": str(arch)}


def apply_settings(case, sets):
    for k, v in sets.items():
        R.xc(case, k, v)
    for k, v in sets.items():
        if R.xq(case, k).lower() != v.lower():
            R.fail(f"XML {k}={R.xq(case, k)} expected {v}")


def check_new_paths(i, which):
    for p in (i[which + "_case"], i[which + "_run"].parent, i[which + "_arch"]):
        if p.exists():
            R.fail(f"path exists without a completed prepare: {p} (inspect; remove by hand only if it is a failed attempt)")
    if jobs(i[which]):
        R.fail(f"{i[which]}: jobs in the queue")


def clone(src, dst):
    srcroot = R.xq(src, "SRCROOT")
    cs = Path(srcroot) / "cime" / "scripts"
    R.cmd([cs / "create_clone", "--case", dst, "--clone", src, "--keepexe"], cwd=cs, timeout=420)
    write_state(dst, phase="PREPARE_ATTEMPTED")
    if R.xq(dst, "CASE") != dst.name:
        R.fail("clone identity")
    if R.xq(dst, "EXEROOT") != R.xq(src, "EXEROOT"):
        R.fail("executable differs from the original case")


# ------------------------------------------------------------------ AD
def ad_prepare(site):
    i = ident(site)
    case = i["ad_case"]
    print(f"\n=== {site} AD: {i['ad0']} -> {i['ad']}", flush=True)
    if read_state(case).get("phase") not in (None, "PREPARE_ATTEMPTED"):
        print(f"  already {read_state(case)['phase']}; nothing changed", flush=True)
        return i
    check_new_paths(i, "ad")
    ad0 = i["ad0_case"]
    if R.xq(ad0, "CLM_ACCELERATED_SPINUP").lower() != "on":
        R.fail("original AD case is not accelerated spin-up")
    rt = R.xq(ad0, "RUN_TYPE")
    ad_lnd = (ad0 / "CaseDocs" / "lnd_in").read_text()
    fin = unq(nml_value(ad_lnd, "finidat"))
    if rt != "startup" or fin:
        R.fail(f"original AD is not a cold start (RUN_TYPE={rt}, finidat={fin or 'none'}); rerun it by hand")
    base, fsur, share, how = pft2_check(ad_lnd)
    if share <= M18.MIN_PCT:
        R.fail(f"PFT 2 share {share:.2f} % in {fsur}: no needleleaf, no rerun needed")
    param, psha = M18.ensure_adopted(base, [site])
    eff = effective_streams(ad0)
    adv = {k: R.xq(ad0, k) for k in ("RUN_TYPE", "RUN_STARTDATE", "CLM_FORCE_COLDSTART", "EXEROOT", "CLM_BLDNML_OPTS")}
    nl = T.set_paramfile((ad0 / "user_nl_clm").read_text(), param)
    clone(ad0, case)
    sets = settings(i["ad_run"], i["ad_arch"])
    apply_settings(case, sets)
    for k, v in adv.items():
        if R.xq(case, k) != v:
            R.fail(f"clone differs from the original AD in {k}")
    (case / "user_nl_clm").write_text(nl)
    i["ad_run"].mkdir(parents=True, exist_ok=True)
    if not (case / ".case.run").is_file():
        R.cmd([case / "case.setup"], cwd=case, timeout=300)
    overlay, a, n, diff = T.preview_verified(case, ad_lnd, [".fates_paramfile"])
    if unq(nml_value((case / "CaseDocs" / "lnd_in").read_text(), "fates_paramfile")) != str(param):
        R.fail("new lnd_in fates_paramfile is not the adopted file")
    if [k for k in diff if not k.endswith(".fates_paramfile")]:
        R.fail(f"lnd_in differs from the original AD in {diff}")
    carried = carry_streams(case, i["ad_run"], eff)
    if (i["ad_run"] / "lnd_in").is_file() and R.digest(i["ad_run"] / "lnd_in") != R.digest(case / "CaseDocs" / "lnd_in"):
        R.fail("RUNDIR lnd_in differs from CaseDocs")
    write_state(case, phase="VERIFIED_NOT_SUBMITTED", kind="AD400", site=site, original=i["ad0"],
                start=adv["RUN_STARTDATE"], years=YEARS, settings=sets, paramfile=str(param), paramfile_sha256=psha,
                base_paramfile=base, pft2_pct_of_veg=round(share, 2), pft2_mapping=how,
                overlay=str(overlay) if overlay else "none", lnd_in_keys_changed=diff, streams_carried=carried,
                lnd_in_sha256=R.digest(case / "CaseDocs" / "lnd_in"),
                datm_streams_sha256=R.digest(case / "CaseDocs" / "datm.streams.xml"))
    print(f"  PFT2 {share:.1f} % | params {Path(param).name} | lnd_in vs original: only fates_paramfile | "
          f"streams {'carried from the original run' if carried else 'identical'} | {YEARS} y from {adv['RUN_STARTDATE']}",
          flush=True)
    print(f"  {site} AD VERIFIED, NOT SUBMITTED", flush=True)
    return i


def submit(case, name):
    s = read_state(case)
    if s.get("phase") != "VERIFIED_NOT_SUBMITTED":
        R.fail(f"{name}: phase {s.get('phase')}; not submitting")
    if R.digest(case / "CaseDocs" / "lnd_in") != s["lnd_in_sha256"] or R.digest(s["paramfile"]) != s["paramfile_sha256"] \
            or R.digest(case / "CaseDocs" / "datm.streams.xml") != s["datm_streams_sha256"]:
        R.fail(f"{name}: lnd_in, streams or parameter file changed after verification")
    cs = (case / "CaseStatus").read_text(errors="replace") if (case / "CaseStatus").is_file() else ""
    if re.search(r"case\.submit starting|case\.run starting", cs) or jobs(name):
        R.fail(f"{name}: already submitted or jobs exist")
    write_state(case, phase="SUBMIT_ATTEMPTED_UNCERTAIN")
    out = R.cmd([case / "case.submit", "--skip-preview-namelist"], cwd=case, timeout=800)
    r, a = R.RUN_RE.search(out), R.ARCH_RE.search(out)
    if not r:
        R.fail(f"{name}: job id not parsed; DO NOT RETRY, check squeue. " + out[-600:])
    write_state(case, phase="SUBMITTED", run_job=r.group(1), archive_job=a.group(1) if a else "", submit_tail=out[-800:])
    print(f"  SUBMITTED {name} run={r.group(1)} archive={a.group(1) if a else '?'}", flush=True)


def ad_run(site):
    i = ident(site)
    if read_state(i["ad_case"]).get("phase") in ("SUBMITTED", "SUBMIT_ATTEMPTED_UNCERTAIN"):
        print(f"{site}: AD {read_state(i['ad_case'])['phase']}; not submitted again", flush=True)
        return
    ad_prepare(site)
    submit(i["ad_case"], i["ad"])


# ------------------------------------------------------------------ Normal
def restart_state(path):
    import numpy as np
    from netCDF4 import Dataset
    with Dataset(str(path)) as ds:
        if "spinup_state" in ds.variables:
            return int(np.asarray(ds.variables["spinup_state"][:]).ravel()[0])
        if "spinup_state" in ds.ncattrs():
            return int(ds.getncattr("spinup_state"))
    return None


def ad_complete(i):
    """Year-400 restart triplet of <AD>_NLF, nothing queued, last run/archive success, RESUBMIT used up."""
    case, name, arch = i["ad_case"], i["ad"], i["ad_arch"]
    if read_state(case).get("phase") != "SUBMITTED":
        R.fail(f"{name}: not submitted ({read_state(case).get('phase')})")
    if jobs(name):
        R.fail(f"{name}: still running")
    y = int(R.xq(case, "RUN_STARTDATE")[:4]) + YEARS
    folder = arch / "rest" / stamp(y)
    files = {c: folder / f"{name}.{c}.r.{stamp(y)}.nc" for _, c in POINTERS}
    missing = [str(p) for p in files.values() if not p.is_file() or p.stat().st_size < 1024]
    if missing:
        have = sorted(d.name for d in (arch / "rest").iterdir()) if (arch / "rest").is_dir() else []
        R.fail(f"{name}: year-{y} restarts missing (latest {have[-1] if have else 'none'})")
    cs = (case / "CaseStatus").read_text(errors="replace")
    lr, la = re.findall(r"case\.run (success|error)", cs), re.findall(r"st_archive (success|error)", cs)
    if not lr or lr[-1] != "success" or not la or la[-1] != "success" or R.xq(case, "RESUBMIT") != "0":
        R.fail(f"{name}: last run/archive not success or RESUBMIT not exhausted")
    st = restart_state(files["clm2"])
    if st != 2:
        R.fail(f"{name}: final spinup_state {st}, expected 2")
    return y, files


def normal_prepare(site):
    i = ident(site)
    case = i["n_case"]
    print(f"\n=== {site} NORMAL: {i['n0']} -> {i['n']} (from {i['ad']})", flush=True)
    if read_state(case).get("phase") not in (None, "PREPARE_ATTEMPTED"):
        print(f"  already {read_state(case)['phase']}; nothing changed", flush=True)
        return i
    y, files = ad_complete(i)
    check_new_paths(i, "n")
    n0 = i["n0_case"]
    date = f"{y:04d}-01-01"
    if R.xq(n0, "RUN_STARTDATE") != date:
        R.fail(f"original Normal starts {R.xq(n0, 'RUN_STARTDATE')}, the new AD ends {date}")
    n_lnd = (n0 / "CaseDocs" / "lnd_in").read_text()
    ad_state = read_state(i["ad_case"])
    if R.digest(unq(nml_value(n_lnd, "fates_paramfile"))) != R.digest(ad_state["base_paramfile"]):
        R.fail("the original Normal used a different parameter file than the original AD")
    param, psha = Path(ad_state["paramfile"]), ad_state["paramfile_sha256"]
    if R.digest(param) != psha:
        R.fail("adopted parameter file changed since the AD case was verified")
    eff = effective_streams(n0)
    src_sha = {c: R.digest(p) for c, p in files.items()}
    clone(n0, case)
    sets = settings(i["n_run"], i["n_arch"])
    sets.update(RUN_REFCASE=i["ad"], RUN_REFDATE=date, RUN_REFTOD="00000", GET_REFCASE="FALSE")
    apply_settings(case, sets)
    for k in ("RUN_TYPE", "RUN_STARTDATE", "CLM_ACCELERATED_SPINUP", "CLM_FORCE_COLDSTART", "CLM_BLDNML_OPTS"):
        if R.xq(case, k) != R.xq(n0, k):
            R.fail(f"clone differs from the original Normal in {k}")
    if R.xq(case, "CLM_ACCELERATED_SPINUP").lower() != "off":
        R.fail("Normal case has accelerated spin-up on")
    i["n_run"].mkdir(parents=True, exist_ok=True)
    for c, src in files.items():
        dst = i["n_run"] / src.name
        shutil.copy2(src, dst)
        if R.digest(dst) != src_sha[c]:
            R.fail(f"copied restart differs ({c})")
    for ptr, c in POINTERS:
        (i["n_run"] / ptr).write_text(files[c].name + "\n")
    staged = str(i["n_run"] / files["clm2"].name)
    nl = T.set_nml((n0 / "user_nl_clm").read_text(), "finidat", f"'{staged}'")
    nl = T.set_paramfile(nl, param)
    (case / "user_nl_clm").write_text(nl)
    if not (case / ".case.run").is_file():
        R.cmd([case / "case.setup"], cwd=case, timeout=300)
    overlay, a, n, diff = T.preview_verified(case, n_lnd, [".fates_paramfile", ".finidat"])
    extra = [k for k in diff if not k.endswith((".fates_paramfile", ".finidat"))]
    if extra:
        R.fail(f"lnd_in differs from the original Normal in {extra}")
    new = (case / "CaseDocs" / "lnd_in").read_text()
    if unq(nml_value(new, "fates_paramfile")) != str(param) or unq(nml_value(new, "finidat")) != staged:
        R.fail("new Normal lnd_in fates_paramfile / finidat not as staged")
    if unq(nml_value(new, "spinup_state")) not in ("", "0"):
        R.fail("new Normal spinup_state is not 0")
    carried = carry_streams(case, i["n_run"], eff)
    if (i["n_run"] / "lnd_in").is_file() and R.digest(i["n_run"] / "lnd_in") != R.digest(case / "CaseDocs" / "lnd_in"):
        R.fail("RUNDIR lnd_in differs from CaseDocs")
    write_state(case, phase="VERIFIED_NOT_SUBMITTED", kind="NORMAL400", site=site, original=i["n0"], refcase=i["ad"],
                start=date, years=YEARS, settings=sets, paramfile=str(param), paramfile_sha256=psha,
                restart_sha256=src_sha, overlay=str(overlay) if overlay else "none", lnd_in_keys_changed=diff,
                streams_carried=carried, lnd_in_sha256=R.digest(case / "CaseDocs" / "lnd_in"),
                datm_streams_sha256=R.digest(case / "CaseDocs" / "datm.streams.xml"))
    print(f"  from {i['ad']} {stamp(y)} | lnd_in vs original Normal: {', '.join(k.split('.', 1)[1] for k in diff)} | "
          f"streams {'carried' if carried else 'identical'}", flush=True)
    print(f"  {site} NORMAL VERIFIED, NOT SUBMITTED", flush=True)
    return i


def normal_run(site):
    i = ident(site)
    if read_state(i["n_case"]).get("phase") in ("SUBMITTED", "SUBMIT_ATTEMPTED_UNCERTAIN"):
        print(f"{site}: NORMAL {read_state(i['n_case'])['phase']}; not submitted again", flush=True)
        return
    normal_prepare(site)
    submit(i["n_case"], i["n"])


# ------------------------------------------------------------------ old output
def old_nc_files(case_dir, name):
    """Large model output of one ORIGINAL case: *.nc in its RUNDIR and DOUT_S_ROOT. Paths must belong to the case."""
    run = Path(R.xq(case_dir, "RUNDIR"))
    arch = Path(R.xq(case_dir, "DOUT_S_ROOT"))
    exe = Path(R.xq(case_dir, "EXEROOT")).resolve()
    if run.parent.name != name or arch.name != name:
        R.fail(f"{name}: RUNDIR {run} / DOUT_S_ROOT {arch} do not belong to the case; not touched")
    out = []
    for root in (run, arch):
        if root.is_dir():
            out += [p for p in root.rglob("*") if p.is_file() and not p.is_symlink() and
                    (p.name.endswith(".nc") or ".nc." in p.name)]
    for p in out:
        rp = p.resolve()
        if exe == rp or exe in rp.parents:
            R.fail(f"{p} is inside a build directory; refusing")
    return out


def purge_old(site, confirm):
    i = ident(site)
    if read_state(i["ad_case"]).get("phase") not in ("VERIFIED_NOT_SUBMITTED", "SUBMIT_ATTEMPTED_UNCERTAIN", "SUBMITTED"):
        R.fail(f"new AD case {i['ad']} not verified yet; old output kept (it is the reference for the new case)")
    total, plan = 0, []
    for key in ("ad0", "n0"):
        name = i[key]
        if jobs(name):
            R.fail(f"{name} has queued/running jobs: scancel them first ({', '.join(r[0] for r in jobs(name))})")
        files = old_nc_files(i[key + "_case"], name)
        size = sum(p.stat().st_size for p in files)
        total += size
        plan.append((name, files, size))
        print(f"  {site} {name}: {len(files)} .nc files, {size / 1e9:.2f} GB", flush=True)
    if confirm != CONFIRM:
        print(f"  {site}: DRY RUN, nothing deleted ({total / 1e9:.2f} GB would be freed)", flush=True)
        return total
    lst = ledger() / f"{site}_purged_files_{R.utc()[:19].replace(':', '')}.txt"
    lst.write_text("".join(f"{p}\t{p.stat().st_size}\n" for _, fs, _ in plan for p in fs))
    n = 0
    for _, fs, _ in plan:
        for p in fs:
            os.remove(p)
            n += 1
    print(f"  {site}: DELETED {n} files, {total / 1e9:.2f} GB (list: {lst})", flush=True)
    return total


# ------------------------------------------------------------------ plan / status
def plan(site):
    i = ident(site)
    ad_lnd = (i["ad0_case"] / "CaseDocs" / "lnd_in").read_text()
    base, fsur, share, _ = pft2_check(ad_lnd)
    rt = R.xq(i["ad0_case"], "RUN_TYPE")
    fin = unq(nml_value(ad_lnd, "finidat"))
    old = [r[0] + ":" + r[2] for k in ("ad0", "n0") for r in jobs(i[k])]
    warn = []
    if rt != "startup" or fin:
        warn.append(f"NOT A COLD START (RUN_TYPE={rt}, finidat={Path(fin).name if fin else '-'})")
    if share <= M18.MIN_PCT:
        warn.append("no PFT 2")
    if old:
        warn.append("old jobs queued: " + " ".join(old))
    print(f"{site:7s} PFT2 {share:6.2f} % | param {R.digest(base)[:10]} | {i['ad0']} -> {i['ad']} | "
          f"{'; '.join(warn) or 'OK'}", flush=True)


def status(site):
    i = ident(site)
    parts = []
    for key, label in (("ad", "AD"), ("n", "NORMAL")):
        case, name = i[key + "_case"], i[key]
        ph = read_state(case).get("phase", "not prepared")
        rest = i[key + "_arch"] / "rest"
        n = len([d for d in rest.iterdir() if d.is_dir()]) if rest.is_dir() else 0
        q = jobs(name) if ph != "not prepared" else []
        parts.append(f"{label} {ph} {n * R.SEG}/{YEARS} y{' [' + ','.join(r[2] for r in q) + ']' if q else ''}")
    print(f"{site:7s} " + " | ".join(parts), flush=True)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("action", choices=("plan", "ad-run", "normal-run", "purge-old", "status"))
    ap.add_argument("--sites", nargs="+", default=sorted(SITES), choices=sorted(SITES))
    ap.add_argument("--confirm", default="")
    a = ap.parse_args(argv)
    load()
    try:
        os.nice(10)
    except OSError:
        pass
    fn = {"plan": plan, "ad-run": ad_run, "normal-run": normal_run, "status": status,
          "purge-old": lambda s: purge_old(s, a.confirm)}[a.action]
    bad, total = 0, 0
    for s in a.sites:
        try:
            r = fn(s)
            if a.action == "purge-old":
                total += r or 0
        except Exception as exc:
            bad += 1
            print(f"{s}: HOLD {str(exc).strip()[:900]}", flush=True)
    if a.action == "purge-old":
        print(f"\nTOTAL {'freed' if a.confirm == CONFIRM else 'would free'}: {total / 1e9:.1f} GB", flush=True)
    print(f"\n{len(a.sites) - bad}/{len(a.sites)} sites OK, {bad} HOLD", flush=True)
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
