#!/usr/bin/env bash
set -euo pipefail

ROOT=/mnt/e/Projects/andes-rl-kundur
PY=/home/wya/andes_venv/bin/python
SCRATCH="$ROOT/scripts/andes_scratch.py"
LOG_DIR="$ROOT/results/r292_unattended/logs"
STATUS_DIR="$ROOT/results/r292_unattended/status"

cd "$ROOT"
mkdir -p "$LOG_DIR" "$STATUS_DIR"

run_entrypoint() {
    "$PY" "$SCRATCH" "$@"
}

wait_three() {
    local first_pid="$1"
    local second_pid="$2"
    local third_pid="$3"
    local status=0
    wait "$first_pid" || status=1
    wait "$second_pid" || status=1
    wait "$third_pid" || status=1
    return "$status"
}

run_training_seed() {
    local seed="$1"
    local seal_hash="$2"
    run_entrypoint scripts/train_r292_vector_td3.py run \
        --expected-manifest-sha256 "$seal_hash" \
        --architecture central_vector \
        --seed "$seed"
    run_entrypoint scripts/train_r292_vector_td3.py run \
        --expected-manifest-sha256 "$seal_hash" \
        --architecture distributed_edge \
        --seed "$seed"
}

run_entrypoint scripts/train_r292_vector_td3.py prepare \
    >"$LOG_DIR/training_prepare.log" 2>&1
TRAINING_HASH=$(awk '{print $1}' memory/rounds/R292/training_seal.json.sha256)

run_training_seed 101 "$TRAINING_HASH" >"$LOG_DIR/training_seed_101.log" 2>&1 &
PID_ONE=$!
run_training_seed 137 "$TRAINING_HASH" >"$LOG_DIR/training_seed_137.log" 2>&1 &
PID_TWO=$!
run_training_seed 173 "$TRAINING_HASH" >"$LOG_DIR/training_seed_173.log" 2>&1 &
PID_THREE=$!
if ! wait_three "$PID_ONE" "$PID_TWO" "$PID_THREE"; then
    printf 'TRAINING_FAILED\n' >"$STATUS_DIR/failed"
    exit 20
fi
run_entrypoint scripts/train_r292_vector_td3.py verify \
    --expected-manifest-sha256 "$TRAINING_HASH" \
    >"$LOG_DIR/training_verify.log" 2>&1
printf 'TRAINING_VERIFIED\n' >"$STATUS_DIR/training_complete"

run_entrypoint scripts/run_r292_fresh_bank.py prepare \
    >"$LOG_DIR/fresh_prepare.log" 2>&1
FRESH_HASH=$(awk '{print $1}' memory/rounds/R292/fresh_bank_screen_seal.json.sha256)
run_entrypoint scripts/run_r292_fresh_bank.py run \
    --expected-manifest-sha256 "$FRESH_HASH" \
    --shard-index 0 --shard-count 3 \
    >"$LOG_DIR/fresh_shard_0.log" 2>&1 &
FRESH_PID_0=$!
run_entrypoint scripts/run_r292_fresh_bank.py run \
    --expected-manifest-sha256 "$FRESH_HASH" \
    --shard-index 1 --shard-count 3 \
    >"$LOG_DIR/fresh_shard_1.log" 2>&1 &
FRESH_PID_1=$!
run_entrypoint scripts/run_r292_fresh_bank.py run \
    --expected-manifest-sha256 "$FRESH_HASH" \
    --shard-index 2 --shard-count 3 \
    >"$LOG_DIR/fresh_shard_2.log" 2>&1 &
FRESH_PID_2=$!
if ! wait_three "$FRESH_PID_0" "$FRESH_PID_1" "$FRESH_PID_2"; then
    printf 'FRESH_SCREEN_FAILED\n' >"$STATUS_DIR/failed"
    exit 30
fi
run_entrypoint scripts/run_r292_fresh_bank.py analyse \
    --expected-manifest-sha256 "$FRESH_HASH" \
    >"$LOG_DIR/fresh_analyse.log" 2>&1
printf 'FRESH_BANK_VERIFIED\n' >"$STATUS_DIR/fresh_complete"

run_entrypoint scripts/run_r292_formal.py prepare \
    >"$LOG_DIR/formal_prepare.log" 2>&1
FORMAL_HASH=$(awk '{print $1}' memory/rounds/R292/formal_seal.json.sha256)
run_entrypoint scripts/run_r292_formal.py run \
    --expected-manifest-sha256 "$FORMAL_HASH" \
    --shard-index 0 --shard-count 3 \
    >"$LOG_DIR/formal_shard_0.log" 2>&1 &
FORMAL_PID_0=$!
run_entrypoint scripts/run_r292_formal.py run \
    --expected-manifest-sha256 "$FORMAL_HASH" \
    --shard-index 1 --shard-count 3 \
    >"$LOG_DIR/formal_shard_1.log" 2>&1 &
FORMAL_PID_1=$!
run_entrypoint scripts/run_r292_formal.py run \
    --expected-manifest-sha256 "$FORMAL_HASH" \
    --shard-index 2 --shard-count 3 \
    >"$LOG_DIR/formal_shard_2.log" 2>&1 &
FORMAL_PID_2=$!
if ! wait_three "$FORMAL_PID_0" "$FORMAL_PID_1" "$FORMAL_PID_2"; then
    printf 'FORMAL_EVALUATION_FAILED\n' >"$STATUS_DIR/failed"
    exit 40
fi
run_entrypoint scripts/run_r292_formal.py analyse \
    --expected-manifest-sha256 "$FORMAL_HASH" \
    >"$LOG_DIR/formal_analyse.log" 2>&1
printf 'R292_FORMAL_COMPLETE\n' >"$STATUS_DIR/complete"
