#!/usr/bin/env python3
"""Short diagnostic re-run of the first AD years with full FATES history output.

Why: the AD400 cases wrote only TOTSOMC, TOTSOMN, TLAI, FATES_GPP, FATES_NPP, TWS
and H2OSNO, and the needleleaf vegetation was already gone before NORMAL400
started. This clones each site's own AD case (create_clone --keepexe, same
executable, surface, forcing, parameter file, CO2, AD settings, start date) and
changes ONLY:
  * history: hist_empty_htapes=.false. (full default FATES set, as in NORMAL400)
             + the original AD fields + per-PFT mortality by type (_SZPF)
  * length:  <years> years in the same 5-year segments the AD cases used
  * RUNDIR / DOUT_S_ROOT: new directories named after the new case
Originals are never modified. The land namelist is regenerated through the same
private FATES-AD overlay the AD cases used, and must equal the AD case's
CaseDocs/lnd_in on every key except hist_*/fates_history_* or nothing is submitted.

Steps (login node):
  python -B 09_...py prepare [--sites DE-Obe FI-Sod] [--years 50]   # clone + verify, NO Slurm
  python -B 09_...py submit  [--sites ...]                          # case.submit --skip-preview-namelist
  python -B 09_...py status  [--sites ...]
  python -B 09_...py reset   --sites X    # only removes a FAILED prepare that never ran
Afterwards: 08_diagnose_collapse_mortality.py --ad-only SITE:CASE ...
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
USER = "ly3n24"
B = Path("/iridisfs/scratch/ly3n24/CLM_FATES")
CASES = B / "cases"
OUT = Path("/scratch/ly3n24/CTSM_FATES_OUTPUTS")
OVERLAYS = [B / "experiments/NonCompetitionObserved22" / d / "_private_ctsm_FATES_AD400_namelist_overlay"
            for d in ("Batch01_10", "Batch03_10", "Batch02_10")]
DEFAULT_SITES = ["DE-Obe", "FI-Sod"]
SEG = 5
DIAG_FIELDS = ["FATES_MORTALITY_CSTARV_SZPF", "FATES_MORTALITY_HYDRAULIC_SZPF", "FATES_MORTALITY_FREEZING_SZPF",
               "FATES_MORTALITY_BACKGROUND_SZPF", "FATES_MORTALITY_IMPACT_SZPF", "FATES_MORTALITY_TERMINATION_SZPF",
               "FATES_MORTALITY_SENESCENCE_SZPF", "FATES_MORTALITY_AGESCEN_SZPF", "FATES_NPLANT_SZPF",
               "FATES_DDBH_SZPF", "FATES_STOREC_TF_CANOPY_SZPF", "FATES_STOREC_TF_USTORY_SZPF"]
HIST_KEYS = ("hist_empty_htapes", "hist_fincl1")
RUN_RE = re.compile(r"Submitted job case\.run with id (\d+)")
ARCH_RE = re.compile(r"Submitted job case\.st_archive with id (\d+)")
STATE = "DIAG_RERUN_STATE.json"


def fail(s):
    raise RuntimeError(str(s))


def utc():
    return datetime.now(timezone.utc).isoformat()


def digest(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def cmd(argv, cwd=None, timeout=300):
    p = subprocess.run([str(a) for a in argv], cwd=cwd, capture_output=True, text=True, timeout=timeout)
    if p.returncode:
        fail(f"rc={p.returncode} {' '.join(map(str, argv))}\nOUT {p.stdout[-1500:]}\nERR {p.stderr[-1500:]}")
    return p.stdout


def xq(case, k):
    return cmd(["./xmlquery", k, "--value"], cwd=case, timeout=90).strip()


def xc(case, k, v):
    cmd([Path(case) / "xmlchange", f"{k}={v}"], cwd=case, timeout=90)


def load07():
    for c in (HERE / "fullseq.py", HERE / "07_plot_full_sequence_GPP_NEE_with_EC.py"):
        if c.is_file():
            spec = importlib.util.spec_from_file_location("fullseq07", c)
            m = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(m)
            P, _ = m.load_plot_module(None)
            return m, P
    fail("module 07 not found beside this script")


# ------------------------------------------------------------------ namelists
def nml_blocks(text):
    """user_nl text -> list of (key or None, [lines]); continuation lines stay with their key."""
    out, cur = [], None
    for ln in text.splitlines(keepends=True):
        m = re.match(r"^\s*([A-Za-z_][A-Za-z0-9_%]*)\s*=", ln)
        cont = cur is not None and out[-1][1] and out[-1][1][-1].split("!")[0].rstrip().endswith(",")
        if m and not cont:
            cur = m.group(1).lower()
            out.append((cur, [ln]))
        elif cont:
            out[-1][1].append(ln)
        else:
            cur = None
            out.append((None, [ln]))
    return out


def fincl_list(lines):
    return re.findall(r"'([^']+)'|\"([^\"]+)\"", "".join(lines).split("=", 1)[1]) if lines else []


def edit_user_nl(text, extra):
    blocks = nml_blocks(text)
    old = {k: "".join(l) for k, l in blocks if k in HIST_KEYS}
    orig = [a or b for a, b in fincl_list(next((l for k, l in blocks if k == "hist_fincl1"), []))]
    fields = list(dict.fromkeys(orig + extra))
    keep = "".join("".join(l) for k, l in blocks if k not in HIST_KEYS).rstrip() + "\n"
    new = ("\n! --- 09_clone_AD_diag_rerun: full FATES history + per-PFT mortality (only change vs AD case) ---\n"
           "hist_empty_htapes = .false.\n"
           "hist_fincl1 = " + ",\n              ".join(f"'{f}'" for f in fields) + "\n")
    return keep + new, old, fields


def parse_nml(text):
    """namelist file -> {group.key: normalized value}."""
    d, grp, key = {}, "", None
    for ln in text.splitlines():
        s = ln.strip()
        if not s or s.startswith("!"):
            continue
        if s.startswith("&"):
            grp, key = s[1:].strip().lower(), None
            continue
        if s == "/":
            grp, key = "", None
            continue
        m = re.match(r"^([A-Za-z_][A-Za-z0-9_%()]*)\s*=\s*(.*)$", s)
        if m:
            key = f"{grp}.{m.group(1).lower()}"
            d[key] = m.group(2)
        elif key:
            d[key] += " " + s
    return {k: re.sub(r"\s+", " ", v.strip().rstrip(",")) for k, v in d.items()}


def is_hist(k):
    name = k.split(".", 1)[-1]
    return name.startswith("hist_") or name.startswith("fates_history")


# ------------------------------------------------------------------ identities
def ident(site, F7, P, years):
    normal = dict(F7.JOB_CASES)[site]
    ad = P.env_value(CASES / normal, "RUN_REFCASE")
    new = f"{ad}_DIAG{years}"
    return {"site": site, "normal": normal, "ad": ad, "new": new, "ad_case": CASES / ad, "case": CASES / new,
            "rundir": OUT / new / "run", "archive": OUT / "archive" / new}


def fates_has(srcroot, names):
    src = Path(srcroot) / "src" / "fates"
    blob = "\n".join(p.read_text(errors="replace") for p in src.rglob("*.F90")) if src.is_dir() else ""
    if not blob:
        fail(f"FATES source not found under {src}")
    return [n for n in names if f"'{n}'" in blob or f'"{n}"' in blob]


def overlay_for(ad_lnd):
    """The private overlay this AD case's namelist was generated with (it shows in default paths)."""
    used = sorted(set(re.findall(r"(/[^'\"\s]*?/_private_ctsm_FATES_AD400_namelist_overlay)/", ad_lnd)))
    if len(used) > 1:
        fail("AD lnd_in refers to more than one overlay: " + ", ".join(used))
    cands = [Path(used[0])] if used else OVERLAYS
    o = next((c for c in cands if (c / "bld" / "CLMBuildNamelist.pm").is_file()), None)
    if o is None:
        fail("private FATES-AD namelist overlay not found: " + ", ".join(map(str, cands)))
    return o


def reset(site, F7, P, years):
    """Remove a FAILED prepare (state PREPARE_ATTEMPTED) that never ran: case dir, empty run dir, no archive."""
    i = ident(site, F7, P, years)
    case, st = i["case"], i["case"] / STATE
    if not case.exists():
        print(f"{site}: nothing to reset ({case} absent)", flush=True)
        return
    phase = json.loads(st.read_text()).get("phase") if st.is_file() else None
    if phase != "PREPARE_ATTEMPTED":
        fail(f"refusing: state is {phase!r}; only a failed prepare (PREPARE_ATTEMPTED) is reset")
    cs = (case / "CaseStatus").read_text(errors="replace") if (case / "CaseStatus").is_file() else ""
    if re.search(r"case\.submit starting|case\.run starting", cs) or queued(i["new"]):
        fail("refusing: this case was submitted or has jobs")
    if i["archive"].exists() and any(i["archive"].iterdir()):
        fail(f"refusing: archive not empty {i['archive']}")
    rd = i["rundir"]
    if rd.exists():
        bad = [p.name for p in rd.iterdir() if re.search(r"\.(clm2|cpl|datm)\.(h|r)", p.name)]
        if bad:
            fail(f"refusing: model output in {rd}: {bad[:3]}")
    import shutil
    if not str(case).startswith(str(CASES) + "/") or not case.name.endswith(f"_DIAG{years}"):
        fail(f"refusing: unexpected case path {case}")
    shutil.rmtree(case)
    for d in (i["rundir"].parent, i["archive"]):
        if d.exists() and d.name == i["new"] and str(d).startswith(str(OUT) + "/"):
            shutil.rmtree(d)
    print(f"{site}: failed prepare removed ({case.name}); run prepare again", flush=True)


def queued(name):
    out = cmd(["squeue", "-u", USER, "-h", "-o", "%i|%j|%T"], timeout=45)
    return [r for r in (ln.split("|") for ln in out.splitlines()) if len(r) >= 3 and name in r[1]]


# ------------------------------------------------------------------ prepare
def prepare(site, F7, P, years):
    i = ident(site, F7, P, years)
    ad, case = i["ad_case"], i["case"]
    print(f"\n=== {site}: {i['ad']} -> {i['new']}", flush=True)
    if not ad.is_dir():
        fail(f"AD case missing: {ad}")
    st = case / STATE
    if case.exists() and st.is_file() and json.loads(st.read_text()).get("phase") != "PREPARE_ATTEMPTED":
        print(f"  already prepared ({json.loads(st.read_text())['phase']}); nothing changed", flush=True)
        return json.loads(st.read_text())
    for p in (case, i["rundir"].parent, i["archive"]):
        if p.exists():
            fail(f"path exists without a completed prepare: {p} (inspect and remove by hand if it is a failed attempt)")
    if xq(ad, "CLM_ACCELERATED_SPINUP").lower() != "on":
        fail("AD case is not accelerated spin-up")
    srcroot = xq(ad, "SRCROOT")
    adv = {k: xq(ad, k) for k in ("RUN_TYPE", "RUN_STARTDATE", "CLM_FORCE_COLDSTART", "EXEROOT", "STOP_N", "CLM_BLDNML_OPTS")}
    if adv["STOP_N"] != str(SEG):
        print(f"  note: AD STOP_N={adv['STOP_N']} (segments here: {SEG} years)", flush=True)
    wall = cmd(["./xmlquery", "JOB_WALLCLOCK_TIME", "--subgroup", "case.run", "--value"], cwd=ad, timeout=90).strip()
    found = fates_has(srcroot, DIAG_FIELDS)
    dropped = [n for n in DIAG_FIELDS if n not in found]
    ad_lnd = (ad / "CaseDocs" / "lnd_in").read_text()
    overlay = overlay_for(ad_lnd)
    ad_streams = (ad / "CaseDocs" / "datm.streams.xml").read_bytes()
    new_nl, old_hist, fields = edit_user_nl((ad / "user_nl_clm").read_text(), found)

    case.parent.mkdir(parents=True, exist_ok=True)
    cimescripts = Path(srcroot) / "cime" / "scripts"
    cmd([cimescripts / "create_clone", "--case", case, "--clone", ad, "--keepexe"], cwd=cimescripts, timeout=420)
    (case / STATE).write_text(json.dumps({"phase": "PREPARE_ATTEMPTED", "at": utc()}) + "\n")
    if xq(case, "CASE") != i["new"]:
        fail("clone identity")
    settings = {"CONTINUE_RUN": "FALSE", "STOP_OPTION": "nyears", "STOP_N": str(SEG), "REST_OPTION": "nyears",
                "REST_N": str(SEG), "RESUBMIT": str(years // SEG - 1), "RESUBMIT_SETS_CONTINUE_RUN": "TRUE",
                "DOUT_S": "TRUE", "RUNDIR": str(i["rundir"]), "DOUT_S_ROOT": str(i["archive"])}
    for k, v in settings.items():
        xc(case, k, v)
    for k, v in settings.items():
        if xq(case, k).lower() != v.lower():
            fail(f"XML {k}={xq(case, k)} expected {v}")
    for k, v in adv.items():
        if k != "STOP_N" and xq(case, k) != v:
            fail(f"clone differs from AD in {k}: {xq(case, k)} vs {v}")
    (case / "user_nl_clm").write_text(new_nl)
    i["rundir"].mkdir(parents=True, exist_ok=True)
    if not (case / ".case.run").is_file():
        cmd([case / "case.setup"], cwd=case, timeout=300)
    env, lock = case / "env_case.xml", case / "LockedFiles" / "env_case.xml"
    orig = env.read_bytes()
    try:
        xc(case, "COMP_ROOT_DIR_LND", str(overlay))
        cmd([case / "preview_namelists"], cwd=case, timeout=600)
    finally:
        xc(case, "COMP_ROOT_DIR_LND", "$SRCROOT")
    if env.read_bytes() != orig or (lock.is_file() and lock.read_bytes() != orig):
        fail("env_case.xml / lock not restored after overlay preview")

    new_lnd = (case / "CaseDocs" / "lnd_in").read_text()
    a, n = parse_nml(ad_lnd), parse_nml(new_lnd)
    diff = sorted(k for k in set(a) | set(n) if a.get(k) != n.get(k))
    bad = [k for k in diff if not is_hist(k)]
    if bad:
        fail("land namelist differs from the AD case beyond history settings:\n" +
             "\n".join(f"  {k}: AD={a.get(k)!r} NEW={n.get(k)!r}" for k in bad[:20]))
    if (case / "CaseDocs" / "datm.streams.xml").read_bytes() != ad_streams:
        fail("datm.streams.xml differs from the AD case")
    emp = next((v for k, v in n.items() if k.endswith(".hist_empty_htapes")), "")
    if ".false." not in emp.lower():
        fail(f"hist_empty_htapes not .false. in new lnd_in: {emp!r}")
    fin = next((v for k, v in n.items() if k.endswith(".hist_fincl1")), "")
    missing = [f for f in fields if f not in fin]
    if missing:
        fail("hist_fincl1 in new lnd_in lacks " + ", ".join(missing))
    dim = next((v for k, v in n.items() if k.endswith(".fates_history_dimlevel")), None)
    state = {"phase": "VERIFIED_NOT_SUBMITTED", "at": utc(), **{k: str(v) for k, v in i.items()},
             "years": years, "settings": settings, "wallclock_per_segment": wall, "overlay": str(overlay),
             "old_hist_lines": old_hist, "hist_fincl1": fields, "dropped_not_in_fates_source": dropped,
             "fates_history_dimlevel": dim, "lnd_in_hist_keys_changed": diff,
             "lnd_in_sha256": digest(case / "CaseDocs" / "lnd_in"),
             "datm_streams_sha256": digest(case / "CaseDocs" / "datm.streams.xml")}
    (case / STATE).write_text(json.dumps(state, indent=2) + "\n")
    print("  AD history lines (removed):", flush=True)
    for v in old_hist.values():
        print("    " + v.rstrip().replace("\n", "\n    "), flush=True)
    print(f"  new: hist_empty_htapes = .false. ; hist_fincl1 = {len(fields)} fields", flush=True)
    print(f"  per-PFT mortality fields not in this FATES version (skipped): {', '.join(dropped) or 'none'}", flush=True)
    print(f"  fates_history_dimlevel in lnd_in: {dim or 'not set (model default)'}", flush=True)
    print(f"  lnd_in vs AD: only these keys differ: {', '.join(k.split('.', 1)[1] for k in diff)}", flush=True)
    print(f"  run: {years} y from {adv['RUN_STARTDATE']} as {years // SEG} x {SEG}-y segments, wallclock/segment {wall}", flush=True)
    print(f"  RUNDIR {i['rundir']}\n  archive {i['archive']}", flush=True)
    print(f"  {site} VERIFIED, NOT SUBMITTED", flush=True)
    return state


# ------------------------------------------------------------------ submit / status
def submit(site, F7, P, years):
    i = ident(site, F7, P, years)
    case = i["case"]
    st = case / STATE
    if not st.is_file():
        fail("not prepared")
    s = json.loads(st.read_text())
    if s.get("phase") != "VERIFIED_NOT_SUBMITTED":
        fail(f"phase is {s.get('phase')}; not submitting again (check squeue / CaseStatus)")
    if digest(case / "CaseDocs" / "lnd_in") != s["lnd_in_sha256"] or \
            digest(case / "CaseDocs" / "datm.streams.xml") != s["datm_streams_sha256"]:
        fail("CaseDocs changed after verification")
    cs = (case / "CaseStatus").read_text(errors="replace") if (case / "CaseStatus").is_file() else ""
    if re.search(r"case\.submit starting|case\.run starting", cs):
        fail("CaseStatus already shows a submission")
    if queued(i["new"]):
        fail("jobs with this case name are already queued")
    for k, v in s["settings"].items():
        if xq(case, k).lower() != v.lower():
            fail(f"XML {k} changed to {xq(case, k)}")
    s.update(phase="SUBMIT_ATTEMPTED_UNCERTAIN", submit_attempt_utc=utc())
    st.write_text(json.dumps(s, indent=2) + "\n")
    out = cmd([case / "case.submit", "--skip-preview-namelist"], cwd=case, timeout=650)
    r, a = RUN_RE.search(out), ARCH_RE.search(out)
    if not r:
        fail("job id not parsed; DO NOT RETRY, check squeue. " + out[-600:])
    s.update(phase="SUBMITTED", run_job=r.group(1), archive_job=a.group(1) if a else "", submit_tail=out[-800:])
    st.write_text(json.dumps(s, indent=2) + "\n")
    print(f"{site}: SUBMITTED {i['new']} run={r.group(1)} archive={a.group(1) if a else '?'} ({years} y in {SEG}-y segments)", flush=True)


def status(site, F7, P, years):
    i = ident(site, F7, P, years)
    st = i["case"] / STATE
    phase = json.loads(st.read_text()).get("phase") if st.is_file() else "not prepared"
    hist = sorted((i["archive"] / "lnd" / "hist").glob(f"{i['new']}.clm2.h0*.nc")) if (i["archive"] / "lnd" / "hist").is_dir() else []
    yrs = sorted({m.group(1) for p in hist for m in [re.search(r"\.h0a?\.(\d{4})-", p.name)] if m})
    q = queued(i["new"])
    tail = ""
    cs = i["case"] / "CaseStatus"
    if cs.is_file():
        tail = " | ".join(l.strip() for l in cs.read_text(errors="replace").splitlines()[-2:])
    print(f"{site}: {i['new']} | {phase} | archived history years: {len(yrs)}"
          f"{(' (' + yrs[0] + '-' + yrs[-1] + ')') if yrs else ''} | queue: {', '.join(r[2] for r in q) or 'none'}\n   {tail}", flush=True)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("action", choices=("prepare", "submit", "status", "reset"))
    ap.add_argument("--sites", nargs="+", default=DEFAULT_SITES)
    ap.add_argument("--years", type=int, default=50)
    a = ap.parse_args(argv)
    if a.years % SEG or a.years < SEG:
        ap.error(f"--years must be a multiple of {SEG}")
    F7, P = load07()
    unknown = [s for s in a.sites if s not in dict(F7.JOB_CASES)]
    if unknown:
        ap.error("not in the 07 case list: " + ", ".join(unknown))
    bad = 0
    for s in a.sites:
        try:
            {"prepare": prepare, "submit": submit, "status": status, "reset": reset}[a.action](s, F7, P, a.years)
        except Exception as exc:
            bad += 1
            print(f"{s}: HOLD {exc}", flush=True)
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
