#!/usr/bin/env python3
"""Batch04 source-locked UTC/NOLEAP DATM conversion and runtime inventory.

--inspect: source audit + exact BIF metadata + existing CIME/FATES inventory.
--build: same audit, then NEW annual files and manifests. No case/job writes.
--verify --manifest PATH: independently recompute all output fields from CSV.
Optional --height-config JSON supplies per-site zbot_m and height_evidence.
Without height evidence the seven physical forcing fields are built now,
with ZBOT deliberately absent; those files cannot yet drive a model case.

Direct protocol: AD400=80x5y, RESUBMIT=79, no AD5 approval/handoff. Five-year
segments are restart/archive intervals, not a separate scientific test.
Original CSV, PFT/soil files and existing cases remain read-only.
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4
import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = Path('/iridisfs/scratch/ly3n24/CLM_FATES')
EXP = ROOT/'experiments/NonCompetitionObserved22/AmeriFlux_Batch04_10'
UP = ROOT/'experiments/AmeriFlux_MultiSite_10_Batch04'
PFT_RECEIPT = EXP/('PFT_surface_candidate_research_ONLY/'
    'candidate_20261026T165944Z_ab70c90d/'
    'AMF_B04_PFT_SURFACES_BOTH_ARMS_RESEARCH_ONLY.json')
S05 = UP/'qcv5_stage05_candidates/candidate_20261024T103113Z/report.json'
S08 = UP/'qcv5_stage08_remaining_seven_candidates/candidate_20261024T120137Z/report.json'
N = 365*48
FIELDS = ('TA_F','VPD_F','PA_F','SW_IN_F','LW_IN_F','WS_F','P_F')
MAP = {'TBOT':'Sa_tbot','QBOT':'Sa_shum','PSRF':'Sa_pbot',
       'FSDS':'Faxa_swdn','FLDS':'Faxa_lwdn','WIND':'Sa_wind',
       'PRECTmms':'Faxa_precn','ZBOT':'Sa_z'}
UNITS = {'TBOT':'K','QBOT':'kg kg-1','PSRF':'Pa','FSDS':'W m-2',
         'FLDS':'W m-2','WIND':'m s-1','PRECTmms':'mm s-1',
         'RH':'percent','SHUM':'kg kg-1','ZBOT':'m'}
ROUND = {('US-Rpf','200802060700'),('US-Rpf','200802060900'),
         ('US-Syv','200803091300')}
PROTOCOL = {'AD_total_years':400,'AD_smoke_required':False,
            'STOP_OPTION':'nyears','STOP_N':5,'REST_OPTION':'nyears',
            'REST_N':5,'RESUBMIT':79,'RESUBMIT_SETS_CONTINUE_RUN':True,
            'DOUT_S':True,'spinup_state':2}


def need(ok, msg):
    if not ok:
        raise RuntimeError(str(msg))


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda:f.read(4<<20), b''):
            h.update(chunk)
    return h.hexdigest()


def readj(p):
    return json.loads(Path(p).read_text(encoding='utf-8'))


def writej(p, data):
    with Path(p).open('x', encoding='utf-8') as f:
        json.dump(data, f, indent=2, allow_nan=False)
        f.write('\n')


def loadpre():
    p = HERE/'01_audit_source_PFT_soil_surface_and_pair_plan.py'
    spec = importlib.util.spec_from_file_location('b04_sources', p)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def height_options(rows):
    """Do not conflate HEIGHTC or flux/sonic measurement height with TA_F."""
    groups = {}
    candidates = []
    for row in rows:
        key = (row.get('VARIABLE_GROUP',''), row.get('GROUP_ID',''))
        name = row['VARIABLE'].strip().upper()
        if name in ('VAR_INFO_VARNAME','VAR_INFO_HEIGHT','VAR_INFO_DATE'):
            grp = groups.setdefault(key, {})
            if name in grp and grp[name] != row['DATAVALUE']:
                grp['conflict'] = True
            grp[name] = row['DATAVALUE']
        if 'HEIGHT' in name or name == 'ZBOT':
            candidates.append({k:row.get(k,'') for k in
                ('VARIABLE','DATAVALUE','VARIABLE_GROUP','GROUP_ID')})
    sensors = []
    for key, grp in groups.items():
        name = grp.get('VAR_INFO_VARNAME','').upper()
        if any(name == n or name.startswith(n+'_') for n in ('TA','WS','WIND')):
            sensors.append({'group':list(key), **grp})
    return {'sensor_groups_not_automatically_selected':sensors,
            'other_height_rows_not_ZBOT':candidates,
            'TA_F_sensor_crosswalk_verified':False}


def metadata(site, spec, coords):
    original = Path(spec['paths']['native'])
    need(sha(original) == spec['source_provenance']['native']['sha256'],
         site+' original release CSV SHA changed')
    files = list(original.parent.glob('AMF_'+site+'_FLUXNET_BIF_*.csv'))
    need(len(files) == 1, site+' no unique original-release BIF')
    bif = files[0]
    with bif.open(encoding='utf-8-sig', newline='') as f:
        rows = list(csv.DictReader(f))
    need(rows and {'VARIABLE','DATAVALUE','GROUP_ID'} <= set(rows[0]),
         site+' unknown BIF schema')
    selected = {}
    for row in rows:
        need(row.get('SITE_ID',site).strip() in ('',site), 'Unrelated BIF site')
        key = row['VARIABLE'].strip().upper()
        if key not in ('UTC_OFFSET','LOCATION_LAT','LOCATION_LONG'):
            continue
        # US-Seg exact coordinate decision already approved in Stage02.
        if site == 'US-Seg' and key != 'UTC_OFFSET' and row['GROUP_ID'] != '1495':
            continue
        try:
            value = float(row['DATAVALUE'])
        except ValueError:
            continue
        if np.isfinite(value) and value != -9999:
            selected.setdefault(key, set()).add(value)
    need(all(len(selected.get(k,set())) == 1 for k in
         ('UTC_OFFSET','LOCATION_LAT','LOCATION_LONG')), site+' ambiguous clock/coordinates')
    vals = {k:next(iter(v)) for k,v in selected.items()}
    tz = vals['UTC_OFFSET']
    need(-12 <= tz <= 14 and float(tz*2).is_integer(), site+' unsupported UTC offset')
    need(abs(coords[0]-vals['LOCATION_LAT']) < 1e-4 and
         abs((coords[1]-vals['LOCATION_LONG']+180)%360-180) < 1e-4,
         site+' original BIF vs selected surface coordinates differ')
    if site == 'US-Seg':
        need(vals['LOCATION_LAT'] == 34.3623 and
             vals['LOCATION_LONG'] == -106.702 and tz == -7,
             'US-Seg approved group1495 changed')
    return {'UTC_OFFSET_hours':tz,'BIF_path':str(bif),'BIF_sha256':sha(bif),
            'BIF_coordinates':[vals['LOCATION_LAT'],vals['LOCATION_LONG']],
            **height_options(rows)}


def checked_inputs(pft_receipt=PFT_RECEIPT):
    pre = loadpre()
    sites, _, source_shas = pre.audit()
    shared = readj(pft_receipt)
    need(shared['n_sites'] == 10 and shared['n_planned_model_arms'] in (10,20),
         'Shared PFT receipt cohort differs')
    pfts = {r['site']:r for r in shared['site_surfaces']}
    need(len(shared['site_surfaces']) == len(pfts) == 10 and set(pfts) == set(pre.SITES),
         'Shared PFT receipt site duplication/mismatch')
    specs = readj(S05)['sites'] | readj(S08)['sites']
    need(set(specs) == set(pre.SITES), 'Stage05/08 original release roster differs')
    from netCDF4 import Dataset
    output = []
    for row in sites:
        site = row['site']
        surface = pfts[site]
        path = Path(surface['new_model_hypothesis_surface'])
        need(path.is_relative_to(Path(pft_receipt).parent/site) and
             sha(path) == surface['new_surface_SHA256'], site+' shared PFT SHA mismatch')
        need(surface.get('FULL_FATES_start_surface',str(path)) == str(path) ==
             surface['FIXED_NO_COMP_START_SURFACE'] and
             surface['source_surface_SHA256'] == row['source_surface_SHA256'] and
             surface['FATES_mapping_profile'] == row['FATES_mapping_profile'],
             site+' paired surface provenance drift')
        with Dataset(path) as nc, Dataset(row['source_surface_path']) as original:
            host = np.ma.filled(nc['PCT_NAT_PFT'][:],np.nan).ravel()
            want = np.array([row['science_host_PFT_slots'].get(i,0) for i in range(15)])
            need(np.allclose(host,want,atol=1e-5,rtol=0), site+' shared PFT values differ')
            for key in ('PCT_SAND','PCT_CLAY','ORGANIC'):
                need((key in nc.variables) == (key in original.variables), site+' soil schema differs')
                if key in nc.variables:
                    need(np.array_equal(np.ma.filled(nc[key][:],np.nan),
                         np.ma.filled(original[key][:],np.nan), equal_nan=True), site+' soil field changed '+key)
        row.update(shared_surface_path=str(path),shared_surface_sha256=surface['new_surface_SHA256'],
                   metadata=metadata(site,specs[site],row['model_tower_coordinates']))
        print('B04 INPUT PASS',site,'years',row['first_year'],row['last_year'],
              'UTC_OFFSET',row['metadata']['UTC_OFFSET_hours'],flush=True)
        output.append(row)
    return output, source_shas


def convert_values(site, stamps, raw):
    """Unit conversion only; no QC repair or source RH overwrite."""
    a = np.asarray(raw, dtype=float)
    need(a.ndim == 2 and a.shape[1] == len(FIELDS) and len(stamps) == len(a), 'Bad source shape')
    need(np.isfinite(a).all(), site+' missing/NaN forcing value')
    t,v,p,sw,lw,w,rain = a.T
    need(np.all((-55<=t)&(t<=55)&(v>=0)&(p>=65)&(p<=110)), site+' invalid T/VPD/P')
    # Conservative source Gate0 tolerated tiny negative SW/wind/rain. Do
    # not silently clip those here; such a source requires explicit review.
    need(np.all((sw>=0)&(sw<=1600)&(lw>=60)&(lw<=800)&(w>=0)&(w<=75)&(rain>=0)&(rain<=300)),
         site+' negative SW/wind/rain or invalid LW; no automatic clipping')
    es = 6.112*np.exp(17.67*t/(243.5+t))
    e = es-v
    records = []
    for i in np.flatnonzero(e<0):
        need((site,str(stamps[i])) in ROUND and -e[i] <= .0005,
             site+' unexpected VPD saturation violation '+str(stamps[i]))
        records.append({'timestamp_start':str(stamps[i]),
                        'vapour_pressure_rounding_hPa':float(e[i]),
                        'output_e_hPa':0.0,'source_unchanged':True})
    e = np.maximum(e,0)
    q = .622*e/(p*10-(1-.622)*e)
    need(np.isfinite(q).all() and np.all((q>=0)&(q<.08)), site+' invalid QBOT')
    values = {'TBOT':t+273.15,'PSRF':p*1000,'QBOT':q,
              'FSDS':sw,'FLDS':lw,'WIND':w,'PRECTmms':rain/1800,
              'RH':100*e/es,'SHUM':q.copy()}
    return values, records


def source_arrays(row):
    import pandas as pd
    path = Path(row['meteorology_path'])
    before = sha(path)
    need(before == row['meteorology_SHA256'], 'Met source SHA drift before read')
    table = pd.read_csv(path, usecols=['TIMESTAMP_START','TIMESTAMP_END',*FIELDS],
                        dtype={'TIMESTAMP_START':str,'TIMESTAMP_END':str})
    t = pd.to_datetime(table['TIMESTAMP_START'],format='%Y%m%d%H%M',errors='raise')
    end = pd.to_datetime(table['TIMESTAMP_END'],format='%Y%m%d%H%M',errors='raise')
    first, last = row['first_year'], row['last_year']
    expected = pd.date_range(f'{first}-01-01',f'{last+1}-01-01',freq='30min',inclusive='left')
    need(np.array_equal(t.to_numpy(), expected.to_numpy()) and
         np.all((end-t).dt.total_seconds() == 1800), row['site']+' native source chronology differs')
    keep = ~((t.dt.month == 2)&(t.dt.day == 29))
    stamps = table.loc[keep,'TIMESTAMP_START'].to_numpy()
    raw = table.loc[keep,list(FIELDS)].to_numpy(dtype=float)
    need(len(raw) == (last-first+1)*N, 'NOLEAP source count differs')
    values, rounding = convert_values(row['site'],stamps,raw)
    need(sha(path) == before, 'Source changed while reading')
    return values, rounding


def utc_values(values, offset_hours):
    """Exact NOLEAP half-hour permutation over the complete forcing cycle.

    LOCAL = UTC + offset. At UTC slot i, use source slot i+offset*2;
    modulo applies over all source years, not separately within each year.
    """
    slots = float(offset_hours)*2
    need(slots.is_integer(), 'UTC offset not half-hour aligned')
    return {k:np.roll(v,-int(slots)) for k,v in values.items()}


def height_for(site, config):
    if site not in config:
        return None
    row = config[site]
    z = float(row['zbot_m'])
    evidence = row.get('height_evidence','').strip()
    need(np.isfinite(z) and .5<=z<=150 and len(evidence)>10,
         site+' height needs a numeric sensor/proxy value and its provenance')
    need(row.get('height_kind') in ('VERIFIED_TA_F_SENSOR','DOCUMENTED_BASE_TA_SENSOR_PROXY'),
         site+' height must identify a TA sensor; canopy/WS substitutions are not allowed')
    if row['height_kind'] == 'DOCUMENTED_BASE_TA_SENSOR_PROXY':
        need(row.get('FLUXNET_TA_F_sensor_crosswalk_verified') is False and
             row.get('BASE_snapshot_sha256') ==
             '1c1e4171d295406a13d503f877b58661a651c88ffb6f0b6ec498f56bb1fcec5a',
             site+' documented BASE proxy must retain the source pin and uncertainty')
        source = row.get('source_rows',[])
        need(source and all(r['Site_ID'] == site and r['Variable'] == row['source_variable'] for r in source)
             and z in {float(r['Height']) for r in source}, site+' proxy lacks actual TA height evidence')
        for event in row.get('events',[]):
            need(any(r['Start_Date'] == event['local_start'][:8] and
                 float(r['Height']) == float(event['zbot_m']) for r in source),
                 site+' height event does not match BASE measurement-height source')
    return row


def append_height(row, values, height):
    """Height follows the source local calendar BEFORE the common UTC shift."""
    if height is None:
        return values
    import pandas as pd
    clock = pd.date_range(str(row['first_year'])+'-01-01',
                          str(row['last_year']+1)+'-01-01',freq='30min',inclusive='left')
    clock = clock[~((clock.month == 2)&(clock.day == 29))]
    z = np.full(len(clock),float(height['zbot_m']),dtype=float)
    previous = ''
    for event in height.get('events',[]):
        stamp = event['local_start']
        need(stamp > previous and len(stamp) == 12, 'Height events must be strictly chronological')
        date = pd.to_datetime(stamp,format='%Y%m%d%H%M',errors='raise')
        need(.5<=float(event['zbot_m'])<=150, 'Invalid dated sensor height')
        z[clock>=date] = float(event['zbot_m'])
        previous = stamp
    need(len(z) == len(values['TBOT']), 'Height and meteorology clocks differ')
    return {**values,'ZBOT':z}


def annual_write(path, year, coords, values, height, site, source_sha):
    from netCDF4 import Dataset
    need(not path.exists(), 'Cannot overwrite '+str(path))
    with Dataset(path,'w',format='NETCDF4_CLASSIC') as nc:
        for name,length in (('time',N),('lat',1),('lon',1)):
            nc.createDimension(name,length)
        time = nc.createVariable('time','f8',('time',))
        time[:] = (np.arange(N,dtype=float)+.5)/48
        time.units = f'days since {year}-01-01 00:00:00'
        time.calendar = 'noleap'
        time.long_name = 'UTC half-hour interval midpoint'
        for key,value,dim,unit in (('lat',coords[0],('lat',),'degrees_north'),
                                   ('lon',coords[1]%360,('lon',),'degrees_east'),
                                   ('LATIXY',coords[0],('lat','lon'),'degrees_north'),
                                   ('LONGXY',coords[1]%360,('lat','lon'),'degrees_east'),
                                   ('EDGEW',coords[1]%360-.05,('lat','lon'),'degrees_east'),
                                   ('EDGEE',coords[1]%360+.05,('lat','lon'),'degrees_east'),
                                   ('EDGES',coords[0]-.05,('lat','lon'),'degrees_north'),
                                   ('EDGEN',coords[0]+.05,('lat','lon'),'degrees_north')):
            v = nc.createVariable(key,'f8',dim)
            v[:] = value
            v.units = unit
        for key,arr in values.items():
            need(np.asarray(arr).shape == (N,), 'Wrong annual field length')
            v = nc.createVariable(key,'f8',('time','lat','lon'),zlib=True,complevel=2)
            v[:] = np.asarray(arr).reshape(N,1,1)
            v.units = UNITS[key]
        if height:
            need('ZBOT' in values,'Height must follow local calendar and common UTC permutation')
            v = nc['ZBOT']
            v.source_evidence = height['height_evidence']
            v.height_kind = height['height_kind']
        nc.site = site
        nc.original_source_SHA256 = source_sha
        nc.time_conversion = 'Remove Feb29; local interval START -> UTC MIDPOINT; whole-cycle wrap'
        nc.missing_ZBOT_is_not_model_ready = str(height is None)
        nc.soil_policy = 'See shared PFT surface; original grid layers retained, not station observations'


def annual_verify(path, year, coords, values, height):
    from netCDF4 import Dataset
    with Dataset(path) as nc:
        t = nc['time']
        need(t.calendar == 'noleap' and t.units == f'days since {year}-01-01 00:00:00'
             and np.array_equal(t[:],(np.arange(N)+.5)/48), 'Bad annual UTC time coordinate')
        for key,value in (('LATIXY',coords[0]),('LONGXY',coords[1]%360)):
            need(float(nc[key][:].ravel()[0]) == value, 'Wrong forcing point '+key)
        need(('ZBOT' in nc.variables) == bool(height), 'Unexpected/missing ZBOT')
        if height:
            need(nc['ZBOT'].height_kind == height['height_kind'] and
                 nc['ZBOT'].source_evidence == height['height_evidence'],'ZBOT source metadata differs')
        for key,want in values.items():
            need(key in nc.variables and nc[key].dimensions == ('time','lat','lon') and
                 nc[key].units == UNITS[key] and
                 np.array_equal(np.asarray(nc[key][:]).ravel(),want),
                 'NetCDF value/unit mismatch '+key+' '+str(path))


def build(rows, source_shas, height_cfg, output):
    need(not output.exists(), 'New output directory required')
    # Validate all supplied heights BEFORE allocating any forcing files.
    need(set(height_cfg) <= {r['site'] for r in rows}, 'Unknown height-config site')
    heights = {r['site']:height_for(r['site'],height_cfg) for r in rows}
    output.mkdir(parents=True, exist_ok=False)
    all_sites = []
    for row in rows:
        site = row['site']
        target = output/site/'yearly'
        target.mkdir(parents=True,exist_ok=False)
        values, rounding = source_arrays(row)
        height = heights[site]
        fields = utc_values(append_height(row,values,height),row['metadata']['UTC_OFFSET_hours'])
        files = []
        for i,year in enumerate(range(row['first_year'],row['last_year']+1)):
            chunk = {k:v[i*N:(i+1)*N] for k,v in fields.items()}
            path = target/f'{year}.nc'
            annual_write(path,year,row['model_tower_coordinates'],chunk,height,site,row['meteorology_SHA256'])
            annual_verify(path,year,row['model_tower_coordinates'],chunk,height)
            files.append({'year':year,'path':str(path),'sha256':sha(path)})
        record = {**row,'annual_files':files,'height':height,'rounding_events_output_only':rounding,
                  'eight_DATM_fields_present':height is not None,
                  'CIME_case_created':False,'Slurm_submitted':False}
        writej(output/site/'manifest.json',record)
        all_sites.append(record)
        print('B04 UTC DATM CREATED',site,'annual_files',len(files),'ZBOT',
              height or 'MISSING_DO_NOT_SUBMIT',flush=True)
    manifest = output/'B04_UTC_NOLEAP_DATM_MANIFEST.json'
    writej(manifest, {'stage':'B04_DATM_UTC_NOLEAP_DIRECT_AD400_INPUTS',
        'source_receipts':source_shas,'direct_AD400_protocol':PROTOCOL,'sites':all_sites,
        'annual_file_count':sum(len(x['annual_files']) for x in all_sites),
        'model_cases_created':False,'model_jobs_submitted':False})
    print('B04 DATM MANIFEST',manifest,flush=True)
    print('B04 DIRECT AD400 PLAN 80x5y RESUBMIT=79 | NO AD5 TEST/HANDOFF')
    return manifest


def verify(manifest):
    data = readj(manifest)
    need(data['stage'] == 'B04_DATM_UTC_NOLEAP_DIRECT_AD400_INPUTS' and
         data['direct_AD400_protocol'] == PROTOCOL,'Wrong conversion/protocol receipt')
    rows = data['sites']
    need(len(rows) == 10 and {r['site'] for r in rows} == set(loadpre().SITES), 'Wrong manifest cohort')
    count = 0
    for row in rows:
        values, rounding = source_arrays(row)
        need(rounding == row['rounding_events_output_only'], 'VPD-rounding receipt differs')
        expected = utc_values(append_height(row,values,row['height']),row['metadata']['UTC_OFFSET_hours'])
        need(sha(row['metadata']['BIF_path']) == row['metadata']['BIF_sha256'], 'BIF source drift')
        need(sha(row['shared_surface_path']) == row['shared_surface_sha256'], 'Shared PFT surface drift')
        years = list(range(row['first_year'],row['last_year']+1))
        need([f['year'] for f in row['annual_files']] == years, 'Annual year inventory differs')
        for i,entry in enumerate(row['annual_files']):
            need(sha(entry['path']) == entry['sha256'], 'Annual SHA differs')
            annual_verify(entry['path'],entry['year'],row['model_tower_coordinates'],
                          {k:v[i*N:(i+1)*N] for k,v in expected.items()},row['height'])
            count += 1
        print('B04 FULL SOURCE->UTC->NETCDF VERIFY PASS',row['site'],flush=True)
    need(count == data['annual_file_count'], 'Total annual count differs')
    print('B04 ALL ANNUAL SOURCE/EVERY FIELD/TIMESTEP VERIFIED',count)


def runtime_inventory():
    import subprocess
    parameter = ROOT/'CTSM/src/fates/parameter_files/fates_params_default.json'
    if parameter.is_file():
        data = readj(parameter)['parameters']
        print('B04 INSTALLED FATES PARAM',parameter,'SHA256',sha(parameter),flush=True)
        for key in ('fates_pftname','fates_hlm_pft_map','fates_recruit_init_density',
                    'fates_recruit_init_seed','fates_recruit_prescribed_rate'):
            if key in data:
                print('B04 FATES PARAMETER',key,json.dumps(data[key].get('data')),flush=True)
    for root in (ROOT/'CTSM/src/fates',ROOT/'CTSM/src'):
        # Bounded tracked source search, only identifiers that affect paired
        # initial composition. No traversal of scratch/model outputs.
        try:
            p = subprocess.run(['rg','-n','-m','3','-g','*.F90',
                'use_fates_fixed_biogeog|fates_initdenc|fates_hlm_pft_map',str(root)],
                text=True,capture_output=True,timeout=40)
            print('B04 INITIALIZATION SOURCE EVIDENCE',str(root),p.stdout[:16000],flush=True)
        except (OSError,subprocess.TimeoutExpired) as e:
            print('B04 INITIALIZATION SEARCH UNAVAILABLE',str(e),flush=True)
    casedir = ROOT/'cases'
    for site in loadpre().SITES:
        existing = sorted(casedir.glob(site+'_*AMF*B04*'))[:8]
        print('B04 EXISTING CASE INVENTORY',site,[str(p) for p in existing],flush=True)
    # Reference only: never infer Batch04 soil/PFT/coords from this other site.
    ref = ROOT/'cases/CA-Ca3_AMF_FIXNC_AD400_UTC_V2_PTS_AD5'
    if (ref/'xmlquery').is_file():
        for key in ('EXEROOT','BUILD_COMPLETE','CLM_BLDNML_OPTS','CALENDAR','DATM_MODE','MPI_RUN_COMMAND'):
            p = subprocess.run([str(ref/'xmlquery'),key,'--value'],cwd=ref,text=True,
                               capture_output=True,timeout=40)
            print('B04 BATCH01 BUILD REFERENCE',key,p.returncode,p.stdout.strip(),flush=True)
    print('B04 INVENTORY NO CIME/SLURM MODIFICATIONS',flush=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    mode = ap.add_mutually_exclusive_group(required=True)
    for name in ('self-test','inspect','build','verify'):
        mode.add_argument('--'+name,action='store_true')
    ap.add_argument('--outdir',type=Path)
    ap.add_argument('--manifest',type=Path)
    ap.add_argument('--pft-receipt',type=Path,default=PFT_RECEIPT)
    ap.add_argument('--height-config',type=Path)
    a = ap.parse_args()
    if a.self_test:
        vector = {'TEST':np.arange(2*N)}
        shifted = utc_values(vector,-7)['TEST']
        need(shifted[0] == 2*N-14 and shifted[N] == N-14, 'UTC boundary shift failed')
        need(np.array_equal(np.sort(shifted),vector['TEST']), 'UTC permutation lost slots')
        need(PROTOCOL['STOP_N']*(PROTOCOL['RESUBMIT']+1) == 400 and
             not PROTOCOL['AD_smoke_required'], 'Not direct AD400')
        print('B04 DIRECT400/UTC MATH SELF-TEST PASS; NO HPC ACCESS')
        return
    if a.verify:
        need(a.manifest is not None,'--verify requires --manifest')
        verify(a.manifest)
        return
    rows, shas = checked_inputs(a.pft_receipt)
    for row in rows:
        print('B04 EXACT SITE METADATA',row['site'],json.dumps(row['metadata']),flush=True)
    runtime_inventory()
    if a.inspect:
        print('B04 INSPECT COMPLETE: NO WRITES; AD5 NOT REQUIRED')
        return
    folder = a.outdir or EXP/('DATM_UTC_NOLEAP_direct400/candidate_'+
                  datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'_'+uuid4().hex[:8])
    build(rows,shas,readj(a.height_config) if a.height_config else {},folder)


if __name__ == '__main__':
    main()
