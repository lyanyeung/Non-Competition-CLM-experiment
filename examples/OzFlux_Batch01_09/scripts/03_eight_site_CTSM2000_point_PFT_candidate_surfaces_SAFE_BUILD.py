#!/usr/bin/env python3
"""OzFlux FIXNC Stage03: remaining 8 CTSM2000 point PFT surfaces.

PREP: --preflight validates actual Stage01 PFT and Stage02 successful
original NetCDF coordinate/source receipts, source grid and CTSM
subset_data tool, without creating any files or invoking Slurm.
BUILD: --build --confirm CREATE_EIGHT_ISOLATED_OZFLUX_FIXNC_SURFACE_CANDIDATES
creates NEW CTSM2000 point references in a FRESH direct HOME folder,
then separate PFT v1.1 candidates. Only PCT_NAT_PFT in new copies is
modified; all other reference variables are checked exactly. No source
or pre-existing case changes. Site metadata coordinates are from
source L6 and have not been independently tower-site verified. Gridded
soil is reference, NOT validated site soil. No AD5/AD400 or CIME.
"""
from __future__ import annotations
import argparse,csv,hashlib,json,math,re,shutil,subprocess,sys
from collections import Counter
from pathlib import Path
import netCDF4
import numpy as np

HOME=Path.home()
CTSM_ROOT=Path("/iridisfs/scratch/ly3n24/CLM_FATES")
DATA=HOME/"ozflux_nc_stage01_code/pft"
STAGE01=HOME/"ozflux_nc_stage01_20261102T215107Z"/"ozflux09_operator_PFT_and_IRIDIS_readiness.json"
STAGE02_DIR=HOME/"ozflux_nc_stage02_ASM_20261102T215809Z"
STAGE02=STAGE02_DIR/"ozflux09_stage02_ASM_FIXNC_surface_candidate_science_HOLD.json"
STAGE02_TSV=STAGE02_DIR/"ozflux09_stage02_9site_reference_surface_and_coordinate_register.tsv"
ASM_PFT_SHA="d06ad3111d93de69e7f2dd7f048b02a9161aee4ff853afafedcdfed71a54f3a1"
ASM_REF_SHA="18edace32d8e356c7d73269329dca7ed6338140e1ad1456f1a88691522c307fa"
UPSTREAM="d62c814585c4aa85731f77b4a555efe6ec9e94a3"
HOST_BLOB="698d702e83265290e3cf1f1890235b67ede290ee"
REMAINING=("AU-Cow","AU-Cpr","AU-DaS","AU-Dry",
           "AU-Gin","AU-How","AU-Stp","AU-Tum")
# Values are exact repeated global+scalar metadata records from Stage02.
# Fail closed on any discrepancy; not independently published tower coords.
COORD={
 "AU-Cow":(-16.23819,145.42715),
 "AU-Cpr":(-34.0027,140.5877),
 "AU-DaS":(-14.1592,131.3881),
 "AU-Dry":(-15.2588,132.3706),
 "AU-Gin":(-31.376351,115.71377),
 "AU-How":(-12.4952,131.15005),
 "AU-Stp":(-17.1507,133.3502),
 "AU-Tum":(-35.6566,148.1516),
}
REF_SOURCE="surfdata_0.9x1.25_hist_2000_16pfts_c240908.nc"
MESH="fv0.9x1.25_141008_ESMFmesh.nc"
CONFIRM="CREATE_EIGHT_ISOLATED_OZFLUX_FIXNC_SURFACE_CANDIDATES"
TSV_FIELDS=("site","lat_from_original_L6","lon_from_original_L6",
 "reference_surface","reference_sha256","candidate_surface",
 "candidate_sha256","host_PCT_NAT_PFT_natland","host_bare0_percent",
 "reference_soil_layers","CTSM_reference_point_only","only_variable_changed",
 "tower_coordinates_independently_verified","tower_soil_science_approved",
 "DATM_science_approved","case_FATES_map_verified","AD5_authorised",
 "AD400_authorised")

def sha(p):
    h=hashlib.sha256()
    with p.open("rb") as fd:
        for block in iter(lambda:fd.read(1<<20),b""):h.update(block)
    return h.hexdigest()

def gitblob(p):
    b=p.read_bytes()
    h=hashlib.sha1()
    h.update(("blob "+str(len(b))+"\0").encode()+b)
    return h.hexdigest()

def regular(p):
    if not p.is_file() or p.is_symlink():raise ValueError("Missing/symlink source "+str(p))
    return p

def load_csv(p,delimiter=","):
    with regular(p).open("r",encoding="utf-8-sig",newline="") as f:
        rd=csv.DictReader(f,delimiter=delimiter)
        rows=list(rd)
    if any(None in row for row in rows):raise ValueError("CSV row width mismatch "+str(p))
    return rows

def config_text(raw):
    """Change [surfdat] only; do not alter an unrelated [landuse] dir."""
    headers=list(re.finditer(
       r"(?m)^[ \t]*\[surfdat\][ \t]*(?:[;#][^\r\n]*)?$",raw))
    if len(headers)!=1:raise ValueError("CTSM source has not exactly one [surfdat]")
    start=headers[0].end()
    nxt=re.search(r"(?m)^[ \t]*\[[A-Za-z0-9_-]+\][ \t]*(?:[;#][^\r\n]*)?$",raw[start:])
    end=start+nxt.start() if nxt else len(raw)
    sec=raw[start:end]
    for key,val in (("dir","lnd/clm2/surfdata_esmf/ctsm5.3.0"),
                    ("surfdat_16pft",REF_SOURCE),("mesh_surf",MESH)):
        pat=re.compile(r"(?m)^([ \t]*"+re.escape(key)+r"[ \t]*=[ \t]*)[^\r\n]*\r?$")
        sec,n=pat.subn(lambda m:m.group(1)+val,sec)
        if n!=1:raise ValueError("CTSM config surfdat missing/duplicate "+key)
    return raw[:start]+sec+raw[end:]

def input_gate():
    a=json.loads(regular(STAGE01).read_text(encoding="utf-8"))
    b=json.loads(regular(STAGE02).read_text(encoding="utf-8"))
    if (a.get("source_commit")!=UPSTREAM or len(a.get("operator_accepted_PRIMARY_PFT_9_sites",[]))!=9
        or a.get("AD400_authorised") is not False):
        raise ValueError("Stage01 actual successful PFT receipt missing/changed")
    s=b.get("new_AU_ASM_isolated_surface") or {}
    if (b.get("mode")!="BUILD_ISOLATED_AU_ASM_FIXNC_PFT_CANDIDATE"
        or s.get("candidate_sha256")!=ASM_PFT_SHA
        or s.get("original_reference_surface_SHA256")!=ASM_REF_SHA
        or s.get("gridded_soil_and_all_other_variables_bitwise_values_preserved") is not True
        or b.get("AD5_authorised") is not False
        or b.get("AD400_authorised") is not False):
        raise ValueError("Stage02 exact operator AU-ASM candidate receipt mismatch")
    if sha(regular(Path(s["candidate_path"])))!=ASM_PFT_SHA:
        raise ValueError("Stage02 AU-ASM candidate bytes changed")
    matrix=DATA/"OZFLUX_09_PRIMARY_CLM_PCT_NAT_PFT_20261102.csv"
    if gitblob(regular(matrix))!=HOST_BLOB:
        raise ValueError("Operator selected nine-site host PFT blob drift")
    src=load_csv(matrix)
    if len(src)!=9 or Counter(x["site"] for x in src)!=Counter((*REMAINING,"AU-ASM")):
        raise ValueError("PFT site IDs duplicated/missing")
    pft={r["site"]:r for r in src}
    coords=load_csv(STAGE02_TSV,"\t")
    if len(coords)!=9 or Counter(x["site"] for x in coords)!=Counter((*REMAINING,"AU-ASM")):
        raise ValueError("Stage02 coordinate register missing sites")
    coord={r["site"]:r for r in coords}
    for site,(lat,lon) in COORD.items():
        r=coord[site]
        if r["lat_lon_metadata_consistent"]!="True" or r["raw_L6_present"]!="1":
            raise ValueError("Missing/inconsistent original source coordinate "+site)
        a=json.loads(r["latitude_candidates_json"])
        b=json.loads(r["longitude_candidates_json"])
        if (len(a["candidates"])<2 or len(b["candidates"])<2
            or not any("global:" in x["from"] for x in a["candidates"])
            or not any("variable:" in x["from"] for x in a["candidates"])
            or not any("global:" in x["from"] for x in b["candidates"])
            or not any("variable:" in x["from"] for x in b["candidates"])):
            raise ValueError("Need source L6 global + variable independent field metadata "+site)
        for v in a["candidates"]:
            if abs(float(v["value"])-lat)>1e-5:
                raise ValueError("Source L6 latitude changed "+site)
        for v in b["candidates"]:
            if abs(float(v["value"])-lon)>1e-5:
                raise ValueError("Source L6 longitude changed "+site)
        if abs(float(a["coordinate"])-lat)>1e-5 or abs(float(b["coordinate"])-lon)>1e-5:
            raise ValueError("Stage02 source coordinate mismatch "+site)
        values=[float(pft[site][f"PCT_NAT_PFT_{i}"]) for i in range(15)]
        if (any(not math.isfinite(v) or v<0 or v>100 for v in values)
            or abs(sum(values)-100)>0.00005):
            raise ValueError("Invalid PFT vector "+site)
    return pft,{"Stage01_report_SHA256":sha(STAGE01),
                "Stage02_report_SHA256":sha(STAGE02),
                "Stage02_coordinate_register_SHA256":sha(STAGE02_TSV),
                "PFT_blob":gitblob(matrix),"upstream":UPSTREAM}

def ctsm_gate():
    base=CTSM_ROOT
    tool=regular(base/"CTSM/tools/site_and_regional/subset_data")
    template=regular(base/"CTSM/tools/site_and_regional/default_data_2000.cfg")
    grid=regular(base/"inputdata/lnd/clm2/surfdata_esmf/ctsm5.3.0"/REF_SOURCE)
    mesh=regular(base/"inputdata/share/meshes"/MESH)
    if not __import__("os").access(tool,__import__("os").X_OK):
        raise ValueError("CTSM subset_data not executable")
    cfg=config_text(template.read_text(encoding="utf-8"))
    # bounded help inspection, never builds files.
    run=subprocess.run([sys.executable,"-B",str(tool),"point","--help"],
                       cwd=base/"CTSM",capture_output=True,text=True,timeout=120)
    if run.returncode!=0 or any(x not in run.stdout for x in (
        "--lat","--lon","--site","--surf-year","--create-surface",
        "--inputdata-dir","--cfg-file","--outdir")):
        raise ValueError("CTSM subset_data command options unavailable "+run.stderr[-500:])
    return {"subset_data_SHA256":sha(tool),"template_SHA256":sha(template),
            "gridded_reference_SHA256":sha(grid),"mesh_SHA256":sha(mesh),
            "cfg_SHA256":hashlib.sha256(cfg.encode()).hexdigest()},cfg,tool

def point_values(path,lat,lon):
    with netCDF4.Dataset(str(path),"r") as ds:
        for key in ("LATIXY","LONGXY","PCT_NAT_PFT","PCT_SAND",
                    "PCT_CLAY","ORGANIC"):
            if key not in ds.variables:raise ValueError("Point surface missing "+key)
        xy=lambda name:np.ma.asarray(ds.variables[name][:]).filled(np.nan).ravel().astype(float)
        la=xy("LATIXY");lo=xy("LONGXY")
        if la.size!=1 or lo.size!=1 or abs(float(la[0])-lat)>0.05 or abs((float(lo[0])-lon+180)%360-180)>0.05:
            raise ValueError("Subset surface does not match tower L6 coords")
        v=xy("PCT_NAT_PFT")
        if v.size not in (15,16) or not np.isfinite(v).all() or abs(v.sum()-100)>0.1:
            raise ValueError("Source reference PFT schema invalid")
        sands=xy("PCT_SAND");clays=xy("PCT_CLAY");organics=xy("ORGANIC")
        if not (len(sands)==len(clays)==len(organics)==10 and
            np.isfinite(sands).all() and np.isfinite(clays).all() and
            np.isfinite(organics).all() and np.all(sands>=0) and
            np.all(clays>=0) and np.all(sands+clays<=100.001)):
            raise ValueError("Reference soil 10 layer geometry/values invalid")
        return {"PFT_slots":int(v.size),
                "soil_layers":int(len(sands)),
                "ref_lat":float(la[0]),"ref_lon":float(lo[0])}

def validate_copy(source,target,host):
    with netCDF4.Dataset(str(source),"r") as before, netCDF4.Dataset(str(target),"r") as after:
        if set(before.variables)!=set(after.variables):
            raise ValueError("CTSM source vs PFT-copy variable list differs")
        for name in before.variables:
            a=np.ma.array(before.variables[name][:])
            b=np.ma.array(after.variables[name][:])
            if a.shape!=b.shape:raise ValueError("Variable shape changed "+name)
            if name=="PCT_NAT_PFT":
                wanted=np.array(host+([0.0] if b.size==16 else []))
                if not np.allclose(np.ma.filled(b,np.nan).ravel(),wanted,atol=2.5e-5,rtol=0):
                    raise ValueError("Candidate PFT mismatch")
            elif not np.ma.allequal(a,b):
                raise ValueError("Non-PFT reference source variable was changed "+name)
        for k in ("PCT_SAND","PCT_CLAY","ORGANIC"):
            if not np.ma.allequal(
                  np.ma.array(before.variables[k][:]),
                  np.ma.array(after.variables[k][:])):
                raise ValueError("Reference soil changed "+k)
    return True

def build_one(site,host,latlon,out,cfg,tool):
    lat,lon=latlon
    site_dir=out/site
    site_dir.mkdir(mode=0o700,exist_ok=False)
    ref_dir=site_dir/"CTSM2000_REFERENCE"
    ref_dir.mkdir(mode=0o700,exist_ok=False)
    config=site_dir/"CTSM2000_source_data.cfg"
    config.write_text(cfg,encoding="utf-8")
    cmd=[sys.executable,"-B",str(tool),"point",
         "--lat",str(lat),"--lon",str(lon),"--lon-type","180",
         "--site",site,"--surf-year","2000","--create-surface",
         "--create-user-mods","--inputdata-dir",str(CTSM_ROOT/"inputdata"),
         "--cfg-file",str(config),"--outdir",str(ref_dir)]
    print("STAGE03 BUILD REFERENCE",site,"coords",lat,lon,flush=True)
    subprocess.run(cmd,cwd=CTSM_ROOT/"CTSM",stdin=subprocess.DEVNULL,
                   timeout=1800,check=True)
    refs=sorted(p for p in ref_dir.glob("surfdata*.nc") if p.is_file() and not p.is_symlink())
    if len(refs)!=1:raise ValueError("Expected one generated point surface for "+site)
    detail=point_values(refs[0],lat,lon)
    candidate=site_dir/("surfdata_"+site+"_NC_FIXNC_PFT_v1p1_CTSM2000_SOIL_REFERENCE.nc")
    if candidate.exists():raise ValueError("New candidate already exists")
    shutil.copyfile(refs[0],candidate)
    with netCDF4.Dataset(str(candidate),"r+") as ds:
        v=ds.variables["PCT_NAT_PFT"]
        n=int(np.prod(v.shape))
        if n not in (15,16):raise ValueError("PFT count drift in copied surface")
        wanted=np.array(host+([0.0] if n==16 else []),dtype=float).reshape(v.shape)
        v[:]=wanted
        ds.setncattr("ozflux_nc_source_commit",UPSTREAM)
        ds.setncattr("ozflux_nc_model_source","operator-v1.1 DEFAULT14 natland incl bare host0")
        ds.setncattr("ozflux_nc_soil_status","CTSM2000 GRID REFERENCE ONLY; not site approved")
        ds.setncattr("ozflux_nc_surface_status","FIXNC PFT candidate ONLY; no AD5 AD400 authorisation")
        ds.setncattr("ozflux_nc_source_reference_sha256",sha(refs[0]))
        ds.setncattr("ozflux_nc_coordinates","Original site L6 metadata; external site verification pending")
    validate_copy(refs[0],candidate,host)
    return {"site":site,"lat_from_original_L6":lat,"lon_from_original_L6":lon,
      "reference_surface":str(refs[0]),"reference_sha256":sha(refs[0]),
      "candidate_surface":str(candidate),"candidate_sha256":sha(candidate),
      "host_PCT_NAT_PFT_natland":json.dumps(host),
      "host_bare0_percent":host[0],"reference_soil_layers":detail["soil_layers"],
      "CTSM_reference_point_only":True,"only_variable_changed":"PCT_NAT_PFT",
      "tower_coordinates_independently_verified":False,
      "tower_soil_science_approved":False,"DATM_science_approved":False,
      "case_FATES_map_verified":False,"AD5_authorised":False,
      "AD400_authorised":False}

def self_test():
    assert len(REMAINING)==8 and len(COORD)==8
    assert COORD["AU-Cow"]==(-16.23819,145.42715)
    cfg="[surfdat]\ndir = old\nsurfdat_16pft = old.nc\nmesh_surf = oldmesh\n\n[landuse]\ndir = retain\n"
    x=config_text(cfg)
    assert "ctsm5.3.0" in x and "[landuse]\ndir = retain" in x
    assert config_text(x)==x
    assert sum((29,0,0,0,0,65,0,0,0,0,0,0,0,2,4))==100
    print("OZFLUX NC STAGE03 SELF-TEST PASS: CTSM2000 scoped cfg, 8 metadata sites, PFT/bare, no input writes")

def main():
    if sys.argv[1:]==["--self-test"]:return self_test()
    ap=argparse.ArgumentParser(description=__doc__)
    grp=ap.add_mutually_exclusive_group(required=True)
    grp.add_argument("--preflight",action="store_true")
    grp.add_argument("--build",action="store_true")
    ap.add_argument("--confirm")
    ap.add_argument("--out",type=Path,required=True)
    args=ap.parse_args()
    out=args.out.resolve()
    if (args.out.is_symlink() or out.exists() or out.parent!=HOME.resolve()
        or CTSM_ROOT.resolve()==out or CTSM_ROOT.resolve() in out.parents):
        raise ValueError("New direct HOME output folder required")
    pft,source=input_gate()
    ctsm,cfg,tool=ctsm_gate()
    print("STAGE03 SOURCE 9 PFT/8 COORD, Stage02 ASM surface AND CTSM TOOL verified")
    for site in REMAINING:
        host=[float(pft[site][f"PCT_NAT_PFT_{i}"]) for i in range(15)]
        print("SITE",site,"L6_COORD",COORD[site],
              "HOST_NAT_PFT",json.dumps({i:v for i,v in enumerate(host) if v}),
              "BARE",host[0], "SOIL GRID REFERENCE ONLY")
    if args.preflight:
        print("STAGE03 PREFLIGHT PASS; no directory or surface created")
        print("AD5/AD400 HOLD")
        return
    if args.confirm!=CONFIRM:
        raise ValueError("Missing exact explicit build confirmation")
    out.mkdir(mode=0o700,exist_ok=False,parents=False)
    completed=[]
    try:
        for site in REMAINING:
            host=[float(pft[site][f"PCT_NAT_PFT_{i}"]) for i in range(15)]
            rec=build_one(site,host,COORD[site],out,cfg,tool)
            completed.append(rec)
            print("STAGE03 SITE_SURFACE_CREATED",site,"SHA256",rec["candidate_sha256"],flush=True)
    finally:
        # Preserve partial completed outputs if a site tool fails.
        status={"stage":"OzFlux noncompetition Stage03 eight isolated CTSM2000 reference+PFT surfaces",
         "operator_PFT_snapshot_SHA":source,"CTSM_grid_and_tools_SHA":ctsm,
         "completed_sites":completed,"target_sites":list(REMAINING),
         "all_eight_candidates_complete":len(completed)==8,
         "source_L6_coordinates_not_independently_site_verified":True,
         "gridded_reference_soil_not_site_measured":True,
         "site_meteorological_DATM_not_approved":True,
         "active_case_FATES_map_not_checked":True,
         "old_AU_How_competition_case_unchanged":True,
         "AD5_submitted":False,"AD400_submitted":False}
        (out/"ozflux09_stage03_eight_candidate_surface_source_gate.json").write_text(
         json.dumps(status,indent=2,ensure_ascii=False),encoding="utf-8")
        with (out/"ozflux09_stage03_eight_FIXNC_surface_inventory.tsv").open(
           "w",encoding="utf-8",newline="") as f:
            w=csv.DictWriter(f,fieldnames=TSV_FIELDS,delimiter="\t",extrasaction="raise")
            w.writeheader();w.writerows(completed)
    print("STAGE03 ALL EIGHT FIXNC PFT SURFACE CANDIDATES CREATED; NO CIME/SLURM")
    print("SCIENCE HOLD: GRID SOIL / DATM / EFFECTIVE CASE MAP / 2018 AGB")
    print("REPORT_DIR",out)

if __name__=="__main__":main()
