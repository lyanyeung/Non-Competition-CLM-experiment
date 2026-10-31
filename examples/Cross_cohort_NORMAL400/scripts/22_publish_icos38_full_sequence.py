#!/usr/bin/env python3
"""Publish fresh 38-site figures and a provenance index, never raw data."""
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
CORE = Path("examples/Batch03_10/scripts/15_plot_AD400_NORMAL400_convergence_and_EC.py")
SCRIPT = Path("examples/Cross_cohort_NORMAL400/scripts/21_icos38_full_sequence.py")
SAFE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git(*args, cwd=None):
    p = subprocess.run(["git", *map(str, args)], cwd=cwd, text=True, capture_output=True)
    if p.returncode:
        raise RuntimeError("git " + " ".join(map(str, args)) + " failed: " + p.stderr[-3000:])
    return p.stdout.strip()


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--run", required=True, type=Path)
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--core", required=True, type=Path)
    ap.add_argument("--script", required=True, type=Path)
    a = ap.parse_args()
    if not re.fullmatch(r"login-[0-9a-f]{32}", a.run_id):
        raise ValueError("Invalid login run ID")
    root = a.run.expanduser().resolve(strict=True)
    parts = Path(str(root) + ".analysis_exit_status").read_text().strip().split("|")
    if len(parts) != 4 or parts[0] != a.run_id or not parts[1].isdigit():
        raise ValueError("No matching completion marker")
    if digest(a.core.resolve(strict=True)) != parts[2] or digest(a.script.resolve(strict=True)) != parts[3]:
        raise ValueError("Plotting code differs from the recorded run")
    with (root / "site_status.csv").open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    if len(rows) != 38 or len({r.get("Site") for r in rows}) != 38:
        raise ValueError("Expected 38 unique site records; do not publish an interrupted analysis")
    if not any(r.get("Status") in ("OK", "MODEL_ONLY_OR_INCOMPLETE_EC", "PARTIAL_MODEL") for r in rows):
        raise ValueError("No completed plots to publish")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    rel = Path("figures/ICOS38_NT") / (stamp + "_" + a.run_id[-8:])
    with tempfile.TemporaryDirectory(prefix="publish_icos38_", dir=root.parent) as tmp:
        checkout = Path(tmp) / "repo"
        git("clone", "--depth", "1", "--branch", "main", REPO, checkout)
        if digest(checkout / CORE) != parts[2] or digest(checkout / SCRIPT) != parts[3]:
            raise ValueError("GitHub plotting code changed since the run; review before publishing")
        target = checkout / rel; target.mkdir(parents=True, exist_ok=False)
        lines = ["# ICOS 38 sites: AD400 → Normal400 full-sequence diagnostics", "",
                 "Fresh plots; no reuse of earlier PNGs. Each day uses valid NT GPP in preference to DT across sources; DT is used only when NT is unavailable that day.",
                 "NT/DT counts are valid observation days over the indicated forcing period, not sample counts or a guarantee of completeness.",
                 "Only verified completed AD400→Normal400 pairs are shown; other protocols and missing cases are not relabelled as 800-year runs.",
                 "EC range uses years with 12 months having at least 20 valid days; EC monthly min/max use monthly climatology.",
                 "The index does not upload raw model or observation files. Cases without plots require the local site_status.csv and analysis.log.",
                 f"Run: {a.run_id}; analysis exit status: {parts[1]}.", "",
                 "[GPP overview](ALL_38_GPP_full_sequence_overview.png) · [NEE overview](ALL_38_NEE_full_sequence_overview.png)", "",
                 "| Site | Normal case | Status | Streams | NT days | DT days | Figure | Provenance |",
                 "| --- | --- | --- | --- | ---: | ---: | --- | --- |"]
        sums = []
        for name in ("GPP", "NEE"):
            src = root / f"ALL_38_{name}_full_sequence_overview.png"
            if not src.is_file() or src.read_bytes()[:8] != b"\x89PNG\r\n\x1a\n":
                raise ValueError("Missing or invalid 38-site overview: " + str(src))
            dst = target / src.name; shutil.copyfile(src, dst)
            sums.append(f"{digest(dst)}  {src.name}")
        for row in rows:
            site, case = row.get("Site", ""), row.get("Normal_case", "")
            if not SAFE.fullmatch(site) or (case and not SAFE.fullmatch(case)):
                raise ValueError("Unsafe site or case name")
            status = row.get("Status", "MISSING")
            status = status if re.fullmatch(r"[A-Z_]+", status) else "UNKNOWN"
            figcell = metacell = "missing"
            if case:
                folder = (root / site / case).resolve()
                if root not in folder.parents:
                    raise ValueError("Case path escapes run directory")
                src = folder / f"{site}_03_GPP_NEE_full_sequence_AD400_NORMAL400.png"
                meta = folder / f"{site}_metadata.json"
                if src.is_file() and meta.is_file():
                    if src.resolve().parent != folder or src.stat().st_size > 95_000_000 or src.read_bytes()[:8] != b"\x89PNG\r\n\x1a\n":
                        raise ValueError("Invalid figure " + str(src))
                    dest = target / site / case / src.name; dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(src, dest)
                    inner = dest.relative_to(target).as_posix(); sums.append(f"{digest(dest)}  {inner}")
                    figcell = f"[PNG]({inner})"
                    obj = json.loads(meta.read_text(encoding="utf-8"))
                    obj["ec_sources"] = [{"source_file": Path(p.get("path", "")).name,
                                          "gpp_column": p.get("gpp_column", ""),
                                          "valid_GPP_days": p.get("valid_GPP_days"),
                                          "valid_NEE_days": p.get("valid_NEE_days"),
                                          "sample_interval_seconds": p.get("sample_interval_seconds"),
                                          "source_error": bool(p.get("reason"))} for p in obj.get("ec_sources", [])]
                    obj.pop("ec_error", None)
                    mdest = dest.with_name(f"{site}_provenance.json")
                    mdest.write_text(json.dumps(obj, indent=2, allow_nan=True) + "\n", encoding="utf-8")
                    mi = mdest.relative_to(target).as_posix(); sums.append(f"{digest(mdest)}  {mi}")
                    metacell = f"[JSON]({mi})"
            stream = row.get("Stream_comparison", "")
            stream = stream if stream in ("MATCH", "DIFFERENT", "UNVERIFIED") else "—"
            lines.append(f"| {site} | {case or '—'} | {status} | {stream} | {row.get('NT_days', '')} | {row.get('DT_days', '')} | {figcell} | {metacell} |")
        if not sums:
            raise ValueError("No readable fresh images to publish")
        (target / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
        (target / "SHA256SUMS").write_text("\n".join(sums) + "\n", encoding="utf-8")
        git("add", "--", rel, cwd=checkout)
        git("commit", "-m", "Publish fresh ICOS 38 NT-first flux diagnostics", cwd=checkout)
        commit = git("rev-parse", "HEAD", cwd=checkout)
        git("push", "origin", "HEAD:main", cwd=checkout)
        print("PUSH SUCCESS; commit:", commit)
        print("GitHub: https://github.com/lyanyeung/Non-Competition-CLM-experiment/tree/main/" + rel.as_posix())
        print("Included files:", len(sums), "; indexed sites:", len(rows))


if __name__ == "__main__":
    main()

