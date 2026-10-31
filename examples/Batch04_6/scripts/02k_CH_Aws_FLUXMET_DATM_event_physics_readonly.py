#!/usr/bin/env python3
"""ICOS Batch04 Stage02K: CH-Aws event-by-event original FLUXMET vs DATM physics.

READ-ONLY EVIDENCE (NOT source science approval). Use operator-saved Stage02J
original FLUXMET_HH event contexts, Stage02E exact event-index ledger, and
Stage02C original case-to-annual DATM paths. For each of 20 events, preserve
both TIMESTAMP_START and TIMESTAMP_END exact-zero source candidates; compare
seven candidate DATM QBOT/TBOT/PSRF event values and derived VPD/RH.

Do not infer which START/END convention or time-zone is active. FLUXMET _F
and QC values are processed products, not necessarily native tower QC0.
Some conditional source T/VPD/Q/p comparisons are given as unit HYPOTHESES
only; BIF metadata column inventory is included, not treated as verified.
Only --out-dir creates new reports in an existing EMPTY directory.
No source/CIME/FATES/Slurm writes or forcing-case selection.
"""
from __future__ import annotations
import argparse
import collections
import csv
import datetime as dt
import json
import math
from pathlib import Path

STAGE_J = "STAGE02J_CH_AWS_ORIGINAL_FLUXMET_HH_EVENT_REVIEW"
STAGE_E = "STAGE02E_CH_AWS_QBOT_VARIANT_DIFF"
STAGE_C = "STAGE02C_SITE_DATM_CANDIDATE_YEAR_AND_SAMPLE_QC"
CASE_REF = "CH-Aws_FATES_SPINUP500_11P"
YEARS = tuple(range(2006, 2025))
COMPARE_FIELDS = ("QBOT", "TBOT", "PSRF")
SRC_FIELDS = ("RH", "TA_F", "TA_F_QC", "TA_F_MDS", "TA_F_MDS_QC",
              "TA_ERA", "VPD_F", "VPD_F_QC", "VPD_F_MDS",
              "VPD_F_MDS_QC", "VPD_ERA", "PA", "PA_F", "PA_F_QC", "PA_ERA")
CSV_FIELDS = ("event_id","event_time_DATM","source_timestamp_column",
              "original_timestamp","FLUXMET_TA_F","FLUXMET_VPD_F",
              "FLUXMET_VPD_F_QC","FLUXMET_TA_F_QC","FLUXMET_RH",
              "FLUXMET_TA_ERA","FLUXMET_VPD_ERA","FLUXMET_PA",
              "FLUXMET_PA_F","DATM_reference_QBOT_kgkg",
              "DATM_reference_TBOT_C","DATM_reference_PSRF_Pa",
              "DATM_reference_VPD_water_hPa","source_VPD_F_delta_to_reference_hPa_HYPOTHESIS",
              "candidate_most_different_case","candidate_most_different_QBOT_gkg",
              "candidate_most_different_VPD_water_hPa",
              "timestamp_basis_verified","FLUXMET_units_verified",
              "original_tower_QC_verified","ERA5_source_verified")


def validate_inputs(c, e, j):
    if not isinstance(c,dict) or c.get("stage")!=STAGE_C or c.get("science_release") is not False:
        raise ValueError("Stage02C must be the unreleased original CIME inventory")
    if not isinstance(e,dict) or e.get("stage")!=STAGE_E or e.get("science_release") is not False:
        raise ValueError("Stage02E source-difference report missing or released")
    if e.get("baseline_only_not_scientific_selection") is not True:
        raise ValueError("Stage02E diagnostic baseline must be explicitly unapproved")
    if not isinstance(j,dict) or j.get("stage")!=STAGE_J or j.get("science_release") is not False:
        raise ValueError("Stage02J original FLUXMET HH report missing or released")
    raw=j.get("raw_HH_product",{})
    if raw.get("scan_complete") is not True or int(raw.get("rows_scanned",-1))!=333120:
        raise ValueError("Full original 2006–2024 FLUXMET_HH source scan not proven")
    source_rows=raw.get("original_product_records",[])
    if len(j.get("event_comparisons",[]))!=20 or len(source_rows)!=200:
        raise ValueError("Expected actual Stage02J twenty events, two clocks and 5 HH each")
    if len(e.get("year_reports",[]))!=19:
        raise ValueError("Stage02E must contain 19 annual comparisons")
    sites=[r for r in c.get("sites",[]) if r.get("site")=="CH-Aws"]
    if len(sites)!=1 or len(sites[0].get("cases",[]))!=8:
        raise ValueError("Stage02C CH-Aws case inventory incomplete")
    return sites[0]["cases"]


def case_paths(cases):
    index={}
    for row in cases:
        name=row["case"]
        if name in index: raise ValueError("Duplicate original source case")
        byyear={}
        for ref in row["site_datm"]:
            yr=int(ref["year"])
            p=Path(ref["path"])
            if not p.is_absolute() or not p.name.startswith("CH-Aws_DATM_"):
                raise ValueError("Unpinned annual case forcing file")
            if yr in byyear:raise ValueError("Duplicate year")
            byyear[yr]=str(p)
        if tuple(sorted(byyear))!=YEARS:
            raise ValueError("Incomplete annual source years: "+name)
        index[name]=byyear
    distinct={}
    for name,byyear in index.items():
        sig=tuple(byyear[y] for y in YEARS)
        distinct.setdefault(sig,[]).append(name)
    if len(distinct)!=7 or CASE_REF not in index:
        raise ValueError("Expected exactly seven distinct CH-Aws DATM input sets and reference")
    groups=[{"cases":sorted(names), "years":dict(zip(YEARS,sig))}
            for sig,names in distinct.items()]
    return sorted(groups,key=lambda x:",".join(x["cases"]))


def event_index(e):
    out=collections.defaultdict(list)
    for group in e["year_reports"]:
        y=group["year"]
        for item in group.get("comparisons",[]):
            if item.get("comparison_status")!="ALIGNED":
                raise ValueError("Stage02E has an unaligned comparison")
            for pt in item.get("largest_5_HH",[]):
                label=str(pt.get("time",""))
                i=pt.get("index")
                if isinstance(i,int) and 0<=i<17520:
                    out[(y,label)].append(i)
    final={}
    for key,positions in out.items():
        if len(set(positions))>1:
            raise ValueError("Conflicting DATM half-hour index for same Stage02E event: "+str(key))
        final[key]=positions[0]
    return final


def vapour_hpa(q,p):
    return q*p/(.622+.378*q)/100.


def buck_esw_hpa(TK):
    C=TK-273.15
    return 6.1121*math.exp((18.678-C/234.5)*C/(257.14+C))


def source_float(field):
    if field is None: return None
    try:
        v=float(str(field).strip())
        if not math.isfinite(v) or v<=-9990: return None
        return v
    except (TypeError,ValueError):
        return None


def metadata_inventory(j):
    p=Path(j.get("raw_HH_product",{}).get("source_path",""))
    if not p.is_absolute() or p.name!="EUF_CH-Aws_FLUXNET_FLUXMET_HH_2006-2024_v1.3_r2.csv":
        raise ValueError("Unexpected FLUXMET_HH product provenance path")
    name=p.name.replace("FLUXMET_HH","BIFVARINFO_HH")
    meta=p.with_name(name)
    res={"path":str(meta),"status":"MISSING","matched_variable_rows":[]}
    if not meta.is_file():return res
    try:
        if meta.stat().st_size>5_000_000:
            res["status"]="TOO_BIG_METADATA"
            return res
        with meta.open("r",encoding="utf-8-sig",errors="replace",newline="") as f:
            reader=csv.DictReader(f)
            res["header_columns"]=(reader.fieldnames or [])[:100]
            for i,row in enumerate(reader):
                if i>10000:
                    res["status"]="TRUNCATED_METADATA"
                    break
                values=" ".join(str(v) for v in row.values())
                if any(w in values for w in ("TA_F","VPD_F","PA_F","RH","VPD_ERA")):
                    if len(res["matched_variable_rows"])<50:
                        res["matched_variable_rows"].append({
                            str(k):str(v)[:220] for k,v in row.items()
                        })
            else:res["status"]="READ_METADATA"
    except Exception as exc:
        res["status"]=type(exc).__name__+": "+str(exc)
    return res


def nc_sample(path,index,Dataset,nc):
    if not Path(path).is_file():raise FileNotFoundError(path)
    with Dataset(path,"r") as ds:
        vals={}
        for name in COMPARE_FIELDS:
            keys=[k for k in ds.variables if k.upper()==name]
            if len(keys)!=1:raise ValueError("Missing DATM variable "+name)
            v=ds.variables[keys[0]]
            if v.size!=17520:raise ValueError("DATM annual point size not 17520")
            import numpy as np
            raw=np.ma.asarray(v[index]).reshape(-1)
            if raw.size!=1 or bool(np.ma.getmaskarray(raw)[0]):
                raise ValueError("Masked or non-singleton DATM site value "+name)
            values=float(raw.data[0])
            if not math.isfinite(values):raise ValueError("Nonfinite DATM "+name)
            vals[name]=values
            vals[name+"_units"]=str(getattr(v,"units","")).lower().strip()
        if vals["QBOT_units"] not in ("kg/kg","kg kg-1","kg kg^-1","kg kg**-1","1"):
            raise ValueError("Unexpected QBOT source units")
        if vals["TBOT_units"] not in ("k","kelvin"):
            raise ValueError("Unexpected TBOT source units")
        if vals["PSRF_units"] not in ("pa","pascal","pascals"):
            raise ValueError("Unexpected pressure source units")
        timevar=ds.variables.get("time")
        if timevar is None or timevar.size!=17520:
            raise ValueError("Source annual time coordinate missing")
        units=str(getattr(timevar,"units",""))
        calendar=str(getattr(timevar,"calendar","standard"))
        stamp="NO_CF_DATM_TIME_UNITS"
        if " since " in units.lower():
            stamp=str(nc.num2date(float(timevar[index]),units=units,
                                 calendar=calendar,only_use_cftime_datetimes=True))
        return {
            "path":str(path),"index":index,"DATM_time":stamp,
            "QBOT_kgkg":vals["QBOT"],"TBOT_K":vals["TBOT"],
            "PSRF_Pa":vals["PSRF"],
            "vapor_pressure_hPa":vapour_hpa(vals["QBOT"],vals["PSRF"]),
            "RH_water_pct":100.*vapour_hpa(vals["QBOT"],vals["PSRF"])/buck_esw_hpa(vals["TBOT"]),
            "VPD_water_hPa":buck_esw_hpa(vals["TBOT"])-vapour_hpa(vals["QBOT"],vals["PSRF"]),
        }


def exact_source_rows(event):
    rows=event.get("original_FLUXMET_source_rows",[])
    per_clock=collections.defaultdict(list)
    for x in rows:
        if x.get("offset_minutes")==0 and x.get("source_time_column") in (
                "TIMESTAMP_START","TIMESTAMP_END"):
            per_clock[x["source_time_column"]].append(x)
    return {k:per_clock[k] for k in ("TIMESTAMP_START","TIMESTAMP_END")}


def fmt_source(row,ref_vpd):
    if row is None:return {"status":"NO_SOURCE_EXACT_TIME_MATCH"}
    fields=row.get("field_values",{})
    if not isinstance(fields,dict):raise ValueError("Wrong saved FLUXMET source field schema")
    chosen={k:fields.get(k) for k in SRC_FIELDS if k in fields}
    vpd=source_float(fields.get("VPD_F"))
    temp=source_float(fields.get("TA_F"))
    pa=source_float(fields.get("PA_F"))
    # Hypotheses are NOT evidence. TA_F in Celsius, VPD_F in hPa,
    # PA_F in kPa are the expected FLUXNET convention and must be checked
    # against file-specific metadata, QC provenance and time basis first.
    es=buck_esw_hpa(temp+273.15) if temp is not None and -90<temp<65 else None
    e=(es-vpd) if es is not None and vpd is not None else None
    q=None
    if e is not None and pa is not None and 0<=e<pa*10. and pa>0:
        ep=e*100
        pp=pa*1000
        q=.622*ep/(pp-.378*ep)
    return {
        "status":"SOURCE_CANDIDATE_UNVERIFIED_TIME_AND_QC",
        "raw_source_values":chosen,
        "FLUXMET_VPD_F_raw":fields.get("VPD_F"),
        "FLUXMET_VPD_F_QC_raw":fields.get("VPD_F_QC"),
        "FLUXMET_TA_F_QC_raw":fields.get("TA_F_QC"),
        "source_numeric_hypothesis":"TA_F_C, VPD_F_hPa, PA_F_kPa ONLY_IF_VERIFIED_FROM_PRODUCT_METADATA",
        "es_liquid_water_hPa_if_units_hypothesis":es,
        "vapor_hPa_if_units_hypothesis":e,
        "QBOT_kgkg_if_units_hypothesis":q,
        "VPD_F_minus_DATM_reference_VPD_hPa_if_units_hypothesis":
            vpd-ref_vpd if vpd is not None else None,
        "source_QC_interpretation":"UNVERIFIED",
        "timestamp_interpretation":"UNVERIFIED_START_END_AND_UTC",
        "ERA5_provenance":"UNVERIFIED",
    }


def selftest():
    fake_cases=[]
    for i in range(8):
        fake_cases.append({"case":CASE_REF if i==0 else "CH-Aws_FATES_TEST_"+str(i),
        "site_datm":[{"year":y,"path":"/synthetic/variant_"+str(min(i,6))+
                      "/CH-Aws_DATM_"+str(y)+".nc"} for y in YEARS]})
    c={"stage":STAGE_C,"science_release":False,
       "sites":[{"site":"CH-Aws","cases":fake_cases}]}
    e={"stage":STAGE_E,"science_release":False,
       "baseline_only_not_scientific_selection":True,
       "year_reports":[{"year":y,"comparisons":[{"comparison_status":"ALIGNED",
         "largest_5_HH":[{"time":"2007-07-22 07:30:00","index":42}] if y==2007 else []}]
         } for y in YEARS]}
    j={"stage":STAGE_J,"science_release":False,
       "raw_HH_product":{"scan_complete":True,"rows_scanned":333120,
                         "original_product_records":[{} for _ in range(200)]},
       "event_comparisons":[{} for _ in range(20)]}
    validate_inputs(c,e,j)
    assert len(case_paths(fake_cases))==7
    assert event_index(e)[(2007,"2007-07-22 07:30:00")]==42
    assert math.isclose(vapour_hpa(.004,80000),5.126,rel_tol=.02)
    assert source_float("-9999") is None
    assert source_float("12.5")==12.5
    sample={"field_values":{"TA_F":"7.52","VPD_F":"10.344","PA_F":"79.941",
                            "VPD_F_QC":"1"}}
    r=fmt_source(sample,4.0)
    assert r["FLUXMET_VPD_F_QC_raw"]=="1"
    print("STAGE02K SELF-TEST PASS: exact 7-path CH-Aws inventory, 20 source events, annual DATM event index, conditional units; NO WRITES")


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--self-test",action="store_true")
    ap.add_argument("--stage02j",type=Path)
    ap.add_argument("--stage02e",type=Path)
    ap.add_argument("--stage02c",type=Path)
    ap.add_argument("--out-dir",type=Path)
    args=ap.parse_args()
    if args.self_test:
        selftest();return
    for path in (args.stage02c,args.stage02e,args.stage02j):
        if path is None or not path.is_file():
            ap.error("Require existing source-pinned Stage02C, Stage02E and Stage02J JSON")
    if not args.out_dir or not args.out_dir.is_dir() or any(args.out_dir.iterdir()):
        ap.error("--out-dir must exist and be EMPTY")
    try:
        import netCDF4 as nc
    except ImportError as exc:
        ap.error("Activate clm_fates_env for netCDF4: "+str(exc))
    c=json.loads(args.stage02c.read_text())
    e=json.loads(args.stage02e.read_text())
    j=json.loads(args.stage02j.read_text())
    cases=validate_inputs(c,e,j)
    groups=case_paths(cases)
    indices=event_index(e)
    units=metadata_inventory(j)
    print("BIFVARINFO_METADATA",units["status"],"FILE",units["path"],
          "MATCHING_METADATA_ROWS",len(units["matched_variable_rows"]))
    events=[]
    rows=[]
    model_holds=0
    for event in j["event_comparisons"]:
        yr=int(str(event["time"])[:4])
        key=(yr,event["time"])
        if key not in indices:
            raise ValueError("No exact Stage02E half-hour index for "+str(key))
        i=indices[key]
        model=[]
        for group in groups:
            path=group["years"][yr]
            record={"cases":group["cases"],"path":path}
            try:
                snap=nc_sample(path,i,nc.Dataset,nc)
                if str(snap["DATM_time"])!=str(event["time"]):
                    raise ValueError("DATM CF time does not exactly match Stage02J event label: "+
                                     snap["DATM_time"]+" vs "+event["time"])
                record.update(snap)
                record["status"]="DATM_INTERNAL_EVENT_READ"
            except Exception as exc:
                model_holds+=1
                record["status"]="HOLD_"+type(exc).__name__
                record["error"]=str(exc)
            model.append(record)
        ref=next((v for v in model if CASE_REF in v["cases"]),None)
        if ref is None or ref.get("status")!="DATM_INTERNAL_EVENT_READ":
            raise ValueError("Missing/invalid historical reference DATM event "+str(key))
        same=[v for v in model if v.get("status")=="DATM_INTERNAL_EVENT_READ"]
        for v in same:
            if (abs(v["TBOT_K"]-ref["TBOT_K"])>1e-9 or
                abs(v["PSRF_Pa"]-ref["PSRF_Pa"])>1e-6):
                v["status"]="HOLD_NOT_QBOT_ONLY"
        if any(v.get("status")!="DATM_INTERNAL_EVENT_READ" for v in model):
            raise ValueError("Event DATM source mismatch; no scientific report written "+str(key))
        most=max(same,key=lambda v:abs(v["QBOT_kgkg"]-ref["QBOT_kgkg"]))
        original=exact_source_rows(event)
        source={}
        for clock in ("TIMESTAMP_START","TIMESTAMP_END"):
            options=original[clock]
            if len(options)!=1:
                source[clock]={"status":"HOLD_EXPECTED_EXACTLY_ONE_MATCH",
                               "match_count":len(options)}
            else:
                source[clock]=fmt_source(options[0],ref["VPD_water_hPa"])
        summary={
            "event_id":event["event_id"],"DATM_event_time":event["time"],"DATM_year":yr,
            "DATM_halfhour_index":i,
            "model_versions":model,
            "unapproved_reference_case":CASE_REF,
            "most_different_candidate_case":",".join(most["cases"]),
            "max_abs_QBOT_delta_gkg":abs(most["QBOT_kgkg"]-ref["QBOT_kgkg"])*1000,
            "same_time_source_alternative_START":source["TIMESTAMP_START"],
            "same_time_source_alternative_END":source["TIMESTAMP_END"],
            "source_QC_verified":False,"native_tower_observation_verified":False,
            "ERA5_source_verified":False,"time_start_end_verified":False,
            "scientific_release":"HOLD",
        }
        events.append(summary)
        print("EVENT",event["event_id"],event["time"],"INDEX",i,
              "MAX_ABS_DQ_GKG",round(summary["max_abs_QBOT_delta_gkg"],6),
              "REF_VPD_HPA",round(ref["VPD_water_hPa"],6),
              "TA_DATM_C",round(ref["TBOT_K"]-273.15,3),
              "SOURCE_START_VPD",source["TIMESTAMP_START"].get("FLUXMET_VPD_F_raw"),
              "SOURCE_END_VPD",source["TIMESTAMP_END"].get("FLUXMET_VPD_F_raw"),
              "START_QC",source["TIMESTAMP_START"].get("FLUXMET_VPD_F_QC_raw"),
              "END_QC",source["TIMESTAMP_END"].get("FLUXMET_VPD_F_QC_raw"))
        for clock in ("TIMESTAMP_START","TIMESTAMP_END"):
            v=source[clock]
            raw=v.get("raw_source_values",{})
            rows.append({
                "event_id":event["event_id"],"event_time_DATM":event["time"],
                "source_timestamp_column":clock,
                "original_timestamp":event["time"],
                "FLUXMET_TA_F":raw.get("TA_F"),"FLUXMET_VPD_F":raw.get("VPD_F"),
                "FLUXMET_VPD_F_QC":raw.get("VPD_F_QC"),
                "FLUXMET_TA_F_QC":raw.get("TA_F_QC"),
                "FLUXMET_RH":raw.get("RH"),"FLUXMET_TA_ERA":raw.get("TA_ERA"),
                "FLUXMET_VPD_ERA":raw.get("VPD_ERA"),
                "FLUXMET_PA":raw.get("PA"),"FLUXMET_PA_F":raw.get("PA_F"),
                "DATM_reference_QBOT_kgkg":ref["QBOT_kgkg"],
                "DATM_reference_TBOT_C":ref["TBOT_K"]-273.15,
                "DATM_reference_PSRF_Pa":ref["PSRF_Pa"],
                "DATM_reference_VPD_water_hPa":ref["VPD_water_hPa"],
                "source_VPD_F_delta_to_reference_hPa_HYPOTHESIS":
                    v.get("VPD_F_minus_DATM_reference_VPD_hPa_if_units_hypothesis"),
                "candidate_most_different_case":summary["most_different_candidate_case"],
                "candidate_most_different_QBOT_gkg":most["QBOT_kgkg"]*1000,
                "candidate_most_different_VPD_water_hPa":most["VPD_water_hPa"],
                "timestamp_basis_verified":False,"FLUXMET_units_verified":False,
                "original_tower_QC_verified":False,"ERA5_source_verified":False,
            })
    report={
        "stage":"STAGE02K_CH_AWS_FLUXMET_DATM_EVENT_PHYSICS_REVIEW",
        "read_only":True,"science_release":False,
        "input_modified":False,"Slurm_submitted":False,
        "stage02c":str(args.stage02c),"stage02e":str(args.stage02e),"stage02j":str(args.stage02j),
        "BIFVARINFO_source_metadata":units,
        "FLUXMET_numeric_assumptions_NOT_VERIFIED":"TA Celsius; VPD hPa; PA kPa; inspect product metadata",
        "FLUXMET_original_product_is_processed":True,
        "DATM_time_alignment_to_event_label_verified":True,
        "source_START_END_and_UTC_alignment_verified":False,
        "tower_native_QC0_verified":False,"ERA5_source_verified":False,
        "events":events,
    }
    p_json=args.out_dir/"stage02k_CH_Aws_source_DATM_event_physics.json"
    p_csv=args.out_dir/"stage02k_CH_Aws_source_DATM_two_clock_candidates.csv"
    with p_json.open("x",encoding="utf-8") as h:
        json.dump(report,h,indent=2);h.write("\n")
    with p_csv.open("x",encoding="utf-8",newline="") as h:
        w=csv.DictWriter(h,fieldnames=CSV_FIELDS);w.writeheader();w.writerows(rows)
    print("EVENT_COUNT",len(events),"MODEL_READ_HOLDS",model_holds)
    print("EXACT_START_END_SOURCE_CANDIDATE_ROWS",len(rows))
    print("JSON",p_json)
    print("CSV",p_csv)
    print("ALL DATM CASE SELECTION, TOWER QC AND ERA5 SCIENCE GATES HOLD; NO SOURCE MODIFICATIONS")


if __name__=="__main__":
    main()
