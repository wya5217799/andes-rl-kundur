# Handoff — R56 LSTM recurrent actor implementation

**Date prepared**: 2026-05-17 (end of R55 session)
**Target**: implement LSTM-actor TD3 to break the 0.334 / 0.365 / 0.351
production triangle ceiling established by R48-R55.
**Estimated cost**: 1-2 days (code + debugging + 3-seed sweep + verdict)
**Confidence**: highest among remaining structural pivots (per R55 verdict).
Only structural change that makes deterministic eval policy
**internally** time-varying (no exploration noise dependency).

---

## Read first (next session, in order)

1. `memory/handoffs/2026-05-17_R56_lstm-actor-implementation.md` — this file
2. `memory/handoffs/2026-05-17_post-R55_arc-summary.md` — full R43-R55 narrative,
   structural ceiling rationale, anti-patterns
3. `memory/STATE.md` — current 62-claim oracle, leaderboard
4. `memory/rounds/R55/verdict.md` — six-failure hexagon details +
   architectural-pivot menu
5. `src/andes_rl_kundur/agents/networks.py` — current MLP actor/critic
   class structure
6. `src/andes_rl_kundur/agents/td3.py` — TD3Agent class to mirror

---

## Why LSTM (background)

The R49-R55 six-failure hexagon established that any **memoryless
deterministic policy** on V4 + decentralized obs + paper-faithful
reward converges to a static setpoint at eval. The failure mode
is invariant to:
- training algorithm (TD3 / SAC)
- obs augmentation (action history, time-in-obs)
- per-step reward shaping (anti-smoothness W=1 / W=10)
- shared initialisation
- hidden capacity (32 / 64 / 128 / 256)

Diagnostic: per-agent action span over 6 s = 9-21 % of paper's
claimed 400 / 800. Cross-agent mean curve span (the actual
`utilization` metric input) bottlenecked by the same.

**LSTM unlocks structural time-variance**: the policy `π(obs_t, h_t)`
has hidden state `h_t` encoding the trajectory so far. Even with
identical observations, `h_t` differs across time → π output
differs across time → action varies temporally **without needing
exploration noise to induce it**. The noise-hijack channel
(R50/R55 mechanism) is bypassed because reward depends on
deterministic-policy output, which is now naturally time-varying.

---

## Round number to claim

Use **R56** (next free after R55, accounting for Codex's R53). Before
starting, run Codex's atomic round reservation tool:

```bash
wsl bash -c "cd <repo> && /home/wya/andes_venv/bin/python memory/tools/reserve_round.py R56"
```

This was added in commit `0cb893c` to prevent the R42/R45/R53
collisions experienced in the prior session. If it fails (Codex
took R56 in parallel), bump to R57.

---

## Goal (success criteria for R56)

**Primary**: 3-seed mean 6-axis > **0.40** at h=64 norm 75ep TD3+LSTM.
This would break the 0.365 single-seed ceiling and establish a new
production setting.

**Secondary** (consolation): per-agent dM_span at eval > 30 % of
paper (vs current 9-21 % baseline). Even if 6-axis doesn't break,
demonstrating temporal action variation at deterministic eval would
**falsify the static-setpoint structural finding** and open new
research direction.

**Floor (not failure)**: mean ≥ 0.30 with dM_span > 25 %. Still a
useful claim — would confirm LSTM lifts utilization without
necessarily clearing R48-β baseline.

**Real failure mode**: mean < 0.20 OR collapse on some seeds. Then
LSTM doesn't help on V4 even with structural memory; the bottleneck
is genuinely the reward landscape, not policy class. CLM-006N
negative.

---

## Architectural decisions (pre-decided to save next-session time)

| Decision | Choice | Rationale |
|---|---|---|
| Actor architecture | `LSTMCell(obs_dim, hidden=64) + Linear(64, action_dim)` per agent | Matches R48 h=64 sweet spot; minimal new params |
| Per-agent or shared LSTM | **Per-agent** (4 independent) | Maintains existing multi-agent decentralisation; each agent's hidden state encodes its local trajectory |
| Critic architecture | Separate LSTMCell per critic (Q1, Q2), shared with actor's LSTM **disabled** | Standard practice; sharing causes gradient interference |
| Critic hidden | 64 (match actor) | Symmetry |
| Sequence length L | 25 (half-episode) | Tradeoff: longer = better h fidelity, but smaller batch |
| Burn-in B | 5 | Short enough to discard, long enough to stabilise h |
| Batch size | 32 sequences | Fits in CPU memory; matches recurrent-RL conventions |
| Replay buffer | Episodes stored full; sample random L-step subsequences with stride 1 | Simplest; episode buffer ~50 steps × 75 episodes = 3750 transitions per agent |
| Initial hidden state | All zeros, both train and eval | Standard |
| Burn-in gradient | Disabled (frozen h, no grad) | Standard R2D2 hack |
| Action noise (training) | Same Gaussian σ=0.1 as TD3 baseline | Don't change two things at once |
| Target nets | Standard Polyak update of LSTM + Linear | Matches TD3 |

**Open architectural question**: should the actor see only current
`obs` plus its `h_prev`, or current `obs` concatenated with
`prev_action` (deliberate redundancy)? Recommendation: only `obs`
(matches R49 finding that adding action history hurts).

---

## Implementation plan (file-by-file)

### 1. `src/andes_rl_kundur/agents/networks.py` (~2 hr)

Add two classes:

```python
class RecurrentActor(nn.Module):
    """LSTMCell-based deterministic actor for TD3.
    
    forward(obs, h_prev) -> (action, h_new)
    obs:    (batch, obs_dim)
    h_prev: tuple of (h_cell, c_cell), each (batch, hidden)
    action: (batch, action_dim) in tanh range
    h_new:  same shape as h_prev
    """
    def __init__(self, obs_dim, action_dim, hidden=64):
        super().__init__()
        self.lstm = nn.LSTMCell(obs_dim, hidden)
        self.fc_out = nn.Linear(hidden, action_dim)
        self.hidden = hidden

    def forward(self, obs, h_prev):
        h, c = self.lstm(obs, h_prev)
        a = torch.tanh(self.fc_out(h))
        return a, (h, c)

    def init_hidden(self, batch_size, device='cpu'):
        h = torch.zeros(batch_size, self.hidden, device=device)
        c = torch.zeros(batch_size, self.hidden, device=device)
        return (h, c)


class RecurrentCritic(nn.Module):
    """LSTMCell critic Q(obs, action) with own hidden state."""
    def __init__(self, obs_dim, action_dim, hidden=64):
        super().__init__()
        self.lstm = nn.LSTMCell(obs_dim + action_dim, hidden)
        self.fc_out = nn.Linear(hidden, 1)
        self.hidden = hidden

    def forward(self, obs, action, h_prev):
        x = torch.cat([obs, action], dim=-1)
        h, c = self.lstm(x, h_prev)
        q = self.fc_out(h)
        return q, (h, c)

    def init_hidden(self, batch_size, device='cpu'):
        h = torch.zeros(batch_size, self.hidden, device=device)
        c = torch.zeros(batch_size, self.hidden, device=device)
        return (h, c)
```

Tests (~30 min):
```python
def test_recurrent_actor_produces_time_varying_output():
    actor = RecurrentActor(obs_dim=7, action_dim=2, hidden=64)
    obs = torch.randn(1, 7)
    h = actor.init_hidden(1)
    a1, h = actor(obs, h)
    a2, h = actor(obs, h)  # same obs, different h
    assert not torch.allclose(a1, a2), "h_t should make output time-varying"

def test_recurrent_actor_batched():
    actor = RecurrentActor(7, 2, 64)
    obs = torch.randn(32, 7)
    h = actor.init_hidden(32)
    a, h_new = actor(obs, h)
    assert a.shape == (32, 2)
    assert h_new[0].shape == (32, 64)
```

### 2. `src/andes_rl_kundur/agents/replay_buffer.py` (~2 hr)

Add `SequenceReplayBuffer`. Stores full episodes; samples
fixed-length subsequences.

```python
class SequenceReplayBuffer:
    def __init__(self, capacity_episodes=200, seq_len=25, burn_in=5,
                 obs_dim=7, action_dim=2):
        self.capacity = capacity_episodes
        self.seq_len = seq_len
        self.burn_in = burn_in
        self.episodes = []  # list of dicts with arrays
        self.episode_idx = 0

    def add_episode(self, transitions):
        """transitions: list of (obs, action, reward, next_obs, done) tuples."""
        if len(self.episodes) >= self.capacity:
            self.episodes[self.episode_idx % self.capacity] = self._to_arrays(transitions)
        else:
            self.episodes.append(self._to_arrays(transitions))
        self.episode_idx += 1

    def sample(self, batch_size):
        """Returns batch of (B, T, dim) where T = seq_len + burn_in."""
        # Pick random episodes; from each, random subsequence
        T = self.burn_in + self.seq_len
        sampled_episodes = np.random.choice(len(self.episodes), batch_size, replace=True)
        batch = {k: [] for k in ('obs', 'action', 'reward', 'next_obs', 'done')}
        for ep_idx in sampled_episodes:
            ep = self.episodes[ep_idx]
            ep_len = len(ep['obs'])
            if ep_len < T:
                # Pad with last step if episode shorter than T
                start = 0
                ...
            else:
                start = np.random.randint(0, ep_len - T + 1)
            for k in batch:
                batch[k].append(ep[k][start:start+T])
        return {k: torch.tensor(np.stack(v)) for k, v in batch.items()}
```

Tests:
```python
def test_sequence_buffer_basic():
    buf = SequenceReplayBuffer(capacity_episodes=10, seq_len=10, burn_in=2,
                               obs_dim=7, action_dim=2)
    ep = [(np.random.randn(7), np.random.randn(2), 0.0,
           np.random.randn(7), False) for _ in range(20)]
    buf.add_episode(ep)
    batch = buf.sample(4)
    assert batch['obs'].shape == (4, 12, 7)
```

### 3. New file `src/andes_rl_kundur/agents/td3_lstm.py` (~3 hr)

Mirror `td3.py` (the non-recurrent TD3Agent) but with:
- `self.actor = RecurrentActor(...)`
- `self.critic1 = RecurrentCritic(...)`, `self.critic2 = RecurrentCritic(...)`
- `select_action(obs, h)` returns `(action, h_new)`
- `update(batch)` operates on sequences:
  - For each subsequence, burn-in B steps without gradient
  - Compute target Q over remaining seq_len steps using target nets + their own burn-in
  - Standard TD3 twin-critic loss + delayed actor update
- `save(path)` includes recurrent state dict; sets `algo='td3_lstm'` in ckpt

The complete TD3 algorithm with recurrence:
```
For each batch of sequences:
    Burn-in (no grad):
        h_actor = init; h_critic_1 = init; h_critic_2 = init
        h_target_actor = init; ...
        for t in 0..B-1:
            h_actor = actor.lstm(seq.obs[t], h_actor)
            h_critic_1 = critic1.lstm(seq.obs[t] + seq.action[t], h_critic_1)
            ...
    Training (grad):
        for t in B..B+L-1:
            # Compute target
            with torch.no_grad():
                target_action, h_target_actor = target_actor(seq.next_obs[t], h_target_actor) + clipped noise
                target_q1, h_target_c1 = target_critic1(seq.next_obs[t], target_action, h_target_c1)
                target_q2, h_target_c2 = target_critic2(...)
                target_q = seq.reward[t] + gamma * (1 - seq.done[t]) * min(target_q1, target_q2)
            # Critic loss
            current_q1, h_c1 = critic1(seq.obs[t], seq.action[t], h_c1)
            current_q2, h_c2 = critic2(...)
            critic_loss += mse(current_q1, target_q) + mse(current_q2, target_q)
            # Actor (delayed)
            if step % policy_delay == 0:
                actor_q1, _ = critic1(seq.obs[t], actor(seq.obs[t], h_actor)[0], h_c1_clone)
                actor_loss += -actor_q1.mean()
```

This is the trickiest part. **Test the recurrent gradient flow before
running a real training**: verify that `actor_loss.backward()`
populates `actor.lstm.weight_ih_l0.grad`. If grad is None, sequence
unrolling is broken.

### 4. `scripts/train.py` (~2 hr)

Add `--algo td3_lstm` branch. Key changes:

- Construct `TD3LSTMAgent` instead of `TD3Agent`.
- In episode rollout: maintain per-agent hidden state across steps within
  an episode; reset at episode start.
- Replay buffer: use `SequenceReplayBuffer` instead of step-level buffer.
- Store full episodes at end-of-episode (not incrementally).
- Pass `batch_size` interpretation: now batch_size = number of sequences,
  not steps.

```python
# Episode rollout
for ep in range(episodes):
    obs = env.reset(...)
    transitions = [[] for _ in range(N_AGENTS)]
    h = [agent.init_hidden(1) for agent in agents]
    for step in range(STEPS_PER_EPISODE):
        actions = {}
        for i in range(N_AGENTS):
            a, h[i] = agents[i].select_action(obs[i], h[i], noise=σ_explore)
            actions[i] = a
        next_obs, rewards, done, info = env.step(actions)
        for i in range(N_AGENTS):
            transitions[i].append((obs[i], actions[i], rewards[i], next_obs[i], done))
        obs = next_obs
        if done:
            break
    for i in range(N_AGENTS):
        agents[i].buffer.add_episode(transitions[i])
    # Per-episode update loop (run G gradient steps; G=50 typical)
    for _ in range(G):
        for i in range(N_AGENTS):
            agents[i].update()
```

### 5. `scripts/eval_ddic.py` + `paper_path.py` (~1 hr)

`paper_path.deterministic_actor_action_fn` needs to maintain hidden
state across steps within a scenario. Currently it's stateless (single
step at a time).

Suggested change:
```python
def deterministic_actor_action_fn(agents):
    h = [None for _ in agents]  # init lazily on first call
    def _fn(step, obs, n_agents):
        nonlocal h
        if h[0] is None:
            h = [agents[i].init_hidden(1) if hasattr(agents[i], 'init_hidden') else None
                 for i in range(n_agents)]
        result = {}
        for i in range(n_agents):
            if h[i] is not None:
                action, h[i] = agents[i].select_action(obs[i], h[i], deterministic=True)
            else:
                action = agents[i].select_action(obs[i], deterministic=True)
            result[i] = action
        return result
    return _fn
```

Handle scenario-boundary reset: caller must rebuild action_fn between
scenarios so hidden state resets. Or add a `reset_hidden()` method
on the fn.

### 6. `src/andes_rl_kundur/agents/checkpoint_loader.py` (~30 min)

Add `td3_lstm` branch alongside existing `td3` / `sac`. Auto-detect
via `algo` field in ckpt:

```python
algo = detect_algo(ckpt_path)
if algo == "td3_lstm":
    agent = TD3LSTMAgent(obs_dim=obs_dim, action_dim=action_dim,
                         hidden_sizes=hidden_sizes, device=device)
elif algo == "td3":
    ...
```

### 7. Tests (~1 hr)

In addition to the network tests above, add:

- `tests/test_sequence_replay_buffer.py` — basic add/sample, edge cases
  (short episode, exact-length episode, multi-episode buffer wrap)
- `tests/test_td3_lstm_agent.py` — gradient flow, save/load, deterministic
  eval produces time-varying actions across calls within an episode
- `tests/test_v4_env_regression.py` — keep existing 1e-9 paper baseline
  test passing (no regression from new agent code)

---

## Training command (predicted, when ready)

```bash
for seed in 49 50 51; do
  /home/wya/andes_venv/bin/python scripts/train.py \
      --algo td3_lstm \
      --normalize-actions \
      --episodes 75 \
      --seed $seed \
      --hidden-size 64 \
      --save-dir results/td3_lstm_h64_s$seed \
      --log-interval 10
done
```

Wall time prediction: ~15-20 min per seed (recurrent unroll is slow on
CPU; if too slow, reduce gradient_steps_per_episode). With 3 parallel
WSL, total ~20 min.

---

## Risk inventory

| Risk | Mitigation |
|---|---|
| LSTM training instability (NaN/Inf grads common with RNNs) | Gradient clipping (max_norm=10), smaller LR (1e-4 vs 3e-4 baseline) |
| Sequence buffer memory: 200 ep × 50 steps × 4 agents × ~80 floats ≈ 3 MB. Fine. | n/a |
| Per-episode update too slow (50 grad steps × 32 sequences × seq_len=25 = 40000 LSTM cell calls per gradient sweep) | Reduce G or seq_len first; profile before optimising |
| Hidden state reset bug at scenario boundary in eval | Test: run 2 scenarios back-to-back; second scenario's first action should differ from first scenario's first action only if h reset correctly |
| Codex parallel session lands a competing R56 | Use `reserve_round.py` first; if Codex took R56, bump to R57 |
| LSTM works but is WORSE than baseline | Possible — verdict it as "R56 LSTM negative", confirms the 0.334 ceiling is reward-landscape-bounded not policy-class-bounded |

---

## What "complete R56" looks like

When the next session ends, expect:

- 3 ckpts at `results/td3_lstm_h64_s{49,50,51}/`
- `results/research_loop/r56_alpha_lstm.json` — scores + diagnostic
- `results/research_loop/eval_v4_baseline/td3_lstm_h64_s{49,50,51}_load_step_{1,2}.json`
- `memory/rounds/R56/plan.md` + `verdict.md`
- New `CLM-0063` documenting the finding (positive OR negative)
- If positive: `CLM-0064` decision making LSTM the new production
  recommendation (supersede CLM-0055)
- Commit `round: R56 — LSTM recurrent actor {WIN|FAIL}`

If positive and big (mean > 0.45):
- Add `LSTMTD3Agent` to public API
- Backfill ablation: try LSTM on R48-β baseline reward (no anti-smoothness)
  and on the windowed reward together to see if LSTM unlocks BOTH
- File a Q-0005 on whether LSTM + R50 anti-smoothness combination works

---

## Reference snapshot of current state at handoff

```
Production triangle (since R48):
  0.334  TD3 norm 75ep h=64 3-seed mean (CLM-0055)
  0.351  HAWE h=64 median (CLM-0056)
  0.365  s51 h=64 single (CLM-0054)

Six-failure hexagon ceiling:
  R49 obs aug         -21%
  R50 anti-smooth W=1 -67%
  R51 SAC h=64        -68%
  R52 time-in-obs     -19%
  R54 warmstart-shared -8%
  R55 anti-smooth W=10 -67%

LSTM is one of 5 remaining structural pivots; the highest-confidence one.
Cost ~1-2 days. Success criterion: mean > 0.40 OR dM_span > 30%.
```

---

## File pointers

- This handoff: `memory/handoffs/2026-05-17_R56_lstm-actor-implementation.md`
- General arc summary: `memory/handoffs/2026-05-17_post-R55_arc-summary.md`
- Memory oracle: `memory/STATE.md`
- Round reservation tool: `memory/tools/reserve_round.py`
- Existing TD3 to mirror: `src/andes_rl_kundur/agents/td3.py`
- Networks module: `src/andes_rl_kundur/agents/networks.py`
- Replay buffer: `src/andes_rl_kundur/agents/replay_buffer.py`
- Checkpoint loader: `src/andes_rl_kundur/agents/checkpoint_loader.py`
- train.py: `scripts/train.py` (build_agents at line 179)
- eval action_fn: `src/andes_rl_kundur/evaluation/paper_path.py:47`
  (`deterministic_actor_action_fn`)
