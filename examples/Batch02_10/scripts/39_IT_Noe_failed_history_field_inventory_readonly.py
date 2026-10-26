#!/usr/bin/env python3
"""Stage39: EXACT failed IT-Noe 4733521 history-field error triage, read only.

htapes_fieldlist "GPP in fincl(4) for history tape 1" is item 4 of
hist_fincl1, NOT hist_fincl4. Inventory the effective lnd_in requested
hist_finclN and compare against 4733521 lnd.log's registered history fields.
No original/new CIME changes, no Slurm and no forcing edits.
"""
from __future__ import annotations
import argparse,hashlib,re
from pathlib import Path

B=Path("/iridisfs/scratch/ly3n24/CLM_FATES")
CASE=B/"cases/IT-Noe_B02_FIXNC_AD400_BARE34_SHRUB66_AD5"
RUN=Path("/scratch/ly3n24/CTSM_FATES_OUTPUTS")/CASE.name/"run"
JOB="4733521"
REGISTER=re.compile(r"(?m)^\s*\d+\s+([A-Za-z][A-Za-z0-9_]+)\s{2,}")
ASSIGN=re.compile(r"(?m)^\s*([a-z][a-z_0-9]*)\s*=",re.I)
QUOTE=re.compile(r"['\"]([^'\"]+)['\"]")
def sha(p):
 h=hashlib.sha256()
 with p.open("rb") as f:
  for c in iter(lambda:f.read(1<<20),b""):h.update(c)
 return h.hexdigest()
def parse_history(namelist):
 lines=namelist.splitlines()
 items=[]
 key=None;value=[]
 for line in lines:
  a=ASSIGN.match(line)
  if a:
   if key:items.append((key,"\n".join(value)))
   key=a.group(1).lower()
   value=[line[a.end():]]
  elif key:
   value.append(line)
 if key:items.append((key,"\n".join(value)))
 return [(key,[z.strip() for z in QUOTE.findall(v) if z.strip()])
         for key,v in items if re.fullmatch(r"hist_fincl\d+",key)]
def listfields(log):
 fields=set()
 for name in REGISTER.findall(log):
  if not name[0].isdigit() and (name.isupper() or name.startswith("FATES")):
   fields.add(name.upper())
 return fields
def run():
 doc=CASE/"CaseDocs/lnd_in";eff=RUN/"lnd_in"
 assert doc.is_file() and eff.is_file(),"IT-Noe original effective land namelist unavailable"
 assert sha(doc)==sha(eff),"CaseDocs and effective failed-run lnd_in SHA differ"
 logs=sorted(RUN.glob("lnd.log."+JOB+".*"))
 assert len(logs)==1,"Expected one exact failed-run lnd.log.4733521.*; found "+str(logs)
 log=logs[0].read_text(errors="replace")
 assert "htapes_fieldlist ERROR: GPP in fincl(" in log and "histFileMod.F90" in log,"Not exact Stage38 history output error"
 history=parse_history(doc.read_text(errors="replace"))
 assert history,"No hist_finclN found in failed effective lnd_in; parser needs review"
 fields=listfields(log)
 assert len(fields)>100,"History field registry not confidently parsed; do not create case"
 print("STAGE39 CASE",CASE)
 print("STAGE39 LOG",logs[0],"SHA",sha(logs[0]))
 print("STAGE39 EFFECTIVE_NAMELIST_SHA",sha(doc))
 print("STAGE39 REGISTERED_FIELDS",len(fields))
 print("STAGE39 EXACT ERROR: history tape 1 item 4 GPP; NOT the fourth tape")
 unresolved=[]
 for key,vals in history:
  tape=int(key.removeprefix("hist_fincl"))
  print("STAGE39 REQUESTED",key,"COUNT",len(vals))
  for idx,raw in enumerate(vals,1):
   field=raw.split(":",1)[0].strip().upper()
   ok=field in fields
   print("STAGE39 FIELD",key,idx,raw,
         "REGISTERED" if ok else "UNREGISTERED_CANDIDATE")
   if not ok:unresolved.append((tape,idx,raw))
 print("STAGE39 UNREGISTERED_TOTAL",len(unresolved),unresolved)
 print("STAGE39 GPP REGISTERED","GPP" in fields)
 print("STAGE39 POSSIBLE FATES NAMES",
       sorted(x for x in fields if "GPP" in x or x in ("NEE","NEP","NPP","GPP"))[:75])
 print("STAGE39 NO CHANGES; no Slurm; do not rerun Stage15.")
def main():
 ap=argparse.ArgumentParser(description=__doc__)
 g=ap.add_mutually_exclusive_group(required=True)
 g.add_argument("--self-test",action="store_true")
 g.add_argument("--audit",action="store_true")
 args=ap.parse_args()
 if args.self_test:
  a=parse_history("hist_fincl1 = 'TLAI', 'FATES_GPP_PF', 'NEE', 'GPP'\nhist_fincl2 = 'FSH'")
  assert a[0][1][3]=="GPP" and a[1][0]=="hist_fincl2"
  assert listfields("  1234 FATES_GPP_PF          kg m-2 s-1\n  3 NEE        kg m-2 s-1")=={"FATES_GPP_PF","NEE"}
  assert "GPP" not in listfields("  1234 FATES_GPP_PF          kg m-2 s-1")
  print("STAGE39 SELF-TEST PASS | finite tape/item inventory | NO WRITES")
 else:run()
if __name__=="__main__":main()
