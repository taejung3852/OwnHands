from __future__ import annotations

import argparse
import json
from pathlib import Path



def main() -> int:
    parser = argparse.ArgumentParser(prog="devharness")
    subparsers = parser.add_subparsers(dest="command", required=True)
    demo = subparsers.add_parser("m1-demo", help="historical M1 evidence demo")
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
        "m15-comparison-plan", help="historical M1.5 nine-run plan"
    )
    comparison.add_argument("--package", type=Path, required=True)
    comparison.add_argument("--target-commit", required=True)
    lint = subparsers.add_parser(
        "m15-context-lint", help="historical M1.5 context lint"
    )
    lint.add_argument("--root", type=Path, required=True)
    lint.add_argument("--sources", type=Path, required=True)
    dashboard = subparsers.add_parser("dashboard", help="run the local read-only Dashboard")
    dashboard.add_argument("--data-root", type=Path, help="local data root to read")
    dashboard.add_argument("--project-id", required=True, help="the one project this run serves")
    dashboard.add_argument("--host", default="127.0.0.1", help="loopback host to bind")
    dashboard.add_argument("--port", type=int, default=8765)
    mcp = subparsers.add_parser("mcp-server", help="run stdio MCP server")
    mcp.add_argument("--data-root", type=Path, help="local data root for evidence")
    mcp.add_argument("--legacy-tools", action="store_true", help="enable historical M4.5 tools")
    arguments = parser.parse_args()

    if arguments.command == "dashboard":
        from .dashboard.server import DashboardServer
        from .paths import DataPaths
        try:
            server = DashboardServer(DataPaths.resolve(arguments.data_root), arguments.project_id,
                                     host=arguments.host, port=arguments.port)
        except ValueError as error:
            parser.error(str(error))
        try:
            server.start()
        except OSError as error:
            parser.error(f"cannot bind {arguments.host}:{arguments.port} ({error.strerror}); "
                         "choose a free port with --port")
        # The boot token goes to the local user on stdout only: never a URL, log or response.
        print(f"dashboard=http://{server.authority}/")
        print(f"token={server.token}", flush=True)
        try:
            server._thread.join()
        except KeyboardInterrupt:
            pass
        finally:
            server.stop()
        return 0

    if arguments.command == "mcp-server":
        from .mcp.server import McpServer
        server = McpServer(data_root=arguments.data_root, legacy_tools=arguments.legacy_tools)
        server.run_stdio()
        return 0

    if arguments.command == "m1-demo":
        from .review import run_m1_demo
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
    from .context_architecture import ContextArchitectureError, build_comparison_plan, lint_context

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
