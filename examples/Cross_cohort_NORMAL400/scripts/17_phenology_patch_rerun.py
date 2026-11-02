#!/usr/bin/env python3
"""Rerun the first AD years with the upstream FATES fix for the cold-deciduous "never cold" trap.

Diagnosis (docs/NEEDLELEAF_COLLAPSE_DIAGNOSIS.md, section 16): after a warm autumn the FATES
"cold lifespan" leaf-off (leaves still on > 400 days after the last cold leaf-off) sets the site to
phen_cstat_nevercold. GDD only accumulates in the "is cold" state, so the trees never flush again and
starve (CZ-Stn, DE-Lnf). In warm climates the leaf-on rule also needs >= 1 chilling day, so
cold-deciduous trees stay leafless (US-SRM, US-SRG, US-CMW, FR-Pue).

Upstream fix: NGEET/fates 6d9f5b34 (R. Fisher, 2025-11-19; first in sci.1.94.0_api.47.0.0):
  1. lifespan leaf-off sets phen_cstat_iscold instead of phen_cstat_nevercold
  2. with fixed biogeography the chilling-day requirement for leaf-on is 0 instead of 1
This script backports exactly those lines into a private copy of the case's own
EDPhysiologyMod.F90 in <new case>/SourceMods/src.clm/ (the shared FATES source is not touched) and:

  prepare: create_clone of the site's AD case WITHOUT --keepexe (own executable, EXEROOT checked to be
           the new case's own), the 09 diagnostic history, <years> years in 5-year segments, patched
           SourceMods file (each replacement must match exactly once, diff kept in the case),
           preview_namelists through the AD case's overlay -> lnd_in must equal the AD case's except
           history keys; then case.build and a check that the patched file was compiled.
  submit:  case.submit --skip-preview-namelist (only a verified, built case; never twice)
  run:     prepare, then submit only if verified and built
  status / cases (LABEL:CASE list for scripts 08 and 16)

Usage (login node; the build takes a while, run it with setsid nohup):
  python -B 17_...py run [--sites CZ-Stn DE-Lnf US-SRM] [--years 50]
  python -B 17_...py status
"""
from __future__ import annotations

import argparse
import difflib
import importlib.util
import json
import os
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
SITES = ["CZ-Stn", "DE-Lnf", "US-SRM"]
STATE = "PHENFIX_STATE.json"
UPSTREAM = "NGEET/fates 6d9f5b34 (sci.1.94.0_api.47.0.0)"
R = None


def load09():
    global R
    for c in (HERE / "09_clone_AD_diag_rerun.py", HERE / "rerun.py"):
        if c.is_file():
            spec = importlib.util.spec_from_file_location("rerun09", c)
            R = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(R)
            return
    raise FileNotFoundError("module 09 (09_clone_AD_diag_rerun.py) not found beside this script")


# ------------------------------------------------------------------ the patch
DECL_ANCHOR = re.compile(r"^([ \t]*integer\s*::\s*ncdstart\b.*)$", re.M)
LEAFON_IF = re.compile(r"^([ \t]*)if \( any\(currentSite%cstatus == \[phen_cstat_iscold,phen_cstat_nevercold\]\) \.and\. &\s*\n"
                       r"\s*\(currentSite%grow_deg_days > gdd_threshold\)", re.M)
NCHILL_OLD = "(currentSite%nchilldays >= 1)) then"
NCHILL_NEW = "(currentSite%nchilldays >= nchill_threshold)) then"
NEVER_OLD = re.compile(r"currentSite%cstatus = phen_cstat_nevercold(\s*! alter status of site to imply that this)")
NCHILL_BLOCK = ("{i}! [phenology patch, backport of {up}]\n"
                "{i}! if fixed biogeography is on, we don't have an nchill threshold logic, because\n"
                "{i}! we are only growing cold deciduous trees where they are in real life\n"
                "{i}if(hlm_use_fixed_biogeog .eq. ifalse)then\n"
                "{i}   nchill_threshold=1\n"
                "{i}else\n"
                "{i}   nchill_threshold=0\n"
                "{i}endif\n\n")


def patch_source(text):
    """Return the patched EDPhysiologyMod.F90 text; refuse unless every anchor matches exactly once."""
    def once(n, what):
        if n != 1:
            R.fail(f"phenology patch: expected exactly one {what}, found {n}; FATES version differs, not patching")
    if "nchill_threshold" in text:
        R.fail("source already contains nchill_threshold (already patched or newer FATES); nothing to do")
    for need in ("hlm_use_fixed_biogeog", "ifalse"):
        if not re.search(rf"use\s+\w+\s*,\s*only\s*:[^\n]*\b{need}\b", text, re.I):
            R.fail(f"phenology patch: {need} is not imported in this EDPhysiologyMod.F90")
    once(len(DECL_ANCHOR.findall(text)), "'integer :: ncdstart' declaration")
    once(len(LEAFON_IF.findall(text)), "cold leaf-on IF block")
    once(text.count(NCHILL_OLD), f"'{NCHILL_OLD}'")
    once(len(NEVER_OLD.findall(text)), "lifespan 'cstatus = phen_cstat_nevercold'")
    t = DECL_ANCHOR.sub(lambda m: m.group(1) + "\n    integer  :: nchill_threshold  ! chill days for cold-decid. budburst [patch: NGEET/fates 6d9f5b34]", text, count=1)
    t = LEAFON_IF.sub(lambda m: NCHILL_BLOCK.format(i=m.group(1), up=UPSTREAM) + m.group(0), t, count=1)
    t = t.replace(NCHILL_OLD, NCHILL_NEW, 1)
    t = NEVER_OLD.sub(r"currentSite%cstatus = phen_cstat_iscold\1 [patch 6d9f5b34]", t, count=1)
    # self-check: only the intended lines changed
    ud = list(difflib.unified_diff(text.splitlines(), t.splitlines(), n=0, lineterm=""))
    added = [l for l in ud if l.startswith("+") and not l.startswith("+++")]
    removed = [l for l in ud if l.startswith("-") and not l.startswith("---")]
    if len(removed) != 2 or len(added) != 12:   # 1 declaration + 9-line block + 2 changed lines
        R.fail(f"phenology patch self-check failed: {len(removed)} lines removed, {len(added)} added")
    long = [l for l in t.splitlines() if len(l) > 132 and l not in text.splitlines()]
    if long:
        R.fail(f"phenology patch would add Fortran lines longer than 132 characters: {long[0][:60]}...")
    return t


# ------------------------------------------------------------------ cases
def ident(site, F7, P, years):
    i = R.ident(site, F7, P, years)
    new = f"{i['ad']}_PHENFIX{years}"
    i.update(new=new, case=R.CASES / new, rundir=R.OUT / new / "run", archive=R.OUT / "archive" / new,
             exeroot=R.OUT / new / "bld")
    return i


def read_state(i):
    st = i["case"] / STATE
    return json.loads(st.read_text()) if st.is_file() else {}


def write_state(i, **kw):
    s = read_state(i)
    s.update(kw, at=R.utc())
    (i["case"] / STATE).write_text(json.dumps(s, indent=2) + "\n")
    return s


def prepare(site, F7, P, years):
    i = ident(site, F7, P, years)
    ad, case = i["ad_case"], i["case"]
    print(f"\n=== {site}: {i['ad']} -> {i['new']} (FATES phenology patch, own build)", flush=True)
    s = read_state(i)
    if s.get("phase") in ("VERIFIED_BUILT_NOT_SUBMITTED", "SUBMITTED", "SUBMIT_ATTEMPTED_UNCERTAIN"):
        print(f"  already {s['phase']}; nothing changed", flush=True)
        return
    if s.get("phase") == "PATCHED_NOT_BUILT":
        print("  patched and verified earlier; building", flush=True)
        return build(i)
    for p in (case, i["rundir"].parent, i["archive"]):
        if p.exists():
            R.fail(f"path exists without a completed prepare: {p} (inspect and remove by hand if it is a failed attempt)")
    if R.xq(ad, "CLM_ACCELERATED_SPINUP").lower() != "on":
        R.fail("AD case is not accelerated spin-up")
    srcroot = R.xq(ad, "SRCROOT")
    ad_exe = R.xq(ad, "EXEROOT")
    adv = {k: R.xq(ad, k) for k in ("RUN_TYPE", "RUN_STARTDATE", "CLM_FORCE_COLDSTART", "CLM_BLDNML_OPTS")}
    src = Path(srcroot) / "src" / "fates" / "biogeochem" / "EDPhysiologyMod.F90"
    if (ad / "SourceMods" / "src.clm" / "EDPhysiologyMod.F90").is_file():
        R.fail("the AD case already has its own SourceMods EDPhysiologyMod.F90; not stacking patches")
    original = src.read_text()
    patched = patch_source(original)                      # fails before anything is created
    ad_lnd = (ad / "CaseDocs" / "lnd_in").read_text()
    ad_streams = (ad / "CaseDocs" / "datm.streams.xml").read_bytes()
    overlay = R.overlay_for(ad_lnd) if "_private_ctsm_FATES_AD400_namelist_overlay" in ad_lnd else None
    found = R.fates_has(srcroot, R.DIAG_FIELDS)
    nl, old_hist, fields = R.edit_user_nl((ad / "user_nl_clm").read_text(), found)
    cimescripts = Path(srcroot) / "cime" / "scripts"
    R.cmd([cimescripts / "create_clone", "--case", case, "--clone", ad], cwd=cimescripts, timeout=420)
    write_state(i, phase="PREPARE_ATTEMPTED")
    if R.xq(case, "CASE") != i["new"]:
        R.fail("clone identity")
    settings = {"CONTINUE_RUN": "FALSE", "STOP_OPTION": "nyears", "STOP_N": str(R.SEG), "REST_OPTION": "nyears",
                "REST_N": str(R.SEG), "RESUBMIT": str(years // R.SEG - 1), "RESUBMIT_SETS_CONTINUE_RUN": "TRUE",
                "DOUT_S": "TRUE", "RUNDIR": str(i["rundir"]), "DOUT_S_ROOT": str(i["archive"]),
                "EXEROOT": str(i["exeroot"])}
    for k, v in settings.items():
        R.xc(case, k, v)
    for k, v in settings.items():
        if R.xq(case, k).lower() != v.lower():
            R.fail(f"XML {k}={R.xq(case, k)} expected {v}")
    if Path(R.xq(case, "EXEROOT")).resolve() == Path(ad_exe).resolve():
        R.fail("EXEROOT equals the AD case's (shared executable); refusing to build into it")
    for k, v in adv.items():
        if R.xq(case, k) != v:
            R.fail(f"clone differs from AD in {k}")
    (case / "user_nl_clm").write_text(nl)
    sm = case / "SourceMods" / "src.clm"
    sm.mkdir(parents=True, exist_ok=True)
    (sm / "EDPhysiologyMod.F90").write_text(patched)
    diff = "".join(difflib.unified_diff(original.splitlines(True), patched.splitlines(True),
                                        fromfile=str(src), tofile="SourceMods/src.clm/EDPhysiologyMod.F90"))
    (case / "PHENFIX_patch.diff").write_text(diff)
    i["rundir"].mkdir(parents=True, exist_ok=True)
    if not (case / ".case.run").is_file():
        R.cmd([case / "case.setup"], cwd=case, timeout=300)
    env, lock = case / "env_case.xml", case / "LockedFiles" / "env_case.xml"
    orig = env.read_bytes()
    if overlay is None:
        R.cmd([case / "preview_namelists"], cwd=case, timeout=600)
    else:
        try:
            R.xc(case, "COMP_ROOT_DIR_LND", str(overlay))
            R.cmd([case / "preview_namelists"], cwd=case, timeout=600)
        finally:
            R.xc(case, "COMP_ROOT_DIR_LND", "$SRCROOT")
    if env.read_bytes() != orig or (lock.is_file() and lock.read_bytes() != orig):
        R.fail("env_case.xml / lock not restored after overlay preview")
    a, n = R.parse_nml(ad_lnd), R.parse_nml((case / "CaseDocs" / "lnd_in").read_text())
    keys = sorted(k for k in set(a) | set(n) if a.get(k) != n.get(k))
    bad = [k for k in keys if not R.is_hist(k)]
    if bad:
        R.fail("land namelist differs from the AD case beyond history settings:\n" +
               "\n".join(f"  {k}: AD={a.get(k)!r} NEW={n.get(k)!r}" for k in bad[:20]))
    if (case / "CaseDocs" / "datm.streams.xml").read_bytes() != ad_streams:
        R.fail("datm.streams.xml differs from the AD case")
    fin = next((v for k, v in n.items() if k.endswith(".hist_fincl1")), "")
    if any(f not in fin for f in fields):
        R.fail("hist_fincl1 incomplete in new lnd_in")
    write_state(i, phase="PATCHED_NOT_BUILT", **{k: str(v) for k, v in i.items()}, years=years, settings=settings,
                upstream=UPSTREAM, fates_source=str(src), fates_source_sha256=R.digest(src),
                patched_sha256=R.digest(sm / "EDPhysiologyMod.F90"), overlay=str(overlay) if overlay else "none",
                hist_fincl1=fields, lnd_in_keys_changed=keys, ad_exeroot=ad_exe,
                lnd_in_sha256=R.digest(case / "CaseDocs" / "lnd_in"),
                datm_streams_sha256=R.digest(case / "CaseDocs" / "datm.streams.xml"))
    print(f"  patch: {len(diff.splitlines())} diff lines (saved as {case / 'PHENFIX_patch.diff'})", flush=True)
    print(f"  lnd_in vs AD: only these keys differ: {', '.join(k.split('.', 1)[1] for k in keys)}", flush=True)
    print(f"  EXEROOT {i['exeroot']} (AD case: {ad_exe})", flush=True)
    build(i)


def build(i):
    case = i["case"]
    print(f"  building {i['new']} (own executable) ...", flush=True)
    R.cmd([case / "case.build"], cwd=case, timeout=7200)
    exeroot = Path(R.xq(case, "EXEROOT"))
    exe = exeroot / "cesm.exe"
    if not exe.is_file():
        R.fail(f"build finished but {exe} is missing")
    patched = case / "SourceMods" / "src.clm" / "EDPhysiologyMod.F90"
    objs = [p for p in (exeroot / "lnd" / "obj").glob("*") if p.name.lower() in ("edphysiologymod.o", "edphysiologymod.mod")]
    if not objs:
        R.fail("EDPhysiologyMod object not found in the build; cannot confirm the patch was compiled")
    if max(p.stat().st_mtime for p in objs) < patched.stat().st_mtime:
        R.fail("EDPhysiologyMod object is older than the patched source: patch not compiled")
    fp = exeroot / "lnd" / "obj" / "Filepath"
    if fp.is_file() and str(case / "SourceMods" / "src.clm") not in fp.read_text():
        R.fail("SourceMods/src.clm is not in the land build Filepath")
    if R.digest(case / "CaseDocs" / "lnd_in") != read_state(i)["lnd_in_sha256"]:
        R.fail("CaseDocs/lnd_in changed during the build")
    write_state(i, phase="VERIFIED_BUILT_NOT_SUBMITTED", exe=str(exe), exe_sha256=R.digest(exe))
    print(f"  {i['new']} BUILT AND VERIFIED, NOT SUBMITTED", flush=True)


def submit(site, F7, P, years):
    i = ident(site, F7, P, years)
    case = i["case"]
    s = read_state(i)
    if s.get("phase") != "VERIFIED_BUILT_NOT_SUBMITTED":
        R.fail(f"phase is {s.get('phase')}; not submitting")
    if R.digest(case / "CaseDocs" / "lnd_in") != s["lnd_in_sha256"] or \
            R.digest(case / "SourceMods" / "src.clm" / "EDPhysiologyMod.F90") != s["patched_sha256"]:
        R.fail("lnd_in or patched source changed after verification")
    cs = (case / "CaseStatus").read_text(errors="replace") if (case / "CaseStatus").is_file() else ""
    if re.search(r"case\.submit starting|case\.run starting", cs) or R.queued(i["new"]):
        R.fail("already submitted or jobs exist")
    write_state(i, phase="SUBMIT_ATTEMPTED_UNCERTAIN")
    out = R.cmd([case / "case.submit", "--skip-preview-namelist"], cwd=case, timeout=650)
    r, a = R.RUN_RE.search(out), R.ARCH_RE.search(out)
    if not r:
        R.fail("job id not parsed; DO NOT RETRY, check squeue. " + out[-600:])
    write_state(i, phase="SUBMITTED", run_job=r.group(1), archive_job=a.group(1) if a else "")
    print(f"{site}: SUBMITTED {i['new']} run={r.group(1)} archive={a.group(1) if a else '?'}", flush=True)


def run_one(site, F7, P, years):
    i = ident(site, F7, P, years)
    if read_state(i).get("phase") in ("SUBMITTED", "SUBMIT_ATTEMPTED_UNCERTAIN"):
        print(f"{site}: {read_state(i)['phase']}; not submitted again", flush=True)
        return
    prepare(site, F7, P, years)
    if read_state(i).get("phase") != "VERIFIED_BUILT_NOT_SUBMITTED":
        R.fail(f"not verified/built (phase {read_state(i).get('phase')}); not submitted")
    submit(site, F7, P, years)


def status(site, F7, P, years):
    i = ident(site, F7, P, years)
    h = i["archive"] / "lnd" / "hist"
    yrs = sorted({m.group(1) for p in (h.glob(f"{i['new']}.clm2.h0*.nc") if h.is_dir() else [])
                  for m in [re.search(r"\.h0a?\.(\d{4})-", p.name)] if m})
    q = R.queued(i["new"])
    print(f"{site}: {i['new']} | {read_state(i).get('phase', 'not prepared')} | archived years: {len(yrs)} | "
          f"queue: {', '.join(r[2] for r in q) or 'none'}", flush=True)


def cases(site, F7, P, years):
    print(f"{site}_phenfix:{ident(site, F7, P, years)['new']}", flush=True)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("action", choices=("prepare", "submit", "run", "status", "cases"))
    ap.add_argument("--sites", nargs="+", default=SITES)
    ap.add_argument("--years", type=int, default=50)
    a = ap.parse_args(argv)
    load09()
    if a.years % R.SEG or a.years < R.SEG:
        ap.error(f"--years must be a multiple of {R.SEG}")
    try:
        os.nice(10)
    except OSError:
        pass
    F7, P = R.load07()
    bad = 0
    for s in a.sites:
        try:
            {"prepare": prepare, "submit": submit, "run": run_one, "status": status, "cases": cases}[a.action](s, F7, P, a.years)
        except Exception as exc:
            bad += 1
            print(f"{s}: HOLD {exc}", flush=True)
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
