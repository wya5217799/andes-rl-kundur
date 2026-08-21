# Transition / trajectory schema

推荐使用 Parquet；每行表示一个 joint transition。数组字段必须在 `trace_metadata.json` 中声明 shape、channel order、dtype、unit。

## 身份字段

| field | type | 说明 |
|---|---|---|
| `run_id` | string | 唯一正式运行 ID |
| `object_id` | enum A/B | 禁止跨对象混合 |
| `arm_id` | string | controller/learner arm |
| `profile_bank_id` | string | bank合同 |
| `profile_id` | string | profile |
| `scenario_id` | string | signed/localized scenario |
| `training_seed` | int/null | 训练顶层单位 |
| `environment_seed` | int/null | trajectory随机性 |
| `episode_id` | string | episode |
| `step_index` | int | 从0开始 |
| `time_s` | float | 物理时间 |

## 状态与动作

| field | shape | unit/语义 |
|---|---:|---|
| `obs_t` | joint obs | frozen observation coordinates |
| `physical_state_digest` | scalar/hash | 可选完整state另存NPZ |
| `prev_executed_action` | 8 for A | normalized executed action at t-1 |
| `raw_policy_action` | 8 | pre-amplitude/slew |
| `amplitude_clipped_action` | 8 | after [-1,1] clamp |
| `executed_action` | 8 | after stateful slew projector |
| `physical_command` | 8 for A / 4 for B | actual M/D changes or power pu |
| `actuator_hidden_state_before` | variable | headroom/SOC/hysteresis/cache |
| `actuator_hidden_state_after` | variable | next actuator state |
| `active_mode_id` | string | clamp/headroom/protection branch |

## 奖励与转移

| field | 说明 |
|---|---|
| `reward_total` | actual stored reward |
| `reward_components` | common/differential/neighbor/penalties |
| `cost_components` | constrained costs |
| `next_obs` | observed next state |
| `completed` | trajectory completed |
| `valid` | protocol valid |
| `tds_failed` | simulator failure |
| `done` | Bellman terminal flag |
| `termination_reason` | explicit reason |

## Replay 与 target audit

另表 `target_audit.parquet`：

```text
transition_row_id
replay_obs
replay_prev_executed_action
replay_action
replay_reward
replay_next_obs
replay_done
target_actor_raw_action
target_projected_action
critic_current_action_input
critic_target_action_input
q1_current,q2_current
q1_target,q2_target
td_target
bellman_residual
projector_code_sha256
critic_code_sha256
```

## 完整性规则

- `next transition.prev_executed_action == current.executed_action`；
- physical command可由 executed action + headroom/mode独立重构；
- raw action不得代替executed action作为“实际动作”汇总；
- invalid/failed rows不可删除；
- 每条summary必须能映射到完整row ID集合。
