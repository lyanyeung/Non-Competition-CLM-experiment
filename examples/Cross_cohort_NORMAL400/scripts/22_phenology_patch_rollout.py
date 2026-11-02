#!/usr/bin/env python3
"""Roll out the FATES phenology patch (NGEET/fates 6d9f5b34 backport, script 17) to every site with a cold-deciduous
PFT, combined with the adopted needleleaf parameters (fix F) where the site also has PFT 2.

Decision 2026-11-02 evening (docs, section 16): the patch removes the "never cold" trap (CZ-Stn, DE-Lnf survive).
The needleleaf reruns (<AD>_NLF, script 20) started without it, so at sites that ALSO have a cold-deciduous PFT they
are stopped and restarted with patch + F, to run 800 years once instead of twice.

Classification (read from each site's surface data + parameter file; cold-deciduous = fates_phen_leaf_habit == 2
(ihard_season_decid; older FATES: fates_phen_season_decid == 1), mapped from PCT_NAT_PFT with fates_hlm_pft_map):
  RESTART_NLF   PFT 2 and cold-deciduous: stop <AD>_NLF, new <AD>_NLFP = patch + F
  KEEP_NLF      PFT 2, no cold-deciduous PFT: <AD>_NLF keeps running (nothing changes)
  RERUN_PHEN    no PFT 2, cold-deciduous: new <AD>_PHEN = patch only (parameters unchanged)
  UNCHANGED     neither: the original runs stand
  EXCLUDED      US-CMW (groundwater site, section 11)
  RESTART_AD    AD-only case of another cohort (EXTRA_AD, e.g. ICOS Batch04 GL-ZaH) with a cold-deciduous PFT:
                stop it (cancel-ad), new <AD>_PHEN = patch only, its own (private) parameter file unchanged

New AD case: create_clone of the ORIGINAL AD case WITHOUT --keepexe (own executable, EXEROOT = OUT/<new>/bld),
patched EDPhysiologyMod.F90 in its own SourceMods (a SourceMods symlink is replaced by a private copy first, so no
other case is touched), fates_paramfile -> adopted copy only for RESTART_NLF; lnd_in must equal the original AD on
every other key; DATM streams = the ones the original run read; build with the script-17 procedure (spinup settings
hidden only during case.build, restored byte-identical, lnd_in re-verified), compile check from the build log;
80 x 5 years; submit once. Normal: script-01 method from the new AD (clone --keepexe = the patched executable),
hybrid from the year-400 restarts.

Actions:
  plan                         READ ONLY
  cancel-nlf  [--confirm STOP_NLF_FOR_PHENOLOGY_PATCH]   RESTART_NLF sites: RESUBMIT=0, scancel the <AD>_NLF jobs,
                               mark it CANCELLED_REPLACED (dry run without --confirm)
  ad-run                       RESTART_NLF (only once its NLF is cancelled) and RERUN_PHEN sites: prepare, build, verify,
                               submit (about 5-8 min per site, sequential; run with setsid nohup)
  normal-run                   sites whose new AD finished 400 years
  purge-old   [--confirm DELETE_OLD_PHENOLOGY_OUTPUTS]   .nc output of every replaced case: original AD/Normal of
                               RERUN_PHEN, RESTART_NLF and KEEP_NLF sites, and the cancelled <AD>_NLF cases (dry run without
                               --confirm); never a running case, never a build dir, never CaseDocs / namelists / stream xml
  status
"""
from __future__ import annotations

import argparse
import difflib
import importlib.util
import json
import os
import shutil
from pathlib import Path

HERE = Path(__file__).resolve().parent
OTHER = {"AT-Neu": "AT-Neu_B03_FIXNC_NORMAL400", "BR-Ma2": "BR-Ma2_AMF_FIXNC_NORMAL400_UTC_V2_PTS",
         "CH-Cha": "CH-Cha_B03_FIXNC_NORMAL400", "CH-Fru": "CH-Fru_B02_FIXNC_NORMAL400",
         "CZ-Stn": "CZ-Stn_B03_FIXNC_NORMAL400", "DE-Hai": "DE-Hai_B01_FIXNC_NORMAL400",
         "DE-Hzd": "DE-Hzd_B03_FIXNC_NORMAL400", "DE-Lnf": "DE-Lnf_B03_FIXNC_NORMAL400",
         "DK-Sor": "DK-Sor_B02_FIXNC_ICOS_DBF100_NORMAL400", "ES-LJu": "ES-LJu_B02_FIXNC_MET24_GPPNPP_HISTFIX_NORMAL400",
         "FR-Hes": "FR-Hes_B02_FIXNC_NORMAL400", "FR-Pue": "FR-Pue_B01_FIXNC_NORMAL400",
         "GF-Guy": "GF-Guy_B03_FIXNC_NORMAL400", "IT-Col": "IT-Col_B01_FIXNC_NORMAL400",
         "IT-MBo": "IT-MBo_B02_FIXNC_NORMAL400", "IT-Noe": "IT-Noe_B02_FIXNC_GPPNPP_HISTFIX_NORMAL400",
         "US-CMW": "US-CMW_AMF_B02_FIXNC_NORMAL400_DIRECT", "US-EML": "US-EML_AMF_B02_FIXNC_NORMAL400_DIRECT",
         "US-ICh": "US-ICh_AMF_B02_FIXNC_NORMAL400_DIRECT", "US-ICt": "US-ICt_AMF_B02_FIXNC_NORMAL400_DIRECT",
         "US-Kon": "US-Kon_AMF_B03_FIXNC_NORMAL400_DIRECT", "US-MMS": "US-MMS_AMF_B03_FIXNC_NORMAL400_DIRECT",
         "US-NR3": "US-NR3_AMF_B03_FIXNC_NORMAL400_DIRECT", "US-Rpf": "US-Rpf_AMF_B04_FIXNC_NORMAL400_BASETA_V1",
         "US-SRG": "US-SRG_AMF_B04_FIXNC_NORMAL400_BASETA_V1", "US-SRM": "US-SRM_AMF_B04_FIXNC_NORMAL400_BASETA_V1",
         "US-Seg": "US-Seg_AMF_B04_FIXNC_NORMAL400_BASETA_V1", "US-Ses": "US-Ses_AMF_B04_FIXNC_NORMAL400_BASETA_V1",
         "US-Ton": "US-Ton_AMF_B04_FIXNC_NORMAL400_BASETA_V1", "US-UiD": "US-UiD_AMF_B05_FIXNC_NORMAL400_DIRECT",
         "US-Var": "US-Var_AMF_B05_FIXNC_NORMAL400_DIRECT", "US-WCr": "US-WCr_AMF_B05_FIXNC_NORMAL400_DIRECT",
         "US-Whs": "US-Whs_AMF_B05_FIXNC_NORMAL400_DIRECT", "US-Wkg": "US-Wkg_AMF_B05_FIXNC_NORMAL400_DIRECT"}
# AD-only cases of other cohorts (no Normal case yet), checked on 2026-11-02 22:36: only GL-ZaH has a cold-deciduous
# PFT (private arctic parameter file); DE-Gri, DE-RuR, IT-Tor, ES-Agu (ICOS Batch04) have none and keep running.
EXTRA_AD = {"GL-ZaH": "GL-ZaH_ICOS_B04_FIXNC_AD400_DIRECT"}
CONFIRM_CANCEL_AD = "STOP_AD_FOR_PHENOLOGY_PATCH"
EXCLUDED = {"US-CMW": "groundwater-dependent site, excluded (docs section 11)"}
DECID_PARAMS = (("fates_phen_leaf_habit", 2), ("fates_phen_season_decid", 1))   # FATES >= ~1.70 / older
CONFIRM_CANCEL = "STOP_NLF_FOR_PHENOLOGY_PATCH"
CONFIRM_PURGE = "DELETE_OLD_PHENOLOGY_OUTPUTS"
PATCH_ACTIONS = ("RESTART_NLF", "RERUN_PHEN", "RESTART_AD")
M17 = M18 = M20 = M21 = T = R = None
SITES = {}


def load():
    global M17, M18, M20, M21, T, R, SITES
    def mod(name, fn):
        spec = importlib.util.spec_from_file_location(name, HERE / fn)
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        return m
    M20 = mod("rerun20", "20_needleleaf_rerun_AD400_NORMAL400.py")
    M20.load()
    M18, T, R = M20.M18, M20.T, M20.R
    M17 = mod("phen17", "17_phenology_patch_rerun.py")
    M17.T, M17.R = T, R
    M21 = mod("hi21", "21_fix_humanindex_rerun.py")
    M21.M20, M21.T, M21.R = M20, T, R
    for need in ((M17, "compile_evidence"), (M17, "hide_spinup_state"), (M20, "carry_streams"), (M18, "ensure_adopted")):
        if not hasattr(need[0], need[1]):
            raise RuntimeError(f"{need[0].__name__} is too old (no {need[1]}); download the current scripts")
    SITES = {**M20.SITES, **OTHER, **{k: None for k in EXTRA_AD}}


# ------------------------------------------------------------------ classification
def decid_share(pct_nat_pft, params):
    """Share (%) of the vegetated area in cold-deciduous FATES PFTs, and their names."""
    import numpy as np
    prm = params["parameters"]
    names = [str(x).strip() for x in prm["fates_pftname"]["data"]]
    key, flag = next(((k, f) for k, f in DECID_PARAMS if k in prm), (None, None))
    if key is None:
        raise ValueError("no phenology-habit parameter (" + " / ".join(k for k, _ in DECID_PARAMS) + ") in parameter file")
    dec = np.asarray(prm[key]["data"], float).ravel() == flag
    if len(dec) != len(names):
        raise ValueError(f"{key} has {len(dec)} values for {len(names)} PFTs")
    pct = np.asarray(pct_nat_pft, float).ravel()
    veg = pct[1:].sum()
    if veg <= 0:
        return 0.0, []
    ent = prm["fates_hlm_pft_map"]
    m = np.moveaxis(np.asarray(ent["data"], float), T.pft_axis(ent, len(names)), -1)
    n = min(m.shape[0], len(pct) - 1)
    area = (pct[1:1 + n, None] * m[:n, :]).sum(axis=0) / veg * 100      # % of vegetation per FATES PFT
    present = [(names[p], round(float(area[p]), 1)) for p in range(len(names)) if dec[p] and area[p] > 0]
    return float(sum(a for _, a in present)), present


def ident(site):
    needle = site in M20.SITES
    suf = "_NLFP" if needle else "_PHEN"
    if site in EXTRA_AD:                      # AD-only case: the Normal name follows the script-01 convention
        ad0 = EXTRA_AD[site]
        n0 = ad0.replace("_AD400", "_NORMAL400", 1)
    else:
        n0 = SITES[site]
        ad0 = R.xq(R.CASES / n0, "RUN_REFCASE")
        if not ad0:
            R.fail(f"{n0}: RUN_REFCASE empty")
    i = {"site": site, "needle": needle, "ad0": ad0, "n0": n0, "nlf": ad0 + M20.SUFFIX, "ad": ad0 + suf, "n": n0 + suf,
         "ad_only": site in EXTRA_AD}
    for k in ("ad0", "n0", "nlf", "ad", "n"):
        i[k + "_case"] = R.CASES / i[k]
        i[k + "_run"] = R.OUT / i[k] / "run"
        i[k + "_arch"] = R.OUT / "archive" / i[k]
    i["exeroot"] = R.OUT / i["ad"] / "bld"
    return i


def classify(site):
    i = ident(site)
    if site in EXCLUDED:
        return i, "EXCLUDED", 0.0, [], EXCLUDED[site]
    lnd = (i["ad0_case"] / "CaseDocs" / "lnd_in").read_text()
    base, fsur, p2, _ = M20.pft2_check(lnd)
    pct = M18.read_pct(fsur)
    share, present = decid_share(pct, json.loads(Path(base).read_text()))
    if i["ad_only"]:
        act = "RESTART_AD" if share > M18.MIN_PCT else "UNCHANGED"
    elif share > M18.MIN_PCT:
        act = "RESTART_NLF" if i["needle"] else "RERUN_PHEN"
    else:
        act = "KEEP_NLF" if i["needle"] else "UNCHANGED"
    return i, act, share, present, f"PFT2 {p2:.1f} %"


# ------------------------------------------------------------------ actions
def plan(site):
    i, act, share, present, note = classify(site)
    extra = ""
    if act == "RESTART_NLF":
        extra = f" | NLF: {M20.read_state(i['nlf_case']).get('phase', 'not prepared')}"
    if act == "RESTART_AD":
        q = M20.jobs(i["ad0"])
        extra = f" | original AD {i['ad0']} jobs: {' '.join(r[0] + ':' + r[2] for r in q) or 'none'}"
    print(f"{site:7s} {act:11s} cold-deciduous {share:5.1f} % {present} | {note}{extra}", flush=True)
    return act


def cancel_nlf(site, confirm):
    i, act, *_ = classify(site)
    if act != "RESTART_NLF":
        print(f"{site}: {act}, nothing to cancel", flush=True)
        return
    case, name = i["nlf_case"], i["nlf"]
    ph = M20.read_state(case).get("phase")
    if ph == "CANCELLED_REPLACED":
        print(f"{site}: {name} already cancelled", flush=True)
        return
    q = M20.jobs(name)
    if confirm != CONFIRM_CANCEL:
        print(f"{site}: DRY RUN would stop {name} ({ph}; jobs {' '.join(r[0] + ':' + r[2] for r in q) or 'none'})", flush=True)
        return
    if case.is_dir():
        R.xc(case, "RESUBMIT", "0")                 # an archive job finishing now must not resubmit
    for _ in range(3):
        q = M20.jobs(name)
        if not q:
            break
        R.cmd(["scancel", *[r[0] for r in q]], timeout=60)
        import time
        time.sleep(5)
    if M20.jobs(name):
        R.fail(f"{name}: jobs still in the queue after scancel")
    rest = i["nlf_arch"] / "rest"
    done = len([d for d in rest.iterdir() if d.is_dir()]) * R.SEG if rest.is_dir() else 0
    if case.is_dir():
        M20.write_state(case, phase="CANCELLED_REPLACED", replaced_by=i["ad"], years_done_at_cancel=done)
    print(f"{site}: STOPPED {name} after {done} archived years; replaced by {i['ad']}", flush=True)


def cancel_ad(site, confirm):
    """AD-only cases of other cohorts (EXTRA_AD): stop the unpatched original AD so it can be replaced."""
    i, act, *_ = classify(site)
    if act != "RESTART_AD":
        print(f"{site}: {act}, nothing to cancel", flush=True)
        return
    case, name = i["ad0_case"], i["ad0"]
    q = M20.jobs(name)
    if confirm != CONFIRM_CANCEL_AD:
        print(f"{site}: DRY RUN would stop {name} (jobs {' '.join(r[0] + ':' + r[2] for r in q) or 'none'})", flush=True)
        return
    R.xc(case, "RESUBMIT", "0")
    import time
    for _ in range(3):
        q = M20.jobs(name)
        if not q:
            break
        R.cmd(["scancel", *[r[0] for r in q]], timeout=60)
        time.sleep(5)
    if M20.jobs(name):
        R.fail(f"{name}: jobs still in the queue after scancel")
    rest = i["ad0_arch"] / "rest"
    done = len([d for d in rest.iterdir() if d.is_dir()]) * R.SEG if rest.is_dir() else 0
    (M20.ledger() / f"{site}_original_AD_stopped_{R.utc()[:19].replace(':', '')}.json").write_text(json.dumps(
        {"case": name, "years_archived_at_stop": done, "replaced_by": i["ad"], "reason": "unpatched FATES phenology",
         "at": R.utc()}, indent=1) + "\n")
    print(f"{site}: STOPPED {name} after {done} archived years; replaced by {i['ad']}", flush=True)


def ad_prepare(site):
    i, act, share, present, _ = classify(site)
    if act not in PATCH_ACTIONS:
        print(f"{site}: {act}, no patched rerun", flush=True)
        return None
    if act == "RESTART_NLF" and M20.read_state(i["nlf_case"]).get("phase") not in (None, "CANCELLED_REPLACED"):
        R.fail(f"{i['nlf']} is still {M20.read_state(i['nlf_case']).get('phase')}; run cancel-nlf first")
    if act == "RESTART_AD" and M20.jobs(i["ad0"]):
        R.fail(f"original {i['ad0']} still has jobs; run cancel-ad first")
    case = i["ad_case"]
    print(f"\n=== {site} {act}: {i['ad0']} -> {i['ad']} (phenology patch{' + needleleaf F' if i['needle'] else ''})",
          flush=True)
    phase = M20.read_state(case).get("phase")
    if phase == "PATCHED_NOT_BUILT":
        print("  patched and verified earlier; building", flush=True)
        build(i)
        return i
    if phase not in (None, "PREPARE_ATTEMPTED"):
        print(f"  already {phase}; nothing changed", flush=True)
        return i
    M20.check_new_paths(i, "ad")
    ad0 = i["ad0_case"]
    if R.xq(ad0, "CLM_ACCELERATED_SPINUP").lower() != "on":
        R.fail("original AD case is not accelerated spin-up")
    ad_lnd = (ad0 / "CaseDocs" / "lnd_in").read_text()
    rt, fin = R.xq(ad0, "RUN_TYPE"), M20.unq(M20.nml_value(ad_lnd, "finidat"))
    if rt != "startup" or fin:
        R.fail(f"original AD is not a cold start (RUN_TYPE={rt}, finidat={fin or 'none'})")
    base = M20.unq(M20.nml_value(ad_lnd, "fates_paramfile"))
    if i["needle"]:
        param, psha = M18.ensure_adopted(base, [site])
    else:
        param, psha = Path(base), R.digest(base)
    srcroot = R.xq(ad0, "SRCROOT")
    src = Path(srcroot) / "src" / "fates" / "biogeochem" / "EDPhysiologyMod.F90"
    if (ad0 / "SourceMods" / "src.clm" / "EDPhysiologyMod.F90").is_file():
        R.fail("the original AD case has its own SourceMods EDPhysiologyMod.F90; not stacking patches")
    original = src.read_text()
    patched = M17.patch_source(original)                  # fails before anything is created
    eff = M20.effective_streams(ad0)
    adv = {k: R.xq(ad0, k) for k in ("RUN_TYPE", "RUN_STARTDATE", "CLM_FORCE_COLDSTART", "CLM_BLDNML_OPTS")}
    ad_exe = R.xq(ad0, "EXEROOT")
    nl = (ad0 / "user_nl_clm").read_text()
    if i["needle"]:
        nl = T.set_paramfile(nl, param)
    cs = Path(srcroot) / "cime" / "scripts"
    R.cmd([cs / "create_clone", "--case", case, "--clone", ad0], cwd=cs, timeout=420)     # own build: no --keepexe
    M20.write_state(case, phase="PREPARE_ATTEMPTED")
    if R.xq(case, "CASE") != i["ad"]:
        R.fail("clone identity")
    sets = M20.settings(i["ad_run"], i["ad_arch"])
    sets["EXEROOT"] = str(i["exeroot"])
    M20.apply_settings(case, sets)
    if Path(R.xq(case, "EXEROOT")).resolve() == Path(ad_exe).resolve():
        R.fail("EXEROOT equals the original's (shared executable); refusing to build into it")
    for k, v in adv.items():
        if R.xq(case, k) != v:
            R.fail(f"clone differs from the original AD in {k}")
    sm = case / "SourceMods"
    if sm.is_symlink():                                  # never write into another case's SourceMods
        real = sm.resolve()
        sm.unlink()
        shutil.copytree(real, sm, symlinks=False)
    tgt = sm / "src.clm"
    tgt.mkdir(parents=True, exist_ok=True)
    if (tgt / "EDPhysiologyMod.F90").exists():
        R.fail("cloned SourceMods already has EDPhysiologyMod.F90")
    (tgt / "EDPhysiologyMod.F90").write_text(patched)
    (case / "PHENFIX_patch.diff").write_text("".join(difflib.unified_diff(
        original.splitlines(True), patched.splitlines(True), fromfile=str(src), tofile="SourceMods/src.clm/EDPhysiologyMod.F90")))
    (case / "user_nl_clm").write_text(nl)
    i["ad_run"].mkdir(parents=True, exist_ok=True)
    if not (case / ".case.run").is_file():
        R.cmd([case / "case.setup"], cwd=case, timeout=300)
    allowed = [".fates_paramfile"] if i["needle"] else []
    overlay, a, n, diff = T.preview_verified(case, ad_lnd, allowed)
    bad = [k for k in diff if not any(k.endswith(x) for x in allowed)]
    if bad:
        R.fail(f"lnd_in differs from the original AD in {bad}")
    if M20.unq(M20.nml_value((case / "CaseDocs" / "lnd_in").read_text(), "fates_paramfile")) != str(param):
        R.fail("new lnd_in fates_paramfile is not the intended file")
    carried = M20.carry_streams(case, i["ad_run"], eff)
    M20.write_state(case, phase="PATCHED_NOT_BUILT", kind="AD400", site=site, action=act, original=i["ad0"],
                    start=adv["RUN_STARTDATE"], years=M20.YEARS, settings=sets, paramfile=str(param), paramfile_sha256=psha,
                    base_paramfile=base, cold_deciduous=present, needleleaf_fix=i["needle"], upstream=M17.UPSTREAM,
                    fates_source=str(src), fates_source_sha256=R.digest(src), patched_sha256=R.digest(tgt / "EDPhysiologyMod.F90"),
                    overlay=str(overlay) if overlay else "none", lnd_in_keys_changed=diff, effective_streams=str(eff),
                    streams_carried=carried, ad_exeroot=ad_exe, lnd_in_sha256=R.digest(case / "CaseDocs" / "lnd_in"),
                    datm_streams_sha256=R.digest(case / "CaseDocs" / "datm.streams.xml"))
    print(f"  cold-deciduous {share:.1f} % {present} | lnd_in vs original: {', '.join(k.split('.', 1)[1] for k in diff) or 'identical'}"
          f" | streams {'carried' if carried else 'identical'} | EXEROOT {i['exeroot']}", flush=True)
    build(i)
    return i


def pgrep_build(name):
    out = R.cmd(["ps", "-u", R.USER, "-o", "pid=,args="], timeout=30)
    return [ln for ln in out.splitlines() if "case.build" in ln and f"/{name}/" in ln + "/"]


def build(i):
    """script-17 procedure: case.build with CLM_ACCELERATED_SPINUP off and the user_nl_clm spinup_state line(s)
    commented out (the plain build-namelist refuses FATES AD), both restored, namelist re-generated through the verified
    overlay (and the original streams re-applied) and required to be byte-identical to the verified one."""
    case = i["ad_case"]
    st = M20.read_state(case)
    print(f"  building {i['ad']} ...", flush=True)
    spin = R.xq(case, "CLM_ACCELERATED_SPINUP")
    unl = case / "user_nl_clm"
    orig = unl.read_bytes()
    if spin.lower() == "off" and M17.BUILD_TAG.encode() in orig and st.get("phase") == "PATCHED_NOT_BUILT":
        # an earlier build of this script was killed inside case.build: undo exactly what it changed, then rebuild
        if R.xq(i["ad0_case"], "CLM_ACCELERATED_SPINUP").lower() != "on":
            R.fail("interrupted build, and the original AD is not 'on' either; inspect by hand")
        if pgrep_build(i["ad"]):
            R.fail(f"a case.build of {i['ad']} is still running (left by a killed ad-run); wait for it to end")
        orig = orig.decode().replace(M17.BUILD_TAG, "").encode()
        unl.write_bytes(orig)
        R.xc(case, "CLM_ACCELERATED_SPINUP", "on")
        spin = R.xq(case, "CLM_ACCELERATED_SPINUP")
        print("  repaired an interrupted earlier build (spinup on, user_nl_clm line restored)", flush=True)
    if spin.lower() != "on":
        R.fail(f"CLM_ACCELERATED_SPINUP is {spin!r} before the build, expected 'on'")
    if M17.BUILD_TAG.encode() in orig:
        R.fail("user_nl_clm still has a line hidden by an interrupted build; restore it by hand (remove the tag)")
    hidden, nh = M17.hide_spinup_state(orig.decode())
    try:
        R.xc(case, "CLM_ACCELERATED_SPINUP", "off")
        unl.write_text(hidden)
        R.cmd([case / "case.build"], cwd=case, timeout=7200)
    finally:
        unl.write_bytes(orig)
        R.xc(case, "CLM_ACCELERATED_SPINUP", spin)
    if unl.read_bytes() != orig or R.xq(case, "CLM_ACCELERATED_SPINUP") != spin:
        R.fail("user_nl_clm / CLM_ACCELERATED_SPINUP not restored after the build")
    ov = st.get("overlay", "none")
    T.run_preview(case, None if ov in ("none", "", None) else Path(ov))
    if st.get("streams_carried"):
        M20.carry_streams(case, i["ad_run"], Path(st["effective_streams"]))
    if R.digest(case / "CaseDocs" / "lnd_in") != st["lnd_in_sha256"]:
        R.fail("lnd_in regenerated after the build differs from the verified one")
    if R.digest(case / "CaseDocs" / "datm.streams.xml") != st["datm_streams_sha256"]:
        R.fail("DATM streams after the build differ from the verified ones")
    exeroot = Path(R.xq(case, "EXEROOT"))
    exe = exeroot / "cesm.exe"
    if not exe.is_file():
        R.fail(f"build finished but {exe} is missing")
    patched = case / "SourceMods" / "src.clm" / "EDPhysiologyMod.F90"
    if R.digest(patched) != st["patched_sha256"]:
        R.fail("patched source changed after verification")
    ok, msg = M17.compile_evidence(exeroot, i["ad"], patched.stat().st_mtime)
    print(f"  compile check: {msg}", flush=True)
    if not ok:
        R.fail(msg)
    M20.write_state(case, phase="VERIFIED_NOT_SUBMITTED", exe=str(exe), exe_sha256=R.digest(exe),
                    build_hidden_spinup_lines=nh)
    print(f"  {i['ad']} BUILT AND VERIFIED, NOT SUBMITTED", flush=True)


def ad_run(site):
    i = ident(site)
    if M20.read_state(i["ad_case"]).get("phase") in ("SUBMITTED", "SUBMIT_ATTEMPTED_UNCERTAIN"):
        print(f"{site}: {i['ad']} {M20.read_state(i['ad_case'])['phase']}; not submitted again", flush=True)
        return
    if ad_prepare(site) is None:
        return
    M20.submit(i["ad_case"], i["ad"])


def normal_run(site):
    i, act, *_ = classify(site)
    if act not in PATCH_ACTIONS:
        print(f"{site}: {act}, no patched Normal", flush=True)
        return
    j = dict(i)                        # script 21's Normal (script-01 method) on our names
    if M20.read_state(j["n_case"]).get("phase") in ("SUBMITTED", "SUBMIT_ATTEMPTED_UNCERTAIN"):
        print(f"{site}: {j['n']} {M20.read_state(j['n_case'])['phase']}; not submitted again", flush=True)
        return
    M21.ident = lambda _ad0, _j=j: _j
    M21.normal_prepare(i["ad0"])
    M20.submit(j["n_case"], j["n"])


def purge_old(site, confirm):
    i, act, *_ = classify(site)
    # Only *.nc of cases that are replaced: a new case needs nothing of them but CaseDocs / user_nl / stream xml (kept).
    if act == "RERUN_PHEN":
        targets = [("ad0", i["ad0"]), ("n0", i["n0"])]
    elif act == "RESTART_NLF":
        if i["nlf_case"].is_dir() and M20.read_state(i["nlf_case"]).get("phase") != "CANCELLED_REPLACED":
            R.fail(f"{i['nlf']} not cancelled; run cancel-nlf first")
        targets = [("nlf", i["nlf"]), ("ad0", i["ad0"]), ("n0", i["n0"])]
    elif act == "KEEP_NLF":
        if M20.read_state(i["nlf_case"]).get("phase") not in ("VERIFIED_NOT_SUBMITTED", "SUBMIT_ATTEMPTED_UNCERTAIN", "SUBMITTED"):
            R.fail(f"{i['nlf']} not verified; originals kept")
        targets = [("ad0", i["ad0"]), ("n0", i["n0"])]
    else:
        print(f"{site}: {act}, nothing to purge", flush=True)
        return 0
    total, plan_ = 0, []
    for key, name in targets:
        if M20.jobs(name):
            R.fail(f"{name} has queued/running jobs")
        if not i[key + "_case"].is_dir():
            continue
        files = M20.old_nc_files(i[key + "_case"], name)
        size = sum(p.stat().st_size for p in files)
        total += size
        plan_.append((name, files))
        print(f"  {site} {name}: {len(files)} .nc files, {size / 1e9:.2f} GB", flush=True)
    if confirm != CONFIRM_PURGE:
        print(f"  {site}: DRY RUN, nothing deleted ({total / 1e9:.2f} GB would be freed)", flush=True)
        return total
    lst = M20.ledger() / f"{site}_phen_purged_files_{R.utc()[:19].replace(':', '')}.txt"
    lst.write_text("".join(f"{p}\t{p.stat().st_size}\n" for _, fs in plan_ for p in fs))
    for _, fs in plan_:
        for p in fs:
            os.remove(p)
    print(f"  {site}: DELETED {sum(len(fs) for _, fs in plan_)} files, {total / 1e9:.2f} GB (list: {lst})", flush=True)
    return total


def status(site):
    i, act, *_ = classify(site)
    parts = [f"{act:11s}"]
    keys = {"RESTART_NLF": ("nlf", "ad", "n"), "KEEP_NLF": ("nlf",), "RERUN_PHEN": ("ad", "n"),
            "RESTART_AD": ("ad", "n")}.get(act, ())
    for key in keys:
        ph = M20.read_state(i[key + "_case"]).get("phase", "not prepared")
        rest = i[key + "_arch"] / "rest"
        n = len([d for d in rest.iterdir() if d.is_dir()]) if rest.is_dir() else 0
        q = M20.jobs(i[key]) if ph not in ("not prepared", "CANCELLED_REPLACED") else []
        parts.append(f"{ {'nlf': 'NLF', 'ad': 'AD', 'n': 'NORMAL'}[key] } {ph} {n * R.SEG}y{' [' + ','.join(r[2] for r in q) + ']' if q else ''}")
    print(f"{site:7s} " + " | ".join(parts), flush=True)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("action", choices=("plan", "cancel-nlf", "cancel-ad", "ad-run", "normal-run", "purge-old", "status"))
    ap.add_argument("--sites", nargs="+", default=None)
    ap.add_argument("--confirm", default="")
    a = ap.parse_args(argv)
    load()
    sites = a.sites or sorted(SITES)
    unknown = [s for s in sites if s not in SITES]
    if unknown:
        ap.error("unknown sites: " + " ".join(unknown))
    try:
        os.nice(10)
    except OSError:
        pass
    fn = {"plan": plan, "cancel-nlf": lambda s: cancel_nlf(s, a.confirm), "cancel-ad": lambda s: cancel_ad(s, a.confirm), "ad-run": ad_run, "normal-run": normal_run,
          "purge-old": lambda s: purge_old(s, a.confirm), "status": status}[a.action]
    bad, counts, total = 0, {}, 0
    for s in sites:
        try:
            r = fn(s)
            if a.action == "plan":
                counts[r] = counts.get(r, 0) + 1
            if a.action == "purge-old":
                total += r or 0
        except Exception as exc:
            bad += 1
            print(f"{s}: HOLD {str(exc).strip()[:900]}", flush=True)
    if counts:
        print("\n" + ", ".join(f"{k} {v}" for k, v in sorted(counts.items())), flush=True)
    if a.action == "purge-old":
        print(f"TOTAL {'freed' if a.confirm == CONFIRM_PURGE else 'would free'}: {total / 1e9:.1f} GB", flush=True)
    print(f"\n{len(sites) - bad}/{len(sites)} sites OK, {bad} HOLD", flush=True)
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
