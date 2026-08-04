#!/usr/bin/env bash
set -uo pipefail

repo_root="/mnt/c/Users/27443/Desktop/andes-rl-kundur"
python_bin="/home/wya/andes_venv/bin/python"
scratch_runner="scripts/andes_scratch.py"
experiment_runner="scripts/run_r299_edge_information_probe.py"
if [[ $# -ne 1 ]]; then
  echo "usage: $0 <seal-sha256>" >&2
  exit 2
fi
seal_hash="$1"
result_dir="results/r299_edge_information_probe"

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
