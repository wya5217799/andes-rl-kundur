#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON=/home/wya/andes_venv/bin/python
SEAL="$ROOT/memory/rounds/R293/fresh_bank_screen_seal.json"
OUT="$ROOT/results/r293_fresh_bank"
LOGS="$OUT/logs"
STATUS="$OUT/status"
mkdir -p "$LOGS" "$STATUS"
if [[ -e "$STATUS/complete" || -e "$STATUS/failed" ]]; then
  echo "R293 fresh-bank screen already has terminal status" >&2
  exit 2
fi
expected="$(awk 'NR==1 {print $1}' "$SEAL.sha256")"
if [[ -z "$expected" ]]; then
  echo "missing R293 fresh-bank seal hash" >&2
  exit 2
fi

pids=()
for shard in 0 1 2; do
  "$PYTHON" "$ROOT/scripts/andes_scratch.py" \
    "$ROOT/scripts/run_r293_fresh_bank.py" run \
    --expected-manifest-sha256 "$expected" \
    --shard-index "$shard" --shard-count 3 \
    >"$LOGS/shard_${shard}.log" 2>&1 &
  pids+=("$!")
done
failed=0
for pid in "${pids[@]}"; do
  if ! wait "$pid"; then failed=1; fi
done
if [[ "$failed" -ne 0 ]]; then
  : >"$STATUS/failed"
  exit 1
fi
"$PYTHON" "$ROOT/scripts/andes_scratch.py" \
  "$ROOT/scripts/run_r293_fresh_bank.py" analyse \
  --expected-manifest-sha256 "$expected" \
  >"$LOGS/analyse.log" 2>&1
: >"$STATUS/complete"
