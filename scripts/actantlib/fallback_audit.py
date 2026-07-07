"""Run-local fallback audit schema and conservative static scanner."""

from __future__ import annotations

import ast
import re
from pathlib import Path
from typing import Any, Iterable

from .errors import ActantError
from .io import normalize_rel, read_json, write_json


FALLBACK_AUDIT_ARTIFACT = "fallback-audit.json"
FALLBACK_AUDIT_STATUSES = frozenset({"clear", "findings", "not-applicable"})
FALLBACK_LANGUAGE = re.compile(
    r"\b(fallback|best[- ]effort|legacy shim|compatibility shim|ignore error|ignored error)\b",
    re.IGNORECASE,
)


def default_fallback_audit() -> dict[str, Any]:
    return {
        "schema_version": 1,
        "status": "not-applicable",
        "coverage": "not-yet-scanned",
        "findings": [],
        "declared_fallbacks": [],
        "not_applicable_reason": "No codeflow implementation surface has been declared yet.",
    }


def fallback_audit_path(run_dir: Path) -> Path:
    return run_dir / FALLBACK_AUDIT_ARTIFACT


def load_fallback_audit(run_dir: Path) -> dict[str, Any]:
    return read_json(fallback_audit_path(run_dir))


def write_fallback_audit(run_dir: Path, audit: dict[str, Any]) -> None:
    validate_fallback_audit(audit)
    write_json(fallback_audit_path(run_dir), audit)


def validate_fallback_audit(audit: dict[str, Any]) -> None:
    if audit.get("schema_version") != 1:
        raise ActantError("fallback-audit.json schema_version must be 1")
    status = audit.get("status")
    if status not in FALLBACK_AUDIT_STATUSES:
        raise ActantError("fallback-audit.json status must be clear, findings, or not-applicable")
    if not isinstance(audit.get("coverage"), str) or not audit["coverage"].strip():
        raise ActantError("fallback-audit.json coverage must be a non-empty string")
    findings = audit.get("findings")
    declared = audit.get("declared_fallbacks")
    if not isinstance(findings, list):
        raise ActantError("fallback-audit.json findings must be a list")
    if not isinstance(declared, list):
        raise ActantError("fallback-audit.json declared_fallbacks must be a list")
    for index, finding in enumerate(findings, start=1):
        _validate_finding(finding, index)
    for index, fallback in enumerate(declared, start=1):
        _validate_declared_fallback(fallback, index)
    if status == "clear" and findings:
        raise ActantError("fallback-audit.json status clear cannot include findings")
    if status == "findings" and not findings:
        raise ActantError("fallback-audit.json status findings requires at least one finding")
    if status == "not-applicable" and not audit.get("not_applicable_reason"):
        raise ActantError("fallback-audit.json not-applicable requires not_applicable_reason")


def unresolved_fallback_findings(audit: dict[str, Any]) -> list[dict[str, Any]]:
    validate_fallback_audit(audit)
    if audit["status"] != "findings":
        return []
    declared = audit.get("declared_fallbacks", [])
    return [
        finding
        for finding in audit["findings"]
        if not finding.get("resolved") and not _finding_has_declaration(finding, declared)
    ]


def scan_changed_files(project: Path, files: Iterable[str | Path], coverage: str = "changed-files-static") -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    for item in files:
        path = _resolve_scanned_path(project, item)
        rel = normalize_rel(path.relative_to(project.resolve()))
        findings.extend(_scan_text_file(path, rel))
        if path.suffix == ".py":
            findings.extend(_scan_python_ast(path, rel))
    findings.sort(key=lambda row: (row["path"], row["line"], row["kind"]))
    return {
        "schema_version": 1,
        "status": "findings" if findings else "clear",
        "coverage": coverage,
        "findings": findings,
        "declared_fallbacks": [],
    }


def _validate_finding(finding: Any, index: int) -> None:
    if not isinstance(finding, dict):
        raise ActantError(f"fallback-audit.json finding {index} must be an object")
    for field in ("id", "path", "line", "kind", "message"):
        if not finding.get(field):
            raise ActantError(f"fallback-audit.json finding {index} missing {field}")
    if not isinstance(finding["line"], int) or finding["line"] < 1:
        raise ActantError(f"fallback-audit.json finding {index} line must be a positive integer")


def _validate_declared_fallback(fallback: Any, index: int) -> None:
    if not isinstance(fallback, dict):
        raise ActantError(f"fallback-audit.json declared_fallback {index} must be an object")
    for field in ("reason", "scope", "user_visible_behavior"):
        if not isinstance(fallback.get(field), str) or not fallback[field].strip():
            raise ActantError(f"fallback-audit.json declared_fallback {index} missing {field}")
    if not any(fallback.get(field) for field in ("test_ref", "check_ref", "evidence_ref", "not_applicable_reason")):
        raise ActantError(
            f"fallback-audit.json declared_fallback {index} requires test_ref, check_ref, evidence_ref, "
            "or not_applicable_reason"
        )


def _finding_has_declaration(finding: dict[str, Any], declared: list[dict[str, Any]]) -> bool:
    finding_scopes = {
        str(finding.get("id")),
        str(finding.get("path")),
        f"{finding.get('path')}:{finding.get('line')}",
        f"{finding.get('path')}#L{finding.get('line')}",
    }
    return any(str(item.get("scope")) in finding_scopes for item in declared)


def _resolve_scanned_path(project: Path, item: str | Path) -> Path:
    path = Path(item)
    if not path.is_absolute():
        path = project / path
    resolved_project = project.resolve()
    resolved_path = path.resolve()
    try:
        resolved_path.relative_to(resolved_project)
    except ValueError as exc:
        raise ActantError(f"fallback audit file is outside project: {item}") from exc
    if not resolved_path.is_file():
        raise ActantError(f"fallback audit file does not exist: {item}")
    return resolved_path


def _scan_text_file(path: Path, rel: str) -> list[dict[str, Any]]:
    text = _read_scannable_text(path)
    findings: list[dict[str, Any]] = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()
        if re.match(r"except\s*:", stripped):
            findings.append(_finding(rel, line_number, "bare-except", "bare except handler"))
        if re.match(r"except\s+Exception\b", stripped):
            findings.append(_finding(rel, line_number, "broad-except", "broad Exception handler"))
        if FALLBACK_LANGUAGE.search(line):
            findings.append(_finding(rel, line_number, "fallback-language", "explicit fallback or shim language"))
        if re.search(r"\.get\([^,\n]+,\s*[^)\n]+\)", line):
            findings.append(_finding(rel, line_number, "ambiguous-default", "mapping get with default value"))
        if _looks_like_getattr_default(line):
            findings.append(_finding(rel, line_number, "ambiguous-default", "getattr with default value"))
    return findings


def _scan_python_ast(path: Path, rel: str) -> list[dict[str, Any]]:
    try:
        tree = ast.parse(_read_scannable_text(path), filename=str(path))
    except SyntaxError:
        return []
    findings: list[dict[str, Any]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.ExceptHandler):
            continue
        if _handler_contains_pass(node):
            findings.append(_finding(rel, node.lineno, "except-pass", "pass inside exception handler"))
        if _handler_returns_placeholder(node):
            findings.append(_finding(rel, node.lineno, "except-default-return", "exception handler returns a default placeholder"))
        if _handler_warns_without_raise(node):
            findings.append(_finding(rel, node.lineno, "warning-only-continuation", "exception handler warns and continues"))
        if _is_import_compatibility_handler(node):
            findings.append(_finding(rel, node.lineno, "compatibility-import-shim", "import compatibility shim"))
    return findings


def _read_scannable_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text(encoding="utf-8", errors="ignore")


def _finding(path: str, line: int, kind: str, message: str) -> dict[str, Any]:
    return {
        "id": f"{path}:{line}:{kind}",
        "path": path,
        "line": line,
        "kind": kind,
        "message": message,
    }


def _looks_like_getattr_default(line: str) -> bool:
    match = re.search(r"\bgetattr\s*\((.+)\)", line)
    return bool(match and match.group(1).count(",") >= 2)


def _handler_contains_pass(node: ast.ExceptHandler) -> bool:
    return any(isinstance(child, ast.Pass) for child in ast.walk(node))


def _handler_returns_placeholder(node: ast.ExceptHandler) -> bool:
    return any(
        isinstance(child, ast.Return) and _is_placeholder_return(child.value)
        for child in ast.walk(node)
    )


def _handler_warns_without_raise(node: ast.ExceptHandler) -> bool:
    has_warning = any(isinstance(child, ast.Call) and _is_warning_call(child) for child in ast.walk(node))
    has_raise = any(isinstance(child, ast.Raise) for child in ast.walk(node))
    return has_warning and not has_raise


def _is_import_compatibility_handler(node: ast.ExceptHandler) -> bool:
    if not _handler_catches(node, {"ImportError", "ModuleNotFoundError"}):
        return False
    return any(isinstance(child, (ast.Import, ast.ImportFrom)) for child in ast.walk(node))


def _handler_catches(node: ast.ExceptHandler, names: set[str]) -> bool:
    if node.type is None:
        return False
    if isinstance(node.type, ast.Name):
        return node.type.id in names
    if isinstance(node.type, ast.Tuple):
        return any(isinstance(elt, ast.Name) and elt.id in names for elt in node.type.elts)
    return False


def _is_warning_call(node: ast.Call) -> bool:
    func = node.func
    if isinstance(func, ast.Attribute):
        return func.attr in {"warn", "warning", "exception"}
    if isinstance(func, ast.Name):
        return func.id in {"warn", "warning"}
    return False


def _is_placeholder_return(value: ast.AST | None) -> bool:
    if value is None:
        return True
    if isinstance(value, ast.Constant):
        return value.value in {None, "", 0, False}
    if isinstance(value, (ast.List, ast.Dict, ast.Tuple, ast.Set)):
        return len(value.elts if hasattr(value, "elts") else value.keys) == 0
    return False
