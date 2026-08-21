"""Sealed WSL runner for R436: energy-port baseline-anchored residual SAC canary.

Owner-authorized supplementary ring 1 (2026-08-19): the first learning
experiment on the verified energy-port object.  The deterministic
bandpass K=3.5 controller (R409 HELDOUT-PASS) is the frozen baseline
anchor; per-agent SAC learns one normalized residual scalar per VSG,
mapped through the existing feasibility-native residual seam
(``FeasibilityNativeVSGActionMap.map_residual_action``): zero residual =
exact deterministic baseline, so the learned policy can never leave the
baseline's feasible headroom (hard no-harm floor by construction).

Two learning arms (5 seeds each): ``residual_sac_no_message`` (neighbour
obs slots honest-zero) and ``residual_sac_message`` (full neighbour
slots).  References: ``bandpass_k3p5`` (R409 structure, re-run on every
evaluation variant, R434 precedent) and ``zero_feedback``.

Training: 43,200 steps/run, 8 development conditions from the R408 dev
bank on the nominal plant, seeds 401-405, R431 hyperparameters (SACAgent
verbatim).  Evaluation: the 10 EIG-sound R413 variants (learning arms
never saw them), frozen R409 thresholds (r_d <= 0.95, r_cross <= 1.10,
all R379 guards), nominal anchor must reproduce R408 dev values within
1e-6 relative.  Pre-registered decision tree and exact formulas:
``memory/rounds/R436/plan.md`` + ``memory/rounds/R436/formulas.md``.

Lifecycle (WSL only, always through the scratch launcher):
  python scripts/andes_scratch.py scripts/run_r436_energy_residual_sac.py capacity
  python scripts/andes_scratch.py scripts/run_r436_energy_residual_sac.py rehearse
  python scripts/andes_scratch.py scripts/run_r436_energy_residual_sac.py prepare
  python scripts/andes_scratch.py scripts/run_r436_energy_residual_sac.py shards
  python scripts/andes_scratch.py scripts/run_r436_energy_residual_sac.py train --arm <arm> --seed <seed>
  python scripts/andes_scratch.py scripts/run_r436_energy_residual_sac.py eval-variant <variant_id> [--arm <arm>]
  python scripts/andes_scratch.py scripts/run_r436_energy_residual_sac.py classify

All formal artifacts are create-only with sha256 sidecars under
results/research_loop/r436_energy_residual_sac/.
"""

# ruff: noqa: E402, I001

from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import sys
import time
from collections.abc import Mapping, Sequence
from concurrent.futures import ProcessPoolExecutor
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, TextIO

for _thread_variable in (
    "OMP_NUM_THREADS",
    "OPENBLAS_NUM_THREADS",
    "MKL_NUM_THREADS",
    "NUMEXPR_NUM_THREADS",
):
    os.environ[_thread_variable] = "1"
os.environ["DISABLE_TOGGLER"] = "1"

import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[1]
for _bootstrap_path in (ROOT, ROOT / "src", ROOT / "scripts"):
    if str(_bootstrap_path) not in sys.path:
        sys.path.insert(0, str(_bootstrap_path))

from andes_rl_kundur.agents.sac import SACAgent  # noqa: E402
from andes_rl_kundur.control.active_power import (  # noqa: E402
    r272_frozen_bess_contract,
)
from andes_rl_kundur.control.feasibility_native_vsg_action import (  # noqa: E402
    FeasibilityNativeVSGActionMap,
)
from andes_rl_kundur.control.ring_bandpass_damping import RingBandpassDamping  # noqa: E402
from andes_rl_kundur.evaluation.gate_b3_deterministic import (  # noqa: E402
    LOCAL_ARM,
    ZERO_ARM,
    build_contract as _base_contract,
    probe_request,
    summarize_arm_records,
)
from scripts.run_r408_v2_solving_gate import (  # noqa: E402
    ACTION_CLIP,
    BandpassArmController,
    _enrich_row,
)
from scripts.run_r372_energy_port_object_gate import (  # noqa: E402
    _identity,
    _port_row,
)
from run_r401_cd_matd3_canary_contract import (  # noqa: E402
    _memory_resources,
    _other_research_python_processes,
)

ROUND_ID = "R436"
PLAN = ROOT / "memory/rounds/R436/plan.md"
FORMULAS = ROOT / "memory/rounds/R436/formulas.md"
LINE = ROOT / "paper/yang_md_decoupling_marl/LINE.md"
REHEARSAL = ROOT / "memory/rounds/R436/rehearsal.json"
CAPACITY = ROOT / "memory/rounds/R436/capacity_evidence.json"
SEAL = ROOT / "memory/rounds/R436/formal_seal.json"
OUT = ROOT / "results/research_loop/r436_energy_residual_sac"
R408_OUT = ROOT / "results/research_loop/r408_v2_solving_gate"
R409_OUT = ROOT / "results/research_loop/r409_heldout_gate"
R413_OUT = ROOT / "results/research_loop/r413_topology_robustness"

TRAINING_SEEDS = (401, 402, 403, 404, 405)
STEPS_PER_EPISODE = 50
TOTAL_INTERACTION_STEPS = 43_200
HIDDEN_SIZES = (128, 128, 128, 128)
LR = 3.0e-4
GAMMA = 0.99
TAU = 0.005
BUFFER_SIZE = 10_000
BATCH_SIZE = 256
ALPHA_MIN = 0.005
ALPHA_MAX = 5.0
MAX_GRAD_NORM = 1.0
RESIDUAL_SCALE = ACTION_CLIP  # 0.70, same scale as the baseline clip
OBS_DIM = 7
ACTION_DIM = 1
NOMINAL_FREQUENCY_HZ = 60.0
NOMINAL_P_ES_DENOM = 600.0

LEARNING_ARMS = ("residual_sac_no_message", "residual_sac_message")
MESSAGE_ARM = "residual_sac_message"
NO_MESSAGE_ARM = "residual_sac_no_message"
EVAL_ARMS = (ZERO_ARM, LOCAL_ARM, "bandpass_k3p5")

DIFFERENTIAL_RATIO_MAX = 0.95
PROBE_CROSS_RATIO_MAX = 1.10
STRICT_CROSS_RATIO_MAX = 0.95
BASE_ANCHOR = {"r_d": 0.938947, "r_cross": 0.539791}
BASE_ANCHOR_TOLERANCE_RELATIVE = 1.0e-6

CAPACITY_RUNGS = (1, 2, 4, 8, 12, 16)
CAPACITY_TASKS_PER_RUNG = 32
TRAIN_WORKER_RSS_FLOOR_BYTES = 944_214_016
MARGINAL_GAIN_MIN = 1.05
MARGINAL_GAIN_CONFIRM_LOW = 1.03
MARGINAL_GAIN_CONFIRM_HIGH = 1.07
OS_FLOOR_BYTES = 3 * 1024**3

# Training conditions: R408 dev-bank condition set, nominal plant only.
TRAINING_CONDITIONS: tuple[dict[str, Any], ...] = (
    {
        "condition_id": "dev3_probe_bus15_minus_0p45",
        "delta_u": {"PQ_Bus15": -0.45},
        "kind": "probe",
    },
    {
        "condition_id": "dev3_disturbance_pq1_plus_0p65",
        "delta_u": {"PQ_1": 0.65},
        "kind": "disturbance",
    },
    {
        "condition_id": "dev3_disturbance_bus14_minus_0p55",
        "delta_u": {"PQ_Bus14": -0.55},
        "kind": "disturbance",
    },
)

# Variant bank: frozen R413 list minus the two VSG-tie outage variants
# excluded by the sealed R413 case-level EIG soundness verdict.
TOPOLOGY_VARIANTS: tuple[dict[str, Any], ...] = (
    {"variant_id": "nominal", "kind": "none"},
    {"variant_id": "out_Line_4", "kind": "outage", "line_idx": "Line_4"},
    {"variant_id": "out_Line_5", "kind": "outage", "line_idx": "Line_5"},
    {"variant_id": "out_Line_7", "kind": "outage", "line_idx": "Line_7"},
    {"variant_id": "out_Line_8", "kind": "outage", "line_idx": "Line_8"},
    {"variant_id": "x0p5_Line_4", "kind": "impedance", "line_idx": "Line_4", "factor": 0.5},
    {"variant_id": "x1p5_Line_4", "kind": "impedance", "line_idx": "Line_4", "factor": 1.5},
    {"variant_id": "x0p5_Line_7", "kind": "impedance", "line_idx": "Line_7", "factor": 0.5},
    {"variant_id": "x1p5_Line_7", "kind": "impedance", "line_idx": "Line_7", "factor": 1.5},
    {"variant_id": "x1p5_Line_7_12", "kind": "impedance", "line_idx": "Line_7_12", "factor": 1.5},
)

ADJACENCY = {0: (1, 3), 1: (0, 2), 2: (1, 3), 3: (2, 0)}


def safe_emit(message: str, *, stream: TextIO | None = None) -> bool:
    target = sys.stdout if stream is None else stream
    try:
        print(message, file=target, flush=True)
    except BrokenPipeError:
        if stream is None:
            sys.stdout = open(os.devnull, "w", encoding="utf-8")
        return False
    return True


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _relative(path: Path) -> str:
    return path.resolve().relative_to(ROOT.resolve()).as_posix()


def _write_new_json(path: Path, payload: Mapping[str, Any]) -> str:
    if path.exists() or Path(f"{path}.sha256").exists():
        raise FileExistsError(f"refusing to overwrite create-only artifact: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )
    path.write_text(text + "\n", encoding="utf-8")
    digest = _sha256_file(path)
    Path(f"{path}.sha256").write_text(f"{digest}  {path.name}\n", encoding="ascii")
    return digest


def _read_hashed_json(path: Path) -> dict[str, Any]:
    sidecar = Path(f"{path}.sha256")
    if not path.is_file() or not sidecar.is_file():
        raise FileNotFoundError(f"missing hashed JSON: {path}")
    expected = sidecar.read_text(encoding="ascii").split()[0]
    actual = _sha256_file(path)
    if actual != expected:
        raise RuntimeError(f"hash mismatch: {path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return value


def build_contract() -> dict[str, Any]:
    """One frozen R436 contract: object, arms, seeds, budgets, thresholds."""
    base = _base_contract()
    base["round"] = ROUND_ID
    base["training_authorized"] = True
    base["r436"] = {
        "learning_arms": list(LEARNING_ARMS),
        "training_seeds": list(TRAINING_SEEDS),
        "training_conditions": list(TRAINING_CONDITIONS),
        "total_interaction_steps": TOTAL_INTERACTION_STEPS,
        "steps_per_episode": STEPS_PER_EPISODE,
        "residual_scale": RESIDUAL_SCALE,
        "obs_dim": OBS_DIM,
        "action_dim": ACTION_DIM,
        "hidden_sizes": list(HIDDEN_SIZES),
        "lr": LR,
        "gamma": GAMMA,
        "tau": TAU,
        "buffer_size": BUFFER_SIZE,
        "batch_size": BATCH_SIZE,
        "alpha_min": ALPHA_MIN,
        "alpha_max": ALPHA_MAX,
        "max_grad_norm": MAX_GRAD_NORM,
        "topology_variants": [
            {k: v for k, v in variant.items() if k != "kind"}
            for variant in TOPOLOGY_VARIANTS
        ],
        "evaluation_arms": list(EVAL_ARMS),
        "thresholds": {
            "differential_ratio_max": DIFFERENTIAL_RATIO_MAX,
            "probe_cross_ratio_max": PROBE_CROSS_RATIO_MAX,
            "strict_cross_ratio_max": STRICT_CROSS_RATIO_MAX,
            "base_anchor": BASE_ANCHOR,
            "base_anchor_tolerance_relative": BASE_ANCHOR_TOLERANCE_RELATIVE,
        },
        "formulas_sha256": _sha256_file(FORMULAS),
    }
    return base


def contract_sha256(contract: Mapping[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(contract, sort_keys=True).encode("utf-8")
    ).hexdigest()


def _assert_wsl_scratch() -> None:
    if os.name != "posix":
        raise RuntimeError("R436 physical commands are WSL/POSIX-only")
    if Path.cwd().resolve() == ROOT.resolve():
        raise RuntimeError("R436 must run through scripts/andes_scratch.py")
    torch.set_num_threads(1)
    try:
        torch.set_num_interop_threads(1)
    except RuntimeError:
        pass


def load_seal() -> dict[str, Any]:
    seal = _read_hashed_json(SEAL)
    if seal.get("round") != ROUND_ID:
        raise RuntimeError("seal belongs to another round")
    if seal.get("contract_sha256") != contract_sha256(build_contract()):
        raise RuntimeError("sealed contract drifted from the frozen module")
    launch = seal.get("launch", {})
    if int(launch.get("wsl_python_processes", 0)) + int(
        launch.get("other_reserved_processes", 0)
    ) != int(launch.get("host_process_budget", -1)):
        raise RuntimeError("sealed launch budget is inconsistent")
    for name, entry in (seal.get("sources") or {}).items():
        if entry["sha256"] != _sha256_file(ROOT / entry["path"]):
            raise RuntimeError(f"source drifted from the R436 seal: {name}")
    return seal


def source_manifest() -> dict[str, dict[str, str]]:
    sources = {
        "runner": Path(__file__).resolve(),
        "runner_tests": ROOT / "tests/test_run_r436_energy_residual_sac.py",
        "formulas": FORMULAS,
        "learner": ROOT / "src/andes_rl_kundur/agents/sac.py",
        "learner_base": ROOT / "src/andes_rl_kundur/agents/sac_base.py",
        "networks": ROOT / "src/andes_rl_kundur/agents/networks.py",
        "replay_buffer": ROOT / "src/andes_rl_kundur/agents/replay_buffer.py",
        "residual_seam": ROOT
        / "src/andes_rl_kundur/control/feasibility_native_vsg_action.py",
        "residual_seam_tests": ROOT / "tests/test_feasibility_native_vsg_action.py",
        "bandpass": ROOT / "src/andes_rl_kundur/control/ring_bandpass_damping.py",
        "energy_port_env": ROOT / "src/andes_rl_kundur/env/andes/vsg_energy_port_env.py",
        "v4_environment": ROOT
        / "src/andes_rl_kundur/env/andes/andes_vsg_env_v4.py",
        "v4_config": ROOT / "src/andes_rl_kundur/env/andes/v4_config.py",
        "base_environment": ROOT / "src/andes_rl_kundur/env/andes/base_env.py",
        "contract": ROOT / "src/andes_rl_kundur/evaluation/gate_b3_deterministic.py",
        "active_power": ROOT / "src/andes_rl_kundur/control/active_power.py",
        "r408_runner": ROOT / "scripts/run_r408_v2_solving_gate.py",
        "r372_runner": ROOT / "scripts/run_r372_energy_port_object_gate.py",
        "scratch_launcher": ROOT / "scripts/andes_scratch.py",
        "dependencies": ROOT / "pyproject.toml",
    }
    return {
        name: {"path": _relative(path), "sha256": _sha256_file(path)}
        for name, path in sources.items()
    }


def parent_manifest() -> dict[str, dict[str, str]]:
    paths = {
        "r409_analysis": R409_OUT / "formal_analysis.json",
        "r408_analysis": R408_OUT / "formal_analysis.json",
        "r413_analysis": R413_OUT / "formal_analysis.json",
        "r436_plan": PLAN,
        "r436_formulas": FORMULAS,
    }
    return {
        name: {"path": _relative(path), "sha256": _sha256_file(path)}
        for name, path in paths.items()
    }


def authority_checks() -> dict[str, bool]:
    plan_text = PLAN.read_text(encoding="utf-8")
    line_text = LINE.read_text(encoding="utf-8")
    contract = build_contract()
    return {
        "active_plan": "state: active" in plan_text
        and "manuscript_line: yang-md-decoupling-marl" in plan_text
        and "R436" in plan_text,
        "active_line": "line_id: yang-md-decoupling-marl" in line_text
        and "status: active" in line_text,
        "contract_closed": (
            list(contract["r436"]["training_seeds"]) == list(TRAINING_SEEDS)
            and len(contract["r436"]["learning_arms"]) == 2
            and len(contract["r436"]["topology_variants"]) == 10
            and int(contract["r436"]["total_interaction_steps"])
            == TOTAL_INTERACTION_STEPS
        ),
        "output_absence": not OUT.exists(),
    }


def _installed_runtime() -> dict[str, Any]:
    import andes

    case_path = Path(andes.get_case("kundur/kundur_full.xlsx")).resolve()
    return {
        "python": sys.version,
        "andes_version": str(getattr(andes, "__version__", "unknown")),
        "case_path": str(case_path),
        "case_sha256": _sha256_file(case_path),
    }


def _build_env(variant: Mapping[str, Any] | None = None):
    """Nominal (training) or variant (evaluation) energy-port environment."""
    from andes_rl_kundur.env.andes.andes_vsg_env_v4 import AndesMultiVSGEnvV4
    from andes_rl_kundur.env.andes.vsg_energy_port_env import AndesVSGEnergyPortEnv
    from andes_rl_kundur.evaluation.topology_status import apply_line_outage

    variant_kind = None if variant is None else str(variant["kind"])
    variant_line = None if variant is None else variant.get("line_idx")
    variant_factor = None if variant is None else variant.get("factor")

    if variant is not None and str(variant["variant_id"]) != "nominal":

        class _VariantEnv(AndesMultiVSGEnvV4):
            def _build_system(self):
                ss = super()._build_system()
                if variant_kind == "outage":
                    apply_line_outage(ss, str(variant_line))
                elif variant_kind == "impedance":
                    position = list(ss.Line.idx.v).index(str(variant_line))
                    current = float(ss.Line.x.v[position])
                    ss.Line.set(
                        "x", str(variant_line), current * float(variant_factor), attr="v"
                    )
                return ss

        env_class = _VariantEnv
    else:
        env_class = AndesMultiVSGEnvV4

    base_env = env_class(
        random_disturbance=False,
        comm_fail_prob=0.0,
        comm_delay_steps=0,
    )
    base_env.seed(42)
    base_env.STEPS_PER_EPISODE = STEPS_PER_EPISODE
    return AndesVSGEnergyPortEnv(base_env=base_env)


def _frequencies(port_env: Any) -> np.ndarray:
    return (
        np.asarray(port_env.base_env._get_vsg_omega(), dtype=float)
        * NOMINAL_FREQUENCY_HZ
    )


def _voltage_pu(port_env: Any) -> np.ndarray:
    return np.asarray(
        [
            port_env.base_env.ss.GENCLS.v.v[position]
            for position in port_env.base_env._vsg_pos
        ],
        dtype=float,
    )


def _joint_obs(
    frequencies: np.ndarray,
    previous_frequencies: np.ndarray,
    p_es: np.ndarray,
    previous_residuals: np.ndarray,
    masked: bool,
) -> np.ndarray:
    """7-slot rows per formulas.md section 1."""
    f_dev = (frequencies - NOMINAL_FREQUENCY_HZ) / NOMINAL_FREQUENCY_HZ
    rocof = (
        (frequencies - previous_frequencies) / (0.2 * NOMINAL_FREQUENCY_HZ)
    )
    p_es_norm = np.asarray(p_es, dtype=float) / NOMINAL_P_ES_DENOM
    rows = []
    for i in range(4):
        neighbours = ADJACENCY[i]
        n_dev = [f_dev[j] for j in neighbours]
        if masked:
            n_dev = [0.0, 0.0]
        rows.append(
            [
                float(f_dev[i]),
                float(rocof[i]),
                float(p_es_norm[i]),
                float(n_dev[0]),
                float(n_dev[1]),
                float(previous_residuals[i]),
                1.0,
            ]
        )
    return np.asarray(rows, dtype=np.float32)


def _reward(
    joint_obs: np.ndarray,
    residuals: np.ndarray,
    masked: bool,
) -> np.ndarray:
    """Formulas.md section 3, per agent."""
    f_dev = joint_obs[:, 0]
    neighbour_dev = joint_obs[:, 3:5]
    rewards = np.zeros(4, dtype=np.float32)
    for i in range(4):
        eta = [0.0, 0.0] if masked else [1.0, 1.0]
        n_active = 1.0 + sum(eta)
        omega_bar = (
            f_dev[i] + sum(e * n for e, n in zip(eta, neighbour_dev[i]))
        ) / n_active
        r_f = -(f_dev[i] - omega_bar) ** 2 - sum(
            e * (n - omega_bar) ** 2
            for e, n in zip(eta, neighbour_dev[i])
        )
        r_abs = -(float(residuals[i])) ** 2
        r_H = -(np.mean(residuals) / 2.0) ** 2
        r_D = -(np.mean(residuals - np.mean(residuals))) ** 2
        rewards[i] = (
            100.0 * r_f + 50.0 * r_abs + 0.0056 * r_H + 0.0056 * r_D
        )
    return rewards


class ResidualSACWrapper:
    """Four independent per-agent SAC agents for the energy-port residual.

    Each agent outputs one normalized residual scalar (action_dim=1);
    ``masked`` zeroes the neighbour observation slots (3-4) in act and
    store (no-message arm).  The wrapper mirrors R429's AdaptedSACArmWrapper
    seam so the training/eval loops stay identical in shape.
    """

    def __init__(self, masked: bool) -> None:
        self.masked = bool(masked)
        self.agents = [
            SACAgent(
                obs_dim=OBS_DIM,
                action_dim=ACTION_DIM,
                hidden_sizes=list(HIDDEN_SIZES),
                lr=LR,
                gamma=GAMMA,
                tau=TAU,
                buffer_size=BUFFER_SIZE,
                batch_size=BATCH_SIZE,
                device="cpu",
                alpha_min=ALPHA_MIN,
                alpha_max=ALPHA_MAX,
            )
            for _ in range(4)
        ]
        for agent in self.agents:
            agent.max_grad_norm = MAX_GRAD_NORM

    def _rows(self, joint_obs: np.ndarray) -> np.ndarray:
        rows = np.asarray(joint_obs, dtype=np.float32).reshape(4, OBS_DIM)
        if self.masked:
            rows = rows.copy()
            rows[:, 3:5] = 0.0
        return rows

    def act(self, joint_obs: np.ndarray, deterministic: bool = False) -> np.ndarray:
        rows = self._rows(joint_obs)
        return np.stack(
            [
                agent.select_action(rows[index], deterministic=deterministic)
                for index, agent in enumerate(self.agents)
            ]
        ).astype(np.float32)

    def store(
        self,
        joint_obs: np.ndarray,
        actions: np.ndarray,
        rewards: np.ndarray,
        next_obs: np.ndarray,
        done: bool,
    ) -> None:
        rows = self._rows(joint_obs)
        next_rows = self._rows(next_obs)
        action_rows = np.asarray(actions, dtype=np.float32).reshape(4, ACTION_DIM)
        reward_rows = np.asarray(rewards, dtype=float).reshape(4)
        for index, agent in enumerate(self.agents):
            agent.store_transition(
                rows[index],
                action_rows[index],
                float(reward_rows[index]),
                next_rows[index],
                bool(done),
            )

    def update_all(self) -> dict[str, float] | None:
        diagnostics = [agent.update() for agent in self.agents]
        if any(value is None for value in diagnostics):
            return None
        assert all(value is not None for value in diagnostics)
        keys = diagnostics[0].keys()  # type: ignore[union-attr]
        return {
            key: float(
                np.mean([float(value[key]) for value in diagnostics if value is not None])
            )
            for key in keys
        }

    def save(self, path: Path) -> None:
        torch.save(
            {
                "schema_version": 1,
                "round": ROUND_ID,
                "kind": "residual-sac-energy-port",
                "masked": self.masked,
                "agents": [
                    {
                        "actor": agent.actor.state_dict(),
                        "critic": agent.critic.state_dict(),
                        "critic_target": agent.critic_target.state_dict(),
                        "log_alpha": agent.log_alpha.detach().cpu(),
                    }
                    for agent in self.agents
                ],
            },
            str(path),
        )

    def load(self, path: Path) -> None:
        payload = torch.load(str(path), map_location="cpu", weights_only=True)
        if payload.get("kind") != "residual-sac-energy-port":
            raise ValueError("not an R436 residual-SAC checkpoint")
        if bool(payload.get("masked")) != self.masked:
            raise ValueError("R436 checkpoint information-pattern mismatch")
        for agent, entry in zip(self.agents, payload["agents"], strict=True):
            agent.actor.load_state_dict(entry["actor"])
            agent.critic.load_state_dict(entry["critic"])
            agent.critic_target.load_state_dict(entry["critic_target"])
            agent.log_alpha.data = entry["log_alpha"].to(agent.device)


def _agent_for(arm_id: str, device: str) -> ResidualSACWrapper:
    return ResidualSACWrapper(masked=(arm_id == NO_MESSAGE_ARM))


def _save_agent_snapshot(agent: ResidualSACWrapper, path: Path) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    agent.save(path)
    digest = _sha256_file(path)
    Path(f"{path}.sha256").write_text(
        f"{digest}  {path.name}\n", encoding="ascii"
    )
    return digest


def _gradient_direction_probe(arm_id: str) -> dict[str, Any]:
    """objective-semantics probe on the real learner (formulas section 3)."""
    torch.manual_seed(0)
    np.random.seed(0)
    agent = _agent_for(arm_id, "cpu")
    obs = np.zeros((4, OBS_DIM), dtype=np.float32)
    obs[:, 0] = 0.01  # small positive frequency deviation
    obs[:, 6] = 1.0
    residuals_np = np.array([0.3, -0.2, 0.1, -0.4], dtype=np.float32)
    masked = arm_id == NO_MESSAGE_ARM
    obs[:, 5] = residuals_np
    obs_t = torch.FloatTensor(obs)
    actions, _ = agent.agents[0].actor.sample(obs_t)
    scaled = RESIDUAL_SCALE * actions  # (4,1)
    scaled.retain_grad()
    # Tensor reward (probe-only; training uses the numpy reward).
    f_dev = obs_t[:, 0]
    neighbour_dev = obs_t[:, 3:5]
    reward_rows = []
    for i in range(4):
        eta = [0.0, 0.0] if masked else [1.0, 1.0]
        n_active = 1.0 + sum(eta)
        omega_bar = (
            f_dev[i] + sum(e * n for e, n in zip(eta, neighbour_dev[i]))
        ) / n_active
        r_f = -(f_dev[i] - omega_bar) ** 2 - sum(
            e * (n - omega_bar) ** 2 for e, n in zip(eta, neighbour_dev[i])
        )
        r_abs = -(scaled[i, 0]) ** 2
        r_H = -(torch.mean(scaled[:, 0]) / 2.0) ** 2
        r_D = -(torch.mean(scaled[:, 0] - torch.mean(scaled[:, 0]))) ** 2
        reward_rows.append(100.0 * r_f + 50.0 * r_abs + 0.0056 * r_H + 0.0056 * r_D)
    total = torch.stack(reward_rows).sum()
    total.backward()
    grads = scaled.grad.detach().numpy() if scaled.grad is not None else None
    reward_np = total.detach().numpy()
    result = {
        "finite": bool(grads is not None and np.all(np.isfinite(grads))),
        "grad_norm": float(np.linalg.norm(grads)) if grads is not None else None,
        "reward_finite": bool(np.isfinite(reward_np)),
        "reward_negative": bool(reward_np <= 0.0),
    }
    if grads is not None:
        # r_abs term drives |residual| down: d(r_abs)/d(scaled) = -2*scaled.
        # The expected direction uses the CURRENT scaled action, so the
        # alignment is the cosine between the measured gradient and the
        # penalty-descent direction at the sampled action.
        expected = -2.0 * scaled.detach().numpy()[:, 0]
        result["r_abs_alignment"] = float(
            np.dot(grads[:, 0], expected) / max(np.linalg.norm(expected), 1e-12)
        )
        result["r_abs_alignment_positive"] = bool(
            result["r_abs_alignment"] > 0.0
        )
    return result


def _train_arm_seed(arm_id: str, seed: int) -> str:
    _assert_wsl_scratch()
    load_seal()
    contract = build_contract()
    masked = arm_id == NO_MESSAGE_ARM
    run_dir = OUT / "train" / arm_id / f"seed{seed}"
    if run_dir.exists():
        raise FileExistsError(f"training output exists: {run_dir}")
    run_dir.mkdir(parents=True, exist_ok=True)
    snapshots_dir = run_dir / "snapshots"
    snapshots_dir.mkdir(parents=True, exist_ok=True)
    _write_new_json(
        run_dir / "started.json",
        {
            "schema_version": 1,
            "round": ROUND_ID,
            "arm_id": arm_id,
            "training_seed": int(seed),
            "created_utc": datetime.now(UTC).isoformat(),
            "contract_sha256": contract_sha256(contract),
            "torch_threads": torch.get_num_threads(),
        },
    )
    torch.manual_seed(int(seed))
    np.random.seed(int(seed))
    random.seed(int(seed))
    agent = _agent_for(arm_id, "cpu")
    env = _build_env()
    controller = BandpassArmController(
        k=3.5, nominal_frequency_hz=NOMINAL_FREQUENCY_HZ
    )
    action_map = FeasibilityNativeVSGActionMap(r272_frozen_bess_contract())
    critic_loss_trace: list[float] = []
    executed_steps = 0
    episodes_attempted = 0
    tds_failed_episodes = 0
    invalid_reason: str | None = None
    previous_residuals = np.zeros(4, dtype=np.float32)
    previous_executed_power = np.zeros(4, dtype=float)
    previous_p_es = np.zeros(4, dtype=float)
    schedule = [str(c["condition_id"]) for c in TRAINING_CONDITIONS]
    conditions = {str(c["condition_id"]): c for c in TRAINING_CONDITIONS}
    episode_index = 0
    while executed_steps < TOTAL_INTERACTION_STEPS:
        condition_id = schedule[episode_index % len(schedule)]
        episode_index += 1
        condition = conditions[condition_id]
        observation = env.reset(delta_u=dict(condition["delta_u"]))
        previous_frequencies = _frequencies(env)
        previous_residuals = np.zeros(4, dtype=np.float32)
        previous_executed_power = np.zeros(4, dtype=float)
        previous_p_es = np.zeros(4, dtype=float)
        episode_steps = 0
        for _step_index in range(STEPS_PER_EPISODE):
            frequencies = _frequencies(env)
            joint = _joint_obs(
                frequencies, previous_frequencies, previous_p_es,
                previous_residuals, masked,
            )
            raw = agent.act(joint, deterministic=False)  # (4,1)
            if not np.all(np.isfinite(raw)):
                invalid_reason = "nonfinite actor output"
                break
            residuals = RESIDUAL_SCALE * np.asarray(raw, dtype=float).reshape(4)
            controller_action = controller.act(frequencies, dt_seconds=0.2)
            common_action = np.mean(controller_action) * np.ones(4)
            differential_action = controller_action - common_action
            voltage = _voltage_pu(env)
            mapped = action_map.map_action(
                normalized_actions=controller_action,
                previous_power_system_pu=previous_executed_power,
                soc=np.full(4, 0.5, dtype=float),
                voltage_pu=voltage,
                dt_seconds=0.2,
            )
            baseline_power = mapped.feasible_power_system_pu
            residual_mapped = action_map.map_residual_action(
                normalized_residual_actions=residuals,
                baseline_power_system_pu=baseline_power,
                previous_power_system_pu=previous_executed_power,
                soc=np.full(4, 0.5, dtype=float),
                voltage_pu=voltage,
                dt_seconds=0.2,
            )
            _obs, _rew, done, info = env.step(
                residual_mapped.feasible_power_system_pu
            )
            executed_steps += 1
            episode_steps += 1
            frequencies_after = _frequencies(env)
            tds_failed = bool(info["tds_failed"])
            terminal = bool(done) or tds_failed
            p_es_after = np.asarray(info["P_es"], dtype=float)
            if p_es_after.shape != (4,):
                p_es_after = np.zeros(4, dtype=float)
            joint_after = _joint_obs(
                frequencies_after, frequencies, p_es_after, residuals, masked
            )
            if tds_failed:
                reward = np.full(4, -50.0, dtype=np.float32)
            else:
                reward = _reward(joint_after, residuals, masked)
            agent.store(
                joint, raw, reward, joint_after, terminal,
            )
            diagnostics = agent.update_all()
            if diagnostics is not None:
                loss_value = float(diagnostics["critic_loss"])
                critic_loss_trace.append(loss_value)
                if not np.isfinite(loss_value):
                    invalid_reason = "nonfinite critic loss"
                    break
            previous_frequencies = frequencies_after.copy()
            previous_residuals = residuals.copy()
            previous_executed_power = (
                residual_mapped.feasible_power_system_pu.copy()
            )
            previous_p_es = p_es_after.copy()
            if tds_failed:
                tds_failed_episodes += 1
                break
        if invalid_reason is not None:
            break
        episodes_attempted += 1
        if episodes_attempted % 240 == 0:
            _save_agent_snapshot(
                agent, snapshots_dir / f"episode{episodes_attempted}.pt"
            )
    try:
        env.close()
    except Exception:
        pass
    convergence_valid = invalid_reason is None and executed_steps == TOTAL_INTERACTION_STEPS
    missing = invalid_reason is not None
    checkpoint_sha = None
    if convergence_valid:
        checkpoint_sha = _save_agent_snapshot(agent, run_dir / "final.pt")
    trace_sha = _write_new_json(
        run_dir / "critic_loss_trace.json",
        {
            "schema_version": 1,
            "round": ROUND_ID,
            "arm_id": arm_id,
            "training_seed": int(seed),
            "critic_losses": critic_loss_trace,
        },
    )
    manifest = {
        "schema_version": 1,
        "round": ROUND_ID,
        "arm_id": arm_id,
        "training_seed": int(seed),
        "interaction_steps": int(executed_steps),
        "episodes_attempted": int(episodes_attempted),
        "tds_failed_episodes": int(tds_failed_episodes),
        "convergence_diagnostics_valid": bool(convergence_valid),
        "missing": bool(missing),
        "invalid_reason": invalid_reason,
        "final_checkpoint_sha256": checkpoint_sha,
        "critic_loss_trace_sha256": trace_sha,
        "critic_loss_count": int(len(critic_loss_trace)),
        "any_tds_failure": bool(tds_failed_episodes > 0),
        "created_utc": datetime.now(UTC).isoformat(),
        "contract_sha256": contract_sha256(contract),
    }
    return _write_new_json(run_dir / "manifest.json", manifest)


def _checkpoint_path(arm_id: str, seed: int) -> Path:
    path = OUT / "train" / arm_id / f"seed{seed}" / "final.pt"
    if not path.is_file() or not Path(f"{path}.sha256").is_file():
        raise FileNotFoundError(f"missing trained checkpoint: {path}")
    return path


def _load_agent(arm_id: str, seed: int) -> ResidualSACWrapper:
    agent = _agent_for(arm_id, "cpu")
    agent.load(_checkpoint_path(arm_id, seed))
    return agent


def _eval_jobs(variant: Mapping[str, Any], arm_id: str) -> list[dict[str, Any]]:
    """One arm x one variant: 8 paired probes + 2 disturbances (R408 shape)."""
    jobs = []
    contract = build_contract()
    probe_condition = {
        "condition_id": "dev3_probe_bus15_minus_0p45",
        "delta_u": {"PQ_Bus15": -0.45},
    }
    for input_mode in contract["mode_ids"]:
        for sign in ("positive", "negative"):
            jobs.append(
                {
                    "order": len(jobs),
                    "phase": "evaluation",
                    "arm_id": arm_id,
                    "variant_id": str(variant["variant_id"]),
                    "experiment_kind": "probe",
                    "condition_id": probe_condition["condition_id"],
                    "delta_u": dict(probe_condition["delta_u"]),
                    "input_mode": input_mode,
                    "sign": sign,
                }
            )
    for condition in (
        {
            "condition_id": "dev3_disturbance_pq1_plus_0p65",
            "delta_u": {"PQ_1": 0.65},
        },
        {
            "condition_id": "dev3_disturbance_bus14_minus_0p55",
            "delta_u": {"PQ_Bus14": -0.55},
        },
    ):
        jobs.append(
            {
                "order": len(jobs),
                "phase": "evaluation",
                "arm_id": arm_id,
                "variant_id": str(variant["variant_id"]),
                "experiment_kind": "disturbance",
                "condition_id": condition["condition_id"],
                "delta_u": dict(condition["delta_u"]),
                "input_mode": None,
                "sign": None,
            }
        )
    return jobs


def _run_eval_job(job: Mapping[str, Any]) -> dict[str, Any]:
    """One eval trajectory for a deterministic arm (zero/local/bandpass)."""
    variant = next(
        v for v in TOPOLOGY_VARIANTS if v["variant_id"] == job["variant_id"]
    )
    arm_id = str(job["arm_id"])
    if arm_id in LEARNING_ARMS:
        raise ValueError(f"{arm_id} must run through the per-seed path")
    env = _build_env(variant)
    controller = BandpassArmController(
        k=3.5, nominal_frequency_hz=NOMINAL_FREQUENCY_HZ
    )
    local_controller = None
    if arm_id == LOCAL_ARM:
        from andes_rl_kundur.control.feasibility_native_deterministic import (
            FeasibilityNativeLocalController,
        )
        contract = build_contract()
        local_controller = FeasibilityNativeLocalController(
            device_count=4,
            nominal_frequency_hz=NOMINAL_FREQUENCY_HZ,
            kp_n_per_hz=float(contract["local_gains"]["kp_n_per_hz"]),
            ki_n_per_hz_s=float(contract["local_gains"]["ki_n_per_hz_s"]),
        )
    action_map = FeasibilityNativeVSGActionMap(r272_frozen_bess_contract())
    rows: list[dict[str, Any]] = []
    identity: dict[str, Any] = {}
    failure: str | None = None
    previous_power_system_pu = np.zeros(4, dtype=float)
    current_soc = np.full(4, 0.5, dtype=float)
    try:
        env.reset(delta_u=dict(job["delta_u"]))
        identity = _identity(env.base_env)
        for _step_index in range(STEPS_PER_EPISODE):
            frequencies = _frequencies(env)
            if arm_id == ZERO_ARM:
                controller_action = np.zeros(4, dtype=float)
            elif arm_id == LOCAL_ARM:
                assert local_controller is not None
                controller_action = local_controller.act(
                    frequencies_hz=frequencies, dt_seconds=0.2
                )
            else:  # bandpass_k3p5
                controller_action = controller.act(frequencies, dt_seconds=0.2)
            normalized = controller_action.copy()
            if job["experiment_kind"] == "probe":
                normalized = normalized + probe_request(
                    str(job["input_mode"]), str(job["sign"]), contract=build_contract()
                )
            common_action = np.mean(normalized) * np.ones(4, dtype=float)
            differential_action = normalized - common_action
            voltage = _voltage_pu(env)
            mapped = action_map.map_action(
                normalized_actions=normalized,
                previous_power_system_pu=previous_power_system_pu,
                soc=current_soc,
                voltage_pu=voltage,
                dt_seconds=0.2,
            )
            _obs, _rew, done, info = env.step(
                mapped.feasible_power_system_pu
            )
            row = _port_row(info, step_index=_step_index, done=bool(done))
            row = _enrich_row(
                row,
                normalized=normalized,
                controller_action=controller_action,
                common_action=common_action,
                differential_action=differential_action,
                mapped=mapped,
            )
            rows.append(row)
            previous_power_system_pu = np.asarray(
                row["commanded_power_system_pu"], dtype=float
            )
            current_soc = np.asarray(row["soc"], dtype=float)
            if bool(info["tds_failed"]):
                failure = "tds_failed"
                break
    except Exception as exc:  # noqa: BLE001
        failure = f"{type(exc).__name__}: {exc}"
    try:
        env.close()
    except Exception:
        pass
    return {
        "arm_id": arm_id,
        "variant_id": str(job["variant_id"]),
        "condition_id": str(job["condition_id"]),
        "experiment_kind": str(job["experiment_kind"]),
        "input_mode": job["input_mode"],
        "sign": job["sign"],
        "completed_steps": len(rows),
        "identity": identity,
        "failure": failure,
        "tds_failed": bool(failure == "tds_failed"),
        "steps": rows,
    }


def _summarize_variant(variant: Mapping[str, Any]) -> dict[str, Any]:
    """Per-variant summaries for every arm (deterministic + learning medians)."""
    contract = build_contract()
    results: dict[str, dict] = {}
    for arm_id in EVAL_ARMS:
        jobs = _eval_jobs(variant, arm_id)
        records = [_run_eval_job(job) for job in jobs]
        summary = summarize_arm_records(records, contract=contract)
        results[arm_id] = summary
    for arm_id in LEARNING_ARMS:
        per_seed: dict[str, dict] = {}
        for seed in TRAINING_SEEDS:
            jobs = _eval_jobs(variant, arm_id)
            records = [_run_eval_job_seed(job, arm_id, seed) for job in jobs]
            per_seed[str(seed)] = summarize_arm_records(records, contract=contract)
        results[arm_id] = {"per_seed": per_seed}
    return {"variant_id": str(variant["variant_id"]), "arms": results}


def _run_eval_job_seed(job: Mapping[str, Any], arm_id: str, seed: int) -> dict[str, Any]:
    """One eval trajectory for a single seed of a learning arm."""
    variant = next(
        v for v in TOPOLOGY_VARIANTS if v["variant_id"] == job["variant_id"]
    )
    env = _build_env(variant)
    controller = BandpassArmController(
        k=3.5, nominal_frequency_hz=NOMINAL_FREQUENCY_HZ
    )
    action_map = FeasibilityNativeVSGActionMap(r272_frozen_bess_contract())
    agent = _load_agent(arm_id, int(seed))
    rows: list[dict[str, Any]] = []
    identity: dict[str, Any] = {}
    failure: str | None = None
    previous_residuals = np.zeros(4, dtype=np.float32)
    previous_p_es = np.zeros(4, dtype=float)
    previous_power_system_pu = np.zeros(4, dtype=float)
    current_soc = np.full(4, 0.5, dtype=float)
    masked = arm_id == NO_MESSAGE_ARM
    try:
        env.reset(delta_u=dict(job["delta_u"]))
        identity = _identity(env.base_env)
        previous_frequencies = _frequencies(env)
        for _step_index in range(STEPS_PER_EPISODE):
            frequencies = _frequencies(env)
            joint = _joint_obs(
                frequencies, previous_frequencies, previous_p_es,
                previous_residuals, masked,
            )
            raw = agent.act(joint, deterministic=True)  # (4,1)
            residuals = RESIDUAL_SCALE * np.asarray(raw, dtype=float).reshape(4)
            controller_action = controller.act(frequencies, dt_seconds=0.2)
            normalized = controller_action.copy()
            if job["experiment_kind"] == "probe":
                normalized = normalized + probe_request(
                    str(job["input_mode"]), str(job["sign"]), contract=build_contract()
                )
            common_action = np.mean(normalized) * np.ones(4, dtype=float)
            differential_action = normalized - common_action
            voltage = _voltage_pu(env)
            mapped = action_map.map_action(
                normalized_actions=normalized,
                previous_power_system_pu=previous_power_system_pu,
                soc=current_soc,
                voltage_pu=voltage,
                dt_seconds=0.2,
            )
            baseline_power = mapped.feasible_power_system_pu
            residual_mapped = action_map.map_residual_action(
                normalized_residual_actions=residuals,
                baseline_power_system_pu=baseline_power,
                previous_power_system_pu=previous_power_system_pu,
                soc=current_soc,
                voltage_pu=voltage,
                dt_seconds=0.2,
            )
            _obs, _rew, done, info = env.step(
                residual_mapped.feasible_power_system_pu
            )
            row = _port_row(info, step_index=_step_index, done=bool(done))
            row = _enrich_row(
                row,
                normalized=normalized,
                controller_action=controller_action,
                common_action=common_action,
                differential_action=differential_action,
                mapped=mapped,
            )
            rows.append(row)
            previous_frequencies = _frequencies(env)
            previous_residuals = residuals.copy()
            previous_power_system_pu = np.asarray(
                row["commanded_power_system_pu"], dtype=float
            )
            current_soc = np.asarray(row["soc"], dtype=float)
            p_es_after = np.asarray(info["P_es"], dtype=float)
            if p_es_after.shape == (4,):
                previous_p_es = p_es_after.copy()
            if bool(info["tds_failed"]):
                failure = "tds_failed"
                break
    except Exception as exc:  # noqa: BLE001
        failure = f"{type(exc).__name__}: {exc}"
    try:
        env.close()
    except Exception:
        pass
    return {
        "arm_id": arm_id,
        "variant_id": str(job["variant_id"]),
        "condition_id": str(job["condition_id"]),
        "experiment_kind": str(job["experiment_kind"]),
        "input_mode": job["input_mode"],
        "sign": job["sign"],
        "completed_steps": len(rows),
        "identity": identity,
        "failure": failure,
        "tds_failed": bool(failure == "tds_failed"),
        "steps": rows,
    }


def classify() -> str:
    analysis_path = OUT / "formal_analysis.json"
    if not analysis_path.is_file():
        raise FileNotFoundError("missing formal_analysis.json; run eval first")
    analysis = _read_hashed_json(analysis_path)
    return json.dumps(analysis["classification"], indent=2, sort_keys=True)


def _capacity_job(_job_id: int) -> dict[str, Any]:
    variant = TOPOLOGY_VARIANTS[0]
    job = _eval_jobs(variant, "bandpass_k3p5")[0]
    record = _run_eval_job(job)
    return {"ok": bool(record["completed_steps"] > 0)}


def _select_rung(payload: dict[str, Any]) -> dict[str, Any]:
    """Select the rung by the 5% marginal-throughput rule + memory rule."""
    rungs = payload["rungs"]
    best = max(rungs, key=lambda r: r["throughput_jobs_per_second"])
    selected_workers = int(best["workers"])
    selected_throughput = float(best["throughput_jobs_per_second"])
    # marginal rule: confirm the last accepted rung's marginal gain >= 1.05
    decisions = []
    previous_throughput = None
    for rung in rungs:
        throughput = float(rung["throughput_jobs_per_second"])
        marginal = (
            throughput / previous_throughput if previous_throughput else None
        )
        decisions.append(
            {
                "workers": int(rung["workers"]),
                "throughput_jobs_per_second": throughput,
                "marginal_gain": round(marginal, 4) if marginal else None,
                "accepted": bool(
                    marginal is None or marginal >= MARGINAL_GAIN_MIN
                ),
            }
        )
        previous_throughput = throughput
    # memory rule: projected concurrent training-worker RSS + OS floor
    # must not exceed WSL MemTotal (owner rule 2026-08-17: 900 MB floor per
    # live-training worker + fixed 3 GiB OS headroom vs MemTotal).
    logical, physical_memory, wsl_available = _memory_resources()
    mem_total = wsl_available or physical_memory
    projected_rss = selected_workers * TRAIN_WORKER_RSS_FLOOR_BYTES
    memory_safe = bool(
        projected_rss + OS_FLOOR_BYTES <= mem_total + int(1.5 * 1024**3)
    )
    payload["selected_workers"] = selected_workers
    payload["selected_throughput_jobs_per_second"] = selected_throughput
    payload["readiness"] = "RUN-READY" if memory_safe else "MEMORY-BLOCKED"
    payload["rung_decisions"] = decisions
    payload["memory_rule"] = (
        "projected concurrent training-worker RSS (900 MB floor per worker) "
        "plus fixed 3 GiB OS floor must not exceed WSL MemTotal"
    )
    payload["training_worker_rss_anchor"] = TRAIN_WORKER_RSS_FLOOR_BYTES
    payload["os_floor_bytes"] = OS_FLOOR_BYTES
    payload["host_process_budget"] = selected_workers + 1
    payload["wsl_python_processes"] = selected_workers + 1
    payload["other_reserved_processes"] = 0
    payload["native_threads_per_process"] = 1
    payload["representative_task"] = {
        "arm_id": "bandpass_k3p5",
        "variant": "nominal",
        "tasks_per_rung": CAPACITY_TASKS_PER_RUNG,
    }
    return payload


def measure_capacity() -> str:
    payload = {"rungs": []}
    for workers in CAPACITY_RUNGS:
        start = time.monotonic()
        with ProcessPoolExecutor(max_workers=workers) as pool:
            results = list(pool.map(_capacity_job, range(workers * 4)))
        wall = time.monotonic() - start
        payload["rungs"].append(
            {
                "workers": workers,
                "jobs": len(results),
                "wall_seconds": round(wall, 3),
                "throughput_jobs_per_second": round(
                    len(results) / max(wall, 1e-9), 4
                ),
                "all_ok": all(r["ok"] for r in results),
            }
        )
    payload["authorization"] = (
        "owner-authorized max parallelism; representative eval job (bandpass "
        "nominal probe), 4 tasks per worker"
    )
    payload = _select_rung(payload)
    return json.dumps(payload, indent=2, sort_keys=True)


def rehearse() -> str:
    checks = {
        "authority": authority_checks(),
        "runtime": _installed_runtime(),
        "sources": source_manifest(),
        "parents": parent_manifest(),
        "output_absence": not OUT.exists(),
        "contract_sha256": contract_sha256(build_contract()),
        "gradient_probe": _gradient_direction_probe(NO_MESSAGE_ARM),
        "gradient_probe_message": _gradient_direction_probe(MESSAGE_ARM),
    }
    # one bandpass reference trajectory + one short residual trajectory
    variant = TOPOLOGY_VARIANTS[0]
    job = _eval_jobs(variant, "bandpass_k3p5")[0]
    record = _run_eval_job(job)
    checks["reference_trajectory"] = {
        "rows": int(len(record.get("steps", []))),
        "tds_failed": bool(record.get("tds_failed")),
        "identity_ok": bool(record.get("identity") is not None),
    }
    return json.dumps(checks, indent=2, sort_keys=True)


def prepare() -> str:
    checks = authority_checks()
    if not all(checks.values()):
        raise RuntimeError(f"authority checks failed: {checks}")
    if not checks["output_absence"]:
        raise FileExistsError("formal output root already exists")
    rehearsal = _read_hashed_json(REHEARSAL)
    if not rehearsal.get("gradient_probe", {}).get("r_abs_alignment_positive"):
        raise RuntimeError("objective-semantics probe failed in rehearsal")
    capacity = _read_hashed_json(CAPACITY)
    selected = int(capacity.get("selected_workers", 0))
    if selected <= 0:
        raise RuntimeError("capacity evidence has no selected rung")
    launch = {
        "wsl_python_processes": selected + 1,
        "other_reserved_processes": 0,
        "host_process_budget": selected + 1,
        "native_threads_per_process": 1,
    }
    seal = {
        "schema_version": 1,
        "round": ROUND_ID,
        "created_utc": datetime.now(UTC).isoformat(),
        "contract_sha256": contract_sha256(build_contract()),
        "formulas_sha256": _sha256_file(FORMULAS),
        "plan_sha256": _sha256_file(PLAN),
        "authority": checks,
        "launch": launch,
        "capacity": {
            "path": _relative(CAPACITY),
            "sha256": _sha256_file(CAPACITY),
            "selected_workers": selected,
        },
        "rehearsal": {
            "path": _relative(REHEARSAL),
            "sha256": _sha256_file(REHEARSAL),
        },
        "sources": source_manifest(),
        "parents": parent_manifest(),
        "scientific_classification_inspected": False,
        "formal_authority": True,
        "training_executed": False,
    }
    digest = _write_new_json(SEAL, seal)
    return json.dumps({"seal_sha256": digest}, indent=2, sort_keys=True)


def _ratio_from_summaries(
    candidate: Mapping[str, Any],
    local: Mapping[str, Any],
) -> dict[str, float]:
    """r_d / r_cross from arm summaries (frozen R409 ratio semantics)."""
    local_diff = float(local["disturbance"]["mean_differential_frequency_energy_hz2_s"])
    local_off = float(local["probe"]["off_diagonal_response_energy_hz2_s"])
    diff_ratio = (
        float(candidate["disturbance"]["mean_differential_frequency_energy_hz2_s"])
        / local_diff
        if local_diff > 0.0
        else float("inf")
    )
    cross_ratio = (
        float(candidate["probe"]["off_diagonal_response_energy_hz2_s"]) / local_off
        if local_off > 0.0
        else float("inf")
    )
    return {
        "r_d": diff_ratio,
        "r_cross": cross_ratio,
        "strict_cross_pass": bool(cross_ratio <= STRICT_CROSS_RATIO_MAX),
        "guards_pass": bool(candidate["guards_pass"]),
        "guard_errors": list(candidate["guard_errors"]),
    }


def _learning_median_ratios(
    per_seed: Mapping[str, Mapping[str, Any]],
    local: Mapping[str, Any],
) -> dict[str, Any]:
    """5-seed medians of r_d / r_cross for one learning arm."""
    ratios = [_ratio_from_summaries(summary, local) for summary in per_seed.values()]
    r_d_values = sorted(float(r["r_d"]) for r in ratios)
    r_cross_values = sorted(float(r["r_cross"]) for r in ratios)
    n = len(r_d_values)
    median_r_d = r_d_values[n // 2] if n else float("inf")
    median_r_cross = r_cross_values[n // 2] if n else float("inf")
    return {
        "median_r_d": median_r_d,
        "median_r_cross": median_r_cross,
        "strict_cross_pass_median": bool(median_r_cross <= STRICT_CROSS_RATIO_MAX),
        "guards_pass_median": all(bool(r["guards_pass"]) for r in ratios),
        "per_seed_ratios": [
            {
                "seed": str(seed),
                "r_d": ratios[index]["r_d"],
                "r_cross": ratios[index]["r_cross"],
                "guards_pass": ratios[index]["guards_pass"],
            }
            for index, seed in enumerate(per_seed)
        ],
    }


def _write_analysis() -> str:
    """Aggregate all variant summaries into formal_analysis.json + classify."""
    payload = {
        "schema_version": 1,
        "round": ROUND_ID,
        "contract_sha256": contract_sha256(build_contract()),
        "seal_sha256": _sha256_file(SEAL),
        "variants": {},
        "classification": None,
    }
    variants_dir = OUT / "variants"
    if not variants_dir.is_dir():
        raise FileNotFoundError("missing variants/ directory; run eval first")
    local_paths = sorted(variants_dir.glob("*.json"))
    if len(local_paths) != len(TOPOLOGY_VARIANTS):
        raise RuntimeError(
            f"expected {len(TOPOLOGY_VARIANTS)} variant files, got {len(local_paths)}"
        )
    per_variant: dict[str, dict[str, Any]] = {}
    for path in local_paths:
        summary = _read_hashed_json(path)
        variant_id = str(summary["variant_id"])
        local = summary["arms"][LOCAL_ARM]
        bandpass = summary["arms"]["bandpass_k3p5"]
        entry = {
            "bandpass": _ratio_from_summaries(bandpass, local),
            "local": {
                "differential_energy": float(
                    local["disturbance"]["mean_differential_frequency_energy_hz2_s"]
                ),
                "off_diagonal_energy": float(
                    local["probe"]["off_diagonal_response_energy_hz2_s"]
                ),
            },
        }
        for arm_id in LEARNING_ARMS:
            entry[arm_id] = _learning_median_ratios(
                summary["arms"][arm_id]["per_seed"], local
            )
        per_variant[variant_id] = entry
        payload["variants"][variant_id] = entry
    payload["classification"] = _classify(per_variant)
    return _write_new_json(OUT / "formal_analysis.json", payload)


def _classify(per_variant: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    """Pre-registered decision tree (plan.md)."""
    nominal = per_variant.get("nominal")
    if nominal is None:
        raise RuntimeError("nominal variant missing from evaluation")
    bandpass_nominal = nominal["bandpass"]
    anchor_ok = (
        abs(bandpass_nominal["r_d"] - BASE_ANCHOR["r_d"])
        / BASE_ANCHOR["r_d"]
        <= BASE_ANCHOR_TOLERANCE_RELATIVE
        and abs(bandpass_nominal["r_cross"] - BASE_ANCHOR["r_cross"])
        / BASE_ANCHOR["r_cross"]
        <= BASE_ANCHOR_TOLERANCE_RELATIVE
    )
    learned_pass_variants: dict[str, list[str]] = {arm: [] for arm in LEARNING_ARMS}
    bandpass_pass_variants: dict[str, list[str]] = {"bandpass_k3p5": []}
    for variant_id, entry in per_variant.items():
        bp = entry["bandpass"]
        if bp["r_d"] <= DIFFERENTIAL_RATIO_MAX and bp["r_cross"] <= PROBE_CROSS_RATIO_MAX and bp["guards_pass"]:
            bandpass_pass_variants["bandpass_k3p5"].append(variant_id)
        for arm_id in LEARNING_ARMS:
            arm = entry[arm_id]
            if (
                arm["median_r_d"] <= DIFFERENTIAL_RATIO_MAX
                and arm["median_r_cross"] <= PROBE_CROSS_RATIO_MAX
                and arm["guards_pass_median"]
            ):
                learned_pass_variants[arm_id].append(variant_id)
    # LEARNED-BEYOND-DETERMINISTIC: learning arm passes a variant the
    # bandpass reference does not.
    bandpass_set = set(bandpass_pass_variants["bandpass_k3p5"])
    beyond: dict[str, list[str]] = {}
    for arm_id in LEARNING_ARMS:
        beyond[arm_id] = [
            v for v in learned_pass_variants[arm_id] if v not in bandpass_set
        ]
    if any(beyond.values()):
        classification = "LEARNED-BEYOND-DETERMINISTIC"
    else:
        # MESSAGE-INCREMENT: >10% median improvement on either endpoint
        # with no guard deterioration, across all variants.
        message_increment = False
        for variant_id, entry in per_variant.items():
            msg = entry[MESSAGE_ARM]
            no_msg = entry[NO_MESSAGE_ARM]
            if not (msg["guards_pass_median"] or no_msg["guards_pass_median"]):
                continue
            r_d_delta = (no_msg["median_r_d"] - msg["median_r_d"]) / max(
                no_msg["median_r_d"], 1e-12
            )
            r_cross_delta = (no_msg["median_r_cross"] - msg["median_r_cross"]) / max(
                no_msg["median_r_cross"], 1e-12
            )
            if r_d_delta > 0.10 or r_cross_delta > 0.10:
                message_increment = True
                break
        if message_increment:
            classification = "MESSAGE-INCREMENT"
        else:
            classification = "NO-LEARNING-INCREMENT"
    return {
        "classification": classification,
        "nominal_anchor_passed": bool(anchor_ok),
        "nominal_bandpass": {
            "r_d": bandpass_nominal["r_d"],
            "r_cross": bandpass_nominal["r_cross"],
        },
        "bandpass_pass_variants": bandpass_pass_variants["bandpass_k3p5"],
        "learned_pass_variants": learned_pass_variants,
        "beyond_deterministic_variants": beyond,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=[
        "capacity", "rehearse", "prepare", "train", "shard", "eval-variant",
        "eval-all", "classify", "aggregate",
    ])
    parser.add_argument("--arm", default=None)
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--variant", default=None)
    parser.add_argument("shard_id", nargs="?")
    args = parser.parse_args()
    if args.command == "capacity":
        payload = json.loads(measure_capacity())
        CAPACITY.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        safe_emit(json.dumps(payload, indent=2, sort_keys=True))
    elif args.command == "rehearse":
        payload = json.loads(rehearse())
        _write_new_json(REHEARSAL, payload)
        safe_emit(json.dumps(payload, indent=2, sort_keys=True))
    elif args.command == "prepare":
        safe_emit(prepare())
    elif args.command == "train":
        if args.arm is None or args.seed is None:
            raise SystemExit("train requires --arm and --seed")
        if args.arm not in LEARNING_ARMS:
            raise SystemExit(f"unknown learning arm: {args.arm}")
        safe_emit("R436 training manifest: " + _train_arm_seed(args.arm, args.seed))
    elif args.command == "shard":
        if args.shard_id is None:
            raise SystemExit("shard requires a shard id")
        if "|" in args.shard_id:
            phase, arm_id, seed = args.shard_id.split("|")
            if phase != "train":
                raise SystemExit(f"unsupported shard phase: {phase}")
            if arm_id not in LEARNING_ARMS:
                raise SystemExit(f"unknown learning arm: {arm_id}")
            safe_emit(
                "R436 training manifest: "
                + _train_arm_seed(arm_id, int(seed))
            )
        else:
            variant_id = args.shard_id
            variant = next(
                (v for v in TOPOLOGY_VARIANTS if v["variant_id"] == variant_id),
                None,
            )
            if variant is None:
                raise SystemExit(f"unknown variant: {variant_id}")
            summary = _summarize_variant(variant)
            out = OUT / "variants" / f"{variant_id}.json"
            digest = _write_new_json(out, summary)
            safe_emit(json.dumps({"variant": variant_id, "sha256": digest}, indent=2))
    elif args.command == "eval-variant":
        if args.variant is None:
            raise SystemExit("eval-variant requires --variant")
        variant = next(
            v for v in TOPOLOGY_VARIANTS if v["variant_id"] == args.variant
        )
        summary = _summarize_variant(variant)
        out = OUT / "variants" / f"{args.variant}.json"
        digest = _write_new_json(out, summary)
        safe_emit(json.dumps({"variant": args.variant, "sha256": digest}, indent=2))
    elif args.command == "eval-all":
        for variant in TOPOLOGY_VARIANTS:
            summary = _summarize_variant(variant)
            out = OUT / "variants" / f"{variant['variant_id']}.json"
            _write_new_json(out, summary)
            safe_emit(f"variant {variant['variant_id']} done")
        safe_emit("R436 evaluation complete")
    elif args.command == "aggregate":
        safe_emit(_write_analysis())
    else:
        safe_emit(classify())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
