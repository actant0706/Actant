"""Actant CLI parser and command dispatcher."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .codex_install import REPO_ROOT, default_codex_home, install_into_codex
from .contract import SCOPES, STAGES
from .errors import ActantError
from .fallback_audit import scan_changed_files, validate_fallback_audit, write_fallback_audit
from .io import read_json
from .project import init_dirs
from .runtime import advance, finish, resolve_run_dir, start_run
from .spec import spec_add_context, spec_init_capability, spec_list, validate_spec_system
from .tasks import task_finish, task_list, task_split, task_start, task_validate
from .validate import validate_run


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Actant persisted run controller")
    parser.add_argument("--project", type=Path, default=Path.cwd(), help="project root containing .actant")
    sub = parser.add_subparsers(dest="command", required=True)

    init = sub.add_parser("init", help="create .actant directories")
    init.add_argument("--force", action="store_true", help="reuse a non-empty .actant directory")

    start = sub.add_parser("start-run", help="start a persisted explicit Actant run")
    start.add_argument("--activation-mode", required=True)
    start.add_argument("--scope", required=True, choices=sorted(SCOPES))
    start.add_argument("--memory-policy", required=True)
    start.add_argument("--objective", default="")
    start.add_argument("--slug")
    start.add_argument("--run-id")
    start.add_argument("--parent-run-id")
    start.add_argument("--model-version-id")
    start.add_argument("--hypothesis-id")
    start.add_argument("--skill", default="actant")
    start.add_argument("--trigger", default="$actant")
    start.add_argument("--reason")

    adv = sub.add_parser("advance", help="advance one gate-approved stage")
    adv.add_argument("--through", choices=STAGES)
    adv.add_argument("--skill", default="actant")
    adv.add_argument("--trigger", default="$actant advance")
    adv.add_argument("--reason")

    sub.add_parser("validate", help="validate .actant structure and active run")

    fin = sub.add_parser("finish", help="mark a run done when evolution gates pass")
    fin.add_argument("--skill", default="actant")
    fin.add_argument("--trigger", default="$actant finish")
    fin.add_argument("--reason")

    spec = sub.add_parser("spec", help="manage Actant specs")
    spec_sub = spec.add_subparsers(dest="spec_command", required=True)
    spec_sub.add_parser("list", help="list spec markdown files")
    spec_sub.add_parser("validate", help="validate spec system")
    init_cap = spec_sub.add_parser("init-capability", help="create a capability spec folder")
    init_cap.add_argument("slug")
    init_cap.add_argument("--title", required=True)
    init_cap.add_argument("--trigger-class", default="new-capability")
    add_ctx = spec_sub.add_parser("add-context", help="append a run-scoped context manifest entry")
    add_ctx.add_argument("run")
    add_ctx.add_argument("mode", choices=["codeflow", "check"])
    add_ctx.add_argument("file")
    add_ctx.add_argument("--reason", required=True)

    task = sub.add_parser("task", help="manage run-local tasks")
    task_sub = task.add_subparsers(dest="task_command", required=True)
    task_list_p = task_sub.add_parser("list", help="list tasks")
    task_list_p.add_argument("run", nargs="?", default="active")
    task_val = task_sub.add_parser("validate", help="validate run-local task plan")
    task_val.add_argument("run", nargs="?", default="active")
    task_split_p = task_sub.add_parser("split", help="create a one-task task plan")
    task_split_p.add_argument("run", nargs="?", default="active")
    task_split_p.add_argument("--title", default="Implement approved Actant slice")
    task_split_p.add_argument("--spec-ref", action="append")
    task_split_p.add_argument("--acceptance", action="append")
    task_split_p.add_argument("--evidence", action="append")
    task_split_p.add_argument("--force", action="store_true")
    task_start_p = task_sub.add_parser("start", help="mark one task active")
    task_start_p.add_argument("task_id")
    task_start_p.add_argument("run", nargs="?", default="active")
    task_finish_p = task_sub.add_parser("finish", help="mark a task done")
    task_finish_p.add_argument("task_id")
    task_finish_p.add_argument("run", nargs="?", default="active")

    audit = sub.add_parser("fallback-audit", help="manage run-local fallback audit")
    audit_sub = audit.add_subparsers(dest="fallback_audit_command", required=True)
    audit_scan = audit_sub.add_parser("scan", help="scan a scoped changed-file surface")
    audit_scan.add_argument("run", nargs="?", default="active")
    audit_scan.add_argument("--file", action="append", required=True)
    audit_scan.add_argument("--coverage", default="changed-files-static")
    audit_validate = audit_sub.add_parser("validate", help="validate fallback-audit.json")
    audit_validate.add_argument("run", nargs="?", default="active")

    install = sub.add_parser(
        "install-codex",
        help="install Actant skills into a local Codex home and update config.toml",
    )
    install.add_argument("--codex-home", type=Path, default=default_codex_home())
    install.add_argument("--source-root", type=Path, default=REPO_ROOT)
    install.add_argument("--config", type=Path)
    install.add_argument("--skip-config", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        project = args.project.resolve()
        if args.command == "init":
            init_dirs(project, force=args.force)
            print(f"Initialized {project / '.actant'}")
        elif args.command == "start-run":
            start_run(args)
        elif args.command == "advance":
            advance(args)
        elif args.command == "validate":
            validate_run(project)
        elif args.command == "finish":
            finish(args)
        elif args.command == "spec":
            if args.spec_command == "list":
                spec_list(project)
            elif args.spec_command == "validate":
                validate_spec_system(project)
            elif args.spec_command == "init-capability":
                spec_init_capability(project, args)
            elif args.spec_command == "add-context":
                spec_add_context(project, args)
            else:
                parser.error("unknown spec command")
        elif args.command == "task":
            run_dir = resolve_run_dir(project, args.run)
            if args.task_command == "list":
                task_list(run_dir)
            elif args.task_command == "validate":
                task_validate(run_dir)
            elif args.task_command == "split":
                task_split(run_dir, args)
            elif args.task_command == "start":
                task_start(run_dir, args.task_id)
            elif args.task_command == "finish":
                task_finish(run_dir, args.task_id)
            else:
                parser.error("unknown task command")
        elif args.command == "fallback-audit":
            run_dir = resolve_run_dir(project, args.run)
            if args.fallback_audit_command == "scan":
                audit = scan_changed_files(project, args.file, coverage=args.coverage)
                write_fallback_audit(run_dir, audit)
                print(f"Fallback audit {audit['status']}; findings: {len(audit['findings'])}")
            elif args.fallback_audit_command == "validate":
                validate_fallback_audit(read_json(run_dir / "fallback-audit.json"))
                print("Actant fallback audit validation passed.")
            else:
                parser.error("unknown fallback-audit command")
        elif args.command == "install-codex":
            summary = install_into_codex(
                source_root=args.source_root,
                codex_home=args.codex_home,
                config_path=args.config,
                update_config=not args.skip_config,
            )
            print(f"Installed Actant skills into {summary.skills_root}")
            print(f"Registered skills: {len(summary.installed_skill_paths)}")
            if summary.config_path is not None:
                if summary.config_changed:
                    print(f"Updated Codex config: {summary.config_path}")
                    if summary.backup_path is not None:
                        print(f"Config backup: {summary.backup_path}")
                else:
                    print(f"Codex config already up to date: {summary.config_path}")
            else:
                print("Skipped Codex config update.")
            print("Note: start a new thread or restart Codex if an existing thread does not refresh skills.")
        else:
            parser.error("unknown command")
    except ActantError as exc:
        print(f"actantctl: error: {exc}", file=sys.stderr)
        return 2
    return 0
