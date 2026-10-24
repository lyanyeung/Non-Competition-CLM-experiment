#!/usr/bin/env python3
"""Stage04, CA-TP4 only. Prepare an ISOLATED TECHNICAL DATM PILOT, not AD400.

Evidence-driven independent transformations from Stage81:
  FLUXNET HH TIMESTAMP_START + TIMESTAMP_END => interval midpoint +15 minutes;
  optional experimental ZBOT=28 m FROM BASE TA_PI_F_1_1_1; sensor crosswalk
  with consolidated FLUXNET TA_F is UNVERIFIED. An explicit command flag is
  required before preview writes.

Outputs: 22 yearly copied NetCDFs (do not alter 213 original files), a detached
true CIME/CDEPS <file><stream_info> stream XML cloned from an existing CH-Dav
*CONFIGURATION REFERENCE*, and SHA+scientific-caveat manifest. No case setup,
no enabling streams, no Slurm, no scientific approval. All other supporting
global CDEPS streams are preserved as template references, not imported
as site-representative data.

--self-test: pure assertions
--check: exact all-record CA-TP4 half-hour Stage80-to-raw-FLUXNET clock audit,
         22-year source file SHA validation, reference stream/NC schema test;
         no writes
--build-preview --outdir NEW_DIR --ack-provisional-height:
         repeat --check then copy only the CA-TP4 NCs to a new directory,
         add ZBOT=28m as TEST ASSUMPTION, shift time to FLUXNET midpoint,
         create DETACHED site-specific candidate datm.streams.xml.
"""
from __future__ import annotations
import argparse,csv,hashlib,json,shutil,xml.etree.ElementTree as ET
from datetime import datetime,timedelta,timezone
from pathlib import Path

BASE=Path("/iridisfs/scratch/ly3n24/CLM_FATES")
AMF=BASE/"experiments/AmeriFlux_MultiSite_10"
S80=AMF/"reports/stage80_RH_lt1_final_20261024T123353Z"
S81=AMF/"reports/stage81_DATM_technical_20261024T162235Z"
S82=AMF/"reports/stage82_DATM_case_integration_preflight_20261024T231124502670Z"
RAW=BASE/"sites/MY_EC_SITE/CA-TP4/forcing/raw/AMF_CA-TP4_FLUXNET_2002-2023_v1.3_r1/AMF_CA-TP4_FLUXNET_FLUXMET_HH_2002-2023_v1.3_r1.csv"
REFERENCE=BASE/"cases/CH-Dav_B01_FIXNC_AD400"
EXPECTED_YEARS=list(range(2002,2024))
ZBOT_PILOT=28.0
MET_MAP={
 "PRECTmms":"Faxa_precn","FSDS":"Faxa_swdn","ZBOT":"Sa_z",
 "TBOT":"Sa_tbot","WIND":"Sa_wind","QBOT":"Sa_shum",
 "PSRF":"Sa_pbot","FLDS":"Faxa_lwdn"}
REQUIRED_META={'time','TBOT','QBOT','PSRF','FSDS','FLDS','WIND','PRECTmms'}

def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()

def load_json(p):
 if not p.is_file():raise RuntimeError("Missing pinned previous stage manifest "+str(p))
 return json.loads(p.read_text(encoding="utf-8"))

def parse_start(st):
 return datetime.strptime(st,"%Y%m%d%H%M")

def source_clock_audit(source):
 if not RAW.is_file():raise RuntimeError("Missing exact original HH CSV "+str(RAW))
 expected=0;raw_skipped=0
 with source.open(encoding='utf-8-sig',newline='') as i,RAW.open(encoding='utf-8-sig',newline='') as r:
  x=csv.DictReader(i);y=csv.DictReader(r)
  if not {"time"}.issubset(x.fieldnames or []) or not {"TIMESTAMP_START","TIMESTAMP_END"}.issubset(y.fieldnames or []):
   raise RuntimeError("Expected explicit original HH start/end and selected Stage80 time")
  originals=iter(y)
  for source_row in x:
   row=next(originals,None)
   while row is not None and row["TIMESTAMP_START"][4:8]=="0229":
    raw_skipped+=1
    row=next(originals,None)
   if row is None:raise RuntimeError("Raw FLUXNET ended early at "+str(expected))
   stamp=parse_start(row["TIMESTAMP_START"])
   end=parse_start(row["TIMESTAMP_END"])
   if end-stamp!=timedelta(minutes=30):
    raise RuntimeError("Raw HH interval not exactly 30 minutes: "+str(stamp))
   if source_row["time"]!=stamp.strftime("%Y-%m-%d %H:%M:%S"):
    raise RuntimeError("Stage80 selected time differs from native TIMESTAMP_START: "+repr((source_row["time"],row["TIMESTAMP_START"])))
   if stamp.month==2 and stamp.day==29:
    raise RuntimeError("NOLEAP skipped Feb29 still in selected forcing")
   expected+=1
  for row in originals:
   if row["TIMESTAMP_START"][4:8]=="0229":
    raw_skipped+=1
   else:raise RuntimeError("Raw FLUXNET has extra non-Feb29 interval "+row["TIMESTAMP_START"])
 if expected!=len(EXPECTED_YEARS)*17520:
  raise RuntimeError("Wrong source record count "+str(expected))
 print("RAW FLUXNET -> STAGE80 CLOCK EXACT MATCH:",expected,"half-hour intervals;",
       "skipped leap-day rows:",raw_skipped)
 print("TIME BASIS: source TIMESTAMP_START labels match Stage80; proposed netCDF time=START+15m as interval midpoint")
 return expected,raw_skipped

def inputs():
 a=load_json(S81/"manifest.json")
 b=load_json(S82/"manifest.json")
 c=load_json(S80/"manifest.json")
 if (a.get("stage")!=81 or a.get("all_annual_netcdf_files")!=213 or
     b.get("stage")!=82 or b.get("verified_annual_files_sha256")!=213 or
     c.get("stage")!=80 or c.get("native_ERA5_joint_replaced_rows")!=18):
  raise RuntimeError("Stage80/81/82 provenance changed")
 if sha(S81/"manifest.json")!=b["input_stage81_manifest_sha256"]:
  raise RuntimeError("Stage82 no longer references Stage81")
 if sha(S80/"manifest.json")!=a["stage80_receipt_sha256"]:
  raise RuntimeError("Stage81 no longer references Stage80")
 v=[s for s in a["sites"] if s["site"]=="CA-TP4"]
 if len(v)!=1 or len(v[0]["annual_files"])!=22:raise RuntimeError("CA-TP4 22-year record missing")
 source=Path(v[0]["forcing_path"])
 if sha(source)!=v[0]["forcing_sha256"]:raise RuntimeError("CA-TP4 final forcing source altered")
 files=[]
 for expect,f in zip(EXPECTED_YEARS,v[0]["annual_files"]):
  p=Path(f["file"])
  if int(f["year"])!=expect or p!=S81/"CA-TP4"/"yearly"/f"{expect:04d}.nc":
   raise RuntimeError("Wrong-year or wrong-directory Stage81 CA-TP4 file")
  if not p.is_file() or sha(p)!=f["sha256"]:
   raise RuntimeError("CA-TP4 annual NetCDF checksum drift "+str(p))
  files.append((expect,p))
 return source,files

def reference_fields(nc):
 import numpy as np
 from netCDF4 import Dataset
 xml=REFERENCE/"CaseDocs/datm.streams.xml"
 if not xml.is_file():raise RuntimeError("Original complete CIME case stream XML missing")
 tree=ET.parse(xml)
 root=tree.getroot()
 streams=[s for s in root.iter("stream_info") if s.attrib.get("name","").startswith("CLM_USRDAT.")]
 if len(streams)!=1:raise RuntimeError("Need exactly one 1PT main met stream in original reference")
 st=streams[0]
 for key,val in (("taxmode","cycle"),("tintalgo","linear"),("mapalgo","none")):
  obj=st.find(key)
  if obj is None or (obj.text or "").strip()!=val:
   raise RuntimeError("Reference DATM stream "+key+" differs from pinned expectation")
 datavars=st.find("datavars")
 datafiles=st.find("datafiles")
 if datavars is None or datafiles is None:
  raise RuntimeError("Reference stream lacks datavars or datafiles")
 original_map={}
 for v in datavars:
  bits=(v.text or "").split()
  if len(bits)!=2:raise RuntimeError("Unexpected CDEPS datavars element "+ET.tostring(v,encoding="unicode")[:200])
  original_map[bits[0]]=bits[1]
 if any(original_map.get(k)!=v for k,v in MET_MAP.items()):
  raise RuntimeError("Effective CDEPS stream main met mapping changed; inspect manually")
 reference_nc=Path(next(iter(datafiles)).text.strip())
 if not reference_nc.is_file():raise RuntimeError("Reference CH-Dav NetCDF not found "+str(reference_nc))
 with Dataset(reference_nc) as orig:
  if "ZBOT" not in orig.variables:
   raise RuntimeError("Reference forcing lacks ZBOT: cannot confirm shape")
  expected_shape=orig.variables["ZBOT"].dimensions
  dims=orig.variables["QBOT"].dimensions
  if expected_shape!=dims:
   raise RuntimeError("Reference ZBOT/QBOT shape mismatch")
  ref_axes={"ZBOT_dims":expected_shape,
            "reference_dimensions":{k:len(v) for k,v in orig.dimensions.items()},
            "reference_ZBOT_units":getattr(orig.variables["ZBOT"],"units","UNKNOWN")}
  print("REFERENCE NETCDF DIMENSIONS:",ref_axes)
 return tree,root,st,ref_axes,sha(xml)

def inspect_nc(files,expected_dims):
 from netCDF4 import Dataset
 import numpy as np
 for year,p in files:
  with Dataset(p) as ds:
   v=ds.variables["time"]
   if v.calendar!="noleap" or len(ds.dimensions["time"])!=17520:
    raise RuntimeError("Stage81 NOLEAP yearly time unexpected "+str(p))
   if "ZBOT" in ds.variables:raise RuntimeError("Original Stage81 unexpectedly contains ZBOT")
   if not REQUIRED_META.issubset(ds.variables):
    raise RuntimeError("Missing input meteorology vars "+str(year))
   for key in ("QBOT","TBOT","FSDS","PSRF","WIND"):
    if ds.variables[key].dimensions!=expected_dims:
     raise RuntimeError("CDEPS reference field dimensions incompatible: "+key+" "+str(year)+" vs "+str(expected_dims))
   values=v[:]
   expected=np.arange(17520,dtype="float64")/48.0
   if not np.allclose(values,expected,atol=1e-9,rtol=0):
    raise RuntimeError("Stage81 per-year native time index not recognized "+str(year))
 print("ALL 22 CA-TP4 NC DIMENSIONS AND NATIVE CLOCK: PASS")

def build_preview(out,files,ref,original,year_count):
 import numpy as np
 from netCDF4 import Dataset
 out=out.resolve()
 if out.exists():raise RuntimeError("Never overwrite a directory: "+str(out))
 out.mkdir(parents=True)
 yearly=out/"CA-TP4"/"yearly"
 yearly.mkdir(parents=True)
 written=[]
 for year,original_nc in files:
  dest=yearly/f"{year:04d}.nc"
  shutil.copy2(original_nc,dest)
  with Dataset(dest,"r+") as ds:
   time=ds.variables["time"]
   time[:]=np.arange(17520,dtype="float64")/48.0+(15.0/1440.0)
   time.long_name="FLUXNET HH interval MIDPOINT in local standard time (TIMESTAMP_START + 15 minutes)"
   if "ZBOT" in ds.variables:raise RuntimeError("Unexpected ZBOT present in copied original")
   z=ds.createVariable("ZBOT","f8",ds.variables["QBOT"].dimensions,
                       zlib=True,complevel=2)
   z.units="m";z.long_name="PROVISIONAL fixed tower TA_PI_F_1_1_1 height; not verified crosswalk to TA_F"
   z[:]=np.full(ds.variables["QBOT"].shape,ZBOT_PILOT,dtype="float64")
   ds.ca_tp4_zbot_evidence="BASE 2026-09-08 TA_PI_F_1_1_1 28m; FLUXNET TA_F sensor provenance UNVERIFIED"
   ds.interval_midpoint_shift_minutes=15
   ds.source_stage81_sha256=sha(original_nc)
   ds.science_release="PROVISIONAL_AD5_SMOKE_TECHNICAL_PREVIEW_ONLY"
  with Dataset(dest) as ds:
   if not np.allclose(ds.variables["time"][[0,1,-1]],
                      [1/96,1/48+1/96,17519/48+1/96],atol=1e-10,rtol=0):
    raise RuntimeError("Midpoint readback failure "+str(year))
   if not np.all(ds.variables["ZBOT"][:]==28.0):
    raise RuntimeError("Pilot ZBOT readback failure "+str(year))
   for key in REQUIRED_META-{"time"}:
    if key not in ds.variables:raise RuntimeError("Lost forcing input "+key)
  written.append({"year":year,"path":str(dest),"sha256":sha(dest),"stage81_original_sha256":sha(original_nc)})
  print("PILOT NETCDF CHECK PASS",year,flush=True)
 tree,root,stream,dimensions,ref_sha=ref
 stream.find("year_first").text=str(EXPECTED_YEARS[0])
 stream.find("year_last").text=str(EXPECTED_YEARS[-1])
 stream.find("year_align").text=str(EXPECTED_YEARS[0])
 for x in list(stream.find("datafiles")):stream.find("datafiles").remove(x)
 for y in EXPECTED_YEARS:
  # preserve original <file> node names from CDEPS.
  ET.SubElement(stream.find("datafiles"),"file").text=str(yearly/f"{y:04d}.nc")
 stream.find("taxmode").text="cycle"
 stream.find("tintalgo").text="linear"
 stream.find("offset").text="0"
 target_xml=out/"CA-TP4"/"datm.streams.CA-TP4.CANDIDATE_NOT_ACTIVATED.xml"
 tree.write(target_xml,encoding="utf-8",xml_declaration=True)
 with ET.parse(target_xml) as tree_read:
  st=next(s for s in tree_read.iter("stream_info") if s.attrib.get("name","").startswith("CLM_USRDAT."))
  assert len(st.find("datafiles"))==22
  assert st.find("year_first").text=="2002" and st.find("year_last").text=="2023"
 manifest={
  "stage":"AMERIFLUX_AD400_DATM_CA_TP4_PILOT_STAGE04",
  "source_stage80_selected_sha256":sha(S80/"10_site_selected_forcing_sources.tsv"),
  "source_stage81_manifest_sha256":sha(S81/"manifest.json"),
  "source_stage82_manifest_sha256":sha(S82/"manifest.json"),
  "reference_real_CIME_stream_sha256":ref_sha,
  "reference_effective_datm_mode":"1PT;CDEPS_file_stream_info;cycle;linear",
  "source_original_selected_forcing_sha256":sha(original),
  "source_raw_fluxnet_HH_sha256":sha(RAW),
  "site":"CA-TP4","modified_stage81_files":False,"annual_netcdf_files":22,
  "time_policy":"FLUXNET TIMESTAMP_START+15MIN LOCAL_STANDARD midpoint; verified every original source interval before build",
  "height_m":28.0,"height_evidence":"BASE TA_PI_F_1_1_1; static; no date events",
  "TA_F_source_sensor_verified":False,
  "height_approval":"EXPLICIT PROVISIONAL PROXY FOR SMOKE ONLY; NOT OBSERVATIONAL SCIENCE RELEASE",
  "DATM_stream":"DETACHED XML CANDIDATE; NOT INSTALLED IN ACTUAL CASE",
  "model_case_created":False,"Slurm_submitted":False,"production_release":False,
  "remaining_gates":["Case native stream placement / build_namelist and CDEPS preview",
                     "Local standard solar time relative to longitude/coupler calendar",
                     "TA_F crosswalk/height instrument and actual wind measurement height",
                     "CA-TP4 actual PFT, landunit and soil input, FATES executable/params",
                     "site-appropriate domain, no accidental re-use of CH-Dav inputs",
                     "CO2 spinup baseline and annual forcing cycle with 5-year AD smoke first"],
  "stream_candidate":{"path":str(target_xml),"sha256":sha(target_xml)},
  "files":written}
 (out/"manifest.json").write_text(json.dumps(manifest,indent=2)+"\n",encoding="utf-8")
 print("PILOT DATM CANDIDATE COMPLETE:",out)
 print("22 NC MIDPOINT/ZBOT-28m CANDIDATES; stream clone NOT ACTIVATED; original Stage81 NC unchanged.")
 print("NO CIME CASE, CIME INPUT OR SLURM MODIFICATION.")

def selftest():
 assert len(EXPECTED_YEARS)==22
 assert set(MET_MAP)=={"PRECTmms","FSDS","ZBOT","TBOT","WIND","QBOT","PSRF","FLDS"}
 assert parse_start("200201010000")+timedelta(minutes=30)==parse_start("200201010030")
 assert 15/1440==1/96
 print("SELF-TEST PASS: 22 annual files, exact 8-source-to-DATM mapping, midpoint+15min; explicit 28m pilot only")

def main():
 p=argparse.ArgumentParser(description=__doc__)
 q=p.add_mutually_exclusive_group(required=True)
 q.add_argument("--self-test",action="store_true")
 q.add_argument("--check",action="store_true")
 q.add_argument("--build-preview",action="store_true")
 p.add_argument("--outdir",type=Path)
 p.add_argument("--ack-provisional-height",action="store_true")
 args=p.parse_args()
 if args.self_test:selftest();return
 if args.build_preview and (not args.ack_provisional_height or args.outdir is None):
  p.error("--build-preview requires --outdir NEW_DIR --ack-provisional-height")
 if args.check and (args.outdir is not None or args.ack_provisional_height):
  p.error("--check takes no output/approval flags")
 source,files=inputs()
 clock_rows,skipped=source_clock_audit(source)
 ref=reference_fields(None)
 inspect_nc(files,ref[3]["ZBOT_dims"])
 print("PREFLIGHT: 10-site Stage81 left unchanged; CA-TP4 raw time START match verified.")
 print("REFERENCE CDEPS mode: cycle/linear; QBOT -> Sa_shum; ZBOT -> Sa_z.")
 print("CA-TP4 ZBOT=28m TA_PI_F_1_1_1 is a PROXY, NOT proven FLUXNET TA_F crosswalk.")
 if args.check:
  print("CHECK PASS: NO WRITES; could build 22 independent technical pilot NCs with explicit proxy acknowledgment.")
  return
 build_preview(args.outdir,files,ref,source,clock_rows)

if __name__=="__main__":main()
