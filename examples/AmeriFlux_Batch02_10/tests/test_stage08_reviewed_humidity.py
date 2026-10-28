import importlib.util
import json
import re
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import numpy as np
from netCDF4 import Dataset

SCRIPT = Path(__file__).resolve().parents[1]/'scripts/08_US_ICh_reviewed_humidity_repair.py'
spec = importlib.util.spec_from_file_location('stage08', SCRIPT)
M = importlib.util.module_from_spec(spec); spec.loader.exec_module(M)


def forcing(path, year=2008):
    path.parent.mkdir(parents=True,exist_ok=True)
    with Dataset(path,'w') as d:
        for k,n in [('time',17520),('lat',1),('lon',1)]: d.createDimension(k,n)
        t = d.createVariable('time','f8',('time',))
        t.units=f'days since {year}-01-01 00:00:00'; t.calendar='noleap'
        t[:] = np.arange(17520)/48+1/96
        vals = {'RH':(70.,'%'),'QBOT':(.0002,'kg/kg'),'SHUM':(.0002,'kg/kg'),
                'TBOT':(241.108,'K'),'PSRF':(88822.,'Pa'),'ZBOT':(1.93,'m'),
                'WIND':(.196,'m/s'),'FSDS':(0.,'W/m2')}
        for k,(v,unit) in vals.items():
            x=d.createVariable(k,'f8',('time','lat','lon')); x.units=unit; x[:]=v
        if year == 2008:
            d['RH'][510,0,0]=.023877231414651562
            d['QBOT'][510,0,0]=7.024361018661533e-8
            d['SHUM'][510,0,0]=7.024361018661533e-8
        d.utc_offset_hours=-9


def cds(path, lat=68.5, count=24):
    with Dataset(path,'w') as d:
        d.createDimension('valid_time',count)
        t=d.createVariable('valid_time','i8',('valid_time',));t.units='hours since 2008-01-11 00:00:00';t[:]=np.arange(count)
        for k,value in [('latitude',lat),('longitude',210.75)]:
            v=d.createVariable(k,'f8');v.assignValue(value)
        for k,value,unit in [('t2m',235.6,'K'),('d2m',232.3,'K'),('sp',87400.,'Pa')]:
            v=d.createVariable(k,'f8',('valid_time',));v.units=unit;v[:]=value


class HumidityTests(unittest.TestCase):
    def test_policy_boundaries_and_known_failure(self):
        mask,q,vpd=M.proposed([241.108]*5,[88822]*5,[.023877,1.,.5,.5,.5],
                             [-37.588879,-37.5,-37.5,-40.0421,-40.042],
                             [70.82619325,70.,49.99,70.,50.])
        np.testing.assert_array_equal(mask,[True,False,False,False,True])
        self.assertAlmostEqual(q[0],.0002084,places=7)
        self.assertAlmostEqual(vpd[0],.1226,places=4)

    def test_cyclic_utc_and_noleap_mapping(self):
        with tempfile.TemporaryDirectory() as td:
            f=Path(td)/'2007.nc'; forcing(f,2007)
            with Dataset(f) as d: dates=M.source_dates(d,2007,18)
            self.assertEqual(dates[0],datetime(2026,1,1,0,15))
            self.assertEqual(dates[17],datetime(2026,1,1,8,45))
            self.assertEqual(dates[18],datetime(2007,1,1,9,15))
            f=Path(td)/'2008.nc';forcing(f)
            with Dataset(f) as d: dates=M.source_dates(d,2008,18)
            self.assertEqual(dates[59*48],datetime(2008,2,29,0,15))
            self.assertEqual(dates[59*48+17],datetime(2008,2,29,8,45))
            self.assertEqual(dates[59*48+18],datetime(2008,3,1,9,15))
            self.assertEqual(dates[510],datetime(2008,1,11,15,15))

    def test_full_19_year_source_scan_and_tamper_detection(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); records=[]
            for y in range(2007,2026):
                f=root/f'{y}.nc';forcing(f,y)
                records.append({'year':y,'path':str(f),'sha256':M.sha(f)})
            M.save(root/'manifest.json',dict(complete=True,site='US-ICh',utc_offset_h=-9,shift_records=18,files=records))
            src,low=M.inventory(root)
            self.assertEqual(len(src),19);self.assertEqual(len(low),1)
            self.assertEqual(low[0]['source_utc'],'2008-01-11T15:15:00')
            with Dataset(root/'2010.nc','r+') as d:d['TBOT'][0,0,0]=250
            with self.assertRaisesRegex(RuntimeError,'source changed'):M.inventory(root)

    def test_cds_grid_clock_and_interpolation(self):
        with tempfile.TemporaryDirectory() as td:
            f=Path(td)/'era.nc';cds(f)
            era=M.read_cds(f,datetime(2008,1,11),datetime(2008,1,11))
            low=[dict(source_utc='2008-01-11T15:15:00',file_year=2008,index=510,
                      TA_C=-32.042,PA_Pa=88822.,RH_before=.023877)]
            self.assertEqual(M.decisions(low,era)[0]['decision'],'REPAIR')
            bad=Path(td)/'bad.nc';cds(bad,lat=68.75)
            with self.assertRaisesRegex(RuntimeError,'grid'):M.read_cds(bad,datetime(2008,1,11),datetime(2008,1,11))
            short=Path(td)/'short.nc';cds(short,count=23)
            with self.assertRaisesRegex(RuntimeError,'time axis'):M.read_cds(short,datetime(2008,1,11),datetime(2008,1,11))

    def test_unaddressed_known_failure_blocks_release(self):
        low=[dict(source_utc='2008-01-11T15:15:00',file_year=2008,index=510,TA_C=-32.042,PA_Pa=88822.,RH_before=.02)]
        sec=np.array([(datetime(2008,1,11,h)-datetime(1970,1,1)).total_seconds() for h in (15,16)])
        with self.assertRaisesRegex(RuntimeError,'known failing'):
            M.decisions(low,(sec,np.array([-37.5,-37.5]),np.array([40.,40.])))

    def test_versioned_forcing_preserves_every_unapproved_value(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);src=root/'old/2008.nc';forcing(src)
            before=M.sha(src)
            sources=[dict(year=2008,path=str(src),sha256=before)]
            rows=[dict(file_year=2008,index=510,decision='REPAIR',RH_after=70.82619325,
                       QBOT_after=.0002083875,VPD_after_hPa=.12256)]
            M.write_csv(root/'all_low_RH_decisions.csv',rows)
            dest,fm=M.build_forcing(root,sources,rows)
            self.assertEqual(M.sha(src),before)
            with Dataset(src) as a,Dataset(dest/'2008.nc') as b:
                for k in ('TBOT','PSRF','ZBOT','WIND','FSDS','time'):
                    np.testing.assert_array_equal(a[k][:],b[k][:])
                keep=np.arange(17520)!=510
                np.testing.assert_array_equal(a['QBOT'][keep],b['QBOT'][keep])
                self.assertAlmostEqual(float(b['RH'][510,0,0]),70.82619325)
            self.assertEqual(M.build_forcing(root,sources,rows)[1],fm)
            with Dataset(dest/'2008.nc','r+') as d:d['TBOT'][0,0,0]=250
            with self.assertRaisesRegex(RuntimeError,'candidate forcing changed'):M.build_forcing(root,sources,rows)

    def test_xml_ancillary_and_user_stream_path_invariants(self):
        x='<file><stream_info name="CLM_USRDAT.UNSET"><taxmode>cycle</taxmode><datafiles><file>/old/2008.nc</file></datafiles></stream_info><stream_info name="dust"><datafiles><file>/dust.nc</file></datafiles></stream_info></file>'
        expect=M.expected_xml(x,{'/old/2008.nc':'/new/2008.nc'})
        y=x.replace('/old/2008.nc','/new/2008.nc')
        self.assertEqual(M.canonical(M.ET.fromstring(y)),expect)
        self.assertNotEqual(M.canonical(M.ET.fromstring(y.replace('/dust.nc','/wrong.nc'))),expect)
        self.assertEqual(M.replace_paths('met:datafiles = /old/2008.nc\n',{'/old/2008.nc':'/new/2008.nc'}),'met:datafiles = /new/2008.nc\n')
        with self.assertRaises(RuntimeError):M.replace_paths('other',{'/old/2008.nc':'/new/2008.nc'})


class FakeCIME:
    FATES_FLAGS={'use_fates':'.true.','use_fates_fixed_biogeog':'.true.','use_fates_nocomp':'.true.'}
    RUN_RE=re.compile(r'Submitted job case\.run with id (\d+)')
    ARCH_RE=re.compile(r'Submitted job case\.st_archive with id (\d+)')
    def __init__(self,root,preview_fail=False,submit_fail=False):
        self.EXP=root/'exp';self.EXP.mkdir()
        self.case=root/'case';self.case.mkdir();(self.case/'LockedFiles').mkdir();(self.case/'CaseDocs').mkdir()
        self.run=root/'run';self.run.mkdir();self.arch=root/'archive';self.arch.mkdir()
        self.OVERLAY=root/'overlay';self.preview_fail=preview_fail;self.submit_fail=submit_fail
        self.submit_count=0;self.cancelled=[];self.pending=True
        self.file=root/'old/2008.nc';forcing(self.file)
        self.new=root/'new/2008.nc';self.new.parent.mkdir();shutil=__import__('shutil');shutil.copy2(self.file,self.new)
        self.surface=root/'surfdata_US-ICh_FIXNC_PFT_soil10_stage07_v2.nc';self.surface.write_text('soil')
        self.param=root/'arctic.json';self.param.write_text('{}')
        self.cfg=dict(CASE=self.name('US-ICh'),RUNDIR=str(self.run),DOUT_S_ROOT=str(self.arch),RUN_TYPE='startup',RUN_STARTDATE='2007-01-01',CONTINUE_RUN='FALSE',CLM_FORCE_COLDSTART='on',CLM_ACCELERATED_SPINUP='on',STOP_N='5',REST_N='5',STOP_OPTION='nyears',REST_OPTION='nyears',RESUBMIT='79',RESUBMIT_SETS_CONTINUE_RUN='TRUE')
        land='\n'.join([f'{k} = {v}' for k,v in self.FATES_FLAGS.items()]+['spinup_state = 2',f"fsurdat = '{self.surface}'",f"fates_paramfile = '{self.param}'"])
        xml=f'<file><stream_info name="CLM_USRDAT.UNSET"><taxmode>cycle</taxmode><datafiles><file>{self.file}</file></datafiles></stream_info><stream_info name="dust"><datafiles><file>/dust.nc</file></datafiles></stream_info></file>'
        (self.case/'CaseDocs/lnd_in').write_text(land);(self.run/'lnd_in').write_text(land)
        (self.case/'CaseDocs/datm.streams.xml').write_text(xml);(self.run/'datm.streams.xml').write_text(xml)
        (self.case/'user_nl_datm_streams').write_text(f'met:datafiles = {self.file}\n')
        (self.case/'user_nl_clm').write_text('UNCHANGED');(self.case/'CaseStatus').write_text('case.run starting 4741683\ncase.run error\n')
        for rel in ('env_case.xml','LockedFiles/env_case.xml','env_run.xml'):(self.case/rel).write_text('ORIGINAL')
        (self.run/(self.name('US-ICh')+'.clm2.h0a.2008.nc')).write_text('PARTIAL HISTORY')
        self.led=root/'ledger.json';self.save(self.led,dict(phase='AD400_SUBMITTED',first_run_job='4741683',first_archive_job='4741684',surface=str(self.surface),surface_sha256=M.sha(self.surface),fates_paramfile=str(self.param),fates_paramfile_sha256=M.sha(self.param)))
    def name(self,s):return 'US-ICh_AMF_B02_FIXNC_AD400_DIRECT'
    def case_dir(self,s):return self.case
    def run_dir(self,s):return self.run
    def arch_dir(self,s):return self.arch
    def ledger(self,s):return self.led
    def xq(self,c,k):return self.cfg[k]
    def xc(self,c,k,v):
        if k=='COMP_ROOT_DIR_LND':
            text='ORIGINAL' if v=='$SRCROOT' else 'OVERLAY'
            for rel in ('env_case.xml','LockedFiles/env_case.xml'):(self.case/rel).write_text(text)
        else:self.cfg[k]=v
    def latest(self,s):return None,0
    def queued(self,n):return [['4741684','st_archive.'+n,'PENDING']] if self.pending else []
    def sacct_name(self,n):return [(4741683,'run.'+n,'FAILED','1:0')]
    def stack_guard(self):return {'soft':'unlimited'}
    def load(self,p):return json.loads(Path(p).read_text())
    def save(self,p,o):return M.save(p,o)
    def nml_get(self,t,k):
        x=re.search(r'(?m)^\s*'+k+r'\s*=\s*(.*)$',t)
        return x.group(1).strip().strip("'\"") if x else None
    def cmd(self,argv,cwd=None,timeout=None):
        a=list(map(str,argv))
        if 'preview_namelists' in a[0]:
            old=(self.case/'CaseDocs/datm.streams.xml').read_text()
            for p in (self.case/'CaseDocs/datm.streams.xml',self.run/'datm.streams.xml'):
                p.write_text(old.replace(str(self.file),str(self.new)))
            if self.preview_fail:raise RuntimeError('simulated preview failure')
            return 'PREVIEW OK'
        if a[0]=='scancel':self.pending=False;self.cancelled.append(a[1]);return ''
        if 'case.submit' in a[0]:
            self.submit_count+=1
            if self.submit_fail:raise RuntimeError('simulated ambiguous submission')
            return 'Submitted job case.run with id 999000\nSubmitted job case.st_archive with id 999001\n'
        raise AssertionError(a)


class RecoveryTests(unittest.TestCase):
    def apply(self,root,f):
        state=dict(phase='FORCING_BUILT')
        sources=[dict(year=2008,path=str(f.file),sha256=M.sha(f.file))]
        fm={'files':[dict(year=2008,path=str(f.new),sha256=M.sha(f.new))]}
        with patch.object(M,'S6',f):M.apply_and_submit(root,state,sources,fm)

    def test_real_guard_preview_history_backup_and_submit_once(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);f=FakeCIME(root)
            self.apply(root,f)
            self.assertEqual(f.submit_count,1);self.assertEqual(f.cancelled,['4741684'])
            self.assertEqual(f.cfg['RESUBMIT'],'79');self.assertEqual(f.cfg['CONTINUE_RUN'],'FALSE')
            self.assertEqual((f.case/'user_nl_clm').read_text(),'UNCHANGED')
            self.assertFalse(list(f.run.glob('*.h*.nc')))
            self.assertEqual(len(list((root/'case_backup/partial_history').glob('*.nc'))),1)
            self.assertEqual(json.loads((root/'state.json').read_text())['phase'],'SUBMITTED')
            self.assertEqual(f.load(f.led)['first_run_job'],'999000')
            # A new invocation stops at the persisted submission phase before any
            # case guard or mutation, even if the model has not started yet.
            d=f.EXP/'Stage08_USICh_reviewed_humidity';d.mkdir()
            M.save(d/'state.json',dict(phase='SUBMITTED',run_job='999000',archive_job='999001'))
            with patch.object(M,'S6',f),patch.object(M.sys,'argv',[str(SCRIPT),'run','--confirm',M.ACK]):M.main()
            self.assertEqual(f.submit_count,1)

    def test_preview_failure_restores_inputs_without_cancelling(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);f=FakeCIME(root,preview_fail=True)
            old=(f.case/'CaseDocs/datm.streams.xml').read_text()
            with self.assertRaisesRegex(RuntimeError,'simulated preview'):self.apply(root,f)
            self.assertEqual((f.case/'CaseDocs/datm.streams.xml').read_text(),old)
            self.assertEqual((f.run/'datm.streams.xml').read_text(),old)
            self.assertEqual((f.case/'env_case.xml').read_text(),'ORIGINAL')
            self.assertEqual(f.submit_count,0);self.assertEqual(f.cancelled,[])
            self.assertTrue(list(f.run.glob('*.h*.nc')))

    def test_ambiguous_submit_is_never_repeated(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);f=FakeCIME(root,submit_fail=True)
            with self.assertRaisesRegex(RuntimeError,'ambiguous'):self.apply(root,f)
            state=json.loads((root/'state.json').read_text())
            self.assertEqual(state['phase'],'SUBMIT_ATTEMPTED_UNCERTAIN')
            d=f.EXP/'Stage08_USICh_reviewed_humidity';d.mkdir();M.save(d/'state.json',state)
            with patch.object(M,'S6',f),patch.object(M.sys,'argv',[str(SCRIPT),'run','--confirm',M.ACK]):
                with self.assertRaisesRegex(RuntimeError,'refusing automatic retry'):M.main()
            self.assertEqual(f.submit_count,1)

    def test_new_run_or_existing_restart_blocks_cold_start(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);f=FakeCIME(root)
            with patch.object(M,'S6',f):
                (f.run/'case.clm2.r.2012.nc').write_text('RESTART')
                with self.assertRaisesRegex(RuntimeError,'usable restart'):M.guard_case()
                (f.run/'case.clm2.r.2012.nc').unlink()
                (f.case/'CaseStatus').write_text('case.run starting 999999\n')
                with self.assertRaisesRegex(RuntimeError,'newer model run'):M.guard_case()
            self.assertEqual(f.submit_count,0)


if __name__=='__main__':unittest.main()
