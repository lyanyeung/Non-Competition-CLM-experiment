#!/usr/bin/env python3
"""OzFlux AU-ASM Stage22: source-pinned zbedrock (siliceous hardpan) on the verified Stage13 SITE-SOIL v2 Surface.

Operator decision 2026-11-03: use_bedrock = .true. for the OzFlux / JapanFlux sites, AU-ASM first. Upstream
science choice is OzFlux_JapanFlux_SurfaceFields, branch oz-jp-surface-carbon-20261103, commit
b10377c624e7fbd4712be29ce04d99c4858cc676: AU-ASM zbedrock = 1.0 m, the siliceous hardpan at ~1 m with roots above
it and a perched reservoir. With CTSM d5ea9d01 and 20SL_8.5m that is bedrock layer 9, so the column bottom is
1.20 m. ORGANIC stays f09 for AU-ASM.

Source is the Stage13 v2 candidate, SHA256 pinned. Every variable except zbedrock must stay byte-identical. The
new file is a distinct EXPLORATORY candidate, not science approval or an authorisation to prepare/submit AD400.

zbedrock acts only with use_bedrock = .true. (the FATES default is .false.). Any later AD400 / NORMAL400 /
observation-run controller binding this Surface must set it in user_nl_clm and verify lnd_in.
"""
from __future__ import annotations
import argparse,csv,hashlib,json,shutil,sys
from pathlib import Path
import numpy as np
from netCDF4 import Dataset

HOME=Path.home()
SOURCE=HOME/"ozflux_nc_stage13_soil_20261103T130125Z"/"surfdata_AU-ASM_NC_FIXNC_PFT_v1p1_SITE_SOIL_v2_20261103_INTERIM.nc"
SOURCE_SHA="2c3de9a54b11189ab4d6413eb29fe91fe36b6ec0f87b9a3ae999d6a7a3a7e8a1"
SOURCE_RECEIPT=SOURCE.parent/"stage13_AU_ASM_v2_SITE_SOIL_candidate_NOT_MODEL_APPROVED.json"
UPSTREAM_REPO="lyanyeung/CLM-FATES-single-site-workflows"
UPSTREAM_COMMIT="b10377c624e7fbd4712be29ce04d99c4858cc676"
NAMES={"surface_fields":("OZ_JP_RECOMMENDED_SURFACE_FIELDS_20_SITES_20261103.csv",
                         "abb142ab5ab8adb82ed53df220e38bf29ee12af0")}
OUTPUT_NAME="surfdata_AU-ASM_NC_FIXNC_PFT_v1p1_SITE_SOIL_v2_BEDROCK_v3_20261103_INTERIM.nc"
ACK="BUILD_ISOLATED_AU_ASM_BEDROCK_V3_NO_MODEL"
ZBEDROCK=1.0
SOURCE_ZBEDROCK=31.043          # f09 value inherited by Stage02 and Stage13 (Stage01 surface inventory)
NBEDROCK=9                      # CTSM initVerticalMod with 20SL_8.5m: layer 9 spans 0.92-1.20 m
COLUMN_BOTTOM_M=1.20

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

def pinned_sources(directory):
    filename,expected=NAMES["surface_fields"]
    p=directory/filename
    got=gitblob(p)
    need(got==expected,f"Upstream Git blob mismatch (surface_fields): {got}")
    with regular(p).open(encoding="utf-8-sig",newline="") as f:
        rows=[x for x in csv.DictReader(f) if x["site"]=="AU-ASM"]
    need(len(rows)==1,"No unique AU-ASM surface-field recommendation")
    r=rows[0]
    need(r["zbedrock_class"]=="RESTRICT" and float(r["zbedrock_recommended_m"])==ZBEDROCK,
         "AU-ASM zbedrock recommendation changed; review scientific revision")
    need(int(r["use_bedrock_on_nbedrock"])==NBEDROCK and float(r["use_bedrock_on_soil_bottom_m"])==COLUMN_BOTTOM_M,
         "AU-ASM CLM bedrock layer mapping changed")
    need(r["organic_rule"]=="F09","AU-ASM ORGANIC rule changed; this stage edits zbedrock only")
    return {"path":str(p.resolve()),"git_blob_sha1":got,"zbedrock_basis":r["zbedrock_basis"],
            "zbedrock_tier":r["zbedrock_tier"]}

def frozen_surface(source=SOURCE,source_sha=SOURCE_SHA,receipt=SOURCE_RECEIPT):
    need(sha256(source)==source_sha,"Stage13 v2 source SHA changed")
    if receipt is not None:
        rec=json.loads(regular(receipt).read_text())
        need(rec.get("candidate_sha256")==source_sha and rec.get("zbedrock_hardpan_approx_1m_applied") is False,
             "Stage13 receipt does not match the pinned v2 source")
    with Dataset(str(source),"r") as ds:
        ds.set_auto_maskandscale(False)
        need("zbedrock" in ds.variables,"Source surface has no zbedrock")
        z=np.asarray(ds.variables["zbedrock"][:],dtype=float)
        need(z.size==1 and abs(float(z.reshape(-1)[0])-SOURCE_ZBEDROCK)<1e-3,
             "Source zbedrock is not the inherited f09 value "+str(z.reshape(-1).tolist()))
        lat=float(np.array(ds.variables["LATIXY"][:]).reshape(-1)[0])
        lon=float(np.array(ds.variables["LONGXY"][:]).reshape(-1)[0])
        need(abs(lat+22.2828)<1e-6 and abs(lon-133.2493)<1e-6,"AU-ASM coordinates changed")
        return {"zbedrock":float(z.reshape(-1)[0]),"latitude":lat,"longitude":lon}

def exact_var(original,candidate):
    a=np.asarray(original[:]);b=np.asarray(candidate[:])
    return a.dtype==b.dtype and a.shape==b.shape and a.tobytes()==b.tobytes()

def check_candidate(path,source=SOURCE,source_sha=SOURCE_SHA):
    need(path.is_file() and not path.is_symlink(),"Missing independent candidate")
    unchanged=[]
    with Dataset(str(source),"r") as before,Dataset(str(path),"r") as after:
        before.set_auto_maskandscale(False)
        after.set_auto_maskandscale(False)
        need(set(before.dimensions)==set(after.dimensions),"Dimension keys changed")
        for key in before.dimensions:
            need(len(before.dimensions[key])==len(after.dimensions[key]),"Dimension length changed "+key)
        need(set(before.variables)==set(after.variables),"Variable schema changed")
        need(set(before.ncattrs())==set(after.ncattrs()),"Global attrs changed")
        for k in before.ncattrs():
            need(str(before.getncattr(k))==str(after.getncattr(k)),"Global attr mismatch "+k)
        changed=[]
        for name in before.variables:
            v,w=before.variables[name],after.variables[name]
            need(v.dimensions==w.dimensions and v.dtype==w.dtype,"Variable definition drift "+name)
            need(set(v.ncattrs())==set(w.ncattrs()),"Variable attrs changed "+name)
            for attr in v.ncattrs():
                a=np.asarray(v.getncattr(attr));b=np.asarray(w.getncattr(attr))
                need(a.dtype==b.dtype and a.shape==b.shape and a.tobytes()==b.tobytes(),
                     "NetCDF var attribute drift "+name+"/"+attr)
            if name=="zbedrock":
                x=np.asarray(w[:],dtype=float).reshape(-1)
                need(len(x)==1 and abs(x[0]-ZBEDROCK)<1e-9,"Target zbedrock mismatch")
                changed.append(name)
            else:
                need(exact_var(v,w),"Other NetCDF data variable changed "+name)
                unchanged.append(name)
        need(changed==["zbedrock"],"Not exactly zbedrock selected")
    return {"modified_variables":changed,"other_variables_byte_exact":len(unchanged),
            "soil_texture_PFT_landunit_ORGANIC_unchanged":True,
            "source_SHA256_still_equal":sha256(source)==source_sha}

def build_candidate(source,candidate):
    shutil.copyfile(source,candidate)
    with Dataset(str(candidate),"r+") as ds:
        ds.set_auto_maskandscale(False)
        v=ds.variables["zbedrock"]
        need(v.size==1,"zbedrock target size")
        v[:]=np.full(v.shape,ZBEDROCK,dtype=v.dtype)
        ds.sync()

def self_test():
    import tempfile
    need(ZBEDROCK>0.32,"zbedrock <= 0.32 m would silently give the full column in CTSM")
    need(tuple(NAMES)==("surface_fields",),"Immutable source list")
    with tempfile.TemporaryDirectory() as d:
        d=Path(d);src=d/"v2.nc";cand=d/"v3.nc"
        with Dataset(str(src),"w") as ds:
            ds.createDimension("lsmlat",1);ds.createDimension("lsmlon",1);ds.createDimension("nlevsoi",10)
            ds.title="t"
            ds.createVariable("LATIXY","f8",("lsmlat","lsmlon"))[:]=-22.2828
            ds.createVariable("LONGXY","f8",("lsmlat","lsmlon"))[:]=133.2493
            z=ds.createVariable("zbedrock","f8",("lsmlat","lsmlon"));z.units="m";z[:]=SOURCE_ZBEDROCK
            ds.createVariable("PCT_SAND","f8",("nlevsoi","lsmlat","lsmlon"))[:]=np.full((10,1,1),74.)
        sha=sha256(src)
        old=frozen_surface(src,sha,None)
        need(abs(old["zbedrock"]-SOURCE_ZBEDROCK)<1e-9,"self-test source read")
        build_candidate(src,cand)
        proof=check_candidate(cand,src,sha)
        need(proof["modified_variables"]==["zbedrock"] and proof["other_variables_byte_exact"]==3,"self-test proof")
        with Dataset(str(cand),"r+") as ds:ds.variables["PCT_SAND"][0,0,0]=75.
        try:
            check_candidate(cand,src,sha);need(False,"drift not detected")
        except ValueError as e:
            need("PCT_SAND" in str(e),"wrong drift report")
    print("OZFLUX AU-ASM STAGE22 SELF-TEST PASS | zbedrock-only isolated variant, byte-exact other fields; no Slurm")

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("action",choices=("self-test","plan","build","verify"))
    ap.add_argument("--evidence-dir",type=Path)
    ap.add_argument("--out",type=Path)
    ap.add_argument("--receipt",type=Path)
    ap.add_argument("--confirm",default="")
    a=ap.parse_args()
    if a.action=="self-test":return self_test()
    need(a.evidence_dir is not None,"Provide --evidence-dir with the pinned GitHub surface-field CSV")
    pinned=pinned_sources(a.evidence_dir.resolve(strict=True))
    old=frozen_surface()
    if a.action=="plan":
        print("UPSTREAM SURFACE-FIELD SOURCE",UPSTREAM_REPO,UPSTREAM_COMMIT)
        print("GITHUB SURFACE-FIELD GIT BLOB VERIFIED",pinned["git_blob_sha1"])
        print("STAGE13 v2 SOURCE SHA AND RECEIPT VERIFIED",SOURCE_SHA)
        print("OLD zbedrock",old["zbedrock"],"m (f09, Pelletier soil thickness) -> NEW",ZBEDROCK,"m")
        print("BASIS",pinned["zbedrock_basis"])
        print("CLM 20SL_8.5m: nbedrock",NBEDROCK,"column bottom",COLUMN_BOTTOM_M,"m (only with use_bedrock = .true.)")
        print("ONLY zbedrock CHANGES; texture v2, PFT, landunits, ORGANIC unchanged")
        print("CANDIDATE ONLY; NO MODEL CASE OR SLURM; FORCING SCIENCE HOLD")
        return
    if a.action=="verify":
        need(a.receipt is not None,"Provide --receipt manifest for verification")
        receipt=json.loads(regular(a.receipt).read_text())
        need(receipt.get("surface_source_sha256")==SOURCE_SHA and receipt.get("upstream_commit")==UPSTREAM_COMMIT and
             receipt.get("science_approved") is False and receipt.get("AD400_authorised") is False and
             receipt.get("use_bedrock_required") is True,
             "Candidate receipt provenance/science flags changed")
        p=Path(receipt["candidate_path"])
        need(sha256(p)==receipt["candidate_sha256"],"Candidate SHA changed after construction")
        proof=check_candidate(p)
        print("BEDROCK v3 INDEPENDENT VERIFY PASS",json.dumps(proof,sort_keys=True))
        print("REQUIRES use_bedrock = .true. IN ANY CASE BINDING IT; FORCING SCIENCE HOLD; NO SLURM")
        return
    need(a.out is not None and a.confirm==ACK,"build needs --out and --confirm "+ACK)
    out=a.out
    need(not out.is_symlink() and not out.exists() and out.parent.resolve()==HOME.resolve(),
         "Output must be unused direct HOME directory")
    out.mkdir(mode=0o700,parents=False,exist_ok=False)
    candidate=out/OUTPUT_NAME
    build_candidate(SOURCE,candidate)
    proof=check_candidate(candidate)
    manifest={
      "experiment":"OzFlux_Batch01_09 AU-ASM FIXNC SITE-SOIL v2 + BEDROCK v3 (INTERIM)",
      "surface_source":str(SOURCE),"surface_source_sha256":SOURCE_SHA,
      "surface_source_receipt":str(SOURCE_RECEIPT),
      "upstream_repo":UPSTREAM_REPO,"upstream_commit":UPSTREAM_COMMIT,"evidence_git_blobs":pinned,
      "zbedrock_old_m":old["zbedrock"],"zbedrock_new_m":ZBEDROCK,
      "clm_nbedrock_20SL_8.5m":NBEDROCK,"clm_column_bottom_m":COLUMN_BOTTOM_M,
      "use_bedrock_required":True,"use_bedrock_namelist":"use_bedrock = .true.",
      "lower_boundary_condition_required":2,
      "ORGANIC_changed":False,"texture_changed_vs_v2":False,"PFT_landunit_changed":False,
      "candidate_path":str(candidate),"candidate_sha256":sha256(candidate),"proof":proof,
      "science_approved":False,"AD400_authorised":False,"forcing_science_hold":True,
      "case_created":False,"Slurm_submitted":False,
      "next":"forcing science QC release; a new controller binding this SHA with use_bedrock = .true. in AD400, NORMAL400 and the observation run"
    }
    rec=out/"stage22_AU_ASM_v3_BEDROCK_candidate_NOT_MODEL_APPROVED.json"
    with rec.open("x",encoding="utf-8") as f:
        json.dump(manifest,f,indent=2,ensure_ascii=False)
    print("BEDROCK v3 ISOLATED CANDIDATE BUILD PASS")
    print("ONLY zbedrock MODIFIED; ALL OTHER VARIABLES IDENTICAL",proof["other_variables_byte_exact"])
    print("CANDIDATE_SHA256",manifest["candidate_sha256"])
    print("CANDIDATE",candidate)
    print("RECEIPT",rec)
    print("REQUIRES use_bedrock = .true.; FORCING HOLD; NO AD400, NO SLURM")

if __name__=="__main__":main()
