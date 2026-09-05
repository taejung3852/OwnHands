from __future__ import annotations

import argparse
import json
from pathlib import Path

from devharness.m2_review import run_m2_demo


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate the ownhands M2 synthetic local preview")
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--fixture", type=Path, default=Path("tests/fixtures/m2/project"))
    arguments = parser.parse_args()
    repository = Path.cwd().resolve()
    if arguments.data_root.resolve().is_relative_to(repository):
        parser.error("raw Evidence data-root must be outside the repository")
    result = run_m2_demo(
        arguments.data_root,
        arguments.fixture,
        arguments.output,
        observed_at="2026-09-05T12:00:00+00:00",
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
