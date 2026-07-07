"""Spec-system helpers and spec command implementations."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .contract import SPEC_CORE_FILES
from .errors import ActantError
from .gates import validate_gate_shape
from .io import actant_root, append_jsonl, normalize_rel, read_json, relative_to_project, write_json, write_text
from .project import validate_agents_chain
from .runtime import resolve_run_dir


def load_spec_registry(root: Path) -> dict[str, dict[str, Any]]:
    registry_path = root / "specs" / "registry.json"
    if not registry_path.exists():
        return {}
    data = read_json(registry_path)
    entries = data.get("entries", [])
    if not isinstance(entries, list):
        raise ActantError("spec registry entries must be a list")
    registry: dict[str, dict[str, Any]] = {}
    for entry in entries:
        path = entry.get("path")
        if not path:
            raise ActantError("spec registry entry missing path")
        if not entry.get("trigger_class"):
            raise ActantError(f"spec registry entry missing trigger_class: {path}")
        if entry.get("accepted") is not True:
            raise ActantError(f"spec registry entry is not accepted: {path}")
        registry[str(path).replace("\\", "/")] = entry
    return registry


def spec_markdown_files(root: Path) -> list[Path]:
    specs = root / "specs"
    if not specs.exists():
        return []
    return sorted(path for path in specs.rglob("*.md") if path.is_file())


def validate_spec_file_registry(project: Path) -> None:
    root = actant_root(project)
    registry = load_spec_registry(root)
    for path in spec_markdown_files(root):
        rel = normalize_rel(path.relative_to(project))
        dotted = f".{rel}" if not rel.startswith(".") else rel
        if normalize_rel(path.relative_to(root / "specs")) in SPEC_CORE_FILES:
            continue
        if (
            "/adr/" in dotted
            or "/capabilities/" in dotted
            or "/guides/" in dotted
            or not dotted.endswith(".actant/specs/architecture.md")
        ):
            if dotted not in registry:
                raise ActantError(f"spec file lacks accepted trigger record: {dotted}")


def context_entry_allowed(project: Path, run_dir: Path, file_ref: str) -> bool:
    rel = relative_to_project(project, file_ref)
    rel_text = normalize_rel(rel)
    if rel_text.startswith(".actant/specs/") and rel_text.endswith(".md"):
        return (project / rel).exists()
    try:
        run_rel = (project / rel).resolve().relative_to(run_dir.resolve())
        run_text = normalize_rel(run_rel)
        if run_text.startswith("research") and rel.suffix in {".md", ".jsonl", ".txt"}:
            return (project / rel).exists()
    except ValueError:
        pass
    if rel_text.startswith(".actant/external-docs/") and rel.suffix in {".md", ".json", ".jsonl"}:
        return (project / rel).exists()
    return False


def validate_context_manifest(project: Path, run_dir: Path, path: Path, expected_mode: str) -> None:
    if not path.exists():
        return
    with path.open("r", encoding="utf-8") as fh:
        for index, line in enumerate(fh, start=1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ActantError(f"invalid JSONL in {path} line {index}: {exc}") from exc
            if row.get("mode") != expected_mode:
                raise ActantError(f"{path.name} line {index} has wrong mode")
            file_ref = row.get("file")
            if not file_ref or not row.get("reason"):
                raise ActantError(f"{path.name} line {index} requires file and reason")
            if not context_entry_allowed(project, run_dir, str(file_ref)):
                raise ActantError(f"{path.name} line {index} has illegal context file: {file_ref}")


def validate_spec_system(project: Path) -> None:
    root = actant_root(project)
    if not root.exists():
        raise ActantError(f"missing {root}")
    for rel in SPEC_CORE_FILES:
        if not (root / "specs" / rel).exists():
            raise ActantError(f"missing spec file: .actant/specs/{rel}")
    validate_agents_chain(project)
    validate_spec_file_registry(project)
    status_path = root / "status.json"
    if status_path.exists():
        status = read_json(status_path)
        run_id = status.get("active_run_id")
        if run_id:
            run_dir = root / "runs" / run_id
            validate_context_manifest(project, run_dir, run_dir / "codeflow-context.jsonl", "codeflow")
            validate_context_manifest(project, run_dir, run_dir / "check-context.jsonl", "check")
            gate_path = run_dir / "gate.json"
            if gate_path.exists():
                gate = read_json(gate_path)
                validate_gate_shape(gate)
    print("Actant spec validation passed.")


def spec_list(project: Path) -> None:
    root = actant_root(project)
    for path in spec_markdown_files(root):
        print(normalize_rel(path.relative_to(project)))


def spec_init_capability(project: Path, args: argparse.Namespace) -> None:
    root = actant_root(project)
    cap = root / "specs" / "capabilities" / args.slug
    if cap.exists():
        raise ActantError(f"capability already exists: {args.slug}")
    write_text(cap / "index.md", f"# {args.title}\n\nCapability overview.\n")
    write_text(cap / "contract.md", f"# {args.title} Contract\n\nActionable behavior contract.\n")
    write_text(cap / "quality.md", f"# {args.title} Quality\n\nObservable quality expectations.\n")
    (cap / "adr").mkdir(parents=True, exist_ok=True)
    registry_path = root / "specs" / "registry.json"
    registry = read_json(registry_path) if registry_path.exists() else {"schema_version": 1, "entries": []}
    for name, kind in [
        ("index.md", "capability-index"),
        ("contract.md", "capability-contract"),
        ("quality.md", "capability-quality"),
    ]:
        registry.setdefault("entries", []).append(
            {
                "path": f".actant/specs/capabilities/{args.slug}/{name}",
                "kind": kind,
                "trigger_class": args.trigger_class,
                "accepted": True,
            }
        )
    write_json(registry_path, registry)
    print(f"Initialized capability: {args.slug}")


def spec_add_context(project: Path, args: argparse.Namespace) -> None:
    run_dir = resolve_run_dir(project, args.run)
    if not context_entry_allowed(project, run_dir, args.file):
        raise ActantError(f"illegal or missing context file: {args.file}")
    row = {"file": args.file.replace("\\", "/"), "reason": args.reason, "mode": args.mode}
    target = run_dir / f"{args.mode}-context.jsonl"
    append_jsonl(target, row)
    print(f"Added {args.mode} context: {row['file']}")
