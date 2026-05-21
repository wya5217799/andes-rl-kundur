#!/usr/bin/env bash
# R100-W2 λ_h sweep — runs after W1 lands.
# Use only if W1 (λ_h=0.01) gives MARGINAL result; if W1 already CONFIRM
# or REGRESS, prefer paper-grade multi-seed at the best λ_h instead.
#
# Usage: bash scripts/r100_lambda_sweep.sh
# Runs 3 waves sequentially: λ_h ∈ {0.003, 0.03, 0.1}. Each ~15 min.

set -euo pipefail

cd /mnt/c/Users/27443/Desktop/andes-rl-kundur
source ~/andes_venv/bin/activate

for L in 0.003 0.03 0.1; do
  TAG=$(printf "%s" "$L" | tr '.' 'p')
  SAVEDIR="results/r100_w2_hreg_lambda${TAG}_s54"
  echo "=== R100-W2 λ_h=$L → $SAVEDIR ==="
  LR=1e-4 python scripts/train.py \
      --algo td3_lstm_hreg \
      --h-norm-reg "$L" \
      --episodes 75 --seed 54 \
      --hidden-size 64 --tau 0.001 \
      --normalize-actions \
      --lstm-lr-warmup-eps 5 \
      --save-dir "$SAVEDIR"
done
