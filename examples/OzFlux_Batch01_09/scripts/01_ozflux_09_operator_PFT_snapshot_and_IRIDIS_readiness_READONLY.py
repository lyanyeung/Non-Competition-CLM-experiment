#!/usr/bin/env python3
"""OzFlux non-competition Stage01 — operator-selected v1.1 PFT READ-ONLY gate.

Authoritative PFT source: lyanyeung/CLM-FATES-single-site-workflows
branch oz-jp-pft-guidance-20261102 commit
d62c814585c4aa85731f77b4a555efe6ec9e94a3,
examples/OzFlux_JapanFlux_PFT/ (operator-accepted v1.1, 2026-11-02).

The 9 OzFlux model hypotheses are allowed as PRIMARY PFT for FIXNC.
This gate does NOT approve DATM physics, soil, actual point surfaces,
FATES active mapping in a case, or any Slurm submission.

Outputs new HOME JSON + TSV only. No CIME, Slurm, model/original writes.
"""
from __future__ import annotations
import argparse,csv,hashlib,json,math
from pathlib import Path
import sys
from collections import Counter

HOME=Path.home()
BASE=Path("/iridisfs/scratch/ly3n24/CLM_FATES")
SOURCE_BRANCH="oz-jp-pft-guidance-20261102"
SOURCE_COMMIT="d62c814585c4aa85731f77b4a555efe6ec9e94a3"
NCSOURCE="lyanyeung/Non-Competition-CLM-experiment"
DATA={
 "OZ_JP_ORIGINAL_20_SITE_PFT_MASTER_PINNED_20261102.csv":"b283e41601167e176397f3224b58c6c2f691146e",
 "OZFLUX_09_PRIMARY_CLM_PCT_NAT_PFT_20261102.csv":"698d702e83265290e3cf1f1890235b67ede290ee",
 "OZFLUX_09_PRIMARY_FATES_PFT_PERCENT_20261102.csv":"cec1df31f3e959e854aca6105a665a42321afa7c",
 "OZFLUX_09_PRIMARY_PFT_VALIDATION_20261102.csv":"2106f818b93eefb97323650535af5ec665628665",
 "OZFLUX_09_ORIGINAL_L6_SITES_MANIFEST.tsv":"de65b38ae838a6b4f7bbaec44e6350a55c255f14",
}
EXPECTED=("AU-ASM","AU-Cow","AU-Cpr","AU-DaS","AU-Dry",
          "AU-Gin","AU-How","AU-Stp","AU-Tum")
# These are the active DEFAULT14 host->FATES mapping entries.
# host0 is BARE, not a FATES cohort.
HOST_TO_FATES={1:2,3:3,4:1,5:4,6:5,7:6,9:7,10:9,13:13,14:14}
REPORT_FIELDS=("site","PFT_source_approved_by_operator",
  "PFT_status","host_PFT_natland_json","FATES_PFT_natland_json",
  "bare_natland_percent","active_FATES_classes","raw_L6_file_count",
  "raw_L6_files_present","raw_L6_files_missing",
  "candidate_DATM_candidate_only","CTSM_reference_surface_present_NOT_PFT_OVERRIDE",
  "new_FIXNC_surface_science_verified","source_meteorology_approved",
  "effective_case_fates_mapping_verified","AD5_authorised",
  "AD400_authorised","next_action")

def blob_hash(path):
    data=path.read_bytes()
    h=hashlib.sha1()
    h.update(("blob "+str(len(data))+"\0").encode())
    h.update(data)
    return h.hexdigest()

def read_table(path,delimiter=","):
    if not path.is_file() or path.is_symlink():
        raise ValueError("Source is not original regular file: "+str(path))
    with path.open("r",encoding="utf-8-sig",newline="") as f:
        rd=csv.DictReader(f,delimiter=delimiter)
        cols=rd.fieldnames or []
        if not cols:raise ValueError("Missing source CSV header "+str(path))
        rows=list(rd)
    if any(None in r for r in rows):
        raise ValueError("Invalid source CSV row width "+str(path))
    return rows

def bounded(value,context):
    try:x=float(value)
    except (ValueError,TypeError):raise ValueError("Not numeric "+context)
    if not math.isfinite(x) or x < -1e-9 or x >100+1e-9:
        raise ValueError("Out of range % "+context)
    return max(0.0,x)

def close(a,b,atol=0.0005):
    return abs(a-b)<=atol

def require_exact_sites(rows,label):
    """Same nine exact operator-selected sites, exactly once; any ordering."""
    got=Counter(r["site"] for r in rows)
    want=Counter(EXPECTED)
    if got!=want:
        raise ValueError("Site membership/count mismatch in "+label+
                         "; expected="+str(dict(want))+
                         "; got="+str(dict(got)))
    return True

def validate_data(data_dir):
    if data_dir.is_symlink() or not data_dir.is_dir():
        raise ValueError("Input data directory missing/symlink")
    for name,blob in DATA.items():
        p=data_dir/name
        if not p.is_file() or p.is_symlink() or blob_hash(p)!=blob:
            raise ValueError("Git original PFT SNAPSHOT SHA mismatch "+name)
    master=read_table(data_dir/"OZ_JP_ORIGINAL_20_SITE_PFT_MASTER_PINNED_20261102.csv")
    host=read_table(data_dir/"OZFLUX_09_PRIMARY_CLM_PCT_NAT_PFT_20261102.csv")
    fates=read_table(data_dir/"OZFLUX_09_PRIMARY_FATES_PFT_PERCENT_20261102.csv")
    validation=read_table(data_dir/"OZFLUX_09_PRIMARY_PFT_VALIDATION_20261102.csv")
    inventory=read_table(data_dir/"OZFLUX_09_ORIGINAL_L6_SITES_MANIFEST.tsv","\t")
    if len(master)!=20 or len(host)!=9 or len(fates)!=9 or len(validation)!=9 or len(inventory)!=10:
        raise ValueError("Snapshot original counts 20/9/9/9/10 mismatch")
    # Site row ORDER has no scientific meaning. The reviewed upstream
    # v1.1 CSV correctly has AU-How before AU-Gin, whereas EXPECTED
    # previously listed AU-Gin first. Validate exact IDs and counts;
    # do NOT silently accept missing or duplicated sites.
    require_exact_sites(host,"CLM host PRIMARY")
    require_exact_sites(fates,"FATES PRIMARY")
    require_exact_sites(validation,"round-trip PRIMARY")
    if Counter(r["site"] for r in inventory)!=Counter(
            {**{site:1 for site in EXPECTED},"AU-ASM":2}):
        raise ValueError("10 original source file manifest missing/duplicate site")
    oz_master=[r for r in master if r.get("network")=="OzFlux"]
    require_exact_sites(oz_master,"20-site original source OzFlux")
    source={r["site"]:r for r in oz_master}
    f_by={r["site"]:r for r in fates}
    v_by={r["site"]:r for r in validation}
    result=[]
    for row in host:
        site=row["site"]
        s=source[site];fr=f_by[site];v=v_by[site]
        if (row.get("network")!="OzFlux" or row.get("mapping_profile")!="DEFAULT14"
            or fr.get("network")!="OzFlux" or fr.get("mapping_profile")!="DEFAULT14"
            or v.get("scenario")!="PRIMARY" or v.get("round_trip")!="PASS"
            or v.get("mapping_profile")!="DEFAULT14"):
            raise ValueError("Network/default map/validation problem "+site)
        # Human-readable recommendation and machine input must refer to
        # the SAME canonical source master row.
        hostvals={i:bounded(row[f"PCT_NAT_PFT_{i}"],site+str(i))
                  for i in range(15)}
        fatesvals={i:bounded(fr[f"FATES_PFT_{i:02d}_pct_natland"],site+str(i))
                    for i in range(1,15)}
        veg={i:bounded(fr[f"FATES_PFT_{i:02d}_pct_vegetated_only"],site+str(i))
               for i in range(1,15)}
        if not close(sum(hostvals.values()),100.0,0.00005):
            raise ValueError("CLM host total !=100 incl bare "+site)
        if not close(sum(fatesvals.values())+hostvals[0],100,0.0001):
            raise ValueError("FATES bare plus alive!=100 "+site)
        if not close(float(s["bare_percent"]),hostvals[0],0.00001):
            raise ValueError("Master source bare != host bare "+site)
        if not close(float(fr["bare_pct_natland"]),hostvals[0],0.00001):
            raise ValueError("FATES output lost independent bare area "+site)
        if not close(float(v["natural_area_sum"]),100.0,0.00001):
            raise ValueError("Source round-trip row total differs "+site)
        live={i:x for i,x in fatesvals.items() if x>1e-8}
        if not 1<=len(live)<=4 or int(v["live_type_count"])!=len(live):
            raise ValueError("FATES active class >4 or count mismatch "+site)
        for i,val in hostvals.items():
            if i==0:continue
            mapped=HOST_TO_FATES.get(i)
            if mapped is None and val>1e-8:
                raise ValueError("Host class not in exact DEFAULT14 FATES map "+site+" "+str(i))
            if mapped is not None and not close(val,fatesvals[mapped],0.00005):
                raise ValueError("Exact host->FATES natland area mismatch "+site+" "+str(i))
        if hostvals[0]<99.9999:
            for i,x in live.items():
                if not close(veg[i],x/(100-hostvals[0])*100,0.0007):
                    raise ValueError("Vegetated-only PFT fraction mismatch "+site+" "+str(i))
        for i in fatesvals:
            if i not in live and abs(veg[i])>0.0001:
                raise ValueError("Unmapped vegetated-only leakage "+site)
        if not close(sum(veg.values()),100.0,0.002):
            raise ValueError("Vegetated-only sum not 100 "+site)
        if not close(sum(float(x) for x in __import__("json").loads(s["clm_pct_nat_pft_json"]).values())+hostvals[0],100.0,0.0001):
            # master JSON has live host only, no bare.
            raise ValueError("Master source JSON host components total mismatch "+site)
        if any(not close(float(x),fatesvals[int(i)],0.0001)
               for i,x in json.loads(s["fates_natland_percent_json"]).items()):
            raise ValueError("Master source FATES JSON mismatch "+site)
        result.append({
          "site":site,
          "host":{str(i):x for i,x in hostvals.items() if x>1e-8},
          "fates":{str(i):x for i,x in live.items()},
          "bare_percent":hostvals[0],
          "uncertainty":s["uncertainty"],
          "source_status":s["status"],
          "source_target_state":s["target_state"],
          "source_target_period":s["target_period"],
          "source_provisional_prior":s["provisional_prior"],
          "source_hold_flag":s["hold_flag"],
        })
    return result,inventory

def filesystem_preview(rows,inventory):
    # No recursion and no writer actions; bounded exact known directories.
    raw_root=BASE/"sites"/"MY_EC_SITE"
    asm_ref=HOME/"ozflux_stage16_reference_20261102T023647Z"/"surfdata_AU-ASM_hist_2000_16pfts_c261102.nc"
    # Stage14 candidates may be named ozflux_ASM_* rather than
    # ozflux_stage14_* on the operator host. This is existence-only;
    # it is never a DATM physics or science approval.
    asm_stage14_home=sorted({*HOME.glob("ozflux_stage14*"),
                             *HOME.glob("ozflux_ASM*")})[:60]
    asm_stage14_candidate=sum(len(list(d.glob("*201?.nc"))) for d in asm_stage14_home if d.is_dir() and not d.is_symlink())
    # Raw source L6 counts are NOT converted simulation forcing.
    out=[]
    for r in rows:
        site=r["site"]
        names=[entry["filename"] for entry in inventory if entry["site"]==site]
        exists=[(raw_root/site/"forcing"/"raw"/n).is_file() for n in names]
        action=("Prepare distinct no-competition PFT surface and verify "
                "DATM/soil/CIME mapping; then isolated AD5; only then AD400")
        out.append({
          "site":site,
          "PFT_source_approved_by_operator":True,
          "PFT_status":r["source_status"],
          "host_PFT_natland_json":json.dumps(r["host"],sort_keys=True),
          "FATES_PFT_natland_json":json.dumps(r["fates"],sort_keys=True),
          "bare_natland_percent":r["bare_percent"],
          "active_FATES_classes":len(r["fates"]),
          "raw_L6_file_count":len(names),
          "raw_L6_files_present":sum(exists),
          "raw_L6_files_missing":json.dumps([n for n,ok in zip(names,exists) if not ok]),
          "candidate_DATM_candidate_only":site=="AU-ASM" and asm_stage14_candidate>0,
          "CTSM_reference_surface_present_NOT_PFT_OVERRIDE":site=="AU-ASM" and asm_ref.is_file(),
          "new_FIXNC_surface_science_verified":False,
          "source_meteorology_approved":False,
          "effective_case_fates_mapping_verified":False,
          "AD5_authorised":False,
          "AD400_authorised":False,
          "next_action":action,
        })
    return out

def self_test():
    a=[29,65,2,4]
    assert sum(a)==100
    assert HOST_TO_FATES[5]==4 and HOST_TO_FATES[4]==1 and HOST_TO_FATES[9]==7
    assert HOST_TO_FATES[13]==13 and HOST_TO_FATES[14]==14
    assert close((65/71)*100,91.5493,0.00005)
    assert len(DATA)==5 and len(set(DATA.values()))==5
    assert len(EXPECTED)==9 and EXPECTED[0]=="AU-ASM"
    ordered=[{"site":site} for site in EXPECTED]
    flipped=[{"site":site} for site in (
        "AU-ASM","AU-Cow","AU-Cpr","AU-DaS","AU-Dry",
        "AU-How","AU-Gin","AU-Stp","AU-Tum")]
    assert require_exact_sites(ordered,"regression ordering")
    assert require_exact_sites(flipped,"actual v1.1 AU-How/AU-Gin order")
    for invalid in (flipped[:-1],flipped[:-1]+[{"site":"AU-Gin"}]):
        try:require_exact_sites(invalid,"missing or duplicate test")
        except ValueError:pass
        else:raise AssertionError("Duplicated/missing site accepted")
    print("OZFLUX NC STAGE01 SELF-TEST PASS | 9 exact distinct PFT sites, AU-How/Gin order regression, duplicates rejected, bare0, DEFAULT14; NO WRITES")

def main():
    if sys.argv[1:]==["--self-test"]:
        self_test();return
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--data-dir",required=True,type=Path)
    p.add_argument("--out",required=True,type=Path)
    args=p.parse_args()
    out=args.out.resolve()
    if (args.out.is_symlink() or out.exists() or out.parent!=HOME.resolve()
        or BASE.resolve()==out or BASE.resolve() in out.parents):
        raise ValueError("Output must be NEW direct HOME report folder")
    values,inventory=validate_data(args.data_dir)
    rows=filesystem_preview(values,inventory)
    if len(rows)!=9:raise ValueError("Expected exact 9 source-cohort PFT rows")
    manifest={
      "stage":"NonCompetition OzFlux09 Stage01 operator-accepted v1.1 PFT and IRIDIS readiness READONLY",
      "source_repo":"lyanyeung/CLM-FATES-single-site-workflows",
      "source_branch":SOURCE_BRANCH,"source_commit":SOURCE_COMMIT,
      "source_directory":"examples/OzFlux_JapanFlux_PFT",
      "noncompetition_repository":NCSOURCE,
      "PFT_repository_snapshot_Git_blobs":DATA,
      "operator_accepted_PRIMARY_PFT_9_sites":values,
      "model_mode":{"use_fates_nocomp":True,"use_fates_fixed_biogeog":True,
                    "cold_start":True,"active_PFT_mapping":"DEFAULT14 case confirmation pending"},
      "PFT_is_model_hypothesis_not_observation":True,
      "input_area_denominator":"NATVEG LANDUNIT INCL HOST BARE0; NOT renormalized",
      "physical_inputs_by_site_readonly_inventory":rows,
      "note":"Input PFT choice approved for experimental hypotheses. Meteo, surface, soil and CIME science gates independent.",
      "new_surface_or_forcing_or_model_case_created":False,
      "AD5_submitted":False,"AD400_submitted":False,
      "AD400_authorised":False,
    }
    out.mkdir(parents=False,mode=0o700,exist_ok=False)
    with (out/"ozflux09_operator_PFT_and_input_readiness.tsv").open(
        "x",encoding="utf-8",newline="") as f:
        w=csv.DictWriter(f,fieldnames=REPORT_FIELDS,extrasaction="raise",delimiter="\t")
        w.writeheader();w.writerows(rows)
    (out/"ozflux09_operator_PFT_and_IRIDIS_readiness.json").write_text(
        json.dumps(manifest,indent=2,ensure_ascii=False,allow_nan=False),
        encoding="utf-8")
    print("OZFLUX NONCOMPETITION SOURCE GIT BLOBS VERIFIED: 5 SNAPSHOTS")
    print("OZFLUX PRIMARY PFT 9/9 PASS, SOURCE COMMIT",SOURCE_COMMIT)
    for r in rows:
        print("SITE",r["site"],"PFT",r["FATES_PFT_natland_json"],
              "BARE",r["bare_natland_percent"],
              "RAW_L6",str(r["raw_L6_files_present"])+"/"+str(r["raw_L6_file_count"]),
              "REFERENCE_SURFACE",r["CTSM_reference_surface_present_NOT_PFT_OVERRIDE"],
              "FIXNC_SURFACE",r["new_FIXNC_surface_science_verified"])
    print("GATE: PFTs operator selected; do NOT equate original L6 with DATM forcing")
    print("GATE: 0/9 new PFT-specific FIXNC surface/CIME effective binding verified")
    print("GATE: no case, forcing, surface, job or model change; AD400 NOT submitted")
    print("REPORT_DIR",out)

if __name__=="__main__":
    main()
