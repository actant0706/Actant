---
name: actant-codeflow
description: Actant implementation subskill. Use when the user explicitly invokes $actant-codeflow to implement an approved Actant slice with plan and battle context, no silent fallbacks, scoped edits, a change record, and an explicit opt-in delegated subagent mode when the user asks for parallel or delegated execution; defaults to chat-only explicit-session unless --run or durable .actant recording is requested.
---

# Actant Codeflow

Default to `explicit-session`: implement only when the user explicitly requested implementation. Do not write `.actant` unless explicit run intent is present.

## Verification Terms

- `Verification Policy`: workflow-level rule that strong completion claims require fresh evidence, or an explicit unverified/blocked label.
- `Verification Strategy`: required planning-stage primary evidence path; exactly one family controls the first-pass evidence model.
- `Execution Style`: optional sub-strategy explaining how the chosen strategy is carried out; it is never a gate field unless later given validator-friendly semantics.

## Preconditions

Require:

- a plan in the prompt/session or persisted run
- a battle summary or verdict in the prompt/session or persisted run
- verdict not `block`
- a declared verification strategy for implementation-ready work, such as `test-first`, `test-alongside`, `lighter-checks`, or `tracer-first`

If any precondition is missing, block instead of improvising implementation.

## Implementation Rules

- Keep edits scoped to the approved slice.
- Implement only `gate.json.task.active_task_id` by default when a persisted run has a task plan.
- Read task-local context and `codeflow-context.jsonl` before implementation in persisted runs.
- Return to planning instead of editing outside the active task boundary.
- Update specs during codeflow only when the approved task changes a declared long-lived contract.
- Preserve the canonical owner and source of truth.
- Do not add silent fallbacks, compatibility shims, swallowed errors, or best-effort branches.
- Use Actant's own implementation discipline: review the plan first, check missing decisions, keep edits scoped, and require fresh evidence before completion claims.
- Follow the approved verification strategy instead of inventing a new one during implementation.
- If planning marked the task `test-first`, do not skip directly to implementation-first work. Prepare the failing/targeted test path before or as the first implementation step.
- If planning marked the task `test-alongside`, keep implementation and checks moving together instead of deferring verification setup entirely to `check`.
- If planning marked the task `lighter-checks`, do not invent fake unit-test obligations; prepare the promised lighter evidence path instead.
- If planning marked the task `tracer-first`, build the thin tracer, smoke, tiny-run, or realistic narrow evidence path before broadening the implementation surface.
- Keep completion claims inside the declared evidence envelope. Codeflow may prepare evidence paths, but `check` still decides whether the evidence is sufficient.
- Do not auto-call `$actant-check`.
- For boundary-sensitive changes, run a rot preflight before broadening the edit or starting cleanup. Inspect the smallest changed slice, classify the touched code as interface, implementation, persistent-state owner, reusable module, integration/mainboard, or plugin/feature code, then check for rot vectors such as avoidable public API or schema churn, new cross-module dependency direction, leaked persistent state, broad config or untyped flag bags becoming implicit interfaces, premature shared helpers, or integration code absorbing feature detail. Use `preventing-code-rot` when it is explicitly invoked or clearly triggered by its own rules; otherwise perform the same preflight locally and make the smallest preventative edit that preserves the boundary.
- For Python/code slices, run a simplification sequence after the main implementation path is in place. Pick the smallest touched slice worth simplifying, preserve exact behavior, avoid compatibility paths, fallback branches, speculative abstraction, or clever compression, make one focused cleanup at a time, then run the narrowest executable validation available for that slice. Use `code-simplifier` when it is explicitly invoked or clearly triggered by its own rules; otherwise perform the same simplification sequence locally and record the result in the change record or `gate.json`.
- For docs, manifest, config-only, or other non-code slices, record `simplifier_not_applicable_reason`.
- Run or update the run-local fallback audit before handing off to check. The audit exposes suspicious fallback patterns on the changed surface; it does not prove fallback behavior is absent.

When the verification strategy is missing, weak, or contradictory to the approved task risk, stop and return to planning or battle instead of silently choosing a different evidence model inside codeflow.

## Delegated Subagent Mode

Use subagent mode only when the user explicitly asks for delegated or parallel work, such as "use subagents", "delegate this", "parallel workers", or "with subagents", and only when the current runtime exposes subagent tools.

When subagent mode is active, begin with a compact delegation banner:

```text
Mode: actant-codeflow/subagents
Visible outputs: delegation ledger, worker brief summary, returned status, integration decision
Delegation: tool-search-pending | used | skipped_by_policy | unavailable_after_tool_search | tool_search_unavailable
State persistence: chat-only unless explicit-run
Exit condition: delegated codeflow result is integrated or parent-only fallback completes
```

Subagent mode does not relax normal codeflow boundaries:

- Stay inside the approved codeflow slice and active task boundary.
- Do not delegate planning, battle, or stage-transition decisions.
- Do not let workers edit outside their explicit write scope.
- Do not let workers recursively spawn subagents.
- Do not auto-call `$actant-check`.
- Parent owns decomposition, worker briefs, model/reasoning selection, integration, verification, `change-record.md`, and the final user-facing result.

Use subagents only when the overhead is justified. If the task is small, tightly coupled, blocked on immediate parent judgment, or has overlapping write ownership, skip delegation and report a degradation line:

```text
Degradation: subagent codeflow -> skipped_by_policy; reason: <specific reason>; parent fallback: <what will happen instead>
```

Prefer these orchestration patterns:

- `spark-worker`: one bounded writer for a local codeflow slice.
- `one-writer-one-reviewer`: one writer plus one read-only reviewer for higher-risk implementation.
- `split-writers-final-review`: multiple writers only when write scopes are explicitly disjoint; parent integrates and may use a final reviewer.

Do not use parallel writers when two workers could touch the same files, ownership boundary, or invariant. If the write scopes overlap, keep execution parent-only or serialize the work.

Before spawning workers, run the subagent tool-discovery gate and the cost gate:

1. Confirm that delegation was explicitly requested.
2. Check whether at least one worker can materially benefit from narrower context, cheaper model/reasoning, parallelism, or independent review.
3. Discover and use subagent tools only when the runtime supports them.
4. If delegation is unavailable or unsafe, report degradation and continue parent-only when useful.

Every worker brief must stay bounded:

- role: `explorer`, `worker`, or `reviewer`
- one mission only
- minimal context
- exact read scope
- exact write scope or `none`
- forbidden actions, including no recursive subagents and no edits outside scope
- model/reasoning choice within the parent ceiling
- validation expectations
- output schema with status, changed files, summary, validation, concerns, and needs

If `request_user_input` is available in Default mode after codeflow finishes, ask whether to run exactly one recommended next explicit action, usually `$actant-check` or `$actant-check --run`. If the user accepts, run only that action after checking its preconditions; otherwise stop.

## Persisted Run Mode

When run intent is explicit, write `change-record.md` and update `gate.json.codeflow`:

- `rot_gate`: `done` or `not-applicable`
- `simplifier`: `done` when a code simplification review was performed
- `simplifier_not_applicable_reason`: non-empty when simplification is not applicable
- `fallback_audit`: `clear`, `findings`, or `not-applicable`
- `evidence_refs`: include `fallback-audit.json` or the validation output supporting the fallback audit claim

Also write or update `fallback-audit.json`. Use `clear` only when the scanned surface has no known risky patterns, `findings` when suspicious fallback patterns remain and are declared or repaired, and `not-applicable` only when the task has no meaningful code-path fallback surface. Declared fallbacks are run-local and must include reason, exact scope, user-visible behavior, and a test, check, evidence ref, or explicit not-applicable reason.

In `change-record.md`, also record the verification strategy that codeflow followed and what implementation-side evidence path was prepared:

```text
Rot Review:
- Findings: <No rot vectors found | concise findings>
- Boundary preserved: <owner/interface/dependency rule>
- Preventative edit: <none | short edit>
Verification Strategy Followed: <test-first | test-alongside | lighter-checks | tracer-first>
Why Followed: <short reason from the approved plan>
Simplification Review:
- Target slice: <file or symbol | not-applicable>
- Result: <done | not-applicable>
- Validation: <exact command | none available>
Prepared Evidence Path:
- <targeted test path | lighter checks | tracer path | tiny run path>
Not Yet Verified Here:
- <what still belongs to check>
Fallback Audit:
- Status: <clear | findings | not-applicable>
- Coverage: <changed-files-static | reason for not-applicable>
- Declared Fallbacks: <none | concise list with scope and evidence ref>
```

`Execution Style` may be recorded when it clarifies how the strategy was carried out, but it does not replace the required strategy field and it does not become a gate field.

If a local simplification review could not run executable validation, say that plainly in `change-record.md` instead of inventing a softer fallback story.

When subagent mode was used, record it in `change-record.md`:

```text
Helper used: subagent-orchestrator
Pattern: <spark-worker | one-writer-one-reviewer | split-writers-final-review>
Delegation scope: <active task slice>
Validation: <worker checks plus parent integration checks>
Result: <short result>
```

Recommend `$actant-check --run` as the next explicit action. Do not invoke it automatically.
