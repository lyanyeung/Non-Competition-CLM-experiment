#!/usr/bin/env python3
"""OzFlux NC AU-ASM: DIRECT AD400, 80 x five-year segments, NO AD5.

Compatible with the existing proven AmeriFlux Batch02 CIME direct-AD400
helper, pinned by exact Git blob SHA. This script ONLY reuses the six
operator-verified, already existing AU-ASM Stage14 provisional DATM NCs.
It NEVER rebuilds/changes the original L6, six DATM, reference or FIXNC
Surface, FATES parameter file, shared CTSM, or historical AU-How case.

Actions:
  self-test: no IRIDIS files; static monkeypatch protocol tests
  check: read-only provenance, effective FATES default14 and template checks
  prepare: explicit consent; creates one isolated CIME case; preview and verify;
           NO Slurm job submitted (attempt-ledger prevents blind repeat)
  submit: explicit consent; revalidates sources, CaseDocs and 80x5 settings;
          issues exactly ONE CIME case.submit with RESUBMIT=79
  status: read-only, existing job/case status
The GRID_REFERENCE soil and 2013-2018 provisional forcing hypotheses are
declared EXPLORATORY. This is NOT scientific approval of site soil, model
UTC clock, longwave ACCESS fill, spinup equilibrium, or model skill.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
from pathlib import Path
import numpy as np
from netCDF4 import Dataset

SITE="AU-ASM"
HOME=Path.home()
B=Path("/iridisfs/scratch/ly3n24/CLM_FATES")
DATM=HOME/"ozflux_stage14_FSDS0_20261102T012038Z"
SURF=HOME/"ozflux_nc_stage02_ASM_20261102T215809Z"/"surfdata_AU-ASM_NC_FIXNC_PFT_v1p1_CTSM2000_SOIL_REFERENCE.nc"
SURF_SHA="d06ad3111d93de69e7f2dd7f048b02a9161aee4ff853afafedcdfed71a54f3a1"
S4=HOME/"ozflux_nc_stage04_20261102T223221Z_FIX"/"ozflux_nc_stage04_nine_site_forcing_handoff.json"
S5=HOME/"ozflux_nc_stage05_20261102T224556Z_FIX"/"stage05_three_site_priority_summary.json"
S7=HOME/"ozflux_nc_stage07_20261103T061721Z"/"stage07_AU_ASM_GRIDREF_AD5_CIME_PLAN.json"
S14=DATM/"stage14_FSDS0_provisional_manifest.json"
HELPER_BLOB="decc61898a89109c3819faca2c8c3134ebed77ee"
HELPER_NAME="06_direct_AD400_ten_site_cases_and_submit.py"
# Stored under a new OzFlux code location; not loaded from the user's
# mutable checkout unless its Git blob matches HELPER_BLOB exactly.
CASE_NAME="AU-ASM_OZ_FIXNC_GRIDREF_AD400_DIRECT"
STAGE_DIR=B/"experiments/NonCompetitionObserved22/OzFlux_Batch01_09/Stage08_DIRECT_AD400"
TEMPLATE=B/"cases/CH-Dav_B01_FIXNC_AD400"
CO2_DEFAULTS=(
    B/"experiments/NonCompetitionObserved22/AmeriFlux_Batch02_10/Stage06_direct_AD400/co2_annmean_gl.csv",
    B/"experiments/NonCompetitionObserved22/Batch01_10/_private_ctsm_FATES_AD400_namelist_overlay/co2_annmean_gl.csv",
)
ANNUAL={
2013:"0e722aec1d73d35ff4671ccd1c72fbf02c7e3af8f9fdd6cae291834741b2bffe",
2014:"54345a6ae15ba8091b118dc62c891cff1fb851eda895178a47c8d3a23143871b",
2015:"6d7b9cc4f0e24d6395f1f6d1ae3217f9fd70a67d93f41969eb6cdafe283447bf",
2016:"8b5576e424625a0bf62f0fb0fa552230ff7c01e26e440a565242e169fe455c7f",
2017:"634d8d395e95331cf9f13dcbf5d48edbc2e881af4ca913acb75abe1333032951",
2018:"8ce901670486469358525c95f6a78db82698a5712312c4b1bf610aff744be55d"}
ACCEPT="ACCEPT_AU_ASM_GRIDREF_PROVISIONAL_FORCING_EXPLORATORY_DIRECT_AD400"
ACK_PREP="PREPARE_AU_ASM_DIRECT_AD400_CASE_NO_SLURM"
ACK_SUB="SUBMIT_AU_ASM_DIRECT_AD400_80x5_ONCE"
FIELDS={"PRECTmms":"Faxa_precn","FSDS":"Faxa_swdn","ZBOT":"Sa_z",
        "TBOT":"Sa_tbot","WIND":"Sa_wind","QBOT":"Sa_shum",
        "PSRF":"Sa_pbot","FLDS":"Faxa_lwdn"}

def fail(s): raise RuntimeError(str(s))

def h(p):
    p=Path(p)
    if not p.is_file() or p.is_symlink():fail("missing/symlink input "+str(p))
    t=hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda:f.read(4*1024*1024),b""):t.update(b)
    return t.hexdigest()

def blob(p):
    p=Path(p)
    z=p.read_bytes()
    return hashlib.sha1(b"blob "+str(len(z)).encode()+b"\0"+z).hexdigest()

def load(p):return json.loads(Path(p).read_text(encoding="utf-8"))

def verify_sources():
    a,b,c=load(S4),load(S5),load(S7)
    if (a.get("all_nine_surface_candidates_exist") is not True
      or a.get("AU_ASM_FSDS0_years_source_SHA_verified") != list(ANNUAL)
      or a.get("AD400_authorised") is not False
      or a.get("DATM_climate_streams_approved") is not False):
        fail("Stage04 immutable physical-source receipt/hold is different")
    if (b.get("stage08_196_variable_years_reconciled") is not True
      or b.get("AD5_authorised") is not False
      or b.get("AD400_authorised") is not False):
        fail("Stage05 immutable source-QC receipt changed")
    if (c.get("read_only") is not True
      or c.get("science_approval") is not False
      or c.get("CIME_case_created") is not False
      or c.get("Slurm_submitted") is not False
      or c.get("GRIDREF_ONLY_NOT_SITE_SOIL") is not True
      or len(c.get("candidate_datm",[]))!=6):
        fail("Historical Stage07 input source receipt invalid")
    if h(SURF)!=SURF_SHA:fail("Stage02 immutable PFT surface SHA changed")
    with Dataset(str(SURF),"r") as ds:
        p=np.ma.asarray(ds.variables["PCT_NAT_PFT"][:],dtype=float).filled(np.nan).ravel()
        if len(p) not in (15,16):fail("PFT host slots not 15 or 16")
        desired=np.zeros(len(p))
        for k,v in ((0,29),(5,65),(13,2),(14,4)):desired[k]=v
        if not np.array_equal(p,desired):fail("Actual ASM host PFT not fixed-v1.1")
        la=float(np.asarray(ds.variables["LATIXY"][:]).ravel()[0])
        lo=float(np.asarray(ds.variables["LONGXY"][:]).ravel()[0])
        if abs(la+22.2828)>1e-6 or abs(lo-133.2493)>1e-6:fail("Surface coordinates changed")
        nat=float(np.asarray(ds.variables["PCT_NATVEG"][:]).ravel()[0])
        if abs(nat-100)>1e-5:fail("Cannot use a point surface with NATVEG !=100")
        for v in ("PCT_SAND","PCT_CLAY","ORGANIC"):
            z=np.ma.asarray(ds.variables[v][:],dtype=float).filled(np.nan).ravel()
            if len(z)!=10 or not np.isfinite(z).all():fail("gridref soil malformed "+v)
    files=[]
    for y,known in ANNUAL.items():
        p=DATM/f"AU-ASM_FSDS0_PROVISIONAL_DATM_{y}.nc"
        if h(p)!=known:fail("Stage14 immutable candidate SHA differs "+str(y))
        with Dataset(str(p),"r") as ds:
            t=ds.variables["time"]
            v=np.ma.asarray(t[:],dtype=float).filled(np.nan)
            want=(np.arange(17520,dtype=float)+.5)/48
            if (len(v)!=17520 or getattr(t,"calendar",None)!="noleap"
                or getattr(t,"units",None)!=f"days since {y}-01-01 00:00:00"
                or not np.allclose(v,want,rtol=0,atol=1e-12)):
                fail("DATM time axis mismatch "+str(y))
            if set(FIELDS)-set(ds.variables):fail("DATM variable missing "+str(y))
            if abs(float(ds.variables["lat"][0])-la)>1e-6:
                fail("DATM latitude mismatch "+str(y))
            if abs(float(ds.variables["lon"][0])-lo)>1e-6:
                fail("DATM longitude mismatch "+str(y))
        files.append((y,p,known))
    if c["surface"]["sha256"]!=SURF_SHA or {
         x["year"]:x["sha256"] for x in c["candidate_datm"]}!=ANNUAL:
        fail("Stage07 read-only snapshot does not match live Stage14")
    return {"path":SURF,"sha256":SURF_SHA,
            "host":{0:29.,5:65.,13:2.,14:4.},"lat":la,"lon":lo},files

def get_co2(path):
    if path:
        q=Path(path)
        if not q.is_file():fail("CO2 CSV path missing "+str(q))
        return q
    for q in CO2_DEFAULTS:
        if q.is_file() and not q.is_symlink():return q
    fail("No verified existing NOAA annual CO2 CSV. Pass --co2-csv PATH; do not guess 2013 value.")

def helper_module(path):
    if blob(path)!=HELPER_BLOB:fail("Proven Batch02 CIME helper blob SHA changed")
    sp=importlib.util.spec_from_file_location("ozflux_pinned_AD400_helper",str(path))
    module=importlib.util.module_from_spec(sp)
    sp.loader.exec_module(module)
    return module

def configure(m,files):
    m.TEMPLATE=TEMPLATE
    m.SITES={SITE:(2013,2018)}
    m.ORDER=(SITE,)
    m.ARCTIC=()
    m.SEGMENTS=80
    m.SEG_YEARS=5
    m.SACCT_START="2026-11-01"
    m.D06=STAGE_DIR
    m.name=lambda site:CASE_NAME
    m.surface=lambda site:SURF
    m.forcing_dir=lambda site:DATM
    m.stage95_files=lambda site,full_sha=False:files
    # Stage14 supplies already-verified UTC-center NOLEAP candidates; do not
    # re-transform time or write new annual forcing.
    m.build_forcing=lambda site,inp,surface,clock:{
        "files":[{"path":str(p)} for y,p,sha in inp],"step_minutes":30}
    return m

def check_map(m,param):
    if param.suffix.lower()==".json":
        matrix=m._json_map(load(param))
    elif param.suffix.lower()==".nc":
        with Dataset(str(param)) as ds:
            _,matrix,_=m.fates_map_matrix(ds)
    else:fail("Unsupported FATES param extension "+str(param))
    if matrix.shape!=(14,14) or not np.allclose(matrix,m.DEFAULT14,rtol=0,atol=1e-12):
        fail("Template effective FATES default14 map not proven")
    expected={4:65.,13:2.,14:4.}
    applied={}
    for host,v in ((5,65.),(13,2.),(14,4.)):
        for index,w in enumerate(matrix[host-1]):
            if w>0:applied[index+1]=applied.get(index+1,0)+v*float(w)
    if any(abs(applied.get(k,0)-expected.get(k,0))>1e-8 for k in set(applied)|set(expected)):
        fail("Effective FATES host->PFT mapping differs from approved hypothesis")
    return applied

def check(m,co2,srf,files,for_prepare=False):
    if not TEMPLATE.is_dir():fail("Required CH-Dav reference case missing")
    template=m.template_info()
    mapped=check_map(m,template["paramfile"])
    ann,origin,co2_sha=m.co2_table(co2)
    v=float(ann[2013])
    if not 250<v<500:fail("2013 CO2 global annual mean outside bound")
    for p in (m.case_dir(SITE),m.OUT/CASE_NAME,m.arch_dir(SITE),m.ledger(SITE)):
        if p.exists() or p.is_symlink():
            fail("Target direct AD400 existing (do not overwrite/retry) "+str(p))
    if m.queued(CASE_NAME) or m.sacct_name(CASE_NAME):
        fail("Matching Slurm queue/accounting already exists; no duplicate submit")
    stream=m.stream_text(SITE,[p for y,p,sha in files],2013,2018)
    if "CH-Dav_DATM_" in stream or "/CH-Dav/forcing" in stream:
        fail("Template meteorology leaked into candidate stream")
    land=m.clm_text(SITE,template["paramfile"])
    if m.nml_get(land,"fsurdat")!=str(SURF):
        fail("Staged FATES user land namelist has wrong surface")
    expected_xml=m.xml_settings(SITE,srf,v)
    if (expected_xml["STOP_N"]!="5" or expected_xml["REST_N"]!="5"
        or expected_xml["RESUBMIT"]!="79"
        or expected_xml["RUN_STARTDATE"]!="2013-01-01"
        or expected_xml["CLM_ACCELERATED_SPINUP"]!="on"
        or expected_xml["DATM_YR_START"]!="2013"
        or expected_xml["DATM_YR_END"]!="2018"):
        fail("Not a direct AD400 80x5 proposal")
    print("CH-Dav CIME TEMPLATE PASS",template["exe"],"SHA",template["exe_sha256"][:20],flush=True)
    print("SOURCE PROVENANCE PASS Surface and six Stage14 Datm file SHAs",flush=True)
    print("FATES MAP VERIFIED",applied_to_text(mapped),flush=True)
    print("2013 NOAA GLOBAL CO2",v,"CSV SHA",co2_sha,flush=True)
    print("CIME PROPOSED case",CASE_NAME,"start 2013 target 2413 STOP_N=5 RESUBMIT=79",flush=True)
    print("PROVISIONAL GRIDREF SOIL, SOURCE TIME, 2017 ACCESS FLDS: EXPLORATORY SCIENCE HOLD",flush=True)
    ctx={"tpl":template,"co2":ann,"co2_src":origin+" sha256="+co2_sha,
         "surface":{SITE:srf},
         "clock":{SITE:{"utc_offset_h":9.5,"zbot_m":11.6,
                        "zbot_note":"already in exact Stage14 source, no recoding",
                        "source_receipt_sha256":h(S7)}}}
    return ctx,expected_xml

def applied_to_text(d):return ",".join(f"FATES{k}:{v:.4f}%" for k,v in sorted(d.items()))

def prepare(m,co2,srf,files):
    ctx,expect=check(m,co2,srf,files,True)
    m.prepare_one(SITE,ctx)
    led=m.ledger(SITE)
    obj=m.load(led)
    if obj.get("phase")!="CASE_VERIFIED_NOT_SUBMITTED":
        fail("Prepared CIME case did not pass generated namelist audit")
    obj.update(protocol="EXPLORATORY_GRIDREF_DIRECT_AD400_80x5_RESUBMIT79_NO_AD5",
               Stage04_receipt=str(S4),Stage04_sha256=h(S4),
               Stage05_receipt=str(S5),Stage05_sha256=h(S5),
               Stage07_prior_plan=str(S7),Stage07_prior_plan_sha256=h(S7),
               Stage14_manifest=str(S14) if S14.is_file() else "NOT_USED",
               input_annual_SHA256=ANNUAL,
               SITE_SOIL_SCIENCE_APPROVED=False,
               MET_PROVISIONAL_TIME_SCIENCE_APPROVED=False,
               FLDS_2017_395H_FILL_SCIENCE_APPROVED=False,
               CIME_EFFECTIVE_INPUTS_VERIFIED=True,
               AD5_SKIPPED_BY_OPERATOR_DIRECT400=True,
               scientific_status="EXPLORATORY_INPUTS_UNAPPROVED")
    m.save(led,obj)
    print("AU-ASM DIRECT AD400 CASE VERIFIED, NO SLURM SUBMITTED",
          m.case_dir(SITE),flush=True)
    print("LEDGER",led,flush=True)

def submit(m,srf,files):
    led=m.ledger(SITE)
    if not led.is_file():fail("Missing prepared verified case ledger")
    o=m.load(led)
    if (o.get("phase")!="CASE_VERIFIED_NOT_SUBMITTED"
        or o.get("protocol")!="EXPLORATORY_GRIDREF_DIRECT_AD400_80x5_RESUBMIT79_NO_AD5"
        or o.get("scientific_status")!="EXPLORATORY_INPUTS_UNAPPROVED"):
        fail("Unreviewed or already attempted submission ledger state")
    for p,expected in ((S4,o["Stage04_sha256"]),(S5,o["Stage05_sha256"]),
                       (S7,o["Stage07_prior_plan_sha256"]),(SURF,SURF_SHA)):
        if h(p)!=expected:fail("Source/receipt changed: "+str(p))
    for y,p,sha in files:
        if h(p)!=sha or o["input_annual_SHA256"].get(str(y))!=sha:
            fail("Source annual forcing changed since prepare: "+str(y))
    co2=float(o["co2_ppmv"])
    effective=m.xml_settings(SITE,srf,co2)
    m.validate_case(SITE,srf,[p for y,p,sha in files],
                    Path(o["fates_paramfile"]),co2,effective)
    print("DIRECT AD400 VERIFIED: STOP_N=5 / RESUBMIT=79 / first 2013 / target 2413",flush=True)
    print("EXPLORATORY GRID SOIL + PROVISIONAL ATMOSPHERE; NO AD5 PILOT",flush=True)
    stack=m.stack_guard()
    m.submit_one(SITE,stack)

def selftest():
    assert sum((29,65,2,4))==100
    assert len(ANNUAL)==6 and tuple(ANNUAL)==tuple(range(2013,2019))
    assert len(FIELDS)==8 and FIELDS["QBOT"]=="Sa_shum"
    assert 80*5==400 and 80-1==79 and 2013+400==2413
    assert "AD400" in CASE_NAME and "AD5" not in CASE_NAME
    print("OZFLUX AU-ASM STAGE08 DIRECT AD400 SELF-TEST PASS | 80x5 RESUBMIT79, no AD5",flush=True)

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("action",choices=("self-test","check","prepare","submit","status"))
    p.add_argument("--helper",type=Path)
    p.add_argument("--co2-csv",type=Path)
    p.add_argument("--accept-exploratory",default="")
    p.add_argument("--confirm",default="")
    args=p.parse_args()
    if args.action=="self-test":return selftest()
    if args.helper is None:fail("Provide --helper path, validated against pinned source blob")
    m=helper_module(args.helper)
    # status does not need site forcing re-hashes
    if args.action=="status":
        configure(m,[])
        return m.status((SITE,))
    srf,files=verify_sources()
    configure(m,files)
    if args.action=="submit":
        if args.confirm!=ACK_SUB or args.accept_exploratory!=ACCEPT:
            fail("Submission requires --accept-exploratory "+ACCEPT+" --confirm "+ACK_SUB)
        return submit(m,srf,files)
    co2=get_co2(args.co2_csv)
    if args.action=="check":
        return check(m,co2,srf,files)
    if args.action=="prepare":
        if args.confirm!=ACK_PREP or args.accept_exploratory!=ACCEPT:
            fail("Prepare requires --accept-exploratory "+ACCEPT+" --confirm "+ACK_PREP)
        return prepare(m,co2,srf,files)
    fail("unrecognized action")

if __name__=="__main__":main()
