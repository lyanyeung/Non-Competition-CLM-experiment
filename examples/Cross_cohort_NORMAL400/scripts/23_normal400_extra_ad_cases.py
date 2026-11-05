#!/usr/bin/env python3
"""Normal400 for AD400 cases that were NOT made by scripts 20/21/22 (ICOS Batch04: DE-Gri, DE-RuR, IT-Tor, ES-Agu,
and CH-Aws whose _HINONE AD case was made by Batch04 06c).

Method = script 21 normal-run (script-01 method), unchanged: create_clone --keepexe of the AD case; hybrid from the
year-400 restarts (copied, sha-checked, rpointers); CLM_ACCELERATED_SPINUP off, spinup_state removed, finidat = staged
restart, fates_paramfile pinned to the AD's file; fsurdat / params / CO2 / FATES switches / history / DATM checked equal
to the AD; 80 x 5 years; submitted once (NLF_STATE.json in the new case).

Only two things differ from script 21, because these AD cases have no NLF_STATE.json and their own output paths:
  * AD completion is checked without the state file: nothing queued, CLM_ACCELERATED_SPINUP on, year-400 restart
    triplet present, last case.run and st_archive success, RESUBMIT 0, final spinup_state 2;
  * the AD RUNDIR / DOUT_S_ROOT are read from the case (xmlquery), not assumed.
Normal name: AD name with _AD400 -> _NORMAL400 (DE-Gri_ICOS_B04_FIXNC_NORMAL400_DIRECT, ..._NORMAL400_DIRECT_HINONE).

These sites have neither PFT 2 nor a cold-deciduous PFT (maintenance log 2026-11-02 22:36; check with
b04_fix_check.py), so the shared unpatched executable and their own parameter files stand.

Put this file next to 20/21 (needs 21_fix_humanindex_rerun.py -> 20 -> 18 -> 13 in the same folder).
hist_fincl lists are compared without blanks after commas ('A', 'B' == 'A','B'; DE-Gri's AD lnd_in has blanks,
the regenerated one not, 2026-11-05). Names and order must still be identical.

  check         READ ONLY: AD complete? Normal state?
  prepare       create + verify the Normal case, do not submit
  run           prepare if needed, then submit once (run with setsid nohup)
  status        READ ONLY
  clean-failed  [--confirm REMOVE_FAILED_NORMAL_PREPARE] remove a PREPARE_ATTEMPTED Normal case (never set up for a
                run, never submitted): case dir, <OUT>/<case>, empty archive; file list to the ledger first
"""
from __future__ import annotations

import argparse
import importlib.util
import os
import re
import shutil
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEFAULT = ["DE-Gri_ICOS_B04_FIXNC_AD400_DIRECT", "DE-RuR_ICOS_B04_FIXNC_AD400_DIRECT",
           "IT-Tor_ICOS_B04_FIXNC_AD400_DIRECT", "ES-Agu_ICOS_B04_FIXNC_AD400_DIRECT",
           "CH-Aws_ICOS_B04_FIXNC_AD400_DIRECT_HINONE"]
CONFIRM = "REMOVE_FAILED_NORMAL_PREPARE"
M21 = M20 = R = None


def load():
    global M21, M20, R
    spec = importlib.util.spec_from_file_location("hi21", HERE / "21_fix_humanindex_rerun.py")
    M21 = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(M21)
    M21.load()
    M20, R = M21.M20, M21.R
    M20.ad_complete = ad_complete_nostate          # used inside M21.normal_prepare
    orig_nv = M20.nml_value

    def nml_value(text, key):                      # M21.normal_prepare compares hist_fincl1 through this
        v = orig_nv(text, key)
        if v is not None and key.lower().startswith("hist_fincl"):
            v = re.sub(r"\s*,\s*", ",", str(v).strip())
        return v
    M20.nml_value = nml_value


def ident(ad):
    if "_AD400" not in ad:
        R.fail(f"{ad}: not an AD400 case name")
    adc = R.CASES / ad
    if not adc.is_dir():
        R.fail(f"{ad}: case not found")
    n = ad.replace("_AD400", "_NORMAL400", 1)
    i = {"ad0": ad, "ad": ad, "n": n, "ad0_case": adc, "ad_case": adc,
         "ad_run": Path(R.xq(adc, "RUNDIR")), "ad_arch": Path(R.xq(adc, "DOUT_S_ROOT")),
         "n_case": R.CASES / n, "n_run": R.OUT / n / "run", "n_arch": R.OUT / "archive" / n}
    i["ad0_run"], i["ad0_arch"] = i["ad_run"], i["ad_arch"]
    return i


def ad_complete_nostate(i):
    """Same checks as script 20 ad_complete, without NLF_STATE.json."""
    case, name, arch = i["ad_case"], i["ad"], i["ad_arch"]
    if M20.jobs(name):
        R.fail(f"{name}: still running")
    if R.xq(case, "CLM_ACCELERATED_SPINUP").lower() != "on":
        R.fail(f"{name}: not an accelerated spin-up case")
    y = int(R.xq(case, "RUN_STARTDATE")[:4]) + M20.YEARS
    folder = arch / "rest" / M20.stamp(y)
    files = {c: folder / f"{name}.{c}.r.{M20.stamp(y)}.nc" for _, c in M20.POINTERS}
    missing = [str(p) for p in files.values() if not p.is_file() or p.stat().st_size < 1024]
    if missing:
        have = sorted(d.name for d in (arch / "rest").iterdir()) if (arch / "rest").is_dir() else []
        R.fail(f"{name}: year-{y} restarts missing (latest {have[-1] if have else 'none'}): {missing[:1]}")
    cs = (case / "CaseStatus").read_text(errors="replace")
    lr, la = re.findall(r"case\.run (success|error)", cs), re.findall(r"st_archive (success|error)", cs)
    if not lr or lr[-1] != "success" or not la or la[-1] != "success" or R.xq(case, "RESUBMIT") != "0":
        R.fail(f"{name}: last run/archive not success or RESUBMIT not exhausted")
    st = M20.restart_state(files["clm2"])
    if st != 2:
        R.fail(f"{name}: final spinup_state {st}, expected 2")
    return y, files


def n_phase(i):
    return M20.read_state(i["n_case"]).get("phase")


def check(ad):
    i = ident(ad)
    ph = n_phase(i)
    if ph:
        print(f"{ad}: Normal {i['n']} already {ph}", flush=True)
        return
    y, files = ad_complete_nostate(i)
    print(f"{ad}: READY | year-{y} restarts present, spinup_state 2 | Normal -> {i['n']}", flush=True)


def prepare(ad):
    i = ident(ad)
    if n_phase(i) in ("SUBMITTED", "SUBMIT_ATTEMPTED_UNCERTAIN", "VERIFIED_NOT_SUBMITTED"):
        print(f"{i['n']}: {n_phase(i)}; nothing changed", flush=True)
        return i
    M21.ident = lambda _ad0, _i=i: _i
    M21.normal_prepare(ad)
    return i


def run(ad):
    i = ident(ad)
    if n_phase(i) in ("SUBMITTED", "SUBMIT_ATTEMPTED_UNCERTAIN"):
        print(f"{i['n']}: {n_phase(i)}; not submitted again", flush=True)
        return
    prepare(ad)
    M20.submit(i["n_case"], i["n"])


def clean_failed(ad, confirm):
    i = ident(ad)
    case, name = i["n_case"], i["n"]
    top, arch = i["n_run"].parent, i["n_arch"]
    ph = n_phase(i)
    if ph != "PREPARE_ATTEMPTED":
        print(f"{name}: phase {ph}; nothing to clean", flush=True)
        return
    if M20.jobs(name):
        R.fail(f"{name}: jobs in the queue")
    cs = (case / "CaseStatus").read_text(errors="replace") if (case / "CaseStatus").is_file() else ""
    if "case.submit" in cs or "case.run" in cs:
        R.fail(f"{name}: CaseStatus shows a submit/run; not a failed prepare")
    if "_NORMAL400" not in name or case.parent != R.CASES or top.parent != R.OUT or name == i["ad"]:
        R.fail(f"{name}: unexpected paths {case} {top}")
    exe = Path(R.xq(case, "EXEROOT")) if (case / "env_build.xml").is_file() else None
    if exe and (exe == top or top in exe.parents):
        R.fail(f"{name}: EXEROOT {exe} is inside {top}; build dirs are never removed")
    if (top / "bld").exists():
        R.fail(f"{top}/bld exists; build dirs are never removed")
    if arch.is_dir() and any(arch.rglob("*.nc")):
        R.fail(f"{arch} holds .nc output; not a failed prepare")
    paths = [p for p in (case, top, arch) if p.exists()]
    files = [(f, f.stat().st_size) for p in paths for f in sorted(p.rglob("*")) if f.is_file()]
    print(f"{name}: PREPARE_ATTEMPTED | {len(files)} files, {sum(s for _, s in files) / 1e9:.2f} GB in "
          f"{', '.join(map(str, paths))}", flush=True)
    if confirm != CONFIRM:
        print(f"  dry run; add --confirm {CONFIRM}", flush=True)
        return
    log = M20.ledger() / f"{name}_failed_normal_prepare_removed_{R.utc().replace(':', '')}.txt"
    log.write_text("".join(f"{f}\t{s}\n" for f, s in files))
    for p in paths:
        shutil.rmtree(p)
    print(f"  REMOVED; file list: {log}", flush=True)


def status(ad):
    i = ident(ad)
    for key in ("ad", "n"):
        rest = i[key + "_arch"] / "rest"
        n = len([d for d in rest.iterdir() if d.is_dir()]) if rest.is_dir() else 0
        q = M20.jobs(i[key])
        ph = "-" if key == "ad" else (n_phase(i) or "not prepared")
        print(f"  {i[key]}: {ph} | {n * R.SEG}/{M20.YEARS} y | queue: {', '.join(r[2] for r in q) or 'none'}", flush=True)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("action", choices=("check", "prepare", "run", "status", "clean-failed"))
    ap.add_argument("--cases", nargs="+", default=DEFAULT, help="AD400 case names")
    ap.add_argument("--confirm", default="")
    a = ap.parse_args(argv)
    load()
    if a.action in ("prepare", "run", "clean-failed"):
        out = R.cmd(["ps", "-u", R.USER, "-o", "pid=,args="], timeout=30)
        others = [ln.strip() for ln in out.splitlines() if "23_normal400_extra_ad_cases.py" in ln
                  and not ln.strip().startswith(str(os.getpid()) + " ") and " check" not in ln and " status" not in ln]
        if others:
            ap.error("another script-23 action is running:\n  " + "\n  ".join(others))
    bad = 0
    for c in a.cases:
        try:
            {"check": check, "prepare": prepare, "run": run, "status": status,
             "clean-failed": lambda x: clean_failed(x, a.confirm)}[a.action](c)
        except Exception as exc:
            bad += 1
            print(f"{c}: HOLD {str(exc).strip()[:900]}", flush=True)
    print(f"\n{len(a.cases) - bad}/{len(a.cases)} OK, {bad} HOLD", flush=True)
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
