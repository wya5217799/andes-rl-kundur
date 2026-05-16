#!/usr/bin/env bash
# R58 paper-strict training launcher.
# Trains 18 ckpts: 3 algos × 3 seeds × 2 configs (pure / rescaled).
# 6 waves of 3 parallel WSL python processes (max-concurrency cap).
# Total ~72 min wall on the project's 16C/32T workstation.
#
# Each ckpt-dir = results/r58_{config}_{algo}_s{seed}/

set -uo pipefail

PY=/home/wya/andes_venv/bin/python
ROOT=/mnt/c/Users/27443/Desktop/andes-rl-kundur
cd "$ROOT" || exit 1

train_one() {
    local cfg=$1 algo=$2 seed=$3
    local outdir="results/r58_${cfg}_${algo}_s${seed}"
    rm -rf "$outdir"
    mkdir -p "$outdir"
    local extra=""
    if [[ "$algo" == "td3_lstm" ]]; then
        extra="--lstm-lr-warmup-eps 5"
    fi
    $PY scripts/train.py \
        --algo "$algo" --normalize-actions --episodes 75 \
        --seed "$seed" --hidden-size 64 \
        --reward-config "$cfg" \
        $extra \
        --save-dir "$outdir" \
        --log-interval 25 \
        > "$outdir/stdout.log" 2>&1
}

run_wave() {
    local cfg=$1 seed=$2
    echo "[$(date +%H:%M:%S)] === wave $cfg s$seed (sac td3 td3_lstm parallel) ==="
    train_one "$cfg" sac      "$seed" &
    train_one "$cfg" td3      "$seed" &
    train_one "$cfg" td3_lstm "$seed" &
    wait
    echo "[$(date +%H:%M:%S)] === wave $cfg s$seed done ==="
}

# 6 waves total
for cfg in paper_strict_pure paper_strict_rescaled; do
    for seed in 49 50 51; do
        run_wave "$cfg" "$seed"
    done
done

echo "[$(date +%H:%M:%S)] === ALL 18 R58 trainings complete ==="
