#!/usr/bin/env bash
# Download only the second European/ICOS batch source inventory. No model jobs.
set -euo pipefail
B02_REPO_DIR="${B02_REPO_DIR:-$HOME/Non-Competition-CLM-experiment}"
B02_REF="${B02_REF:-main}"
if [[ ! "$B02_REF" =~ ^[A-Za-z0-9._-]+$ ]]; then
  echo "Invalid B02_REF; use a commit SHA, tag, or simple branch name." >&2
  exit 2
fi
B02_TMP="$(mktemp -d)"
trap 'rm -rf -- "$B02_TMP"' EXIT
cat > "$B02_TMP/SHA256SUMS" <<'SHA'
0e4e813e4d7f26d22df8d6ca64509dbda059e0f73b40a43eb0d5fe73d08160c9  data/batch02_10_sites.csv
3db4c4687204a30b6d6653ad4ac8b4f1f1f8e5e64f891889260c46ab838a7cdf  data/batch02_10_input_gates.csv
41dcc83db8db7746b0b678a6216e5a95345db82e0de7737bd15d2155abbbac48  examples/Batch02_10/scripts/01_audit_batch02_inputs_readonly.py
SHA
while read -r B02_HASH B02_FILE; do
  mkdir -p "$B02_TMP/$(dirname "$B02_FILE")"
  curl -fLsS "https://raw.githubusercontent.com/lyanyeung/Non-Competition-CLM-experiment/$B02_REF/$B02_FILE"     -o "$B02_TMP/$B02_FILE"
done < "$B02_TMP/SHA256SUMS"
(cd "$B02_TMP" && sha256sum -c SHA256SUMS)
# All downloads must validate before updating any checkout source file.
while read -r B02_HASH B02_FILE; do
  mkdir -p "$B02_REPO_DIR/$(dirname "$B02_FILE")"
  if [[ -L "$B02_REPO_DIR/$B02_FILE" ]]; then
    echo "Refusing to replace symlink: $B02_REPO_DIR/$B02_FILE" >&2
    exit 2
  fi
  install -m 644 "$B02_TMP/$B02_FILE" "$B02_REPO_DIR/$B02_FILE"
done < "$B02_TMP/SHA256SUMS"
B02_SCRIPT="$B02_REPO_DIR/examples/Batch02_10/scripts/01_audit_batch02_inputs_readonly.py"
python3 -B "$B02_SCRIPT" self-test
B02_ARGS=()
if [[ -n "${B02_BASE:-}" ]]; then B02_ARGS+=(--base "$B02_BASE"); fi
if [[ -n "${B02_REPORT_ROOT:-}" ]]; then B02_ARGS+=(--report-root "$B02_REPORT_ROOT"); fi
B02_LOG="$(mktemp "${B02_REPORT_ROOT:-$HOME}/Batch02_10_audit_$(date -u +%Y%m%dT%H%M%SZ)_XXXXXX.log")"
python3 -B "$B02_SCRIPT" audit "${B02_ARGS[@]}" 2>&1 | tee "$B02_LOG"
echo "CONSOLE_LOG=$B02_LOG"
