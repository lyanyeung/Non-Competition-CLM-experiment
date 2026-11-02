#!/usr/bin/env python3
"""Batch04 CH-Aws Stage06A, READ ONLY: humidity scan for the option-A forcing repair, plus case and surface inventory.

Operator decision, 2 Nov 2026 (option A): the CH-Aws forcing starts from the original FLUXNET product. Only
physically implausible MDS-filled humidity is replaced with the packaged ERA value (VPD_ERA); measured TA and
pressure stay unchanged. Same approach as IT-Tor F1 and the DE-Gri edits. This stage only measures. It writes
nothing outside a new HOME report folder.

1. Cases. For every cases/CH-Aws* case: build state, start year, CO2, DATM years and folder, effective FATES flags,
   surface and parameter file, CaseStatus tail, archived restart sets and error lines from the newest run logs.
2. Surfaces. For every distinct fsurdat: landunits, host PCT_NAT_PFT, soil sand/clay/ORGANIC, point vs PTS, sha.
3. FLUXMET scan. Reads all rows of EUF_CH-Aws_FLUXNET_FLUXMET_HH_2006-2024_v1.3_r2.csv.
   - implied RH_F = 100 (1 - VPD_F / es(TA_F)) and RH_ERA = 100 (1 - VPD_ERA / es(TA_ERA));
   - per year: VPD_F_QC counts;
   - QC1 (MDS-filled) half-hours counted for a grid of rules: RH_F below 5/10/20/30 % and RH_ERA - RH_F at least
     30/50 points;
   - the same low-RH counts for measured (QC0) half-hours, to show how often the site really is that dry;
   - episodes, hour of day, measured RH availability;
   - what three ways of using ERA would give at the flagged half-hours.
4. Forcing versions. Each distinct case DATM path set (7 expected) is compared half-hour by half-hour with the
   FLUXMET TIMESTAMP_START labels, 29 Feb dropped. The comparison covers:
   - TBOT alignment;
   - half-hours whose QBOT differs from the value implied by TA_F/VPD_F;
   - what each version did at the half-hours the main rule flags.
Main rule (Stage02O criterion): VPD_F_QC = 1 and RH_F < 10 % and RH_ERA - RH_F >= 50 points.

Output: ~/ICOS_Batch04_stage06a_CH_Aws.XXXXXXXX/ with a summary JSON and a PRIVATE CSV of candidate half-hours.
The CSV holds licensed values; never commit it.

Actions
  self-test   no HPC, temp files only
  run         READ ONLY; new HOME report folder only
"""
import argparse, csv, gzip, hashlib, json, math, re, subprocess, sys, tempfile
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

B = Path("/iridisfs/scratch/ly3n24/CLM_FATES")
HOME = Path.home()
SITE = B / "sites/MY_EC_SITE/CH-Aws"
SOURCE_NAME = "EUF_CH-Aws_FLUXNET_FLUXMET_HH_2006-2024_v1.3_r2.csv"
SOURCE_BYTES, SOURCE_ROWS = 372131800, 333120          # Stage02J
FIRST, LAST = 2006, 2024
NY, NH = LAST - FIRST + 1, 17520
RH_CUTS, GAP_CUTS, MAIN = (5, 10, 20, 30), (30, 50), (10, 50)
CUM = (0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334)
NEED_COLS = ("TIMESTAMP_START", "TA_F", "TA_F_QC", "VPD_F", "VPD_F_QC", "VPD_ERA", "TA_ERA")
OPT_COLS = ("PA_F", "RH", "VPD_F_MDS_QC")
CASE_KEYS = ("BUILD_COMPLETE", "RUN_STARTDATE", "STOP_N", "RESUBMIT", "CLM_ACCELERATED_SPINUP", "CCSM_CO2_PPMV",
             "CLM_CO2_TYPE", "DATM_YR_START", "DATM_YR_END", "PTS_LAT", "PTS_LON", "EXEROOT", "RUNDIR", "DOUT_S_ROOT")
NML_KEYS = ("fsurdat", "fates_paramfile", "use_fates_sp", "use_fates_nocomp", "use_fates_fixed_biogeog", "spinup_state")
LOG_PAT = re.compile(r"ERROR|endrun|NaN|negative|abort|SIGSEGV|forrtl|Traceback", re.I)


def need(x, msg):
    if not x: raise RuntimeError(msg)


def utc(): return datetime.now(timezone.utc).isoformat()


def sha(p):
    h = hashlib.sha256()
    with Path(p).open("rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""): h.update(b)
    return h.hexdigest()


def xq(case, key):
    try:
        p = subprocess.run([str(case / "xmlquery"), key, "--value"], cwd=case, text=True, capture_output=True, timeout=90)
        return p.stdout.strip() if p.returncode == 0 else None
    except Exception:
        return None


def nmlget(t, key):
    z = re.findall(r"(?im)^\s*" + re.escape(key) + r"\s*=\s*([^\r\n!]*)", t)
    return [x.strip().rstrip(",").strip("'\" ").strip() for x in z]


def parse_stream(case):
    doc = case / "CaseDocs/datm.streams.xml"
    if not doc.is_file(): return [], {}
    blocks = [x for x in ET.parse(doc).getroot().iter("stream_info") if x.get("name") == "CLM_USRDAT.UNSET"]
    if len(blocks) != 1: return [], {}
    e = blocks[0]
    return ([(x.text or "").strip() for x in e.find("datafiles")],
            {k: (e.findtext(k) or "").strip() for k in ("year_first", "year_last", "year_align", "taxmode", "offset")})


# ------------------------------------------------------------------ physics (same Magnus form as 05a)
def es_hpa(t_c):
    import numpy as np
    return 6.112 * np.exp(17.67 * t_c / (t_c + 243.5))


def q_from(t_c, vpd_hpa, p_pa):
    import numpy as np
    e = (es_hpa(t_c) - vpd_hpa) * 100.0
    with np.errstate(invalid="ignore"):
        return np.where(e >= 0, 0.622 * e / (p_pa - 0.378 * e), np.nan)


def rh_from_q(q, t_k, p_pa):
    e = q * p_pa / (0.622 + 0.378 * q)
    return 100.0 * e / (100.0 * es_hpa(t_k - 273.15))


def rh_from_vpd(t_c, vpd_hpa):
    return 100.0 * (1.0 - vpd_hpa / es_hpa(t_c))


def label_index(stamp):
    """FLUXMET 'YYYYMMDDHHMM' -> (year, no-leap half-hour index), or None for 29 February."""
    y, m, d, hh, mi = int(stamp[:4]), int(stamp[4:6]), int(stamp[6:8]), int(stamp[8:10]), int(stamp[10:12])
    if m == 2 and d == 29: return None
    need(mi in (0, 30), "unexpected minute in " + stamp)
    return y, (CUM[m - 1] + d - 1) * 48 + hh * 2 + mi // 30


def runs(mask):
    out, n = [], 0
    for v in mask:
        if v: n += 1
        elif n: out.append(n); n = 0
    if n: out.append(n)
    return out


# ------------------------------------------------------------------ 1-2. cases and surfaces
def tail_lines(path, n=3, pat=None, cap=20 << 20):
    try:
        raw = gzip.open(path, "rb").read(cap) if path.suffix == ".gz" else path.read_bytes()[-(1 << 20):]
    except Exception as e:
        return [f"<unreadable {e}>"]
    lines = [x for x in raw.decode(errors="replace").splitlines() if x.strip()]
    if pat is not None: lines = [x for x in lines if pat.search(x)]
    return [x.strip()[:200] for x in lines[-n:]]


def case_inventory():
    out = []
    for c in sorted(p for p in (B / "cases").glob("CH-Aws*") if p.is_dir() and (p / "xmlquery").exists()):
        r = {"case": c.name, **{k: xq(c, k) for k in CASE_KEYS}}
        lnd = (c / "CaseDocs/lnd_in").read_text(errors="replace") if (c / "CaseDocs/lnd_in").is_file() else ""
        r.update({k: (nmlget(lnd, k) or [None])[0] for k in NML_KEYS})
        files, st = parse_stream(c)
        yrs = [int(m.group(1)) for f in files for m in [re.search(r"_DATM_(\d{4})", Path(f).name)] if m]
        r.update({"datm_paths": files, "datm_years": [min(yrs), max(yrs)] if yrs else None, "datm_n": len(files),
                  "datm_dirs": sorted({str(Path(f).parent) for f in files}), "stream": st,
                  "exe_present": bool(r["EXEROOT"]) and (Path(r["EXEROOT"]) / "cesm.exe").is_file()})
        cs = c / "CaseStatus"
        r["casestatus_tail"] = tail_lines(cs, 3) if cs.is_file() else []
        rest = Path(r["DOUT_S_ROOT"] or "/nonexistent") / "rest"
        sets = sorted(x.name for x in rest.iterdir() if x.is_dir()) if rest.is_dir() else []
        r["restart_sets"] = {"n": len(sets), "first": sets[0] if sets else None, "last": sets[-1] if sets else None}
        logs = {}
        rd = Path(r["RUNDIR"] or "/nonexistent")
        if rd.is_dir():
            for kind in ("cesm", "lnd", "atm"):
                cand = sorted(rd.glob(f"{kind}.log.*"), key=lambda p: p.stat().st_mtime)
                if cand: logs[cand[-1].name] = tail_lines(cand[-1], 4, LOG_PAT)
        r["newest_run_log_errors"] = logs
        out.append(r)
    return out


def surface_info(path):
    from netCDF4 import Dataset
    import numpy as np
    with Dataset(str(path)) as ds:
        g = lambda k: np.ma.filled(np.ma.asarray(ds.variables[k][:]).astype(float), np.nan) if k in ds.variables else None
        pft = g("PCT_NAT_PFT").reshape(ds.variables["PCT_NAT_PFT"].shape[0], -1)[:, 0]
        land = {k: float(np.nansum(g(k))) for k in ("PCT_NATVEG", "PCT_CROP", "PCT_LAKE", "PCT_WETLAND", "PCT_GLACIER", "PCT_URBAN") if k in ds.variables}
        prof = lambda k: [round(float(x), 2) for x in g(k).reshape(g(k).shape[0], -1)[:, 0]] if k in ds.variables else None
        return {"sha256": sha(path), "landunits": land, "host_PCT_NAT_PFT": {int(i): round(float(x), 3) for i, x in enumerate(pft) if x},
                "lat": float(g("LATIXY").ravel()[0]), "lon": float(g("LONGXY").ravel()[0]),
                "PCT_SAND": prof("PCT_SAND"), "PCT_CLAY": prof("PCT_CLAY"), "ORGANIC": prof("ORGANIC")}


# ------------------------------------------------------------------ 3. FLUXMET
def scan(path, first=FIRST, last=LAST):
    import numpy as np
    ny = last - first + 1
    A = {k: np.full((ny, NH), np.nan) for k in NEED_COLS[1:] + OPT_COLS}
    seen = np.zeros((ny, NH), dtype=bool); labels = np.full((ny, NH), "", dtype=object)
    n = feb29 = outside = 0
    with Path(path).open(newline="", encoding="utf-8-sig") as f:
        rd = csv.reader(f); hdr = next(rd)
        ix = {c: hdr.index(c) for c in NEED_COLS + OPT_COLS if c in hdr}
        need(all(c in ix for c in NEED_COLS), f"FLUXMET lacks {[c for c in NEED_COLS if c not in ix]}")
        for row in rd:
            n += 1
            li = label_index(row[ix["TIMESTAMP_START"]])
            if li is None: feb29 += 1; continue
            y, i = li
            if not first <= y <= last: outside += 1; continue
            need(not seen[y - first, i], "duplicate label " + row[ix["TIMESTAMP_START"]])
            seen[y - first, i] = True; labels[y - first, i] = row[ix["TIMESTAMP_START"]]
            for k in A:
                if k in ix:
                    try: v = float(row[ix[k]])
                    except ValueError: continue
                    if v > -9990: A[k][y - first, i] = v
    return A, seen, labels, {"rows": n, "feb29_rows": feb29, "outside_rows": outside, "columns": len(hdr),
                             "optional_present": [c for c in OPT_COLS if c in ix]}


def humidity_stats(A, first=FIRST):
    import numpy as np
    with np.errstate(invalid="ignore", divide="ignore"):
        rhf = rh_from_vpd(A["TA_F"], A["VPD_F"]); rhe = rh_from_vpd(A["TA_ERA"], A["VPD_ERA"]); gap = rhe - rhf
        qc = A["VPD_F_QC"]; qc0, qc1, qc2 = qc == 0, qc == 1, qc == 2
        grid = {f"RH_F<{r} & gap>={g}": int(np.sum(qc1 & (rhf < r) & (gap >= g))) for r in RH_CUTS for g in GAP_CUTS}
        qc0_low = {f"RH_F<{r}": int(np.sum(qc0 & (rhf < r))) for r in RH_CUTS}
        qc0_low_era = {f"RH_F<{r}": (round(float(np.nanmedian(rhe[qc0 & (rhf < r)])), 1) if np.any(qc0 & (rhf < r)) else None) for r in RH_CUTS}
        neg = {f"QC{q}": int(np.sum((qc == q) & (rhf < 0))) for q in (0, 1, 2)}
        M = qc1 & (rhf < MAIN[0]) & (gap >= MAIN[1])
        per_year = {first + j: {"QC0": int(qc0[j].sum()), "QC1": int(qc1[j].sum()), "QC2": int(qc2[j].sum()),
                                "missing": int(np.isnan(qc[j]).sum()), "main": int(M[j].sum())} for j in range(qc.shape[0])}
        L = runs(M.ravel().tolist())
        bins = {"1": sum(1 for x in L if x == 1), "2-3": sum(1 for x in L if 2 <= x <= 3), "4-6": sum(1 for x in L if 4 <= x <= 6),
                "7-12": sum(1 for x in L if 7 <= x <= 12), ">12": sum(1 for x in L if x > 12)}
        hours = [int(np.sum(M & ((np.arange(NH) % 48) // 2 == h)[None, :])) for h in range(24)]
        rh_meas = A["RH"]
        meas = {"RH_finite_all": int(np.sum(np.isfinite(rh_meas))), "RH_finite_QC1": int(np.sum(np.isfinite(rh_meas) & qc1)),
                "RH_finite_main": int(np.sum(np.isfinite(rh_meas) & M))}
        if meas["RH_finite_main"]:
            meas["main_measured_RH_median"] = round(float(np.nanmedian(rh_meas[M])), 1)
        ta_qc_main = {f"TA_F_QC{q}": int(np.sum(M & (A["TA_F_QC"] == q))) for q in (0, 1, 2)}
        mds_qc_main = ({f"VPD_F_MDS_QC{q}": int(np.sum(M & (A["VPD_F_MDS_QC"] == q))) for q in (0, 1, 2, 3)}
                       if np.any(np.isfinite(A["VPD_F_MDS_QC"])) else None)
        # three ways to use ERA at the flagged half-hours (measured TA_F kept)
        t = A["TA_F"]
        o1 = rh_from_vpd(t, A["VPD_ERA"])                                     # VPD_ERA with TA_F
        o2 = rhe                                                              # RH_ERA kept
        o3 = 100.0 * (es_hpa(A["TA_ERA"]) - A["VPD_ERA"]) / es_hpa(t)         # ERA vapour pressure kept
        opts = {}
        for name, o in (("VPD_ERA_with_TA_F", o1), ("RH_ERA_kept", o2), ("ERA_vapour_pressure_kept", o3)):
            v = o[M]
            opts[name] = {"median_RH": round(float(np.nanmedian(v)), 1) if v.size else None,
                          "n_below_0": int(np.sum(v < 0)), "n_above_100": int(np.sum(v > 100)), "n_nan": int(np.sum(np.isnan(v)))}
        summary = {"main_rule": f"VPD_F_QC=1 & RH_F<{MAIN[0]} & RH_ERA-RH_F>={MAIN[1]}", "main_n": int(M.sum()),
                   "QC1_total": int(qc1.sum()), "QC0_total": int(qc0.sum()), "QC2_total": int(qc2.sum()),
                   "grid_QC1": grid, "QC0_low_RH": qc0_low, "QC0_low_RH_median_RH_ERA": qc0_low_era, "RH_F_below_0": neg,
                   "per_year": per_year, "episodes": {"n": len(L), "max_len_HH": max(L) if L else 0, "length_bins": bins},
                   "main_by_local_hour": hours, "measured_RH": meas, "main_TA_F_QC": ta_qc_main, "main_VPD_F_MDS_QC": mds_qc_main,
                   "main_gap_median": round(float(np.nanmedian(gap[M])), 1) if M.any() else None,
                   "main_RH_F_median": round(float(np.nanmedian(rhf[M])), 2) if M.any() else None, "era_options_at_main": opts}
    return summary, M, rhf, rhe, gap


# ------------------------------------------------------------------ 4. forcing versions
def versions(cases, A, M, rhe):
    import numpy as np
    from netCDF4 import Dataset
    groups = {}
    for r in cases:
        p = r["datm_paths"]
        if r["datm_years"] == [FIRST, LAST] and len(p) == NY: groups.setdefault(tuple(p), []).append(r["case"])
    out = []
    for paths, names in groups.items():
        T, Q, P = (np.full((NY, NH), np.nan) for _ in range(3))
        for j, f in enumerate(paths):
            with Dataset(f) as ds:
                for arr, k in ((T, "TBOT"), (Q, "QBOT"), (P, "PSRF")): arr[j] = np.ma.filled(np.ma.asarray(ds.variables[k][:]).astype(float), np.nan).ravel()[:NH]
        with np.errstate(invalid="ignore"):
            qf = q_from(A["TA_F"], A["VPD_F"], P)
            fin = np.isfinite(qf) & np.isfinite(Q)
            align = np.abs(T - (A["TA_F"] + 273.15)) < 0.01
            same = fin & (np.abs(Q - qf) <= 1e-8)                               # bit-level, as 05a checks
            changed = fin & ~(np.abs(Q - qf) <= 1e-3 * np.abs(qf) + 1e-8)       # a real edit, not a formula/rounding difference
            rhv = rh_from_q(Q, T, P)
            negsrc = np.isfinite(A["VPD_F"]) & (A["VPD_F"] > es_hpa(A["TA_F"]))
            out.append({"cases": sorted(names), "paths_dir": sorted({str(Path(x).parent) for x in paths}),
                        "TBOT_aligned_fraction": round(float(align.sum() / np.isfinite(T).sum()), 6),
                        "QBOT_equal_FLUXMET": int(same.sum()), "QBOT_differs": int(changed.sum()), "compared_HH": int(fin.sum()),
                        "differs_by_year": {FIRST + j: int(changed[j].sum()) for j in range(NY) if changed[j].any()},
                        "differs_at_main": int(np.sum(changed & M)), "differs_outside_main": int(np.sum(changed & ~M)),
                        "median_RH_at_main": round(float(np.nanmedian(rhv[M])), 1) if M.any() else None,
                        "main_within_10pt_of_RH_ERA": int(np.sum(M & (np.abs(rhv - rhe) < 10))),
                        "source_VPD_above_es_HH": int(negsrc.sum()),
                        "min_RH_at_source_VPD_above_es": round(float(np.nanmin(rhv[negsrc])), 2) if negsrc.any() else None,
                        "_rhv": rhv})
    out.sort(key=lambda v: (v["QBOT_differs"], -v["QBOT_equal_FLUXMET"]))
    return out


# ------------------------------------------------------------------ run
def run():
    import numpy as np
    work = Path(tempfile.mkdtemp(prefix="ICOS_Batch04_stage06a_CH_Aws.", dir=HOME))
    print("==== STAGE06A CH-Aws (read only) | report folder", work)
    cases = case_inventory()
    print(f"\n== 1. CASES ({len(cases)} found, Stage02C expected 8)")
    for r in cases:
        print(f"  {r['case']}: BUILD {r['BUILD_COMPLETE']} exe {'yes' if r['exe_present'] else 'NO'} | start {r['RUN_STARTDATE']} STOP_N {r['STOP_N']}"
              f" RESUBMIT {r['RESUBMIT']} ACCEL {r['CLM_ACCELERATED_SPINUP']} | CO2 {r['CLM_CO2_TYPE']} {r['CCSM_CO2_PPMV']}")
        print(f"     DATM {r['datm_n']} files {r['datm_years']} {r['datm_dirs']} | stream {r['stream']}")
        print(f"     lnd_in: sp {r['use_fates_sp']} nocomp {r['use_fates_nocomp']} fixed {r['use_fates_fixed_biogeog']} spinup_state {r['spinup_state']}"
              f" | fsurdat {r['fsurdat']} | param {r['fates_paramfile']}")
        print(f"     restarts {r['restart_sets']} | CaseStatus tail {r['casestatus_tail']}")
        for k, v in r["newest_run_log_errors"].items(): print(f"     {k}: {v if v else 'no error lines'}")
    surfs = {}
    print("\n== 2. SURFACES")
    for s in sorted({r["fsurdat"] for r in cases if r["fsurdat"]}):
        if not Path(s).is_file(): print("  MISSING", s); continue
        info = surface_info(s); surfs[s] = info
        users = [r["case"] for r in cases if r["fsurdat"] == s]
        pts = {(r["PTS_LAT"], r["PTS_LON"]) for r in cases if r["fsurdat"] == s}
        print(f"  {s}\n     sha {info['sha256'][:12]} | used by {len(users)}: {users}\n     landunits {info['landunits']}"
              f" | host PFT {info['host_PCT_NAT_PFT']} (operator proxy 13:100) | point {info['lat']:.4f},{info['lon']:.4f} | PTS {pts}")
        print(f"     sand {info['PCT_SAND']}\n     clay {info['PCT_CLAY']}\n     ORGANIC {info['ORGANIC']}")
    hits = [p for p in SITE.rglob(SOURCE_NAME) if p.is_file() and not p.is_symlink()]
    need(len(hits) == 1, f"expected one {SOURCE_NAME} under {SITE}, found {[str(h) for h in hits]}")
    src = hits[0]; need(src.stat().st_size == SOURCE_BYTES, f"FLUXMET size {src.stat().st_size} != Stage02J {SOURCE_BYTES}")
    print(f"\n== 3. FLUXMET scan {src}")
    A, seen, labels, meta = scan(src)
    need(meta["rows"] == SOURCE_ROWS and meta["feb29_rows"] == 240 and meta["outside_rows"] == 0, f"row accounting {meta}")
    need(bool(seen.all()), f"{int((~seen).sum())} no-leap half-hours have no FLUXMET row")
    print(f"  rows {meta['rows']} | 29 Feb rows dropped {meta['feb29_rows']} | all {NY}x{NH} no-leap labels present | optional columns {meta['optional_present']}")
    s, M, rhf, rhe, gap = humidity_stats(A)
    print(f"  VPD_F_QC totals: QC0 measured {s['QC0_total']} | QC1 MDS {s['QC1_total']} | QC2 ERA {s['QC2_total']}")
    print("  QC1 half-hours by rule (RH_F below / RH_ERA - RH_F at least):")
    for k, v in s["grid_QC1"].items(): print(f"     {k:24s} {v}")
    print(f"  measured (QC0) half-hours with low RH_F: {s['QC0_low_RH']} | their median RH_ERA {s['QC0_low_RH_median_RH_ERA']}")
    print(f"  RH_F < 0 (VPD_F above saturation) by QC: {s['RH_F_below_0']}")
    print(f"  MAIN RULE {s['main_rule']}: {s['main_n']} half-hours | median RH_F {s['main_RH_F_median']} | median gap {s['main_gap_median']} points")
    print("  per year (QC0 / QC1 / QC2 / missing / main):")
    for y, v in s["per_year"].items(): print(f"     {y}: {v['QC0']:6d} {v['QC1']:6d} {v['QC2']:6d} {v['missing']:5d} {v['main']:5d}")
    print(f"  episodes {s['episodes']}")
    print(f"  main by local hour 00..23: {s['main_by_local_hour']}")
    print(f"  measured RH column: {s['measured_RH']} | TA_F_QC at main {s['main_TA_F_QC']} | VPD_F_MDS_QC at main {s['main_VPD_F_MDS_QC']}")
    print("  ERA use at main half-hours (measured TA_F kept):")
    for k, v in s["era_options_at_main"].items(): print(f"     {k:26s} {v}")
    vs = versions(cases, A, M, rhe)
    print(f"\n== 4. FORCING VERSIONS ({len(vs)} distinct 2006-2024 path sets; first = closest to FLUXMET)")
    for v in vs:
        print(f"  {v['cases']} | {v['paths_dir']}")
        print(f"     TBOT aligned {v['TBOT_aligned_fraction']} | of {v['compared_HH']} HH: QBOT = FLUXMET (bit) {v['QBOT_equal_FLUXMET']} | differs >0.1% {v['QBOT_differs']}"
              f" (at main {v['differs_at_main']}, elsewhere {v['differs_outside_main']}) | by year {v['differs_by_year']}")
        print(f"     at main: median RH {v['median_RH_at_main']} | within 10 points of RH_ERA {v['main_within_10pt_of_RH_ERA']}/{s['main_n']}"
              f" | source VPD>es HH {v['source_VPD_above_es_HH']} min RH there {v['min_RH_at_source_VPD_above_es']}")
    cand = (A["VPD_F_QC"] == 1) & (rhf < max(RH_CUTS)) & (gap >= min(GAP_CUTS))
    csvp = work / "stage06a_CH_Aws_candidate_HH_PRIVATE.csv"
    with csvp.open("x", newline="") as f:
        w = csv.writer(f)
        w.writerow(["TIMESTAMP_START", "year", "datm_index", "TA_F", "TA_F_QC", "VPD_F", "VPD_F_QC", "VPD_F_MDS_QC", "VPD_ERA", "TA_ERA",
                    "RH_measured", "RH_F", "RH_ERA", "main_rule"] + ["RH_" + v["cases"][0] for v in vs])
        for j, i in zip(*np.nonzero(cand)):
            w.writerow([labels[j, i], FIRST + j, i] + [A[k][j, i] for k in ("TA_F", "TA_F_QC", "VPD_F", "VPD_F_QC", "VPD_F_MDS_QC", "VPD_ERA", "TA_ERA", "RH")]
                       + [round(float(rhf[j, i]), 3), round(float(rhe[j, i]), 3), bool(M[j, i])] + [round(float(v["_rhv"][j, i]), 3) for v in vs])
    for v in vs: v.pop("_rhv")
    (work / "stage06a_CH_Aws_summary.json").write_text(json.dumps(
        {"stage": "STAGE06A_CH_AWS_READONLY", "created_utc": utc(), "science_release": False, "source": str(src), "source_meta": meta,
         "cases": cases, "surfaces": surfs, "humidity": s, "versions": vs}, indent=2, default=str) + "\n")
    print(f"\nCANDIDATE CSV (PRIVATE, do not commit) {csvp} rows {int(cand.sum())} | summary {work / 'stage06a_CH_Aws_summary.json'}")
    print("STAGE06A COMPLETE | nothing outside the report folder written")


def self_test():
    import numpy as np
    from netCDF4 import Dataset
    assert label_index("200603010000") == (2006, 59 * 48) and label_index("200802290130") is None
    assert label_index("202412312330") == (2024, NH - 1) and label_index("202511131430") == (2025, 316 * 48 + 29)
    t, vpd, p = np.array([5.0, -3.0]), np.array([2.0, 0.5]), np.array([80000.0, 80000.0])
    assert np.allclose(rh_from_q(q_from(t, vpd, p), t + 273.15, p), rh_from_vpd(t, vpd))
    assert np.isnan(q_from(np.array([0.0]), np.array([10.0]), np.array([80000.0]))[0])
    assert runs([0, 1, 1, 0, 1, 0, 0, 1, 1, 1]) == [2, 1, 3]
    with tempfile.TemporaryDirectory() as d:
        d = Path(d); f = d / SOURCE_NAME
        rows = [("200801010000", 1.0, 0, 6.0, 1, 0.1, 1.0), ("200801010030", 1.0, 0, 6.0, 0, 0.1, 1.0),
                ("200802290000", 1.0, 0, 1.0, 1, 1.0, 1.0), ("200801010100", 1.0, 0, -9999, -9999, 0.1, 1.0)]
        with f.open("w", newline="") as h:
            w = csv.writer(h); w.writerow(["TIMESTAMP_START", "TA_F", "TA_F_QC", "VPD_F", "VPD_F_QC", "VPD_ERA", "TA_ERA", "RH"])
            for r in rows: w.writerow(list(r) + [-9999])
        A, seen, labels, meta = scan(f, 2008, 2008)
        assert meta["rows"] == 4 and meta["feb29_rows"] == 1 and seen.sum() == 3 and np.isnan(A["VPD_F"][0, 2])
        s, M, rhf, rhe, gap = humidity_stats(A, 2008)
        assert s["main_n"] == 1 and M[0, 0] and not M[0, 1] and s["QC0_low_RH"]["RH_F<10"] == 1 and s["episodes"]["n"] == 1
        nc = d / "CH-Aws_DATM_2008.nc"
        with Dataset(str(nc), "w") as ds:
            ds.createDimension("time", NH); ds.createDimension("lat", 1); ds.createDimension("lon", 1)
            q = q_from(np.full(NH, 1.0), np.full(NH, 0.5), np.full(NH, 80000.0))
            for k, v in (("TBOT", np.full(NH, 274.15)), ("QBOT", q), ("PSRF", np.full(NH, 80000.0))): ds.createVariable(k, "f8", ("time", "lat", "lon"))[:] = v.reshape(NH, 1, 1)
        global FIRST, LAST, NY
        saved = (FIRST, LAST, NY); FIRST, LAST, NY = 2008, 2008, 1
        try:
            A2 = {k: np.full((1, NH), np.nan) for k in A}; A2["TA_F"][:] = 1.0; A2["VPD_F"][:] = 0.5; A2["VPD_F"][0, 5] = 0.6
            v = versions([{"case": "CH-Aws_X", "datm_paths": [str(nc)], "datm_years": [2008, 2008]}], A2, np.zeros((1, NH), bool), np.full((1, NH), 50.0))
            assert v[0]["TBOT_aligned_fraction"] == 1.0 and v[0]["QBOT_differs"] == 1 and v[0]["QBOT_equal_FLUXMET"] == NH - 1
        finally:
            FIRST, LAST, NY = saved
    print("STAGE06A SELF-TEST PASS (labels/no-leap index, humidity physics, FLUXMET scan, rule counts, version diff; no HPC)")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("action", choices=("self-test", "run"))
    a = ap.parse_args()
    self_test() if a.action == "self-test" else run()


if __name__ == "__main__":
    try: main()
    except RuntimeError as e: print("STAGE06A HOLD:", e, file=sys.stderr); sys.exit(2)
