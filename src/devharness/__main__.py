from __future__ import annotations

import argparse
import json
from pathlib import Path

from .context_architecture import (
    ContextArchitectureError,
    build_comparison_plan,
    lint_context,
)
from .review import run_m1_demo


def main() -> int:
    parser = argparse.ArgumentParser(prog="devharness")
    subparsers = parser.add_subparsers(dest="command", required=True)
    demo = subparsers.add_parser("m1-demo", help="render the M1 evidence vertical slice")
    demo.add_argument(
        "--data-root",
        type=Path,
        help="local data root (defaults to the operating-system application data path)",
    )
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
    comparison = subparsers.add_parser(
        "m15-comparison-plan", help="render the fixed M1.5 nine-run plan"
    )
    comparison.add_argument("--package", type=Path, required=True)
    comparison.add_argument("--target-commit", required=True)
    lint = subparsers.add_parser(
        "m15-context-lint", help="lint declared context sources without modifying them"
    )
    lint.add_argument("--root", type=Path, required=True)
    lint.add_argument("--sources", type=Path, required=True)
    mcp = subparsers.add_parser("mcp-server", help="run stdio MCP server")
    mcp.add_argument("--data-root", type=Path, help="local data root for evidence")
    arguments = parser.parse_args()

    if arguments.command == "mcp-server":
        from .mcp.server import McpServer
        server = McpServer(data_root=arguments.data_root)
        server.run_stdio()
        return 0

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
    try:
        if arguments.command == "m15-comparison-plan":
            package = json.loads(arguments.package.read_text(encoding="utf-8"))
            plan = build_comparison_plan(package, arguments.target_commit)
            print(json.dumps(plan, ensure_ascii=False, indent=2))
            return 0
        if arguments.command == "m15-context-lint":
            sources = json.loads(arguments.sources.read_text(encoding="utf-8"))
            report = lint_context(arguments.root, sources)
            print(json.dumps(report, ensure_ascii=False, indent=2))
            return 0
    except (ContextArchitectureError, json.JSONDecodeError, OSError) as error:
        parser.error(str(error))
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
