#!/usr/bin/env bash
# Cancel ONLY the superseded NL-Loo PRE50 job-chain. Never touches other sites.
# NO restart, forcing, history or case files are removed.
set -euo pipefail
EXPECTED="CANCEL_OLD_NL_LOO_PRE50_ONLY"
if [[ "${1:-}" != "--confirm" || "${2:-}" != "$EXPECTED" ]]; then
  echo "Usage: bash $0 --confirm $EXPECTED" >&2; exit 2
fi
if [[ "${USER}" != "ly3n24" ]]; then echo "Wrong cluster account" >&2; exit 3; fi
for round in 1 2 3 4; do
  mapfile -t jobs < <(
    squeue -u "$USER" -h -o '%i|%j' |
      awk -F'|' '$2=="run.NL-Loo_OBSPFT_NC_PRE50" || $2=="st_archive.NL-Loo_OBSPFT_NC_PRE50" {print $1}'
  )
  if (( ${#jobs[@]} == 0 )); then
    echo "No OLD NL-Loo PRE50 jobs found on sweep $round."
    break
  fi
  printf 'Cancelling only OLD NL-Loo PRE50 job IDs: %s\n' "${jobs[*]}"
  for j in "${jobs[@]}"; do
    [[ "$j" =~ ^[0-9]+$ ]] || { echo "Unexpected job id $j"; exit 4; }
    scancel "$j" || true
  done
  sleep 2
done
echo "=== Remaining OLD PRE50 model/archive tasks (must be empty) ==="
squeue -u "$USER" -h -o '%i|%j|%T' |
  awk -F'|' '$2=="run.NL-Loo_OBSPFT_NC_PRE50" || $2=="st_archive.NL-Loo_OBSPFT_NC_PRE50" {print}'
echo "=== Recent OLD PRE50 accounting ==="
sacct -n -X -S now-1day -u "$USER" --format=JobID,JobName,State,ExitCode -P |
  grep -F 'NL-Loo_OBSPFT_NC_PRE50' | tail -20 || true
echo "Finished. Case and archives unchanged. Confirm zero queue entries before starting new experiment."
