#!/usr/bin/env python3
"""OzFlux AU-Gin TERN FLUXNET Stage02: 2011–2025 HH actual MET source/QC audit.

Zero assumptions that a complete FLUXMET_HH timeline proves observations.
For 7 essential variables TA, VPD, SW_IN, LW_IN, PA, P, WS:
- exact source SHA256, ZIP file member, and Stage01 receipt checks;
- exact TIMESTAMP_START/END interval relationships (UTC NOT assumed);
- annual and monthly count of finite F and QC0/1/2/other/missing values;
- first/last QC0 per variable, Jan-May 2011 and year 2011 per-month detail;
- longest consecutive non-QC0 (gap-filled/ERA) and nonfinite periods;
- F vs packaged ERA by source QC class as only same-product comparison;
- conservative range/saturation triage; no physical edits;
- inspect actual BIF & BIFVARINFO metadata for provenance questions.

Original 2011 Jan 1 timestamp could be filled/artificial before June
installation; a 2011-2025 source label DOES NOT certify 15 years of tower
observations or 15 year continuous flux-based ecosystem measurement.

No original ZIP extraction, writing to source, existing OzFlux L6 overwrite,
DATM, Surface, CIME, Slurm or NOAA fetch. New HOME TSV/JSON only.
"""
from __future__ import annotations
import argparse,csv,datetime as dt,hashlib,io,json,math,re,sys,zipfile
from collections import Counter,defaultdict
from pathlib import Path

HOME=Path.home()
SOURCE=Path("/iridisfs/scratch/ly3n24/CLM_FATES/sites/MY_EC_SITE/AU-Gin/forcing/raw/TERN_FLUXNET_2011_2025/TERN_AU-Gin_FLUXNET_2011-2025_v1.3_r1.zip")
EXPECTED="acd78491b6f5f2c1374da2076d73a6c8b6ef430b256b78da3d300656943d6f14"
STAGE01=HOME/"ozflux_AU_Gin_stage01_20261104T053930Z/stage01_AU_Gin_TERN_2011_2025_original_ZIP_source_AUDIT_HOLD.json"
MEMBER="TERN_AU-Gin_FLUXNET_FLUXMET_HH_2011-2025_v1.3_r1.csv"
FIELDS=("TA","VPD","SW_IN","LW_IN","PA","P","WS")
QC_CLASSES=("QC0","QC1","QC2","QC_OTHER","QC_MISSING","F_MISSING","F_FINITE")
BINS={"TA":(-55,65),"VPD":(0,105),"SW_IN":(-10,1600),
      "LW_IN":(120,650),"PA":(65,110),"P":(-0.01,250),"WS":(-0.01,70)}
# Source values are numeric with -9999 and variants of -9999 as missing.
YEAR_HEAD=("year","variable","HH_total","F_finite","F_missing",
           "QC0_measured_class","QC1_gapfill_class","QC2_ERA_class",
           "QC_other","QC_missing","F_QC0_finite","F_QC1_finite",
           "F_QC2_finite","F_QC_other_finite",
           "QC0_fraction","ERA_QC2_fraction",
           "first_QC0_native","last_QC0_native","physical_screen_count",
           "ERA_matched_when_QC0_n","ERA_minus_F_at_QC0_mean","ERA_minus_F_at_QC0_RMSE")
MONTH_HEAD=("year","month","variable","HH_total","F_finite",
            "QC0","QC1","QC2","QC_other","QC_missing",
            "F_missing","F_QC0_finite","QC0_fraction")
SPELL_HEAD=("variable","class","first_native","last_native",
            "n_HH","hours","year_start","year_end",
            "rank_within_class","source_QC_approved")
def need(x,msg):
    if not x:raise ValueError(str(msg))
def sha(path):
    p=Path(path)
    need(p.is_file() and not p.is_symlink(),"Immutable source missing/symlink "+str(p))
    h=hashlib.sha256()
    with p.open("rb") as f:
        for block in iter(lambda:f.read(4<<20),b""):h.update(block)
    return h.hexdigest()
def parse(t):
    s=(t or "").strip()
    need(re.fullmatch(r"\d{12}",s) is not None,"Unrecognized source native timestamp: "+str(s))
    return dt.datetime.strptime(s,"%Y%m%d%H%M")
def number(t):
    try:
        a=float(str(t).strip())
        return a if math.isfinite(a) and a>-9990 else None
    except (ValueError,TypeError):return None
def qc(t):
    n=number(t)
    if n is None:return "QC_MISSING"
    if n in (0,1,2):return "QC"+str(int(n))
    return "QC_OTHER"
def row_key(y,m,var):
    return (y,m,var)
def new_bin():
    return {"n":0,"finite":0,"missing":0,
            "flags":Counter(),"finite_by_qc":Counter(),
            "physical":0,"first_obs":None,"last_obs":None,
            "era_count_qc0":0,"era_diff_sum":0.0,"era_diff_sq_sum":0.0}
def update_bin(d,stamp,var,value,flag,era):
    d["n"]+=1
    d["flags"][flag]+=1
    if value is None:d["missing"]+=1
    else:
        d["finite"]+=1
        d["finite_by_qc"][flag]+=1
        if flag=="QC0":
            if d["first_obs"] is None:d["first_obs"]=stamp
            d["last_obs"]=stamp
        lo,hi=BINS[var]
        if value<lo or value>hi:d["physical"]+=1
        if flag=="QC0" and era is not None:
            error=era-value
            d["era_count_qc0"]+=1
            d["era_diff_sum"]+=error
            d["era_diff_sq_sum"]+=error*error
def span_obj(var,category,start,end,num):
    return dict(variable=var,**{"class":category},
      first_native=start.strftime("%Y-%m-%d %H:%M"),
      last_native=end.strftime("%Y-%m-%d %H:%M"),
      n_HH=num,hours=num/2,year_start=start.year,year_end=end.year)
def save_tsv(path,fieldnames,rows):
    with path.open("x",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=fieldnames,delimiter="\t",extrasaction="ignore")
        w.writeheader();w.writerows(rows)
def summary_year(y,var,b):
    N=b["n"]
    return {"year":y,"variable":var,"HH_total":N,
      "F_finite":b["finite"],"F_missing":b["missing"],
      "QC0_measured_class":b["flags"]["QC0"],
      "QC1_gapfill_class":b["flags"]["QC1"],
      "QC2_ERA_class":b["flags"]["QC2"],
      "QC_other":b["flags"]["QC_OTHER"],
      "QC_missing":b["flags"]["QC_MISSING"],
      "F_QC0_finite":b["finite_by_qc"]["QC0"],
      "F_QC1_finite":b["finite_by_qc"]["QC1"],
      "F_QC2_finite":b["finite_by_qc"]["QC2"],
      "F_QC_other_finite":b["finite_by_qc"]["QC_OTHER"],
      "QC0_fraction":b["finite_by_qc"]["QC0"]/N,
      "ERA_QC2_fraction":b["flags"]["QC2"]/N,
      "first_QC0_native":b["first_obs"].isoformat(sep=" ") if b["first_obs"] else "",
      "last_QC0_native":b["last_obs"].isoformat(sep=" ") if b["last_obs"] else "",
      "physical_screen_count":b["physical"],
      "ERA_matched_when_QC0_n":b["era_count_qc0"],
      "ERA_minus_F_at_QC0_mean":b["era_diff_sum"]/b["era_count_qc0"]
                                  if b["era_count_qc0"] else None,
      "ERA_minus_F_at_QC0_RMSE":math.sqrt(
           b["era_diff_sq_sum"]/b["era_count_qc0"])
                                  if b["era_count_qc0"] else None}
def summary_month(y,m,var,b):
    N=b["n"]
    return {"year":y,"month":m,"variable":var,"HH_total":N,
      "F_finite":b["finite"],
      "QC0":b["flags"]["QC0"],"QC1":b["flags"]["QC1"],
      "QC2":b["flags"]["QC2"],"QC_other":b["flags"]["QC_OTHER"],
      "QC_missing":b["flags"]["QC_MISSING"],
      "F_missing":b["missing"],
      "F_QC0_finite":b["finite_by_qc"]["QC0"],
      "QC0_fraction":b["finite_by_qc"]["QC0"]/N}
def bif_samples(z):
    result={}
    for name in z.namelist():
        base=name.rsplit("/",1)[-1]
        if "BIF" not in base.upper() or not base.lower().endswith(".csv"):
            continue
        if "BIFVARINFO" not in base.upper() and not re.search(r"_BIF_20",base):
            continue
        picked=[];row_count=0
        info=z.getinfo(name)
        need(info.file_size<32_000_000,"BIF source member >32MB, inspect separately: "+name)
        with z.open(name) as data:
            raw=data.read(info.file_size+1)
            need(len(raw)==info.file_size,"BIF original bytes length mismatch: "+name)
            try:
                decoded=raw.decode("utf-8-sig")
                encoding="utf-8-sig"
                warning=None
            except UnicodeDecodeError as exc:
                warning="Non-UTF8 source byte at offset "+str(exc.start)+" = 0x"+format(raw[exc.start],"02x")
                try:
                    decoded=raw.decode("cp1252")
                    encoding="cp1252"
                except UnicodeDecodeError:
                    decoded=raw.decode("latin-1")
                    encoding="latin-1"
            reader=csv.DictReader(io.StringIO(decoded,newline=""))
            need({"SITE_ID","VARIABLE","DATAVALUE"}.issubset(set(reader.fieldnames or [])),
                 "BIF metadata schema does not contain mandatory fields: "+name)
            for r in reader:
                row_count+=1
                site=(r.get("SITE_ID") or "").strip()
                if site and site!="AU-Gin":continue
                var=(r.get("VARIABLE") or "").strip()
                val=(r.get("DATAVALUE") or "").strip()
                focus=bool(re.search(r"LAT|LON|HEIGHT|ELEV|TIME|START|END|YEAR|DATE|SITE_NAME|INSTRUMENT|VEGETATION|LAND_USE|ESTABLISH|SOIL",var,re.I))
                if focus and len(picked)<160:
                    picked.append({"variable":var,"value":val[:180],
                                   "variable_group":r.get("VARIABLE_GROUP"),
                                   "group_id":r.get("GROUP_ID")})
        result[base]={"rows":row_count,"selected_provenance_fields":picked,
          "original_BIF_member_SHA256":hashlib.sha256(raw).hexdigest(),
          "source_byte_count":len(raw),
          "encoding_used":encoding,"encoding_is_inferred":True,
          "non_ascii_byte_count":sum(v>=128 for v in raw),
          "decoding_warning":warning}
    return result
def selftest():
    need(parse("201101010000")==dt.datetime(2011,1,1),"timestamp")
    need(parse("202601010000")-parse("202512312330")==dt.timedelta(minutes=30),
         "interval end")
    need(number("-9999.0000") is None and number("0.0")==0.0,
         "missing numeric source")
    need(qc("0.0")=="QC0" and qc("2")=="QC2" and qc("3")=="QC_OTHER","flags")
    b=new_bin()
    update_bin(b,dt.datetime(2011,1,1),"TA",10, "QC0",11)
    need(summary_year(2011,"TA",b)["ERA_minus_F_at_QC0_RMSE"]==1.0,
         "per QC class stats")
    print("OZFLUX AU-GIN STAGE02 SELFTEST PASS | exact source/year/month/QC0/ERA and 2011 origin; READ ONLY")
def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--self-test",action="store_true")
    p.add_argument("--out",type=Path)
    a=p.parse_args()
    if a.self_test:return selftest()
    o=a.out
    need(o is not None and o.parent.resolve()==HOME.resolve()
         and not o.exists() and not o.is_symlink(),"Output must be a NEW direct HOME folder")
    need(sha(SOURCE)==EXPECTED,"Original TERN ZIP bytes changed")
    prior=json.loads(STAGE01.read_text(encoding="utf-8"))
    need(prior.get("source_sha256_verified")==EXPECTED and
         prior.get("native_FLUXMET_HH_timeline",{}).get("total_rows")==262992 and
         prior.get("AD400_authorised") is False,
         "Actual Stage01 source/coverage science receipt changed")
    # Source CSV is read as a stream; do not materialise all ~263k rows in RAM.
    monthly=defaultdict(new_bin)
    annual=defaultdict(new_bin)
    obs_firstlast={v:{"first":None,"last":None} for v in FIELDS}
    spells=defaultdict(list);open_spells={}
    first_start=None;last_end=None;prev_end=None
    n=0;native_bad_end=0;native_noncontiguous=0
    n_measure_any=0;n_measure_all=0;n_era_any=0
    nighttime_solar_alarms=0;vpd_ta_supersaturation=0
    with zipfile.ZipFile(SOURCE,"r") as z:
        names=z.namelist()
        need(names.count(MEMBER)==1,"Unique FLUXMET_HH source file lost")
        nfo=z.getinfo(MEMBER)
        need(nfo.file_size<4_000_000_000,"Unexpected >4GB HH payload")
        bif=bif_samples(z)
        with z.open(MEMBER,"r") as stream:
            r=csv.DictReader(io.TextIOWrapper(stream,encoding="utf-8-sig",newline=""))
            required={"TIMESTAMP_START","TIMESTAMP_END"}
            for v in FIELDS:required.update([v+"_F",v+"_F_QC",v+"_ERA"])
            need(required.issubset(set(r.fieldnames or [])),
                 "Unexpected missing original FLUXMET_HH met columns: "+str(sorted(required-set(r.fieldnames or []))))
            for row in r:
                start=parse(row["TIMESTAMP_START"]);end=parse(row["TIMESTAMP_END"])
                need(start.year in range(2011,2026),"Raw year outside 2011..2025")
                if end-start!=dt.timedelta(minutes=30):native_bad_end+=1
                if prev_end is not None and prev_end!=start:native_noncontiguous+=1
                if first_start is None:first_start=start
                prev_end=end;last_end=end
                n+=1
                flags={}
                values={}
                for v in FIELDS:
                    observed=number(row[v+"_F"])
                    era=number(row[v+"_ERA"])
                    flag=qc(row[v+"_F_QC"])
                    flags[v]=flag;values[v]=observed
                    update_bin(monthly[(start.year,start.month,v)],start,v,observed,flag,era)
                    update_bin(annual[(start.year,v)],start,v,observed,flag,era)
                    if flag=="QC0" and observed is not None:
                        if obs_firstlast[v]["first"] is None:obs_firstlast[v]["first"]=start
                        obs_firstlast[v]["last"]=start
                    for cat,ispart in (("NON_QC0",flag!="QC0"),
                         ("ERA_QC2",flag=="QC2"),
                         ("F_MISSING",observed is None)):
                        key=(v,cat)
                        opened=open_spells.get(key)
                        if ispart:
                            if opened is None:open_spells[key]=(start,start,1)
                            else:open_spells[key]=(opened[0],start,opened[2]+1)
                        elif opened:
                            spells[key].append(span_obj(v,cat,*opened))
                            open_spells.pop(key)
                if any(flags[v]=="QC0" for v in FIELDS):n_measure_any+=1
                if all(flags[v]=="QC0" and values[v] is not None for v in FIELDS):
                    n_measure_all+=1
                if any(flags[v]=="QC2" for v in FIELDS):n_era_any+=1
                ta=values["TA"];vpd=values["VPD"]
                if ta is not None and vpd is not None:
                    es=6.112*math.exp(max(-50,min(30,17.67*ta/(ta+243.5)))) if -100<ta<90 else None
                    if es is not None and vpd>es*1.05:vpd_ta_supersaturation+=1
        for key,record in open_spells.items():
            spells[key].append(span_obj(key[0],key[1],*record))
    need(n==262992 and first_start==dt.datetime(2011,1,1) and
         last_end==dt.datetime(2026,1,1),
         "2011..2025 original 15-calendar-year source span changed")
    need(native_bad_end==0 and native_noncontiguous==0,
         "Source native TIMESTAMP_START/END 30min continuity changed")
    summary=[]
    for y in range(2011,2026):
        for v in FIELDS:
            b=annual[(y,v)]
            required_rows=48*(366 if (y%4==0 and (y%100!=0 or y%400==0)) else 365)
            need(b["n"]==required_rows,"Unexpected source annual halfhours "+str((y,v)))
            summary.append(summary_year(y,v,b))
    monthly_out=[summary_month(y,m,v,monthly[(y,m,v)])
        for y in range(2011,2026) for m in range(1,13) for v in FIELDS]
    largest=[]
    for key,sp in sorted(spells.items()):
        sorted_sp=sorted(sp,key=lambda r:(-r["n_HH"],r["first_native"]))[:20]
        for j,x in enumerate(sorted_sp,1):
            largest.append({**x,"rank_within_class":j,
                            "source_QC_approved":False})
    results={"site":"AU-Gin","stage":"Stage02 original TERN FLUXNET HH source/QC",
      "original_ZIP_SHA256":EXPECTED,"member":MEMBER,"original_file_size_bytes":SOURCE.stat().st_size,
      "first_timestamp_start":first_start.isoformat(sep=" "),
      "last_timestamp_end":last_end.isoformat(sep=" "),
      "native_total_HH":n,
      "native_non30minute_timestamp_end_rows":native_bad_end,
      "native_noncontiguous_interval_rows":native_noncontiguous,
      "native_timezone_unverified":True,
      "first_last_QC0_records":{v:{k:d.isoformat(sep=" ") if d is not None else None
                                 for k,d in z.items()} for v,z in obs_firstlast.items()},
      "2011_JAN_to_MAY_QC0_by_variable":{
         v:sum(monthly[(2011,m,v)]["finite_by_qc"]["QC0"] for m in range(1,6))
         for v in FIELDS},
      "2011_JAN_to_MAY_ERA_QC2_by_variable":{
         v:sum(monthly[(2011,m,v)]["flags"]["QC2"] for m in range(1,6))
         for v in FIELDS},
      "2011_monthly_qc_summary":[r for r in monthly_out if r["year"]==2011],
      "all_seven_met_QC0_finite_HH":n_measure_all,
      "at_least_one_met_QC0_HH":n_measure_any,
      "at_least_one_met_ERA_QC2_HH":n_era_any,
      "source_physics_VPD_exceeds_saturation_at_reported_Ta_1p05":vpd_ta_supersaturation,
      "all_annual_qc_summary":summary,
      "BIF_BIFVARINFO_original_metadata_excerpts":bif,
      "source_2011_before_station_June_established_provenanced":False,
      "15_calendar_years_label_verified":True,
      "15_full_years_original_tower_met_verified":False,
      "15_full_years_model_forcing_QC_approved":False,
      "ERA_is_same_Fluxnet_processed_source_not_independent_reference":True,
      "old_Gingin_L6_not_overwritten":True,
      "source_QC0_means_measured_class_NOT_independent_sensor_verification":True,
      "science_release":False,"AD400_authorised":False,
      "no_source_DATM_Surface_CIME_Slurm_modified":True}
    o.mkdir(mode=0o700,parents=False,exist_ok=False)
    save_tsv(o/"stage02_AU_Gin_2011_2025_annual_7met_QC_provenance.tsv",YEAR_HEAD,summary)
    save_tsv(o/"stage02_AU_Gin_2011_2025_monthly_7met_QC_provenance.tsv",MONTH_HEAD,monthly_out)
    save_tsv(o/"stage02_AU_Gin_longest_nonQC0_ERA_missing_spells.tsv",SPELL_HEAD,largest)
    (o/"stage02_AU_Gin_15yr_source_2011_early_QC_science_HOLD.json").write_text(
       json.dumps(results,indent=2,ensure_ascii=False),encoding="utf-8")
    print("AU-GIN STAGE02 SOURCE ZIP SHA256 VERIFIED",EXPECTED)
    print("NATIVE_HH",n,"START",results["first_timestamp_start"],
          "LAST_END",results["last_timestamp_end"],"BAD_INTERVALS",native_bad_end,
          "NONCONTIGUOUS",native_noncontiguous)
    print("FIRST_LAST_QC0",json.dumps(results["first_last_QC0_records"]))
    print("2011_JAN_MAY_ORIGINAL_QC0",json.dumps(results["2011_JAN_to_MAY_QC0_by_variable"]))
    print("2011_JAN_MAY_ERA_QC2",json.dumps(results["2011_JAN_to_MAY_ERA_QC2_by_variable"]))
    for y in range(2011,2026):
        fields=[(v,annual[(y,v)]) for v in FIELDS]
        print("YEAR",y," ".join(f"{v}:obs{b['finite_by_qc']['QC0']}/{b['n']},ERA{b['flags']['QC2']},missing{b['missing']}"
              for v,b in fields))
    for v in FIELDS:
        for cat in ("NON_QC0","ERA_QC2","F_MISSING"):
            sp=sorted(spells.get((v,cat),[]),key=lambda z:(-z["n_HH"],z["first_native"]))
            if sp:
                print("LONGEST",v,cat,sp[0]["first_native"],sp[0]["last_native"],
                      "HH",sp[0]["n_HH"])
    print("BIF_METADATA_SOURCE_EXCERPT_COUNTS",
          json.dumps({k:{"rows":x["rows"],"selected":len(x["selected_provenance_fields"])}
                      for k,x in bif.items()}))
    print("STAGE02 READONLY QC SOURCE TRIAGE PASS; SCIENCE HOLD; NO DATM/AD400/SLURM")
    print("REPORT_DIR",o)
if __name__=="__main__":main()
