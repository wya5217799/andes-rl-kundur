#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON=/home/wya/andes_venv/bin/python
SEAL="$ROOT/memory/rounds/R293/training_seal.json"
OUT="$ROOT/results/r293_prior_residual_training"
LOGS="$OUT/logs"
STATUS="$OUT/status"
mkdir -p "$LOGS" "$STATUS"
if [[ -e "$STATUS/complete" || -e "$STATUS/failed" ]]; then
  echo "R293 training already has a terminal status" >&2
  exit 2
fi
expected="$(awk 'NR==1 {print $1}' "$SEAL.sha256")"
if [[ -z "$expected" ]]; then
  echo "missing R293 training seal hash" >&2
  exit 2
fi

tasks=(
  "central_prior 211" "distributed_prior 211"
  "central_prior 257" "distributed_prior 257"
  "central_prior 293" "distributed_prior 293"
  "central_prior 331" "distributed_prior 331"
  "central_prior 379" "distributed_prior 379"
)

run_worker() {
  local shard="$1"
  local index architecture seed
  for index in "${!tasks[@]}"; do
    if (( index % 3 != shard )); then
      continue
    fi
    read -r architecture seed <<<"${tasks[$index]}"
    "$PYTHON" "$ROOT/scripts/andes_scratch.py" \
      "$ROOT/scripts/train_r293_prior_residual.py" run \
      --expected-manifest-sha256 "$expected" \
      --architecture "$architecture" --seed "$seed" \
      >"$LOGS/${architecture}_s${seed}.log" 2>&1
  done
}

pids=()
for shard in 0 1 2; do
  run_worker "$shard" &
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
  "$ROOT/scripts/train_r293_prior_residual.py" verify \
  --expected-manifest-sha256 "$expected" \
  >"$LOGS/verify.log" 2>&1
: >"$STATUS/complete"
