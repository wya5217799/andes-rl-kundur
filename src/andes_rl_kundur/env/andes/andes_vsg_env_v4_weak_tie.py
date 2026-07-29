"""R286 weak-tie-corridor V4+storage variant (Q-0045).

Zero-training transfer evaluation plant: identical to
``AndesMultiVSGEnvV4Storage`` except the 7<->8 triple-circuit inter-area
tie corridor (``Line_4`` / ``Line_5`` / ``Line_6``) has its ``r`` and ``x``
multiplied by ``TIE_K`` after ``setup()`` and before the power flow that
``base_env.reset()`` runs on the returned system. This is exactly the
parameter timing already frozen in ``probes/eig_alloc_common.py`` (R283
axis B / R285), so time-domain and linearization weak-grid evidence share
one definition of "weakened tie".

Discipline (R286 plan asset-protection contract):
- This file is NEW. It does not modify ``andes_vsg_env_v4.py``,
  ``andes_vsg_storage_env.py``, or ``base_env.py``.
- Only ``r`` and ``x`` of ``TIE_IDX`` are scaled; no other plant parameter
  is touched.
"""

from __future__ import annotations

from andes_rl_kundur.env.andes.andes_vsg_storage_env import (
    AndesMultiVSGEnvV4Storage,
)

# 7<->8 triple-circuit long tie corridor — dominant reactance of the
# inter-area path (x ~ 0.22 each); the 8<->9 pair (x ~ 0.02) stays
# untouched, matching probes/eig_alloc_common.py.
TIE_IDX = ("Line_4", "Line_5", "Line_6")


class AndesMultiVSGEnvV4WeakTie(AndesMultiVSGEnvV4Storage):
    """V4+storage plant with a weakened inter-area tie corridor."""

    def __init__(self, *args, tie_k: float = 1.0, **kwargs) -> None:
        if tie_k < 1.0:
            raise ValueError("tie_k < 1.0 strengthens the corridor; "
                             "R286 only weakens (tie_k >= 1.0)")
        self.tie_k = float(tie_k)
        super().__init__(*args, **kwargs)

    def _build_system(self):
        ss = super()._build_system()
        self.tie_lines_applied = None
        if abs(self.tie_k - 1.0) > 1e-12:
            line_idx = list(ss.Line.idx.v)
            detail = {}
            for tidx in TIE_IDX:
                pos = line_idx.index(tidx)
                ss.Line.r.v[pos] = float(ss.Line.r.v[pos] * self.tie_k)
                ss.Line.x.v[pos] = float(ss.Line.x.v[pos] * self.tie_k)
                detail[tidx] = {
                    "r": float(ss.Line.r.v[pos]),
                    "x": float(ss.Line.x.v[pos]),
                }
            self.tie_lines_applied = detail
        return ss
