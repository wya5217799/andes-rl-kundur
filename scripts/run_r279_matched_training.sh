#!/usr/bin/env bash
set -euo pipefail

cd /mnt/e/Projects/andes-rl-kundur
PYTHON_BIN="${PYTHON_BIN:-/home/wya/andes_venv/bin/python}"
SEAL_REL="memory/rounds/R279/training_seal.json"
OUT_REL="results/r279_matched_training"
GUARD_SUMMARY="results/r279_causal_guard/causal_guard_summary.json"

if [[ ! -x "$PYTHON_BIN" ]]; then
  echo "Missing executable real-ANDES interpreter: $PYTHON_BIN" >&2
  exit 2
fi
if [[ ! -f "$GUARD_SUMMARY" ]]; then
  echo "Causal full-horizon guard must finish before matched TD3 training." >&2
  exit 3
fi

"$PYTHON_BIN" -m pytest \
  tests/test_causal_area_feedback.py \
  tests/test_central_scalar_td3.py \
  tests/test_reviewer_identifiability.py \
  tests/test_icems_residual_evaluation.py -q
"$PYTHON_BIN" memory/tools/round_preflight.py R279

if [[ ! -f "$SEAL_REL" ]]; then
  "$PYTHON_BIN" scripts/train_r279_matched_td3.py prepare
fi
SEAL_HASH="$(awk '{print $1}' "${SEAL_REL}.sha256")"
if [[ ${#SEAL_HASH} -ne 64 ]]; then
  echo "Invalid matched-training seal hash: $SEAL_HASH" >&2
  exit 4
fi

mkdir -p "${OUT_REL}/logs"
for architecture in shared centralized; do
  smoke_dir="${OUT_REL}/smoke/${architecture}_s17_e2"
  if [[ -f "${smoke_dir}/training_summary.json" ]]; then
    echo "Smoke run already complete: ${architecture}"
  elif [[ -d "$smoke_dir" ]]; then
    echo "Incomplete smoke run retained; refusing a retry: $smoke_dir" >&2
    exit 5
  else
    stamp="$(date -u +%Y%m%dT%H%M%SZ)"
    timeout --signal=TERM 30m "$PYTHON_BIN" \
      scripts/train_r279_matched_td3.py run \
      --expected-manifest-sha256 "$SEAL_HASH" \
      --architecture "$architecture" --seed 17 --smoke-episodes 2 \
      >"${OUT_REL}/logs/${stamp}_smoke_${architecture}_s17.stdout.log" \
      2>"${OUT_REL}/logs/${stamp}_smoke_${architecture}_s17.stderr.log"
  fi
done

run_wave() {
  local wave="$1"
  shift
  local pids=()
  local labels=()
  local failure=0
  while (( "$#" )); do
    local architecture="$1"
    local seed="$2"
    shift 2
    local run_dir="${OUT_REL}/${architecture}_s${seed}"
    if [[ -f "${run_dir}/training_summary.json" ]]; then
      echo "Formal run already complete: ${architecture} seed=${seed}"
      continue
    fi
    if [[ -d "$run_dir" ]]; then
      echo "Incomplete formal run retained; refusing retry: $run_dir" >&2
      failure=1
      continue
    fi
    local stamp
    stamp="$(date -u +%Y%m%dT%H%M%SZ)"
    timeout --signal=TERM 180m "$PYTHON_BIN" \
      scripts/train_r279_matched_td3.py run \
      --expected-manifest-sha256 "$SEAL_HASH" \
      --architecture "$architecture" --seed "$seed" \
      >"${OUT_REL}/logs/${stamp}_${architecture}_s${seed}.stdout.log" \
      2>"${OUT_REL}/logs/${stamp}_${architecture}_s${seed}.stderr.log" &
    pids+=("$!")
    labels+=("${architecture}_s${seed}")
    echo "Started wave=${wave} ${labels[-1]} pid=${pids[-1]}"
  done
  for index in "${!pids[@]}"; do
    if ! wait "${pids[$index]}"; then
      echo "Training failed for ${labels[$index]}; artifacts retained, no retry." >&2
      failure=1
    fi
  done
  if [[ "$failure" -ne 0 ]]; then
    return 1
  fi
}

run_wave 1 shared 17 centralized 17 shared 53
run_wave 2 centralized 53 shared 89 centralized 89

if [[ -f "${OUT_REL}/training_matrix_summary.json" ]]; then
  echo "Training matrix already verified; refusing to overwrite summary."
else
  "$PYTHON_BIN" scripts/train_r279_matched_td3.py verify \
    --expected-manifest-sha256 "$SEAL_HASH"
fi

echo "R279 matched shared/centralized TD3 training complete."