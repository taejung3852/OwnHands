from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from .catalog import Catalog
from .context_architecture import (
    ContextArchitectureError,
    build_comparison_plan,
    lint_context,
)
from .dashboard_actions import (
    ValidationRequest,
    run_feature_validation,
    submit_task_decision,
)
from .dashboard_export import export_masked_history
from .dashboard_server import (
    DashboardConfig,
    DashboardServices,
    serve_dashboard,
)
from .dashboard_security import issue_session_token
from .dashboard_sources import resolve_evidence
from .dashboard_view import assemble_task_review
from .evidence import EvidenceStore
from .events import EventLog
from .identity import IdentityRegistry
from .paths import DataPaths
from .projections import ProjectionEngine
from .review import run_m1_demo


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _dashboard_services(data_root: Path) -> tuple[DashboardServices, Catalog]:
    catalog = Catalog.open(DataPaths.resolve(data_root))
    events = EventLog(catalog)
    evidence_store = EvidenceStore(catalog, events)
    identities = IdentityRegistry(catalog)
    projections = ProjectionEngine(catalog, events)

    def load_view(task_id: str):
        task = identities.get_task(task_id)
        projection = projections.project(task_id)
        freshness = projections.freshness(task_id)
        return assemble_task_review(
            task=task,
            events=events,
            projection=projection,
            freshness=freshness,
            evidence_store=evidence_store,
            baseline=None,
            context_status=None,
            execution_contract=None,
            m3_packet=None,
            assurance_packet=None,
            guarantee_report=None,
            assembled_at=_now(),
        )

    def evidence(task_id: str, evidence_id: str, disclose_raw: bool):
        return resolve_evidence(
            evidence_store,
            task_id=task_id,
            evidence_id=evidence_id,
            assurance_packet=None,
            disclose_raw=disclose_raw,
        )

    def validate(task_id: str, subject_ref: str, form: dict[str, str]):
        return run_feature_validation(
            adapter=None,
            request=ValidationRequest(
                task_id=task_id,
                subject_ref=subject_ref,
                expected=form.get("expected", "No expected result supplied"),
                input_summary=form.get("input_summary", "No input supplied"),
            ),
            evidence_store=evidence_store,
            evidence_id=f"evidence:direct:{uuid4()}",
            occurred_at=_now(),
        )

    def decide(view, form: dict[str, str]):
        return submit_task_decision(
            view=view,
            events=events,
            form=form,
            event_id=f"event:decision:{uuid4()}",
            occurred_at=_now(),
        )

    def export_history(view, sections: tuple[str, ...]) -> bytes:
        return export_masked_history(
            view=view,
            sections=sections,
            private_roots=(data_root,),
            exported_at=_now(),
        )

    return (
        DashboardServices(
            load_view=load_view,
            resolve_evidence=evidence,
            validate_feature=validate,
            decide=decide,
            export_history=export_history,
        ),
        catalog,
    )


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
    dashboard = subparsers.add_parser(
        "dashboard", help="serve the local five-route review Dashboard"
    )
    dashboard.add_argument("--data-root", type=Path, required=True)
    dashboard.add_argument("--host", default="127.0.0.1")
    dashboard.add_argument("--port", type=int, default=0)
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
    if arguments.command == "dashboard":
        if arguments.host not in {"127.0.0.1", "::1"}:
            parser.error("Dashboard must bind to loopback")
        if not 0 <= arguments.port <= 65535:
            parser.error("Dashboard port must be between 0 and 65535")
        try:
            services, catalog = _dashboard_services(arguments.data_root)
        except (OSError, ValueError) as error:
            parser.error(str(error))
        try:
            serve_dashboard(
                DashboardConfig(
                    host=arguments.host,
                    port=arguments.port,
                    session_token=issue_session_token(),
                    data_root=arguments.data_root,
                ),
                services,
            )
        finally:
            catalog.close()
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
