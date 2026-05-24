"""R80 Phase A — V5 env zero-action sanity 探针.

RED expectation:
    1.  V5Config.v5_default() + AndesMultiVSGEnvV5 能正常实例化, reset 不 crash.
    2.  LS1 + LS2 anchor 扰动 + 50 步 zero action, traces 不空.
    3.  max_df > 0 (有扰动响应), 不是 flatline.
    4.  跟 V4 zero-action 对比 4 个数: max_df / final_df / settling / cum_rf.

paper 沉默 framing 下 (ADR-0004), 没有硬通过判据 — 只记数. 数对了进 Phase B.

Output: probes/r80_v5_zero_action.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from andes_rl_kundur.env.andes.andes_vsg_env_v4 import AndesMultiVSGEnvV4  # noqa: E402
from andes_rl_kundur.env.andes.andes_vsg_env_v5 import AndesMultiVSGEnvV5  # noqa: E402
from andes_rl_kundur.env.andes.v4_config import V4Config  # noqa: E402
from andes_rl_kundur.env.andes.v5_config import V5Config  # noqa: E402
from andes_rl_kundur.probes.andes_common.paper_constants import SCENARIOS  # noqa: E402

# Cycle 3a (TDD vertical bisection): 加一个最弱 scenario "no_disturb",
# 测 V5_regca1 在零扰动下能否 hold steady. 通过 → 知道是扰动响应崩;
# 不通过 → 是 init / 参数 / G4 链 disable 残留干扰.
SCENARIOS = dict(SCENARIOS)
SCENARIOS["no_disturb"] = {}


PROBE_OUT = ROOT / "probes" / "r80_v5_zero_action.json"
SEED = 42
N_STEPS = 50  # 10 s @ 0.2 s = 50 步 (paper Sec.IV-A)


def _run_one(env_cls, env_cfg, scenario_name):
    """跑一个 env + scenario zero-action episode, 抓 freq trace + 6-axis 数."""
    env = env_cls(random_disturbance=False, comm_fail_prob=0.0, config=env_cfg)
    env.seed(SEED)
    env.STEPS_PER_EPISODE = N_STEPS
    obs = env.reset(delta_u=SCENARIOS[scenario_name])

    N = env.N_AGENTS
    freq_traces = []   # 时间序列 (T, N)
    times = []
    cum_rf = 0.0
    for step in range(N_STEPS):
        actions = {i: np.zeros(2, dtype=np.float32) for i in range(N)}
        obs, rewards, done, info = env.step(actions)
        if info.get("tds_failed"):
            break
        freq_traces.append(list(info["freq_hz"].astype(float)))
        times.append(float(info["time"]))
        # cum_rf paper Sec.IV-C global form: -sum_t sum_i (f_i - mean_f)^2
        f_t = np.asarray(info["freq_hz"], dtype=float)
        f_bar = float(f_t.mean())
        cum_rf += -float(((f_t - f_bar) ** 2).sum())
        if done:
            break
    env.close()

    if not freq_traces:
        return {"n_steps": 0, "error": "no traces collected"}

    arr = np.asarray(freq_traces)  # (T, N)
    # ANDES kundur_full.xlsx 的 nominal 是 50 Hz (paper Sec.IV-A 一致).
    # 此前的探针误写 60 是 ANDES library 默认混淆, freq_trace 实测在 50 附近.
    nominal = 50.0
    dfreq = arr - nominal
    abs_dfreq = np.abs(dfreq)
    max_df_per_t = abs_dfreq.max(axis=1)  # (T,)
    max_df = float(max_df_per_t.max())
    final_df = float(abs_dfreq[-1].max())
    # settling: 时间 t > 3 s 后是否所有 |df| < 0.05? 简化版.
    settled = bool((times[-1] >= 3.0) and (abs_dfreq[-1] < 0.05).all())
    return {
        "n_steps": len(freq_traces),
        "max_df_hz": max_df,
        "final_df_hz": final_df,
        "settled_3s_below_005": settled,
        "cum_rf_global": cum_rf,
        "t_end_s": float(times[-1]),
        "freq_trace_first": freq_traces[0],
        "freq_trace_last": freq_traces[-1],
    }


def main():
    PROBE_OUT.parent.mkdir(parents=True, exist_ok=True)
    out = {"seed": SEED, "n_steps": N_STEPS, "results": {}}

    for label, env_cls, env_cfg in [
        ("V4_baseline",        AndesMultiVSGEnvV4, V4Config.paper_faithful()),
        ("V5_w2_only",         AndesMultiVSGEnvV5, V5Config.v5_default()),         # cycle 3c GREEN candidate
        ("V5_regca1_both",     AndesMultiVSGEnvV5, V5Config.v5_regca1_both()),     # cycle 3a RED record
        ("V5_gencls_fall",     AndesMultiVSGEnvV5, V5Config.v4_plant_fallback()),
    ]:
        out["results"][label] = {}
        for scen in ("no_disturb", "load_step_1", "load_step_2"):
            try:
                rec = _run_one(env_cls, env_cfg, scen)
            except Exception as e:
                import traceback
                rec = {"error": f"{type(e).__name__}: {e}",
                       "traceback": traceback.format_exc().splitlines()[-8:]}
            out["results"][label][scen] = rec
            # 增量写盘
            PROBE_OUT.write_text(json.dumps(out, indent=2, default=str))
            print(f"{label}/{scen}:", json.dumps(rec, indent=2, default=str)[:400])

    print("\n--- summary ---")
    for label in out["results"]:
        for scen in out["results"][label]:
            r = out["results"][label][scen]
            if "error" in r:
                print(f"  {label}/{scen}: ERROR {r['error'][:80]}")
            else:
                print(f"  {label}/{scen}: max_df={r['max_df_hz']:.4f} "
                      f"final_df={r['final_df_hz']:.4f} "
                      f"cum_rf={r['cum_rf_global']:.4e} "
                      f"n_steps={r['n_steps']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
