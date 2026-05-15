# Frozen ANDES env ancestors

These env classes were superseded by `env/andes/andes_vsg_env_v4.py`
(self-contained, paper-faithful) on 2026-05-16. They are preserved
here for historical reference and to keep `git log --follow` working
on the inheritance chain.

**Do not import these in active code.**

| File | What it is | Why moved |
|------|-----------|-----------|
| `andes_vsg_env.py` | V1 Kundur 4-VSG baseline | Superseded by V4; V4 inlines V1's `_build_system` + `_apply_disturbance`. |
| `andes_vsg_env_v2.py` | V2 (hetero D₀, expanded action range) | Sweep variant, never paper baseline. Findings: D₀=[20,16,4,8] is paper-deviation, not paper convention. |
| `andes_vsg_env_v3.py` | V3 (V2 + IEEEG1/EXST1 via `_pre_setup_addons`) | Stepping stone. R10 forensic fix lives in V4 directly. |
| `andes_ne_env.py` | New England 39-bus GENCLS env | M₀<20 → TDS divergence; never reached training. |
| `andes_ne_regca1_env.py` | New England 39-bus + REGCA1 | 6 algebraic+state-var DAE bloat; never converged. |

For the deviations log and R10–R16 forensic context, see
`memory/rounds/R10/verdict.md` and the V4 module docstring.
