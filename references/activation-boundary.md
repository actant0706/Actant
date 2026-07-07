# Activation Boundary

Use this reference when deciding whether Actant should participate.

## Modes

`off-actant`
: Ordinary coding, chat, or one-off work. Do not read or write `.actant`.

`implicit-router`
: Read-only Actant classification. Use when the task looks like AI engineering work, a model iteration, a training/eval/data/loss/config/checkpoint boundary change, or a continuation of existing Actant work, but the user did not explicitly ask to use Actant. You may read `.actant/status.json` and the active run summary if they exist. Recommend one explicit next action. Do not write files, call subskills, implement code, advance a run, or promote memory.

`explicit-session`
: The user explicitly asks for Actant-style planning, battle, check, or evolution but does not ask to record or persist. Run one subworkflow in chat. Do not write `.actant`, advance stages, update stable memory, or auto-chain the next subskill.

`explicit-run`
: The user explicitly asks to record, persist, continue, write into `.actant`, invokes `$actant`, or uses `--run`. Use `scripts/actantctl.py` and enforce gates from `gate.json`.

## Phrase Map

| Phrase or context | Mode | Writes `.actant` |
| --- | --- | --- |
| ordinary coding/chat request | `off-actant` | no |
| AI model iteration without explicit Actant request | `implicit-router` | no |
| `use Actant to plan this` | `explicit-session` | no |
| `$actant-planning` | `explicit-session` | no |
| `$actant-planning --run` | `explicit-run` | yes |
| `$actant` | `explicit-run` | yes |
| `continue the active Actant run` | `explicit-run` | yes |
| `record this in .actant` | `explicit-run` | yes |

## Scope Defaults

| Request type | Default scope | Memory recommendation |
| --- | --- | --- |
| main AI algorithm or training/eval pipeline work | `project` | `promote` if recorded |
| related helper task | `side-task` | `record-only` if recorded |
| throwaway experiment | `scratch` | `record-only` if recorded |
| reference review or package audit | `reference` | `record-only` if recorded |

Inside an explicit run, `current_memory_policy` must be `promote` or `record-only`; `no-record` is invalid.
