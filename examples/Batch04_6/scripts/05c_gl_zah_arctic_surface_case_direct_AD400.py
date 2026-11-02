#!/usr/bin/env python3
"""Batch04 GL-ZaH: Arctic PFT point surface, isolated FIXNC direct AD400 case, one-time submit.

Same method as the three running Batch04 chains (DE-RuR_prepare_ad400.py / ES-Agu_prepare_ad400.py and 04e):
clone the original case with --keepexe, private FATES AD namelist overlay preview, FIXNC flags with
spinup_state=2, RESUBMIT 0 at prepare and 79 only at the one-time submit, crash-safe submission sentinel.

GL-ZaH specifics
  template   GL-ZaH_FATES_SPINUP500_11P (built, 26 annual DATM files 2000-2025, CO2 368.96 = NOAA 2000)
  surface    template point surface with ONLY PCT_NAT_PFT changed to the operator vector
             host 0 bare 43 | 9 evergreen shrub 53 | 11 deciduous boreal shrub 3 | 12 Arctic C3 grass 1
             (ICOS_Unassigned_6 six-site CSV, ACCEPTED_PROXY_WITH_PRIVATE_MAP); landunits, soil and point unchanged
  FATES      private candidate (sha pinned): host 9 -> broadleaf_evergreen_arctic_shrub,
             host 11 -> broadleaf_colddecid_arctic_shrub, host 12 -> arctic_c3_grass; identical to the shared
             default file everywhere else (checked)
Science: the Cassiope-heath plot is not a measured flux-footprint PFT fraction; soil is inherited from the grid.

Actions
  self-test                                                   no HPC, no files outside a temp dir
  check                                                       READ ONLY
  build-surface --confirm BUILD_GL_ZAH_B04_ARCTIC_SURFACE     new folder only
  prepare       --confirm PREPARE_GL_ZAH_B04_AD400_NO_SLURM   new case, no Slurm
  audit                                                       READ ONLY
  submit        --confirm SUBMIT_GL_ZAH_EXPLORATORY_DIRECT_AD400_80X5_ONCE
Never repeat prepare or submit after a ledger or submission receipt exists.
"""
import argparse, configparser, copy, hashlib, json, os, re, resource, shutil, socket, subprocess, sys, tempfile
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

B = Path("/iridisfs/scratch/ly3n24/CLM_FATES")
CTSM = B / "CTSM"
OUTPUT = Path("/scratch/ly3n24/CTSM_FATES_OUTPUTS")
TEMPLATE = B / "cases/GL-ZaH_FATES_SPINUP500_11P"
NAME = "GL-ZaH_ICOS_B04_FIXNC_AD400_DIRECT"
CASE = B / "cases" / NAME
RUN = OUTPUT / NAME / "run"
ARCH = OUTPUT / "archive" / NAME
EXP = B / "experiments/NonCompetitionObserved22/ICOS_Unassigned_6"
PARAM = EXP / "GL-ZaH_private_arctic_map_candidate_v1/fates_params_GL-ZaH_arctic_private_candidate.json"
PARAM_SHA = "56d9433f5915686b2877367124c39ee1f167d2c5c2cbc88cc5e190f53d31cd62"
SHARED_PARAM = CTSM / "src/fates/parameter_files/fates_params_default.json"
SHARED_PARAM_SHA = "0819f8fddcb3566f6209f72bb1159a3161d03c8225a1464727b1d2b21aec6c04"
SOURCE_SURF = B / "sites/MY_EC_SITE/GL-ZaH/subset_data/surfdata_GL-ZaH_hist_2000_16pfts_c261014.nc"
SOURCE_SURF_SHA = "ea0d9f04187e9d14cb0be91d55c39793bcccea266b4fae7cb116aa48400a5371"
SURF_DIR = EXP / "GL-ZaH_B04_arctic_PFT_surface_v1"
SURF = SURF_DIR / "GL-ZaH_B04_ARCTIC_PFT_POINT_CANDIDATE.nc"
SURF_MANIFEST = SURF_DIR / "manifest.json"
TARGET = {0: 43.0, 9: 53.0, 11: 3.0, 12: 1.0}
ARCTIC_ROWS = {9: "broadleaf_evergreen_arctic_shrub", 11: "broadleaf_colddecid_arctic_shrub", 12: "arctic_c3_grass"}
FIRST, LAST = 2000, 2025
CO2_2000 = 368.96
REPORTS = B / "experiments/Batch04_GL_ZaH_AD400_DIRECT_preparation"
LEDGER = REPORTS / "stage05c_prepare_state.json"
SUBMISSION = REPORTS / "stage05c_submission_attempt_PRIVATE.json"
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
ACK_SURF, ACK_PREP = "BUILD_GL_ZAH_B04_ARCTIC_SURFACE", "PREPARE_GL_ZAH_B04_AD400_NO_SLURM"
ACK_SUB = "SUBMIT_GL_ZAH_EXPLORATORY_DIRECT_AD400_80X5_ONCE"


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


# ------------------------------------------------------------------ inputs
def param_check():
    need(PARAM.is_file() and sha(PARAM) == PARAM_SHA, "Private GL parameter missing or sha differs")
    need(SHARED_PARAM.is_file() and sha(SHARED_PARAM) == SHARED_PARAM_SHA, "Shared default FATES parameter changed")
    cand, base = json.loads(PARAM.read_text()), json.loads(SHARED_PARAM.read_text())
    names = [str(x).strip() for x in cand["parameters"]["fates_pftname"]["data"]]
    m = cand["parameters"]["fates_hlm_pft_map"]["data"]
    for host, want in ARCTIC_ROWS.items():
        need(m[host - 1] == [1.0 if n == want else 0.0 for n in names], f"host {host} does not map only to {want}")
    other = copy.deepcopy(cand)
    for host in (9, 11): other["parameters"]["fates_hlm_pft_map"]["data"][host - 1] = base["parameters"]["fates_hlm_pft_map"]["data"][host - 1]
    need(other == base, "Private parameter differs from the shared default outside host rows 9 and 11")
    return {"param": str(PARAM), "param_sha256": PARAM_SHA, "rows": {h: n for h, n in ARCTIC_ROWS.items()}}


def read_surface(path):
    from netCDF4 import Dataset
    import numpy as np
    with Dataset(str(path)) as ds:
        g = lambda k: np.ma.asarray(ds.variables[k][:]).astype(float)
        land = {k: float(g(k).sum()) for k in ("PCT_NATVEG", "PCT_CROP", "PCT_LAKE", "PCT_WETLAND", "PCT_GLACIER", "PCT_URBAN") if k in ds.variables}
        pft = g("PCT_NAT_PFT").reshape(ds.variables["PCT_NAT_PFT"].shape[0], -1)[:, 0]
        return {"land": land, "pft": pft.tolist(), "lat": float(g("LATIXY").ravel()[0]), "lon": float(g("LONGXY").ravel()[0]),
                "organic": g("ORGANIC").ravel().tolist(), "sand": g("PCT_SAND").ravel().tolist(), "clay": g("PCT_CLAY").ravel().tolist()}


def make_surface(source, partial, target):
    """Copy source, change only PCT_NAT_PFT[:,0,0] to target, prove every other variable is unchanged."""
    from netCDF4 import Dataset
    import numpy as np
    need(not partial.exists(), "partial surface exists")
    shutil.copyfile(source, partial)
    with Dataset(str(partial), "r+") as ds:
        v = ds.variables["PCT_NAT_PFT"]; need(v.dimensions[0] == "natpft" and v.shape[0] == 15, "PCT_NAT_PFT is not natpft x 15")
        new = np.zeros(v.shape, dtype=v.dtype)
        for h, f in target.items(): new[h, ...] = f
        v[:] = new
        ds.setncattr("b04_gl_zah_pft_edit", f"PCT_NAT_PFT set to host {json.dumps({str(k): v for k, v in target.items()})}; source sha {sha(source)}; {utc()}")
    with Dataset(str(source)) as a, Dataset(str(partial)) as b:
        need(set(a.variables) == set(b.variables), "variable set changed")
        for k in a.variables:
            x, y = np.ma.asarray(a.variables[k][:]), np.ma.asarray(b.variables[k][:])
            if k == "PCT_NAT_PFT":
                want = np.zeros(x.shape); [want.__setitem__((h, ...), f) for h, f in target.items()]
                need(np.allclose(np.ma.filled(y, np.nan), want, atol=1e-9), "PCT_NAT_PFT not written as target")
            else:
                need(x.shape == y.shape and np.ma.allequal(x, y), "unexpected change in " + k)
    s = read_surface(partial)
    need(abs(s["land"].get("PCT_NATVEG", 0) - 100) < 1e-9 and all(abs(s["land"].get(k, 0)) < 1e-9 for k in
         ("PCT_CROP", "PCT_LAKE", "PCT_WETLAND", "PCT_GLACIER", "PCT_URBAN")), f"landunits not NATVEG 100: {s['land']}")
    need(abs(sum(s["pft"]) - 100) < 1e-9, "PCT_NAT_PFT does not sum to 100")
    return s


def surface_state():
    """(path, sha) of the verified built surface, or (None, None) if it has not been built."""
    if not SURF_DIR.exists(): return None, None
    need(SURF.is_file() and SURF_MANIFEST.is_file() and not SURF_DIR.is_symlink(), "GL surface folder incomplete: inspect " + str(SURF_DIR))
    r = json.loads(SURF_MANIFEST.read_text())
    need(r.get("surface_sha256") == sha(SURF) and r.get("source_sha256") == SOURCE_SURF_SHA, "GL surface manifest sha mismatch")
    s = read_surface(SURF)
    need(all(abs(s["pft"][h] - TARGET.get(h, 0.0)) < 1e-9 for h in range(15)), "built surface PFT is not the target")
    return SURF, r["surface_sha256"]


def build_surface(confirm):
    need(confirm == ACK_SURF, "requires --confirm " + ACK_SURF)
    p, h = surface_state()
    if p: print("GL SURFACE EXISTS AND VERIFIED", p, h); return
    need(SOURCE_SURF.is_file() and sha(SOURCE_SURF) == SOURCE_SURF_SHA, "Template surface missing or sha differs")
    tmp = SURF_DIR.with_name(SURF_DIR.name + ".partial")
    need(not tmp.exists(), "leftover " + str(tmp) + "; inspect")
    tmp.mkdir(parents=True)
    s = make_surface(SOURCE_SURF, tmp / SURF.name, TARGET)
    (tmp / "manifest.json").write_text(json.dumps({"site": "GL-ZaH", "status": "EXPLORATORY_FIXNC_SURFACE_NOT_SCIENCE_RELEASE",
        "source": str(SOURCE_SURF), "source_sha256": SOURCE_SURF_SHA, "surface": str(SURF), "surface_sha256": sha(tmp / SURF.name),
        "host_PCT_NAT_PFT": {str(k): v for k, v in TARGET.items()}, "changed_variables": ["PCT_NAT_PFT"], "point": [s["lat"], s["lon"]],
        "soil_inherited_from_grid": True, "basis": "ICOS_Unassigned_6 six-site CSV ACCEPTED_PROXY_WITH_PRIVATE_MAP",
        "created_utc": utc()}, indent=2) + "\n")
    need(sha(SOURCE_SURF) == SOURCE_SURF_SHA, "template surface changed during build")
    tmp.rename(SURF_DIR)
    print("GL SURFACE BUILT", SURF, sha(SURF), "| only PCT_NAT_PFT changed:", TARGET)


def datm_files():
    files, st = parse_stream(TEMPLATE)
    years = []
    for f in files:
        m = re.search(r"_DATM_(\d{4})", Path(f).name); need(m is not None, "unexpected DATM file " + f); years.append(int(m.group(1)))
    need(years == list(range(FIRST, LAST + 1)), f"template DATM years {years[:1]}..{years[-1:]} n={len(years)}")
    need(all(Path(f).is_file() and not Path(f).is_symlink() for f in files), "template DATM file missing")
    need(st.get("taxmode") == "cycle", "template stream not cycle")
    return [Path(f) for f in files]


def overlay():
    x = [p for p in OVERLAYS if all((p / f).is_file() for f in ("bld/CLMBuildNamelist.pm", "bld/build-namelist"))]
    need(x, "NO_VALID_PRIVATE_FATES_AD_NAMELIST_OVERLAY; do NOT clone"); return x[0]


def preflight(show=True, need_surface=True):
    for key, want in (("BUILD_COMPLETE", "TRUE"), ("DATM_MODE", "1PT"), ("CALENDAR", "NO_LEAP"), ("ATM_NCPL", "48"),
                      ("CLM_USRDAT_NAME", "UNSET"), ("RESUBMIT", "0"), ("CLM_CO2_TYPE", "constant")):
        need(xq(TEMPLATE, key).upper() == want.upper(), f"template {key} = {xq(TEMPLATE, key)}, expected {want}")
    need(abs(float(xq(TEMPLATE, "CCSM_CO2_PPMV")) - CO2_2000) < 0.005, "template CO2 is not the NOAA 2000 value")
    need(xq(TEMPLATE, "CLM_BLDNML_OPTS").split() == "--bgc fates --no-megan --no-drydep --no-fire_emis".split(), "template BGC options")
    exe = Path(xq(TEMPLATE, "EXEROOT")) / "cesm.exe"; need(exe.is_file(), "shared executable missing")
    need((CTSM / "cime/scripts/create_clone").is_file(), "create_clone missing")
    lnd = (TEMPLATE / "CaseDocs/lnd_in").read_text()
    need(nmlget(lnd, "fsurdat") == str(SOURCE_SURF), "template fsurdat is not the pinned GL surface")
    need(sha(SOURCE_SURF) == SOURCE_SURF_SHA, "template surface sha changed")
    par = param_check()
    files = datm_files()
    surf, surf_sha = surface_state()
    if need_surface: need(surf is not None, "GL surface not built: run build-surface first")
    s = read_surface(surf or SOURCE_SURF)
    pts = (float(xq(TEMPLATE, "PTS_LAT")), float(xq(TEMPLATE, "PTS_LON")))
    need(abs(s["lat"] - pts[0]) < 0.01 and abs((s["lon"] - pts[1] + 180) % 360 - 180) < 0.01, f"surface point {s['lat']},{s['lon']} != PTS {pts}")
    ov = overlay()
    land = (TEMPLATE / "user_nl_clm").read_text()
    need(nmlget(land, "reseed_dead_plants") is None, "template user_nl_clm has reseed_dead_plants")
    land = nmlset(land, "fsurdat", f"'{SURF}'")
    land = nmlset(land, "fates_paramfile", f"'{PARAM}'")
    for k, v in FLAGS.items(): land = nmlset(land, k, v)
    land = nmlset(land, "finidat", "''")
    land = nmlset(land, "hist_fincl1", ", ".join(f"'{x}'" for x in HISTORY))
    stream = stream_replace((TEMPLATE / "user_nl_datm_streams").read_text(), files)
    for p in (CASE, RUN, ARCH):
        if p.exists() or p.is_symlink(): need(LEDGER.is_file(), "new case/run/archive exists without ledger: " + str(p))
    ctx = {"files": [str(f) for f in files], "surface": str(SURF), "surface_sha256": surf_sha, "exe": str(exe), "overlay": str(ov),
           "land": land, "stream": stream, **par}
    if show:
        print("STAGE05C PREFLIGHT PASS | GL-ZaH | SCIENCE HOLD (proxy PFT, inherited soil)")
        print(f"  template {TEMPLATE.name} | exe {exe} | overlay {ov}")
        print(f"  DATM {len(files)} files {FIRST}-{LAST} in {files[0].parent} | CO2 {xq(TEMPLATE, 'CCSM_CO2_PPMV')} (NOAA 2000)")
        print(f"  private FATES {PARAM.name} sha {PARAM_SHA[:12]} rows {ARCTIC_ROWS}")
        print(f"  surface {'BUILT ' + str(SURF) + ' sha ' + surf_sha[:12] if surf else 'NOT BUILT (build-surface writes ' + str(SURF) + ')'}")
        print(f"  target host PCT_NAT_PFT {TARGET} | current {[round(x, 3) for x in s['pft']]}")
        print(f"  landunits {s['land']} | point {s['lat']:.4f},{s['lon']:.4f} | PTS {pts}")
        print(f"  soil inherited: sand {s['sand']} clay {s['clay']} ORGANIC {[round(x, 2) for x in s['organic']]}")
        print(f"  case {NAME} {FIRST}->{FIRST + 400} | STOP_N 5, prepare RESUBMIT 0, submit sets 79 | ledger {'EXISTS' if LEDGER.is_file() else 'none'}")
        keys = sorted({m.group(1) for m in re.finditer(r"(?m)^\s*([A-Za-z_]\w*)\s*=", (TEMPLATE / 'user_nl_clm').read_text())})
        print("  template user_nl_clm keys:", keys)
    return ctx


def verify(c):
    for k, v in SETTINGS.items():
        got = xq(CASE, k); need(got.lower() == v.lower(), "NEW CASE XML mismatch " + k + ": " + got)
    need(xq(CASE, "CASE") == NAME, "case identity")
    need(abs(float(xq(CASE, "CCSM_CO2_PPMV")) - CO2_2000) < 0.005 and xq(CASE, "CLM_CO2_TYPE") == "constant", "CO2 changed")
    need(Path(xq(CASE, "EXEROOT")).resolve() == Path(c["exe"]).parent.resolve(), "EXEROOT changed")
    doc = CASE / "CaseDocs/lnd_in"; need(doc.is_file(), "CaseDocs/lnd_in missing")
    text = doc.read_text()
    for k, v in {**FLAGS, "fsurdat": c["surface"], "fates_paramfile": c["param"], "finidat": ""}.items():
        need(nmlget(text, k) == v, "Effective lnd_in mismatch " + k + "=" + str(nmlget(text, k)))
    hist = re.search(r"(?ims)^\s*hist_fincl1\s*=\s*(.*?)(?=^[ \t]*[A-Za-z_]\w*[ \t]*=|^[ \t]*/[ \t]*$|\Z)", text)
    need(hist is not None and re.findall(r"['\"]([^'\"]+)['\"]", hist.group(1)) == HISTORY, "Wrong history fields")
    need((RUN / "lnd_in").is_file() and sha(RUN / "lnd_in") == sha(doc), "RUNDIR lnd_in differs from CaseDocs")
    files, st = parse_stream(CASE)
    need(files == c["files"], "CRITICAL: effective DATM stream is not the 26 template files")
    for k, v in {"year_first": str(FIRST), "year_last": str(LAST), "year_align": str(FIRST), "taxmode": "cycle", "offset": "0"}.items():
        need(st[k] == v, "DATM cycle mismatch " + k)
    need((RUN / "datm.streams.xml").is_file() and sha(RUN / "datm.streams.xml") == sha(CASE / "CaseDocs/datm.streams.xml"), "RUNDIR stream differs")
    need(sha(c["surface"]) == c["surface_sha256"] and sha(c["param"]) == c["param_sha256"], "surface or parameter drift")
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
        tmp = env.with_name("env_case.xml.gl_restore_tmp"); need(not tmp.exists(), "Unexpected restore file")
        with tmp.open("xb") as f: f.write(before); f.flush(); os.fsync(f.fileno())
        os.replace(tmp, env)
    need(env.read_bytes() == locked.read_bytes() == before, "env_case lock not restored after preview")
    rec = verify(c)
    rec.update({"phase": "PREPARED_VERIFIED_NOT_SUBMITTED", "template": str(TEMPLATE), "source_science_HOLD": True,
                "run_target": "DIRECT_AD400_80x5_NO_AD5", "PFT_surface": c["surface"], "PFT_surface_sha256": c["surface_sha256"],
                "FATES_param": c["param"], "FATES_param_sha256": c["param_sha256"], "host_PCT_NAT_PFT": {str(k): v for k, v in TARGET.items()},
                "datm_files": c["files"], "datm_sha256": {f: sha(f) for f in c["files"]}, "co2_ppmv": CO2_2000, "created_utc": utc(),
                "manual_science_decisions": ["Cassiope-heath plot is not a measured footprint PFT fraction",
                                             "inherited grid soil", "provisional dynamic-ZBOT forcing"]})
    with LEDGER.open("w") as f: json.dump(rec, f, indent=2); f.write("\n")
    print("STAGE05C VERIFIED NEW DIRECT AD400 CASE; NO SLURM", CASE)


def scheduler_clear():
    q = cmd(["squeue", "-h", "-u", os.environ.get("USER", "ly3n24"), "-o", "%i|%j|%T"], None, 100)
    need(not [s for s in q.splitlines() if NAME in s], "Slurm queue already has this case")
    h = cmd(["sacct", "-X", "-u", os.environ.get("USER", "ly3n24"), "-S", "2026-11-02", "--format=JobIDRaw,JobName%90,State",
             "--parsable2", "--noheader"], None, 100)
    need(not [s for s in h.splitlines() if NAME in s], "Slurm accounting already knows this case")


def audit(check_queue=True):
    need(LEDGER.is_file(), "no prepare ledger")
    need(not SUBMISSION.exists() and not SUBMISSION.is_symlink(), "submission receipt exists; never submit twice")
    obj = json.loads(LEDGER.read_text())
    need(obj.get("phase") == "PREPARED_VERIFIED_NOT_SUBMITTED" and obj.get("slurm_submitted") is False, "ledger phase " + str(obj.get("phase")))
    c = {"files": obj["datm_files"], "surface": obj["PFT_surface"], "surface_sha256": obj["PFT_surface_sha256"],
         "param": obj["FATES_param"], "param_sha256": obj["FATES_param_sha256"], "exe": str(Path(xq(TEMPLATE, "EXEROOT")) / "cesm.exe")}
    param_check()
    h = verify(c)
    need(h["lnd_in_sha256"] == obj["lnd_in_sha256"] and h["effective_stream_sha256"] == obj["effective_stream_sha256"], "case changed after prepare")
    for f, d in obj["datm_sha256"].items(): need(sha(f) == d, "DATM file changed " + f)
    need((CASE / "env_case.xml").read_bytes() == (CASE / "LockedFiles/env_case.xml").read_bytes(), "env_case lock error")
    cs = (CASE / "CaseStatus").read_text(errors="replace") if (CASE / "CaseStatus").is_file() else ""
    need(not re.search(r"case\.submit starting|case\.run starting", cs), "CaseStatus shows a prior submission")
    need("--skip-preview-namelist" in cmd([CASE / "case.submit", "--help"], CASE, 100, allowed=(0, 1, 2)), "case.submit lacks --skip-preview-namelist")
    if check_queue: scheduler_clear()
    print("STAGE05C AUDIT PASS | prepared, verified, never submitted |", CASE)
    return obj


def submit(confirm):
    need(confirm == ACK_SUB, "requires --confirm " + ACK_SUB)
    obj = audit(True)
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
    print(f"GL-ZaH EXPLORATORY DIRECT AD400 SUBMITTED | run {run[0]} | archive {arch[0]} | {FIRST}->{FIRST + 400} 80x5 | skip_pnl persisted {persisted}")


def self_test():
    import numpy as np
    from netCDF4 import Dataset
    assert sum(TARGET.values()) == 100 and set(TARGET) <= set(range(15)) and 400 // int(SETTINGS["STOP_N"]) - 1 == 79
    t = nmlset("  fsurdat = '/a.nc'\nuse_fates_nocomp = .false.\n", "use_fates_nocomp", ".true.")
    assert nmlget(t, "use_fates_nocomp") == ".true." and nmlget(nmlset(t, "finidat", "''"), "finidat") == ""
    raw = "".join(f"CLM_USRDAT.UNSET:{k} = old\n" for k in REQUIRED_STREAM if k not in ("datafiles", "datavars", "offset"))
    raw += "CLM_USRDAT.UNSET:datafiles = /x/GL-ZaH_DATM_2000.nc, \\\n/x/GL-ZaH_DATM_2001.nc\nCLM_USRDAT.UNSET:datavars = TBOT Sa_tbot, \\\nQBOT Sa_shum\n"
    out = stream_replace(raw, [Path(f"/y/GL-ZaH_DATM_{y}.nc") for y in range(FIRST, LAST + 1)])
    assert "year_last = 2025" in out and "/y/GL-ZaH_DATM_2025.nc" in out and "/x/" not in out and "QBOT Sa_shum" in out and "offset = 0" in out
    with tempfile.TemporaryDirectory() as d:
        d = Path(d); src = d / "src.nc"
        with Dataset(str(src), "w") as ds:
            for n, k in (("lsmlat", 1), ("lsmlon", 1), ("natpft", 15), ("nlevsoi", 10), ("numurbl", 3)): ds.createDimension(n, k)
            for n, val in (("PCT_NATVEG", 100.0), ("PCT_CROP", 0.0), ("PCT_LAKE", 0.0), ("PCT_WETLAND", 0.0), ("PCT_GLACIER", 0.0),
                           ("LATIXY", 74.4733), ("LONGXY", 339.449)):
                ds.createVariable(n, "f8", ("lsmlat", "lsmlon"))[:] = val
            ds.createVariable("PCT_URBAN", "f8", ("numurbl", "lsmlat", "lsmlon"))[:] = 0.0
            p = ds.createVariable("PCT_NAT_PFT", "f8", ("natpft", "lsmlat", "lsmlon")); a = np.zeros((15, 1, 1)); a[0], a[11], a[12] = 74.4, 0.24, 25.36; p[:] = a
            for n in ("PCT_SAND", "PCT_CLAY", "ORGANIC"): ds.createVariable(n, "f8", ("nlevsoi", "lsmlat", "lsmlon"))[:] = 7.0
        s = make_surface(src, d / "new.nc", TARGET)
        assert [round(x, 9) for x in s["pft"]] == [TARGET.get(h, 0.0) for h in range(15)]
        try: make_surface(src, d / "new.nc", TARGET); raise AssertionError("overwrote an existing partial")
        except RuntimeError: pass
    print("STAGE05C SELF-TEST PASS (namelist, DATM stream rewrite, surface edit with whole-file diff; no HPC)")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("action", choices=("self-test", "check", "build-surface", "prepare", "audit", "submit"))
    ap.add_argument("--confirm", default="")
    a = ap.parse_args()
    if a.action == "self-test": return self_test()
    if a.action == "check": preflight(show=True, need_surface=False); print("STAGE05C CHECK PASS | READ ONLY"); return
    if a.action == "build-surface": return build_surface(a.confirm)
    if a.action == "prepare": return prepare(a.confirm)
    if a.action == "audit": audit(True); return
    if a.action == "submit": return submit(a.confirm)


if __name__ == "__main__":
    try: main()
    except RuntimeError as e: print("STAGE05C HOLD:", e, file=sys.stderr); sys.exit(2)
