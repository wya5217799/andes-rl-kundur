#!/usr/bin/env bash
# R58 H3 sanity — train s51 paper_strict_pure td3_lstm for 500 ep.
# Verifies whether the H2.A divergence prediction (PHI_H=PHI_D=1.0 →
# r_h/r_f imbalance → training fails) persists at paper convergence
# horizon (paper Sec.IV-B says 500 ep stabilises).
#
# Wall ~85 min single seed × 500 ep on the project workstation.

set -uo pipefail
PY=/home/wya/andes_venv/bin/python
ROOT=/mnt/c/Users/27443/Desktop/andes-rl-kundur
cd "$ROOT" || exit 1

OUT=results/r58_sanity500_pure_td3_lstm_s51
rm -rf "$OUT"
mkdir -p "$OUT"

$PY scripts/train.py \
    --algo td3_lstm --normalize-actions --episodes 500 \
    --seed 51 --hidden-size 64 \
    --reward-config paper_strict_pure \
    --lstm-lr-warmup-eps 5 \
    --save-dir "$OUT" \
    --log-interval 25 \
    > "$OUT/stdout.log" 2>&1

echo "[$(date +%H:%M:%S)] s51 _pure 500ep sanity done"
