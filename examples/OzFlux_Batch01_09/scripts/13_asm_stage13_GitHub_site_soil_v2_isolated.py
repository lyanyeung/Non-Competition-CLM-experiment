#!/usr/bin/env python3
"""OzFlux AU-ASM Stage13: source-pinned v1 GitHub soil SITE-SOIL v2 Surface.

Mandatory source is OzFlux_JapanFlux_Soil, branch oz-jp-soil-texture-20261103,
commit ba79a8cd86a0c20425f520754a6d221c64ed8fc5. Strong SHA checks:
the 10-layer WIDE and LONG tables and manual 0-100cm source policy are all
frozen as Git blob SHAs, together with the existing immutable Stage02 surface
SHA256. Use only that scientific choice, NEVER modify old surface/forcing.
Every variable except PCT_SAND and PCT_CLAY must stay value-identical.
The new result is a distinct EXPLORATORY candidate, not soil-science
certification or an authorisation to prepare/submit AD400.
"""
from __future__ import annotations
import argparse,csv,hashlib,json,shutil,sys
from pathlib import Path
import numpy as np
from netCDF4 import Dataset

HOME=Path.home()
SOURCE=HOME/"ozflux_nc_stage02_ASM_20261102T215809Z"/"surfdata_AU-ASM_NC_FIXNC_PFT_v1p1_CTSM2000_SOIL_REFERENCE.nc"
SOURCE_SHA="d06ad3111d93de69e7f2dd7f048b02a9161aee4ff853afafedcdfed71a54f3a1"
UPSTREAM_REPO="lyanyeung/CLM-FATES-single-site-workflows"
UPSTREAM_COMMIT="ba79a8cd86a0c20425f520754a6d221c64ed8fc5"
NAMES={
  "wide":("OZ_JP_RECOMMENDED_CLM10_SOIL_TEXTURE_WIDE_20261103.csv",
          "427f5eac76e5a49ded03859fd7238da927f064d1"),
  "long":("OZ_JP_RECOMMENDED_CLM10_SOIL_TEXTURE_LONG_20261103.csv",
          "d730b06c35fe11f5e2179d6e65dc6e8d64f26c8e"),
  "manual":("manual_depth_assignments_20261103.csv",
          "cf68ee4f6fb2ca0f7e5b2aa5c48c23d568660bf3"),
}
OUTPUT_NAME="surfdata_AU-ASM_NC_FIXNC_PFT_v1p1_SITE_SOIL_v2_20261103_INTERIM.nc"
ACK="BUILD_ISOLATED_AU_ASM_GITHUB_SITE_SOIL_V2_NO_MODEL"
EXPECTED_SAND=np.array([74.]*7+[70.6]*3,dtype=float)
EXPECTED_CLAY=np.array([15.]*7+[23.9]*3,dtype=float)
HOST={0:29.,5:65.,13:2.,14:4.}

def need(cond,msg):
    if not cond:raise ValueError(str(msg))

def regular(p):
    p=Path(p)
    need(p.is_file() and not p.is_symlink(),"Missing or symlink file "+str(p))
    return p

def sha256(p):
    h=hashlib.sha256()
    with regular(p).open("rb") as f:
        for part in iter(lambda:f.read(4<<20),b""):h.update(part)
    return h.hexdigest()

def gitblob(p):
    b=regular(p).read_bytes()
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()

def records(p):
    with regular(p).open(encoding="utf-8-sig",newline="") as f:
        return list(csv.DictReader(f))

def pinned_sources(directory):
    result={}
    for label,(filename,expected_sha) in NAMES.items():
        p=directory/filename
        got=gitblob(p)
        need(got==expected_sha,f"Upstream Git blob mismatch ({label}): {got}")
        result[label]={"path":str(p.resolve()),"git_blob_sha1":got}
    wide=[x for x in records(directory/NAMES["wide"][0]) if x["site"]=="AU-ASM"]
    need(len(wide)==1 and wide[0]["tier"]=="T1 site measured",
         "No unique AU-ASM T1 source-recommendation record")
    w=wide[0]
    sand=np.array([float(w[f"PCT_SAND_L{i}"]) for i in range(1,11)])
    clay=np.array([float(w[f"PCT_CLAY_L{i}"]) for i in range(1,11)])
    need(np.allclose(sand,EXPECTED_SAND,atol=1e-9,rtol=0) and
         np.allclose(clay,EXPECTED_CLAY,atol=1e-9,rtol=0),
         "AU-ASM GitHub v1 ten-layer numbers changed; review scientific revision")
    need(np.all((sand>=0)&(clay>=0)&(sand+clay<=100)),
         "Illegal sand+clay source proportions")
    long=[x for x in records(directory/NAMES["long"][0]) if x["site"]=="AU-ASM"]
    need(len(long)==10,"No 10 AU-ASM LONG provenance records")
    layers={int(r["layer"]):r for r in long}
    need(set(layers)==set(range(1,11)),"AU-ASM LONG layer identity")
    provenance=[]
    for j in range(1,11):
        x=layers[j]
        need(abs(float(x["PCT_SAND"])-sand[j-1])<1e-9 and
             abs(float(x["PCT_CLAY"])-clay[j-1])<1e-9,
             "WIDE/LONG source inconsistency layer "+str(j))
        want="LIT" if j<=7 else "SOILGRIDS"
        need(x["source"]==want,"Wrong GitHub source tier at layer "+str(j))
        need(x["how"]==("EXTENDED_BELOW_200cm" if j==10 else "COVERED"),
             "Unexpected GitHub layer extension classification "+str(j))
        provenance.append({"layer":j,"node_m":float(x["node_m"]),
                           "source_tier":x["source"],"how":x["how"]})
    manual=[x for x in records(directory/NAMES["manual"][0]) if
            x["site"]=="AU-ASM" and x["evidence_id"]=="AU-ASM-E01"]
    need(len(manual)==1 and float(manual[0]["applied_top_cm"])==0
         and float(manual[0]["applied_bottom_cm"])==100,
         "AU-ASM manual field texture 0-100 cm scope changed")
    return sand,clay,provenance,result,manual[0]["rationale"]

def frozen_surface():
    need(sha256(SOURCE)==SOURCE_SHA,"Old Stage02 FIXNC PFT source SHA changed")
    with Dataset(str(SOURCE),"r") as ds:
        v=ds.variables
        need(set(("PCT_SAND","PCT_CLAY","ORGANIC","PCT_NAT_PFT",
                  "PCT_NATVEG","PCT_CROP","LATIXY","LONGXY")).issubset(v),
             "Source surface missing expected CLM soil/land/PFT keys")
        ds.set_auto_maskandscale(False)
        p=np.array(v["PCT_NAT_PFT"][:]).reshape(-1)
        need(len(p) in (15,16),"Wrong PFT slot count")
        expected=np.zeros(len(p))
        for k,value in HOST.items():expected[k]=value
        need(np.allclose(p,expected,rtol=0,atol=1e-7),"PFT no longer v1.1")
        lat=float(np.array(v["LATIXY"][:]).reshape(-1)[0])
        lon=float(np.array(v["LONGXY"][:]).reshape(-1)[0])
        need(abs(lat+22.2828)<1e-6 and abs(lon-133.2493)<1e-6,
             "AU-ASM coordinates changed")
        for f in ("PCT_SAND","PCT_CLAY","ORGANIC"):
            a=np.asarray(v[f][:],dtype=float)
            need(a.size==10 and np.isfinite(a).all(),"Invalid original 10 layers "+f)
        return {f:np.asarray(v[f][:],dtype=float).reshape(-1).tolist()
                for f in ("PCT_SAND","PCT_CLAY","ORGANIC")} | {
                   "latitude":lat,"longitude":lon,
                   "natveg_pct":float(np.asarray(v["PCT_NATVEG"][:]).reshape(-1)[0]),
                   "crop_pct":float(np.asarray(v["PCT_CROP"][:]).reshape(-1)[0])}

def exact_var(original,candidate):
    a=np.asarray(original[:]);b=np.asarray(candidate[:])
    return a.dtype==b.dtype and a.shape==b.shape and a.tobytes()==b.tobytes()

def check_candidate(path,sand,clay):
    need(path.is_file() and not path.is_symlink(),"Missing independent candidate")
    unchanged=[]
    with Dataset(str(SOURCE),"r") as before,Dataset(str(path),"r") as after:
        before.set_auto_maskandscale(False)
        after.set_auto_maskandscale(False)
        need(set(before.dimensions)==set(after.dimensions),"Dimension keys changed")
        for key in before.dimensions:
            need(len(before.dimensions[key])==len(after.dimensions[key]),
                 "Dimension length changed "+key)
        need(set(before.variables)==set(after.variables),"Variable schema changed")
        need(set(before.ncattrs())==set(after.ncattrs()),"Global attrs changed")
        for k in before.ncattrs():
            need(str(before.getncattr(k))==str(after.getncattr(k)),
                 "Global attr mismatch "+k)
        changed=[]
        for name in before.variables:
            v,w=before.variables[name],after.variables[name]
            need(v.dimensions==w.dimensions and v.dtype==w.dtype,
                 "Variable definition drift "+name)
            need(set(v.ncattrs())==set(w.ncattrs()),"Variable attrs changed "+name)
            for attr in v.ncattrs():
                a=np.asarray(v.getncattr(attr));b=np.asarray(w.getncattr(attr))
                need(a.dtype==b.dtype and a.shape==b.shape and a.tobytes()==b.tobytes(),
                     "NetCDF var attribute drift "+name+"/"+attr)
            if name in ("PCT_SAND","PCT_CLAY"):
                target=sand if name=="PCT_SAND" else clay
                x=np.asarray(w[:],dtype=float).reshape(-1)
                need(len(x)==10 and np.allclose(x,target,atol=1e-5,rtol=0),
                     "Target layer profile mismatch "+name)
                changed.append(name)
            else:
                need(exact_var(v,w),"Other NetCDF data variable changed "+name)
                unchanged.append(name)
        need(set(changed)=={"PCT_SAND","PCT_CLAY"},"Not exactly two soil fields selected")
    return {"modified_variables":sorted(changed),
            "other_variables_byte_exact":len(unchanged),
            "PFT_and_landunit_unchanged":True,
            "original_reference_still_exists":True,
            "source_SHA256_still_equal":sha256(SOURCE)==SOURCE_SHA}

def self_test():
    need(np.array_equal(EXPECTED_SAND,np.array([74.]*7+[70.6]*3)),"Sand")
    need(np.array_equal(EXPECTED_CLAY,np.array([15.]*7+[23.9]*3)),"Clay")
    need(np.all(EXPECTED_SAND+EXPECTED_CLAY<=100),"Percentage")
    need(tuple(NAMES)==("wide","long","manual"),"Immutable source list")
    print("OZFLUX AU-ASM STAGE13 SELF-TEST PASS | 7 T1 proxy + 3 SoilGrids, isolated two-field variant; no Slurm")

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("action",choices=("self-test","plan","build","verify"))
    ap.add_argument("--evidence-dir",type=Path)
    ap.add_argument("--out",type=Path)
    ap.add_argument("--receipt",type=Path)
    ap.add_argument("--confirm",default="")
    a=ap.parse_args()
    if a.action=="self-test":return self_test()
    need(a.evidence_dir is not None,"Provide --evidence-dir with pinned GitHub CSVs")
    evidence=a.evidence_dir.resolve(strict=True)
    sand,clay,prof,pinned,manual=pinned_sources(evidence)
    old=frozen_surface()
    if a.action=="plan":
        print("UPSTREAM SOIL SCIENCE SOURCE",UPSTREAM_REPO,UPSTREAM_COMMIT)
        print("GITHUB WIDE/LONG/MANUAL GIT BLOBS VERIFIED")
        print("OLD SURFACE SHA VERIFIED",SOURCE_SHA)
        print("OLD SAND",old["PCT_SAND"],"OLD CLAY",old["PCT_CLAY"])
        print("NEW SAND",sand.tolist(),"NEW CLAY",clay.tolist())
        print("T1 SCOPE 0-100 cm is an inferred model-depth assumption, not measured 7 layers")
        print("L8-L10 SoilGrids; L10 extends profile below 200cm")
        print("HARDPAN ~1m not yet represented with zbedrock")
        print("GITHUB SITE SOIL V2 IS A CANDIDATE; NO MODEL CASE OR SLURM; FORCING SCIENCE HOLD")
        return
    if a.action=="verify":
        need(a.receipt is not None,"Provide --receipt manifest for verification")
        receipt=json.loads(regular(a.receipt).read_text())
        need(receipt.get("surface_source_sha256")==SOURCE_SHA and
             receipt.get("upstream_commit")==UPSTREAM_COMMIT and
             receipt.get("science_approved") is False and
             receipt.get("AD400_authorised") is False,
             "Candidate receipt provenance/science flags changed")
        p=Path(receipt["candidate_path"])
        need(sha256(p)==receipt["candidate_sha256"],
             "Candidate SHA changed after construction")
        proof=check_candidate(p,sand,clay)
        print("SITE-SOIL v2 INDEPENDENT VERIFY PASS",json.dumps(proof,sort_keys=True))
        print("FORCING SCIENCE HOLD; SOIL SITE DEPTH ASSUMPTION UNRELEASED; NO SLURM")
        return
    need(a.out is not None and a.confirm==ACK,
         "build needs --out and --confirm "+ACK)
    out=a.out
    need(not out.is_symlink() and not out.exists() and out.parent.resolve()==HOME.resolve(),
         "Output must be unused direct HOME directory")
    # Do all source, frozen 10-layer, depth and Git blob checks BEFORE mutation.
    out.mkdir(mode=0o700,parents=False,exist_ok=False)
    candidate=out/OUTPUT_NAME
    shutil.copyfile(SOURCE,candidate)
    with Dataset(str(candidate),"r+") as ds:
        ds.set_auto_maskandscale(False)
        for name,target in (("PCT_SAND",sand),("PCT_CLAY",clay)):
            v=ds.variables[name]
            need(v.size==10,"Texture target layer size "+name)
            v[:]=target.reshape(v.shape)
        ds.sync()
    proof=check_candidate(candidate,sand,clay)
    manifest={
      "experiment":"OzFlux_Batch01_09 AU-ASM FIXNC SITE-SOIL v2 (INTERIM)",
      "surface_source":str(SOURCE),
      "surface_source_sha256":SOURCE_SHA,
      "upstream_repo":UPSTREAM_REPO,"upstream_commit":UPSTREAM_COMMIT,
      "evidence_git_blobs":pinned,"source_of_layer_values":prof,
      "manual_depth_0_to_100_cm":manual,
      "site_texture_particle_size_scheme":"UNSTATED_AS_REPORTED",
      "zbedrock_hardpan_approx_1m_applied":False,
      "ORGANIC_changed":False,"PFT_landunit_changed":False,
      "source_soil_unchanged":True,
      "candidate_path":str(candidate),"candidate_sha256":sha256(candidate),
      "new_PCT_SAND":sand.tolist(),"new_PCT_CLAY":clay.tolist(),
      "proof":proof,
      "science_approved":False,"AD400_authorised":False,
      "soil_site_depth_assumption_pending":True,
      "forcing_science_hold":True,
      "case_created":False,"Slurm_submitted":False,
      "next":"review T1 0-100cm assumption and SLGA availability, time+wind AWS forcing QC, real CIME soil binding before direct AD400"
    }
    rec=out/"stage13_AU_ASM_v2_SITE_SOIL_candidate_NOT_MODEL_APPROVED.json"
    with rec.open("x",encoding="utf-8") as f:
        json.dump(manifest,f,indent=2,ensure_ascii=False)
    print("GITHUB SITE-SOIL v2 ISOLATED CANDIDATE BUILD PASS")
    print("ONLY PCT_SAND AND PCT_CLAY MODIFIED; ALL OTHER VARIABLES IDENTICAL",
          proof["other_variables_byte_exact"])
    print("CANDIDATE_SHA256",manifest["candidate_sha256"])
    print("CANDIDATE",candidate)
    print("RECEIPT",rec)
    print("SOIL SCIENCE HOLD; FORCING HOLD; NO AD400, NO SLURM")

if __name__=="__main__":main()
