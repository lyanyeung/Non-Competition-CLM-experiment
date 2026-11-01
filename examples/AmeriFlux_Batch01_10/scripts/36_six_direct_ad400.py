#!/usr/bin/env python3
"""Prepare and submit selected six-site direct AD400 cases on IRIDIS.

Uses the already prepared, unmodified Stage23 UTC forcing and surface receipts.
The new cases are separate from the previously previewed AD5 cases. One CIME
submission runs 80 five-year segments (79 resubmissions). No Normal is started.
The default sites are CA-TP1 and CA-TP3; the other four have unresolved Met
flags and require the explicit --unmodified-flagged-inputs option. This option
labels them exploratory and does not apply any candidate repair.
"""
import argparse
import importlib.util
from pathlib import Path

SITES=('CA-Cbo','CA-Man','CA-TP1','CA-TP3','US-Aud','US-Bar')
DEFAULT=('CA-TP1','CA-TP3')
FLAGGED=set(SITES)-set(DEFAULT)


def load_module(path, name):
    spec=importlib.util.spec_from_file_location(name, path)
    mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    return mod


def selected(sites, allow_flagged):
    result=tuple(s for s in SITES if s in (sites or DEFAULT))
    if not result: raise ValueError('No sites selected')
    flagged=FLAGGED.intersection(result)
    if flagged and not allow_flagged:
        raise ValueError('Unresolved Met flags in '+', '.join(sorted(flagged))+'; use reviewed inputs or explicitly select --unmodified-flagged-inputs for exploratory runs')
    return result


def setup(stage, helper, root, data):
    stage.configure(helper,root,data)
    helper.SEGMENTS=80
    helper.SEG_YEARS=5
    helper.D06=helper.B/'experiments/NonCompetitionObserved22/AmeriFlux_Batch01_10/Stage36_six_direct_AD400'
    helper.name=lambda site: f'{site}_AMF_B01SIX_FIXNC_AD400_DIRECT'


def preflight(helper, data, co2_file, sites):
    template=helper.template_info()
    co2, co2_src, co2_sha=helper.co2_table(co2_file)
    matrix=helper._json_map(__import__('json').loads(template['paramfile'].read_text()))
    ctx={'tpl':template,'co2':co2,'co2_src':co2_src+' sha256='+co2_sha,'surface':{},'clock':{}}
    for site in sites:
        item=data[site]; obj=item['receipt']; surface=item['surface']
        if obj['fates_parameter_sha256'] != template['param_sha256']: raise ValueError(site+': FATES parameter checksum differs')
        mapped={}
        for host,value in surface['host'].items():
            if host:
                for slot,weight in enumerate(matrix[host-1]):
                    if weight>0: mapped[slot+1]=mapped.get(slot+1,0)+value*float(weight)
        want=item['fates']
        if any(abs(mapped.get(k,0)-want.get(k,0))>1e-3 for k in set(mapped)|set(want)): raise ValueError(site+': FATES mapping mismatch')
        if not 250<co2[item['years'][0]]<500: raise ValueError(site+': CO2 out of range')
        for p in (helper.case_dir(site),helper.OUT/helper.name(site),helper.arch_dir(site),helper.ledger(site)):
            if p.exists() or p.is_symlink(): raise ValueError(site+': case, output or ledger already exists: '+str(p))
        if helper.queued(helper.name(site)) or helper.sacct_name(helper.name(site)): raise ValueError(site+': matching Slurm history exists')
        pol=obj['height_policy']
        ctx['surface'][site]=surface
        ctx['clock'][site]={'utc_offset_h':float(obj['UTC_offset_hours']),'zbot_m':float(pol['baseline_m']),
                            'height_policy':pol,'zbot_note':'baseline; forcing may have dynamic ZBOT',
                            'source_receipt_sha256':helper.digest(item['manifest'])}
        print('CHECK PASS',site,'DIRECT AD400 80x5; unmodified Stage23; flagged=',site in FLAGGED,flush=True)
    return ctx


def prepare(helper,data,ctx,sites):
    for site in sites:
        helper.prepare_one(site,ctx)
        p=helper.ledger(site); ledger=helper.load(p)
        if ledger.get('phase')!='CASE_VERIFIED_NOT_SUBMITTED': raise ValueError(site+': case verification incomplete')
        ledger.update(stage23_input_manifest=str(data[site]['manifest']),
                      stage23_input_manifest_sha256=helper.digest(data[site]['manifest']),
                      met_review='UNMODIFIED_FLAGGED_EXPLORATORY' if site in FLAGGED else 'NO_QC0_TEMPERATURE_SUSPECTS_IN_PRIOR_SCREEN',
                      candidate_repairs_applied=False)
        helper.save(p,ledger)
        print('DIRECT AD400 PREPARED',site,'no jobs submitted',flush=True)


def submit(helper,data,sites):
    stack=helper.stack_guard()
    for site in sites:
        obj=helper.load(helper.ledger(site)); item=data[site]
        if obj.get('phase')!='CASE_VERIFIED_NOT_SUBMITTED': raise ValueError(site+': no verified, unsubmitted direct AD400 ledger')
        if helper.digest(item['manifest'])!=obj.get('stage23_input_manifest_sha256'): raise ValueError(site+': Stage23 manifest changed')
        if helper.digest(Path(helper.xq(helper.TEMPLATE,'EXEROOT'))/'cesm.exe')!=obj['executable_sha256']: raise ValueError(site+': executable changed')
        expected=helper.xml_settings(site,item['surface'],float(obj['co2_ppmv']))
        helper.validate_case(site,item['surface'],item['files'],Path(obj['fates_paramfile']),float(obj['co2_ppmv']),expected)
        if site in FLAGGED: print('WARNING',site,'EXPLORATORY: UNMODIFIED FORCING HAS UNRESOLVED MET FLAGS',flush=True)
        helper.submit_one(site,stack)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('action',choices=('check','prepare','submit','status'))
    p.add_argument('--run',required=True,type=Path); p.add_argument('--helper',required=True,type=Path)
    p.add_argument('--stage26',required=True,type=Path); p.add_argument('--co2-csv',required=True,type=Path)
    p.add_argument('--sites',nargs='+',choices=SITES); p.add_argument('--unmodified-flagged-inputs',action='store_true')
    a=p.parse_args(); sites=selected(a.sites,a.unmodified_flagged_inputs)
    stage=load_module(a.stage26,'six_stage26'); helper=stage.load_helper(a.helper)
    root,data=stage.inputs(a.run); setup(stage,helper,root,data)
    if a.action in ('check','prepare'):
        ctx=preflight(helper,data,a.co2_csv,sites)
        if a.action=='prepare': prepare(helper,data,ctx,sites)
    elif a.action=='submit': submit(helper,data,sites)
    else: helper.status(sites)


if __name__=='__main__': main()
