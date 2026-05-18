#!/usr/bin/env bash
# R58 paper-strict eval launcher.
# Evaluates 36 ckpts (9 historical + 18 paper-strict + 9 radsec) on the
# 20-scenario R58 test set via paper Sec.IV-C metric (global cum_rf).
#
# Phase 1: 3 batches in parallel (historical / pure / rescaled).
# Phase 2: 1 batch alone (radsec — keeps total <= 3 parallel WSL python).
# Per-ckpt JSON: results/research_loop/r58_paper_metric_<label>.json

set -uo pipefail

PY=/home/wya/andes_venv/bin/python
ROOT=/mnt/c/Users/27443/Desktop/andes-rl-kundur
cd "$ROOT" || exit 1

run_batch() {
    local label=$1; shift
    local logfile="results/_r58_eval_${label}.log"
    echo "[$(date +%H:%M:%S)] eval batch $label: $@"
    $PY scripts/_r58_paper_strict_eval.py --ckpt-dirs "$@" \
        > "$logfile" 2>&1
    echo "[$(date +%H:%M:%S)] eval batch $label done"
}

# ─── Phase 1: 3-batch parallel ──────────────────────────────────────

# Batch 1 — 9 historical baselines (R48-β / R51-α / R57-α)
HISTORICAL=(
    results/td3_norm_h64_s49
    results/td3_norm_h64_s50
    results/td3_norm_h64_s51
    results/sac_norm_h64_s49
    results/sac_norm_h64_s50
    results/sac_norm_h64_s51
    results/td3_lstm_h64_warmup5_s49
    results/td3_lstm_h64_warmup5_s50
    results/td3_lstm_h64_warmup5_s51
)

# Batch 2 — 9 R58 paper_strict_pure ckpts
PURE_NEW=()
for algo in sac td3 td3_lstm; do
    for seed in 49 50 51; do
        PURE_NEW+=("results/r58_paper_strict_pure_${algo}_s${seed}")
    done
done

# Batch 3 — 9 R58 paper_strict_rescaled ckpts
RESC_NEW=()
for algo in sac td3 td3_lstm; do
    for seed in 49 50 51; do
        RESC_NEW+=("results/r58_paper_strict_rescaled_${algo}_s${seed}")
    done
done

echo "=== Phase 1: 3-batch parallel ==="
run_batch historical "${HISTORICAL[@]}" &
run_batch pure       "${PURE_NEW[@]}"   &
run_batch rescaled   "${RESC_NEW[@]}"   &
wait
echo "=== Phase 1 done ==="

# ─── Phase 2: radsec alone ──────────────────────────────────────────

# Batch 4 — 9 R58 paper_strict_pure_radsec ckpts (audit A3 supplement)
RADSEC_NEW=()
for algo in sac td3 td3_lstm; do
    for seed in 49 50 51; do
        RADSEC_NEW+=("results/r58_paper_strict_pure_radsec_${algo}_s${seed}")
    done
done

echo "=== Phase 2: radsec batch ==="
run_batch radsec "${RADSEC_NEW[@]}"
echo "=== Phase 2 done ==="

echo "[$(date +%H:%M:%S)] === ALL 36 R58 evaluations complete ==="
