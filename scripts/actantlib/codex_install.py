"""Install Actant skills into a local Codex home and update config.toml."""

from __future__ import annotations

import os
import re
import shutil
from dataclasses import dataclass
from pathlib import Path

from .errors import ActantError
from .io import utc_now


REPO_ROOT = Path(__file__).resolve().parents[2]
FEATURES_SECTION = "[features]"
REQUEST_USER_INPUT_FLAG = "default_mode_request_user_input"
ROOT_SKILL_DIRS = ("agents", "assets", "references", "scripts")
SUBSKILL_NAMES = (
    "actant-battle",
    "actant-check",
    "actant-codeflow",
    "actant-evolution",
    "actant-planning",
)


@dataclass(frozen=True)
class CodexInstallSummary:
    codex_home: Path
    skills_root: Path
    config_path: Path | None
    backup_path: Path | None
    installed_skill_paths: tuple[Path, ...]
    config_changed: bool


def default_codex_home() -> Path:
    raw = os.environ.get("CODEX_HOME")
    if raw:
        return Path(raw).expanduser()
    return Path.home() / ".codex"


def _detect_newline(text: str) -> str:
    return "\r\n" if "\r\n" in text else "\n"


def _join_lines(lines: list[str], newline: str) -> str:
    if not lines:
        return ""
    return newline.join(lines) + newline


def _is_section_header(line: str) -> bool:
    stripped = line.strip()
    return stripped.startswith("[") and stripped.endswith("]")


def ensure_request_user_input_flag(text: str) -> tuple[str, bool]:
    newline = _detect_newline(text)
    lines = text.splitlines()
    target_line = f"{REQUEST_USER_INPUT_FLAG} = true"

    for index, line in enumerate(lines):
        if line.strip() != FEATURES_SECTION:
            continue
        end = len(lines)
        for probe in range(index + 1, len(lines)):
            if _is_section_header(lines[probe]):
                end = probe
                break
        for probe in range(index + 1, end):
            if re.match(rf"^\s*{re.escape(REQUEST_USER_INPUT_FLAG)}\s*=", lines[probe]):
                if lines[probe] == target_line:
                    return _join_lines(lines, newline), False
                lines[probe] = target_line
                return _join_lines(lines, newline), True
        lines.insert(end, target_line)
        return _join_lines(lines, newline), True

    appended = list(lines)
    if appended and appended[-1].strip():
        appended.append("")
    appended.extend([FEATURES_SECTION, target_line])
    return _join_lines(appended, newline), True


def ensure_skill_registry_entries(text: str, skill_paths: list[Path]) -> tuple[str, bool]:
    newline = _detect_newline(text)
    lines = text.splitlines()
    desired_paths = [str(path) for path in skill_paths]
    remaining = set(desired_paths)
    output: list[str] = []
    changed = False
    index = 0

    while index < len(lines):
        if lines[index].strip() != "[[skills.config]]":
            output.append(lines[index])
            index += 1
            continue

        block_end = index + 1
        while block_end < len(lines) and not _is_section_header(lines[block_end]):
            block_end += 1

        block = list(lines[index:block_end])
        path_value: str | None = None
        path_line_index: int | None = None
        enabled_line_index: int | None = None

        for offset, line in enumerate(block[1:], start=1):
            match = re.match(r"^\s*path\s*=\s*(['\"])(.+)\1\s*$", line)
            if match:
                path_value = match.group(2)
                path_line_index = offset
            if re.match(r"^\s*enabled\s*=", line):
                enabled_line_index = offset

        if path_value in remaining:
            remaining.discard(path_value)
            if enabled_line_index is None:
                insert_at = (path_line_index + 1) if path_line_index is not None else len(block)
                block = block[:insert_at] + ["enabled = true"] + block[insert_at:]
                changed = True
            elif block[enabled_line_index] != "enabled = true":
                block[enabled_line_index] = "enabled = true"
                changed = True

        output.extend(block)
        index = block_end

    if remaining:
        for path_text in desired_paths:
            if path_text not in remaining:
                continue
            if output and output[-1].strip():
                output.append("")
            output.extend(
                [
                    "[[skills.config]]",
                    f"path = '{path_text}'",
                    "enabled = true",
                ]
            )
            changed = True

    return _join_lines(output, newline), changed


def _config_backup_path(config_path: Path) -> Path:
    stamp = utc_now().replace("-", "").replace(":", "")
    return config_path.with_name(f"{config_path.name}.bak-{stamp}-actant-install")


def update_codex_config(config_path: Path, skill_paths: list[Path]) -> tuple[Path | None, bool]:
    config_path = config_path.expanduser().resolve()
    config_path.parent.mkdir(parents=True, exist_ok=True)
    original = config_path.read_text(encoding="utf-8") if config_path.exists() else ""

    updated, feature_changed = ensure_request_user_input_flag(original)
    updated, registry_changed = ensure_skill_registry_entries(updated, skill_paths)
    changed = feature_changed or registry_changed
    if not changed:
        return None, False

    backup_path: Path | None = None
    if config_path.exists():
        backup_path = _config_backup_path(config_path)
        shutil.copy2(config_path, backup_path)
    config_path.write_text(updated, encoding="utf-8", newline="")
    return backup_path, True


def _reset_dir(path: Path, parent_root: Path) -> None:
    resolved = path.resolve()
    root = parent_root.resolve()
    if resolved == root or root not in resolved.parents:
        raise ActantError(f"refusing to replace directory outside skills root: {path}")
    if resolved.exists():
        shutil.rmtree(resolved)


def _copy_dir(src: Path, dst: Path) -> None:
    if not src.exists():
        raise ActantError(f"missing install source: {src}")
    shutil.copytree(src, dst)


def _copy_file(src: Path, dst: Path) -> None:
    if not src.exists():
        raise ActantError(f"missing install source: {src}")
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)


def _subskill_source_dir(source_root: Path, name: str) -> Path:
    repo_style = source_root / "skills" / name
    if (repo_style / "SKILL.md").exists():
        return repo_style
    installed_style = source_root.parent / name
    if (installed_style / "SKILL.md").exists():
        return installed_style
    raise ActantError(f"missing install source: {repo_style}")


def _validate_source_root(source_root: Path) -> None:
    if not (source_root / "SKILL.md").exists():
        raise ActantError(f"missing install source: {source_root / 'SKILL.md'}")
    for name in SUBSKILL_NAMES:
        _subskill_source_dir(source_root, name)


def install_actant_skills(source_root: Path, codex_home: Path) -> tuple[Path, ...]:
    source_root = source_root.expanduser().resolve()
    codex_home = codex_home.expanduser().resolve()
    skills_root = codex_home / "skills"
    skills_root.mkdir(parents=True, exist_ok=True)
    _validate_source_root(source_root)

    root_target = skills_root / "actant"
    _reset_dir(root_target, skills_root)
    root_target.mkdir(parents=True, exist_ok=True)
    _copy_file(source_root / "SKILL.md", root_target / "SKILL.md")
    for name in ROOT_SKILL_DIRS:
        _copy_dir(source_root / name, root_target / name)

    installed = [root_target / "SKILL.md"]
    for name in SUBSKILL_NAMES:
        dst = skills_root / name
        _reset_dir(dst, skills_root)
        _copy_dir(_subskill_source_dir(source_root, name), dst)
        installed.append(dst / "SKILL.md")

    return tuple(installed)


def install_into_codex(
    source_root: Path,
    codex_home: Path | None = None,
    config_path: Path | None = None,
    update_config: bool = True,
) -> CodexInstallSummary:
    resolved_codex_home = (codex_home or default_codex_home()).expanduser().resolve()
    installed_skill_paths = install_actant_skills(source_root, resolved_codex_home)

    resolved_config: Path | None = None
    backup_path: Path | None = None
    config_changed = False
    if update_config:
        resolved_config = (config_path or (resolved_codex_home / "config.toml")).expanduser().resolve()
        backup_path, config_changed = update_codex_config(resolved_config, list(installed_skill_paths))

    return CodexInstallSummary(
        codex_home=resolved_codex_home,
        skills_root=resolved_codex_home / "skills",
        config_path=resolved_config,
        backup_path=backup_path,
        installed_skill_paths=installed_skill_paths,
        config_changed=config_changed,
    )
