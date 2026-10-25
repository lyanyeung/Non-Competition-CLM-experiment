#!/usr/bin/env python3
"""Stage15 — Lane A standalone forest-point TECHNICAL surface candidates.

The four Lane-A UTC forcing pilots are already built by Stage14. This tool
does not redo forcing, ERA5/RH QC or UTC conversion.

Scientifically explicit experiment scenarios (NOT measured footprint area):
BR-Ma2 : NATVEG100 CROP0; FATES PFT1 evergreen tropical broadleaf 100;
         source published ORCHIDEE model-assumed forest cover, not field PFT.
CA-Ca3: NATVEG100 CROP0; FATES PFT2 evergreen extratrop needleleaf 100;
         published 75% Douglas fir, 21% cedar, 4% fir grouped one FATES PFT.
CA-LP1: NATVEG100 CROP0; FATES PFT2 evergreen extratrop needleleaf 100;
         evidence covers only three documented conifer species/saplings,
         and beetle mortality/stand age NOT encoded in static PFT fractions.
US-Bar : NO SURFACE CREATED, source reports PFT6 83%, PFT2 >=14% and
         residual ~3% unspecified; do not fabricate or normalize.

At build, copy ONLY source station point surface with exact SHA from
existing pinned Stage81 inventory, replace natural-vegetation landunit and
CLM host NAT_PFT, preserve 10-layer gridded sand/clay and every other source
variable without changes. Verify source FATES HLM map against the **actual
effective private AD parameter file**. Each candidate output accompanied by
signed receipt, excludes production approval, no CIME/Slurm actions.

--self-test: pure assertions
--check: read-only all 4 Stage14 receipts, three source surfaces/FATES map,
         exact published PFT evidence and US-Bar unresolved remainder
--build-preview --ack-idealized-three-forest-proxies --outdir BRAND_NEW
       materialize 3 independent point surfaces and US-Bar HOLD receipt.
"""
from __future__ import annotations
import argparse,csv,hashlib,json,shutil
from pathlib import Path
import numpy as np
from netCDF4 import Dataset

ROOT=Path("/iridisfs/scratch/ly3n24/CLM_FATES")
EXP=ROOT/"experiments/AmeriFlux_MultiSite_10"
SOURCE_STAGE14=EXP/"reports/stage14_LaneA_UTC_20261025T083517624796820Z"
ST81=EXP/"reports/stage81_DATM_technical_20261024T162235Z/manifest.json"
EVIDENCE=Path(__file__).resolve().parent/"Batch01_EC_FATES_PFT_experiment_candidates_v4_20261023.tsv"
EVIDENCE_BLOB="266a1bb8f56a3ca99eef317a20dc913f3b5cf9a4"
PARAM=ROOT/"experiments/NonCompetitionObserved22/Batch01_10/_private_ctsm_FATES_AD400_namelist_overlay/src/fates/parameter_files/fates_params_default.json"
# Host CLM natural pft idx 4 = broadleaf evergreen tropical, 1 = needleleaf evergreen extratrop
# Actual private FATES mapping is checked by name and slot BEFORE assigning anything.
FOREST={
 "BR-Ma2":(4,1,"broadleaf_evergreen_tropical_tree",100.0),
 "CA-Ca3":(1,2,"needleleaf_evergreen_extratrop_tree",100.0),
 "CA-LP1":(1,2,"needleleaf_evergreen_extratrop_tree",100.0)}
FOUR={"BR-Ma2","CA-Ca3","CA-LP1","US-Bar"}
CHANGE={"PCT_NATVEG","PCT_CROP","PCT_LAKE","PCT_WETLAND",
        "PCT_GLACIER","PCT_URBAN","PCT_NAT_PFT"}
ZERO=("PCT_CROP","PCT_LAKE","PCT_WETLAND","PCT_GLACIER","PCT_URBAN")
HOLD_SITE="US-Bar"

def fail(msg):raise RuntimeError(str(msg))

def sha(p):
 h=hashlib.sha256()
 with p.open("rb") as f:
  for x in iter(lambda:f.read(1048576),b""):h.update(x)
 return h.hexdigest()

def read_json(p):
 if not p.is_file():fail("Missing source file "+str(p))
 return json.loads(p.read_text(encoding="utf-8"))

def evidence():
 if not EVIDENCE.is_file():fail("Pinned evidence TSV missing next to script")
 data=EVIDENCE.read_bytes()
 blob=b"blob "+str(len(data)).encode()+b"\0"+data
 if hashlib.sha1(blob).hexdigest()!=EVIDENCE_BLOB:
  fail("Published evidence TSV version changed")
 with EVIDENCE.open(encoding="utf-8-sig",newline="") as f:
  d={x["site"]:x for x in csv.DictReader(f,delimiter="\t")}
 if not FOUR.issubset(d):fail("Pinned PFT file missing some Lane A sites")
 required={"BR-Ma2":"PFT1=100","CA-Ca3":"PFT2=100",
           "CA-LP1":"PFT2=100","US-Bar":"PFT6=83"}
 for s,key in required.items():
  if key not in d[s]["published_PFT_or_cover_percent"]:
   fail(s+": expected published PFT pattern no longer present")
  if d[s]["fraction_is_verified_FATES_initialization"]!="NO":
   fail(s+": source PFT science status changed, review before using")
 bar=d["US-Bar"]["published_PFT_or_cover_percent"]
 if not ("PFT2>=14" in bar and "~3" in bar):
  fail("US-Bar PFT unknown residual updated; re-evaluate before allocating")
 return d

def effective_map():
 if not PARAM.is_file():fail("Actual private FATES AD effective parameter file missing")
 data=read_json(PARAM)["parameters"]
 names=list(data["fates_pftname"]["data"])
 m=np.asarray(data["fates_hlm_pft_map"]["data"],dtype=float)
 if m.ndim!=2 or m.shape[1]!=len(names):
  fail("Actual FATES HLM_PFT_MAP shape does not match PFT names")
 output={}
 for site,(idx,slot,label,pct) in FOREST.items():
  if idx<1 or idx>m.shape[0]:fail(site+": CLM host PFT idx out of map range")
  found=[i+1 for i in np.flatnonzero(m[idx-1]>0)]
  if found!=[slot] or names[slot-1]!=label:
   fail(site+f": effective HLM map of CLM NATPFT {idx} maps to FATES {found}, expected {slot} {label}")
  output[site]={"CLM_HOST_NATPFT_INDEX":idx,"FATES_PFT_SLOT":slot,
                "FATES_PFT_NAME":label,"STAND_GROUP_PROXY_PERCENT":pct}
 return output

def stage14():
 m=read_json(SOURCE_STAGE14/"manifest.json")
 if (m.get("stage")!=14 or m.get("lane")!="AMERIFLUX_BATCH01_4_STATIC_ZBOT_TECHNICAL" or
     m.get("model_case_created") is not False or
     m.get("slurm_submitted") is not False or
     m.get("scientific_production_release") is not False):
  fail("Stage14 not an unsubmitted technical forcing candidate")
 if len(m.get("sites",[]))!=4 or {r["site"] for r in m["sites"]}!=FOUR:
  fail("Stage14 four static sites not as planned")
 if sum(r["years"] for r in m["sites"])!=80:
  fail("Stage14 incomplete 80-year census")
 result={}
 for rec in m["sites"]:
  p=Path(rec["manifest"])
  if p!=SOURCE_STAGE14/rec["site"]/"manifest.json" or sha(p)!=rec["manifest_sha256"]:
   fail("Stage14 source site receipt SHA changed "+rec["site"])
  d=read_json(p)
  if (d.get("site")!=rec["site"] or
      d.get("model_case_created") is not False or
      d.get("slurm_submitted") is not False or
      d.get("production_release") is not False or
      len(d.get("files",[]))!=rec["years"]):
   fail("Stage14 source site not complete or source released")
  result[rec["site"]]=d
 return result

def make_vector(var,idx):
 if var.size!=15 or sum("natpft" in v.lower() for v in var.dimensions)!=1:
  fail("Unexpected CLM 15 natpft 1PT vector shape/dimensions")
 dim=next(i for i,v in enumerate(var.dimensions) if "natpft" in v.lower())
 out=np.zeros(var.shape,dtype=np.float64)
 ix=[0]*len(var.shape)
 ix[dim]=idx
 out[tuple(ix)]=100.
 return out

def source_surfaces():
 m=read_json(ST81)
 if m.get("stage")!=81 or m.get("all_annual_netcdf_files")!=213:
  fail("Original source 213 year stage81 census changed")
 rows={r["site"]:r for r in m["sites"]}
 if set(FOREST)-set(rows):fail("One forest source surface missing")
 return rows

def model_source(p,row,site):
 if p!=Path(row["surface_path"]) or not p.is_file() or sha(p)!=row["surface_sha256"]:
  fail(site+": original Stage81 reference surface SHA changed")
 with Dataset(p) as ds:
  must=CHANGE|{"PCT_SAND","PCT_CLAY","LONGXY","LATIXY"}
  if not must.issubset(ds.variables):fail(site+": original source surface missing "+str(must-set(ds.variables)))
  lat=float(np.ma.filled(ds.variables["LATIXY"][:],np.nan).ravel()[0])
  lon=float(np.ma.filled(ds.variables["LONGXY"][:],np.nan).ravel()[0])%360
  if not (np.isfinite(lat) and np.isfinite(lon)):
   fail(site+": invalid coordinates")
  orig={}
  for key in ("PCT_NATVEG",*ZERO):
   x=np.ma.filled(ds.variables[key][:],np.nan).ravel()
   if not np.isfinite(x).all() or (key!="PCT_URBAN" and len(x)!=1):
    fail(site+": source host landunit invalid "+key)
   orig[key]=float(np.sum(x))
  pft=ds.variables["PCT_NAT_PFT"]
  if pft.size!=15:fail(site+": source natural PFT vector length not 15")
  if abs(np.ma.filled(pft[:],0).sum()-100)>0.5:
   fail(site+": existing natural PFT not sum 100")
  # Grid texture kept *exactly* as original, do not claim tower soil.
  soil={}
  for k in ("PCT_SAND","PCT_CLAY"):
   a=np.ma.filled(ds.variables[k][:],np.nan)
   if not np.isfinite(a).all() or np.min(a)<0 or np.max(a)>100:
    fail(site+": bad source grid-soil "+k)
   soil[k]={"levels":int(a.size),"range":[float(np.min(a)),float(np.max(a))]}
 print(f"SOURCE FOREST SITE {site}: NATVEG {orig['PCT_NATVEG']:.3f}% CROP {orig['PCT_CROP']:.3f}% SOIL {soil}")
 return orig,soil,(lat,lon)

def equal(a,b):
 a=np.ma.asarray(a);b=np.ma.asarray(b)
 if not np.array_equal(np.ma.getmaskarray(a),np.ma.getmaskarray(b)):return False
 if a.dtype.kind in ("f","c") and b.dtype.kind in ("f","c"):
  return np.array_equal(np.ma.filled(a,0),np.ma.filled(b,0),equal_nan=True)
 return np.array_equal(np.ma.filled(a),np.ma.filled(b))

def write_and_verify(src,dest,idx,site):
 shutil.copy2(src,dest)
 with Dataset(dest,"r+") as d:
  d.variables["PCT_NATVEG"][:]=100.
  for var in ZERO:d.variables[var][:]=0.
  d.variables["PCT_NAT_PFT"][:]=make_vector(d.variables["PCT_NAT_PFT"],idx)
  d.technical_experiment="IDEALIZED_FOREST_POINT_NOT_MEASURED_EC_FOOTPRINT"
  d.tower_soil_status="UNMODIFIED_GRID_SOIL_FALLBACK_NOT_SITE_OBS"
  d.population="STAND_PFT_GROUP_PROXY_NOT_FATES_INITIAL_FOREST_STRUCTURE"
 with Dataset(src) as a,Dataset(dest) as b:
  if set(a.variables)!=set(b.variables):fail(site+": modified variable registry")
  for var in a.variables:
   if a.variables[var].dimensions!=b.variables[var].dimensions:
    fail(site+": NetCDF variable dimensions changed "+var)
   if var not in CHANGE and not equal(a.variables[var][:],b.variables[var][:]):
    fail(site+": unrelated surface variable changed "+var)
  for var,value in (("PCT_NATVEG",100.),*[(key,0.) for key in ZERO]):
   x=np.ma.filled(b.variables[var][:],np.nan)
   if not np.isfinite(x).all() or not np.allclose(x,value,atol=1e-4,rtol=0):
    fail(site+": model landunit fraction incorrect "+var)
  want=make_vector(b.variables["PCT_NAT_PFT"],idx)
  if not np.array_equal(np.ma.filled(b.variables["PCT_NAT_PFT"][:],np.nan),want):
   fail(site+": forest PFT group is not unique 100%")
  tot=sum(np.ma.filled(b.variables[v][:],np.nan).sum() for v in ("PCT_NATVEG",*ZERO))
  if abs(tot-100)>1e-4:fail(site+": total host landunit percent not 100")
 print("NEW SURFACE PASS:",site,"idealized NATVEG100 / single forest FATES PFT group, grid soil unchanged")

def main():
 a=argparse.ArgumentParser(description=__doc__)
 g=a.add_mutually_exclusive_group(required=True)
 g.add_argument("--self-test",action="store_true")
 g.add_argument("--check",action="store_true")
 g.add_argument("--build-preview",action="store_true")
 a.add_argument("--outdir",type=Path)
 a.add_argument("--ack-idealized-three-forest-proxies",action="store_true")
 x=a.parse_args()
 if x.self_test:
  assert len(FOREST)==3 and len(FOUR)==4 and set(FOREST)|{"US-Bar"}==FOUR
  assert FOREST["BR-Ma2"][:2]==(4,1)
  assert FOREST["CA-Ca3"][:2]==(1,2)
  print("SELF-TEST PASS: 3 named forest stands, 1 unresolved US-Bar hold; no implicit allocation")
  return
 if x.check and (x.outdir or x.ack_idealized_three_forest_proxies):
  a.error("--check is read-only")
 if x.build_preview and (x.outdir is None or not x.ack_idealized_three_forest_proxies):
  a.error("--build-preview requires --outdir NEW and --ack-idealized-three-forest-proxies")
 met=stage14()
 ev=evidence()
 mapped=effective_map()
 rows=source_surfaces()
 for site in FOREST:
  source=Path(rows[site]["surface_path"])
  old,soil,coord=model_source(source,rows[site],site)
  print("PFT SCIENCE",site,ev[site]["published_PFT_or_cover_percent"],
        "EVIDENCE BASIS",ev[site]["percentage_denominator"],"MAP",mapped[site])
  if list(map(float,met[site]["source_point_lat_lon"]))!=list(map(float,coord)):
   if not np.allclose(met[site]["source_point_lat_lon"],coord,rtol=0,atol=1e-4):
    fail(site+": Stage14 UTC forcing vs Stage81 grid surface location changed")
 print("US-Bar HOLD: PFT6=83, PFT2>=14, approximately 3% unclassified; no auto normalization")
 print("STAGE15 PREFLIGHT PASS: 3 forest PFT/host-map/soil-point sources, Stage14 four met receipts, US-Bar held")
 if x.check:return
 out=x.outdir.expanduser().resolve()
 if out.exists() or out.is_symlink():fail("Refuse existing output directory: "+str(out))
 out.mkdir(parents=True,exist_ok=False)
 summary={"stage":15,"source_stage14_manifest_sha256":sha(SOURCE_STAGE14/"manifest.json"),
          "source_FATES_param_sha256":sha(PARAM),"PFT_evidence_git_blob":EVIDENCE_BLOB,
          "scientific_production_release":False,"site_soil_measured":False,
          "model_cases_created":False,"slurm_submitted":False,
          "US-Bar":"HOLD_UNCLASSIFIED_PFT_SHARE_NOT_ASSIGNED",
          "sites":[]}
 for site,(idx,slot,label,pct) in FOREST.items():
  src=Path(rows[site]["surface_path"])
  old,soil,coord=model_source(src,rows[site],site)
  sdir=out/site
  sdir.mkdir()
  dst=sdir/f"surfdata_{site}_FIXNC_IDEALIZED_{label}_100_GRIDSOIL_v1.nc"
  before=sha(src)
  write_and_verify(src,dst,idx,site)
  if sha(src)!=before:fail(site+": source original changed during build")
  item={"site":site,"original":str(src),"original_sha256":before,
        "new_surface":str(dst),"new_surface_sha256":sha(dst),
        "site_source_years":met[site]["start_year"],"source_fates_pft":mapped[site],
        "source_pft_evidence":ev[site]["reference"],
        "evidence_denominator":ev[site]["percentage_denominator"],
        "original_landunit_percent":old,"original_soil_grid":soil,
        "model_landunit_proxy":{"NATVEG":100,"CROP":0,"host_natpft":idx,"percent":100},
        "stand_area_fraction_verified":False,"site_soil_measured":False,
        "model_case_created":False,"slurm_submitted":False,
        "production_release":False}
  rec=sdir/"manifest.json"
  rec.write_text(json.dumps(item,indent=2)+"\n",encoding="utf-8")
  summary["sites"].append({"site":site,"manifest":str(rec),"sha256":sha(rec)})
  print("FOREST PROXY COMPLETED",site,flush=True)
 (out/"manifest.json").write_text(json.dumps(summary,indent=2)+"\n",encoding="utf-8")
 print("STAGE15 SUCCESS: THREE independent idealized forest-point surface candidates")
 print("US-Bar MIXED FOREST HOLD; NO PFT ASSIGNMENT; NO CIME OR SLURM ACTION")
 print("OUTPUT:",out)

if __name__=="__main__":main()
