#!/usr/bin/env bash
set -euo pipefail

cd /mnt/e/Projects/andes-rl-kundur
exec /home/wya/andes_venv/bin/python \
  scripts/eval_attainable_oracle.py \
  --out-dir results/r270_attainable_oracle
