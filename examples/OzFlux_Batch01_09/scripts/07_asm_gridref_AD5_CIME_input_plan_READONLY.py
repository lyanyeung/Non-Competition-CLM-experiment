#!/usr/bin/env python3
"""OzFlux NC AU-ASM Stage07: immutable GRIDREF AD5 CIME input PLAN, READ ONLY.

Never creates or edits a CIME case, user-mods, shared source, NetCDF,
CIME namelist, FATES parameter file or Slurm job. Reports only under a NEW
direct HOME directory. No scientific approval for soil, forcing or spinup.
"""
from __future__ import annotations
import argparse,hashlib,json,re,sys
from pathlib import Path
import numpy as np
import netCDF4

HOME=Path.home()
ROOT=Path("/iridisfs/scratch/ly3n24/CLM_FATES")
CASES=ROOT/"cases"
CASE_NAME="AU-ASM_OZ_FIXNC_GRIDREF_AD5"
SURF=HOME/"ozflux_nc_stage02_ASM_20261102T215809Z"/"surfdata_AU-ASM_NC_FIXNC_PFT_v1p1_CTSM2000_SOIL_REFERENCE.nc"
SURF_SHA="d06ad3111d93de69e7f2dd7f048b02a9161aee4ff853afafedcdfed71a54f3a1"
DATM=HOME/"ozflux_stage14_FSDS0_20261102T012038Z"
STAGE04=HOME/"ozflux_nc_stage04_20261102T223221Z_FIX"/"ozflux_nc_stage04_nine_site_forcing_handoff.json"
STAGE05=HOME/"ozflux_nc_stage05_20261102T224556Z_FIX"/"stage05_three_site_priority_summary.json"
ANNUAL={
2013:"0e722aec1d73d35ff4671ccd1c72fbf02c7e3af8f9fdd6cae291834741b2bffe",
2014:"54345a6ae15ba8091b118dc62c891cff1fb851eda895178a47c8d3a23143871b",
2015:"6d7b9cc4f0e24d6395f1f6d1ae3217f9fd70a67d93f41969eb6cdafe283447bf",
2016:"8b5576e424625a0bf62f0fb0fa552230ff7c01e26e440a565242e169fe455c7f",
2017:"634d8d395e95331cf9f13dcbf5d48edbc2e881af4ca913acb75abe1333032951",
2018:"8ce901670486469358525c95f6a78db82698a5712312c4b1bf610aff744be55d"}
MAP={"PRECTmms":"Faxa_precn","FSDS":"Faxa_swdn",
     "FLDS":"Faxa_lwdn","TBOT":"Sa_tbot",
     "QBOT":"Sa_shum","PSRF":"Sa_pbot",
     "WIND":"Sa_wind","ZBOT":"Sa_z"}
FATES=("fates_hlm_pft_map","fates_paramfile","fsurdat","use_fates",
       "use_fates_nocomp","use_fates_fixed_biogeog","spinup_state")

def regular(p):
    if p.is_symlink() or not p.is_file():raise ValueError("missing or symlink file: "+str(p))
    return p

def hashfile(p):
    h=hashlib.sha256()
    with regular(p).open("rb") as f:
        for b in iter(lambda:f.read(4*1024*1024),b""):h.update(b)
    return h.hexdigest()

def exact_sha(p, expected):
    got=hashfile(p)
    if got!=expected:raise ValueError(f"immutable SHA mismatch {p}: {got}")
    return str(p.resolve())

def check_receipts():
    a=json.loads(regular(STAGE04).read_text())
    b=json.loads(regular(STAGE05).read_text())
    if (a.get("all_nine_surface_candidates_exist") is not True or
        a.get("AU_ASM_FSDS0_years_source_SHA_verified")!=list(ANNUAL) or
        a.get("DATM_climate_streams_approved") is not False or
        a.get("AD400_authorised") is not False or
        b.get("stage08_196_variable_years_reconciled") is not True or
        b.get("AD5_authorised") is not False):
        raise ValueError("Stage04/Stage05 prior verified science-HOLD state changed")

def audit_surface():
    exact_sha(SURF,SURF_SHA)
    with netCDF4.Dataset(str(SURF),"r") as d:
        p=np.ma.asarray(d.variables["PCT_NAT_PFT"][:],dtype=float).filled(np.nan).reshape(-1)
        e=np.zeros(len(p))
        if len(p) not in (15,16):raise ValueError("Unexpected PFT host slot length")
        for k,v in ((0,29),(5,65),(13,2),(14,4)):e[k]=v
        if not np.array_equal(p,e):raise ValueError("AU-ASM accepted v1.1 host PFT changed")
        la=float(np.asarray(d.variables["LATIXY"][:]).ravel()[0])
        lo=float(np.asarray(d.variables["LONGXY"][:]).ravel()[0])
        if abs(la+22.2828)>1e-6 or abs(lo-133.2493)>1e-6:raise ValueError("Surface coords changed")
        soil={}
        for v in ("PCT_SAND","PCT_CLAY","ORGANIC"):
            x=np.ma.asarray(d.variables[v][:],dtype=float).filled(np.nan).reshape(-1)
            if len(x)!=10 or not np.isfinite(x).all():raise ValueError("Invalid grid-soil layer "+v)
            soil[v]={"units":getattr(d.variables[v],"units","unknown"),
                     "values":[float(z) for z in x]}
        return {"sha256":SURF_SHA,"path":str(SURF.resolve()),"PCT_NAT_PFT":p.tolist(),
                "latitude":la,"longitude":lo,"CTSM_GRID_SOIL_REFERENCE_UNAPPROVED":soil}

def audit_met():
    files=[]
    for year,expected_hash in ANNUAL.items():
        f=DATM/f"AU-ASM_FSDS0_PROVISIONAL_DATM_{year}.nc"
        exact_sha(f,expected_hash)
        with netCDF4.Dataset(str(f),"r") as d:
            t=d.variables["time"]
            if len(t)!=17520 or getattr(t,"calendar",None)!="noleap":
                raise ValueError("AU-ASM DATM calendar/records changed "+str(year))
            expected=(np.arange(17520,dtype=float)+0.5)/48
            if (getattr(t,"units",None)!=f"days since {year}-01-01 00:00:00"
                 or not np.allclose(t[:],expected,atol=1e-12,rtol=0)):
                raise ValueError("DATM half-hour center differs "+str(year))
            lat=float(d.variables["lat"][0]);lon=float(d.variables["lon"][0])
            if abs(lat+22.2828)>1e-6 or abs(lon-133.2493)>1e-6:
                raise ValueError("DATM site coordinates changed "+str(year))
            for field in MAP:
                if field not in d.variables:
                    raise ValueError("Missing DATM field "+field+" "+str(year))
            files.append({"year":year,"filename":str(f.resolve()),
                          "sha256":expected_hash,"noleap_half_hours":17520})
    return files

def read_case_template():
    preferred=CASES/"CH-Dav_B01_FIXNC_AD400"
    if preferred.is_dir(): chosen=preferred
    else:
        options=sorted(p for p in CASES.iterdir() if p.is_dir()
                       and (p/"CaseDocs/lnd_in").is_file() and
                       (p/"CaseDocs/datm_in").is_file())
        chosen=options[0] if options else None
    if chosen is None:
        return {"available":False,"read_only":True,"effective_FATES_map_verified_for_AU_ASM":False}
    result={"available":True,"case_name":chosen.name,"read_only":True,
            "effective_FATES_map_verified_for_AU_ASM":False,
            "WARNING":"Reference for CIME syntax only: NEVER inherit its site forcing, surface, soil or FATES map"}
    for file in ("CaseDocs/lnd_in","CaseDocs/datm_in","CaseDocs/datm.streams.xml",
                 "user_nl_clm","user_nl_datm_streams"):
        p=chosen/file
        if p.is_file() and not p.is_symlink():
            result[file]={"exists":True}
            if file in ("CaseDocs/lnd_in","user_nl_clm"):
                content=p.read_text(errors="replace")
                v={}
                for key in FATES:
                    matches=re.findall(r"(?im)^\s*"+re.escape(key)+r"\s*=\s*([^\n!]*)",content)
                    if matches:v[key]=matches[-1].strip()[:400]
                result[file]["selected_namelist_values"]=v
            if file=="user_nl_datm_streams":
                content=p.read_text(errors="replace")
                result[file]["has_CLM_USRDAT_UNSET"]=bool("CLM_USRDAT.UNSET" in content)
                result[file]["has_offset_override"]="CLM_USRDAT.UNSET:offset" in content
        else:result[file]={"exists":False}
    return result

def prep_preview(files):
    rows=[
      "# PREVIEW ONLY. DO NOT COPY INTO EFFECTIVE CIME USER-MODS WITHOUT CASE REVIEW.",
      "# AU-ASM GRID_REFERENCE 6-year candidate forcing, science_approval=FALSE",
      "CLM_USRDAT.UNSET:taxmode = cycle",
      "CLM_USRDAT.UNSET:tintalgo = linear",
      "CLM_USRDAT.UNSET:mapalgo = none",
      "CLM_USRDAT.UNSET:meshfile = none",
      "CLM_USRDAT.UNSET:year_first = 2013",
      "CLM_USRDAT.UNSET:year_last = 2018",
      "CLM_USRDAT.UNSET:year_align = 2013",
      "CLM_USRDAT.UNSET:datafiles = \\",
    ]
    for i,f in enumerate(files):
        suffix=", \\" if i+1<len(files) else ""
        rows.append(f["filename"]+suffix)
    rows+=["CLM_USRDAT.UNSET:datavars = \\"]
    items=list(MAP.items())
    for i,(field,target) in enumerate(items):
        rows.append(field+" "+target+(", \\" if i+1<len(items) else ""))
    rows+=["# CDEPS effective offsets, stream syntax and FATES map require case-specific verification."]
    return "\n".join(rows)+"\n"

def selftest():
    assert sum({0:29,5:65,13:2,14:4}.values())==100
    assert tuple(ANNUAL)==tuple(range(2013,2019))
    assert len(MAP)==8 and MAP["QBOT"]=="Sa_shum"
    s=prep_preview([{"filename":"/source/2013.nc"},{"filename":"/source/2014.nc"}])
    assert "year_first = 2013" in s and "/source/2013.nc, \\" in s
    assert "PRECTmms Faxa_precn" in s
    print("OZFLUX STAGE07 SELF-TEST PASS: exact 6-year preview, eight CDEPS met fields, immutable source and CIME guards; READ ONLY")

def main():
    if sys.argv[1:]==["--self-test"]:return selftest()
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out",required=True,type=Path)
    a=ap.parse_args()
    if a.out.is_symlink() or a.out.exists() or a.out.parent.resolve()!=HOME.resolve():
        raise ValueError("--out must be unused direct HOME child")
    for p in (ROOT/"CTSM", ROOT/"CTSM/cime/scripts/create_newcase",ROOT/"inputdata",CASES):
        if not p.exists():raise ValueError("Missing actual CTSM/CIME path "+str(p))
    target=CASES/CASE_NAME
    if target.exists() or target.is_symlink():
        raise ValueError("Refuse CIME case collision: "+str(target))
    prior=[p.name for p in CASES.iterdir() if p.is_dir() and
           ("asm" in p.name.lower() or "alice" in p.name.lower())]
    if prior:raise ValueError("Potential AU-ASM prior case(s) require manual review: "+str(prior))
    check_receipts()
    print("STAGE04/05 ORIGINAL SOURCE RECEIPTS PASS")
    surface=audit_surface()
    print("AU-ASM GRIDREF SURFACE SHA, 10-LAYER SOIL AND PFT PASS")
    files=audit_met()
    print("AU-ASM SIX STAGE14 SOURCE SHAS AND NOLEAP TIME PASS")
    template=read_case_template()
    print("READONLY CIME REFERENCE",template.get("case_name","NONE"))
    report={
      "stage":"OzFlux NC AU-ASM Stage07 isolated GRIDREF AD5 input plan",
      "read_only":True,"source_surface_DATM_unchanged":True,
      "CIME_case_created":False,"Slurm_submitted":False,
      "AD5_authorised":False,"AD400_authorised":False,
      "science_approval":False,
      "SITE_SOIL_SCIENCE_HOLD":True,
      "SOURCE_NATIVE_TIME_HYPOTHESIS_REVIEW_PENDING":True,
      "AU_ASM_2017_FLDS_395H_ACCESS_REVIEW_PENDING":True,
      "FATES_EFFECTIVE_PFT_MAP_VERIFIED":False,
      "GRIDREF_ONLY_NOT_SITE_SOIL":True,
      "model_case_plan_path":str(target),
      "date_window":"2013–2018 candidate cycling; proposed 2013 startup 5-year engineering-only smoke test",
      "surface":surface,"candidate_datm":files,
      "CIME_reference_template":template,
      "CDEPS_preview_offset_not_approved":True,
      "next":"Independent user_mods input, effective FATES map, soil assumption, CDEPS offset & real CaseDocs validation BEFORE any CIME case creation or AD5"
    }
    a.out.mkdir(mode=0o700,parents=False,exist_ok=False)
    (a.out/"stage07_AU_ASM_GRIDREF_AD5_CIME_PLAN.json").write_text(
       json.dumps(report,indent=2,ensure_ascii=False),encoding="utf-8")
    (a.out/"stage07_user_nl_datm_streams_PREVIEW_NOT_ACTIVATED.txt").write_text(
       prep_preview(files),encoding="utf-8")
    print("AU-ASM READONLY STAGE07 PLAN SUCCESS")
    print("SCIENCE APPROVAL FALSE; NO CIME CASE CREATED; NO SLURM/AD5/AD400")
    print("REPORT_DIR",a.out)

if __name__=="__main__":main()
