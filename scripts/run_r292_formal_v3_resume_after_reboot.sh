#!/usr/bin/env bash
set -euo pipefail

ROOT=/mnt/e/Projects/andes-rl-kundur
PY=/home/wya/andes_venv/bin/python
SCRATCH="$ROOT/scripts/andes_scratch.py"
RUN_DIR="$ROOT/results/r292_recovery_v3_unattended"
LOG_DIR="$RUN_DIR/logs"
STATUS_DIR="$RUN_DIR/status"

cd "$ROOT"
if [[ -e "$STATUS_DIR/failed" || -e "$STATUS_DIR/complete" ]]; then
    printf 'Failed or completed R292 execution is not resumable.\n' >&2
    exit 2
fi
if [[ ! -e "$STATUS_DIR/phase" ]] || \
   [[ "$(<"$STATUS_DIR/phase")" != "FORMAL_V3_RUNNING_THREE_SHARDS" ]]; then
    printf 'R292 is not in the interrupted formal-running phase.\n' >&2
    exit 3
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

if ! run_entrypoint scripts/audit_r292_formal_v3_resume.py \
    >"$LOG_DIR/formal_v3_resume1_audit.log" 2>&1; then
    printf 'FORMAL_V3_RESUME1_AUDIT_FAILED\n' >"$STATUS_DIR/failed"
    exit 10
fi
FORMAL_HASH=$(awk '{print $1}' memory/rounds/R292/formal_v3_seal.json.sha256)
printf 'FORMAL_V3_RESUME1_RUNNING_THREE_SHARDS\n' >"$STATUS_DIR/phase"

run_entrypoint scripts/run_r292_formal_v3.py run \
    --expected-manifest-sha256 "$FORMAL_HASH" \
    --shard-index 0 --shard-count 3 \
    >"$LOG_DIR/formal_v3_resume1_shard_0.log" 2>&1 &
FORMAL_PID_0=$!
run_entrypoint scripts/run_r292_formal_v3.py run \
    --expected-manifest-sha256 "$FORMAL_HASH" \
    --shard-index 1 --shard-count 3 \
    >"$LOG_DIR/formal_v3_resume1_shard_1.log" 2>&1 &
FORMAL_PID_1=$!
run_entrypoint scripts/run_r292_formal_v3.py run \
    --expected-manifest-sha256 "$FORMAL_HASH" \
    --shard-index 2 --shard-count 3 \
    >"$LOG_DIR/formal_v3_resume1_shard_2.log" 2>&1 &
FORMAL_PID_2=$!
if ! wait_three "$FORMAL_PID_0" "$FORMAL_PID_1" "$FORMAL_PID_2"; then
    printf 'FORMAL_V3_RESUME1_EVALUATION_FAILED\n' >"$STATUS_DIR/failed"
    exit 20
fi

printf 'FORMAL_V3_RESUME1_ANALYSE\n' >"$STATUS_DIR/phase"
if ! run_entrypoint scripts/run_r292_formal_v3.py analyse \
    --expected-manifest-sha256 "$FORMAL_HASH" \
    >"$LOG_DIR/formal_v3_resume1_analyse.log" 2>&1; then
    printf 'FORMAL_V3_RESUME1_ANALYSE_FAILED\n' >"$STATUS_DIR/failed"
    exit 30
fi
printf 'R292_FORMAL_V3_COMPLETE\n' >"$STATUS_DIR/phase"
printf 'R292_FORMAL_V3_COMPLETE\n' >"$STATUS_DIR/complete"
