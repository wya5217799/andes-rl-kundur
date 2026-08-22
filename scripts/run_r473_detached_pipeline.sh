#!/usr/bin/env bash
set -euo pipefail

repo="/mnt/e/Projects/andes-rl-kundur"
python_bin="/home/wya/andes_venv/bin/python"

cd "${repo}"

"${python_bin}" scripts/andes_scratch.py scripts/run_r473_u2_source_factorial.py import

"${python_bin}" scripts/andes_scratch.py scripts/soft_spot_shard_driver.py \
  --runner scripts/run_r473_u2_source_factorial.py \
  --shards tmp/andes/r473_train_shards.json \
  --workers 16 \
  --round R473 \
  --log-dir tmp/andes/r473_train_logs

"${python_bin}" -c 'from pathlib import Path; import json; paths=list(Path("results/research_loop/r473_u2_source_factorial/train").glob("*/*/manifest.json")); assert len(paths)==108, f"expected 108 training manifests, found {len(paths)}"; assert all(json.load(open(path))["valid"] and int(json.load(open(path))["interaction_steps"])==43200 for path in paths)'

"${python_bin}" scripts/andes_scratch.py scripts/soft_spot_shard_driver.py \
  --runner scripts/run_r473_u2_source_factorial.py \
  --shards tmp/andes/r473_eval_shards.json \
  --workers 16 \
  --round R473 \
  --log-dir tmp/andes/r473_eval_logs

"${python_bin}" scripts/andes_scratch.py scripts/run_r473_u2_source_factorial.py aggregate
"${python_bin}" scripts/andes_scratch.py scripts/run_r473_u2_source_factorial.py manifest
