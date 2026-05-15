"""V4 paper-faithful SAC training driver — ANDES Kundur 4-VSG.

Mirrors `train_andes.py` (V1) but imports `AndesMultiVSGEnvV4`. V4 consolidates
R10-R17 fixes:
  - IEEEG1 governor + EXST1 AVR DAE-active (Root #2 fix)
  - G4 inertia preserved (paper Kundur 4 SG)
  - VSG_M0=200 (H₀=100s, paper Eq.12 box middle)
  - VSG_D0=100 (uniform paper-magnitude)
  - Action range paper Sec.IV-B: [-200,+600]/[-200,+600]

V2/V3 ckpts NOT compatible (env physics changed). Fresh training only.

Example (3 seed parallel):
    /home/wya/andes_venv/bin/python scenarios/kundur/train_andes_v4.py \
        --episodes 200 --seed 42 --save-dir results/v4_seed42 &
    /home/wya/andes_venv/bin/python scenarios/kundur/train_andes_v4.py \
        --episodes 200 --seed 43 --save-dir results/v4_seed43 &
    /home/wya/andes_venv/bin/python scenarios/kundur/train_andes_v4.py \
        --episodes 200 --seed 44 --save-dir results/v4_seed44 &
"""
from __future__ import annotations

# ╭─ V4 import alias: keep the rest of train_andes.py logic identical ─╮
# This module copies train_andes.py file content via runpy with the V4 env
# class swapped in. Avoid file duplication so logic stays in sync with V1.
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

# Import V4 env and alias it to AndesMultiVSGEnv at the env.andes_vsg_env module
# level. train_andes.py does `from env.andes_vsg_env import AndesMultiVSGEnv`
# so once we monkey-patch that name, the V1 trainer code uses V4 transparently.
from env.andes.andes_vsg_env_v4 import AndesMultiVSGEnvV4  # noqa: E402

import env.andes_vsg_env as _legacy_compat  # noqa: E402

_legacy_compat.AndesMultiVSGEnv = AndesMultiVSGEnvV4

# Sanity tag so logs show V4 in train_andes monitor output.
print(f"[train_andes_v4] using AndesMultiVSGEnvV4 (paper-faithful R10-R17 fixes)")
print(f"[train_andes_v4] V4 deviation_summary: {AndesMultiVSGEnvV4.deviation_summary()}")

# Now exec the main trainer — it imports AndesMultiVSGEnv from env.andes_vsg_env
# which we've patched to V4 above.
import runpy  # noqa: E402

runpy.run_path(
    str(ROOT / "scenarios" / "kundur" / "train_andes.py"),
    run_name="__main__",
)
