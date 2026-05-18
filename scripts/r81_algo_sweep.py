"""R81 algorithm-side sweep launcher — 9 wave sequential single-seed × 75 ep smoke.

每个 wave = R72_w4 baseline hyper + 1 改动. seed s54 全 wave 一致.
完成后 train.py --final-eval 自动写 results/<save-dir>/final_eval_summary.json
含 6-axis geo + cum_rf.

不并行 (ANDES 单 WSL session 限制 + 16C 物理). Sequential.
每 wave ~11 min wall (R72_w4 实测 75 ep), 总 ~100 min.

Output:
    results/r81_w{1..9}_<short>_s54/                (per-wave train + eval dir)
    results/r81_w{1..9}_<short>_s54_stdout.log     (per-wave train log)
    results/r81_summary.json                       (top-level summary collected here)
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SEED = 54  # R72_w4_LSTM_s54 同 seed
EPISODES = 75

# R72_w4 baseline (从 results/r72_w4_lstm_tau001_warmup5_s54_stdout.log + training_log.json 反推)
BASELINE_CLI = [
    "--algo", "td3_lstm",
    "--episodes", str(EPISODES),
    "--seed", str(SEED),
    "--hidden-size", "64",
    "--tau", "0.001",
    "--lstm-lr-warmup-eps", "5",
    "--normalize-actions",
    "--final-eval",
]

# 9 wave 定义. 每条 = (wave_id, short_desc, extra_cli, extra_env)
WAVES: list[tuple[str, str, list[str], dict[str, str]]] = [
    # ─── Tier 1: obs / reward augmentation ────────────────────────────
    ("w1", "time_obs",          [], {"INCLUDE_TIME_OBS": "1"}),
    ("w2", "own_action_obs",    [], {"INCLUDE_OWN_ACTION_OBS": "1"}),
    ("w3", "phi_settle10",      ["--phi-settle", "10.0"], {}),
    ("w4", "lambda_smooth_neg1",[], {"LAMBDA_SMOOTH": "-1.0"}),
    ("w5", "time_phi_settle",   ["--phi-settle", "10.0"], {"INCLUDE_TIME_OBS": "1"}),
    # ─── Tier 2: algo / hyper sweep ──────────────────────────────────
    ("w6", "sac_h128",          ["--algo", "sac", "--hidden-size", "128"], {}),
    ("w7", "td3_h128",          ["--algo", "td3", "--hidden-size", "128"], {}),
    ("w8", "lstm_h128",         ["--hidden-size", "128"], {}),  # override baseline hidden=64
    ("w9", "lstm_gamma095",     ["--gamma", "0.95"], {}),
]


def _build_cli(wave_id: str, short: str, extra_cli: list[str]) -> tuple[list[str], Path, Path]:
    """Build train.py CLI list + return save_dir + stdout_log paths."""
    save_dir = ROOT / "results" / f"r81_{wave_id}_{short}_s{SEED}"
    stdout_log = ROOT / "results" / f"r81_{wave_id}_{short}_s{SEED}_stdout.log"
    cli = ["python3", str(ROOT / "scripts" / "train.py")]
    cli += BASELINE_CLI
    # Wave-specific override: replace baseline elements if conflict (e.g. --algo, --hidden-size)
    # Simple approach: walk extra_cli, if its --flag appears in baseline, remove baseline copy first.
    extra_flags = {extra_cli[i] for i in range(0, len(extra_cli), 2) if extra_cli[i].startswith("--")}
    filtered_baseline: list[str] = []
    skip = False
    for tok in cli[2:]:  # skip ["python3", train.py]
        if skip:
            skip = False
            continue
        if tok in extra_flags:
            skip = True
            continue
        filtered_baseline.append(tok)
    cli = cli[:2] + filtered_baseline + extra_cli
    cli += ["--save-dir", str(save_dir)]
    return cli, save_dir, stdout_log


def _run_wave(wave_id: str, short: str, extra_cli: list[str],
              extra_env: dict[str, str]) -> dict[str, Any]:
    cli, save_dir, stdout_log = _build_cli(wave_id, short, extra_cli)
    env = os.environ.copy()
    env.update(extra_env)
    # Clear any conflicting env var so wave is isolated
    if "INCLUDE_TIME_OBS" not in extra_env:
        env.pop("INCLUDE_TIME_OBS", None)
    if "INCLUDE_OWN_ACTION_OBS" not in extra_env:
        env.pop("INCLUDE_OWN_ACTION_OBS", None)
    if "LAMBDA_SMOOTH" not in extra_env:
        env.pop("LAMBDA_SMOOTH", None)

    print(f"\n========== R81-{wave_id} ({short}) ==========")
    print(f"  cli: {' '.join(cli)}")
    print(f"  env extras: {extra_env}")
    print(f"  save_dir: {save_dir}")

    save_dir.mkdir(parents=True, exist_ok=True)
    with open(stdout_log, "w", encoding="utf-8") as logf:
        proc = subprocess.run(cli, env=env, stdout=logf, stderr=subprocess.STDOUT,
                              cwd=str(ROOT))
    print(f"  exit code: {proc.returncode}")

    # Pull final_eval_summary.json
    fe = save_dir / "final_eval_summary.json"
    if not fe.exists():
        return {"wave": wave_id, "short": short, "exit": proc.returncode,
                "error": "no final_eval_summary.json"}
    summary = json.loads(fe.read_text(encoding="utf-8"))
    return {"wave": wave_id, "short": short, "exit": proc.returncode,
            "save_dir": str(save_dir.relative_to(ROOT)),
            "geo": summary.get("geo"),
            "cum_rf": summary.get("cum_rf"),
            "LS1": summary.get("LS1"), "LS2": summary.get("LS2"),
            "cum_rf_LS1": summary.get("cum_rf_LS1"),
            "cum_rf_LS2": summary.get("cum_rf_LS2"),
            }


def main():
    grand: dict[str, Any] = {"baseline": "r72_w4_lstm_tau001_warmup5_s54 (geo=0.391)",
                              "seed": SEED, "episodes": EPISODES, "waves": []}
    out_path = ROOT / "results" / "r81_summary.json"

    for wave_id, short, extra_cli, extra_env in WAVES:
        rec = _run_wave(wave_id, short, extra_cli, extra_env)
        grand["waves"].append(rec)
        # Incremental flush so a crash mid-sweep keeps partial data
        out_path.write_text(json.dumps(grand, indent=2, default=str), encoding="utf-8")
        if rec.get("geo") is not None:
            print(f"  geo = {rec['geo']:.4f} (vs baseline 0.391, "
                  f"Δ = {rec['geo'] - 0.391:+.4f})")

    print("\n========== R81 sweep done ==========")
    for r in grand["waves"]:
        g = r.get("geo")
        gstr = f"{g:.4f}" if isinstance(g, (int, float)) else "ERR"
        print(f"  R81-{r['wave']:3s} ({r['short']:20s}): geo={gstr} cum_rf={r.get('cum_rf')}")
    print(f"\nSummary: {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
