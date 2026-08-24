#!/usr/bin/env bash
set -euo pipefail

# R480 transport-only wrapper: keep the WSL instance alive while the R480
# resume runner executes the six-cell H-sensitivity bank (R474/R475 launch
# pattern). Scientific logic lives in scripts/run_r480_h_sensitivity_resume.py.

repo="/mnt/e/Projects/andes-rl-kundur"
python_bin="/home/wya/andes_venv/bin/python"

cd "${repo}"
"${python_bin}" scripts/andes_scratch.py scripts/run_r480_h_sensitivity_resume.py execute
