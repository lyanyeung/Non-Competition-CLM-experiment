#!/usr/bin/env python3
"""Batch01 Stage10 | CZ-BK1: audit forcing, validate FATES map, stage surface.

Modes:
  --action self-test : no HPC files, no writes
  --action audit     : read-only model inputs; report written under HOME
  --action build     : EXPLICIT OPT-IN; create a new, isolated candidate NetCDF
  --action verify    : read-only verify the independently versioned candidate

The user has selected CZ-BK1 ENF100, NATVEG100/CROP0 and Flechard (2020)
Table S4 sand/silt/clay 22/58/21 (published sum 101). The all-10-texture-layer
constant assumption is NOT observed at each depth; 'build' requires a separate
exact ACK. It does not edit originals/CIME, submit jobs or certify AD5 readiness.
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
import math
import os
import shutil
import tempfile
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path("/iridisfs/scratch/ly3n24/CLM_FATES")
REPO = Path(__file__).resolve().parents[3]
CASE = ROOT / "cases/CZ-BK1_FATES_SPINUP500"
SOURCE = ROOT / "sites/MY_EC_SITE/CZ-BK1/subset_data/surfdata_CZ-BK1_hist_2000_16pfts_c261012.nc"
PARAM = ROOT / "CTSM/src/fates/parameter_files/fates_params_default.json"
STREAM = CASE / "CaseDocs/datm.streams.xml"
S4 = REPO / "data/batch01_10_Flechard2020_TableS4_soil.csv"
DECISIONS = REPO / "data/batch01_10_soil_input_decisions.csv"
SCENARIOS = REPO / "data/batch01_10_pft_scenarios.csv"
OUT = (ROOT / "experiments/NonCompetitionObserved22/Batch01_10/CZ-BK1/surface"
       / "surfdata_CZ-BK1_FIXNC_ENF100_SoilFlechardS4_uniform10_v1.nc")
RECEIPT = OUT.with_suffix(".json")
ACK = "ACCEPT_CZ_BK1_FLECHARD_S4_UNIFORM_TEN_TEXTURE_LAYERS_AS_MODEL_PROXY"
LAND_OTHER = ("PCT_LAKE", "PCT_WETLAND", "PCT_GLACIER", "PCT_URBAN")
CHANGED = ("PCT_NATVEG", "PCT_CROP", "PCT_NAT_PFT", "PCT_SAND", "PCT_CLAY")
PFT_NAME = "needleleaf_evergreen_extratrop_tree"
TIME_STEPS_EXPECTED = 365 * 48  # ONLY for existing half-hourly NO_LEAP station files
YEARS = tuple(range(2004, 2026))


def stop(msg):
    raise RuntimeError(str(msg))


def sha(path):
    h=hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda:f.read(1024*1024),b""):
            h.update(chunk)
    return h.hexdigest()


def rows_by_site(path):
    with path.open(encoding="utf-8-sig",newline="") as f:
        return {row["site"]:row for row in csv.DictReader(f)}


def composition():
    s4=rows_by_site(S4)["CZ-BK1"]
    d=rows_by_site(DECISIONS)["CZ-BK1"]
    mix=rows_by_site(SCENARIOS)["CZ-BK1"]
    if d["soil_texture_decision"]!="FLECHARD2020_S4_STATION_TEXTURE_SELECTED":
        stop("CZ-BK1 soil choice changed in decision CSV")
    if any(float(mix[k])!=(100 if k=="ENF" else 0)
           for k in ("ENF","DNF","DBF","EBF")):
        stop("CZ-BK1 tree mix is no longer ENF100")
    raw={k:float(s4[k+"_pct_reported"]) for k in ("sand","silt","clay")}
    if raw!={"sand":22.,"silt":58.,"clay":21.}:
        stop("Source Flechard S4 values changed")
    t=sum(raw.values())
    if t!=101:
        stop("Published rounding sum was expected to be 101")
    return {
        "reported_flechard_S4_sand_silt_clay":raw,
        "reported_sum":t,
        "normalization":"divide each literature percentage by 101; do not call this independently measured",
        "new_surface_fine_earth_pct":{k:100*v/t for k,v in raw.items()},
        "reported_site_soil_depth_m":0.55,
        "soil_texture_sampled_vertical_intervals":"NOT_REPORTED_BY_TABLE_S4",
        "proposed_input_layer_policy":"UNIFORM_ALL_10_TEXTURE_INPUT_LAYERS_IS_UNMEASURED_EXTRAPOLATION",
    }


def stream_data():
    if not STREAM.is_file() or STREAM.is_symlink():
        stop("Original generated DATM stream absent/symlink")
    root=ET.parse(STREAM).getroot()
    def field(name):
        el=root.find(".//"+name)
        if el is None or not el.text:
            stop("Missing DATM stream tag: "+name)
        return el.text.strip()
    years=(int(field("year_first")),int(field("year_last")),int(field("year_align")))
    if years!=(2004,2025,2004):
        stop("Unexpected DATM years "+str(years))
    paths=[p.text.strip() for p in root.findall(".//datafiles/file")
           if p.text and p.text.strip()]
    if len(paths)!=len(YEARS) or len(set(paths))!=len(paths):
        stop("Expected 22 unique annual forcing files in XML")
    for year,actual in zip(YEARS,paths):
        file=Path(actual)
        if (file.name!=f"CZ-BK1_DATM_{year}.nc" or
            "datm_v5_candidate_timevarying_zbot" not in file.parts):
            stop("DATM file order/name changed: "+str(file))
        if not str(file).startswith(str(ROOT/"sites/MY_EC_SITE/CZ-BK1/forcing")+"/"):
            stop("DATM file escapes station forcing folder: "+str(file))
    return {"year_first":years[0],"year_last":years[1],
            "year_align":years[2],"files":paths,"stream_sha256":sha(STREAM)}


def verify_mapping():
    if not PARAM.is_file() or PARAM.is_symlink():
        stop("FATES default parameter JSON unavailable")
    import numpy as np
    doc=json.loads(PARAM.read_text(encoding="utf8"))
    params=doc["parameters"]
    names=params["fates_pftname"]["data"]
    mat=np.asarray(params["fates_hlm_pft_map"]["data"],dtype=float)
    if len(names)!=14 or mat.shape!=(14,14):
        stop("Unexpected FATES PFT mapping dimension")
    row=mat[0]  # CLM natpft index1 -> fates HLM map row index0
    found=np.flatnonzero(row>0)
    if (len(found)!=1 or not np.isclose(row[found[0]],1) or
        names[int(found[0])]!=PFT_NAME):
        stop("CLM natpft index1 does not map uniquely to expected FATES ENF")
    return {"source":str(PARAM),"sha256":sha(PARAM),
            "clm_natpft_index":1,
            "fates_species_name":names[int(found[0])]}


def surface_schema():
    import numpy as np
    from netCDF4 import Dataset
    if not SOURCE.is_file() or SOURCE.is_symlink():
        stop("Source surface missing/symlink; cannot use technical schema")
    result={"source":str(SOURCE),"sha256":sha(SOURCE)}
    with Dataset(str(SOURCE),"r") as ds:
        for name in CHANGED:
            if name not in ds.variables:
                stop("Source schema required variable missing: "+name)
        for name in ("PCT_NATVEG","PCT_CROP"):
            if ds.variables[name].size!=1:
                stop("Expected one-point landunit variable "+name)
        pft=ds.variables["PCT_NAT_PFT"]
        if "natpft" not in pft.dimensions:
            stop("Missing expected natpft axis")
        paxis=pft.dimensions.index("natpft")
        if pft.shape[paxis]!=15 or any(
                v!=1 for i,v in enumerate(pft.shape) if i!=paxis):
            stop("Expected CLM natural PFT array 15x1x1")
        shapes={}
        for field in ("PCT_SAND","PCT_CLAY"):
            var=ds.variables[field]
            axes=[i for i,k in enumerate(var.dimensions)
                  if "levsoi" in k.lower() or k.lower() in ("nlevgrnd","nlevsoil")]
            if len(axes)!=1 or var.shape[axes[0]]!=10 or any(
                    n!=1 for i,n in enumerate(var.shape) if i!=axes[0]):
                stop("Unexpected 10-layer soil texture shape: "+field)
            if not np.issubdtype(var.dtype,np.floating):
                stop("Soil texture variable is not floating point: "+field)
            shapes[field]={"shape":list(var.shape),
                           "dimensions":list(var.dimensions)}
        for field in LAND_OTHER:
            if field in ds.variables:
                a=np.ma.filled(ds.variables[field][:],np.nan)
                if not np.isfinite(a).all() or not np.allclose(a,0,atol=1e-6):
                    stop("Non-zero source non-forest landunit needs explicit handling: "+field)
        result["soil_shapes"]=shapes
        result["natpft_shape"]=list(pft.shape)
        result["soil_structure"]="Actual old lnd_in: 20SL_8.5m; 10 texture INPUT layers, not 10 reported observed horizons"
        result["other_required_landunit_fields_zero"]=True
        result["old_source_values_policy"]="SCHEMA_ONLY; DO NOT USE SOURCE GRID LANDCOVER OR SOIL TEXTURE AS SCIENCE"
    return result


def check_forcing(paths):
    from netCDF4 import Dataset
    out=[]
    bad=[]
    for year,file in zip(YEARS,paths):
        path=Path(file)
        info={"year":year,"path":str(path),"exists":path.is_file()}
        if not path.is_file():
            info["status"]="MISSING"
            bad.append(str(path))
        else:
            try:
                with Dataset(str(path),"r") as ds:
                    t=ds.variables.get("time")
                    if t is None:
                        info["status"]="NO_TIME_VARIABLE"
                    else:
                        info["time_len"]=int(t.size)
                        info["calendar"]=str(getattr(t,"calendar","NOT_DECLARED"))
                        info["time_units"]=str(getattr(t,"units","NOT_DECLARED"))
                        if t.size==TIME_STEPS_EXPECTED:
                            info["status"]="HALF_HOURLY_NOLEAP_COUNT_PLAUSIBLE"
                        else:
                            info["status"]="REVIEW_TIME_LENGTH"
                    info["variables"]=list(ds.variables)[:60]
                    info["dimensions"]={k:len(v) for k,v in ds.dimensions.items()}
                    if info["status"]!="HALF_HOURLY_NOLEAP_COUNT_PLAUSIBLE":
                        bad.append(f"{year}:{info['status']}")
            except Exception as exc:
                info["status"]="READ_ERROR:"+repr(exc)
                bad.append(f"{year}:{info['status']}")
        out.append(info)
    return {"files":out,"count":len(out),
            "all_22_annual_files_readable_and_expected_timesteps":not bool(bad),
            "problems":bad,
            "remaining_checks":"Validate actual time coordinate/bounds, leap handling, physical forcing variables, QC and effective runtime streams; length alone is not sufficient"}


def audit(stage09):
    if not stage09.is_file() or stage09.name!="all_sites.json" or not (
            stage09.parent.name.startswith("Batch01_10_stage09_CZ_AD5_inputs_")):
        stop("Expected original Stage09 saved JSON")
    data=json.loads(stage09.read_text(encoding="utf8"))
    if (data.get("site")!="CZ-BK1" or data.get("source_modified") is not False
        or data.get("slurm_submitted") is not False):
        stop("Stage09 provenance/safety mismatch")
    status={}
    status["stage09"]={"path":str(stage09),"sha256":sha(stage09)}
    status["soil"]=composition()
    status["forcing_config"]=stream_data()
    status["fates_map"]=verify_mapping()
    status["source_surface"]=surface_schema()
    status["forcing_content"]=check_forcing(status["forcing_config"]["files"])
    status["all_basic_checks_pass"]=status["forcing_content"][
        "all_22_annual_files_readable_and_expected_timesteps"]
    status["new_case_created"]=False
    status["new_surface_created"]=False
    status["slurm_submitted"]=False
    out=(Path.home().resolve()/("Batch01_10_stage10_CZ_surface_audit_"+
          datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")))
    out.mkdir(mode=0o700,exist_ok=False)
    dest=out/"audit.json"
    dest.write_text(json.dumps(status,indent=2,ensure_ascii=False)+"\n",
                    encoding="utf8")
    print("CZ STAGE10 AUDIT | NO MODEL INPUT WRITES")
    print("SELECTED CZ FINE-EARTH CANDIDATE:",status["soil"]["new_surface_fine_earth_pct"])
    print("FATES MAP VERIFIED:",status["fates_map"]["fates_species_name"])
    print("DATM years:",status["forcing_config"]["year_first"],
          "-",status["forcing_config"]["year_last"])
    print("FORCING METADATA:",status["forcing_content"]["count"],
          "files; expected half-hourly counts pass:",
          status["all_basic_checks_pass"])
    if not status["all_basic_checks_pass"]:
        print("FORCING PROBLEMS:",status["forcing_content"]["problems"])
    print("SOIL NOTE: uniform profile across 10 input layers is an UNMEASURED proxy.")
    print("REPORT:",dest)
    print("NO NETCDF CREATED, NO CIME CASES, NO SLURM.")
    return dest


def checked_report(path):
    if (path.name!="audit.json" or not path.parent.name.startswith(
            "Batch01_10_stage10_CZ_surface_audit_") or not path.is_file()):
        stop("Expected original saved Stage10 audit.json")
    report=json.loads(path.read_text(encoding="utf8"))
    if report.get("all_basic_checks_pass") is not True:
        stop("Forcing metadata audit was not green")
    c=composition()
    if report["soil"]!=c:
        stop("CZ soil publication/decision data changed since audit")
    for file,current in (
        (SOURCE,report["source_surface"]["sha256"]),
        (PARAM,report["fates_map"]["sha256"]),
        (STREAM,report["forcing_config"]["stream_sha256"]),
    ):
        if sha(file)!=current:
            stop("Audited input changed; re-audit instead of building "+str(file))
    if report.get("slurm_submitted") is not False:
        stop("Unexpected Slurm flag")
    return report


def same_array(a,b):
    import numpy as np
    aa=np.ma.asarray(a)
    bb=np.ma.asarray(b)
    if aa.shape!=bb.shape or aa.dtype!=bb.dtype:
        return False
    if not np.array_equal(np.ma.getmaskarray(aa),np.ma.getmaskarray(bb)):
        return False
    x=np.ma.getdata(aa)
    y=np.ma.getdata(bb)
    if np.issubdtype(x.dtype,np.inexact):
        return bool(np.array_equal(x,y,equal_nan=True))
    return bool(np.array_equal(x,y))


def validate_candidate(path,report):
    import numpy as np
    from netCDF4 import Dataset
    desired=report["soil"]["new_surface_fine_earth_pct"]
    with Dataset(str(SOURCE),"r") as src, Dataset(str(path),"r") as ds:
        if set(src.dimensions)!=set(ds.dimensions) or set(src.variables)!=set(ds.variables):
            stop("New candidate lost original schema dimensions or variables")
        for k in src.dimensions:
            if len(src.dimensions[k])!=len(ds.dimensions[k]):
                stop("Changed dimension length: "+k)
        for k in src.variables:
            a,b=src.variables[k],ds.variables[k]
            if a.dimensions!=b.dimensions or a.dtype!=b.dtype:
                stop("Changed variable layout: "+k)
            if k not in CHANGED and not same_array(a[:],b[:]):
                stop("An unrelated variable changed: "+k)
        for k,v in (("PCT_NATVEG",100.),("PCT_CROP",0.)):
            a=np.ma.filled(ds.variables[k][:],np.nan)
            if a.size!=1 or not np.isclose(float(a.ravel()[0]),v,atol=1e-5):
                stop("Invalid new landunit "+k)
        pft=np.ma.filled(ds.variables["PCT_NAT_PFT"][:],np.nan).ravel()
        required=np.zeros(15)
        required[1]=100.
        if not np.allclose(pft,required,atol=0.001,rtol=0):
            stop("New CLM 15-PFT distribution not ENF100 at index1")
        for key,target in (("PCT_SAND",desired["sand"]),
                           ("PCT_CLAY",desired["clay"])):
            v=np.ma.filled(ds.variables[key][:],np.nan)
            if v.size!=10 or not np.allclose(v,target,atol=1e-4,rtol=0):
                stop("New soil variable differs from acknowledged 10-layer proxy: "+key)
    return True


def build(args):
    if args.ack_uniform_ten_layer_soil_proxy!=ACK:
        stop("Cannot create uniform profile without exact --ack-uniform-ten-layer-soil-proxy "+ACK)
    if args.audit_json is None:
        stop("--audit-json required for build")
    report=checked_report(args.audit_json.expanduser().resolve())
    if OUT.exists() or OUT.is_symlink() or RECEIPT.exists():
        stop("New CZ-BK1 candidate surface/receipt already exists: refuse overwrite")
    OUT.parent.mkdir(parents=True,exist_ok=True)
    import numpy as np
    from netCDF4 import Dataset
    fd,tmpname=tempfile.mkstemp(dir=OUT.parent,prefix=".CZ-BK1-stage10-",suffix=".nc")
    os.close(fd)
    tmp=Path(tmpname)
    try:
        shutil.copyfile(SOURCE,tmp)
        desired=report["soil"]["new_surface_fine_earth_pct"]
        with Dataset(str(tmp),"r+") as ds:
            ds.variables["PCT_NATVEG"][:]=100.
            ds.variables["PCT_CROP"][:]=0.
            pft=ds.variables["PCT_NAT_PFT"]
            vals=np.zeros(pft.shape,dtype=float)
            axis=pft.dimensions.index("natpft")
            addr=[0]*vals.ndim
            addr[axis]=1
            vals[tuple(addr)]=100.
            pft[:]=vals
            for key,target in (("PCT_SAND",desired["sand"]),
                               ("PCT_CLAY",desired["clay"])):
                v=ds.variables[key]
                v[:]=np.full(v.shape,target,dtype=float)
        validate_candidate(tmp,report)
        if sha(SOURCE)!=report["source_surface"]["sha256"]:
            stop("Source changed during build")
        receipt={
            "site":"CZ-BK1",
            "model_description":"FIXNC ENF100 / NATVEG100 / CROP0",
            "stage10_audit":str(args.audit_json.expanduser().resolve()),
            "stage10_audit_sha256":sha(args.audit_json.expanduser().resolve()),
            "source_surface":str(SOURCE),
            "source_surface_sha256":report["source_surface"]["sha256"],
            "fates_map_check":report["fates_map"],
            "new_surface":str(OUT),
            "new_surface_sha256":sha(tmp),
            "new_soil_fine_earth_pct":desired,
            "soil_layer_policy":"ASSUMED UNIFORM all 10 texture input layers; extrapolated beyond 0.55m site soil-depth reference; not depth-measured",
            "original_grid_ecological_values":"Not used as site science. All other unchanged NetCDF variables are technical inheritance and require model sanity checks.",
            "CIME_case_created":False,
            "slurm_submitted":False,
        }
        if OUT.exists() or RECEIPT.exists():
            stop("Output collision")
        os.link(tmp,OUT)
        try:
            with RECEIPT.open("x",encoding="utf8") as f:
                json.dump(receipt,f,indent=2,ensure_ascii=False)
                f.write("\n")
        except Exception:
            # Preserve candidate for forensic review rather than overwrite/delete.
            raise
        print("NEW VERSIONED CANDIDATE:",OUT)
        print("SHA256:",receipt["new_surface_sha256"])
        print("RECEIPT:",RECEIPT)
        print("NO CIME CASE, NO SLURM; NEW SURFACE IS NOT AN AD5 APPROVAL")
    finally:
        if tmp.exists():
            tmp.unlink()


def verify():
    if not OUT.is_file() or OUT.is_symlink() or not RECEIPT.is_file():
        stop("Versioned candidate NetCDF or receipt does not exist")
    r=json.loads(RECEIPT.read_text(encoding="utf8"))
    if r.get("new_surface")!=str(OUT) or sha(OUT)!=r.get("new_surface_sha256"):
        stop("Candidate NetCDF/receipt mismatch")
    audit_path=Path(r["stage10_audit"])
    report=checked_report(audit_path)
    validate_candidate(OUT,report)
    print("CZ-BK1 FIXNC CANDIDATE VERIFY PASS",OUT)
    print("NO MODEL CASE OR SLURM ACTION; SCIENCE DEPTH AND CIME PREFLIGHT REMAIN")


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--action",choices=("self-test","audit","build","verify"),default="audit")
    p.add_argument("--stage09",type=Path)
    p.add_argument("--audit-json",type=Path)
    p.add_argument("--ack-uniform-ten-layer-soil-proxy",default="")
    args=p.parse_args()
    if args.action=="self-test":
        assert 22+58+21==101 and abs(100*(22+58+21)/101-100)<1e-10
        assert len(YEARS)==22 and TIME_STEPS_EXPECTED==17520
        assert len(CHANGED)==5
        print("STAGE10 SELF-TEST PASS | CZ candidate and forcing metadata contracts")
        print("NO WRITES")
    elif args.action=="audit":
        if args.stage09 is None:
            p.error("--stage09 required")
        audit(args.stage09.expanduser().resolve())
    elif args.action=="build":
        build(args)
    else:
        verify()


if __name__=="__main__":
    main()
