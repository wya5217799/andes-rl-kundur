#!/usr/bin/env bash
# R286 watchdog: wait for all shards, verify 192 traces, then analyse.
set -uo pipefail
cd /mnt/c/Users/27443/Desktop/andes-rl-kundur
SEAL="524c2cbdab009cfa932e03148c050c5c349df5ea30e7fd59cdbc01de97ae78c4"
OUT=results/r286_weak_grid_td
while pgrep -f "run_r286_weak_grid_td.py run" > /dev/null; do sleep 30; done
n=$(ls "$OUT"/traces/*.json 2>/dev/null | wc -l)
echo "WATCHDOG traces=$n time=$(date -Iseconds)" > "$OUT/logs/watchdog.txt"
if [ "$n" -ne 192 ]; then
  echo "ABORT: expected 192 traces, got $n — analyse NOT run" >> "$OUT/logs/watchdog.txt"
  grep -l "RuntimeError\|Error\|Traceback" "$OUT"/logs/shard_*.log >> "$OUT/logs/watchdog.txt" 2>/dev/null || true
  exit 1
fi
/home/wya/andes_venv/bin/python scripts/run_r286_weak_grid_td.py analyse \
  --expected-manifest-sha256 "$SEAL" >> "$OUT/logs/watchdog.txt" 2>&1
echo "ANALYSE_EXIT=$?" >> "$OUT/logs/watchdog.txt"
