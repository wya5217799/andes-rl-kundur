#!/usr/bin/env bash
# R58 audit-A3 supplementary training — paper_strict_pure_radsec.
# 9 ckpts: 3 algos (sac/td3/td3_lstm) × 3 seeds (49/50/51).
# 3 waves of 3 parallel WSL python processes (max-concurrency cap).
# Total ~36 min wall on the project workstation.
#
# Pre-condition: scripts/_r58_train_all.sh has finished (the 18-seed
# matrix with paper_strict_pure / paper_strict_rescaled). This script
# is the "audit A3 supplement" testing whether paper-Eq.15 in rad/s
# instead of Hz changes the PHI=1 divergence story.
#
# Each ckpt-dir = results/r58_paper_strict_pure_radsec_{algo}_s{seed}/

set -uo pipefail

PY=/home/wya/andes_venv/bin/python
ROOT=/mnt/c/Users/27443/Desktop/andes-rl-kundur
cd "$ROOT" || exit 1

CFG=paper_strict_pure_radsec

train_one() {
    local algo=$1 seed=$2
    local outdir="results/r58_${CFG}_${algo}_s${seed}"
    rm -rf "$outdir"
    mkdir -p "$outdir"
    local extra=""
    if [[ "$algo" == "td3_lstm" ]]; then
        extra="--lstm-lr-warmup-eps 5"
    fi
    $PY scripts/train.py \
        --algo "$algo" --normalize-actions --episodes 75 \
        --seed "$seed" --hidden-size 64 \
        --reward-config "$CFG" \
        $extra \
        --save-dir "$outdir" \
        --log-interval 25 \
        > "$outdir/stdout.log" 2>&1
}

run_wave() {
    local seed=$1
    echo "[$(date +%H:%M:%S)] === wave radsec s$seed (sac td3 td3_lstm parallel) ==="
    train_one sac      "$seed" &
    train_one td3      "$seed" &
    train_one td3_lstm "$seed" &
    wait
    echo "[$(date +%H:%M:%S)] === wave radsec s$seed done ==="
}

for seed in 49 50 51; do
    run_wave "$seed"
done

echo "[$(date +%H:%M:%S)] === ALL 9 R58 radsec trainings complete ==="
