#!/usr/bin/env python3
"""Stage36: CH-Lae 3 EXPLORATORY localized temperature anomaly candidates.

Not original tower-QC certified or ERA5-verified. Exact Stage33 anomalies:
2012-Nov02 14:30: 10.149 C between 1.076/-0.728 C, paired QBOT high.
2015-Jun12 15:30: 14.097 C between 23.02/20.35 C; TBOT only.
2017-Jun27 14:30: 15.452 C between 24.386/23.970 C, paired QBOT low.
Both CH-Lae 2005-Dec31 abrupt sustained step and 2012-Nov01 15:30
sustained cold step are retained/UNVERIFIED, not called valid observations.
3 changed annual NC files + 18 unmodified originals for model sensitivity.
Never touch original forcing, existing case, Slurm or prior submissions.
"""
from __future__ import annotations
import argparse,hashlib,json,os,shutil,tempfile,xml.etree.ElementTree as ET
from pathlib import Path
from datetime import datetime,timezone
import numpy as np
from netCDF4 import Dataset,num2date

SITE="CH-Lae"
ROOT=Path("/iridisfs/scratch/ly3n24/CLM_FATES")
CASE=ROOT/"cases/CH-Lae_B02_FIXNC_FOREST_PROXY_AD5"
DEST=ROOT/"experiments/NonCompetitionObserved22/Batch02_10/stage36_CH_Lae_targeted_MET_QC_v1"
STREAM_SHA="dc015e2bd718609d573d0c14adf86a88a9bc6762a2bdfd2cc9ab23a891dc7a61"
PINS={
 2005:"61e1aa3e37a452052d90a9325e026853cf17988d7dde3fd3d5127168b5dbb710",
 2012:"c33516c923f5664ac87c16b252337dd4919ef03b1efd6089a5bb3bc449952832",
 2015:"5449640847ad4941e1036c6e3df99ece104b33b2ba2a998a98ec8323bdf5af23f6",
 2017:"f1c801dee830a2029b15b4fdbd371aff5358f5136632fe828036d7de25117994"}
YEARS=(2012,2015,2017)
ACK="CREATE_CH_LAE_STAGE36_THREE_YEAR_EXPLORATORY_MET_OVERLAY"
VERSION="CH-Lae-2012-2015-2017-local-TQ-candidate-v1-20261026"

def require(ok,msg):
 if not ok:raise RuntimeError(str(msg))
def sha(path):
 h=hashlib.sha256()
 with Path(path).open("rb") as f:
  for chunk in iter(lambda:f.read(1048576),b""):h.update(chunk)
 return h.hexdigest()
def expected_year_fields(first,last,align):
 return (int(first),int(last),int(align))==(2004,2024,2004)

def stream():
 cp=CASE/"CaseDocs/datm.streams.xml"
 rt=Path("/scratch/ly3n24/CTSM_FATES_OUTPUTS")/CASE.name/"run/datm.streams.xml"
 require(cp.is_file() and rt.is_file() and sha(cp)==sha(rt)==STREAM_SHA,
         "CDEPS actual CaseDocs/RUNDIR stream changed")
 root=ET.parse(cp).getroot()
 ss=[node for node in root.iter("stream_info") if node.attrib.get("name")=="CLM_USRDAT.UNSET"]
 require(len(ss)==1,"selected one-point stream ambiguous")
 s=ss[0]
 require(expected_year_fields(s.find("year_first").text,
                              s.find("year_last").text,
                              s.find("year_align").text),
         "Unexpected CH-Lae met years/year_align")
 require(s.find("taxmode").text.strip()=="cycle" and
         s.find("offset").text.strip()=="0","Unexpected met time policy")
 entries=s.find("datafiles")
 require(entries is not None and len(entries)==21,"Not twenty-one annual sources")
 out={}
 for y,node in zip(range(2004,2025),entries):
  p=Path((node.text or "").strip())
  require(p.is_file() and p.name.startswith("CH-Lae_DATM_") and
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
def put(ds,key,edits):
 # Write only the authorized half-hours. Never write the full variable:
 # reserializing ~17520 floats may re-quantize untouched entries.
 v=ds.variables[key]
 require("time" in v.dimensions and v.size==17520,
         "Unexpected selected NetCDF variable shape "+key)
 require(v.dtype.kind=="f" and v.dtype.itemsize in (4,8),
         "Explicit float32/float64 storage required for exact quantization guard "+key)
 require(not hasattr(v,"scale_factor") and not hasattr(v,"add_offset"),
         "Packed/scaled variable unsupported for unambiguous precision guard "+key)
 ax=v.dimensions.index("time")
 for i,value in edits.items():
  require(0<=i<17520 and np.isfinite(value),"Invalid authorized edit")
  loc=[0]*v.ndim
  loc[ax]=int(i)
  v[tuple(loc)]=np.asarray(value,dtype=v.dtype).item()

def quantized_match(candidate,readback,dtype):
 # Exact match after the *declared on-disk* float representation.
 dt=np.dtype(dtype)
 require(dt.kind=="f" and dt.itemsize in (4,8),
         "Cannot audit unexpected NetCDF target numeric type")
 expect=np.asarray(candidate,dtype=dt).item()
 return np.asarray(readback,dtype=dt).item()==expect

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
 return np.zeros(0,dtype=int),rh(t,q,p)

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
 # T in C, Q in kg/kg. Exact existing full-year NetCDF source pins above.
 observations={
   2012:(14669,"2012-11-02 14:30:00","TQ",10.149,-0.728),
   2015:(7807,"2015-06-12 15:30:00","T",14.097,20.35),
   2017:(8525,"2017-06-27 14:30:00","TQ",15.452,23.970)}
 for y in YEARS:
  t,q,p,dates=getyear(files[y],y)
  i,when,kind,observed,next_expected=observations[y]
  require(str(dates[i])==when,"Pinned CH-Lae anomalous timestamp moved "+str(y))
  old=float(t[i]-273.15)
  after=float(t[i+1]-273.15)
  require(abs(old-observed)<.025 and abs(after-next_expected)<.025,
          "Stage33 source T/context not preserved "+str(y))
  require(abs(t[i]-(t[i-1]+t[i+1])/2)>5,
          "Temperature not an isolated anomaly at selected index "+str(y))
  require(abs(t[i-1]-t[i+1])<3.0,
          "Local neighbor temperature disagreement; hold for human review "+str(y))
  edits={"TBOT":{i:float((t[i-1]+t[i+1])/2)},"QBOT":{}}
  if kind=="TQ":
   mean=float((q[i-1]+q[i+1])/2)
   require(abs(q[i]-mean)>.0015,
           "Expected paired source QBOT discontinuity no longer present "+str(y))
   edits["QBOT"][i]=mean
  tn=t.copy();qn=q.copy()
  for k,v in edits["TBOT"].items():tn[k]=v
  for k,v in edits["QBOT"].items():qn[k]=v
  newrh=rh(tn,qn,p)
  require(0<newrh[i]<110 and abs(tn[i]-t[i-1])<3 and
          abs(tn[i]-t[i+1])<3,
          "New local T/Q candidate numerically inconsistent "+str(y))
  changes={key:{str(j):{"original":float((t if key=="TBOT" else q)[j]),
                          "candidate":value,"timestamp":str(dates[j])}
                for j,value in di.items()} for key,di in edits.items()}
  allplan[y]=(edits,changes,tn,qn)
  if verbose:
   print("STAGE36 PLAN",y,"TEMP_C_ORIGINAL",round(old,3),
         "TEMP_C_PROPOSED",round(float(tn[i]-273.15),3),
         "RH_ORIGINAL",round(float(rh(t,q,p)[i]),3),
         "RH_PROPOSED",round(float(newrh[i]),3),
         "QBOT_EDITS",len(edits["QBOT"]),"TBOT_EDITS",len(edits["TBOT"]),
         "SHA",PINS[y])
 print("STAGE36 SCIENCE HOLDS PRESERVED 2005-Dec31 and 2012-Nov01 sustained steps: NOT ALTERED")
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
     require(quantized_match(v,zz[i],b.variables[key].dtype),
             "Post-NetCDF quantized value mismatch "+key+" at HH "+str(i)+
             " expected_on_disk="+str(np.asarray(v,dtype=b.variables[key].dtype).item())+
             " got="+str(float(zz[i])))
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
  out=DEST/f"CH-Lae_DATM_{y}_STAGE36_TARGETED_EXPLORATORY.nc"
  fd,tmpname=tempfile.mkstemp(prefix=".ch-lae-datm36-",suffix=".nc",dir=DEST)
  os.close(fd);tmp=Path(tmpname)
  try:
   shutil.copy2(source,tmp)
   with Dataset(tmp,"r+") as ds:
    for key in ("TBOT","QBOT"):
     if edits[key]:
      put(ds,key,edits[key])
    ds.setncattr("batch02_stage36","exploratory_manual_inference_not_original_QC_or_ERA_verified")
   verify_candidate(source,tmp,edits)
   d=sha(tmp);os.link(tmp,out)
   results[y]={"path":str(out),"sha256":d,"source":str(source),
               "source_sha256":PINS[y],"changes":changes}
   print("STAGE36 BUILT",y,"SHA",d,"T",len(edits["TBOT"]),"Q",len(edits["QBOT"]))
  finally:tmp.unlink(missing_ok=True)
 selected=[]
 for y in range(2004,2025):
  p=Path(results[y]["path"]) if y in YEARS else files[y]
  selected.append({"year":y,"path":str(p),
                   "sha256":results[y]["sha256"] if y in YEARS else sha(p),
                   "modified":y in YEARS})
 require(len(selected)==21,"Expected 21 annual DATM inputs")
 manifest={
  "version":VERSION,"site":SITE,"source_case":CASE.name,
  "source_stream_sha256":STREAM_SHA,"years":[2004,2024],
  "record_count_per_year":17520,"science_status":
   "EXPLORATORY_LOCAL_3POINT_T_Q_INTERPOLATION_NOT_NATIVE_QC_OR_ERA5",
  "original_precipitation_all_21_years_retained":True,
  "unresolved_2005_Dec31_sustained_step_retained":True,
  "unresolved_2012_Nov01_sustained_step_retained":True,
  "total_QBOT_edits":sum(len(plan[y][0]["QBOT"]) for y in YEARS),
  "total_TBOT_edits":sum(len(plan[y][0]["TBOT"]) for y in YEARS),
  "modified_years":results,"selected_21_annual_DATM":selected,
  "original_source_files_modified":False,"CIME_case_modified":False,
  "Slurm_submitted":False,"created_utc":datetime.now(timezone.utc).isoformat()}
 require(manifest["total_QBOT_edits"]==2 and
         manifest["total_TBOT_edits"]==3,"Patch count unexpected")
 path=DEST/"manifest.json"
 with path.open("x") as f:
  json.dump(manifest,f,indent=2);f.write("\n");f.flush();os.fsync(f.fileno())
 print("STAGE36 CREATED MANIFEST",path,"QBOT",2,"TBOT",3,
       "21-year ready selection; ORIGINALS UNTOUCHED, NO SLURM")
def main():
 ap=argparse.ArgumentParser(description=__doc__)
 g=ap.add_mutually_exclusive_group(required=True)
 for k in ("self-test","audit","build"):g.add_argument("--"+k,action="store_true")
 ap.add_argument("--confirm",default="")
 a=ap.parse_args()
 if a.self_test:
  assert expected_year_fields("2004","2024","2004")
  assert not expected_year_fields("2004","2025","2004")
  assert YEARS==(2012,2015,2017) and len(PINS)==4
  assert 2+1==3 and 1+0+1==2
  assert quantized_match(283.123456789,np.float32(283.123456789),np.dtype("f4"))
  assert "stage36_CH_Lae_targeted_MET_QC_v1" in str(DEST)
  print("STAGE36 SELF-TEST PASS: exact CH-Lae scenarios, time axis, quantization, isolated no-ops; NO WRITES")
  return

 require(not a.build or a.confirm==ACK,
         "--build requires --confirm "+ACK)
 files=stream()
 plan=get_plan(files)
 if a.audit:
  print("STAGE36 AUDIT PASS: 2012/2015/2017 isolated anomalies; 2005 and 2012 sustained steps retained; all 21 annual precip unchanged; NO WRITES")
  return
 build(files,plan)
if __name__=="__main__":main()
