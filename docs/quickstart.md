# Actant Quickstart

This quickstart uses only commands that are covered by the current local tests.

## Optional Codex Wrappers

To install the local Actant skill bundle into your Codex home and register it in `config.toml`:

```powershell
actant install-codex
```

This keeps `%CODEX_HOME%\skills` and the Codex skill registry aligned with the current repo copy. Existing threads may need a new thread or a Codex restart before they see the refreshed skill list.

The open-source interface is the CLI. If your Codex environment exposes the optional Actant stage wrappers, you can use them directly when you do not want persisted `.actant` state:

```text
$actant-planning Turn this idea into a falsifiable plan.
$actant-battle Challenge the plan.
$actant-check Check whether the validation evidence is enough.
```

This does not require `actant init`.

## Persisted Project State

From a project root:

```powershell
actant init
actant validate
actant spec validate
```

`actant init` creates `.actant/specs/`, `.actant/agent-profile.md`, and a short managed loader block in `AGENTS.md`.

Start a run:

```powershell
actant start-run --activation-mode explicit-run --scope project --memory-policy promote --objective "demo run"
```

The command creates `.actant/status.json` and `.actant/runs/<run_id>/`.

Create and start a task when the plan is broad enough to need an explicit task boundary:

```powershell
actant task split
actant task validate
actant task start T-001
```

Add spec context only for spec files, run-local research notes, or tracked external docs:

```powershell
actant spec add-context active codeflow .actant/specs/architecture.md --reason "Contract for codeflow"
```

Validate the structure:

```powershell
actant validate
```

For codeflow handoff, scan the changed implementation surface and review `fallback-audit.json`:

```powershell
actant fallback-audit scan active --file path/to/changed_file.py
```

The audit is intentionally conservative. `clear` means no known risky fallback patterns were found in the scanned surface, while `findings` means the pattern needs repair or a run-local declaration with reason, exact scope, user-visible behavior, and evidence.

## Continue With Optional Codex Wrappers

If your Codex environment exposes the staged wrappers:

```text
$actant-planning --run
$actant-battle --run
$actant-codeflow --run
$actant-check --run
$actant-evolution --run
```

Each stage recommends the next explicit action. It does not run the next stage automatically.
