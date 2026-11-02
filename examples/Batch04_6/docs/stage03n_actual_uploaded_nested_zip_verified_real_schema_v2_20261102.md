# Batch04 IT-TrF Stage03N actual uploaded ZIP verified; nested ICOS outer bundle and real CSV schema (2026-11-02)

## Root cause of operator's SHA check failure — confirmed by actual uploaded bytes

User supplied a file named `ICOSETC_IT-TrF_METEO_L2(1).zip` (the **outer ICOS multi-file licence bundle**). It is **16,792,611 bytes** with SHA256 `d41b915371ddb31df7e08ecb95970714369f24480596ff69018e5fa4670603be`. Valid ZIP, `testzip()=None`/CRC pass. Contents:

1. Inner `ICOSETC_IT-TrF_METEO_L2.zip`, **16,713,915 bytes**, SHA256 **`9b037df04c46478b8f9da50a8b9996a084a5b2aadabfc11c9b8caabdd940797f`**, exact match to [ICOS original 2025 object](https://meta.icos-cp.eu/objects/mwN98ExGR4uPnaUKi5mWoISl)
2. `!TOC.csv`, including original product PID `11676/mwN98ExGR4uPnaUKi5mWoISl`
3. `!LICENCE.pdf` (a copy of the ICOS licence)

The embedded **inner** ZIP is also CRC-valid and contains one **53,923,697-byte** original `ICOSETC_IT-TrF_METEO_L2.csv`. Therefore the SHA mismatch at IRIDIS6 is completely explained by checking the outer container against the inner data-object SHA. The transfer is **not** shown damaged; don't bypass SHA, don't repeatedly download, and don't mislabel outer as original inner ZIP. Both ZIPs must remain immutable and only the inner original data object passed to Stage03N `--archive`.

### Safe IRIDIS6 unwrapping (never overwrite the transferred outer ZIP)

If the outer bundle was transferred as `$HOME/ICOS_Batch04_neighbor_reference/ICOSETC_IT-TrF_METEO_L2.zip` despite being an outer 16,792,611-byte wrapper, run:

```bash
python3 - <<'PY'
from pathlib import Path
from zipfile import ZipFile
from hashlib import sha256
from shutil import copyfileobj
home=Path.home()/"ICOS_Batch04_neighbor_reference"
outer=home/"ICOSETC_IT-TrF_METEO_L2.zip"  # operator-supplied OUTER bundle
dst=home/"original_icos_object"/"ICOSETC_IT-TrF_METEO_L2.zip"
outer_expected="d41b915371ddb31df7e08ecb95970714369f24480596ff69018e5fa4670603be"
inner_expected="9b037df04c46478b8f9da50a8b9996a084a5b2aadabfc11c9b8caabdd940797f"
def digest(p):
 h=sha256()
 with p.open("rb") as f:
  for block in iter(lambda:f.read(1024*1024),b""):h.update(block)
 return h.hexdigest()
assert outer.is_file() and digest(outer)==outer_expected, "Outer differs from inspected user upload; do not overwrite"
with ZipFile(outer) as z:
 assert z.testzip() is None
 assert "ICOSETC_IT-TrF_METEO_L2.zip" in z.namelist()
 dst.parent.mkdir(parents=True,exist_ok=True)
 with z.open("ICOSETC_IT-TrF_METEO_L2.zip") as src:
  if dst.exists():
   assert digest(dst)==inner_expected, "Existing inner file differs; do not overwrite"
  else:
   with dst.open("xb") as out:copyfileobj(src,out)
assert dst.stat().st_size==16713915 and digest(dst)==inner_expected
with ZipFile(dst) as z:assert z.testzip() is None
print("OFFICIAL_INNER_SHA256_PASS",dst)
PY
```

The file name on IRIDIS might differ (especially if Windows retained `(1)`); adjust `outer=` to the actual exact outer path after looking at `ls -lb`. Under no circumstance rename an outer wrapper and claim it is the inner object.

## Actual original CSV schema, not guesswork

The user-provided inner original CSV header is:

```
TIMESTAMP_START,TIMESTAMP_END,ALB,D_SNOW,G,G_1,G_2,G_3,LW_IN,LW_OUT,NETRAD,P,PA,PPFD_BC_IN_1,PPFD_BC_IN_1_N,PPFD_BC_IN_1_SD,PPFD_IN,PPFD_OUT,RH,SW_IN,SW_OUT,SWC_1,SWC_2,SWC_3,T_CANOPY,TA,TS_1,TS_2,TS_3,WD,WS
```

**Not** `TIMESTAMP,TIMESTAMP_END,TA` as the original Stage03N anticipated from ICOS portal *display* fields. Every original row sampled in 2025-11-12..20 has a **30-minute** `TIMESTAMP_START`→`TIMESTAMP_END` interval difference. This is an interval duration, **not proof of UTC–local offset**; the exact source timestamp standard must be established independently before comparison with IT-Tor. The original CSV has **NO per-row `TA_QC` or TA quality flag column**. Portal "good flag values 0,1" should not be interpreted as a provided per-row FLUXNET `*_F_QC` flag or immediate measured-sensor certification.

### Real IT-TrF data availability (literal source labels; no cross-site clock alignment or scientific comparison)

2025-11-12 00:00 through 2025-11-20 23:30: **432 HH**, **288 valid TA**, **144 missing (-9999)**.

| Previously ranked IT-Tor MDS source-label interval | IT-TrF rows with same unaligned literal label | Finite TA | Missing |
|---|---:|---:|---:|
| 2025-11-15 17:00 to 11-18 07:00 | 125 | **48** | **77** |
| 2025-11-13 17:30 to 11-14 07:00 | 28 | **28** | **0** |
| 2025-11-13 14:30 to 15:30 | 3 | **3** | **0** |

Missing whole days include Nov 15, Nov 16 and Nov 18 in the selected neighbour source window. The 48 valid values in the first priority interval occur during Nov 17, while the other 77 records are missing. This is a *source availability finding*, not a measured-temperature accuracy verdict. Need to inspect actual station sensor calibration/height/TA aggregation and clock convention before using any values to adjudicate IT-Tor QC1 vs packaged ERA.

## Script fix and next instructions

Original [Stage03N source inspector](../scripts/03n_IT_TrF_official_2025_L2_METEO_SHA_and_TA_time_preflight_READONLY.py) is updated *in place* to v2, preserving original ICOS ZIP SHA gate. It reads the actual `TIMESTAMP_START,TIMESTAMP_END,TA` columns, enforces 30-minute interval continuity in selected Nov12-20 2025, reports exact 432/288 and priority 125/48, 28/28, 3/3 when run on the verified inner data object. It flags lack of actual `TA_QC` field and incomplete time harmonization explicitly. Output remains PRIVATE on IRIDIS, original outer and inner ZIPs unchanged, and **no FLUXMET/Stage28/DATM NC, CIME/PFT/FATES/Slurm or QC1 replacement**.

The assistant's local inspection was performed directly on the user-supplied uploaded bytes. The corrected GitHub script itself still requires running its AST/self-test and real `--archive` on IRIDIS6; do not claim the patched script already ran there.

**Science HOLD:** real IT-Tor 156 QC1 priority half-hours with 98 strong MDS-versus-packaged-ERA negative differences are not independently proven erroneous. IT-TrF is a distinct larch forest station. IT-Tor ten-layer soil `ORGANIC=0` and other separate Batch04 science gates remain pending.
