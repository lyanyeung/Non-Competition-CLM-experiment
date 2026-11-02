#!/usr/bin/env python3
"""Batch04 Stage05B, READ ONLY: running-chain audit, IT-Tor F1/soil inputs, GL-ZaH surface preflight.

1. DE-Gri / DE-RuR / ES-Agu <site>_ICOS_B04_FIXNC_AD400_DIRECT: queue, accounting since 2026-11-02, CaseStatus,
   archived restart sets (clm2/datm/cpl) and spinup_state, RESUBMIT left, effective FATES flags, CO2 setting versus
   the constant first-forcing-year NOAA value used by earlier batches.
2. IT-Tor F1: diff of the IRIDIS6 run copy (sha 2a537d46...) against the repository copy; F1 manifest summary.
3. IT-Tor soil: pinned CTSM lines that read ORGANIC on the 10 surface-data levels and map it to the 20SL_8.5m
   model layers, so the S1 profile can be built on the real mapping.
4. GL-ZaH: template case, its surface (landunits, PFT slots, soil, point), DATM stream, CO2, and the private Arctic
   parameter candidate (sha and host rows 9/11/12).
Prints only. Creates, edits or submits nothing.

    python3 -B 05b_batch04_status_itTor_soil_glZaH_preflight_READONLY.py [self-test]
"""
import csv, difflib, hashlib, json, re, subprocess, sys
import xml.etree.ElementTree as ET
from pathlib import Path

B = Path("/iridisfs/scratch/ly3n24/CLM_FATES")
OUT = Path("/scratch/ly3n24/CTSM_FATES_OUTPUTS")
CTSM = B / "CTSM"
HOME = Path.home()
HERE = Path(__file__).resolve().parent
RUNNING = {"DE-Gri": 2004, "DE-RuR": 2011, "ES-Agu": 2006}
CO2_CSV = B / "experiments/NonCompetitionObserved22/AmeriFlux_Batch02_10/Stage06_direct_AD400/co2_annmean_gl.csv"
F1_RUN = HOME / "ICOS_Batch04_IT_Tor_F1_2a537d46.py"
F1_REPO = HERE / "05a_it_tor_make_f1_candidate.py"
GL_TEMPLATE = B / "cases/GL-ZaH_FATES_SPINUP500_11P"
GL_PARAM = B / "experiments/NonCompetitionObserved22/ICOS_Unassigned_6/GL-ZaH_private_arctic_map_candidate_v1/fates_params_GL-ZaH_arctic_private_candidate.json"
GL_PARAM_SHA = "56d9433f5915686b2877367124c39ee1f167d2c5c2cbc88cc5e190f53d31cd62"
GL_TARGET = {0: 43.0, 9: 53.0, 11: 3.0, 12: 1.0}   # operator-selected six-site PFT CSV (ICOS_Unassigned_6)
SIX_SITE_CSV = HERE.parents[1] / "ICOS_Unassigned_6/data/six_site_FIXNC_operator_selected_PFT_20261025.csv"


def sha(p):
    h = hashlib.sha256()
    with Path(p).open("rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""): h.update(b)
    return h.hexdigest()


def run(args, cwd=None, timeout=90):
    try:
        p = subprocess.run([str(a) for a in args], cwd=cwd, text=True, capture_output=True, timeout=timeout)
        return p.returncode, (p.stdout + p.stderr).strip()
    except Exception as e:
        return 99, f"{type(e).__name__}: {e}"


def xq(case, key):
    rc, out = run(["./xmlquery", key, "--value"], cwd=case)
    return out if rc == 0 else f"<ERR {out[-120:]}>"


def nml(text, key):
    hits = re.findall(r"(?im)^\s*" + re.escape(key) + r"\s*=\s*([^\r\n!]*)", text)
    return [h.strip().rstrip(",").strip("'\" ") for h in hits]


def co2_table():
    vals = {}
    if CO2_CSV.is_file():
        for ln in CO2_CSV.read_text().splitlines():
            p = [x.strip() for x in ln.split(",")]
            if len(p) >= 2 and p[0].isdigit(): vals[int(p[0])] = float(p[1])
    return vals


def spinup_state(path):
    try:
        from netCDF4 import Dataset
        import numpy as np
        with Dataset(str(path)) as ds:
            if "spinup_state" in ds.variables: return int(np.asarray(ds.variables["spinup_state"][:]).ravel()[0])
            if "spinup_state" in ds.ncattrs(): return int(ds.getncattr("spinup_state"))
        return "absent"
    except Exception as e:
        return f"ERR {type(e).__name__}: {e}"


def section(t): print("\n" + "=" * 8, t, "=" * 8, flush=True)


# ---------------------------------------------------------------- 1. running chains
def audit_running(co2):
    section("1. RUNNING DIRECT AD400 CHAINS (read only)")
    for s, start in RUNNING.items():
        name = f"{s}_ICOS_B04_FIXNC_AD400_DIRECT"; case = B / "cases" / name; arch = OUT / "archive" / name
        print(f"\n--- {s} {name}")
        if not case.is_dir(): print("  CASE MISSING", case); continue
        for k in ("RUN_STARTDATE", "STOP_N", "RESUBMIT", "CONTINUE_RUN", "CLM_ACCELERATED_SPINUP", "CLM_CO2_TYPE",
                  "CCSM_CO2_PPMV", "DATM_CO2_TSERIES", "DATM_YR_START", "DATM_YR_END", "DATM_YR_ALIGN"):
            print(f"  {k} = {xq(case, k)}")
        want = co2.get(start)
        got = xq(case, "CCSM_CO2_PPMV")
        try: diff = f"{float(got) - want:+.2f}" if want else "n/a"
        except ValueError: diff = "n/a"
        print(f"  CO2 CHECK: case {got} ppm vs NOAA {start} annual mean {want} ppm (earlier-batch convention) diff {diff}")
        lnd = (case / "CaseDocs/lnd_in").read_text() if (case / "CaseDocs/lnd_in").is_file() else ""
        for k in ("spinup_state", "use_fates_nocomp", "use_fates_fixed_biogeog", "use_fates_sp", "co2_ppmv", "fsurdat", "fates_paramfile"):
            print(f"  lnd_in {k} = {nml(lnd, k)}")
        cs = (case / "CaseStatus").read_text(errors="replace").splitlines() if (case / "CaseStatus").is_file() else []
        print("  CaseStatus tail:"); [print("    " + x) for x in cs[-4:]]
        print("  case.run success count:", sum("case.run success" in x for x in cs),
              "| error lines:", sum(re.search(r"error|fail", x, re.I) is not None for x in cs))
        rc, q = run(["squeue", "-h", "-u", "ly3n24", "-o", "%i|%j|%T|%M", "-n", f"run.{name},st_archive.{name}"])
        print("  queue:", q.replace("\n", " ; ") or "(none)")
        rc, a = run(["sacct", "-X", "-n", "-P", "-u", "ly3n24", "-S", "2026-11-02", "--name", f"run.{name},st_archive.{name}",
                     "--format=JobIDRaw,JobName%90,State,ExitCode"])
        rows = [r.split("|") for r in a.splitlines() if r.count("|") >= 3]
        states = {}
        for r in rows: states[(r[1].split(".")[0], r[2])] = states.get((r[1].split(".")[0], r[2]), 0) + 1
        print("  sacct:", dict(sorted(states.items())))
        bad = [r for r in rows if r[2].split()[0] not in ("COMPLETED", "RUNNING", "PENDING") or
               (r[2] == "COMPLETED" and r[3] != "0:0")]
        print("  non-OK jobs (DE-Gri 4807852 FAILED / 4807853 CANCELLED are the known pre-fix attempt):", bad or "none")
        rest = sorted(x for x in (arch / "rest").iterdir() if x.is_dir()) if (arch / "rest").is_dir() else []
        print(f"  archived restart sets: {len(rest)} | first {rest[0].name if rest else '-'} | latest {rest[-1].name if rest else '-'}"
              f" | expected first {start + 5:04d}-01-01-00000, target {start + 400:04d}-01-01-00000")
        for d in ([rest[0]] if rest else []) + ([rest[-1]] if len(rest) > 1 else []):
            files = {c: list(d.glob(f"{name}.{c}.r.*.nc")) for c in ("clm2", "datm", "cpl")}
            print(f"    {d.name}: " + " ".join(f"{c}={len(v)}" for c, v in files.items()),
                  "| clm2 spinup_state =", spinup_state(files["clm2"][0]) if files["clm2"] else "no clm2 restart")
        hist = sorted((arch / "lnd/hist").glob("*.clm2.h0.*.nc")) if (arch / "lnd/hist").is_dir() else []
        print(f"  archived h0 files: {len(hist)} | last {hist[-1].name if hist else '-'}")


# ---------------------------------------------------------------- 2. IT-Tor F1
def it_tor_f1():
    section("2. IT-Tor F1: IRIDIS run copy vs repository copy")
    for p in (F1_RUN, F1_REPO):
        print(f"  {p}: {'sha ' + sha(p) if p.is_file() else 'MISSING'}")
    if F1_RUN.is_file() and F1_REPO.is_file():
        d = list(difflib.unified_diff(F1_RUN.read_text().splitlines(), F1_REPO.read_text().splitlines(),
                                      "IRIDIS_run_copy", "repository_copy", lineterm="", n=1))
        print(f"  diff lines: {len(d)}"); [print("    " + x) for x in d[:80]]
    man = sorted(HOME.glob("ICOS_Batch04_IT_Tor_F1.*/result/manifest_PRIVATE.json"))
    for m in man:
        r = json.loads(m.read_text())
        print(f"  manifest {m.parent}: status {r.get('status')} | candidate sha {r.get('candidate_sha256')} | "
              f"changes {len(r.get('changes', []))} | clock verified {r.get('source_label_clock_alignment_independently_verified')}")


# ---------------------------------------------------------------- 3. IT-Tor soil mapping
def it_tor_soil():
    section("3. IT-Tor soil: pinned CTSM ORGANIC read and layer mapping")
    rc, head = run(["git", "-C", CTSM, "rev-parse", "HEAD"]); print("  CTSM HEAD:", head)
    rc, st = run(["git", "-C", CTSM, "status", "--short", "--", "src/biogeophys/SoilStateInitTimeConstMod.F90", "src/main/initVerticalMod.F90"])
    print("  local modifications:", st or "none")
    f = CTSM / "src/biogeophys/SoilStateInitTimeConstMod.F90"
    if f.is_file():
        L = f.read_text(errors="replace").splitlines()
        pats = (r"zsoifl\s*\(", r"zisoifl\s*\(", r"dzsoifl\s*\(", r"organic3d\s*\(", r"om_frac\s*=", r"organic_max",
                r"organic_frac_squared", r"nlevsoifl")
        shown = set()
        for pat in pats:
            hits = [i for i, x in enumerate(L) if re.search(pat, x, re.I)]
            print(f"  -- {pat}: {len(hits)} lines")
            for i in hits[:6]:
                for j in range(max(0, i - 1), min(len(L), i + 2)):
                    if j not in shown: print(f"    {j + 1}: {L[j]}"); shown.add(j)
    else:
        print("  MISSING", f)
    g = CTSM / "src/main/initVerticalMod.F90"
    if g.is_file():
        L = g.read_text(errors="replace").splitlines()
        hits = [i for i, x in enumerate(L) if "20SL_8.5m" in x]
        print(f"  -- initVerticalMod 20SL_8.5m: {len(hits)} lines")
        for i in hits:
            for j in range(i, min(len(L), i + 12)): print(f"    {j + 1}: {L[j]}")
    case = B / "cases/IT-Tor_FATES_SPINUP1000_S30SHARED"
    lnd = (case / "CaseDocs/lnd_in").read_text() if (case / "CaseDocs/lnd_in").is_file() else ""
    for k in ("soil_layerstruct_predefined", "organic_frac_squared", "paramfile", "fsurdat"):
        print(f"  IT-Tor template lnd_in {k} = {nml(lnd, k)}")
    logs = sorted((OUT / "IT-Tor_FATES_SPINUP1000_S30SHARED/run").glob("lnd.log.*")) if (OUT / "IT-Tor_FATES_SPINUP1000_S30SHARED/run").is_dir() else []
    print("  IT-Tor template lnd logs in run dir:", len(logs))
    if logs:
        t = logs[-1].read_text(errors="replace").splitlines()
        for i, x in enumerate(t):
            if re.search(r"zsoi|zisoi|dzsoi|nlevsoi|nlevgrnd", x, re.I):
                print("    " + x.strip()[:160])
                if i > 4000: break


# ---------------------------------------------------------------- 4. GL-ZaH
def gl_zah(co2):
    section("4. GL-ZaH preflight for a site surface and case")
    t = GL_TEMPLATE
    if not t.is_dir(): print("  TEMPLATE MISSING", t); return
    for k in ("BUILD_COMPLETE", "RUN_STARTDATE", "DATM_MODE", "CALENDAR", "ATM_NCPL", "RESUBMIT", "CONTINUE_RUN",
              "CLM_USRDAT_NAME", "CLM_BLDNML_OPTS", "COMP_ROOT_DIR_LND", "PTS_LAT", "PTS_LON", "CLM_CO2_TYPE", "CCSM_CO2_PPMV",
              "DATM_YR_START", "DATM_YR_END", "DATM_YR_ALIGN", "EXEROOT"):
        print(f"  {k} = {xq(t, k)}")
    exe = Path(xq(t, "EXEROOT")) / "cesm.exe"
    print("  executable:", exe, "exists" if exe.is_file() else "MISSING")
    print("  NOAA CO2 2000:", co2.get(2000))
    cs = (t / "CaseStatus").read_text(errors="replace") if (t / "CaseStatus").is_file() else ""
    print("  template case.run success count:", cs.count("case.run success"))
    lnd = (t / "CaseDocs/lnd_in").read_text() if (t / "CaseDocs/lnd_in").is_file() else ""
    for k in ("fsurdat", "fates_paramfile", "use_fates", "use_fates_nocomp", "use_fates_fixed_biogeog", "spinup_state",
              "soil_layerstruct_predefined", "finidat", "hist_fincl1"):
        print(f"  lnd_in {k} = {nml(lnd, k)}")
    for f in ("user_nl_clm", "user_nl_datm_streams", "LockedFiles/env_case.xml"):
        print(f"  {f}: {'present' if (t / f).is_file() else 'MISSING'}")
    doc = t / "CaseDocs/datm.streams.xml"
    if doc.is_file():
        st = {e.get("name"): e for e in ET.parse(doc).getroot().iter("stream_info")}
        m = st.get("CLM_USRDAT.UNSET")
        if m is not None:
            files = [Path((x.text or "").strip()) for x in m.find("datafiles")]
            yrs = sorted(int(re.search(r"_DATM_(\d{4})", p.name).group(1)) for p in files if re.search(r"_DATM_(\d{4})", p.name))
            print(f"  DATM stream: {len(files)} files, years {yrs[:1]}..{yrs[-1:]}, missing {sum(not p.is_file() for p in files)},"
                  f" dirs {sorted({str(p.parent) for p in files})}")
            for k in ("year_first", "year_last", "year_align", "taxmode"):
                print(f"    {k} = {(m.findtext(k) or '').strip()}")
            print("    datavars:", [(e.text or "").strip() for e in m.find("datavars")])
        print("  stream names:", sorted(st))
    fs = nml(lnd, "fsurdat")
    if fs and Path(fs[0]).is_file():
        p = Path(fs[0]); print(f"  surface {p}\n    sha {sha(p)}")
        try:
            from netCDF4 import Dataset
            import numpy as np
            with Dataset(str(p)) as ds:
                print("    dims:", {k: len(v) for k, v in ds.dimensions.items()})
                for k in ("PCT_NATVEG", "PCT_CROP", "PCT_LAKE", "PCT_WETLAND", "PCT_GLACIER", "PCT_URBAN", "LATIXY", "LONGXY",
                          "PCT_NAT_PFT", "PCT_CFT", "PCT_SAND", "PCT_CLAY", "ORGANIC", "FMAX", "zbedrock", "SLOPE"):
                    if k in ds.variables:
                        v = np.ma.asarray(ds.variables[k][:]).ravel()
                        txt = v.tolist() if v.size <= 16 else f"{v.size} values, nonzero {np.flatnonzero(v).tolist()[:16]}"
                        print(f"    {k} {ds.variables[k].dimensions}: {txt}")
                    else:
                        print(f"    {k}: absent")
        except Exception as e:
            print("    SURFACE READ ERROR", type(e).__name__, e)
    print("  target host vector (operator six-site CSV):", GL_TARGET)
    if SIX_SITE_CSV.is_file():
        rows = [r for r in csv.DictReader(SIX_SITE_CSV.open(encoding="utf-8-sig")) if "GL-ZaH" in ",".join(r.values())]
        print("  six-site CSV GL-ZaH row:", rows[:1])
    if GL_PARAM.is_file():
        print(f"  private param sha {sha(GL_PARAM)} ({'PASS' if sha(GL_PARAM) == GL_PARAM_SHA else 'MISMATCH'})")
        p = json.loads(GL_PARAM.read_text())["parameters"]
        names = [str(x).strip() for x in p["fates_pftname"]["data"]]; m = p["fates_hlm_pft_map"]["data"]
        for h in (9, 11, 12):
            row = m[h - 1]; print(f"    host {h} -> " + ", ".join(f"{names[i]} {v}" for i, v in enumerate(row) if v))
    else:
        print("  private param MISSING", GL_PARAM)


def self_test():
    assert nml("  fsurdat = '/a.nc'\n spinup_state = 2\n", "fsurdat") == ["/a.nc"]
    assert nml("x = 1\n", "y") == []
    assert sum(GL_TARGET.values()) == 100
    assert list(RUNNING) == ["DE-Gri", "DE-RuR", "ES-Agu"]
    print("STAGE05B SELF-TEST PASS (no HPC, no files)")


if __name__ == "__main__":
    if sys.argv[1:] == ["self-test"]: self_test(); sys.exit(0)
    co2 = co2_table()
    for fn in (lambda: audit_running(co2), it_tor_f1, it_tor_soil, lambda: gl_zah(co2)):
        try: fn()
        except Exception as e: print("SECTION ERROR", type(e).__name__, e)
    print("\nSTAGE05B READ-ONLY COMPLETE | nothing created, edited or submitted")
