#!/usr/bin/env python3
"""NonCompetition OzFlux09 Stage02: PFT-specific AU-ASM point surface pilot.

--preflight (DEFAULT): no file/surface/case changes. Verify immutable
Stage01 operator 9-site source snapshot, exact old AU-ASM Stage16
CTSM-2000 point reference SHA, 10 source L6 originals and physical
metadata coords for the remaining eight sites. Record missing coords,
CTSM input/tool readiness, and original reference soil/landunit schema.

--build-asm: after preflight and explicit confirmation, create exactly
ONE NEW AU-ASM FIXNC PFT candidate NetCDF by byte-copying the original
source-verified Stage16 CTSM point surface into a fresh HOME output
directory, modifying only the NATLAND PCT_NAT_PFT variable, adding
clearly labelled provenance attributes, then re-open and compare every
unchanged NetCDF variable to the source. Gridded soil is only a
REFERENCE, NOT independently tower-validated; the new surface is
NOT scientifically approved for AD5 or AD400. Never touch the existing
source, other sites, AU-How competition case, DATM, params, Slurm.

Source input: operator-accepted 2026-11-02 OzFlux PFT v1.1.
"""
from __future__ import annotations

import argparse
from collections import Counter
import csv
import hashlib
import json
import math
from pathlib import Path
import shutil
import sys
import time

import netCDF4
import numpy as np

HOME=Path.home()
CTSM_ROOT=Path("/iridisfs/scratch/ly3n24/CLM_FATES")
SOURCE=HOME/"ozflux_nc_stage01_20261102T215107Z"
DATA=HOME/"ozflux_nc_stage01_code"/"pft"
REF=HOME/"ozflux_stage16_reference_20261102T023647Z"/"surfdata_AU-ASM_hist_2000_16pfts_c261102.nc"
REF_SHA="18edace32d8e356c7d73269329dca7ed6338140e1ad1456f1a88691522c307fa"
REQUIRED_PFT_BLOB="698d702e83265290e3cf1f1890235b67ede290ee"
REQUIRED_FATES_BLOB="cec1df31f3e959e854aca6105a665a42321afa7c"
SITES=("AU-ASM","AU-Cow","AU-Cpr","AU-DaS","AU-Dry",
       "AU-Gin","AU-How","AU-Stp","AU-Tum")
ASM_LAT=-22.2828
ASM_LON=133.2493
MAX_COORD_AGREEMENT_DEG=0.05
CONFIRM="CREATE_NEW_AU_ASM_FIXNC_PFT_SURFACE_CANDIDATE_ONLY"
CANDIDATE_FILENAME="surfdata_AU-ASM_NC_FIXNC_PFT_v1p1_CTSM2000_SOIL_REFERENCE.nc"
ROWS=("site","raw_L6_count","raw_L6_present","latitude_candidates_json",
      "longitude_candidates_json","lat_lon_metadata_consistent",
      "coordinate_status","CTSM_surface_candidate_exists",
      "CTSM_surface_candidate_source","PFT_choice_percent_json",
      "bare_host0_percent","FATES_mapping_effective_case_verified",
      "met_DATM_science_approved","soil_science_approved","AD5_authorised",
      "AD400_authorised")

def sha256(path):
    h=hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda:f.read(4*1024*1024),b""):h.update(chunk)
    return h.hexdigest()

def gitblob(path):
    b=path.read_bytes()
    h=hashlib.sha1()
    h.update(("blob "+str(len(b))+"\0").encode())
    h.update(b)
    return h.hexdigest()

def csvlist(path,delimiter=","):
    if path.is_symlink() or not path.is_file():
        raise ValueError("Missing/symlink original input "+str(path))
    with path.open("r",encoding="utf-8-sig",newline="") as f:
        rdr=csv.DictReader(f,delimiter=delimiter)
        records=list(rdr)
    if not records or any(None in r for r in records):
        raise ValueError("Unexpected source CSV schema "+str(path))
    return records

def source_gate():
    p=SOURCE/"ozflux09_operator_PFT_and_IRIDIS_readiness.json"
    if not p.is_file() or p.is_symlink():
        raise ValueError("Actual operator Stage01 PFT source receipt missing "+str(p))
    doc=json.loads(p.read_text(encoding="utf-8"))
    if (doc.get("source_commit")!="d62c814585c4aa85731f77b4a555efe6ec9e94a3"
        or len(doc.get("operator_accepted_PRIMARY_PFT_9_sites",[]))!=9
        or doc.get("AD400_authorised") is not False
        or doc.get("new_surface_or_forcing_or_model_case_created") is not False):
        raise ValueError("Operator Stage01 PFT receipt version/status differs")
    matrix=DATA/"OZFLUX_09_PRIMARY_CLM_PCT_NAT_PFT_20261102.csv"
    fates=DATA/"OZFLUX_09_PRIMARY_FATES_PFT_PERCENT_20261102.csv"
    if any(not x.is_file() or x.is_symlink() for x in (matrix,fates)):
        raise ValueError("Git-snapshotted PFT CSV missing")
    if gitblob(matrix)!=REQUIRED_PFT_BLOB or gitblob(fates)!=REQUIRED_FATES_BLOB:
        raise ValueError("Git PFT source snapshot SHA mismatch")
    src=csvlist(matrix)
    if len(src)!=9 or Counter(r["site"] for r in src)!=Counter(SITES):
        raise ValueError("Nine PFT site membership/count mismatch")
    originals=csvlist(DATA/"OZFLUX_09_ORIGINAL_L6_SITES_MANIFEST.tsv","\t")
    if len(originals)!=10:raise ValueError("Original L6 10-file manifest count differs")
    return doc,{x["site"]:x for x in src},originals,{"stage01_operator_receipt_sha256":sha256(p),
           "source_9_site_clm_PFT_blob":gitblob(matrix),
           "source_9_site_fates_PFT_blob":gitblob(fates)}

def pft_values(row):
    vals=[float(row[f"PCT_NAT_PFT_{i}"]) for i in range(15)]
    if any(not math.isfinite(x) or x<0 or x>100 for x in vals):
        raise ValueError("Nonfinite or invalid input host PFT")
    if abs(sum(vals)-100)>0.00005:raise ValueError("PFT natland 100% not closed")
    return vals

def exact_ref():
    if REF.is_symlink() or not REF.is_file() or sha256(REF)!=REF_SHA:
        raise ValueError("Actual Stage16 AU-ASM point reference surface SHA mismatch")
    with netCDF4.Dataset(str(REF),"r") as ds:
        needed=("LATIXY","LONGXY","PCT_NAT_PFT","PCT_SAND","PCT_CLAY","ORGANIC")
        if any(x not in ds.variables for x in needed):
            raise ValueError("Reference source missing critical fields")
        lat=np.asarray(ds.variables["LATIXY"][:],dtype=float).ravel()
        lon=np.asarray(ds.variables["LONGXY"][:],dtype=float).ravel()
        pft=np.asarray(ds.variables["PCT_NAT_PFT"][:],dtype=float).ravel()
        sand=np.asarray(ds.variables["PCT_SAND"][:],dtype=float).ravel()
        clay=np.asarray(ds.variables["PCT_CLAY"][:],dtype=float).ravel()
        organic=np.asarray(ds.variables["ORGANIC"][:],dtype=float).ravel()
        if (len(lat)!=1 or len(lon)!=1
            or abs(float(lat[0])-ASM_LAT)>MAX_COORD_AGREEMENT_DEG
            or abs((float(lon[0])-ASM_LON+180)%360-180)>MAX_COORD_AGREEMENT_DEG):
            raise ValueError("Stage16 coordinate differs from exact AU-ASM source")
        if len(pft) not in (15,16) or np.ma.count_masked(ds.variables["PCT_NAT_PFT"][:]):
            raise ValueError("Reference NAT PFT vector length/mask unexpected")
        if (not np.isfinite(pft).all() or abs(pft.sum()-100)>0.15
            or not all(np.isfinite(x).all() for x in (sand,clay,organic))
            or len(sand)!=10 or len(clay)!=10 or len(organic)!=10
            or np.any(sand<0) or np.any(clay<0) or np.any(sand+clay>100.001)):
            raise ValueError("Reference soil/PFT lacks required physical schema")
        return {
          "path":str(REF),"sha256":REF_SHA,
          "latitude":float(lat[0]),"longitude":float(lon[0]),
          "PCT_NAT_PFT_source":pft.tolist(),
          "natpft_slots":int(len(pft)),
          "sand_reference_per_layer":sand.tolist(),
          "clay_reference_per_layer":clay.tolist(),
          "organic_reference_per_layer":organic.tolist(),
          "science_status":"CTSM_GRID_REFERENCE_ONLY; NO SITE SOIL SCIENCE APPROVAL",
        }

def numeric_attr(v):
    if v is None:return None
    try:
        if hasattr(v,"__len__") and not isinstance(v,(bytes,str)):
            if len(v)!=1:return None
            v=v[0]
        x=float(v)
        return x if math.isfinite(x) else None
    except (ValueError,TypeError,OverflowError):
        return None

def coords_from_l6(path):
    """Metadata-only: never load original flux time series into RAM."""
    observed={"lat":[],"lon":[]}
    accepted={
        "lat":("latitude","lat","lat_site","latitude_deg","site_latitude",
               "tower_latitude","Latitude","LATITUDE","Lat"),
        "lon":("longitude","lon","long","lon_site","longitude_deg",
               "site_longitude","tower_longitude","Longitude","LONGITUDE","Lon"),
    }
    with netCDF4.Dataset(str(path),"r") as ds:
        attrs={a:ds.getncattr(a) for a in ds.ncattrs()}
        for axis,names in accepted.items():
            for k in names:
                if k in attrs:
                    val=numeric_attr(attrs[k])
                    if val is not None:observed[axis].append({"from":"global:"+k,"value":val})
                if k in ds.variables and ds.variables[k].size==1:
                    var=ds.variables[k]
                    val=numeric_attr(var[:])
                    if val is not None:observed[axis].append({"from":"variable:"+k,"value":val})
        # L6 PyFluxPro often stores site coordinates on
        # global attributes with names like 'site_latitude'.
        # Do NOT parse unconstrained comments or infer coordinates.
    return observed

def coordinate_summary(items):
    out={}
    for axis,vals in items.items():
        x=[v["value"] for v in vals]
        if not x:
            out[axis]={"status":"MISSING_EXPLICIT_NC_METADATA","candidates":[],"coordinate":None}
            continue
        valid=(-45<=a<=-8 for a in x) if axis=="lat" else (110<=a<=156 for a in x)
        if not all(valid):
            out[axis]={"status":"OUTSIDE_AUSTRALIA_BOUNDS","candidates":vals,"coordinate":None}
            continue
        if max(x)-min(x)>MAX_COORD_AGREEMENT_DEG:
            out[axis]={"status":"CONFLICTING_SOURCE_CANDIDATES","candidates":vals,"coordinate":None}
            continue
        out[axis]={"status":"NC_METADATA_CANDIDATE_NOT_INDEPENDENT_VERIFIED",
                   "candidates":vals,"coordinate":sum(x)/len(x)}
    return out

def inspect_others(pft_rows, original_l6):
    root=CTSM_ROOT/"sites/MY_EC_SITE"
    report=[]
    for site in SITES:
        rows=[r for r in original_l6 if r["site"]==site]
        if len(rows)!=(2 if site=="AU-ASM" else 1):
            raise ValueError("Wrong number of L6 source files "+site)
        source_coord=[]
        for entry in rows:
            path=root/site/"forcing/raw"/entry["filename"]
            if not path.is_file() or path.is_symlink():
                raise ValueError("Missing original L6 physical input "+str(path))
            c=coords_from_l6(path)
            source_coord.extend([(entry["filename"],c)])
        allvalues={"lat":[],"lon":[]}
        for filename,xy in source_coord:
            for axis in ("lat","lon"):
                allvalues[axis]+=[{"from":filename+" "+r["from"],"value":r["value"]}
                                 for r in xy[axis]]
        co=coordinate_summary(allvalues)
        lat,lon=co["lat"],co["lon"]
        ok=lat["coordinate"] is not None and lon["coordinate"] is not None
        report.append({
            "site":site,"raw_L6_count":len(rows),"raw_L6_present":len(rows),
            "latitude_candidates_json":json.dumps(lat,sort_keys=True),
            "longitude_candidates_json":json.dumps(lon,sort_keys=True),
            "lat_lon_metadata_consistent":ok,
            "coordinate_status":"L6_METADATA_UNVERIFIED_BY_OFFICIAL_SITE" if ok else "NEEDS_EXPLICIT_COORDINATE_EVIDENCE",
            "CTSM_surface_candidate_exists":site=="AU-ASM",
            "CTSM_surface_candidate_source":str(REF) if site=="AU-ASM" else "",
            "PFT_choice_percent_json":json.dumps({
              str(i):v for i,v in enumerate(pft_values(pft_rows[site])) if v>0},sort_keys=True),
            "bare_host0_percent":pft_values(pft_rows[site])[0],
            "FATES_mapping_effective_case_verified":False,
            "met_DATM_science_approved":False,
            "soil_science_approved":False,
            "AD5_authorised":False,"AD400_authorised":False,
        })
    return report

def copy_candidate(pft_row,out):
    if out.exists():raise ValueError("Output folder already exists")
    new=out/CANDIDATE_FILENAME
    out.mkdir(mode=0o700,exist_ok=False,parents=False)
    shutil.copyfile(REF,new)
    expect=pft_values(pft_row)
    with netCDF4.Dataset(str(new),"r+") as ds:
        var=ds.variables["PCT_NAT_PFT"]
        n=int(np.prod(var.shape))
        if n not in (15,16):
            raise ValueError("PFT slot count unexpectedly changed")
        arr=np.array(expect+([0.0] if n==16 else []),dtype=np.float64).reshape(var.shape)
        var[:]=arr
        ds.setncattr("ozflux_nc_experiment","FIXNC NEW SURFACE CANDIDATE; not approved model input")
        ds.setncattr("ozflux_PFT_source_branch","oz-jp-pft-guidance-20261102")
        ds.setncattr("ozflux_PFT_source_commit","d62c814585c4aa85731f77b4a555efe6ec9e94a3")
        ds.setncattr("ozflux_reference_surface_sha256",REF_SHA)
        ds.setncattr("ozflux_original_soil_source","unchanged CTSM2000 point GRID reference; tower soil science HOLD")
        ds.setncattr("ozflux_bare_ground_host_index","0; preserved in natural-land fraction")
        ds.setncattr("ozflux_model_authorised","NO; AD5 and AD400 not submitted")
    with netCDF4.Dataset(str(REF),"r") as before,netCDF4.Dataset(str(new),"r") as after:
        if set(before.variables)!=set(after.variables):
            raise ValueError("Candidate variables differ from reference")
        changed=[]
        for k in before.variables:
            aa=np.ma.array(before.variables[k][:])
            bb=np.ma.array(after.variables[k][:])
            if aa.shape!=bb.shape:raise ValueError("Source variable shape changed "+k)
            if k=="PCT_NAT_PFT":
                if not np.allclose(np.asarray(bb).ravel(),
                    np.array(expect+([0.0] if bb.size==16 else [])),
                    atol=2.5e-5,rtol=0):
                    raise ValueError("New 9-site input vector not represented in AU-ASM surface")
                changed.append(k)
            elif not np.ma.allequal(aa,bb):
                raise ValueError("Non-PFT source variable changed: "+k)
        if changed!=["PCT_NAT_PFT"]:
            raise ValueError("Source-diff scope not exact natPFT variable")
    return {"candidate_path":str(new),"candidate_sha256":sha256(new),
            "changed_existing_variables":["PCT_NAT_PFT"],
            "original_reference_surface_SHA256":REF_SHA,
            "source_NAT_PFT_natland_percent":expect,
            "gridded_soil_and_all_other_variables_bitwise_values_preserved":True,
            "point_surface_model_science_approved":False,
            "DATM_and_effective_case_FATES_mapping_verified":False,
            "AD5_or_AD400_authorised":False}

def self_test():
    x={"site":"AU-ASM",**{f"PCT_NAT_PFT_{i}":"0" for i in range(15)}}
    for i,v in ((0,29),(5,65),(13,2),(14,4)):x[f"PCT_NAT_PFT_{i}"]=str(v)
    assert pft_values(x)[0]==29 and sum(pft_values(x))==100
    good=coordinate_summary({"lat":[{"from":"x","value":-22.28}],
                             "lon":[{"from":"x","value":133.25}]})
    assert good["lat"]["coordinate"]<0 and good["lon"]["coordinate"]>0
    missing=coordinate_summary({"lat":[],"lon":[]})
    assert missing["lat"]["coordinate"] is None
    assert coordinate_summary({"lat":[{"from":"a","value":-20},
                                    {"from":"b","value":-23}],
                               "lon":[]})["lat"]["status"]=="CONFLICTING_SOURCE_CANDIDATES"
    assert CONFIRM.startswith("CREATE_NEW_")
    print("OZFLUX NC STAGE02 SELF-TEST PASS: isolated ASM PFT vector, source coordinate conflict/missing safeguards; NO SOURCE CHANGES")

def main():
    if sys.argv[1:]==["--self-test"]:
        self_test();return
    ap=argparse.ArgumentParser(description=__doc__)
    mode=ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--preflight",action="store_true")
    mode.add_argument("--build-asm",action="store_true")
    ap.add_argument("--confirm")
    ap.add_argument("--out",type=Path,required=True)
    args=ap.parse_args()
    out=args.out.resolve()
    if (args.out.is_symlink() or out.exists() or out.parent!=HOME.resolve()
        or CTSM_ROOT.resolve()==out or CTSM_ROOT.resolve() in out.parents):
        raise ValueError("Use a new direct HOME output folder only")
    rec,pft,originals,provenance=source_gate()
    reference=exact_ref()
    rows=inspect_others(pft,originals)
    mode_name="PREFLIGHT_READONLY" if args.preflight else "BUILD_ISOLATED_AU_ASM_FIXNC_PFT_CANDIDATE"
    print("STAGE02 SOURCE SHA VERIFIED",provenance)
    print("STAGE02 AU-ASM REFERENCE SURFACE SHA VERIFIED",REF_SHA)
    for r in rows:
        print("SITE",r["site"],"RAW_L6",r["raw_L6_present"],"SOURCE COORDS",
              r["coordinate_status"],"PFT",r["PFT_choice_percent_json"])
    build=None
    if args.build_asm:
        if args.confirm!=CONFIRM:
            raise ValueError("Build confirmation missing, require "+CONFIRM)
        build=copy_candidate(pft["AU-ASM"],out)
        print("STAGE02 ASM FIXNC PFT SURFACE CANDIDATE WRITTEN",build)
    else:
        out.mkdir(mode=0o700,exist_ok=False,parents=False)
        print("STAGE02 PREVIEW ONLY; NO SOURCE/SURFACE/MODEL FILE MODIFIED")
    report={
      "stage":"OzFlux non-competition Stage02 9-site surface coordinate gate and isolated AU-ASM v1.1 PFT candidate",
      "mode":mode_name,
      "source_operator_stage01":provenance,
      "reference_AU_ASM_CTSM2000":reference,
      "site_PFT_and_L6_coordinates":rows,
      "new_AU_ASM_isolated_surface":build,
      "no_old_case_or_original_source_or_forcing_or_params_modified":True,
      "gridded_soil_not_tower_profile":True,
      "PFT_source_operator_selected":True,
      "PFT_input_not_independent_observation":True,
      "site_specific_soil_science_approved":False,
      "DATM_and_native_clock_science_approved":False,
      "CIME_FATES_effective_mapping_verified":False,
      "AD5_authorised":False,"AD400_authorised":False,
      "Slurm_jobs_submitted":False,
    }
    with (out/"ozflux09_stage02_9site_reference_surface_and_coordinate_register.tsv").open(
       "x",encoding="utf-8",newline="") as f:
        w=csv.DictWriter(f,delimiter="\t",fieldnames=ROWS,extrasaction="raise")
        w.writeheader();w.writerows(rows)
    (out/"ozflux09_stage02_ASM_FIXNC_surface_candidate_science_HOLD.json").write_text(
       json.dumps(report,ensure_ascii=False,indent=2,allow_nan=False),encoding="utf-8")
    print("STAGE02 MODE",mode_name,"9/9 ORIGINAL L6 PRESENT, ASM reference source verified")
    print("STAGE02 NEW FIXNC PFT SURFACE CREATED",bool(build))
    print("STAGE02 UNVERIFIED SOIL/DATM/CASE MAP; NO AD5/AD400, NO SLURM")
    print("REPORT_DIR",out)

if __name__=="__main__":
    main()
