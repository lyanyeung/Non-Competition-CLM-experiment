#!/usr/bin/env python3
"""Batch04 IT-Tor: detached S1 soil-organic surface candidate and a provenance-clean F1 rebuild. Never creates a case.

S1 (soil). The inherited Stage02X IT-Tor surface has ORGANIC = 0 in all ten surface-data levels. Leolini et al. 2025
(Agric. For. Meteorol. 367:110486, Table 1 and Sect. 2.2; measured, from TOC/SOM) give topsoil SOC 64.7 Mg C/ha in
0-20 cm, bulk density 0.95 g/cm3. With the CTSM surface convention of 0.58 gC per g organic matter this is
    64.7 Mg C/ha = 6.47 kg C/m2 -> 32.35 kg C/m3 over 0.20 m -> 55.776 kg OM/m3.
In the pinned CTSM (d5ea9d0) SoilStateInitTimeConstMod gives each model layer the surface-data level that contains
its node depth; with 20SL_8.5m the model layers 1-4 are exactly 0-0.20 m and take surface levels 1-4, layer 5
(0.20-0.32 m) takes level 5. S1 therefore sets ORGANIC levels 1-4 = 55.776 and keeps levels 5-10 = 0 (no data below
20 cm). The model then holds exactly the measured 6.47 kg C/m2 in 0-20 cm. All other variables are unchanged.

F1 (forcing). The existing candidate on IRIDIS6 (result/candidate.nc) was not written by the repository script
05a, whose run copy is no longer on disk. f1-rebuild runs the repository 05a into a new empty folder and compares
the result with the existing candidate variable by variable, so the file a case will use has a known generator.

Actions
  self-test                                          no HPC, temp files only
  check                                              READ ONLY
  build-s1   --confirm BUILD_IT_TOR_S1_SOIL_CANDIDATE   new folder only
  f1-rebuild --confirm REBUILD_IT_TOR_F1_WITH_REPO_05A  new folder only
"""
import argparse, hashlib, json, math, re, shutil, subprocess, sys, tempfile
from datetime import datetime, timezone
from pathlib import Path

B = Path("/iridisfs/scratch/ly3n24/CLM_FATES")
CTSM = B / "CTSM"
CTSM_HEAD = "d5ea9d0136530370a62ef267ccfaff6f001ef914"
HOME = Path.home()
HERE = Path(__file__).resolve().parent
SURF_SRC = B / "experiments/Batch04_GitHub_PFT_Gz7kLAkn/IT-Tor_B04_GITHUBPFT_POINT_CANDIDATE.nc"
SURF_SRC_SHA = "908b73f67f74333fa70fcd3b07d8500de14c70b4efdd1e6f36ea23bb4f8b7c7b"
S1_DIR = B / "experiments/NonCompetitionObserved22/Batch04_6/IT-Tor_S1_soil_organic_candidate_v1"
S1 = S1_DIR / "IT-Tor_B04_GITHUBPFT_S1_ORGANIC_POINT_CANDIDATE.nc"
TEMPLATE = B / "cases/IT-Tor_FATES_SPINUP1000_S30SHARED"
SOC_MG_HA, DEPTH_M, C_FRAC = 64.7, 0.20, 0.58
OM_KG_M3 = SOC_MG_HA * 0.1 / DEPTH_M / C_FRAC          # 55.7759 kg organic matter / m3
F1_05A = HERE / "05a_it_tor_make_f1_candidate.py"
F1_05A_SHA = "997f237bec468bca97c75a42fea2523c32af8a85974b529375cfc93c9e23b9bd"
STAGE03B = HOME / "ICOS_Batch04_stage03b_reuse_PbMYw9CH/results/stage03b_four_site_reused_stage28_DATM_lineage.json"
CONTEXT = HOME / "ICOS_Batch04_stage03j_vzDUtipV/results/stage03j_IT_Tor_54_context_MDS_ERA_fields_PRIVATE.csv"
ACK_S1, ACK_F1 = "BUILD_IT_TOR_S1_SOIL_CANDIDATE", "REBUILD_IT_TOR_F1_WITH_REPO_05A"


def need(x, msg):
    if not x: raise RuntimeError(msg)


def sha(p):
    h = hashlib.sha256()
    with Path(p).open("rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""): h.update(b)
    return h.hexdigest()


def utc(): return datetime.now(timezone.utc).isoformat()


def run(args, cwd=None, timeout=900):
    p = subprocess.run([str(a) for a in args], cwd=cwd, text=True, capture_output=True, timeout=timeout)
    return p.returncode, (p.stdout + p.stderr).strip()


# ------------------------------------------------------------------ CTSM layer mapping (pinned d5ea9d0 formulas)
def surface_levels(n=10):
    z = [0.025 * (math.exp(0.5 * (j - 0.5)) - 1.0) for j in range(1, n + 2)]          # zsoifl(1..n+1)
    zi = [0.0] + [0.5 * (z[j] + z[j + 1]) for j in range(n)]                          # zisoifl(0..n)
    return z, zi


def model_layers_20SL(nlevsoi=20):
    dz = []
    for j in range(1, nlevsoi + 1):
        if j <= 4: dz.append(j * 0.02)
        elif j <= 13: dz.append(dz[3] + (j - 4) * 0.04)
        else: dz.append(dz[12] + (j - 13) * 0.10)
    zi = [0.0]
    for d in dz: zi.append(zi[-1] + d)
    zs = [0.5 * (zi[j] + zi[j + 1]) for j in range(nlevsoi)]
    return dz, zi, zs


def mapping():
    """Surface-data level (1-based) used by each model soil layer, as in SoilStateInitTimeConstMod."""
    _, zfl = surface_levels(); dz, zi, zs = model_layers_20SL(); out = []
    for lev, z in enumerate(zs, start=1):
        if lev == 1 or z <= zfl[1]: k = 1
        elif z > zfl[10]: k = 10
        else: k = next(j + 1 for j in range(1, 10) if zfl[j] < z <= zfl[j + 1])
        out.append((lev, zi[lev - 1], zi[lev], z, k))
    return out


def s1_profile():
    return [round(OM_KG_M3, 4)] * 4 + [0.0] * 6


def integrated_om(profile):
    return sum((top_bot[2] - top_bot[1]) * profile[top_bot[4] - 1] for top_bot in mapping() if top_bot[2] <= DEPTH_M + 1e-9)


# ------------------------------------------------------------------ S1
def make_s1(source, partial, profile):
    from netCDF4 import Dataset
    import numpy as np
    need(not partial.exists(), "partial exists")
    shutil.copyfile(source, partial)
    with Dataset(str(partial), "r+") as ds:
        v = ds.variables["ORGANIC"]; need(v.dimensions[0] == "nlevsoi" and v.shape[0] == 10, "ORGANIC is not nlevsoi x 10")
        a = np.zeros(v.shape, dtype=v.dtype)
        for k, x in enumerate(profile): a[k, ...] = x
        v[:] = a
        ds.setncattr("b04_it_tor_s1_edit", f"ORGANIC levels 1-4 = {profile[0]} kg/m3 (64.7 Mg C/ha 0-20 cm, Leolini et al. 2025, "
                                           f"0.58 gC/gOM), levels 5-10 = 0; source sha {sha(source)}; {utc()}")
    with Dataset(str(source)) as a, Dataset(str(partial)) as b:
        need(set(a.variables) == set(b.variables), "variable set changed")
        for k in a.variables:
            x, y = np.ma.asarray(a.variables[k][:]), np.ma.asarray(b.variables[k][:])
            if k == "ORGANIC":
                need(np.allclose(np.ma.filled(y, np.nan).reshape(10, -1)[:, 0], profile, atol=1e-4), "ORGANIC not written")
            else:
                need(x.shape == y.shape and np.ma.allequal(x, y), "unexpected change in " + k)


def read_organic(path):
    from netCDF4 import Dataset
    import numpy as np
    with Dataset(str(path)) as ds:
        v = ds.variables["ORGANIC"]
        return np.ma.asarray(v[:]).reshape(10, -1)[:, 0].astype(float).tolist(), getattr(v, "units", "")


def paramfile_values():
    lnd = (TEMPLATE / "CaseDocs/lnd_in").read_text()
    m = re.search(r"(?im)^\s*paramfile\s*=\s*'([^']+)'", lnd); need(m is not None, "template paramfile not found")
    from netCDF4 import Dataset
    import numpy as np
    with Dataset(m.group(1)) as ds:
        get = lambda k: float(np.ma.asarray(ds.variables[k][:]).ravel()[0]) if k in ds.variables else None
        return m.group(1), get("organic_max"), get("om_frac_sf")


def build_s1(confirm):
    need(confirm == ACK_S1, "requires --confirm " + ACK_S1)
    if S1_DIR.exists():
        man = json.loads((S1_DIR / "manifest.json").read_text())
        need(man.get("surface_sha256") == sha(S1), "existing S1 sha mismatch"); print("S1 EXISTS AND VERIFIED", S1, man["surface_sha256"]); return
    need(SURF_SRC.is_file() and sha(SURF_SRC) == SURF_SRC_SHA, "IT-Tor Stage02X surface missing or sha differs")
    org, _ = read_organic(SURF_SRC); need(all(x == 0 for x in org), "source ORGANIC is not all zero; stop and review")
    m = mapping(); need([k for (_, _, _, _, k) in m[:5]] == [1, 2, 3, 4, 5], f"layer mapping changed: {m[:5]}")
    prof = s1_profile()
    tmp = S1_DIR.with_name(S1_DIR.name + ".partial"); need(not tmp.exists(), "leftover " + str(tmp)); tmp.mkdir(parents=True)
    make_s1(SURF_SRC, tmp / S1.name, prof)
    om = integrated_om(prof)
    (tmp / "manifest.json").write_text(json.dumps({"site": "IT-Tor", "status": "DETACHED_S1_SOIL_SENSITIVITY_NOT_RELEASED",
        "source": str(SURF_SRC), "source_sha256": SURF_SRC_SHA, "surface": str(S1), "surface_sha256": sha(tmp / S1.name),
        "changed_variables": ["ORGANIC"], "ORGANIC_kg_m3_levels_1_10": prof,
        "basis": "Leolini et al. 2025 AFM 367:110486 Table 1 / Sect. 2.2: SOC 64.7 Mg C/ha 0-20 cm (measured), BD 0.95",
        "conversion": "0.58 gC per g organic matter (CTSM surface ORGANIC units)", "ctsm_head": CTSM_HEAD,
        "model_layer_mapping_20SL_8p5m": m, "model_integrated_OM_0_20cm_kg_m2": om, "model_integrated_C_0_20cm_kg_m2": om * C_FRAC,
        "below_20cm": "0 (no measurement)", "created_utc": utc()}, indent=2) + "\n")
    need(sha(SURF_SRC) == SURF_SRC_SHA, "source changed during build")
    tmp.rename(S1_DIR)
    print(f"S1 BUILT {S1} sha {sha(S1)} | ORGANIC {prof} | model 0-20 cm C {om * C_FRAC:.4f} kg/m2")


# ------------------------------------------------------------------ F1
def existing_f1():
    return sorted(HOME.glob("ICOS_Batch04_IT_Tor_F1.*/result/candidate.nc"))


def compare_nc(a_path, b_path):
    from netCDF4 import Dataset
    import numpy as np
    diffs = []
    with Dataset(str(a_path)) as a, Dataset(str(b_path)) as b:
        if set(a.variables) != set(b.variables): diffs.append(f"variable sets differ {sorted(set(a.variables) ^ set(b.variables))}")
        for k in sorted(set(a.variables) & set(b.variables)):
            x, y = np.ma.asarray(a.variables[k][:]), np.ma.asarray(b.variables[k][:])
            if x.shape != y.shape or not np.ma.allequal(x, y):
                n = int(np.sum(np.ma.filled(x != y, True))) if x.shape == y.shape else -1
                diffs.append(f"{k}: {n} values differ")
    return diffs


def f1_rebuild(confirm):
    need(confirm == ACK_F1, "requires --confirm " + ACK_F1)
    need(F1_05A.is_file() and sha(F1_05A) == F1_05A_SHA, "repository 05a missing or sha differs")
    need(STAGE03B.is_file() and CONTEXT.is_file(), "Stage03B report or Stage03J private context missing")
    work = Path(tempfile.mkdtemp(prefix="ICOS_Batch04_IT_Tor_F1_05a.", dir=HOME))
    (work / "test").mkdir(); (work / "result").mkdir()
    rc, out = run([sys.executable, "-B", F1_05A, "--self-test", "--test-dir", work / "test"]); print(out); need(rc == 0, "05a self-test failed")
    rc, out = run([sys.executable, "-B", F1_05A, "--stage03b", STAGE03B, "--context", CONTEXT, "--out-dir", work / "result"]); print(out)
    need(rc == 0, "05a run failed")
    new = work / "result/IT-Tor_DATM_2025_F1.nc"; need(new.is_file(), "05a output missing")
    print("NEW F1 (repository 05a):", new, sha(new))
    for old in existing_f1():
        d = compare_nc(old, new)
        print(f"  vs existing {old} sha {sha(old)}: {'IDENTICAL DATA (all variables)' if not d else 'DIFFERENT: ' + '; '.join(d)}")
    print("Use the 05a output (with manifest_PRIVATE.json) for any IT-Tor F1 case; no case or job created.")


# ------------------------------------------------------------------ check
def check():
    print("==== IT-Tor S1 / F1 CHECK (read only) ====")
    rc, head = run(["git", "-C", CTSM, "rev-parse", "HEAD"]); print("CTSM HEAD", head, "PINNED" if head == CTSM_HEAD else "DIFFERS FROM d5ea9d0")
    rc, st = run(["git", "-C", CTSM, "status", "--short", "--", "src/biogeophys/SoilStateInitTimeConstMod.F90", "src/main/initVerticalMod.F90"])
    print("local modifications:", st or "none")
    f = CTSM / "src/biogeophys/SoilStateInitTimeConstMod.F90"
    if f.is_file():
        L = f.read_text(errors="replace").splitlines()
        print("SoilStateInitTimeConstMod 455-496 (model-layer search):")
        for j in range(454, min(len(L), 496)): print(f"  {j + 1}: {L[j]}")
    g = CTSM / "src/main/initVerticalMod.F90"
    if g.is_file():
        L = g.read_text(errors="replace").splitlines()
        print("initVerticalMod node-depth lines (S1 assumes thickness-based zsoi = layer midpoint):")
        for j, x in enumerate(L):
            if re.search(r"^\s*zsoi\s*\(\s*j\s*\)\s*=|^\s*zisoi\s*\(\s*j\s*\)\s*=", x): print(f"  {j + 1}: {x.strip()}")
    need(SURF_SRC.is_file(), "source surface missing")
    print("source surface", SURF_SRC, "sha", "PASS" if sha(SURF_SRC) == SURF_SRC_SHA else "MISMATCH")
    org, units = read_organic(SURF_SRC); print("source ORGANIC", org, "| units", units)
    pf, omax, sf = paramfile_values(); print(f"paramfile {pf} | organic_max {omax} | om_frac_sf {sf}")
    _, zfl = surface_levels(); print("surface-data interfaces (m):", [round(x, 6) for x in zfl])
    print("model layer -> surface level (20SL_8.5m, node-depth rule):")
    for lev, top, bot, z, k in mapping()[:8]: print(f"  layer {lev:2d} {top:.2f}-{bot:.2f} m node {z:.3f} -> level {k}")
    prof = s1_profile(); om = integrated_om(prof)
    print(f"S1 ORGANIC levels 1-10 = {prof} kg/m3 | om_frac top = {prof[0] / omax * sf:.3f}" if omax else f"S1 {prof}")
    print(f"S1 model 0-20 cm: OM {om:.4f} kg/m2, C {om * C_FRAC:.4f} kg/m2 (target {SOC_MG_HA / 10:.3f})")
    print("S1 folder:", "EXISTS" if S1_DIR.exists() else "not built", S1_DIR)
    print("05a repository copy:", sha(F1_05A) if F1_05A.is_file() else "MISSING")
    for p in existing_f1():
        print("existing F1 candidate:", p, sha(p), "| folder files:", sorted(x.name for x in p.parent.iterdir()))
        for x in sorted(p.parent.parent.glob("*")): print("   ", x.name)
    print("CHECK COMPLETE | nothing written")


def self_test():
    import numpy as np
    from netCDF4 import Dataset
    _, zfl = surface_levels()
    assert [round(x, 6) for x in zfl] == [0.0, 0.017513, 0.045092, 0.090562, 0.165529, 0.28913, 0.492912, 0.828893, 1.382831, 2.296121, 3.801882]
    dz, zi, zs = model_layers_20SL()
    assert abs(zi[4] - 0.20) < 1e-12 and [round(x, 2) for x in dz[:6]] == [0.02, 0.04, 0.06, 0.08, 0.12, 0.16]
    assert [k for (_, _, _, _, k) in mapping()[:6]] == [1, 2, 3, 4, 5, 6]
    assert abs(OM_KG_M3 - 55.7759) < 1e-4 and abs(integrated_om(s1_profile()) * C_FRAC - 6.47) < 1e-3
    with tempfile.TemporaryDirectory() as d:
        d = Path(d); src = d / "s.nc"
        with Dataset(str(src), "w") as ds:
            for n, k in (("nlevsoi", 10), ("lsmlat", 1), ("lsmlon", 1)): ds.createDimension(n, k)
            for n, v in (("ORGANIC", 0.0), ("PCT_SAND", 43.0), ("PCT_CLAY", 18.0)): ds.createVariable(n, "f8", ("nlevsoi", "lsmlat", "lsmlon"))[:] = v
        make_s1(src, d / "n.nc", s1_profile())
        assert read_organic(d / "n.nc")[0][:5] == [55.7759] * 4 + [0.0] and compare_nc(src, src) == []
        assert any("ORGANIC" in x for x in compare_nc(src, d / "n.nc"))
    print("STAGE05D SELF-TEST PASS (layer mapping, 6.47 kg C/m2 closure, S1 edit with whole-file diff; no HPC)")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("action", choices=("self-test", "check", "build-s1", "f1-rebuild"))
    ap.add_argument("--confirm", default="")
    a = ap.parse_args()
    {"self-test": self_test, "check": check, "build-s1": lambda: build_s1(a.confirm), "f1-rebuild": lambda: f1_rebuild(a.confirm)}[a.action]()


if __name__ == "__main__":
    try: main()
    except RuntimeError as e: print("STAGE05D HOLD:", e, file=sys.stderr); sys.exit(2)
