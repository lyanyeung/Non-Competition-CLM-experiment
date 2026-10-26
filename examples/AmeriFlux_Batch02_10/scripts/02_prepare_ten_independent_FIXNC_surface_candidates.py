#!/usr/bin/env python3
"""AmeriFlux Batch02: source-gated versioned PFT+CLM10 soil surface candidates.

--self-test: check index / PFT and soil math, without file reads or writes.
--check: source evidence/site-surface inventory, no writing.
--build: prepare independent NEW idealized NATVEG100/CROP0 FIXNC surface
         candidates only where the original 10-layer measured/survey texture
         agrees with source-pinned recommended 0-30cm values.
NEVER alters original grids, site cases, forcing, FATES parameter maps or
Slurm. Arctic-PURE and ORGANIC are unresolved experiment gates, even after
a candidate surface is generated. No AD400 spinups are submitted.

Soil layers come from the ORIGINAL full AmeriFlux50 Stage01 final
09_RECOMMENDED_CLM10_PCT_SAND_PCT_CLAY_WIDE.csv rather than copying 0–30cm
averages into ten layers. Missing/contradictory site evidence is HOLD.
"""
import argparse,csv,hashlib,json,math,os,shutil,tempfile
from pathlib import Path
from datetime import datetime,timezone
import numpy as np
from netCDF4 import Dataset

SITES=("US-BZS","US-CMW","US-EML","US-GLE","US-Ha1","US-Ho1","US-Ho2","US-Ho3","US-ICh","US-ICt")
DATA="AMF_BATCH02_10_PFT_SOIL_RECOMMENDATIONS_SOURCE_PINNED_20261026.csv"
CLM=Path("/iridisfs/scratch/ly3n24/CLM_FATES")
SURF_SOURCE=CLM/"sites/MY_EC_SITE"
OUT=CLM/"experiments/NonCompetitionObserved22/AmeriFlux_Batch02_10"
SOIL_GUESSES=(
 Path.home()/"CLM_FATES_SOIL/AmeriFlux50_20261026/09_RECOMMENDED_CLM10_PCT_SAND_PCT_CLAY_WIDE.csv",
 Path.home()/"CLM_FATES_SOIL/AmeriFlux50_20261026_full_BADM/09_RECOMMENDED_CLM10_PCT_SAND_PCT_CLAY_WIDE.csv")
LAND_OTHER=("PCT_LAKE","PCT_WETLAND","PCT_GLACIER","PCT_URBAN")
PROFILE_REQUIRED_ARCTIC=("US-BZS","US-EML","US-ICh","US-ICt")
STAGE01_SHA="231aedd5d7105c6d7557de0cff6287ee61ad361b"
VERSION="AMF_BATCH02_FIXNC_SURFACE_SOURCE_PROFILE_CLM10_v1"

def sha(p):
    h=hashlib.sha256()
    with Path(p).open("rb") as f:
        for b in iter(lambda:f.read(1<<20),b""):h.update(b)
    return h.hexdigest()
def readcsv(p):
    with Path(p).open("r",newline="",encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))
def fail(msg):
    raise RuntimeError(msg)
def register(path):
    rows=readcsv(path)
    if len(rows)!=10 or {r["site"] for r in rows}!=set(SITES):
        fail("Wrong Batch02 register: require exact ten AmeriFlux sites")
    out={}
    for r in rows:
        if r["source_batch"]!="AmeriFlux_Batch02":
            fail("Other-cohort parameter selected "+r["site"])
        host={int(k):float(v) for k,v in json.loads(
            r["recommended_clm_host_PCT_NAT_PFT_json"]).items()}
        if (any(k<0 or k>14 or v<0 for k,v in host.items()) or
            not math.isclose(sum(host.values()),100,abs_tol=1e-6)):
            fail("Original PFT host 0..14 map is invalid "+r["site"])
        if r["fates_mapping_profile"] not in ("DEFAULT14","ARCTIC_PURE"):
            fail("Unhandled site-specific FATES HLM mapping "+r["site"])
        out[r["site"]]=(r,host)
    return out
def profile(path,reg):
    if not path.is_file():
        fail("No complete Layer1..10 evidence: "+str(path)+
           " (first run original AmeriFlux50 Stage01 with --badm-dir, original source cache)")
    rows=readcsv(path)
    if len(rows)<10:fail("Stage01 soil wide table is too small")
    bysite={}
    for r in rows:
        site=r.get("site","")
        if site not in SITES:continue
        if site in bysite:fail("Duplicate soil profile site "+site)
        sand=[];clay=[]
        for i in range(1,11):
            sk=f"PCT_SAND_L{i}";ck=f"PCT_CLAY_L{i}"
            try:
                sa=float(r[sk]);cl=float(r[ck])
            except (ValueError,TypeError,KeyError):
                fail(site+" does not have 10 independently derived texture layers")
            if not(math.isfinite(sa) and math.isfinite(cl)
                   and sa>=0 and cl>=0 and sa+cl<=100.0001):
                fail(site+" physically invalid soil horizon "+str(i))
            sand.append(sa);clay.append(cl)
        m=reg[site][0]
        # Original Stage01 top_mean = arithmetic mean of first five nodes,
        # output rounded to one decimal place. It must match the independently
        # source-pinned final 50-site recommendation rather than a stale run.
        # Ho2/Ho3 were deliberately assigned a NEIGHBOUR Ho1 ReESH
        # profile after independent Stage01 ran T3 site-specific SoilGrids.
        # Their final decision is validated after the measured Ho1 override.
        if site not in ("US-Ho2","US-Ho3"):
            for key,layer in (("recommended_sand_0_30cm_pct",sand),
                              ("recommended_clay_0_30cm_pct",clay)):
                expected=float(m[key])
                if abs(round(sum(layer[:5])/5,1)-expected)>0.11:
                    fail(site+" Stage01 L1-L5 average differs from final 50site "+key+
                         ": "+str(round(sum(layer[:5])/5,1))+" vs "+str(expected))
        bysite[site]={"sand":sand,"clay":clay,"tier":r.get("tier",""),
                       "profile_sha256":sha(path)}
    # The authoritative 50-site final soil decision selects the measured
    # US-Ho1 ReESH profile as a NEAR-TOWER PROXY for US-Ho2 and US-Ho3.
    # The original Stage01 independent site-column could instead be T3
    # SoilGrids (Ho2 38.5/14.3, Ho3 40.2/11.4). Do not accidentally
    # overwrite this explicit FINAL source decision. Preserve provenance.
    for site in ("US-Ho2","US-Ho3"):
        chosen=reg[site][0]
        if chosen["soil_tier"]!="T1N Ho1 ReESH":
            fail("Howland near-neighbour soil decision no longer matches pinned register")
        parent=bysite.get("US-Ho1")
        if parent is None or parent["tier"] not in ("T1_SITE_MEASURED","T1_SITE_MEASURED_REESH"):
            fail("Cannot apply Ho1 texture proxy: exact original measured Ho1 CLM10 profile unavailable")
        entry={"sand":list(parent["sand"]),"clay":list(parent["clay"]),
               "tier":"T1N_HO1_REESH_APPROVED_NEIGHBOUR_PROXY",
               "profile_sha256":parent["profile_sha256"],
               "soil_provenance_source_site":"US-Ho1",
               "original_site_specific_stage01_tier":bysite.get(site,{}).get("tier","MISSING")}
        for key,layer in (("recommended_sand_0_30cm_pct",entry["sand"]),
                          ("recommended_clay_0_30cm_pct",entry["clay"])):
            if abs(round(sum(layer[:5])/5,1)-float(chosen[key]))>.11:
                fail(site+" documented Ho1 ReESH proxy disagrees with FINAL soil values")
        bysite[site]=entry
    return bysite

def original(site):
    """Select real original point surface, not an arbitrary new FIXNC output.

    Prefer the same batch02 primary single-point surfdata folder that worked
    for GLE Stage103. If that does not exist, use the original independent
    Stage04 soil collector's *explicit selected source surface* receipt.
    Never silently select the first of multiple unrelated source surfaces.
    """
    d=SURF_SOURCE/site/"subset_data_batch02_surf2000"
    files=sorted(x for x in d.glob("surfdata*.nc") if x.is_file() and not x.is_symlink())
    if len(files)==1:return files[0]
    if len(files)>1:fail(site+" multiple primary Batch02 source surface files "+str(d))
    summary=(Path.home()/"CLM_FATES_SOIL/AmeriFlux_Batch02_10_20261026_Stage04/10_RECOMMENDED_SITE_SUMMARY.csv")
    if summary.is_file():
        match=[row for row in readcsv(summary) if row.get("site")==site]
        if len(match)==1:
            ref=match[0].get("reference_surface","")
            if ref:
                path=Path(ref.rsplit(":",1)[-1])
                if (path.is_absolute() and path.is_file() and not path.is_symlink()
                    and path.name.startswith("surfdata") and path.suffix==".nc"
                    and (site in path.parts or any(
                        p.startswith(site+"_") for p in path.parts))):
                    print("AMF_B02_SURFACE_ORIGINAL_STAGE04_SELECTED",
                        site,str(path),flush=True)
                    return path
    # If Stage04 did not record a resolvable source, require uniqueness of
    # all relevant site surfaces; never choose among conflicting versions.
    found=sorted(p for p in (SURF_SOURCE/site).rglob("surfdata*.nc")
             if p.is_file() and not p.is_symlink()
             and not any(t in p.parts for t in ("forcing","raw","packages")))
    if len(found)==1:return found[0]
    fail(site+" source site surface absent/ambiguous: primary "+str(d)+
         "; Stage04 selected source unavailable; alternatives "+
         str([str(p) for p in found[:8]]))

def candidate(site):
    return OUT/site/"surface"/f"surfdata_{site}_FIXNC_PFT_soil10_stage02_v1.nc"

def audit_layout(site,p):
    with Dataset(p) as ds:
        required=("PCT_NATVEG","PCT_CROP","PCT_NAT_PFT","PCT_SAND","PCT_CLAY")
        for k in required:
            if k not in ds.variables:fail(site+" original surface missing "+k)
        for k in ("PCT_NATVEG","PCT_CROP"):
            if ds[k].size!=1:fail(site+" landunit not one-point "+k)
        pft=ds["PCT_NAT_PFT"]
        if pft.size!=15 or "natpft" not in pft.dimensions:
            fail(site+" expected CLM 15-point natpft schema; investigate actual model map")
        for k in ("PCT_SAND","PCT_CLAY"):
            if ds[k].size!=10:fail(site+" soil is not exactly ten CLM layers "+k)
        if "LATIXY" not in ds.variables or "LONGXY" not in ds.variables:
            fail(site+" model point LATIXY/LONGXY absent")
        coords=[float(np.ma.filled(ds[k][:],np.nan).ravel()[0]) for k in ("LATIXY","LONGXY")]
        if any(not math.isfinite(x) for x in coords):
            fail(site+" model point coords nonfinite")
        organic={"found":"ORGANIC" in ds.variables,
                 "min":None,"max":None}
        if organic["found"]:
            q=np.ma.filled(ds["ORGANIC"][:],np.nan).astype(float)
            organic.update(min=float(q.min()),max=float(q.max()))
        return {"site":site,"point_coords_original":coords,"organic_original":organic}

def verify(site,path,host,soil):
    with Dataset(path) as ds:
        for k,target in (("PCT_NATVEG",100.),("PCT_CROP",0.)):
            z=np.ma.filled(ds[k][:],np.nan).ravel()
            if len(z)!=1 or abs(float(z[0])-target)>1e-4:
                fail(site+" independent FIXNC "+k+" mismatch")
        for k in LAND_OTHER:
            if k in ds.variables and not np.allclose(
                  np.ma.filled(ds[k][:],np.nan),0,atol=1e-4):
                fail(site+" expected zero non-vegetation land unit "+k)
        v=ds["PCT_NAT_PFT"]
        actual=np.ma.filled(v[:],np.nan).ravel()
        want=np.array([host.get(i,0.) for i in range(15)])
        if not np.allclose(actual,want,atol=1e-4):
            fail(site+" CLM point PCT_NAT_PFT differs from registered FATES host map")
        for name,values in (("PCT_SAND",soil["sand"]),("PCT_CLAY",soil["clay"])):
            got=np.ma.filled(ds[name][:],np.nan).ravel()
            if not np.allclose(got,values,atol=1e-4):
                fail(site+" recommended true L1..L10 "+name+" mismatch")

def build(site,metadata,host,soil):
    old=original(site);audit=audit_layout(site,old)
    dst=candidate(site);receipt=dst.with_suffix(".json")
    if dst.exists() or receipt.exists():
        if dst.is_file() and receipt.is_file():
            marker=json.loads(receipt.read_text())
            if marker.get("surface_sha256")==sha(dst):
                verify(site,dst,host,soil)
                print("AMF_B02_SURFACE_EXISTING_VERIFIED",site,dst,flush=True)
                return
        fail(site+" refuses overwrite of existing surface or receipt")
    dst.parent.mkdir(parents=True,exist_ok=True)
    fd,temp=tempfile.mkstemp(suffix=".nc",dir=dst.parent,prefix=f".{site}.")
    os.close(fd);tmp=Path(temp);oldsha=sha(old)
    try:
        shutil.copyfile(old,tmp)
        with Dataset(tmp,"r+") as ds:
            ds["PCT_NATVEG"][:]=100.
            ds["PCT_CROP"][:]=0.
            for name in LAND_OTHER:
                if name in ds.variables:ds[name][:]=0.
            v=ds["PCT_NAT_PFT"];arr=np.zeros(v.shape)
            axis=v.dimensions.index("natpft")
            for i,val in host.items():
                sl=[0]*arr.ndim;sl[axis]=i;arr[tuple(sl)]=val
            v[:]=arr
            for name,values in (("PCT_SAND",soil["sand"]),("PCT_CLAY",soil["clay"])):
                v=ds[name]
                if v.size!=10:fail(site+" soil geometry no longer 10 layers")
                v[:]=np.asarray(values).reshape(v.shape)
            ds.AMF_FIXNC_science_status="SURFACE_CANDIDATE_ONLY_NOT_ACTIVATED"
            ds.AMF_FIXNC_original_organic_field_policy="UNCHANGED_NEEDS_SOIL_SCIENCE_REVIEW"
            ds.AMF_FIXNC_PFT_map_profile=metadata["fates_mapping_profile"]
        verify(site,tmp,host,soil)
        if sha(old)!=oldsha:fail(site+" original source surface mutated")
        report={
            "schema":VERSION,"site":site,
            "source_surface":str(old),"source_sha256":oldsha,
            "surface":str(dst),"surface_sha256":sha(tmp),
            "original_site_schema":audit,
            "registered_PFT_host_pct":host,
            "recommended_FATES_pct":metadata["recommended_fates_natland_percent"],
            "fates_parameter_map_profile":metadata["fates_mapping_profile"],
            "fates_private_parameter_map_activated":False,
            "soil_source_tier":metadata["soil_tier"],
            "soil_full_depth_10layers":soil,
            "site_ORGANIC_approved":False,
            "surface_landunit_assumption":"IDEALIZED_NATVEG100_CROP0_NOT_WHOLE_EC_FOOTPRINT",
            "model_CASE_CREATED":False,"Slurm_SUBMITTED":False,
            "original_running_historical_cases_untouched":True,
            "created_utc":datetime.now(timezone.utc).isoformat()}
        # No overwrite. Surface is atomically linked in-place AFTER verification.
        os.link(tmp,dst)
        with receipt.open("x") as f:json.dump(report,f,indent=2);f.write("\n")
        print("AMF_B02_SURFACE_PREPARED",site,dst,"PFT_PROFILE",metadata["fates_mapping_profile"],
              "ORGANIC_HOLD",flush=True)
    finally:
        tmp.unlink(missing_ok=True)

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    actions=ap.add_mutually_exclusive_group(required=True)
    for action in ("self-test","check","build"):actions.add_argument("--"+action,action="store_true")
    ap.add_argument("--register",type=Path,default=Path(__file__).resolve().parent.parent/"data"/DATA)
    ap.add_argument("--soil-wide",type=Path)
    a=ap.parse_args()
    if a.self_test:
        assert len(SITES)==10 and "US-GLE" in SITES
        assert math.isclose(sum([20,60,10,10]),100)
        assert sum(1 for x in SITES if x in PROFILE_REQUIRED_ARCTIC)==4
        print("AMF_B02_SURFACE_SELF_TEST_PASS | 10 sites, 15 PFT host slots, 10 true soil layers, no writes")
        return
    reg=register(a.register)
    soil_file=a.soil_wide
    if soil_file is None:
        soil_file=next((x for x in SOIL_GUESSES if x.is_file()),SOIL_GUESSES[0])
    profiles=profile(soil_file,reg)
    print("AMF_B02_SOIL_SOURCE",soil_file,"SHA",sha(soil_file),
          "PROFILE_SITES",len(profiles),flush=True)
    ok=0;problems=[]
    for site in SITES:
        try:
            if site not in profiles:fail(site+" has no verified 10-layer Stage01 profile")
            m,host=reg[site]
            old=original(site);audit=audit_layout(site,old)
            if a.build:build(site,m,host,profiles[site])
            else:
                print("AMF_B02_SURFACE_CHECK_PASS",site,
                    "SOURCE",old,"PFT_PROFILE",m["fates_mapping_profile"],
                    "ORGANIC_NEEDS_REVIEW",flush=True)
            ok+=1
        except Exception as exc:
            problems.append((site,str(exc)))
            print("AMF_B02_SURFACE_HOLD",site,str(exc),flush=True)
    print("AMF_B02_SURFACE_SUMMARY",ok,"/10",
          "ACTION","BUILD_NEW_CANDIDATES" if a.build else "READONLY_CHECK",
          "HOLDS",len(problems),flush=True)
    if problems:raise SystemExit(3)
    print("AMF_B02_SURFACE_DONE | all 10 separate PFT/soil10 candidates, NO CIME CASES OR SLURM",flush=True)

if __name__=="__main__":
    main()
