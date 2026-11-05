#!/usr/bin/env python3
"""Script 20 normal-run for KEEP_NLF sites whose ORIGINAL Normal lnd_in has no spinup_state line, while the
regenerated namelist writes spinup_state = 0.

2026-11-04 16:34 UTC, script 20 normal-run: 8 sites HOLD with
  "no overlay reproduces the AD lnd_in: ... clm_inparm.spinup_state (AD=None NEW='0')"
  (CA-Ca3, CA-LP1, US-GLE, US-Mpj, US-NR1, US-Vcm, US-Vcp, US-Wjs); every other key matched the original Normal.
"Absent" and "0" mean the same thing: with CLM_ACCELERATED_SPINUP off CTSM uses spinup_state 0, and script 20 itself
accepts "" or "0" for the new Normal. Only that one difference is accepted here (original absent -> new exactly 0);
every other check of script 20 normal_prepare / submit is unchanged.

The failed attempts left a half-made Normal case (phase PREPARE_ATTEMPTED, never set up/submitted), so script 20
refuses ("path exists"). clean-failed removes exactly that attempt after checks and writes the file list to the
ledger first (same rule as purge-old: dry run unless confirmed).

  clean-failed [--confirm REMOVE_FAILED_NORMAL_PREPARE]   remove the PREPARE_ATTEMPTED Normal case dir, its
                                                           <OUT>/<case> folder (run/ with copied restarts) and archive
  normal-run                                               script 20 normal_prepare + submit with the tolerance
  status                                                   script 20 status
Put next to 20 (needs 20 -> 18 -> 13 -> 09 in the same folder).
"""
from __future__ import annotations

import argparse
import importlib.util
import shutil
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEFAULT = ["CA-Ca3", "CA-LP1", "US-GLE", "US-Mpj", "US-NR1", "US-Vcm", "US-Vcp", "US-Wjs"]
CONFIRM = "REMOVE_FAILED_NORMAL_PREPARE"
M20 = T = R = None


def load():
    global M20, T, R
    spec = importlib.util.spec_from_file_location("rerun20", HERE / "20_needleleaf_rerun_AD400_NORMAL400.py")
    M20 = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(M20)
    M20.load()
    T, R = M20.T, M20.R
    orig = T.preview_verified

    def preview_verified(case, ref_lnd, allowed=()):
        ov, a, n, diff = orig(case, ref_lnd, list(allowed) + [".spinup_state"])
        for k in [k for k in diff if k.endswith(".spinup_state")]:
            if not (a.get(k) is None and str(n.get(k)).strip("'\" ") == "0"):
                R.fail(f"{k}: original {a.get(k)!r}, new {n.get(k)!r}; only absent -> 0 is accepted")
            print(f"  accepted: {k} absent in the original Normal, 0 in the new one (CTSM default)", flush=True)
        return ov, a, n, [k for k in diff if not k.endswith(".spinup_state")]

    T.preview_verified = preview_verified          # M20.normal_prepare looks it up at call time


def clean_failed(site, confirm):
    i = M20.ident(site)
    case, name = i["n_case"], i["n"]
    top, arch = i["n_run"].parent, i["n_arch"]
    ph = M20.read_state(case).get("phase")
    if ph != "PREPARE_ATTEMPTED":
        print(f"{site}: {name} phase {ph}; nothing to clean", flush=True)
        return
    if M20.jobs(name):
        R.fail(f"{name}: jobs in the queue")
    cs = (case / "CaseStatus").read_text(errors="replace") if (case / "CaseStatus").is_file() else ""
    if "case.submit" in cs or "case.run" in cs:
        R.fail(f"{name}: CaseStatus shows a submit/run; not a failed prepare")
    if not name.endswith(M20.SUFFIX) or case.parent != R.CASES or top.parent != R.OUT:
        R.fail(f"{name}: unexpected paths {case} {top}")
    exe = Path(R.xq(case, "EXEROOT")) if (case / "env_build.xml").is_file() else None
    if exe and (exe == top or top in exe.parents):
        R.fail(f"{name}: EXEROOT {exe} is inside {top}; build dirs are never removed")
    if (top / "bld").exists():
        R.fail(f"{top}/bld exists; build dirs are never removed")
    if arch.is_dir() and any(arch.rglob("*.nc")):
        R.fail(f"{arch} holds .nc output; not a failed prepare")
    paths = [p for p in (case, top, arch) if p.exists()]
    files = [(f, f.stat().st_size) for p in paths for f in sorted(p.rglob("*")) if f.is_file()]
    gb = sum(s for _, s in files) / 1e9
    print(f"{site}: {name} PREPARE_ATTEMPTED | {len(files)} files, {gb:.2f} GB in {', '.join(map(str, paths))}",
          flush=True)
    if confirm != CONFIRM:
        print(f"  dry run; add --confirm {CONFIRM}", flush=True)
        return
    log = M20.ledger() / f"{site}_failed_normal_prepare_removed_{R.utc().replace(':', '')}.txt"
    log.write_text("".join(f"{f}\t{s}\n" for f, s in files))
    for p in paths:
        shutil.rmtree(p)
    print(f"  REMOVED; file list: {log}", flush=True)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("action", choices=("clean-failed", "normal-run", "status"))
    ap.add_argument("--sites", nargs="+", default=DEFAULT)
    ap.add_argument("--confirm", default="")
    a = ap.parse_args(argv)
    load()
    bad = 0
    for s in a.sites:
        try:
            {"clean-failed": lambda x: clean_failed(x, a.confirm), "normal-run": M20.normal_run,
             "status": M20.status}[a.action](s)
        except Exception as exc:
            bad += 1
            print(f"{s}: HOLD {str(exc).strip()[:900]}", flush=True)
    print(f"\n{len(a.sites) - bad}/{len(a.sites)} OK, {bad} HOLD", flush=True)
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
