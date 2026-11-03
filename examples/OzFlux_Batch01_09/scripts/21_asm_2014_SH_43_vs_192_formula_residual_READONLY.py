#!/usr/bin/env python3
"""AU-ASM Stage21: SOURCE-PINNED 2014 SH 43-vs-192 L3/L6 thermodynamic audit.

Review exact Stage20 235 source-QC0 mismatch episode values; compare the
2014 Aug 192-halfhour AH/RH-compatible episode to the 2014 Nov/Dec 43-HH
AH/RH-incompatible episode. Quantify SH residuals (g/kg), L3/L6 AH,
RH, temperature and pressure differences and original QC classifications.
Test potential 1-4 halfhour temporal misalignment of reconstructed q,
and calculate pressure implied by source AH, Ta and reported SH as a
diagnostic; NEVER assume the latter is actual pressure.

All arithmetic is READ ONLY. Matching is mathematical consistency, NOT
proof of original sensor measurement or correct source QC. No repairs to
L3, L6, DATM, Surface, CIME, Slurm; remain science HOLD.
"""
from __future__ import annotations
import argparse,csv,hashlib,json,math,statistics,sys
from collections import Counter
from pathlib import Path

HOME=Path.home()
S20=HOME/"ozflux_nc_stage20_20261103T182509Z"
STAGE20_JSON=S20/"stage20_2014_SH_QC0_source_science_HOLD.json"
STAGE20_TSV=S20/"stage20_235_SH_and_aux_humidity_source_rows.tsv"
L3=HOME/"ozflux_ASM_TERN_2026v3_L3_source/AliceSpringsMulga_20100903T0000_to_20230308T0900_L3.nc"
L3_SHA="8faa211fe95aa9f0382bf8d3848cb3245d6c8a25bf4ac440e6e92a77c8759076"
L6=Path("/iridisfs/scratch/ly3n24/CLM_FATES/sites/MY_EC_SITE/AU-ASM/forcing/raw/AliceSpringsMulga1_20100903T0000_to_20230308T0900_L6.nc")
L6_SHA="b9381c4ed0744d03ae609cfbf3805e30bbb9223851a05f4e5b63b149dd0b10eb"
EPISODES=(
    ("AUG192","2014-08-26 17:30:00","2014-08-30 17:00:00",192),
    ("NOV43","2014-11-30 15:00:00","2014-12-01 12:00:00",43)
)
SAMPLE=("episode","native_time","L3_SH","L3_SH_QC","L6_SH",
    "L6_SH_QC","L3_AH","L3_AH_QC","L6_AH","L6_AH_QC",
    "L3_RH","L3_RH_QC","L6_RH","L6_RH_QC",
    "L3_ps","L3_ps_QC","L6_ps","L6_ps_QC",
    "L3_Ta","L3_Ta_QC","L6_Ta","L6_Ta_QC",
    "SH_from_L6_AH_Ta_ps","SH_from_L6_RH_Ta_ps",
    "L6_SH_minus_AH_estimate_gkg","L6_SH_minus_RH_estimate_gkg",
    "AH_implied_pressure_kPa_diagnostic")
def need(ok,why):
    if not ok:raise ValueError(why)
def sha(p):
    p=Path(p)
    need(p.is_file() and not p.is_symlink(),"Missing source "+str(p))
    h=hashlib.sha256()
    with p.open("rb") as f:
        for x in iter(lambda:f.read(4<<20),b""):h.update(x)
    return h.hexdigest()
def read_csv(p):
    need(p.is_file() and not p.is_symlink(),"Missing Stage20 CSV "+str(p))
    with p.open(encoding="utf-8",newline="") as f:
        return list(csv.DictReader(f,delimiter="\t"))
def value(s):
    if s is None or s=="":return None
    try:v=float(s)
    except (ValueError,TypeError):return None
    return v if math.isfinite(v) and v>-9990 else None
def median(values):
    return float(statistics.median(values)) if values else None
def mean(values):
    return float(statistics.fmean(values)) if values else None
def stat(values):
    a=[float(x) for x in values if x is not None and math.isfinite(x)]
    return {"n":len(a),"min":min(a) if a else None,
            "median":median(a),"mean":mean(a),
            "max":max(a) if a else None,
            "max_abs":max(map(abs,a)) if a else None}
def implied_pressure(sh,ah,ta):
    # q = 0.622 e / (p - 0.378 e)
    # e_hPa = AH [g m-3] * T_K / 216.7, p_kPa = p_hPa/10
    if sh is None or ah is None or ta is None:return None
    if sh<=0 or ah<0 or not(-80<ta<70):return None
    e=ah*(ta+273.15)/216.7
    p_hpa=.622*e/sh+.378*e
    return p_hpa/10 if 20<p_hpa/10<150 else None
def qv(row,key):
    return value(row.get(key))
def best_time_lag(rows):
    # Distinguish a one-record stale/shifted SH series from true calculation
    # mismatch, but do not apply or approve a shift.
    target=[qv(r,"L6_SH") for r in rows]
    source=[qv(r,"SH_from_L6_AH_Ta_ps") for r in rows]
    scores={}
    for offset in range(-4,5):
        errors=[]
        for i,p in enumerate(target):
            j=i+offset
            if p is not None and 0<=j<len(source) and source[j] is not None:
                errors.append(abs(p-source[j])*1000)
        scores[str(offset)]={"pairs":len(errors),"MAE_gkg":mean(errors),
                  "max_absolute_gkg":max(errors) if errors else None}
    best=min((v["MAE_gkg"],int(k)) for k,v in scores.items()
             if v["MAE_gkg"] is not None)[1]
    return {"offsets_HH":scores,"lowest_MAE_offset_HH":best,
            "lag_is_only_a_hypothesis":True}
def selftest():
    need(abs(implied_pressure(.00732,8.64,20)-100)<5,"pressure inverse")
    need(value("-9999")==None and value("0.0")==0,"QC parse")
    need(stat([0.1,-0.1])["max_abs"]==0.1,"stats")
    print("OZFLUX STAGE21 SELF-TEST PASS | 43 vs 192 SH formula residual + QC/lag diagnostics, READ ONLY")
def main():
    if sys.argv[1:]==["--self-test"]:return selftest()
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out",type=Path,required=True)
    o=p.parse_args().out
    need(o.parent.resolve()==HOME.resolve() and not o.exists() and not o.is_symlink(),
         "Use new direct HOME output directory")
    need(sha(L3)==L3_SHA and sha(L6)==L6_SHA,
         "Actual immutable L3 or L6 bytes changed")
    r20=json.loads(STAGE20_JSON.read_text(encoding="utf-8"))
    need(r20["L3_SHA256"]==L3_SHA and r20["L6_SHA256"]==L6_SHA and
         r20["source_exceptions_exactly"]==235 and
         r20["n_spells"]==2 and
         r20["science_release"] is False and
         r20["AD400_authorised"] is False,
         "Stage20 verified operator science HOLD changed")
    require_spells={z["start_native"]:(z["end_native"],int(z["n_HH"]))
                    for z in r20["episodes"]}
    raw=read_csv(STAGE20_TSV)
    need(len(raw)>=235,"Stage20 context insufficient")
    result={}
    output=[]
    for name,start,end,N in EPISODES:
        need(require_spells.get(start)==(end,N),
             "Stage20 episode scope changed "+name)
        rows=[r for r in raw if start<=r["native_time"]<=end]
        need(len(rows)==N and len(set(r["native_time"] for r in rows))==N,
             "Expected exactly original "+str(N)+" source halfhours")
        need(all(qv(r,"L3_SH_QC")==1 and qv(r,"L6_SH_QC")==0 and
                  qv(r,"L3_SH") is None and qv(r,"L6_SH") is not None
                 for r in rows),"Original SH L3-gap / L6-QC0 cohort changed")
        flags={f"{source}_{var}_QC":dict(Counter(
               str(qv(r,f"{source}_{var}_QC")) for r in rows))
               for source in ("L3","L6")
               for var in ("SH","AH","RH","VPD","Ta","ps")
               if f"{source}_{var}_QC" in rows[0]}
        d={"start":start,"end":end,"records":N,
           "flags":flags,"variable_changes":{},
           "sensitivity_NOT_applied":True}
        for var in ("AH","RH","Ta","ps","VPD"):
            x=[qv(r,f"L3_{var}") for r in rows]
            y=[qv(r,f"L6_{var}") for r in rows]
            paired=[y[i]-x[i] for i in range(N)
                    if x[i] is not None and y[i] is not None]
            d["variable_changes"][var]={
                "L3_source":stat(x),"L6_value":stat(y),
                "L6_minus_L3_when_both_valid":stat(paired)}
        delta_ah=[];delta_rh=[];press=[];p_errors=[]
        for r in rows:
            sh=qv(r,"L6_SH")
            qah=qv(r,"SH_from_L6_AH_Ta_ps")
            qrh=qv(r,"SH_from_L6_RH_Ta_ps")
            err_ah=(sh-qah)*1000 if qah is not None else None
            err_rh=(sh-qrh)*1000 if qrh is not None else None
            if err_ah is not None:delta_ah.append(err_ah)
            if err_rh is not None:delta_rh.append(err_rh)
            p_imp=implied_pressure(sh,qv(r,"L6_AH"),qv(r,"L6_Ta"))
            if p_imp is not None:press.append(p_imp)
            ps=qv(r,"L6_ps")
            if p_imp is not None and ps is not None:p_errors.append(p_imp-ps)
            output.append({k:{"episode":name,"L6_SH_minus_AH_estimate_gkg":err_ah,
                        "L6_SH_minus_RH_estimate_gkg":err_rh,
                        "AH_implied_pressure_kPa_diagnostic":p_imp}.get(k,r.get(k))
                        for k in SAMPLE})
        d["SH_minus_AH_based_estimate_gkg"]=stat(delta_ah)
        d["SH_minus_RH_based_estimate_gkg"]=stat(delta_rh)
        d["AH_SH_implied_pressure_kPa_not_observed"]=stat(press)
        d["implied_pressure_minus_reported_AWS_ps_kPa"]=stat(p_errors)
        d["SH_vs_AH_one_to_four_HH_lag_screen"]=best_time_lag(rows)
        d["RH_SH_matches_1e-5"] = sum(abs(v)<=.01 for v in delta_rh)
        d["AH_SH_matches_1e-5"] = sum(abs(v)<=.01 for v in delta_ah)
        result[name]=d
    need(result["AUG192"]["AH_SH_matches_1e-5"]==192
         and result["AUG192"]["RH_SH_matches_1e-5"]==192,
         "August positive reference control lost")
    need(result["NOV43"]["AH_SH_matches_1e-5"]==0
         and result["NOV43"]["RH_SH_matches_1e-5"]==0,
         "November source discrepancy no longer matches Stage20")
    report={"stage":"AU-ASM Stage21 read-only 2014 43-vs-192 original SH source forensic",
        "L3_SHA256":L3_SHA,"L6_SHA256":L6_SHA,
        "stage20_report":str(STAGE20_JSON),"n_source_exceptions":235,
        "episodes":result,
        "source_SH_QC0_approved":False,
        "reconstructed_equations_do_not_prove_true_measurement":True,
        "pressure_implied_by_q_AH_is_not_observation":True,
        "AWSPressure_calibration_proven":False,
        "force_change_original_QCFlag":False,
        "proposed_repair_authorised":False,
        "science_release":False,"AD400_authorised":False,
        "no_inputs_surface_CIME_slurm_changed":True}
    o.mkdir(mode=0o700,parents=False,exist_ok=False)
    with (o/"stage21_exact_235_SH_differential_43_vs_192.tsv").open(
             "x",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=SAMPLE,delimiter="\t",extrasaction="raise")
        w.writeheader();w.writerows(output)
    (o/"stage21_43vs192_SH_formula_pressure_QC_science_HOLD.json").write_text(
       json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    for name,d in result.items():
        print("EPISODE",name,d["start"],d["end"],"HH",d["records"])
        for var in ("AH","RH","Ta","ps"):
            print("L3_VS_L6",name,var,json.dumps(
                  d["variable_changes"][var]["L6_minus_L3_when_both_valid"]))
        print("SOURCE_QC_FLAGS",name,json.dumps(d["flags"]))
        print("SH_MINUS_AH_FORMULA_gkg",name,json.dumps(d["SH_minus_AH_based_estimate_gkg"]))
        print("SH_MINUS_RH_FORMULA_gkg",name,json.dumps(d["SH_minus_RH_based_estimate_gkg"]))
        print("AH_SH_IMPLIED_PRESSURE_MINUS_AWS_PS_kPa",name,
              json.dumps(d["implied_pressure_minus_reported_AWS_ps_kPa"]))
        print("BEST_TIME_LAG_DONOR_Q_HH",name,
              d["SH_vs_AH_one_to_four_HH_lag_screen"]["lowest_MAE_offset_HH"])
        if name=="NOV43":
            for row in [x for x in output if x["episode"]=="NOV43"][:5]:
                print("NOV43_EXAMPLE",row["native_time"],
                      "L6_SH",row["L6_SH"],"AH",row["L6_AH"],"RH",row["L6_RH"],
                      "Ta",row["L6_Ta"],"ps",row["L6_ps"],
                      "Q_FROM_AH",row["SH_from_L6_AH_Ta_ps"],
                      "Q_FROM_RH",row["SH_from_L6_RH_Ta_ps"],
                      "Q_DELTA_AH_GKG",row["L6_SH_minus_AH_estimate_gkg"],
                      "Q_IMPLIED_PRESSURE_kPa",row["AH_implied_pressure_kPa_diagnostic"])
    print("STAGE21 2014 SH ORIGIN SCREEN COMPLETE; SCIENCE HOLD; NO AD400/SLURM")
    print("REPORT_DIR",o)
if __name__=="__main__":main()
