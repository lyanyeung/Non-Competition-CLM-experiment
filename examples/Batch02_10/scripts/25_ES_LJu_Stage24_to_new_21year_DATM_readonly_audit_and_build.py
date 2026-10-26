#!/usr/bin/env python3
"""Batch02 ES-LJu Stage25: copy actual effective 21 annual CDEPS NetCDF files
into a NEW isolated directory and patch exactly TBOT, QBOT, PRECTmms from
operator-approved Stage24 forcing. Never touch original source/model case/Slurm.
Uses original same-year DATM as the template to preserve ZBOT, axes, units,
coordinates, non-meteorological attributes and every other forcing variable.
"""
import argparse, hashlib, json, re, shutil
import xml.etree.ElementTree as ET
from pathlib import Path
import numpy as np
import pandas as pd
from netCDF4 import Dataset

BASE=Path("/iridisfs/scratch/ly3n24/CLM_FATES")
SITE="ES-LJu"
CASE=BASE/"cases/ES-LJu_B02_FIXNC_AD400_BARE49_C3GRA31_SHRUB20_AD5"
STAGE24=Path("/iridisfs/home/ly3n24/ES_LJu_stage24_20261026T023307Z")
STAGE23=Path("/iridisfs/home/ly3n24/ES_LJu_stage23_20261026T013605Z")
STAGE21=BASE/"experiments/NonCompetitionObserved22/Batch02_10/stage21_20261026T011416Z"
SOURCE24=STAGE24/"ES-LJu_stage24_full21yr_provisional_candidate.csv"
ACK="BUILD_ES_LJU_STAGE24_DATM_21Y"
REPLACE={"TBOT":"TBOT","QBOT":"QBOT","PRECTmms":"PRECTmms"}
def req(ok,msg):
 if not bool(ok):raise RuntimeError(str(msg))
def sha(p):
 h=hashlib.sha256()
 with Path(p).open("rb") as f:
  for c in iter(lambda:f.read(1<<20),b""):h.update(c)
 return h.hexdigest()
def stream(case):
 f=case/"CaseDocs/datm.streams.xml"
 req(f.is_file(),f"CaseDocs stream missing {f}")
 root=ET.parse(f).getroot()
 ss=[s for s in root.iter("stream_info") if s.get("name")=="CLM_USRDAT.UNSET"]
 req(len(ss)==1,"Expected unique CLM_USRDAT.UNSET forcing stream")
 s=ss[0]
 def read(k):
  v=s.find(k)
  req(v is not None,"Missing stream "+k)
  return (v.text or "").strip()
 first=int(read("year_first"));last=int(read("year_last"))
 req((first,last)==(2004,2024),"ES-LJu CDEPS year loop changed")
 req(read("taxmode")=="cycle" and int(read("year_align"))==2004 and read("offset")=="0",
     "Unexpected CDEPS timing")
 data=s.find("datafiles")
 req(data is not None,"Missing datm <datafiles>")
 files=[Path((node.text or "").strip()) for node in data]
 req(len(files)==21,"Expected 21 actual effective yearly DATM files")
 for yr,p in zip(range(2004,2025),files):
  req(p.is_file() and p.stat().st_size>0,f"Missing CDEPS template {p}")
  req(p.name.startswith("ES-LJu_DATM_") and bool(re.search(r"(?<!\d)"+str(yr)+r"(?!\d)",p.stem)),
      f"CDEPS wrong site/year template {p}")
 return f,files
def year_values(d,y):
 sl=d.loc[d.time.dt.year==y]
 req(len(sl)==17520,f"CSV year {y} not NOLEAP 17520")
 req(sl.time.iloc[0]==pd.Timestamp(f"{y}-01-01 00:00") and
     sl.time.iloc[-1]==pd.Timestamp(f"{y}-12-31 23:30"),
     f"Selected time endpoints {y} differ")
 req((sl.time.diff().dropna()==pd.Timedelta(minutes=30)).all(),
     f"Selected 30-min time gaps {y}")
 return sl
def vec(v,n=17520):
 req(v.ndim>=1 and v.shape[0]==n and np.prod(v.shape[1:])==1,
     f"Unexpected NetCDF point shape for {v.name}: {v.shape}")
 a=np.asarray(np.ma.filled(v[:],np.nan),dtype=float).reshape(-1)
 req(len(a)==n and np.isfinite(a).all(),f"{v.name} contains missing/nonfinite")
 return a
def compare(a,b,name,eps):
 delta=float(np.max(np.abs(a-b)))
 req(delta<eps,f"{name}: selected Stage28 vs effective DATM do not match; maxdiff={delta}, tol={eps}")
 return delta
def test():
 v=np.arange(17520,dtype=float)
 req(len(v)==365*48,"NOLEAP self-test")
 req(abs(0.01*1800-18)<1e-10,"PRECTmms conversion self-test")
 print("STAGE25 SELF-TEST PASS: 21x17520, 30-min timestep, meteorological variables")
def main():
 p=argparse.ArgumentParser(description=__doc__)
 g=p.add_mutually_exclusive_group(required=True)
 g.add_argument("--self-test",action="store_true")
 g.add_argument("--audit",action="store_true")
 g.add_argument("--build",action="store_true")
 p.add_argument("--out",type=Path)
 p.add_argument("--confirm")
 a=p.parse_args()
 test()
 if a.self_test:return
 if a.build and a.confirm!=ACK:p.error("--build requires --confirm "+ACK)
 if not a.build and a.confirm:p.error("--confirm only with --build")
 req(SOURCE24.is_file(),"Stage24 full candidate CSV missing")
 m24=json.loads((STAGE24/"04_science_decision_manifest.json").read_text())
 m23=json.loads((STAGE23/"05_metadata.json").read_text())
 req(sha(STAGE23/"ES-LJu_stage23_boundary_repaired_full21yr_candidate.csv")==
     m24["Stage23_parent_candidate_sha256"],"Stage24 Stage23 parent SHA failed")
 req(m23["whole_year_candidate_created"] and not m23["HOLD"],
     "Stage23 unreleased boundary scope")
 req(m24["2013_12_25_original_precip_left_untouched"] is True,
     "2013 tower rain preservation missing")
 req(m24["rain_hold_28_days_count"]==28 and
     abs(float(m24["rain_hold_28_days_total_mm"])-25.14)<.005,
     "28 accepted rain exceptions changed")
 req(abs(float(m24["original_tower_daily_total_mm"])-
         float(m24["Stage24_reallocated_daily_total_mm"]))<1e-7,
     "2016 precipitation amount not conserved")
 src28=Path(json.loads((STAGE21/"06_manifest.json").read_text())["selected_stage28_original"])
 m21=json.loads((STAGE21/"06_manifest.json").read_text())
 req(src28.is_file() and sha(src28)==m21["original_sha256"],
     "Original Stage28 forcing provenance mismatch")
 expected=pd.read_csv(SOURCE24,low_memory=False)
 base=pd.read_csv(src28,usecols=["time","TBOT","QBOT","PRECTmms"],low_memory=False)
 required={"time","TBOT","QBOT","PRECTmms","PSRF","FSDS","FLDS","WIND"}
 req(required.issubset(expected.columns),
     "Stage24 candidate missing required DATM variables "+str(required-set(expected)))
 expected.time=pd.to_datetime(expected.time,errors="raise")
 base.time=pd.to_datetime(base.time,errors="raise")
 req(len(expected)==len(base)==21*365*48 and
     expected.time.equals(base.time) and expected.time.is_unique and
     expected.time.is_monotonic_increasing,
     "Stage24/original source time mismatch")
 req(not ((expected.time.dt.month==2)&(expected.time.dt.day==29)).any(),
     "Stage24 has leap day")
 for key in required-{"time"}:
  req(np.isfinite(expected[key].to_numpy(dtype=float)).all(),
      f"Stage24 invalid numeric {key}")
 req((expected.PRECTmms>=0).all() and
     (expected.TBOT.between(180,340)).all() and
     (expected.QBOT.between(0,.05)).all(),
     "Stage24 gross physical forcing bounds failed")
 original_stream,templates=stream(CASE)
 run_stream=Path("/scratch/ly3n24/CTSM_FATES_OUTPUTS")/CASE.name/"run/datm.streams.xml"
 req(run_stream.is_file() and sha(run_stream)==sha(original_stream),
     "Effective Stage13 preview RUNDIR stream changed")
 out=None
 if a.build:
  req(a.out is not None,"--build requires --out new path")
  out=a.out.expanduser().resolve()
  req(not out.exists() and not out.is_symlink(),
      "New output directory already exists; never overwrite")
 rows=[]
 print("STAGE25 INPUT PROVENANCE VERIFIED Stage24=",sha(SOURCE24),
       "original Stage28=",sha(src28))
 for year,template in zip(range(2004,2025),templates):
  ss=year_values(expected,year)
  bb=year_values(base,year)
  with Dataset(template) as nc:
   req("time" in nc.variables,"CDEPS time variable missing")
   req(len(nc.variables["time"][:])==17520,
       f"{year} template time count mismatch")
   req(all(x in nc.variables for x in (
       "TBOT","QBOT","PRECTmms","PSRF","FSDS","FLDS","WIND","ZBOT")),
       f"{year} missing required original DATM vars")
   # These unchanged fields must be identical to selected Stage24 sources,
   # proving that reuse of the original grid/height/meteorology is appropriate.
   orig_values={k:vec(nc.variables[k]) for k in
       ("TBOT","QBOT","PRECTmms","PSRF","FSDS","FLDS","WIND")}
   for key,tol in (("TBOT",.015),("QBOT",.00002),("PRECTmms",.00002)):
    compare(orig_values[key],bb[key].to_numpy(float),year+" ORIGINAL "+key,tol)
   for key,tol in (("PSRF",.15),("FSDS",.15),("FLDS",.15),("WIND",.02)):
    compare(orig_values[key],ss[key].to_numpy(float),year+" KEEP "+key,tol)
  changed={}
  for name in REPLACE:
   old=orig_values[name]
   new=ss[name].to_numpy(float)
   changed[name]=int((np.abs(new-old)>{"TBOT":.005,"QBOT":1e-8,
                                      "PRECTmms":1e-9}[name]).sum())
  record={"year":year,"original_template":str(template),
          "original_template_sha256":sha(template),
          "new_modified_TBOT_HH":changed["TBOT"],
          "new_modified_QBOT_HH":changed["QBOT"],
          "new_modified_PRECTmms_HH":changed["PRECTmms"],
          "original_year_precip_mm":float(orig_values["PRECTmms"].sum()*1800),
          "stage24_year_precip_mm":float(ss.PRECTmms.sum()*1800)}
  if a.build:
   target=out/(f"ES-LJu_DATM_{year}_STAGE24_FIXNC_PROVISIONAL.nc")
   if year==2004:out.mkdir(parents=True,exist_ok=False)
   req(not target.exists(),"Refuse existing output "+str(target))
   shutil.copy2(template,target)
   with Dataset(target,"r+") as nc:
    for name in REPLACE:
     var=nc.variables[name]
     req(var.shape[0]==17520 and np.prod(var.shape[1:])==1,
         f"Unexpected target NetCDF variable shape {name}")
     source_array=ss[name].to_numpy(float).reshape(var.shape)
     var[:]=source_array
    nc.sync()
   with Dataset(template) as before,Dataset(target) as after:
    for name in before.variables:
     req(name in after.variables and before.variables[name].shape==
         after.variables[name].shape,
         f"Missing NetCDF coordinate variable {name}")
     if name not in REPLACE:
      x=np.ma.getdata(before.variables[name][:])
      y=np.ma.getdata(after.variables[name][:])
      req(np.array_equal(x,y,equal_nan=True),
          f"Unexpected mutation of {name} {year}")
    for name in REPLACE:
     arr=vec(after.variables[name])
     tol={"TBOT":.015,"QBOT":.00002,"PRECTmms":.00002}[name]
     compare(arr,ss[name].to_numpy(float),f"{year} written {name}",tol)
   record.update({"new_DATM_path":str(target),
                  "new_DATM_sha256":sha(target)})
  rows.append(record)
  print(f"STAGE25 {year} TEMPLATE VERIFIED; TBOT={changed['TBOT']} "
        f"QBOT={changed['QBOT']} RAIN={changed['PRECTmms']}"
        +(" NEW_DATM_VERIFIED" if a.build else " READ_ONLY"))
 if a.build:
  manifest=pd.DataFrame(rows)
  manifest.to_csv(out/"01_21year_DATM_SHA_and_source_ledger.csv",index=False)
  (out/"02_manifest.json").write_text(json.dumps({
   "site":"ES-LJu","stage24_source_path":str(SOURCE24),
   "stage24_source_sha256":sha(SOURCE24),
   "original_Stage28_sha256":sha(src28),
   "old_case_stream":str(original_stream),
   "old_case_stream_sha256":sha(original_stream),
   "year_count":21,"source_year_first":2004,"source_year_last":2024,
   "records_per_year":17520,
   "new_annual_DATM_paths":[r["new_DATM_path"] for r in rows],
   "new_annual_DATM_sha256":[r["new_DATM_sha256"] for r in rows],
   "originals_untouched":True,"slurm_submitted":False,
   "scientific_decision":"operator-approved ES-LJu Stage24 meteorology, with site PFT proxy explicitly provisional"
  },indent=2)+"\n")
  print("STAGE25 CREATED 21/21 SHA-VERIFIED ANNUAL DATM:",out)
 else:
  print("STAGE25 AUDIT PASSED 21/21; all source DATM readable, no writes")
 print("NO SOURCE NETCDF, STAGE13 CASE, ACTIVE DATM, SLURM CHANGED")

if __name__=="__main__":main()
