#!/usr/bin/env python3
"""Cancel ONLY the ten unwanted Batch04 FULL case chains; keep FIXNC.

--check is read-only. --apply batches exact-name FULL job IDs into scancel,
sets those FULL cases' RESUBMIT=0, then sweeps once more for racing chained
submissions. No FIXNC XML, ledger, job or model output is changed/deleted.
Only a final empty FULL queue plus all existing FULL RESUBMIT=0 is PASS.
"""
import argparse
from datetime import datetime, timezone
import getpass
import json
from pathlib import Path
import re
import subprocess
from uuid import uuid4

B = Path('/iridisfs/scratch/ly3n24/CLM_FATES')
EXP = B/'experiments/NonCompetitionObserved22/AmeriFlux_Batch04_10'
SITES = ('US-Rpf','US-SP1','US-SRG','US-SRM','US-Seg','US-Ses','US-Slt','US-Syv','US-Ton','US-Uaf')


def full_case(site):
    if site not in SITES:
        raise RuntimeError('Not a Batch04 site')
    return site+'_AMF_B04_FULL_AD400_BASETA_V1'


FULL_NAMES = {prefix+full_case(site) for site in SITES
              for prefix in ('run.','st_archive.','')}


def command(args,cwd=None,check=True):
    p = subprocess.run(list(map(str,args)),cwd=cwd,text=True,capture_output=True,timeout=90)
    if check and p.returncode:
        raise RuntimeError('Command failed '+repr(list(map(str,args)))+'\n'+p.stdout+p.stderr)
    return p


def parse_queue(text):
    records = []
    for line in text.splitlines():
        fields = [x.strip() for x in line.split('|')]
        if len(fields) != 3:
            raise RuntimeError('Unexpected squeue output: '+line)
        job,name,state = fields
        if not re.fullmatch(r'[0-9_+\[\],%\-]+',job):
            raise RuntimeError('Invalid Slurm job identifier '+job)
        records.append({'id':job,'name':name,'state':state})
    return records


def queue():
    p = command(['squeue','-u',getpass.getuser(),'-h','-o','%i|%.180j|%T'])
    return parse_queue(p.stdout)


def selected(records):
    return [r for r in records if r['name'] in FULL_NAMES]


def cancel(records):
    target = selected(records)
    if not target:
        return {'requested_ids':[],'returncode':0,'output':'No matching FULL jobs'}
    ids = sorted({r['id'] for r in target})
    # Single batch RPC, exact owner-selected job IDs, not a prefix/wildcard.
    p = command(['scancel',*ids],check=False)
    print('B04 FULL CANCEL REQUEST',','.join(ids),'returncode',p.returncode,flush=True)
    if p.stdout or p.stderr:
        print((p.stdout+p.stderr).strip(),flush=True)
    return {'requested_ids':ids,'returncode':p.returncode,'output':p.stdout+p.stderr}


def stop(apply):
    before = queue()
    record = {'mode':'apply' if apply else 'check','user':getpass.getuser(),
              'created_utc':datetime.now(timezone.utc).isoformat(),
              'FULL_before':selected(before),'FIXNC_mutated':False,'output_files_deleted':False}
    destination = None
    if apply:
        folder = EXP/'FULL_cancellation_records'
        folder.mkdir(parents=True,exist_ok=True)
        destination = folder/(datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'_'+uuid4().hex[:8]+'.json')
        with destination.open('x') as f:
            json.dump({**record,'status':'STOP_ATTEMPT_STARTED'},f,indent=2)
        record['first_cancel'] = cancel(before)
    states = []
    for site in SITES:
        path = B/'cases'/full_case(site)
        row = {'case':str(path)}
        if not (path/'xmlquery').is_file():
            row['state'] = 'FULL_CASE_MISSING'
        else:
            try:
                if apply:
                    command([path/'xmlchange','RESUBMIT=0'],cwd=path)
                row['RESUBMIT'] = command([path/'xmlquery','RESUBMIT','--value'],cwd=path).stdout.strip()
                row['state'] = 'AUTO_RESUBMIT_DISABLED' if row['RESUBMIT'] == '0' else 'AUTO_RESUBMIT_STILL_ENABLED'
            except Exception as e:
                row['state'] = 'XML_CHECK_FAILED'
                row['error'] = str(e)
        states.append(row)
        print('B04 FULL CASE',site,row['state'],flush=True)
    if apply:
        record['second_cancel'] = cancel(queue())
    after = queue() if apply else before
    remaining = selected(after)
    record.update(cases=states,FULL_remaining=remaining,
                  FIXNC_queue_after=[r for r in after if '_AMF_B04_FIXNC_' in r['name']])
    disabled = all(r['state'] in ('AUTO_RESUBMIT_DISABLED','FULL_CASE_MISSING') for r in states)
    ok = not remaining and disabled
    record['status'] = 'FULL_STOPPED_FIXNC_PRESERVED' if ok else 'FULL_STOP_NOT_YET_VERIFIED'
    if destination:
        destination.write_text(json.dumps(record,indent=2)+'\n')
        print('B04 FULL STOP RECEIPT',destination,flush=True)
    for row in remaining:
        print('B04 FULL STILL IN QUEUE',row['id'],row['name'],row['state'],flush=True)
    for row in record['FIXNC_queue_after']:
        print('B04 RETAINED FIXNC QUEUE',row['id'],row['name'],row['state'],flush=True)
    print('B04 STOP SUMMARY',record['status'],'FULL remaining',len(remaining),
          'FIXNC queued',len(record['FIXNC_queue_after']),flush=True)
    return 0 if ok else 2


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument('--check',action='store_true')
    mode.add_argument('--apply',action='store_true')
    args = ap.parse_args()
    raise SystemExit(stop(args.apply))


if __name__ == '__main__':
    main()
