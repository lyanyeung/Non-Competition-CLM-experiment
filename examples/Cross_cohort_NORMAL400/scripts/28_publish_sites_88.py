#!/usr/bin/env python3
"""Publish the fresh 88-site index, four PNG types and derived metrics only."""
import argparse
import csv
import hashlib
import importlib.util
import json
import re
import shutil
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path

REPO = "git@github.com:lyanyeung/Non-Competition-CLM-experiment.git"
SOURCES = {
    "plot.py": "examples/Batch03_10/scripts/15_plot_AD400_NORMAL400_convergence_and_EC.py",
    "scan.py": "examples/Cross_cohort_NORMAL400/scripts/02_scan_all_spinup_progress_readonly.py",
    "run.py": "examples/Cross_cohort_NORMAL400/scripts/03_plot_all_completed_sites.py",
    "registry.py": "examples/Cross_cohort_NORMAL400/scripts/26_site_registry.py",
    "driver.py": "examples/Cross_cohort_NORMAL400/scripts/27_plot_sites_88.py",
}
FIGURES = ("_01_carbon_pools_AD400_NORMAL400.png", "_04_carbon_pools_AD400_panels.png",
           "_02_carbon_pools_NORMAL400_panels.png", "_GPP_NEE_monthly_overview.png")
DERIVED = ("_AD_diagnostics.csv", "_convergence_metrics.csv")
SAFE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")


def sha(data): return hashlib.sha256(data).hexdigest()


def command(*args, cwd=None, binary=False):
    p = subprocess.run(["git", *map(str, args)], cwd=cwd, capture_output=True)
    if p.returncode:
        raise RuntimeError("git " + " ".join(map(str, args)) + " failed: " + p.stderr.decode(errors="replace")[-3000:])
    return p.stdout if binary else p.stdout.decode("utf-8").strip()


def read_csv(path):
    with path.open(newline="", encoding="utf-8") as f: return list(csv.DictReader(f))


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--run", required=True, type=Path)
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--tool", required=True, type=Path)
    a = ap.parse_args()
    if not re.fullmatch(r"login-[0-9a-f]{32}", a.run_id): raise ValueError("Invalid run ID")
    root = a.run.resolve(strict=True); tool = a.tool.resolve(strict=True)
    info = json.loads((root / "RUN_COMPLETE.json").read_text(encoding="utf-8"))
    if info.get("run_id") != a.run_id or not re.fullmatch(r"[0-9a-f]{40}", info.get("source_commit", "")):
        raise ValueError("Run completion marker or source revision is invalid")
    for name in SOURCES:
        if sha((tool / name).read_bytes()) != info.get("code_sha256", {}).get(name):
            raise ValueError("Run tool differs from recorded hash: " + name)
    sites = read_csv(root / "site_status.csv"); cases = read_csv(root / "case_status.csv")
    if (len(sites) != 88 or len({r.get("Site") for r in sites}) != 88
        or sum(r.get("Network") == "ICOS" for r in sites) != 38
        or sum(r.get("Network") == "AmeriFlux" for r in sites) != 50
        or any(r.get("Status") == "NOT_YET_CHECKED" for r in sites)):
        raise ValueError("The run has no complete 38+50 site inventory")
    if {r.get("Site") for r in cases} != {r.get("Site") for r in sites}:
        raise ValueError("Case inventory does not cover the site inventory")
    selected = {r["Site"]: [] for r in sites}
    for row in cases:
        site, case = row.get("Site", ""), row.get("Normal_case", "")
        if not SAFE.fullmatch(site) or (case and not SAFE.fullmatch(case)):
            raise ValueError("Unsafe site or case identifier")
        selected[site].append(row)
    if not any(int(r.get("Figures") or 0) > 0 for r in cases):
        raise ValueError("No figures from this run; not publishing")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    rel = Path("figures/AD400_NORMAL400") / (stamp + "_88_" + a.run_id[-8:])
    with tempfile.TemporaryDirectory(prefix="publish_sites88_", dir=root.parent) as tmp:
        checkout = Path(tmp) / "repo"
        command("clone", "--depth", "1", "--branch", "main", REPO, checkout)
        command("fetch", "--depth", "1", "origin", info["source_commit"], cwd=checkout)
        for name, path in SOURCES.items():
            data = command("show", f"{info['source_commit']}:{path}", cwd=checkout, binary=True)
            if sha(data) != info["code_sha256"][name]:
                raise ValueError("Recorded source revision does not match run tool: " + name)
        spec = importlib.util.spec_from_file_location("verified_site_registry", tool / "registry.py")
        registry = importlib.util.module_from_spec(spec); spec.loader.exec_module(registry)
        expected = {r["site"]: (r["network"], r["batch"]) for r in registry.records()}
        if {r["Site"]: (r["Network"], r["Batch"]) for r in sites} != expected:
            raise ValueError("Site inventory does not match the verified 38+50 registry")
        target = checkout / rel; target.mkdir(parents=True, exist_ok=False)
        lines = ["# ICOS 38 and AmeriFlux 50: AD400 / Normal400 diagnostics", "",
                 "These are candidate inventories, not counts of completed runs. ICOS has three named FIXNC batches plus example and unassigned sites; the batch labels follow the 2026-10-25 site inventory and do not imply a case was created or finished. The actual discovered cases and statuses are listed below.",
                 "Fresh plots for every verified completed fixed-biogeography/no-competition AD400→Normal400 pair discovered in this run. Multiple cases are separate; incomplete or absent cases remain listed.",
                 "Only PNG images and derived carbon diagnostic tables are uploaded; model histories and tower observations remain on IRIDIS.",
                 "Normal convergence metrics use Normal years only. AD diagnostics describe accelerated conditions and do not establish Normal-phase equilibrium.",
                 "Tower GPP priority per day is NT VUT, NT CUT, DT VUT, DT CUT; the actual source and field are identified in plots and provenance.",
                 f"Source commit: `{info['source_commit']}`. Run: `{a.run_id}`; exit status: {info['exit_code']}.", "",
                 "| Network | Batch | Site | Site status | Normal case | Case status | Streams | AD + Normal | AD only | Normal only | GPP / NEE | Metrics | Provenance |",
                 "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
        checksums = []
        for item in sites:
            site = item["Site"]
            for row in selected[site]:
                case = row.get("Normal_case", "")
                links = ["missing"] * 4; metrics = []; provenance = "missing"
                if case:
                    folder = (root / site / case).resolve()
                    if root not in folder.parents: raise ValueError("Case directory outside run")
                    for idx, suffix in enumerate((*FIGURES, *DERIVED)):
                        src = folder / (site + suffix)
                        if not src.is_file(): continue
                        src = src.resolve()
                        if src.parent != folder or src.stat().st_size > 95_000_000: raise ValueError("Unsafe output " + str(src))
                        if suffix.endswith(".png") and src.read_bytes()[:8] != b"\x89PNG\r\n\x1a\n": raise ValueError("Invalid PNG " + str(src))
                        dst = target / site / case / src.name; dst.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copyfile(src, dst); inner = dst.relative_to(target).as_posix()
                        checksums.append(f"{sha(dst.read_bytes())}  {inner}")
                        link = f"[{'PNG' if suffix.endswith('.png') else 'CSV'}]({inner})"
                        if idx < len(FIGURES): links[idx] = link
                        else: metrics.append(link)
                    meta = folder / (site + "_metadata.json")
                    if meta.is_file():
                        if meta.resolve().parent != folder or meta.stat().st_size > 2_000_000:
                            raise ValueError("Unsafe metadata " + str(meta))
                        obj = json.loads(meta.read_text(encoding="utf-8"))
                        cleaned = {k: obj.get(k) for k in ("site", "ad_case", "normal_case", "status", "gpp_policy",
                                   "ec_gpp_columns_used", "ec_nee_columns_used", "forcing_first_last_align",
                                   "ec_cycle_model_years", "carbon_variables", "carbon_units", "missing_primary_carbon_variables")}
                        cleaned["ec_sources"] = [{"source_file": Path(p.get("path", "")).name,
                            "gpp_column": p.get("gpp_column", ""), "valid_GPP_days": p.get("valid_GPP_days"),
                            "valid_NEE_days": p.get("valid_NEE_days"), "source_error": bool(p.get("reason"))}
                            for p in obj.get("ec_sources", [])]
                        dst = target / site / case / (site + "_provenance.json"); dst.parent.mkdir(parents=True, exist_ok=True)
                        dst.write_text(json.dumps(cleaned, indent=2) + "\n", encoding="utf-8")
                        inner = dst.relative_to(target).as_posix(); checksums.append(f"{sha(dst.read_bytes())}  {inner}")
                        provenance = f"[JSON]({inner})"
                ss = item.get("Status", "UNKNOWN"); cs = row.get("Status", "UNKNOWN")
                if not re.fullmatch(r"[A-Z_]+", ss): ss = "UNKNOWN"
                if not re.fullmatch(r"[A-Z_]+", cs): cs = "UNKNOWN"
                stream = row.get("Stream_comparison", "")
                stream = stream if stream in ("MATCH", "DIFFERENT", "UNVERIFIED") else "—"
                lines.append(f"| {item['Network']} | {item['Batch']} | {site} | {ss} | {case or '—'} | {cs} | {stream} | "
                             + " | ".join(links) + " | " + (" / ".join(metrics) or "missing") + f" | {provenance} |")
        if not checksums: raise ValueError("No valid files to publish")
        (target / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
        (target / "SHA256SUMS").write_text("\n".join(checksums) + "\n", encoding="utf-8")
        command("add", "--", rel, cwd=checkout)
        command("commit", "-m", "Publish ICOS and AmeriFlux AD Normal diagnostic figures", cwd=checkout)
        commit = command("rev-parse", "HEAD", cwd=checkout)
        command("push", "origin", "HEAD:main", cwd=checkout)
        print("PUSH SUCCESS; commit:", commit)
        print("GitHub: https://github.com/lyanyeung/Non-Competition-CLM-experiment/tree/main/" + rel.as_posix())
        print("Indexed", len(sites), "sites; published", len(checksums), "files.")


if __name__ == "__main__": main()

