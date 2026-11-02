#!/usr/bin/env python3
"""ICOS Batch04 (DE-Gri, DE-RuR, IT-Tor, ES-Agu): FIXNC direct AD400 80 x 5 from the already verified inputs.

User decision 2026-11-02: direct AD400 (one case.submit, STOP_N=5, RESUBMIT=79, no AD5 smoke), the protocol of
AmeriFlux Batch03/05 and ICOS Batch02 BE-Bra/CH-Lae. The residual source-science HOLDs listed in RESIDUAL are carried
into the ledger as accepted-for-this-run, not resolved. CH-Aws (RH source) and GL-ZaH (private Arctic FATES map) are
not part of this script.

Inputs (read only; verified by check and again by prepare)
  template  <site>_FATES_SPINUP1000_S30SHARED, create_clone --keepexe (ICOS Batch03 precedent; S30EXCL has RESUBMIT=199)
  surface   Stage02X GitHub-PFT point candidates, SHA verified 2026-11-01: NATVEG 100, CROP 0, approved PFT, soil inherited
  forcing   the template's own CLM_USRDAT annual DATM files = FLUXNET13 Stage28/29b/30 (Stage02V/03B: 22/15/18/19 years);
            DE-Gri 2011 and 2024 replaced by the operator-approved edits (Stage03U/V, 11 + 23 half-hours), copied
            SHA-verified from HOME to scratch at prepare
  FATES     template fates_paramfile, default map (host 13 -> cool_c3_grass, host 9 -> broadleaf_evergreen_extratrop_shrub)
  CO2       NOAA annual mean of the first forcing year (B3_01 table)
  history   TOTSOMC TOTSOMN TLAI FATES_GPP FATES_NPP TWS H2OSNO (Batch02 Stage43 histfix list)
  machinery AmeriFlux B3_01 (sha pinned): private FATES AD overlay preview, ledgers, stack guard, submit, audits

Stream window: year_first = year_align = first forcing year = RUN_STARTDATE year, taxmode cycle. Model year Y reads
forcing first + (Y - first) mod n, so DE-Gri reads the 2011 / 2024 edits at model years 2011 / 2024 (8th / 21st year)
and every 22 years after; the first 5-year segment reads 2004-2008.

Actions
  self-test                                   no HPC, no files
  check                                       READ ONLY
  prepare --confirm PREPARE_B04_FOUR_DIRECT_AD400_CASES_NO_SLURM
  submit  --confirm SUBMIT_B04_FOUR_DIRECT_AD400_80x5_ONCE
  status | audit-first5 | audit-ad400         READ ONLY
  quarantine-failed-prepare --sites .. --confirm QUARANTINE_B04_FAILED_PREPARE_NO_SLURM
Ledgers refuse duplicate stateful actions.
"""
import argparse, hashlib, importlib.util, json, re, shutil
import xml.etree.ElementTree as ET
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
B301 = HERE.parents[1] / "AmeriFlux_Batch03_10/scripts/B3_01_direct_AD400_FIXNC_80x5.py"
B301_SHA = "be9d43e74c5132c9cadd0503a9361657dec466512514ddf3a994ddaf2abbd863"


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""): h.update(b)
    return h.hexdigest()


if not B301.is_file() or sha(B301) != B301_SHA: raise SystemExit(f"need B3_01 (sha {B301_SHA[:12]}) at {B301}")
_s = importlib.util.spec_from_file_location("b301", B301); M = importlib.util.module_from_spec(_s); _s.loader.exec_module(M)

B = M.B
EXP = B / "experiments/NonCompetitionObserved22/Batch04_6"
D01 = EXP / "Stage04_direct_AD400"
SURF_DIR = B / "experiments/Batch04_GitHub_PFT_Gz7kLAkn"
GRI_PLAN = Path.home() / "ICOS_Batch04_gri_plan.RgXTDNHK/de_gri_input_plan_PRIVATE.json"
SITES = {"DE-Gri": (2004, 2025), "DE-RuR": (2011, 2025), "IT-Tor": (2008, 2025), "ES-Agu": (2006, 2024)}
ORDER = tuple(SITES)
SURF_SHA = {"DE-Gri": "08887d2daf5d529b5fed89ca21c8094e19dd471ff3387a758ce23b471211ed2b",
            "DE-RuR": "2a4685ae3a43323fcff829bd3fdb5d998d58b4e077923a991ee4afd727767414",
            "IT-Tor": "908b73f67f74333fa70fcd3b07d8500de14c70b4efdd1e6f36ea23bb4f8b7c7b",
            "ES-Agu": "067722b0dc1440abc2e6aef30ca443b04198f697f16e5ba70344e41f89638fa6"}
HOST = {"DE-Gri": {13: 100}, "DE-RuR": {13: 100}, "IT-Tor": {13: 100}, "ES-Agu": {0: 49, 9: 22, 13: 29}}
GRI_EDITS = {2011: "2b075626a3a995311e87dafdfd3ae062c55b3e89665c6ff3f3a5aa5ff001bc1c",
             2024: "eb0dcaaf9f47500d43f0ebd73e2637dd39c93ce1e4083a1dc365595c4f1a58ac"}
RESIDUAL = {"DE-Gri": "49 listed original MDS/QC1 blocks kept as source except the 2011/2024 edits; soil inherited from grid; source clock",
            "DE-RuR": "2012-07-27 rain accumulation clock; dated TA height (2.58 m first); soil and management inherited",
            "IT-Tor": "2025 Oct-Nov 1,458-HH MDS/ERA splice kept (Stage03N decision); all ten soil ORGANIC layers 0 (grid)",
            "ES-Agu": "2018-09-15 rain clock; bare 49 / shrub 22 / grass 29 cover denominator and biocrust; soil inherited"}
HISTORY = ("TOTSOMC", "TOTSOMN", "TLAI", "FATES_GPP", "FATES_NPP", "TWS", "H2OSNO")
BGC_OPTS = "--bgc fates --no-megan --no-drydep --no-fire_emis"
MPI = "srun --mpi=pmix --ntasks=1 --cpus-per-task=1 --cpu-bind=cores"
EXPECT_FATES = {9: "broadleaf_evergreen_extratrop_shrub", 13: "cool_c3_grass"}
STREAM = "CLM_USRDAT.UNSET"
ACK_P, ACK_SUB = "PREPARE_B04_FOUR_DIRECT_AD400_CASES_NO_SLURM", "SUBMIT_B04_FOUR_DIRECT_AD400_80x5_ONCE"
ACK_Q = "QUARANTINE_B04_FAILED_PREPARE_NO_SLURM"


def name(s): return f"{s}_B04_FIXNC_AD400_DIRECT"
def template(s): return B / "cases" / f"{s}_FATES_SPINUP1000_S30SHARED"
def surface(s): return SURF_DIR / f"{s}_B04_GITHUBPFT_POINT_CANDIDATE.nc"
def stage_dir(): return EXP / "DE-Gri" / "datm_approved_edits_b04_v1"


# point the pinned B3_01 machinery (case_dir, run_dir, arch_dir, ledger, submit, audits) at this cohort
M.name, M.D01, M.SACCT_START, M.surface = name, D01, "2026-11-02", surface


def pick(sites):
    if not sites: return ORDER
    bad = [s for s in sites if s not in SITES]
    if bad: M.fail("unknown sites " + ",".join(bad))
    return tuple(s for s in ORDER if s in sites)


def forcing_year(s, model_year):
    first, last = SITES[s]
    return first + (model_year - first) % (last - first + 1)


# ------------------------------------------------------------- pure text helpers (self-tested)
def by_year(s, files):
    out = {}
    for p in files:
        m = re.search(rf"{re.escape(s)}_DATM_(\d{{4}})", Path(p).name)
        if not m or int(m.group(1)) in out: M.fail(f"{s}: unexpected or duplicated DATM file {p}")
        out[int(m.group(1))] = Path(p)
    first, last = SITES[s]
    if sorted(out) != list(range(first, last + 1)):
        M.fail(f"{s}: DATM years {sorted(out)[:1]}..{sorted(out)[-1:]} n={len(out)}, expected {first}-{last}")
    return out


def stream_text(s, text, files):
    """Template user_nl_datm_streams with the CLM_USRDAT window and datafiles replaced; datavars kept."""
    first, last = SITES[s]
    rex = re.compile(r"(?m)^[ \t]*([A-Za-z][\w.-]*):([A-Za-z_]\w*)[ \t]*=")
    starts = list(rex.finditer(text)); found = {}
    for i, m in enumerate(starts):
        end = starts[i + 1].start() if i + 1 < len(starts) else len(text)
        found.setdefault(m.group(1) + ":" + m.group(2), []).append((m.start(), end))
    pre = STREAM + ":"
    repl = {"year_first": str(first), "year_last": str(last), "year_align": str(first), "offset": "0", "taxmode": "cycle",
            "tintalgo": "linear", "mapalgo": "none", "meshfile": "none", "datafiles": ",".join(str(p) for p in files)}
    for k in (*repl, "datavars"):
        c = len(found.get(pre + k, []))
        if c != 1 and not (k == "offset" and c == 0): M.fail(f"{s}: template stream key {k} count {c}")
    subs = [(found[pre + k][0][0], found[pre + k][0][1], f"{pre}{k} = {v}\n") for k, v in repl.items() if found.get(pre + k)]
    for a, b, v in sorted(subs, reverse=True): text = text[:a] + v + text[b:]
    if not found.get(pre + "offset"): text = text.rstrip() + f"\n{pre}offset = 0\n"
    leak = [o for o in ORDER if o != s and o in text]
    if leak: M.fail(f"{s}: other-site path in DATM streams {leak}")
    return text


def clm_text(s, text, param):
    if M.nml_get(text, "reseed_dead_plants") is not None: M.fail(s + ": template user_nl_clm has reseed_dead_plants")
    text = M.nml_del(text, "finidat")
    # drop any template hist_fincl1 including quoted continuation lines, then set the Stage43 list
    text = re.sub(r"(?im)^[ \t]*hist_fincl1[ \t]*=[^\n]*\n?(?:[ \t]*['\"][^\n]*\n?)*", "", text)
    for k, v in {"fsurdat": f"'{surface(s)}'", **M.FATES_FLAGS, "spinup_state": "2", "fates_paramfile": f"'{param}'",
                 "hist_fincl1": ",".join(f"'{x}'" for x in HISTORY)}.items():
        text = M.nml_set(text, k, v)
    leak = [o for o in ORDER if o != s and o in text]
    if leak: M.fail(f"{s}: other-site path in user_nl_clm {leak}")
    return text


def settings(s, co2):
    first, last = SITES[s]
    return {"RUN_TYPE": "startup", "RUN_STARTDATE": f"{first:04d}-01-01", "CONTINUE_RUN": "FALSE", "CLM_FORCE_COLDSTART": "on",
            "CLM_ACCELERATED_SPINUP": "on", "STOP_OPTION": "nyears", "STOP_N": str(M.SEG_YEARS), "REST_OPTION": "nyears",
            "REST_N": str(M.SEG_YEARS), "RESUBMIT": str(M.SEGMENTS - 1), "RESUBMIT_SETS_CONTINUE_RUN": "TRUE", "DOUT_S": "TRUE",
            "DATM_YR_START": str(first), "DATM_YR_END": str(last), "DATM_YR_ALIGN": str(first),
            "CLM_CO2_TYPE": "constant", "DATM_CO2_TSERIES": "none", "CCSM_CO2_PPMV": f"{co2:.2f}", "MPI_RUN_COMMAND": MPI,
            "RUNDIR": str(M.run_dir(s)), "DOUT_S_ROOT": str(M.arch_dir(s))}


# ------------------------------------------------------------- inputs on IRIDIS6
def stream_doc(case):
    st = {e.attrib.get("name"): e for e in ET.parse(case / "CaseDocs/datm.streams.xml").getroot().iter("stream_info")}
    if STREAM not in st: M.fail(f"{case.name}: no {STREAM} stream")
    m = st[STREAM]
    files = [Path((x.text or "").strip()) for x in m.find("datafiles")]
    pairs = {}
    for e in m.find("datavars"):
        a = (e.text or "").split()
        if len(a) != 2 or a[0] in pairs: M.fail(case.name + ": datavars malformed")
        pairs[a[0]] = a[1]
    return st, files, pairs


def fates_map(pf):
    if pf.suffix.lower() == ".json":
        return M._json_map(json.loads(pf.read_text()))
    from netCDF4 import Dataset, chartostring
    with Dataset(str(pf)) as nc:
        names = [str(x).strip() for x in chartostring(nc.variables["fates_pftname"][:])]
        m = np.asarray(nc.variables["fates_hlm_pft_map"][:], float)
    if names != M.FATES_NAMES: M.fail(f"{pf.name}: FATES pft names differ")
    return m if np.allclose(m, M.DEFAULT14) else m.T


def template_check(s, co2):
    t = template(s)
    if not t.is_dir(): M.fail(f"missing template {t}")
    for k, want in (("BUILD_COMPLETE", "TRUE"), ("DATM_MODE", "1PT"), ("CALENDAR", "NO_LEAP"), ("ATM_NCPL", "48"),
                    ("RESUBMIT", "0"), ("CLM_USRDAT_NAME", "UNSET")):
        if M.xq(t, k).upper() != want: M.fail(f"template {k}={M.xq(t, k)} != {want}")
    if M.xq(t, "CLM_BLDNML_OPTS").split() != BGC_OPTS.split(): M.fail("template CLM_BLDNML_OPTS differs")
    if Path(M.xq(t, "COMP_ROOT_DIR_LND")).resolve() != M.CTSM.resolve(): M.fail("template land root is not the shared CTSM")
    for k in settings(s, co2): M.xq(t, k)   # every variable we will set exists in this CIME
    exe = Path(M.xq(t, "EXEROOT")) / "cesm.exe"
    if not exe.is_file(): M.fail("template executable missing " + str(exe))
    lnd = (t / "CaseDocs/lnd_in").read_text()
    if M.nml_get(lnd, "use_fates") != ".true.": M.fail("template is not a FATES case")
    pf = Path(M.nml_get(lnd, "fates_paramfile") or "")
    if not pf.is_file(): M.fail(f"template fates_paramfile missing {pf}")
    fm = fates_map(pf)
    if not np.allclose(fm, M.DEFAULT14): M.fail(f"{pf.name}: FATES map is not the default")
    for h in HOST[s]:
        if h and M.FATES_NAMES[int(np.argmax(fm[h - 1]))] != EXPECT_FATES[h]: M.fail(f"host {h} does not map to {EXPECT_FATES[h]}")
    for f in ("user_nl_clm", "user_nl_datm_streams", "LockedFiles/env_case.xml"):
        if not (t / f).is_file(): M.fail("template missing " + f)
    for f in ("bld/CLMBuildNamelist.pm", "bld/build-namelist"):
        if not (M.OVERLAY / f).is_file(): M.fail("private FATES AD overlay missing " + f)
    cs = (t / "CaseStatus").read_text(errors="replace") if (t / "CaseStatus").is_file() else ""
    return {"exe": exe, "exe_sha256": M.digest(exe), "paramfile": pf, "param_sha256": M.digest(pf),
            "start": M.xq(t, "RUN_STARTDATE"), "ran": bool(re.search(r"case\.run success", cs)),
            "pts": (float(M.xq(t, "PTS_LAT")), float(M.xq(t, "PTS_LON")))}


def surface_check(s, pts):
    p = surface(s)
    if not p.is_file() or M.digest(p) != SURF_SHA[s]: M.fail(f"surface missing or sha differs {p}")
    from netCDF4 import Dataset
    with Dataset(str(p)) as nc:
        g = lambda k: np.asarray(nc.variables[k][:], float)
        if abs(g("PCT_NATVEG").ravel()[0] - 100) > 1e-6 or abs(g("PCT_CROP").ravel()[0]) > 1e-6: M.fail("surface NATVEG/CROP")
        for k in M.LAND_OTHER:
            if k in nc.variables and abs(g(k).ravel()[0]) > 1e-6: M.fail(f"surface {k} != 0")
        v = g("PCT_NAT_PFT"); v = v.reshape(v.shape[0], -1)[:, 0]; want = np.zeros(len(v))
        for h, f in HOST[s].items(): want[h] = f
        if not np.allclose(v, want, atol=1e-6): M.fail(f"surface PCT_NAT_PFT {np.flatnonzero(v).tolist()} != approved {HOST[s]}")
        lat, lon = float(g("LATIXY").ravel()[0]), float(g("LONGXY").ravel()[0])
        org = g("ORGANIC")
    if abs(lat - pts[0]) > 0.01 or abs((lon - pts[1] + 180) % 360 - 180) > 0.01: M.fail(f"surface point {lat},{lon} != template PTS {pts}")
    return {"path": p, "sha256": SURF_SHA[s], "lat": lat, "lon": lon, "organic_min_max": [float(org.min()), float(org.max())]}


def gri_plan(tpl_years):
    plan = json.loads(GRI_PLAN.read_text())
    if plan.get("surface_sha256") != SURF_SHA["DE-Gri"]: M.fail("DE-Gri plan surface sha differs")
    rows = {int(r["year"]): r for r in plan["annual_inputs"]}
    if sorted(rows) != list(range(2004, 2026)): M.fail("DE-Gri plan years")
    src = {}
    for y, r in rows.items():
        p = Path(r["path"])
        if y in GRI_EDITS:
            if r["kind"] != "approved_sensitivity" or r["sha256"] != GRI_EDITS[y]: M.fail(f"DE-Gri {y}: plan edit row changed")
            src[y] = p
        elif r["kind"] != "historical_baseline" or p != tpl_years[y]: M.fail(f"DE-Gri {y}: plan path differs from template")
        if M.digest(p) != r["sha256"]: M.fail(f"DE-Gri {y}: file sha differs from plan")
    return src


def stage_edits(src, write):
    d = stage_dir(); rc = d / "RECEIPT.json"
    staged = {y: d / Path(src[y]).name for y in GRI_EDITS}
    if rc.is_file():
        for y, p in staged.items():
            if M.digest(p) != GRI_EDITS[y]: M.fail(f"staged DE-Gri {y} sha differs")
        return staged, "reused"
    if not write: return staged, "will copy at prepare"
    if d.exists(): M.fail(f"partial {d}")
    tmp = d.with_name(d.name + ".partial"); shutil.rmtree(tmp, ignore_errors=True); tmp.mkdir(parents=True)
    for y in GRI_EDITS:
        shutil.copy2(src[y], tmp / Path(src[y]).name)
        if M.digest(tmp / Path(src[y]).name) != GRI_EDITS[y]: M.fail(f"copy of DE-Gri {y} sha differs")
    (tmp / "RECEIPT.json").write_text(json.dumps({"from": {y: str(p) for y, p in src.items()}, "sha256": GRI_EDITS,
                                                  "created_utc": M.utc()}, indent=2) + "\n")
    tmp.rename(d)
    return staged, "copied"


def context(sites, write=False):
    co2, co2src = co2_table()
    ctx = {"co2": co2, "co2_src": co2src, "site": {}}; held = {}
    for s in sites:
        print(f"\n=== {s}", flush=True)
        try:
            first, last = SITES[s]
            if first not in co2: M.fail(f"CO2 table lacks {first}")
            tpl = template_check(s, co2[first])
            srf = surface_check(s, tpl["pts"])
            st, tfiles, pairs = stream_doc(template(s))
            ty = by_year(s, tfiles)
            if len({p.parent for p in ty.values()}) != 1: M.fail("template DATM files are not in one directory")
            missing = [y for y, p in ty.items() if not p.is_file()]
            if missing: M.fail(f"template DATM files missing {missing}")
            years = dict(ty); edits = ""
            if s == "DE-Gri":
                src = gri_plan(ty); staged, how = stage_edits(src, write)
                years.update(staged); edits = f" | edits 2011/2024 -> {stage_dir()} ({how})"
            files = [years[y] for y in range(first, last + 1)]
            for k in (M.case_dir(s), M.OUT / name(s), M.arch_dir(s)):
                if (k.exists() or k.is_symlink()) and not M.load(M.ledger(s)): M.fail(f"unexpected existing {k}")
            smoke = [forcing_year(s, first + k) for k in range(M.SEG_YEARS)]
            print(f"  template {template(s).name} start={tpl['start']} ran={tpl['ran']} exe_sha={tpl['exe_sha256'][:12]} "
                  f"param={tpl['paramfile'].name} sha={tpl['param_sha256'][:12]}", flush=True)
            print(f"  surface  {srf['path'].name} sha={srf['sha256'][:12]} host={HOST[s]} point={srf['lat']:.4f},{srf['lon']:.4f} "
                  f"ORGANIC min/max={srf['organic_min_max']}", flush=True)
            print(f"  forcing  {first}-{last} n={len(files)} dir={next(iter(ty.values())).parent}{edits}", flush=True)
            print(f"  datavars {json.dumps(pairs, sort_keys=True)}", flush=True)
            print(f"  window   year_first=year_align={first} cycle {last - first + 1} y | first segment reads {smoke}"
                  + (" | 2011/2024 edits read at model years 2011/2024 (8th/21st), then every 22 y" if s == "DE-Gri" else ""), flush=True)
            print(f"  CO2      {co2[first]:.2f} ppm ({first}) | AD400 {first}->{first + 400} | case {name(s)}", flush=True)
            print(f"  residual {RESIDUAL[s]}", flush=True)
            ctx["site"][s] = {"tpl": tpl, "srf": srf, "files": files, "pairs": pairs, "streams": sorted(st)}
            print(f"  RESULT   {s} ADMITTED", flush=True)
        except Exception as e:
            held[s] = str(e); print(f"  RESULT   {s} HOLD {e}", flush=True)
    return ctx, held


def co2_table():
    vals = {}
    for ln in M.CO2_CSV.read_text().splitlines():
        p = [x.strip() for x in ln.split(",")]
        if len(p) >= 2 and p[0].isdigit(): vals[int(p[0])] = float(p[1])
    return vals, f"{M.CO2_CSV} sha256={M.digest(M.CO2_CSV)}"


def validate_case(s, c, param, co2, sets):
    case = M.case_dir(s); first, last = SITES[s]
    for k, v in sets.items():
        got = M.xq(case, k)
        if k == "CCSM_CO2_PPMV":
            if abs(float(got) - float(v)) > 1e-5: M.fail(f"{s}: XML {k}={got}")
        elif got.lower() != v.lower(): M.fail(f"{s}: XML {k}={got} expected {v}")
    if Path(M.xq(case, "EXEROOT")).resolve() != Path(M.xq(template(s), "EXEROOT")).resolve(): M.fail(s + ": EXEROOT differs")
    doc, run = case / "CaseDocs/lnd_in", M.run_dir(s) / "lnd_in"
    if not doc.is_file() or not run.is_file() or M.digest(doc) != M.digest(run): M.fail(s + ": lnd_in CaseDocs != RUNDIR")
    t = doc.read_text()
    for k, v in {**M.FATES_FLAGS, "spinup_state": "2", "fsurdat": str(surface(s)), "fates_paramfile": str(param)}.items():
        if M.nml_get(t, k) != v: M.fail(f"{s}: lnd_in {k}={M.nml_get(t, k)}")
    if M.nml_get(t, "finidat") not in (None, "", " "): M.fail(s + ": finidat set")
    hist = re.search(r"(?is)hist_fincl1\s*=(.*?)(?:\n\s*\w+\s*=|/)", t)
    if not hist or any(f"'{x}'" not in hist.group(1) for x in HISTORY): M.fail(s + ": hist_fincl1 lacks the Stage43 list")
    c2 = M.nml_get(t, "co2_ppmv")
    if c2 is not None and abs(float(c2) - co2) > 0.03: M.fail(f"{s}: co2_ppmv {c2}")
    new = {e.attrib.get("name"): e for e in ET.parse(case / "CaseDocs/datm.streams.xml").getroot().iter("stream_info")}
    old = {e.attrib.get("name"): e for e in ET.parse(template(s) / "CaseDocs/datm.streams.xml").getroot().iter("stream_info")}
    if set(new) != set(old): M.fail(s + ": DATM stream set differs from template")
    for k in set(new) - {STREAM}:
        if M.canon(new[k]) != M.canon(old[k]): M.fail(s + ": ancillary stream changed " + k)
    m = new[STREAM]
    for k, v in (("year_first", str(first)), ("year_last", str(last)), ("year_align", str(first)), ("offset", "0"),
                 ("taxmode", "cycle"), ("tintalgo", "linear"), ("mapalgo", "none"), ("meshfile", "none")):
        e = m.find(k)
        if e is None or (e.text or "").strip() != v: M.fail(f"{s}: stream {k}")
    _, files, pairs = stream_doc(case)
    if pairs != c["pairs"]: M.fail(f"{s}: datavars changed {pairs}")
    if files != [Path(p) for p in c["files"]]: M.fail(s + ": datafiles differ")
    return {"lnd_in_sha256": M.digest(doc), "datm_streams_sha256": M.digest(case / "CaseDocs/datm.streams.xml")}


def prepare_one(s, ctx):
    led = M.ledger(s)
    if led.exists(): M.fail(f"{s}: ledger exists ({M.load(led).get('phase')})")
    for p in (M.case_dir(s), M.OUT / name(s), M.arch_dir(s)):
        if p.exists() or p.is_symlink(): M.fail(f"{s}: path exists: {p}")
    if M.queued(name(s)) or M.sacct_name(name(s)): M.fail(s + ": jobs exist")
    c = ctx["site"][s]; first, last = SITES[s]; co2 = ctx["co2"][first]; param = c["tpl"]["paramfile"]
    t = template(s); sets = settings(s, co2)
    stream = stream_text(s, (t / "user_nl_datm_streams").read_text(), c["files"])
    land = clm_text(s, (t / "user_nl_clm").read_text(), param)
    forcing_sha = {str(p): M.digest(p) for p in c["files"]}
    M.save(led, {"site": s, "case": str(M.case_dir(s)), "phase": "PREPARE_ATTEMPTED_UNCERTAIN", "at": M.utc()})
    case = M.case_dir(s)
    M.cmd([M.CIMESCRIPTS / "create_clone", "--case", case, "--clone", t, "--keepexe"], cwd=M.CIMESCRIPTS, timeout=420)
    if M.xq(case, "CASE") != name(s): M.fail(s + ": clone identity")
    for k, v in sets.items(): M.xc(case, k, v)
    (case / "user_nl_datm_streams").write_text(stream); (case / "user_nl_clm").write_text(land)
    M.run_dir(s).mkdir(parents=True, exist_ok=True)
    if not (case / ".case.run").is_file(): M.cmd([case / "case.setup"], cwd=case, timeout=300)
    env, lock = case / "env_case.xml", case / "LockedFiles/env_case.xml"
    if not lock.is_file() or env.read_bytes() != lock.read_bytes(): M.fail(s + ": env_case lock inconsistent")
    orig = env.read_bytes()
    if Path(M.xq(case, "COMP_ROOT_DIR_LND")).resolve() != M.CTSM.resolve(): M.fail(s + ": land root is not shared CTSM")
    try:
        M.xc(case, "COMP_ROOT_DIR_LND", str(M.OVERLAY)); M.cmd([case / "preview_namelists"], cwd=case, timeout=600)
    finally:
        M.xc(case, "COMP_ROOT_DIR_LND", "$SRCROOT")
        if env.read_bytes() != orig or lock.read_bytes() != orig: M.fail(s + ": STOP env_case.xml lock not restored")
    h = validate_case(s, c, param, co2, sets)
    M.save(led, {"site": s, "case": str(case), "phase": "CASE_VERIFIED_NOT_SUBMITTED", "name": name(s), "start_year": first,
                 "forcing_years": [first, last], "ad400_target_year": first + 400, "surface": str(surface(s)),
                 "surface_sha256": SURF_SHA[s], "host_PCT_NAT_PFT": HOST[s], "PTS": c["tpl"]["pts"],
                 "organic_min_max": c["srf"]["organic_min_max"], "co2_ppmv": co2, "co2_source": ctx["co2_src"],
                 "fates_paramfile": str(param), "fates_paramfile_sha256": M.digest(param), "forcing_sha256": forcing_sha,
                 "de_gri_edits": {str(y): GRI_EDITS[y] for y in GRI_EDITS} if s == "DE-Gri" else None,
                 "history": list(HISTORY), "executable_sha256": c["tpl"]["exe_sha256"], "template": str(t), **h,
                 "residual_science_hold_accepted_for_run": RESIDUAL[s], "protocol": "DIRECT_AD400_80x5_RESUBMIT79_NO_AD5_SMOKE",
                 "user_decision": "2026-11-02 Batch04 direct AD400", "created_utc": M.utc()})
    print(f"{s} CASE VERIFIED {name(s)} start={first} CO2={co2:.2f} forcing {first}-{last} | NO SLURM", flush=True)


def submit_one(s, stack):
    obj = M.load(M.ledger(s))
    for p, h in (obj.get("forcing_sha256") or {}).items():
        if M.digest(p) != h: M.fail(f"{s}: forcing file changed after prepare {p}")
    M.submit_one(s, stack)


def self_test():
    assert set(SITES) == set(SURF_SHA) == set(HOST) == set(RESIDUAL)
    assert [last - first + 1 for first, last in SITES.values()] == [22, 15, 18, 19]
    for s, v in HOST.items(): assert sum(v.values()) == 100, s
    for h, f in EXPECT_FATES.items(): assert M.FATES_NAMES[int(np.argmax(M.DEFAULT14[h - 1]))] == f, h
    # stream window: DE-Gri edits read at model years 2011 / 2024, first segment 2004-2008, cycle 22
    assert [forcing_year("DE-Gri", 2004 + k) for k in range(5)] == [2004, 2005, 2006, 2007, 2008]
    assert forcing_year("DE-Gri", 2011) == 2011 and forcing_year("DE-Gri", 2024) == 2024 and forcing_year("DE-Gri", 2026) == 2004
    assert forcing_year("ES-Agu", 2006 + 19) == 2006
    # by_year: complete, gap, duplicate
    d = "/x/FLUXNET_13/DE-RuR/datm_annual"
    ok = by_year("DE-RuR", [f"{d}/DE-RuR_DATM_{y}_PROVISIONAL.nc" for y in range(2011, 2026)])
    assert sorted(ok) == list(range(2011, 2026))
    for bad in ([f"{d}/DE-RuR_DATM_{y}_PROVISIONAL.nc" for y in range(2011, 2025)],
                [f"{d}/DE-RuR_DATM_{y}_PROVISIONAL.nc" for y in list(range(2011, 2026)) + [2015]],
                [f"{d}/DE-Gri_DATM_{y}_PROVISIONAL.nc" for y in range(2011, 2026)]):
        try: by_year("DE-RuR", bad)
        except RuntimeError: continue
        raise AssertionError("by_year accepted a bad list")
    # template user_nl_datm_streams in the real multi-line layout
    old = [f"/s/FLUXNET_13/DE-Gri/datm_annual/DE-Gri_DATM_{y}_PROVISIONAL.nc" for y in range(2004, 2026)]
    tpl = ("CLM_USRDAT.UNSET:taxmode = cycle\nCLM_USRDAT.UNSET:tintalgo = linear\nCLM_USRDAT.UNSET:mapalgo = none\n"
           "CLM_USRDAT.UNSET:meshfile = none\nCLM_USRDAT.UNSET:year_first = 2004\nCLM_USRDAT.UNSET:year_last = 2025\n"
           "CLM_USRDAT.UNSET:year_align = 2004\nCLM_USRDAT.UNSET:datafiles = " + ", \\\n".join(old) + "\n"
           "CLM_USRDAT.UNSET:datavars = FSDS Faxa_swdn, \\\nFLDS Faxa_lwdn, \\\nZBOT Sa_z\n")
    new = list(old); new[7] = "/e/DE-Gri/datm_approved_edits_b04_v1/DE-Gri_2011_approved_sensitivity.nc"
    out = stream_text("DE-Gri", tpl, new)
    assert f"CLM_USRDAT.UNSET:datafiles = {','.join(new)}\n" in out and old[7] not in out
    assert "CLM_USRDAT.UNSET:datavars = FSDS Faxa_swdn, \\\nFLDS Faxa_lwdn, \\\nZBOT Sa_z" in out
    assert "CLM_USRDAT.UNSET:offset = 0" in out and "year_align = 2004" in out
    try: stream_text("DE-RuR", tpl, new); raise AssertionError("other-site leak accepted")
    except RuntimeError: pass
    # user_nl_clm: finidat removed, multi-line hist_fincl1 replaced, FATES flags set
    un = ("finidat = '/old/restart.nc'\nhist_fincl1 = 'GPP',\n   'NPP'\nhist_nhtfrq = 0\nuse_fates_nocomp = .false.\n")
    t = clm_text("IT-Tor", un, Path("/p/fates_params.json"))
    assert M.nml_get(t, "finidat") is None and "'NPP'" not in t and M.nml_get(t, "hist_nhtfrq") == "0"
    assert M.nml_get(t, "use_fates_nocomp") == ".true." and M.nml_get(t, "spinup_state") == "2"
    assert "'FATES_GPP','FATES_NPP'" in t and str(surface("IT-Tor")) in t
    sets = settings("ES-Agu", 380.0)
    assert sets["RESUBMIT"] == "79" and sets["STOP_N"] == "5" and sets["DATM_YR_ALIGN"] == "2006" and sets["RUN_STARTDATE"] == "2006-01-01"
    assert name("DE-Gri") == "DE-Gri_B04_FIXNC_AD400_DIRECT" and str(M.ledger("IT-Tor")).startswith(str(D01))
    assert M.case_dir("ES-Agu").name == "ES-Agu_B04_FIXNC_AD400_DIRECT" and M.SEGMENTS * M.SEG_YEARS == 400
    print("B04 04a SELF-TEST PASS (cohort tables, FATES rows 9/13, stream window, DATM year list, user_nl rewrite, "
          "settings, B3_01 pinned; no files, no HPC)")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("action", choices=("self-test", "check", "prepare", "submit", "status", "audit-first5", "audit-ad400",
                                       "quarantine-failed-prepare"))
    ap.add_argument("--sites", nargs="+"); ap.add_argument("--confirm", default="")
    a = ap.parse_args(); sites = pick(a.sites)
    if a.action == "self-test": return self_test()
    if a.action == "status": return M.status(sites)
    if a.action == "audit-first5":
        _, h = M.table("B04 DIRECT AD400 FIRST 5-YEAR AUDIT (read only)", sites, M.first5_one); raise SystemExit(2 if h else 0)
    if a.action == "audit-ad400":
        _, h = M.table("B04 DIRECT AD400 AUDIT (read only)", sites, M.ad400_one); raise SystemExit(2 if h else 0)
    if a.action == "quarantine-failed-prepare":
        if a.confirm != ACK_Q or not a.sites: M.fail("requires --sites and --confirm " + ACK_Q)
        return M.batch("QUARANTINE", sites, M.quarantine_one)
    if a.action == "check":
        _, h = context(sites, write=False)
        print(f"\nB04 04a CHECK", f"PASS {len(sites)}/{len(sites)}" if not h else f"HOLD {len(h)}: " + ",".join(h),
              "| READ ONLY, no files, no Slurm", flush=True)
        raise SystemExit(2 if h else 0)
    if a.action == "prepare":
        if a.confirm != ACK_P: M.fail("requires --confirm " + ACK_P)
        ctx, h = context(sites, write=True)
        if h: M.fail("preflight HOLD for " + ",".join(h) + "; use --sites with admitted sites only")
        return M.batch("PREPARE", sites, lambda s: prepare_one(s, ctx))
    if a.action == "submit":
        if a.confirm != ACK_SUB: M.fail("requires --confirm " + ACK_SUB)
        stack = M.stack_guard()
        return M.batch("SUBMIT", sites, lambda s: submit_one(s, stack))


if __name__ == "__main__":
    main()
