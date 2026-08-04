#!/usr/bin/env bash
set -uo pipefail

repo_root="/mnt/c/Users/27443/Desktop/andes-rl-kundur"
python_bin="/home/wya/andes_venv/bin/python"
scratch_runner="scripts/andes_scratch.py"
experiment_runner="scripts/run_r297_relative_rocof_amplitude.py"
seal_hash="af5e386b608461c2dfdb107c5cafcf4ca2ec2927e5e7a6455aa5223cc3b61e76"
result_dir="results/r297_relative_rocof_amplitude"

cd "${repo_root}"
pids=()
for shard_index in 0 1 2; do
  "${python_bin}" "${scratch_runner}" "${experiment_runner}" run \
    --expected-seal-sha256 "${seal_hash}" \
    --shard-index "${shard_index}" --shard-count 3 \
    > "${result_dir}/shard_${shard_index}.log" 2>&1 &
  pids+=("$!")
done

exit_code=0
for pid in "${pids[@]}"; do
  if ! wait "${pid}"; then exit_code=1; fi
done
for shard_index in 0 1 2; do
  sed -n '1,200p' "${result_dir}/shard_${shard_index}.log"
done
exit "${exit_code}"
