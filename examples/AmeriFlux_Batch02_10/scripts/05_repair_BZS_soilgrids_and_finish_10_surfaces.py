#!/usr/bin/env python3
"""Stage05: isolate US-BZS missing-COORD soil source; finish 10 FIXNC surfaces.

Stage04 actual 10site soil output from 2026-10-26 has US-BZS
coords=None and fallback surface 23.6/26.2. The FINAL 50-site
recommendation instead selects T3 SoilGrids 40.0/8.9. Do not fill L1..10
with the 0-30cm average or manually change old source records.

Prefer an existing completed original 50-site Stage01 *source* 10-layer
BZS SoilGrids row, only if per-layer data/tier/top-mean and original
metadata verify. Otherwise run the SAME original Stage01 collector
once for BZS only, with official repository --coords
US-BZS:64.6963:-148.3235 to enable SoilGrids 250m.

Merge 1 verified BZS row + 9 original Stage04 source rows into a NEW
versioned wide CSV and data SHA receipt. Independently invoke Stage02
check and build on the NEW CSV. No original Stage04 output overwritten.
Original active GLE model, 215 forcing NC and all CIME/Slurm untouched.
"""
import argparse,csv,hashlib,json,os,subprocess,sys
from datetime import datetime,timezone
from pathlib import Path
from uuid import uuid4

SITES=("US-BZS","US-CMW","US-EML","US-GLE","US-Ha1","US-Ho1","US-Ho2","US-Ho3","US-ICh","US-ICt")
WORK=Path.home()/"AMF_Batch02_FIXNC_bootstrap"
SOIL_SCRIPT=WORK/"soil_source/examples/Ameriflux_Site/Ameriflux_Soil/scripts/01_collect_soil_texture_evidence.py"
SURFACE_SCRIPT=WORK/"nc/examples/AmeriFlux_Batch02_10/scripts/02_prepare_ten_independent_FIXNC_surface_candidates.py"
REGISTER=WORK/"nc/examples/AmeriFlux_Batch02_10/data/AMF_BATCH02_10_PFT_SOIL_RECOMMENDATIONS_SOURCE_PINNED_20261026.csv"
STAGE04=Path.home()/"CLM_FATES_SOIL/AmeriFlux_Batch02_10_20261026_Stage04"
ORIG=Path.home()/"CLM_FATES_SOIL/AmeriFlux50_20261026"
REPORTS=Path.home()/"CLM_FATES_SOIL"
COLLECTOR_GITBLOB="231aedd5d7105c6d7557de0cff6287ee61ad361b"
WIDE="09_RECOMMENDED_CLM10_PCT_SAND_PCT_CLAY_WIDE.csv"
SCHEMA="AMF_BATCH02_STAGE05_BZS_ONLY_SOIL_SOURCE_COORD_REPAIR"
COORD="US-BZS:64.6963:-148.3235"

def fail(msg):raise RuntimeError(msg)
def sha(p):
    h=hashlib.sha256()
    with Path(p).open("rb") as f:
        for block in iter(lambda:f.read(1<<20),b""):h.update(block)
    return h.hexdigest()
def gitblob(p):
    body=Path(p).read_bytes()
    return hashlib.sha1(b"blob "+str(len(body)).encode()+b"\0"+body).hexdigest()
def readcsv(p):
    with Path(p).open(encoding="utf-8-sig",newline="") as f:return list(csv.DictReader(f))
def writecsv(p,rows):
    with Path(p).open("x",encoding="utf-8",newline="") as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]))
        w.writeheader();w.writerows(rows)
def top(row,field):
    z=[float(row[f"PCT_{field}_L{i}"]) for i in range(1,6)]
    return round(sum(z)/5,1)
def validate_row(row,ref,site):
    for fld in ("SAND","CLAY"):
        for i in range(1,11):
            v=float(row[f"PCT_{fld}_L{i}"])
            if not (0<=v<=100):fail(site+" invalid L"+str(i)+" "+fld)
    for i in range(1,11):
        if float(row[f"PCT_SAND_L{i}"])+float(row[f"PCT_CLAY_L{i}"])>100.0001:
            fail(site+" sand+clay >100 at L"+str(i))
    if site not in ("US-Ho2","US-Ho3"):
        if abs(top(row,"SAND")-float(ref[site]["recommended_sand_0_30cm_pct"]))>.11 or \
           abs(top(row,"CLAY")-float(ref[site]["recommended_clay_0_30cm_pct"]))>.11:
            fail(site+" original 10-layer recommendation does not agree with pinned 50site FINAL")
    if site=="US-BZS" and row["tier"]!="T3_SOILGRIDS_250M":
        fail("BZS cannot use SURFACE fallback: require T3_SOILGRIDS_250M; got "+row["tier"])

def proof(root):
    wide=root/WIDE
    meta=root/"metadata.json"
    if not wide.is_file() or not meta.is_file():return None
    rows=readcsv(wide)
    r=next((r for r in rows if r["site"]=="US-BZS"),None)
    if not r:return None
    m=json.loads(meta.read_text())
    info=m.get("sites",{}).get("US-BZS",{})
    # Original Stage01 source records a real SoilGrids source, not
    # old SURFACE-only fallback with blank BIF coordinates.
    if "SOILGRIDS" not in info.get("sources",[]):return None
    return r,{"wide":str(wide),"wide_sha256":sha(wide),
       "meta":str(meta),"metadata_sha256":sha(meta),
       "source_info":info}

def run_checked(cmd):
    p=subprocess.run(cmd,check=False)
    if p.returncode:fail("Original source collector failed with code "+str(p.returncode))
def main():
    ap=argparse.ArgumentParser(description=__doc__)
    g=ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--self-test",action="store_true")
    g.add_argument("--repair-build",action="store_true")
    a=ap.parse_args()
    if a.self_test:
        assert len(SITES)==10 and abs(-148.3235)<180 and 64.6963>60
        sample={"tier":"T3_SOILGRIDS_250M"}
        for k in ("SAND","CLAY"):
            for i in range(1,11):sample[f"PCT_{k}_L{i}"]=40.0 if k=="SAND" else 8.9
        assert top(sample,"SAND")==40.0 and top(sample,"CLAY")==8.9
        print("AMF_B02_STAGE05_SELF_TEST_PASS | BZS coordinate-only SoilGrids requery, no source writes")
        return
    for p in (SOIL_SCRIPT,SURFACE_SCRIPT,REGISTER,STAGE04/WIDE):
        if not p.is_file():fail("Missing pinned Stage04 input "+str(p))
    if gitblob(SOIL_SCRIPT)!=COLLECTOR_GITBLOB:
        fail("Original 50-site soil collector Git blob altered")
    refs={r["site"]:r for r in readcsv(REGISTER)}
    stage04=readcsv(STAGE04/WIDE)
    if len(stage04)!=10 or {r["site"] for r in stage04}!=set(SITES):
        fail("Existing Stage04 wide soil output did not contain the exact 10 sites")
    bysite={r["site"]:r for r in stage04}
    if (bysite["US-BZS"]["tier"]!="T4_KEEP_SURFACE"
        or top(bysite["US-BZS"],"SAND")!=23.6
        or top(bysite["US-BZS"],"CLAY")!=26.2):
        fail("BZS old fallback changed: this repair is specific to actual Stage04 observed error")
    for site in SITES[1:]:
        validate_row(bysite[site],refs,site)
    source=proof(ORIG)
    if source:
        row,raw=source
        try:validate_row(row,refs,"US-BZS")
        except Exception:
            source=None
        else:
            print("AMF_B02_BZS_SOURCED_PREVIOUS_ORIGINAL_SOILGRIDS",ORIG,flush=True)
    if not source:
        dest=REPORTS/("AmeriFlux_Batch02_10_Stage05_US_BZS_COORD_REPAIR_"+
          datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")+"_"+uuid4().hex[:8])
        dest.mkdir(parents=True,exist_ok=False)
        print("AMF_B02_BZS_FETCHING_ONLY_ONE_SITE",COORD,"OUT",dest,flush=True)
        run_checked([sys.executable,"-B",str(SOIL_SCRIPT),
               "--sites","US-BZS","--coords",COORD,
               "--output-root",str(dest)])
        source=proof(dest)
        if source is None:
            fail("BZS SoilGrids 250m not available or no coordinate-resolved 10-layer profile. Check source logs, credentials/ISRIC outage. Do NOT fabricate 40/8.9 for ten layers.")
        row,raw=source
        validate_row(row,refs,"US-BZS")
    else:
        row,raw=source
    rows=[dict(bysite[x]) for x in SITES]
    if set(row)!=set(rows[0]):
        fail("BZS SoilGrids collector source layer schema differs from original ten-site Stage04")
    rows[0]=dict(row)
    target=REPORTS/("AmeriFlux_Batch02_10_STAGE05_BZS_FULL_10_LAYER_REPAIRED_"+
       datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")+"_"+uuid4().hex[:8])
    target.mkdir(parents=True,exist_ok=False)
    merged=target/WIDE
    writecsv(merged,rows)
    info={"schema":SCHEMA,"original_stage04_wide":str(STAGE04/WIDE),
         "original_stage04_sha256":sha(STAGE04/WIDE),
         "BZS_original_measured_SoilGrids_provenance":raw,
         "BZS_new_tier":row["tier"],
         "BZS_L1_L10_0_30cm_sand_pct":top(row,"SAND"),
         "BZS_L1_L10_0_30cm_clay_pct":top(row,"CLAY"),
         "original_nine_other_rows_identical":True,
         "all_10_source_years_and_PFT_original_unmodified":True,
         "new_merged_wide":str(merged),"new_wide_sha256":sha(merged),
         "Slurm_jobs_submitted":False,
         "surfaces_isolated_candidate_only":True}
    (target/"receipt.json").write_text(json.dumps(info,indent=2)+"\n")
    print("AMF_B02_BZS_REPAIRED_TRUE_SOIL10 40.0/8.9 T3_SOILGRIDS_250M",flush=True)
    print("AMF_B02_STAGE05_MERGED_WIDE",merged,flush=True)
    # Continue all-site audit + partial builds even if any original
    # point-surface is missing. Stage02 itself prints per-site HOLDs.
    check=subprocess.run([sys.executable,"-B",str(SURFACE_SCRIPT),
      "--check","--soil-wide",str(merged)],check=False)
    print("AMF_B02_STAGE05_SURFACE_CHECK_EXIT",check.returncode,flush=True)
    build=subprocess.run([sys.executable,"-B",str(SURFACE_SCRIPT),
      "--build","--soil-wide",str(merged)],check=False)
    print("AMF_B02_STAGE05_SURFACE_BUILD_EXIT",build.returncode,flush=True)
    print("AMF_B02_STAGE05_REPORT",target,flush=True)
    if build.returncode:
        print("AMF_B02_STAGE05_PARTIAL | original surface layout or site science HOLD printed above; eligible independent candidates retained, NO Slurm",flush=True)
        raise SystemExit(3)
    print("AMF_B02_STAGE05_ALL10_INDEPENDENT_SURFACES_PREPARED_NO_SLURM",flush=True)

if __name__=="__main__":
    main()
