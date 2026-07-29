#!/usr/bin/env bash
set -euo pipefail
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"
PYTHON_BIN="${PYTHON_BIN:-/home/wya/andes_venv/bin/python}"
LOG_DIR="results/r279_unattended"
mkdir -p "$LOG_DIR"
stamp="$(date -u +%Y%m%dT%H%M%SZ)"
log="$LOG_DIR/${stamp}.log"
exec > >(tee -a "$log") 2>&1

echo "[R279 unattended] start=$(date -u +%FT%TZ) repo=$REPO_ROOT"
if [[ ! -x "$PYTHON_BIN" ]]; then
  echo "Missing real-ANDES interpreter: $PYTHON_BIN" >&2
  exit 2
fi
"$PYTHON_BIN" memory/tools/round_preflight.py R279
"$PYTHON_BIN" -m ruff check \
  src/andes_rl_kundur/control/causal_area_feedback.py \
  src/andes_rl_kundur/agents/central_scalar_td3.py \
  src/andes_rl_kundur/evaluation/reviewer_identifiability.py \
  src/andes_rl_kundur/evaluation/r279_controllers.py \
  scripts/run_reviewer_identifiability.py \
  scripts/run_r279_causal_development.py \
  scripts/run_r279_causal_guard.py \
  scripts/train_r279_matched_td3.py \
  scripts/run_r279_fresh_bank.py \
  scripts/run_r279_formal.py \
  scripts/close_r279.py

bash scripts/run_r279_causal_development.sh
bash scripts/run_r279_matched_training.sh
bash scripts/run_r279_fresh_bank.sh
bash scripts/run_r279_formal.sh
"$PYTHON_BIN" scripts/close_r279.py

echo "[R279 unattended] complete=$(date -u +%FT%TZ) log=$log"