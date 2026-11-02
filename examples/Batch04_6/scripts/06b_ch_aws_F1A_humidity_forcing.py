#!/usr/bin/env python3
"""Batch04 CH-Aws Stage06B: option-A humidity forcing F1A as detached annual DATM files. Never creates a case.

Rule (operator option A, 2 Nov 2026; counts from Stage06A)
  target  VPD_F_QC = 1 (MDS-filled) and RH_F < 10 % and RH_ERA - RH_F >= 50 points, at half-hours where the base
          DATM still carries the FLUXMET value (QBOT = q(TA_F, VPD_F, PSRF) bit for bit, TBOT = TA_F + 273.15)
  new     QBOT = q(TA_F, VPD_ERA, PSRF): packaged ERA VPD with the measured temperature and the file's pressure. This is
          the pairing FLUXNET itself uses for its QC2 half-hours. TBOT, PSRF and every other variable are unchanged.
The base is the CH-Aws_FATES_SPINUP500_11P stream (datm_11_provisional_dynamic_zbot_v1). Stage06A showed it equals
FLUXMET bit for bit at all 332,244 half-hours where VPD_F < es(TA_F). The 636 half-hours where VPD_F > es(TA_F)
(77 QC1, 559 QC2) were already replaced when that base was built (lowest RH there 28 %); they are kept as built.
Expected: about 65 target half-hours in 2007-2020. The exploratory RH42A_V8 changed the same 65 half-hours, and it is
the only old CH-Aws case that ran its full length.

Actions
  self-test                                       no HPC, temp files only
  check                                           READ ONLY
  build --confirm BUILD_CH_AWS_F1A_FORCING        new folder only
Output: experiments/NonCompetitionObserved22/Batch04_6/CH-Aws_F1A_forcing_v1/
  CH-Aws_DATM_<year>_F1A.nc       edited years only
  annual_input_plan.json          19 years, path + sha256 + kind
  manifest_PRIVATE.json           every edit with before/after values; licensed-derived, never commit
"""
import argparse, hashlib, importlib.util, json, re, shutil, sys, tempfile
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

B = Path("/iridisfs/scratch/ly3n24/CLM_FATES")
HERE = Path(__file__).resolve().parent
S06A = HERE / "06a_ch_aws_humidity_scan_case_surface_READONLY.py"
S06A_SHA = "3ff21742f4d5032ab841ab75534443a94c4220b0869b31f8c619e2f7e415b1c1"
BASE_CASE = B / "cases/CH-Aws_FATES_SPINUP500_11P"
BASE_DIR = B / "sites/MY_EC_SITE/CH-Aws/forcing/datm_11_provisional_dynamic_zbot_v1"
OUT = B / "experiments/NonCompetitionObserved22/Batch04_6/CH-Aws_F1A_forcing_v1"
PLAN, MANIFEST = OUT / "annual_input_plan.json", OUT / "manifest_PRIVATE.json"
ACK = "BUILD_CH_AWS_F1A_FORCING"
A6 = None   # module 06a (scan, physics, constants)


def need(x, msg):
    if not x: raise RuntimeError(msg)


def utc(): return datetime.now(timezone.utc).isoformat()


def sha(p):
    h = hashlib.sha256()
    with Path(p).open("rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""): h.update(b)
    return h.hexdigest()


def load06a():
    global A6
    need(S06A.is_file() and sha(S06A) == S06A_SHA, "06a missing or sha differs (it supplies the FLUXMET scan)")
    spec = importlib.util.spec_from_file_location("s06a", S06A)
    A6 = importlib.util.module_from_spec(spec); spec.loader.exec_module(A6)


def base_files():
    doc = BASE_CASE / "CaseDocs/datm.streams.xml"
    need(doc.is_file(), "base case stream XML missing " + str(doc))
    blocks = [x for x in ET.parse(doc).getroot().iter("stream_info") if x.get("name") == "CLM_USRDAT.UNSET"]
    need(len(blocks) == 1, "base USRDAT stream count")
    files = [Path((x.text or "").strip()) for x in blocks[0].find("datafiles")]
    yrs = [int(re.search(r"_DATM_(\d{4})", f.name).group(1)) for f in files]
    need(yrs == list(range(A6.FIRST, A6.LAST + 1)), f"base years {yrs[:1]}..{yrs[-1:]}")
    need(all(f.parent == BASE_DIR and f.is_file() and not f.is_symlink() for f in files), "base files not all in " + str(BASE_DIR))
    return files


def read_datm(files):
    import numpy as np
    from netCDF4 import Dataset
    T, Q, P = (np.full((len(files), A6.NH), np.nan) for _ in range(3))
    for j, f in enumerate(files):
        with Dataset(str(f)) as ds:
            for arr, k in ((T, "TBOT"), (Q, "QBOT"), (P, "PSRF")):
                need(ds.variables[k].shape == (A6.NH, 1, 1), f"{f.name} {k} shape {ds.variables[k].shape}")
                arr[j] = np.ma.filled(np.ma.asarray(ds.variables[k][:]).astype(float), np.nan).ravel()
    return T, Q, P


def targets(A, M, T, Q, P):
    """Main-rule half-hours that the base still carries unchanged, and their new QBOT / RH."""
    import numpy as np
    with np.errstate(invalid="ignore"):
        qf = A6.q_from(A["TA_F"], A["VPD_F"], P)
        aligned = np.abs(T - (A["TA_F"] + 273.15)) < 0.01
        carries = np.isfinite(qf) & (np.abs(Q - qf) <= 1e-8) & aligned
        tgt = M & carries
        qnew = A6.q_from(A["TA_F"], A["VPD_ERA"], P)
        rh_old, rh_new = A6.rh_from_q(Q, T, P), A6.rh_from_q(qnew, T, P)
        neg = np.isfinite(A["VPD_F"]) & (A["VPD_F"] > A6.es_hpa(A["TA_F"]))
    return {"tgt": tgt, "qnew": qnew, "rh_old": rh_old, "rh_new": rh_new, "kept": M & ~carries, "misaligned": ~aligned & np.isfinite(T),
            "neg": neg}


def stats(x):
    import numpy as np
    return {"n": int(x.size), "min": round(float(np.min(x)), 2), "median": round(float(np.median(x)), 2), "max": round(float(np.max(x)), 2)} if x.size else {"n": 0}


def check(show=True):
    import numpy as np
    load06a()
    files = base_files()
    src = [p for p in A6.SITE.rglob(A6.SOURCE_NAME) if p.is_file() and not p.is_symlink()]
    need(len(src) == 1 and src[0].stat().st_size == A6.SOURCE_BYTES, f"FLUXMET source not found uniquely with Stage02J size: {src}")
    A, seen, labels, meta = A6.scan(src[0])
    need(meta["rows"] == A6.SOURCE_ROWS and meta["feb29_rows"] == 240 and bool(seen.all()), f"FLUXMET row accounting {meta}")
    s, M, rhf, rhe, gap = A6.humidity_stats(A)
    T, Q, P = read_datm(files)
    t = targets(A, M, T, Q, P)
    tgt = t["tgt"]; n = int(tgt.sum())
    need(1 <= n <= s["main_n"], f"target count {n} outside 1..{s['main_n']}")
    need(bool(np.all(np.isfinite(t["qnew"][tgt]))), "new QBOT not finite at a target")
    need(bool(np.all((t["rh_new"][tgt] > 1) & (t["rh_new"][tgt] <= 100))), "new RH outside (1, 100] at a target")
    per_year = {A6.FIRST + j: int(tgt[j].sum()) for j in range(tgt.shape[0]) if tgt[j].any()}
    mis_neg = int((t["misaligned"] & t["neg"] & (A["VPD_F_QC"] == 1)).sum())
    info = {"fluxmet": str(src[0]), "base_dir": str(BASE_DIR), "main_rule_n": s["main_n"], "targets_n": n, "targets_per_year": per_year,
            "kept_as_built_n": int(t["kept"].sum()), "kept_as_built_rh_base": stats(t["rh_old"][t["kept"]]),
            "target_rh_before": stats(t["rh_old"][tgt]), "target_rh_after": stats(t["rh_new"][tgt]),
            "target_rh_era": stats(rhe[tgt]), "tbot_misaligned_n": int(t["misaligned"].sum()),
            "tbot_misaligned_that_are_QC1_VPD_above_es": mis_neg}
    if show:
        print("STAGE06B CHECK (read only) | CH-Aws F1A humidity rule")
        print(f"  base {BASE_DIR} (19 files 2006-2024) | FLUXMET {src[0].name} rows {meta['rows']}")
        print(f"  main rule {s['main_n']} HH = {n} targets (base still carries FLUXMET value) + {info['kept_as_built_n']} kept as built"
              f" (base RH there {info['kept_as_built_rh_base']})")
        print(f"  targets per year {per_year}")
        print(f"  target RH before {info['target_rh_before']} | after {info['target_rh_after']} | ERA's own RH {info['target_rh_era']}")
        print(f"  TBOT differs from TA_F at {info['tbot_misaligned_n']} HH, of which {mis_neg} are QC1 half-hours with VPD_F > es (built from ERA)")
    return {"files": files, "A": A, "labels": labels, "T": T, "Q": Q, "P": P, "t": t, "rhf": rhf, "rhe": rhe, "info": info}


def edit_year(src, dst, idx, qvals):
    """Copy src to dst, set QBOT at idx, prove that nothing else changed."""
    import numpy as np
    from netCDF4 import Dataset
    need(not dst.exists(), "exists " + str(dst))
    shutil.copyfile(src, dst)
    with Dataset(str(dst), "r+") as ds:
        v = ds.variables["QBOT"]
        for i, q in zip(idx, qvals): v[int(i), 0, 0] = q
        ds.setncattr("b04_ch_aws_f1a_edit", f"QBOT at {len(idx)} half-hours = q(TA_F, VPD_ERA, PSRF) where VPD_F_QC=1, RH_F<10 %, "
                                            f"RH_ERA-RH_F>=50; source sha {sha(src)}; {utc()}")
    with Dataset(str(src)) as a, Dataset(str(dst)) as b:
        need(set(a.variables) == set(b.variables), "variable set changed")
        for k in a.variables:
            x, y = np.ma.asarray(a.variables[k][:]), np.ma.asarray(b.variables[k][:])
            need(x.shape == y.shape, "shape changed " + k)
            if k == "QBOT":
                d = np.flatnonzero(np.ma.filled(x != y, True).ravel())
                need(sorted(d.tolist()) == sorted(int(i) for i in idx), f"QBOT changed at {d.tolist()[:5]}.. not exactly the targets")
                need(np.allclose(y.ravel()[idx], qvals, rtol=1e-6, atol=0), "QBOT not written")
            else:
                need(np.ma.allequal(x, y), "unexpected change in " + k)


def build(confirm):
    import numpy as np
    need(confirm == ACK, "requires --confirm " + ACK)
    if OUT.exists():
        plan = json.loads(PLAN.read_text())
        for r in plan["years"]: need(sha(r["path"]) == r["sha256"], "existing plan sha mismatch " + r["path"])
        print("F1A EXISTS AND VERIFIED", OUT, "| edited years", [r["year"] for r in plan["years"] if r["kind"] == "F1A_edited"]); return
    c = check()
    files, t, A, labels = c["files"], c["t"], c["A"], c["labels"]
    base_sha = {str(f): sha(f) for f in files}
    tmp = OUT.with_name(OUT.name + ".partial"); need(not tmp.exists(), "leftover " + str(tmp) + "; inspect")
    tmp.mkdir(parents=True)
    years, edits = [], []
    for j, f in enumerate(files):
        y = A6.FIRST + j
        idx = np.flatnonzero(t["tgt"][j])
        if idx.size:
            name = f"CH-Aws_DATM_{y}_F1A.nc"
            edit_year(f, tmp / name, idx, t["qnew"][j, idx])
            years.append({"year": y, "kind": "F1A_edited", "path": str(OUT / name), "sha256": sha(tmp / name), "base": str(f),
                          "base_sha256": base_sha[str(f)], "edited_HH": int(idx.size)})
            for i in idx:
                edits.append({"label": labels[j, i], "year": y, "index": int(i), "TA_F": A["TA_F"][j, i], "VPD_F": A["VPD_F"][j, i],
                              "VPD_ERA": A["VPD_ERA"][j, i], "TA_ERA": A["TA_ERA"][j, i], "PSRF": c["P"][j, i],
                              "QBOT_before": c["Q"][j, i], "QBOT_after": float(t["qnew"][j, i]),
                              "RH_before": round(float(t["rh_old"][j, i]), 3), "RH_after": round(float(t["rh_new"][j, i]), 3),
                              "RH_ERA": round(float(c["rhe"][j, i]), 3)})
        else:
            years.append({"year": y, "kind": "historical_baseline", "path": str(f), "sha256": base_sha[str(f)]})
    for f in files: need(sha(f) == base_sha[str(f)], "base file changed during build " + str(f))
    rule = ("VPD_F_QC=1 & RH_F<10 % & RH_ERA-RH_F>=50 at half-hours the base still carries unchanged; "
            "QBOT = q(TA_F, VPD_ERA, PSRF); everything else unchanged")
    (tmp / PLAN.name).write_text(json.dumps({"site": "CH-Aws", "forcing": "F1A", "status": "OPERATOR_OPTION_A_EXPLORATORY",
        "rule": rule, "first": A6.FIRST, "last": A6.LAST, "years": years, "summary": c["info"], "created_utc": utc()}, indent=2, default=str) + "\n")
    (tmp / MANIFEST.name).write_text(json.dumps({"rule": rule, "fluxmet": c["info"]["fluxmet"], "edits": edits}, indent=2, default=float) + "\n")
    tmp.rename(OUT)
    print(f"F1A BUILT {OUT} | {len(edits)} QBOT values in {[r['year'] for r in years if r['kind'] == 'F1A_edited']} | plan {PLAN}")


def self_test():
    import numpy as np
    from netCDF4 import Dataset
    load06a()
    NH = A6.NH
    with tempfile.TemporaryDirectory() as d:
        d = Path(d); src = d / "CH-Aws_DATM_2007.nc"
        with Dataset(str(src), "w") as ds:
            ds.createDimension("time", NH); ds.createDimension("lat", 1); ds.createDimension("lon", 1)
            ta = np.full(NH, 5.0); vpd = np.full(NH, 2.0); p = np.full(NH, 80000.0)
            vpd[10] = 8.5                                                   # MDS fill: RH ~3 %
            vpd[20] = 9.0                                                   # VPD > es: base built from ERA
            q = A6.q_from(ta, vpd, p); q[20] = A6.q_from(np.array([5.0]), np.array([1.0]), np.array([80000.0]))[0]
            for k, v in (("TBOT", ta + 273.15), ("QBOT", q), ("PSRF", p), ("FSDS", np.full(NH, 100.0))):
                ds.createVariable(k, "f8", ("time", "lat", "lon"))[:] = v.reshape(NH, 1, 1)
        A = {k: np.full((1, NH), np.nan) for k in ("TA_F", "VPD_F", "VPD_ERA", "TA_ERA", "VPD_F_QC")}
        A["TA_F"][:] = 5.0; A["VPD_F"][0] = vpd; A["VPD_ERA"][:] = 1.0; A["TA_ERA"][:] = 5.0; A["VPD_F_QC"][:] = 0
        A["VPD_F_QC"][0, 10] = A["VPD_F_QC"][0, 20] = 1
        with np.errstate(invalid="ignore"):
            rhf, rhe = A6.rh_from_vpd(A["TA_F"], A["VPD_F"]), A6.rh_from_vpd(A["TA_ERA"], A["VPD_ERA"])
        M = (A["VPD_F_QC"] == 1) & (rhf < 10) & (rhe - rhf >= 50)
        assert M[0, 10] and M[0, 20] and int(M.sum()) == 2
        T, Q, P = read_datm([src])
        t = targets(A, M, T, Q, P)
        assert t["tgt"][0, 10] and not t["tgt"][0, 20] and int(t["tgt"].sum()) == 1 and t["kept"][0, 20]
        assert 80 < t["rh_new"][0, 10] <= 100 and t["rh_old"][0, 10] < 10
        idx = np.flatnonzero(t["tgt"][0])
        edit_year(src, d / "out.nc", idx, t["qnew"][0, idx])
        try: edit_year(src, d / "out.nc", idx, t["qnew"][0, idx]); raise AssertionError("overwrote")
        except RuntimeError: pass
    print("STAGE06B SELF-TEST PASS (target selection keeps base-built half-hours, ERA VPD pairing, whole-file diff; no HPC)")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("action", choices=("self-test", "check", "build"))
    ap.add_argument("--confirm", default="")
    a = ap.parse_args()
    {"self-test": self_test, "check": lambda: (check(), print("STAGE06B CHECK PASS | READ ONLY")), "build": lambda: build(a.confirm)}[a.action]()


if __name__ == "__main__":
    try: main()
    except RuntimeError as e: print("STAGE06B HOLD:", e, file=sys.stderr); sys.exit(2)
