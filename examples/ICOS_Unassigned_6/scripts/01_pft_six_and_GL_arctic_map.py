#!/usr/bin/env python3
"""Read-only six unassigned ICOS PFT audit and optional independent GL map.
Source: FINAL_38_SITE_FIXNC_PFT_20261025.csv, exact pinned git blob.
Four 100% C3 grass canopy-group proxies, ES-Agu open bare/grass/shrub
proposal, GL-ZaH Arctic evergreen/deciduous shrub private-map proposal.
The --make-private-gl action writes a NEW json candidate only, NOT a CIME
case/surface/Slurm. Site fractions are NOT observed whole tower footprints.
"""
from __future__ import annotations
import argparse,csv,hashlib,json,math
from pathlib import Path

SOURCE_BLOB="63739e00408443bcbb4b286bb3324c76e9fd9100"
PARAM_SHA="0819f8fddcb3566f6209f72bb1159a3161d03c8225a1464727b1d2b21aec6c04"
DEFAULT=Path("/iridisfs/scratch/ly3n24/CLM_FATES/CTSM/src/fates/parameter_files/fates_params_default.json")
SITES={
"CH-Aws":("C3 grass 100 (candidate)","CANDIDATE",{13:100},"HOLD_CASE_TEMPLATE_UNSTABLE"),
"DE-Gri":("C3 grass 100 (candidate)","CANDIDATE",{13:100},"GRASS_HERBACEOUS_PROXY"),
"DE-RuR":("C3 grass 100 (candidate)","CANDIDATE",{13:100},"GRASS_HERBACEOUS_PROXY"),
"IT-Tor":("C3 grass 100 (candidate)","CANDIDATE",{13:100},"GRASS_HERBACEOUS_PROXY"),
"ES-Agu":("bare 49 / C3 grass 29 / evergreen shrub 22","PROPOSED",{0:49,13:29,9:22},"HOLD_57PCT_DENOMINATOR"),
"GL-ZaH":("bare 43 / evergreen arctic dwarf shrub 53 / deciduous arctic shrub 3 / arctic C3 grass 1","PROPOSED",{0:43,9:53,11:3,12:1},"REQUIRES_PRIVATE_ARCTIC_FATES_MAP")}
def fail(s):raise RuntimeError(str(s))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def gitblob(b):return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()
def vector(p):
 a=[0.]*15
 for k,v in p.items():
  if not 0<=k<15 or v<0 or not math.isfinite(v):fail("Invalid PFT")
  a[k]=float(v)
 if abs(sum(a)-100)>1e-6:fail("PFT fraction sum not100")
 return a
def source(path):
 if not path.is_file():fail("Source 38-site CSV missing: "+str(path))
 if gitblob(path.read_bytes())!=SOURCE_BLOB:
  fail("STOP: official 38-site PFT register changed blob SHA")
 with path.open(encoding="utf-8-sig",newline="") as fp:
  allrows=list(csv.DictReader(fp))
 if len(allrows)!=38 or len({x["site"] for x in allrows})!=38:
  fail("Official input not 38 unique stations")
 six={x["site"]:x for x in allrows if x["fixnc_cohort"]=="Not assigned"}
 if set(six)!=set(SITES):fail("Not assigned six-station set changed")
 for name,(expected,status,frac,gate) in SITES.items():
  row=six[name]
  if row["final_PCT_NAT_PFT"]!=expected or not row["status"].startswith(status):
   fail(name+": scientific status/evidence changed")
  vector(frac)
 return six
def parameter(path):
 if not path.is_file() or sha(path)!=PARAM_SHA:
  fail("Pinned original shared FATES params SHA mismatch: "+str(path))
 obj=json.loads(path.read_text(encoding="utf8"))
 p=obj["parameters"];names=list(p["fates_pftname"]["data"])
 mat=p["fates_hlm_pft_map"]["data"]
 if len(names)!=14 or len(mat)!=14 or any(len(x)!=14 for x in mat):
  fail("FATES host map dimensions unexpectedly changed")
 def named_row(host,name):
  x=mat[host-1];i=names.index(name)
  if abs(sum(x)-1)>1e-8 or abs(x[i]-1)>1e-8:
   fail("Shared FATES map changed for host "+str(host))
 named_row(9,"broadleaf_evergreen_extratrop_shrub")
 named_row(12,"arctic_c3_grass")
 named_row(13,"cool_c3_grass")
 if any(abs(float(mat[10][i])-v)>1e-8 for i,v in enumerate([
     0,0,0,0,0,0,0,0,0.1,0.1,0.8,0,0,0])):
  fail("Shared mixed Arctic host11 row changed")
 return obj,names,mat
def check(csvpath,param):
 source(csvpath)
 obj,names,mat=parameter(param)
 print("SIX-SITE OFFICIAL SOURCE PASS; active FATES MAP SHA PASS")
 for site,(proposal,status,fract,gate) in SITES.items():
  print(site,"HOST_NATPFT_0..14",",".join("%g"%v for v in vector(fract)),
        "SOURCE",status,"GATE",gate)
 print("GL-ZaH default HLM9 =",[(names[i],v) for i,v in enumerate(mat[8]) if v])
 print("GL-ZaH default HLM11 =",[(names[i],v) for i,v in enumerate(mat[10]) if v])
 print("CHECK PASS; no measured-footprint claim, no model changes, no Slurm")
def build(csvpath,param,out):
 source(csvpath)
 obj,names,mat=parameter(param)
 if out.exists() or out.is_symlink():fail("Output exists; no overwrite "+str(out))
 a=names.index("broadleaf_evergreen_arctic_shrub")
 b=names.index("broadleaf_colddecid_arctic_shrub")
 # This is a PRIVATE GL-ZaH map only, never the shared parameter file.
 mat[8]=[1. if i==a else 0. for i in range(14)]  # host PFT9
 mat[10]=[1. if i==b else 0. for i in range(14)] # host PFT11
 out.mkdir(parents=True,exist_ok=False)
 new=out/"fates_params_GL-ZaH_arctic_private_candidate.json"
 new.write_text(json.dumps(obj,indent=2)+"\n",encoding="utf8")
 receipt={"status":"UNAPPROVED_TECHNICAL_SCIENCE_CANDIDATE",
    "site":"GL-ZaH","shared_original_sha256":PARAM_SHA,
    "official_evidence_git_blob":SOURCE_BLOB,
    "private_param_file":str(new),"private_param_sha256":sha(new),
    "host_PCT_NAT_PFT_0..14":vector(SITES["GL-ZaH"][2]),
    "host9":"broadleaf_evergreen_arctic_shrub",
    "host11":"broadleaf_colddecid_arctic_shrub",
    "host12":"arctic_c3_grass",
    "model_case_created":False,"surface_created":False,"slurm_submitted":False,
    "next_gate":"Validate site source point, FATES config effective map, UTC met and stand/footprint coverage before AD5"}
 (out/"manifest.json").write_text(json.dumps(receipt,indent=2)+"\n",encoding="utf8")
 if sha(param)!=PARAM_SHA:fail("Shared FATES params unexpectedly changed")
 print("PRIVATE GL-ZaH MAP CREATED:",new)
 print("NO CIME CASE/SURFACE/SLURM; scientific proxy only")
def main():
 ap=argparse.ArgumentParser(description=__doc__)
 mode=ap.add_mutually_exclusive_group(required=True)
 mode.add_argument("--self-test",action="store_true")
 mode.add_argument("--check",action="store_true")
 mode.add_argument("--make-private-gl",action="store_true")
 ap.add_argument("--source",type=Path)
 ap.add_argument("--params",type=Path,default=DEFAULT)
 ap.add_argument("--outdir",type=Path)
 ap.add_argument("--ack-gl-proxy",action="store_true")
 x=ap.parse_args()
 if x.self_test:
  assert len(SITES)==6 and sum(vector(SITES["GL-ZaH"][2]))==100
  assert vector(SITES["ES-Agu"][2])[0]==49
  assert all(SITES[z][2]=={13:100} for z in ("CH-Aws","DE-Gri","DE-RuR","IT-Tor"))
  print("SELF-TEST PASS: six exact unassigned ICOS stations, grass/bare/arctic candidates, 15 host PFTs")
  return
 if x.source is None:ap.error("--source required")
 if x.check:
  if x.outdir or x.ack_gl_proxy:ap.error("--check must be read only")
  check(x.source,x.params)
 else:
  if not x.outdir or not x.ack_gl_proxy:
   ap.error("--make-private-gl requires --outdir NEW and --ack-gl-proxy")
  build(x.source,x.params,x.outdir.expanduser().resolve())
if __name__=="__main__":main()
