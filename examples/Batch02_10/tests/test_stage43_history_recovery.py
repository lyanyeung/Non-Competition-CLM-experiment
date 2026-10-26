import contextlib
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import shutil
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

HERE=Path(__file__).resolve().parent
SCRIPT=HERE.parent/'scripts/43_five_GPP_NPP_histfix_AD400.py'
spec=importlib.util.spec_from_file_location('stage43',SCRIPT)
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)


class RecoveryTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='_stage43_fixture_',dir=HERE)
        self.root=Path(self.temp.name).resolve()
        self.base=self.root/'base';self.output=self.root/'output'
        self.experiment=self.base/'experiment';self.records=self.experiment/'records'
        self.overlay=self.experiment/'overlay';self.ctsm=self.base/'CTSM'
        for name in ['bld/CLMBuildNamelist.pm','bld/build-namelist']:
            p=self.overlay/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text('trusted fixture\n')
        self.patches=[patch.object(m,'BASE',self.base),patch.object(m,'OUTPUT',self.output),
                      patch.object(m,'EXPERIMENT',self.experiment),patch.object(m,'RECORDS',self.records),
                      patch.object(m,'OVERLAY',self.overlay),patch.object(m,'CTSM',self.ctsm)]
        for p in self.patches:p.start()
        self.old_targets=dict(m.TARGETS);self.xml={};self.jobs=[];self.calls=[]
        self.inject_land_change=False;self.fail_submit=False;self.submit_count=0
        m._HASH_CACHE.clear()
        targets={}
        for site,row in self.old_targets.items():
            job,old,new,start,_,logname,_=row
            case=self.base/'cases'/old;run=self.output/old/'run'
            (case/'CaseDocs').mkdir(parents=True);(case/'LockedFiles').mkdir()
            run.mkdir(parents=True)
            assets=self.root/'inputs'/site;assets.mkdir(parents=True)
            for name in ['surface.nc','params.json','cesm.exe','year1.nc','year2.nc']:
                (assets/name).write_bytes(('fixed '+name).encode())
            fields='hist_fincl1 = '+','.join("'"+x+"'" for x in m.BEFORE)+'\n'
            land="&clm_inparm\n"+fields+"hist_mfilt = 12\n"+\
                ''.join(k+' = '+v+'\n' for k,v in {
                'use_fates':'.true.','use_fates_nocomp':'.true.','use_fates_fixed_biogeog':'.true.',
                'use_fates_sp':'.false.','use_cn':'.false.','spinup_state':'2','finidat':"''",
                'fsurdat':"'"+str(assets/'surface.nc')+"'",'fates_paramfile':"'"+str(assets/'params.json')+"'"}.items())+\
                "/\n!#     /opt/build/CLM build-namelist -infile "+str(case)+\
                "/Buildconf/namelist -envxml_dir "+str(case)+" -config "+str(case)+"/config_cache.xml\n"
            (case/'CaseDocs/lnd_in').write_text(land);(run/'lnd_in').write_text(land)
            first=int(start[:4])
            xml='<streams><stream_info name="CLM_USRDAT.UNSET"><year_first>'+str(first)+\
                '</year_first><year_last>'+str(first+1)+'</year_last><datafiles><file>'+str(assets/'year1.nc')+\
                '</file><file>'+str(assets/'year2.nc')+'</file></datafiles></stream_info></streams>'
            (case/'CaseDocs/datm.streams.xml').write_text(xml);(run/'datm.streams.xml').write_text(xml)
            for name in ['user_nl_clm','user_nl_datm_streams','CaseStatus','env_case.xml','LockedFiles/env_case.xml']:
                (case/name).write_text('<config><entry id="COMP_ROOT_DIR_LND" value="$SRCROOT"/></config>\n'
                                      if 'env_case' in name else 'original '+name+'\n')
            (case/'.case.run').write_text('fixture batch script\n')
            registry='\n'.join(' {} {}          units'.format(i,x) for i,x in
                               enumerate(m.AFTER+['FIELD_'+str(n) for n in range(1010)],1))
            log=registry+'\nhtapes_fieldlist ERROR: GPP in fincl(4)\nERROR in histFileMod.F90 at line 899\n'
            (run/logname).write_text(log)
            targets[site]=(job,old,new,start,m.digest(case/'CaseDocs/lnd_in'),logname,m.digest(run/logname))
            values={k:'UNSET' for k in m.SCIENCE_XML}
            values.update(RUN_STARTDATE=start,CALENDAR='NO_LEAP',PTS_LAT='40.0',PTS_LON='10.0',
                          CCSM_CO2_PPMV='370.0',EXEROOT=str(assets),MPI_RUN_COMMAND='srun --mpi=pmix',
                          RUNDIR=str(run),DOUT_S_ROOT=str(self.output/'archive'/old),
                          RUN_TYPE='startup',CONTINUE_RUN='FALSE',CLM_ACCELERATED_SPINUP='on',
                          STOP_N='5',REST_N='5',RESUBMIT='79',BUILD_COMPLETE='TRUE',COMP_ROOT_DIR_LND='$SRCROOT',
                          STOP_OPTION='nyears',REST_OPTION='nyears',DOUT_S='TRUE',RESUBMIT_SETS_CONTINUE_RUN='TRUE')
            self.xml[str(case)]=values
            self.jobs.append(str(int(job)+1)+'|st_archive.'+old+'|PENDING')
        self.target_patch=patch.object(m,'TARGETS',targets);self.target_patch.start()
        self.call_patch=patch.object(m,'call',side_effect=self.call);self.call_patch.start()
        self.stack_patch=patch.object(m,'stack_guard',return_value={'soft_bytes':-1,'hard_bytes':-1,'host':'fixture'})
        self.stack_patch.start()
        self.source_before=self.source_bytes()

    def tearDown(self):
        self.stack_patch.stop();self.call_patch.stop();self.target_patch.stop()
        for p in reversed(self.patches):p.stop()
        self.assertEqual(self.root.parent,HERE)
        self.assertTrue(self.root.name.startswith('_stage43_fixture_'))
        self.temp.cleanup()

    def source_bytes(self):
        return {str(p):p.read_bytes() for row in m.TARGETS.values()
                for folder in [self.base/'cases'/row[1],self.output/row[1]/'run']
                for p in folder.rglob('*') if p.is_file()}

    def call(self,args,cwd=None,timeout=120):
        args=list(map(str,args));self.calls.append(args);tool=Path(args[0]).name
        if tool=='squeue':return '\n'.join(self.jobs)
        if tool=='sacct':
            job=args[args.index('-j')+1]
            return job+'|FAILED|'
        case=Path(args[0]).parent
        if tool=='xmlquery':
            value=self.xml[str(case)][args[1]]
            return str(self.ctsm) if args[1]=='COMP_ROOT_DIR_LND' and value=='$SRCROOT' else value
        if tool=='xmlchange':
            key,val=args[1].split('=',1);self.xml[str(case)][key]=val
            if key=='COMP_ROOT_DIR_LND':
                (case/'env_case.xml').write_text('<config><entry id="COMP_ROOT_DIR_LND" value="'+val+'"/></config>\n')
            return ''
        if tool=='create_clone':
            new=Path(args[args.index('--case')+1]);old=Path(args[args.index('--clone')+1])
            shutil.copytree(old,new)
            self.xml[str(new)]=dict(self.xml[str(old)],CASE=new.name)
            return ''
        if tool=='preview_namelists':
            row=next(r for r in m.TARGETS.values() if r[2]==case.name)
            old=self.base/'cases'/row[1];run=Path(self.xml[str(case)]['RUNDIR'])
            run.mkdir(parents=True)
            text=m.fixed_user_nl((old/'CaseDocs/lnd_in').read_text()).replace(str(old),str(case))
            if self.inject_land_change:text=text.replace('hist_mfilt = 12','hist_mfilt = 24')
            for p in [case/'CaseDocs/lnd_in',run/'lnd_in']:p.write_text(text)
            for p in [case/'CaseDocs/datm.streams.xml',run/'datm.streams.xml']:
                p.write_text('old template selected by preview; must be replaced in new case')
            for p in [case/'CaseDocs/nuopc.runconfig',run/'nuopc.runconfig']:
                p.write_text('scol_lat = 40.0\nscol_lon = 10.0\n')
            return ''
        if tool=='case.submit' and '--help' in args:return '--skip-preview-namelist'
        if tool=='case.submit':
            self.submit_count+=1
            if self.fail_submit:raise RuntimeError('uncertain Slurm connection')
            (case/'.submit_options').write_text('[SubmitOptions]\nskip_pnl = True\n')
            self.jobs.append(str(9000+self.submit_count*2)+'|run.'+case.name+'|PENDING')
            return 'Submitted job case.run with id {}\nSubmitted job case.st_archive with id {}'.format(
                9000+self.submit_count*2,9001+self.submit_count*2)
        raise AssertionError('Unexpected command '+repr(args))

    def invoke(self,action,confirm='',sites=None):
        argv=[str(SCRIPT),'--'+action]
        if confirm:argv+=['--confirm',confirm]
        if sites:argv+=['--sites',*sites]
        out=io.StringIO()
        with patch('sys.argv',argv),contextlib.redirect_stdout(out),contextlib.redirect_stderr(out):
            code=m.main()
        return code,out.getvalue()

    def test_five_case_prepare_verify_submit_and_duplicate_stop(self):
        code,out=self.invoke('prepare',m.P_ACK);self.assertEqual(code,0,out)
        self.assertEqual(self.submit_count,0)
        self.assertEqual(self.source_before,self.source_bytes())
        code,out=self.invoke('verify');self.assertEqual(code,0,out)
        code,out=self.invoke('start',m.S_ACK);self.assertEqual(code,0,out)
        self.assertEqual(self.submit_count,5)
        self.assertEqual(self.source_before,self.source_bytes())
        for site in m.TARGETS:
            p=m.paths(site);data=json.loads(p['submit'].read_text())
            self.assertEqual(data['phase'],'SUBMITTED_AD400_NOT_COMPLETED')
            self.assertEqual(self.xml[str(p['new'])]['RESUBMIT'],'79')
            self.assertEqual(m.fields((p['run']/'lnd_in').read_text()),m.AFTER)
        code,out=self.invoke('start',m.S_ACK)
        self.assertEqual(code,1);self.assertEqual(self.submit_count,5)

    def test_last_source_changed_blocks_all_preparation(self):
        p=m.paths('CH-Lae');(p['oldrun']/p['log_name']).write_text('changed source log')
        code,out=self.invoke('prepare',m.P_ACK)
        self.assertEqual(code,1)
        self.assertFalse(self.records.exists())
        self.assertFalse(any(m.paths(s)['new'].exists() for s in m.TARGETS))

    def test_scientific_change_during_preview_blocks_submission(self):
        self.inject_land_change=True
        code,out=self.invoke('prepare',m.P_ACK,sites=['DK-Sor'])
        self.assertEqual(code,1)
        self.assertIn('Unexpected effective land differences',out)
        self.assertEqual(self.submit_count,0)
        p=m.paths('DK-Sor')
        self.assertEqual(json.loads(p['prep'].read_text())['phase'],'PREPARATION_ATTEMPT_UNCERTAIN')
        self.assertEqual(self.source_before,self.source_bytes())

    def test_uncertain_submission_cannot_be_repeated(self):
        code,out=self.invoke('prepare',m.P_ACK,sites=['DK-Sor']);self.assertEqual(code,0,out)
        self.fail_submit=True
        code,out=self.invoke('start',m.S_ACK,sites=['DK-Sor']);self.assertEqual(code,1)
        self.assertEqual(self.submit_count,1)
        self.assertEqual(json.loads(m.paths('DK-Sor')['submit'].read_text())['phase'],'SUBMISSION_ATTEMPT_UNCERTAIN')
        code,out=self.invoke('start',m.S_ACK,sites=['DK-Sor']);self.assertEqual(code,1)
        self.assertEqual(self.submit_count,1)

    def test_forcing_change_after_prepare_blocks_start(self):
        code,out=self.invoke('prepare',m.P_ACK,sites=['DK-Sor']);self.assertEqual(code,0,out)
        source=self.root/'inputs/DK-Sor/year1.nc'
        source.write_bytes(b'changed meteorology')
        code,out=self.invoke('start',m.S_ACK,sites=['DK-Sor'])
        self.assertEqual(code,1)
        self.assertIn('Source inputs/config changed',out)
        self.assertEqual(self.submit_count,0)

    def test_unrecorded_manual_submission_blocks_start(self):
        code,out=self.invoke('prepare',m.P_ACK,sites=['DK-Sor']);self.assertEqual(code,0,out)
        p=m.paths('DK-Sor');(p['new']/'CaseStatus').write_text('case.submit starting\n')
        code,out=self.invoke('start',m.S_ACK,sites=['DK-Sor'])
        self.assertEqual(code,1)
        self.assertIn('submission/launch history',out)
        self.assertEqual(self.submit_count,0)


class StackTests(unittest.TestCase):
    def test_low_stack_fails_high_stack_and_unlimited_pass(self):
        # Use a fresh module function; RecoveryTests patches only its own calls.
        fake=types.SimpleNamespace(RLIMIT_STACK=3,RLIM_INFINITY=-1,
                                   getrlimit=lambda key:(8*1024*1024,-1))
        with patch.dict(sys.modules,{'resource':fake}),patch.dict('os.environ',{},clear=True):
            with self.assertRaises(RuntimeError):m.stack_guard()
            fake.getrlimit=lambda key:(65536*1024,-1)
            self.assertEqual(m.stack_guard()['soft_bytes'],65536*1024)
            fake.getrlimit=lambda key:(-1,-1)
            self.assertEqual(m.stack_guard()['soft_bytes'],-1)
            with patch.dict('os.environ',{'SBATCH_PROPAGATE':'NONE'}):
                with self.assertRaises(RuntimeError):m.stack_guard()


if __name__=='__main__':unittest.main(verbosity=2)
