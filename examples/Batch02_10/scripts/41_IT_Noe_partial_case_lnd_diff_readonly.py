#!/usr/bin/env python3
"""Stage41: READ-ONLY forensic diff after IT-Noe Stage40 partial preparation.

Do not rerun Stage40 --prepare; do not run Stage40 --start.
Compares SHA-pinned old effective lnd_in versus new CaseDocs/RUNDIR lnd_in,
shows exact differential EXCEPT intended hist_fincl1 field replacement,
then prints all other changed Fortran namelist assignments.
No directories, files, CIME XML, Slurm or receipt writes.
"""
from __future__ import annotations
import argparse,difflib,hashlib,json,re
from pathlib import Path

B=Path("/iridisfs/scratch/ly3n24/CLM_FATES")
E=B/"experiments/NonCompetitionObserved22/Batch02_10"
OLD=B/"cases/IT-Noe_B02_FIXNC_AD400_BARE34_SHRUB66_AD5"
NEW=B/"cases/IT-Noe_B02_FIXNC_GPPNPP_HISTFIX_AD400"
OLD_NML=OLD/"CaseDocs/lnd_in"
NEW_NML=NEW/"CaseDocs/lnd_in"
RUN=Path("/scratch/ly3n24/CTSM_FATES_OUTPUTS")/NEW.name/"run"
NEW_RUN=RUN/"lnd_in"
REC=E/"stage40_IT_Noe_GPPNPP_histfix_AD400/prepare_attempt.json"
SUBMIT=E/"stage40_IT_Noe_GPPNPP_histfix_AD400/submission_attempt.json"
OLD_SHA="a270910c91f55cb492d417109b034a39a1d05ba84c0109434b1c5db7258aeea6"
BEFORE=("TOTSOMC","TOTSOMN","TLAI","GPP","NPP","TWS","H2OSNO")
AFTER=("TOTSOMC","TOTSOMN","TLAI","FATES_GPP","FATES_NPP","TWS","H2OSNO")
TAPE=re.compile(r"(?ims)^[ \t]*hist_fincl1[ \t]*=[ \t]*(.*?)(?=^[ \t]*[A-Za-z_]\w*[ \t]*=|^[ \t]*/[ \t]*$|\Z)")
VAR=re.compile(r"(?m)^[ \t]*([A-Za-z_]\w*)[ \t]*=")
QUOTE=re.compile(r"['\"]([^'\"]+)['\"]")
def require(ok,msg):
 if not ok:raise RuntimeError(str(msg))
def digest(path):
 h=hashlib.sha256()
 with path.open("rb") as f:
  for block in iter(lambda:f.read(1048576),b""):h.update(block)
 return h.hexdigest()
def isolate_tape(txt):
 hits=list(TAPE.finditer(txt))
 require(len(hits)==1,"Expected exactly one hist_fincl1")
 m=hits[0]
 vals=tuple(QUOTE.findall(m.group(1)))
 return vals,txt[:m.start()]+"__REMOVED_ONLY_HIST_FINCL1__\n"+txt[m.end():]
def assignments(txt):
 # Full assignment *sections*, to show unchanged and changed exact values,
 # without discarding possible continuation lines.
 entries=list(VAR.finditer(txt))
 result={}
 for i,mm in enumerate(entries):
  key=mm.group(1).lower()
  chunk=txt[mm.end():entries[i+1].start()] if i+1<len(entries) else txt[mm.end():]
  result.setdefault(key,[]).append(chunk.strip())
 return result
def audit():
 require(OLD_NML.is_file() and NEW_NML.is_file() and NEW_RUN.is_file(),
         "Original or partial new effective lnd_in missing; inspect partial case")
 require(digest(OLD_NML)==OLD_SHA,"Original Stage39 effective lnd_in SHA changed")
 require(REC.is_file(),"Stage40 preparation receipt missing")
 try:r=json.loads(REC.read_text())
 except (OSError,ValueError) as e:raise RuntimeError("Stage40 receipt unreadable: "+str(e))
 require(r.get("phase")=="PREPARATION_ATTEMPT_UNCERTAIN",
         "Stage40 receipt phase unexpected: "+str(r.get("phase")))
 require(not SUBMIT.exists(),
         "New Stage40 submission attempt already exists; DO NOT proceed")
 old=OLD_NML.read_text()
 case=NEW_NML.read_text()
 run=NEW_RUN.read_text()
 before,ox=isolate_tape(old)
 after,cx=isolate_tape(case)
 rr,rx=isolate_tape(run)
 require(before==BEFORE and after==AFTER and rr==AFTER,
         "Unexpected history tape requests; STOP")
 print("STAGE41 READONLY PARTIAL CASE AUDIT")
 print("OLD_NML",OLD_NML,"SHA256",digest(OLD_NML),"SIZE",OLD_NML.stat().st_size)
 print("NEW_CASEDOCS",NEW_NML,"SHA256",digest(NEW_NML),"SIZE",NEW_NML.stat().st_size)
 print("NEW_RUNDIR",NEW_RUN,"SHA256",digest(NEW_RUN),"SIZE",NEW_RUN.stat().st_size)
 print("NEW_CASEDOCS_EQUALS_RUNDIR",digest(NEW_NML)==digest(NEW_RUN))
 print("SOURCE_HIST_FINCL1",list(before))
 print("NEW_HIST_FINCL1",list(after))
 print("PREPARE_RECEIPT_PHASE",r["phase"],"SUBMIT_RECEIPT_ABSENT",not SUBMIT.exists())
 print("BYTE_EXACT_OUTSIDE_HIST_FINCL1",ox==cx)
 print("NEW_RUNDIR_BYTE_EXACT_OUTSIDE_HIST_FINCL1",ox==rx)
 oldvars=assignments(ox);newvars=assignments(cx)
 changed=[]
 for key in sorted(set(oldvars)|set(newvars)):
  if oldvars.get(key)!=newvars.get(key):
   changed.append(key)
   print("CHANGED_EFFECTIVE_KEY",key,
         "OLD",repr(oldvars.get(key)),
         "NEW",repr(newvars.get(key)))
 print("CHANGED_KEYS_COUNT",len(changed),"KEYS",changed)
 print("UNIFIED_DIFF_OUTSIDE_HIST_FINCL1_BEGIN")
 diffs=list(difflib.unified_diff(ox.splitlines(),cx.splitlines(),
            fromfile="Stage39-original-effective-lnd_in",
            tofile="Stage40-partial-new-effective-lnd_in",
            n=3,lineterm=""))
 print("TOTAL_DIFF_LINES",len(diffs))
 for line in diffs[:240]:print(line[:500])
 if len(diffs)>240:print("DIFF_TRUNCATED",len(diffs)-240,"lines omitted")
 print("UNIFIED_DIFF_OUTSIDE_HIST_FINCL1_END")
 print("STAGE41 READONLY END; no correction, no Slurm.")
def main():
 parser=argparse.ArgumentParser(description=__doc__)
 g=parser.add_mutually_exclusive_group(required=True)
 g.add_argument("--self-test",action="store_true")
 g.add_argument("--audit",action="store_true")
 a=parser.parse_args()
 if a.self_test:
  old="&clm_inparm\n hist_fincl1 = 'TOTSOMC', 'TOTSOMN', 'TLAI', 'GPP', 'NPP', 'TWS', 'H2OSNO'\n hist_nhtfrq = 0\n/\n"
  new=old.replace("'GPP', 'NPP'","'FATES_GPP', 'FATES_NPP'")
  x,xx=isolate_tape(old); y,yy=isolate_tape(new)
  require(x==BEFORE and y==AFTER and xx==yy,"History tape isolation regression")
  r=assignments("&x\n a=3\n b=4\n/\n")
  require(list(r)==["a","b"],"Effective assignment parser regression")
  print("STAGE41 SELF-TEST PASS | exact tape comparison and differential, read-only")
 else:audit()
if __name__=="__main__":main()
