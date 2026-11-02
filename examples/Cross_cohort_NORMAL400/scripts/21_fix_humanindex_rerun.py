#!/usr/bin/env python3
"""Rerun an AD400 case that stopped in HumanIndexMod ("ERROR RH is negative"), then its Normal400.

Diagnosis (US-Aud, 2026-11-02): the DATM forcing is clean (QBOT >= 5e-5 kg/kg, RH >= 1.1 %, no negatives, no NaN).
The negative value is CTSM's 2-m DIAGNOSTIC humidity: q_ref2m = forc_q + similarity extrapolation
(CanopyFluxesMod / BareGroundFluxesMod), which can go below zero over very dry air (US-Aud: RH ~1 %, 84-87 kPa).
rh_ref2m is then passed to the human heat-stress indices, whose Wet_Bulb check stops the model. The heat-stress
indices and the 2-m reference humidity are diagnostics only; they do not feed back into the land physics. Fix:
calc_human_stress_indices = 'NONE' (the only change), which skips these diagnostics.

  ad-run      clone <AD> -> <AD>_HINONE (--keepexe), 80 x 5 years, user_nl_clm + calc_human_stress_indices='NONE';
              lnd_in must equal the original AD on every other key; effective DATM streams kept; verify, submit once.
  normal-run  after 400 years: <AD name with _AD400 -> _NORMAL400>_HINONE from create_clone --keepexe of the new AD
              case (method of script 01 / Batch01 Stage21): hybrid from the year-400 restarts (copied, sha-checked,
              rpointers), CLM_ACCELERATED_SPINUP off, spinup_state removed, finidat = staged restart, fates_paramfile
              pinned to the AD's file; fsurdat / params / CO2 / FATES switches / history / DATM checked equal to the AD.
  status
Default case: US-Aud_AMF_B01SIX_FIXNC_AD400_DIRECT. Run with setsid nohup.
"""
from __future__ import annotations

import argparse
import importlib.util
import os
import shutil
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEFAULT = ["US-Aud_AMF_B01SIX_FIXNC_AD400_DIRECT"]
SUFFIX = "_HINONE"
KEY, VALUE = "calc_human_stress_indices", "'NONE'"
SAME_LND = ("fsurdat", "fates_paramfile", "use_crop", "co2_ppmv", "fates_spitfire_mode", "hist_fincl1",
            "use_fates", "use_fates_sp", "use_fates_fixed_biogeog", "use_fates_nocomp", "use_cn", KEY)
M20 = T = R = None


def load():
    global M20, T, R
    spec = importlib.util.spec_from_file_location("rerun20", HERE / "20_needleleaf_rerun_AD400_NORMAL400.py")
    M20 = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(M20)
    M20.load()
    T, R = M20.T, M20.R


def ident(ad0):
    if "_AD400" not in ad0:
        R.fail(f"{ad0}: not an AD400 case name")
    i = {"ad0": ad0, "ad": ad0 + SUFFIX, "n": ad0.replace("_AD400", "_NORMAL400", 1) + SUFFIX}
    for k in ("ad0", "ad", "n"):
        i[k + "_case"] = R.CASES / i[k]
        i[k + "_run"] = R.OUT / i[k] / "run"
        i[k + "_arch"] = R.OUT / "archive" / i[k]
    return i


def drop_key(text, key):
    return "".join("".join(lines) for k, lines in R.nml_blocks(text) if k != key.lower())


# ------------------------------------------------------------------ AD
def ad_prepare(ad0):
    i = ident(ad0)
    case = i["ad_case"]
    print(f"\n=== {ad0} -> {i['ad']} ({KEY} = {VALUE})", flush=True)
    if M20.read_state(case).get("phase") not in (None, "PREPARE_ATTEMPTED"):
        print(f"  already {M20.read_state(case)['phase']}; nothing changed", flush=True)
        return i
    M20.check_new_paths(i, "ad")
    src = i["ad0_case"]
    if R.xq(src, "CLM_ACCELERATED_SPINUP").lower() != "on":
        R.fail("original is not an accelerated spin-up case")
    ad_lnd = (src / "CaseDocs" / "lnd_in").read_text()
    rt, fin = R.xq(src, "RUN_TYPE"), M20.unq(M20.nml_value(ad_lnd, "finidat"))
    if rt != "startup" or fin:
        R.fail(f"original is not a cold start (RUN_TYPE={rt}, finidat={fin or 'none'})")
    base = M20.unq(M20.nml_value(ad_lnd, "fates_paramfile"))
    eff = M20.effective_streams(src)
    adv = {k: R.xq(src, k) for k in ("RUN_TYPE", "RUN_STARTDATE", "CLM_FORCE_COLDSTART", "EXEROOT", "CLM_BLDNML_OPTS")}
    nl = T.set_nml((src / "user_nl_clm").read_text(), KEY, VALUE)
    M20.clone(src, case)
    sets = M20.settings(i["ad_run"], i["ad_arch"])
    M20.apply_settings(case, sets)
    for k, v in adv.items():
        if R.xq(case, k) != v:
            R.fail(f"clone differs from the original in {k}")
    (case / "user_nl_clm").write_text(nl)
    i["ad_run"].mkdir(parents=True, exist_ok=True)
    if not (case / ".case.run").is_file():
        R.cmd([case / "case.setup"], cwd=case, timeout=300)
    overlay, a, n, diff = T.preview_verified(case, ad_lnd, ["." + KEY])
    if [k for k in diff if not k.endswith("." + KEY)]:
        R.fail(f"lnd_in differs from the original in {diff}")
    if M20.unq(M20.nml_value((case / "CaseDocs" / "lnd_in").read_text(), KEY)).upper() != "NONE":
        R.fail(f"new lnd_in {KEY} is not NONE")
    carried = M20.carry_streams(case, i["ad_run"], eff)
    M20.write_state(case, phase="VERIFIED_NOT_SUBMITTED", kind="AD400", original=ad0, change={KEY: VALUE},
                    start=adv["RUN_STARTDATE"], years=M20.YEARS, settings=sets, paramfile=base,
                    paramfile_sha256=R.digest(base), overlay=str(overlay) if overlay else "none",
                    lnd_in_keys_changed=diff, streams_carried=carried,
                    lnd_in_sha256=R.digest(case / "CaseDocs" / "lnd_in"),
                    datm_streams_sha256=R.digest(case / "CaseDocs" / "datm.streams.xml"))
    print(f"  lnd_in vs original: only {KEY} | streams {'carried' if carried else 'identical'} | "
          f"{M20.YEARS} y from {adv['RUN_STARTDATE']}", flush=True)
    print("  AD VERIFIED, NOT SUBMITTED", flush=True)
    return i


def ad_run(ad0):
    i = ident(ad0)
    if M20.read_state(i["ad_case"]).get("phase") in ("SUBMITTED", "SUBMIT_ATTEMPTED_UNCERTAIN"):
        print(f"{i['ad']}: {M20.read_state(i['ad_case'])['phase']}; not submitted again", flush=True)
        return
    ad_prepare(ad0)
    M20.submit(i["ad_case"], i["ad"])


# ------------------------------------------------------------------ Normal (method of script 01)
def normal_prepare(ad0):
    i = ident(ad0)
    case, adc = i["n_case"], i["ad_case"]
    print(f"\n=== {i['ad']} -> {i['n']}", flush=True)
    if M20.read_state(case).get("phase") not in (None, "PREPARE_ATTEMPTED"):
        print(f"  already {M20.read_state(case)['phase']}; nothing changed", flush=True)
        return i
    y, files = M20.ad_complete(i)
    M20.check_new_paths(i, "n")
    date = f"{y:04d}-01-01"
    ad_lnd = (adc / "CaseDocs" / "lnd_in").read_text()
    pf = M20.unq(M20.nml_value(ad_lnd, "fates_paramfile"))
    if not Path(pf).is_file():
        R.fail(f"AD fates_paramfile missing: {pf}")
    eff = M20.effective_streams(adc)
    src_sha = {c: R.digest(p) for c, p in files.items()}
    M20.clone(adc, case)
    sets = M20.settings(i["n_run"], i["n_arch"])
    sets.update(RUN_TYPE="hybrid", RUN_STARTDATE=date, RUN_REFCASE=i["ad"], RUN_REFDATE=date, RUN_REFTOD="00000",
                GET_REFCASE="FALSE", CLM_FORCE_COLDSTART="off", CLM_ACCELERATED_SPINUP="off")
    M20.apply_settings(case, sets)
    i["n_run"].mkdir(parents=True, exist_ok=True)
    for c, src in files.items():
        dst = i["n_run"] / src.name
        shutil.copy2(src, dst)
        if R.digest(dst) != src_sha[c]:
            R.fail(f"copied restart differs ({c})")
    for ptr, c in M20.POINTERS:
        (i["n_run"] / ptr).write_text(files[c].name + "\n")
    staged = str(i["n_run"] / files["clm2"].name)
    t = drop_key((case / "user_nl_clm").read_text(), "spinup_state")
    if M20.nml_value(t, "reseed_dead_plants") is not None:
        R.fail("reseed_dead_plants in user_nl_clm")
    t = T.set_nml(t, "finidat", f"'{staged}'")
    t = T.set_paramfile(t, pf)                     # the AD namelist came from the FATES-AD overlay: pin the file
    (case / "user_nl_clm").write_text(t)
    if not (case / ".case.run").is_file():
        R.cmd([case / "case.setup"], cwd=case, timeout=300)
    R.cmd([case / "preview_namelists"], cwd=case, timeout=600)
    new = (case / "CaseDocs" / "lnd_in").read_text()
    for k in SAME_LND:
        if M20.nml_value(new, k) != M20.nml_value(ad_lnd, k):
            R.fail(f"Normal {k} differs from the AD: {M20.nml_value(new, k)} vs {M20.nml_value(ad_lnd, k)}")
    if M20.unq(M20.nml_value(new, "finidat")) != staged:
        R.fail(f"Normal finidat {M20.nml_value(new, 'finidat')}")
    if M20.unq(M20.nml_value(new, "spinup_state")) not in ("", "0"):
        R.fail("Normal spinup_state is not 0")
    carried = M20.carry_streams(case, i["n_run"], eff)
    if (i["n_run"] / "lnd_in").is_file() and R.digest(i["n_run"] / "lnd_in") != R.digest(case / "CaseDocs" / "lnd_in"):
        R.fail("RUNDIR lnd_in differs from CaseDocs")
    M20.write_state(case, phase="VERIFIED_NOT_SUBMITTED", kind="NORMAL400", refcase=i["ad"], start=date,
                    years=M20.YEARS, settings=sets, paramfile=pf, paramfile_sha256=R.digest(pf),
                    restart_sha256=src_sha, streams_carried=carried,
                    lnd_in_sha256=R.digest(case / "CaseDocs" / "lnd_in"),
                    datm_streams_sha256=R.digest(case / "CaseDocs" / "datm.streams.xml"))
    print(f"  hybrid from {i['ad']} {M20.stamp(y)} | spinup_state 0 | fsurdat/params/CO2/FATES/history = AD | "
          f"streams {'carried' if carried else 'identical'}", flush=True)
    print("  NORMAL VERIFIED, NOT SUBMITTED", flush=True)
    return i


def normal_run(ad0):
    i = ident(ad0)
    if M20.read_state(i["n_case"]).get("phase") in ("SUBMITTED", "SUBMIT_ATTEMPTED_UNCERTAIN"):
        print(f"{i['n']}: {M20.read_state(i['n_case'])['phase']}; not submitted again", flush=True)
        return
    normal_prepare(ad0)
    M20.submit(i["n_case"], i["n"])


def status(ad0):
    i = ident(ad0)
    for key in ("ad", "n"):
        ph = M20.read_state(i[key + "_case"]).get("phase", "not prepared")
        rest = i[key + "_arch"] / "rest"
        n = len([d for d in rest.iterdir() if d.is_dir()]) if rest.is_dir() else 0
        q = M20.jobs(i[key]) if ph != "not prepared" else []
        print(f"{i[key]}: {ph} | {n * R.SEG}/{M20.YEARS} y | queue: {', '.join(r[2] for r in q) or 'none'}", flush=True)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("action", choices=("ad-run", "normal-run", "status"))
    ap.add_argument("--cases", nargs="+", default=DEFAULT, help="original AD400 case names")
    a = ap.parse_args(argv)
    load()
    try:
        os.nice(10)
    except OSError:
        pass
    bad = 0
    for c in a.cases:
        try:
            {"ad-run": ad_run, "normal-run": normal_run, "status": status}[a.action](c)
        except Exception as exc:
            bad += 1
            print(f"{c}: HOLD {str(exc).strip()[:900]}", flush=True)
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
