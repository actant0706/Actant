# Subskill Invocation

Each Actant subskill may be invoked directly. Direct invocation does not imply durable state.

```yaml
direct_allowed: true
auto_chain_next_skill: false
default_activation_mode: explicit-session
writes_actant_state_only_when: explicit-run
```

## Rules

- `$actant-planning` only plans. In persisted runs it may update planning artifacts and task-control records, but it must not edit implementation files or satisfy codeflow outcomes while the current stage is still `planning`.
- `$actant-battle` only challenges a plan.
- `$actant-codeflow` only implements the requested slice when implementation was explicitly requested and plan plus battle context exist.
- `$actant-check` only checks an implementation or artifact target.
- `$actant-evolution` only curates memory and next-step decisions.
- A subskill may recommend one next explicit action.
- A subskill must not invoke the recommended next action.
- A direct subskill call writes `.actant` only when the user says to record it, continue an active run, or use `--run`.
- A request for a later-stage outcome does not authorize skipping the current stage boundary. If planning is active, stay in planning until battle and later gates allow implementation.

## Preconditions

| Subskill | Preconditions |
| --- | --- |
| `$actant-planning` | none |
| `$actant-battle` | a plan in the prompt/session or persisted run |
| `$actant-codeflow` | plan and battle summary in the prompt/session or persisted run |
| `$actant-check` | implementation/change target |
| `$actant-evolution` | check evidence; otherwise output only a proposed next-step note |

When a precondition is missing, block and ask for the missing artifact or recommend the one explicit action that would create it. Do not improvise the next stage.
