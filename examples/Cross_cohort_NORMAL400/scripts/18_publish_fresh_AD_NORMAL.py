#!/usr/bin/env python3
"""Publish fresh cross-cohort figures and selected derived metrics."""
import argparse
import csv
import hashlib
import re
import shutil
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path

REPO = "git@github.com:lyanyeung/Non-Competition-CLM-experiment.git"
PLOT_PATH = Path("examples/Batch03_10/scripts/15_plot_AD400_NORMAL400_convergence_and_EC.py")
SAFE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")
SUFFIXES = ("_01_carbon_pools_AD400_NORMAL400.png", "_02_carbon_pools_NORMAL400_panels.png",
            "_GPP_NEE_monthly_overview.png", "_convergence_metrics.csv")


def git(*args, cwd=None):
    p = subprocess.run(["git", *map(str, args)], cwd=cwd, text=True, capture_output=True)
    if p.returncode:
        raise RuntimeError("git " + " ".join(map(str, args)) + " failed: " + p.stderr[-3000:])
    return p.stdout.strip()


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--run", required=True, type=Path)
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--job")
    mode.add_argument("--login", help="Unique login run ID printed by the runner")
    ap.add_argument("--plotter", required=True, type=Path)
    args = ap.parse_args()
    if args.job and not args.job.isdigit():
        raise ValueError("Job ID must be numeric")
    if args.login and not re.fullmatch(r"login-[0-9a-f]{32}", args.login):
        raise ValueError("Invalid login run ID")
    run_id = args.job or args.login
    root = args.run.expanduser().resolve(strict=True)
    marker = Path(str(root) + ".analysis_exit_status")
    parts = marker.read_text(encoding="utf-8").strip().split("|")
    if (len(parts) != 3 or parts[0] != run_id or not parts[1].isdigit()
            or not re.fullmatch(r"[0-9a-f]{64}", parts[2])):
        raise ValueError("Completion marker missing or does not match job")
    if args.job:
        p = subprocess.run(["sacct", "-n", "-P", "-j", args.job, "--format=JobIDRaw,State"],
                           capture_output=True, text=True, timeout=60, check=True)
        states = [s.split("|")[1].strip().split()[0].rstrip("+") for s in p.stdout.splitlines()
                  if "|" in s and s.split("|")[0].strip() == args.job]
        if len(states) != 1 or states[0] not in {"COMPLETED", "FAILED"}:
            raise ValueError("Job not confirmed finished by sacct: " + repr(states))
    else:
        states = ["LOGIN_FINISHED"]
    with (root / "all_sites_summary.csv").open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        raise ValueError("No cases recorded in summary")
    selected = []
    for row in rows:
        site, case = row.get("Site", ""), row.get("Normal_case", "")
        if not all(SAFE.fullmatch(x) and x not in (".", "..") for x in (site, case)):
            raise ValueError("Unsafe site or case name")
        folder = (root / site / case).resolve()
        if root not in folder.parents:
            raise ValueError("Output path outside run directory")
        files = []
        for suffix in SUFFIXES:
            path = folder / (site + suffix)
            if path.is_file():
                path = path.resolve()
                if folder not in path.parents or path.stat().st_size > 95_000_000:
                    raise ValueError("Unsafe or oversized output " + str(path))
                if suffix.endswith(".png") and path.read_bytes()[:8] != b"\x89PNG\r\n\x1a\n":
                    raise ValueError("Invalid PNG " + str(path))
                files.append((suffix, path))
        selected.append((row, files))
    if not any(files for _, files in selected):
        raise ValueError("No fresh results to publish")
    plotter = args.plotter.expanduser().resolve(strict=True)
    if hashlib.sha256(plotter.read_bytes()).hexdigest() != parts[2]:
        raise ValueError("Plotter differs from the version recorded by the analysis job")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    rel = Path("figures/AD400_NORMAL400") / (stamp + "_fresh_" + run_id)
    with tempfile.TemporaryDirectory(prefix="publish_fresh_", dir=root.parent) as tmp:
        checkout = Path(tmp) / "repo"
        git("clone", "--depth", "1", "--branch", "main", REPO, checkout)
        if hashlib.sha256((checkout / PLOT_PATH).read_bytes()).hexdigest() != parts[2]:
            raise ValueError("GitHub plotter differs from the version used for this job; stop to review")
        target = checkout / rel
        target.mkdir(parents=True, exist_ok=False)
        lines = ["# Fresh AD400 and Normal400 diagnostics", "",
                 "The carbon plots are freshly generated for this run; none are reused from an earlier run.",
                 "Convergence metrics use the Normal phase only and do not constitute a pass/fail verdict.",
                 "Only PNGs and derived convergence metrics are included, no raw model or observation data.",
                 f"Run: {run_id}; analysis exit status: {parts[1]}; state: {states[0]}.",
                 "Missing plots or metrics are listed below. Review local all_sites_summary.csv for errors and stream warnings.",
                 "", "| Site | Normal case | Status | Full carbon | Normal carbon | EC | Metrics |",
                 "| --- | --- | --- | --- | --- | --- | --- |"]
        sums = []
        for row, files in selected:
            site, case = row["Site"], row["Normal_case"]
            present = dict(files)
            cells = []
            for suffix in SUFFIXES:
                if suffix not in present:
                    cells.append("missing")
                    continue
                src = present[suffix]
                dst = target / site / case / src.name
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(src, dst)
                inner = dst.relative_to(target).as_posix()
                sums.append(f"{hashlib.sha256(dst.read_bytes()).hexdigest()}  {inner}")
                cells.append(f"[{'CSV' if suffix.endswith('.csv') else 'PNG'}]({inner})")
            status = row.get("Status", "UNKNOWN")
            status = status if re.fullmatch(r"[A-Za-z_]+", status) else "UNKNOWN"
            lines.append(f"| {site} | {case} | {status} | " + " | ".join(cells) + " |")
        (target / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
        (target / "SHA256SUMS").write_text("\n".join(sums) + "\n", encoding="utf-8")
        git("add", "--", rel, cwd=checkout)
        git("commit", "-m", "Publish fresh AD Normal carbon diagnostics", cwd=checkout)
        commit = git("rev-parse", "HEAD", cwd=checkout)
        git("push", "origin", "HEAD:main", cwd=checkout)
        print("PUSH SUCCESS; commit:", commit)
        print("GitHub: https://github.com/lyanyeung/Non-Competition-CLM-experiment/tree/main/" + rel.as_posix())
        print("Published files:", len(sums), "cases:", len(rows))


if __name__ == "__main__":
    main()

