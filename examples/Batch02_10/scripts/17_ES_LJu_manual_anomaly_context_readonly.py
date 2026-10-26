#!/usr/bin/env python3
"""Stage17 ES-LJu manual anomaly context — READ ONLY. No changes to DATM, cases or Slurm.
Model CDEPS timestamps are noleap; raw FLUXMET source clock is NOT time-aligned.
Requires existing Stage16 report and original, unchanged IRIDIS datasets.
"""
from pathlib import Path
from datetime import datetime, timedelta, date
import calendar, json
import numpy as np
import pandas as pd
from netCDF4 import Dataset

ROOT = Path('/iridisfs/scratch/ly3n24/CLM_FATES/experiments/NonCompetitionObserved22/Batch02_10/stage16_ES_LJu_manual_review_v1_20261025')
m = json.loads((ROOT/'00_science_lineage_and_review_questions.json').read_text())
files = dict(zip(range(2004, 2025), m['DATM_annual_files']))
raw_path = m['original_fluxmet_hourly']['raw_path']

def model_date(year, index):
    d = datetime(year, 1, 1) + timedelta(minutes=30*index)
    if calendar.isleap(year) and index >= 59*48:
        d += timedelta(days=1)
    return d.strftime('%Y-%m-%d %H:%M')

def halfhour_index(dt):
    if dt.month == 2 and dt.day == 29:
        raise ValueError('No-leap calendar excludes February 29')
    day = (dt.date() - date(dt.year, 1, 1)).days
    if calendar.isleap(dt.year) and dt.month >= 3:
        day -= 1
    return day*48 + 2*dt.hour + dt.minute//30

def model_context(value, radius, label):
    dt = datetime.strptime(value, '%Y-%m-%d %H:%M')
    center = halfhour_index(dt)
    lo, hi = max(0, center-radius), min(17520, center+radius+1)
    with Dataset(files[dt.year]) as nc:
        arrays = {v: np.asarray(nc[v][lo:hi, 0, 0], dtype=float)
                  for v in ['TBOT', 'QBOT', 'PSRF', 'PRECTmms']}
    t = arrays['TBOT'] - 273.15
    q = arrays['QBOT']
    p = arrays['PSRF']
    e = q*p/(0.622+0.378*q)
    es = 611.2*np.exp(np.clip(17.67*t/(t+243.5), -20, 20))
    df = pd.DataFrame({
        'DATM_model_time': [model_date(dt.year, k) for k in range(lo, hi)],
        'TBOT_C': np.round(t, 3),
        'QBOT_kgkg': np.round(q, 7),
        'RH_approx_pct': np.round(100*e/es, 2),
        'rain_mm_30min': np.round(arrays['PRECTmms']*1800, 3)
    })
    df.insert(1, 'focus', ['***' if k == center else '' for k in range(lo, hi)])
    print('\n' + '='*86 + '\n' + label + ' | '+value+' (DATM noleap clock)')
    print(df.to_string(index=False))

print('STAGE16 SOURCE:', ROOT)
print('READ ONLY; DATM model time is noleap; raw FLUXMET timestamps are NOT independently aligned.')

print('\n\n### A. ALL TEMPERATURE JUMPS (model +/-3 hours)')
temp = pd.read_csv(ROOT/'05_all_temperature_jump_6h_context.csv')
flag = temp.loc[temp['jump_gt12_at_this_hh'].eq(1), ['model_time']].drop_duplicates()
last = None
for value in flag['model_time']:
    dt = datetime.strptime(value, '%Y-%m-%d %H:%M')
    if last and dt - last <= timedelta(minutes=30):
        last = dt
        continue
    model_context(value, 6, 'TEMPERATURE JUMP')
    last = dt

print('\n\n### B. ALL EXTREME RAINFALL (>40mm/30min; model +/-2 hours)')
rain = pd.read_csv(ROOT/'04_extreme_40mm30min_events_all_years.csv')
for value in rain['model_time'].drop_duplicates():
    model_context(value, 4, 'HEAVY RAIN')

print('\n\n### C. LOW RH: longest 3 + lowest 3 episodes (full episodes with context)')
h = pd.read_csv(ROOT/'07_RH_below5_contiguous_episodes.csv')
selected = pd.concat([
    h.nlargest(3,'duration_hours'),
    h.nsmallest(3,'min_approx_RH_pct')
]).drop_duplicates(subset=['year', 'start_model_time'])
for _, r in selected.iterrows():
    start = str(r['start_model_time'])
    dt1 = datetime.strptime(start, '%Y-%m-%d %H:%M')
    dt2 = datetime.strptime(str(r['end_model_time']), '%Y-%m-%d %H:%M')
    center = dt1 + (dt2-dt1)/2
    center -= timedelta(minutes=center.minute % 30, seconds=center.second)
    radius = max(7, int(r['n_halfhours']//2)+3)
    model_context(center.strftime('%Y-%m-%d %H:%M'), radius,
                  'LOW RH EPISODE '+start+' to '+str(r['end_model_time']))

print('\n\n### D. ORIGINAL FLUXMET (station SOURCE clock; NOT DATM-aligned)')
want = {'TIMESTAMP_START','TIMESTAMP_END','TA_F','TA_F_QC','VPD_F','VPD_F_QC','P_F','P_F_QC'}
raw = pd.read_csv(raw_path, usecols=lambda col: col in want, low_memory=False)
raw['source_time'] = pd.to_datetime(raw['TIMESTAMP_START'].astype(str), format='%Y%m%d%H%M', errors='raise')
raw = raw.sort_values('source_time').reset_index(drop=True)
for v in ['TA_F','VPD_F','P_F']:
    if v in raw:
        raw[v] = pd.to_numeric(raw[v], errors='coerce')

print('\nORIGINAL positive rainfall by source clock, 2005-2010')
wet = raw.loc[(raw['source_time'].dt.year.between(2005, 2010)) & (raw['P_F']>0)].copy()
wet['year'] = wet['source_time'].dt.year
wet['clock'] = wet['source_time'].dt.strftime('%H:%M')
print(wet.groupby(['year','clock'],as_index=False).agg(records=('P_F','size'),rain_mm=('P_F','sum')).to_string(index=False))

print('\nORIGINAL TA_F and QC near model jump nominal times (+/-3h); NOT 1:1 time join')
for value in flag['model_time']:
    dt = pd.Timestamp(value)
    look = raw.loc[raw['source_time'].between(dt-pd.Timedelta(hours=3), dt+pd.Timedelta(hours=3))]
    print('\nSOURCE CLOCK near model',value)
    print(look[[x for x in ('source_time','TA_F','TA_F_QC','VPD_F','VPD_F_QC','P_F','P_F_QC') if x in look]].to_string(index=False))

print('\nORIGINAL P_F + QC near model heavy-rain nominal times (+/-1.5h); NOT time-aligned')
for value in rain['model_time']:
    dt = pd.Timestamp(value)
    look = raw.loc[raw['source_time'].between(dt-pd.Timedelta(minutes=90), dt+pd.Timedelta(minutes=90))]
    print('\nSOURCE CLOCK near model', value)
    print(look[[x for x in ('source_time','P_F','P_F_QC','TA_F','TA_F_QC') if x in look]].to_string(index=False))

print('\nORIGINAL -40C-like TA_F sequences, 2023 Oct 16-20; before and after each episode')
mask_window = raw['source_time'].between('2023-10-16','2023-10-20 23:59:59')
negative = raw.loc[mask_window & raw['TA_F'].between(-41,-39)].copy()
if negative.empty:
    print('No TA_F near -40C in selected original source window')
else:
    negative['episode'] = (negative['source_time'].diff()!=pd.Timedelta(minutes=30)).cumsum()
    groups = negative.groupby('episode')
    episodes = sorted(((len(g),g.index.min(),g.index.max(),g['source_time'].iloc[0],g['source_time'].iloc[-1])
                       for _,g in groups), reverse=True)
    print('near_minus40_records', len(negative), 'episodes', len(episodes))
    for n, start, end, d1, d2 in episodes[:5]:
        print('\nRAW NEAR -40: count',n,'from',d1,'to',d2)
        subset = raw.iloc[max(0,start-4):min(len(raw),end+5)]
        if len(subset)>22:
            subset = pd.concat([subset.head(9),subset.tail(9)])
        print(subset[[x for x in ('source_time','TA_F','TA_F_QC','VPD_F','VPD_F_QC','P_F','P_F_QC') if x in subset]].to_string(index=False))

print('\nNO writes; FORCING, CASE and SLURM UNCHANGED. Human approval required.')
