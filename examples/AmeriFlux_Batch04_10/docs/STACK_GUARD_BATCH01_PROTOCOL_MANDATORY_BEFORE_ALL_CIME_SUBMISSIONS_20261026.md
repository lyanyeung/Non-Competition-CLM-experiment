# AmeriFlux Batch04 — mandatory stack and Slurm resource propagation guard, inherited from Batch01

**Added 26 October 2026 after the operator's confirmed SYVH9/SYVH12 10-site science-source and shared-PFT surface audits.** The operator now has ten SHA-verified initial-PFT research surfaces and a twenty-arm AD400→Normal400 **plan**, but **zero built/submitted CIME cases**. Stack guard is to be enforced by the FUTURE live model submission controller, not by the source/surface builder.

## Confirmed Batch01 technical precedent and this new project

The existing [AmeriFlux Batch01 Stage21 controller](../../AmeriFlux_Batch01_10/scripts/21_laneA_AD400_NORMAL400_controller.py) has `MIN_STACK_KB=65536`, validates RLIMIT_STACK with `resource.getrlimit`, aborts if the soft stack is below that and records `stack_limit_at_submit` in **attempt-before-submit** ledgers. This was introduced after stack-limited IRIDIS6 submit sessions led to Prigent/ESMF mesh runtime problems; the corrected CA-TP4 model then required separate scientific/PTS audits too. **Never claim every Prigent crash is always a stack crash**: passing stack is necessary but not proof of successful FATES simulation.

New [Batch04 common stack guard](../scripts/b04_stack_guard.py) enforces:
- Minimum **65,536 KiB (64 MiB) soft** RLIMIT_STACK in the **real CIME submission process**. Prefer **300,000 KiB** if current stack is too small and hard limit allows it. Raising only, never lower an already larger limit or `unlimited`.
- Independently verify actual Slurm `scontrol show config` reports `PropagateResourceLimits=ALL` or a list explicitly containing `STACK`. If missing, unknown or `NONE`, **do not submit**; check cluster policy rather than assuming the login-node limit reaches compute ranks.
- `require_for_submission(site=...,phase=...,may_raise=True)` **must be called in the same Python submitter process directly before every** `./case.submit --skip-preview-namelist`: AD5, AD395, NORMAL5 and NORMAL395, each resubmit/recovery, and all 20 paired-site arms. It returns a structured resource record to be saved in a non-overwriting, **attempt-before-submit ledger**. It never calls Slurm itself.
- `--self-test` is **pure synthetic** and may safely run any day; `--check` inspects the **current** inherited shell/Python stack and actual Slurm system; `--ensure` raises only that **current Python process**, which is **not inherited by the parent shell**. Running `--ensure` alone then starting `./case.submit` in a new shell is **not protected** and explicitly unsupported.
- These are resource checks **in addition to** source meteorology/forcing, UTC DATM, site-specific ZBOT, ten-layer soil/ORGANIC, FATES map, active case PTS/domain, archived restart/stack guard, and one-time job state checks. A stack PASS **does not** release a blocked scientific case or start AD5.

## Safe interactive read-only check on IRIDIS6 now (no Slurm jobs)

```bash
conda activate clm_fates_env
BASE="$HOME/ameriflux_batch04_fates_pair_setup"
mkdir -p "$BASE"
RAW="https://raw.githubusercontent.com/lyanyeung/Non-Competition-CLM-experiment"
COMMIT="e0d93de4ccf7279ea8e80a0d9efe2cd955fa174d"
SCRIPT="$BASE/b04_stack_guard.py"
curl -fLsS --retry 3 "$RAW/$COMMIT/examples/AmeriFlux_Batch04_10/scripts/b04_stack_guard.py" -o "$SCRIPT"
python3 -B -m py_compile "$SCRIPT"
python3 -B "$SCRIPT" --self-test
ulimit -s
python3 -B "$SCRIPT" --check
```

If `--check` fails only because current login shell stack is under 65536KiB, this is **a resource preflight HOLD**, not a reason to delete or regenerate any ten-site PFT surface.

Before an actual model submitter is later built and run, launch in a NEW subshell so the parent/other tasks remain unaffected:
```bash
(
  set -euo pipefail
  CURRENT="$(ulimit -s)"
  if [[ "$CURRENT" != "unlimited" && "$CURRENT" -lt 65536 ]]; then
    ulimit -s unlimited 2>/dev/null ||
    ulimit -s 300000 2>/dev/null ||
    ulimit -s 65536 2>/dev/null ||
    { echo "HOLD: cannot raise stack to 65536KiB" >&2; exit 1; }
  fi
  python3 -B "$HOME/ameriflux_batch04_fates_pair_setup/b04_stack_guard.py" --check
  # STOP HERE until scientifically approved CIME cases and a submission
  # controller importing require_for_submission() actually exist.
)
```

**Scientific state as of creation:** the paired 20-arm JSON has `submission_resource_guards` policy on every arm and `spinup_authorized=False`. Stage00 setup now downloads and self-tests the resource guard, but does NOT submit any job.

## Future live submitter integration contract — MUST be followed, not yet built

```python
# Only inside a future scientifically approved 20-arm CIME controller.
from b04_stack_guard import require_for_submission

# Validate actual site and active CIME scientific case, PFT map,
# time-centered DATM, sensor ZBOT, PTS/domain and no past job attempts FIRST.
# Save a non-overwriting immutable ATTEMPT ledger BEFORE running case.submit.
proof = require_for_submission(site=site, phase=phase, may_raise=True)
# Write proof into that attempt record (same interpreter/session).
# Run subprocess.run([case / "case.submit", "--skip-preview-namelist"],
#                   cwd=case, check=True) only while proof remains valid.
```

**Do not reuse the European Batch03 or AmeriFlux Batch01 case.submit controller against these new sites**; those controllers contain case-specific restart paths, PTS, source NetCDF and phase ledger references that are not interchangeable with Batch04.
