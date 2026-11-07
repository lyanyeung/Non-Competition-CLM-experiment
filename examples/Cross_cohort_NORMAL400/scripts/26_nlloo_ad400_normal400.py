#!/usr/bin/env python3
"""NL-Loo: fresh AD400 + Normal400 with needleleaf F + the phenology patch, the same procedure as every other site.

NL-Loo was the legacy PRE50/AD200/POST300 example; those runs are gone (only the normal-mode PRE50 / V2_PRE50 cases
remain). Its surface (surfdata_NL-Loo_obsPFT_grass_proxy_v1.nc, despite the name) is HLM1 93.6 % -> FATES PFT 2,
HLM7 2.9 % -> cold-deciduous broadleaf, HLM13 3.5 % -> C3 grass (b04_fix_check.py, 2026-11-07), so both fixes apply.

Step 1, stage-base: an AD400 cold-start case is made from NL-Loo_OBSPFT_NC_V2_PRE50 the way DE-Tha_OBSPFT_NC_V1_AD400
(same OBSPFT_NC lineage, nlloo_inspect.sh 2026-11-07) is set up, and only verified, never built or run:
  create_clone --keepexe of V2_PRE50 -> NL-Loo_OBSPFT_NC_V4_AD400
  CLM_ACCELERATED_SPINUP on, CLM_FORCE_COLDSTART on, RUN_TYPE startup, RUN_STARTDATE 1997-01-01, 80 x 5 years
  user_nl_clm + spinup_state = 2, + hist_fincl1 as DE-Tha, + fates_paramfile pinned to the V2_PRE50 file
  namelist generated through a private FATES-AD overlay; lnd_in must equal V2_PRE50's except spinup_state and
  history keys; spinup_state 2; DATM streams = the stream file V2_PRE50 read (same forcing 1997-2025, align 1997)
Step 2, ad-run / normal-run / auto-normal: exactly script 25 (script 22's ad_prepare / build / submit /
normal_run) with this base as the original AD: <base>_NLFP (adopted needleleaf-F copy of the parameter file +
patch in SourceMods + own build), then NL-Loo_OBSPFT_NC_V4_NORMAL400_NLFP from its year-400 restarts.

Put next to 25 and 22 (needs 25 -> 22 -> 20/21/17/18/13/09). Run with setsid nohup, directly (not inside bash -c).
  plan          READ ONLY
  stage-base    make + verify the base AD case (no build, no submit)
  ad-run        build + verify + submit NL-Loo_OBSPFT_NC_V4_AD400_NLFP
  normal-run | auto-normal | status   as script 25
"""
from __future__ import annotations

import argparse
import importlib.util
import os
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
SITE = "NL-Loo"
SRC = "NL-Loo_OBSPFT_NC_V2_PRE50"
BASE = "NL-Loo_OBSPFT_NC_V4_AD400"
START = "1997-01-01"
HIST = "'TOTSOMC','TOTSOMN','TLAI','FATES_GPP','FATES_NPP','TWS','H2OSNO'"
M25 = M22 = M20 = T = R = None


def load():
    global M25, M22, M20, T, R
    spec = importlib.util.spec_from_file_location("b01_25", HERE / "25_ameriflux_b01_remaining.py")
    M25 = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(M25)
    M25.load()
    M25.SITES5[SITE] = BASE
    M22, M20, T, R = M25.M22, M25.M20, M25.M22.T, M25.R


def stage_base():
    src, case = R.CASES / SRC, R.CASES / BASE
    run, arch = R.OUT / BASE / "run", R.OUT / "archive" / BASE
    ph = M20.read_state(case).get("phase")
    if ph == "BASE_VERIFIED":
        print(f"{BASE}: already BASE_VERIFIED; nothing changed", flush=True)
        return
    if ph not in (None, "PREPARE_ATTEMPTED") or case.exists() or run.parent.exists() or arch.exists():
        R.fail(f"{BASE} or its output paths exist (phase {ph}); inspect, remove by hand only if it is a failed attempt")
    if not src.is_dir():
        R.fail(f"{SRC} not found")
    src_lnd = (src / "CaseDocs" / "lnd_in").read_text()
    if R.xq(src, "CLM_ACCELERATED_SPINUP").lower() != "off" or R.xq(src, "RUN_TYPE") != "startup":
        R.fail(f"{SRC} is not a normal-mode startup case")
    if M20.unq(M20.nml_value(src_lnd, "finidat")):
        R.fail(f"{SRC} has a finidat; not a cold start")
    param = M20.unq(M20.nml_value(src_lnd, "fates_paramfile"))
    if not Path(param).is_file():
        R.fail(f"parameter file missing: {param}")
    eff = M20.effective_streams(src)
    print(f"=== {SRC} -> {BASE} (AD400 base, never run)\n  parameter file {param}\n  streams from {eff}", flush=True)
    M20.clone(src, case)                                    # --keepexe, writes PREPARE_ATTEMPTED
    sets = M20.settings(run, arch)
    sets.update({"CLM_ACCELERATED_SPINUP": "on", "CLM_FORCE_COLDSTART": "on", "RUN_TYPE": "startup",
                 "RUN_STARTDATE": START})
    M20.apply_settings(case, sets)
    nl = (case / "user_nl_clm").read_text()
    nl = T.set_nml(nl, "spinup_state", "2")
    nl = T.set_nml(nl, "hist_fincl1", HIST)
    nl = T.set_paramfile(nl, param)
    (case / "user_nl_clm").write_text(nl)
    run.mkdir(parents=True, exist_ok=True)
    if not (case / ".case.run").is_file():
        R.cmd([case / "case.setup"], cwd=case, timeout=300)
    overlay, a, n, diff = T.preview_verified(case, src_lnd, [".spinup_state", ".fates_paramfile"])
    new_lnd = (case / "CaseDocs" / "lnd_in").read_text()
    if M20.unq(M20.nml_value(new_lnd, "spinup_state")) != "2":
        R.fail(f"generated spinup_state is {M20.nml_value(new_lnd, 'spinup_state')!r}, expected 2")
    if M20.unq(M20.nml_value(new_lnd, "fates_paramfile")) != param:
        R.fail("generated fates_paramfile is not the pinned V2_PRE50 file")
    if M20.unq(M20.nml_value(new_lnd, "finidat")):
        R.fail("generated lnd_in has a finidat; not a cold start")
    carried = M20.carry_streams(case, run, eff)
    M20.write_state(case, phase="BASE_VERIFIED", kind="AD400 base (never run; template of the _NLFP case)",
                    site=SITE, source=SRC, start=START, settings=sets, paramfile=param,
                    paramfile_sha256=R.digest(param), overlay=str(overlay) if overlay else "none",
                    lnd_in_keys_changed=diff, effective_streams=str(eff), streams_carried=carried,
                    lnd_in_sha256=R.digest(case / "CaseDocs" / "lnd_in"),
                    datm_streams_sha256=R.digest(case / "CaseDocs" / "datm.streams.xml"))
    print(f"  lnd_in vs {SRC}: {', '.join(k.split('.', 1)[1] for k in diff) or 'identical'} | spinup_state 2 | "
          f"streams {'carried' if carried else 'identical'} | overlay {overlay}\n  {BASE} BASE_VERIFIED "
          f"(not built, not submitted)", flush=True)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("action", choices=("plan", "stage-base", "ad-run", "normal-run", "auto-normal", "status"))
    ap.add_argument("--every", type=int, default=1200)
    ap.add_argument("--max-hours", type=float, default=60)
    a = ap.parse_args(argv)
    load()
    if a.action not in ("plan", "status"):
        out = R.cmd(["ps", "-u", R.USER, "-o", "pid=,args="], timeout=30)
        others = [ln.strip() for ln in out.splitlines() if "26_nlloo_ad400_normal400.py" in ln
                  and not ln.strip().startswith(str(os.getpid()) + " ") and " plan" not in ln and " status" not in ln]
        if others:
            ap.error("another script-26 action is running:\n  " + "\n  ".join(others))
    try:
        if a.action == "plan":
            print(f"{SITE}: {SRC} -> base {BASE} (phase {M20.read_state(R.CASES / BASE).get('phase', 'not staged')})",
                  flush=True)
            if (R.CASES / BASE / "CaseDocs" / "lnd_in").is_file():
                M25.plan(SITE)
            return 0
        if a.action == "stage-base":
            stage_base()
            return 0
        if a.action in ("ad-run", "normal-run") and M20.read_state(R.CASES / BASE).get("phase") != "BASE_VERIFIED":
            R.fail(f"{BASE} is not BASE_VERIFIED; run stage-base first")
        if a.action == "auto-normal":         # own loop: script 25's auto-normal (other sites) may be running
            end = time.time() + a.max_hours * 3600
            while not M25.normal_submitted(SITE):
                print(f"#### {time.strftime('%F %H:%M', time.gmtime())} UTC  {SITE} Normal not yet submitted", flush=True)
                try:
                    M22.normal_run(SITE)
                except Exception as exc:
                    print(f"{SITE}: HOLD {str(exc).strip()[:300]}", flush=True)
                    if M20.read_state(M25.ident(SITE)["n_case"]).get("phase") == "PREPARE_ATTEMPTED":
                        print("prepare failed (PREPARE_ATTEMPTED); stopping, inspect it", flush=True)
                        return 1
                if M25.normal_submitted(SITE):
                    break
                if time.time() >= end:
                    print(f"stopped after {a.max_hours} h", flush=True)
                    return 1
                time.sleep(a.every)
            print("done: Normal400 submitted", flush=True)
            return 0
        {"ad-run": lambda s: M22.ad_run(s), "normal-run": lambda s: M22.normal_run(s),
         "status": lambda s: M25.status(s)}[a.action](SITE)
        return 0
    except Exception as exc:
        print(f"{SITE}: HOLD {str(exc).strip()[:1200]}", flush=True)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
