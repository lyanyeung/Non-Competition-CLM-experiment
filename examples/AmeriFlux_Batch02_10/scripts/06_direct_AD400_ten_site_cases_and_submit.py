#!/usr/bin/env python3
"""AmeriFlux Batch02 Stage06: ten FIXNC AD400 cases, DIRECT 80 x 5 years (no AD5 smoke).

Operator decision 26 Oct 2026: AmeriFlux Batch02 runs AD400 directly. One CIME
case per site, one case.submit, STOP_N=5, RESUBMIT=79. This is the same
mechanism that completed AD400 for AmeriFlux Batch01 (CA-Ca3, CA-LP1) and ICOS
Batch02 Stage43, with the Batch01 Stage21 stack guard.

Inputs (all read only):
  surfaces  EXP/<SITE>/surface/surfdata_<SITE>_FIXNC_PFT_soil10_stage02_v1.nc + .json
            (Stage02/05: NATVEG100, recommended PFT, L1-L10 soil)
  forcing   Stage95 215 annual NOLEAP NC (local standard time, interval-start labels,
            no ZBOT) in AmeriFlux_MultiSite_10_Batch02/reports/stage95_...
  clock     BIF UTC offset (Stage97/98); US-BZS / US-Ho1 have no BIF offset and use
            their time-zone standard offsets (AKST -9, EST -5; neighbours agree)
  ZBOT      earliest dated BIF TA_F height (Stage98); US-BZS 6.1 m and US-Ho1 29 m
            documented proxies (no BIF height); --zbot SITE=M overrides
  CO2       NOAA GML global annual mean of the first forcing year (as Batch01)
  template  CA-Ca3_AMF_FIXNC_AD400_UTC_V2_PTS_AD5 (AD400 audited PASS) via
            create_clone --keepexe; preview with the proven private FATES AD overlay
  FATES     DEFAULT14 sites pin the template's effective fates_paramfile;
            ARCTIC_PURE sites (US-BZS, US-EML, US-ICh, US-ICt) get a private copy
            with fates_hlm_pft_map host9->FATES10 and host11->FATES11 only

Forcing build (same method as Batch01 Stage14): records move from local standard
time to UTC by -UTC_OFFSET hours; the first records of each UTC year come from
the end of the previous forcing year, cyclically (the year before the first
year is the last year, which is exactly what the spin-up cycle sees); time
labels become interval midpoints; static ZBOT added. Values are not changed.

Actions
  self-test                  no files, no HPC
  check                      READ ONLY: every input, template, absence of new paths
  prepare  --confirm PREPARE_AMF_B02_TEN_DIRECT_AD400_CASES_NO_SLURM
                             per site: forcing, ARCTIC params, clone, preview,
                             validate. Writes ledgers; no Slurm.
  submit   --confirm SUBMIT_AMF_B02_DIRECT_AD400_80x5_ONCE
                             stack guard, then ONE case.submit per verified site
  status                     READ ONLY
  audit-first5               READ ONLY: first 5-year restart, spinup_state=2
  audit-ad400                READ ONLY: 80 run + 80 archive, restart Y+400
  quarantine-failed-prepare --sites ... --confirm QUARANTINE_AMF_B02_FAILED_PREPARE_NO_SLURM
                             move a partial case (never submitted) aside

Never rerun a stateful action after an attempt: ledgers refuse duplicates.
"""
from __future__ import annotations
import argparse, configparser, csv, hashlib, json, re, resource, shutil, subprocess, sys
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[3]
B = Path("/iridisfs/scratch/ly3n24/CLM_FATES")
CTSM = B / "CTSM"
CIMESCRIPTS = CTSM / "cime/scripts"
OUT = Path("/scratch/ly3n24/CTSM_FATES_OUTPUTS")
EXP = B / "experiments/NonCompetitionObserved22/AmeriFlux_Batch02_10"
D06 = EXP / "Stage06_direct_AD400"
SRC = B / "experiments/AmeriFlux_MultiSite_10_Batch02"
S95 = SRC / "reports/stage95_ten_site_122_user_approved_versioned_forcing_215NC_20261026T034516Z_f4afa348"
S98_GLOB = "stage98_batch02_BIF_date_precision_and_height_prehistory_*"
TEMPLATE = B / "cases/CA-Ca3_AMF_FIXNC_AD400_UTC_V2_PTS_AD5"
OVERLAY = B / "experiments/NonCompetitionObserved22/Batch01_10/_private_ctsm_FATES_AD400_namelist_overlay"
REGISTER = REPO / "examples/AmeriFlux_Batch02_10/data/AMF_BATCH02_10_PFT_SOIL_RECOMMENDATIONS_SOURCE_PINNED_20261026.csv"
CO2_URL = "https://gml.noaa.gov/webdata/ccgg/trends/co2/co2_annmean_gl.csv"
USER = "ly3n24"
SACCT_START = "2026-10-26"
MIN_STACK_KB = 65536
SEGMENTS = 80
SEG_YEARS = 5

SITES = {  # first, last forcing year (Stage95 / sites.tsv)
    "US-BZS": (2010, 2024), "US-CMW": (2001, 2021), "US-EML": (2008, 2023),
    "US-GLE": (2005, 2020), "US-Ha1": (1991, 2025), "US-Ho1": (1996, 2023),
    "US-Ho2": (1999, 2025), "US-Ho3": (2003, 2021), "US-ICh": (2007, 2025),
    "US-ICt": (2007, 2025)}
ORDER = tuple(SITES)
ARCTIC = ("US-BZS", "US-EML", "US-ICh", "US-ICt")
# Stage97/98 BIF offsets; BZS/Ho1 have none in their FULLSET BIF.
UTC_BIF = {"US-CMW": -7.0, "US-GLE": -7.0, "US-EML": -9.0, "US-ICh": -9.0, "US-ICt": -9.0,
           "US-Ha1": -5.0, "US-Ho2": -5.0, "US-Ho3": -5.0}
UTC_PROXY = {"US-BZS": (-9.0, "Alaska Standard Time; AmeriFlux data are local standard time; EML/ICh/ICt BIF -9"),
             "US-Ho1": (-5.0, "Eastern Standard Time; neighbouring US-Ho2/US-Ho3 BIF -5")}
ZBOT_PROXY = {"US-BZS": (6.1, "no BIF TA_F height; instruments ~20 ft (6.1 m) on the ~30 ft BZS tower, UAF Aurora 2022"),
              "US-Ho1": (29.0, "no BIF TA_F height; Howland main-tower fluxes measured at 29 m, Hollinger et al. 2004 GCB")}
MET = ("FLDS", "FSDS", "PRECTmms", "PSRF", "QBOT", "RH", "SHUM", "TBOT", "WIND")
FIELDS = {"PRECTmms": "Faxa_precn", "FSDS": "Faxa_swdn", "ZBOT": "Sa_z", "TBOT": "Sa_tbot",
          "WIND": "Sa_wind", "QBOT": "Sa_shum", "PSRF": "Sa_pbot", "FLDS": "Faxa_lwdn"}
FATES_FLAGS = {"use_fates": ".true.", "use_fates_sp": ".false.", "use_fates_fixed_biogeog": ".true.",
               "use_fates_nocomp": ".true.", "use_cn": ".false."}
# fates_hlm_pft_map stored rows = CLM host natpft 1..14, columns = FATES PFT 1..14
DEFAULT14 = np.zeros((14, 14))
for _h, _f in {1: 1, 2: 1, 3: 2, 4: 0, 5: 3, 6: 4, 7: 5, 8: 5, 9: 6, 10: 8, 12: 11, 13: 12, 14: 13}.items():
    DEFAULT14[_h - 1, _f] = 1.0
DEFAULT14[10, 8], DEFAULT14[10, 9], DEFAULT14[10, 10] = 0.1, 0.1, 0.8
ARCTIC_PURE = DEFAULT14.copy()
ARCTIC_PURE[8, :] = 0.0; ARCTIC_PURE[8, 9] = 1.0      # host 9 -> broadleaf_evergreen_arctic_shrub
ARCTIC_PURE[10, :] = 0.0; ARCTIC_PURE[10, 10] = 1.0   # host 11 -> broadleaf_colddecid_arctic_shrub
ACK_PREP = "PREPARE_AMF_B02_TEN_DIRECT_AD400_CASES_NO_SLURM"
ACK_SUB = "SUBMIT_AMF_B02_DIRECT_AD400_80x5_ONCE"
ACK_Q = "QUARANTINE_AMF_B02_FAILED_PREPARE_NO_SLURM"
POINTERS = ("clm2", "datm", "cpl")
RUN_RE = re.compile(r"Submitted job case\.run with id (\d+)")
ARCH_RE = re.compile(r"Submitted job case\.st_archive with id (\d+)")


def fail(s): raise RuntimeError(str(s))
def utc(): return datetime.now(timezone.utc).isoformat()
def stamp(y): return f"{y:04d}-01-01-00000"


def digest(p):
    h = hashlib.sha256()
    with Path(p).open("rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def cmd(argv, cwd=None, timeout=300):
    p = subprocess.run([str(a) for a in argv], cwd=cwd, capture_output=True, text=True, timeout=timeout)
    if p.returncode:
        fail(f"rc={p.returncode} {' '.join(map(str, argv))}\nOUT {p.stdout[-1500:]}\nERR {p.stderr[-1500:]}")
    return p.stdout


def xq(case, k): return cmd(["./xmlquery", k, "--value"], cwd=case, timeout=90).strip()
def xc(case, k, v): cmd([Path(case) / "xmlchange", f"{k}={v}"], cwd=case, timeout=90)


def nml_get(text, key):
    hits = re.findall(r"(?im)^\s*" + re.escape(key) + r"\s*=\s*([^\r\n!]*)", text)
    if len(hits) > 1: fail("duplicate namelist key " + key)
    return hits[0].strip().rstrip(",").strip().strip("'\"").strip() if hits else None


def nml_set(text, key, val):
    pat = r"(?im)^[ \t]*" + re.escape(key) + r"[ \t]*=[^\r\n]*$"
    hits = list(re.finditer(pat, text))
    if len(hits) > 1: fail("duplicate user_nl key " + key)
    line = f"{key} = {val}"
    if hits: return text[:hits[0].start()] + line + text[hits[0].end():]
    return text.rstrip() + "\n" + line + "\n"


def nml_del(text, key):
    return re.sub(r"(?im)^[ \t]*" + re.escape(key) + r"[ \t]*=[^\r\n]*\r?\n?", "", text)


def load(p): return json.loads(Path(p).read_text()) if Path(p).is_file() else {}
def save(p, obj):
    Path(p).parent.mkdir(parents=True, exist_ok=True)
    tmp = Path(str(p) + ".tmp"); tmp.write_text(json.dumps(obj, indent=2, default=str) + "\n"); tmp.replace(p)


def pick(sites):
    if not sites: return ORDER
    bad = [s for s in sites if s not in SITES]
    if bad: fail("unknown sites " + ",".join(bad))
    return tuple(s for s in ORDER if s in sites)


# ---------------------------------------------------------------- identities
def name(s): return f"{s}_AMF_B02_FIXNC_AD400_DIRECT"
def case_dir(s): return B / "cases" / name(s)
def run_dir(s): return OUT / name(s) / "run"
def arch_dir(s): return OUT / "archive" / name(s)
def ledger(s): return D06 / f"{s}_AD400_DIRECT_state.json"
def surface(s): return EXP / s / "surface" / f"surfdata_{s}_FIXNC_PFT_soil10_stage02_v1.nc"
def forcing_dir(s): return EXP / s / "forcing_UTC_midpoint_ZBOT_stage06_v1"
def arctic_param(s): return EXP / s / "fates_params_ARCTIC_PURE_stage06_v1.nc"


# ---------------------------------------------------------------- scheduler
def queued(n):
    out = cmd(["squeue", "-u", USER, "-h", "-o", "%i|%j|%T"], timeout=45)
    rows = [ln.split("|") for ln in out.splitlines() if len(ln.split("|")) >= 3]
    return [r for r in rows if r[1] in ("run." + n, "st_archive." + n)]


def sacct_name(n):
    out = cmd(["sacct", "-X", "-n", "-P", "-u", USER, "-S", SACCT_START, "--name", f"run.{n},st_archive.{n}",
               "--format=JobIDRaw,JobName%100,State,ExitCode"], timeout=90)
    rows = []
    for ln in out.splitlines():
        p = [x.strip() for x in ln.split("|")]
        if len(p) >= 4 and p[0].isdigit() and p[1] in ("run." + n, "st_archive." + n):
            rows.append((int(p[0]), p[1], p[2], p[3]))
    return rows


def stack_guard():
    soft, hard = resource.getrlimit(resource.RLIMIT_STACK)
    if soft != resource.RLIM_INFINITY and soft < MIN_STACK_KB * 1024:
        target = hard if hard == resource.RLIM_INFINITY or hard >= MIN_STACK_KB * 1024 else None
        if target is None: fail(f"stack hard limit {hard // 1024} KiB < {MIN_STACK_KB}; run `ulimit -s unlimited` first")
        resource.setrlimit(resource.RLIMIT_STACK, (target, hard))
        soft = target
    child = subprocess.run([sys.executable, "-c", "import resource;print(resource.getrlimit(resource.RLIMIT_STACK)[0])"],
                           capture_output=True, text=True, timeout=30, check=True)
    if int(child.stdout.strip()) != soft: fail("child process does not inherit the stack limit")
    try:
        cfg = cmd(["scontrol", "show", "config"], timeout=45)
        m = re.search(r"(?im)^\s*PropagateResourceLimits\s*=\s*(\S+)", cfg)
        prop = m.group(1) if m else ""
    except Exception as e:
        fail("cannot verify Slurm PropagateResourceLimits: " + str(e))
    if prop.upper() != "ALL" and "STACK" not in prop.upper().split(","):
        fail("Slurm PropagateResourceLimits does not include STACK: " + repr(prop))
    lab = "unlimited" if soft == resource.RLIM_INFINITY else f"{soft // 1024}KiB"
    print("STACK GUARD PASS soft=", lab, "PropagateResourceLimits=", prop, flush=True)
    return {"soft": lab, "propagate": prop}


# ---------------------------------------------------------------- inputs
def register():
    rows = {r["site"]: r for r in csv.DictReader(REGISTER.open(encoding="utf-8-sig"))}
    if set(rows) != set(SITES): fail("register site set changed")
    for s in SITES:
        prof = rows[s]["fates_mapping_profile"]
        if (prof == "ARCTIC_PURE") != (s in ARCTIC): fail(s + ": mapping profile " + prof)
    return rows


def surface_info(s, reg):
    from netCDF4 import Dataset
    p = surface(s); rec = Path(str(p)[:-3] + ".json")
    if not p.is_file() or not rec.is_file(): fail(s + ": Stage02/05 surface or receipt missing " + str(p))
    r = json.loads(rec.read_text())
    sh = digest(p)
    if r.get("surface_sha256") != sh or r.get("site") != s: fail(s + ": surface sha differs from its receipt")
    host = {int(k): float(v) for k, v in json.loads(reg["recommended_clm_host_PCT_NAT_PFT_json"]).items()}
    with Dataset(p) as ds:
        pft = np.ma.filled(ds.variables["PCT_NAT_PFT"][:], np.nan).ravel()
        lat = float(np.asarray(ds.variables["LATIXY"][:]).ravel()[0])
        lon = float(np.asarray(ds.variables["LONGXY"][:]).ravel()[0]) % 360
        natveg = float(np.asarray(ds.variables["PCT_NATVEG"][:]).ravel()[0])
    want = np.array([host.get(i, 0.0) for i in range(15)])
    if pft.size != 15 or not np.allclose(pft, want, atol=1e-4): fail(s + ": surface PCT_NAT_PFT differs from register")
    if abs(natveg - 100) > 1e-3: fail(s + ": PCT_NATVEG != 100")
    if s in ARCTIC and not any(host.get(i, 0) > 0 for i in (9, 11)): fail(s + ": ARCTIC site without host 9/11")
    if s not in ARCTIC and any(host.get(i, 0) > 0 for i in (9, 10, 11)): fail(s + ": DEFAULT14 site uses host 9/10/11")
    return {"path": p, "sha256": sh, "lat": lat, "lon": lon, "host": host}


def stage98():
    c = sorted(p for p in (SRC / "reports").glob(S98_GLOB) if (p / "manifest.json").is_file())
    if not c: fail("Stage98 height report not found under " + str(SRC / "reports"))
    rep = c[-1]
    rows = {r["site"]: r for r in csv.DictReader((rep / "10_site_height_history_decision_summary.csv").open(encoding="utf8"))}
    ev = json.loads((rep / "site_historical_height_evidence.json").read_text())
    return rep, rows, ev


def clock_and_height(s, s98, overrides):
    rep, rows, ev = s98
    row = rows.get(s) or fail(s + ": not in Stage98 summary")
    got = [float(x) for x in row.get("UTC_BIF_hours", "").split(",") if x.strip()]
    if s in UTC_BIF:
        if got != [UTC_BIF[s]]: fail(f"{s}: Stage98 UTC {got} != expected BIF {UTC_BIF[s]}")
        tz, tz_src = UTC_BIF[s], "BIF UTC_OFFSET (Stage97/98)"
    else:
        if got: fail(f"{s}: Stage98 now reports a BIF UTC {got}; update the proxy table")
        tz, tz_src = UTC_PROXY[s][0], "PROXY: " + UTC_PROXY[s][1]
    events = ev[s]["TA_and_WS_height_evidence"]["TA_F"]["exact_dated_height_events"]
    if s in overrides:
        z, z_src = overrides[s], "OPERATOR --zbot override"
    elif events:
        first = min(e["date_label"] for e in events)
        hs = sorted({float(e["height_m"]) for e in events if e["date_label"] == first})
        if len(hs) != 1: fail(f"{s}: conflicting earliest TA_F heights {hs}; pass --zbot {s}=M")
        z = hs[0]
        allh = sorted({float(e["height_m"]) for e in events})
        z_src = f"earliest dated BIF TA_F height ({first[:10]}); all BIF TA_F heights {allh}"
    elif s in ZBOT_PROXY:
        z, z_src = ZBOT_PROXY[s][0], "PROXY: " + ZBOT_PROXY[s][1]
    else:
        fail(f"{s}: no BIF TA_F height and no proxy; pass --zbot {s}=M")
    if not (1.0 <= z <= 150.0): fail(f"{s}: ZBOT {z} out of range")
    return {"utc_offset_h": tz, "utc_source": tz_src, "zbot_m": z, "zbot_source": z_src, "stage98_report": str(rep)}


def stage95_files(s, full_sha=False):
    m = json.loads((S95 / "manifest.json").read_text())
    rec = next((x for x in m.get("sites", []) if x.get("site") == s), None)
    if not rec or rec.get("NC_count") != SITES[s][1] - SITES[s][0] + 1: fail(s + ": Stage95 manifest site record incomplete")
    files = sorted(rec["NC_technical_preview_files"], key=lambda x: int(x["year"]))
    years = [int(x["year"]) for x in files]
    if years != list(range(SITES[s][0], SITES[s][1] + 1)): fail(s + ": Stage95 years " + str(years[:3]) + "...")
    check = files if full_sha else [files[0], files[-1]]
    for x in check:
        if digest(x["path"]) != x["sha256"]: fail(f"{s}: Stage95 NC sha changed {x['year']}")
    return [(int(x["year"]), Path(x["path"]), x["sha256"]) for x in files]


def read_source(path, year, srf):
    from netCDF4 import Dataset
    with Dataset(path) as ds:
        t = ds.variables["time"]
        tv = np.asarray(t[:], dtype=float)
        if getattr(t, "calendar", "") != "noleap" or getattr(t, "units", "") != f"days since {year}-01-01 00:00:00":
            fail(f"{path}: time units/calendar")
        n = tv.size
        if n not in (17520, 8760): fail(f"{path}: {n} records")
        step = 1440 // (n // 365)
        if not np.allclose(tv, np.arange(n) * step / 1440.0, atol=1e-9, rtol=0): fail(f"{path}: not interval-start labels")
        if "ZBOT" in ds.variables: fail(f"{path}: source already has ZBOT")
        lat = float(np.asarray(ds.variables["LATIXY"][:]).ravel()[0]); lon = float(np.asarray(ds.variables["LONGXY"][:]).ravel()[0]) % 360
        # mapalgo=none: DATM does not remap, so this is a provenance check (same tower), not a grid check.
        if abs(lat - srf["lat"]) > 0.01 or abs(((lon - srf["lon"]) + 180) % 360 - 180) > 0.01:
            fail(f"{path}: forcing point {lat:.5f},{lon:.5f} != surface point {srf['lat']:.5f},{srf['lon']:.5f}")
        data = {}
        for v in MET:
            var = ds.variables[v]
            if tuple(var.dimensions) != ("time", "lat", "lon"): fail(f"{path}: {v} dims {var.dimensions}")
            data[v] = (np.asarray(var[:], dtype=float), getattr(var, "units", ""))
        geo = {k: np.asarray(ds.variables[k][:], dtype=float) for k in ("lat", "lon", "LONGXY", "LATIXY")}
    for v, (a, _) in data.items():
        if not np.all(np.isfinite(a)): fail(f"{path}: non-finite {v}")
    return step, data, geo


def build_forcing(s, files, srf, ch):
    """UTC-midpoint + static ZBOT annual NC. Reuse a complete verified build."""
    from netCDF4 import Dataset
    d = forcing_dir(s); man = d / "manifest.json"
    first, last = SITES[s]
    if man.is_file():
        m = json.loads(man.read_text())
        if (m.get("complete") and m.get("utc_offset_h") == ch["utc_offset_h"] and m.get("zbot_m") == ch["zbot_m"]
                and [x["sha256"] for x in m["source"]] == [x[2] for x in files]
                and all(digest(x["path"]) == x["sha256"] for x in m["files"])):
            print(f"  {s}: forcing reused {d}", flush=True)
            return m
        fail(f"{s}: existing forcing build {d} differs; move it aside first")
    if d.exists(): fail(f"{s}: partial forcing folder {d}; move it aside first")
    tmp = d.with_name(d.name + ".partial"); shutil.rmtree(tmp, ignore_errors=True); tmp.mkdir(parents=True)
    src = {y: read_source(p, y, srf) for y, p, _ in files}
    steps = {v[0] for v in src.values()}
    if len(steps) != 1: fail(f"{s}: mixed time steps {steps}")
    step = steps.pop(); n = 525600 // step
    shift = int(round(-ch["utc_offset_h"] * 60 / step))
    if not (0 < shift < n) or abs(shift * step - (-ch["utc_offset_h"] * 60)) > 1e-6: fail(f"{s}: bad shift {shift}")
    out = []
    for y, p, _ in files:
        prev = last if y == first else y - 1
        _, today, geo = src[y]; _, before, _ = src[prev]
        q = tmp / f"{y}.nc"
        with Dataset(q, "w", format="NETCDF4_CLASSIC") as ds:
            ds.createDimension("time", n); ds.createDimension("lat", 1); ds.createDimension("lon", 1)
            t = ds.createVariable("time", "f8", ("time",))
            t.setncattr("units", f"days since {y}-01-01 00:00:00"); t.setncattr("calendar", "noleap")
            t.setncattr("long_name", f"UTC interval midpoint ({step} min); source local standard time shifted by {-ch['utc_offset_h']} h")
            t[:] = np.arange(n) * step / 1440.0 + step / 2880.0
            for k, dims in (("lat", ("lat",)), ("lon", ("lon",)), ("LONGXY", ("lat", "lon")), ("LATIXY", ("lat", "lon"))):
                v = ds.createVariable(k, "f8", dims); v[:] = geo[k]
            for k in MET:
                arr = np.concatenate([before[k][0][n - shift:], today[k][0][:n - shift]], axis=0)
                v = ds.createVariable(k, "f8", ("time", "lat", "lon"), zlib=True, complevel=2)
                v.setncattr("units", today[k][1]); v[:] = arr
            z = ds.createVariable("ZBOT", "f8", ("time", "lat", "lon"), zlib=True, complevel=2)
            z.setncattr("units", "m"); z.setncattr("long_name", "static TA_F sensor-height proxy: " + ch["zbot_source"])
            z[:] = np.full((n, 1, 1), ch["zbot_m"])
            for k, v in (("site_id", s), ("utc_offset_hours", ch["utc_offset_h"]), ("utc_source", ch["utc_source"]),
                         ("zbot_source", ch["zbot_source"]), ("source_nc", str(p)),
                         ("utc_year_start_policy", f"first {shift} records from forcing year {prev} (cyclic spin-up)"),
                         ("stage", "AmeriFlux Batch02 Stage06 direct AD400 forcing v1")):
                ds.setncattr(k, v)
        with Dataset(q) as ds:  # read back: exact values moved, nothing altered
            for k in MET:
                a = np.asarray(ds.variables[k][:], dtype=float)
                if not (np.array_equal(a[shift:], today[k][0][:n - shift]) and np.array_equal(a[:shift], before[k][0][n - shift:])):
                    fail(f"{s}: readback mismatch {y} {k}")
        out.append({"year": y, "path": str(d / q.name), "sha256": digest(q)})
    m = {"site": s, "complete": True, "step_minutes": step, "records_per_year": n, "shift_records": shift,
         "utc_offset_h": ch["utc_offset_h"], "utc_source": ch["utc_source"], "zbot_m": ch["zbot_m"],
         "zbot_source": ch["zbot_source"], "years": [first, last],
         "source": [{"year": y, "path": str(p), "sha256": h} for y, p, h in files], "files": out, "created_utc": utc()}
    (tmp / "manifest.json").write_text(json.dumps(m, indent=2) + "\n")
    tmp.rename(d)
    for x in out:
        if digest(x["path"]) != x["sha256"]: fail(f"{s}: forcing moved file sha")
    print(f"  {s}: forcing built {len(out)} years step={step}min shift={shift} ZBOT={ch['zbot_m']} -> {d}", flush=True)
    return m


def fates_map_matrix(ds):
    v = ds.variables["fates_hlm_pft_map"]
    a = np.asarray(v[:], dtype=float)
    dims = tuple(v.dimensions)
    if a.shape != (14, 14): fail("fates_hlm_pft_map shape " + str(a.shape))
    hlm_first = "hlm" in dims[0].lower()
    return v, (a if hlm_first else a.T), hlm_first


def build_arctic_param(s, base):
    from netCDF4 import Dataset
    p = arctic_param(s); rec = Path(str(p) + ".json")
    if p.is_file() and rec.is_file():
        r = json.loads(rec.read_text())
        if r.get("sha256") == digest(p) and r.get("base_sha256") == digest(base):
            with Dataset(p) as ds:
                if not np.allclose(fates_map_matrix(ds)[1], ARCTIC_PURE): fail(s + ": existing ARCTIC param map wrong")
            print(f"  {s}: ARCTIC_PURE param reused {p}", flush=True)
            return p
        fail(s + ": existing ARCTIC param/receipt mismatch; move aside")
    if p.exists(): fail(s + ": partial ARCTIC param " + str(p))
    with Dataset(base) as ds:
        if not np.allclose(fates_map_matrix(ds)[1], DEFAULT14): fail("template FATES map is not DEFAULT14; refuse")
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = Path(str(p) + ".partial"); shutil.copyfile(base, tmp)
    with Dataset(tmp, "r+") as ds:
        v, _, hlm_first = fates_map_matrix(ds)
        v[:] = ARCTIC_PURE if hlm_first else ARCTIC_PURE.T
        ds.setncattr("AMF_B02_stage06_map", "ARCTIC_PURE: host9->broadleaf_evergreen_arctic_shrub, host11->broadleaf_colddecid_arctic_shrub; all else DEFAULT14")
    with Dataset(tmp) as ds:
        if not np.allclose(fates_map_matrix(ds)[1], ARCTIC_PURE): fail(s + ": ARCTIC map write failed")
    tmp.rename(p)
    rec.write_text(json.dumps({"site": s, "path": str(p), "sha256": digest(p), "base": str(base), "base_sha256": digest(base),
                               "profile": "ARCTIC_PURE", "changed_rows_host": [9, 11], "created_utc": utc()}, indent=2) + "\n")
    print(f"  {s}: ARCTIC_PURE param built {p}", flush=True)
    return p


def co2_table(path=None):
    d = D06 / "co2_annmean_gl.csv"
    src = Path(path) if path else d
    if not src.is_file():
        import urllib.request
        d.parent.mkdir(parents=True, exist_ok=True)
        with urllib.request.urlopen(CO2_URL, timeout=60) as r: d.write_bytes(r.read())
        src = d
    vals = {}
    for ln in src.read_text().splitlines():
        p = [x.strip() for x in ln.split(",")]
        if len(p) >= 2 and p[0].isdigit():
            vals[int(p[0])] = float(p[1])
    if not vals or any(SITES[s][0] not in vals for s in SITES): fail("CO2 table lacks a first forcing year: " + str(src))
    return vals, str(src), digest(src)


def template_info():
    for k, want in (("BUILD_COMPLETE", "TRUE"), ("DATM_MODE", "1PT"), ("CALENDAR", "NO_LEAP"), ("ATM_NCPL", "48")):
        if xq(TEMPLATE, k).upper() != want: fail(f"template {k} != {want}")
    exe = Path(xq(TEMPLATE, "EXEROOT")) / "cesm.exe"
    if not exe.is_file(): fail("template executable missing " + str(exe))
    lnd = (TEMPLATE / "CaseDocs/lnd_in").read_text()
    for k, v in FATES_FLAGS.items():
        if nml_get(lnd, k) != v: fail(f"template lnd_in {k}={nml_get(lnd, k)}")
    if nml_get(lnd, "spinup_state") != "2": fail("template is not an AD case")
    pf = nml_get(lnd, "fates_paramfile")
    if not pf or not Path(pf).is_file(): fail("template fates_paramfile missing " + str(pf))
    for f in ("user_nl_clm", "user_nl_datm_streams", "LockedFiles/env_case.xml"):
        if not (TEMPLATE / f).is_file(): fail("template missing " + f)
    for f in ("bld/CLMBuildNamelist.pm", "bld/build-namelist"):
        if not (OVERLAY / f).is_file(): fail("private FATES AD overlay missing " + f)
    cs = (TEMPLATE / "CaseStatus").read_text(errors="replace") if (TEMPLATE / "CaseStatus").is_file() else ""
    if not re.search(r"case\.run success", cs): fail("template has no successful case.run")
    return {"exe": exe, "exe_sha256": digest(exe), "paramfile": Path(pf), "param_sha256": digest(pf),
            "hist_fincl1": re.findall(r"'([^']+)'", (lnd.split("hist_fincl1", 1) + [""])[1].split("\n", 1)[0])}


# ---------------------------------------------------------------- case
def stream_text(s, files, first, last):
    t = (TEMPLATE / "user_nl_datm_streams").read_text()
    rex = re.compile(r"(?m)^[ \t]*([A-Za-z][\w.-]*):([A-Za-z_]\w*)[ \t]*=")
    starts = list(rex.finditer(t)); found = {}
    for i, m in enumerate(starts):
        end = starts[i + 1].start() if i + 1 < len(starts) else len(t)
        found.setdefault(m.group(1) + ":" + m.group(2), []).append((m.start(), end))
    pre = "CLM_USRDAT.UNSET:"
    repl = {"year_first": str(first), "year_last": str(last), "year_align": str(first), "offset": "0",
            "taxmode": "cycle", "tintalgo": "linear", "mapalgo": "none", "meshfile": "none",
            "datafiles": ",".join(str(p) for p in files)}
    for k in (*repl, "datavars"):
        c = len(found.get(pre + k, []))
        if c != 1 and not (k == "offset" and c == 0): fail(f"template stream key {k} count {c}")
    subs = [(found[pre + k][0][0], found[pre + k][0][1], f"{pre}{k} = {v}\n") for k, v in repl.items() if found.get(pre + k)]
    for a, b, v in sorted(subs, reverse=True): t = t[:a] + v + t[b:]
    if not found.get(pre + "offset"): t = t.rstrip() + f"\n{pre}offset = 0\n"
    if "CA-Ca3" in t: fail("template site path leaked into DATM streams")
    return t


def clm_text(s, param):
    t = (TEMPLATE / "user_nl_clm").read_text()
    if nml_get(t, "reseed_dead_plants") is not None: fail("template user_nl_clm has reseed_dead_plants")
    t = nml_del(t, "finidat")
    for k, v in {"fsurdat": f"'{surface(s)}'", **FATES_FLAGS, "spinup_state": "2", "fates_paramfile": f"'{param}'"}.items():
        t = nml_set(t, k, v)
    if "CA-Ca3" in t: fail("template site path leaked into user_nl_clm")
    return t


def xml_settings(s, srf, co2):
    first, last = SITES[s]
    return {"RUN_TYPE": "startup", "RUN_STARTDATE": f"{first:04d}-01-01", "CONTINUE_RUN": "FALSE",
            "CLM_FORCE_COLDSTART": "on", "CLM_ACCELERATED_SPINUP": "on",
            "STOP_OPTION": "nyears", "STOP_N": str(SEG_YEARS), "REST_OPTION": "nyears", "REST_N": str(SEG_YEARS),
            "RESUBMIT": str(SEGMENTS - 1), "RESUBMIT_SETS_CONTINUE_RUN": "TRUE", "DOUT_S": "TRUE",
            "DATM_YR_START": str(first), "DATM_YR_END": str(last), "DATM_YR_ALIGN": str(first),
            "CLM_CO2_TYPE": "constant", "DATM_CO2_TSERIES": "none", "CCSM_CO2_PPMV": f"{co2:.2f}",
            "PTS_LAT": f"{srf['lat']:.6f}", "PTS_LON": f"{srf['lon']:.6f}", "PTS_DOMAINFILE": "UNSET",
            "RUNDIR": str(run_dir(s)), "DOUT_S_ROOT": str(arch_dir(s))}


def canon(e): return (e.tag, tuple(sorted(e.attrib.items())), (e.text or "").strip(), tuple(canon(k) for k in e))


def validate_case(s, srf, files, param, co2, settings):
    case = case_dir(s); first, last = SITES[s]
    for k, v in settings.items():
        got = xq(case, k)
        if k in ("PTS_LAT", "PTS_LON", "CCSM_CO2_PPMV"):
            if abs(float(got) - float(v)) > 1e-5: fail(f"{s}: XML {k}={got}")
        elif got.lower() != v.lower(): fail(f"{s}: XML {k}={got} expected {v}")
    if Path(xq(case, "EXEROOT")).resolve() != Path(xq(TEMPLATE, "EXEROOT")).resolve(): fail(s + ": EXEROOT differs from template")
    doc, run = case / "CaseDocs/lnd_in", run_dir(s) / "lnd_in"
    if not doc.is_file() or not run.is_file() or digest(doc) != digest(run): fail(s + ": lnd_in missing or CaseDocs != RUNDIR")
    t = doc.read_text()
    for k, v in {**FATES_FLAGS, "spinup_state": "2", "fsurdat": str(surface(s)), "fates_paramfile": str(param)}.items():
        if nml_get(t, k) != v: fail(f"{s}: lnd_in {k}={nml_get(t, k)}")
    if nml_get(t, "finidat") not in (None, "", " "): fail(s + ": lnd_in finidat " + str(nml_get(t, "finidat")))
    if nml_get(t, "reseed_dead_plants") is not None: fail(s + ": reseed_dead_plants present")
    c = nml_get(t, "co2_ppmv")
    if c is not None and abs(float(c) - co2) > 0.03: fail(f"{s}: lnd_in co2_ppmv {c}")
    new = {e.attrib.get("name"): e for e in ET.parse(case / "CaseDocs/datm.streams.xml").getroot().iter("stream_info")}
    old = {e.attrib.get("name"): e for e in ET.parse(TEMPLATE / "CaseDocs/datm.streams.xml").getroot().iter("stream_info")}
    if set(new) != set(old) or "CLM_USRDAT.UNSET" not in new: fail(s + ": DATM stream set differs from template")
    for k in set(new) - {"CLM_USRDAT.UNSET"}:
        if canon(new[k]) != canon(old[k]): fail(s + ": ancillary stream changed " + k)
    m = new["CLM_USRDAT.UNSET"]
    for k, v in (("year_first", str(first)), ("year_last", str(last)), ("year_align", str(first)), ("offset", "0"),
                 ("taxmode", "cycle"), ("tintalgo", "linear"), ("mapalgo", "none"), ("meshfile", "none")):
        e = m.find(k)
        if e is None or (e.text or "").strip() != v: fail(f"{s}: generated stream {k}")
    pairs = {}
    for e in m.find("datavars"):
        a = (e.text or "").split()
        if len(a) != 2 or a[0] in pairs: fail(s + ": datavars malformed")
        pairs[a[0]] = a[1]
    if pairs != FIELDS: fail(f"{s}: datavars {pairs}")
    if [Path((x.text or "").strip()) for x in m.find("datafiles")] != [Path(p) for p in files]: fail(s + ": datafiles differ")
    rc = case / "CaseDocs/nuopc.runconfig"
    if rc.is_file():
        txt = rc.read_text()
        for key, want in (("scol_lat", srf["lat"]), ("scol_lon", srf["lon"])):
            mm = re.search(r"(?m)^\s*" + key + r"\s*=\s*(\S+)", txt)
            if mm and float(mm.group(1)) >= -900 and abs((float(mm.group(1)) - want + 180) % 360 - 180) > 1e-4:
                fail(f"{s}: nuopc.runconfig {key}={mm.group(1)} != surface {want}")
    return {"lnd_in_sha256": digest(doc), "datm_streams_sha256": digest(case / "CaseDocs/datm.streams.xml")}


def prepare_one(s, ctx):
    led = ledger(s)
    if led.exists(): fail(f"{s}: ledger exists ({load(led).get('phase')}); no duplicate prepare")
    for p in (case_dir(s), OUT / name(s), arch_dir(s)):
        if p.exists() or p.is_symlink(): fail(f"{s}: path exists, no overwrite: {p}")
    if queued(name(s)) or sacct_name(name(s)): fail(s + ": jobs already exist for " + name(s))
    srf, ch, files = ctx["surface"][s], ctx["clock"][s], stage95_files(s, full_sha=True)
    fm = build_forcing(s, files, srf, ch)
    param = build_arctic_param(s, ctx["tpl"]["paramfile"]) if s in ARCTIC else ctx["tpl"]["paramfile"]
    co2 = ctx["co2"][SITES[s][0]]
    nc = [Path(x["path"]) for x in fm["files"]]
    stream, land, settings = stream_text(s, nc, *SITES[s]), clm_text(s, param), xml_settings(s, srf, co2)
    save(led, {"site": s, "case": str(case_dir(s)), "phase": "PREPARE_ATTEMPTED_UNCERTAIN", "at": utc()})
    case = case_dir(s)
    cmd([CIMESCRIPTS / "create_clone", "--case", case, "--clone", TEMPLATE, "--keepexe"], cwd=CIMESCRIPTS, timeout=420)
    if xq(case, "CASE") != name(s): fail(s + ": clone identity")
    for k, v in settings.items(): xc(case, k, v)
    (case / "user_nl_datm_streams").write_text(stream)
    (case / "user_nl_clm").write_text(land)
    run_dir(s).mkdir(parents=True, exist_ok=True)
    if not (case / ".case.run").is_file(): cmd([case / "case.setup"], cwd=case, timeout=300)
    env, lock = case / "env_case.xml", case / "LockedFiles/env_case.xml"
    if not lock.is_file() or env.read_bytes() != lock.read_bytes(): fail(s + ": env_case lock inconsistent before preview")
    original = env.read_bytes()
    if Path(xq(case, "COMP_ROOT_DIR_LND")).resolve() != CTSM.resolve(): fail(s + ": land root is not shared CTSM")
    try:
        xc(case, "COMP_ROOT_DIR_LND", str(OVERLAY))
        cmd([case / "preview_namelists"], cwd=case, timeout=600)
    finally:
        xc(case, "COMP_ROOT_DIR_LND", "$SRCROOT")
        if env.read_bytes() != original or lock.read_bytes() != original: fail(s + ": STOP env_case.xml lock not restored")
    h = validate_case(s, srf, nc, param, co2, settings)
    save(led, {"site": s, "case": str(case), "phase": "CASE_VERIFIED_NOT_SUBMITTED", "name": name(s),
               "start_year": SITES[s][0], "forcing_years": list(SITES[s]), "ad400_target_year": SITES[s][0] + 400,
               "surface": str(srf["path"]), "surface_sha256": srf["sha256"], "host_PCT_NAT_PFT": srf["host"],
               "PTS_LAT": srf["lat"], "PTS_LON": srf["lon"], "co2_ppmv": co2, "co2_source": ctx["co2_src"],
               "fates_profile": "ARCTIC_PURE" if s in ARCTIC else "DEFAULT14",
               "fates_paramfile": str(param), "fates_paramfile_sha256": digest(param), **ch,
               "forcing_manifest": str(forcing_dir(s) / "manifest.json"), "forcing_step_minutes": fm["step_minutes"],
               "executable_sha256": ctx["tpl"]["exe_sha256"], "template": str(TEMPLATE), **h,
               "protocol": "DIRECT_AD400_80x5_RESUBMIT79_NO_AD5_SMOKE", "created_utc": utc()})
    print(f"{s} CASE VERIFIED {name(s)} start={SITES[s][0]} CO2={co2:.2f} UTC{ch['utc_offset_h']:+g} ZBOT={ch['zbot_m']} "
          f"FATES={'ARCTIC_PURE' if s in ARCTIC else 'DEFAULT14'} | NO SLURM", flush=True)


def submit_one(s, stack):
    led = ledger(s); obj = load(led)
    if obj.get("phase") != "CASE_VERIFIED_NOT_SUBMITTED": fail(f"{s}: ledger phase {obj.get('phase')}")
    case = case_dir(s)
    cs = (case / "CaseStatus").read_text(errors="replace") if (case / "CaseStatus").is_file() else ""
    if re.search(r"case\.submit starting|case\.run starting", cs): fail(s + ": CaseStatus shows a submission")
    if queued(name(s)) or sacct_name(name(s)): fail(s + ": jobs exist")
    if digest(case / "CaseDocs/lnd_in") != obj["lnd_in_sha256"] or digest(case / "CaseDocs/datm.streams.xml") != obj["datm_streams_sha256"]:
        fail(s + ": CaseDocs changed after verification")
    if digest(obj["surface"]) != obj["surface_sha256"] or digest(obj["fates_paramfile"]) != obj["fates_paramfile_sha256"]:
        fail(s + ": surface or FATES param changed after verification")
    for k, v in (("RESUBMIT", str(SEGMENTS - 1)), ("STOP_N", "5"), ("CONTINUE_RUN", "false"), ("CLM_ACCELERATED_SPINUP", "on")):
        if xq(case, k).lower() != v.lower(): fail(f"{s}: {k}={xq(case, k)}")
    obj.update(phase="SUBMIT_ATTEMPTED_UNCERTAIN", submit_attempt_utc=utc(), stack=stack); save(led, obj)
    out = cmd([case / "case.submit", "--skip-preview-namelist"], cwd=case, timeout=650)
    r, a = RUN_RE.search(out), ARCH_RE.search(out)
    if not r or not a: fail(s + ": job IDs not parsed; DO NOT RETRY. " + out[-600:])
    obj.update(phase="AD400_SUBMITTED", first_run_job=r.group(1), first_archive_job=a.group(1), cime_submit_tail=out[-800:])
    save(led, obj)
    print(f"{s} AD400 DIRECT SUBMITTED {stamp(obj['start_year'])} -> {stamp(obj['ad400_target_year'])} (80x5, RESUBMIT=79) "
          f"run={r.group(1)} archive={a.group(1)}", flush=True)


# ---------------------------------------------------------------- audits
def restart_state(p):
    from netCDF4 import Dataset
    with Dataset(str(p)) as ds:
        if "spinup_state" in ds.variables: return int(np.asarray(ds.variables["spinup_state"][:]).ravel()[0])
        if "spinup_state" in ds.ncattrs(): return int(ds.getncattr("spinup_state"))
    return None


def triplet(s, y):
    f = arch_dir(s) / "rest" / stamp(y)
    files = {c: f / f"{name(s)}.{c}.r.{stamp(y)}.nc" for c in POINTERS}
    for c, p in files.items():
        if not p.is_file() or p.stat().st_size < 1024: fail(f"{s}: missing {p}")
    return files


def latest(s):
    r = arch_dir(s) / "rest"
    n = sorted(x.name for x in r.iterdir() if x.is_dir()) if r.is_dir() else []
    return (n[-1] if n else None), len(n)


def first5_one(s):
    obj = load(ledger(s))
    if obj.get("phase") != "AD400_SUBMITTED": fail(f"{s}: phase {obj.get('phase')}")
    rows = [r for r in sacct_name(name(s)) if r[0] >= int(obj["first_run_job"])]
    bad = [r for r in rows if r[2] not in ("COMPLETED", "RUNNING", "PENDING") or (r[2] == "COMPLETED" and r[3] != "0:0")]
    if bad: fail(f"{s}: failed jobs {bad[:4]}")
    y = obj["start_year"] + SEG_YEARS
    st = restart_state(triplet(s, y)["clm2"])
    if st != 2: fail(f"{s}: first-segment spinup_state={st}, expected 2")
    l, n = latest(s)
    return {"case": name(s), "final": stamp(y), "spinup_state": st, "latest": l, "rest_dirs": n,
            "runs": sum(r[1].startswith("run.") and r[2] == "COMPLETED" for r in rows)}


def ad400_one(s):
    obj = load(ledger(s))
    if obj.get("phase") != "AD400_SUBMITTED": fail(f"{s}: phase {obj.get('phase')}")
    n = name(s)
    if queued(n): fail(s + ": jobs still queued")
    rows = [r for r in sacct_name(n) if r[0] >= int(obj["first_run_job"])]
    bad = [r for r in rows if (r[2], r[3]) != ("COMPLETED", "0:0")]
    if bad: fail(f"{s}: non-COMPLETED jobs {bad[:4]}")
    runs = sum(r[1].startswith("run.") for r in rows); arcs = sum(r[1].startswith("st_archive.") for r in rows)
    if runs < SEGMENTS or arcs < SEGMENTS: fail(f"{s}: {runs} run / {arcs} archive COMPLETED; need {SEGMENTS}")
    if xq(case_dir(s), "RESUBMIT") != "0": fail(s + ": RESUBMIT not exhausted")
    y = obj["ad400_target_year"]; l, nd = latest(s)
    if l != stamp(y): fail(f"{s}: latest restart {l}, expected {stamp(y)}")
    files = triplet(s, y); st = restart_state(files["clm2"])
    if st != 2: fail(f"{s}: final spinup_state={st}")
    return {"case": n, "runs": runs, "archives": arcs, "final": stamp(y), "spinup_state": st, "rest_dirs": nd,
            "start_year": obj["start_year"], "files": {k: str(v) for k, v in files.items()}}


def status(sites):
    for s in sites:
        o = load(ledger(s))
        try: q = "; ".join("|".join(r) for r in queued(name(s))) or "-"
        except Exception: q = "scheduler unavailable"
        print(f"{s:7} PHASE={o.get('phase', '-')} run={o.get('first_run_job', '-')} latest={latest(s)[0]} QUEUE={q}")


def table(title, sites, fn):
    ok, held = {}, {}
    print(title)
    for s in sites:
        try:
            r = fn(s); ok[s] = r
            print(f"  PASS {s:7} " + " ".join(f"{k}={r[k]}" for k in ("case", "runs", "archives", "final", "spinup_state", "latest", "rest_dirs") if k in r))
        except Exception as e:
            held[s] = str(e); print(f"  HOLD {s:7} {str(e)[-400:]}")
    print(f"SUMMARY pass={len(ok)} hold={len(held)}", ("HOLD: " + ",".join(held)) if held else "")
    return ok, held


def batch(label, sites, fn):
    bad = []
    for s in sites:
        try: fn(s)
        except Exception as e:
            print(s, label, "HOLD - DO NOT RETRY BLINDLY:", str(e)[-1500:], flush=True); bad.append(s)
    print(label, "SUMMARY ok=", len(sites) - len(bad), "hold=", bad, flush=True)
    if bad: raise SystemExit(2)


def quarantine_one(s):
    o = load(ledger(s))
    if o.get("phase") != "PREPARE_ATTEMPTED_UNCERTAIN": fail(f"{s}: phase {o.get('phase')}; only failed prepares")
    if queued(name(s)) or sacct_name(name(s)): fail(s + ": Slurm knows this case; refuse")
    cs = (case_dir(s) / "CaseStatus").read_text(errors="replace") if (case_dir(s) / "CaseStatus").is_file() else ""
    if re.search(r"case\.submit|case\.run", cs): fail(s + ": CaseStatus shows submission")
    q = D06 / "quarantine_failed_prepare" / f"{s}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    q.mkdir(parents=True); moved = {}
    for label, p in (("case", case_dir(s)), ("run_parent", OUT / name(s)), ("ledger", ledger(s))):
        if p.exists(): shutil.move(str(p), str(q / label)); moved[label] = str(p)
    (q / "RECEIPT.json").write_text(json.dumps({"site": s, "moved": moved, "utc": utc()}, indent=2) + "\n")
    print(f"  {s}: quarantined to {q} (forcing and ARCTIC param kept; they are reused if verified)")


# ---------------------------------------------------------------- context
def context(sites, args, full=False):
    reg = register()
    tpl = template_info()
    print(f"TEMPLATE PASS {TEMPLATE.name} exe={tpl['exe']} fates_paramfile={tpl['paramfile']} sha={tpl['param_sha256'][:12]}")
    print("TEMPLATE hist_fincl1:", ",".join(tpl["hist_fincl1"]))
    co2, co2_src, co2_sha = co2_table(args.co2_csv)
    s98 = stage98(); print("STAGE98", s98[0])
    over = {}
    for z in args.zbot or []:
        k, v = z.split("="); over[k] = float(v)
    ctx = {"tpl": tpl, "co2": co2, "co2_src": f"{co2_src} sha256={co2_sha}", "surface": {}, "clock": {}}
    held = {}
    print(f"{'site':7} {'years':9} {'CO2':>7} {'UTC':>4} {'ZBOT':>6} {'FATES':11} surface | sources")
    for s in sites:
        try:
            ctx["surface"][s] = surface_info(s, reg[s])
            ctx["clock"][s] = ch = clock_and_height(s, s98, over)
            stage95_files(s, full_sha=full)
            for p in (case_dir(s), OUT / name(s), arch_dir(s)):
                if p.exists() and not load(ledger(s)): fail(f"{s}: unexpected existing {p}")
            print(f"{s:7} {SITES[s][0]}-{SITES[s][1]} {co2[SITES[s][0]]:7.2f} {ch['utc_offset_h']:+4g} {ch['zbot_m']:6.2f} "
                  f"{'ARCTIC_PURE' if s in ARCTIC else 'DEFAULT14':11} OK | UTC {ch['utc_source']} | ZBOT {ch['zbot_source']}")
        except Exception as e:
            held[s] = str(e); print(f"{s:7} HOLD {e}")
    return ctx, held


def self_test():
    assert len(SITES) == 10 and sum(b - a + 1 for a, b in SITES.values()) == 215
    assert set(UTC_BIF) | set(UTC_PROXY) == set(SITES) and not set(UTC_BIF) & set(UTC_PROXY)
    assert np.allclose(DEFAULT14.sum(1), 1) and np.allclose(ARCTIC_PURE.sum(1), 1)
    diff = np.argwhere(~np.isclose(DEFAULT14, ARCTIC_PURE))
    assert sorted({int(r) for r, _ in diff}) == [8, 10]
    assert ARCTIC_PURE[8, 9] == 1 and ARCTIC_PURE[10, 10] == 1 and DEFAULT14[8, 6] == 1
    for step in (30, 60):
        n = 525600 // step
        for tz in (-5, -7, -9):
            sh = int(-tz * 60 / step)
            prev, today = np.arange(n) + 10 ** 6, np.arange(n)
            arr = np.concatenate([prev[n - sh:], today[:n - sh]])
            assert arr.size == n and arr[sh] == 0 and arr[sh - 1] == prev[-1]
    t = "a = 1\n finidat = 'x'\nb = 2\n"; assert nml_get(nml_del(t, "finidat"), "finidat") is None
    assert nml_get(nml_set(t, "a", "3"), "a") == "3"
    assert SEGMENTS * SEG_YEARS == 400 and len({ACK_PREP, ACK_SUB, ACK_Q}) == 3
    assert name("US-GLE") == "US-GLE_AMF_B02_FIXNC_AD400_DIRECT"
    print("AMF B02 STAGE06 SELF-TEST PASS (no files, no HPC)")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("action", choices=("self-test", "check", "prepare", "submit", "status", "audit-first5", "audit-ad400",
                                       "quarantine-failed-prepare"))
    ap.add_argument("--sites", nargs="+")
    ap.add_argument("--confirm", default="")
    ap.add_argument("--zbot", nargs="*", help="SITE=metres overrides")
    ap.add_argument("--co2-csv", help="local copy of NOAA co2_annmean_gl.csv (default: download once)")
    a = ap.parse_args()
    sites = pick(a.sites)
    if a.action == "self-test": return self_test()
    if a.action == "status": return status(sites)
    if a.action == "audit-first5":
        _, h = table("AMF B02 DIRECT AD400 FIRST 5-YEAR AUDIT (read only)", sites, first5_one); raise SystemExit(2 if h else 0)
    if a.action == "audit-ad400":
        _, h = table("AMF B02 DIRECT AD400 AUDIT (read only)", sites, ad400_one); raise SystemExit(2 if h else 0)
    if a.action == "quarantine-failed-prepare":
        if a.confirm != ACK_Q or not a.sites: fail("requires explicit --sites and --confirm " + ACK_Q)
        return batch("QUARANTINE", sites, quarantine_one)
    if a.action == "check":
        _, h = context(sites, a, full=False)
        print("AMF B02 STAGE06 CHECK", "PASS" if not h else "HOLD " + ",".join(h), "| READ ONLY (CO2 table may be downloaded once)")
        raise SystemExit(2 if h else 0)
    if a.action == "prepare":
        if a.confirm != ACK_PREP: fail("requires --confirm " + ACK_PREP)
        ctx, h = context(sites, a, full=False)
        if h: fail("preflight HOLD for " + ",".join(h) + "; use --sites with PASS sites only")
        return batch("PREPARE", sites, lambda s: prepare_one(s, ctx))
    if a.action == "submit":
        if a.confirm != ACK_SUB: fail("requires --confirm " + ACK_SUB)
        stack = stack_guard()
        return batch("SUBMIT", sites, lambda s: submit_one(s, stack))


if __name__ == "__main__":
    main()
