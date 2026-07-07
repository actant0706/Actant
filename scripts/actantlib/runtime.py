"""Runtime commands for persisted Actant runs."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .contract import ARTIFACTS, MEMORY_POLICIES, SCOPES, STAGES, STAGE_FLOW, default_gate, recovery, status_doc
from .errors import ActantError
from .fallback_audit import FALLBACK_AUDIT_ARTIFACT, default_fallback_audit
from .gates import evaluate_stage_transition
from .io import actant_root, append_jsonl, read_json, slugify, utc_now, write_json, write_text
from .project import init_dirs


def make_run_id(objective: str, explicit_slug: str | None) -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    return f"A-{stamp}-{slugify(explicit_slug or objective)}"


def append_trigger(
    root: Path,
    *,
    skill: str,
    trigger: str,
    activation_mode: str,
    scope: str,
    memory_policy: str,
    run_id: str,
    stage_before: str,
    stage_after: str,
    decision: str,
    reason: str,
    summary: str,
) -> None:
    contract = STAGE_FLOW[stage_after]
    append_jsonl(
        root / "trigger-log.jsonl",
        {
            "timestamp": utc_now(),
            "skill": skill,
            "trigger": trigger,
            "activation_mode": activation_mode,
            "scope": scope,
            "current_memory_policy": memory_policy,
            "run_id": run_id,
            "stage_before": stage_before,
            "stage_after": stage_after,
            "next_recommended_stage": contract.next_stage,
            "next_recommended_action": contract.next_action,
            "decision": decision,
            "reason": reason,
            "stage_summary": summary,
        },
    )


def active_run_paths(project: Path) -> tuple[Path, Path, Path, dict[str, Any]]:
    root = actant_root(project)
    status = read_json(root / "status.json")
    run_id = status.get("active_run_id")
    if not run_id:
        raise ActantError("status.json has no active_run_id")
    run_dir = root / "runs" / run_id
    return root, run_dir, run_dir / "gate.json", status


def resolve_run_dir(project: Path, run_selector: str) -> Path:
    root = actant_root(project)
    if run_selector == "active":
        status = read_json(root / "status.json")
        run_selector = status.get("active_run_id")
    if not run_selector:
        raise ActantError("run id is required")
    run_dir = root / "runs" / run_selector
    if not run_dir.exists():
        raise ActantError(f"missing run: {run_selector}")
    return run_dir


def update_stage(root: Path, run_dir: Path, run: dict[str, Any], stage: str) -> None:
    now = utc_now()
    run.update(recovery(stage))
    run["updated_at"] = now
    write_json(run_dir / "run.json", run)
    write_json(root / "status.json", status_doc(run, now))


def print_transition(stage: str) -> None:
    contract = STAGE_FLOW[stage]
    print(f"Current stage: {stage}")
    print(f"Recommended next explicit action: {contract.next_action}")
    if contract.next_stage:
        print(f"Next recommended stage: {contract.next_stage}")


def start_run(args: argparse.Namespace) -> None:
    project = args.project.resolve()
    if args.activation_mode != "explicit-run":
        raise ActantError("start-run requires --activation-mode explicit-run")
    if args.memory_policy not in MEMORY_POLICIES:
        raise ActantError("start-run requires --memory-policy promote or record-only; no-record is invalid")
    if args.scope not in SCOPES:
        raise ActantError(f"invalid scope: {args.scope}")

    root = actant_root(project)
    if not root.exists():
        init_dirs(project)
    else:
        (root / "runs").mkdir(parents=True, exist_ok=True)
        (root / "memory").mkdir(parents=True, exist_ok=True)
        (root / "specs").mkdir(parents=True, exist_ok=True)
        lineage = root / "memory" / "model-lineage.json"
        if not lineage.exists():
            write_json(lineage, {"schema_version": 2, "entries": []})

    now = utc_now()
    run_id = args.run_id or make_run_id(args.objective, args.slug)
    run_dir = root / "runs" / run_id
    if run_dir.exists():
        raise ActantError(f"run already exists: {run_id}")
    run_dir.mkdir(parents=True)

    planning_contract = STAGE_FLOW["planning"]
    run = {
        "run_id": run_id,
        "objective": args.objective,
        "activation_mode": "explicit-run",
        "scope": args.scope,
        "current_memory_policy": args.memory_policy,
        "stage": "planning",
        "next_recommended_stage": planning_contract.next_stage,
        "next_recommended_action": planning_contract.next_action,
        "stage_summary": planning_contract.summary,
        "created_at": now,
        "updated_at": now,
        "parent_run_id": args.parent_run_id,
        "model_version_id": args.model_version_id,
        "hypothesis_id": args.hypothesis_id,
        "artifact_refs": {key: None for key in ARTIFACTS},
        "fallback_audit_ref": FALLBACK_AUDIT_ARTIFACT,
    }

    write_json(run_dir / "run.json", run)
    write_json(run_dir / "gate.json", default_gate())
    write_json(run_dir / FALLBACK_AUDIT_ARTIFACT, default_fallback_audit())
    write_text(run_dir / "codeflow-context.jsonl", "")
    write_text(run_dir / "check-context.jsonl", "")
    write_text(run_dir / "spec-delta.md", "# Spec Delta\n\n")
    write_json(root / "status.json", status_doc(run, now))
    append_trigger(
        root,
        skill=args.skill,
        trigger=args.trigger,
        activation_mode="explicit-run",
        scope=args.scope,
        memory_policy=args.memory_policy,
        run_id=run_id,
        stage_before="bootstrap",
        stage_after="planning",
        decision="start-run",
        reason=args.reason or "user explicitly invoked Actant persisted run",
        summary=run["stage_summary"],
    )
    print_transition("planning")


def advance(args: argparse.Namespace) -> None:
    project = args.project.resolve()
    root, run_dir, gate_path, _status = active_run_paths(project)
    run = read_json(run_dir / "run.json")
    gate = read_json(gate_path)
    target = args.through
    if target and target not in STAGES:
        raise ActantError(f"invalid --through stage: {target}")
    if target:
        raise ActantError("advance --through is disabled by the no-auto-chain invariant")
    if run.get("stage") == "done":
        print_transition("done")
        return

    before = run["stage"]
    decision = evaluate_stage_transition(before, run_dir, run, gate)
    after = decision.next_stage
    update_stage(root, run_dir, run, after)
    append_trigger(
        root,
        skill=args.skill,
        trigger=args.trigger,
        activation_mode="explicit-run",
        scope=run["scope"],
        memory_policy=run["current_memory_policy"],
        run_id=run["run_id"],
        stage_before=before,
        stage_after=after,
        decision=decision.action,
        reason=args.reason or "gate passed",
        summary=decision.message,
    )
    print_transition(after)


def finish(args: argparse.Namespace) -> None:
    project = args.project.resolve()
    root, run_dir, gate_path, _status = active_run_paths(project)
    run = read_json(run_dir / "run.json")
    gate = read_json(gate_path)
    before = run["stage"]
    if before != "done":
        if before != "evolution":
            raise ActantError("finish requires current stage evolution or done")
        decision = evaluate_stage_transition("evolution", run_dir, run, gate)
        after = decision.next_stage
        update_stage(root, run_dir, run, after)
        append_trigger(
            root,
            skill=args.skill,
            trigger=args.trigger,
            activation_mode="explicit-run",
            scope=run["scope"],
            memory_policy=run["current_memory_policy"],
            run_id=run["run_id"],
            stage_before=before,
            stage_after=after,
            decision="finish",
            reason=args.reason or "evolution gate passed",
            summary=decision.message,
        )
    print_transition("done")
