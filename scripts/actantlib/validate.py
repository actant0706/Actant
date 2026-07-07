"""Cross-file validation for Actant projects and runs."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .contract import ARTIFACTS, MEMORY_POLICIES, REQUIRED_STATUS_FIELDS, SCOPES, STAGES, recovery
from .errors import ActantError
from .fallback_audit import FALLBACK_AUDIT_ARTIFACT, load_fallback_audit, validate_fallback_audit
from .gates import validate_gate_shape
from .io import actant_root, read_json, read_jsonl_rows, validate_jsonl
from .project import validate_agents_chain
from .spec import validate_context_manifest, validate_spec_file_registry
from .tasks import validate_task_plan


def _validate_recovery_fields(doc: dict[str, Any], stage: str, label: str) -> None:
    expected = recovery(stage)
    for field in ("stage", "next_recommended_stage", "next_recommended_action", "stage_summary"):
        if doc.get(field) != expected[field]:
            raise ActantError(
                f"{label} recovery mismatch for {field}: expected {expected[field]!r}, got {doc.get(field)!r}"
            )


def _validate_status_matches_run(status: dict[str, Any], run: dict[str, Any]) -> None:
    if status.get("active_run_id") != run.get("run_id"):
        raise ActantError("active run id mismatch")
    for field in ("activation_mode", "scope", "current_memory_policy", "objective"):
        status_field = "active_run_id" if field == "run_id" else field
        if field == "objective":
            if status.get("objective") != run.get("objective"):
                raise ActantError("status objective does not match run objective")
            continue
        if status.get(status_field) != run.get(field):
            raise ActantError(f"status {field} does not match run {field}")
    if status.get("stage") != run.get("stage"):
        raise ActantError("status stage does not match run stage")
    _validate_recovery_fields(status, status["stage"], "status.json")
    _validate_recovery_fields(run, run["stage"], "run.json")


def _validate_trigger_log_for_run(root: Path, run: dict[str, Any]) -> None:
    rows = read_jsonl_rows(root / "trigger-log.jsonl")
    run_rows = [row for row in rows if row.get("run_id") == run.get("run_id")]
    if not run_rows:
        raise ActantError("trigger-log.jsonl has no entries for the active run")
    latest = run_rows[-1]
    if latest.get("stage_after") != run.get("stage"):
        raise ActantError("trigger-log.jsonl latest stage_after does not match run stage")
    expected = recovery(run["stage"])
    for field in ("next_recommended_stage", "next_recommended_action", "stage_summary"):
        if latest.get(field) != expected[field]:
            raise ActantError(f"trigger-log.jsonl latest {field} does not match run recovery")


def validate_run(project: Path) -> None:
    root = actant_root(project)
    if not root.exists():
        raise ActantError(f"missing {root}")
    validate_jsonl(root / "trigger-log.jsonl")
    lineage_path = root / "memory" / "model-lineage.json"
    if lineage_path.exists():
        lineage = read_json(lineage_path)
        if not isinstance(lineage.get("entries"), list):
            raise ActantError("model-lineage.json requires entries list")
        for entry in lineage["entries"]:
            status = entry.get("status")
            if status not in {"draft", "active", "rejected", "promoted", "archived"}:
                raise ActantError(f"invalid model lineage status: {status}")

    status_path = root / "status.json"
    if not status_path.exists():
        print("Actant structure valid; no persisted run is active.")
        return
    status = read_json(status_path)
    for field in REQUIRED_STATUS_FIELDS:
        if field not in status:
            raise ActantError(f"status.json missing field: {field}")
    if status["activation_mode"] != "explicit-run":
        raise ActantError("status.json activation_mode must be explicit-run")
    if status["current_memory_policy"] not in MEMORY_POLICIES:
        raise ActantError("status.json current_memory_policy must be promote or record-only")

    run_dir = root / "runs" / status["active_run_id"]
    run = read_json(run_dir / "run.json")
    gate = read_json(run_dir / "gate.json")
    validate_gate_shape(gate)
    if gate.get("schema_version", 0) >= 5:
        validate_fallback_audit(load_fallback_audit(run_dir))
        if run.get("fallback_audit_ref") != FALLBACK_AUDIT_ARTIFACT:
            raise ActantError("run fallback_audit_ref must point to fallback-audit.json")
    if "spec" in gate or (root / "agent-profile.md").exists():
        validate_agents_chain(project)
        validate_spec_file_registry(project)
        validate_context_manifest(project, run_dir, run_dir / "codeflow-context.jsonl", "codeflow")
        validate_context_manifest(project, run_dir, run_dir / "check-context.jsonl", "check")
    if "task" in gate and gate["task"].get("task_plan_ready") is True:
        validate_task_plan(run_dir, gate)

    if run.get("activation_mode") != "explicit-run":
        raise ActantError("run activation_mode must be explicit-run")
    if run.get("scope") not in SCOPES:
        raise ActantError("run scope is invalid")
    if run.get("current_memory_policy") not in MEMORY_POLICIES:
        raise ActantError("run current_memory_policy is invalid")
    if run.get("stage") not in STAGES:
        raise ActantError("run stage is invalid")

    _validate_status_matches_run(status, run)
    _validate_trigger_log_for_run(root, run)

    artifact_refs = run.get("artifact_refs")
    if not isinstance(artifact_refs, dict):
        raise ActantError("run artifact_refs must be an object")
    for key in ARTIFACTS:
        if key not in artifact_refs:
            raise ActantError(f"run artifact_refs missing key: {key}")
        ref = artifact_refs[key]
        if ref:
            path = Path(ref)
            if not path.is_absolute():
                path = run_dir / path
            if not path.exists():
                raise ActantError(f"artifact ref does not exist: {ref}")
    print("Actant validation passed.")
