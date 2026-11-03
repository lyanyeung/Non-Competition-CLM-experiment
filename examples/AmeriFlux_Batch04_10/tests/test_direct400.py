"""Real NetCDF round trips and synthetic CIME/Slurm failure controls."""
import csv
from contextlib import contextmanager
import importlib.util
import json
from pathlib import Path
import shutil
import sys
import tempfile
import types
import unittest
from unittest.mock import patch
import numpy as np
import pandas as pd
from netCDF4 import Dataset

HERE = Path(__file__).resolve().parents[1]


def module(name,file):
    spec = importlib.util.spec_from_file_location(name,file)
    obj = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(obj)
    return obj


met = module('b04_met_test',HERE/'scripts/04_build_UTC_NOLEAP_DATM_and_inventory.py')
case = module('b04_case_test',HERE/'scripts/05_prepare_and_submit_direct_AD400.py')
HEIGHTS = json.loads((HERE/'data/AMF_BATCH04_TA_SENSOR_PROXY_POLICY_20261026.json').read_text())


@contextmanager
def scratch():
    base = (HERE/'tests/_temporary_tests').resolve()
    base.mkdir(exist_ok=True)
    temp = tempfile.TemporaryDirectory(dir=base)
    # Validate the absolute cleanup target before recursive context cleanup.
    assert Path(temp.name).resolve().is_relative_to(base)
    with temp as folder:
        yield folder


class ForcingTests(unittest.TestCase):
    def test_source_leap_boundary_utc_height_transition_and_netcdf(self):
        with scratch() as folder:
            root = Path(folder)
            path = root/'source.csv'
            time = pd.date_range('2012-01-01','2014-01-01',freq='30min',inclusive='left')
            source = pd.DataFrame({'TIMESTAMP_START':time.strftime('%Y%m%d%H%M'),
                'TIMESTAMP_END':(time+pd.Timedelta(minutes=30)).strftime('%Y%m%d%H%M'),
                'TA_F':10.,'VPD_F':3.,'PA_F':95.,'SW_IN_F':123.,'LW_IN_F':300.,
                'WS_F':2.,'P_F':.18})
            source.to_csv(path,index=False)
            row = {'site':'US-Rpf','first_year':2012,'last_year':2013,
                'meteorology_path':str(path),'meteorology_SHA256':met.sha(path),
                'model_tower_coordinates':[65.12,212.5]}
            values, rounding = met.source_arrays(row)
            self.assertEqual(len(values['TBOT']),2*met.N)
            self.assertEqual(rounding,[])
            self.assertTrue(np.allclose(values['PRECTmms'],.0001))
            height = met.height_for('US-Rpf',HEIGHTS)
            data = met.utc_values(met.append_height(row,values,height),-9)
            clock = pd.date_range('2013-01-01','2014-01-01',freq='30min',inclusive='left')
            transition = int(np.flatnonzero(clock == pd.Timestamp('2013-05-13 09:00'))[0])
            self.assertEqual(data['ZBOT'][met.N+transition-1],2.3)
            self.assertEqual(data['ZBOT'][met.N+transition],4.)
            # Whole-cycle wrap carries the final year's 4m into first UTC year.
            self.assertEqual(data['ZBOT'][0],4.)
            self.assertEqual(data['ZBOT'][18],2.3)
            for i,year in enumerate((2012,2013)):
                fields = {k:v[i*met.N:(i+1)*met.N] for k,v in data.items()}
                out = root/(str(year)+'.nc')
                met.annual_write(out,year,row['model_tower_coordinates'],fields,height,'US-Rpf',row['meteorology_SHA256'])
                met.annual_verify(out,year,row['model_tower_coordinates'],fields,height)
                with Dataset(out) as nc:
                    self.assertEqual(len(nc['time']),17520)
                    self.assertEqual(nc['time'].calendar,'noleap')
                if year == 2013:
                    with Dataset(out,'r+') as nc:
                        nc['QBOT'][100,0,0] = .07
                    with self.assertRaisesRegex(RuntimeError,'mismatch QBOT'):
                        met.annual_verify(out,year,row['model_tower_coordinates'],fields,height)
            self.assertEqual(met.sha(path),row['meteorology_SHA256'])

    def test_three_decimal_rounding_is_timestamp_locked(self):
        raw = np.array([[-6.234,3.842,95,0,250,2,0]],float)
        values, record = met.convert_values('US-Syv',['200803091300'],raw)
        self.assertEqual(values['QBOT'][0],0)
        self.assertEqual(len(record),1)
        with self.assertRaisesRegex(RuntimeError,'unexpected VPD'):
            met.convert_values('US-Syv',['200803091330'],raw)
        raw[0,1] = 4
        with self.assertRaises(RuntimeError):
            met.convert_values('US-Syv',['200803091300'],raw)

    def test_utc_offsets_are_bijective_in_both_directions(self):
        source = np.arange(2*met.N,dtype=float)
        for offset in (-9,-8,-7,-5,3.5,12):
            utc = met.utc_values({'x':source},offset)['x']
            self.assertTrue(np.array_equal(np.sort(utc),source))
            self.assertEqual(utc[0],source[int(offset*2)%(2*met.N)])

    def test_static_sensor_height_and_unknown_kind_rejection(self):
        for site,p in HEIGHTS.items():
            self.assertEqual(met.height_for(site,HEIGHTS),p)
        wrong = {'US-Ton':{**HEIGHTS['US-Ton'],'height_kind':'CANOPY_HEIGHT'}}
        with self.assertRaises(RuntimeError):
            met.height_for('US-Ton',wrong)


class CaseTests(unittest.TestCase):
    def test_new_plan_contains_only_ten_fixnc_cases(self):
        pre = met.loadpre()
        rows = [{'site':s,'meteorology_SHA256':'a'*64,'source_surface_SHA256':'b'*64,
                 'recommended_PFT':'test','FATES_mapping_profile':'DEFAULT14'} for s in pre.SITES]
        plan = pre.plan(rows,{})
        self.assertEqual(len(plan['experiments']),10)
        self.assertEqual(set(plan['arms']),{'FIXED_BIOGEOG_NO_COMPETITION'})
        for row in plan['experiments']:
            self.assertIn('_FIXNC_AD400',row['case_name_proposed'])
            self.assertTrue(row['case_flags_desired_requires_CTSM_build_verification']['use_fates_nocomp'])

    def test_full_preparation_and_submission_are_blocked_before_io(self):
        self.assertEqual(case.ARMS,('FIXNC',))
        with patch.object(case,'paths',side_effect=AssertionError('No FULL filesystem access')):
            with self.assertRaisesRegex(RuntimeError,'FULL preparation is disabled'):
                case.prepare_one('US-Ton','FULL',{},Path('/manifest'),370.57)
            with self.assertRaisesRegex(RuntimeError,'FULL submission is disabled'):
                case.submit_one('US-Ton','FULL',{},Path('/manifest'),370.57)
        with self.assertRaisesRegex(RuntimeError,'FULL is disabled'):
            case.flags('FULL')

    def test_actual_cime_docs_runtime_maps_and_coordinates(self):
        with scratch() as folder:
            root = Path(folder)
            casedir,rundir,archive,ledger = root/'case',root/'run',root/'arch',root/'case.json'
            docs = casedir/'CaseDocs'
            docs.mkdir(parents=True)
            rundir.mkdir()
            bld = root/'bld'
            bld.mkdir()
            (bld/'cesm.exe').write_bytes(b'fixture-binary')
            param = root/'param.json'
            param.write_text('{}')
            row = {'site':'US-Ton','first_year':2001,'last_year':2002,
                   'model_tower_coordinates':[38.43,239.04],
                   'shared_surface_path':'/US-Ton/surf.nc',
                   'annual_files':[{'path':'/US-Ton/2001.nc'},{'path':'/US-Ton/2002.nc'}]}
            for file in ('user_nl_clm','user_nl_datm_streams','.case.run','.submit_options'):
                (casedir/file).write_text('fixture')
            overrides = case.settings(row,casedir,rundir,archive,370.57)
            overrides.update(BUILD_COMPLETE='true',EXEROOT=str(bld))
            xml = '<streams><stream_info name="CLM_USRDAT.UNSET">'
            vals = {'taxmode':'cycle','tintalgo':'linear','mapalgo':'none','meshfile':'none','offset':'0',
                    'year_first':'2001','year_last':'2002','year_align':'2001'}
            xml += ''.join('<'+k+'>'+v+'</'+k+'>' for k,v in vals.items())
            xml += '<datavars>'+''.join('<var>'+k+' '+v+'</var>' for k,v in case.METMAP.items())+'</datavars>'
            xml += '<datafiles><file>/US-Ton/2001.nc</file><file>/US-Ton/2002.nc</file></datafiles></stream_info></streams>'
            runtime = 'scol_lat = 38.43\nscol_lon = 239.04\nsingle_column_lnd_domainfile = UNSET\n'
            for arm in ('FIXNC',):
                land = '\n'.join(k+' = '+v for k,v in case.flags(arm).items())
                land += "\nfsurdat = '/US-Ton/surf.nc'\nfates_paramfile = '"+str(param)+"'\nfinidat = ''\nhist_fincl1 = 'FATES_GPP','FATES_NPP'\n"
                for directory in (docs,rundir):
                    (directory/'lnd_in').write_text(land)
                    (directory/'datm.streams.xml').write_text(xml)
                    (directory/'nuopc.runconfig').write_text(runtime)
                with patch.object(case,'paths',return_value=(casedir,rundir,archive,ledger)),\
                     patch.object(case,'q',side_effect=lambda c,k:overrides[k]):
                    proof = case.generated(casedir,rundir,row,arm,param,370.57)
                    self.assertIn('executable_sha256',proof)
                    (rundir/'nuopc.runconfig').write_text(runtime.replace('38.43','46.81'))
                    with self.assertRaisesRegex(RuntimeError,'coordinates'):
                        case.generated(casedir,rundir,row,arm,param,370.57)
                    (rundir/'nuopc.runconfig').write_text(runtime)
                    for directory in (docs,rundir):
                        (directory/'datm.streams.xml').write_text(xml.replace('/US-Ton/2001.nc','/wrong-station/2001.nc'))
                    with self.assertRaisesRegex(RuntimeError,'wrong station'):
                        case.generated(casedir,rundir,row,arm,param,370.57)

    def test_arctic_only_changes_two_mapping_rows(self):
        old = {'parameters':{'fates_hlm_pft_map':{'data':np.eye(14).tolist()}}}
        fixed = case.parameter_data(old,'ARCTIC_PURE')
        a = np.asarray(old['parameters']['fates_hlm_pft_map']['data'])
        b = np.asarray(fixed['parameters']['fates_hlm_pft_map']['data'])
        self.assertEqual(np.flatnonzero(np.any(a!=b,axis=1)).tolist(),[8])
        self.assertEqual(b[8,9],1)
        self.assertEqual(b[10,10],1)
        self.assertTrue(np.array_equal(a,np.eye(14)))

    def test_multiline_history_and_ancillary_stream_preserved(self):
        text = "x = 1\nhist_fincl1 = 'GPP',\n 'NPP'\ny = 2\n"
        fixed = case.setnml(text,'hist_fincl1',"'FATES_GPP','FATES_NPP'")
        self.assertNotIn("'GPP'",fixed)
        self.assertIn('y = 2',fixed)
        row = {'first_year':2001,'last_year':2002,'annual_files':[{'path':'/US-Ton/2001.nc'},{'path':'/US-Ton/2002.nc'}]}
        src = 'CLM_USRDAT.UNSET:datavars = QBOT Sa_shum\nCLM_USRDAT.UNSET:datafiles = /other_site.nc\npreso3.clim_2000:datafiles = /ozone.nc\n'
        result = case.stream_user(src,row)
        self.assertIn('preso3.clim_2000:datafiles = /ozone.nc',result)
        self.assertNotIn('other_site',result)
        self.assertIn('year_align = 2001',result)

    def test_direct400_no_manual_ad395_handoff(self):
        row = {'first_year':2001,'last_year':2025,'model_tower_coordinates':[38.43,-120.96]}
        settings = case.settings(row,Path('/case'),Path('/run'),Path('/archive'),370.57)
        self.assertEqual(settings['RESUBMIT'],'79')
        self.assertEqual(settings['STOP_N'],'5')
        self.assertEqual(settings['REST_N'],'5')
        self.assertEqual(settings['CONTINUE_RUN'],'FALSE')
        self.assertEqual(settings['PTS_DOMAINFILE'],'UNSET')
        self.assertAlmostEqual(float(settings['PTS_LON']),239.04)

    def test_submit_attempt_is_written_after_live_guard_before_cime(self):
        with scratch() as folder:
            root = Path(folder)
            ledger = root/'case.json'
            ledger.write_text('{}')
            casedir = root/'case'
            casedir.mkdir()
            calls = []
            def guard(**kw):
                calls.append('stack')
                self.assertEqual(kw['phase'],'AD400')
                return {'soft_at_submit_KiB':'unlimited'}
            def command(args,**kw):
                if args[0] == 'squeue':
                    return ''
                self.assertTrue((root/'case_SUBMIT_ATTEMPT.json').is_file())
                self.assertEqual(calls,['stack'])
                calls.append('submit')
                self.assertIn('--skip-preview-namelist',args)
                return 'Submitted job case.run with id 123\nSubmitted job case.st_archive with id 124'
            paths = (casedir,root/'run',root/'archive',ledger)
            with patch.object(case,'paths',return_value=paths),patch.object(case,'verify_one',return_value={}),\
                 patch.object(case,'load_module',return_value=types.SimpleNamespace(require_for_submission=guard)),\
                 patch.object(case,'run',side_effect=command):
                case.submit_one('US-Ton','FIXNC',{},root/'manifest',370.57)
                self.assertEqual(calls,['stack','submit'])
                self.assertEqual(json.loads(ledger.read_text())['first_run_job'],'123')
                with self.assertRaisesRegex(RuntimeError,'Prior submit attempt'):
                    case.submit_one('US-Ton','FIXNC',{},root/'manifest',370.57)
                self.assertEqual(calls,['stack','submit'])

    def test_hard_stack_failure_prevents_attempt_and_cime(self):
        with scratch() as folder:
            root = Path(folder)
            ledger = root/'case.json'
            ledger.write_text('{}')
            guard = types.SimpleNamespace(require_for_submission=lambda **kw:(_ for _ in ()).throw(RuntimeError('stack hard limit')))
            with patch.object(case,'paths',return_value=(root/'case',root/'run',root/'arch',ledger)),\
                 patch.object(case,'verify_one',return_value={}),patch.object(case,'load_module',return_value=guard),\
                 patch.object(case,'run',return_value='') as call:
                with self.assertRaisesRegex(RuntimeError,'stack hard limit'):
                    case.submit_one('US-Ton','FIXNC',{},root/'manifest',370.57)
                self.assertFalse((root/'case_SUBMIT_ATTEMPT.json').exists())
                self.assertEqual(call.call_count,1)  # squeue read only


class StackTests(unittest.TestCase):
    def guard(self,soft,hard,config):
        limits = [soft,hard]
        fake = types.SimpleNamespace(RLIM_INFINITY=-1,RLIMIT_STACK=3,
            getrlimit=lambda key:tuple(limits),
            setrlimit=lambda key,vals:limits.__setitem__(slice(None),vals))
        with patch.dict(sys.modules,{'resource':fake}):
            g = module('b04_stack_test',HERE/'scripts/b04_stack_guard.py')
        output = types.SimpleNamespace(returncode=0,stdout=config,stderr='')
        with patch.object(g.subprocess,'run',return_value=output):
            proof = g.require_for_submission(site='US-Ton',phase='AD400',may_raise=True)
        return proof,limits

    def test_low_raised_and_unlimited_not_reduced(self):
        proof,limits = self.guard(8192*1024,-1,'PropagateResourceLimits = ALL\n')
        self.assertEqual(limits,[300000*1024,-1])
        self.assertTrue(proof['changed_this_python_process_only'])
        proof,limits = self.guard(-1,-1,'PropagateResourceLimits = ALL\n')
        self.assertEqual(limits,[-1,-1])
        self.assertFalse(proof['changed_this_python_process_only'])

    def test_low_hard_limit_or_explicit_stack_exclusion_refused(self):
        with self.assertRaisesRegex(RuntimeError,'HARD LIMIT'):
            self.guard(8192*1024,32768*1024,'PropagateResourceLimits = ALL\n')
        with self.assertRaisesRegex(RuntimeError,'EXPLICITLY EXCLUDED'):
            self.guard(-1,-1,'PropagateResourceLimits = ALL\nPropagateResourceLimitsExcept = STACK\n')


if __name__ == '__main__':
    unittest.main()
