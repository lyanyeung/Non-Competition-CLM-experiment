#!/usr/bin/env python3
"""Read-only DE-Tha landunit/PFT factorial-design and existing forcing QC review.

DO NOT use this as a model-surface generator. It reads the exact pinned source
NetCDF and the existing forcing/qc_v5 reports, then prints scientifically
distinct, explicitly UNAPPROVED hypotheses. No source data, netCDF, Slurm jobs,
CIME cases, controller state or Git files are written.
"""
from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

import numpy as np
from netCDF4 import Dataset

ROOT = Path("/iridisfs/scratch/ly3n24/CLM_FATES")
SITE = ROOT / "sites/MY_EC_SITE/DE-Tha"
SURFACE = SITE / "subset_data/surfdata_DE-Tha_hist_2000_16pfts_c261011.nc"
SHA256_SURFACE = "7e4e4f8fc752d936f80e06a65db0f2163a3f74cdebff5d318973773450f5940d"
QC = SITE / "forcing/qc_v5"
SPECIES = {"ENF":87.0,"DNF":10.0,"identified_DBF":1.0,
           "unresolved_deciduous":2.0}
# This is an illustrative sensitivity assumption, NOT an observed PFT map:
HYPOTHESES = {
    "other_2pct_as_DBF": {1:87.0,3:10.0,7:3.0},
    "other_2pct_as_DNF": {1:87.0,3:12.0,7:1.0},
}

def fail(msg):
    raise RuntimeError(msg)

def sha256(p):
    h=hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda:f.read(1024*1024),b""):
            h.update(chunk)
    return h.hexdigest()

def one(ds,name):
    if name not in ds.variables:
        fail("Missing "+name)
    a=np.ma.filled(ds.variables[name][:],np.nan).ravel()
    if a.size!=1 or not np.isfinite(a).all():
        fail("Unexpected non-singleton "+name)
    return float(a[0])

def surface():
    if not SURFACE.is_file() or sha256(SURFACE)!=SHA256_SURFACE:
        fail("Original DE-Tha surface absent or SHA256 changed; HALT")
    with Dataset(SURFACE,"r") as ds:
        nat=one(ds,"PCT_NATVEG")
        crop=one(ds,"PCT_CROP")
        if abs(nat+crop-100)>0.01:
            fail("Surface landunit fractions not ~100%; inspect additional landunits")
        for k in ("PCT_LAKE","PCT_WETLAND","PCT_GLACIER","PCT_URBAN"):
            if k in ds.variables:
                a=np.ma.filled(ds.variables[k][:],np.nan)
                if not np.isfinite(a).all() or float(np.abs(a).sum())>1e-8:
                    fail("Other landunit present: "+k)
        v=ds.variables["PCT_NAT_PFT"]
        axes=[i for i,k in enumerate(v.dimensions) if k.lower()=="natpft"]
        if len(axes)!=1 or v.shape[axes[0]]!=15 or any(
           n!=1 for i,n in enumerate(v.shape) if i!=axes[0]):
            fail("PFT array dimension assumptions not met")
        old=np.moveaxis(np.ma.filled(v[:],np.nan),axes[0],0).reshape(15)
        if not np.isfinite(old).all() or abs(old.sum()-100)>0.02:
            fail("Invalid PCT_NAT_PFT sum")
        return nat,crop,old

def show_scenario(label,nat,crop,shares):
    # CLM natpft[] share is conditional on the NATVEG landunit; the
    # footprint-to-grid hypothesis and crop management still require review.
    full={k:round(nat*v/100,5) for k,v in shares.items()}
    print("\nHYPOTHESIS:",label)
    print("  grid: PCT_NATVEG =",round(nat,6),"PCT_CROP =",round(crop,6))
    print("  % OF NATVEG:",{f"natpft[{k}]":v for k,v in shares.items()})
    print("  % OF GRID (derived):",full,"crop =",round(crop,6))
    print("  NOT a validated surface and NOT a footprint-weighted product")

def qc_report():
    print("\n=== EXISTING v5 FORCING QC RECEIPTS (UNVERIFIED SEMANTICS) ===")
    for filename in (
        "DE-Tha_status.json","DE-Tha_qc_summary.csv",
        "DE-Tha_manual_review.csv","DE-Tha_replacement_events.csv",
        "DE-Tha_low_RH_diagnostic.csv","DE-Tha_low_RH_decisions.csv",
    ):
        path=QC/filename
        print("\n",filename,":", "PRESENT" if path.is_file() else "MISSING")
        if not path.is_file():
            continue
        print("SHA256:",sha256(path))
        if path.suffix==".json":
            try:
                obj=json.loads(path.read_text(encoding="utf-8-sig"))
                print("JSON:",json.dumps(obj,ensure_ascii=False,sort_keys=True)[:3500])
            except Exception as exc:
                print("JSON READ FAILED:",exc)
        else:
            with path.open(newline="",encoding="utf-8-sig") as handle:
                reader=csv.reader(handle)
                header=next(reader,[])
                total=sum(1 for _ in reader)
            print("HEADER:",header[:24])
            print("RECORDS_EXCLUDING_HEADER:",total)
    print("\nExisting QC evidence must be interpreted, not assumed PASS.")
    print("Climate forcing time coverage and sample DATM time axes were")
    print("checked in script 03, but physical/QC review remains required.")

def main():
    nat,crop,old=surface()
    print("=== ORIGINAL CLM GRID: PINNED READ ONLY ===")
    print("SOURCE:",SURFACE)
    print("SHA256:",SHA256_SURFACE)
    print("PCT_NATVEG:",round(nat,6),"PCT_CROP:",round(crop,6))
    print("ORIGINAL PCT_NAT_PFT:",{i:round(float(v),5)
                                    for i,v in enumerate(old) if abs(v)>1e-5})
    print("\n=== ICOS REPORTED FOREST COMPOSITION ===")
    print(SPECIES)
    print("ICOS records the forest in the flux-influence area; fractions")
    print("are not established as area-weighted 1-point CLM landunits.")
    print("Two unknown percent are 'other' in the deciduous category;")
    print("assignment to DBF or DNF remains an explicit hypothesis.")

    show_scenario("REFERENCE GRID / ORIGINAL SURFACE (NO CHANGES)",
                  nat,crop,{i:float(x) for i,x in enumerate(old) if x>1e-5})
    for name,shares in HYPOTHESES.items():
        if abs(sum(shares.values())-100)>1e-7:
            fail("Invalid hypothetical NAT_PFT total")
        show_scenario("GRID-CONSERVING FIXNC; "+name,nat,crop,shares)
        show_scenario("TOWER-FOREST-PROXY FIXNC; "+name,100.0,0.0,shares)
    print("\n=== CAUSAL EXPERIMENT DESIGN ===")
    print("C0 Ordinary FATES + original surface (existing reference).")
    print("C1 FIXNC FATES + original surface: tests mode effect, conditional")
    print("   on FATES initialization and other settings being held equal.")
    print("C2 FIXNC FATES + grid-conserving PFT mixture: alters natural PFT")
    print("   composition but retains ~37.3% crop fraction (mixed-grid proxy).")
    print("C3 FIXNC FATES + 100% forest-proxy PFT mixture: changes BOTH")
    print("   landunit fractions and vegetation functional composition.")
    print("C2/C3 are not validated without explicit site/flux-footprint")
    print("interpretation, landunit rationale, time representativeness,")
    print("and the unknown deciduous 2% assignment.")
    qc_report()
    print("\nSCIENTIFIC HOLD: choose explicit proxy/experiment before any write")
    print("READ ONLY COMPLETE: no source, case, Slurm job or model modified")

if __name__=="__main__":
    main()
