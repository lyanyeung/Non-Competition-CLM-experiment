#!/usr/bin/env python3
"""Cross-cohort: verified AD400 -> direct NORMAL400 (80 x 5 years, no Normal5 smoke).

Covers the AD400 cases that have no Normal stage of their own:

  AmeriFlux Batch02  Stage06 <SITE>_AMF_B02_FIXNC_AD400_DIRECT (10 sites; US-ICh/ICt
                     after the Stage07 surface repair)
  ICOS Batch02       Stage40 IT-Noe, Stage43 ES-LJu / FR-FBn / CH-Lae,
                     Stage44 DK-Sor / BE-Bra (ICOS basal-area PFT rebuild)
  AmeriFlux Batch04  <SITE>_AMF_B04_FIXNC_AD400_BASETA_V1 (10 sites, FIXNC arm)
  DE-Tha             DE-Tha_OBSPFT_NC_V1_AD400 (AD5 + AD395)

The Batch04 and DE-Tha cases have no machine-readable ledger in this repository, so the
first job of the AD400 chain is taken from Slurm accounting instead: the 80th-last run job
of that exact case name. Every run/st_archive job from there on must be COMPLETED 0:0.
For every site the archive must also hold the full restart sequence Y+5, Y+10 ... Y+400.

Not covered: AmeriFlux Batch01 (use its Stage21 controller), ICOS Batch01/03 and the
four original ICOS Batch02 sites (they already have Normal cases).

Method = AmeriFlux Batch01 Stage21 / ICOS Batch02 Stage27 / DE-Tha Stage14, which
completed Normal runs on IRIDIS6:

  AD400 complete  nothing queued; every run/st_archive job since the ledger's first
                  run job COMPLETED 0:0, >= 80 of each; last CaseStatus events success;
                  RESUBMIT exhausted; latest archived restart = Y+400 (clm2+datm+cpl);
                  land spinup_state = 2.
  stage-normal    NEW case <AD name with _AD400 -> _NORMAL400> from create_clone
                  --keepexe; SourceMods pinned to the executable-owner case; hybrid,
                  RUN_REFCASE = AD case, RUN_STARTDATE = RUN_REFDATE = Y+400-01-01,
                  CLM_ACCELERATED_SPINUP = off; the three AD restarts are COPIED
                  (sha-checked) into the new RUNDIR with rpointers; finidat = copied
                  land restart; explicit spinup_state removed; fates_paramfile pinned
                  to the AD case's effective file. Namelists from the shared CTSM.
                  lnd_in must equal the AD case in fsurdat, fates_paramfile, co2_ppmv,
                  use_crop, fates_spitfire_mode, hist_fincl1 and the FATES switches;
                  DATM streams must be identical. No Slurm.
  submit          operator decision (26-27 Oct 2026): no Normal5 smoke. One
                  case.submit --skip-preview-namelist with STOP_N=5, RESUBMIT=79.
  audit-first5    first segment archived at Y+405 with spinup_state = 0.
  audit-normal400 80+80 jobs, restart Y+800, spinup_state = 0.

AD cases, their run/archive, surfaces, forcing, parameter files, the executable and
the shared CTSM are only read. Ledgers: <EXP22>/Cross_cohort_NORMAL400_direct.
Every stateful step is marked ATTEMPTED before it acts; never rerun one after an
attempt. Run long steps under nohup (SSH drops).

Actions (--sites limits; read-only ones default to all registered sites):
  self-test
  audit-ad400              READ ONLY
  stage-normal             --sites ... --confirm STAGE_CROSS_COHORT_NORMAL400_CASES_NO_SLURM
                           [--carry-ad-streams]  for AD cases whose effective DATM streams were
                           written into CaseDocs + RUNDIR after preview (Batch02 Stage25/34/36/44/45):
                           a regenerated Normal stream file points back to the original forcing, so
                           the AD case's EXACT effective datm.streams.xml is copied into the Normal
                           CaseDocs and RUNDIR (AD RUNDIR copy must equal AD CaseDocs byte for byte,
                           and every listed data file must exist). Recorded in the ledger.
  submit                   --sites ... --confirm SUBMIT_CROSS_COHORT_NORMAL400_DIRECT_80x5_ONCE
  audit-first5             READ ONLY
  audit-normal400          READ ONLY
  inspect-interrupted      READ ONLY: a stage-normal that was cut off
  quarantine-interrupted   --sites ... --confirm QUARANTINE_INTERRUPTED_NORMAL400_STAGE_NO_SLURM
  status                   READ ONLY

800 model years is the design, not proof of equilibrium.
"""
from __future__ import annotations
import argparse, configparser, hashlib, json, os, re, resource, shutil, subprocess, sys
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

BASE = Path("/iridisfs/scratch/ly3n24/CLM_FATES")
CTSM = BASE / "CTSM"
CIMESCRIPTS = CTSM / "cime/scripts"
OUT = Path("/scratch/ly3n24/CTSM_FATES_OUTPUTS")
EXP22 = BASE / "experiments/NonCompetitionObserved22"
D = EXP22 / "Cross_cohort_NORMAL400_direct"
USER = "ly3n24"
SACCT_START = "2026-10-01"
MIN_STACK_KB = 65536
SEGMENTS = 80
SEG_YEARS = 5
POINTERS = (("rpointer.lnd", "clm2"), ("rpointer.atm", "datm"), ("rpointer.cpl", "cpl"))
FATES_FLAGS = {"use_fates": ".true.", "use_fates_sp": ".false.", "use_fates_fixed_biogeog": ".true.",
               "use_fates_nocomp": ".true.", "use_cn": ".false."}
SAME_XML = ("PTS_LAT", "PTS_LON", "PTS_DOMAINFILE", "CCSM_CO2_PPMV", "CLM_BLDNML_OPTS", "CALENDAR", "ATM_NCPL",
            "DATM_MODE", "DATM_YR_START", "DATM_YR_END", "DATM_YR_ALIGN", "EXEROOT", "MPI_RUN_COMMAND")
SAME_LND = ("fsurdat", "fates_paramfile", "use_crop", "co2_ppmv", "fates_spitfire_mode")
ACK_STAGE = "STAGE_CROSS_COHORT_NORMAL400_CASES_NO_SLURM"
ACK_SUB = "SUBMIT_CROSS_COHORT_NORMAL400_DIRECT_80x5_ONCE"
ACK_Q = "QUARANTINE_INTERRUPTED_NORMAL400_STAGE_NO_SLURM"
RUN_RE = re.compile(r"Submitted job case\.run with id (\d+)")
ARCH_RE = re.compile(r"Submitted job case\.st_archive with id (\d+)")

AMF_B02 = ("US-BZS", "US-CMW", "US-EML", "US-GLE", "US-Ha1", "US-Ho1", "US-Ho2", "US-Ho3", "US-ICh", "US-ICt")
STAGE43 = {"ES-LJu": "ES-LJu_B02_FIXNC_MET24_GPPNPP_HISTFIX_AD400",
           "FR-FBn": "FR-FBn_B02_FIXNC_FOREST_GPPNPP_HISTFIX_AD400",
           "CH-Lae": "CH-Lae_B02_FIXNC_MET36_GPPNPP_HISTFIX_AD400"}
STAGE44 = {"DK-Sor": "DK-Sor_B02_FIXNC_ICOS_DBF100_AD400",
           "BE-Bra": "BE-Bra_B02_FIXNC_ICOS_ENF84_DBF16_AD400"}
AMF_B04 = ("US-Rpf", "US-SP1", "US-SRG", "US-SRM", "US-Seg", "US-Ses", "US-Slt", "US-Syv", "US-Ton", "US-Uaf")


def registry():
    """site -> AD case, its own ledger, accepted ledger phases and the key holding the first run job."""
    a02 = EXP22 / "AmeriFlux_Batch02_10/Stage06_direct_AD400"
    b02 = EXP22 / "Batch02_10"
    r = {}
    for s in AMF_B02:
        r[s] = dict(cohort="AmeriFlux Batch02 Stage06", ad=f"{s}_AMF_B02_FIXNC_AD400_DIRECT",
                    ledger=a02 / f"{s}_AD400_DIRECT_state.json", phases=("AD400_SUBMITTED",), job="first_run_job")
    r["IT-Noe"] = dict(cohort="ICOS Batch02 Stage40", ad="IT-Noe_B02_FIXNC_GPPNPP_HISTFIX_AD400",
                       ledger=b02 / "stage40_IT_Noe_GPPNPP_histfix_AD400/submission_attempt.json",
                       phases=("SUBMITTED_NOT_YET_COMPLETED",), job="run_jobid")
    for s, n in STAGE43.items():
        r[s] = dict(cohort="ICOS Batch02 Stage43", ad=n, ledger=b02 / "stage43_five_GPP_NPP_histfix_AD400" / f"{s}_submit.json",
                    phases=("SUBMITTED_AD400_NOT_COMPLETED",), job="run_jobid")
    for s, n in STAGE44.items():
        r[s] = dict(cohort="ICOS Batch02 Stage44", ad=n, ledger=b02 / "stage44_ICOS_PFT_rebuild" / f"{s}_state.json",
                    phases=("AD400_SUBMITTED",), job="first_run_job")
    for s in AMF_B04:
        r[s] = dict(cohort="AmeriFlux Batch04 FIXNC arm", ad=f"{s}_AMF_B04_FIXNC_AD400_BASETA_V1",
                    ledger=None, phases=(), job=None)
    r["DE-Tha"] = dict(cohort="DE-Tha pilot", ad="DE-Tha_OBSPFT_NC_V1_AD400", ledger=None, phases=(), job=None)
    return r


REG = registry()
ORDER = tuple(REG)


def fail(s): raise RuntimeError(str(s))
def utc(): return datetime.now(timezone.utc).isoformat()
def stamp(y): return f"{y:04d}-01-01-00000"


def digest(p):
    h = hashlib.sha256()
    with Path(p).open("rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""): h.update(b)
    return h.hexdigest()


def cmd(argv, cwd=None, timeout=300):
    p = subprocess.run([str(x) for x in argv], cwd=cwd, text=True, stdout=subprocess.PIPE,
                       stderr=subprocess.STDOUT, timeout=timeout)
    if p.returncode: fail("FAILED " + str(argv) + "\n" + p.stdout[-3000:])
    return p.stdout


def xq(case, key): return cmd(["./xmlquery", key, "--value"], cwd=case, timeout=90).strip()
def xc(case, key, val): cmd([Path(case) / "xmlchange", f"{key}={val}"], cwd=case, timeout=90)


def nml_get(text, key):
    found = re.findall(r"(?im)^\s*" + re.escape(key) + r"\s*=\s*([^\r\n!]*)", text)
    if len(found) > 1: fail("Ambiguous " + key)
    return found[0].strip().rstrip(",").strip().strip("'\"").strip() if found else None


def hist_fields(text):
    m = re.search(r"(?ims)^[ \t]*hist_fincl1[ \t]*=[ \t]*(.*?)(?=^[ \t]*[A-Za-z_]\w*[ \t]*=|^[ \t]*/[ \t]*$|\Z)", text)
    return re.findall(r"['\"]([^'\"]+)['\"]", m.group(1)) if m else []


def nml_set(text, key, value):
    pat = r"(?im)^[ \t]*" + re.escape(key) + r"[ \t]*=[^\r\n]*$"
    m = list(re.finditer(pat, text))
    if len(m) > 1: fail("Duplicated key " + key)
    rep = key + " = " + value
    return text[:m[0].start()] + rep + text[m[0].end():] if m else text.rstrip() + "\n" + rep + "\n"


def nml_del(text, key):
    pat = r"(?im)^[ \t]*" + re.escape(key) + r"[ \t]*=[^\r\n]*(\r?\n)?"
    if len(re.findall(pat, text)) > 1: fail("Duplicated key " + key)
    return re.sub(pat, "", text)


def load(p): return json.loads(Path(p).read_text()) if Path(p).is_file() else {}
def save(p, obj):
    Path(p).parent.mkdir(parents=True, exist_ok=True)
    t = Path(str(p) + ".tmp"); t.write_text(json.dumps(obj, indent=2, default=str) + "\n"); t.replace(p)


def pick(sites, default=ORDER):
    if not sites: return list(default)
    bad = [s for s in sites if s not in REG]
    if bad: fail("Not in the cross-cohort registry: " + ",".join(bad) +
                 " (AmeriFlux Batch01 uses its Stage21 controller)")
    return [s for s in ORDER if s in sites]


# ------------------------------------------------------------- names / paths
def ad_name(s): return REG[s]["ad"]
def ad_case(s): return BASE / "cases" / ad_name(s)
def ad_run(s): return OUT / ad_name(s) / "run"
def ad_arch(s): return OUT / "archive" / ad_name(s)
def n_name(s):
    a = ad_name(s)
    if a.count("_AD400") != 1: fail("unexpected AD case name " + a)
    return a.replace("_AD400", "_NORMAL400")
def n_case(s): return BASE / "cases" / n_name(s)
def n_run(s): return OUT / n_name(s) / "run"
def n_arch(s): return OUT / "archive" / n_name(s)
def n_ledger(s): return D / f"{s}_NORMAL400_state.json"


# ------------------------------------------------------------- scheduler
def queue_rows():
    out = cmd(["squeue", "-u", USER, "-h", "-o", "%i|%j|%T"], timeout=45)
    return [ln.split("|") for ln in out.splitlines() if len(ln.split("|")) >= 3]


def queued(name, rows=None):
    rows = queue_rows() if rows is None else rows
    return [r for r in rows if r[1] in ("run." + name, "st_archive." + name)]


def sacct_name(name):
    out = cmd(["sacct", "-X", "-n", "-P", "-u", USER, "-S", SACCT_START, "--name", f"run.{name},st_archive.{name}",
               "--format=JobIDRaw,JobName%100,State,ExitCode"], timeout=90)
    rows = []
    for ln in out.splitlines():
        p = [x.strip() for x in ln.split("|")]
        if len(p) >= 4 and p[0].isdigit() and p[1] in ("run." + name, "st_archive." + name):
            rows.append((int(p[0]), p[1], p[2], p[3]))
    return rows


def stack_guard():
    soft, hard = resource.getrlimit(resource.RLIMIT_STACK)
    if soft != resource.RLIM_INFINITY and soft < MIN_STACK_KB * 1024:
        fail(f"Stack soft limit {soft // 1024} KB < {MIN_STACK_KB} KB. Run `ulimit -s unlimited` in THIS shell first.")
    child = subprocess.run([sys.executable, "-c", "import resource;print(resource.getrlimit(resource.RLIMIT_STACK)[0])"],
                           capture_output=True, text=True, timeout=30, check=True)
    if int(child.stdout.strip()) != soft: fail("child process does not inherit the stack limit")
    env = os.environ.get("SBATCH_PROPAGATE", "")
    if env and not ({"ALL", "STACK"} & set(env.upper().split(","))): fail("SBATCH_PROPAGATE excludes STACK: " + env)
    cfg = cmd(["scontrol", "show", "config"], timeout=45)
    m = re.search(r"(?im)^\s*PropagateResourceLimits\s*=\s*(\S+)", cfg)
    prop = m.group(1) if m else ""
    if prop.upper() != "ALL" and "STACK" not in prop.upper().split(","):
        fail("Slurm PropagateResourceLimits does not include STACK: " + repr(prop))
    lab = "unlimited" if soft == resource.RLIM_INFINITY else f"{soft // 1024}KiB"
    print("STACK GUARD PASS soft=", lab, "PropagateResourceLimits=", prop, flush=True)
    return {"soft": lab, "propagate": prop}


# ------------------------------------------------------------- restarts
def restart_state(path):
    import numpy as np
    from netCDF4 import Dataset
    with Dataset(str(path), "r") as ds:
        if "spinup_state" in ds.variables:
            a = np.asarray(ds.variables["spinup_state"][:]).ravel()
            if a.size != 1: fail("bad spinup_state shape " + str(path))
            return int(a[0])
        if "spinup_state" in ds.ncattrs(): return int(ds.getncattr("spinup_state"))
    return None


def triplet(name, arch, y):
    folder = arch / "rest" / stamp(y)
    if not folder.is_dir(): fail(name + ": archived restart folder missing " + str(folder))
    files = {}
    for _, c in POINTERS:
        p = folder / f"{name}.{c}.r.{stamp(y)}.nc"
        if not p.is_file() or p.is_symlink() or p.stat().st_size < 1024: fail(name + ": missing " + str(p))
        files[c] = p
    return files


def latest(arch):
    r = arch / "rest"
    n = sorted(x.name for x in r.iterdir() if x.is_dir()) if r.is_dir() else []
    return (n[-1] if n else None), len(n)


def submit_options_ok(case):
    cp = configparser.RawConfigParser(); cp.read(Path(case) / ".submit_options")
    return cp.has_section("SubmitOptions") and cp.getboolean("SubmitOptions", "skip_pnl", fallback=False)


def chain(name, case, arch, first, final, want):
    if queued(name): fail(name + ": jobs still queued")
    rows = [r for r in sacct_name(name) if r[0] >= int(first)]
    bad = [r for r in rows if (r[2], r[3]) != ("COMPLETED", "0:0")]
    if bad: fail(name + ": non-COMPLETED jobs since " + str(first) + ": " + repr(bad[:4]))
    runs = [r for r in rows if r[1].startswith("run.")]; arcs = [r for r in rows if r[1].startswith("st_archive.")]
    if len(runs) < SEGMENTS or len(arcs) < SEGMENTS:
        l, _ = latest(arch)
        fail(f"{name}: {len(runs)} run / {len(arcs)} archive COMPLETED; need {SEGMENTS} (latest restart {l})")
    cs = (case / "CaseStatus").read_text(errors="replace")
    lr = re.findall(r"case\.run (success|error)", cs); la = re.findall(r"st_archive (success|error)", cs)
    if not lr or lr[-1] != "success" or not la or la[-1] != "success": fail(name + ": last CaseStatus event not success")
    if xq(case, "RESUBMIT") != "0": fail(name + ": RESUBMIT not exhausted")
    l, n = latest(arch)
    if l != stamp(final): fail(f"{name}: latest restart {l}, expected {stamp(final)}")
    files = triplet(name, arch, final); st = restart_state(files["clm2"])
    if st != want: fail(f"{name}: final spinup_state={st}, expected {want}")
    return {"case": name, "runs": len(runs), "archives": len(arcs), "final": stamp(final), "rest_dirs": n,
            "spinup_state": st, "files": files}


def start_year(case):
    d = xq(case, "RUN_STARTDATE")
    if not re.fullmatch(r"\d{4}-01-01", d): fail(f"{case.name}: RUN_STARTDATE not Jan-01: {d}")
    return int(d[:4])


def ad_first_job(s):
    r = REG[s]
    if r["ledger"] is None:  # no ledger: the 80th-last run job of this exact case name
        runs = sorted(x[0] for x in sacct_name(ad_name(s)) if x[1].startswith("run."))
        if len(runs) < SEGMENTS: fail(f"{s}: only {len(runs)} run jobs in Slurm accounting since {SACCT_START}")
        return str(runs[-SEGMENTS])
    o = load(r["ledger"])
    if not o: fail(f"{s}: AD ledger missing {r['ledger']}")
    if o.get("phase") not in r["phases"]: fail(f"{s}: AD ledger phase {o.get('phase')} (need {'/'.join(r['phases'])})")
    j = str(o.get(r["job"]) or "")
    if not j.isdigit(): fail(f"{s}: AD ledger has no {r['job']}")
    for k in ("skip_preview_persisted", "skip_pnl_persisted"):
        if k in o and o[k] is not True: fail(f"{s}: AD ledger {k}={o[k]}")
    return j


def ad400_one(s):
    j = ad_first_job(s); case = ad_case(s)
    if not case.is_dir(): fail(s + ": AD case missing " + str(case))
    if xq(case, "CLM_ACCELERATED_SPINUP").lower() != "on": fail(s + ": AD case CLM_ACCELERATED_SPINUP is not on")
    lnd = (case / "CaseDocs/lnd_in").read_text()
    for k, v in {**FATES_FLAGS, "spinup_state": "2"}.items():
        if nml_get(lnd, k) != v: fail(f"{s}: AD lnd_in {k}={nml_get(lnd, k)}")
    if not submit_options_ok(case): fail(s + ": AD skip-preview-namelist not persisted")
    if Path(xq(case, "COMP_ROOT_DIR_LND")).resolve() != CTSM.resolve():
        fail(s + ": AD case land root is not the shared CTSM (a Normal clone would inherit it): " + xq(case, "COMP_ROOT_DIR_LND"))
    y = start_year(case)
    r = chain(ad_name(s), case, ad_arch(s), j, y + 400, 2)
    have = {d.name for d in (ad_arch(s) / "rest").iterdir() if d.is_dir()}
    gap = [stamp(y + SEG_YEARS * k) for k in range(1, SEGMENTS + 1) if stamp(y + SEG_YEARS * k) not in have]
    if gap: fail(f"{s}: restart sequence incomplete, missing {gap[:3]} ({len(gap)} of {SEGMENTS})")
    r.update(start_year=y, first_job=j, cohort=REG[s]["cohort"], normal=load(n_ledger(s)).get("phase", "-"))
    return r


# ------------------------------------------------------------- SourceMods
def exe_owner_sourcemods(case):
    owner = BASE / "cases" / Path(xq(case, "EXEROOT")).parent.name / "SourceMods"
    if not owner.is_dir(): fail(f"executable-owner SourceMods missing or dangling: {owner}")
    real = owner.resolve()
    if not real.is_dir(): fail(f"cannot resolve executable-owner SourceMods: {owner}")
    return real


def pin_sourcemods(case):
    sm = Path(case) / "SourceMods"
    if sm.is_dir() and not sm.is_symlink(): return {"SourceMods": "real directory, unchanged"}
    if not sm.is_symlink(): fail(f"SourceMods missing in {case}")
    before = os.readlink(sm); owner = exe_owner_sourcemods(case)
    if Path(before) == owner and sm.exists(): return {"SourceMods": f"already -> {owner}"}
    sm.unlink(); sm.symlink_to(owner)
    if sm.resolve() != owner: fail(f"{case}: SourceMods relink failed")
    return {"SourceMods_before": before, "SourceMods_now": str(owner)}


# ------------------------------------------------------------- Normal400
def ad_effective_streams(s):
    """The stream file the AD run actually read: AD RUNDIR copy, which must equal AD CaseDocs."""
    doc, run = ad_case(s) / "CaseDocs/datm.streams.xml", ad_run(s) / "datm.streams.xml"
    if not doc.is_file() or not run.is_file(): fail(s + ": AD CaseDocs or RUNDIR datm.streams.xml missing")
    if digest(doc) != digest(run): fail(s + ": AD CaseDocs and RUNDIR datm.streams.xml differ; which one the AD read is ambiguous")
    files = [e.text.strip() for e in ET.parse(run).getroot().iter("file") if (e.text or "").strip()]
    missing = [f for f in files if not Path(f).is_file()]
    if not files or missing: fail(f"{s}: AD stream data files missing ({len(missing)}): {missing[:3]}")
    return run, digest(run), len(files)


def stage_normal_one(s, adr, carry=False):
    name = n_name(s); case = n_case(s); led = n_ledger(s); adc = ad_case(s)
    for p in (case, n_run(s), n_arch(s), led):
        if p.exists() or p.is_symlink(): fail(s + ": Normal path exists; no overwrite: " + str(p))
    if queued(name) or sacct_name(name): fail(s + ": Normal jobs queued or in Slurm history")
    if not (adc / "SourceMods").exists(): fail(s + ": AD case SourceMods missing or dangling (create_clone would fail)")
    exe_owner_sourcemods(adc)
    y = adr["start_year"] + 400; files = adr["files"]
    if set(files) != {c for _, c in POINTERS} or adr.get("final") != stamp(y) or adr.get("spinup_state") != 2:
        fail(s + ": AD400 audit result incomplete; stage only PASS sites")
    exe =Path(xq(adc, "EXEROOT")) / "cesm.exe"; exe_sha = digest(exe)
    src_sha = {c: digest(p) for c, p in files.items()}
    ad_lnd = (adc / "CaseDocs/lnd_in").read_text()
    pf = nml_get(ad_lnd, "fates_paramfile")
    if not pf or not Path(pf).is_file(): fail(s + ": AD fates_paramfile missing: " + str(pf))
    surf = nml_get(ad_lnd, "fsurdat")
    if not surf or not Path(surf).is_file(): fail(s + ": AD fsurdat missing: " + str(surf))
    save(led, {"site": s, "case": str(case), "phase": "STAGE_ATTEMPTED_UNCERTAIN", "at": utc()})
    cmd([CIMESCRIPTS / "create_clone", "--case", case, "--clone", adc, "--keepexe"], cwd=CIMESCRIPTS, timeout=420)
    if xq(case, "CASE") != name: fail(s + ": clone identity")
    sm = pin_sourcemods(case)
    if xq(case, "EXEROOT") != str(exe.parent) or digest(exe) != exe_sha: fail(s + ": executable differs")
    if Path(xq(case, "COMP_ROOT_DIR_LND")).resolve() != CTSM.resolve(): fail(s + ": land root is not the shared CTSM")
    date = f"{y:04d}-01-01"
    for k, v in {"RUN_TYPE": "hybrid", "RUN_STARTDATE": date, "RUN_REFCASE": ad_name(s), "RUN_REFDATE": date,
                 "RUN_REFTOD": "00000", "GET_REFCASE": "FALSE", "CONTINUE_RUN": "FALSE",
                 "CLM_FORCE_COLDSTART": "off", "CLM_ACCELERATED_SPINUP": "off",
                 "STOP_OPTION": "nyears", "STOP_N": "5", "REST_OPTION": "nyears", "REST_N": "5", "RESUBMIT": "0",
                 "DOUT_S": "TRUE", "RUNDIR": str(n_run(s)), "DOUT_S_ROOT": str(n_arch(s))}.items():
        xc(case, k, v)
    for k in SAME_XML:
        if xq(case, k) != xq(adc, k): fail(f"{s}: Normal {k} differs from AD case")
    n_run(s).mkdir(parents=True, exist_ok=False)
    for c, src in files.items():
        dst = n_run(s) / src.name; shutil.copy2(src, dst)
        if digest(dst) != src_sha[c]: fail(f"{s}: copied restart differs {c}")
    for ptr, c in POINTERS: (n_run(s) / ptr).write_text(files[c].name + "\n")
    u = case / "user_nl_clm"; t = nml_del(u.read_text(), "spinup_state")
    if nml_get(t, "reseed_dead_plants") is not None: fail(s + ": reseed_dead_plants in user_nl_clm")
    t = nml_set(t, "finidat", "'" + str(n_run(s) / files["clm2"].name) + "'")
    # The AD namelist came from the private FATES-AD overlay; the shared CTSM default may differ.
    t = nml_set(t, "fates_paramfile", "'" + pf + "'")
    u.write_text(t)
    if not (case / ".case.run").is_file(): cmd([case / "case.setup"], cwd=case, timeout=300)
    cmd([case / "preview_namelists"], cwd=case, timeout=600)
    carried = None
    if carry:
        src, src_sha, nfiles = ad_effective_streams(s)
        regenerated_sha = digest(case / "CaseDocs/datm.streams.xml")
        payload = src.read_bytes()
        for target in (case / "CaseDocs/datm.streams.xml", n_run(s) / "datm.streams.xml"):
            tmp = Path(str(target) + ".tmpN400"); tmp.write_bytes(payload); tmp.replace(target)
        carried = {"from": str(src), "sha256": src_sha, "data_files": nfiles, "regenerated_sha256_replaced": regenerated_sha}
        print(s, f"AD effective DATM streams carried ({nfiles} data files, sha {src_sha[:12]})", flush=True)
    validate_normal(s, files)
    save(led, {"site": s, "cohort": REG[s]["cohort"], "case": str(case), "phase": "PREPARED_NOT_SUBMITTED",
               "source_ad_case": ad_name(s), "source_ad_first_job": adr["first_job"], "source_ad_restart": stamp(y),
               "source_restart_sha256": src_sha, "ad_start_year": adr["start_year"], "normal_start_year": y,
               "normal5_target_year": y + SEG_YEARS, "normal400_target_year": y + 400, "executable_sha256": exe_sha,
               "fsurdat": surf, "fsurdat_sha256": digest(surf), "fates_paramfile": pf, "fates_paramfile_sha256": digest(pf),
               "sourcemods": sm, "datm_streams_carried_from_AD": carried, "generated_lnd_in_sha256": digest(case / "CaseDocs/lnd_in"),
               "datm_streams_sha256": digest(case / "CaseDocs/datm.streams.xml"), "created_utc": utc()})
    print(s, "NORMAL CASE STAGED", name, "start", date, "| NO SLURM", flush=True)


def validate_normal(s, files=None):
    case = n_case(s); adc = ad_case(s)
    if files is None:
        y = load(n_ledger(s))["normal_start_year"]
        files = {c: ad_arch(s) / "rest" / stamp(y) / f"{ad_name(s)}.{c}.r.{stamp(y)}.nc" for _, c in POINTERS}
    y = int(files["clm2"].name.split(".r.")[1][:4]); date = f"{y:04d}-01-01"
    for k, v in {"RUN_TYPE": "hybrid", "RUN_STARTDATE": date, "RUN_REFCASE": ad_name(s), "RUN_REFDATE": date,
                 "GET_REFCASE": "FALSE", "CONTINUE_RUN": "FALSE", "CLM_ACCELERATED_SPINUP": "off",
                 "CLM_FORCE_COLDSTART": "off", "RESUBMIT": "0", "STOP_N": "5", "REST_N": "5", "DOUT_S": "TRUE",
                 "RUNDIR": str(n_run(s)), "DOUT_S_ROOT": str(n_arch(s))}.items():
        if xq(case, k).lower() != v.lower(): fail(f"{s}: Normal XML {k}={xq(case, k)}")
    doc, run = case / "CaseDocs/lnd_in", n_run(s) / "lnd_in"
    if not doc.is_file() or not run.is_file() or digest(doc) != digest(run): fail(s + ": Normal lnd_in missing/differs")
    t = doc.read_text(); a = (adc / "CaseDocs/lnd_in").read_text()
    for k, v in FATES_FLAGS.items():
        if nml_get(t, k) != v: fail(f"{s}: Normal lnd_in {k}={nml_get(t, k)}")
    for k in SAME_LND:
        if nml_get(t, k) != nml_get(a, k): fail(f"{s}: Normal {k} differs from AD: {nml_get(t, k)} vs {nml_get(a, k)}")
    if hist_fields(t) != hist_fields(a): fail(s + ": Normal history fields differ from AD")
    if nml_get(t, "finidat") != str(n_run(s) / files["clm2"].name): fail(s + ": Normal finidat " + str(nml_get(t, "finidat")))
    if nml_get(t, "spinup_state") not in (None, "0"): fail(s + ": Normal spinup_state must be 0/absent")
    if nml_get(t, "reseed_dead_plants") is not None: fail(s + ": reseed_dead_plants present")
    sem = lambda e: (e.tag, tuple(sorted(e.attrib.items())), (e.text or "").strip(), tuple(sem(k) for k in e))
    if sem(ET.parse(case / "CaseDocs/datm.streams.xml").getroot()) != sem(ET.parse(adc / "CaseDocs/datm.streams.xml").getroot()):
        fail(s + ": Normal DATM streams differ from AD case (AD streams were set after preview? use --carry-ad-streams)")
    rs = n_run(s) / "datm.streams.xml"
    if rs.is_file() and digest(rs) != digest(case / "CaseDocs/datm.streams.xml"):
        fail(s + ": Normal RUNDIR datm.streams.xml differs from Normal CaseDocs")
    for ptr, c in POINTERS:
        src = files[c]; dst = n_run(s) / src.name
        if not dst.is_file() or digest(dst) != digest(src): fail(f"{s}: staged restart mismatch {c}")
        if (n_run(s) / ptr).read_text().strip() != src.name: fail(f"{s}: rpointer {ptr}")
    if not (case / "SourceMods").exists(): fail(s + ": Normal SourceMods dangling")
    print(s, "VALIDATE PASS: hybrid Normal from", stamp(y), "| spinup_state", nml_get(t, "spinup_state") or "absent",
          "| fsurdat/params/CO2/history/DATM = AD", flush=True)


def submit_one(s, stack):
    led = n_ledger(s); obj = load(led)
    if obj.get("phase") != "PREPARED_NOT_SUBMITTED": fail(s + ": Normal ledger phase " + str(obj.get("phase")))
    case = n_case(s)
    if (case / "CaseStatus").is_file() and re.search(r"case\.submit (starting|success)|case\.run starting",
                                                     (case / "CaseStatus").read_text(errors="replace")):
        fail(s + ": Normal CaseStatus shows a submission")
    if queued(n_name(s)) or sacct_name(n_name(s)): fail(s + ": Normal jobs queued or in Slurm history")
    if latest(n_arch(s))[1]: fail(s + ": Normal archive already has restarts")
    validate_normal(s)
    if digest(case / "CaseDocs/lnd_in") != obj["generated_lnd_in_sha256"]: fail(s + ": lnd_in changed after staging")
    if digest(case / "CaseDocs/datm.streams.xml") != obj["datm_streams_sha256"]: fail(s + ": DATM streams changed after staging")
    if digest(obj["fsurdat"]) != obj["fsurdat_sha256"] or digest(obj["fates_paramfile"]) != obj["fates_paramfile_sha256"]:
        fail(s + ": surface or FATES parameter file changed after staging")
    if xq(case, "RESUBMIT_SETS_CONTINUE_RUN").lower() != "true": fail(s + ": RESUBMIT_SETS_CONTINUE_RUN is not TRUE")
    for line in (case / ".case.run").read_text().splitlines():
        if line.lstrip().startswith("#SBATCH") and "--propagate" in line and not re.search(r"--propagate(?:=|\s+)(?:ALL|STACK)\b", line):
            fail(s + ": batch script overrides stack propagation")
    obj.update(phase="NORMAL400_DIRECT_ATTEMPTED_UNCERTAIN", attempt_utc=utc(), stack_limit_at_submit=stack,
               mode="DIRECT_80x5_NO_NORMAL5_SMOKE", intended_final_year=obj["normal400_target_year"]); save(led, obj)
    xc(case, "RESUBMIT", str(SEGMENTS - 1))
    if xq(case, "RESUBMIT") != str(SEGMENTS - 1) or xq(case, "CONTINUE_RUN").lower() != "false" or xq(case, "STOP_N") != "5":
        fail(s + ": direct settings not applied; DO NOT RETRY")
    out = cmd([case / "case.submit", "--skip-preview-namelist"], cwd=case, timeout=800)
    r, a = RUN_RE.findall(out), ARCH_RE.findall(out)
    if len(r) != 1 or len(a) != 1: fail(s + ": job IDs not parsed; DO NOT RETRY. " + out[-600:])
    persisted = submit_options_ok(case)
    obj.update(phase="NORMAL400_DIRECT_SUBMITTED", NORMAL400_first_run_job=r[0], NORMAL400_first_archive_job=a[0],
               skip_pnl_persisted=persisted, cime_submit_output_tail=out[-850:]); save(led, obj)
    print(s, "NORMAL400 DIRECT SUBMITTED", n_name(s), stamp(obj["normal_start_year"]), "->",
          stamp(obj["normal400_target_year"]), f"({SEGMENTS}x5, RESUBMIT={SEGMENTS - 1}) run=", r[0], "archive=", a[0],
          "skip_pnl=", persisted, flush=True)
    if not persisted: fail(s + ": submitted, but skip-preview persistence uncertain; inspect, never resubmit")


def first5_one(s):
    obj = load(n_ledger(s))
    if obj.get("phase") != "NORMAL400_DIRECT_SUBMITTED": fail(s + ": Normal ledger phase " + str(obj.get("phase")))
    name = n_name(s); first = int(obj["NORMAL400_first_run_job"])
    rows = [r for r in sacct_name(name) if r[0] >= first]
    bad = [r for r in rows if r[2] not in ("COMPLETED", "RUNNING", "PENDING") or (r[2] == "COMPLETED" and r[3] != "0:0")]
    if bad: fail(name + ": failed jobs: " + repr(bad[:4]))
    y = obj["normal5_target_year"]; files = triplet(name, n_arch(s), y); st = restart_state(files["clm2"])
    if st != 0: fail(f"{s}: first-segment spinup_state={st}, expected 0")
    l, n = latest(n_arch(s))
    return {"case": name, "final": stamp(y), "spinup_state": st, "latest": l, "rest_dirs": n,
            "runs": sum(r[1].startswith("run.") and r[2] == "COMPLETED" for r in rows)}


def normal400_one(s):
    obj = load(n_ledger(s))
    if obj.get("phase") != "NORMAL400_DIRECT_SUBMITTED": fail(s + ": Normal ledger phase " + str(obj.get("phase")))
    return chain(n_name(s), n_case(s), n_arch(s), obj["NORMAL400_first_run_job"], obj["normal400_target_year"], 0)


def interrupted_one(s):
    led = n_ledger(s); obj = load(led); name = n_name(s)
    if obj.get("phase") != "STAGE_ATTEMPTED_UNCERTAIN":
        fail(s + ": Normal ledger phase " + str(obj.get("phase")) + " (only STAGE_ATTEMPTED_UNCERTAIN is recoverable)")
    if queued(name): fail(s + ": Normal jobs queued")
    if sacct_name(name): fail(s + ": Slurm history exists for the Normal case; manual review")
    if n_arch(s).exists(): fail(s + ": Normal archive exists " + str(n_arch(s)))
    case = n_case(s)
    if (case / "CaseStatus").is_file() and re.search(r"case\.submit|case\.run starting", (case / "CaseStatus").read_text(errors="replace")):
        fail(s + ": partial case CaseStatus shows a submission")
    return {"case": name, "case_exists": case.is_dir(), "run_exists": n_run(s).is_dir(), "attempt_at": obj.get("at")}


def quarantine_one(s):
    interrupted_one(s)
    q = D / "quarantine_interrupted_stage" / f"{s}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    q.mkdir(parents=True, exist_ok=False); moved = {}
    for tag, p in (("case", n_case(s)), ("run_parent", n_run(s).parent), ("ledger", n_ledger(s))):
        if p.exists() or p.is_symlink():
            dst = q / tag; shutil.move(str(p), str(dst)); moved[tag] = {"from": str(p), "to": str(dst)}
    (q / "QUARANTINE_RECEIPT.json").write_text(json.dumps({"site": s, "moved": moved, "utc": utc(),
                                                           "reason": "interrupted stage-normal, never submitted"}, indent=2) + "\n")
    print(f"{s}: partial Normal stage moved to {q}; run stage-normal again for this site", flush=True)


def status(sites):
    try: rows = queue_rows()
    except Exception: rows = None
    for s in sites:
        a = load(REG[s]["ledger"]) if REG[s]["ledger"] else {"phase": "no-ledger"}; n = load(n_ledger(s))
        q = "scheduler unavailable" if rows is None else (
            "; ".join("|".join(r) for r in queued(ad_name(s), rows) + queued(n_name(s), rows)) or "-")
        print(f"{s:7} AD={a.get('phase', '-')}/{a.get(REG[s]['job'] or '', '-')} AD_latest={latest(ad_arch(s))[0]} "
              f"NORMAL={n.get('phase', '-')} N_latest={latest(n_arch(s))[0]} QUEUE={q}")


def table(title, sites, fn):
    ok, held = {}, {}
    print(title, flush=True)
    for s in sites:
        try:
            r = fn(s); ok[s] = r
            print(f"  PASS {s:7} " + " ".join(f"{k}={r[k]}" for k in ("case", "runs", "archives", "final", "spinup_state",
                                                                        "latest", "rest_dirs", "normal") if k in r), flush=True)
        except Exception as e:
            held[s] = str(e); print(f"  HOLD {s:7} {str(e)[-400:]}", flush=True)
    print(f"SUMMARY pass={len(ok)} hold={len(held)}", ("PASS: " + " ".join(ok)) if ok else "", flush=True)
    return ok, held


def batch(label, sites, fn):
    bad = []
    for s in sites:
        try: fn(s)
        except Exception as e:
            print(s, label, "HOLD — DO NOT RETRY BLINDLY:", str(e)[-1200:], flush=True); bad.append(s)
    print(label, "SUMMARY ok=", len(sites) - len(bad), "hold=", bad, flush=True)
    if bad: raise SystemExit(2)


def self_test():
    assert len(REG) == 27 and len(set(n_name(s) for s in REG)) == 27
    assert n_name("US-Syv") == "US-Syv_AMF_B04_FIXNC_NORMAL400_BASETA_V1"
    assert n_name("DE-Tha") == "DE-Tha_OBSPFT_NC_V1_NORMAL400"
    assert n_name("US-GLE") == "US-GLE_AMF_B02_FIXNC_NORMAL400_DIRECT"
    assert n_name("DK-Sor") == "DK-Sor_B02_FIXNC_ICOS_DBF100_NORMAL400"
    assert n_name("IT-Noe") == "IT-Noe_B02_FIXNC_GPPNPP_HISTFIX_NORMAL400"
    assert all(n_name(s) != ad_name(s) for s in REG)
    t = "a = 1\n spinup_state = 2\nb = 2\n"; assert nml_get(nml_del(t, "spinup_state"), "spinup_state") is None
    assert hist_fields("hist_fincl1 = 'A','B',\n 'C'\nhist_mfilt = 1\n") == ["A", "B", "C"]
    assert RUN_RE.findall("Submitted job case.run with id 4741595") == ["4741595"]
    assert len({ACK_STAGE, ACK_SUB, ACK_Q}) == 3
    try: pick(["CA-TP4"]); raise AssertionError("Batch01 site accepted")
    except RuntimeError: pass
    print("CROSS-COHORT NORMAL400 SELF-TEST PASS (no HPC access, no writes)")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("action", choices=("self-test", "audit-ad400", "stage-normal", "submit", "audit-first5",
                                       "audit-normal400", "inspect-interrupted", "quarantine-interrupted", "status"))
    ap.add_argument("--sites", nargs="+"); ap.add_argument("--confirm", default="")
    ap.add_argument("--carry-ad-streams", action="store_true")
    a = ap.parse_args()
    if a.action == "self-test": return self_test()
    if a.action == "status": return status(pick(a.sites))
    ro = {"audit-ad400": ("AD400 COMPLETION AUDIT (read only)", ad400_one),
          "audit-first5": ("DIRECT NORMAL400 FIRST-SEGMENT AUDIT (read only)", first5_one),
          "audit-normal400": ("NORMAL400 COMPLETION AUDIT (read only)", normal400_one),
          "inspect-interrupted": ("INTERRUPTED NORMAL STAGE (read only)", interrupted_one)}
    if a.action in ro:
        _, h = table(ro[a.action][0], pick(a.sites), ro[a.action][1]); raise SystemExit(2 if h else 0)
    if not a.sites: fail(a.action + " requires explicit --sites")
    sites = pick(a.sites)
    if a.action == "quarantine-interrupted":
        if a.confirm != ACK_Q: fail("requires --confirm " + ACK_Q)
        return batch("QUARANTINE-INTERRUPTED", sites, quarantine_one)
    if a.action == "stage-normal":
        if a.confirm != ACK_STAGE: fail("requires --confirm " + ACK_STAGE)
        ok, h = table("PREFLIGHT AD400", sites, ad400_one)
        if h: fail("AD400 not verified for " + ",".join(h) + "; use --sites with PASS sites only")
        return batch("STAGE-NORMAL", sites, lambda s: stage_normal_one(s, ok[s], a.carry_ad_streams))
    if a.action == "submit":
        if a.confirm != ACK_SUB: fail("requires --confirm " + ACK_SUB)
        stack = stack_guard()
        return batch("SUBMIT-NORMAL400-DIRECT", sites, lambda s: submit_one(s, stack))


if __name__ == "__main__":
    main()
