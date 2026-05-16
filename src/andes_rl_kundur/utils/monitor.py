"""TrainingMonitor: data accumulation + plug-in Check dispatch.

Domain-aware diagnostic checks (reward_magnitude, action_collapse, etc.)
live in :mod:`andes_rl_kundur.scenarios.kundur.training_checks` and are
attached via :func:`register_kundur_default_checks`. This module owns
only the data layer (episode-by-episode storage, calibration, summary
output, save/load) and the Check Protocol dispatch with cooldown +
formatted printing.

Callers invoke ``log_and_check()`` directly from the training loop after
each episode; it returns ``True`` when any registered check returns a
``stop`` severity result.
"""
from __future__ import annotations

from collections import Counter
import csv
import json
from pathlib import Path
from typing import Any

import numpy as np


class TrainingMonitor:
    """Episode-level data accumulator + plug-in Check dispatcher.

    Construct, attach checks via :py:meth:`register_check` (or the
    Kundur default suite via
    :func:`andes_rl_kundur.scenarios.kundur.training_checks.register_kundur_default_checks`),
    then call :py:meth:`log_and_check` from the training loop after each
    episode. Returns ``True`` when a registered check returns
    ``severity='stop'``.
    """

    def __init__(
        self,
        calibration_episodes: int = 20,
        log_interval: int = 10,
        best_reward_callback: callable | None = None,
    ):
        self.calibration_episodes = calibration_episodes
        self.log_interval = log_interval

        # Data storage
        self._episode_rewards: list[float] = []
        self._reward_components: list[dict[str, float]] = []
        self._action_stats: list[dict[str, Any]] = []
        self._env_health: list[dict[str, Any]] = []
        self._per_agent_rewards: list[dict[int, float]] = []
        self._sac_losses: list[list[dict[str, float]]] = []

        # Calibration state
        self._calibrated = False
        self._calibration_data: dict[str, Any] = {}

        # Best reward tracking
        self._best_reward_callback = best_reward_callback
        self._best_reward = float('-inf')
        self._best_episode = -1

        # Early stopping state
        self._early_stop_best_reward = float('-inf')
        self._early_stop_best_ep_idx = 0

        # Trigger history
        self._trigger_history: list[dict[str, Any]] = []

        # Cooldown: suppress repeated warnings of same type
        self._last_trigger_ep: dict[str, int] = {}
        self._cooldown_episodes = 50  # minimum episodes between same warning

        # Registered Check Protocol instances (single execution path).
        # Domain defaults are registered by
        # andes_rl_kundur.scenarios.kundur.training_checks.register_kundur_default_checks.
        from andes_rl_kundur.utils.checks import Check  # noqa: F401 — type hint only
        self._plugin_checks: list = []

    # ─── Public read-only accessors (Check Protocol view) ───
    # Plug-in Check implementations read accumulated state through these
    # properties rather than reaching into the private underscored lists.
    # Keeps the seam clean and lets the storage details evolve.

    @property
    def episode_rewards(self) -> list[float]:
        return self._episode_rewards

    @property
    def action_stats(self) -> list[dict[str, Any]]:
        return self._action_stats

    @property
    def env_health(self) -> list[dict[str, Any]]:
        return self._env_health

    @property
    def reward_components(self) -> list[dict[str, float]]:
        return self._reward_components

    @property
    def per_agent_rewards(self) -> list[dict[int, float]]:
        return self._per_agent_rewards

    @property
    def sac_losses(self) -> list[list[dict[str, float]]]:
        return self._sac_losses

    @property
    def calibration_data(self) -> dict[str, Any]:
        return self._calibration_data

    @property
    def is_calibrated(self) -> bool:
        return self._calibrated

    def register_check(self, check) -> None:
        """Append a :class:`Check` Protocol instance to the registry.

        The monitor invokes every registered check on each
        :py:meth:`log_and_check` call, passing ``(self, episode_record)``.
        Returning ``triggered=True`` with ``severity="stop"`` causes
        ``log_and_check`` to return ``True``, which the training loop
        watches as its halt signal. ``warn`` triggers print but do not
        stop training; repeated warnings from the same check name are
        suppressed by the cooldown window (``self._cooldown_episodes``).
        """
        from andes_rl_kundur.utils.checks import Check
        if not isinstance(check, Check):
            raise TypeError(
                f"Check must satisfy the Check Protocol "
                f"(name: str + run(monitor, episode) -> CheckResult); "
                f"got {type(check).__name__}"
            )
        self._plugin_checks.append(check)

    def log_and_check(
        self,
        episode: int,
        rewards: float,
        reward_components: dict[str, float],
        actions: np.ndarray,
        info: dict[str, Any],
        per_agent_rewards: dict[int, float] | None = None,
        sac_losses: list[dict[str, float]] | None = None,
    ) -> bool:
        """Record episode data and run diagnostic checks.

        Args:
            episode: Episode number.
            rewards: Scalar total reward (all agents summed).
            reward_components: Named reward components, e.g. {"r_f": -1400, "r_h": -5}.
            actions: Shape (n_steps, n_agents, action_dim).
            info: Must contain "tds_failed" (bool) and "max_freq_deviation_hz" (float).
            per_agent_rewards: Per-agent rewards, e.g. {0: -100, 1: -200}.
            sac_losses: Per-agent SAC losses, e.g. [{"critic_loss": 0.5, ...}, ...].

        Returns:
            True if any check triggered a "stop" action.
        """
        # Store data
        self._episode_rewards.append(rewards)
        self._reward_components.append(dict(reward_components))

        # Store per-agent rewards
        if per_agent_rewards is not None:
            self._per_agent_rewards.append(dict(per_agent_rewards))

        # Store SAC losses
        if sac_losses is not None:
            self._sac_losses.append(list(sac_losses))

        # Best reward tracking
        if rewards > self._best_reward:
            self._best_reward = rewards
            self._best_episode = episode
            if self._best_reward_callback is not None:
                self._best_reward_callback(episode, rewards)

        # Compute action statistics per agent
        # actions shape: (steps, agents, action_dim)
        per_agent_std = np.std(actions, axis=0).mean(axis=-1)  # (agents,)
        per_agent_mean = np.mean(actions, axis=0).mean(axis=-1)  # (agents,)
        saturation_ratio = float(np.mean(np.abs(actions) > 0.95))
        self._action_stats.append({
            "per_agent_std": per_agent_std.tolist(),
            "per_agent_mean": per_agent_mean.tolist(),
            "saturation_ratio": saturation_ratio,
        })

        # Store env health
        self._env_health.append({
            "tds_failed": info.get("tds_failed", False),
            "max_freq_deviation_hz": info.get("max_freq_deviation_hz", 0.0),
            "max_power_swing": info.get("max_power_swing"),
        })

        # Calibration phase
        n = len(self._episode_rewards)
        if not self._calibrated and n >= self.calibration_episodes:
            self._calibrate()

        # Periodic summary
        if n > 0 and n % self.log_interval == 0:
            self._log_summary(episode)

        # Run registered checks. Pass `self` so checks can read accumulated
        # state via the public read-only accessors (episode_rewards,
        # action_stats, etc.). Apply cooldown to repeated `warn` triggers
        # so the log doesn't get spammed; `stop` always prints + halts.
        episode_record = {
            "episode": episode,
            "rewards": rewards,
            "reward_components": dict(reward_components),
            "actions": actions,
            "max_freq_deviation_hz": info.get("max_freq_deviation_hz", 0.0),
            "tds_failed": info.get("tds_failed", False),
            "per_agent_rewards": dict(per_agent_rewards or {}),
        }
        any_stop = False
        for chk in self._plugin_checks:
            result = chk.run(self, episode_record)
            if not result.triggered:
                continue
            self._trigger_history.append({
                "check": result.name,
                "episode": episode,
                "action": result.severity,
                "message": result.message,
            })
            # Cooldown suppression for warn-class triggers only.
            if result.severity != "stop":
                last_ep = self._last_trigger_ep.get(result.name, -10 ** 9)
                if episode - last_ep < self._cooldown_episodes:
                    continue
            self._last_trigger_ep[result.name] = episode
            icon = "[STOP]" if result.severity == "stop" else "[!]"
            label = "TRAINING STOPPED" if result.severity == "stop" else "WARNING"
            print(f"\n{icon} [Monitor] {label}: {result.name} @ Ep {episode}")
            print(f"  {result.message}")
            if result.severity == "stop":
                print("  Training terminated.\n")
                any_stop = True
        return any_stop

    # ─── Calibration ───

    def _calibrate(self):
        """Auto-calibrate thresholds from collected baseline data."""
        self._calibrated = True  # Set early to prevent re-entry on exception
        rewards = np.array(self._episode_rewards[:self.calibration_episodes])
        self._calibration_data["reward_mean"] = float(np.mean(rewards))
        self._calibration_data["reward_std"] = float(np.std(rewards))

        # Action std baseline: mean per-agent std across calibration episodes
        all_stds = [s["per_agent_std"] for s in self._action_stats[:self.calibration_episodes]]
        self._calibration_data["action_std_baseline"] = float(np.mean(all_stds))

        # TDS failure baseline
        fails = [h["tds_failed"] for h in self._env_health[:self.calibration_episodes]]
        self._calibration_data["tds_failure_baseline"] = float(np.mean(fails))

        # Critic loss baseline (if SAC losses were logged during calibration)
        cal_losses = self._sac_losses[:self.calibration_episodes]
        if cal_losses:
            all_critic = [
                loss["critic_loss"]
                for ep_losses in cal_losses
                for loss in ep_losses
                if "critic_loss" in loss
            ]
            if all_critic:
                self._calibration_data["critic_loss_baseline"] = float(np.mean(all_critic))

        self._print_calibration_summary()

    def _print_calibration_summary(self):
        d = self._calibration_data
        mu, sigma = d["reward_mean"], d["reward_std"]
        lo, hi = mu - 3 * sigma, mu + 3 * sigma
        act_std = d["action_std_baseline"]
        tds_rate = d["tds_failure_baseline"]
        print(f"[Monitor] Calibration complete ({self.calibration_episodes} episodes).")
        print(f"          Reward baseline: mu={mu:.1f}, std={sigma:.1f} -> magnitude range: [{lo:.0f}, {hi:.0f}]")
        print(f"          Action std baseline: {act_std:.2f} -> collapse threshold: {act_std * 0.1:.3f}")
        print(f"          TDS failure baseline: {tds_rate * 100:.1f}% -> alert threshold: {max(tds_rate * 2, 0.3) * 100:.1f}%")

    # ─── Sliding window statistics ───

    def get_moving_stats(self, window: int = 50) -> dict:
        """Return windowed statistics over the last `window` episodes.

        Returns:
            Dict with keys: reward_mean, reward_std, action_std_mean,
            saturation_ratio_mean, tds_failure_rate, freq_deviation_mean.
        """
        n = len(self._episode_rewards)
        if n == 0:
            return {
                "reward_mean": 0.0,
                "reward_std": 0.0,
                "action_std_mean": 0.0,
                "saturation_ratio_mean": 0.0,
                "tds_failure_rate": 0.0,
                "freq_deviation_mean": 0.0,
            }

        w = min(window, n)
        rewards = np.array(self._episode_rewards[-w:])

        action_stds = [np.mean(s["per_agent_std"]) for s in self._action_stats[-w:]]
        sat_ratios = [s["saturation_ratio"] for s in self._action_stats[-w:]]

        health = self._env_health[-w:]
        fail_count = sum(1 for h in health if h["tds_failed"])
        freq_devs = [h["max_freq_deviation_hz"] for h in health]

        return {
            "reward_mean": float(np.mean(rewards)),
            "reward_std": float(np.std(rewards)),
            "action_std_mean": float(np.mean(action_stds)),
            "saturation_ratio_mean": float(np.mean(sat_ratios)),
            "tds_failure_rate": float(fail_count / w),
            "freq_deviation_mean": float(np.mean(freq_devs)),
        }

    # ─── Multi-run comparison ───

    @classmethod
    def compare_runs(cls, checkpoints: list[str]) -> None:
        """Load multiple monitor checkpoint JSON files and print a comparison table.

        Args:
            checkpoints: List of file paths to JSON checkpoint files.
        """
        runs = []
        for path_str in checkpoints:
            path = Path(path_str)
            with open(path, "r") as f:
                data = json.load(f)
            runs.append((path.name, data))

        if not runs:
            print("[Monitor] No checkpoint files provided.")
            return

        print(f"\n[Monitor] === Multi-Run Comparison ({len(runs)} runs) ===\n")
        header = (
            f"{'Run':<30} {'Episodes':>8} {'Final R':>10} {'Best R':>10} "
            f"{'Best Ep':>8} {'TDS Fail':>9} {'Checks':>7}"
        )
        print(header)
        print("-" * len(header))

        for name, data in runs:
            rewards = data.get("_episode_rewards", data.get("episode_rewards", []))
            n_episodes = len(rewards)
            final_reward = rewards[-1] if rewards else 0.0
            best_reward = max(rewards) if rewards else 0.0
            best_ep = rewards.index(best_reward) if rewards else 0

            env_health = data.get("_env_health", data.get("env_health", []))
            total_tds = sum(1 for h in env_health if h.get("tds_failed", False))

            trigger_history = data.get("_trigger_history", data.get("trigger_history", []))
            n_checks = len(trigger_history)

            print(
                f"{name:<30} {n_episodes:>8} {final_reward:>10.1f} {best_reward:>10.1f} "
                f"{best_ep:>8} {total_tds:>9} {n_checks:>7}"
            )

        print()

    # ─── Persistence & export ───

    def save_checkpoint(self, path: str):
        """Save all monitor state to a JSON file."""
        data = {
            "calibration_episodes": self.calibration_episodes,
            "_calibrated": self._calibrated,
            "_calibration_data": self._calibration_data,
            "_episode_rewards": self._episode_rewards,
            "_reward_components": self._reward_components,
            "_action_stats": self._action_stats,
            "_env_health": self._env_health,
            "_trigger_history": self._trigger_history,
            "_per_agent_rewards": self._per_agent_rewards,
            "_sac_losses": self._sac_losses,
            "_best_reward": self._best_reward,
            "_best_episode": self._best_episode,
            "_early_stop_best_reward": self._early_stop_best_reward,
            "_early_stop_best_ep_idx": self._early_stop_best_ep_idx,
            "_last_trigger_ep": self._last_trigger_ep,
        }
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            json.dump(data, f, indent=2, default=lambda o: float(o) if hasattr(o, 'item') else str(o))

    @classmethod
    def load_checkpoint(cls, path: str) -> "TrainingMonitor":
        """Create a TrainingMonitor from a saved checkpoint JSON."""
        with open(path) as f:
            data = json.load(f)

        monitor = cls(calibration_episodes=data["calibration_episodes"])
        monitor._episode_rewards = data["_episode_rewards"]
        monitor._reward_components = data["_reward_components"]
        monitor._action_stats = data["_action_stats"]
        monitor._env_health = data["_env_health"]
        monitor._trigger_history = data["_trigger_history"]
        monitor._calibration_data = data["_calibration_data"]
        monitor._calibrated = data["_calibrated"]
        monitor._per_agent_rewards = [
            {int(k): v for k, v in d.items()}
            for d in data.get("_per_agent_rewards", [])
        ]
        monitor._sac_losses = data.get("_sac_losses", [])
        monitor._best_reward = data.get("_best_reward", float('-inf'))
        monitor._best_episode = data.get("_best_episode", -1)
        monitor._early_stop_best_reward = data.get("_early_stop_best_reward", float('-inf'))
        monitor._early_stop_best_ep_idx = data.get("_early_stop_best_ep_idx", 0)
        monitor._last_trigger_ep = data.get("_last_trigger_ep", {})

        # If enough episodes exist, ensure calibrated
        if not monitor._calibrated and len(monitor._episode_rewards) >= monitor.calibration_episodes:
            monitor._calibrate()

        return monitor

    def export_csv(self, path: str):
        """Export per-episode data to CSV."""
        n = len(self._episode_rewards)
        if n == 0:
            return

        # Determine number of agents from first action_stats entry
        n_agents = len(self._action_stats[0]["per_agent_mean"])

        # Build header
        header = ["episode", "reward", "r_f", "r_h", "r_d"]
        for i in range(n_agents):
            header.append(f"action_mean_agent_{i}")
        for i in range(n_agents):
            header.append(f"action_std_agent_{i}")
        header.extend(["saturation_ratio", "tds_failed", "max_freq_deviation_hz", "max_power_swing"])

        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(header)

            for ep in range(n):
                comps = self._reward_components[ep]
                stats = self._action_stats[ep]
                health = self._env_health[ep]

                row = [
                    ep,
                    self._episode_rewards[ep],
                    comps.get("r_f", 0.0),
                    comps.get("r_h", 0.0),
                    comps.get("r_d", 0.0),
                ]
                for i in range(n_agents):
                    row.append(stats["per_agent_mean"][i])
                for i in range(n_agents):
                    row.append(stats["per_agent_std"][i])
                row.append(stats["saturation_ratio"])
                row.append(int(health["tds_failed"]))
                row.append(health["max_freq_deviation_hz"])
                row.append(health.get("max_power_swing"))

                writer.writerow(row)

    def export_tensorboard(self, log_dir: str):
        """Export data to TensorBoard format."""
        try:
            from torch.utils.tensorboard import SummaryWriter
        except ImportError:
            print("[Monitor] WARNING: torch.utils.tensorboard not available. "
                  "Skipping TensorBoard export.")
            return

        n = len(self._episode_rewards)
        if n == 0:
            return

        writer = SummaryWriter(log_dir=log_dir)

        for ep in range(n):
            # Reward scalars
            writer.add_scalar("reward/total", self._episode_rewards[ep], ep)

            comps = self._reward_components[ep]
            for key, val in comps.items():
                writer.add_scalar(f"reward/{key}", val, ep)

            # Action stats
            stats = self._action_stats[ep]
            mean_std = float(np.mean(stats["per_agent_std"]))
            writer.add_scalar("action/mean_std", mean_std, ep)
            writer.add_scalar("action/saturation_ratio",
                              stats["saturation_ratio"], ep)

            # Environment health
            health = self._env_health[ep]
            writer.add_scalar("env/max_freq_deviation_hz",
                              health["max_freq_deviation_hz"], ep)

            # Rolling TDS failure rate (window=50)
            window = 50
            start = max(0, ep - window + 1)
            recent = self._env_health[start:ep + 1]
            tds_rate = sum(1 for h in recent if h["tds_failed"]) / len(recent)
            writer.add_scalar("env/tds_failure_rate", tds_rate, ep)

        writer.close()

    # ─── Output formatting ───

    def _log_summary(self, episode: int):
        r = self._episode_rewards[-1]
        comps = self._reward_components[-1]
        total_abs = sum(abs(v) for v in comps.values())
        comp_str = ", ".join(
            f"{k}: {abs(v)/max(total_abs,1e-8)*100:.1f}%" for k, v in comps.items()
        )
        stats = self._action_stats[-1]
        mu_str = "[" + ", ".join(f"{m:.2f}" for m in stats["per_agent_mean"]) + "]"
        std_str = "[" + ", ".join(f"{s:.2f}" for s in stats["per_agent_std"]) + "]"

        # TDS failures in recent log_interval
        recent_health = self._env_health[-self.log_interval:]
        tds_fails = sum(1 for h in recent_health if h["tds_failed"])
        max_freq = max(h["max_freq_deviation_hz"] for h in recent_health)

        print(f"[Monitor] Ep {episode} | Reward: {r:.1f} ({comp_str})")
        print(f"          Actions mu: {mu_str}  std: {std_str}")
        print(f"          TDS fails: {tds_fails}/{len(recent_health)} ({tds_fails/len(recent_health)*100:.1f}%) | Freq peak: {max_freq:.2f} Hz")

        # Per-agent rewards (if available)
        if self._per_agent_rewards:
            par = self._per_agent_rewards[-1]
            par_str = ", ".join(f"a{aid}: {rv:.1f}" for aid, rv in sorted(par.items()))
            print(f"          Per-agent rewards: [{par_str}]")

        # SAC losses (if available)
        if self._sac_losses:
            losses = self._sac_losses[-1]
            critic_vals = [l["critic_loss"] for l in losses if "critic_loss" in l]
            alpha_vals = [l["alpha"] for l in losses if "alpha" in l]
            if critic_vals:
                mean_critic = float(np.mean(critic_vals))
                parts = [f"mean critic_loss: {mean_critic:.3f}"]
                if alpha_vals:
                    mean_alpha = float(np.mean(alpha_vals))
                    parts.append(f"mean alpha: {mean_alpha:.3f}")
                print(f"          SAC: {', '.join(parts)}")

    def summary(self):
        n = len(self._episode_rewards)
        if n == 0:
            print("[Monitor] No episodes recorded.")
            return

        cal_status = "complete" if self._calibrated else f"incomplete ({n}/{self.calibration_episodes} ep)"
        first_r = self._episode_rewards[0]
        last_r = self._episode_rewards[-1]
        best_r = max(self._episode_rewards)
        best_ep = self._episode_rewards.index(best_r)
        worst_r = min(self._episode_rewards)
        worst_ep = self._episode_rewards.index(worst_r)

        total_tds = sum(1 for h in self._env_health if h["tds_failed"])
        max_freq = max(h["max_freq_deviation_hz"] for h in self._env_health)
        max_freq_ep = max(range(n), key=lambda i: self._env_health[i]["max_freq_deviation_hz"])

        print(f"\n[Monitor] === Training Summary ===")
        print(f"  Episodes: {n} | Calibration: {cal_status}")
        print(f"  Reward:   {first_r:.0f} (ep 0) -> {last_r:.0f} (ep {n-1})")
        print(f"  Best:     {best_r:.0f} @ ep {best_ep} | Worst: {worst_r:.0f} @ ep {worst_ep}")

        # Best reward episode (from callback tracking)
        if self._best_episode >= 0:
            print(f"  Best reward callback: {self._best_reward:.0f} @ ep {self._best_episode}")

        # Per-agent reward range
        if self._per_agent_rewards:
            agent_ids = sorted(self._per_agent_rewards[0].keys())
            agent_totals = {
                aid: [r[aid] for r in self._per_agent_rewards if aid in r]
                for aid in agent_ids
            }
            agent_means = {aid: float(np.mean(vals)) for aid, vals in agent_totals.items()}
            best_agent = max(agent_means, key=agent_means.get)
            worst_agent = min(agent_means, key=agent_means.get)
            print(f"  Per-agent reward (mean): best agent {best_agent} = {agent_means[best_agent]:.1f}, "
                  f"worst agent {worst_agent} = {agent_means[worst_agent]:.1f}")

        # Loss trend summary
        if self._sac_losses:
            all_critic = [
                float(np.mean([l["critic_loss"] for l in ep if "critic_loss" in l]))
                for ep in self._sac_losses
                if any("critic_loss" in l for l in ep)
            ]
            if len(all_critic) >= 2:
                early = float(np.mean(all_critic[:min(20, len(all_critic))]))
                late = float(np.mean(all_critic[-min(20, len(all_critic)):]))
                trend = "decreasing" if late < early * 0.9 else ("increasing" if late > early * 1.1 else "stable")
                print(f"  Loss trend: critic_loss early={early:.3f} -> late={late:.3f} ({trend})")

        if self._trigger_history:
            print(f"\n  Checks triggered:")
            # Group by check name
            counts = Counter(t["check"] for t in self._trigger_history)
            for check_name, count in counts.items():
                first_ep = next(t["episode"] for t in self._trigger_history if t["check"] == check_name)
                action = next(t["action"] for t in self._trigger_history if t["check"] == check_name)
                icon = "[STOP]" if action == "stop" else "[!]"
                label = "STOP" if action == "stop" else "WARN"
                print(f"    {check_name:<28} {icon} {label:<5} @ ep {first_ep:<5} ({count} time{'s' if count > 1 else ''})")
        else:
            print(f"\n  No checks triggered.")

        print(f"\n  TDS failures: {total_tds}/{n} ({total_tds/n*100:.1f}%)")
        print(f"  Freq peak deviation: {max_freq:.2f} Hz (ep {max_freq_ep})")
        print()
