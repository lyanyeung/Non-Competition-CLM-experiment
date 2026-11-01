#!/usr/bin/env python3
"""Needleleaf fix trials: first AD years with one needleleaf (PFT 2) parameter change at a time.

Mechanism (docs/NEEDLELEAF_COLLAPSE_DIAGNOSIS.md): FATES carbon-starvation mortality
0.6 x max(0, 1 - storage/leafC) fires every winter because storage is capped at
alloc_storage_cushion (1.2) x leaf C and the heavy needleleaf foliage (slatop 0.005)
draws it below 1 x leaf C. Trials (PFT 2 only; every other PFT and parameter unchanged):

  A  fates_alloc_storage_cushion      1.2   -> 2.4     more margin above the threshold
  B  fates_mort_upthresh_cstarvation  1.0   -> 0.5     die only when storage is really low
  C  fates_leaf_slatop                0.005 -> 0.010   half the leaf C per leaf area
  D  A + C
  E  no parameter change; use_fates_dbh_init = .true. (closed-canopy cold start from
     fates_recruit_init_dbh). A falsification control: the mortality depends on storage /
     leaf C, not on stand closure, so the needleleaf PFT should still collapse.

Each trial is a create_clone --keepexe of the site's own AD case (same executable, surface,
forcing, CO2, AD settings, start date) with: a private copy of the case's FATES parameter
file holding the change (E: the namelist switch instead), the 09 diagnostic history (full FATES output + per-PFT mortality),
<years> years in 5-year segments, and new RUNDIR / DOUT_S_ROOT. The regenerated lnd_in must
equal the AD case's on every key except hist_* / fates_history_* and fates_paramfile (E:
use_fates_dbh_init instead of fates_paramfile), and the
parameter copy must differ from its source only in the intended PFT 2 entries, or nothing is
submitted. Controls are the existing *_DIAG50 re-runs (default parameters, same history).

Steps (login node):
  python -B 13_...py prepare [--sites DE-Obe FI-Sod] [--variants A B C D] [--years 50]   # NO Slurm
  python -B 13_...py submit  [--sites ...] [--variants ...]
  python -B 13_...py status  [--sites ...] [--variants ...]
  python -B 13_...py reset   --sites X --variants Y        # only a FAILED prepare that never ran
  python -B 13_...py cases   [--sites ...] [--variants ...] # LABEL:CASE list for scripts 08/11/12
"""
from __future__ import annotations

import argparse
import copy
import importlib.util
import json
import re
import shutil
from pathlib import Path

HERE = Path(__file__).resolve().parent
PFT = 2
PFT_NAME = "needleleaf_evergreen_extratrop_tree"
VARIANTS = {   # name: (description, PFT-2 parameter changes, namelist changes)
    "A": ("storage cushion 2.4", {"fates_alloc_storage_cushion": 2.4}, {}),
    "B": ("carbon-starvation upthresh 0.5", {"fates_mort_upthresh_cstarvation": 0.5}, {}),
    "C": ("slatop 0.010", {"fates_leaf_slatop": 0.010}, {}),
    "D": ("storage cushion 2.4 + slatop 0.010", {"fates_alloc_storage_cushion": 2.4, "fates_leaf_slatop": 0.010}, {}),
    "E": ("closed-canopy cold start (use_fates_dbh_init), default parameters", {}, {"use_fates_dbh_init": ".true."}),
}
STATE = "PARAM_TRIAL_STATE.json"
R = None   # module 09


def load09():
    global R
    for c in (HERE / "rerun.py", HERE / "09_clone_AD_diag_rerun.py"):
        if c.is_file():
            spec = importlib.util.spec_from_file_location("rerun09", c)
            R = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(R)
            return
    raise FileNotFoundError("module 09 (rerun.py) not found beside this script")


PARAM_DIR = None   # set after load09 (needs R.B)


# ------------------------------------------------------------------ parameter copies
def pft_axis(ent, npft):
    dims = ent.get("dims") or []
    if "fates_pft" in dims:
        return dims.index("fates_pft")
    import numpy as np
    shape = np.shape(ent["data"])
    if npft in shape:
        return list(shape).index(npft)
    raise ValueError("no PFT dimension")


def set_pft(data, axis, idx, value):
    """Return data (nested lists) with every element at position idx of the PFT axis set to value."""
    import numpy as np
    arr = np.moveaxis(np.array(data, dtype=float), axis, -1)
    arr[..., idx] = value
    return np.moveaxis(arr, -1, axis).tolist()


def make_param(base, variant):
    """Write (or verify) the private parameter copy for one variant; return (path, sha, changes)."""
    desc, changes, _ = VARIANTS[variant]
    if not changes:
        R.fail(f"variant {variant} has no parameter changes")
    src = json.loads(Path(base).read_text())
    prm = src["parameters"]
    names = [str(x).strip() for x in prm["fates_pftname"]["data"]]
    if names[PFT - 1] != PFT_NAME:
        R.fail(f"PFT {PFT} in {base} is {names[PFT - 1]!r}, expected {PFT_NAME}")
    new = copy.deepcopy(src)
    record = {}
    for key, val in changes.items():
        ent = new["parameters"].get(key)
        if ent is None:
            R.fail(f"{key} not in parameter file {base}")
        ax = pft_axis(ent, len(names))
        old = json.dumps(ent["data"])
        ent["data"] = set_pft(ent["data"], ax, PFT - 1, val)
        record[key] = {"pft": PFT, "new": val, "old_data": json.loads(old)}
    # independent check: only the intended PFT entries changed
    for key in set(prm) | set(new["parameters"]):
        a, b = prm.get(key), new["parameters"].get(key)
        if key not in changes:
            if a != b:
                R.fail(f"unintended change in {key}")
            continue
        import numpy as np
        A, Bv = np.asarray(a["data"], float), np.asarray(b["data"], float)
        ax = pft_axis(a, len(names))
        A, Bv = np.moveaxis(A, ax, -1), np.moveaxis(Bv, ax, -1)
        if not np.array_equal(np.delete(A, PFT - 1, axis=-1), np.delete(Bv, PFT - 1, axis=-1)):
            R.fail(f"{key}: other PFTs changed")
        if not np.allclose(Bv[..., PFT - 1], changes[key]):
            R.fail(f"{key}: PFT {PFT} not set to {changes[key]}")
        if {k: v for k, v in a.items() if k != "data"} != {k: v for k, v in b.items() if k != "data"}:
            R.fail(f"{key}: metadata changed")
    if {k: v for k, v in src.items() if k != "parameters"} != {k: v for k, v in new.items() if k != "parameters"}:
        R.fail("file-level attributes/dimensions changed")
    PARAM_DIR.mkdir(parents=True, exist_ok=True)
    out = PARAM_DIR / f"fates_params_needleleaf_trial_{variant}.json"
    text = json.dumps(new, indent=1) + "\n"
    rec = Path(str(out) + ".receipt.json")
    if out.exists():
        if out.read_text() != text:
            R.fail(f"existing {out} differs from what this script would write; not overwriting")
    else:
        tmp = Path(str(out) + ".tmp")
        tmp.write_text(text)
        tmp.replace(out)
        rec.write_text(json.dumps({"variant": variant, "description": desc, "source": str(base),
                                   "source_sha256": R.digest(base), "sha256": R.digest(out),
                                   "changes": record, "created_utc": R.utc()}, indent=2) + "\n")
    return out, R.digest(out), record


# ------------------------------------------------------------------ cases
def ident(site, variant, F7, P, years):
    i = R.ident(site, F7, P, years)
    new = f"{i['ad']}_FIX{variant}{years}"
    i.update(new=new, case=R.CASES / new, rundir=R.OUT / new / "run", archive=R.OUT / "archive" / new)
    return i


def set_nml(text, key, value):
    """Replace (or add) one user_nl entry; continuation lines of the old entry go too."""
    blocks = R.nml_blocks(text)
    keep = "".join("".join(l) for k, l in blocks if k != key.lower()).rstrip() + "\n"
    return keep + f"{key} = {value}\n"


def set_paramfile(text, path):
    return set_nml(text, "fates_paramfile", f"'{path}'")


def prepare(site, variant, F7, P, years):
    i = ident(site, variant, F7, P, years)
    ad, case = i["ad_case"], i["case"]
    print(f"\n=== {site} trial {variant} ({VARIANTS[variant][0]}): {i['ad']} -> {i['new']}", flush=True)
    st = case / STATE
    if case.exists() and st.is_file() and json.loads(st.read_text()).get("phase") != "PREPARE_ATTEMPTED":
        print(f"  already prepared ({json.loads(st.read_text())['phase']}); nothing changed", flush=True)
        return
    for p in (case, i["rundir"].parent, i["archive"]):
        if p.exists():
            R.fail(f"path exists without a completed prepare: {p} (use reset for a failed prepare)")
    if R.xq(ad, "CLM_ACCELERATED_SPINUP").lower() != "on":
        R.fail("AD case is not accelerated spin-up")
    srcroot = R.xq(ad, "SRCROOT")
    adv = {k: R.xq(ad, k) for k in ("RUN_TYPE", "RUN_STARTDATE", "CLM_FORCE_COLDSTART", "EXEROOT", "CLM_BLDNML_OPTS")}
    ad_lnd = (ad / "CaseDocs" / "lnd_in").read_text()
    ad_streams = (ad / "CaseDocs" / "datm.streams.xml").read_bytes()
    base_param = R.parse_nml(ad_lnd).get("clm_inparm.fates_paramfile") or next(
        (v for k, v in R.parse_nml(ad_lnd).items() if k.endswith(".fates_paramfile")), None)
    if not base_param:
        R.fail("fates_paramfile not found in AD lnd_in")
    base_param = base_param.strip("'\" ")
    _, pchanges, nchanges = VARIANTS[variant]
    if pchanges:
        param, psha, changes = make_param(base_param, variant)
    else:
        param, psha, changes = Path(base_param), R.digest(base_param), {}
    overlay = R.overlay_for(ad_lnd)
    found = R.fates_has(srcroot, R.DIAG_FIELDS)
    nl, old_hist, fields = R.edit_user_nl((ad / "user_nl_clm").read_text(), found)
    if pchanges:
        nl = set_paramfile(nl, param)
    for key, val in nchanges.items():
        nl = set_nml(nl, key, val)
    wall = R.cmd(["./xmlquery", "JOB_WALLCLOCK_TIME", "--subgroup", "case.run", "--value"], cwd=ad, timeout=90).strip()

    cimescripts = Path(srcroot) / "cime" / "scripts"
    R.cmd([cimescripts / "create_clone", "--case", case, "--clone", ad, "--keepexe"], cwd=cimescripts, timeout=420)
    (case / STATE).write_text(json.dumps({"phase": "PREPARE_ATTEMPTED", "at": R.utc()}) + "\n")
    if R.xq(case, "CASE") != i["new"]:
        R.fail("clone identity")
    settings = {"CONTINUE_RUN": "FALSE", "STOP_OPTION": "nyears", "STOP_N": str(R.SEG), "REST_OPTION": "nyears",
                "REST_N": str(R.SEG), "RESUBMIT": str(years // R.SEG - 1), "RESUBMIT_SETS_CONTINUE_RUN": "TRUE",
                "DOUT_S": "TRUE", "RUNDIR": str(i["rundir"]), "DOUT_S_ROOT": str(i["archive"])}
    for k, v in settings.items():
        R.xc(case, k, v)
    for k, v in settings.items():
        if R.xq(case, k).lower() != v.lower():
            R.fail(f"XML {k}={R.xq(case, k)} expected {v}")
    for k, v in adv.items():
        if R.xq(case, k) != v:
            R.fail(f"clone differs from AD in {k}")
    (case / "user_nl_clm").write_text(nl)
    i["rundir"].mkdir(parents=True, exist_ok=True)
    if not (case / ".case.run").is_file():
        R.cmd([case / "case.setup"], cwd=case, timeout=300)
    env, lock = case / "env_case.xml", case / "LockedFiles" / "env_case.xml"
    orig = env.read_bytes()
    try:
        R.xc(case, "COMP_ROOT_DIR_LND", str(overlay))
        R.cmd([case / "preview_namelists"], cwd=case, timeout=600)
    finally:
        R.xc(case, "COMP_ROOT_DIR_LND", "$SRCROOT")
    if env.read_bytes() != orig or (lock.is_file() and lock.read_bytes() != orig):
        R.fail("env_case.xml / lock not restored after overlay preview")
    a, n = R.parse_nml(ad_lnd), R.parse_nml((case / "CaseDocs" / "lnd_in").read_text())
    diff = sorted(k for k in set(a) | set(n) if a.get(k) != n.get(k))
    allowed = ([".fates_paramfile"] if pchanges else []) + [f".{k}" for k in nchanges]
    bad = [k for k in diff if not (R.is_hist(k) or any(k.endswith(x) for x in allowed))]
    if bad:
        R.fail(f"land namelist differs from the AD case beyond history settings and {allowed}:\n" +
               "\n".join(f"  {k}: AD={a.get(k)!r} NEW={n.get(k)!r}" for k in bad[:20]))
    pf = next((v for k, v in n.items() if k.endswith(".fates_paramfile")), "").strip("'\" ")
    if pf != str(param):
        R.fail(f"new lnd_in fates_paramfile is {pf!r}, expected {param}")
    for key, val in nchanges.items():
        got = next((v for k, v in n.items() if k.endswith("." + key)), None)
        if got is None or got.strip().lower() != val.lower():
            R.fail(f"new lnd_in {key} = {got!r}, expected {val}")
    if (case / "CaseDocs" / "datm.streams.xml").read_bytes() != ad_streams:
        R.fail("datm.streams.xml differs from the AD case")
    fin = next((v for k, v in n.items() if k.endswith(".hist_fincl1")), "")
    if any(f not in fin for f in fields):
        R.fail("hist_fincl1 incomplete in new lnd_in")
    state = {"phase": "VERIFIED_NOT_SUBMITTED", "at": R.utc(), "variant": variant, "description": VARIANTS[variant][0],
             "namelist_changes": nchanges,
             **{k: str(v) for k, v in i.items()}, "years": years, "settings": settings, "wallclock_per_segment": wall,
             "overlay": str(overlay), "paramfile": str(param), "paramfile_sha256": psha, "base_paramfile": base_param,
             "param_changes": changes, "hist_fincl1": fields, "lnd_in_keys_changed": diff,
             "lnd_in_sha256": R.digest(case / "CaseDocs" / "lnd_in"),
             "datm_streams_sha256": R.digest(case / "CaseDocs" / "datm.streams.xml")}
    (case / STATE).write_text(json.dumps(state, indent=2) + "\n")
    for key, c in changes.items():
        old = c["old_data"]
        print(f"  {key}: PFT {PFT} -> {c['new']} (file had {json.dumps(old)[:120]})", flush=True)
    for key, val in nchanges.items():
        print(f"  namelist: {key} = {val} (AD case: {next((v for k, v in a.items() if k.endswith('.' + key)), 'not set (default .false.)')})", flush=True)
    if nchanges.get("use_fates_dbh_init"):
        try:
            prm = json.loads(Path(base_param).read_text())["parameters"]
            print(f"  fates_recruit_init_dbh for PFT {PFT}: {prm['fates_recruit_init_dbh']['data'][PFT - 1]} cm", flush=True)
        except Exception:
            pass
    print(f"  parameter file: {param}" + (" (private copy)" if pchanges else " (unchanged, as in the AD case)"), flush=True)
    print(f"  lnd_in vs AD: only these keys differ: {', '.join(k.split('.', 1)[1] for k in diff)}", flush=True)
    print(f"  run: {years} y from {adv['RUN_STARTDATE']} as {years // R.SEG} x {R.SEG}-y segments, wallclock/segment {wall}", flush=True)
    print(f"  {site} {variant} VERIFIED, NOT SUBMITTED", flush=True)


def submit(site, variant, F7, P, years):
    i = ident(site, variant, F7, P, years)
    case, st = i["case"], i["case"] / STATE
    if not st.is_file():
        R.fail("not prepared")
    s = json.loads(st.read_text())
    if s.get("phase") != "VERIFIED_NOT_SUBMITTED":
        R.fail(f"phase is {s.get('phase')}; not submitting again (check squeue / CaseStatus)")
    if R.digest(case / "CaseDocs" / "lnd_in") != s["lnd_in_sha256"] or R.digest(s["paramfile"]) != s["paramfile_sha256"]:
        R.fail("lnd_in or parameter copy changed after verification")
    cs = (case / "CaseStatus").read_text(errors="replace") if (case / "CaseStatus").is_file() else ""
    if re.search(r"case\.submit starting|case\.run starting", cs) or R.queued(i["new"]):
        R.fail("already submitted or jobs exist")
    s.update(phase="SUBMIT_ATTEMPTED_UNCERTAIN", submit_attempt_utc=R.utc())
    st.write_text(json.dumps(s, indent=2) + "\n")
    out = R.cmd([case / "case.submit", "--skip-preview-namelist"], cwd=case, timeout=650)
    r, a = R.RUN_RE.search(out), R.ARCH_RE.search(out)
    if not r:
        R.fail("job id not parsed; DO NOT RETRY, check squeue. " + out[-600:])
    s.update(phase="SUBMITTED", run_job=r.group(1), archive_job=a.group(1) if a else "", submit_tail=out[-800:])
    st.write_text(json.dumps(s, indent=2) + "\n")
    print(f"{site} {variant}: SUBMITTED {i['new']} run={r.group(1)} archive={a.group(1) if a else '?'}", flush=True)


def status(site, variant, F7, P, years):
    i = ident(site, variant, F7, P, years)
    st = i["case"] / STATE
    phase = json.loads(st.read_text()).get("phase") if st.is_file() else "not prepared"
    h = i["archive"] / "lnd" / "hist"
    yrs = sorted({m.group(1) for p in (h.glob(f"{i['new']}.clm2.h0*.nc") if h.is_dir() else [])
                  for m in [re.search(r"\.h0a?\.(\d{4})-", p.name)] if m})
    q = R.queued(i["new"])
    print(f"{site} {variant}: {i['new']} | {phase} | archived years: {len(yrs)} | queue: {', '.join(r[2] for r in q) or 'none'}", flush=True)


def reset(site, variant, F7, P, years):
    i = ident(site, variant, F7, P, years)
    case, st = i["case"], i["case"] / STATE
    if not case.exists():
        print(f"{site} {variant}: nothing to reset", flush=True)
        return
    phase = json.loads(st.read_text()).get("phase") if st.is_file() else None
    if phase != "PREPARE_ATTEMPTED":
        R.fail(f"refusing: state is {phase!r}; only a failed prepare is reset")
    cs = (case / "CaseStatus").read_text(errors="replace") if (case / "CaseStatus").is_file() else ""
    if re.search(r"case\.submit starting|case\.run starting", cs) or R.queued(i["new"]):
        R.fail("refusing: submitted or has jobs")
    if i["archive"].exists() and any(i["archive"].iterdir()):
        R.fail("refusing: archive not empty")
    if i["rundir"].exists() and any(re.search(r"\.(clm2|cpl|datm)\.(h|r)", p.name) for p in i["rundir"].iterdir()):
        R.fail("refusing: model output in run directory")
    if not str(case).startswith(str(R.CASES) + "/") or not re.search(r"_FIX[A-Z]\d+$", case.name):
        R.fail(f"refusing: unexpected case path {case}")
    shutil.rmtree(case)
    for d in (i["rundir"].parent, i["archive"]):
        if d.exists() and d.name == i["new"] and str(d).startswith(str(R.OUT) + "/"):
            shutil.rmtree(d)
    print(f"{site} {variant}: failed prepare removed; run prepare again", flush=True)


def cases(site, variant, F7, P, years):
    i = ident(site, variant, F7, P, years)
    print(f"{site}_{variant}:{i['new']}:first50", flush=True)


def main(argv=None):
    global PARAM_DIR
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("action", choices=("prepare", "submit", "status", "reset", "cases"))
    ap.add_argument("--sites", nargs="+", default=["DE-Obe", "FI-Sod"])
    ap.add_argument("--variants", nargs="+", default=list(VARIANTS), choices=list(VARIANTS))
    ap.add_argument("--years", type=int, default=50)
    a = ap.parse_args(argv)
    load09()
    PARAM_DIR = R.B / "experiments/NonCompetitionObserved22/NeedleleafFixTrials/params"
    if a.years % R.SEG or a.years < R.SEG:
        ap.error(f"--years must be a multiple of {R.SEG}")
    F7, P = R.load07()
    bad = 0
    for s in a.sites:
        for v in a.variants:
            try:
                {"prepare": prepare, "submit": submit, "status": status, "reset": reset, "cases": cases}[a.action](s, v, F7, P, a.years)
            except Exception as exc:
                bad += 1
                print(f"{s} {v}: HOLD {exc}", flush=True)
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
