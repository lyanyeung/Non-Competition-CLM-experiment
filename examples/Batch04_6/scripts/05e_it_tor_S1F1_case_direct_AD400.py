#!/usr/bin/env python3
"""Batch04 IT-Tor: the single S1 soil + F1 forcing FIXNC direct AD400 case, one-time submit.

Operator decision, 2 Nov 2026: the original inputs (S0 soil ORGANIC = 0, F0 forcing) are dropped and IT-Tor runs
one chain only, S1 + F1. No S0/F0 control chain.

Same method as the three running Batch04 chains (DE-RuR_prepare_ad400.py / ES-Agu_prepare_ad400.py and 04e) and 05c:
clone the original case with --keepexe, private FATES AD namelist overlay preview, FIXNC flags with spinup_state=2,
RESUBMIT 0 at prepare and 79 only at the one-time submit, crash-safe submission sentinel.

IT-Tor specifics
  template   IT-Tor_FATES_SPINUP1000_S30SHARED; 18 annual DATM files 2008-2025 from the Stage03B lineage
             (the same files the template stream uses)
  surface    S1 = Stage02X GitHub-PFT surface (host 13 C3 grass 100) with ORGANIC levels 1-4 = 55.7759 kg/m3,
             levels 5-10 = 0 (05d build-s1; Leolini et al. 2025, 64.7 Mg C/ha 0-20 cm)
  forcing    F1 = 2008-2024 unchanged + 2025 file from 05d f1-rebuild (repository 05a: TBOT/QBOT at the three
             2025-11-13 14:30-15:30 labels replaced by packaged ERA TA/VPD, pressure unchanged). stage-f1 copies
             it to a fixed experiments folder; the case never reads from a HOME temp folder.
  FATES      the template's effective parameter file (shared default; host 13 -> cool C3 grass)
  CO2        constant NOAA global annual mean of 2008, the first forcing year (earlier-batch convention)
Science: S1 is one published topsoil stock (no profile below 20 cm); F1 changes 3 half-hours; the rest of the
2025 Oct-Nov MDS/ERA filled period is kept as in Stage03N.

Actions
  self-test                                                  no HPC, temp files only
  check                                                      READ ONLY
  stage-f1 --confirm STAGE_IT_TOR_F1_FORCING                 new folder only
  prepare  --confirm PREPARE_IT_TOR_B04_S1F1_AD400_NO_SLURM  new case, no Slurm
  audit                                                      READ ONLY
  submit   --confirm SUBMIT_IT_TOR_S1F1_DIRECT_AD400_80X5_ONCE
Never repeat prepare or submit after a ledger or submission receipt exists.
"""
import argparse, configparser, csv, hashlib, json, os, re, resource, shutil, socket, subprocess, sys, tempfile
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

B = Path("/iridisfs/scratch/ly3n24/CLM_FATES")
CTSM = B / "CTSM"
OUTPUT = Path("/scratch/ly3n24/CTSM_FATES_OUTPUTS")
HOME = Path.home()
TEMPLATE = B / "cases/IT-Tor_FATES_SPINUP1000_S30SHARED"
NAME = "IT-Tor_ICOS_B04_FIXNC_AD400_DIRECT"
OLD_NAMES = ("IT-Tor_B04_FIXNC_AD400_DIRECT",)          # superseded four-site 04a naming; must never exist
CASE = B / "cases" / NAME
RUN = OUTPUT / NAME / "run"
ARCH = OUTPUT / "archive" / NAME
FIRST, LAST = 2008, 2025
REPORT_B = HOME / "ICOS_Batch04_stage03b_reuse_PbMYw9CH/results/stage03b_four_site_reused_stage28_DATM_lineage.json"
REPORT_Y = HOME / "ICOS_Batch04_stage02y_pT2JPSjW/results/stage02y_four_site_candidate_surface_case_binding_audit.json"
MANIFESTS = {"STAGE30_CONSOLIDATED": "04_consolidated_13site_271_DATM_SHA256_manifest.csv",
             "STAGE29B": "10_annual_full_DATM_SHA256_manifest.csv"}
SURF_SRC = B / "experiments/Batch04_GitHub_PFT_Gz7kLAkn/IT-Tor_B04_GITHUBPFT_POINT_CANDIDATE.nc"
SURF_SRC_SHA = "908b73f67f74333fa70fcd3b07d8500de14c70b4efdd1e6f36ea23bb4f8b7c7b"
B04 = B / "experiments/NonCompetitionObserved22/Batch04_6"
S1_DIR = B04 / "IT-Tor_S1_soil_organic_candidate_v1"
S1 = S1_DIR / "IT-Tor_B04_GITHUBPFT_S1_ORGANIC_POINT_CANDIDATE.nc"
S1_PROFILE = [55.7759] * 4 + [0.0] * 6
F1_DIR = B04 / "IT-Tor_F1_forcing_v1"
F1 = F1_DIR / "IT-Tor_DATM_2025_F1.nc"
F1_MANIFEST = F1_DIR / "manifest_PRIVATE.json"
F1_TIMES = ("2025-11-13 14:30:00", "2025-11-13 15:00:00", "2025-11-13 15:30:00")
SHARED_PARAM_SHA = "0819f8fddcb3566f6209f72bb1159a3161d03c8225a1464727b1d2b21aec6c04"
CO2_CSV = B / "experiments/NonCompetitionObserved22/AmeriFlux_Batch02_10/Stage06_direct_AD400/co2_annmean_gl.csv"
REPORTS = B / "experiments/Batch04_IT_Tor_AD400_DIRECT_preparation"
LEDGER = REPORTS / "stage05e_prepare_state.json"
SUBMISSION = REPORTS / "stage05e_submission_attempt_PRIVATE.json"
OVERLAYS = (B / "experiments/NonCompetitionObserved22/AmeriFlux_Batch02_10/_private_ctsm_FATES_AD400_namelist_overlay",
            B / "experiments/NonCompetitionObserved22/Batch02_10/_private_ctsm_FATES_AD5_namelist_overlay_v1")
FLAGS = {"use_fates": ".true.", "use_fates_sp": ".false.", "use_fates_fixed_biogeog": ".true.",
         "use_fates_nocomp": ".true.", "use_cn": ".false.", "spinup_state": "2"}
HISTORY = ["TOTSOMC", "TOTSOMN", "TLAI", "FATES_GPP", "FATES_NPP", "TWS", "H2OSNO"]
REQUIRED_STREAM = ("year_first", "year_last", "year_align", "offset", "taxmode", "tintalgo", "mapalgo", "meshfile",
                   "datafiles", "datavars")
SETTINGS = {"RUN_TYPE": "startup", "RUN_STARTDATE": f"{FIRST}-01-01", "CONTINUE_RUN": "FALSE",
            "CLM_ACCELERATED_SPINUP": "on", "CLM_FORCE_COLDSTART": "on", "STOP_OPTION": "nyears", "STOP_N": "5",
            "REST_OPTION": "nyears", "REST_N": "5", "RESUBMIT": "0", "RESUBMIT_SETS_CONTINUE_RUN": "TRUE",
            "DOUT_S": "TRUE", "DATM_YR_START": str(FIRST), "DATM_YR_END": str(LAST), "DATM_YR_ALIGN": str(FIRST),
            "RUNDIR": str(RUN), "DOUT_S_ROOT": str(ARCH)}
ACK_F1, ACK_PREP = "STAGE_IT_TOR_F1_FORCING", "PREPARE_IT_TOR_B04_S1F1_AD400_NO_SLURM"
ACK_SUB = "SUBMIT_IT_TOR_S1F1_DIRECT_AD400_80X5_ONCE"


def need(x, msg):
    if not x: raise RuntimeError(msg)


def utc(): return datetime.now(timezone.utc).isoformat()


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for b in iter(lambda: f.read(1048576), b""): h.update(b)
    return h.hexdigest()


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


def compare_nc(a_path, b_path):
    """{variable: number of differing values} for every variable that differs; -1 if shapes differ."""
    from netCDF4 import Dataset
    import numpy as np
    out = {}
    with Dataset(str(a_path)) as a, Dataset(str(b_path)) as b:
        need(set(a.variables) == set(b.variables), f"variable sets differ {sorted(set(a.variables) ^ set(b.variables))}")
        for k in a.variables:
            x, y = np.ma.asarray(a.variables[k][:]), np.ma.asarray(b.variables[k][:])
            if x.shape != y.shape: out[k] = -1
            elif not np.ma.allequal(x, y): out[k] = int(np.sum(np.ma.filled(x != y, True)))
    return out


# ------------------------------------------------------------------ inputs
def lineage():
    """IT-Tor 2008-2025 annual DATM paths and sha from the Stage03B report (same check as run_pair_prepare.py)."""
    need(REPORT_B.is_file() and REPORT_Y.is_file(), "Stage03B or Stage02Y report missing")
    b, y = json.loads(REPORT_B.read_text()), json.loads(REPORT_Y.read_text())
    need(b.get("read_only") is True and b.get("science_release") is False and y.get("read_only") is True and
         y.get("science_release") is False, "Saved reports are not the expected read-only science-HOLD reports")
    bm = [x for x in b.get("sites", []) if x.get("site") == "IT-Tor"]; ym = [x for x in y.get("sites", []) if x.get("site") == "IT-Tor"]
    need(len(bm) == len(ym) == 1, "IT-Tor missing from Stage03B/Stage02Y")
    sb, sy = bm[0], ym[0]
    need(sb.get("stage28_met_SHA_verified") is True and sb.get("all_current_paths_match_historical") is True and
         sy.get("PFT_selection_approved") is True, "IT-Tor lineage or PFT evidence not verified")
    surf = sy.get("surface", {})
    need(surf.get("candidate_sha") == SURF_SRC_SHA and surf.get("source_soil_unchanged") is True, "Stage02Y IT-Tor surface evidence mismatch")
    tm = [x for x in sy.get("cases", []) if x.get("case") == TEMPLATE.name]
    need(len(tm) == 1 and tm[0].get("Stage02V_static_path_match") is True, "Stage02Y template evidence mismatch")
    path = Path(sb["historical_DATM_manifest"])
    if path.is_dir():
        need(sb.get("historical_manifest_selected") in MANIFESTS, "unknown annual manifest"); path = path / MANIFESTS[sb["historical_manifest_selected"]]
    with path.open(encoding="utf-8-sig", newline="") as f:
        rows = sorted((r for r in csv.DictReader(f) if r.get("site") == "IT-Tor"), key=lambda r: int(r["year"]))
    need([int(r["year"]) for r in rows] == list(range(FIRST, LAST + 1)), "IT-Tor annual years incomplete or duplicated")
    comp = {int(x["year"]): x for x in sb.get("yearly_path_comparisons", [])}
    out = []
    for r in rows:
        c = comp.get(int(r["year"]), {})
        need(c.get("current") == r["datm_nc"] and c.get("literal_path_equal") is True, "annual path mismatch " + r["year"])
        out.append({"year": int(r["year"]), "path": r["datm_nc"], "sha256": r["sha256"]})
    return out


def s1_state():
    need(S1_DIR.is_dir() and not S1_DIR.is_symlink() and S1.is_file(), "S1 surface not built: run 05d build-s1 first")
    m = json.loads((S1_DIR / "manifest.json").read_text())
    need(m.get("surface_sha256") == sha(S1) and m.get("source_sha256") == SURF_SRC_SHA, "S1 manifest sha mismatch")
    need(m.get("changed_variables") == ["ORGANIC"] and m.get("ORGANIC_kg_m3_levels_1_10") == S1_PROFILE, "S1 manifest content")
    return m["surface_sha256"]


def s1_check():
    """S1 differs from the Stage02X source only in ORGANIC, with the S1 profile."""
    from netCDF4 import Dataset
    import numpy as np
    need(SURF_SRC.is_file() and sha(SURF_SRC) == SURF_SRC_SHA, "Stage02X IT-Tor surface missing or sha differs")
    d = compare_nc(SURF_SRC, S1)
    need(set(d) == {"ORGANIC"}, f"S1 differs from Stage02X outside ORGANIC: {d}")
    with Dataset(str(S1)) as ds:
        g = lambda k: np.ma.asarray(ds.variables[k][:]).astype(float)
        org = g("ORGANIC").reshape(10, -1)[:, 0].tolist()
        need(all(abs(a - b) < 1e-3 for a, b in zip(org, S1_PROFILE)), f"S1 ORGANIC {org}")
        pft = g("PCT_NAT_PFT").reshape(ds.variables["PCT_NAT_PFT"].shape[0], -1)[:, 0]
        return {"organic": org, "pft": {i: float(x) for i, x in enumerate(pft) if x}, "natveg": float(g("PCT_NATVEG").sum()),
                "lat": float(g("LATIXY").ravel()[0]), "lon": float(g("LONGXY").ravel()[0])}


def f1_rebuilds():
    return sorted((p for p in HOME.glob("ICOS_Batch04_IT_Tor_F1_05a.*/result")
                   if (p / "IT-Tor_DATM_2025_F1.nc").is_file() and (p / "manifest_PRIVATE.json").is_file()),
                  key=lambda p: (p / "IT-Tor_DATM_2025_F1.nc").stat().st_mtime)


def f1_valid(f1, manifest, base):
    """F1 = the 2025 baseline with exactly 3 TBOT and 3 QBOT values changed at F1_TIMES; manifest agrees."""
    need(manifest.get("status") == "DETACHED_EXPLORATORY_NOT_RELEASED" and manifest.get("site") == "IT-Tor", "F1 manifest status/site")
    need(manifest.get("baseline_path") == base["path"] and manifest.get("baseline_sha256") == base["sha256"], "F1 baseline is not the Stage03B 2025 file")
    need(manifest.get("candidate_sha256") == sha(f1), "F1 file sha differs from its manifest")
    need(sorted(c.get("time") for c in manifest.get("changes", [])) == list(F1_TIMES), "F1 manifest edit times")
    d = compare_nc(base["path"], f1)
    need(d == {"TBOT": 3, "QBOT": 3}, f"F1 differs from the 2025 baseline in more than the six target values: {d}")


def f1_state(base):
    """(path, sha) of the staged F1, or (None, None) if stage-f1 has not run."""
    if not F1_DIR.exists(): return None, None
    need(F1.is_file() and F1_MANIFEST.is_file() and not F1_DIR.is_symlink(), "F1 folder incomplete: inspect " + str(F1_DIR))
    m = json.loads(F1_MANIFEST.read_text())
    need(m.get("staged_sha256") == sha(F1) == m.get("candidate_sha256"), "staged F1 sha mismatch")
    f1_valid(F1, m, base)
    return F1, m["staged_sha256"]


def stage_f1(confirm):
    need(confirm == ACK_F1, "requires --confirm " + ACK_F1)
    base = lineage()[-1]; need(base["year"] == 2025, "last lineage year is not 2025")
    p, h = f1_state(base)
    if p: print("F1 EXISTS AND VERIFIED", p, h); return
    reb = f1_rebuilds(); need(reb, "no 05d f1-rebuild output under ~/ICOS_Batch04_IT_Tor_F1_05a.*; run 05d f1-rebuild first")
    for r in reb[:-1]:
        need(compare_nc(r / "IT-Tor_DATM_2025_F1.nc", reb[-1] / "IT-Tor_DATM_2025_F1.nc") == {}, f"05a rebuilds disagree: {r} vs {reb[-1]}")
    src = reb[-1]; m = json.loads((src / "manifest_PRIVATE.json").read_text())
    f1_valid(src / "IT-Tor_DATM_2025_F1.nc", m, base)
    tmp = F1_DIR.with_name(F1_DIR.name + ".partial"); need(not tmp.exists(), "leftover " + str(tmp) + "; inspect")
    tmp.mkdir(parents=True)
    shutil.copyfile(src / "IT-Tor_DATM_2025_F1.nc", tmp / F1.name)
    need(sha(tmp / F1.name) == m["candidate_sha256"], "copy sha mismatch")
    m.update({"staged_from": str(src), "staged_path": str(F1), "staged_sha256": m["candidate_sha256"], "staged_utc": utc(),
              "generator": "examples/Batch04_6/scripts/05a_it_tor_make_f1_candidate.py sha 997f237b (via 05d f1-rebuild)",
              "operator_decision": "2 Nov 2026: IT-Tor runs S1+F1 only"})
    (tmp / F1_MANIFEST.name).write_text(json.dumps(m, indent=2) + "\n")
    tmp.rename(F1_DIR)
    print(f"F1 STAGED {F1} sha {sha(F1)} | from {src} | {len(reb)} rebuild(s), all identical | only 3 TBOT + 3 QBOT differ from 2025")


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
    rows = lineage()
    tfiles, tst = parse_stream(TEMPLATE)
    need(tfiles == [r["path"] for r in rows] and tst.get("taxmode") == "cycle", "template stream is not the Stage03B 2008-2025 files")
    for r in rows: need(Path(r["path"]).is_file() and sha(r["path"]) == r["sha256"], f"annual DATM sha changed {r['year']}")
    co2 = co2_first_year(); co2_t = float(xq(TEMPLATE, "CCSM_CO2_PPMV"))
    param = template_param()
    ov = overlay()
    s1_sha = s1_state() if need_inputs else (s1_state() if S1_DIR.exists() else None)
    s = s1_check() if s1_sha else None
    if s:
        pts = (float(xq(TEMPLATE, "PTS_LAT")), float(xq(TEMPLATE, "PTS_LON")))
        need(abs(s["lat"] - pts[0]) < 0.01 and abs((s["lon"] - pts[1] + 180) % 360 - 180) < 0.01, f"S1 point {s['lat']},{s['lon']} != PTS {pts}")
    f1, f1_sha = f1_state(rows[-1])
    if need_inputs: need(f1 is not None, "F1 not staged: run stage-f1 first")
    files = [r["path"] for r in rows[:-1]] + [str(f1 or F1)]
    land = (TEMPLATE / "user_nl_clm").read_text()
    land = nmlset(land, "fsurdat", f"'{S1}'")
    land = nmlset(land, "fates_paramfile", f"'{param}'")
    for k, v in FLAGS.items(): land = nmlset(land, k, v)
    land = nmlset(land, "finidat", "''")
    land = nmlset(land, "hist_fincl1", ", ".join(f"'{x}'" for x in HISTORY))
    need(hist_fields(land) == HISTORY, "hist_fincl1 not cleanly replaced in user_nl_clm (continuation lines?)")
    stream = stream_replace((TEMPLATE / "user_nl_datm_streams").read_text(), files)
    for p in [CASE, RUN, ARCH]:
        if p.exists() or p.is_symlink(): need(LEDGER.is_file(), "new case/run/archive exists without ledger: " + str(p))
    for o in OLD_NAMES:
        need(not (B / "cases" / o).exists() and not (OUTPUT / o).exists(), "superseded IT-Tor case exists: " + o + "; stop and review")
    ctx = {"files": files, "surface": str(S1), "surface_sha256": s1_sha, "f1_sha256": f1_sha, "param": str(param),
           "param_sha256": sha(param), "exe": str(exe), "overlay": str(ov), "co2": co2, "co2_template": co2_t,
           "land": land, "stream": stream}
    if show:
        print("STAGE05E PREFLIGHT PASS | IT-Tor S1+F1 single chain | SCIENCE HOLD (single-study topsoil, 3-HH forcing fix)")
        print(f"  template {TEMPLATE.name} | exe {exe} | overlay {ov}")
        print(f"  DATM {len(rows)} Stage03B files {FIRST}-{LAST}, sha verified; case uses 2008-2024 unchanged + 2025 F1")
        print(f"  F1 {'STAGED ' + str(f1) + ' sha ' + f1_sha[:12] if f1 else 'NOT STAGED (stage-f1 copies the 05d rebuild to ' + str(F1) + ')'}"
              f" | 05d rebuilds found: {len(f1_rebuilds())}")
        print(f"  S1 {'BUILT ' + str(S1) + ' sha ' + s1_sha[:12] if s1_sha else 'NOT BUILT (05d build-s1)'}"
              + (f" | ORGANIC {s['organic']} | NATVEG {s['natveg']} | host PFT {s['pft']} | point {s['lat']:.4f},{s['lon']:.4f}" if s else ""))
        print(f"  FATES param {param} sha {ctx['param_sha256'][:12]} ({'shared default' if ctx['param_sha256'] == SHARED_PARAM_SHA else 'NOT the shared default sha'})")
        print(f"  CO2 NOAA {FIRST} {co2} | template {co2_t} | {'same' if abs(co2 - co2_t) < 0.005 else 'prepare sets the NOAA value'}")
        print(f"  case {NAME} {FIRST}->{FIRST + 400} | STOP_N 5, prepare RESUBMIT 0, submit sets 79 | ledger {'EXISTS' if LEDGER.is_file() else 'none'}")
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
    need(hist_fields(text) == HISTORY, "Wrong history fields")
    need((RUN / "lnd_in").is_file() and sha(RUN / "lnd_in") == sha(doc), "RUNDIR lnd_in differs from CaseDocs")
    files, st = parse_stream(CASE)
    need(files == c["files"], "CRITICAL: effective DATM stream is not 2008-2024 Stage03B + 2025 F1")
    for k, v in {"year_first": str(FIRST), "year_last": str(LAST), "year_align": str(FIRST), "taxmode": "cycle", "offset": "0"}.items():
        need(st[k] == v, "DATM cycle mismatch " + k)
    need((RUN / "datm.streams.xml").is_file() and sha(RUN / "datm.streams.xml") == sha(CASE / "CaseDocs/datm.streams.xml"), "RUNDIR stream differs")
    need(sha(c["surface"]) == c["surface_sha256"] and sha(c["param"]) == c["param_sha256"] and sha(F1) == c["f1_sha256"], "S1/param/F1 drift")
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
        tmp = env.with_name("env_case.xml.it_restore_tmp"); need(not tmp.exists(), "Unexpected restore file")
        with tmp.open("xb") as f: f.write(before); f.flush(); os.fsync(f.fileno())
        os.replace(tmp, env)
    need(env.read_bytes() == locked.read_bytes() == before, "env_case lock not restored after preview")
    rec = verify(c)
    rec.update({"phase": "PREPARED_VERIFIED_NOT_SUBMITTED", "template": str(TEMPLATE), "source_science_HOLD": True,
                "run_target": "DIRECT_AD400_80x5_NO_AD5", "variant": "S1F1_ONLY",
                "PFT_surface": c["surface"], "PFT_surface_sha256": c["surface_sha256"], "F1_sha256": c["f1_sha256"],
                "FATES_param": c["param"], "FATES_param_sha256": c["param_sha256"], "datm_files": c["files"],
                "datm_sha256": {f: sha(f) for f in c["files"]}, "co2_ppmv": c["co2"], "co2_template_ppmv": c["co2_template"],
                "created_utc": utc(),
                "manual_science_decisions": ["S1 topsoil stock from one study, nothing below 20 cm",
                                             "F1 fixes 3 half-hours; rest of the 2025 Oct-Nov MDS/ERA fill kept",
                                             "operator dropped S0/F0: single S1F1 chain"]})
    with LEDGER.open("w") as f: json.dump(rec, f, indent=2); f.write("\n")
    print("STAGE05E VERIFIED NEW DIRECT AD400 CASE; NO SLURM", CASE)


def scheduler_clear():
    names = (NAME,) + OLD_NAMES
    q = cmd(["squeue", "-h", "-u", os.environ.get("USER", "ly3n24"), "-o", "%i|%j|%T"], None, 100)
    need(not [s for s in q.splitlines() if any(n in s for n in names)], "Slurm queue already has an IT-Tor B04 case")
    h = cmd(["sacct", "-X", "-u", os.environ.get("USER", "ly3n24"), "-S", "2026-11-02", "--format=JobIDRaw,JobName%90,State",
             "--parsable2", "--noheader"], None, 100)
    need(not [s for s in h.splitlines() if any(n in s for n in names)], "Slurm accounting already knows an IT-Tor B04 case")


def audit(check_queue=True):
    need(LEDGER.is_file(), "no prepare ledger")
    need(not SUBMISSION.exists() and not SUBMISSION.is_symlink(), "submission receipt exists; never submit twice")
    obj = json.loads(LEDGER.read_text())
    need(obj.get("phase") == "PREPARED_VERIFIED_NOT_SUBMITTED" and obj.get("slurm_submitted") is False, "ledger phase " + str(obj.get("phase")))
    c = {"files": obj["datm_files"], "surface": obj["PFT_surface"], "surface_sha256": obj["PFT_surface_sha256"], "f1_sha256": obj["F1_sha256"],
         "param": obj["FATES_param"], "param_sha256": obj["FATES_param_sha256"], "co2": obj["co2_ppmv"],
         "exe": str(Path(xq(TEMPLATE, "EXEROOT")) / "cesm.exe")}
    h = verify(c)
    need(h["lnd_in_sha256"] == obj["lnd_in_sha256"] and h["effective_stream_sha256"] == obj["effective_stream_sha256"], "case changed after prepare")
    for f, d in obj["datm_sha256"].items(): need(sha(f) == d, "DATM file changed " + f)
    need((CASE / "env_case.xml").read_bytes() == (CASE / "LockedFiles/env_case.xml").read_bytes(), "env_case lock error")
    cs = (CASE / "CaseStatus").read_text(errors="replace") if (CASE / "CaseStatus").is_file() else ""
    need(not re.search(r"case\.submit starting|case\.run starting", cs), "CaseStatus shows a prior submission")
    need("--skip-preview-namelist" in cmd([CASE / "case.submit", "--help"], CASE, 100, allowed=(0, 1, 2)), "case.submit lacks --skip-preview-namelist")
    if check_queue: scheduler_clear()
    print("STAGE05E AUDIT PASS | prepared, verified, never submitted |", CASE)
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
    print(f"IT-Tor S1F1 EXPLORATORY DIRECT AD400 SUBMITTED | run {run[0]} | archive {arch[0]} | {FIRST}->{FIRST + 400} 80x5 | skip_pnl persisted {persisted}")


def self_test():
    import numpy as np
    from netCDF4 import Dataset
    assert 400 // int(SETTINGS["STOP_N"]) - 1 == 79 and LAST - FIRST + 1 == 18
    t = nmlset("  fsurdat = '/a.nc'\nhist_fincl1 = 'GPP', 'NPP'\nuse_fates_nocomp = .false.\n", "use_fates_nocomp", ".true.")
    t = nmlset(t, "hist_fincl1", ", ".join(f"'{x}'" for x in HISTORY))
    assert nmlget(t, "use_fates_nocomp") == ".true." and hist_fields(t) == HISTORY
    assert hist_fields(nmlset("hist_fincl1 = 'GPP',\n   'NPP'\n", "hist_fincl1", "'TLAI'")) != ["TLAI"]   # continuation caught
    raw = "".join(f"CLM_USRDAT.UNSET:{k} = old\n" for k in REQUIRED_STREAM if k not in ("datafiles", "datavars", "offset"))
    raw += "CLM_USRDAT.UNSET:datafiles = /x/IT-Tor_DATM_2008.nc, \\\n/x/IT-Tor_DATM_2009.nc\nCLM_USRDAT.UNSET:datavars = TBOT Sa_tbot, \\\nQBOT Sa_shum\n"
    paths = [f"/y/IT-Tor_DATM_{y}.nc" for y in range(FIRST, LAST)] + [str(F1)]
    out = stream_replace(raw, paths)
    assert "year_first = 2008" in out and "year_last = 2025" in out and str(F1) in out and "/x/" not in out and "QBOT Sa_shum" in out
    with tempfile.TemporaryDirectory() as d:
        d = Path(d); base, f1, bad = d / "IT-Tor_DATM_2025.nc", d / "IT-Tor_DATM_2025_F1.nc", d / "bad.nc"
        with Dataset(str(base), "w") as ds:
            ds.createDimension("time", 17520); ds.createDimension("lat", 1); ds.createDimension("lon", 1)
            for n, v in (("TBOT", 270.0), ("QBOT", 0.003), ("PSRF", 78957.0)): ds.createVariable(n, "f8", ("time", "lat", "lon"))[:] = v
        for out_path, idx in ((f1, (15197, 15198, 15199)), (bad, (15197, 15198, 15199, 100))):   # 2025-11-13 14:30-15:30
            shutil.copyfile(base, out_path)
            with Dataset(str(out_path), "r+") as ds:
                for i in idx: ds["TBOT"][i, 0, 0] = 280.0; ds["QBOT"][i, 0, 0] = 0.004
        m = {"status": "DETACHED_EXPLORATORY_NOT_RELEASED", "site": "IT-Tor", "baseline_path": str(base), "baseline_sha256": sha(base),
             "candidate_sha256": sha(f1), "changes": [{"time": x} for x in F1_TIMES]}
        f1_valid(f1, m, {"path": str(base), "sha256": sha(base)})
        try: f1_valid(bad, {**m, "candidate_sha256": sha(bad)}, {"path": str(base), "sha256": sha(base)}); raise AssertionError("extra change accepted")
        except RuntimeError: pass
        try: f1_valid(f1, {**m, "baseline_sha256": "0" * 64}, {"path": str(base), "sha256": sha(base)}); raise AssertionError("wrong baseline accepted")
        except RuntimeError: pass
    print("STAGE05E SELF-TEST PASS (namelist + history, DATM stream with F1 2025, F1 six-value guard; no HPC)")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("action", choices=("self-test", "check", "stage-f1", "prepare", "audit", "submit"))
    ap.add_argument("--confirm", default="")
    a = ap.parse_args()
    if a.action == "self-test": return self_test()
    if a.action == "check": preflight(show=True, need_inputs=False); print("STAGE05E CHECK PASS | READ ONLY"); return
    if a.action == "stage-f1": return stage_f1(a.confirm)
    if a.action == "prepare": return prepare(a.confirm)
    if a.action == "audit": audit(True); return
    if a.action == "submit": return submit(a.confirm)


if __name__ == "__main__":
    try: main()
    except RuntimeError as e: print("STAGE05E HOLD:", e, file=sys.stderr); sys.exit(2)
