"""Single-source contracts for Actant workflow state and templates."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class StageContract:
    next_stage: str | None
    next_action: str
    summary: str


STAGE_FLOW: dict[str, StageContract] = {
    "bootstrap": StageContract(
        "planning",
        "$actant-planning --run",
        "Actant state is initialized; planning is the next explicit step.",
    ),
    "planning": StageContract(
        "battle",
        "$actant-battle --run",
        "Planning is active; prepare plan artifacts before battle.",
    ),
    "battle": StageContract(
        "codeflow",
        "$actant-codeflow --run",
        "Battle verdict allows implementation after required plan updates are applied.",
    ),
    "codeflow": StageContract(
        "check",
        "$actant-check --run",
        "Codeflow has a change record; verification is the next explicit step.",
    ),
    "check": StageContract(
        "evolution",
        "$actant-evolution --run",
        "Check report is available; curate memory and completion decision next.",
    ),
    "evolution": StageContract(
        "done",
        "$actant finish",
        "Evolution decision is recorded; finish can mark the run done.",
    ),
    "done": StageContract(None, "none", "Run is done."),
}

STAGES = tuple(STAGE_FLOW)
SCOPES = frozenset({"project", "side-task", "scratch", "reference"})
MEMORY_POLICIES = frozenset({"promote", "record-only"})
ARTIFACTS = {
    "proposal": "proposal.md",
    "requirements_delta": "requirements-delta.md",
    "tasks": "tasks.md",
    "plan": "plan.md",
    "battle": "battle.md",
    "change_record": "change-record.md",
    "check_report": "check-report.md",
    "evolution": "evolution.md",
}
REQUIRED_STATUS_FIELDS = (
    "schema_version",
    "active_run_id",
    "activation_mode",
    "scope",
    "current_memory_policy",
    "stage",
    "next_recommended_stage",
    "next_recommended_action",
    "stage_summary",
    "updated_at",
)

MANAGED_START = "<!-- actant:start -->"
MANAGED_END = "<!-- actant:end -->"

CONCRETE_EVIDENCE_MARKERS = frozenset(
    {
        "test",
        "pytest",
        "unittest",
        "validate",
        "validation",
        "command",
        "cli",
        "output",
        "file",
        "exists",
        "jsonl",
        "json",
        "manual review",
        "schema",
    }
)
GENERIC_SUCCESS_WORDS = frozenset(
    {"cleaner", "robust", "well structured", "elegant", "better", "improved", "works"}
)

SPEC_CORE_FILES = {
    "context.md": "context",
    "architecture.md": "architecture",
    "guides/index.md": "guide",
    "guides/cross-boundary.md": "guide",
    "guides/project-language.md": "guide",
    "guides/clear-answer.md": "guide",
    "guides/decision-memory.md": "guide",
}

SPEC_TEMPLATES = {
    "context.md": """# Actant Context

Glossary-only long-lived project language.

## Terms

Add terms with:

- Term:
- Definition:
- Use when:
- Avoided synonyms:
""",
    "architecture.md": """# Actant Architecture

## Always-On Invariants

- Actant execution is human-gated.
- Actant must not auto-chain stages.
- One explicit run implements one active task by default.
- Specs are long-lived contracts.
- Run artifacts are temporary control records.
- `AGENTS.md` stays a short loader.
- Operational answers stay concise and concrete.
""",
    "guides/index.md": """# Actant Guides

- `project-language.md`
- `clear-answer.md`
- `decision-memory.md`
- `cross-boundary.md`
""",
    "guides/cross-boundary.md": """# Cross-Boundary Guide

Check ownership, persistent state, public interfaces, and task boundaries before editing across modules.
""",
    "guides/project-language.md": """# Project Language Guide

- Read `.actant/specs/context.md` before codebase-specific answers when terminology matters.
- Use canonical terms from the glossary.
- Avoid invented synonyms.
- Ask one clarification question when a user term is vague or conflicts with code.
""",
    "guides/clear-answer.md": """# Clear Answer Guide

- Answer first.
- Explain only what matters.
- Use the user's language.
- Keep short paragraphs.
- Remove filler.
- Skip tool-call narration.
- Preserve exact code, CLI commands, API names, error strings, and file paths.
""",
    "guides/decision-memory.md": """# Decision Memory Guide

Create ADRs only for decisions that are hard to reverse, would make a future reader ask why, and involved a real tradeoff.
""",
}

GATE_TEMPLATE = {
    "schema_version": 5,
    "spec": {
        "status": "pending",
        "trigger": "none",
        "context_selected": False,
        "spec_delta_required": False,
        "spec_delta_applied": False,
        "promotion_approved": False,
        "promotion_approval_ref": None,
        "na_reason": None,
    },
    "task": {
        "status": "pending",
        "task_plan_ready": False,
        "active_task_id": None,
        "acceptance_defined": False,
        "prd_required": False,
        "prd_ref": None,
        "spec_refs": [],
        "one_task_per_run": True,
    },
    "workflow": {
        "auto_chain_allowed": False,
        "next_explicit_action": None,
    },
    "planning": {
        "status": "pending",
        "evidence_refs": [],
        "has_falsifiable_objective": False,
        "has_hypothesis_or_na_reason": False,
        "has_baseline": False,
        "has_evidence_plan": False,
        "verification_strategy_defined": False,
        "minimum_evidence_defined": False,
    },
    "battle": {
        "status": "pending",
        "evidence_refs": [],
        "verdict": None,
        "requires_plan_update": False,
        "plan_update_applied": False,
    },
    "codeflow": {
        "status": "pending",
        "evidence_refs": [],
        "rot_gate": "pending",
        "simplifier": "pending",
        "simplifier_not_applicable_reason": None,
        "fallback_audit": "pending",
    },
    "check": {
        "status": "pending",
        "evidence_refs": [],
        "result": None,
        "has_direct_evidence": False,
        "strategy_followed": False,
        "evidence_sufficient_for_claim": False,
        "validation_not_run_reason": None,
    },
    "evolution": {
        "status": "pending",
        "evidence_refs": [],
        "done_decision": None,
        "promotion_approved": False,
        "promotion_approved_by": None,
        "bridge_note": None,
        "failure_label": None,
    },
}


def default_gate() -> dict[str, Any]:
    return deepcopy(GATE_TEMPLATE)


def recovery(stage: str) -> dict[str, Any]:
    contract = STAGE_FLOW[stage]
    return {
        "stage": stage,
        "next_recommended_stage": contract.next_stage,
        "next_recommended_action": contract.next_action,
        "stage_summary": contract.summary,
        "blocked_on": None,
    }


def status_doc(run: dict[str, Any], now: str) -> dict[str, Any]:
    doc = {
        "schema_version": 2,
        "objective": run.get("objective"),
        "active_run_id": run["run_id"],
        "activation_mode": "explicit-run",
        "scope": run["scope"],
        "current_memory_policy": run["current_memory_policy"],
        "current_plan": run["artifact_refs"].get("plan"),
        "current_battle": run["artifact_refs"].get("battle"),
        "current_change": run["artifact_refs"].get("change_record"),
        "current_check": run["artifact_refs"].get("check_report"),
        "current_evolution": run["artifact_refs"].get("evolution"),
        "done_criteria": None,
        "updated_at": now,
        "notes": [],
    }
    doc.update(recovery(run["stage"]))
    return doc
