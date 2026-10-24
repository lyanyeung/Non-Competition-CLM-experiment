#!/usr/bin/env python3
"""Batch01 Stage06: VALIDATE SITE SOIL EVIDENCE ONLY, without source fsurdat.

This is deliberately fail-closed: missing tower-field sand/silt/clay is not
filled from CLM grid or guessed from soil taxonomic names. For documented
measurements including stones, derive PCT_SAND/PCT_CLAY of the <2mm fine earth
by dividing by measured sand+silt+clay, separately at each measured horizon.
Do NOT populate unmeasured model layers or create a production NetCDF here.

Run: python3 -B examples/Batch01_10/scripts/06_audit_observed_soil_only.py
"""
from __future__ import annotations
import csv
import math
from pathlib import Path

CSV=Path(__file__).resolve().parents[3]/"data/batch01_10_soil_site_observations.csv"
SITES=("CZ-BK1","IT-Ren","RU-Fyo","CH-Dav","IT-Col",
       "FR-Fon","FI-Sod","FR-Pue","DE-Hai","BE-Vie")
NUM=("sand_pct_total","silt_pct_total","clay_pct_total","stones_pct_total")

def main():
    with CSV.open(encoding="utf-8-sig",newline="") as stream:
        rows=list(csv.DictReader(stream))
    if set(x["site"] for x in rows)!=set(SITES):
        raise SystemExit("ERROR: expected exactly ten Batch01 site IDs")
    measurements={k:[] for k in SITES}
    missing=set()
    for row in rows:
        site=row["site"]
        if row["data_status"]=="NEED_SITE_OBSERVATION":
            if any(row[k].strip() for k in
                   (*NUM,"depth_top_cm","depth_bottom_cm")):
                raise SystemExit("ERROR: unverified row includes numeric data: "+site)
            missing.add(site)
            continue
        if row["data_status"]!="STATION_PROFILE_REPORTED":
            raise SystemExit("ERROR: unreviewed evidence status at "+site)
        if not row["source"].startswith("https://"):
            raise SystemExit("ERROR: evidence source URL required at "+site)
        try:
            top=float(row["depth_top_cm"])
            bottom=float(row["depth_bottom_cm"])
            sand,silt,clay,stones=(float(row[k]) for k in NUM)
        except (ValueError,KeyError) as err:
            raise SystemExit("ERROR: invalid field soil data for "+site) from err
        if (not all(map(math.isfinite,(top,bottom,sand,silt,clay,stones))) or
            top<0 or top>=bottom or
            any(z<0 or z>100 for z in (sand,silt,clay,stones))):
            raise SystemExit("ERROR: field soil values out of physical bounds: "+site)
        fine=sand+silt+clay
        if fine<=0 or abs(fine+stones-100)>0.15:
            raise SystemExit("ERROR: texture+stone total not ~100: "+site)
        item=(top,bottom,100*sand/fine,100*silt/fine,100*clay/fine,stones)
        measurements[site].append(item)
    for site in SITES:
        depths=sorted(measurements[site])
        for prev,nxt in zip(depths,depths[1:]):
            if prev[1]>nxt[0]:
                raise SystemExit("ERROR: overlapping horizons for "+site)
        print(site, "SITE_SOIL_EVIDENCE",
              "MEASURED_HORIZONS="+str(len(depths)),
              "MISSING_SCIENTIFIC_EVIDENCE="+str(site in missing))
        for top,bottom,sand,silt,clay,stones in depths:
            print(f"  {top:g}-{bottom:g} cm: FINE_EARTH Sand={sand:.3f}% "
                  f"Silt={silt:.3f}% Clay={clay:.3f}% "
                  f"(original stones={stones:g}%, excluded)")
        if not depths:
            print("  HOLD: no measured sand/silt/clay; no grid substitution allowed")
        else:
            print("  HOLD: depth-to-CLM-layer mapping and deeper horizons not approved")
    print("TOTAL: measured sites=",sum(bool(x) for x in measurements.values()),
          "missing measured sites=",sum(not x for x in measurements.values()))
    print("NO PRODUCTION FSURDAT, NO SOURCE GRID TEXTURE, NO SLURM.")

if __name__=="__main__":
    main()
