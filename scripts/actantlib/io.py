"""Filesystem and serialization helpers for Actant."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .errors import ActantError


def utc_now() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def slugify(text: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", text.strip().lower()).strip("-")
    return slug[:40] or "run"


def read_json(path: Path) -> Any:
    try:
        with path.open("r", encoding="utf-8-sig") as fh:
            return json.load(fh)
    except FileNotFoundError as exc:
        raise ActantError(f"missing file: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ActantError(f"invalid JSON in {path}: {exc}") from exc


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as fh:
        json.dump(data, fh, indent=2, ensure_ascii=True)
        fh.write("\n")


def append_jsonl(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(row, ensure_ascii=True, sort_keys=True))
        fh.write("\n")


def read_jsonl_rows(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.exists():
        return rows
    with path.open("r", encoding="utf-8") as fh:
        for index, line in enumerate(fh, start=1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ActantError(f"invalid JSONL in {path} line {index}: {exc}") from exc
            if not isinstance(row, dict):
                raise ActantError(f"invalid JSONL object in {path} line {index}")
            rows.append(row)
    return rows


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise ActantError(f"missing file: {path}") from exc


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def actant_root(project: Path) -> Path:
    return project / ".actant"


def validate_jsonl(path: Path) -> None:
    read_jsonl_rows(path)


def relative_to_project(project: Path, path_text: str) -> Path:
    path = Path(path_text)
    if path.is_absolute():
        try:
            return path.resolve().relative_to(project.resolve())
        except ValueError as exc:
            raise ActantError(f"path is outside project: {path_text}") from exc
    return path


def normalize_rel(path: Path) -> str:
    return path.as_posix()

