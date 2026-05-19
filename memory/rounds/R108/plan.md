---
round: R108
state: active
opened: '2026-05-19'
closed: null
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R108 plan — Wire R98 critic prototypes into train.py + offline smoke (R83-closed-negative unblocks CLM-0157 (a)(b))

**Status**: ACTIVE
**Opened**: 2026-05-19
**Driver**: R83 closed-NEGATIVE (4 wave 全 ≤ baseline 0.391). 解开 CLM-0157
"R87+ execution gated on R83 result" 锁. R98 已交付 td3_qr_lstm + td3_afe_lstm
agent + 22/22 tests; **缺最后一步 train.py dispatch**. R108 加 dispatch + 离线
smoke (无 ANDES, 仅 build_agents) — R83/R85/R96/R97/R100/R102/R103/R104/R106
全部正交.
**Parent**: R83 verdict (closed-negative, 4 wave RED) + CLM-0189 (QR proto)
+ CLM-0190 (AFE proto) + CLM-0157 (R87+ gate condition met).

## TL;DR

train.py 现状: R100 (td3_lstm_hreg) 已 wired in 47/85/305/370 行. R108 加同
pattern 的 td3_qr_lstm + td3_afe_lstm dispatch (2 个 import + 2 个 choices
entry + 2 个 elif branch + 1 个 CLI arg `--qr-n-quantiles`) + 离线 smoke test
(import train.py, parse --algo td3_qr_lstm, build_agents on dummy shapes, no
ANDES). Wall ~30 min.

不动: R98 agent 文件 / networks_critic_variants.py / td3_lstm.py / td3_lstm_hreg.py /
任何 R57+ ckpt / 任何已有 test. **改一个文件 train.py** + 加 1 个新测试 file.

## R83-closure 含义 (research-meaningful 紧迫性)

R83 4 wave 全 RED 直接证伪 obs-space-bottleneck 假设. CLM-0157 顺序:
(a) > (b) > (c). CLM-0150 part B 已 rule out (c). R96/R100 (hreg) 已 cover h-norm
regularisation 不在 CLM-0157 路径上 (CLM-0157 没 (d) h-state regularisation,
它是 R93/R100 自己的 mechanism path). R98 (a)+(b) 是 **CLM-0157 第一线**
执行步.

R108 一旦 wire 完, R109+ 可以一行启动:

```bash
# R109 candidate
python scripts/train.py --algo td3_qr_lstm --episodes 75 --seed 54 \
    --hidden-size 64 --tau 0.001 --lstm-lr-warmup-eps 5 \
    --normalize-actions --save-dir results/r109_w1_qr_lstm_s54 --final-eval

# R110 candidate
python scripts/train.py --algo td3_afe_lstm --episodes 75 --seed 54 \
    --hidden-size 64 --tau 0.001 --lstm-lr-warmup-eps 5 \
    --normalize-actions --save-dir results/r110_w1_afe_lstm_s54 --final-eval
```

WSL 当前 4 进程 (R103/R100/R102/R106). R109 + R110 等 ≥1 slot 空就跑.

## Wave 顺序

| Wave | 内容 | Wall |
|---|---|---|
| **W1** | (this file) plan.md | done |
| **W2** | train.py dispatch + import + choices + CLI flag | ~15 min |
| **W3** | tests/test_train_critic_variants_smoke.py (build_agents 不 crash on --algo td3_qr_lstm / td3_afe_lstm) | ~10 min |
| **W4** | Verdict + 1 CLM-NEW + chat brief | ~15 min |

Total wall ~40 min, **零 ANDES**.

## Smoke test design

不需要 ANDES — 只测 train.py 模块级的 `build_agents` 路径:

1. 用 dummy env-shape (`N=4, obs_dim=7, action_dim=2`)
2. 用 stub argparse Namespace 模拟 `--algo td3_qr_lstm --hidden-size 64 ...`
3. 调 `train.build_agents(args, obs_dim=7, action_dim=2, N=4)` (signature 跟
   现有 build_agents 一致)
4. assert agent list 长度 = N, 每个 agent 是 TD3QRLstmAgent
5. assert agent.algo_name == "td3_qr_lstm", agent.is_recurrent
6. 重复用 --algo td3_afe_lstm

如果 build_agents 内部 import 链触发 andes_rl_kundur env import: 用 sys.modules
stub `andes` (跟 R98 测试同 pattern).

## 资源冲突 gate

- R103/R100 training 在跑: 都 read train.py 但 process 已 load in-memory.
  我改 train.py 不影响 running processes (Python 不 re-import).
- R102 magnitude PI eval 跑: 完全不 read train.py.
- R106 env floor eval 跑: 完全不 read train.py.
- WSL 进程: 0 增 (我不 launch training, 只 wire dispatch + 离线 smoke).
- 输出 namespace: `tests/test_train_critic_variants_smoke.py` (新文件).

## 资产保护契约

不动: src/agents/{td3_lstm,td3_lstm_hreg,td3_lstm2,td3_transformer,sac,sac_ctde,td3}.py /
V4 / V4Config / base_env / paper_grade_axes / replay_buffer / 任何 R57+ ckpt /
任何已有 test.

**改动**: scripts/train.py (additive — 2 import + 2 choices entry + 2 elif +
1 CLI arg; 0 删除 / 0 重写已有行).

新建: tests/test_train_critic_variants_smoke.py.

## 测试不变量

- V4 regression 不需重跑 (零 env 改动)
- 现有 train.py 其他 algo 路径 (sac / td3 / td3_lstm / td3_lstm_hreg /
  td3_lstm2 / td3_transformer) 0 改动 → 0 regression risk
- R57+ SOTA ckpt 完全不 load 不 write

## Gate

Pass = smoke test 全过 + train.py 还能 `python -c "import scripts.train"` 不 import
错 + base agent dispatch (e.g. `--algo td3_lstm`) 路径仍 build_agents 成功 (regression).

Fail = 任一项 → 修到 pass, 不绕过.

## Cross-references

- CLM-0157 (R86 R87+ priority) — R108 closes the dispatch gap
- CLM-0189 (QR proto) — R108 wires --algo td3_qr_lstm
- CLM-0190 (AFE proto) — R108 wires --algo td3_afe_lstm
- R83 verdict (closed-NEGATIVE) — unblocks R98+R108 execution
- R100/td3_lstm_hreg dispatch (line 47/85/305/370) — pattern reference
- R104 / CLM-0188 warm-h_0 universal feasibility — parallel mechanism path,
  不互斥 (R109+ 训 td3_qr_lstm with warm-h_0 init is double fix)
