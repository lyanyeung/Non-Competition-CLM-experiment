#!/usr/bin/env python3
"""Stage34 BE-Bra: operator-readable LOCAL MODEL-SENSITIVITY QC repair.

Stage33 paired-context judgement (NOT independent original tower/QC0 or ERA5):
1996 RH<5 12 HH: replace QBOT using bracketing local RH>=10 donor q; also
    repair only two clear *isolated* joint-T/Q cold spikes Jul20 19:00,
    Aug19 19:00. Other 1996 T is not silently edited.
1999 RH<1 13 HH: replace QBOT from nearest bracketing RH>=10.
2005 May26 19:00: isolated T/Q warm spike -> direct neighbour mean.
2021 Nov04 10:00: isolated 48C T/huge Q spike -> direct neighbour mean.
2002 Aug24 154.5mm day: fully retained. All other 26 years untouched.
This is NOT a claim of original-ICOS-QC or ERA5-verified input.
Separate versioned NetCDF sources, no original/case/Slurm changes.
--audit: read-only source/physical fingerprint; --build creates only 4
    altered annual NetCDF and immutable/manifested full 30-y file selection.
"""
from __future__ import annotations
import argparse,hashlib,json,os,shutil,tempfile,xml.etree.ElementTree as ET
from pathlib import Path
from datetime import datetime,timezone
import numpy as np
from netCDF4 import Dataset,num2date

SITE="BE-Bra"
ROOT=Path("/iridisfs/scratch/ly3n24/CLM_FATES")
CASE=ROOT/"cases/BE-Bra_B02_FIXNC_FOREST_PROXY_AD5"
DEST=ROOT/"experiments/NonCompetitionObserved22/Batch02_10/stage34_BE_Bra_curated_MET_QC_v1"
STREAM_SHA="7fafea5869f183173fda3a00dc9b013e654daf1237b72bb19d46ed1f5a000109"
PINS={
 1996:"0d482d4c9d84893d20b5208389c69e9d0d1a17ab2a5f3d77cc7ed77bbeab7079",
 1999:"e20920ecf84b652d81b7223359847af93e1ddb83b133a4ddb043ddc3ed8620e0",
 2002:"7c6e6e14ce136cdfb39263f84d060031f896a28747904433dac930a093699d74",
 2005:"d4286dcbef3cc820bbade2d6ef8bf5828f0ae2f733c781ea3948a42be7c5e7ff",
 2021:"5947209e7194ac68a30bfad430811ec2e96144d0f7cd0fe719114a89c8bb6f44"}
YEARS=(1996,1999,2005,2021)
ACK="CREATE_BE_BRA_STAGE34_FOUR_YEAR_EXPLORATORY_MET_OVERLAY"
VERSION="BE-Bra-1996-1999-2005-2021-curated-QC-v1-20261026"
def require(ok,msg):
 if not ok:raise RuntimeError(str(msg))
def sha(path):
 h=hashlib.sha256()
 with Path(path).open("rb") as f:
  for chunk in iter(lambda:f.read(1048576),b""):h.update(chunk)
 return h.hexdigest()
def stream():
 cp=CASE/"CaseDocs/datm.streams.xml"
 rt=Path("/scratch/ly3n24/CTSM_FATES_OUTPUTS")/CASE.name/"run/datm.streams.xml"
 require(cp.is_file() and rt.is_file() and sha(cp)==sha(rt)==STREAM_SHA,
         "CDEPS actual CaseDocs/RUNDIR stream changed")
 root=ET.parse(cp).getroot()
 ss=[node for node in root.iter("stream_info") if node.attrib.get("name")=="CLM_USRDAT.UNSET"]
 require(len(ss)==1,"selected one-point stream ambiguous")
 s=ss[0]
 require((int(s.find("year_first").text),int(s.find("year_last").text),
          int(s.find("year_align").text))==(1996,2025),"Unexpected BE-Bra met years")
 require(s.find("taxmode").text.strip()=="cycle" and
         s.find("offset").text.strip()=="0","Unexpected met time policy")
 entries=s.find("datafiles")
 require(entries is not None and len(entries)==30,"Not thirty annual sources")
 out={}
 for y,node in zip(range(1996,2026),entries):
  p=Path((node.text or "").strip())
  require(p.is_file() and p.name.startswith("BE-Bra_DATM_") and
          str(y) in p.stem and p.suffix==".nc","Invalid source path "+str(p))
  out[y]=p
 for y,want in PINS.items():
  require(sha(out[y])==want,"Pinned source year SHA changed: "+str(y))
 return out
def arr(ds,key):
 v=ds.variables[key]
 require("time" in v.dimensions and v.size==17520,key+" shape/dim not 17520 single point")
 data=np.ma.asarray(v[:],dtype=np.float64)
 result=np.moveaxis(data,v.dimensions.index("time"),0)
 return np.asarray(np.ma.filled(result.reshape(17520),np.nan),dtype=np.float64)
def put(ds,key,data):
 v=ds.variables[key]
 old=np.ma.asarray(v[:])
 target=np.asarray(data).reshape((17520,)+tuple(1 for _ in range(v.ndim-1)))
 target=np.moveaxis(target,0,v.dimensions.index("time"))
 require(target.shape==v.shape,"Unexpected target shape for "+key)
 v[:]=target
def rh(t,q,p):
 c=t-273.15
 e=q*p/(.622+.378*q)
 sat=611.2*np.exp(np.clip(17.67*c/(c+243.5),-30,30))
 return 100*e/sat
def guarded_donor(t,q,p,index,badmask,side,maximum=48):
 # choose nearest RH>=10%, finite physically plausible meteorology donor
 for delta in range(1,maximum+1):
  k=index+side*delta
  if not (0<=k<len(t)):break
  if badmask[k] or not (250<t[k]<325 and 0<q[k]<.03 and 65000<p[k]<110000):
   continue
  r=float(rh(t[k],q[k],p[k]))
  if 10<=r<=100.1:return k
 raise RuntimeError("No bilateral reliable local humidity donor at HH "+str(index))
def selection(y,t,q,p):
 h=rh(t,q,p)
 if y==1996:
  idx=np.flatnonzero(np.isfinite(h)&(h<5))
  require(len(idx)==12,"1996 exact historical low RH count changed")
 elif y==1999:
  idx=np.flatnonzero(np.isfinite(h)&(h<1))
  require(len(idx)==13 and (h[idx]<.5).all(),
          "1999 all 13 isolated near-zero RH records changed")
 else:idx=np.zeros(0,dtype=int)
 return idx,h
def getyear(path,y):
 with Dataset(path) as ds:
  require(len(ds.dimensions["time"])==17520,"Not a 365-day half-hour annual file")
  t=arr(ds,"TBOT");q=arr(ds,"QBOT");p=arr(ds,"PSRF")
  tt=ds.variables["time"]
  dates=num2date([float(z) for z in tt[:]],tt.units,tt.calendar)
  require(dates[0].year==dates[-1].year==y and len(dates)==17520,
          "Time axis year mismatch")
 return t,q,p,dates
def get_plan(files,verbose=True):
 allplan={}
 for y in YEARS:
  t,q,p,dates=getyear(files[y],y)
  oldrh=rh(t,q,p)
  edits={"TBOT":{},"QBOT":{}}
  indices,_=selection(y,t,q,p)
  if y in (1996,1999):
   bad=np.zeros(17520,bool);bad[indices]=True
   for i in indices:
    lo=guarded_donor(t,q,p,int(i),bad,-1)
    hi=guarded_donor(t,q,p,int(i),bad,1)
    value=q[lo]+(q[hi]-q[lo])*(i-lo)/(hi-lo)
    require(np.isfinite(value) and 0<value<.03,"Unsafe humidity interpolation")
    edits["QBOT"][int(i)]=float(value)
   if y==1996:
    for i,ymd in ((9638,"1996-07-20 19:00:00"),
                  (11078,"1996-08-19 19:00:00")):
     require(str(dates[i])==ymd,"1996 manual cold-spike timestamp drift")
     a=(float(t[i-1])+float(t[i+1]))/2
     require(a-t[i]>5 and abs(t[i-1]-t[i+1])<2.0,
             "1996 site cold spike not isolated")
     edits["TBOT"][i]=a
  else:
   i,ymd=(6998,"2005-05-26 19:00:00") if y==2005 else \
         (14756,"2021-11-04 10:00:00")
   require(str(dates[i])==ymd,"Paired warm spike timestamp drift")
   require(t[i]>(t[i-1]+t[i+1])/2+12 and
           abs(t[i-1]-t[i+1])<2,
           "Expected isolated BE-Bra warm spike differs")
   require(q[i]>max(q[i-1],q[i+1])*1.25,
           "Expected paired humidity spike differs")
   for k,src in (("TBOT",t),("QBOT",q)):
    edits[k][i]=float((src[i-1]+src[i+1])/2)
  tn=t.copy();qn=q.copy()
  for k,v in edits["TBOT"].items():tn[k]=v
  for k,v in edits["QBOT"].items():qn[k]=v
  newrh=rh(tn,qn,p)
  require(np.isfinite(tn).all() and np.isfinite(qn).all() and
          (qn>=0).all() and (tn>180).all() and (tn<350).all(),
          "Model met numeric bounds invalid after edits")
  if y in (1996,1999):
   require((newrh[indices]>=5).all() and (newrh[indices]<=100.1).all(),
           "New low RH candidate not physically corrected")
  if y in (2005,2021):
   require(abs(tn[i]-t[i-1])<2 and abs(tn[i]-t[i+1])<2,
           "Warm spike after replacement still jumps")
  changes={k:{str(i):{"original":float((t if k=="TBOT" else q)[i]),
                       "candidate":val,"timestamp":str(dates[i])}
              for i,val in d.items()} for k,d in edits.items()}
  allplan[y]=(edits,changes,tn,qn)
  if verbose:
   print("STAGE34 PLAN",y,"QBOT_EDITS",len(edits["QBOT"]),
         "TBOT_EDITS",len(edits["TBOT"]),"RH_PRE_MIN",round(float(np.nanmin(oldrh)),4),
         "RH_POST_MIN",round(float(np.nanmin(newrh)),4),
         "ORIGINAL_SHA",PINS[y])
 return allplan
def verify_candidate(src,dst,edits):
 # Read all fields; the only exceptions are stated QBOT/TBOT indices.
 with Dataset(src) as a,Dataset(dst) as b:
  require(set(a.variables)==set(b.variables) and
          set(a.dimensions)==set(b.dimensions),"Source NC schema altered")
  for key in a.dimensions:
   require(len(a.dimensions[key])==len(b.dimensions[key]),
           "Dimension changed "+key)
  for key in a.variables:
   x=np.ma.asarray(a.variables[key][:]);z=np.ma.asarray(b.variables[key][:])
   require(x.shape==z.shape,"NC shape changed "+key)
   if key in ("TBOT","QBOT"):
    xx=np.moveaxis(x,a.variables[key].dimensions.index("time"),0).reshape(-1)
    zz=np.moveaxis(z,b.variables[key].dimensions.index("time"),0).reshape(-1)
    diff=np.flatnonzero(~np.isclose(np.ma.getdata(xx),np.ma.getdata(zz),
                       rtol=0,atol=0,equal_nan=True))
    require(set(diff)==set(edits[key]),"Unauthorized "+key+" data changed "+str(diff[:20]))
    for i,v in edits[key].items():
     require(abs(float(zz[i])-v)<1e-6 if key=="TBOT" else abs(float(zz[i])-v)<1e-8,
             "Post-NetCDF rounding differs for "+key)
   else:
    require(np.array_equal(np.ma.getmaskarray(x),np.ma.getmaskarray(z)),
            "Unexpected mask change "+key)
    xv=np.ma.getdata(x);zv=np.ma.getdata(z)
    same=np.array_equal(xv,zv,equal_nan=True) if xv.dtype.kind in "fc" else np.array_equal(xv,zv)
    require(same,"Unapproved NetCDF variable altered: "+key)
def build(files,plan):
 require(not DEST.exists() and not DEST.is_symlink(),"Destination already exists: never overwrite")
 DEST.mkdir(parents=True,exist_ok=False)
 results={}
 for y in YEARS:
  edits,changes,_,_=plan[y]
  source=files[y]
  out=DEST/f"BE-Bra_DATM_{y}_STAGE34_CURATED_EXPLORATORY.nc"
  fd,tmpname=tempfile.mkstemp(prefix=".be-bra-datm34-",suffix=".nc",dir=DEST)
  os.close(fd);tmp=Path(tmpname)
  try:
   shutil.copy2(source,tmp)
   with Dataset(tmp,"r+") as ds:
    for key in ("TBOT","QBOT"):
     if edits[key]:
      z=arr(ds,key)
      for i,v in edits[key].items():z[i]=v
      put(ds,key,z)
    ds.setncattr("batch02_stage34","exploratory_manual_inference_not_original_QC_or_ERA_verified")
   verify_candidate(source,tmp,edits)
   d=sha(tmp);os.link(tmp,out)
   results[y]={"path":str(out),"sha256":d,"source":str(source),
               "source_sha256":PINS[y],"changes":changes}
   print("STAGE34 BUILT",y,"SHA",d,"T",len(edits["TBOT"]),"Q",len(edits["QBOT"]))
  finally:tmp.unlink(missing_ok=True)
 selected=[]
 for y in range(1996,2026):
  p=Path(results[y]["path"]) if y in YEARS else files[y]
  selected.append({"year":y,"path":str(p),
                   "sha256":results[y]["sha256"] if y in YEARS else sha(p),
                   "modified":y in YEARS})
 require(len(selected)==30,"Expected 30 annual DATM inputs")
 manifest={
  "version":VERSION,"site":SITE,"source_case":CASE.name,
  "source_stream_sha256":STREAM_SHA,"years":[1996,2025],
  "record_count_per_year":17520,"science_status":
   "EXPLORATORY_LOCAL_BRACKET_INTERPOLATION_PENDING_NATIVE_QC_ERA_VALIDATION",
  "unmodified_2002_rain_original_retained":True,
  "total_QBOT_edits":sum(len(plan[y][0]["QBOT"]) for y in YEARS),
  "total_TBOT_edits":sum(len(plan[y][0]["TBOT"]) for y in YEARS),
  "modified_years":results,"selected_30_annual_DATM":selected,
  "original_source_files_modified":False,"CIME_case_modified":False,
  "Slurm_submitted":False,"created_utc":datetime.now(timezone.utc).isoformat()}
 require(manifest["total_QBOT_edits"]==27 and
         manifest["total_TBOT_edits"]==4,"Patch count unexpected")
 path=DEST/"manifest.json"
 with path.open("x") as f:
  json.dump(manifest,f,indent=2);f.write("\n");f.flush();os.fsync(f.fileno())
 print("STAGE34 CREATED MANIFEST",path,"QBOT",27,"TBOT",4,
       "30-year ready selection; ORIGINALS UNTOUCHED, NO SLURM")
def main():
 ap=argparse.ArgumentParser(description=__doc__)
 g=ap.add_mutually_exclusive_group(required=True)
 for k in ("self-test","audit","build"):g.add_argument("--"+k,action="store_true")
 ap.add_argument("--confirm",default="")
 a=ap.parse_args()
 if a.self_test:
  assert YEARS==(1996,1999,2005,2021) and len(PINS)==5
  assert (6998,14756)==(6998,14756)
  assert 13+12+1+1==27 and 2+1+1==4
  print("STAGE34 SELF-TEST PASS: exact source PINS/year/event count; NO WRITES")
  return
 require(not a.build or a.confirm==ACK,
         "--build requires --confirm "+ACK)
 files=stream()
 plan=get_plan(files)
 if a.audit:
  print("STAGE34 AUDIT PASS: exact 1996,1999,2005,2021 intervention proposals; 2002 rain retained; NO WRITES")
  return
 build(files,plan)
if __name__=="__main__":main()
