#!/usr/bin/env bash
# R286 progress check: trace count + per-shard last line.
cd /mnt/c/Users/27443/Desktop/andes-rl-kundur/results/r286_weak_grid_td
n=$(ls traces/ 2>/dev/null | grep -c '\.json$' || true)
echo "traces: $n / 192"
for i in 0 1 2 3 4 5 6 7; do
  printf 'shard_%s: ' "$i"
  tail -n 1 "logs/shard_${i}.log" 2>/dev/null | cut -c1-120 || echo "(no log)"
done
pgrep -fc run_r286_weak_grid_td || echo "0 running"
