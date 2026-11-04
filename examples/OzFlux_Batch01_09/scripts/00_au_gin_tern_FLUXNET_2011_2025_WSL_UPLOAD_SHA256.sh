#!/usr/bin/env bash
# OzFlux AU-Gin updated TERN FLUXNET source upload from Windows WSL to IRIDIS6.
# Original ZIP preserved, old Gingin_L6.nc NOT overwritten, no model work.
set -euo pipefail

FILE="TERN_AU-Gin_FLUXNET_2011-2025_v1.3_r1.zip"
SOURCE="/mnt/d/Fluxes_Tower_Experiment/Ozflux/AU-Gin/$FILE"
REMOTE="ly3n24@iridis6.soton.ac.uk"
REMOTE_DIR="/iridisfs/scratch/ly3n24/CLM_FATES/sites/MY_EC_SITE/AU-Gin/forcing/raw/TERN_FLUXNET_2011_2025"
REMOTE_FILE="$REMOTE_DIR/$FILE"
REPORT="$HOME/ozflux_AU_Gin_TERN_2011_2025_stage00_sha256.txt"

die(){ echo "STOP: $*" >&2; exit 1; }
if (( $# > 1 )); then die "Usage: script [--preflight-only]"; fi
if (( $# == 1 )); then [[ "$1" == --preflight-only ]] || die "Unknown option"; fi
for x in sha256sum rsync ssh stat awk mktemp head od tr; do
    command -v "$x" >/dev/null || die "Missing command: $x"
done

[[ -d "$(dirname "$SOURCE")" && ! -L "$(dirname "$SOURCE")" ]] ||
    die "Expected original Windows WSL AU-Gin folder missing"
[[ -f "$SOURCE" && ! -L "$SOURCE" && -r "$SOURCE" && -s "$SOURCE" ]] ||
    die "Original AU-Gin ZIP absent/empty/symlink: $SOURCE"
[[ "$(head -c 2 "$SOURCE" | od -An -tx1 | tr -d ' \n')" == 504b ]] ||
    die "ZIP source does not start with PK magic"
SIZE="$(stat -c %s "$SOURCE")"
LOCAL_SHA="$(sha256sum "$SOURCE" | awk '{print $1}')"
[[ "$LOCAL_SHA" =~ ^[0-9a-f]{64}$ ]] || die "Invalid local SHA256"
echo "SOURCE=$SOURCE"
echo "BYTES=$SIZE"
echo "LOCAL_SHA256=$LOCAL_SHA"
echo "DESTINATION=$REMOTE:$REMOTE_FILE"
if (( $# == 1 )); then
    echo "STAGE00 PREFLIGHT PASS — no network, no transfer, no file changes"
    exit 0
fi

SOCKROOT="$(mktemp -d /tmp/ozflux-gin-ssh.XXXXXXXX)"
SOCKET="$SOCKROOT/master"
finish(){
    ssh -S "$SOCKET" -O exit "$REMOTE" >/dev/null 2>&1 || true
    rm -f -- "$SOCKET"
    rmdir -- "$SOCKROOT" 2>/dev/null || true
}
trap finish EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

echo "Opening one IRIDIS6 SSH connection; complete MFA if prompted."
ssh -MNf -S "$SOCKET" -o ControlMaster=yes -o ControlPersist=no \
    -o BatchMode=no -o NumberOfPasswordPrompts=1 \
    -o ServerAliveInterval=30 -o ServerAliveCountMax=3 \
    -o ConnectTimeout=30 "$REMOTE"

remote(){
    ssh -S "$SOCKET" -O check "$REMOTE" >/dev/null 2>&1 ||
        die "SSH master connection lost"
    ssh -S "$SOCKET" -o ControlMaster=no -o BatchMode=yes \
        -o ProxyCommand=false "$REMOTE" "$@"
}
remote "set -eu; command -v sha256sum >/dev/null; command -v rsync >/dev/null; mkdir -p '$REMOTE_DIR'; test -d '$REMOTE_DIR'; test ! -L '$REMOTE_DIR'; test ! -L '$REMOTE_FILE'"
EXISTS="$(remote "if test -f '$REMOTE_FILE'; then echo YES; elif test -e '$REMOTE_FILE'; then echo COLLISION; else echo NO; fi")"

if [[ "$EXISTS" == YES ]]; then
    REMOTE_SHA="$(remote "sha256sum '$REMOTE_FILE'" | awk '{print $1}')"
    REMOTE_SIZE="$(remote "stat -c %s '$REMOTE_FILE'")"
    [[ "$REMOTE_SHA" == "$LOCAL_SHA" && "$REMOTE_SIZE" == "$SIZE" ]] ||
        die "A different remote file already exists; no overwrite authorised"
    echo "REMOTE ZIP ALREADY PRESENT; SHA256 AND SIZE MATCH"
elif [[ "$EXISTS" == NO ]]; then
    RSYNC_RSH="ssh -S $SOCKET -o ControlMaster=no -o BatchMode=yes -o ProxyCommand=false"
    rsync -rtv --progress --ignore-existing --partial-dir=.rsync-partial \
        -e "$RSYNC_RSH" -- "$SOURCE" "$REMOTE:$REMOTE_FILE"
    REMOTE_SHA="$(remote "sha256sum '$REMOTE_FILE'" | awk '{print $1}')"
    REMOTE_SIZE="$(remote "stat -c %s '$REMOTE_FILE'")"
    [[ "$REMOTE_SHA" == "$LOCAL_SHA" && "$REMOTE_SIZE" == "$SIZE" ]] ||
        die "Transfer not verified; do not use remote ZIP"
    echo "TRANSFER SHA256 VERIFIED"
else
    die "Remote path collision: $REMOTE_FILE"
fi

{
    printf 'SITE\tAU-Gin\n'
    printf 'FILE\t%s\n' "$FILE"
    printf 'LOCAL_SOURCE\t%s\n' "$SOURCE"
    printf 'REMOTE_TARGET\t%s\n' "$REMOTE:$REMOTE_FILE"
    printf 'SIZE_BYTES\t%s\n' "$SIZE"
    printf 'SHA256\t%s\n' "$LOCAL_SHA"
    printf 'STATE\tTRANSFER_VERIFIED_NO_OVERWRITE\n'
    printf 'SCIENCE_QC\tHOLD_NOT_A_DATM_APPROVAL\n'
} > "$REPORT"

echo "SHA_RECEIPT=$REPORT"
echo "STAGE00 PASS: AU-Gin TERN ZIP 1/1 uploaded and verified"
echo "OLD Gingin_L6.nc UNTOUCHED; NO forcing, CIME, Surface or Slurm changes"
