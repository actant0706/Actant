---
name: actant-planning
description: Actant planning subskill for human-gated AI engineering work. Use when the user explicitly invokes $actant-planning to produce or converge a falsifiable plan, inspect baseline evidence, record a hypothesis or not-applicable reason, define tasks and evidence, pressure-test unresolved planning decisions with one-question-at-a-time chat or popup interrogation, or capture planning docs such as decision logs and glossary/spec-update candidates; defaults to chat-only explicit-session unless --run or durable .actant recording is requested.
---

# Actant Planning

Default to `explicit-session`: plan in chat and do not write `.actant` unless the user gives explicit run intent such as `--run`, `record this in .actant`, or `continue the active Actant run`.

Planning is not codeflow. Do not modify source code, tests, configs, implementation docs, or other implementation-slice files while planning is active. In `explicit-run`, planning may update only planning-stage artifacts and task-control records. If the user asks for implementation while the current stage is still `planning`, do not implement; keep the work in planning and recommend the next explicit stage action instead.

## Verification Terms

- `Verification Policy`: workflow-level rule that strong completion claims require fresh evidence, or an explicit unverified/blocked label.
- `Verification Strategy`: required planning-stage primary evidence path; exactly one family controls the first-pass evidence model.
- `Execution Style`: optional sub-strategy explaining how the chosen strategy is carried out; it is never a gate field unless later given validator-friendly semantics.

## Output

Produce:

- falsifiable objective
- scope recommendation: `project`, `side-task`, `scratch`, or `reference`
- memory recommendation if recorded: `promote` or `record-only`
- baseline evidence inspected or missing
- hypothesis, or a reason hypothesis is not applicable
- implementation tasks
- evidence plan
- verification strategy
- why this strategy
- minimum evidence for done
- not covered initially
- risks and non-goals
- execution style when it materially clarifies first-pass execution; otherwise omit it
- one recommended next explicit action

Split broad plans into task-sized slices when the work has multiple independently verifiable changes, crosses ownership boundaries, changes both behavior and docs/specs, or would make codeflow touch unrelated files. Select exactly one active task by default, decide whether PRD and/or spec references are required, and keep acceptance and evidence expectations falsifiable. Propose a `.actant/specs/context.md` update when a new or ambiguous term is resolved; for small local changes, record `gate.json.spec.na_reason` instead.

For implementation-ready work, choose exactly one `Verification Strategy` family:

- `test-first`
- `test-alongside`
- `lighter-checks`
- `tracer-first`

If the task needs multiple evidence forms, choose one primary strategy for the first-pass evidence path and record the secondary evidence in `Minimum Evidence For Done`, not as a second strategy.

Planning outputs should include a fixed section such as:

```text
Verification Strategy: <test-first | test-alongside | lighter-checks | tracer-first>
Why This Strategy: <reason>
Minimum Evidence For Done:
- ...
Not Covered Initially:
- ...
Execution Style: <optional detail only when it clarifies execution>
```

Use Actant's own planning discipline when useful: brainstorming, zoom-out, prototype design, debugging diagnosis, and implementation-ready planning.

## Context-Grounded Plan Interrogation

Use this planning method when the user asks to be grilled, asks for popup questions, asks to narrow a plan, asks for docs during planning, or asks for plan convergence.

Inspect available repo context, Actant specs, existing planning artifacts, task state, and evidence constraints before asking the user anything. Ask only when the answer cannot be discovered from context.

Run a one-question-at-a-time loop before producing the final plan:

1. Identify unresolved decisions that affect the objective, scope, task split, verification strategy, acceptance evidence, spec/doc impact, memory policy, or next explicit action.
2. Before asking, state a `Best Current Answer` grounded in the inspected context. Make clear whether it is evidence-backed or a provisional answer based on explicit assumptions.
3. Ask exactly one decision question. Prefer `request_user_input` as the default surface whenever it is available and the decision can be expressed as 2-3 mutually exclusive choices. Put the `Best Current Answer` first as the recommended choice and include a concise tradeoff for each choice. Use chat only when `request_user_input` is unavailable or when the decision genuinely requires free-form input.
4. After each answer, update the working plan state and record how the answer changes the objective, tasks, evidence plan, or docs/spec implications. If the user does not override the recommended choice, continue from the `Best Current Answer`. Continue only while another answer could still materially change the first implementable slice.
5. Stop when the remaining uncertainty can be recorded as a risk, non-goal, or follow-up rather than changing the first implementable slice.
6. Produce the final plan only after summarizing the decisions fixed by the interrogation.

If the user wants documentation captured during this loop, produce `Decision Log`, `Glossary Candidates`, `ADR Candidates`, or `Spec Update Candidates` as needed. In `explicit-session`, keep them in chat. In `explicit-run`, use these exact artifact destinations unless the user explicitly requested a different planning-slice file:

- `plan.md` -> `## Decision Log`
- `plan.md` -> `## ADR Candidates`
- `requirements-delta.md` -> `## Glossary Candidates`
- `requirements-delta.md` -> `## Spec Update Candidates`

If one of these sections is not applicable, write `- None.` rather than inventing a new location. Propose `.actant/specs/context.md` updates for resolved durable terms when appropriate. Do not create external ADR, glossary, implementation, or product docs during planning unless the user explicitly requested those files and they are inside the planning slice.

This loop is an Actant planning method, not a new stage and not an external helper dependency. If the user explicitly asks for deeper questioning or questioning with doc capture, treat that as an optional helper mode and report its participation separately. Preserve the no-auto-chain invariant, the no-implementation planning boundary, and the "one recommended next explicit action" rule.

Do not call `$actant-battle` automatically.

If `request_user_input` is available in Default mode, ask whether to run exactly one recommended next explicit action after the plan is produced. The recommended option is usually `$actant-battle` or `$actant-battle --run`. If the user accepts, run only that action after checking its preconditions; otherwise stop.

## Stage Boundary

- Planning may create or revise planning artifacts only.
- Planning may not implement code, patch runtime behavior, edit tests as implementation work, or modify product/output artifacts outside the planning slice.
- Planning may not skip battle. Implementation belongs to `$actant-codeflow` only after battle produced a non-`block` verdict and any required plan update has been applied.
- If the active run is still in `planning`, do not satisfy requests for codeflow outcomes in the same step. Update the plan, then recommend the one correct next explicit action.

## Plan Update Mode

Use plan update mode after a battle verdict of `revise-and-proceed`.

In chat-only mode, summarize how the battle delta changes the objective, tasks, plan, or evidence plan. Do not implement the change itself during plan update mode.

In persisted run mode, update the relevant planning artifacts and set `gate.json.battle.plan_update_applied` to true only after the battle delta has been incorporated. Do not edit implementation files during this mode. If another battle pass is required, recommend `$actant-battle --run`; otherwise recommend `$actant-codeflow --run`.

## Persisted Run Mode

When run intent is explicit:

1. Start or continue the active run with `scripts/actantctl.py` from the Actant source folder, or with the installed `actant` command.
2. Create or update `proposal.md`, `requirements-delta.md`, `tasks.md`, and `plan.md`, keeping captured decision/doc sections in their fixed destinations.
3. Create or update `task-plan.json` and task-local records when the work is broad enough to split.
4. Select spec refs and context manifests only for durable contracts, not source-code paths.
5. Set `gate.json.planning.verification_strategy_defined` to true only when the planning artifacts explicitly define the strategy family.
6. Set `gate.json.planning.minimum_evidence_defined` to true only when the planning artifacts explicitly define concrete minimum evidence for done.
7. Set `gate.json.planning.evidence_refs` to the plan sections or validation output supporting the readiness claim.
8. Set `gate.json.planning.status` to `ready` only when the planning gates are actually satisfied.
9. Record the current stage as `planning` and recommend `$actant-battle --run`.
10. Do not modify implementation files while completing planning.

File existence alone never satisfies the planning gate; update `gate.json` deliberately.
