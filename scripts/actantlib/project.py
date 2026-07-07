"""Project initialization and managed Actant document helpers."""

from __future__ import annotations

import re
from pathlib import Path

from .contract import MANAGED_END, MANAGED_START, SPEC_CORE_FILES, SPEC_TEMPLATES
from .errors import ActantError
from .io import actant_root, read_text, write_json, write_text


def managed_agents_block() -> str:
    return "\n".join(
        [
            MANAGED_START,
            "Actant loader: read `.actant/agent-profile.md` before Actant-managed work.",
            "The profile points to `.actant/specs/context.md`, `.actant/specs/architecture.md`, and guide files.",
            "Preserve user-authored instructions outside this managed block.",
            MANAGED_END,
            "",
        ]
    )


def update_agents_loader(project: Path) -> None:
    path = project / "AGENTS.md"
    existing = path.read_text(encoding="utf-8") if path.exists() else ""
    pattern = re.compile(
        rf"{re.escape(MANAGED_START)}.*?{re.escape(MANAGED_END)}\s*",
        flags=re.DOTALL,
    )
    without_blocks = pattern.sub("", existing).rstrip()
    block = managed_agents_block().rstrip()
    if without_blocks:
        write_text(path, f"{without_blocks}\n\n{block}\n")
    else:
        write_text(path, f"{block}\n")


def write_spec_skeleton(root: Path, force: bool = False) -> None:
    specs = root / "specs"
    specs.mkdir(parents=True, exist_ok=True)
    for rel, text in SPEC_TEMPLATES.items():
        path = specs / rel
        if force or not path.exists():
            write_text(path, text)
    profile = root / "agent-profile.md"
    if force or not profile.exists():
        write_text(
            profile,
            """# Actant Agent Profile

Read `.actant/specs/context.md` for canonical project language when terminology matters.
Read `.actant/specs/architecture.md` for Actant invariants before changing workflow behavior.
Read `.actant/specs/guides/project-language.md` for codebase-specific answers.
Read `.actant/specs/guides/clear-answer.md` before responding.
Read `.actant/specs/guides/decision-memory.md` before creating ADRs.
""",
        )
    registry = specs / "registry.json"
    if force or not registry.exists():
        entries = [
            {
                "path": f".actant/specs/{rel}",
                "kind": kind,
                "trigger_class": "core-skeleton",
                "accepted": True,
            }
            for rel, kind in sorted(SPEC_CORE_FILES.items())
        ]
        write_json(registry, {"schema_version": 1, "entries": entries})


def init_dirs(project: Path, force: bool = False) -> None:
    root = actant_root(project)
    (root / "runs").mkdir(parents=True, exist_ok=True)
    (root / "memory").mkdir(parents=True, exist_ok=True)
    (root / "specs").mkdir(parents=True, exist_ok=True)
    write_spec_skeleton(root, force=force)
    update_agents_loader(project)
    lineage = root / "memory" / "model-lineage.json"
    if not lineage.exists() or force:
        write_json(lineage, {"schema_version": 2, "entries": []})


def profile_refs(profile_text: str) -> list[str]:
    return re.findall(r"`(\.actant/[^`]+?\.md)`", profile_text)


def validate_agents_chain(project: Path) -> None:
    agents = project / "AGENTS.md"
    text = read_text(agents)
    if text.count(MANAGED_START) != 1 or text.count(MANAGED_END) != 1:
        raise ActantError("AGENTS.md must contain exactly one Actant managed block")
    block_start = text.index(MANAGED_START)
    block_end = text.index(MANAGED_END, block_start)
    block = text[block_start:block_end]
    if ".actant/agent-profile.md" not in block:
        raise ActantError("AGENTS.md managed block must point to .actant/agent-profile.md")
    profile_path = project / ".actant" / "agent-profile.md"
    profile = read_text(profile_path)
    for ref in profile_refs(profile):
        if not (project / ref).exists():
            raise ActantError(f"agent profile references missing file: {ref}")

