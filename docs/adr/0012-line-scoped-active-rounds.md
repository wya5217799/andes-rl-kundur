# ADR-0012: Scope active research rounds by manuscript line

- **Status:** Accepted
- **Date:** 2026-08-04
- **Deciders:** repository owner and Codex workflow review
- **Supersedes:** ADR-0009's repository-global precedence for a line-owned active round
- **Related:** ADR-0008, ADR-0009, `skills/kundur-round/SKILL.md`

## Context

The repository can carry several active manuscript lines, but cold-start and
round-reservation tools treated any active research round as a repository-wide
lock. An ICEMS experiment therefore prevented an independent model-first paper
task from even entering its own bounded context. Bypassing strict reservation
was unsafe because it also removed the protection against duplicate work after
context compression.

The repository also encoded a fixed three-process WSL ceiling. That mixed a
historical contention observation with a permanent machine-independent policy
and could not adapt to different host capacity or concurrent manuscript work.

## Decision

Every new round declares `manuscript_line` in `plan.md` frontmatter. A concrete
line id owns the round for that manuscript; explicit `null` denotes a
repository-global round. From R339 onward the field is mandatory.

`session_context.py --line <line-id>` resumes only active rounds owned by that
line plus any repository-global round. `reserve_round.py --line <line-id>
--strict-no-active --write-plan-stub` rejects a second active round on the same
line but ignores active rounds on other lines. The command accepts the
canonical line id, delivery root, or a unique delivery-root basename and writes
the canonical id into the new plan.

Frozen legacy plans are not edited. When they contain an existing
`Selected line` declaration naming a registered `paper/...` root, the tools resolve it through the
delivery-line registry. An active plan with no resolvable ownership remains a
repository-global lock, which is the safe compatibility behavior.

Formal simulation concurrency has no fixed repository process count. From
R339 onward each formal plan prospectively binds capacity evidence, a measured
whole-host process budget, its complete process count, and capacity already
reserved by other executing lines. The two allocations must fit within that
frozen budget. Native numerical threads remain pinned to one per process unless
a later evidence-backed decision changes that separate rule. Older frozen
rounds retain their declared process counts.

Round and claim identifiers remain repository-global and atomic. Protected
shared assets remain globally coordinated.

## Consequences

- One task may advance ICEMS while another advances the model-first paper.
- A compressed or duplicate session cannot start a second evidence round on
  the same manuscript line.
- General sessions without `--line` retain the conservative global view.
- Existing R338 remains byte-for-byte unchanged and is resolved as owned by
  `icems2026` from its frozen plan body.
- Faster machines may use more than three processes when prospective capacity
  evidence supports it; concurrent lines cannot each claim the full host.
