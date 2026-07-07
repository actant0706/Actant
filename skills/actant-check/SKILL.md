---
name: actant-check
description: Actant verification subskill. Use when the user explicitly invokes $actant-check to verify an implementation or artifact target, collect direct evidence, and produce a pass, revise, or fail result; defaults to chat-only explicit-session unless --run or durable .actant recording is requested.
---

# Actant Check

Default to `explicit-session`: verify the target in chat and do not write `.actant` unless explicit run intent is present.

## Verification Terms

- `Verification Policy`: workflow-level rule that strong completion claims require fresh evidence, or an explicit unverified/blocked label.
- `Verification Strategy`: required planning-stage primary evidence path; exactly one family controls the first-pass evidence model.
- `Execution Style`: optional sub-strategy explaining how the chosen strategy is carried out; it is never a gate field unless later given validator-friendly semantics.

## Preconditions

Require an implementation or artifact target. If no target exists, block and ask for the target or recommend `$actant-codeflow`.

## Verification

Prefer direct evidence:

- tests
- static validation
- CLI runs
- artifact inspection
- focused evals, metrics, tiny runs, or tensor/config/dataset/checkpoint evidence for AI/ML work

For persisted runs, verify the active task against its task acceptance criteria, evidence expectations, declared `Verification Strategy`, minimum evidence for done, declared spec refs, and `check-context.jsonl`. Compare the result against the architecture invariants, the active task boundary, the no-auto-chain rule, and the strength of the actual claim being made.

Read `fallback-audit.json` during check. Treat `clear` as "no known risky fallback patterns found in the scanned surface," not proof that no fallback exists. Treat `findings` as acceptable only when each finding is either repaired or covered by a declared run-local fallback with reason, exact scope, user-visible behavior, and test/check/evidence support.

Use Actant's own testing and verification discipline before claiming pass, fix, or completion.

Treat `Execution Style` as explanatory detail only. It may help interpret the implementation path, but it is not a gate field and it does not replace the declared `Verification Strategy`.

Return one result:

- `pass`
- `revise`
- `fail`

If validation cannot be run, state the reason. Do not claim completion without fresh evidence or a clear validation-not-run reason.

When run intent is explicit, write `check-report.md` with a fixed section such as:

```text
Strategy Followed: yes | no
Evidence Sufficient For Claim: yes | no
Remaining Unverified:
- ...
```

`Strategy Followed` answers whether implementation respected the declared `Verification Strategy`. `Evidence Sufficient For Claim` answers whether the collected evidence supports the actual completion claim being made under the `Verification Policy`.

If `request_user_input` is available in Default mode after check finishes, ask whether to run exactly one recommended next explicit action, usually `$actant-evolution` or `$actant-evolution --run`. If the user accepts, run only that action after checking its preconditions; otherwise stop.

## Persisted Run Mode

When run intent is explicit, write `check-report.md` and update `gate.json.check`:

- `result`: `pass`, `revise`, or `fail`
- `has_direct_evidence`: true when direct evidence was collected
- `evidence_refs`: direct refs for the evidence supporting `has_direct_evidence`
- `strategy_followed`: true when the implementation respected the declared verification strategy
- `evidence_sufficient_for_claim`: true when the evidence supports the actual claim being made
- `validation_not_run_reason`: non-empty when direct evidence is unavailable

Recommend `$actant-evolution --run` as the next explicit action. Do not invoke it automatically.
