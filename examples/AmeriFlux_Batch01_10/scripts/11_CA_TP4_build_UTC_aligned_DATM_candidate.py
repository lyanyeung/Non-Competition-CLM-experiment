#!/usr/bin/env python3
"""Stage11: UTC-aligned CA-TP4 CDEPS 22-year forcing CANDIDATE, no CIME/Slurm.

Original Stage04 native NetCDF: 00:15 on 2002-Jan-01 represents
2002-Jan-01 00:15 local standard time (UTC-5); local-time solar phase
was confirmed by Stage10 2002/2010/2019 observed FSDS night-energy test.
CTSM's solar hour angle is calculated from UTC midnight and longitude:
https://escomp.github.io/CTSM/release-clm5.0/tech_note/Surface_Albedos/CLM50_Tech_Note_Surface_Albedos.html
CDEPS streams offset positive shifts source time forward in seconds:
https://escomp.github.io/CDEPS/versions/master/html/streams.html

For deterministic yearly files in a whole-year NOLEAP 22-year CDEPS cycle,
we DO NOT merely add offset=+18000 to the existing stream (would move
time endpoints beyond annual boundaries). Instead, NEW UTC-year files keep
00:15,00:45,...,23:45 UTC times and shift ALL MET data by exactly 10 HH
source slots across year boundaries:
  UTC year y slots [0..9] <- prior source year's final 10 LST slots;
  UTC year y slots [10..17519] <- current source year LST [0..17509].
  2002 preceding source year is 2023, as the input 22-yr cycle wraps.
  2023 last UTC slot then flows to 2002 first UTC slot, preserving
  the 5-hour physical continuity of the repeated 22-year input sequence.
This is a TECHNICAL CYCLE BOUNDARY assumption, not an observation in 2001.

--self-test  NumPy cyclic index/time unit checks, no filesystem changes
--check      PINNED Stage04 originals, Stage08 case receipt, boundary plan;
             no writes, no CIME changes
--build-preview --outdir BRAND_NEW --ack-cyclic-utc-5-shift
             verify first, then write only independent 22 NC and detached XML
             with cycle/linear, offset=0, 2002-2023. No case setup/submission.

Original Stage04/Stage06/Stage08 files remain unmodified. This new product
is not authorized for scientific simulation without separately validating
actual model/coupler grid geometry, solar convention, CO2 and stand/soil.
"""
from __future__ import annotations
import argparse,hashlib,json,shutil,xml.etree.ElementTree as ET
from pathlib import Path
import numpy as np
from netCDF4 import Dataset

B=Path("/iridisfs/scratch/ly3n24/CLM_FATES")
SRC=B/"experiments/AmeriFlux_MultiSite_10/reports/stage04_CA_TP4_DATM_PILOT_20261025T054800121260846_Z"
ROOT=B/"experiments/NonCompetitionObserved22/AmeriFlux_Batch01_10/CA-TP4"
STATE=ROOT/"stage08_CA_TP4_AD5_CASE_PREVIEW_ATTEMPT.json"
CASE=B/"cases/CA-TP4_AMF_FIXNC_AD400_PILOT"
YEARS=list(range(2002,2024))
HH=17520
SHIFT=10
CORE={"TBOT","FSDS","FLDS","PRECTmms","WIND","PSRF","QBOT","SHUM","ZBOT","RH"}
DETACHED=SRC/"CA-TP4/datm.streams.CA-TP4.CANDIDATE_NOT_ACTIVATED.xml"

def sha(p):
 h=hashlib.sha256()
 with p.open("rb") as f:
  for b in iter(lambda:f.read(1<<20),b""):h.update(b)
 return h.hexdigest()

def no(msg):raise RuntimeError(str(msg))

def loads(p):
 if not p.is_file():no("Missing source "+str(p))
 return json.loads(p.read_text(encoding="utf8"))

def files_and_receipts():
 manifest=loads(SRC/"manifest.json")
 receipt=loads(STATE)
 if (manifest.get("site")!="CA-TP4" or
     manifest.get("annual_netcdf_files")!=22 or
     manifest.get("height_m")!=28. or
     manifest.get("TA_F_source_sensor_verified") is not False or
     manifest.get("production_release") is not False):
  no("Stage04 technical-science flags changed")
 if (receipt.get("state")!="PREVIEW_VERIFIED_NOT_SUBMITTED" or
     receipt.get("model_jobs_submitted") is not False or
     receipt.get("ready_to_submit_AD5") is not False or
     receipt.get("stage04_met_manifest_sha256")!=sha(SRC/"manifest.json")):
  no("Stage08 new case is changed/submitted or no longer references Stage04")
 for key,fn in (("CIME_generated_datm_stream_xml_sha256","datm.streams.xml"),
                ("CIME_generated_lnd_in_sha256","lnd_in")):
  if sha(CASE/"CaseDocs"/fn)!=receipt[key]:no("Stage08 CaseDocs changed "+fn)
 if (CASE/"env_case.xml").read_bytes()!=(CASE/"LockedFiles/env_case.xml").read_bytes():
  no("Stage08 CIME case lock modified")
 items=manifest.get("files",[])
 if len(items)!=22:no("Missing 22 year entries")
 files={}
 for y,item in zip(YEARS,items):
  p=SRC/"CA-TP4/yearly"/f"{y}.nc"
  if item["year"]!=y or Path(item["path"])!=p or sha(p)!=item["sha256"]:
   no("Original source SHA/year mismatch "+str(y))
  files[y]=p
 if sha(DETACHED)!=manifest["stream_candidate"]["sha256"]:
  no("Original detached CDEPS XML checksum drift")
 return manifest,receipt,files

def check_schema(files):
 fields=None
 for y in YEARS:
  with Dataset(files[y]) as nc:
   t=nc.variables["time"]
   if len(t)!=HH or t.calendar!="noleap" or not np.allclose(
     t[[0,1,HH-1]],[1/96,1/48+1/96,(HH-1)/48+1/96],
     atol=1e-11,rtol=0):
    no("Original noleap midpoint time changed "+str(y))
   vals={name for name,v in nc.variables.items() if
         len(v.dimensions)>0 and v.dimensions[0]=="time" and name!="time"}
   if not CORE.issubset(vals) or (fields is not None and vals!=fields):
    no("Unexpected or changing time-dependent met fields "+str(y))
   if any(nc.variables[name].shape[0]!=HH for name in vals):
    no("Unexpected met time dimension "+str(y))
   fields=vals
 return sorted(fields)

def prior_year(y):
 return y-1 if y>YEARS[0] else YEARS[-1]

def index_transform(year):
 # Explicit full-year cyclic index mapping, bijective across all 22 years.
 return [(prior_year(year),HH-SHIFT+i) if i<SHIFT
         else (year,i-SHIFT) for i in range(HH)]

def selftest():
 assert prior_year(2002)==2023 and prior_year(2003)==2002
 assert index_transform(2002)[0]==(2023,HH-10)
 assert index_transform(2002)[9]==(2023,HH-1)
 assert index_transform(2002)[10]==(2002,0)
 assert index_transform(2023)[-1]==(2023,HH-11)
 allindexes={k for y in YEARS for k in index_transform(y)}
 assert len(allindexes)==22*HH
 print("SELF-TEST PASS: unique 385440 HH UTC slots, 10-record UTC-5 shift, cyclic 2023->2002 wrap")

def validate_xml():
 root=ET.parse(DETACHED).getroot()
 matches=[x for x in root.iter("stream_info") if
          x.attrib.get("name")=="CLM_USRDAT.UNSET"]
 if len(matches)!=1:no("Unexpected CDEPS met stream")
 m=matches[0]
 for k,v in (("year_first","2002"),("year_last","2023"),("year_align","2002"),
             ("taxmode","cycle"),("tintalgo","linear"),("offset","0")):
  a=m.find(k)
  if a is None or (a.text or "").strip()!=v:
   no("Unexpected source CDEPS stream "+k)
 return root,m

def check():
 m,r,files=files_and_receipts()
 names=check_schema(files)
 validate_xml()
 print("STAGE11 INPUT PASS: 22 pristine source years, Stage08 original CaseDocs and lock, effective technical stream")
 print("FIELDS TO UTC-SHIFT:",",".join(names))
 print("SITE UTC_OFFSET=-5.0h; SHIFT=10 x 30min later relative to source LOCAL time")
 print("UTC 2002 Jan-01 00:15 <- LOCAL 2023 Dec-31 19:15 (forcing loop boundary)")
 print("UTC 2002 Jan-01 05:15 <- LOCAL 2002 Jan-01 00:15")
 print("UTC 2023 Dec-31 23:45 <- LOCAL 2023 Dec-31 18:45")
 print("TOTAL UTC HALF-HOURS:",22*HH,"one-to-one cyclic permutation")
 print("CIME CASE CURRENTLY REFERENCES STAGE04 LOCAL-TIME FILES; NO MODEL CHANGE.")
 print("READ-ONLY CHECK PASS. New UTC copies require explicit --ack-cyclic-utc-5-shift.")
 return files,names,m

def equal(a,b):
 x=np.ma.asarray(a)
 y=np.ma.asarray(b)
 if not np.array_equal(np.ma.getmaskarray(x),np.ma.getmaskarray(y)):
  return False
 if x.dtype.kind in "fc" and y.dtype.kind in "fc":
  return np.array_equal(np.ma.filled(x,0),np.ma.filled(y,0),equal_nan=True)
 return np.array_equal(np.ma.filled(x),np.ma.filled(y))

def output_nc(dest,orig,prev,names):
 shutil.copy2(orig,dest)
 with Dataset(orig) as now,Dataset(prev) as preceding,Dataset(dest,"r+") as utc:
  for name in names:
   p=preceding.variables[name]
   s=now.variables[name]
   d=utc.variables[name]
   if p.dimensions!=d.dimensions or s.dimensions!=d.dimensions:
    no("Incompatible source variable dimensions "+name)
   d[:SHIFT,...]=p[HH-SHIFT:HH,...]
   d[SHIFT:HH,...]=s[:HH-SHIFT,...]
  utc.time_reference="UTC_NOLEAP_MIDPOINT_PLUS5_HOURS_FROM_FLUXNET_UTC_MINUS5"
  utc.time_boundary_policy="WHOLE_22_YEAR_CYCLIC_UTC_SHIFT;FIRST_2002_SLOTS_FROM_2023_LST_FINAL_5H"
  utc.provisional_ZBOT_m=28.0
  utc.science_release="TECHNICAL_UTC_DATM_CANDIDATE_NOT_ACTIVATED"
 with Dataset(orig) as now,Dataset(prev) as preceding,Dataset(dest) as utc:
  for name in names:
   d=utc.variables[name]
   if not equal(d[:SHIFT,...],preceding.variables[name][HH-SHIFT:HH,...]):
    no("UTC first 10 slots incorrectly shifted "+name)
   if not equal(d[SHIFT:HH,...],now.variables[name][:HH-SHIFT,...]):
    no("UTC remaining slots incorrectly shifted "+name)
  if not equal(utc.variables["time"][:],now.variables["time"][:]):
   no("UTC midpoint time coordinate was accidentally changed")

def create(out,files,names,manifest):
 out=out.expanduser().resolve()
 if out.exists() or out.is_symlink():
  no("Refuse existing UTC candidate output "+str(out))
 (out/"CA-TP4/yearly").mkdir(parents=True,exist_ok=False)
 saved=[]
 for y in YEARS:
  src=files[y]
  target=out/"CA-TP4/yearly"/f"{y}.nc"
  output_nc(target,src,files[prior_year(y)],names)
  saved.append(dict(year=y,path=str(target),sha256=sha(target),
                    stage04_source_sha256=sha(src),
                    previous_local_source_year=prior_year(y)))
  print("UTC SOURCE INTEGRITY PASS",y,flush=True)
 root,stream=validate_xml()
 files_xml=stream.find("datafiles")
 if files_xml is None:no("No source CDEPS datafiles")
 for el in list(files_xml):files_xml.remove(el)
 for e in saved:
  ET.SubElement(files_xml,"file").text=e["path"]
 stream.find("offset").text="0"
 xml=out/"CA-TP4/datm.streams.CA-TP4.UTC_CANDIDATE_NOT_ACTIVATED.xml"
 ET.ElementTree(root).write(xml,encoding="utf-8",xml_declaration=True)
 reparse=ET.parse(xml).getroot().find("stream_info")
 if len(reparse.find("datafiles"))!=22 or reparse.find("offset").text!="0":
  no("UTC detached CDEPS stream readback failed")
 note={
  "stage":11,"site":"CA-TP4","base_utc_offset_hours":-5,
  "n_years":22,"annual_samples":17520,"total_samples":22*17520,
  "source_stage04_manifest_sha256":sha(SRC/"manifest.json"),
  "source_case_stage08_unchanged":True,
  "source_clock":"FLUXNET_SITE_LST_UTC_MINUS5",
  "target_clock":"UTC_NOLEAP_HALF_HOUR_MIDPOINT",
  "shift_halfhours":10,"shift_seconds":18000,"stream_offset_seconds":0,
  "time_coordinate_edit":False,
  "cyclic_boundary":"2002_UTC_first_10_samples_from_2023_LST_final_10",
  "science_scope":"PROVISIONAL_ZBOT28M_ENF93_DBF7_GRIDSOIL_TECHNICAL_ONLY",
  "model_case_created":False,"model_case_modified":False,
  "slurm_submitted":False,"production_release":False,
  "model_CO2_2002_choice_applied":False,
  "model_solar_clock_runtime_verified":False,
  "pilot_nc":saved,
  "detached_CDEPS_stream_path":str(xml),
  "detached_CDEPS_stream_sha256":sha(xml)}
 (out/"manifest.json").write_text(json.dumps(note,indent=2)+"\n",encoding="utf-8")
 print("STAGE11 UTC PILOT COMPLETED:",out)
 print("CIME/SLURM UNCHANGED; original Stage04 NetCDF checksums unchanged")

def main():
 ap=argparse.ArgumentParser(description=__doc__)
 g=ap.add_mutually_exclusive_group(required=True)
 g.add_argument("--self-test",action="store_true")
 g.add_argument("--check",action="store_true")
 g.add_argument("--build-preview",action="store_true")
 ap.add_argument("--outdir",type=Path)
 ap.add_argument("--ack-cyclic-utc-5-shift",action="store_true")
 a=ap.parse_args()
 if a.self_test:selftest();return
 if a.check and (a.outdir is not None or a.ack_cyclic_utc_5_shift):
  ap.error("--check accepts neither output nor acknowledgment")
 if a.build_preview and (a.outdir is None or not a.ack_cyclic_utc_5_shift):
  ap.error("--build-preview needs --outdir BRAND_NEW --ack-cyclic-utc-5-shift")
 files,names,m=check()
 if a.check:return
 create(a.outdir,files,names,m)

if __name__=="__main__":main()
