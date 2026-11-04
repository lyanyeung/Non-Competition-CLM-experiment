#!/usr/bin/env python3
"""OzFlux AU-ASM Stage25: source-based NOAA GHCNh nearby hourly station discovery.

Read ONLY original official NOAA GHCNh station-list.csv and (optional) monthly
observation inventory; independently audit exact AU-ASM L6 SHA and actual
Stage24 UWA HTTP403 source-HOLD receipt. Report nearest stations and coverage
for 2013–2018 before choosing any independent NOAA event comparator.

This is STATION DISCOVERY ONLY, not a source-vs-tower fit or meteorological
repair. NOAA Alice Springs airport is ~180 km from the Pine Hill tower:
airport absence of a gust does not invalidate a local tower observation.
No GHCNh station ID is assumed, no stations are automatically approved.
No original forcing, DATM, Site-Soil, CIME, Slurm or AD400 changes.

NOAA GHCNh public references:
https://www.ncei.noaa.gov/products/global-historical-climatology-network-hourly
https://www.ncei.noaa.gov/oa/global-historical-climatology-network/hourly/doc/ghcnh-station-list.csv
https://www.ncei.noaa.gov/oa/global-historical-climatology-network/hourly/doc/ghcnh-inventory.txt
"""
from __future__ import annotations
import argparse,csv,hashlib,json,math,re,sys
from pathlib import Path
from collections import defaultdict
HOME=Path.home()
L6=Path("/iridisfs/scratch/ly3n24/CLM_FATES/sites/MY_EC_SITE/AU-ASM/forcing/raw/AliceSpringsMulga1_20100903T0000_to_20230308T0900_L6.nc")
L6_SHA="b9381c4ed0744d03ae609cfbf3805e30bbb9223851a05f4e5b63b149dd0b10eb"
PREV=HOME/"ozflux_nc_stage24_20261104T045052Z/stage24_UWA_AWS_2014_ps_raw_source_provenance_HOLD.json"
SITE=(-22.2828,133.2493,606.0)
YEAR_SET=(2013,2014,2015,2016,2017,2018)
NOAA_STATION_URL="https://www.ncei.noaa.gov/oa/global-historical-climatology-network/hourly/doc/ghcnh-station-list.csv"
NOAA_INV_URL="https://www.ncei.noaa.gov/oa/global-historical-climatology-network/hourly/doc/ghcnh-inventory.txt"
HEAD=("GHCN_ID","NAME","LATITUDE","LONGITUDE","ELEVATION_m","DISTANCE_km",
      "ELEVATION_minus_tower_m","WMO_ID","ICAO","STATION_LIST_SHA256",
      "INVENTORY_VERIFIED","OBS_2013","OBS_2014","OBS_2015",
      "OBS_2016","OBS_2017","OBS_2018",
      "OBS_2014_08","OBS_2014_11","OBS_2014_12",
      "OBS_2017_08","OBS_2017_09","OBS_2018_03","OBS_2018_06",
      "SCIENCE_STATUS")
def guard(test,message):
    if not test:raise RuntimeError(str(message))
def digest(p):
    p=Path(p)
    guard(p.is_file() and not p.is_symlink(),"File not accessible/nonregular "+str(p))
    h=hashlib.sha256()
    with p.open("rb") as f:
        for ch in iter(lambda:f.read(4<<20),b""):h.update(ch)
    return h.hexdigest()
def distance(a,b,c,d):
    p1,p2=math.radians(a),math.radians(c)
    delta=p2-p1
    x=math.sin(delta/2)**2+math.cos(p1)*math.cos(p2)*math.sin(
        math.radians(d-b)/2)**2
    return 2*6371.0*math.asin(math.sqrt(x))
def optional_float(x):
    try:
        v=float(x)
        return v if math.isfinite(v) else None
    except (ValueError,TypeError):return None
def first(src,*keys):
    for k in keys:
        if src.get(k) is not None and str(src.get(k)).strip():
            return str(src[k]).strip()
    return ""
def stations(path):
    rows=[]
    with path.open("r",encoding="utf-8-sig",newline="") as f:
        # Never let CSV parse a network error/HTML response as station rows.
        firstline=f.readline()
        guard("<html" not in firstline.lower() and "<!doctype" not in firstline.lower(),
              "NOAA station response is HTML, not a file")
        f.seek(0)
        r=csv.DictReader(f)
        guard(r.fieldnames is not None and
              {"LATITUDE","LONGITUDE"}.issubset({v.upper().strip()
                   for v in r.fieldnames}),"NOAA GHCNh CSV unexpected header")
        for raw in r:
            row={k.upper().strip():v for k,v in raw.items() if k is not None}
            station=first(row,"GHCN_ID","ID","STATION_ID")
            lat=optional_float(row.get("LATITUDE"))
            lon=optional_float(row.get("LONGITUDE"))
            if (not re.fullmatch("[A-Za-z0-9]{11}",station)
                or lat is None or lon is None or not(-90<=lat<=90)
                or not(-180<=lon<=180)):continue
            km=distance(SITE[0],SITE[1],lat,lon)
            if km>500:continue
            elev=optional_float(first(row,"ELEVATION","ELEVATION_M"))
            rows.append({"GHCN_ID":station,
                 "NAME":first(row,"NAME","STATION_NAME"),
                 "LATITUDE":lat,"LONGITUDE":lon,
                 "ELEVATION_m":elev,"DISTANCE_km":km,
                 "ELEVATION_minus_tower_m":elev-SITE[2] if elev is not None else None,
                 "WMO_ID":first(row,"WMO_ID","WMO"),
                 "ICAO":first(row,"ICAO")})
    rows.sort(key=lambda x:(x["DISTANCE_km"],x["GHCN_ID"]))
    guard(len(rows)>=1,"No NOAA GHCNh stations within 500 km of tower; no guessing")
    return rows
def inventory(path,selected):
    target=set(selected)
    years=defaultdict(lambda:defaultdict(lambda:[0]*12))
    valid=0
    with path.open(encoding="utf-8-sig") as f:
        for line in f:
            v=line.strip().split()
            if len(v)<14 or v[0] not in target:continue
            try:
                year=int(v[1])
                counts=[int(x) for x in v[2:14]]
            except ValueError:continue
            guard(year>1800 and all(x>=0 for x in counts),
                  "NOAA inventory negative/invalid monthly count")
            if year not in YEAR_SET:continue
            guard(year not in years[v[0]],
                  "Duplicate NOAA GHCNh station-year inventory "+v[0]+" "+str(year))
            years[v[0]][year]=counts
            valid+=1
    return years,valid
def selftest():
    guard(179<distance(-22.2828,133.2493,-23.7951,133.8890)<182,
          "Reference Alice Springs Airport ~180 km")
    guard(distance(-22.2828,133.2493,-22.2828,133.2493)<1e-8,
          "Haversine identity")
    guard(len(YEAR_SET)==6,"Study years")
    print("OZFLUX STAGE25 SELF-TEST PASS: NOAA station-distance and inventory metadata gates; READ ONLY")
def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--self-test",action="store_true")
    p.add_argument("--stations",type=Path)
    p.add_argument("--inventory",type=Path)
    p.add_argument("--out",type=Path)
    a=p.parse_args()
    if a.self_test:return selftest()
    guard(a.out is not None and a.out.parent.resolve()==HOME.resolve() and
          not a.out.exists() and not a.out.is_symlink(),
          "Output must be a new immediate HOME folder")
    guard(a.stations is not None and a.stations.is_file() and not
          a.stations.is_symlink(),"NOAA original station list required")
    l6hash=digest(L6)
    guard(l6hash==L6_SHA,"Immutable AU-ASM L6 source changed")
    receipt=json.loads(PREV.read_text(encoding="utf-8"))
    guard(receipt.get("AWS_access_status")=="not_provided" and
          receipt.get("science_release") is False and
          receipt.get("AD400_authorised") is False and
          receipt.get("L6_SHA256")==L6_SHA,
          "Actual Stage24 operator source access/HOLD changed")
    station_sha=digest(a.stations)
    allcandidates=stations(a.stations)
    inventory_counts={}
    inv_sha=None
    checked=0
    if a.inventory is not None:
        guard(a.inventory.is_file() and not a.inventory.is_symlink(),
              "NOAA inventory requested but missing")
        inv_sha=digest(a.inventory)
        inventory_counts,checked=inventory(a.inventory,
                                          [r["GHCN_ID"] for r in allcandidates])
        guard(checked>0,
              "Inventory parsed zero nearby station-years. Check NOAA format before proceeding.")
    out=[]
    for r in allcandidates:
        info=dict(r)
        info["STATION_LIST_SHA256"]=station_sha
        info["INVENTORY_VERIFIED"]=bool(inv_sha)
        for y in YEAR_SET:
            months=inventory_counts.get(r["GHCN_ID"],{}).get(y,[0]*12)
            info["OBS_"+str(y)]=sum(months) if inv_sha else None
        for y,m in ((2014,8),(2014,11),(2014,12),
                    (2017,8),(2017,9),(2018,3),(2018,6)):
            months=inventory_counts.get(r["GHCN_ID"],{}).get(y,[0]*12)
            info[f"OBS_{y}_{m:02d}"]=months[m-1] if inv_sha else None
        info["SCIENCE_STATUS"]="CANDIDATE_ONLY_NOAA_NOT_EVENT_VERIFIED"
        out.append(info)
    short=out[:30]
    report={"site":"AU-ASM","original_L6_SHA256":L6_SHA,
            "prior_stage24_UWA_access":"HTTP_403_NOT_PROVIDED",
            "NOAA_GHCNh_station_list_url":NOAA_STATION_URL,
            "NOAA_GHCNh_station_list_sha256":station_sha,
            "NOAA_GHCNh_inventory_url":NOAA_INV_URL,
            "NOAA_GHCNh_inventory_sha256":inv_sha,
            "NOAA_inventory_nearby_station_year_records_checked":checked,
            "tower_lat_lon_elev_m":SITE,
            "candidate_max_distance_km":500,
            "candidate_count_within_500km":len(allcandidates),
            "nearest_30":short,
            "2018_16p29613_wind_spike_independent_source_verified":False,
            "airport_distance_is_approximately_180km_and_cannot_disprove_local_wind":True,
            "GHCNh_does_not_supply_site_flux_tower_FLDS":True,
            "NOAA_station_observation_data_downloaded":False,
            "source_timezone_END_vs_CENTER_approved":False,
            "science_release":False,"AD400_authorised":False,
            "no_originals_DATM_Surface_CIME_Slurm_writes":True}
    a.out.mkdir(mode=0o700,parents=False)
    with (a.out/"stage25_NOAA_GHCNh_30_nearest_2013_2018_station_candidates.tsv").open(
             "x",encoding="utf-8",newline="") as f:
        w=csv.DictWriter(f,fieldnames=HEAD,delimiter="\t",extrasaction="raise")
        w.writeheader()
        w.writerows(short)
    (a.out/"stage25_NOAA_station_geography_and_yearly_coverage_HOLD.json").write_text(
          json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    print("NOAA VERIFIED STATION LIST SHA",station_sha)
    print("NOAA INVENTORY SOURCE SHA",inv_sha)
    print("STATIONS WITHIN 500 KM",len(allcandidates))
    for i,x in enumerate(short[:18],1):
        print("NOAA_NEAREST",i,x["GHCN_ID"],x["NAME"],
              "DIST_KM",round(x["DISTANCE_km"],2),
              "ELEV_DIFF_M",x["ELEVATION_minus_tower_m"],
              "WMO",x["WMO_ID"],"ICAO",x["ICAO"],
              "OBS_2014",x["OBS_2014"],"OBS_2017",x["OBS_2017"],
              "OBS_2018",x["OBS_2018"],
              "2018_MAR",x["OBS_2018_03"],"2018_JUN",x["OBS_2018_06"])
    print("STAGE25 NOAA NEAREST STATION PROVENANCE ONLY; NO DONOR/QC APPROVAL, NO AD400")
    print("REPORT_DIR",a.out)
if __name__=="__main__":main()
