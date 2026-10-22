#!/usr/bin/env python3
"""Read-only NL-Loo pilot inspection. No case or model writes."""
import argparse, json, re, subprocess, hashlib
from pathlib import Path

ROOT=Path("/iridisfs/scratch/ly3n24/CLM_FATES")
CASE=ROOT/"cases/NL-Loo_FATES_SPINUP500"
def cmd(args,cwd):
 try:
  r=subprocess.run(args,cwd=cwd,capture_output=True,text=True,timeout=25)
  return {"rc":r.returncode,"stdout":r.stdout.strip()[:3000],"stderr":r.stderr.strip()[:500]}
 except Exception as e:return {"error":str(e)}
def nml(p):
 out={}
 if p.is_file():
  for line in p.read_text(errors="replace").splitlines():
   m=re.match(r"^\s*([a-z][a-z0-9_]*)\s*=\s*(.*)",line,re.I)
   if m:out[m.group(1).lower()]=m.group(2).split("!")[0].strip().strip(",").strip().strip("'\u0022")
 return out
def main():
 ap=argparse.ArgumentParser();ap.add_argument("--out",type=Path,default=Path.home()/"NL_Loo_NC_audit");a=ap.parse_args()
 if not CASE.is_dir() or not (CASE/"CaseDocs/lnd_in").is_file():raise SystemExit("STOP: baseline case/lnd_in absent; no fallback permitted")
 d=nml(CASE/"CaseDocs/lnd_in")
 keys=["fsurdat","fates_paramfile","use_fates","use_fates_sp","use_fates_fixed_biogeog","use_fates_nocomp","spinup_state"]
 j={"case":str(CASE),"site":"NL-Loo","mode_flags":{k:d.get(k,"NOT_IN_GENERATED_NAMELIST") for k in keys},"xml":{k:cmd(["./xmlquery",k,"--value"],CASE) for k in ["COMPSET","CLM_ACCELERATED_SPINUP","RUN_TYPE","RUN_STARTDATE","STOP_N","RESUBMIT","EXEROOT","RUNDIR","DOUT_S_ROOT","CLM_CO2_TYPE","CCSM_CO2_PPMV"]},"git_ctsm":cmd(["git","rev-parse","HEAD"],ROOT/"CTSM"),"submitted":False}
 for key in ("fsurdat","fates_paramfile"):
  raw=d.get(key,"").strip().strip("'\u0022")
  if raw.startswith("$"):j[key+"_status"]="VARIABLE_UNRESOLVED";continue
  p=Path(raw);p=p if p.is_absolute() else CASE/p
  j[key+"_status"]={"path":str(p),"exists":p.is_file(),"sha256":hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() and p.stat().st_size<15_000_000 else "NOT_HASHED_LARGE_OR_MISSING"}
  if key=="fates_paramfile" and p.is_file() and p.suffix==".json":
   f=json.loads(p.read_text());pars=f.get("parameters",{})
   j["fates_json"]={"pft_dimension":f.get("dimensions",{}).get("fates_pft"),"pft_names":pars.get("fates_pftname",{}).get("data"),"hlm_pft_map":pars.get("fates_hlm_pft_map",{}).get("data"),"hlm_pft_map_dims":pars.get("fates_hlm_pft_map",{}).get("dims")}
  if key=="fsurdat" and p.is_file():
   try:
    import netCDF4,numpy as np
    with netCDF4.Dataset(p) as ds:
     j["surface_landunits"]={}
     for name in ["PCT_NATVEG","PCT_CROP","PCT_WETLAND","PCT_LAKE","PCT_GLACIER","PCT_URBAN"]:
      if name in ds.variables:j["surface_landunits"][name]=np.asarray(ds[name][:]).ravel().tolist()
     if "PCT_NAT_PFT" in ds.variables:
      v=ds["PCT_NAT_PFT"];j["surface_host_PFT"]={"dims":v.dimensions,"values":np.asarray(v[:]).ravel().tolist(),"warning":"HOST CLM PFT vector, not FATES observed ground-area fractions"}
   except Exception as e:j["surface_error"]=str(e)
 a.out.mkdir(parents=True,exist_ok=True)
 (a.out/"00_overview.json").write_text(json.dumps(j,indent=2,default=str)+"\n")
 print("READ-ONLY INSPECTION COMPLETE",a.out/"00_overview.json")
 print("STOP GATE: validate landunit denominator, FATES PFT map, fixed-biogeography behavior, AD restart support, and executable mode before preparing or submitting a case.")
if __name__=="__main__":main()
