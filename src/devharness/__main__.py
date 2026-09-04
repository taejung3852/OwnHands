from __future__ import annotations

import argparse
from pathlib import Path

from .review import run_m1_demo


def main() -> int:
    parser = argparse.ArgumentParser(prog="devharness")
    subparsers = parser.add_subparsers(dest="command", required=True)
    demo = subparsers.add_parser("m1-demo", help="render the M1 evidence vertical slice")
    demo.add_argument("--data-root", type=Path, required=True)
    demo.add_argument("--output", type=Path, required=True)
    demo.add_argument(
        "--fixture",
        type=Path,
        default=Path("tests/fixtures/hwpx_package_inspection.json"),
    )
    demo.add_argument(
        "--matrix",
        type=Path,
        default=Path("docs/product/guarantee-matrix.v1.json"),
    )
    arguments = parser.parse_args()

    if arguments.command == "m1-demo":
        result = run_m1_demo(
            arguments.data_root,
            arguments.output,
            arguments.fixture,
            arguments.matrix,
        )
        print(f"task_id={result.task_id}")
        print(f"evidence_id={result.evidence_id}")
        print(f"report={result.report_path}")
        print(f"review={result.output_path}")
        print(f"fresh={str(result.freshness.is_fresh).lower()}")
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
