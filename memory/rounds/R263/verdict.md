# R263 verdict — durable programme and next-goal selector are operational

**Date**: 2026-07-24
**Status**: CLOSED-POSITIVE
**Type**: infra
**Wall**: ~45 min implementation, tests, and research-process audit

## TL;DR

The accepted Phase A to Phase B research direction is now encoded as a
repository-owned programme rather than chat context. New sessions have one
bootstrap path, and the read-only selector blocks duplicate work, ranks only
programme-approved open questions, and emits a complete, verifiable `/goal`
contract. The first live scientific target after this closure is Q-0027.

## What changed

- `memory/RESEARCH_PROGRAM.md` records the north star, five phase gates,
  evaluation obligations, scope limits, and kill/pivot rules.
- Root `AGENTS.md` makes that programme, STATE, and project process the
  mandatory new-session bootstrap.
- `memory/tools/research_goal.py` exposes one interface,
  `select_next_goal(repo_root)`, and a CLI/JSON representation.
- `tests/test_research_goal.py` tests selection and refusal behavior through
  the public interface.
- `CLAUDE.md` and `README.md` now point future agents to the same workflow.
- CLM-0515 records the Phase A/Phase B relationship as a durable decision.

## Gate evaluation

| Pre-registered gate | Result |
|---|---|
| Clean fixture selects Q-0027 and renders objective, reading, scope, verification, and stopping conditions | **PASS** |
| Genuine active round returns `blocked-active-round` | **PASS**; live R263 check blocked before closure |
| Stale active plan with an existing verdict does not block | **PASS** |
| Closed and unranked questions are not selected | **PASS** |
| Missing required reading fails loudly | **PASS** |
| Memory tool regression suite | **PASS**, 200 tests |
| Focused selector suite | **PASS**, 7 tests |
| R263 preflight | **PASS**, 0 BLOCK and 0 WARN |

The pre-registered outcome is **READY**. The programme and selector may now
be used to launch the first scientific milestone.

## Interpretation

This layer does not make an open-ended backlog run forever. It supplies a
bounded research state machine:

1. one durable north star and current phase;
2. one ranked, falsifiable question;
3. one active round at a time;
4. explicit evidence commands and stopping conditions;
5. a verdict that advances, closes, or pivots the question;
6. a newly selected goal only after the previous round is closed.

That matches the intended use of Codex goals: a durable objective with a
verifiable stopping condition. The repository state remains the scientific
authority, so a restarted session can recover without relying on conversation
memory or treating `/goal` as an unbounded autonomous loop.

## Claim + falsification

**Claim**: the repository can deterministically select and render the next
TPWRS-oriented research contract while refusing duplicate work during an
active round.

**Scope**: this is evidence about research orchestration, not evidence that
the proposed residual controller improves any scientific endpoint.

**Killshot**: a clean repository state that selects an unranked/closed
question, bypasses an active round, or produces a goal without required
evidence and stopping conditions falsifies the claim.

**Independent verification path**:

```powershell
python -m pytest memory/tools/tests tests/test_research_goal.py -q
python memory/tools/research_goal.py --json
python memory/tools/validate.py
python memory/tools/render.py
```

## Assets

- `AGENTS.md`
- `memory/RESEARCH_PROGRAM.md`
- `memory/tools/research_goal.py`
- `tests/test_research_goal.py`
- `memory/claims/CLM-0515.md`

## Questions opened (this round)

- (none)

## Questions closed (this round)

- (none)

## Questions advanced (this round, status unchanged)

- **Q-0027** — promoted from a chat-level suggestion to the first
  programme-ranked scientific goal, with explicit evidence and stop gates.

## 给 PI 的话

**这轮干了啥**：把“过去算法实验到底怎样通向新方向”写成仓库的长期研究纲领，并做了一个下一目标选择器；以后新会话会先恢复当前轮次，再按论文主线选一个问题。

**结果（一句话）**：自动研究基础层已经通过预注册门槛，200 项记忆工具回归和 7 项选择器测试通过；关闭 R263 后应唯一选择 Q-0027。

**这和已有实验的关系**：已有算法实验是 Phase A，不是白做；它们给出了强基线、平台期、循环网络正确性风险，以及论文指标和自创多轴指标的冲突。Phase B 正是针对这些已测出的失败机制设计残差、图泛化和安全约束。

**默认下一步**：按选择器输出启动 Q-0027，先用冻结的 R201 与 droop k=10 做预注册状态门控探针，报告物理频率端点；有协同迹象才进入修正后的多种子训练。

**你想插一脚就说**：你可以调整长期 north star、阶段顺序或 Q-0027 成功门槛；若不调整，我会依照仓库中的 programme 和 stop conditions 持续推进，而不会回到无边界的算法枚举。
