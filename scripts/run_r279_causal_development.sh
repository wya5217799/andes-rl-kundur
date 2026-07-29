#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_BIN="/home/wya/andes_venv/bin/python"
SEAL_REL="memory/rounds/R279/causal_development_seal.json"
RESULT_REL="results/r279_causal_development"
SHARD_COUNT=3

cd "$REPO_ROOT"

if pgrep -af '/home/wya/andes_venv/bin/python .*run_r279_causal_development.py run' >/dev/null; then
  echo "Refusing to overlap an existing R279 causal-development process." >&2
  exit 2
fi

"$PYTHON_BIN" memory/tools/round_preflight.py R279 --json
"$PYTHON_BIN" memory/tools/dual_metric_lint.py
"$PYTHON_BIN" -m pytest \
  tests/test_causal_area_feedback.py \
  tests/test_central_scalar_td3.py \
  tests/test_reviewer_identifiability.py \
  tests/test_icems_residual_env.py \
  tests/test_icems_residual_evaluation.py -q

if [[ ! -f "$SEAL_REL" ]]; then
  "$PYTHON_BIN" scripts/run_r279_causal_development.py prepare
fi
SEAL_HASH="$(awk '{print $1}' "${SEAL_REL}.sha256")"
if [[ ${#SEAL_HASH} -ne 64 ]]; then
  echo "Invalid causal-development seal hash: $SEAL_HASH" >&2
  exit 3
fi

mkdir -p "${RESULT_REL}/logs"
RUN_STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
pids=()
for shard in $(seq 0 $((SHARD_COUNT - 1))); do
  stdout="${RESULT_REL}/logs/${RUN_STAMP}_shard${shard}.stdout.log"
  stderr="${RESULT_REL}/logs/${RUN_STAMP}_shard${shard}.stderr.log"
  timeout --signal=TERM 60m "$PYTHON_BIN" \
    scripts/run_r279_causal_development.py run \
    --expected-manifest-sha256 "$SEAL_HASH" \
    --shard-index "$shard" \
    --shard-count "$SHARD_COUNT" \
    >"$stdout" 2>"$stderr" &
  pids+=("$!")
  echo "Started shard $shard pid=${pids[$shard]} logs=$stdout,$stderr"
done

failed=0
for shard in $(seq 0 $((SHARD_COUNT - 1))); do
  if ! wait "${pids[$shard]}"; then
    echo "Shard $shard failed; retaining all partial traces and logs." >&2
    failed=1
  fi
done
if [[ "$failed" -ne 0 ]]; then
  exit 4
fi

if [[ -f "${RESULT_REL}/causal_development_summary.json" ]]; then
  echo "R279 causal development is already analysed; refusing to overwrite it."
else
  "$PYTHON_BIN" scripts/run_r279_causal_development.py analyse \
    --expected-manifest-sha256 "$SEAL_HASH"
fi

DEV_SUMMARY_HASH="$(awk '{print $1}' "${RESULT_REL}/causal_development_summary.json.sha256")"
GUARD_SEAL_REL="memory/rounds/R279/causal_guard_seal.json"
GUARD_RESULT_REL="results/r279_causal_guard"
if [[ ! -f "$GUARD_SEAL_REL" ]]; then
  "$PYTHON_BIN" scripts/run_r279_causal_guard.py prepare \
    --expected-development-summary-sha256 "$DEV_SUMMARY_HASH"
fi
GUARD_SEAL_HASH="$(awk '{print $1}' "${GUARD_SEAL_REL}.sha256")"
mkdir -p "${GUARD_RESULT_REL}/logs"
GUARD_STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
pids=()
for shard in $(seq 0 $((SHARD_COUNT - 1))); do
  stdout="${GUARD_RESULT_REL}/logs/${GUARD_STAMP}_shard${shard}.stdout.log"
  stderr="${GUARD_RESULT_REL}/logs/${GUARD_STAMP}_shard${shard}.stderr.log"
  timeout --signal=TERM 60m "$PYTHON_BIN" \
    scripts/run_r279_causal_guard.py run \
    --expected-manifest-sha256 "$GUARD_SEAL_HASH" \
    --shard-index "$shard" \
    --shard-count "$SHARD_COUNT" \
    >"$stdout" 2>"$stderr" &
  pids+=("$!")
  echo "Started guard shard $shard pid=${pids[$shard]} logs=$stdout,$stderr"
done
failed=0
for shard in $(seq 0 $((SHARD_COUNT - 1))); do
  if ! wait "${pids[$shard]}"; then
    echo "Guard shard $shard failed; retaining partial traces and logs." >&2
    failed=1
  fi
done
if [[ "$failed" -ne 0 ]]; then
  exit 5
fi
if [[ -f "${GUARD_RESULT_REL}/causal_guard_summary.json" ]]; then
  echo "R279 causal guard is already analysed; refusing to overwrite it."
else
  "$PYTHON_BIN" scripts/run_r279_causal_guard.py analyse \
    --expected-manifest-sha256 "$GUARD_SEAL_HASH"
fi

echo "R279 Stage B development and full-horizon guard complete."