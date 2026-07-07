---
name: actant-battle
description: Actant battle-review subskill. Use when the user explicitly invokes $actant-battle to challenge an Actant plan, identify blockers, and produce a proceed, revise-and-proceed, or block verdict; defaults to chat-only explicit-session unless --run or durable .actant recording is requested.
---

# Actant Battle

Default to `explicit-session`: review the plan in chat and do not write `.actant` unless explicit run intent is present.

## Verification Terms

- `Verification Policy`: workflow-level rule that strong completion claims require fresh evidence, or an explicit unverified/blocked label.
- `Verification Strategy`: required planning-stage primary evidence path; exactly one family controls the first-pass evidence model.
- `Execution Style`: optional sub-strategy explaining how the chosen strategy is carried out; it is never a gate field unless later given validator-friendly semantics.

## Preconditions

Require a plan in the prompt/session or a persisted run plan. If no plan is available, block and recommend `$actant-planning`.

## Review

Challenge:

- objective falsifiability
- baseline sufficiency
- ownership and boundary clarity
- evidence plan
- verification strategy presence and family choice
- whether the chosen verification strategy matches task risk and task shape
- whether minimum evidence for done is concrete and falsifiable
- memory scope and promotion risk
- no-fallback and no-auto-chain constraints
- likely failure modes
- missing contract or declared spec context
- active task size, dependency order, and acceptance concreteness
- glossary drift and unclear output expectations

Use Actant's own battle-review discipline to stress-test the plan before implementation.

If the user explicitly asks for deeper questioning, use one-question-at-a-time interrogation before finalizing the verdict. If the user asks for questioning with doc capture, use that as an external helper mode and keep Actant gate state separate.

Return one verdict:

- `proceed`
- `revise-and-proceed`
- `block`

For `revise-and-proceed`, also output:

- required plan updates
- required task changes
- required verification-strategy changes
- required evidence-plan changes
- whether another battle pass is required

Recommend exactly one next explicit action. Do not call `$actant-codeflow` automatically.

If `request_user_input` is available in Default mode and the verdict is not `block`, ask whether to run exactly one recommended next explicit action. For `proceed`, this is usually `$actant-codeflow` or `$actant-codeflow --run`; for `revise-and-proceed`, it is the required planning update. If the user accepts, run only that action after checking its preconditions; otherwise stop.

## Persisted Run Mode

When run intent is explicit, write `battle.md`, set `gate.json.battle.verdict`, and add `gate.json.battle.evidence_refs` pointing to the verdict section or review evidence. The evidence ref is for the high-impact verdict claim only; do not turn every battle note into a required citation.

- `proceed`: set `requires_plan_update` to false and recommend `$actant-codeflow --run`.
- `revise-and-proceed`: set `requires_plan_update` to true and keep `plan_update_applied` false until `$actant-planning --run` incorporates the battle delta into `proposal.md`, `tasks.md`, `plan.md`, or `requirements-delta.md`, including any required verification-strategy or minimum-evidence changes.
- `block`: return to planning.

Do not recommend `$actant-codeflow --run` while a required plan update is unapplied.
