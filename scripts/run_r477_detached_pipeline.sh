#!/usr/bin/env bash
set -euo pipefail

repo="/mnt/e/Projects/andes-rl-kundur"
python_bin="/home/wya/andes_venv/bin/python"
phase="startup"
child_pid=""

cd "${repo}"

write_inventory() {
  local exit_code="$1"
  R477_PIPELINE_PHASE="${phase}" R477_PIPELINE_EXIT_CODE="${exit_code}" \
    "${python_bin}" scripts/andes_scratch.py \
      scripts/run_r477_u2_confirmatory.py inventory >/dev/null 2>&1 || true
}

on_exit() {
  local exit_code="$?"
  write_inventory "${exit_code}"
}

on_signal() {
  local exit_code="$1"
  phase="interrupted:${phase}"
  if [[ -n "${child_pid}" ]]; then
    kill -TERM -- "-${child_pid}" 2>/dev/null || true
    wait "${child_pid}" 2>/dev/null || true
    child_pid=""
  fi
  exit "${exit_code}"
}

run_phase() {
  phase="$1"
  shift
  setsid "$@" &
  child_pid="$!"
  wait "${child_pid}"
  child_pid=""
}

trap on_exit EXIT
trap 'on_signal 130' INT
trap 'on_signal 143' TERM

runner=("${python_bin}" scripts/andes_scratch.py scripts/run_r477_u2_confirmatory.py)
driver=("${python_bin}" scripts/andes_scratch.py scripts/soft_spot_shard_driver.py)

run_phase verify "${runner[@]}" verify
run_phase import "${runner[@]}" import

for wave in 1 2; do
  run_phase "training-wave-${wave}" "${driver[@]}" \
    --runner scripts/run_r477_u2_confirmatory.py \
    --shards "tmp/andes/r477_train_wave${wave}_shards.json" \
    --workers 16 \
    --round R477 \
    --log-dir "tmp/andes/r477_train_logs/wave${wave}"
  if [[ "${wave}" == "1" ]]; then
    first_wave_result="$(find tmp/andes/r477_train_logs/wave1 -name driver_result.json -type f | sort | tail -n 1)"
    if [[ -z "${first_wave_result}" ]]; then
      echo "missing first-wave driver result" >&2
      exit 1
    fi
    run_phase eta-recalibration "${runner[@]}" eta "${first_wave_result}"
  fi
done

run_phase training-completeness "${python_bin}" -c \
  'from pathlib import Path; import json; paths=list(Path("results/research_loop/r477_u2_confirmatory/train").glob("*/*/manifest.json")); assert len(paths)==48, f"expected 48 training manifests, found {len(paths)}"; assert all(json.load(open(path))["valid"] and int(json.load(open(path))["interaction_steps"])==43200 for path in paths)'

run_phase evaluation "${driver[@]}" \
  --runner scripts/run_r477_u2_confirmatory.py \
  --shards tmp/andes/r477_eval_shards.json \
  --workers 16 \
  --round R477 \
  --log-dir tmp/andes/r477_eval_logs

run_phase budget "${runner[@]}" budget
run_phase aggregate "${runner[@]}" aggregate
run_phase manifest "${runner[@]}" manifest
phase="complete"
