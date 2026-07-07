---
name: actant
description: Human-gated Actant router and persisted run controller for AI engineering workflows. Use for implicit read-only Actant routing, explicit Actant sessions, and explicit persisted Actant runs with script-enforced gates, scoped memory policy, JSON/JSONL state, and manual next-action recommendations.
---

# Actant

Actant is a human-controlled activation layer, not an automatic workflow engine.

Use it to decide whether Actant should participate, to run chat-only Actant methods when explicitly requested, or to create/continue a persisted `.actant` run only when the user explicitly asks for durable Actant state.

## Activation Boundary

Choose exactly one mode:

- `off-actant`: ordinary work. Do not read or write `.actant`.
- `implicit-router`: read-only routing. You may read `.actant/status.json` and the active run summary if they exist, classify whether Actant is useful, and recommend one explicit next action. Do not write files, start runs, advance stages, call subskills, implement code, or promote memory.
- `explicit-session`: the user explicitly wants Actant's method but not durable state. Run one Actant-style workflow in chat. Do not create or modify `.actant`, advance stages, write trigger logs, or auto-chain subskills.
- `explicit-run`: the user explicitly asks Actant to record, persist, continue, write into `.actant`, invokes `$actant`, or uses `--run`. Use `.actant` state and `scripts/actantctl.py`.

Read `references/activation-boundary.md` when activation intent is ambiguous.

## Scope and Memory Policy

Persisted runs require:

- `scope`: `project`, `side-task`, `scratch`, or `reference`
- `current_memory_policy`: `promote` or `record-only`

Never use `no-record` inside an `explicit-run`. Use `session_memory_policy: no-record` only for `off-actant`, `implicit-router`, and `explicit-session`.

Promotion to stable `.actant` memory is allowed only during `$actant-evolution --run`, only with evidence, and only when the user approves promotion.

## Persisted Runs

Use the stdlib-only CLI:

```bash
actant init
actant start-run --activation-mode explicit-run --scope project --memory-policy promote
actant advance
actant validate
actant finish
```

The state machine is:

```text
bootstrap -> planning -> battle -> codeflow -> check -> evolution -> done
```

Each `advance` moves at most one stage unless the user explicitly supplied `--through <stage>`. Every persisted transition must leave recovery fields in `status.json`, `run.json`, and `trigger-log.jsonl`:

- `stage`
- `next_recommended_stage`
- `next_recommended_action`
- `stage_summary`

After every persisted transition, tell the user:

```text
Current stage: <stage>
Recommended next explicit action: <action>
```

The recommendation is a reminder only. Do not invoke it automatically.

## Interactive Next Action Gate

When `request_user_input` is available in Default mode, use it as Actant's first handoff step after planning, battle, codeflow, check, evolution, or a router recommendation.

Offer exactly one recommended next explicit action and one stop/defer option. The recommended option should name the exact command or subskill, such as `$actant-battle --run` or `$actant-codeflow`. If the user chooses the recommended option, run only that one action and re-check its normal preconditions before doing any work. If the user stops or does not answer, do not advance, simulate, or mark complete the next stage.

This gate is human approval, not auto-chaining. It must preserve the no-auto-chain invariant and the "at most one next explicit action" rule.

## Subskills

Direct subskill invocation is allowed and defaults to `explicit-session` unless the user provides run intent such as `--run`, `record this in .actant`, or `continue the active Actant run`.

- `$actant-planning` only plans.
- `$actant-battle` only challenges a plan.
- `$actant-codeflow` only implements a requested slice when a plan and battle summary are present.
- `$actant-check` only verifies a change target.
- `$actant-evolution` only curates completion and memory decisions.

When the current stage is `planning`, planning may update planning artifacts only. It must not edit implementation files, satisfy codeflow outcomes, or skip directly to implementation.

Read `references/subskill-invocation.md` before routing direct subskill calls or deciding whether a subskill may write `.actant`.

## Built-In Stage Methods

Actant may use internal planning, review, implementation, debugging, testing, verification, and carry-forward methods inside its own stages when they strengthen the result.

Read `references/stage-methods.md` when an Actant stage needs those methods. Describe them as Actant stage methods rather than as external skill inheritance.

Helper skills and helper modes such as questioning helpers, `code-simplifier`, `preventing-code-rot`, `enhanced-reasoning-router`, and `subagent-orchestrator` remain explicit opt-in helpers.

## Gates

Gates apply only to `explicit-run` records. The parser source of truth is `.actant/runs/<run_id>/gate.json`; Markdown artifacts are for human review.

Required machine files:

```text
.actant/status.json
.actant/runs/<run_id>/run.json
.actant/runs/<run_id>/gate.json
.actant/runs/<run_id>/task-plan.json
.actant/runs/<run_id>/codeflow-context.jsonl
.actant/runs/<run_id>/check-context.jsonl
.actant/runs/<run_id>/fallback-audit.json
.actant/runs/<run_id>/spec-delta.md
.actant/trigger-log.jsonl
.actant/memory/model-lineage.json
```

Human artifacts are created lazily by stage:

```text
proposal.md
requirements-delta.md
tasks.md
plan.md
battle.md
change-record.md
check-report.md
evolution.md
```

Use `actantctl.py validate` before claiming a persisted run is structurally sound, and `actantctl.py finish` before claiming it is done.

In schema v5, `gate.json` is an agent-updated claim ledger. Require evidence refs only for high-impact claims: `planning.status == ready`, `battle.verdict`, `codeflow.fallback_audit`, `check.has_direct_evidence`, and `evolution.promotion_approved`. Fallback audit status exposes risk on the scanned surface; it is not proof that fallback behavior is absent.

## Spec And Task Controls

`actant init` installs a short root `AGENTS.md` managed block and keeps durable Actant rules in `.actant/agent-profile.md` and `.actant/specs/`.

Use specs for new capabilities, workflow stages, CLI/API/config/schema/artifact-shape changes, stage or gate semantics, cross-module ownership changes, repeated bug-prevention rules, and durable tradeoff decisions. Skip specs for narrow bug fixes, formatting, and local implementation swaps with no lasting contract impact.

Task records are run-local control artifacts. Planning may split broad work into tasks, but one explicit run implements one active task by default. Multiple active tasks require a validator-visible `multi_task_reason`.

Every stage may recommend at most one next explicit action and must not call, simulate, or mark complete the next stage.
