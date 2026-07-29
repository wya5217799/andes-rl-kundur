#!/usr/bin/env bash
# R286 weak-tie transfer — 8-shard parallel launcher (WSL only).
set -euo pipefail
SEAL="524c2cbdab009cfa932e03148c050c5c349df5ea30e7fd59cdbc01de97ae78c4"
cd /mnt/c/Users/27443/Desktop/andes-rl-kundur
mkdir -p results/r286_weak_grid_td/logs
for i in 0 1 2 3 4 5 6 7; do
  nohup /home/wya/andes_venv/bin/python scripts/run_r286_weak_grid_td.py run \
    --expected-manifest-sha256 "$SEAL" \
    --shard-index "$i" --shard-count 8 \
    > "results/r286_weak_grid_td/logs/shard_${i}.log" 2>&1 &
done
sleep 3
pgrep -fc run_r286_weak_grid_td
