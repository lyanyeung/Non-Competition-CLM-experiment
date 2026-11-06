#!/usr/bin/env python3
"""Publish a plot_done_normal400.sh output folder to GitHub (login node, SSH), like the earlier publishers.

Uploads, to main: figures/NewNormal400/<folder stamp>/
  - every PNG (Stage15 convergence_EC/<site>/..., full_sequence/<site>/<case>/..., ALL_SITES overviews)
  - result tables that hold metrics only: AD400_NORMAL400_summary.csv, full_sequence_summary.csv, last_cycle_metrics.csv,
    <site>_convergence_metrics.csv, <site>_flux_metrics.csv, <site>_metadata.json, pairs.txt
  - README.md (index: one row per site with links, overviews inline), SHA256SUMS
Not uploaded: daily / monthly / annual time-series tables (they carry EC observation values), model output.

  python -B publish_new_normal400_figures.py <output folder>            # dry run: lists what would be pushed
  python -B publish_new_normal400_figures.py <output folder> --push     # clone main, add, commit, push
  python -B publish_new_normal400_figures.py <output folder> --push --update
        the folder is already on main (e.g. published before step 3): add the new files, replace changed ones,
        rebuild README.md and SHA256SUMS; nothing on main is deleted
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

REPO = "git@github.com:lyanyeung/Non-Competition-CLM-experiment.git"
WEB = "https://github.com/lyanyeung/Non-Competition-CLM-experiment"
KEEP_NAMES = ("AD400_NORMAL400_summary.csv", "full_sequence_summary.csv", "last_cycle_metrics.csv", "pairs.txt")
KEEP_SUFFIXES = (".png", "_convergence_metrics.csv", "_flux_metrics.csv", "_metadata.json")
MAX_MB = 200


def selected(root: Path):
    out = []
    for p in sorted(root.rglob("*")):
        if p.is_file() and (p.name in KEEP_NAMES or p.name.endswith(KEEP_SUFFIXES)):
            out.append(p)
    return out


def summary_rows(path: Path):
    if not path.is_file():
        return {}
    with path.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    key = next((k for k in ("Site", "site") if rows and k in rows[0]), None)
    return {r[key]: r for r in rows} if key else {}


def fmt(v):
    try:
        return f"{float(v):.2f}"
    except (TypeError, ValueError):
        return (v or "").strip()


def readme(root: Path, dest_rel: str, files):
    stamp = root.name
    pairs = [ln.split(":") for ln in (root / "pairs.txt").read_text().split() if ln.count(":") == 2] \
        if (root / "pairs.txt").is_file() else []
    fs = summary_rows(root / "full_sequence" / "full_sequence_summary.csv")
    rel = {p.relative_to(root).as_posix() for p in files}

    def link(path, label):
        return f"[{label}]({path})" if path in rel else "—"

    cols = []
    if fs:
        first = next(iter(fs.values()))
        for want in ("Status", "EC_GPP_mean", "Model_GPP_last_cycle", "GPP_bias", "EC_NEE_mean",
                     "Model_NEE_last_cycle", "NEE_bias", "Flags"):
            hit = next((k for k in first if k.lower() == want.lower()), None)
            if hit:
                cols.append(hit)
    lines = [
        f"# New Normal400 figures: {stamp}",
        "",
        f"Made with `plot_done_normal400.sh`: script 24 (last complete forcing cycle against the EC tower), Stage15 "
        f"(carbon-pool convergence and monthly GPP / NEE against EC) and script 07 (800-year full sequence with the EC "
        f"reference). Published "
        f"{datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC. Inputs: AD400 = `RUN_REFCASE` of each Normal400 case "
        "(needleleaf variant F `_NLF` / `_NLFP`, phenology patch `_PHEN`, Batch04 and HINONE cases).",
        "",
        "800 model years do not prove equilibrium. The flags are hints for review, not conclusions. "
        "Only PNGs and metric tables are published; time-series tables with EC values stay on IRIDIS.",
        "",
        "## Overviews",
        "",
    ]
    for ov in ("last_cycle_EC/ALL_SITES_last_cycle_mean_vs_EC.png",
               "last_cycle_EC/ALL_SITES_last_cycle_GPP_seasonal_cycle.png",
               "last_cycle_EC/ALL_SITES_last_cycle_NEE_seasonal_cycle.png",
               "full_sequence/ALL_SITES_GPP_full_sequence_overview.png",
               "full_sequence/ALL_SITES_NEE_full_sequence_overview.png"):
        if ov in rel:
            lines += [f"![{Path(ov).stem}]({ov})", ""]
    lc = {}
    lcp = root / "last_cycle_EC" / "last_cycle_metrics.csv"
    if lcp.is_file():
        with lcp.open(newline="", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                if r.get("Case") == "new" and r.get("Status") == "OK":
                    lc[(r["Site"], r["Flux"])] = r
    lc_cols = [("GPP", "Mean_model", "GPP model"), ("GPP", "Mean_EC", "GPP EC"), ("GPP", "Ratio", "GPP model/EC"),
               ("GPP", "R2", "GPP R²"), ("NEE", "Mean_model", "NEE model"), ("NEE", "Mean_EC", "NEE EC"),
               ("NEE", "R2", "NEE R²")] if lc else []
    head = ["Site", "AD400 → Normal400", "Last cycle vs EC", "Carbon pools 800 y", "Normal panels",
            "Monthly GPP/NEE vs EC (Stage15)", "Full sequence"] + [c[2] for c in lc_cols] + cols
    lines += ["## Sites", "", "| " + " | ".join(head) + " |", "|" + "---|" * len(head)]
    for site, ad, normal in pairs:
        c = f"convergence_EC/{site}/{site}"
        row = [site, f"`{ad}` → `{normal}`",
               link(f"last_cycle_EC/{site}/{site}_last_cycle_GPP_NEE_vs_EC.png", "png"),
               link(f"{c}_01_carbon_pools_AD400_NORMAL400.png", "png"),
               link(f"{c}_02_carbon_pools_NORMAL400_panels.png", "png"),
               link(f"{c}_GPP_NEE_monthly_overview.png", "png"),
               link(f"full_sequence/{site}/{normal}/{site}_03_GPP_NEE_full_sequence_AD400_NORMAL400.png", "png")]
        row += [fmt(lc.get((site, fl), {}).get(k, "")) for fl, k, _ in lc_cols]
        row += [fmt(fs.get(site, {}).get(k, "")).replace("|", "/") for k in cols]
        lines.append("| " + " | ".join(row) + " |")
    lines += ["", "Model / EC columns: mean monthly flux over the paired months of the last complete forcing cycle "
              "(g C m-2 d-1, new Normal400). "
              "Tables: [last-cycle metrics](last_cycle_EC/last_cycle_metrics.csv), "
              "[convergence / flux summary](convergence_EC/AD400_NORMAL400_summary.csv), "
              "[full-sequence summary](full_sequence/full_sequence_summary.csv). Checksums: `SHA256SUMS`.", ""]
    return "\n".join(lines)


def run(cmd, cwd=None):
    print("+ " + " ".join(cmd), flush=True)
    subprocess.run(cmd, cwd=cwd, check=True)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("folder", type=Path)
    ap.add_argument("--push", action="store_true")
    ap.add_argument("--update", action="store_true", help="add to / refresh a folder already on main")
    ap.add_argument("--repo", default=REPO)
    a = ap.parse_args(argv)
    root = a.folder.expanduser().resolve()
    if not any((root / d).is_dir() for d in ("convergence_EC", "full_sequence", "last_cycle_EC")):
        ap.error(f"{root}: no convergence_EC/ or full_sequence/ - not a plot_done_normal400.sh output")
    files = selected(root)
    pngs = [p for p in files if p.suffix == ".png"]
    mb = sum(p.stat().st_size for p in files) / 1e6
    dest_rel = f"figures/NewNormal400/{root.name}"
    print(f"{root}\n  {len(pngs)} PNG, {len(files) - len(pngs)} tables, {mb:.1f} MB -> main:{dest_rel}")
    for p in files:
        print("   ", p.relative_to(root))
    if not pngs:
        ap.error("no PNGs to publish")
    if mb > MAX_MB:
        ap.error(f"{mb:.0f} MB is more than {MAX_MB} MB; publish a subset")
    if not a.push:
        print("\ndry run; add --push to publish")
        return 0
    with tempfile.TemporaryDirectory(prefix="pub_newnormal_") as tmp:
        repo = Path(tmp) / "repo"
        run(["git", "clone", "--depth", "1", "--branch", "main", a.repo, str(repo)])
        dest = repo / dest_rel
        if dest.exists() and not a.update:
            ap.error(f"{dest_rel} already exists on main; nothing pushed (add --update to add the new files)")
        new = changed = 0
        for p in files:
            q0 = dest / p.relative_to(root)
            if not q0.exists():
                new += 1
            elif q0.read_bytes() != p.read_bytes():
                changed += 1
            q = dest / p.relative_to(root)
            q.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(p, q)
        (dest / "README.md").write_text(readme(root, dest_rel, files), encoding="utf-8")
        sums = [f"{hashlib.sha256(q.read_bytes()).hexdigest()}  {q.relative_to(dest).as_posix()}"
                for q in sorted(dest.rglob("*")) if q.is_file() and q.name != "SHA256SUMS"]
        (dest / "SHA256SUMS").write_text("\n".join(sums) + "\n")
        print(f"  {new} new file(s), {changed} changed file(s)", flush=True)
        run(["git", "add", dest_rel], cwd=repo)
        if subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=repo).returncode == 0:
            print("nothing changed on main; nothing pushed")
            return 0
        what = "update" if a.update else "new Normal400 convergence + EC figures"
        run(["git", "commit", "-q", "-m", f"figures: {what} {root.name} ({len(pngs)} PNG; +{new} new, {changed} changed)"],
            cwd=repo)
        for attempt in range(3):
            try:
                run(["git", "push", "origin", "HEAD:main"], cwd=repo)
                break
            except subprocess.CalledProcessError:
                if attempt == 2:
                    raise
                run(["git", "pull", "--rebase", "origin", "main"], cwd=repo)
    print(f"PUSH SUCCESS\n{WEB}/tree/main/{dest_rel}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
