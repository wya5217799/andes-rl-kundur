#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON=/home/wya/andes_venv/bin/python
SEAL="$ROOT/memory/rounds/R293/classical_development_seal.json"
SIDECAR="$SEAL.sha256"
OUT="$ROOT/results/r293_classical_development"
LOGS="$OUT/logs"
STATUS="$OUT/status"

mkdir -p "$LOGS" "$STATUS"
if [[ -e "$STATUS/complete" || -e "$STATUS/failed" ]]; then
  echo "R293 classical development already has a terminal status" >&2
  exit 2
fi
expected="$(awk 'NR==1 {print $1}' "$SIDECAR")"
if [[ -z "$expected" ]]; then
  echo "missing R293 classical development seal hash" >&2
  exit 2
fi

pids=()
for shard in 0 1 2; do
  "$PYTHON" "$ROOT/scripts/andes_scratch.py" \
    "$ROOT/scripts/run_r293_classical_development.py" run \
    --expected-manifest-sha256 "$expected" \
    --shard-index "$shard" --shard-count 3 \
    >"$LOGS/shard_${shard}.log" 2>&1 &
  pids+=("$!")
done

failed=0
for pid in "${pids[@]}"; do
  if ! wait "$pid"; then
    failed=1
  fi
done
if [[ "$failed" -ne 0 ]]; then
  : >"$STATUS/failed"
  exit 1
fi

"$PYTHON" "$ROOT/scripts/andes_scratch.py" \
  "$ROOT/scripts/run_r293_classical_development.py" analyse \
  --expected-manifest-sha256 "$expected" \
  >"$LOGS/analyse.log" 2>&1
: >"$STATUS/complete"
