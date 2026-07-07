"""Run-local task plan helpers and commands."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from .contract import CONCRETE_EVIDENCE_MARKERS, GENERIC_SUCCESS_WORDS, default_gate
from .errors import ActantError
from .io import read_json, write_json, write_text


def task_plan_path(run_dir: Path) -> Path:
    return run_dir / "task-plan.json"


def load_task_plan(run_dir: Path) -> dict[str, Any] | None:
    path = task_plan_path(run_dir)
    if not path.exists():
        return None
    plan = read_json(path)
    if not isinstance(plan, dict):
        raise ActantError("task-plan.json must be an object")
    return plan


def task_items(plan: dict[str, Any]) -> list[dict[str, Any]]:
    tasks = plan.get("tasks", [])
    if not isinstance(tasks, list):
        raise ActantError("task-plan.json tasks must be a list")
    for task in tasks:
        if not isinstance(task, dict):
            raise ActantError("task-plan.json tasks must be objects")
    return tasks


def is_concrete_text(value: Any, *, evidence: bool) -> bool:
    if not isinstance(value, str) or not value.strip():
        return False
    text = value.strip().lower()
    if text in GENERIC_SUCCESS_WORDS:
        return False
    if any(word in text for word in GENERIC_SUCCESS_WORDS) and len(text.split()) <= 5:
        return False
    if evidence and not any(marker in text for marker in CONCRETE_EVIDENCE_MARKERS):
        return False
    return True


def validate_task_plan(run_dir: Path, gate: dict[str, Any] | None = None) -> dict[str, Any]:
    plan = load_task_plan(run_dir)
    if plan is None:
        raise ActantError("missing task-plan.json")
    tasks = task_items(plan)
    active_ids: list[str] = []
    explicit_active = plan.get("active_task_id")
    if isinstance(explicit_active, str) and explicit_active:
        active_ids.append(explicit_active)
    elif isinstance(explicit_active, list):
        active_ids.extend(str(item) for item in explicit_active if item)
    for task in tasks:
        if task.get("status") == "active":
            task_id = task.get("id")
            if task_id:
                active_ids.append(str(task_id))
    unique_active = sorted(set(active_ids))
    if len(unique_active) > 1 and not plan.get("multi_task_reason"):
        raise ActantError("multiple active tasks require multi_task_reason")

    known_ids = {str(task.get("id")) for task in tasks if task.get("id")}
    if not known_ids:
        raise ActantError("task-plan.json requires at least one task")
    for task_id in unique_active:
        if task_id not in known_ids:
            raise ActantError(f"active task not found: {task_id}")

    for task in tasks:
        task_id = task.get("id") or "<unknown>"
        deps = task.get("depends_on", [])
        if not isinstance(deps, list):
            raise ActantError(f"task {task_id} depends_on must be a list")
        missing = [dep for dep in deps if str(dep) not in known_ids]
        if missing:
            raise ActantError(
                f"task {task_id} depends on missing task(s): {', '.join(map(str, missing))}"
            )
        if task.get("status") not in {"pending", "ready", "active", "done", "blocked"}:
            raise ActantError(f"task {task_id} has invalid status")
        if task.get("status") in {"ready", "active"}:
            acceptance = task.get("acceptance", [])
            evidence_items = task.get("evidence", [])
            if (
                not acceptance
                or not isinstance(acceptance, list)
                or not all(is_concrete_text(item, evidence=False) for item in acceptance)
            ):
                raise ActantError(f"task {task_id} requires concrete acceptance criteria")
            if (
                not evidence_items
                or not isinstance(evidence_items, list)
                or not all(is_concrete_text(item, evidence=True) for item in evidence_items)
            ):
                raise ActantError(f"task {task_id} requires concrete evidence expectations")
            if task.get("prd_required") is True and not task.get("prd_ref"):
                raise ActantError(f"task {task_id} requires prd_ref")
            if task.get("spec_required") is True and not task.get("spec_refs"):
                raise ActantError(f"task {task_id} requires spec_refs")
    if gate is not None:
        task_gate = gate.get("task", {})
        active_task_id = task_gate.get("active_task_id")
        if active_task_id and active_task_id not in known_ids:
            raise ActantError(f"gate active_task_id not found: {active_task_id}")
    return plan


def validate_task_for_codeflow(run_dir: Path, gate: dict[str, Any]) -> None:
    plan = validate_task_plan(run_dir, gate)
    active_task_id = gate.get("task", {}).get("active_task_id") or plan.get("active_task_id")
    if not active_task_id:
        raise ActantError("codeflow requires one active task")
    active_ids = [active_task_id] if isinstance(active_task_id, str) else list(active_task_id)
    if len(set(active_ids)) > 1 and not plan.get("multi_task_reason"):
        raise ActantError("codeflow for multiple active tasks requires multi_task_reason")


def write_tasks_markdown(run_dir: Path, plan: dict[str, Any]) -> None:
    lines = ["# Tasks", ""]
    for task in task_items(plan):
        lines.append(f"## {task.get('id')} - {task.get('title')}")
        lines.append("")
        lines.append(f"- Status: {task.get('status')}")
        lines.append(f"- Depends on: {', '.join(task.get('depends_on') or []) or 'none'}")
        lines.append(f"- Change budget: {task.get('change_budget') or 'unspecified'}")
        lines.append("")
    write_text(run_dir / "tasks.md", "\n".join(lines))


def task_list(run_dir: Path) -> None:
    plan = validate_task_plan(run_dir)
    for task in task_items(plan):
        marker = "*" if task.get("id") == plan.get("active_task_id") else "-"
        print(f"{marker} {task.get('id')} [{task.get('status')}] {task.get('title')}")


def task_validate(run_dir: Path) -> None:
    validate_task_plan(run_dir)
    print("Actant task validation passed.")


def task_split(run_dir: Path, args: argparse.Namespace) -> None:
    path = task_plan_path(run_dir)
    if path.exists() and not args.force:
        raise ActantError("task-plan.json already exists; use --force to replace it")
    plan = {
        "schema_version": 1,
        "active_task_id": "T-001",
        "multi_task_reason": None,
        "tasks": [
            {
                "id": "T-001",
                "title": args.title,
                "status": "ready",
                "depends_on": [],
                "change_budget": "single-concern",
                "prd_ref": None,
                "spec_refs": args.spec_ref or [],
                "acceptance": args.acceptance
                or ["Validation command reports the task acceptance boundary as satisfied"],
                "evidence": args.evidence or ["actant task validate command passes"],
            }
        ],
    }
    write_json(path, plan)
    write_tasks_markdown(run_dir, plan)
    (run_dir / "tasks" / "T-001").mkdir(parents=True, exist_ok=True)
    write_text(run_dir / "tasks" / "T-001" / "task.md", f"# T-001 - {args.title}\n")
    validate_task_plan(run_dir)
    print("Created task-plan.json with active task T-001")


def task_start(run_dir: Path, task_id: str) -> None:
    plan = validate_task_plan(run_dir)
    tasks = task_items(plan)
    target = next((task for task in tasks if task.get("id") == task_id), None)
    if not target:
        raise ActantError(f"task not found: {task_id}")
    done = {task.get("id") for task in tasks if task.get("status") == "done"}
    missing = [dep for dep in target.get("depends_on", []) if dep not in done]
    if missing:
        raise ActantError(f"task dependencies are not done: {', '.join(missing)}")
    active = [
        task.get("id")
        for task in tasks
        if task.get("status") == "active" and task.get("id") != task_id
    ]
    if active and not plan.get("multi_task_reason"):
        raise ActantError("second active task requires multi_task_reason")
    target["status"] = "active"
    plan["active_task_id"] = task_id
    write_json(task_plan_path(run_dir), plan)
    gate_path = run_dir / "gate.json"
    if gate_path.exists():
        gate = read_json(gate_path)
        gate.setdefault("task", default_gate()["task"])
        gate["task"].update(
            {
                "status": "ready",
                "task_plan_ready": True,
                "active_task_id": task_id,
                "acceptance_defined": True,
                "prd_required": bool(target.get("prd_required")),
                "prd_ref": target.get("prd_ref"),
                "spec_refs": target.get("spec_refs", []),
                "one_task_per_run": not bool(plan.get("multi_task_reason")),
            }
        )
        write_json(gate_path, gate)
    print(f"Started task: {task_id}")


def task_finish(run_dir: Path, task_id: str) -> None:
    plan = validate_task_plan(run_dir)
    for task in task_items(plan):
        if task.get("id") == task_id:
            task["status"] = "done"
            if plan.get("active_task_id") == task_id:
                plan["active_task_id"] = None
            write_json(task_plan_path(run_dir), plan)
            print(f"Finished task: {task_id}")
            return
    raise ActantError(f"task not found: {task_id}")

