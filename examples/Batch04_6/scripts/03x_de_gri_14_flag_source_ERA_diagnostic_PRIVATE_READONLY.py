#!/usr/bin/env python3
"""DE-Gri exact 14 legacy flags source-vs-selected context, no model/input writes.

The output is a PRIVATE diagnostic. QC0/1/2 and ERA differences are not
proof of meteorological validity, and edited time labels are not science release.
"""
import argparse
import csv
import hashlib
import json
import math
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path

C_STAGE = 'STAGE03C_BATCH04_REUSE_HISTORICAL_SCIENCE_HOLDS_AND_AMERIFLUX_DELTA_SCOPE'
D_STAGE = 'STAGE03D_BATCH04_RECOVER_OLD_RAIN_AND_TARGETED_ORIGINAL_SOURCE_CONTEXT'
B_STAGE = 'STAGE03B_BATCH04_REUSE_FLUXNET13_STAGE28_STAGE29B_30_SOURCE_LINEAGE'
SRC_FIELDS = ('TA_F','TA_F_QC','TA_ERA','VPD_F','VPD_F_QC','VPD_ERA','PA_F','P_F','P_F_QC')
SEL_FIELDS = ('TA_USE','VPD_USE','TBOT','QBOT','PSRF','PRECTmms')

def tparse(s, source):
    s=str(s).strip().strip('\'"')
    if source and s.endswith('.0') and s[:-2].isdigit():s=s[:-2]
    try: t=datetime.strptime(s,'%Y%m%d%H%M') if source else datetime.fromisoformat(s)
    except ValueError: return None
    return t if t.tzinfo is None else None

def num(v):
    try:
        x=float(v)
        return x if math.isfinite(x) and x!=-9999 else None
    except (ValueError,TypeError):return None

def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(1048576),b''):h.update(b)
    return h.hexdigest()

def scan(path, source, centers):
    stamps={c+timedelta(minutes=30*i) for c in centers for i in range(-2,3)}
    key='TIMESTAMP_START' if source else 'time'
    needed=SRC_FIELDS if source else SEL_FIELDS
    out={}
    with path.open('r',newline='',encoding='utf-8-sig') as f:
        reader=csv.DictReader(f)
        if not set((key,)+needed).issubset(reader.fieldnames or []):
            raise ValueError('Missing source/selected columns '+str(set((key,)+needed)-set(reader.fieldnames or [])))
        for row in reader:
            t=tparse(row[key],source)
            if t is None:raise ValueError('Invalid source time '+str(row[key]))
            if t in stamps:
                if t in out:raise ValueError('Duplicate time '+str(t))
                out[t]={k:num(row.get(k)) for k in needed}
    return out

def rh(t,v):
    if t is None or v is None or t<=-80 or t>=70:return None
    sat=6.112*math.exp(17.67*t/(t+243.5))
    return 100*(1-v/sat) if sat>0 else None

def calc(src,sel,center):
    a=src.get(center)
    b=sel.get(center)
    if a is None or b is None:return {'source_present':bool(a),'forcing_present':bool(b),'scope':'MISSING'}
    prev=sel.get(center-timedelta(minutes=30))
    nex=sel.get(center+timedelta(minutes=30))
    dv=lambda f,x:round(f[x]-b[x],3) if f and f.get(x) is not None and b.get(x) is not None else None
    rhval=rh(b.get('TA_USE'),b.get('VPD_USE'))
    eq=lambda f,x,y: f.get(x) is not None and b.get(y) is not None and abs(f[x]-b[y])<1e-5
    rain=b.get('PRECTmms')*1800 if b.get('PRECTmms') is not None else None
    return {'source_present':True,'forcing_present':True,
       'source_T_QC':a.get('TA_F_QC'),'source_VPD_QC':a.get('VPD_F_QC'),
       'source_T_C':a.get('TA_F'),'forcing_T_C':b.get('TA_USE'),'source_TA_ERA_C':a.get('TA_ERA'),
       'forcing_T_minus_source_C':round(b['TA_USE']-a['TA_F'],4) if a.get('TA_F') is not None and b.get('TA_USE') is not None else None,
       'source_VPD_hPa':a.get('VPD_F'),'forcing_VPD_hPa':b.get('VPD_USE'),'source_VPD_ERA_hPa':a.get('VPD_ERA'),
       'forcing_VPD_minus_source_hPa':round(b['VPD_USE']-a['VPD_F'],4) if a.get('VPD_F') is not None and b.get('VPD_USE') is not None else None,
       'forcing_RH_water_pct':round(rhval,3) if rhval is not None else None,
       'forcing_rain_mm_per_HH':round(rain,3) if rain is not None else None,
       'source_P_QC':a.get('P_F_QC'),'source_P_mm':a.get('P_F'),
       'T_step_before_C':-dv(prev,'TA_USE') if dv(prev,'TA_USE') is not None else None,
       'T_step_after_C':dv(nex,'TA_USE'),
       'T_source_equals_selected':eq(a,'TA_F','TA_USE'),
       'VPD_source_equals_selected':eq(a,'VPD_F','VPD_USE'),
       'ERA_T_difference_C':round(b['TA_USE']-a['TA_ERA'],3) if b.get('TA_USE') is not None and a.get('TA_ERA') is not None else None,
       'ERA_VPD_difference_hPa':round(b['VPD_USE']-a['VPD_ERA'],3) if b.get('VPD_USE') is not None and a.get('VPD_ERA') is not None else None,
       'source_is_original_measured_T_and_VPD': a.get('TA_F_QC')==0 and a.get('VPD_F_QC')==0}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--self-test',action='store_true')
    for a in ('stage03b','stage03c','stage03d','stage03w'):p.add_argument('--'+a,type=Path)
    p.add_argument('--out',type=Path)
    a=p.parse_args()
    if a.self_test:
        assert tparse('201106130700',True)==datetime(2011,6,13,7)
        assert tparse('2011-06-13 07:00:00',False)==datetime(2011,6,13,7)
        assert rh(20,0)==100 and num('-9999') is None
        assert calc({}, {}, datetime(2011,6,13,7))['scope']=='MISSING'
        print('STAGE03X SELF-TEST PASS | exact flags only, NO RELEASE');return
    paths=[a.stage03b,a.stage03c,a.stage03d,a.stage03w]
    if any(q is None or not q.is_file() for q in paths):p.error('Need Stage03B/C/D/W reports')
    if a.out is None or a.out.exists() or a.out.is_symlink() or not a.out.parent.is_dir():p.error('Output must be a new PRIVATE file')
    b,c,d,w=[json.loads(x.read_text(encoding='utf-8')) for x in paths]
    if b.get('stage')!=B_STAGE or c.get('stage')!=C_STAGE or d.get('stage')!=D_STAGE or w.get('site')!='DE-Gri':raise ValueError('Incorrect stages')
    if any(x.get('science_release') is not False for x in (b,c,d,w)):raise ValueError('Source reports must remain science HOLD')
    items=[x for x in c['issues'] if x['site']=='DE-Gri' and x['issue']=='STAGE28_REMAINING_MET_FLAG']
    if len(items)!=14 or len(w.get('flags_PRIVATE',[]))!=14:raise ValueError('Expected exactly 14 flags')
    targets=[tparse(x['start_or_time'],False) for x in items]
    if any(t is None for t in targets) or len(set(targets))!=14:raise ValueError('Flag timestamps missing/duplicated')
    if set(t.isoformat(sep=' ') for t in targets)!={str(z['time']) for z in w['flags_PRIVATE']}:raise ValueError('Stage03W flag time drift')
    r=next(x for x in d['sites'] if x['site']=='DE-Gri')
    bb=next(x for x in b['sites'] if x['site']=='DE-Gri')
    src=Path(r['source_manifest_primary_file']); met=Path(r['Stage28_selected_forcing_path'])
    if not src.is_file() or not met.is_file() or str(met)!=bb['stage28_met_path'] or sha(met)!=bb['stage28_met_SHA_expected']:raise ValueError('Original Stage28 source/hash mismatch')
    original,selected=scan(src,True,targets),scan(met,False,targets)
    flags=[]
    for item,t in zip(items,targets):
        label=next(x['class'] for x in w['flags_PRIVATE'] if x['time']==t.isoformat(sep=' '))
        props=calc(original,selected,t)
        flags.append({'time':t.isoformat(sep=' '),'original_flag_metadata':item.get('source_numeric_or_meta'),
                      'legacy_decision':item.get('legacy_decision'), 'stage03w_window':label,
                      **props, 'science_status':'HOLD_UNLESS_INDEPENDENT_EVIDENCE'})
    result={'site':'DE-Gri','read_only':True,'science_release':False,'AD5_authorized':False,'source_path':str(src),
         'stage28_forcing_sha_verified':True,'time_alignment_verification':'SAME_LABEL_ONLY_NOT_INDEPENDENT_UTC_PROOF',
         '14_flags':flags,'remaining_without_both_values':sum(not (x['source_present'] and x['forcing_present']) for x in flags),
         'summary_QC':dict(Counter(str(x.get('source_T_QC'))+'/'+str(x.get('source_VPD_QC')) for x in flags)),
         'operator_action':'Review only concerning flags and independent evidence; avoid blanket ERA substitution or automatic AD5 release'}
    with a.out.open('x',encoding='utf-8') as f:json.dump(result,f,indent=2,ensure_ascii=False);f.write('\n')
    print('STAGE03X DE-GRI 14 FLAGS SOURCE/ERA/SELECTED | SCIENCE HOLD')
    print('STAGE28 SOURCE SHA PASS | EXACT FLAG COUNT',len(flags),'MISSING_PAIRS',result['remaining_without_both_values'])
    print('QC T/VPD CATEGORIES',result['summary_QC'])
    for q in flags:
        print('FLAG',q['time'],'QC',q.get('source_T_QC'),q.get('source_VPD_QC'),'T',q.get('forcing_T_C'),'T_ERA',q.get('source_TA_ERA_C'), 'VPD',q.get('forcing_VPD_hPa'),'RH',q.get('forcing_RH_water_pct'),'PRECTmm',q.get('forcing_rain_mm_per_HH'),'STEP_B_A',q.get('T_step_before_C'),q.get('T_step_after_C'),'MATCH',q.get('T_source_equals_selected'),q.get('VPD_source_equals_selected'),'EDIT_WINDOW',q['stage03w_window'])
    print('PRIVATE_REPORT',a.out)
    print('NO INPUTS / CASES / SLURM CHANGED; NOT AD5 APPROVED')

if __name__=='__main__':main()
