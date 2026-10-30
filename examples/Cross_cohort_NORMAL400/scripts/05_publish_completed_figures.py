#!/usr/bin/env python3
"""Publish generated PNG plots only, after the retry job has finished.

Uses the retry summary and its prior-run provenance. Does not upload model,
observation or derived CSV files. Clones a fresh repo; never changes the user's
existing checkout. Run on the login node with working GitHub authentication.
"""
import argparse
import csv
import hashlib
import json
import re
import shutil
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path

REPO = "git@github.com:lyanyeung/Non-Competition-CLM-experiment.git"
SAFE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")
SUFFIXES = ("_01_carbon_pools_AD400_NORMAL400.png",
            "_02_carbon_pools_NORMAL400_panels.png", "_GPP_NEE_monthly_overview.png")


def read_rows(root):
    with (root / "all_sites_summary.csv").open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def check_name(name):
    if not name or not SAFE.fullmatch(name) or name in (".", ".."):
        raise ValueError("Unsafe or missing site/case identifier: " + repr(name))
    return name


def pngs(root, site, case):
    root = root.resolve()
    folder = (root / check_name(site) / check_name(case)).resolve()
    if root not in folder.parents:
        raise ValueError("Input figure directory escapes its run root")
    result = {}
    for suffix in SUFFIXES:
        p = folder / (site + suffix)
        if p.is_file():
            real = p.resolve()
            if folder not in real.parents or real.stat().st_size > 95_000_000:
                raise ValueError("Unsafe image path or image too large: " + str(p))
            with real.open("rb") as f:
                if f.read(8) != b"\x89PNG\r\n\x1a\n":
                    raise ValueError("Not a PNG file: " + str(p))
            result[suffix] = real
    return result


def inventory(run):
    run = run.resolve()
    info = json.loads((run / "RUN_INFO.json").read_text(encoding="utf-8"))
    fallback = [info["previous_root"]] if info.get("previous_root") else []
    old_roots = [Path(x).resolve() for x in info.get("previous_roots", fallback)]
    sources = {}
    for root in (*old_roots, run):
        for row in read_rows(root):
            site, case, ad = row.get("Site", ""), row.get("Normal_case", ""), row.get("AD_case", "")
            check_name(site); check_name(case)
            # A Normal case should not inherit figures from a different AD case.
            sources.setdefault((site, case), []).append((root, row, pngs(root, site, case)))
    selected = []
    for key, options in sorted(sources.items()):
        ad_names = {o[1].get("AD_case", "") for o in options if o[1].get("AD_case", "")}
        if len(ad_names) > 1:
            raise ValueError(f"Conflicting AD cases for {key}: {sorted(ad_names)}")
        # Take all figures from one coherent run. Prefer the retry on a tie.
        root, row, files = max(enumerate(options), key=lambda x: (len(x[1][2]), x[0]))[1]
        selected.append(((key[0], key[1], next(iter(ad_names), "")), root, row, files))
    return info, selected


def git(*args, cwd=None):
    p = subprocess.run(["git", *map(str, args)], cwd=cwd, text=True, capture_output=True)
    if p.returncode:
        raise RuntimeError("git " + " ".join(map(str, args)) + " failed:\n" + p.stderr[-3000:])
    return p.stdout.strip()


def require_job_finished(job):
    if not str(job).isdigit():
        raise ValueError("retry job ID must contain digits only")
    p = subprocess.run(["sacct", "-n", "-P", "-j", str(job), "--format=JobIDRaw,State"],
                       text=True, capture_output=True, timeout=60)
    states = [x.split("|")[1].strip().split()[0].rstrip("+") for x in p.stdout.splitlines()
              if "|" in x and x.split("|")[0].strip() == str(job)]
    terminal = {"COMPLETED", "FAILED", "CANCELLED", "TIMEOUT", "OUT_OF_MEMORY",
                "NODE_FAIL", "PREEMPTED", "BOOT_FAIL", "DEADLINE", "REVOKED"}
    if p.returncode or len(states) != 1 or states[0] not in terminal:
        raise RuntimeError(f"Retry job {job} is not confirmed finished by sacct: {states}; {p.stderr.strip()}")
    return states[0]


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--run", required=True, type=Path, help="Finished retry output directory")
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--retry-job", help="Slurm ID of the finished retry job")
    mode.add_argument("--login", action="store_true", help="Use a completed direct login-node retry")
    ap.add_argument("--publish", action="store_true", help="Clone, commit and push derived PNGs to main")
    args = ap.parse_args()
    run = args.run.expanduser().resolve()
    state = require_job_finished(args.retry_job) if args.retry_job else "LOGIN_COMPLETE"
    info, selected = inventory(run)
    if args.login:
        complete = json.loads((run / "RUN_COMPLETE.json").read_text(encoding="utf-8"))
        if info.get("run_mode") != "login" or not info.get("run_id") or complete.get("run_id") != info["run_id"]:
            raise ValueError("Login retry does not have a matching completed-run marker")
    elif info.get("retry_job") != str(args.retry_job):
        raise ValueError("Retry job ID does not match the job recorded in RUN_INFO.json")
    if not str(info.get("previous_job", "")).isdigit():
        raise ValueError("Previous job ID in run metadata is invalid")
    nfiles = sum(len(x[3]) for x in selected)
    if not nfiles:
        raise RuntimeError("No valid PNG figures found; nothing to publish")
    missing = sum(bool(x[3]) and len(x[3]) < len(SUFFIXES) for x in selected)
    nofig = sum(not x[3] for x in selected)
    print(f"Retry {args.retry_job or 'login'}: {state}; inventory: {nfiles} PNGs, {missing} partial cases, {nofig} cases with no figure")
    for (site, case, ad), _, row, files in selected:
        print(f"{site:7} {case}: {len(files)}/3 PNGs; {row.get('Status', 'UNKNOWN')}")
    if not args.publish:
        print("Read-only inventory; use --publish after checking the results.")
        return 0
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    rel = Path("figures") / "AD400_NORMAL400" / (stamp + "_job" + str(info["previous_job"]))
    # Clone in a fresh temporary directory; existing source checkouts untouched.
    with tempfile.TemporaryDirectory(prefix="publish_plots_", dir=run.parent) as tmp:
        checkout = Path(tmp) / "repository"
        git("clone", "--depth", "1", "--branch", "main", REPO, checkout)
        target = checkout / rel
        target.mkdir(parents=True, exist_ok=False)
        lines = ["# AD400 + Normal400 diagnostic figures", "",
                 "The figures are exploratory and do not establish ecological convergence.",
                 "Only generated PNG figures are included; no model, observation or derived data files are uploaded.",
                 "NT GPP is preferred; inspect each figure's legend for the actual partition.",
                 "Missing plots and cases below are explicitly recorded; stream and timestamp differences need scientific review.",
                 "", "| Site | Normal case | Source status | Carbon overview | Normal panels | EC comparison |",
                 "| --- | --- | --- | --- | --- | --- |"]
        sums = []
        for (site, case, ad), source_root, row, files in selected:
            cells = []
            for suffix in SUFFIXES:
                src = files.get(suffix)
                if src is None:
                    cells.append("missing")
                    continue
                out = target / site / case / src.name
                out.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(src, out)
                digest = hashlib.sha256(out.read_bytes()).hexdigest()
                inner = out.relative_to(target).as_posix()
                sums.append(f"{digest}  {inner}")
                cells.append(f"[PNG]({inner})")
            status = row.get("Status", "UNKNOWN")
            if not re.fullmatch(r"[A-Za-z_]+", status):
                status = "UNKNOWN"
            if len(files) < len(SUFFIXES):
                status += " (missing plots)"
            lines.append(f"| {site} | {case} | {status} | " + " | ".join(cells) + " |")
        (target / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
        (target / "SHA256SUMS").write_text("\n".join(sums) + "\n", encoding="utf-8")
        git("add", "--", rel.as_posix(), cwd=checkout)
        git("commit", "-m", "Publish completed AD400 Normal400 diagnostic figures", cwd=checkout)
        commit = git("rev-parse", "HEAD", cwd=checkout)
        git("push", "origin", "HEAD:main", cwd=checkout)
        remote = git("ls-remote", "origin", "refs/heads/main", cwd=checkout)
        print("PUSH SUCCESS; commit:", commit)
        print("GitHub: https://github.com/lyanyeung/Non-Competition-CLM-experiment/tree/main/" + rel.as_posix())
        print("Remote head:", remote.split()[0] if remote else "UNKNOWN")
        print(f"Published {nfiles} PNGs. {missing} partial cases and {nofig} without figures are listed in the index.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
