#!/usr/bin/env bash
set -euo pipefail

ROOT=/mnt/e/Projects/andes-rl-kundur
PY=/home/wya/andes_venv/bin/python
SCRATCH="$ROOT/scripts/andes_scratch.py"
LOG_DIR="$ROOT/results/r292_recovery_unattended/logs"
STATUS_DIR="$ROOT/results/r292_recovery_unattended/status"

cd "$ROOT"
mkdir -p "$LOG_DIR" "$STATUS_DIR"
if [[ -e "$STATUS_DIR/complete" || -e "$STATUS_DIR/failed" ]]; then
    printf 'Recovery status already exists; refusing to overwrite.\n' >&2
    exit 2
fi

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

if ! run_entrypoint scripts/recover_r292_fresh_bank.py prepare \
    >"$LOG_DIR/screen_v2_prepare.log" 2>&1; then
    printf 'SCREEN_V2_PREPARE_FAILED\n' >"$STATUS_DIR/failed"
    exit 10
fi
SCREEN_HASH=$(awk '{print $1}' memory/rounds/R292/fresh_bank_screen_v2_seal.json.sha256)
if ! run_entrypoint scripts/recover_r292_fresh_bank.py analyse \
    --expected-manifest-sha256 "$SCREEN_HASH" \
    >"$LOG_DIR/screen_v2_analyse.log" 2>&1; then
    printf 'SCREEN_V2_ANALYSE_FAILED\n' >"$STATUS_DIR/failed"
    exit 20
fi
printf 'SCREEN_V2_VERIFIED\n' >"$STATUS_DIR/screen_complete"

if ! run_entrypoint scripts/run_r292_formal_v2.py prepare \
    >"$LOG_DIR/formal_v2_prepare.log" 2>&1; then
    printf 'FORMAL_V2_PREPARE_FAILED\n' >"$STATUS_DIR/failed"
    exit 30
fi
FORMAL_HASH=$(awk '{print $1}' memory/rounds/R292/formal_v2_seal.json.sha256)

run_entrypoint scripts/run_r292_formal_v2.py run \
    --expected-manifest-sha256 "$FORMAL_HASH" \
    --shard-index 0 --shard-count 3 \
    >"$LOG_DIR/formal_v2_shard_0.log" 2>&1 &
FORMAL_PID_0=$!
run_entrypoint scripts/run_r292_formal_v2.py run \
    --expected-manifest-sha256 "$FORMAL_HASH" \
    --shard-index 1 --shard-count 3 \
    >"$LOG_DIR/formal_v2_shard_1.log" 2>&1 &
FORMAL_PID_1=$!
run_entrypoint scripts/run_r292_formal_v2.py run \
    --expected-manifest-sha256 "$FORMAL_HASH" \
    --shard-index 2 --shard-count 3 \
    >"$LOG_DIR/formal_v2_shard_2.log" 2>&1 &
FORMAL_PID_2=$!
if ! wait_three "$FORMAL_PID_0" "$FORMAL_PID_1" "$FORMAL_PID_2"; then
    printf 'FORMAL_V2_EVALUATION_FAILED\n' >"$STATUS_DIR/failed"
    exit 40
fi
if ! run_entrypoint scripts/run_r292_formal_v2.py analyse \
    --expected-manifest-sha256 "$FORMAL_HASH" \
    >"$LOG_DIR/formal_v2_analyse.log" 2>&1; then
    printf 'FORMAL_V2_ANALYSE_FAILED\n' >"$STATUS_DIR/failed"
    exit 50
fi
printf 'R292_FORMAL_V2_COMPLETE\n' >"$STATUS_DIR/complete"
