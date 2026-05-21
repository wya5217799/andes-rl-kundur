# R108 verdict — train.py dispatch wire for R98 critic prototypes (R83 unlock → R109+ ready)

**Date**: 2026-05-19
**Status**: DONE (8/8 smoke + 22/22 R98 regression all pass)
**Type**: infrastructure (1 file mod + 1 new test, 0 ANDES, 0 training)
**Wall**: ~30 min

## TL;DR

R83 closed-NEGATIVE 解开 CLM-0157 gate. R108 把 R98 已交付的 td3_qr_lstm +
td3_afe_lstm agent 接到 train.py: 2 import + 2 choices entry + 2 build_agents
elif branch + 1 CLI arg ``--qr-n-quantiles`` + 2 mutex list extension.
**修一个 pre-existing argparse `%w` bug** (line 184 `~5%` → `~5%%`, 别 session 写的).

测试: 8/8 smoke (build_agents 分发 + parse_args + ctde/warmstart rejection +
td3_lstm / td3_lstm_hreg regression) + 22/22 R98 unchanged = **30/30 combined**.
0 WSL 进程, 0 ANDES. R109/R110 training round 现在只差一行 CLI flag 启动.

## Methodology

### Wire-up pattern (mirrors td3_lstm_hreg R100 pattern)

train.py 现有 dispatch tree 6 algo (sac / td3 / td3_lstm / td3_transformer /
td3_lstm2 / td3_lstm_hreg). R108 加同模式 2 个 entry. 每个 elif branch:

1. LSTM_LR_UNCLAMP env-var clamp (lstm hyper-param protocol)
2. lr / batch=32 / buffer=200 episodes (跟 td3_lstm 一致)
3. seq=25 burn=5 (recurrent buffer 配置)
4. lr_warmup_eps argv passthrough
5. algo-specific kwargs (qr_n_quantiles for QR; nothing extra for AFE)

`--qr-n-quantiles` CLI 默认 51 (Dabney 2018 QR-DQN canonical). AFE 没新 CLI
(critic input dim 是函数 of action_dim, 不需 hyper).

### Mutex list extensions

跟着 td3_lstm_hreg 进 2 处:
- L314 `--ctde` rejection: 现在 `("td3", "td3_lstm", ..., "td3_qr_lstm", "td3_afe_lstm")`
- L527 `--warmstart-shared` rejection: 同上 (RecurrentActor state_dict 不兼容 GaussianActor)

### Sidecar fix

跑 smoke 时 parse_args 暴露 train.py L184 `~5%` argparse parse 错误
(unsupported format character 'w' at index 229 → `%(default)s` style %-formatting
看到 `%w` 不认识). 这是别 session 在 R61 注释更新中写入的 pre-existing bug —
不影响已 in-memory loaded 的 R100/R103 进程, 但任何新 `python scripts/train.py
--help` 会 crash. 1 字符 `%` → `%%` escape fix.

### Smoke test design (8 cases, all pass)

不需要 ANDES — `andes` stub + dummy env shape `(N=4, obs_dim=7, action_dim=2)`:

- 1× module-level import regression (stub OK)
- 1× parse_args 接受 `--algo td3_qr_lstm` / `--algo td3_afe_lstm`
- 2× build_agents 分发正确 (instance type, algo_name, is_recurrent)
- 2× regression: td3_lstm / td3_lstm_hreg 仍正确分发
- 2× mutex rejection: --ctde + --warmstart-shared 对两个新 algo

## Results

### File diff

| File | Δ LoC | Net change |
|---|---|---|
| ``scripts/train.py`` | +75 / -2 | 2 import + 1 CLI arg + 1 choices line ext + 2 mutex list ext + 2 elif branch + 1 char fix |
| ``tests/test_train_critic_variants_smoke.py`` | +180 / -0 | new |
| ``memory/rounds/R108/{plan,verdict}.md`` | + | new |
| ``memory/claims/CLM-0205.md`` | + | new |
| ``src/andes_rl_kundur/agents/td3_qr_lstm.py`` | 0 | unchanged (R98) |
| ``src/andes_rl_kundur/agents/td3_afe_lstm.py`` | 0 | unchanged (R98) |
| ``src/andes_rl_kundur/agents/networks_critic_variants.py`` | 0 | unchanged (R98) |
| ``src/andes_rl_kundur/agents/td3_lstm.py`` | 0 | unchanged |
| ``src/andes_rl_kundur/agents/td3_lstm_hreg.py`` | 0 | unchanged |
| 任何 R57+ ckpt | 0 | unchanged |

### Test results

```
tests/test_critic_variants.py:           22 passed  (R98)
tests/test_train_critic_variants_smoke.py: 8 passed  (R108)
combined:                                30 passed in 4.84s
```

(`tests/test_td3_lstm_agent.py` 15/15 仍 pass via earlier R98-W3 regression check.)

## Verification

- 8/8 R108 smoke 全过 ✓
- 22/22 R98 critic_variants 仍全过 ✓
- 15/15 base td3_lstm_agent 仍全过 (R98 verdict 已验, R108 不动 td3_lstm 源码) ✓
- train.py module import 不 crash (`python -c "import scripts.train"`) ✓
- `train.py --help` 不 crash (实际是修 `%w` bug 顺手解的) ✓
- V4 regression `tests/test_v4_env_regression.py` **不需重跑** (零 env / V4 / base_env 改动) ✓
- 任何 R57+ SOTA ckpt 未 load 未 write ✓
- WSL 0 新进程 (R100/R103/R102/R106 in-flight, R108 是纯 Windows 操作) ✓
- 修改的 train.py 不影响 in-flight Python processes (已 in-memory loaded) ✓

## Cross-references

- CLM-0157 (R86 R87+ priority order a > b > c, gated on R83) — R108 unlocks (a)(b)
- CLM-0189 (R98 QR proto), CLM-0190 (R98 AFE proto) — R108 makes both CLI-launchable
- CLM-0205 (this round) — train.py dispatch wire change list
- R83 verdict (closed-NEGATIVE) — gate condition met, R108 immediately follows
- R100 / td3_lstm_hreg dispatch pattern at L370 — R108 mirrors
- R104 / CLM-0188 warm-h_0 universal feasibility — R109+ can stack warm-h_0 + QR/AFE for double-fix
- R96 / CLM-0163 (value-horizon mismatch γ=0.99) — orthogonal mechanism; R109+ may also vary γ
- ADR-0001 (src layout) / ADR-0002 (V4 SSOT) — compliant (additive only, no SSOT mutation)

## Questions opened (this round)

- (none) — R108 不开新 Q, 只解锁 R109+ training execution.

## Questions closed (this round)

- (none) — Q-0014 (algorithm exploration backlog) advanced但 not 闭, 因为 (a)+(b)
  prototype 训完才能 close.

## Questions advanced (this round, status unchanged)

- **Q-0014** (open, algorithm exploration backlog) — R108 把 CLM-0157(a)+(b)
  执行 cost 从 "code-write + integration" 降到 "1 行 CLI flag + 等 WSL slot".
  R109 + R110 是 Q-0014 下个直接 follow-up. R104 warm-h_0 path 也 viable
  (Q-0022 ready); R109/R110 + R104 prototype 不互斥, 可 stack.

## 给 PI 的话

**这周干了啥**: 继续 R98 + R83 closed-NEGATIVE 解锁链. R108 = 把 R98 已交付的两个 critic-representation prototype (td3_qr_lstm + td3_afe_lstm) wire 进 train.py dispatch, 7 处 train.py 改动 (additive, 0 删除) + 1 pre-existing argparse 1-char bug 顺手修了. 8/8 smoke test 全过, 22/22 R98 critic test 仍全过 = 30/30. 0 ANDES, 0 WSL, 0 in-flight process 影响. R109/R110 现在 1 行 CLI flag 就可启动.

**结果（一句话）**: `--algo td3_qr_lstm` (51-quantile distributional critic, Dabney 2018 QR-DQN canonical) + `--algo td3_afe_lstm` (critic input `[obs, a, a², |a|, sign(a)]`, min-viable-diff) 都接好 train.py + 0-ANDES smoke test 验证 build_agents 实例化 + algo_name + is_recurrent + mutex rejection + 现有 td3_lstm/td3_lstm_hreg dispatch regression 全过. 顺手修了 train.py 一个 argparse `%w` format bug (别 session 写的, 阻挡任何 `--help` 调用).

**意外**: 4 个 WSL training/eval 进程同时跑 (R100 td3_lstm_hreg + R103 paper_strict_pure td3_lstm + R102 magnitude PI eval + R106 env floor eval) 超过 CLAUDE.md "max 3 parallel" 1 个 — 不是我开的, 是其他 session 之间的 transient overlap. R102 (~10 min) + R106 (~30 min) 都是 eval 不久就会释放, 我没改这些. R109/R110 等到 ≥1 slot 空就可以启动 (~5-15 min 等候), 我的离线工作不阻塞他们.

**我默认下一步做**: (1) 等 R102 / R106 任意一个完工 (~5-15 min). (2) 一旦 ≥1 ANDES slot 空开, 开 R109 = `--algo td3_qr_lstm` 单 seed s54 75 ep (跟 R72_w4 / R83 / R100 / R103 baseline 1:1, geo 直接比 0.391). 同时 R110 = `--algo td3_afe_lstm` 单 seed s54 75 ep, 跟 R109 平行 (但 ANDES slot 紧张就 sequential). (3) 等 R109/R110 verdict 出来对比 R72_w4=0.391: 任一 ≥ 0.45 → 找到 plateau-breaker, paper Sec.V mechanism 立论翻盘; 都 ≤ 0.391 → critic representation **also** RED, plateau 真正是 env-side 或 multi-agent-coordination side (R92 CTDE finding); 中间 → 数据点纳入 paper. 沉默就这么做.

**你想插一脚就说**: (a) 想我现在就 launch R109 即使 WSL slot 满 (CLAUDE.md 是建议不是硬限, 4 process 多半 OK) — 风险中, 我推荐 wait; (b) 想我开 R111 = stacked fix: td3_qr_lstm + R104 warm-h_0 init + R100 h-norm-reg 三个都打开看叠加效果 — 工程量 ~30 min code, 但 R109 单 fix verdict 先出来更 informative; (c) 想我直接转 paper Sec.V mechanism synthesis (R57-R108 全部 closed claim 编 paper-narrative chapter draft) — 离线 ~2h, 利用 R83 closed-NEGATIVE 这个 milestone 写综述, 跟 (a)/(b) 不互斥; (d) 想我关 R108 不管下一步 — fine, 代码 + 测试已就绪, 任何 R109+ round 一行就启动. 我推荐 **(c) paper Sec.V synthesis** 利用现在 mechanism story 已经完整的窗口期.
