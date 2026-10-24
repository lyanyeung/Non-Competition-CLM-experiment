#!/usr/bin/env python3
"""READ ONLY DE-Tha soil texture: site-reported values vs original and new surface.

Primary field reference: DE-Tha tower forest first mineral horizon,
sand 17%, silt 71%, clay 12%; reported relatively constant to 1.2 m.
Reference: https://www.researchgate.net/publication/241243196_Net_Ecosystem_Exchange_and_Net_Biome_Productivity_of_different_land_use_in_eastern_Germany
Nearby 2024 Tharandt forest plots are NOT the same EC tower:
https://onlinelibrary.wiley.com/doi/10.1002/jpln.202400073

The original and derived NetCDFs must match pinned SHA256s. Report each model
soil layer; do not confuse layer index with an observational depth interval.
The new forest-PFT experiment has not changed soil texture. No writes.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
import numpy as np
from netCDF4 import Dataset

ROOT = Path("/iridisfs/scratch/ly3n24/CLM_FATES")
ORIG = ROOT / "sites/MY_EC_SITE/DE-Tha/subset_data/surfdata_DE-Tha_hist_2000_16pfts_c261011.nc"
NEW = ROOT / "experiments/NonCompetitionObserved22/DE-Tha/surface/surfdata_DE-Tha_ObsForest_FIXNC_ENF87_DNF10_DBF3_v1.nc"
EXPECTED_SHA = {
    ORIG:"7e4e4f8fc752d936f80e06a65db0f2163a3f74cdebff5d318973773450f5940d",
    NEW:"6d415b420ece0f18dca051c91849dcd5a3a5748779f9ee349c98e84e52e80600"
}
REF_SAND = 17.0
REF_SILT = 71.0
REF_CLAY = 12.0

def fail(m):
    raise RuntimeError(str(m))

def sha256(p):
    h=hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda:f.read(1048576), b""):
            h.update(chunk)
    return h.hexdigest()

def identity_check():
    for p,digest in EXPECTED_SHA.items():
        if not p.is_file() or p.is_symlink():
            fail("Missing or linked surface: "+str(p))
        actual=sha256(p)
        if actual != digest:
            fail(f"Pinned source changed: {p}\n  expected {digest}\n  actual {actual}")
        print(f"PASS SHA256 {p.name}: {actual}",flush=True)

def scalar_profile(ds, field):
    if field not in ds.variables:
        fail(f"Source surface lacks {field}")
    v=ds.variables[field]
    arr=np.ma.asarray(v[:])
    # Keep the full masked-array object for later identity comparison.
    data=np.ma.filled(arr.astype(float),np.nan)
    if not np.isfinite(data).all():
        fail(f"Missing/invalid values in {field}")
    axis_candidates=[i for i,d in enumerate(v.dimensions)
                     if "levsoi" in d.lower() or d.lower() in
                        ("nlevsoi","nlevgrnd","nlevsoil")]
    if len(axis_candidates)!=1:
        fail(f"Cannot identify one mineral-soil layer axis for {field}: {v.dimensions}")
    axis=axis_candidates[0]
    if any(s != 1 for i,s in enumerate(v.shape) if i!=axis):
        fail(f"Expected single point surface for {field}: {v.dimensions} {v.shape}")
    profile=np.moveaxis(data,axis,0).reshape(v.shape[axis])
    if profile.size<1 or profile.size>40:
        fail(f"Unexpected soil-layer count {field}: {profile.size}")
    if np.any(profile<0) or np.any(profile>100):
        fail(f"{field} values outside 0..100: {profile}")
    return profile, v

def soil_profile(ds):
    sand,vs=scalar_profile(ds,"PCT_SAND")
    clay,vc=scalar_profile(ds,"PCT_CLAY")
    if len(sand)!=len(clay):
        fail("Sand/clay soil layers differ")
    silt=100-sand-clay
    if (silt < -0.01).any() or (silt > 100.01).any():
        fail("Inconsistent sand+clay > 100 in soil profile")
    print("SOIL texture variable shapes:",vs.dimensions,vc.dimensions)
    print("SOIL units:",repr(getattr(vs,"units","UNSPECIFIED")),
          repr(getattr(vc,"units","UNSPECIFIED")))
    return sand,clay,silt

def texture_identity(original,derived,ds1,ds2):
    """Check soil texture and optional soil structural fields are untouched."""
    fields=sorted(set(ds1.variables).intersection(ds2.variables))
    names=[x for x in fields if any(key in x.upper() for key in
                 ("PCT_SAND","PCT_CLAY","ORGANIC","ORGMAT","SOIL_COLOR",
                  "PCT_GRAVEL","PCT_ROCK","PCT_STONE","SOILDEPTH"))]
    if not {"PCT_SAND","PCT_CLAY"}.issubset(set(names)):
        fail("Soil texture fields missing from comparison")
    for name in names:
        a=np.ma.asarray(ds1.variables[name][:])
        b=np.ma.asarray(ds2.variables[name][:])
        if a.shape!=b.shape or not np.array_equal(np.ma.getmaskarray(a),np.ma.getmaskarray(b)) or not np.array_equal(np.ma.getdata(a),np.ma.getdata(b),equal_nan=True):
            fail("Derived surface altered inherited soil variable: "+name)
        print("UNCHANGED:",name, "shape=",a.shape)
    if not np.array_equal(original[0],derived[0]) or not np.array_equal(original[1],derived[1]):
        fail("Derived soil texture changed")
    print("PASS: inherited sand/clay and listed soil fields identical to original")

def depth_info(ds, n):
    """Never invent depth from a 10-layer surface that lacks a depth coordinate."""
    for name in ("ZSOI","zsoi","levsoi","nlevsoi","soil_depth"):
        if name in ds.variables:
            v=ds.variables[name]
            a=np.ma.filled(v[:],np.nan).ravel()
            if len(a)==n and np.isfinite(a).all():
                if name=="nlevsoi" and np.array_equal(a,np.arange(1,n+1)):
                    continue
                units=str(getattr(v,"units","UNSPECIFIED"))
                if "m" in units.lower() and "mm" not in units.lower():
                    return [float(x) for x in a],units,name
                print(f"DEPTH CANDIDATE {name}={a} units={units}; not assumed physical depth")
    return None,None,None

def main():
    identity_check()
    print("\nFIELD-REPORTED TOWER REFERENCE: sand=17%, silt=71%, clay=12%")
    print("Horizon: first mineral layer; reported approximately stable to 1.2 m")
    print("REFERENCE: https://www.researchgate.net/publication/241243196_Net_Ecosystem_Exchange_and_Net_Biome_Productivity_of_different_land_use_in_eastern_Germany")
    print("CAUTION: 2024 non-tower Tharandt plots show high spatial texture variability")
    with Dataset(ORIG,"r") as original,Dataset(NEW,"r") as derived:
        s1,c1,si1=soil_profile(original)
        s2,c2,si2=soil_profile(derived)
        texture_identity((s1,c1,si1),(s2,c2,si2),original,derived)
        depth,units,depthkey=depth_info(original,len(s1))
        print("\n%-8s %-15s %10s %10s %10s %10s %10s" %
              ("LAYER","DEPTH_IF_FOUND","SAND %","SILT %","CLAY %","dSAND pp","dCLAY pp"))
        for i,(a,b,c) in enumerate(zip(s1,si1,c1),1):
            z=f"{depth[i-1]:.4f} {units}" if depth is not None else "UNKNOWN"
            print("%-8d %-15s %10.3f %10.3f %10.3f %+10.3f %+10.3f" %
                  (i,z,a,b,c,a-REF_SAND,c-REF_CLAY))
        if depth is None:
            print("DEPTH WARNING: No verified model mineral-soil depth coordinate.")
            print("             Layer index does not equal actual sampled depth.")
        else:
            print("DEPTH COORDINATE:",depthkey,";",units)
        # First grid mineral layer only. Full-depth agreement requires actual
        # layer boundary depths plus co-located field measurements.
        ds=abs(float(s1[0])-REF_SAND)
        dc=abs(float(c1[0])-REF_CLAY)
        siltd=abs(float(si1[0])-REF_SILT)
        print(f"\nTOP-MODEL-LAYER |delta sand|={ds:.2f} pp, "
              f"|delta silt|={siltd:.2f} pp, |delta clay|={dc:.2f} pp")
        print("INTERPRETATION GUIDE (not an empirical validation threshold):")
        if max(ds,dc,siltd)>10:
            print("LARGE_DIFFERENCE: >10 percentage points in at least one fraction")
        elif max(ds,dc,siltd)>5:
            print("NOTICEABLE_DIFFERENCE: >5 percentage points in at least one fraction")
        else:
            print("BROAD_NUMERIC_AGREEMENT: <=5 pp in all fractions for model top layer")
        print("NOTE: proximity does not prove the source grid and tower soil profiles match.")
    print("READ ONLY COMPLETE: no NetCDF, soil properties, model case or Slurm jobs modified")

if __name__=="__main__":
    main()
