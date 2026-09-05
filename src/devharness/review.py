from __future__ import annotations

import html
import json
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path

from .catalog import Catalog
from .evidence import EvidenceDraft, EvidenceRecord, EvidenceStore
from .events import EventDraft, EventLog
from .guarantees import GuaranteeEvaluator
from .identity import IdentityRegistry
from .paths import DataPaths
from .projections import Freshness, ProjectionEngine


@dataclass(frozen=True)
class DemoResult:
    task_id: str
    evidence_id: str
    report: dict
    report_path: Path
    output_path: Path
    freshness: Freshness


def run_m1_demo(
    data_root: Path | str | None,
    output_path: Path | str,
    fixture_path: Path | str,
    matrix_path: Path | str,
) -> DemoResult:
    output_path = Path(output_path).resolve()
    fixture = json.loads(Path(fixture_path).read_text(encoding="utf-8"))
    _validate_fixture(fixture)

    paths = DataPaths.resolve(data_root)
    with Catalog.open(paths) as catalog:
        registry = IdentityRegistry(catalog)
        project = registry.register_project(fixture["project_locator"])
        worktree = registry.register_worktree(
            project.project_id, fixture["worktree_locator"]
        )
        task_fixture = fixture["task"]
        task = registry.create_task(
            worktree.worktree_id,
            mode=task_fixture["mode"],
            commit=task_fixture["commit"],
            branch=task_fixture["branch"],
            cwd=task_fixture["cwd"],
            environment_ref=task_fixture["environment_ref"],
        )

        events = EventLog(catalog)
        events.append(
            EventDraft(
                event_id=f"task-created:{task.task_id}",
                task_id=task.task_id,
                event_type="task.created",
                event_version=1,
                occurred_at="2026-09-04T12:00:00+00:00",
                payload={"mode": task.mode},
                collection_method="m1-demo",
                redaction_status="not_needed",
            ),
            _identity_dict,
        )

        evidence_fixture = fixture["evidence"]
        evidence_id = f"evidence:{task.task_id}:test-run"
        evidence_store = EvidenceStore(catalog, events)
        evidence = evidence_store.put(
            EvidenceDraft(
                evidence_id=evidence_id,
                task_id=task.task_id,
                requirement_id=evidence_fixture["requirement_id"],
                evidence_type=evidence_fixture["evidence_type"],
                subject_ref=evidence_fixture["subject_ref"],
                exact_scope=evidence_fixture["exact_scope"],
                result=evidence_fixture["result"],
                basis=evidence_fixture["basis"],
                fields=evidence_fixture["fields"],
                content=evidence_fixture["raw_content"].encode("utf-8"),
                collection_method=evidence_fixture["collection_method"],
                redaction_status=evidence_fixture["redaction_status"],
            ),
            _fixture_redactor(evidence_fixture["redact"]),
        )

        evaluator = GuaranteeEvaluator(catalog, evidence_store, matrix_path)
        report = evaluator.evaluate(task.task_id, ["GM-013"])
        evaluator.validate_report(report)
        events.append(
            EventDraft(
                event_id=f"guarantee-evaluated:{report['report_id']}",
                task_id=task.task_id,
                event_type="guarantee.evaluated",
                event_version=1,
                occurred_at=report["generated_at"],
                payload={
                    "report_id": report["report_id"],
                    "claim_ids": [
                        result["claim_id"] for result in report["claim_results"]
                    ],
                },
                collection_method="guarantee-evaluator",
                redaction_status="reference_only",
            ),
            _identity_dict,
        )

        projection = ProjectionEngine(catalog, events)
        projection.project(task.task_id)
        freshness = projection.freshness(task.task_id)
        active_evidence = evidence_store.list_for_task(task.task_id)
        rendered = render_task_review(report, freshness, active_evidence)

    report_path = output_path.with_suffix(".report.json")
    _atomic_write_text(
        report_path,
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
    )
    _atomic_write_text(output_path, rendered)
    return DemoResult(
        task_id=task.task_id,
        evidence_id=evidence.evidence_id,
        report=report,
        report_path=report_path,
        output_path=output_path,
        freshness=freshness,
    )


def render_task_review(
    report: dict,
    freshness: Freshness,
    evidence_records: list[EvidenceRecord],
) -> str:
    claim_rows = "".join(
        "<tr>"
        f"<td>{html.escape(result['claim_id'])}</td>"
        f"<td>{html.escape(result['permitted_statement'] or '판정 가능한 문장 없음')}</td>"
        f"<td>{html.escape(result['verdict'])}</td>"
        f"<td>{html.escape(result['scope'])}</td>"
        "</tr>"
        for result in report["claim_results"]
    )
    evidence_rows = "".join(
        "<tr>"
        f"<td>{html.escape(record.evidence_id)}</td>"
        f"<td>{html.escape(record.evidence_type)}</td>"
        f"<td>{html.escape(record.exact_scope)}</td>"
        f"<td>{html.escape(record.basis)}</td>"
        f"<td><code>{html.escape(record.content_hash)}</code></td>"
        "</tr>"
        for record in evidence_records
    )
    risks = "".join(
        f"<li>{html.escape(risk)}</li>"
        for result in report["claim_results"]
        for risk in result["residual_risks"]
    )
    freshness_label = "Fresh" if freshness.is_fresh else "Stale"
    task_mode = report["task"]["mode"]
    imported_notice = (
        "<p class=\"boundary\"><strong>Imported Task:</strong> "
        "DevHarness 관리 시작 전의 Control 상태와 집행 여부는 Unobserved입니다.</p>"
        if task_mode == "imported"
        else ""
    )
    return f"""<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>DevHarness M1 최소 검토 화면</title>
  <style>
    body {{ max-width: 72rem; margin: 2rem auto; padding: 0 1rem; font: 16px/1.55 system-ui, sans-serif; color: #20242c; background: #faf9f5; }}
    table {{ width: 100%; border-collapse: collapse; margin-block: 1rem 2rem; }}
    th, td {{ border: 1px solid #c8c7c1; padding: .65rem; text-align: left; vertical-align: top; }}
    code {{ overflow-wrap: anywhere; }}
    .boundary {{ border-left: .3rem solid #3f4785; padding: .75rem 1rem; background: #eeedf6; }}
  </style>
</head>
<body>
  <main>
    <h1>DevHarness M1 최소 검토 화면</h1>
    <p class="boundary">이 파일은 M1 데이터 흐름 확인용 산출물이며 M5 Production UI가 아닙니다.</p>
    <p>Task mode: {html.escape(task_mode)}</p>
    {imported_notice}
    <h2>판정 요약</h2>
    <table>
      <thead><tr><th>Claim</th><th>허용 문장</th><th>판정</th><th>범위</th></tr></thead>
      <tbody>{claim_rows}</tbody>
    </table>
    <h2>Evidence 참조</h2>
    <table>
      <thead><tr><th>ID</th><th>Type</th><th>범위</th><th>근거 방식</th><th>SHA-256</th></tr></thead>
      <tbody>{evidence_rows}</tbody>
    </table>
    <h2>Freshness와 한계</h2>
    <p>{freshness_label}: Event head {freshness.event_head} / Projection {freshness.projected_sequence}</p>
    <p>수집 완전성: {freshness.collection_completeness.capitalize()}</p>
    <ul>{risks}</ul>
  </main>
</body>
</html>
"""


def _fixture_redactor(replacements: list[list[str]]):
    normalized = [(source.encode("utf-8"), target.encode("utf-8")) for source, target in replacements]

    def redact(content: bytes) -> bytes:
        for source, target in normalized:
            content = content.replace(source, target)
        return content

    return redact


def _identity_dict(payload: dict) -> dict:
    return payload


def _validate_fixture(fixture: dict) -> None:
    if fixture.get("fixture_version") != "1.0":
        raise ValueError("unsupported fixture version")
    for key in ("project_locator", "worktree_locator", "task", "evidence"):
        if key not in fixture:
            raise ValueError(f"fixture is missing {key}")
    if fixture["task"].get("mode") not in {"managed", "imported"}:
        raise ValueError("fixture task mode is invalid")
    if not fixture["evidence"].get("redact"):
        raise ValueError("fixture must declare explicit redaction replacements")


def _atomic_write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}-", dir=path.parent)
    temporary_path = Path(temporary_name)
    try:
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_path, path)
    finally:
        if temporary_path.exists():
            temporary_path.unlink()
