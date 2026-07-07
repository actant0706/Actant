# Stage Methods

This reference describes the internal methods Actant may use inside each stage.

## Stage Mapping

| Method family | Actant stage |
| --- | --- |
| brainstorming | planning |
| option search | planning or battle |
| plan review | battle |
| implementation | codeflow |
| debugging | planning for diagnosis, codeflow for repair, check for evidence |
| prototype design | planning for research spike design, codeflow for tiny implementation, check for tiny-run evidence |
| testing | check |
| verification | check |
| carry-forward | evolution |
| zoom-out | planning baseline and scope discovery |

## Rules

- Use the same verification vocabulary across stages:
  - `Verification Policy`: workflow-level rule that strong completion claims require fresh evidence, or an explicit unverified/blocked label.
  - `Verification Strategy`: required planning-stage primary evidence path; exactly one family controls the first-pass evidence model.
  - `Execution Style`: optional sub-strategy explaining how the chosen strategy is carried out; it is never a gate field unless later given validator-friendly semantics.
- Keep Actant's human-gated stage machine. Internal methods do not allow auto-chaining stages.
- Describe the result as an Actant stage method, not as an inherited external workflow.
- Do not create worktrees, branches, commits, or pull requests unless the user asks.
- Keep disciplined stage outputs: baseline, owner, contract, non-goals, verification path, and evidence envelope when the task needs them.
- While `planning` is active, do not modify implementation files. Planning may update planning artifacts only and must stop before codeflow work begins.
- Use subagents only when the user explicitly asks for delegated or parallel work and the current runtime supports it.

## Stage Details

Planning:
: Use brainstorming, diagnosis, prototype design, and zoom-out to produce a falsifiable objective, baseline, owner, contract or boundary, tasks, non-goals, evidence plan, one required `Verification Strategy`, and concrete minimum evidence for done. Update planning artifacts only; do not patch implementation files or runtime behavior during planning.

Battle:
: Use plan review before implementation. Challenge missing baseline, wrong owner, weak verification, wrong strategy choice, vague minimum evidence, fallback drift, memory pollution, and unresolved implementation decisions.

Codeflow:
: Review the plan before editing, keep edits scoped, preserve canonical ownership, avoid silent fallbacks, follow the declared `Verification Strategy`, and prepare a change record. When the user explicitly asks for delegated or parallel work and the runtime supports it, subagents may implement bounded portions of the approved codeflow slice, but the parent still owns integration, verification, and the final stage result.

Check:
: Use fresh evidence before claiming pass, fixed, supported, complete, or improved. Judge the result against the declared `Verification Strategy` and the actual claim strength. Report covered, not covered, and remaining risk.

Evolution:
: Decide whether the run is done, should carry forward, or should retain a failed or unverified lesson with an explicit label.
