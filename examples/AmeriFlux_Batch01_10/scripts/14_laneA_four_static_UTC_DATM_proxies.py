#!/usr/bin/env python3
"""AmeriFlux Batch01 Stage14 — 4 STATIC-height technical UTC forcing pilots.

NO REPROCESSING of Stage80 selected meteorology. Use the 4 sites' existing
Stage81 annual NOLEAP 30-min NetCDF (Stage82 already SHA-validated for all
213 years). Treat Stage81 'time=local interval START' as an explicit
CA-TP4-like PILOT ASSUMPTION, not universally source-verified. Add +15 min
midpoint and local-standard to UTC phase conversion (BIF UTC_OFFSET by site),
including entire 4/5/8-hour cyclic year boundary and unchanged meteorological
values, and a distinct unverified site ZBOT BASE sensor height candidate.

Sites: BR-Ma2, CA-Ca3, CA-LP1, US-Bar.
Do not build PFT/surfaces or modify CIME/Slurm.
--self-test pure index/year mathematical checks
--check read-only BIF, Stage31/81/82 receipts and original 4-site files
--build-preview --outdir NEW --ack-four-static-sensor-proxies:
  independent site/year NetCDF, detached CDEPS stream, provenance manifest;
  validates every new field against 2 source years and noon/solar for 3 years.
"""
from __future__ import annotations
import argparse,csv,hashlib,json,math,shutil,xml.etree.ElementTree as ET
from pathlib import Path
import numpy as np
from netCDF4 import Dataset

R=Path("/iridisfs/scratch/ly3n24/CLM_FATES")
AMF=R/"experiments/AmeriFlux_MultiSite_10"
ST81=AMF/"reports/stage81_DATM_technical_20261024T162235Z/manifest.json"
ST82=AMF/"reports/stage82_DATM_case_integration_preflight_20261024T231124502670Z/manifest.json"
ST31=AMF/"reports/stage31_provisional_ZBOT_scenarios_20261022T022341481986Z/01_provisional_site_height_policies.json"
SRC_BIF=R/"sites/MY_EC_SITE"
S11=AMF/"reports/stage11_CA_TP4_DATM_UTC_20261025T080240825734395Z"
EXPECTED={"BR-Ma2":(1999,2016,-4.0,51.1),
          "CA-Ca3":(2001,2024,-8.0,12.0),
          "CA-LP1":(2007,2024,-8.0,26.0),
          "US-Bar":(2004,2023,-5.0,23.8)}
REQUIRED_MET=("FLDS","FSDS","PRECTmms","PSRF","QBOT","RH","SHUM","TBOT","WIND")
VARS={**{k:1 for k in REQUIRED_MET},"ZBOT":1}
CDEPS_MAP={"PRECTmms":"Faxa_precn","FSDS":"Faxa_swdn","ZBOT":"Sa_z",
           "TBOT":"Sa_tbot","WIND":"Sa_wind","QBOT":"Sa_shum",
           "PSRF":"Sa_pbot","FLDS":"Faxa_lwdn"}
N=17520
DATA=R/"sites/MY_EC_SITE"
TEMPLATE=S11/"CA-TP4/datm.streams.CA-TP4.UTC_CANDIDATE_NOT_ACTIVATED.xml"
ST11_META=S11/"manifest.json"

def fail(msg):raise RuntimeError(str(msg))
def jload(path):
 if not path.is_file():fail("Missing pinned input "+str(path))
 return json.loads(path.read_text(encoding="utf-8"))
def sha(p):
 h=hashlib.sha256()
 with p.open("rb") as f:
  for block in iter(lambda:f.read(1<<20),b""):h.update(block)
 return h.hexdigest()
def prev_year(y,first,last):
 return last if y==first else y-1
def slots(y,first,last,shift):
 return [(prev_year(y,first,last),N-shift+i) if i<shift
         else (y,i-shift) for i in range(N)]
def selftest():
 assert len(EXPECTED)==4 and sum(b-a+1 for a,b,_,_ in EXPECTED.values())==80
 for site,(a,b,tz,zbot) in EXPECTED.items():
  shift=int(-tz*2)
  assert 1<=shift<=N
  assert slots(a,a,b,shift)[0]==(b,N-shift)
  assert slots(a,a,b,shift)[shift-1]==(b,N-1)
  assert slots(a,a,b,shift)[shift]==(a,0)
  assert len({pair for y in range(a,b+1) for pair in slots(y,a,b,shift)})==(b-a+1)*N
 print("SELF-TEST PASS: 4 Lane A, 80 years, three UTC offsets (-4,-8,-5), per-site cyclic HH bijections")

def clock_bif(site):
 raw=DATA/site/"forcing/raw"
 choices=sorted(raw.glob(f"AMF_{site}_FLUXNET_*/AMF_{site}_FLUXNET_BIF_*.csv"))
 if len(choices)!=1:fail(site+": expected one exact-release BIF CSV")
 p=choices[0]
 meta={}
 with p.open(encoding="utf-8-sig",newline="") as f:
  rd=csv.DictReader(f)
  if not {"VARIABLE","DATAVALUE"}.issubset(rd.fieldnames or []):
   fail(site+": raw AmeriFlux BIF format changed")
  for row in rd:
   name=(row.get("VARIABLE") or "").strip().upper()
   val=(row.get("DATAVALUE") or "").strip()
   if name in ("UTC_OFFSET","LOCATION_LAT","LOCATION_LONG") and val:
    meta.setdefault(name,set()).add(val)
 if any(len(meta.get(k,set()))!=1 for k in ("UTC_OFFSET","LOCATION_LAT","LOCATION_LONG")):
  fail(site+": UTC offset or BIF location ambiguous")
 return {k:float(next(iter(v))) for k,v in meta.items()},sha(p)

def input_manifest():
 s81=jload(ST81);s82=jload(ST82);s31=jload(ST31)
 if s81.get("stage")!=81 or s81.get("all_annual_netcdf_files")!=213:
  fail("Original Stage81 entire ten-station inventory changed")
 if s82.get("stage")!=82 or s82.get("verified_annual_files_sha256")!=213 or s82.get("input_stage81_manifest_sha256")!=sha(ST81):
  fail("Original Stage82 SHA-verified census not intact")
 if s31.get("method")!="AmeriFlux_STAGE31_BASE_STATIC_DYNAMIC_POLICY_SCENARIOS":
  fail("Stage31 original BASE measurement-height science policy changed")
 site_records={x["site"]:x for x in s81["sites"]}
 if len(site_records)!=10:fail("Original Stage81 site count changed")
 meta=s31.get("provisional_sensor_policy",{})
 sites={}
 for site,(first,last,expectedtz,height) in EXPECTED.items():
  row=site_records[site]
  if (row.get("years")!=f"{first}-{last}" or
      row.get("years_written")!=last-first+1):
   fail(site+": Stage81 year list changed")
  policy=meta.get(site)
  if not policy or policy.get("candidate_ZBOT_mode")!="STATIC" or policy.get("dated_events"):
   fail(site+": not a static candidate under pinned Stage31")
  if (abs(float(policy["baseline_m"])-height)>1e-5 or
      policy.get("FLUXNET_TA_F_sensor_crosswalk")=="VERIFIED"):
   fail(site+": sensor candidate does not match previous unverified BASE policy")
  actual,rawsha=clock_bif(site)
  if abs(actual["UTC_OFFSET"]-expectedtz)>1e-9:
   fail(site+": original BIF UTC offset unexpectedly changed")
  recs=row.get("annual_files",[])
  if len(recs)!=last-first+1:fail(site+": Stage81 annual_files incomplete")
  allfiles=[]
  for year,item in zip(range(first,last+1),recs):
   p=Path(item["file"])
   if year!=item["year"] or not p.is_file() or not p.is_absolute():
    fail(site+": annual NC missing/out of order "+str(year))
   allfiles.append((year,p,item["sha256"]))
  surfloc=(float(row["point_grid_lat"]),float(row["point_grid_lon"])%360)
  bifloc=(actual["LOCATION_LAT"],actual["LOCATION_LONG"]%360)
  if abs(surfloc[0]-bifloc[0])>0.1 or abs((surfloc[1]-bifloc[1]+180)%360-180)>0.1:
   fail(site+": model site and BIF point location differ >0.1 deg")
  sites[site]={"years":(first,last),"tz":expectedtz,"ZBOT":height,
    "BIF_sha256":rawsha,"BIF_lat_lon":bifloc,
    "point_lat_lon":surfloc,"NC":allfiles,"policy":policy}
 return sites

def check_nc(sites,allsha=False):
 for site,obj in sites.items():
  yfiles=obj["NC"]
  test=yfiles if allsha else [yfiles[0],yfiles[-1]]
  for year,path,digest in test:
   if sha(path)!=digest:fail(f"{site} Stage81 source annual NC SHA changed {year}")
  for year,path,digest in (yfiles[0],yfiles[-1]):
   with Dataset(path) as ds:
    time=np.asarray(ds.variables["time"][:],dtype=float)
    if (len(time)!=N or getattr(ds.variables["time"],"calendar","")!="noleap" or
        not np.allclose(time[[0,1,-1]],[0,1/48,(N-1)/48],atol=1e-11,rtol=0)):
     fail(site+": original Stage81 TIME is not 30min source-start")
    if not set(REQUIRED_MET).issubset(ds.variables) or "ZBOT" in ds.variables:
     fail(site+": expected original Stage81 met fields without ZBOT")
    for name in REQUIRED_MET:
     if ds.variables[name].dimensions!=("time","lat","lon"):
      fail(site+": unexpected source time/geo dimensions "+name)
    lat=float(ds.variables["LATIXY"][:].ravel()[0])
    lon=float(ds.variables["LONGXY"][:].ravel()[0])%360
    if abs(lat-obj["point_lat_lon"][0])>1e-5 or abs(lon-obj["point_lat_lon"][1])>1e-5:
     fail(site+": source annual model point differs from Stage81 selected surface")
  print("INPUT PASS",site,"YEARS",obj["years"],"BIF_UTC",obj["tz"],
        "static-ZBOT-PROXY",obj["ZBOT"],"m; initial/end NetCDF+coords verified")
 if allsha:print("ALL 80 SOURCE YEAR NETCDF SHA PASSED")
 else:print("Stage82 receipt covers 213 SHA; first/last site annual files independently rehashed")

def stream_template():
 m=jload(ST11_META)
 if m.get("stage")!=11 or m.get("site")!="CA-TP4" or m.get("slurm_submitted") is not False:
  fail("Stage11 independent UTC template provenance changed")
 if sha(TEMPLATE)!=m.get("detached_CDEPS_stream_sha256"):
  fail("Exact original Stage11 detached CDEPS template changed")
 root=ET.parse(TEMPLATE).getroot()
 x=[v for v in root.iter("stream_info") if v.attrib.get("name")=="CLM_USRDAT.UNSET"]
 if len(x)!=1:fail("No unique 1PT CDEPS reference source")
 mapping={}
 for v in x[0].find("datavars"):
  pair=(v.text or "").split()
  if len(pair)!=2:fail("Malformed reference stream datavars")
  mapping[pair[0]]=pair[1]
 if any(mapping.get(k)!=v for k,v in CDEPS_MAP.items()):
  fail("Reference CDEPS eight mapped fields changed")
 return root,x[0]

def equality(x,y):
 x=np.ma.asarray(x);y=np.ma.asarray(y)
 return np.array_equal(np.ma.getmaskarray(x),np.ma.getmaskarray(y)) and np.array_equal(
   np.ma.filled(x,0),np.ma.filled(y,0),equal_nan=True)

def reindex_one(year,files,dir_year,shift,height,src_prev):
 shutil.copy2(files,dir_year)
 with Dataset(files) as today,Dataset(src_prev) as yesterday,Dataset(dir_year,"r+") as new:
  v=new.variables["time"]
  v[:]=np.arange(N,dtype=float)/48.+1/96
  v.long_name="UTC site 30-min interval midpoint; time source FLUXNET local standard UTC shifted"
  z=new.createVariable("ZBOT","f8",new.variables["QBOT"].dimensions,zlib=True,complevel=2)
  z.units="m";z.long_name="PROVISIONAL STAGE31 BASE ambient TA sensor height; TA_F crosswalk UNVERIFIED"
  z[:]=height
  for var in REQUIRED_MET:
   target=new.variables[var]
   target[:shift,...]=yesterday.variables[var][N-shift:N,...]
   target[shift:N,...]=today.variables[var][:N-shift,...]
  new.time_axis_policy="UTC_NC_NOLEAP_TIME_MIDPOINT_30MIN"
  new.original_label_policy="ASSUMED_STAGE81_START_LABEL_LOCAL_STANDARD_TIME_NEEDS_RAW_TA_F_TIME_SOURCE_CONFIRMATION"
  new.utc_year_start_boundary="RECYCLE_PREVIOUS_YEAR_LAST_UTC_OFFSET_HOURS_FOR_FIRST_RECORDS"
  new.height_policy="STATIC_BASE_SENSOR_PROXY_NOT_VERIFIED_FLUXNET_TA_F"
  new.site_science_status="TECHNICAL_ONLY_DO_NOT_USE_FOR_PRODUCTION"
 with Dataset(files) as today,Dataset(src_prev) as yesterday,Dataset(dir_year) as new:
  if not np.allclose(new.variables["time"][[0,1,N-1]],
            [1/96,1/48+1/96,(N-1)/48+1/96],rtol=0,atol=1e-10):
   fail("Bad UTC midpoint NetCDF "+str(dir_year))
  if not np.allclose(new.variables["ZBOT"][[0,123,N-1],0,0],height,rtol=0,atol=1e-6):
   fail("Bad provisional ZBOT "+str(dir_year))
  for var in REQUIRED_MET:
   if (not equality(new.variables[var][:shift,...],yesterday.variables[var][N-shift:N,...]) or
       not equality(new.variables[var][shift:N,...],today.variables[var][:N-shift,...])):
    fail("Any meteorological field corrupted by UTC permutation "+var+" "+str(dir_year))

def solar_bad_fraction(path,lat,lon):
 with Dataset(path) as nc:
  t=np.asarray(nc.variables["time"][:],dtype=float)
  sw=np.asarray(nc.variables["FSDS"][:,0,0],dtype=float)
 if len(t)!=N or not np.isfinite(sw).all() or np.sum(sw)<=0:fail("Bad solar test input")
 if lon>180:lon-=360
 mins=(t%1)*1440;doy=np.floor(t)+1
 gamma=2*np.pi/365*(doy-1+(mins/60-12)/24)
 eq=229.18*(0.000075+0.001868*np.cos(gamma)-0.032077*np.sin(gamma)
  -0.014615*np.cos(2*gamma)-0.040849*np.sin(2*gamma))
 decl=(0.006918-0.399912*np.cos(gamma)+0.070257*np.sin(gamma)
  -0.006758*np.cos(2*gamma)+0.000907*np.sin(2*gamma)
  -0.002697*np.cos(3*gamma)+0.00148*np.sin(3*gamma))
 hour=np.deg2rad(((mins+eq+4*lon)%1440)/4-180)
 phi=math.radians(lat)
 cosz=np.sin(phi)*np.sin(decl)+np.cos(phi)*np.cos(decl)*np.cos(hour)
 nighttime=cosz<math.sin(math.radians(-3))
 return 100.*float(np.sum(sw[nighttime])/np.sum(sw))

def build(out,sites):
 if out.exists() or out.is_symlink():fail("Refusing existing output root")
 out.mkdir(parents=True,exist_ok=False)
 summary={"stage":14,"lane":"AMERIFLUX_BATCH01_4_STATIC_ZBOT_TECHNICAL",
          "original_stage81_manifest_sha256":sha(ST81),"original_stage82_manifest_sha256":sha(ST82),
          "original_stage31_height_policy_sha256":sha(ST31),
          "stage11_CDEPS_UTC_template_sha256":sha(TEMPLATE),
          "model_case_modified":False,"model_case_created":False,"slurm_submitted":False,
          "source_timestamp_start_crosswalk_verified":False,
          "height_sensor_TA_F_crosswalk_verified":False,
          "site_FATES_PFT_surface_created":False,
          "scientific_production_release":False,"sites":[]}
 for site,obj in sites.items():
  first,last=obj["years"];shift=int(-obj["tz"]*2)
  source={y:p for y,p,_ in obj["NC"]}
  siteout=out/site/"yearly";siteout.mkdir(parents=True)
  rows=[]
  sampleyears={first,(first+last)//2,last}
  for year,p,_ in obj["NC"]:
   target=siteout/f"{year}.nc"
   reindex_one(year,p,target,shift,obj["ZBOT"],source[prev_year(year,first,last)])
   if year in sampleyears:
    bad=solar_bad_fraction(target,*obj["point_lat_lon"])
    print("UTC FSDS NIGHT FRACTION",site,year,round(bad,3),"%")
    if bad>10:fail(site+": solar phase not plausible for UTC; STOP all station case work")
   rows.append({"year":year,"path":str(target),"sha256":sha(target),
       "input_sha256":sha(p),"prior_local_year":prev_year(year,first,last)})
   print("UTC SOURCE PASS",site,year,flush=True)
  root,stream=stream_template()
  for key,value in (("year_first",first),("year_last",last),("year_align",first),("offset",0)):
   x=stream.find(key)
   if x is None:fail("Detached CDEPS stream missing "+key)
   x.text=str(value)
  data=stream.find("datafiles")
  if data is None:fail("Detached stream no datafiles")
  for v in list(data):data.remove(v)
  for row in rows:ET.SubElement(data,"file").text=row["path"]
  pathxml=out/site/f"datm.streams.{site}.UTC_TECHNICAL_NOT_ACTIVATED.xml"
  ET.ElementTree(root).write(pathxml,encoding="utf-8",xml_declaration=True)
  doc={"site":site,"start_year":first,"last_year":last,
       "source_BIF_UTC_OFFSET":obj["tz"],"UTC_SHIFT_HALFHOURS":shift,
       "ZBOT_STATIC_M_PROVISIONAL":obj["ZBOT"],"SOURCE_BASE_POLICY":obj["policy"],
       "source_BIF_sha256":obj["BIF_sha256"],
       "source_point_lat_lon":obj["point_lat_lon"],
       "files":rows,"detached_stream":str(pathxml),
       "detached_stream_sha256":sha(pathxml),
       "time_centering_policy":"SITE_LOCAL_START_PLUS_15MIN_AND_UTC_SHIFT_UNCONFIRMED_ORIGINAL_TIMESTAMP_CROSSWALK",
       "model_coupler_clock_verified":False,
       "source_TA_F_sensor_height_verified":False,
       "model_case_created":False,"slurm_submitted":False,
       "production_release":False}
  (out/site/"manifest.json").write_text(json.dumps(doc,indent=2)+"\n")
  summary["sites"].append({"site":site,"years":len(rows),"manifest":str(out/site/"manifest.json"),"manifest_sha256":sha(out/site/"manifest.json")})
  print("SITE COMPLETE",site,"UTC YEARS",len(rows),"STATIC ZBOT",obj["ZBOT"])
 (out/"manifest.json").write_text(json.dumps(summary,indent=2)+"\n")
 print("STAGE14 SUCCESS: FOUR independent UTC technical-forcing candidates, all original Stage81 unchanged")
 print("NO site PFT surface, NO CIME case, NO Slurm. Output",out)

def main():
 ap=argparse.ArgumentParser(description=__doc__)
 g=ap.add_mutually_exclusive_group(required=True)
 g.add_argument("--self-test",action="store_true")
 g.add_argument("--check",action="store_true")
 g.add_argument("--build-preview",action="store_true")
 ap.add_argument("--outdir",type=Path)
 ap.add_argument("--ack-four-static-sensor-proxies",action="store_true")
 args=ap.parse_args()
 if args.self_test:selftest();return
 if args.check and (args.outdir or args.ack_four_static_sensor_proxies):
  ap.error("--check is read-only")
 if args.build_preview and (args.outdir is None or not args.ack_four_static_sensor_proxies):
  ap.error("--build-preview requires --outdir NEW and --ack-four-static-sensor-proxies")
 sites=input_manifest()
 check_nc(sites,allsha=args.build_preview)
 stream_template()
 print("STAGE14 INPUT CHECK PASS: four existing Stage81 site ensembles, timestamp basis is a PROXY.")
 if args.check:return
 build(args.outdir.resolve(),sites)

if __name__=="__main__":main()
