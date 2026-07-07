# Helper Integrations

Actant has five lifecycle subskills: planning, battle, codeflow, check, and evolution. Other skills are optional helpers that may strengthen a stage only when explicitly invoked or when their own trigger rules apply.

Do not turn helpers into Actant stages. Do not auto-call helpers. Do not modify helper skill trigger behavior.

## Helper Map

| Helper | Useful during | How to use |
| --- | --- | --- |
| `enhanced-reasoning-router` | Any complex Actant task | Use as reasoning middleware for uncertainty, evidence, and verification quality. It does not replace Actant gates. |
| `explicit questioning helper` | Planning or battle | Use only when the user explicitly asks for deeper one-question-at-a-time pressure testing. Actant planning otherwise prefers its native interrogation loop. |
| `explicit questioning+docs helper` | Planning or battle | Use only when the user explicitly asks for questioning plus doc capture. Actant planning otherwise prefers its native documentation capture inside planning artifacts. |
| `preventing-code-rot` | Codeflow | Use before boundary-sensitive implementation or simplification to check ownership, public interfaces, dependencies, state, and architecture drift. |
| `code-simplifier` | Codeflow | Use after a Python/code implementation slice when the user asks to simplify or when Actant codeflow records `gate.json.codeflow.simplifier = "done"`. |
| `subagent-orchestrator` | Codeflow | Use only when the user explicitly asks for delegated or parallel work and the runtime supports subagents. Keep the Actant task boundary authoritative; parent owns integration, verification, and `change-record.md`. |

## Stage Patterns

Planning:
: Actant planning has its own context-grounded interrogation loop for one-question-at-a-time plan convergence and should prefer it by default. For each question, it should first state a `Best Current Answer` from repo/spec context, then prefer `request_user_input` as the default popup surface whenever the decision fits 2-3 mutually exclusive choices. Put the `Best Current Answer` first as the recommended choice, then update the working plan before asking another question. Use chat only when popup input is unavailable or the decision truly needs free-form input. The resulting answers may be summarized into `proposal.md`, `tasks.md`, and `plan.md` only in `explicit-run` mode. External questioning remains an explicit opt-in helper, not a dependency of planning.

Planning with docs:
: Actant planning may capture a decision log plus glossary, ADR, or spec-update candidates during the interrogation loop. In `explicit-session`, keep those docs in chat. In `explicit-run`, keep them in fixed planning-artifact sections: `plan.md` for `Decision Log` and `ADR Candidates`, and `requirements-delta.md` for `Glossary Candidates` and `Spec Update Candidates`; also propose `.actant/specs/context.md` updates for resolved terms unless the user explicitly requested external planning docs. External questioning with doc capture remains an explicit opt-in helper, not a dependency of planning.

Battle:
: An explicit questioning helper can deepen adversarial review, but Actant still records only one battle verdict: `proceed`, `revise-and-proceed`, or `block`.

Codeflow:
: Actant codeflow now embeds the same rot-preflight and behavior-preserving simplification sequence by default for boundary-sensitive and Python/code slices. `preventing-code-rot` remains the explicit helper form of the boundary audit, and `code-simplifier` remains the explicit helper form of the focused cleanup pass. `subagent-orchestrator` can run `spark-worker`, `one-writer-one-reviewer`, or `split-writers-final-review` patterns for bounded active-task implementation when the user explicitly asked for delegation and write scopes are safe. For non-code work, record `simplifier_not_applicable_reason` instead.

Check:
: `enhanced-reasoning-router` can improve evidence calibration, but Actant still requires `check-report.md`, `gate.json.check.strategy_followed`, and `gate.json.check.evidence_sufficient_for_claim` for strong completion claims.

Evolution:
: Helpers may inform the memory decision, but only Actant evolution can approve promotion, and user approval is required for stable memory.

## Reporting Rule

When a helper participates, name it in the stage artifact:

```text
Helper used: code-simplifier
Evidence: <command or inspection>
Result: <short result>
```

When a helper did not participate, do not claim its benefits. Use a plain not-applicable reason when appropriate.
