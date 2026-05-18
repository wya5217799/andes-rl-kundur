"""R80 Cycle 3c audit — V5_regca1 + no_disturb 7-step TDS fail 详细诊断.

只跑一个 case: V5_regca1 + no_disturbance + 50 step zero action, 把每一步
ss.TDS.converged + DAE residual + 哪些 variable 触发 fail 都打出来.

不写 JSON, 只 stdout. 目标是找 cycle 3c 的最小修复点.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from andes_rl_kundur.env.andes.andes_vsg_env_v5 import AndesMultiVSGEnvV5
from andes_rl_kundur.env.andes.v5_config import V5Config


def main():
    env = AndesMultiVSGEnvV5(
        random_disturbance=False, comm_fail_prob=0.0,
        config=V5Config.v5_default(),
    )
    env.seed(42)
    env.STEPS_PER_EPISODE = 50
    obs = env.reset(delta_u=None)  # zero disturbance
    print(f"[reset] N={env.N_AGENTS}, ss.TDS.converged={env.ss.TDS.converged}")
    print(f"[reset] ss.PFlow.converged={env.ss.PFlow.converged}")
    print(f"[reset] REGCA1 records={env.ss.REGCA1.n}, REECA1={env.ss.REECA1.n}")
    print(f"[reset] GENROU active={sum(int(u) for u in env.ss.GENROU.u.v)}/{env.ss.GENROU.n}")
    print(f"[reset] freq_hz init = {env._get_freq_hz() if hasattr(env, '_get_freq_hz') else 'n/a'}")

    # 直接看 ANDES TDS state
    print(f"[reset] TDS.config.tf = {env.ss.TDS.config.tf}")
    print(f"[reset] TDS time t = {env.ss.dae.t}")

    N = env.N_AGENTS
    for step in range(50):
        actions = {i: np.zeros(2, dtype=np.float32) for i in range(N)}
        obs, rewards, done, info = env.step(actions)
        ok = not info.get("tds_failed", False)
        t = info.get("time", -1.0)
        freq = info.get("freq_hz")
        max_dev = float(np.max(np.abs(np.asarray(freq) - 50.0))) if freq is not None else None
        print(f"step {step:02d}: t={t:.3f} ok={ok} max_dev={max_dev} "
              f"tds.converged={env.ss.TDS.converged} done={done}")
        if not ok or done:
            print(f"  ** TDS_FAILED at step {step}, t={t} **")
            print(f"  REGCA1 Pe = {list(env.ss.REGCA1.Pe.v) if hasattr(env.ss.REGCA1, 'Pe') else 'n/a'}")
            print(f"  REGCA1 Ipcmd = {list(env.ss.REGCA1.Ipcmd.v) if hasattr(env.ss.REGCA1, 'Ipcmd') else 'n/a'}")
            print(f"  REGCA1 omega-like = {list(env.ss.REGCA1.__dict__.get('a').v) if 'a' in env.ss.REGCA1.__dict__ else 'n/a'}")
            print(f"  GENCLS omega = {list(env.ss.GENCLS.omega.v)}")
            print(f"  GENROU u (G4 should be 0): {list(env.ss.GENROU.u.v)}")
            print(f"  GENROU active syn omega = {[env.ss.GENROU.omega.v[i] for i in range(env.ss.GENROU.n) if env.ss.GENROU.u.v[i] > 0]}")
            break
    env.close()


if __name__ == "__main__":
    main()
