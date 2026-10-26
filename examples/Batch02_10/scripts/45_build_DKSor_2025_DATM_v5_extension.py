#!/usr/bin/env python3
"""Batch02 Stage45: add forcing year 2025 to the DK-Sor v5 DATM record (1996-2024 -> 1996-2025).

Source: sites/MY_EC_SITE/DK-Sor/forcing/merged_multisource_v1/DK-Sor_multisource_HH_1996_2025_candidate.csv
(ICOS FLUXNET 1996-2024 + ICOSETC, yearly met coverage 1.0 for 1996-2025).
Conversion: exactly the FLUXNET_MultiSite_6 v5 rule (03_prepare_six_site_forcing_v5.py):
  TBOT = TA_F + 273.15; es = 6.112 exp(17.67 TA/(TA+243.5)) hPa; ea = (es - VPD_F)*100 Pa;
  PSRF = PA_F*1000; QBOT = 0.622 ea/(PSRF - 0.378 ea); FSDS = max(SW_IN_F,0); FLDS = LW_IN_F;
  WIND = max(WS_F,0); PRECTmms = max(P_F,0)/1800.
ZBOT: the 2024 file's height (BIF history 43 m since 2021-02-06), must be constant through 2024.
The 2025 NetCDF copies the exact layout/attributes of DK-Sor_DATM_2024.nc and only replaces values.

Gates (all read only in `check`):
  1. merged CSV header has the seven FLUXNET variables; 2025 has 17520 half-hours (no 29 Feb)
  2. REGRESSION: merged 2024 converted with the same rule reproduces DK-Sor_DATM_2024.nc
     (>=99% of records within tolerance per variable; v5 QC replacements explain the rest)
  3. 2025 sanity ranges (v5) and QBOT <= saturation; no missing values
  4. 2025 vs FLUXNET ERA5_HH (1981-2025) for TA/SW/LW/PA/WS: bias/RMSE/correlation printed
`build --confirm BUILD_DKSOR_2025_DATM_AND_1996_2025_FOLDER` writes
  experiments/.../Batch02_10/stage45_DKSor_DATM_1996_2025/ : 29 symlinks to the unchanged
  1996-2024 files + new DK-Sor_DATM_2025.nc + manifest.json. Original files are never modified.
"""
import argparse, hashlib, json, os, shutil, sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

SITE = Path('/iridisfs/scratch/ly3n24/CLM_FATES/sites/MY_EC_SITE/DK-Sor/forcing')
MERGED = SITE / 'merged_multisource_v1/DK-Sor_multisource_HH_1996_2025_candidate.csv'
V5 = SITE / 'datm_v5_candidate_timevarying_zbot'
ERA_GLOB = ('raw_multisource_v1/ICOS/ICOS_DK-Sor_FLUXNET_ERA5_HH_1981-2025_v1.3_r1.csv',
            'raw/ICOS_DK-Sor_FLUXNET_1996-2024_v1.3_r1/ICOS_DK-Sor_FLUXNET_ERA5_HH_1981-2025_v1.3_r1.csv')
OUT = Path('/iridisfs/scratch/ly3n24/CLM_FATES/experiments/NonCompetitionObserved22/Batch02_10/stage45_DKSor_DATM_1996_2025')
ACK = 'BUILD_DKSOR_2025_DATM_AND_1996_2025_FOLDER'
FLX = ('TA_F', 'VPD_F', 'PA_F', 'SW_IN_F', 'LW_IN_F', 'WS_F', 'P_F')
RANGES = {'TBOT': (180, 340), 'QBOT': (0, 0.08), 'PSRF': (49000, 111000), 'FSDS': (0, 1600),
          'FLDS': (0, 800), 'WIND': (0, 75), 'PRECTmms': (0, 300 / 1800)}
TOL = {'TBOT': 0.011, 'QBOT': 2e-5, 'PSRF': 11.0, 'FSDS': 0.11, 'FLDS': 0.11, 'WIND': 0.011, 'PRECTmms': 1e-6}
ERA_PAIRS = (('TA_F', 'TA_ERA'), ('SW_IN_F', 'SW_IN_ERA'), ('LW_IN_F', 'LW_IN_ERA'), ('PA_F', 'PA_ERA'), ('WS_F', 'WS_ERA'))


def need(ok, why):
    if not ok: raise RuntimeError(str(why))


def sha(p):
    h = hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''): h.update(b)
    return h.hexdigest()


def convert(df):
    ta = df['TA_F'].to_numpy(float)
    es = 6.112 * np.exp(17.67 * ta / (ta + 243.5))
    ea = (es - df['VPD_F'].to_numpy(float)) * 100
    psrf = df['PA_F'].to_numpy(float) * 1000
    return {'TBOT': ta + 273.15, 'QBOT': 0.622 * ea / (psrf - 0.378 * ea), 'PSRF': psrf,
            'FSDS': np.clip(df['SW_IN_F'].to_numpy(float), 0, None), 'FLDS': df['LW_IN_F'].to_numpy(float),
            'WIND': np.clip(df['WS_F'].to_numpy(float), 0, None), 'PRECTmms': np.clip(df['P_F'].to_numpy(float), 0, None) / 1800}


def noleap_index(year):
    import pandas as pd
    t = pd.date_range(f'{year}-01-01 00:00', f'{year}-12-31 23:30', freq='30min')
    return t[~((t.month == 2) & (t.day == 29))]


def load_merged():
    import pandas as pd
    need(MERGED.is_file(), f'missing {MERGED}')
    head = pd.read_csv(MERGED, nrows=0).columns.tolist()
    tcol = head[0]
    miss = [c for c in FLX if c not in head]
    need(not miss, f'merged CSV lacks {miss}; header = {head}')
    df = pd.read_csv(MERGED, usecols=[tcol, *FLX], low_memory=False)
    df[tcol] = pd.to_datetime(df[tcol], errors='raise')
    df = df.rename(columns={tcol: 'time'})
    for c in FLX: df[c] = pd.to_numeric(df[c], errors='coerce')
    return df, head


def year_frame(df, year):
    sub = df[df.time.dt.year == year].copy()
    sub = sub[~((sub.time.dt.month == 2) & (sub.time.dt.day == 29))]
    exp = noleap_index(year)
    need(len(sub) == len(exp) and np.array_equal(sub.time.to_numpy(), exp.to_numpy()), f'{year}: {len(sub)} rows, chronology != {len(exp)} noleap half-hours')
    return sub.reset_index(drop=True)


def nc_read(path):
    from netCDF4 import Dataset
    with Dataset(str(path)) as ds:
        out = {k: np.asarray(ds.variables[k][:], dtype=float).ravel() for k in ds.variables
               if ds.variables[k].dimensions and ds.variables[k].dimensions[0] == 'time'}
    return out


def check(verbose=True):
    import pandas as pd
    df, head = load_merged()
    print('MERGED', MERGED, 'rows', len(df), 'first', df.time.iloc[0], 'last', df.time.iloc[-1])
    f24 = V5 / 'DK-Sor_DATM_2024.nc'; need(f24.is_file(), f'missing {f24}')
    ref = nc_read(f24)
    tvars = sorted(ref)
    known = set(RANGES) | {'ZBOT', 'time'}
    extra = [v for v in tvars if v not in known]
    need(not extra, f'2024 DATM file has time variables this tool does not rebuild: {extra}')
    z = ref['ZBOT']; need(np.allclose(z, z[0]), f'ZBOT not constant in 2024: {np.unique(z)[:5]}')
    zbot = float(z[0]); print(f'ZBOT 2024 constant {zbot} m -> used for 2025')
    # 2. regression on 2024
    c24 = convert(year_frame(df, 2024))
    print('REGRESSION merged-2024 (v5 rule) vs DK-Sor_DATM_2024.nc:')
    for v in RANGES:
        d = np.abs(c24[v] - ref[v]); ok = d <= TOL[v]
        frac = float(ok.mean())
        print(f'  {v:9} within_tol={frac*100:7.3f}%  max_abs_diff={np.nanmax(d):.4g}  n_outside={int((~ok).sum())}')
        need(frac >= 0.99, f'REGRESSION HOLD {v}: only {frac*100:.2f}% of 2024 records reproduce the v5 file')
    # 3. 2025 sanity
    y = year_frame(df, 2025)
    nan = {c: int(y[c].isna().sum()) for c in FLX}
    need(not any(nan.values()), f'2025 missing values {nan}')
    c25 = convert(y)
    for v, (lo, hi) in RANGES.items():
        a = c25[v]; bad = ~np.isfinite(a) | (a < lo) | (a > hi)
        need(not bad.any(), f'2025 {v}: {int(bad.sum())} values outside {lo}-{hi}, rows {np.flatnonzero(bad)[:5]}')
    t = c25['TBOT'] - 273.15; es = 6.112 * np.exp(17.67 * t / (t + 243.5)) * 100
    qsat = 0.622 * es / (c25['PSRF'] - 0.378 * es)
    need(np.all(c25['QBOT'] <= qsat * 1.001), '2025 QBOT above saturation')
    print('2025 SANITY PASS: 17520 half-hours, no missing values, v5 ranges, QBOT <= saturation')
    print('2025 annual means:', {v: round(float(c25[v].mean()), 4) for v in ('TBOT', 'FSDS', 'FLDS', 'WIND', 'PSRF')},
          'P mm/yr', round(float(c25['PRECTmms'].sum() * 1800), 1))
    m24 = {v: float(ref[v].mean()) for v in ('TBOT', 'FSDS')}
    print('2024 annual means (v5 file):', {k: round(x, 4) for k, x in m24.items()}, 'P mm/yr', round(float(ref['PRECTmms'].sum() * 1800), 1))
    # 4. ERA5 comparison
    era = next((SITE / g for g in ERA_GLOB if (SITE / g).is_file()), None)
    if era is None:
        print('ERA5 HH file not found; comparison skipped')
    else:
        e = pd.read_csv(era, usecols=lambda c: c in ('TIMESTAMP_START',) + tuple(x[1] for x in ERA_PAIRS), low_memory=False)
        e['time'] = pd.to_datetime(e.TIMESTAMP_START.astype(str), format='%Y%m%d%H%M')
        m = y.merge(e, on='time', how='left')
        print('2025 vs FLUXNET ERA5_HH', era.name)
        for a, b in ERA_PAIRS:
            if b not in m: continue
            x, r = m[a].to_numpy(float), pd.to_numeric(m[b], errors='coerce').to_numpy(float)
            ok = np.isfinite(x) & np.isfinite(r) & (r > -9000)
            if ok.sum() < 100: print(f'  {a:8} vs {b}: too few ERA values'); continue
            d = x[ok] - r[ok]
            print(f'  {a:8} vs {b:10} n={int(ok.sum()):5} bias={d.mean():8.3f} rmse={np.sqrt((d**2).mean()):8.3f} r={np.corrcoef(x[ok], r[ok])[0,1]:.3f}')
    return c25, zbot, f24


def build():
    from netCDF4 import Dataset
    c25, zbot, f24 = check()
    need(not OUT.exists(), f'{OUT} exists; inspect it (it is never overwritten)')
    tmp = OUT.with_name(OUT.name + '.partial'); shutil.rmtree(tmp, ignore_errors=True); tmp.mkdir(parents=True)
    src = sorted(V5.glob('DK-Sor_DATM_*.nc'))
    years = [int(p.stem.split('_')[-1]) for p in src]
    need(years == list(range(1996, 2025)), f'v5 folder years {years[:2]}..{years[-2:]}')
    for p in src: os.symlink(p, tmp / p.name)
    new = tmp / 'DK-Sor_DATM_2025.nc'
    shutil.copyfile(f24, new)
    with Dataset(str(new), 'r+') as ds:
        t = ds.variables['time']
        need('2024' in t.units, f'unexpected time units {t.units}')
        t.units = t.units.replace('2024', '2025')
        for v, a in c25.items():
            ds.variables[v][:] = a.reshape(ds.variables[v].shape)
        ds.variables['ZBOT'][:] = np.full(ds.variables['ZBOT'].shape, zbot)
        ds.setncattr('stage45_source', f'{MERGED.name} year 2025 (ICOSETC/ICOS merged), FLUXNET_MultiSite_6 v5 conversion; layout copied from {f24.name}')
    with Dataset(str(new)) as ds:  # readback in the file's own storage type (v5 files are float32)
        for v, a in c25.items():
            var = ds.variables[v]
            got = np.ma.filled(np.ma.asarray(var[:]), np.nan).ravel().astype(var.dtype)
            need(np.array_equal(got, a.astype(var.dtype)), f'readback {v} (dtype {var.dtype})')
        need(np.all(np.asarray(ds.variables['ZBOT'][:]).ravel() == np.asarray(zbot, dtype=ds.variables['ZBOT'].dtype)), 'readback ZBOT')
        tu = ds.variables['time'].units
    need(tu.startswith('days since 2025-01-01'), f'time units {tu}')
    files = sorted(tmp.glob('DK-Sor_DATM_*.nc'))
    man = {'site': 'DK-Sor', 'years': [1996, 2025], 'n_files': len(files), 'zbot_2025_m': zbot,
           'source_csv': str(MERGED), 'source_csv_sha256': sha(MERGED), 'template_2024': str(f24),
           'template_2024_sha256': sha(f24), 'new_2025_sha256': sha(new),
           'links_1996_2024_to': str(V5), 'created_utc': datetime.now(timezone.utc).isoformat()}
    (tmp / 'manifest.json').write_text(json.dumps(man, indent=2) + '\n')
    tmp.rename(OUT)
    print(f'STAGE45 BUILD PASS -> {OUT} ({len(files)} files 1996-2025; 2025 new, 1996-2024 symlinked unchanged)')


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('action', choices=('self-test', 'check', 'build'))
    ap.add_argument('--confirm', default='')
    a = ap.parse_args()
    if a.action == 'self-test':
        import pandas as pd
        d = pd.DataFrame({'TA_F': [0.0, 20.0], 'VPD_F': [0.0, 10.0], 'PA_F': [100.0, 101.3], 'SW_IN_F': [-1.0, 500.0],
                          'LW_IN_F': [300.0, 350.0], 'WS_F': [-0.1, 3.0], 'P_F': [0.0, 1.8]})
        c = convert(d)
        assert abs(c['TBOT'][1] - 293.15) < 1e-9 and c['FSDS'][0] == 0 and c['WIND'][0] == 0 and abs(c['PRECTmms'][1] - 0.001) < 1e-12
        assert abs(c['QBOT'][0] - 0.622 * 611.2 / (100000 - 0.378 * 611.2)) < 1e-12
        assert len(noleap_index(2024)) == 17520 and len(noleap_index(2025)) == 17520
        print('STAGE45 SELF-TEST PASS (no files)')
    elif a.action == 'check':
        check()
    else:
        need(a.confirm == ACK, 'requires --confirm ' + ACK)
        build()
