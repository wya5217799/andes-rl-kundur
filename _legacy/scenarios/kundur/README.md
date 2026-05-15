# Frozen Kundur training scripts

Replaced by `scenarios/kundur/train.py` on 2026-05-16. Kept here so
historical commands in round verdicts (`memory/rounds/R*/verdict.md`,
`_legacy/CONTEXT.md`) remain interpretable.

**Do not run these.**

| File | What it was | Replacement |
|------|-------------|-------------|
| `train_andes.py` | The 21 KB historical train loop. Imported `env.andes_vsg_env` (broken since the V1 file is now under `_legacy/env/andes/`) and was only runnable via the `train_andes_v4.py` monkey-patch shim. | `scenarios/kundur/train.py` (direct V4 import, no shim). |
| `train_andes_v4.py` | Shim that monkey-patched `env.andes_vsg_env` to V4, then ran `train_andes.py` via `runpy`. | Same — the new `train.py` imports V4 directly. |
| `train_andes_warmstart.py` | Copy-paste fork of `train_andes.py` that added "load one shared actor checkpoint into all four agents." | `train.py --warmstart-shared <ckpt> [--warmstart-mode actor_only\|actor_and_critic]`. |

All three referenced `from env.andes_vsg_env import AndesMultiVSGEnv`,
which has not existed as a module since the V4-self-contained refactor.
The new `scenarios/kundur/train.py` imports `AndesMultiVSGEnvV4` from
`env.andes.andes_vsg_env_v4` directly — no shim, no monkey patch.
