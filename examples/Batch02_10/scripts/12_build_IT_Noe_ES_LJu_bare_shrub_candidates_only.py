#!/usr/bin/env python3
"""Stage12: only two explicit Batch02 six-site PFT candidate surfaces.
IT-Noe: HLM bare0=34%, temperate evergreen shrub9=66% (COVER MIDPOINT);
ES-LJu: bare0=49%, cool C3 grass13=31%, evergreen shrub9=20%
        (19.8% unclassified VEGETATION prorated; phenology assumption).

Source surfaces come from the exact known original, site-specific CIME
CaseDocs/lnd_in, with source SHA256 recorded. Leave source grid soil,
geography, all forcing data and shared FATES unchanged. The NEW dedicated
point surface is NATVEG100/CROP0/other0, a technical model proxy, not
measured footprint area. Bare ground is NATPFT[0] inside natural landunit.
--plan: READ ONLY checks originals, geometry, mapping, 15-PFT layout;
--build --confirm CREATE_TWO_BATCH02_BARE_SHRUB_SURFACE_PROXIES:
    creates two VERSIONED NetCDF candidates, SHA receipt, no case/Slurm.
Do not build other four FOREST sites with unresolved tree species percentages.
"""
from __future__ import annotations
import argparse,hashlib,json,os,re,shutil,tempfile
from datetime import datetime,timezone
from pathlib import Path
import numpy as np
from netCDF4 import Dataset

ROOT=Path("/iridisfs/scratch/ly3n24/CLM_FATES")
PARAM=ROOT/"CTSM/src/fates/parameter_files/fates_params_default.json"
PARAM_SHA="0819f8fddcb3566f6209f72bb1159a3161d03c8225a1464727b1d2b21aec6c04"
DEST=ROOT/"experiments/NonCompetitionObserved22/Batch02_10/stage12_remaining6_bare_shrub_candidates_v1"
SITES={
"IT-Noe":{"source_case":"IT-Noe_ERA5_ABW_BRANCH2009",
          "host":{0:34,9:66},"bare_basis":"42-91% vegetation range, central midpoint 66.5% and 33.5% bare; rounded 66/34",
          "scientific_hold":"UNAPPROVED_FOOTPRINT_COVER_JUNIPER_IS_NEEDLELEAF_SHRUB_PROXY"},
"ES-LJu":{"source_case":"ES-LJu_FATES_SPINUP1000_S30SHARED",
          "host":{0:49,13:31,9:20},"bare_basis":"49.1% measured gravel/rock/bare ground; 19.8% unnamed vegetation distributed grass/shrub pro rata",
          "scientific_hold":"UNNAMED_19_8_VEGETATION_SHRUB_PHENOLOGY_PROXY"}}
CHANGED={"PCT_NATVEG","PCT_CROP","PCT_NAT_PFT","PCT_LAKE",
         "PCT_WETLAND","PCT_GLACIER","PCT_URBAN"}
CONFIRM="CREATE_TWO_BATCH02_BARE_SHRUB_SURFACE_PROXIES"

def stop(msg):raise RuntimeError(str(msg))
def digest(file):
 h=hashlib.sha256()
 with Path(file).open("rb") as f:
  for b in iter(lambda:f.read(1<<20),b""):h.update(b)
 return h.hexdigest()
def namelist_path(case):
 p=case/"CaseDocs/lnd_in"
 if not p.is_file():stop("Original site source CaseDocs/lnd_in absent "+str(p))
 matches=re.findall(r"""(?im)^\s*fsurdat\s*=\s*['"]?([^'"\s,!,]+)""",p.read_text(encoding="utf8"))
 if len(matches)!=1:stop("Cannot resolve unique original fsurdat "+str(p))
 file=Path(matches[0])
 if not file.is_file() or not file.name.startswith("surfdata_"+case.name.split("_")[0]):
  stop("Source surface not site-specific source case: "+str(file))
 return file
def matrix():
 if not PARAM.is_file() or digest(PARAM)!=PARAM_SHA:
  stop("Active FATES default parameter SHA differs from verified Batch02 source")
 params=json.loads(PARAM.read_text(encoding="utf8"))["parameters"]
 names=params["fates_pftname"]["data"]
 mat=params["fates_hlm_pft_map"]["data"]
 if len(names)!=14 or len(mat)!=14:stop("FATES 14 class mapping unexpected")
 for host,want in ((9,"broadleaf_evergreen_extratrop_shrub"),
                  (13,"cool_c3_grass")):
  row=mat[host-1]
  if any(abs(float(x)-(1. if i==names.index(want) else 0.))>1e-8 for i,x in enumerate(row)):
   stop("Source FATES host PFT mapping not unique: HLM"+str(host))
 print("FATES MAPPING PASS HLM9 evergreen extra-tropical shrub, HLM13 cool C3 grass, HLM0 bare")
def prepare(site):
 item=SITES[site]
 case=ROOT/"cases"/item["source_case"]
 if not case.is_dir():stop("Original case missing "+str(case))
 source=namelist_path(case)
 pft=[0.]*15
 for k,v in item["host"].items():pft[k]=float(v)
 if abs(sum(pft)-100)>1e-9:stop("Invalid PFT total")
 with Dataset(source) as ds:
  required=("LATIXY","LONGXY","PCT_NAT_PFT","PCT_NATVEG","PCT_CROP","PCT_SAND","PCT_CLAY")
  for key in required:
   if key not in ds.variables:stop("Source surface missing "+key)
  v=ds.variables["PCT_NAT_PFT"]
  if v.size!=15 or v.dimensions[0]!="natpft":
   stop("Source natural PFT vector not index0-14")
  for k in ("LATIXY","LONGXY","PCT_NATVEG","PCT_CROP"):
   if ds.variables[k].size!=1:stop("Not a point surface "+k)
  lat=float(np.asarray(ds.variables["LATIXY"][:]).reshape(-1)[0])
  lon=float(np.asarray(ds.variables["LONGXY"][:]).reshape(-1)[0])%360
  if not (-90<=lat<=90 and 0<=lon<360):stop("Source coordinates invalid")
  soil={}
  for k in ("PCT_SAND","PCT_CLAY"):
   v=ds.variables[k]
   soil[k]={"shape":list(v.shape),"first_layers":[float(x) for x in np.asarray(v[:]).ravel()[:10]]}
 print("PLAN",site,"SOURCE",source,"LAT/LON",(lat,lon),
       "HOST_NATPFT_NONZERO",item["host"],"INPUT_SOIL_PRESERVED_GRID")
 print("SCIENCE STATUS",item["scientific_hold"],"DATA PROVENANCE",item["bare_basis"])
 return source,pft,(lat,lon),soil
def verify(source,candidate,pft,point):
 with Dataset(source) as a,Dataset(candidate) as b:
  if set(a.variables)!=set(b.variables) or set(a.dimensions)!=set(b.dimensions):
   stop("NetCDF source schema changed in proposed candidate")
  for k in a.dimensions:
   if len(a.dimensions[k])!=len(b.dimensions[k]):stop("NetCDF dimension changed "+k)
  for k in a.variables:
   if k in CHANGED:continue
   x=np.ma.asarray(a.variables[k][:]);y=np.ma.asarray(b.variables[k][:])
   if x.shape!=y.shape or not np.array_equal(np.ma.getmaskarray(x),np.ma.getmaskarray(y)):
    stop("Unintended changed variable mask/shape "+k)
   c=np.ma.getdata(x);d=np.ma.getdata(y)
   same=np.array_equal(c,d,equal_nan=True) if c.dtype.kind in "fc" else np.array_equal(c,d)
   if not same:stop("Unintended NetCDF variable changed "+k)
  for k,w in (("PCT_NATVEG",100),("PCT_CROP",0)):
   if not np.allclose(np.asarray(b.variables[k][:]).ravel(),w,atol=1e-4):
    stop("Candidate incorrect natural landunit "+k)
  for k in CHANGED-{"PCT_NATVEG","PCT_CROP","PCT_NAT_PFT"}:
   if k in b.variables and not np.allclose(b.variables[k][:],0,atol=1e-4):
    stop("Candidate other landunit non-zero "+k)
  arr=np.asarray(b.variables["PCT_NAT_PFT"][:]).ravel()
  if not np.allclose(arr,pft,atol=1e-5):stop("Candidate 15-vector PFT incorrect")
  newpoint=(float(np.asarray(b.variables["LATIXY"][:]).ravel()[0]),
            float(np.asarray(b.variables["LONGXY"][:]).ravel()[0])%360)
  if abs(newpoint[0]-point[0])>1e-7 or abs((newpoint[1]-point[1]+180)%360-180)>1e-7:
   stop("Candidate surface point moved")
def build_one(site,plan):
 source,pft,point,soil=plan
 item=SITES[site]
 dest=DEST/site/("surfdata_"+site+"_B02_BARESHRUB_PFT_proxy_v1.nc")
 receipt=DEST/site/"manifest.json"
 if dest.exists() or dest.is_symlink() or receipt.exists() or receipt.is_symlink():
  stop("Refusing second build; examine already existing candidate/receipt "+str(dest))
 dest.parent.mkdir(parents=True,exist_ok=True)
 fd,tmpstr=tempfile.mkstemp(prefix=".pft-temp-",suffix=".nc",dir=dest.parent)
 os.close(fd)
 tmp=Path(tmpstr)
 try:
  shutil.copyfile(source,tmp)
  with Dataset(tmp,"r+") as ds:
   ds.variables["PCT_NATVEG"][:]=100.
   ds.variables["PCT_CROP"][:]=0.
   for k in CHANGED-{"PCT_NATVEG","PCT_CROP","PCT_NAT_PFT"}:
    if k in ds.variables:ds.variables[k][:]=0.
   v=ds.variables["PCT_NAT_PFT"]
   v[:]=np.asarray(pft).reshape(v.shape)
   ds.setncattr("batch02_six_pft_proxy_version","v1_20261025")
   ds.setncattr("batch02_six_pft_proxy_status","UNAPPROVED_AREA_PROXY_NO_CIME_RUN")
  verify(source,tmp,pft,point)
  if not dest.parent.is_dir() or not source.is_file():stop("Missing dest/source during build")
  orig_digest=digest(source)
  tmp_digest=digest(tmp)
  if not dest.exists():os.link(tmp,dest)
  else:stop("Candidate changed concurrently")
  detail={"site":site,"candidate":str(dest),"candidate_sha256":tmp_digest,
   "original_case":item["source_case"],"original_fsurdat":str(source),
   "original_fsurdat_sha256":orig_digest,"source_point_lat_lon":point,
   "PCT_NAT_PFT_15_HOST":pft,"PCT_NATVEG":100,"PCT_CROP":0,
   "other_landunits":"ASSUMED_0_POINT_PROXY","soil":"ORIGINAL_GRID_PCT_SAND_AND_CLAY_PRESERVED",
   "original_source_soil":soil,"science_gate":item["scientific_hold"],
   "evidence_and_proxy":item["bare_basis"],
   "FATES_default_parameter_sha256":PARAM_SHA,
   "original_surface_modified":False,"forcing_modified":False,
   "CIME_cases_created":False,"Slurm_jobs_submitted":False,
   "created_utc":datetime.now(timezone.utc).isoformat()}
  with receipt.open("x",encoding="utf8") as out:
   json.dump(detail,out,indent=2);out.write("\n")
  print("STAGE12 CANDIDATE BUILT",site,dest,"SHA256",tmp_digest,"NO JOBS")
 finally:
  tmp.unlink(missing_ok=True)
def main():
 p=argparse.ArgumentParser(description=__doc__)
 g=p.add_mutually_exclusive_group(required=True)
 g.add_argument("--self-test",action="store_true")
 g.add_argument("--plan",action="store_true")
 g.add_argument("--build",action="store_true")
 p.add_argument("--confirm",default="")
 args=p.parse_args()
 if args.self_test:
  assert set(SITES)=={"IT-Noe","ES-LJu"}
  assert all(sum(x["host"].values())==100 for x in SITES.values())
  print("SELF-TEST PASS two exact explicit Batch02 shrub/bare proxy surfaces; no writes")
  return
 if args.build and args.confirm!=CONFIRM:
  p.error("Explicit confirmation required for new NetCDF surface candidates")
 matrix()
 plans={s:prepare(s) for s in SITES}
 for site in SITES:
  target=DEST/site/("surfdata_"+site+"_B02_BARESHRUB_PFT_proxy_v1.nc")
  print("TARGET",site,target,
        "EXISTS",target.exists(),
        "ACTION","UNTOUCHED" if args.plan else "CREATE_ONLY")
 if args.plan:
  print("STAGE12 PLAN PASS 2/2; ORIGINAL MODEL/CASES/SLURM UNCHANGED")
  return
 # All two must have free new destination before any write.
 for site in SITES:
  d=DEST/site/("surfdata_"+site+"_B02_BARESHRUB_PFT_proxy_v1.nc")
  rec=d.parent/"manifest.json"
  if d.exists() or d.is_symlink() or rec.exists() or rec.is_symlink():
   stop("Candidate destination already exists; refuse partial overwrite "+str(d))
 for site in SITES:build_one(site,plans[site])
 print("STAGE12 TWO BATCH02 BARE/SHRUB SURFACE CANDIDATES CREATED, NO SLURM")
if __name__=="__main__":main()
