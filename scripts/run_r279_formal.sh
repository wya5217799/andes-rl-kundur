#!/usr/bin/env bash
set -euo pipefail
cd /mnt/e/Projects/andes-rl-kundur
PYTHON_BIN="${PYTHON_BIN:-/home/wya/andes_venv/bin/python}"
SEAL_REL="memory/rounds/R279/formal_seal.json"
OUT_REL="results/r279_formal_evaluation"
SHARD_COUNT=8

if [[ ! -x "$PYTHON_BIN" ]]; then
  echo "Missing executable real-ANDES interpreter: $PYTHON_BIN" >&2
  exit 2
fi
if [[ ! -f "results/r279_fresh_bank/screen_summary.json" ]]; then
  echo "Fresh-bank screen must finish before formal sealing." >&2
  exit 3
fi
classification="$($PYTHON_BIN -c 'import json; print(json.load(open("results/r279_fresh_bank/screen_summary.json"))["decision"]["classification"])')"
if [[ "$classification" != "PASS" ]]; then
  echo "Fresh-bank screen classification is $classification; formal run forbidden." >&2
  exit 4
fi
"$PYTHON_BIN" memory/tools/round_preflight.py R279
if [[ ! -f "$SEAL_REL" ]]; then
  "$PYTHON_BIN" scripts/run_r279_formal.py prepare
fi
SEAL_HASH="$(awk '{print $1}' "${SEAL_REL}.sha256")"
if [[ ${#SEAL_HASH} -ne 64 ]]; then
  echo "Invalid formal seal hash: $SEAL_HASH" >&2
  exit 5
fi
mkdir -p "${OUT_REL}/logs"
stamp="$(date -u +%Y%m%dT%H%M%SZ)"
pids=()
for shard in $(seq 0 $((SHARD_COUNT - 1))); do
  timeout --signal=TERM 180m "$PYTHON_BIN" scripts/run_r279_formal.py run \
    --expected-manifest-sha256 "$SEAL_HASH" --shard-index "$shard" --shard-count "$SHARD_COUNT" \
    >"${OUT_REL}/logs/${stamp}_formal_shard${shard}.stdout.log" \
    2>"${OUT_REL}/logs/${stamp}_formal_shard${shard}.stderr.log" &
  pids+=("$!")
  echo "Started formal shard=$shard pid=${pids[-1]}"
done
failed=0
for shard in $(seq 0 $((SHARD_COUNT - 1))); do
  if ! wait "${pids[$shard]}"; then
    echo "Formal shard $shard failed; all partial traces retained, no automatic retry." >&2
    failed=1
  fi
done
if [[ "$failed" -ne 0 ]]; then
  exit 6
fi
if [[ -f "${OUT_REL}/formal_summary.json" ]]; then
  echo "Formal matrix already analysed; refusing to overwrite it."
else
  "$PYTHON_BIN" scripts/run_r279_formal.py analyse --expected-manifest-sha256 "$SEAL_HASH"
fi
echo "R279 eight-arm formal evaluation complete."
