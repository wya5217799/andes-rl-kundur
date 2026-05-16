"""7-axis paper-alignment evaluator for ANDES Kundur 4-VSG traces.

v2 改进 (2026-05-09):
  - Axis 6: _action_utilization 替代 _box_containment
      旧: box containment 因 proj 动作范围 [-5,+15] 恒在 paper 框 [-100,+300] 内
          → 所有 ckpt 恒得 1.0 (退化轴, 无鉴别力)
      新: proj_span / paper_span → 真实衡量 agent 动作空间利用率
          项目 ΔH span≈5, paper span=400 → score≈0.013 (正确暴露 1.3% 利用率)
  - Axes 4-5: 对所有轨迹计算 (移除 is_ddic 门控)
      旧: DDIC=6轴, non-DDIC=3轴 → 轴数不等, 几何均值分母不一致
      新: 统一 5 轴基础 (1-5); no-ctrl ΔH/ΔD≈0 → smoothness score≈1.0 (正确)
  - Axes 6-7: DDIC 专属 (action utilization + improvement vs no-ctrl)
      no-ctrl 无动作, 这两轴语义不适用
  - Axis 7 (新): improvement_vs_no_ctrl
      自动搜索 eval_dir 中同 scenario 的 no_ctrl 参考轨迹
      存在时: score = (no_ctrl_max_df - ctrl_max_df) / no_ctrl_max_df
      不存在: 跳过 (不惩罚, 不计入几何均值)
  - 几何均值语义修正:
      旧注释: "任何轴 0 → 总分 0" (错误)
      实际: soft-clamp max(s, 0.01) per axis; 轴得 0.0 → 贡献 log(0.01)≈-4.6,
            强力拉低但不归零总分 (防止 log(-∞) 数值溢出)
  - 容差来源: TOL 各键现附推导注释

Axes (论文 benchmark = 1.0, 项目越接近越高):
  1. max_|Δf|_Hz      峰值偏差          论文 LS1=0.13 / LS2=0.10 Hz
  2. final_|Δf|@6s    6s 残值           论文 LS1=0.08 / LS2=0.05 Hz
  3. settling_s       收敛时刻          论文 LS1=3.0  / LS2=2.5 s
  4. dH_smoothness    ΔH 步间抖动 std   论文 ≈0 (DDIC 平稳控制)
  5. dD_smoothness    ΔD 步间抖动 std   论文 ≈0
  6. dH_utilization   ΔH 动作利用率     proj_span/paper_span (all traces; no-ctrl→score≈0)
  7. dD_utilization   ΔD 动作利用率     proj_span/paper_span (all traces; no-ctrl→score≈0)
  8. improvement      vs no-ctrl 改善   (no_ctrl_df-ctrl_df)/no_ctrl_df [DDIC+ref]

总分 = geometric mean(axes), soft-clamp 0.01 per axis

Usage:
    python evaluation/paper_grade_axes.py [eval_dir]

Default eval_dir = results/andes_eval_paper_specific_v2_envV2_hetero/
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import numpy as np


# ─── Paper benchmarks (Yang2023 Fig.6/7/8/9, 2026-05-06 visual extraction) ──

@dataclass(frozen=True)
class PaperBenchmark:
    scenario: str
    max_abs_df_Hz: float           # DDIC target (Fig.7/9)
    final_abs_df_Hz: float         # DDIC residual at 6s
    settling_to_residual_s: float  # DDIC settling time
    dH_avg_smooth_std: float       # ideal = 0
    dD_avg_smooth_std: float       # ideal = 0
    dH_range: tuple[float, float]  # Eq.12 action box (NOT span benchmark)
    dD_range: tuple[float, float]
    # no_ctrl_max_abs_df_Hz: paper Fig.6/8 no-control peak |Δf|.
    # 0.0 = unknown → Axis 8 (improvement) disabled for this scenario.
    # TODO: extract from paper Fig.6/8 no-ctrl traces and fill in.
    no_ctrl_max_abs_df_Hz: float = 0.0
    note: str = ""


PAPER = {
    "load_step_1": PaperBenchmark(
        scenario="load_step_1",
        max_abs_df_Hz=0.13, final_abs_df_Hz=0.08, settling_to_residual_s=3.0,
        dH_avg_smooth_std=0.0, dD_avg_smooth_std=0.0,
        dH_range=(-100.0, 300.0), dD_range=(-200.0, 600.0),
        no_ctrl_max_abs_df_Hz=0.0,
        note="DDIC target=Fig.7; action box=Eq.12 Sec.IV-B; no_ctrl_max_df=TBD(Fig.6)",
    ),
    "load_step_2": PaperBenchmark(
        scenario="load_step_2",
        max_abs_df_Hz=0.10, final_abs_df_Hz=0.05, settling_to_residual_s=2.5,
        dH_avg_smooth_std=0.0, dD_avg_smooth_std=0.0,
        dH_range=(-100.0, 300.0), dD_range=(-200.0, 600.0),
        no_ctrl_max_abs_df_Hz=0.0,
        note="DDIC target=Fig.9; action box=Eq.12 Sec.IV-B; no_ctrl_max_df=TBD(Fig.8)",
    ),
}


# Tolerances: half-width around paper value at which score → 0.
# Derivation documented per key.
TOL = dict(
    # max_df=0.10: paper LS1=0.13 Hz → band [0.03, 0.23] for >0 score.
    # ≈77% of paper value; one "decade" of signal magnitude.
    max_df=0.10,
    # final_df=0.06: paper LS1=0.08 Hz → band [0.02, 0.14].
    # ≈75% of paper value; tighter than max_df (steady-state more predictable).
    final_df=0.06,
    # settling=4.0 s: paper LS1=3.0 s → band [0, 7 s].
    # Loose to avoid ∞-settling penalty dominating geometric mean.
    settling=4.0,
    # dH_smooth=10: step-change std ≤ 10 for >0 score.
    # DM_MAX=30 → tolerance ≈ 1/3 of full action range (engineering judgment).
    dH_smooth=10.0,
    # dD_smooth=30: DD range [-10, 30] → tolerance = full DD range.
    # D control noisier than H; looser band appropriate.
    dD_smooth=30.0,
)


@dataclass
class AxisScore:
    name: str
    project_value: float
    paper_value: float
    score: float
    note: str = ""


@dataclass
class TraceScore:
    label: str
    scenario: str
    is_ddic: bool
    axes: list[AxisScore] = field(default_factory=list)
    overall: float = 0.0

    def summary(self) -> str:
        lines = [f"\n=== {self.label} / {self.scenario} (DDIC={self.is_ddic}) ==="]
        for a in self.axes:
            bar = int(a.score * 20) * "#" + int((1 - a.score) * 20) * "."
            extra = f"  {a.note}" if a.note else ""
            lines.append(
                f"  {a.name:24s} project={a.project_value:8.3f}  paper={a.paper_value:8.3f}  "
                f"score={a.score:.2f}  [{bar}]{extra}"
            )
        n = len(self.axes)
        lines.append(
            f"  {'OVERALL (geo mean)':24s} {'':>8s}  {'':>8s}  "
            f"score={self.overall:.3f}  [{n} axes]"
        )
        return "\n".join(lines)


# ─── Scoring helpers ──────────────────────────────────────────────────────────

def _tol_score(project: float, paper: float, tol: float) -> float:
    return float(max(0.0, 1.0 - abs(project - paper) / tol))


def _settling_time(t: np.ndarray, df: np.ndarray, residual_band_Hz: float = 0.02,
                   final_df_Hz: float = 0.0, dt_window: float = 0.5) -> float:
    """Time after which max|Δf - final_df| stays < residual_band_Hz over dt_window window."""
    max_per_t = np.max(np.abs(df), axis=1)
    deviation_from_residual = np.abs(max_per_t - final_df_Hz)
    dt = float(np.median(np.diff(t))) if len(t) > 1 else 1e-6
    n_window = max(1, int(dt_window / max(dt, 1e-6)))
    for i in range(len(t) - n_window):
        if np.all(deviation_from_residual[i : i + n_window] < residual_band_Hz):
            return float(t[i])
    return float("inf")


def _hf_std(arr: np.ndarray) -> float:
    """High-freq oscillation: step-to-step diff std of avg curve over agents."""
    avg = arr.mean(axis=1)
    return float(np.std(np.diff(avg)))


def _action_range(arr: np.ndarray) -> tuple[float, float]:
    """Min/max of the CROSS-AGENT MEAN curve over time.

    R50 opt D — explicit naming to prevent misinterpretation.
    ``arr`` is shape (T, N_agents) — typically ``H - H[0]`` or ``D - D[0]``
    (the state delta from t=0 per agent, over the first 6 seconds).
    We FIRST average across the N agents at each timestep, THEN take min/max
    of the resulting 1-D time series. This is NOT the per-step action
    magnitude and NOT the per-agent action range — it is specifically the
    excursion of the **collective mean** over the response window.

    Two counter-intuitive consequences (R49 audit, CLM-0057):
      * An agent emitting large but TEMPORALLY-FLAT actions scores LOW
        because the mean curve barely moves.
      * Four agents emitting large but UNCORRELATED actions can score LOW
        because cross-agent cancellation flattens the mean.
    See ``_action_utilization`` for the score derived from this range.
    """
    avg = arr.mean(axis=1)
    return float(avg.min()), float(avg.max())


def _action_utilization(proj_span: float, paper_span: float) -> float:
    """Fraction of paper action range actually used: proj_span / paper_span, clipped [0, 1].

    score = 1.0 → agent uses full paper range or more
    score → 0   → agent barely moves (e.g. proj_span=5, paper_span=400 → 1.3%)

    Replaces _box_containment (R07 Bug-A, 2026-05-07):
      old logic: check proj range ⊂ paper box → trivially 1.0 for all ckpts
                 (project DH ∈ [-5,+15] is always inside box [-100,+300])
      new logic: measures how much of available space agent actually exploits.

    IMPORTANT (R50 opt D, post-R49 diagnostic):
      ``proj_span`` and ``paper_span`` are SPANS (max - min) of the
      cross-agent-mean curve over the first 6 seconds — see ``_action_range``.
      They are NOT per-step action magnitudes. A policy that pushes a
      large action at the disturbance and holds (TD3-style static setpoint,
      R48-β / R49 default behavior) will score LOW on this axis even if
      the instantaneous |delta_M| reaches the upper action bound. The
      bottleneck for this axis is **temporal variation of the collective
      mean**, not raw action authority.

    >>> _action_utilization(50.0, 400.0)
    0.125
    >>> _action_utilization(400.0, 400.0)
    1.0
    >>> _action_utilization(600.0, 400.0)
    1.0
    >>> _action_utilization(0.0, 400.0)
    0.0
    """
    if paper_span < 1.0:
        return 1.0
    return float(min(1.0, max(0.0, proj_span / paper_span)))


def _improvement_score(ctrl_max_df: float, no_ctrl_max_df: float) -> Optional[float]:
    """Relative frequency improvement over no-control baseline.

    score = (no_ctrl - ctrl) / no_ctrl, clipped [0, 1].
    Returns None when no_ctrl_max_df <= 0 (reference unavailable → axis skipped).

    score = 1.0: ctrl eliminates deviation completely
    score = 0.0: ctrl same or worse than no-ctrl
    """
    if no_ctrl_max_df <= 0.0:
        return None
    return float(max(0.0, min(1.0, (no_ctrl_max_df - ctrl_max_df) / no_ctrl_max_df)))


def _load_no_ctrl_max_df(eval_dir: Path, scenario: str) -> float:
    """Find a no-control reference trace in eval_dir and return its max |Δf| (6s window).

    Naming conventions tried in order:
      noctrl_{scenario}.json
      no_ctrl_{scenario}.json
      baseline_{scenario}.json

    Returns 0.0 if not found or trace is invalid.
    """
    candidates = [
        eval_dir / f"noctrl_{scenario}.json",
        eval_dir / f"no_ctrl_{scenario}.json",
        eval_dir / f"no_control_{scenario}.json",
        eval_dir / f"baseline_{scenario}.json",
    ]
    for path in candidates:
        if not path.exists():
            continue
        try:
            with open(path, encoding='utf-8') as _f:
                j = json.load(_f)
            tr = j.get("traces", [])
            if not tr or j.get("tds_failed"):
                continue
            df = np.array([s["delta_f_es"] for s in tr])
            if np.isnan(df).any():
                continue
            t0 = tr[0]["t"]
            mask_6s = np.array([s["t"] for s in tr]) <= t0 + 6.0
            return float(np.max(np.abs(df[mask_6s])))
        except Exception:
            continue
    return 0.0


# ─── Main evaluator ───────────────────────────────────────────────────────────

def evaluate_trace(trace_json_path: Path, paper: PaperBenchmark, is_ddic: bool,
                   label: str, no_ctrl_max_df: float = 0.0) -> TraceScore:
    """Compute up to 8-axis score for one trace JSON.

    Axes 1-7 apply to ALL traces (frequency alignment, smoothness, action utilization).
    For no-ctrl traces axes 6-7 score near 0 (no action → no utilization), which is correct.
    Axis 8 applies to DDIC only when a no-ctrl reference is available.

    Args:
        trace_json_path: Path to trace JSON (keys: 'traces', 'tds_failed').
        paper: PaperBenchmark for this scenario.
        is_ddic: True if this trace uses RL (DDIC) control.
        label: Human-readable checkpoint label.
        no_ctrl_max_df: Max |Δf| of no-control trace for same scenario.
                        0 = unavailable → falls back to paper.no_ctrl_max_abs_df_Hz.
                        Still 0 after fallback → Axis 8 skipped.
    """
    with open(trace_json_path, encoding='utf-8') as _f:
        j = json.load(_f)
    tr = j["traces"]
    if not tr:
        return TraceScore(label=label, scenario=paper.scenario, is_ddic=is_ddic,
                          axes=[], overall=0.0)
    # C2.2 fix (r30): partial trace after TDS failure is not paper-comparable.
    if j.get("tds_failed") is True:
        return TraceScore(label=label, scenario=paper.scenario, is_ddic=is_ddic,
                          axes=[], overall=0.0)

    t = np.array([s["t"] for s in tr])
    df_full = np.array([s["delta_f_es"] for s in tr])
    H_full = np.array([s["M_es"] for s in tr]) / 2.0   # M = 2H convention
    D_full = np.array([s["D_es"] for s in tr])

    # C2.1 fix (r30): NaN in any field invalidates the whole trace.
    if np.isnan(df_full).any() or np.isnan(H_full).any() or np.isnan(D_full).any():
        return TraceScore(label=label, scenario=paper.scenario, is_ddic=is_ddic,
                          axes=[], overall=0.0)

    # B1 fix (r28): settling uses FULL trace (not truncated to 6s) to avoid
    # misreporting ∞ for controllers that settle between 6-10 s.
    # B2 fix (r28): band around own final residual (not paper residual) to avoid
    # double-penalising project-vs-paper steady-state mismatch.
    own_final_df = float(np.max(np.abs(df_full[-1])))
    proj_settling = _settling_time(t, df_full, residual_band_Hz=0.02,
                                   final_df_Hz=own_final_df)

    # Other axes use 6s window for direct paper-Fig comparison.
    mask_6s = t <= t[0] + 6.0
    df = df_full[mask_6s]
    H = H_full[mask_6s]
    D = D_full[mask_6s]

    dH = H - H[0:1]
    dD = D - D[0:1]

    proj_max_df = float(np.max(np.abs(df)))
    proj_final_df = float(np.abs(df[-1]).max())
    proj_dH_std = _hf_std(dH)
    proj_dD_std = _hf_std(dD)
    proj_dH_min, proj_dH_max = _action_range(dH)
    proj_dD_min, proj_dD_max = _action_range(dD)
    proj_dH_span = proj_dH_max - proj_dH_min
    proj_dD_span = proj_dD_max - proj_dD_min
    paper_dH_span = paper.dH_range[1] - paper.dH_range[0]
    paper_dD_span = paper.dD_range[1] - paper.dD_range[0]

    # ── Axes 1-3: frequency alignment (ALL traces) ──
    settling_val = proj_settling if proj_settling != float("inf") else 99.0
    axes: list[AxisScore] = [
        AxisScore("max_|df|_Hz", proj_max_df, paper.max_abs_df_Hz,
                  _tol_score(proj_max_df, paper.max_abs_df_Hz, TOL["max_df"])),
        AxisScore("final_|df|@6s", proj_final_df, paper.final_abs_df_Hz,
                  _tol_score(proj_final_df, paper.final_abs_df_Hz, TOL["final_df"])),
        AxisScore("settling_s", settling_val, paper.settling_to_residual_s,
                  _tol_score(settling_val, paper.settling_to_residual_s, TOL["settling"])),
    ]

    # ── Axes 4-5: smoothness (ALL traces, no is_ddic gate) ──
    # no-ctrl: ΔH/ΔD ≈ 0 throughout → std ≈ 0 → score ≈ 1.0 (correct: no action = maximally smooth)
    # DDIC: varies with policy quality → meaningful diagnostic signal
    axes.append(AxisScore("dH_smoothness", proj_dH_std, paper.dH_avg_smooth_std,
                          max(0.0, 1.0 - proj_dH_std / TOL["dH_smooth"])))
    axes.append(AxisScore("dD_smoothness", proj_dD_std, paper.dD_avg_smooth_std,
                          max(0.0, 1.0 - proj_dD_std / TOL["dD_smooth"])))

    # ── Axes 6-7: action utilization (ALL traces) ──
    # Measures what fraction of the paper action space the agent actually exploits.
    # IMPORTANT (2026-05-10 fix): applied to ALL traces, not just DDIC, otherwise
    # no-control trace (5 axes) would unfairly outscore DDIC (8 axes) due to
    # geometric-mean denominator mismatch. For no-control: proj_span ≈ 0 → score ≈ 0,
    # correctly penalising "no action at all" as poor utilization of the action space.
    axes.append(AxisScore(
        "dH_utilization", proj_dH_span, paper_dH_span,
        _action_utilization(proj_dH_span, paper_dH_span),
        note=f"proj=[{proj_dH_min:+.1f},{proj_dH_max:+.1f}] paper_span={paper_dH_span:.0f}",
    ))
    axes.append(AxisScore(
        "dD_utilization", proj_dD_span, paper_dD_span,
        _action_utilization(proj_dD_span, paper_dD_span),
        note=f"proj=[{proj_dD_min:+.1f},{proj_dD_max:+.1f}] paper_span={paper_dD_span:.0f}",
    ))

    # ── Axis 8: improvement vs no-ctrl baseline (DDIC only, optional) ──
    # Falls back to paper benchmark's no_ctrl field if no runtime reference was found.
    if is_ddic:
        ref = no_ctrl_max_df if no_ctrl_max_df > 0.0 else paper.no_ctrl_max_abs_df_Hz
        impr = _improvement_score(proj_max_df, ref)
        if impr is not None:
            axes.append(AxisScore(
                "improvement_vs_noctrl", proj_max_df, ref, impr,
                note=f"ctrl={proj_max_df:.3f} noctrl_ref={ref:.3f}",
            ))

    # Geometric mean with soft-clamp at 0.01 per axis.
    # Soft-clamp prevents log(-∞) on zero-scoring axes.
    # A zero-scoring axis contributes log(0.01)≈-4.6 to the log-sum,
    # pulling the overall score down sharply (but not to 0).
    scores = [a.score for a in axes]
    overall = math.exp(sum(math.log(max(s, 0.01)) for s in scores) / len(scores))
    return TraceScore(label=label, scenario=paper.scenario, is_ddic=is_ddic,
                      axes=axes, overall=overall)


def rank_models(eval_dir: Path, ckpt_labels: list[str]) -> list[tuple[str, float]]:
    no_ctrl_refs = {scen: _load_no_ctrl_max_df(eval_dir, scen)
                    for scen in ["load_step_1", "load_step_2"]}
    rankings = []
    for lbl in ckpt_labels:
        scores = []
        for scen in ["load_step_1", "load_step_2"]:
            p = eval_dir / f"{lbl}_{scen}.json"
            if not p.exists():
                continue
            ts = evaluate_trace(p, PAPER[scen], is_ddic=("ddic" in lbl),
                                label=lbl, no_ctrl_max_df=no_ctrl_refs[scen])
            scores.append(ts.overall)
        if scores:
            # C1 fix (r30): geometric mean across scenarios (consistent with per-trace geo mean).
            combined = math.exp(sum(math.log(max(x, 0.01)) for x in scores) / len(scores))
            rankings.append((lbl, combined))
    rankings.sort(key=lambda x: -x[1])
    return rankings


if __name__ == "__main__":
    import sys
    import os

    ROOT = Path(__file__).resolve().parents[1]
    eval_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else \
        ROOT / "results" / "andes_eval_paper_specific_v2_envV2_hetero"

    _NO_CTRL_PREFIXES = ("noctrl_", "no_ctrl_", "no_control_", "baseline_")

    files = os.listdir(eval_dir)
    labels = sorted(set(
        f.replace("_load_step_1.json", "").replace("_load_step_2.json", "")
        for f in files
        if f.endswith(".json")
        and not any(f.startswith(p) for p in _NO_CTRL_PREFIXES)
    ))

    no_ctrl_refs = {scen: _load_no_ctrl_max_df(eval_dir, scen)
                    for scen in ["load_step_1", "load_step_2"]}

    print(f"Eval dir: {eval_dir}")
    print(f"Found {len(labels)} ckpt labels")
    for scen, ref in no_ctrl_refs.items():
        if ref > 0:
            print(f"  no_ctrl ref [{scen}]: {ref:.3f} Hz  → Axis 8 enabled")
        else:
            print(f"  no_ctrl ref [{scen}]: NOT FOUND  → Axis 8 disabled")
    print()

    all_scores: list[TraceScore] = []
    for lbl in labels:
        for scen in ["load_step_1", "load_step_2"]:
            p = eval_dir / f"{lbl}_{scen}.json"
            if not p.exists():
                continue
            ts = evaluate_trace(p, PAPER[scen], is_ddic=("ddic" in lbl),
                                label=lbl, no_ctrl_max_df=no_ctrl_refs[scen])
            all_scores.append(ts)

    all_scores.sort(key=lambda x: -x.overall)

    print("=" * 100)
    print("TOP 6 (full breakdown)")
    print("=" * 100)
    for ts in all_scores[:6]:
        print(ts.summary())

    print("\n" + "=" * 100)
    print("RANKING by geometric mean(LS1, LS2) overall score")
    print("=" * 100)
    by_lbl: dict[str, list[float]] = {}
    for ts in all_scores:
        by_lbl.setdefault(ts.label, []).append(ts.overall)

    combined = sorted(
        [(lbl, math.exp(
            sum(math.log(max(x, 0.01)) for x in s) / len(s)
        )) for lbl, s in by_lbl.items() if len(s) == 2],
        key=lambda x: -x[1],
    )
    print(f"{'rank':>4s}  {'label':50s}  {'geo_overall':>12s}")
    for i, (lbl, s) in enumerate(combined, 1):
        marker = " <- BEST" if i == 1 else ""
        print(f"{i:4d}  {lbl:50s}  {s:12.3f}{marker}")
