#!/usr/bin/env bash
# One invocation, preflight -> strict first-five-year audit -> remaining 45 years.
# Will NOT submit AD200/postAD300 (unverified CIME AD transition). No deletion.
set -euo pipefail
cd "$HOME/Non-Competition-CLM-experiment"
python -m py_compile scripts/04_NL_Loo_spinup_45_200_300.py
python scripts/04_NL_Loo_spinup_45_200_300.py status
python scripts/04_NL_Loo_spinup_45_200_300.py audit5
python scripts/04_NL_Loo_spinup_45_200_300.py continue45 \
  --confirm CONTINUE_NL_LOO_PRE50_45Y
printf '\n45-YEAR CONTINUATION SUBMITTED if the prior command reported SUBMITTED.\n'
printf 'Remaining CIME segments resubmit automatically; AD200/postAD300 remain gated.\n'
