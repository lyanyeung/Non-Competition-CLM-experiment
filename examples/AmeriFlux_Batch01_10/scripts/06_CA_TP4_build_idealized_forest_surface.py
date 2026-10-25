#!/usr/bin/env python3
"""Stage06 CA-TP4 independent TECHNICAL forest-point surface scenario.

Create a *new* point surface in a dedicated output directory:
  natural-vegetated landunit 100%, crop and other landunits 0%;
  CLM HLM natpft idx1 ENF 93%, idx7 DBF 7%; matches the
  *FATES* tree stand grouping PFT2=93/PFT6=7 ONLY under a checked
  local fates_hlm_pft_map. This is an IDEALIZED proxy for model TECHNICAL
  SMOKE, NOT measured ground-area/footprint percentages.
  Source 10-layer PCT_SAND/PCT_CLAY and ALL OTHER soil/terrain
  variables are unchanged; *grid-soil fallback*, NOT observed site soil.

Prereqs: Stage05 read-only success + pinned evidence and site surface.
No model cases or Slurm are modified, submitted or prepared by Stage06.
--self-test / --check are read-only;
--build --outdir NEW_DIRECTORY --ack-idealized-forest-grid-soil
is explicit experimental opt-in, cannot overwrite anything.
"""
from __future__ import annotations
import argparse,csv,hashlib,json,math,os,shutil
from datetime import datetime,timezone
from pathlib import Path

import numpy as np
from netCDF4 import Dataset

BASE=Path("/iridisfs/scratch/ly3n24/CLM_FATES")
ORIGINAL=BASE/"sites/MY_EC_SITE/CA-TP4/subset_data/surfdata_CA-TP4_hist_2000_16pfts_c261021.nc"
SOURCE_SHA256="ceaf4ebed72fd5e43e34838f2a360d6524752a631bc925f087af8b7612847748"
PARAM=BASE/"CTSM/src/fates/parameter_files/fates_params_default.json"
HERE=Path(__file__).resolve().parent
EVIDENCE=HERE/"Batch01_EC_FATES_PFT_experiment_candidates_v4_20261023.tsv"
EVIDENCE_BLOB="266a1bb8f56a3ca99eef317a20dc913f3b5cf9a4"
SITE="CA-TP4"
LAND_ZERO=("PCT_CROP","PCT_LAKE","PCT_WETLAND","PCT_GLACIER","PCT_URBAN")
CHANGED=("PCT_NATVEG","PCT_CROP","PCT_LAKE","PCT_WETLAND",
         "PCT_GLACIER","PCT_URBAN","PCT_NAT_PFT")
ENF=1
DBF=7
EXPECTED={"needleleaf_evergreen_extratrop_tree":93.,
          "broadleaf_colddecid_extratrop_tree":7.}
EXPECTED_PFT={ENF:93.0,DBF:7.0}

def sha(path):
 h=hashlib.sha256()
 with path.open("rb") as f:
  for b in iter(lambda:f.read(1048576),b""):h.update(b)
 return h.hexdigest()

def fail(msg):
 raise RuntimeError(str(msg))

def pft_map():
 if not PARAM.is_file():fail("FATES paramfile not found "+str(PARAM))
 data=json.loads(PARAM.read_text(encoding="utf-8"))["parameters"]
 names=list(data["fates_pftname"]["data"])
 raw=np.asarray(data["fates_hlm_pft_map"]["data"],dtype=float)
 if raw.ndim!=2 or len(raw)<DBF:fail("Unexpected FATES HLM map shape "+repr(raw.shape))
 found={}
 for idx,classname in ((ENF,"needleleaf_evergreen_extratrop_tree"),(DBF,"broadleaf_colddecid_extratrop_tree")):
  mapped=[names[i] for i in np.flatnonzero(raw[idx-1]>0)]
  if mapped!=[classname]:
   fail(f"CLM natpft index {idx} maps to FATES {mapped}, not solely {classname}; do not create surface")
  found[str(idx)]={"fates_pft_name":mapped[0],"fates_pft_slot_1based":names.index(mapped[0])+1}
 if found[str(ENF)]["fates_pft_slot_1based"]!=2 or found[str(DBF)]["fates_pft_slot_1based"]!=6:
  fail("Expected FATES PFT indices 2 and 6 differ: "+repr(found))
 return found

def evidence():
 if not EVIDENCE.is_file():fail("Pinned stand composition TSV absent: download Stage05 companion file "+str(EVIDENCE))
 raw=EVIDENCE.read_bytes()
 git_blob=b"blob "+str(len(raw)).encode()+b"\0"+raw
 if hashlib.sha1(git_blob).hexdigest()!=EVIDENCE_BLOB:
  fail("Pinned stand composition evidence changed")
 with EVIDENCE.open(encoding="utf-8-sig",newline="") as f:
  rows=[r for r in csv.DictReader(f,delimiter="\t") if r.get("site")==SITE]
 if len(rows)!=1:fail("Ambiguous CA-TP4 PFT evidence")
 row=rows[0]
 if ("PFT2=93" not in row["published_PFT_or_cover_percent"] or
     "PFT6=7" not in row["published_PFT_or_cover_percent"] or
     row["fraction_is_verified_FATES_initialization"]!="NO"):
  fail("Stand fractions/source denominator changed: do not pretend site PFT ground-area is observed")
 return row

def vector(ds):
 var=ds.variables["PCT_NAT_PFT"]
 if var.size!=15 or sum("natpft" in d.lower() for d in var.dimensions)!=1:
  fail("Expected 15-element CLM natural PFT layout, found "+repr((var.shape,var.dimensions)))
 axis=next(i for i,d in enumerate(var.dimensions) if "natpft" in d.lower())
 arr=np.zeros(var.shape,dtype="f8")
 for idx,pct in EXPECTED_PFT.items():
  indices=[0]*len(var.shape)
  indices[axis]=idx
  arr[tuple(indices)]=pct
 return arr

def source_check():
 if not ORIGINAL.is_file() or ORIGINAL.is_symlink() or sha(ORIGINAL)!=SOURCE_SHA256:
  fail("Original CA-TP4 surface checksum changed or original missing")
 mapping=pft_map()
 ev=evidence()
 with Dataset(ORIGINAL) as ds:
  required=set(CHANGED)|{"PCT_SAND","PCT_CLAY"}
  if not required.issubset(ds.variables):fail("Original surface schema missing "+repr(required-set(ds.variables)))
  for name in ("PCT_NATVEG",*LAND_ZERO):
   size=ds.variables[name].size
   if name=="PCT_URBAN":
    if size<1:fail("Missing source urban density classes")
   elif size!=1:fail("Not a point landunit "+name)
  for field in ("PCT_SAND","PCT_CLAY"):
   vals=np.ma.filled(ds.variables[field][:],np.nan).ravel()
   if vals.size!=10 or not np.isfinite(vals).all() or np.any(vals<0) or np.any(vals>100):
    fail("Invalid ten-layer source grid soil "+field)
  old={}
  for k in ("PCT_NATVEG",*LAND_ZERO):
   data=np.ma.filled(ds.variables[k][:],np.nan).ravel()
   if not np.isfinite(data).all():fail("Nonfinite source landunit "+k)
   old[k]=float(data.sum()) if k=="PCT_URBAN" else float(data[0])
  oldpft=np.ma.filled(ds.variables["PCT_NAT_PFT"][:],np.nan).ravel()
  if oldpft.size!=15 or not np.isfinite(oldpft).all():
   fail("Original source natural PFT invalid")
  v=vector(ds)
  print("GRID SOURCE LANDUNIT PCT:",{k:round(v,5) for k,v in old.items()})
  print("GRID SOURCE NATPFT:",[round(float(x),5) for x in oldpft])
  soil={}
  for field in ("PCT_SAND","PCT_CLAY"):
   x=np.ma.filled(ds.variables[field][:],np.nan).ravel()
   soil[field]={"levels":len(x),"min":float(np.min(x)),"max":float(np.max(x))}
  print("GRID SOURCE SOIL TEXTURE:",soil)
  print("PROPOSED CA-TP4 FOREST POINT: NATVEG100 CROP0, ENF93 DBF7")
  print("FATES HLM MAP CHECK:",mapping)
  print("TREE EVIDENCE:",ev["published_PFT_or_cover_percent"])
  print("DENOMINATOR:",ev["percentage_denominator"])
  print("SOIL POLICY: GRID 10-LAYER TEXTURE INHERITED, NOT MEASURED")
  return mapping,ev,old,soil

def modify(dst):
 with Dataset(dst,"r+") as ds:
  for key,target in (("PCT_NATVEG",100.0),):
   ds.variables[key][:]=target
  for key in LAND_ZERO:
   ds.variables[key][:]=0.
  ds.variables["PCT_NAT_PFT"][:]=vector(ds)
  ds.ca_tp4_science_scope="IDEALIZED_FOREST_POINT_FOR_TECHNICAL_AD5_SMOKE_NOT_OBSERVED_WHOLE_FOOTPRINT"
  ds.ca_tp4_stand_composition="ENF93_PFT2_DB7_PFT6_TREE_STAND_SPECIES_NOT_GROUND_AREA"
  ds.ca_tp4_soil_policy="PCT_SAND/CLAY INHERITED FROM ORIGINAL GRID; NOT OBSERVED STATION PROFILE"
  ds.ca_tp4_all_other_surface_variables="UNMODIFIED_ORIGINAL_POINT_SURFACE_VALUES_GRID_PROXIES"

def array_identical(a,b):
 # Compare masks and data across both numeric and text NetCDF variables.
 x=np.ma.asarray(a);y=np.ma.asarray(b)
 if not np.array_equal(np.ma.getmaskarray(x),np.ma.getmaskarray(y)):
  return False
 if x.dtype.kind in ("f","c") and y.dtype.kind in ("f","c"):
  return np.array_equal(np.ma.filled(x,0),np.ma.filled(y,0),equal_nan=True)
 return np.array_equal(np.ma.filled(x),np.ma.filled(y))

def verify(dest,source):
 with Dataset(source) as a,Dataset(dest) as b:
  if set(a.variables)!=set(b.variables):fail("Copied surface variable set changed")
  for k in a.variables:
   if a.variables[k].dimensions!=b.variables[k].dimensions:
    fail("Variable dimension changed "+k)
   if k not in CHANGED:
    if not array_identical(a.variables[k][:],b.variables[k][:]):
     fail("Unrelated grid soil, terrain or point-surface variable changed "+k)
  for k,v in (("PCT_NATVEG",100.0),*[(x,0.) for x in LAND_ZERO]):
   vals=np.ma.filled(b.variables[k][:],np.nan).ravel()
   if not np.isfinite(vals).all() or (k!="PCT_URBAN" and len(vals)!=1) or not np.allclose(vals,v,rtol=0,atol=1e-5):
    fail("Pilot landunit incorrect "+k)
  arr=np.ma.filled(b.variables["PCT_NAT_PFT"][:],np.nan)
  wanted=vector(b)
  if not np.isfinite(arr).all() or not np.allclose(arr,wanted,atol=1e-5,rtol=0):
   fail("Pilot natural PFTs wrong")
  total=sum(float(np.ma.filled(b.variables[k][:],np.nan).sum()) for k in ("PCT_NATVEG",*LAND_ZERO))
  if abs(total-100)>1e-4:fail("Pilot landunit total!=100")
  for k in ("PCT_SAND","PCT_CLAY"):
   if not array_identical(a.variables[k][:],b.variables[k][:]):fail("Grid soil modified "+k)
 print("NEW SURFACE VERIFIED: forest NATVEG100, CROP0, ENF93 DBF7; all unrelated fields unchanged")
 return True

def build(out):
 out=out.expanduser().resolve()
 if out.exists() or out.is_symlink():fail("Refuse existing output directory "+str(out))
 mapping,evidence_row,previous,soil=source_check()
 original_sha=sha(ORIGINAL)
 out.mkdir(parents=True)
 dst=out/"surfdata_CA-TP4_FIXNC_ENF93_DBF7_forestry_proxy_gridsoil_v1.nc"
 shutil.copy2(ORIGINAL,dst)
 modify(dst)
 verify(dst,ORIGINAL)
 if sha(ORIGINAL)!=original_sha:fail("Source surface changed during isolated build")
 document={"site":SITE,"experiment":"CA-TP4_IDEALIZED_FOREST_POINT_PFT93_7_GRIDSOIL_ONLY",
           "model_stage":"AD5_PREPARATION_NOT_MODEL_READY","surface":str(dst),
           "surface_sha256":sha(dst),"original_surface":str(ORIGINAL),
           "original_surface_sha256":original_sha,
           "evidence_git_blob_sha1":EVIDENCE_BLOB,
           "stand_PFT_source":evidence_row["reference"],
           "stand_percent_denominator":evidence_row["percentage_denominator"],
           "stand_tree_PFT_percent":{"FATES_PFT2_ENF":93,"FATES_PFT6_DBF":7},
           "surface_hypothesis":{"NATVEG":100,"CROP":0,"ENF_CLM_NATPFT_1":93,"DBF_CLM_NATPFT_7":7},
           "soil_policy":"GRID_SOIL_TEXTURE_FALLBACK_ONLY_NOT_OBSERVED",
           "soil_source_layer_details":soil,"other_fields":"UNMODIFIED_GRID_SCHEMA_NOT_OBSERVED",
           "fates_mapping_verified_local_paramfile":mapping,
           "original_landunit":previous,
           "production_quality_forest_footprint_evidence":False,
           "site_specific_soil_observation_used":False,
           "FATES_case_created":False,"Slurm_submitted":False,
           "model_release":False,"created_utc":datetime.now(timezone.utc).isoformat()}
 receipt=out/"manifest.json"
 receipt.write_text(json.dumps(document,indent=2)+"\n",encoding="utf-8")
 print("SUCCESS: CA-TP4 independently versioned forest-proxy surface",dst)
 print("MANIFEST:",receipt)
 print("NO CIME CASE / SLURM ACTIONS. 2002-2023 MET PILOT REMAINS IN STAGE04.")

def selftest():
 assert len(EXPECTED_PFT)==2 and sum(EXPECTED_PFT.values())==100.
 assert ENF==1 and DBF==7
 assert len(LAND_ZERO)==5
 print("SELF-TEST PASS: explicit NATVEG100-CROP0 proxy, CLM idx1/7 ENF93 DBF7, pinned PFT evidence")

def main():
 p=argparse.ArgumentParser(description=__doc__)
 g=p.add_mutually_exclusive_group(required=True)
 g.add_argument("--self-test",action="store_true")
 g.add_argument("--check",action="store_true")
 g.add_argument("--build",action="store_true")
 p.add_argument("--outdir",type=Path)
 p.add_argument("--ack-idealized-forest-grid-soil",action="store_true")
 a=p.parse_args()
 if a.self_test:selftest();return
 if a.check:
  if a.outdir is not None or a.ack_idealized_forest_grid_soil:p.error("Read-only --check accepts neither output nor ack")
  source_check()
  print("READ-ONLY INPUTS PASS — CREATE NO FILES; explicit idealized-landunit ack required for --build")
  return
 if not a.build or not a.outdir or not a.ack_idealized_forest_grid_soil:
  p.error("--build requires --outdir NEW_DIR and --ack-idealized-forest-grid-soil")
 build(a.outdir)

if __name__=="__main__":main()
