---
name: actant-evolution
description: Actant evolution subskill. Use when the user explicitly invokes $actant-evolution to decide done versus carry-forward, curate memory promotion, update model lineage only with approval, and preserve a recovery note; defaults to chat-only explicit-session unless --run or durable .actant recording is requested.
---

# Actant Evolution

Default to `explicit-session`: curate the next-step decision in chat and do not write `.actant` unless explicit run intent is present.

## Preconditions

Require check evidence. If check evidence is missing, output only a proposed next-step note and recommend `$actant-check`.

## Decisions

Choose:

- `done`: the run can finish
- `carry-forward`: the run leaves follow-up work

For memory:

- `record-only` runs cannot promote stable memory.
- `promote` runs may promote only during evolution, only with evidence, and only with explicit user approval.
- Spec deltas may be recommended, but promotion into `.actant/specs/` requires `gate.json.spec.promotion_approved = true` and a non-empty `promotion_approval_ref`.
- Reference-scope promotion into project memory requires a bridge note.
- Failed or unverified lessons require a failure label.

Use Actant's own carry-forward discipline: record what was verified, what remains risky, and which follow-up should become the next explicit action.

Do not silently patch other skills or stable memory.

If `request_user_input` is available in Default mode after evolution finishes, ask whether to run exactly one recommended next explicit action, usually `$actant finish` for persisted runs. If the user accepts, run only that action after checking its preconditions; otherwise stop.

## Persisted Run Mode

When run intent is explicit, write `evolution.md` and update `gate.json.evolution`:

- `done_decision`: `done` or `carry-forward`
- `promotion_approved`: true only when the user approved promotion
- `evidence_refs`: required when `promotion_approved` is true, pointing to user approval and supporting run evidence
- `promotion_approved_by`: `user` when promotion is approved
- `bridge_note`: required for reference promotion
- `failure_label`: required when retaining lessons from failed or unverified runs

Recommend `$actant finish` as the next explicit action. Do not run it automatically.
