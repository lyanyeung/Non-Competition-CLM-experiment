#!/usr/bin/env python3
"""Stage19 ES-LJu isolated candidate: two explicit operator decisions + marked boundary bridge.
No DATM, CIME, Slurm, raw, or prior Stage28 edits. Science approval remains HOLD.
"""
import argparse,hashlib,json
from pathlib import Path
import numpy as np
import pandas as pd

R=Path("/iridisfs/scratch/ly3n24/CLM_FATES/experiments/NonCompetitionObserved22/Batch02_10/stage16_ES_LJu_manual_review_v1_20261025")
SHA="a9c0d441e5e4b02b310158891d040ebe14c7ff50172a64ee250c0b4aaf05df1e"

def sha(p):
 h=hashlib.sha256()
 with Path(p).open("rb") as f:
  for b in iter(lambda:f.read(1<<20),b""):h.update(b)
 return h.hexdigest()

def sat(T):return 6.112*np.exp(np.clip(17.67*T/(T+243.5),-20,20))
def thermo(T,V,P):
 es=sat(T);ea=(es-V)*100
 if not all(map(np.isfinite,(T,V,P,ea))) or not (0<ea<P and V>=0):
  raise ValueError("Invalid TA/VPD/PSRF tuple")
 q=.622*ea/(P-.378*ea)
 rh=100*(es-V)/es
 if not (0<q<0.05 and 1<=rh<=100):
  raise ValueError(f"Invalid resulting RH/QBOT {rh} {q}")
 return q,rh

def main():
 ap=argparse.ArgumentParser()
 ap.add_argument("--out",type=Path,required=True,help="New isolated directory only")
 a=ap.parse_args()
 manifest=json.loads((R/"00_science_lineage_and_review_questions.json").read_text())
 source=Path(manifest["stage28_source"]["path"])
 if not source.is_file() or sha(source)!=SHA or manifest["stage28_source"]["sha256"]!=SHA:
  raise RuntimeError("Pinned selected Stage28 CSV SHA mismatch: STOP")
 raw=Path(manifest["original_fluxmet_hourly"]["raw_path"])
 eras=sorted(raw.parent.glob("*ERA5_HH*.csv"))
 if len(eras)!=1:raise RuntimeError("Exactly one ES-LJu ERA5_HH companion expected")
 era_path=eras[0]
 data=pd.read_csv(source,low_memory=False)
 required={"time","TA_USE","VPD_USE","TBOT","QBOT","PSRF"}
 if not required.issubset(data):raise RuntimeError("Selected Stage28 missing columns")
 data["time"]=pd.to_datetime(data.time,errors="raise")
 if data.time.duplicated().any() or len(data)!=21*17520:
  raise RuntimeError("Selected Stage28 timeline mismatch")
 era=pd.read_csv(era_path,usecols=["TIMESTAMP_START","TA_ERA","VPD_ERA"],
                 dtype={"TIMESTAMP_START":str},low_memory=False)
 era["time"]=pd.to_datetime(era.TIMESTAMP_START,format="%Y%m%d%H%M",errors="raise")
 era=era[era.time.dt.year.between(2004,2024)&~((era.time.dt.month==2)&(era.time.dt.day==29))]
 if era.time.duplicated().any() or len(era)!=len(data):
  raise RuntimeError("ERA half-hour timeline mismatch")
 era=era.set_index("time")
 if not data.time.isin(era.index).all():
  raise RuntimeError("Missing ERA timestamp(s)")
 def ix(t):
  hit=data.index[data.time==pd.Timestamp(t)]
  if len(hit)!=1:raise RuntimeError("Missing/duplicate source time "+t)
  return int(hit[0])
 edits=[]
 def patch(t,T,V,why):
  i=ix(t);P=float(data.at[i,"PSRF"])
  q,rh=thermo(float(T),float(V),P)
  edits.append(dict(time=t,decision=why,
    old_T_C=float(data.at[i,"TA_USE"]),new_T_C=float(T),
    old_VPD_hPa=float(data.at[i,"VPD_USE"]),new_VPD_hPa=float(V),
    old_QBOT=float(data.at[i,"QBOT"]),new_QBOT=q,new_RH_pct=rh))
  data.at[i,"TA_USE"]=T;data.at[i,"VPD_USE"]=V
  data.at[i,"TBOT"]=T+273.15;data.at[i,"QBOT"]=q

 # APPROVED 1: interpolate precisely at 2015-09-16 15:00
 a0=ix("2015-09-16 14:30");b0=ix("2015-09-16 15:30");center=ix("2015-09-16 15:00")
 for i,want in ((a0,21.631),(b0,21.522),(center,8.960)):
  if abs(float(data.at[i,"TA_USE"])-want)>.003:
   raise RuntimeError("2015 input anchor drift")
 patch("2015-09-16 15:00",
       (float(data.at[a0,"TA_USE"])+float(data.at[b0,"TA_USE"]))/2,
       (float(data.at[a0,"VPD_USE"])+float(data.at[b0,"VPD_USE"]))/2,
       "APPROVED_OPERATOR_INTERPOLATE_TA_VPD")

 # APPROVED 2: use verified companion ERA5 TA+VPD at 16:00 and 16:30
 for t,expected in (("2023-10-18 16:00",6.441),("2023-10-18 16:30",4.040)):
  i=ix(t)
  if abs(float(data.at[i,"TA_USE"])-expected)>.003:
   raise RuntimeError("2023 input anchor drift at "+t)
  rr=era.loc[pd.Timestamp(t)]
  patch(t,float(rr.TA_ERA),float(rr.VPD_ERA),
        "APPROVED_OPERATOR_ERA5_TA_VPD_PAIR")

 # SAFETY BOUNDARY: operator asked to avoid a newly created discontinuity.
 # 15:30 is separately labelled PROVISIONAL; interpolation from original
 # 15:00 to newly ERA-filled 16:00, not an undeclared ERA replacement.
 left=ix("2023-10-18 15:00");middle=ix("2023-10-18 15:30")
 right=ix("2023-10-18 16:00")
 if abs(float(data.at[left,"TA_USE"])-11.302)>.003 or abs(float(data.at[middle,"TA_USE"])-10.071)>.003:
  raise RuntimeError("2023 transition boundary anchor drift")
 patch("2023-10-18 15:30",
       (float(data.at[left,"TA_USE"])+float(data.at[right,"TA_USE"]))/2,
       (float(data.at[left,"VPD_USE"])+float(data.at[right,"VPD_USE"]))/2,
       "PROVISIONAL_15_30_BRIDGE_REQUIRES_APPROVAL")

 context=data[data.time.between("2023-10-18 14:30","2023-10-18 20:30")].copy()
 context["RH_pct"]=100*(sat(context.TA_USE)-context.VPD_USE)/sat(context.TA_USE)
 context["jump_abs_C"]=context.TA_USE.diff().abs()
 print("2023-10-18 post-candidate boundary (all timestamp labels as selected Stage28):")
 print(context[["time","TA_USE","VPD_USE","QBOT","RH_pct","jump_abs_C"]].to_string(index=False))
 if (context.jump_abs_C.dropna()>5).any():
  raise RuntimeError("2023 remaining jump exceeds 5C/HH: stop, no candidate saved")

 dest=a.out.expanduser().resolve()
 if dest.exists() or dest.is_symlink():
  raise RuntimeError("Never overwrite existing output")
 dest.mkdir(parents=True,exist_ok=False)
 data["time"]=data.time.dt.strftime("%Y-%m-%d %H:%M:%S")
 data.to_csv(dest/"ES-LJu_stage19_decisions_with_provisional_bridge.csv",index=False)
 pd.DataFrame(edits).to_csv(dest/"00_exact_edit_ledger.csv",index=False)
 (dest/"01_metadata.json").write_text(json.dumps({
  "selected_source_path":str(source),"selected_source_sha256":SHA,
  "ERA5_companion_path":str(era_path),"ERA5_companion_sha256":sha(era_path),
  "scientific_status":"HOLD_2023_BRIDGE_AND_OTHER_MET_ISSUES",
  "originals_unchanged":True},indent=2)+"\n")
 print("\nEDIT LEDGER\n",pd.DataFrame(edits).to_string(index=False))
 print("ISOLATED CANDIDATE:",dest)
 print("NO SOURCE/DATM/CASE/SLURM MODIFICATIONS; SCIENCE HOLD")

if __name__=="__main__":main()
