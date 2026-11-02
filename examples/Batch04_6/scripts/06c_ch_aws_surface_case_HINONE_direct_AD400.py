#!/usr/bin/env python3
"""Batch04 CH-Aws: GitHub-PFT point surface, isolated FIXNC direct AD400 case with F1A forcing and HINONE, one-time submit.

Same method as the running Batch04 chains (DE-RuR_prepare_ad400.py, 05c, 05e): clone the original case with --keepexe,
private FATES AD namelist overlay preview, FIXNC flags with spinup_state=2, RESUBMIT 0 at prepare and 79 only at the
one-time submit, crash-safe submission sentinel.

CH-Aws specifics
  template   CH-Aws_FATES_SPINUP500_11P: original-forcing case, 19 annual DATM files 2006-2024, CO2 381.15 (NOAA 2006)
  surface    template point surface, Stage02X method. PCT_NATVEG 100, PCT_CROP 0, lake/wetland/glacier/urban 0,
             PCT_NAT_PFT host 13 C3 grass 100 (operator proxy). Soil and point unchanged; no site SOC measurement was
             found, so ORGANIC stays as inherited, as at DE-Gri/DE-RuR/ES-Agu.
  forcing    F1A plan from 06b: 2006-2024 base files, with the edited years replaced by CH-Aws_DATM_<year>_F1A.nc
  HINONE     calc_human_stress_indices = 'NONE' (maintenance/RULES_FOR_NEW_CASES.md, docs section 17). 7 of the 8 old
             CH-Aws cases stopped with "RH is negative" in HumanIndexMod, a diagnostic-only 2 m humidity. No effect
             on fluxes.
  phenology  maintenance rule: the class is computed with script 22's own functions (decid_share, M18.pft2_share,
             branch full-sequence-gpp-nee-ec at the pinned commit) on the NEW surface and the case's parameter file.
             Only UNCHANGED (no cold-deciduous PFT, no PFT 2) may use the shared executable; any other class HOLDs.
  FATES      the template's parameter file, required to be the shared default (host 13 -> cool C3 grass)

Actions
  self-test                                                      no HPC, temp files only
  check                                                          READ ONLY
  build-surface --confirm BUILD_CH_AWS_B04_GITHUBPFT_SURFACE     new folder only
  prepare       --confirm PREPARE_CH_AWS_B04_F1A_HINONE_AD400_NO_SLURM
  audit                                                          READ ONLY
  submit        --confirm SUBMIT_CH_AWS_F1A_HINONE_DIRECT_AD400_80X5_ONCE
  --rollout-dir  folder with scripts 09-22 of branch full-sequence-gpp-nee-ec at the pinned commit
Never repeat prepare or submit after a ledger or submission receipt exists.
"""
import argparse, configparser, hashlib, importlib.util, json, os, re, resource, shutil, socket, subprocess, sys, tempfile
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

B = Path("/iridisfs/scratch/ly3n24/CLM_FATES")
CTSM = B / "CTSM"
OUTPUT = Path("/scratch/ly3n24/CTSM_FATES_OUTPUTS")
TEMPLATE = B / "cases/CH-Aws_FATES_SPINUP500_11P"
NAME = "CH-Aws_ICOS_B04_FIXNC_AD400_DIRECT_HINONE"
CASE = B / "cases" / NAME
RUN = OUTPUT / NAME / "run"
ARCH = OUTPUT / "archive" / NAME
FIRST, LAST = 2006, 2024
BASE_DIR = B / "sites/MY_EC_SITE/CH-Aws/forcing/datm_11_provisional_dynamic_zbot_v1"
SOURCE_SURF = B / "sites/MY_EC_SITE/CH-Aws/subset_data/surfdata_CH-Aws_hist_2000_16pfts_c261014.nc"
SOURCE_SURF_SHA12 = "7893004e1922"                     # Stage06A
B04 = B / "experiments/NonCompetitionObserved22/Batch04_6"
SURF_DIR = B04 / "CH-Aws_B04_GITHUBPFT_surface_v1"
SURF = SURF_DIR / "CH-Aws_B04_GITHUBPFT_POINT_CANDIDATE.nc"
SURF_MANIFEST = SURF_DIR / "manifest.json"
TARGET = {13: 100.0}
OTHERS = ("PCT_LAKE", "PCT_WETLAND", "PCT_GLACIER", "PCT_URBAN")
EDITABLE = {"PCT_NATVEG", "PCT_CROP", "PCT_NAT_PFT", *OTHERS}
F1A_PLAN = B04 / "CH-Aws_F1A_forcing_v1/annual_input_plan.json"
SHARED_PARAM_SHA = "0819f8fddcb3566f6209f72bb1159a3161d03c8225a1464727b1d2b21aec6c04"
ROLLOUT_COMMIT = "c092804eafa211319aaac7a70b009793071010de"
S22_BLOB = "5c2faf165f1fd53c7af4ebd96326c3e90175599f"
DEFAULT_ROLLOUT = Path.home() / "NCE_full_sequence_c092804/examples/Cross_cohort_NORMAL400/scripts"
CO2_CSV = B / "experiments/NonCompetitionObserved22/AmeriFlux_Batch02_10/Stage06_direct_AD400/co2_annmean_gl.csv"
REPORTS = B / "experiments/Batch04_CH_Aws_AD400_DIRECT_preparation"
LEDGER = REPORTS / "stage06c_prepare_state.json"
SUBMISSION = REPORTS / "stage06c_submission_attempt_PRIVATE.json"
OVERLAYS = (B / "experiments/NonCompetitionObserved22/AmeriFlux_Batch02_10/_private_ctsm_FATES_AD400_namelist_overlay",
            B / "experiments/NonCompetitionObserved22/Batch02_10/_private_ctsm_FATES_AD5_namelist_overlay_v1")
FLAGS = {"use_fates": ".true.", "use_fates_sp": ".false.", "use_fates_fixed_biogeog": ".true.",
         "use_fates_nocomp": ".true.", "use_cn": ".false.", "spinup_state": "2"}
HINONE = ("calc_human_stress_indices", "'NONE'")
HISTORY = ["TOTSOMC", "TOTSOMN", "TLAI", "FATES_GPP", "FATES_NPP", "TWS", "H2OSNO"]
REQUIRED_STREAM = ("year_first", "year_last", "year_align", "offset", "taxmode", "tintalgo", "mapalgo", "meshfile",
                   "datafiles", "datavars")
SETTINGS = {"RUN_TYPE": "startup", "RUN_STARTDATE": f"{FIRST}-01-01", "CONTINUE_RUN": "FALSE",
            "CLM_ACCELERATED_SPINUP": "on", "CLM_FORCE_COLDSTART": "on", "STOP_OPTION": "nyears", "STOP_N": "5",
            "REST_OPTION": "nyears", "REST_N": "5", "RESUBMIT": "0", "RESUBMIT_SETS_CONTINUE_RUN": "TRUE",
            "DOUT_S": "TRUE", "DATM_YR_START": str(FIRST), "DATM_YR_END": str(LAST), "DATM_YR_ALIGN": str(FIRST),
            "RUNDIR": str(RUN), "DOUT_S_ROOT": str(ARCH)}
ACK_SURF, ACK_PREP = "BUILD_CH_AWS_B04_GITHUBPFT_SURFACE", "PREPARE_CH_AWS_B04_F1A_HINONE_AD400_NO_SLURM"
ACK_SUB = "SUBMIT_CH_AWS_F1A_HINONE_DIRECT_AD400_80X5_ONCE"
ROLLOUT = DEFAULT_ROLLOUT


def need(x, msg):
    if not x: raise RuntimeError(msg)


def utc(): return datetime.now(timezone.utc).isoformat()


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for b in iter(lambda: f.read(1048576), b""): h.update(b)
    return h.hexdigest()


def git_blob(path):
    data = Path(path).read_bytes()
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


def cmd(args, cwd, timeout=90, allowed=(0,)):
    p = subprocess.run([str(x) for x in args], cwd=cwd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                       timeout=timeout, check=False)
    need(p.returncode in allowed, "COMMAND " + str([str(x) for x in args]) + " RC=" + str(p.returncode) + " " +
         (p.stdout + p.stderr)[-1600:])
    return (p.stdout + p.stderr).strip()


def xq(case, key): return cmd([case / "xmlquery", key, "--value"], case)
def xc(case, key, value): return cmd([case / "xmlchange", f"{key}={value}"], case)


def nmlget(t, key):
    z = re.findall(r"(?im)^\s*" + re.escape(key) + r"\s*=\s*([^\r\n!]*)", t)
    need(len(z) <= 1, "Duplicate namelist key " + key)
    return z[0].strip().rstrip(",").strip("'\" ").strip() if z else None


def nmlset(t, key, value):
    m = list(re.finditer(r"(?im)^\s*" + re.escape(key) + r"\s*=\s*[^\r\n!]*", t))
    need(len(m) <= 1, "Duplicate namelist key " + key)
    line = f"{key} = {value}"
    return (t[:m[0].start()] + line + t[m[0].end():]) if m else (t.rstrip() + "\n" + line + "\n")


def hist_fields(t):
    m = re.search(r"(?ims)^\s*hist_fincl1\s*=\s*(.*?)(?=^[ \t]*[A-Za-z_]\w*[ \t]*=|^[ \t]*/[ \t]*$|\Z)", t)
    return re.findall(r"['\"]([^'\"]+)['\"]", m.group(1)) if m else None


def stream_replace(t, paths):
    rex = re.compile(r"(?m)^[ \t]*([A-Za-z][\w.\-]*):([A-Za-z_]\w*)[ \t]*=")
    matches = list(rex.finditer(t)); found = {}
    for i, m in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(t)
        found.setdefault(m.group(1) + ":" + m.group(2), []).append((m.start(), end))
    pre = "CLM_USRDAT.UNSET:"
    rep = {"year_first": str(FIRST), "year_last": str(LAST), "year_align": str(FIRST), "offset": "0", "taxmode": "cycle",
           "tintalgo": "linear", "mapalgo": "none", "meshfile": "none", "datafiles": ",".join(str(x) for x in paths)}
    for key in REQUIRED_STREAM:
        count = len(found.get(pre + key, []))
        need(count == 1 or (key == "offset" and count == 0), "Original DATM stream field ambiguous or missing " + key + " " + str(count))
    subs = [(found[pre + k][0][0], found[pre + k][0][1], pre + k + " = " + v + "\n") for k, v in rep.items() if found.get(pre + k)]
    for st, en, new in sorted(subs, reverse=True): t = t[:st] + new + t[en:]
    if not found.get(pre + "offset"): t = t.rstrip() + "\n" + pre + "offset = 0\n"
    return t


def parse_stream(case):
    doc = case / "CaseDocs/datm.streams.xml"
    need(doc.is_file(), "Generated CIME DATM stream XML missing " + str(doc))
    blocks = [x for x in ET.parse(doc).getroot().iter("stream_info") if x.get("name") == "CLM_USRDAT.UNSET"]
    need(len(blocks) == 1, "Generated USRDAT stream count incorrect")
    e = blocks[0]
    files = [(x.text or "").strip() for x in e.find("datafiles")]
    settings = {k: (e.findtext(k) or "").strip() for k in ("year_first", "year_last", "year_align", "taxmode", "offset")}
    return files, settings


def co2_first_year():
    need(CO2_CSV.is_file(), "NOAA CO2 table missing " + str(CO2_CSV))
    vals = {}
    for ln in CO2_CSV.read_text().splitlines():
        p = [x.strip() for x in ln.split(",")]
        if len(p) >= 2 and p[0].isdigit(): vals[int(p[0])] = float(p[1])
    need(FIRST in vals, f"NOAA CO2 {FIRST} missing from table")
    return vals[FIRST]


# ------------------------------------------------------------------ phenology class (script 22 functions)
M22 = None


def rollout22():
    global M22
    if M22 is None:
        need(ROLLOUT.is_dir(), f"rollout scripts folder missing: {ROLLOUT} (worktree of full-sequence-gpp-nee-ec at {ROLLOUT_COMMIT[:7]})")
        head = cmd(["git", "-C", ROLLOUT, "rev-parse", "HEAD"], None, 30)
        need(head == ROLLOUT_COMMIT, f"rollout folder is at {head}, expected {ROLLOUT_COMMIT}")
        s22 = ROLLOUT / "22_phenology_patch_rollout.py"
        need(s22.is_file() and git_blob(s22) == S22_BLOB, "script 22 missing or blob differs")
        spec = importlib.util.spec_from_file_location("rollout22", s22)
        M22 = importlib.util.module_from_spec(spec); spec.loader.exec_module(M22)
        M22.load()
    return M22


def phenology_class(pct, param_path):
    m22 = rollout22()
    params = json.loads(Path(param_path).read_text())
    share, present = m22.decid_share(pct, params)
    p2, how = m22.M18.pft2_share(pct, params)
    lim = m22.M18.MIN_PCT
    cls = ("UNCHANGED" if share <= lim and p2 <= lim else
           "NEEDS_PATCH_AND_F" if share > lim and p2 > lim else "NEEDS_PHENOLOGY_PATCH" if share > lim else "NEEDS_NEEDLELEAF_F")
    return {"class": cls, "cold_deciduous_pct_of_veg": round(share, 3), "cold_deciduous_pfts": present,
            "pft2_pct_of_veg": round(p2, 3), "pft2_mapping": how, "min_pct": lim, "script22_blob": S22_BLOB, "rollout_commit": ROLLOUT_COMMIT}


# ------------------------------------------------------------------ surface (Stage02X method)
def read_surface(path):
    from netCDF4 import Dataset
    import numpy as np
    with Dataset(str(path)) as ds:
        g = lambda k: np.ma.filled(np.ma.asarray(ds.variables[k][:]).astype(float), np.nan)
        land = {k: float(np.nansum(g(k))) for k in ("PCT_NATVEG", "PCT_CROP", *OTHERS) if k in ds.variables}
        pft = g("PCT_NAT_PFT").reshape(ds.variables["PCT_NAT_PFT"].shape[0], -1)[:, 0]
        return {"land": land, "pft": pft.tolist(), "lat": float(g("LATIXY").ravel()[0]), "lon": float(g("LONGXY").ravel()[0]),
                "organic": g("ORGANIC").ravel().tolist(), "sand": g("PCT_SAND").ravel().tolist(), "clay": g("PCT_CLAY").ravel().tolist()}


def make_surface(source, partial, target):
    from netCDF4 import Dataset
    import numpy as np
    need(not partial.exists(), "partial surface exists")
    shutil.copyfile(source, partial)
    with Dataset(str(partial), "r+") as ds:
        ds.variables["PCT_NATVEG"][:] = 100.0
        ds.variables["PCT_CROP"][:] = 0.0
        for k in OTHERS:
            if k in ds.variables: ds.variables[k][:] = 0.0
        v = ds.variables["PCT_NAT_PFT"]; need(v.dimensions[0] == "natpft" and v.shape[0] == 15, "PCT_NAT_PFT is not natpft x 15")
        new = np.zeros(v.shape, dtype=v.dtype)
        for h, f in target.items(): new[h, ...] = f
        v[:] = new
        ds.setncattr("b04_ch_aws_pft_edit", f"Stage02X method: NATVEG 100, other landunits 0, PCT_NAT_PFT host "
                                            f"{json.dumps({str(k): v for k, v in target.items()})}; source sha {sha(source)}; {utc()}")
    with Dataset(str(source)) as a, Dataset(str(partial)) as b:
        need(set(a.variables) == set(b.variables), "variable set changed")
        for k in a.variables:
            if k in EDITABLE: continue
            x, y = np.ma.asarray(a.variables[k][:]), np.ma.asarray(b.variables[k][:])
            need(x.shape == y.shape and np.ma.allequal(x, y), "unexpected change in " + k)
    s = read_surface(partial)
    need(abs(s["land"]["PCT_NATVEG"] - 100) < 1e-9 and all(abs(s["land"].get(k, 0)) < 1e-9 for k in ("PCT_CROP", *OTHERS)), f"landunits {s['land']}")
    need(all(abs(s["pft"][h] - target.get(h, 0.0)) < 1e-9 for h in range(15)), "PCT_NAT_PFT not the target")
    return s


def surface_state():
    if not SURF_DIR.exists(): return None, None
    need(SURF.is_file() and SURF_MANIFEST.is_file() and not SURF_DIR.is_symlink(), "CH-Aws surface folder incomplete: inspect " + str(SURF_DIR))
    r = json.loads(SURF_MANIFEST.read_text())
    need(r.get("surface_sha256") == sha(SURF) and r.get("source_sha256", "").startswith(SOURCE_SURF_SHA12), "CH-Aws surface manifest sha mismatch")
    s = read_surface(SURF)
    need(all(abs(s["pft"][h] - TARGET.get(h, 0.0)) < 1e-9 for h in range(15)), "built surface PFT is not the target")
    return SURF, r["surface_sha256"]


def build_surface(confirm):
    need(confirm == ACK_SURF, "requires --confirm " + ACK_SURF)
    p, h = surface_state()
    if p: print("CH-Aws SURFACE EXISTS AND VERIFIED", p, h); return
    need(SOURCE_SURF.is_file() and sha(SOURCE_SURF).startswith(SOURCE_SURF_SHA12), "template surface missing or sha differs")
    tmp = SURF_DIR.with_name(SURF_DIR.name + ".partial"); need(not tmp.exists(), "leftover " + str(tmp) + "; inspect")
    tmp.mkdir(parents=True)
    old = read_surface(SOURCE_SURF)
    s = make_surface(SOURCE_SURF, tmp / SURF.name, TARGET)
    (tmp / SURF_MANIFEST.name).write_text(json.dumps({"site": "CH-Aws", "status": "EXPLORATORY_FIXNC_SURFACE_NOT_SCIENCE_RELEASE",
        "method": "Stage02X (02x_four_site_approved_GitHub_PFT_surface_candidates.py)", "source": str(SOURCE_SURF),
        "source_sha256": sha(SOURCE_SURF), "surface": str(SURF), "surface_sha256": sha(tmp / SURF.name),
        "host_PCT_NAT_PFT": {str(k): v for k, v in TARGET.items()}, "changed_variables": sorted(EDITABLE),
        "original_landunits": old["land"], "original_PCT_NAT_PFT": old["pft"], "point": [s["lat"], s["lon"]],
        "soil_inherited_from_grid": True, "ORGANIC_note": "all 0 as inherited; no site SOC measurement found (2 Nov 2026)",
        "basis": "ICOS_Unassigned_6 six-site CSV, CH-Aws 13:100 ACCEPTED_PROXY_ONLY", "created_utc": utc()}, indent=2) + "\n")
    need(sha(SOURCE_SURF).startswith(SOURCE_SURF_SHA12), "template surface changed during build")
    tmp.rename(SURF_DIR)
    print("CH-Aws SURFACE BUILT", SURF, sha(SURF), "| NATVEG 100, PCT_NAT_PFT", TARGET, "| soil and point unchanged")


# ------------------------------------------------------------------ forcing plan (06b)
def f1a_files(tfiles, need_plan=True):
    if not F1A_PLAN.is_file():
        need(not need_plan, "F1A forcing not built: run 06b build first")
        return None, None
    plan = json.loads(F1A_PLAN.read_text())
    yrs = plan["years"]
    need(plan.get("forcing") == "F1A" and [r["year"] for r in yrs] == list(range(FIRST, LAST + 1)), "F1A plan years")
    for r, t in zip(yrs, tfiles):
        need(Path(r["path"]).is_file() and sha(r["path"]) == r["sha256"], f"F1A plan file missing or sha differs {r['path']}")
        if r["kind"] == "historical_baseline": need(r["path"] == t, f"plan baseline {r['year']} is not the template file")
        else: need(r["kind"] == "F1A_edited" and r["base"] == t and sha(t) == r["base_sha256"], f"plan edit {r['year']} base mismatch")
    return [r["path"] for r in yrs], plan


def overlay():
    x = [p for p in OVERLAYS if all((p / f).is_file() for f in ("bld/CLMBuildNamelist.pm", "bld/build-namelist"))]
    need(x, "NO_VALID_PRIVATE_FATES_AD_NAMELIST_OVERLAY; do NOT clone"); return x[0]


def template_param():
    p = nmlget((TEMPLATE / "CaseDocs/lnd_in").read_text(), "fates_paramfile")
    need(p is not None, "template effective FATES parameter file missing")
    f = Path(p).resolve(); need(f.is_file() and f.suffix == ".json", "missing/unsupported FATES parameter " + str(f))
    return f


def preflight(show=True, need_inputs=True):
    need(TEMPLATE.is_dir() and not TEMPLATE.is_symlink(), "template case missing " + str(TEMPLATE))
    for key, want in (("BUILD_COMPLETE", "TRUE"), ("DATM_MODE", "1PT"), ("CALENDAR", "NO_LEAP"), ("ATM_NCPL", "48"),
                      ("CLM_CO2_TYPE", "constant")):
        need(xq(TEMPLATE, key).upper() == want.upper(), f"template {key} = {xq(TEMPLATE, key)}, expected {want}")
    need("--bgc fates" in xq(TEMPLATE, "CLM_BLDNML_OPTS"), "template is not a FATES build")
    exe = Path(xq(TEMPLATE, "EXEROOT")) / "cesm.exe"; need(exe.is_file(), "shared executable missing")
    need((CTSM / "cime/scripts/create_clone").is_file(), "create_clone missing")
    lnd = (TEMPLATE / "CaseDocs/lnd_in").read_text()
    need(nmlget(lnd, "fsurdat") == str(SOURCE_SURF) and sha(SOURCE_SURF).startswith(SOURCE_SURF_SHA12), "template fsurdat is not the Stage06A surface")
    tfiles, tst = parse_stream(TEMPLATE)
    yrs = [int(re.search(r"_DATM_(\d{4})", Path(f).name).group(1)) for f in tfiles]
    need(yrs == list(range(FIRST, LAST + 1)) and all(Path(f).parent == BASE_DIR for f in tfiles) and tst.get("taxmode") == "cycle",
         "template stream is not the 2006-2024 base forcing")
    files, plan = f1a_files(tfiles, need_inputs)
    param = template_param(); psha = sha(param)
    need(psha == SHARED_PARAM_SHA, f"template parameter file is not the shared default ({psha[:12]})")
    surf, surf_sha = surface_state()
    if need_inputs: need(surf is not None, "CH-Aws surface not built: run build-surface first")
    pct = read_surface(surf)["pft"] if surf else [TARGET.get(h, 0.0) for h in range(15)]
    phen = phenology_class(pct, param)
    phen_old = phenology_class(read_surface(SOURCE_SURF)["pft"], param)
    need(phen["class"] == "UNCHANGED", f"phenology class {phen['class']}: needs the script-22 patched build / F parameters, not this script")
    s = read_surface(surf or SOURCE_SURF)
    pts = (float(xq(TEMPLATE, "PTS_LAT")), float(xq(TEMPLATE, "PTS_LON")))
    need(abs(s["lat"] - pts[0]) < 0.01 and abs((s["lon"] - pts[1] + 180) % 360 - 180) < 0.01, f"surface point {s['lat']},{s['lon']} != PTS {pts}")
    co2, co2_t = co2_first_year(), float(xq(TEMPLATE, "CCSM_CO2_PPMV"))
    ov = overlay()
    land = (TEMPLATE / "user_nl_clm").read_text()
    land = nmlset(land, "fsurdat", f"'{SURF}'")
    land = nmlset(land, "fates_paramfile", f"'{param}'")
    for k, v in FLAGS.items(): land = nmlset(land, k, v)
    land = nmlset(land, "finidat", "''")
    land = nmlset(land, "hist_fincl1", ", ".join(f"'{x}'" for x in HISTORY))
    land = nmlset(land, *HINONE)
    need(hist_fields(land) == HISTORY, "hist_fincl1 not cleanly replaced in user_nl_clm (continuation lines?)")
    stream = stream_replace((TEMPLATE / "user_nl_datm_streams").read_text(), files or tfiles)
    for p in (CASE, RUN, ARCH):
        if p.exists() or p.is_symlink(): need(LEDGER.is_file(), "new case/run/archive exists without ledger: " + str(p))
    others = [p.name for p in (B / "cases").glob("CH-Aws_ICOS_B04*") if p.name != NAME]
    need(not others, f"another CH-Aws Batch04 case exists: {others}")
    ctx = {"files": files, "surface": str(SURF), "surface_sha256": surf_sha, "param": str(param), "param_sha256": psha,
           "exe": str(exe), "overlay": str(ov), "co2": co2, "co2_template": co2_t, "land": land, "stream": stream, "phenology": phen,
           "plan_sha256": sha(F1A_PLAN) if plan else None}
    if show:
        print("STAGE06C PREFLIGHT PASS | CH-Aws F1A + HINONE | SCIENCE HOLD (grass proxy, inherited soil, option-A humidity)")
        print(f"  template {TEMPLATE.name} | exe {exe} | overlay {ov}")
        ed = [r["year"] for r in plan["years"] if r["kind"] == "F1A_edited"] if plan else None
        print(f"  DATM {FIRST}-{LAST}: {'F1A plan, edited years ' + str(ed) if plan else 'F1A NOT BUILT (06b build)'}")
        print(f"  surface {'BUILT ' + str(SURF) + ' sha ' + surf_sha[:12] if surf else 'NOT BUILT (build-surface writes ' + str(SURF) + ')'}")
        print(f"  host PFT now {[round(x, 3) for x in s['pft']]} | landunits {s['land']} | point {s['lat']:.4f},{s['lon']:.4f} PTS {pts}")
        print(f"  soil inherited: sand {s['sand'][:1]} clay {s['clay'][:1]} ORGANIC {s['organic'][:1]} (all 10 levels equal)")
        print(f"  PHENOLOGY (script 22 functions): new surface {phen['class']} cold-decid {phen['cold_deciduous_pct_of_veg']} % "
              f"PFT2 {phen['pft2_pct_of_veg']} % | old surface would be {phen_old['class']} (cold-decid {phen_old['cold_deciduous_pct_of_veg']} % "
              f"{phen_old['cold_deciduous_pfts']}, PFT2 {phen_old['pft2_pct_of_veg']} %)")
        print(f"  FATES param {param} (shared default) | CO2 NOAA {FIRST} {co2} | template {co2_t} | {'same' if abs(co2 - co2_t) < 0.005 else 'prepare sets NOAA'}")
        print(f"  HINONE {HINONE[0]} = {HINONE[1]} | case {NAME} {FIRST}->{FIRST + 400} | ledger {'EXISTS' if LEDGER.is_file() else 'none'}")
    return ctx


def verify(c):
    for k, v in SETTINGS.items():
        got = xq(CASE, k); need(got.lower() == v.lower(), "NEW CASE XML mismatch " + k + ": " + got)
    need(xq(CASE, "CASE") == NAME, "case identity")
    need(abs(float(xq(CASE, "CCSM_CO2_PPMV")) - c["co2"]) < 0.005 and xq(CASE, "CLM_CO2_TYPE") == "constant", "CO2 is not the NOAA first-year value")
    need(Path(xq(CASE, "EXEROOT")).resolve() == Path(c["exe"]).parent.resolve(), "EXEROOT changed")
    doc = CASE / "CaseDocs/lnd_in"; need(doc.is_file(), "CaseDocs/lnd_in missing")
    text = doc.read_text()
    for k, v in {**FLAGS, "fsurdat": c["surface"], "fates_paramfile": c["param"], "finidat": ""}.items():
        need(nmlget(text, k) == v, "Effective lnd_in mismatch " + k + "=" + str(nmlget(text, k)))
    need((nmlget(text, HINONE[0]) or "").upper() == "NONE", f"effective {HINONE[0]} is {nmlget(text, HINONE[0])}")
    need(hist_fields(text) == HISTORY, "Wrong history fields")
    need((RUN / "lnd_in").is_file() and sha(RUN / "lnd_in") == sha(doc), "RUNDIR lnd_in differs from CaseDocs")
    files, st = parse_stream(CASE)
    need(files == c["files"], "CRITICAL: effective DATM stream is not the F1A plan")
    for k, v in {"year_first": str(FIRST), "year_last": str(LAST), "year_align": str(FIRST), "taxmode": "cycle", "offset": "0"}.items():
        need(st[k] == v, "DATM cycle mismatch " + k)
    need((RUN / "datm.streams.xml").is_file() and sha(RUN / "datm.streams.xml") == sha(CASE / "CaseDocs/datm.streams.xml"), "RUNDIR stream differs")
    need(sha(c["surface"]) == c["surface_sha256"] and sha(c["param"]) == c["param_sha256"], "surface/param drift")
    need(not list(RUN.glob("rpointer*")) and not list(RUN.glob("*.r.*.nc")), "restart files already in RUNDIR")
    return {"case": str(CASE), "lnd_in_sha256": sha(doc), "effective_stream_sha256": sha(CASE / "CaseDocs/datm.streams.xml"),
            "verified_annual_file_count": len(files), "future_resubmits": 79, "science_release": False, "slurm_submitted": False}


def prepare(confirm):
    need(confirm == ACK_PREP, "requires --confirm " + ACK_PREP)
    need(not LEDGER.exists(), "Prior prepare attempt exists; do not run blindly")
    c = preflight()
    for p in (CASE, RUN, ARCH): need(not p.exists() and not p.is_symlink(), "exists: " + str(p))
    REPORTS.mkdir(parents=True, exist_ok=True)
    with LEDGER.open("x") as f:
        json.dump({"phase": "PREPARATION_ATTEMPT_UNCERTAIN", "science_release": False, "created_utc": utc(), "case": str(CASE)}, f, indent=2)
    print("CLONING NEW PRIVATE CASE (NO SLURM)", CASE, flush=True)
    cmd([CTSM / "cime/scripts/create_clone", "--case", CASE, "--clone", TEMPLATE, "--keepexe"], CTSM / "cime/scripts", 600)
    need(xq(CASE, "CASE") == NAME, "clone identity")
    for k, v in SETTINGS.items(): xc(CASE, k, v)
    if abs(c["co2"] - c["co2_template"]) >= 0.005: xc(CASE, "CCSM_CO2_PPMV", f"{c['co2']}")
    (CASE / "user_nl_datm_streams").write_text(c["stream"]); (CASE / "user_nl_clm").write_text(c["land"])
    RUN.mkdir(parents=True, exist_ok=True)
    if not (CASE / ".case.run").is_file(): cmd([CASE / "case.setup"], CASE, 400)
    env, locked = CASE / "env_case.xml", CASE / "LockedFiles/env_case.xml"
    need(locked.is_file() and env.read_bytes() == locked.read_bytes(), "env_case lock mismatch before preview")
    before = env.read_bytes(); old_root = xq(CASE, "COMP_ROOT_DIR_LND")
    need(old_root == "$SRCROOT" or Path(old_root).resolve() == CTSM.resolve(), "Unexpected CTSM land root " + old_root)
    try:
        xc(CASE, "COMP_ROOT_DIR_LND", c["overlay"]); cmd([CASE / "preview_namelists"], CASE, 680)
    finally:
        xc(CASE, "COMP_ROOT_DIR_LND", old_root)
    if env.read_bytes() != before:   # same semantic restore as the DE-RuR / ES-Agu preparation
        def sig_without_root(raw):
            root = ET.fromstring(raw); removed = 0
            for parent in root.iter():
                for child in list(parent):
                    if child.tag == "entry" and child.get("id") == "COMP_ROOT_DIR_LND": parent.remove(child); removed += 1
            need(removed == 1, "Unexpected land root entries")
            def sig(e): return (e.tag, tuple(sorted(e.attrib.items())), (e.text or "").strip(), tuple(sig(x) for x in e))
            return sig(root)
        need(sig_without_root(env.read_bytes()) == sig_without_root(before), "Other env_case.xml settings changed; stop")
        need(locked.read_bytes() == before, "Locked env_case.xml changed")
        tmp = env.with_name("env_case.xml.ch_restore_tmp"); need(not tmp.exists(), "Unexpected restore file")
        with tmp.open("xb") as f: f.write(before); f.flush(); os.fsync(f.fileno())
        os.replace(tmp, env)
    need(env.read_bytes() == locked.read_bytes() == before, "env_case lock not restored after preview")
    rec = verify(c)
    rec.update({"phase": "PREPARED_VERIFIED_NOT_SUBMITTED", "template": str(TEMPLATE), "source_science_HOLD": True,
                "run_target": "DIRECT_AD400_80x5_NO_AD5", "forcing": "F1A", "F1A_plan": str(F1A_PLAN), "F1A_plan_sha256": c["plan_sha256"],
                "PFT_surface": c["surface"], "PFT_surface_sha256": c["surface_sha256"], "FATES_param": c["param"],
                "FATES_param_sha256": c["param_sha256"], "phenology_class": c["phenology"], "human_stress_indices": "NONE",
                "datm_files": c["files"], "datm_sha256": {f: sha(f) for f in c["files"]}, "co2_ppmv": c["co2"],
                "co2_template_ppmv": c["co2_template"], "created_utc": utc(),
                "manual_science_decisions": ["C3 grass 100 is a herbaceous proxy, not a measured footprint fraction",
                                             "inherited grid soil, ORGANIC 0 (no site SOC found)",
                                             "option-A humidity: MDS-filled RH<10 % replaced by packaged ERA VPD"]})
    with LEDGER.open("w") as f: json.dump(rec, f, indent=2, default=str); f.write("\n")
    print("STAGE06C VERIFIED NEW DIRECT AD400 CASE; NO SLURM", CASE)


def scheduler_clear():
    q = cmd(["squeue", "-h", "-u", os.environ.get("USER", "ly3n24"), "-o", "%i|%j|%T"], None, 100)
    need(not [s for s in q.splitlines() if "CH-Aws_ICOS_B04" in s], "Slurm queue already has a CH-Aws Batch04 case")
    h = cmd(["sacct", "-X", "-u", os.environ.get("USER", "ly3n24"), "-S", "2026-11-02", "--format=JobIDRaw,JobName%90,State",
             "--parsable2", "--noheader"], None, 100)
    need(not [s for s in h.splitlines() if "CH-Aws_ICOS_B04" in s], "Slurm accounting already knows a CH-Aws Batch04 case")


def audit(check_queue=True):
    need(LEDGER.is_file(), "no prepare ledger")
    need(not SUBMISSION.exists() and not SUBMISSION.is_symlink(), "submission receipt exists; never submit twice")
    obj = json.loads(LEDGER.read_text())
    need(obj.get("phase") == "PREPARED_VERIFIED_NOT_SUBMITTED" and obj.get("slurm_submitted") is False, "ledger phase " + str(obj.get("phase")))
    c = {"files": obj["datm_files"], "surface": obj["PFT_surface"], "surface_sha256": obj["PFT_surface_sha256"],
         "param": obj["FATES_param"], "param_sha256": obj["FATES_param_sha256"], "co2": obj["co2_ppmv"],
         "exe": str(Path(xq(TEMPLATE, "EXEROOT")) / "cesm.exe")}
    h = verify(c)
    need(h["lnd_in_sha256"] == obj["lnd_in_sha256"] and h["effective_stream_sha256"] == obj["effective_stream_sha256"], "case changed after prepare")
    for f, d in obj["datm_sha256"].items(): need(sha(f) == d, "DATM file changed " + f)
    need(sha(F1A_PLAN) == obj["F1A_plan_sha256"], "F1A plan changed after prepare")
    need((CASE / "env_case.xml").read_bytes() == (CASE / "LockedFiles/env_case.xml").read_bytes(), "env_case lock error")
    cs = (CASE / "CaseStatus").read_text(errors="replace") if (CASE / "CaseStatus").is_file() else ""
    need(not re.search(r"case\.submit starting|case\.run starting", cs), "CaseStatus shows a prior submission")
    need("--skip-preview-namelist" in cmd([CASE / "case.submit", "--help"], CASE, 100, allowed=(0, 1, 2)), "case.submit lacks --skip-preview-namelist")
    if check_queue: scheduler_clear()
    print("STAGE06C AUDIT PASS | prepared, verified, never submitted |", CASE)
    return obj


def submit(confirm):
    need(confirm == ACK_SUB, "requires --confirm " + ACK_SUB)
    audit(True)
    soft, hard = resource.getrlimit(resource.RLIMIT_STACK)
    if soft != resource.RLIM_INFINITY and soft < 64 * 1024 * 1024:
        need(hard == resource.RLIM_INFINITY or hard >= 64 * 1024 * 1024, "stack hard limit under 64 MiB")
        resource.setrlimit(resource.RLIMIT_STACK, (hard, hard))
    print("STACK", resource.getrlimit(resource.RLIMIT_STACK), "HOST", socket.gethostname(), flush=True)
    rec = {"phase": "SUBMISSION_ATTEMPT_UNCERTAIN", "submit_utc": utc(), "case": str(CASE), "science_release": False, "no_separate_AD5": True}
    with SUBMISSION.open("x") as f: json.dump(rec, f, indent=2); f.write("\n"); f.flush(); os.fsync(f.fileno())
    cmd([CASE / "xmlchange", "RESUBMIT=79"], CASE, 90)
    need(xq(CASE, "RESUBMIT") == "79", "RESUBMIT=79 failed; attempt uncertain, do not retry")
    p = subprocess.run([str(CASE / "case.submit"), "--skip-preview-namelist"], cwd=CASE, capture_output=True, text=True, timeout=650, check=False)
    print("CIME SUBMIT STDOUT\n" + p.stdout[-4000:], "\nCIME SUBMIT STDERR\n" + p.stderr[-1200:], flush=True)
    need(p.returncode == 0, "case.submit returned nonzero; attempt uncertain, do not retry")
    run = re.findall(r"Submitted job case\.run with id (\d+)", p.stdout); arch = re.findall(r"Submitted job case\.st_archive with id (\d+)", p.stdout)
    need(len(run) == 1 and len(arch) == 1, "could not parse job IDs; do NOT retry")
    cfg = configparser.RawConfigParser(); opts = CASE / ".submit_options"
    if opts.is_file(): cfg.read(opts)
    persisted = cfg.has_section("SubmitOptions") and cfg.getboolean("SubmitOptions", "skip_pnl", fallback=False)
    rec.update({"phase": "AD400_SUBMITTED_MODEL_NOT_COMPLETED", "run_job_id": run[0], "archive_job_id": arch[0],
                "skip_preview_persisted": persisted, "submitted_utc": utc()})
    with SUBMISSION.open("w") as f: json.dump(rec, f, indent=2); f.write("\n")
    print(f"CH-Aws F1A HINONE EXPLORATORY DIRECT AD400 SUBMITTED | run {run[0]} | archive {arch[0]} | {FIRST}->{FIRST + 400} 80x5 | skip_pnl persisted {persisted}")


def self_test():
    import numpy as np
    from netCDF4 import Dataset
    assert 400 // int(SETTINGS["STOP_N"]) - 1 == 79 and LAST - FIRST + 1 == 19
    t = nmlset(nmlset("  fsurdat = '/a.nc'\nhist_fincl1 = 'GPP'\n", "hist_fincl1", ", ".join(f"'{x}'" for x in HISTORY)), *HINONE)
    assert hist_fields(t) == HISTORY and nmlget(t, HINONE[0]) == "NONE"
    raw = "".join(f"CLM_USRDAT.UNSET:{k} = old\n" for k in REQUIRED_STREAM if k not in ("datafiles", "datavars", "offset"))
    raw += "CLM_USRDAT.UNSET:datafiles = /x/CH-Aws_DATM_2006.nc\nCLM_USRDAT.UNSET:datavars = TBOT Sa_tbot, \\\nQBOT Sa_shum\n"
    out = stream_replace(raw, [f"/y/CH-Aws_DATM_{y}.nc" for y in range(FIRST, 2007)] + [f"/z/CH-Aws_DATM_2007_F1A.nc"])
    assert "year_last = 2024" in out and "/z/CH-Aws_DATM_2007_F1A.nc" in out and "/x/" not in out and "QBOT Sa_shum" in out
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        (d / "h").write_bytes(b"hello\n"); assert git_blob(d / "h") == "ce013625030ba8dba906f756967f9e9ca394464a"
        src = d / "src.nc"
        with Dataset(str(src), "w") as ds:
            for n, k in (("lsmlat", 1), ("lsmlon", 1), ("natpft", 15), ("nlevsoi", 10), ("numurbl", 3)): ds.createDimension(n, k)
            for n, val in (("PCT_NATVEG", 96.3755), ("PCT_CROP", 3.6245), ("PCT_LAKE", 0.0), ("PCT_WETLAND", 0.0), ("PCT_GLACIER", 0.0),
                           ("LATIXY", 46.5831), ("LONGXY", 9.7906)):
                ds.createVariable(n, "f8", ("lsmlat", "lsmlon"))[:] = val
            ds.createVariable("PCT_URBAN", "f8", ("numurbl", "lsmlat", "lsmlon"))[:] = 0.0
            p = ds.createVariable("PCT_NAT_PFT", "f8", ("natpft", "lsmlat", "lsmlon")); a = np.zeros((15, 1, 1))
            a[0], a[2], a[8], a[12], a[13] = 11.5, 24.2, 5.6, 56.6, 2.1; p[:] = a
            for n in ("PCT_SAND", "PCT_CLAY", "ORGANIC"): ds.createVariable(n, "f8", ("nlevsoi", "lsmlat", "lsmlon"))[:] = 7.0
        s = make_surface(src, d / "new.nc", TARGET)
        assert s["pft"][13] == 100.0 and sum(s["pft"]) == 100.0 and s["land"]["PCT_CROP"] == 0.0 and s["sand"] == [7.0] * 10
        try: make_surface(src, d / "new.nc", TARGET); raise AssertionError("overwrote an existing partial")
        except RuntimeError: pass
    print("STAGE06C SELF-TEST PASS (namelist + HINONE + history, DATM stream with F1A, Stage02X surface edit, git blob; no HPC)")


def main():
    global ROLLOUT
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("action", choices=("self-test", "check", "build-surface", "prepare", "audit", "submit"))
    ap.add_argument("--confirm", default="")
    ap.add_argument("--rollout-dir", type=Path, default=DEFAULT_ROLLOUT)
    a = ap.parse_args()
    ROLLOUT = a.rollout_dir
    if a.action == "self-test": return self_test()
    if a.action == "check": preflight(show=True, need_inputs=False); print("STAGE06C CHECK PASS | READ ONLY"); return
    if a.action == "build-surface": return build_surface(a.confirm)
    if a.action == "prepare": return prepare(a.confirm)
    if a.action == "audit": audit(True); return
    if a.action == "submit": return submit(a.confirm)


if __name__ == "__main__":
    try: main()
    except RuntimeError as e: print("STAGE06C HOLD:", e, file=sys.stderr); sys.exit(2)
