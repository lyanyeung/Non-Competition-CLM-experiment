#!/usr/bin/env python3
"""Fresh per-case AD/Normal carbon and EC figures for ICOS38 + AmeriFlux50.

Read-only model inputs; do not submit or modify simulations. All 88 registered
sites are represented in site_status.csv. Every matching Normal case is recorded
separately; no independent longest-case pairing or recycled PNGs are used.
"""
import argparse
import csv
import importlib.util
import re
import traceback
from pathlib import Path
from types import SimpleNamespace


HERE = Path(__file__).resolve().parent
SAFE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")
SUFFIXES = ("_01_carbon_pools_AD400_NORMAL400.png", "_04_carbon_pools_AD400_panels.png",
            "_02_carbon_pools_NORMAL400_panels.png", "_GPP_NEE_monthly_overview.png")


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


def safe_name(name):
    if not SAFE.fullmatch(name) or name in (".", ".."):
        raise ValueError("Unsafe site or case name: " + repr(name))
    return name


def write_csv(path, rows, required):
    fields = sorted(set(required) | {k for row in rows for k in row})
    tmp = path.with_name("." + path.name + ".tmp")
    with tmp.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields); w.writeheader(); w.writerows(rows)
    tmp.replace(path)


def status_for(rows):
    if any(r.get("Status") == "OK" and r.get("Figures") == 4 for r in rows): return "COMPLETE"
    if any(r.get("Figures", 0) > 0 for r in rows): return "PARTIAL_FIGURES"
    if any("RUNNING" in r.get("Normal_scan", "").split("+") or
           "RUNNING" in r.get("AD_scan", "").split("+") for r in rows): return "RUNNING"
    if rows and all(r.get("Status") == "NO_NORMAL_CASE" for r in rows): return "NO_NORMAL_CASE"
    return "NOT_READY_OR_ERROR"


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output-root", required=True, type=Path)
    args = ap.parse_args()
    out = args.output_root.expanduser().resolve()
    if any(out == p or p in out.parents for p in (Path("/scratch"), Path("/iridisfs/scratch"))):
        raise ValueError("Output must not be under scratch")
    if out.exists() and any(out.iterdir()):
        raise ValueError("Output directory must be new or empty")
    registry = load("site_registry", HERE / "registry.py").records()
    scan = load("progress_scan", HERE / "scan.py")
    common = load("all_sites", HERE / "run.py")
    plot = load("plot_stage15", HERE / "plot.py")
    queue = common.verified_queue(scan.USER); scan.queue = lambda: queue
    rows = scan.scan(None, True, False)
    by_name = {r["name"]: r for r in rows}
    out.mkdir(parents=True, exist_ok=True)
    settings = SimpleNamespace(archive_root=scan.OUT / "archive", cases_root=scan.BASE / "cases",
        sites_root=scan.BASE / "sites/MY_EC_SITE", output_root=out,
        allow_incomplete=False, carbon_only=False, case_subdirectories=True,
        min_halfhour=40, min_days=20, obs_csv={})
    summaries = [{"Site": safe_name(r["site"]), "Network": r["network"], "Batch": r["batch"],
                  "Status": "NOT_YET_CHECKED", "Normal_cases": 0, "Complete_cases": 0}
                 for r in registry]
    cases = []
    write_csv(out / "site_status.csv", summaries, ("Site", "Network", "Batch", "Status"))
    for summary in summaries:
        site = summary["Site"]
        print(f"\n== {site} | {summary['Network']} {summary['Batch']} ==", flush=True)
        normals = sorted((r for r in rows if r["site"] == site and r["mode"] == "NORMAL"), key=lambda x: x["name"])
        records = []
        if not normals:
            ad = [r for r in rows if r["site"] == site and r["mode"] == "AD"]
            records.append({"Site": site, "Network": summary["Network"], "Batch": summary["Batch"],
                            "Normal_case": "", "AD_case": "", "Status": "NO_NORMAL_CASE",
                            "AD_scan": "+".join(sorted({r["verdict"] for r in ad})) or "NOT_FOUND", "Figures": 0})
            print("  no Normal case; AD states:", records[-1]["AD_scan"], flush=True)
        for r in normals:
            normal_name = safe_name(r["name"])
            ad_name = r.get("refcase") or ""
            rec = {"Site": site, "Network": summary["Network"], "Batch": summary["Batch"],
                   "Normal_case": normal_name, "AD_case": ad_name, "Normal_scan": r["verdict"],
                   "AD_scan": "NOT_FOUND", "Status": "NOT_READY", "Figures": 0}
            try:
                if ad_name: safe_name(ad_name)
                if r["verdict"] != "DONE":
                    raise ValueError("Normal case is not confirmed complete")
                ad = by_name.get(ad_name)
                if not ad or ad["site"] != site or ad["mode"] != "AD":
                    raise ValueError("RUN_REFCASE is not a scanned same-site AD case")
                rec["AD_scan"] = ad["verdict"]
                if ad["verdict"] != "DONE":
                    raise ValueError("Referenced AD case is not confirmed complete")
                common.restart_check(scan, ad); common.restart_check(scan, r)
                stream, pa, pn = common.stream_status(scan, ad_name, normal_name)
                rec.update(Stream_comparison=stream, AD_stream=pa, Normal_stream=pn)
                if stream != "MATCH":
                    print("  WARNING: AD/Normal streams", stream, flush=True)
                pair = {"site": site, "ad": ad_name, "normal": normal_name,
                        "ad_case_dir": settings.cases_root / ad_name, "cohort": summary["Batch"]}
                rec.update(plot.process(pair, settings))
            except Exception as exc:
                rec["Error"] = f"{type(exc).__name__}: {exc}"
                print("  NOT READY:", rec["Error"], flush=True)
                if __import__("os").environ.get("DEBUG"): traceback.print_exc()
            folder = out / site / normal_name
            rec["Figures"] = sum((folder / (site + suffix)).is_file() for suffix in SUFFIXES)
            rec["Output_directory"] = str(folder)
            print(" ", normal_name, "|", rec["Status"], "|", rec["Figures"], "/4 figures", flush=True)
            records.append(rec)
        cases.extend(records)
        summary["Normal_cases"] = len(normals)
        summary["Complete_cases"] = sum(r.get("Status") == "OK" and r.get("Figures") == 4 for r in records)
        summary["Status"] = status_for(records)
        write_csv(out / "site_status.csv", summaries, ("Site", "Network", "Batch", "Status"))
        write_csv(out / "case_status.csv", cases, ("Site", "Network", "Batch", "Normal_case", "AD_case", "Status"))
    for group in ("ICOS", "AmeriFlux"):
        group_rows = [r for r in summaries if r["Network"] == group]
        print(f"{group}: {sum(r['Status'] == 'COMPLETE' for r in group_rows)}/{len(group_rows)} sites with all four figures", flush=True)
    print("Site status:", out / "site_status.csv", flush=True)
    print("Case status:", out / "case_status.csv", flush=True)
    return int(any(r["Status"] != "COMPLETE" for r in summaries))


if __name__ == "__main__":
    raise SystemExit(main())

