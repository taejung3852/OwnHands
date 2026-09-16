from __future__ import annotations

import argparse
import json
from pathlib import Path

from devharness.m4_review import run_m4_fixture


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate the ownhands M4 synthetic local review")
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--packet", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--observed-at", default="2026-09-06T12:00:00+00:00")
    arguments = parser.parse_args()
    repository = Path.cwd().resolve()
    if arguments.data_root.resolve().is_relative_to(repository):
        parser.error("raw Evidence data-root must be outside the repository")
    result = run_m4_fixture(
        arguments.data_root,
        arguments.packet,
        arguments.output,
        observed_at=arguments.observed_at,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
