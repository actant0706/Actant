#!/usr/bin/env python3
"""Compatibility wrapper for the Actant CLI implementation."""

from __future__ import annotations

from actantlib.cli import main


if __name__ == "__main__":
    raise SystemExit(main())
