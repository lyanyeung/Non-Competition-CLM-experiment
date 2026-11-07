#!/bin/bash
# Waits for the running script-25 ad-run (CA-TP1, CA-TP3, CA-Cbo, CA-Man), then builds + submits the US-Bar
# _NLFP AD (its default-parameter run is kept for the version comparison), then starts auto-normal for all five.
# Run as a FILE (not bash -c): script 25 refuses to start when another process command line names it.
#   setsid nohup bash b01_chain.sh > $HOME/CLM_FATES_PLOTS/b01_chain.log 2>&1 < /dev/null &
cd "$(dirname "$0")" || exit 1
PY=${PY:-$HOME/.conda/envs/clm_fates_env/bin/python}
echo "#### $(date -u '+%F %H:%M UTC') waiting for the running ad-run"
while pgrep -u "$USER" -f "[2]5_ameriflux_b01_remaining.py ad-run" >/dev/null; do sleep 60; done
echo "#### $(date -u '+%F %H:%M UTC') US-Bar ad-run"
"$PY" -B 25_ameriflux_b01_remaining.py ad-run --sites US-Bar
echo "#### $(date -u '+%F %H:%M UTC') auto-normal (all five)"
exec "$PY" -B 25_ameriflux_b01_remaining.py auto-normal
