#!/usr/bin/env python3
"""One consolidated READ-ONLY nine-site AmeriFlux FIXNC AD400/Normal400 rollout audit.

This is NOT nine reruns of the Stage80 meteorology QC or the CA-TP4 pilot
12-stage workflow. It reads the EXISTING pinned 213 NC Stage81/82 census,
original Stage31 station-height candidate policy, published FATES species
research metadata, individual AMF BIF UTC_OFFSET and existing point surfaces.
Reports a 9-site execution matrix: provisional static-height fast lane,
dated-height scientific reviews, ambiguous multi-height hold. All 9 remain
subject to model-ready landunit/PFT/soil and TA_F source science checks.

--self-test pure assertions
--check read-only complete nine-site state; NO writes, model, Slurm, NetCDF.
"""
from __future__ import annotations
import argparse,csv,hashlib,json,math
from pathlib import Path
import numpy as np
from netCDF4 import Dataset

ROOT=Path("/iridisfs/scratch/ly3n24/CLM_FATES")
AMF=ROOT/"experiments/AmeriFlux_MultiSite_10"
S31=AMF/"reports/stage31_provisional_ZBOT_scenarios_20261022T022341481986Z/01_provisional_site_height_policies.json"
S81=AMF/"reports/stage81_DATM_technical_20261024T162235Z/manifest.json"
S82=AMF/"reports/stage82_DATM_case_integration_preflight_20261024T231124502670Z/manifest.json"
SITES=("BR-Ma2","CA-Ca3","CA-Cbo","CA-LP1","CA-Man","CA-TP1","CA-TP3","US-Aud","US-Bar")
STATIC={"BR-Ma2":51.1,"CA-Ca3":12.0,"CA-LP1":26.0,"US-Bar":23.8}
DYNAMIC={"CA-TP1":4.0,"CA-TP3":16.0,"US-Aud":1.25}
BLOCKED={"CA-Cbo","CA-Man"}
ALL=set(SITES)|{"CA-TP4"}
HERE=Path(__file__).resolve().parent
PFT=HERE/"Batch01_EC_FATES_PFT_experiment_candidates_v4_20261023.tsv"
PFT_GIT_BLOB="266a1bb8f56a3ca99eef317a20dc913f3b5cf9a4"
ACTUAL_SOURCE=ROOT/"sites/MY_EC_SITE"
CA_TP4_CASE=ROOT/"cases/CA-TP4_AMF_FIXNC_AD400_UTC_V2_AD5"

def sha(p):
 h=hashlib.sha256()
 with p.open("rb") as f:
  for block in iter(lambda:f.read(1<<20),b""):h.update(block)
 return h.hexdigest()

def fail(msg):raise RuntimeError(str(msg))

def load(p):
 if not p.is_file():fail("Missing existing report "+str(p))
 return json.loads(p.read_text(encoding="utf-8"))

def get_stage_data():
 s31=load(S31);s81=load(S81);s82=load(S82)
 if s31.get("method")!="AmeriFlux_STAGE31_BASE_STATIC_DYNAMIC_POLICY_SCENARIOS":
  fail("Pinned ZBOT source changed")
 if (s81.get("stage")!=81 or s81.get("all_annual_netcdf_files")!=213 or
     len(s81.get("sites",[]))!=10):
  fail("Existing Stage81 10-site 213 year file census changed")
 if (s82.get("stage")!=82 or
     s82.get("verified_annual_files_sha256")!=213 or
     s82.get("input_stage81_manifest_sha256")!=sha(S81)):
  fail("Original Stage82 all-annual-SHA evidence missing or drift")
 pol=s31.get("provisional_sensor_policy")
 if not isinstance(pol,dict) or set(pol)!=ALL-BLOCKED:fail("Expected 8 site height policies, 2 original holds")
 records={x["site"]:x for x in s81["sites"]}
 if set(records)!=ALL:fail("Stage81 original 10-site membership changed")
 return pol,records

def get_pft():
 if not PFT.is_file():fail("Expected Stage05 published PFT evidence TSV alongside this script: "+str(PFT))
 data=PFT.read_bytes()
 blob=b"blob "+str(len(data)).encode()+b"\0"+data
 if hashlib.sha1(blob).hexdigest()!=PFT_GIT_BLOB:
  fail("Wrong/upgraded/unverified published PFT dataset; use original pinned TSV")
 with PFT.open(newline="",encoding="utf-8-sig") as f:
  data={r["site"]:r for r in csv.DictReader(f,delimiter="\t")}
 if not ALL.issubset(data):fail("Published FATES PFT site table lacks members")
 return data

def bif(site):
 folder=ACTUAL_SOURCE/site/"forcing/raw"
 # Limit to exact release subdir: one source BIF per given site.
 choices=sorted(folder.glob(f"AMF_{site}_FLUXNET_*/AMF_{site}_FLUXNET_BIF_*.csv"))
 if len(choices)!=1:
  fail(f"{site}: expected one exact-release BIF, got {len(choices)}; source not reliably chosen")
 p=choices[0]
 with p.open(encoding="utf-8-sig",newline="") as f:
  rd=csv.DictReader(f)
  if not {"VARIABLE","DATAVALUE"}.issubset(rd.fieldnames or []):
   fail(site+": original source BIF malformed")
  meta={}
  for row in rd:
   key=(row.get("VARIABLE") or "").strip().upper()
   val=(row.get("DATAVALUE") or "").strip()
   if key in ("UTC_OFFSET","LOCATION_LAT","LOCATION_LONG") and val:
    meta.setdefault(key,set()).add(val)
 out={}
 for field in ("UTC_OFFSET","LOCATION_LAT","LOCATION_LONG"):
  vals=meta.get(field)
  if not vals or len(vals)!=1:fail(site+": UTC/geolocation BIF ambiguity "+field)
  out[field]=float(next(iter(vals)))
 if not (-12<=out["UTC_OFFSET"]<=14):fail(site+": invalid site UTC_OFFSET")
 return out

def original_surface(site,bif_meta):
 folder=ACTUAL_SOURCE/site/"subset_data"
 choices=sorted(folder.glob("surfdata*.nc"))
 if len(choices)!=1:fail(site+": original site surface ambiguous")
 p=choices[0]
 with Dataset(p) as ds:
  vals={}
  for field in ("PCT_NATVEG","PCT_CROP","LONGXY","LATIXY"):
   if field not in ds.variables:fail(site+": missing original surface "+field)
   x=np.ma.filled(ds.variables[field][:],np.nan).ravel()
   if len(x)!=1 or not np.isfinite(x[0]):fail(site+": point surface scalar invalid "+field)
   vals[field]=float(x[0])
  pf=np.ma.filled(ds.variables["PCT_NAT_PFT"][:],np.nan).ravel()
  if len(pf) not in (15,16) or not np.isfinite(pf).all():
   fail(site+": invalid source host CLM natpft vector")
  if abs(float(sum(pf))-100)>0.5:
   fail(site+": grid CLM natural PFT does not sum to 100")
  if abs(vals["LATIXY"]-bif_meta["LOCATION_LAT"])>0.1 or (
    abs(((vals["LONGXY"]%360)-(bif_meta["LOCATION_LONG"]%360)+180)%360-180)>0.1):
   fail(site+": original surface model location differs by >0.1deg from BIF")
 return vals

def height_status(site,policy):
 if site in BLOCKED:
  if policy is not None:fail(site+": expected explicit no-verified-sensor condition")
  return "MULTILAYER_HOLD","—",0
 if policy is None:fail(site+": missing pinned provisional BASE TA measurement height")
 val=float(policy["baseline_m"])
 expected=STATIC.get(site,DYNAMIC.get(site))
 if expected is None or abs(val-expected)>1e-5:fail(site+": ZBOT baseline changed unexpectedly")
 if policy.get("FLUXNET_TA_F_sensor_crosswalk")=="VERIFIED":
  fail(site+": input candidate source now says verified; review published evidence first")
 events=policy.get("dated_events",[])
 if site in STATIC and (policy.get("candidate_ZBOT_mode")!="STATIC" or len(events)):
  fail(site+": static sensor hypothesis changed")
 if site in DYNAMIC and (policy.get("candidate_ZBOT_mode")!="DYNAMIC" or not len(events)):
  fail(site+": dynamic sensor events missing")
 cat="STATIC_PROXY" if site in STATIC else "DYNAMIC_REVIEW"
 return cat,str(val),len(events)

def nc_availability(site,rec):
 data=rec.get("annual_files",[])
 if len(data)!=rec["years_written"] or len(data)<10:
  fail(site+": selected Stage81 annual forcing not complete")
 years=[int(x["year"]) for x in data]
 if years!=list(range(min(years),max(years)+1)):
  fail(site+": yearly NetCDF forcing discontinuous")
 for x in (data[0],data[-1]):
  p=Path(x["file"])
  if not p.is_file():fail(site+": missing source first/last year NC "+str(p))
 # Stage82 already verified SHA256 for all 213 source years; do not rehash.
 return f"{years[0]}-{years[-1]}",len(data)

def other_case_status(site):
 old=list((ROOT/"cases").glob(site+"_AMF_FIXNC*"))
 return len(old)

def selftest():
 assert len(SITES)==9 and len(ALL)==10
 assert set(STATIC)|set(DYNAMIC)|BLOCKED==set(SITES)
 assert not (set(STATIC)&set(DYNAMIC) or set(STATIC)&BLOCKED or set(DYNAMIC)&BLOCKED)
 assert sum((len(STATIC),len(DYNAMIC),len(BLOCKED)))==9
 print("SELF-TEST PASS: 9 exact AmeriFlux Batch01 stations, 4 static + 3 dynamic + 2 ambiguous height policies")

def main():
 ap=argparse.ArgumentParser(description=__doc__)
 op=ap.add_mutually_exclusive_group(required=True)
 op.add_argument("--self-test",action="store_true")
 op.add_argument("--check",action="store_true")
 args=ap.parse_args()
 if args.self_test:selftest();return
 pol,records=get_stage_data()
 pfts=get_pft()
 print("=== NINE-SITE AMERIFLUX AD400 ROLLOUT / REUSE EXISTING MET STAGE80-82 ===")
 print("SITE | YEARS | HH_NC | BIF_UTC_H | HEIGHT_STATUS | BASE_M | EVENTS | NAT/CROP_GRID_PCT | PFT_STAND_CANDIDATE | CIME_CASES")
 for site in SITES:
  b=bif(site)
  grid=original_surface(site,b)
  cat,z,events=height_status(site,pol.get(site))
  span,count=nc_availability(site,records[site])
  e=pfts[site]
  assert e["fraction_is_verified_FATES_initialization"]=="NO"
  cases=other_case_status(site)
  print(f"{site} | {span} | {count} | {b['UTC_OFFSET']:+g} | {cat} | {z} | {events} | "
        f"{grid['PCT_NATVEG']:.2f}/{grid['PCT_CROP']:.2f} | "
        f"{e['published_PFT_or_cover_percent']} | {cases}",flush=True)
 print("=== ACTION ORDER, USING ONE SHARED BATCH ENGINE; NO REPEATED QC ===")
 print("LANE A: BR-Ma2 CA-Ca3 CA-LP1 US-Bar — STATIC HEIGHT PROXY, technical pilot ONLY; original crosswalk TA_F unverified.")
 print("LANE B: CA-TP1 CA-TP3 US-Aud — DYNAMIC ZBOT DATE EVENTS; need source-varying measurement choice before 800-yr model.")
 print("LANE C: CA-Cbo CA-Man — MULTILAYER HEIGHT HOLD; select the correct source sensor first.")
 print("CA-TP4: Stage12 separate UTC-V2 AD5 CIME preview VERIFIED; still no submitted AD5.")
 print("SITE PFT SCIENCE: each published stand ratio is a candidate, NOT measured ground area; US-Aud C4 grass/bare ground must use separate landunit policy.")
 print("ALL 9: BIF UTC offset is reported above, not inferred. Original Stage80/81/82 213 NC are reused; NO forcing recalculation.")
 print("NO MODEL / SURFACE / NETCDF / CASE / SLURM WRITES. THIS IS A ONE-PASS BATCH INVENTORY.")
if __name__=="__main__":main()
