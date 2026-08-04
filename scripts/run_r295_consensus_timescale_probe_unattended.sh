#!/usr/bin/env bash
set -uo pipefail

repo_root="/mnt/c/Users/27443/Desktop/andes-rl-kundur"
python_bin="/home/wya/andes_venv/bin/python"
runner="scripts/run_r295_consensus_timescale_probe.py"
seal_hash="ae24ad0a6b782a0ceeb805baaf0952eb1b65dffd7fba38be099d3340a8e5492c"
result_dir="results/r295_consensus_timescale_probe"

cd "${repo_root}"

pids=()
for shard_index in 0 1 2; do
  "${python_bin}" "${runner}" run \
    --expected-seal-sha256 "${seal_hash}" \
    --shard-index "${shard_index}" \
    --shard-count 3 \
    > "${result_dir}/shard_${shard_index}.log" 2>&1 &
  pids+=("$!")
done

exit_code=0
for pid in "${pids[@]}"; do
  if ! wait "${pid}"; then
    exit_code=1
  fi
done

for shard_index in 0 1 2; do
  sed -n '1,200p' "${result_dir}/shard_${shard_index}.log"
done

exit "${exit_code}"
