# Actant User Manual

## What Actant Is

Actant is a human-gated workflow layer for AI engineering and research work. It helps separate planning, battle review, implementation, verification, and memory promotion.

Actant is not an automatic workflow engine. It recommends the next explicit action, but it does not automatically run the next stage.

Actant is verification-oriented by default. That does not mean every task must use TDD. It means strong completion claims require fresh evidence, while planning decides the right evidence path for the task.

## CLI And Codex Use

The open-source Actant contract is the CLI. Codex stage wrappers are optional convenience entrypoints around the same workflow when your local setup exposes them.

To install the local Actant skill bundle into Codex and register it for cross-project discovery:

```powershell
actant install-codex
```

This copies `actant` and the staged subskills into `%CODEX_HOME%\skills`, ensures `config.toml` keeps `default_mode_request_user_input = true`, and adds explicit `[[skills.config]]` entries for the installed skills. Existing threads may need a new thread or a Codex restart before they pick up the refreshed registry.

Start with Actant when a task is complex enough to benefit from structured planning or evidence:

```text
$actant Record this model iteration.
```

For chat-only work that should not write `.actant` state:

```text
$actant-planning Turn this idea into a plan.
$actant-battle Challenge this plan.
$actant-check Check whether this evidence is enough.
```

If your Codex setup exposes the staged wrappers, use `--run` to operate on the active persisted run:

```text
$actant-planning --run
$actant-battle --run
$actant-codeflow --run
$actant-check --run
$actant-evolution --run
```

Each stage recommends one next explicit action. You choose whether to run it.

## Project Initialization

From the project root:

```powershell
actant init
```

This creates `.actant/` for persisted runs.

It also creates:

- a short Actant-managed block in `AGENTS.md`
- `.actant/agent-profile.md`
- `.actant/specs/context.md`
- `.actant/specs/architecture.md`
- `.actant/specs/guides/*.md`

Re-running `actant init` updates only the managed Actant loader block and preserves user-authored `AGENTS.md` content outside it.

You do not need `actant init` for chat-only planning or review.

## Persisted Run Flow

Typical flow:

```powershell
actant init
actant start-run --activation-mode explicit-run --scope project --memory-policy promote --objective "describe the run"
actant validate
```

Then, if those optional Codex wrappers are available in your environment:

```text
$actant-planning --run
$actant-battle --run
$actant-codeflow --run
$actant-check --run
$actant-evolution --run
```

Finally:

```powershell
actant finish
```

## Stages

Verification vocabulary:

- `Verification Policy`: workflow-level rule that strong completion claims require fresh evidence, or an explicit unverified/blocked label.
- `Verification Strategy`: required planning-stage primary evidence path; exactly one family controls the first-pass evidence model.
- `Execution Style`: optional sub-strategy explaining how the chosen strategy is carried out; it is never a gate field unless later given validator-friendly semantics.

`planning`
: Define falsifiable objective, baseline, hypothesis or not-applicable reason, tasks, non-goals, evidence plan, one required `Verification Strategy`, and minimum evidence for done.

`battle`
: Challenge the plan and produce one verdict: `proceed`, `revise-and-proceed`, or `block`. A `revise-and-proceed` verdict must be incorporated into the plan before codeflow.

`codeflow`
: Implement the approved slice. Keep edits scoped. Follow the declared `Verification Strategy`. Do not add silent fallbacks, compatibility shims, swallowed errors, or best-effort branches. Maintain `fallback-audit.json` so suspicious fallback patterns in the changed surface are visible; `clear` means no known risky pattern was found, not proof that none exists.

`check`
: Verify with fresh evidence such as tests, static validation, CLI runs, artifact inspection, tiny runs, metrics, or tensor/config/dataset/checkpoint evidence. Judge whether the strategy was followed and whether the evidence is sufficient for the claim.

`evolution`
: Decide done versus carry-forward and whether memory promotion is allowed.

## When To Use Spec

| Change type | Spec expectation |
| --- | --- |
| New capability, workflow stage, CLI/API/config/schema/artifact shape, or gate semantics | Required |
| Cross-module ownership change or repeated bug-prevention rule | Required |
| Hard-to-reverse tradeoff decision that future readers will question | ADR required |
| Large refactor, experiment protocol, model/data/eval convention | Light spec recommended |
| Narrow bug fix, formatting, local implementation swap, pure cleanup | Usually skip; record run-local notes only |

Use `actant spec validate` to check the spec chain, context manifests, managed `AGENTS.md` loader, and promotion gates.

`gate.json` is agent-updated machine state, not paperwork for the user to hand-edit. Schema v5 requires evidence refs for high-impact claims only: planning readiness, battle verdict, codeflow fallback audit status, direct check evidence, and approved evolution promotion.

## Tasks

Broad plans should be split into run-local tasks:

```powershell
actant task split
actant task validate
actant task start T-001
```

One explicit run implements one active task by default. More than one active task requires a concrete `multi_task_reason` in `task-plan.json`.

## How Actant Answers

Actant answers first, explains only what matters, uses canonical project terms from `.actant/specs/context.md`, and keeps short paragraphs. It preserves exact code, CLI commands, API names, error strings, and file paths.

## What Actant Must Not Do

- no automatic stage chaining
- no broad task execution outside the active task
- no unapproved durable memory or spec promotion
- no silent fallbacks or compatibility shims during codeflow
- no more than one recommended next explicit action

## Memory Policy

Persisted runs require one memory policy:

- `promote`: run evidence may later be promoted to stable memory, only during evolution and only with user approval.
- `record-only`: keep run artifacts, but do not update stable memory.

`no-record` is valid only for chat-only/session work, not persisted runs.

## Scopes

- `project`: main AI algorithm, model, training, eval, data, loss, config, checkpoint, or tensor-boundary work.
- `side-task`: related helper task that should not steer the main lineage.
- `scratch`: temporary exploration.
- `reference`: external reading, review, package audit, or reference material.

## Useful Commands

```powershell
actant init
actant validate
actant spec list
actant spec validate
actant spec init-capability my-feature --title "My Feature"
actant spec add-context active codeflow .actant/specs/architecture.md --reason "Contract for codeflow"
actant task split
actant task validate
actant task start T-001
actant task finish T-001
actant fallback-audit scan active --file path/to/changed_file.py
actant start-run --activation-mode explicit-run --scope project --memory-policy promote --objective "..."
actant advance
actant finish
```

## More Documentation

- [Quickstart](quickstart.md)
- [Codex transcript example](../examples/codex-transcript.md)

## Current Limitations

- `actant start-run` is still explicit and somewhat verbose.
- The package is Windows-first today because the global shim is `actant.cmd`.
- Open-source packaging, installer scripts, examples, and CI are still early.
