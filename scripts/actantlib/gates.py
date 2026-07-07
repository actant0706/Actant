"""Stage gate evaluation and gate-shape validation."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .contract import ARTIFACTS, MEMORY_POLICIES, STAGE_FLOW, default_gate
from .errors import ActantError
from .fallback_audit import FALLBACK_AUDIT_STATUSES, load_fallback_audit, unresolved_fallback_findings, validate_fallback_audit
from .tasks import validate_task_for_codeflow


@dataclass(frozen=True)
class TransitionDecision:
    action: str
    next_stage: str
    message: str


def artifact_exists(run_dir: Path, run: dict[str, Any], name: str) -> bool:
    ref = run.get("artifact_refs", {}).get(name)
    if ref:
        path = Path(ref)
        if not path.is_absolute():
            path = run_dir / path
    else:
        path = run_dir / ARTIFACTS[name]
    return path.exists()


def require_artifacts(run_dir: Path, run: dict[str, Any], names: list[str]) -> None:
    missing = [ARTIFACTS[name] for name in names if not artifact_exists(run_dir, run, name)]
    if missing:
        raise ActantError("missing required artifact(s): " + ", ".join(missing))


def _advance(next_stage: str) -> TransitionDecision:
    return TransitionDecision("advance", next_stage, STAGE_FLOW[next_stage].summary)


def _loop(next_stage: str) -> TransitionDecision:
    return TransitionDecision("loop", next_stage, STAGE_FLOW[next_stage].summary)


def evaluate_planning_gate(
    run_dir: Path, run: dict[str, Any], gate: dict[str, Any]
) -> TransitionDecision:
    require_artifacts(run_dir, run, ["proposal", "requirements_delta", "tasks", "plan"])
    planning = gate.get("planning", {})
    required = [
        planning.get("status") == "ready",
        planning.get("has_falsifiable_objective") is True,
        planning.get("has_hypothesis_or_na_reason") is True,
        planning.get("has_baseline") is True,
        planning.get("has_evidence_plan") is True,
        planning.get("verification_strategy_defined") is True,
        planning.get("minimum_evidence_defined") is True,
    ]
    if not all(required):
        raise ActantError("planning gate is not ready")
    require_evidence_refs(gate, "planning", "planning.status == ready")
    spec = gate.get("spec")
    if spec and spec.get("status") == "not_applicable" and not spec.get("na_reason"):
        raise ActantError("spec not_applicable requires na_reason")
    return _advance("battle")


def evaluate_battle_gate(
    run_dir: Path, run: dict[str, Any], gate: dict[str, Any]
) -> TransitionDecision:
    require_artifacts(run_dir, run, ["battle"])
    battle = gate.get("battle", {})
    verdict = battle.get("verdict")
    if verdict == "block":
        return _loop("planning")
    if verdict not in {"proceed", "revise-and-proceed"}:
        raise ActantError("battle verdict must be proceed, revise-and-proceed, or block")
    require_evidence_refs(gate, "battle", "battle.verdict")
    if battle.get("requires_plan_update") is True and battle.get("plan_update_applied") is not True:
        raise ActantError("battle verdict requires plan update before codeflow")
    if verdict == "revise-and-proceed" and battle.get("plan_update_applied") is not True:
        raise ActantError("revise-and-proceed requires plan_update_applied before codeflow")
    if "task" in gate and gate["task"].get("task_plan_ready") is True:
        validate_task_for_codeflow(run_dir, gate)
    return _advance("codeflow")


def evaluate_codeflow_gate(
    run_dir: Path, run: dict[str, Any], gate: dict[str, Any]
) -> TransitionDecision:
    require_artifacts(run_dir, run, ["change_record"])
    codeflow = gate.get("codeflow", {})
    rot_gate = codeflow.get("rot_gate")
    simplifier = codeflow.get("simplifier")
    reason = codeflow.get("simplifier_not_applicable_reason")
    if rot_gate not in {"done", "not-applicable"}:
        raise ActantError("codeflow rot_gate must be done or not-applicable")
    if simplifier != "done" and not reason:
        raise ActantError("codeflow requires simplifier done or simplifier_not_applicable_reason")
    fallback_audit = codeflow.get("fallback_audit")
    if fallback_audit not in FALLBACK_AUDIT_STATUSES:
        raise ActantError("codeflow fallback_audit must be clear, findings, or not-applicable")
    require_evidence_refs(gate, "codeflow", "codeflow.fallback_audit")
    audit = load_fallback_audit(run_dir)
    validate_fallback_audit(audit)
    if audit.get("status") != fallback_audit:
        raise ActantError("codeflow fallback_audit does not match fallback-audit.json status")
    if fallback_audit == "findings":
        unresolved = unresolved_fallback_findings(audit)
        if unresolved:
            raise ActantError(f"codeflow fallback audit has unresolved finding(s): {len(unresolved)}")
    return _advance("check")


def evaluate_check_gate(
    run_dir: Path, run: dict[str, Any], gate: dict[str, Any]
) -> TransitionDecision:
    require_artifacts(run_dir, run, ["check_report"])
    check = gate.get("check", {})
    if check.get("result") not in {"pass", "revise", "fail"}:
        raise ActantError("check result must be pass, revise, or fail")
    if check.get("has_direct_evidence") is not True and not check.get("validation_not_run_reason"):
        raise ActantError("check requires direct evidence or validation_not_run_reason")
    if check.get("result") == "pass":
        if check.get("has_direct_evidence") is not True:
            raise ActantError("check pass requires direct evidence")
        require_evidence_refs(gate, "check", "check.has_direct_evidence")
        if check.get("strategy_followed") is not True:
            raise ActantError("check pass requires strategy_followed")
        if check.get("evidence_sufficient_for_claim") is not True:
            raise ActantError("check pass requires evidence_sufficient_for_claim")
    return _advance("evolution")


def evaluate_evolution_gate(
    run_dir: Path, run: dict[str, Any], gate: dict[str, Any]
) -> TransitionDecision:
    require_artifacts(run_dir, run, ["evolution"])
    spec = gate.get("spec")
    if spec:
        if spec.get("spec_delta_required") is True and spec.get("spec_delta_applied") is not True:
            raise ActantError("required spec delta has not been applied")
        if spec.get("trigger") == "promotion":
            if spec.get("promotion_approved") is not True or not spec.get("promotion_approval_ref"):
                raise ActantError("spec promotion requires explicit user approval and promotion_approval_ref")
    evolution = gate.get("evolution", {})
    decision = evolution.get("done_decision")
    if decision not in {"done", "carry-forward"}:
        raise ActantError("evolution done_decision must be done or carry-forward")
    policy = run.get("current_memory_policy")
    if policy == "record-only" and evolution.get("promotion_approved"):
        raise ActantError("record-only runs cannot promote memory")
    if policy == "promote" and evolution.get("promotion_approved"):
        require_evidence_refs(gate, "evolution", "evolution.promotion_approved")
        if evolution.get("promotion_approved_by") != "user":
            raise ActantError("memory promotion requires promotion_approved_by=user")
        if run.get("scope") == "reference" and not evolution.get("bridge_note"):
            raise ActantError("reference promotion requires bridge_note")
        check = gate.get("check", {})
        if check.get("result") != "pass" and not evolution.get("failure_label"):
            raise ActantError("failed or unverified promotion requires failure_label")
    if policy not in MEMORY_POLICIES:
        raise ActantError("explicit run has invalid current_memory_policy")
    return _advance("done")


def evaluate_stage_transition(
    stage: str, run_dir: Path, run: dict[str, Any], gate: dict[str, Any]
) -> TransitionDecision:
    if stage == "bootstrap":
        return _advance("planning")
    if stage == "planning":
        return evaluate_planning_gate(run_dir, run, gate)
    if stage == "battle":
        return evaluate_battle_gate(run_dir, run, gate)
    if stage == "codeflow":
        return evaluate_codeflow_gate(run_dir, run, gate)
    if stage == "check":
        return evaluate_check_gate(run_dir, run, gate)
    if stage == "evolution":
        return evaluate_evolution_gate(run_dir, run, gate)
    raise ActantError(f"cannot advance from stage: {stage}")


def require_evidence_refs(gate: dict[str, Any], section: str, claim: str) -> None:
    if gate.get("schema_version", 0) < 5:
        return
    refs = gate.get(section, {}).get("evidence_refs")
    if not _is_non_empty_string_list(refs):
        raise ActantError(f"{claim} requires {section}.evidence_refs")


def _is_non_empty_string_list(value: Any) -> bool:
    return isinstance(value, list) and bool(value) and all(isinstance(item, str) and item.strip() for item in value)


def validate_gate_shape(gate: dict[str, Any]) -> None:
    expected = default_gate()
    schema_version = gate.get("schema_version", 0)
    field_introduced_at = {
        ("planning", "verification_strategy_defined"): 4,
        ("planning", "minimum_evidence_defined"): 4,
        ("check", "strategy_followed"): 4,
        ("check", "evidence_sufficient_for_claim"): 4,
        ("planning", "evidence_refs"): 5,
        ("battle", "evidence_refs"): 5,
        ("codeflow", "evidence_refs"): 5,
        ("codeflow", "fallback_audit"): 5,
        ("check", "evidence_refs"): 5,
        ("evolution", "evidence_refs"): 5,
    }
    for section, fields in expected.items():
        if not isinstance(fields, dict):
            continue
        if section in {"spec", "task", "workflow"} and section not in gate:
            continue
        if section not in gate or not isinstance(gate[section], dict):
            raise ActantError(f"gate.json missing section: {section}")
        for field in fields:
            introduced_at = field_introduced_at.get((section, field))
            if schema_version and introduced_at and schema_version < introduced_at:
                continue
            if field not in gate[section]:
                raise ActantError(f"gate.json missing field: {section}.{field}")
    workflow = gate.get("workflow")
    if workflow:
        if workflow.get("auto_chain_allowed") is not False:
            raise ActantError("workflow.auto_chain_allowed must be false")
        next_action = workflow.get("next_explicit_action")
        if isinstance(next_action, list) and len(next_action) > 1:
            raise ActantError("workflow recommends more than one next explicit action")
    spec = gate.get("spec")
    if spec:
        if spec.get("status") == "not_applicable" and not spec.get("na_reason"):
            raise ActantError("spec not_applicable requires na_reason")
        if spec.get("trigger") == "promotion":
            if spec.get("promotion_approved") is not True or not spec.get("promotion_approval_ref"):
                raise ActantError("spec promotion requires explicit user approval and promotion_approval_ref")
    _validate_asserted_evidence_refs(gate)


def _validate_asserted_evidence_refs(gate: dict[str, Any]) -> None:
    if gate.get("schema_version", 0) < 5:
        return
    claim_checks = [
        ("planning", gate.get("planning", {}).get("status") == "ready", "planning.status == ready"),
        ("battle", bool(gate.get("battle", {}).get("verdict")), "battle.verdict"),
        ("codeflow", gate.get("codeflow", {}).get("fallback_audit") in FALLBACK_AUDIT_STATUSES, "codeflow.fallback_audit"),
        ("check", gate.get("check", {}).get("has_direct_evidence") is True, "check.has_direct_evidence"),
        ("evolution", gate.get("evolution", {}).get("promotion_approved") is True, "evolution.promotion_approved"),
    ]
    for section, asserted, claim in claim_checks:
        refs = gate.get(section, {}).get("evidence_refs")
        if refs is not None and not isinstance(refs, list):
            raise ActantError(f"{section}.evidence_refs must be a list")
        if isinstance(refs, list) and any(not isinstance(item, str) or not item.strip() for item in refs):
            raise ActantError(f"{section}.evidence_refs entries must be non-empty strings")
        if asserted:
            require_evidence_refs(gate, section, claim)
