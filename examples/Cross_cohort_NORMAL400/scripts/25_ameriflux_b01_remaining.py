#!/usr/bin/env python3
"""AmeriFlux Batch01, the five sites that ran on the Stage21 controller and were never part of the needleleaf /
phenology rollout: CA-TP1, CA-TP3, US-Bar, CA-Cbo, CA-Man.

Their AD400 (all five) and Normal400 (CA-TP1, CA-TP3, US-Bar) ran with the default parameter file and the
unpatched FATES code. Checked on 2026-11-07 with b04_fix_check.py: every one has PFT 2 (needleleaf F applies);
CA-TP3, US-Bar and CA-Cbo also have a cold-deciduous PFT (phenology patch applies).
  CA-TP1  HLM1 100                 CA-TP3  HLM1 99 / HLM7 1       US-Bar  HLM1 17 / HLM7 83
  CA-Cbo  HLM1 18.6 / HLM7 81.4    CA-Man  HLM2 100

So each site gets one new 800-year run, <AD>_NLFP -> <Normal>_NLFP, made by script 22's own code: ad_prepare /
build / submit (clone of the original AD, adopted needleleaf-F copy of its parameter file, the FATES phenology
patch in SourceMods, own build, namelist and streams verified against the original AD) and normal_run (script-21
Normal method: hybrid from the year-400 restarts of the new AD). The patch is applied at CA-TP1 and CA-Man as well,
where it has nothing to act on (no cold-deciduous PFT), so all five follow one procedure. The forcing is the one
of the existing AD case (streams carried over); the detached CA-Cbo / CA-Man Met candidates (Stage51-57) are not
used. The original cases are left untouched (no purge here).

Put next to 22 (needs 22 -> 20/21/17/18/13/09 in the same folder). Run actions other than plan/status with
setsid nohup, directly (not inside bash -c), one at a time.
  plan          READ ONLY: names, PFT 2 share, cold-deciduous share, original AD / Normal progress
  ad-run        prepare + build + verify + submit the new AD400 (about 5-8 min build per site, sequential)
  normal-run    Normal400 of the sites whose new AD finished 400 years (HOLD otherwise)
  auto-normal   normal-run every --every s until all five are submitted (max --max-hours)
  status        READ ONLY
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
SITES5 = {"CA-TP1": "CA-TP1_AMF_B01SIX_FIXNC_AD400_DIRECT", "CA-TP3": "CA-TP3_AMF_B01SIX_FIXNC_AD400_DIRECT",
          "US-Bar": "US-Bar_AMF_B01SIX_FIXNC_AD400_DIRECT", "CA-Cbo": "CA-Cbo_AMF_B01SIX_FIXNC_AD400_DIRECT",
          "CA-Man": "CA-Man_AMF_B01SIX_FIXNC_AD400_DIRECT"}
ACT = "B01_NLFP"
SUF = "_NLFP"
M22 = M20 = M18 = R = None


def load():
    global M22, M20, M18, R
    spec = importlib.util.spec_from_file_location("roll22", HERE / "22_phenology_patch_rollout.py")
    M22 = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(M22)
    M22.load()
    M20, M18, R = M22.M20, M22.M18, M22.R
    M22.PATCH_ACTIONS = tuple(M22.PATCH_ACTIONS) + (ACT,)
    M22.ident = ident                     # ad_run / ad_prepare / normal_run look these up at call time
    M22.classify = classify


def ident(site):
    if site not in SITES5:
        R.fail(f"{site}: not one of {', '.join(SITES5)}")
    ad0 = SITES5[site]
    n0 = ad0.replace("_AD400", "_NORMAL400", 1)
    i = {"site": site, "needle": True, "ad0": ad0, "n0": n0, "nlf": ad0 + M20.SUFFIX, "ad": ad0 + SUF, "n": n0 + SUF,
         "ad_only": not (R.CASES / n0).is_dir()}
    for k in ("ad0", "n0", "nlf", "ad", "n"):
        i[k + "_case"] = R.CASES / i[k]
        i[k + "_run"] = R.OUT / i[k] / "run"
        i[k + "_arch"] = R.OUT / "archive" / i[k]
    i["exeroot"] = R.OUT / i["ad"] / "bld"
    return i


def classify(site):
    i = ident(site)
    if not i["ad0_case"].is_dir():
        R.fail(f"{i['ad0']}: case not found")
    lnd = (i["ad0_case"] / "CaseDocs" / "lnd_in").read_text()
    base, fsur, p2, _ = M20.pft2_check(lnd)
    if p2 <= M18.MIN_PCT:
        R.fail(f"{site}: PFT 2 share {p2:.2f} %, the needleleaf fix does not apply; not a {ACT} site")
    share, present = M22.decid_share(M18.read_pct(fsur), json.loads(Path(base).read_text()))
    return i, ACT, share, present, f"PFT2 {p2:.1f} %"


def years(case, arch):
    rest = arch / "rest"
    n = len([d for d in rest.iterdir() if d.is_dir()]) if rest.is_dir() else 0
    return n * R.SEG


def plan(site):
    i, act, share, present, note = classify(site)
    a0 = years(i["ad0_case"], Path(R.xq(i["ad0_case"], "DOUT_S_ROOT")))
    n0 = years(i["n0_case"], Path(R.xq(i["n0_case"], "DOUT_S_ROOT"))) if not i["ad_only"] else None
    print(f"{site:7s} {note} | cold-deciduous {share:.1f} % {present or ''} | original AD {a0}/400"
          f"{'' if n0 is None else f', Normal {n0}/400'}\n        new: {i['ad']} -> {i['n']}", flush=True)


def status(site):
    i = ident(site)
    parts = []
    for key, lab in (("ad", "AD"), ("n", "NORMAL")):
        ph = M20.read_state(i[key + "_case"]).get("phase", "not prepared")
        q = M20.jobs(i[key]) if ph != "not prepared" else []
        parts.append(f"{lab} {ph} {years(i[key + '_case'], i[key + '_arch'])}/400 y"
                     + (f" [{','.join(r[2] for r in q)}]" if q else ""))
    print(f"{site:7s} " + " | ".join(parts), flush=True)


def normal_submitted(site):
    return M20.read_state(ident(site)["n_case"]).get("phase") in ("SUBMITTED", "SUBMIT_ATTEMPTED_UNCERTAIN")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("action", choices=("plan", "ad-run", "normal-run", "auto-normal", "status"))
    ap.add_argument("--sites", nargs="+", default=list(SITES5))
    ap.add_argument("--every", type=int, default=1200)
    ap.add_argument("--max-hours", type=float, default=36)
    a = ap.parse_args(argv)
    load()
    if a.action not in ("plan", "status"):
        out = R.cmd(["ps", "-u", R.USER, "-o", "pid=,args="], timeout=30)
        others = [ln.strip() for ln in out.splitlines() if "25_ameriflux_b01_remaining.py" in ln
                  and not ln.strip().startswith(str(os.getpid()) + " ") and " plan" not in ln and " status" not in ln]
        if others:
            ap.error("another script-25 action is running:\n  " + "\n  ".join(others))
    if a.action == "auto-normal":
        end = time.time() + a.max_hours * 3600
        while True:
            left = [s for s in a.sites if not normal_submitted(s)]
            print(f"#### {time.strftime('%F %H:%M', time.gmtime())} UTC  waiting: {' '.join(left) or 'none'}", flush=True)
            if not left:
                print("done: all Normal400 submitted", flush=True)
                return 0
            for s in left:
                try:
                    M22.normal_run(s)
                except Exception as exc:
                    print(f"{s}: HOLD {str(exc).strip()[:300]}", flush=True)
                    if M20.read_state(ident(s)["n_case"]).get("phase") == "PREPARE_ATTEMPTED":
                        print(f"{s}: prepare failed (PREPARE_ATTEMPTED); stopping, inspect it", flush=True)
                        return 1
            if time.time() >= end:
                print(f"stopped after {a.max_hours} h", flush=True)
                return 1
            time.sleep(a.every)
    bad = 0
    fn = {"plan": plan, "status": status, "ad-run": M22.ad_run, "normal-run": M22.normal_run}[a.action]
    for s in a.sites:
        try:
            fn(s)
        except Exception as exc:
            bad += 1
            print(f"{s}: HOLD {str(exc).strip()[:900]}", flush=True)
    print(f"\n{len(a.sites) - bad}/{len(a.sites)} OK, {bad} HOLD", flush=True)
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
