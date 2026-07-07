# Actant
<div align="center">
    <img src="logo.png" alt="Actant logo" width="200">
</div>


Actant is a human-gated harness for AI engineering and research workflows, with explicit planning, adversarial review, codeflow execution, verification, and repo-local memory decisions.

`v0.6` is an alpha release. The current CLI is tested on Windows, and future releases will support more platforms.

## Workflow

![Actant workflow](assets/readme/actant-workflow-v0.6.png)

Actant keeps stage transitions explicit. It does not auto-chain the workflow for you.

## Tools

### Core CLI

- `actant init` initializes repo-local Actant state.
- `actant validate` validates the local setup.
- `actant spec ...` manages repo-local specs and shared context.
- `actant start-run ...` starts an explicit persisted run.
- `actant finish` closes the current run.

### Stage Commands

- `$actant-planning` turns an objective into an explicit plan.
- `$actant-battle` runs the adversarial review before implementation.
- `$actant-codeflow` executes the approved slice.
- `$actant-check` verifies the result with fresh evidence.
- `$actant-evolution` decides done, carry-forward, and memory promotion.

### Supporting Commands

- `actant spec validate` checks the current spec state.
- `actant spec list` lists known specs and contexts.
- `actant task split` breaks a plan into tracked tasks.
- `actant task validate` checks task structure before execution.
- `actant fallback-audit scan ...` surfaces suspicious fallback patterns in the changed surface.

## Quick Start

```text
actant init
actant validate
actant start-run --activation-mode explicit-run --scope project --memory-policy promote --objective "demo run"
```

```text
$actant-planning --run
$actant-battle --run
$actant-codeflow --run
$actant-check --run
$actant-evolution --run
```

```text
actant finish
```

## Docs

- [Quickstart](docs/quickstart.md)
- [User manual](docs/actant-user-manual.md)

## Contact

If something looks wrong or unclear, open an issue or contact [me](mailto:actant@agent.qq.com).

## License

Apache-2.0. See [LICENSE](LICENSE).
