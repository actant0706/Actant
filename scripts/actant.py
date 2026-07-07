#!/usr/bin/env python3
"""Convenience entrypoint for Actant commands."""

from __future__ import annotations

import sys

from actantlib.cli import main as cli_main

def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args:
        print(
            "usage: actant <init|start-run|advance|validate|finish|spec|task|fallback-audit|install-codex>"
        )
        return 0

    return cli_main(args)


if __name__ == "__main__":
    raise SystemExit(main())
