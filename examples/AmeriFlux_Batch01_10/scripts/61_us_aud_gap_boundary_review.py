#!/usr/bin/env python3
"""Stage61: reuse the verified Stage60 audit with two expanded Q1 boundaries.

No forcing or case modifications. Stage60 writes only the requested private
CSV/JSON report. The QC and discrepancy thresholds remain review markers.
"""
import argparse, hashlib, importlib.util, sys
from pathlib import Path

PIN60='fb24f3d733eaaf06359c2d5a370f29548e943730'
WINDOWS=[
    ('STAGE61_APR_MORNING','2023-04-30 06:00:00','2023-04-30 13:30:00'),
    ('STAGE61_DEC19_BEFORE','2023-12-19 08:00:00','2023-12-19 14:30:00'),
    ('STAGE61_DEC18_AFTER','2023-12-18 19:00:00','2023-12-18 23:00:00'),
]


def main():
    p=argparse.ArgumentParser(description=__doc__,add_help=False)
    p.add_argument('--stage60',type=Path,required=True)
    a,other=p.parse_known_args(); path=a.stage60.resolve(strict=True); raw=path.read_bytes()
    digest=hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()
    if digest!=PIN60: raise ValueError('Stage60 source checksum differs')
    spec=importlib.util.spec_from_file_location('stage60_61',path); stage=importlib.util.module_from_spec(spec); spec.loader.exec_module(stage)
    if not callable(getattr(stage,'main',None)) or not callable(getattr(stage,'noaa',None)): raise ValueError('Stage60 API mismatch')
    is_test='--self-test' in other
    if not is_test:
        stage.WINDOWS=WINDOWS
        original_noaa=stage.noaa
        def skip_empty(year,times):
            if not times: return {},{'year':year,'status':'NO_TIMESTAMPS_NO_DOWNLOAD'}
            return original_noaa(year,times)
        stage.noaa=skip_empty
        print('STAGE61 READ ONLY | expanded 2023 April morning and December boundaries; no case or forcing modifications',flush=True)
    sys.argv=[str(path),*other]; stage.main()
    if is_test: print('STAGE61 SELF-TEST PASS | pinned Stage60 wrapper; NO WRITES',flush=True)
    else: print('STAGE61 COMPLETE | Stage60 output above covers only STAGE61 windows',flush=True)


if __name__=='__main__': main()
