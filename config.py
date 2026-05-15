"""SAC training hyperparameters.

Paper reference: Yang et al., IEEE TPWRS 2023, Table I.

Only the hyperparameters that are read from training/eval scripts live
here. Physics parameters (H₀, D₀, action bounds, disturbance magnitudes,
load step vectors, bus topology) belong on the env class — see
``env/andes/andes_vsg_env_v4.py`` (paper-faithful) and ``base_env.py``.
"""
from __future__ import annotations

# ─── Network architecture (Section IV-A: 4 fully-connected layers × 128) ───
HIDDEN_SIZES: list[int] = [128, 128, 128, 128]

# ─── SAC hyperparameters (Table I — standard defaults) ───
LR: float = 3e-4
GAMMA: float = 0.99
TAU_SOFT: float = 0.005
BUFFER_SIZE: int = 10_000      # accumulates across episodes
BATCH_SIZE: int = 256
WARMUP_STEPS: int = 1_000      # ~20 episodes of 50 transitions

# ─── Training-loop policy (Algorithm 1 line 16) ───
# Standard off-policy SAC accumulates experience across episodes.
CLEAR_BUFFER_PER_EPISODE: bool = False
