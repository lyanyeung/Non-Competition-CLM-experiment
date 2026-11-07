#!/usr/bin/env python3
"""AU-Gin Stage12: discover actual first-party sensor/meteorological provenance.

After *actual operator* Stage11 (5 spikes, 2 VPD QC1 physical inconsistencies),
inspect native TERN ZIP member/header inventory, original BIF and BIFVARINFO_HH,
and old OzFlux L6 netCDF metadata as a separate, non-interchangeable lineage.

Crucial nuance: Stage11 TA RAW=None and RH RAW=None reflect that Stage10's
selected source-context table has no TA_raw, and RH raw was missing at those
particular timestamps. They do NOT prove no raw TA/RH sensor measurements
exist in any OTHER file or older OzFlux L6.

NO source writes, NO interpolation / constrained VPD applied, NO DATM/Slurm.
"""
from __future__ import annotations
import argparse,csv,datetime as dt,hashlib,io,json,math,re,zipfile
from pathlib import Path
H=Path.home()
ZIP=Path("/iridisfs/scratch/ly3n24/CLM_FATES/sites/MY_EC_SITE/AU-Gin/forcing/raw/TERN_FLUXNET_2011_2025/TERN_AU-Gin_FLUXNET_2011-2025_v1.3_r1.zip")
OLD_L6=Path("/iridisfs/scratch/ly3n24/CLM_FATES/sites/MY_EC_SITE/AU-Gin/forcing/raw/Gingin_L6.nc")
ZIP_SHA="acd78491b6f5f2c1374da2076d73a6c8b6ef430b256b78da3d300656943d6f14"
D11=H/"ozflux_AU_Gin_stage11_20261107T044259Z"
D10=H/"ozflux_AU_Gin_stage10_20261105T184415Z"
SOURCE11=D11/"stage11_AU_Gin_7priority_source_science_HOLD.json"
VPD11=D11/"stage11_AU_Gin_2VPD_QC1_source_RH_physics.tsv"
SPIKE11=D11/"stage11_AU_Gin_5spike_multivar_source_gate.tsv"
HOLD11=D11/"stage11_AU_Gin_28group_HOLD_receipt.tsv"
SOURCE10=D10/"stage10_AU_Gin_full_28event_7priority_science_HOLD.json"
CONTEXT10=D10/"stage10_AU_Gin_7priority_91HH_original_multivar_context.tsv"
FLUXMET="TERN_AU-Gin_FLUXNET_FLUXMET_HH_2011-2025_v1.3_r1.csv"
BIF="TERN_AU-Gin_FLUXNET_BIF_2011-2025_v1.3_r1.csv"
BIF_SHA="d28640e9f9a1bef14d0dc54679f56f4674652e88efc9ac15a93425e725fb8a0e"
TARGETS={
 "PA_20120609_PREVIOUS":("2012-06-09 08:00:00","PA"),
 "PA_20120610":("2012-06-10 13:30:00","PA"),
 "TA_20160507":("2016-05-07 16:00:00","TA"),
 "TA_20160520":("2016-05-20 18:00:00","TA"),
 "WS_20190913":("2019-09-13 03:00:00","WS"),
 "VPD_QC1_20130205":("2013-02-05 06:30:00","VPD"),
 "VPD_QC1_20130216":("2013-02-16 07:00:00","VPD")}
TGT_STRINGS={x[0].replace("-","").replace(" ","").replace(":","") for x in TARGETS.values()}
INV_COLS=("zip_member","uncompressed_size_bytes","compressed_size_bytes",
          "is_csv","looks_like_hh_timestamped_data","timestamp_field",
          "column_count","raw_like_TA_columns","raw_like_RH_columns",
          "raw_like_VPD_columns","raw_like_WS_columns",
          "raw_like_PA_columns","has_TA_F","has_VPD_F",
          "header_preview","header_decoder")
BIF_COLS=("member","original_member_SHA256","decoder","row_index",
          "SITE_ID","VARIABLE_GROUP","VARIABLE","DATAVALUE","GROUP_ID",
          "source_original_row_json")
CAND_COLS=("source_member","member_SHA256","source_clock_is_NOT_assumed_verified",
           "source_native_time","candidate_variable","candidate_raw_value",
           "candidate_native_column","is_nonFLUXMET_separate_sensor_record",
           "scientific_repair_authorised")
L6_COLS=("original_netCDF_path","old_L6_SHA256","variable_name","dimensions",
         "shape","dtype","units","long_name","standard_name",
         "measurement_height","calendar_or_time_units","source_lineage_verified")
def require(x,s):
    if not x:raise RuntimeError(str(s))
def sha(p):
    p=Path(p)
    require(p.is_file() and not p.is_symlink(),"Source missing/symlink "+str(p))
    h=hashlib.sha256()
    with p.open("rb") as f:
        for q in iter(lambda:f.read(4<<20),b""):h.update(q)
    return h.hexdigest()
def tsvin(p):
    with p.open(encoding="utf-8",newline="") as f:
        return list(csv.DictReader(f,delimiter="\t"))
def tsvout(path,cols,items):
    with path.open("x",encoding="utf-8",newline="") as f:
        wr=csv.DictWriter(f,delimiter="\t",fieldnames=cols,extrasaction="raise")
        wr.writeheader();wr.writerows(items)
def is_raw(name,v):
    x=str(name).upper()
    if x==v:return True
    if re.match(r"^"+v+r"(_[0-9]+)+($|_)",x):return True
    if re.match(r"^"+v+r"_(RAW|OBS|ORIG|SENSOR|MEAS)(_|$)",x):return True
    return False
def is_relevant_bif(row):
    # Exact metadata keyword matches only; raw strings are retained, not parsed
    # into corrections, measuring heights or verified instrument identities.
    a=(row.get("VARIABLE_GROUP") or "")+" "+(row.get("VARIABLE") or "")
    return bool(re.search(
      r"(^|[^A-Z0-9])(TA|VPD|RH|WS|WIND|METEO|AIR_TEMP|HUMID|TEMP|PRESS|HEIGHT|SENSOR|GAPFILL|UTC_OFFSET)([^A-Z0-9]|$)",
      a.upper()))
def decode(raw):
    for codec in ("utf-8-sig","cp1252","latin-1"):
        try:return raw.decode(codec),codec
        except UnicodeDecodeError:continue
    raise ValueError("Failed to decode original source BIF text")
def zip_csv_header(z,info):
    with z.open(info,"r") as f:
        buf=f.readline(1<<20)
    if not buf or len(buf)>=(1<<20) or b"\0" in buf:return [],"not_utf_csv_or_large_header"
    s,codec=decode(buf)
    return next(csv.reader([s.strip("\r\n")]),[]),codec
def exact_stamp(x):
    x=str(x or "").strip()
    if re.fullmatch(r"\d{12}",x):return x
    try:return dt.datetime.fromisoformat(x).strftime("%Y%m%d%H%M")
    except ValueError:return None
def scan_member(z,info,cols):
    # This is source *discovery*, not a blanket acceptance of another CSV.
    # Only exact, well-formed timestamps are matched; no time-offset guessing.
    target_col=next((c for c in cols if c in ("TIMESTAMP_START","TIMESTAMP","TIMESTAMP_END")),None)
    require(target_col is not None,"No source timestamp for scan")
    rawcols=[c for c in cols if
             any(is_raw(c,v) for v in ("TA","RH","VPD","WS","PA"))]
    if not rawcols:return [],0
    result=[];seen=0
    with z.open(info,"r") as f:
        stream=io.TextIOWrapper(f,encoding="utf-8-sig",newline="")
        rd=csv.DictReader(stream)
        require(rd.fieldnames and len(rd.fieldnames)==len(cols),
                "Source candidate headers changed")
        for row in rd:
            seen+=1
            tm=exact_stamp(row.get(target_col))
            if tm not in TGT_STRINGS:continue
            for name in rawcols:
                val=str(row.get(name) or "").strip()
                if not val or val in ("-9999","-9999.0","-9999.000"):continue
                result.append({"source_member":info.filename,
                   "member_SHA256":"PINNED_TO_FULL_SOURCE_ZIP",
                   "source_clock_is_NOT_assumed_verified":True,
                   "source_native_time":tm,
                   "candidate_variable":name.split("_")[0],
                   "candidate_raw_value":val,
                   "candidate_native_column":name,
                   "is_nonFLUXMET_separate_sensor_record":info.filename!=FLUXMET,
                   "scientific_repair_authorised":False})
    return result,seen
def netcdf_metadata(path):
    if not path.exists():return [],{"status":"OLD_L6_NOT_FOUND"}
    require(path.is_file() and not path.is_symlink(),"Old L6 symlink/unsafe")
    oldsha=sha(path)
    try:
        import netCDF4
    except ImportError:
        return [],{"status":"NETCDF4_PYTHON_UNAVAILABLE",
                   "old_L6_SHA256":oldsha}
    found=[]
    with netCDF4.Dataset(str(path),"r") as ds:
        def walk(group,pre=""):
            for name,v in group.variables.items():
                if re.search(r"TA|RH|VPD|WS|WIND|TEMP|PRESS|TIME|HUMID|GAP|QC",
                             name.upper()):
                    found.append({
                     "original_netCDF_path":str(path),"old_L6_SHA256":oldsha,
                     "variable_name":pre+name,
                     "dimensions":",".join(v.dimensions),
                     "shape":str(tuple(int(q) for q in v.shape)),
                     "dtype":str(v.dtype),
                     "units":str(getattr(v,"units",""))[:150],
                     "long_name":str(getattr(v,"long_name",""))[:180],
                     "standard_name":str(getattr(v,"standard_name",""))[:160],
                     "measurement_height":str(getattr(v,"height",""))[:100],
                     "calendar_or_time_units":str(getattr(v,"calendar",""))[:100] if "time" in name.lower() else "",
                     "source_lineage_verified":False})
            for sub,child in group.groups.items():walk(child,pre+sub+"/")
        walk(ds)
    return found,{"status":"OLD_L6_METADATA_READ_ONLY","old_L6_SHA256":oldsha,
                  "candidate_variables":len(found)}
def selftest():
    require(is_raw("TA","TA") and not is_raw("TA_F","TA")
           and not is_raw("TA_ERA","TA"),"Don't confuse TA_F with raw TA")
    require(is_raw("WS_1_1_1","WS") and is_raw("RH_RAW","RH"),"Source name detector")
    require(exact_stamp("2013-02-05 06:30:00")=="201302050630","Native local HH time")
    require(len(TARGETS)==7 and len(TGT_STRINGS)==7,"Seven unique source times")
    require(is_relevant_bif({"VARIABLE_GROUP":"UTC_OFFSET","VARIABLE":"UTC_OFFSET"}),
            "UTC BIF rows")
    print("AU-GIN STAGE12 SELFTEST PASS | source file and first-party TA/RH/WS identity; NO REPAIR")
def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--self-test",action="store_true")
    ap.add_argument("--out",type=Path)
    a=ap.parse_args()
    if a.self_test:return selftest()
    out=a.out
    require(out is not None and out.parent.resolve()==H.resolve()
            and not out.exists() and not out.is_symlink(),
            "Create NEW direct HOME report folder")
    require(sha(ZIP)==ZIP_SHA,"Original 127MB TERN source changed")
    r11=json.loads(SOURCE11.read_text(encoding="utf-8"))
    r10=json.loads(SOURCE10.read_text(encoding="utf-8"))
    require(r11.get("original_zip_SHA256")==ZIP_SHA
            and r11.get("priority_single_sample_spike_source_reviews")==5
            and r11.get("VPD_QC1_physics_conflicts")==2
            and r11.get("BIF_site_UTC_OFFSET")==8
            and r11.get("all_28_event_groups_remain_science_HOLD") is True
            and r11.get("AD400_authorised") is False,
            "Actual operator Stage11 science receipt changed")
    require(r10.get("original_TERN_zip_SHA256")==ZIP_SHA
            and r10.get("original_28_event_groups_reconstructed")==28
            and r10.get("original_44_flag_rows_reconstructed")==44
            and r10.get("priority_source_context_HH")==91
            and r10.get("AD400_authorised") is False,
            "Actual operator Stage10 science receipt changed")
    vpd11=tsvin(VPD11);spikes11=tsvin(SPIKE11);hold11=tsvin(HOLD11)
    require(len(vpd11)==2 and len(spikes11)==5 and len(hold11)==28,
            "Actual Stage11 5/2/28 source reports changed")
    info=[];bif=[];sourceRows=[];candidate_scanned=[];errors=[]
    with zipfile.ZipFile(ZIP,"r") as z:
        names=z.namelist()
        require(len(names)==len(set(names)),"Duplicate ZIP member names")
        require(names.count(FLUXMET)==1 and names.count(BIF)==1,
                "Actual original TERN flux data/BIF source names changed")
        metcols=[]
        for member in z.infolist():
            require(not member.filename.startswith("/") and
                    ".." not in Path(member.filename).parts,
                    "Untrusted path inside immutable source ZIP")
            if not member.filename.lower().endswith(".csv"):
                info.append({"zip_member":member.filename,
                    "uncompressed_size_bytes":member.file_size,
                    "compressed_size_bytes":member.compress_size,
                    "is_csv":False,"looks_like_hh_timestamped_data":False,
                    "timestamp_field":"","column_count":0,"raw_like_TA_columns":"",
                    "raw_like_RH_columns":"","raw_like_VPD_columns":"",
                    "raw_like_WS_columns":"","raw_like_PA_columns":"",
                    "has_TA_F":False,"has_VPD_F":False,
                    "header_preview":"","header_decoder":""})
                continue
            cols,codec=zip_csv_header(z,member)
            ishh=bool("TIMESTAMP_START" in cols or "TIMESTAMP" in cols)
            if member.filename==FLUXMET:metcols=cols
            info.append({
              "zip_member":member.filename,
              "uncompressed_size_bytes":member.file_size,
              "compressed_size_bytes":member.compress_size,
              "is_csv":True,"looks_like_hh_timestamped_data":ishh,
              "timestamp_field":"TIMESTAMP_START" if "TIMESTAMP_START" in cols else
                  "TIMESTAMP" if "TIMESTAMP" in cols else
                  "TIMESTAMP_END" if "TIMESTAMP_END" in cols else "",
              "column_count":len(cols),
              "raw_like_TA_columns":";".join(x for x in cols if is_raw(x,"TA")),
              "raw_like_RH_columns":";".join(x for x in cols if is_raw(x,"RH")),
              "raw_like_VPD_columns":";".join(x for x in cols if is_raw(x,"VPD")),
              "raw_like_WS_columns":";".join(x for x in cols if is_raw(x,"WS")),
              "raw_like_PA_columns":";".join(x for x in cols if is_raw(x,"PA")),
              "has_TA_F":"TA_F" in cols,"has_VPD_F":"VPD_F" in cols,
              "header_preview":";".join(cols[:15]),
              "header_decoder":codec})
            if member.filename==BIF or "BIFVARINFO_HH" in member.filename:
                raw=z.read(member)
                text,decoder=decode(raw)
                rd=csv.DictReader(io.StringIO(text,newline=""))
                for i,row in enumerate(rd):
                    if member.filename==BIF and
                       (row.get("SITE_ID") or "").strip()!="AU-Gin":
                        continue
                    if not is_relevant_bif(row):continue
                    bif.append({
                     "member":member.filename,
                     "original_member_SHA256":hashlib.sha256(raw).hexdigest(),
                     "decoder":decoder,"row_index":i+2,
                     "SITE_ID":row.get("SITE_ID",""),
                     "VARIABLE_GROUP":row.get("VARIABLE_GROUP",""),
                     "VARIABLE":row.get("VARIABLE",""),
                     "DATAVALUE":row.get("DATAVALUE",""),
                     "GROUP_ID":row.get("GROUP_ID",""),
                     "source_original_row_json":json.dumps(row,ensure_ascii=False)})
        require(len(metcols)==221 and "TA_F" in metcols
                and "VPD_F_QC" in metcols and "RH" in metcols,
                "Actual 221-column native FLUXMET_HH schema changed")
        require(hashlib.sha256(z.read(BIF)).hexdigest()==BIF_SHA,
                "Actual TERN BIF member changed")
        scan_candidates=[x for x in info if x["is_csv"] and
             x["looks_like_hh_timestamped_data"] and
             any(x["raw_like_"+v+"_columns"] for v in ("TA","RH","VPD","WS","PA")) and
             "ERA5" not in x["zip_member"].upper() and
             x["uncompressed_size_bytes"]<500_000_000]
        scan_candidates.sort(key=lambda r:(r["zip_member"]!=FLUXMET,
                                           -sum(bool(r["raw_like_"+v+"_columns"])
                                            for v in ("TA","RH","VPD","WS","PA"))))
        # Stream up to 4 original HH source candidates, source label exact match
        # only; these are PROVENANCE EVIDENCE and NOT independent validation.
        for c in scan_candidates[:4]:
            name=c["zip_member"]
            try:
                matched,seen=scan_member(z,z.getinfo(name),
                     next(csv.reader([z.open(name).readline().decode("utf-8-sig").strip("\r\n")])))
                sourceRows.extend(matched)
                candidate_scanned.append({"member":name,
                                          "original_native_source_rows_scanned":seen,
                                          "matched_native_source_values":len(matched)})
            except (ValueError,UnicodeError,csv.Error,KeyError) as e:
                errors.append({"member":name,"reason":str(e)[:200]})
    l6,status=netcdf_metadata(OLD_L6)
    require(len(info)>0 and len(bif)>0,"ZIP/header and BIF provenance inventory empty")
    originalTA=[r for r in info if r["raw_like_TA_columns"]]
    originalRH=[r for r in info if r["raw_like_RH_columns"]]
    report={
      "site":"AU-Gin",
      "stage":"Stage12 first-party source provenance for TA RH VPD PA WS",
      "original_TERN_zip_SHA256":ZIP_SHA,
      "Stage10_operator_receipt_SHA256":sha(SOURCE10),
      "Stage11_operator_receipt_SHA256":sha(SOURCE11),
      "original_BIF_member_SHA256":BIF_SHA,
      "FLUXMET_HH_column_count":len(metcols),
      "FLUXMET_HH_explicit_raw_like_TA_columns":
         [x for x in metcols if is_raw(x,"TA")],
      "FLUXMET_HH_explicit_raw_like_RH_columns":
         [x for x in metcols if is_raw(x,"RH")],
      "ZIP_all_member_count":len(info),
      "ZIP_members_with_raw_like_TA":len(originalTA),
      "ZIP_members_with_raw_like_RH":len(originalRH),
      "BIF_variable_provenance_rows":len(bif),
      "source_candidate_HH_members_scanned":candidate_scanned,
      "source_member_parse_errors_with_scope":errors,
      "older_L6_metadata_status":status,
      "older_L6_is_a_separate_not_interchangeable_processing_product":True,
      "no_RH_available_in_2013_Stage11_selected_center":True,
      "source_same_zip_data_NOT_independent_validation":True,
      "RH_raw_missing_in_selected_context_DOES_NOT_PROVE_no_other_RH_data":True,
      "2016_TA_raw_missing_in_Stage11_DOES_NOT_PROVE_no_TA_in_original_TERN_ZIP":True,
      "model_repair_authorised":False,
      "forcing_or_CIME_or_Slurm_modified":False,
      "AD400_authorised":False}
    out.mkdir(mode=0o700,exist_ok=False)
    tsvout(out/"stage12_AU_Gin_original_ZIP_CSV_schema_and_raw_channel_inventory.tsv",
           INV_COLS,info)
    tsvout(out/"stage12_AU_Gin_original_BIF_sensor_QC_height_provenance.tsv",
           BIF_COLS,bif)
    tsvout(out/"stage12_AU_Gin_other_original_native_HH_raw_channel_matches.tsv",
           CAND_COLS,sourceRows)
    tsvout(out/"stage12_AU_Gin_older_L6_channel_metadata_not_equivalent.tsv",
           L6_COLS,l6)
    (out/"stage12_AU_Gin_source_identity_TA_RH_VPD_2016_2013_science_HOLD.json").write_text(
         json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    print("STAGE12 ORIGINAL TERN ZIP & ACTUAL STAGE10/STAGE11 SHA256 VERIFIED")
    print("FLUXMET_HH_COLUMNS",len(metcols))
    print("FLUXMET_EXPLICIT_TA_RAW",report["FLUXMET_HH_explicit_raw_like_TA_columns"])
    print("FLUXMET_EXPLICIT_RH_RAW",report["FLUXMET_HH_explicit_raw_like_RH_columns"])
    print("ZIP_RAW_LIKE_TA_MEMBER_COUNT",len(originalTA),
          "RH_MEMBER_COUNT",len(originalRH),
          "BIF_RELEVANT_PROVENANCE_ROWS",len(bif))
    for x in candidate_scanned:
        print("SCANNED_FIRST_PARTY_MEMBER",x["member"],
              "ROWS",x["original_native_source_rows_scanned"],
              "SEVEN_FOCUS_MATCHED_VALUES",x["matched_native_source_values"])
    for x in sourceRows[:45]:
        print("NATIVE_RAW_FOCUS",x["source_native_time"],
              x["candidate_native_column"],x["candidate_raw_value"],
              "MEMBER",x["source_member"])
    for x in errors:
        print("SOURCE_MEMBER_PARSE_REVIEW_HOLD",x["member"],x["reason"])
    print("OLD_L6_SOURCE_METADATA",json.dumps(status,ensure_ascii=False))
    for x in l6[:35]:
        print("OLD_L6_CANDIDATE_HEADER",x["variable_name"],
              "SHAPE",x["shape"],"UNITS",x["units"],
              "LONG_NAME",x["long_name"][:80])
    print("STAGE12 READONLY FIRST-PARTY SOURCE REVIEW PASS; NO SCIENCE REPAIR/AD400")
    print("REPORT_DIR",out)
if __name__=="__main__":main()
