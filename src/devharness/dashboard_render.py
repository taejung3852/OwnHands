from __future__ import annotations

import hashlib
import html
import json
from collections.abc import Iterable, Mapping
from urllib.parse import quote

from .dashboard_assets import dashboard_css, dashboard_script
from .dashboard_sources import EvidenceView
from .dashboard_view import TaskReviewView


_STATUS = {
    "pass": ("✓", "Passed", "pass"),
    "passed": ("✓", "Passed", "pass"),
    "fail": ("✕", "Failed", "danger"),
    "failed": ("✕", "Failed", "danger"),
    "hard_block": ("■", "Hard Block", "danger"),
    "soft_block": ("▲", "Soft Block", "warning"),
    "not_run": ("○", "Not Run", "unknown"),
    "no_adequate_test": ("△", "No Adequate Test", "warning"),
    "inconclusive": ("?", "Inconclusive", "warning"),
    "not_evaluated": ("○", "Not Evaluated", "unknown"),
    "unobserved": ("○", "Unobserved", "unknown"),
    "reference_only": ("◇", "Reference Only", "unknown"),
    "unavailable": ("○", "Unavailable", "unknown"),
    "fresh": ("✓", "Fresh", "pass"),
    "stale": ("▲", "Stale", "warning"),
    "complete": ("✓", "Complete", "pass"),
    "ready": ("✓", "Ready", "pass"),
    "observed": ("●", "Observed", "pass"),
    "inferred": ("◇", "Inferred", "warning"),
    "unknown": ("?", "Unknown", "unknown"),
}
_DECISION_LABELS = {
    "accept": "결과 수용",
    "revise": "수정 요청",
    "reject": "결과 거절",
    "additional_validation": "추가 검증",
    "risk_acceptance": "잔여 위험 수용",
}


def _e(value: object) -> str:
    return html.escape("" if value is None else str(value), quote=True)


def _segment(value: object) -> str:
    return quote(str(value), safe=":._-")


def _task_path(view: TaskReviewView) -> str:
    return f"/tasks/{_segment(view.task['task_id'])}"


def _status(value: object, basis: object | None = None) -> str:
    key = str(value).casefold().replace(" ", "_")
    symbol, label, tone = _STATUS.get(key, ("?", str(value).replace("_", " ").title(), "unknown"))
    basis_html = ""
    if basis is not None:
        basis_key = str(basis).casefold().replace(" ", "_")
        basis_label = _STATUS.get(basis_key, ("", str(basis).replace("_", " ").title(), ""))[1]
        basis_html = f'<span class="status-basis">· {_e(basis_label)}</span>'
    return (
        f'<span class="status status-{tone}">'
        f'<span class="status-symbol" aria-hidden="true">{_e(symbol)}</span>'
        f'<span>{_e(label)}</span>{basis_html}</span>'
    )


def _evidence_link(view: TaskReviewView, evidence_id: object, label: str | None = None) -> str:
    path = f"{_task_path(view)}/evidence/{_segment(evidence_id)}"
    return f'<a href="{_e(path)}">{_e(label or str(evidence_id))}</a>'


def _evidence_links(view: TaskReviewView, refs: Iterable[object]) -> str:
    items = "".join(f"<li>{_evidence_link(view, ref)}</li>" for ref in refs)
    return f'<ul class="evidence-links">{items}</ul>' if items else '<p class="metadata">연결된 Evidence 없음</p>'


def _freshness_banner(view: TaskReviewView) -> str:
    freshness = view.freshness
    completeness = view.completeness
    missing = completeness.get("missing", ())
    missing_html = ""
    if missing:
        missing_html = "<p>수집되지 않은 항목: " + ", ".join(_e(item) for item in missing) + "</p>"
    return (
        '<section class="freshness-banner" aria-labelledby="freshness-heading">'
        '<h2 id="freshness-heading">현재 정보 상태</h2><div class="freshness-grid">'
        f'<div><h3>최신성</h3>{_status(freshness.get("state"))}'
        f'<p>Event { _e(freshness.get("event_head")) } · Projection { _e(freshness.get("projected_sequence")) } · 지연 { _e(freshness.get("lag")) }</p></div>'
        f'<div><h3>수집 완전성</h3>{_status(completeness.get("state"))}{missing_html}</div>'
        '</div></section>'
    )


def _summary_cards(view: TaskReviewView) -> str:
    summary = view.summary
    changed = summary.get("changed_paths", ())
    relations = summary.get("declared_relations", ())
    warnings = summary.get("warnings", ())
    return (
        '<div class="card-grid">'
        f'<article class="card"><h3>요청</h3><p>{_e(summary.get("goal") or "평가할 근거 없음")}</p></article>'
        f'<article class="card"><h3>실제 변화</h3><p>{_e(summary.get("change_statement"))}</p><p class="metadata">변경 경로 {len(changed)}개</p></article>'
        f'<article class="card"><h3>연관 범위</h3><p>근거가 닫힌 관계 {len(relations)}개</p></article>'
        f'<article class="card warning"><h3>현재 행동</h3>{_status(summary.get("gate"))}<p>{_e(" · ".join(str(item) for item in warnings) or "표시된 Evidence를 확인하세요.")}</p></article>'
        '</div>'
    )


def _diagram_refs(diagram: Mapping[str, object]) -> tuple[str, ...]:
    refs = []
    for ref in diagram.get("evidence_refs", ()):
        if isinstance(ref, str) and ref not in refs:
            refs.append(ref)
    for edge in diagram.get("edges", ()):
        if not isinstance(edge, Mapping):
            continue
        for ref in edge.get("evidence_refs", ()):
            if isinstance(ref, str) and ref not in refs:
                refs.append(ref)
    return tuple(refs)


def _bounded_diagram(view: TaskReviewView) -> str:
    diagram = view.diagram
    if diagram.get("state") != "observed" or not diagram.get("nodes"):
        return '<section aria-labelledby="diagram-heading"><h3 id="diagram-heading">변경 관계 Diagram</h3><p>' + _status("unobserved") + '</p><p>source-backed node와 edge가 없어 Diagram을 만들지 않았습니다.</p></section>'
    digest = hashlib.sha256(str(view.task["task_id"]).encode("utf-8")).hexdigest()[:12]
    prefix = f"task-{digest}"
    title_id = f"{prefix}-diagram-title"
    desc_id = f"{prefix}-diagram-desc"
    nodes = tuple(diagram.get("nodes", ()))
    edges = tuple(diagram.get("edges", ()))
    node_positions = {str(node.get("node_id")): (40 + index * 280, 70) for index, node in enumerate(nodes) if isinstance(node, Mapping)}
    svg_edges = []
    for edge in edges:
        if not isinstance(edge, Mapping):
            continue
        start = node_positions.get(str(edge.get("from")), (40, 70))
        end = node_positions.get(str(edge.get("to")), (320, 70))
        svg_edges.append(f'<line class="edge" x1="{start[0] + 180}" y1="{start[1] + 30}" x2="{end[0]}" y2="{end[1] + 30}" />')
    svg_nodes = []
    for index, node in enumerate(nodes):
        if not isinstance(node, Mapping):
            continue
        node_id = str(node.get("node_id"))
        x, y = node_positions[node_id]
        svg_nodes.append(
            f'<g id="{prefix}-node-{index}"><rect class="node" x="{x}" y="{y}" width="180" height="60" rx="8" />'
            f'<text x="{x + 10}" y="{y + 35}">{_e(node_id)}</text></g>'
        )
    refs = _diagram_refs(diagram)
    svg_refs = "".join(
        f'<a href="{_e(_task_path(view) + "/evidence/" + _segment(ref))}"><text x="40" y="{170 + index * 24}">Evidence: {_e(ref)}</text></a>'
        for index, ref in enumerate(refs)
    )
    width = max(680, len(nodes) * 280 + 40)
    height = max(230, 190 + len(refs) * 24)
    fallback_edges = "".join(
        '<li>'
        + _e(f"{edge.get('from')} → {edge.get('to')} ({edge.get('relation_type')})")
        + _evidence_links(view, edge.get("evidence_refs", ()))
        + '</li>'
        for edge in edges
        if isinstance(edge, Mapping)
    )
    return (
        '<section aria-labelledby="diagram-heading"><h3 id="diagram-heading">변경 관계 Diagram</h3>'
        '<div class="diagram-scroll" role="region" aria-label="변경 관계 SVG" tabindex="0">'
        f'<svg role="img" aria-labelledby="{title_id} {desc_id}" viewBox="0 0 {width} {height}">'
        f'<title id="{title_id}">Task 변경과 연관 기능 관계</title>'
        f'<desc id="{desc_id}">source가 제공한 node와 edge만 표시한 dependency impact graph</desc>'
        + "".join(svg_edges)
        + "".join(svg_nodes)
        + svg_refs
        + '</svg></div>'
        '<div class="diagram-fallback" role="region" aria-label="변경 관계 HTML 대체 목록" tabindex="0">'
        f'<p>종류: {_e(diagram.get("kind"))}</p><ul>{fallback_edges}</ul></div></section>'
    )


def _related_checklist(view: TaskReviewView) -> str:
    rows = []
    for relation in view.relations:
        target_ref = relation.get("target_ref")
        next_action = "직접 검증 대상 아님"
        if isinstance(target_ref, str) and (
            target_ref == "subject:hwpx" or target_ref.startswith("subject:hwpx:")
        ):
            validation = f"{_task_path(view)}/validate/{_segment(target_ref)}"
            next_action = f'<a href="{_e(validation)}">검증 보기</a>'
        rows.append(
            '<tr>'
            f'<td>{_e(relation.get("priority"))}</td><td>{_e(target_ref)}</td>'
            f'<td>{_status(relation.get("basis"))}</td><td>{_evidence_links(view, relation.get("evidence_refs", ()))}</td>'
            f'<td>{next_action}</td></tr>'
        )
    body = "".join(rows) or '<tr><td colspan="5">분류할 관계 근거 없음</td></tr>'
    return (
        '<section aria-labelledby="relations-heading"><h3 id="relations-heading">연관 기능 Checklist</h3>'
        '<div class="table-scroll" role="region" aria-label="연관 기능 표" tabindex="0"><table><thead><tr>'
        '<th>우선순위</th><th>대상</th><th>근거</th><th>Evidence</th><th>다음 행동</th>'
        f'</tr></thead><tbody>{body}</tbody></table></div></section>'
    )


def _verification_table(view: TaskReviewView) -> str:
    rows = []
    for row in view.verification:
        identity = row.get("test_id") or row.get("gap_id") or row.get("subject_ref")
        rows.append(
            '<tr>'
            f'<td>{_e(row.get("kind"))}</td><td>{_e(identity)}</td>'
            f'<td>{_status(row.get("result"), row.get("basis"))}</td>'
            f'<td>{_evidence_links(view, row.get("evidence_refs", ()))}</td></tr>'
        )
    return (
        '<section aria-labelledby="verification-heading"><h3 id="verification-heading">검증 상태</h3>'
        '<div class="table-scroll" role="region" aria-label="검증 표" tabindex="0"><table><thead><tr>'
        '<th>종류</th><th>대상</th><th>상태와 근거</th><th>Evidence</th>'
        f'</tr></thead><tbody>{"".join(rows)}</tbody></table></div></section>'
    )


def _guarantee_claims(view: TaskReviewView) -> str:
    items = []
    for claim in view.guarantees:
        risks = claim.get("residual_risks", ())
        items.append(
            '<li class="card">'
            f'<h4>{_e(claim.get("claim_id"))}</h4>{_status(claim.get("status"), claim.get("basis"))}'
            f'<p>{_e(claim.get("permitted_statement") or "확정 문장을 만들 근거 없음")}</p>'
            f'<p class="metadata">잔여 위험: {_e(" · ".join(str(item) for item in risks) or "표시된 위험 없음")}</p>'
            f'{_evidence_links(view, claim.get("evidence_refs", ()))}</li>'
        )
    return '<section aria-labelledby="guarantee-heading"><h3 id="guarantee-heading">Task Guarantee</h3><ul>' + "".join(items) + '</ul></section>'


def _decision_form(view: TaskReviewView, csrf_token: str) -> str:
    decision = view.decision
    gate = decision.get("gate")
    assurance_source = view.assurance.get("source", {})
    assurance_gate = view.assurance.get("gate", {})
    choices = tuple(decision.get("allowed_decisions", ()))
    if gate == "hard_block":
        choices = tuple(item for item in choices if item not in {"accept", "risk_acceptance"})
    if not decision.get("submission_allowed") or not choices:
        return f'<p>{_status(gate)}</p><p>{_e(decision.get("reason") or "현재 상태에서는 판단을 기록할 수 없습니다.")}</p>'
    options = "".join(f'<option value="{_e(choice)}">{_e(_DECISION_LABELS.get(choice, choice))}</option>' for choice in choices)
    hidden = {
        "csrf_token": csrf_token,
        "task_id": view.task.get("task_id"),
        "assurance_packet_fingerprint": assurance_source.get("fingerprint"),
        "gate_fingerprint": assurance_gate.get("fingerprint"),
        "gate_decision": assurance_gate.get("decision"),
        "evidence_refs": "\n".join(str(item) for item in assurance_gate.get("evidence_refs", ())),
    }
    hidden_html = "".join(
        f'<input type="hidden" name="{_e(name)}" value="{_e(value)}">'
        for name, value in hidden.items()
    )
    return (
        f'<p>현재 Gate: {_status(gate)}</p>'
        f'<form method="post" action="{_e(_task_path(view))}" class="form-grid">'
        f'{hidden_html}'
        '<label for="decision-choice">판단</label><select id="decision-choice" name="decision" required>'
        f'{options}</select>'
        '<label for="decision-source">판단 출처</label><select id="decision-source" name="decision_source" required><option value="reviewer">Reviewer</option><option value="product_authority">Product authority</option></select>'
        '<label for="decision-actor">판단자 참조</label><input id="decision-actor" name="actor_ref" required autocomplete="off">'
        '<label for="decision-reason">이유</label><textarea id="decision-reason" name="reason" required></textarea>'
        '<label for="decision-risks">수용한 잔여 위험</label><textarea id="decision-risks" name="residual_risks"></textarea>'
        '<label for="decision-follow-up">후속 조치</label><textarea id="decision-follow-up" name="follow_up" required></textarea>'
        '<button type="submit">판단 기록</button></form>'
    )


def render_task_review(view: TaskReviewView, *, csrf_token: str) -> str:
    return "".join(
        (
            _freshness_banner(view),
            '<section id="summary" class="panel" aria-labelledby="summary-heading"><h2 id="summary-heading">한눈에 보기</h2>' + _summary_cards(view) + '</section>',
            '<details id="trace"><summary>변경과 연관 기능</summary><h2>변경과 연관 기능</h2>' + _bounded_diagram(view) + _related_checklist(view) + '</details>',
            '<details id="evidence"><summary>검증과 근거</summary><h2>검증과 근거</h2>' + _verification_table(view) + _guarantee_claims(view) + '</details>',
            '<section id="decision" class="panel" aria-labelledby="decision-heading"><h2 id="decision-heading">판단</h2>' + _decision_form(view, csrf_token) + '</section>',
        )
    )


def _control_table(view: TaskReviewView, controls: object, label: str) -> str:
    if not isinstance(controls, Mapping):
        return f'<p>{_status("unobserved")}</p><p>{_e(label)} control 자료가 없습니다.</p>'
    rows = []
    for name in ("config", "agents", "rules", "hooks", "sandbox", "approval"):
        control = controls.get(name, {})
        cells = []
        for stage in ("configured", "loaded", "enforced"):
            check = control.get(stage, {}) if isinstance(control, Mapping) else {}
            cells.append(f'<td>{_status(check.get("result", "not_run"), check.get("basis", "unobserved"))}{_evidence_links(view, check.get("evidence_refs", ()))}</td>')
        rows.append(f'<tr><th scope="row">{_e(name)}</th>{"".join(cells)}</tr>')
    return (
        f'<div class="table-scroll" role="region" aria-label="{_e(label)} control 표" tabindex="0"><table>'
        '<thead><tr><th>Control</th><th>Configured</th><th>Loaded</th><th>Enforced</th></tr></thead>'
        f'<tbody>{"".join(rows)}</tbody></table></div>'
    )


def render_harness_status(view: TaskReviewView) -> str:
    source = view.harness.get("source", {})
    return (
        '<section id="harness-page" class="panel" aria-labelledby="harness-heading"><h2 id="harness-heading">Harness 상태</h2>'
        f'<p>Project source: {_status(source.get("status"), source.get("scope"))}</p>'
        f'<p>현재 Task 적용: {_status("observed" if source.get("task_applicable") else "unobserved")}</p>'
        '<h3>Task control</h3>' + _control_table(view, view.harness.get("controls"), "Task")
        + '<h3>Project-level 관찰</h3>' + _control_table(view, view.harness.get("project_controls"), "Project")
        + '<h3>Imported historical limitation</h3>' + _control_table(view, view.harness.get("imported_controls"), "Imported")
        + '</section>'
    )


def render_feature_validation(view: TaskReviewView, *, subject_ref: str, csrf_token: str) -> str:
    action = f"{_task_path(view)}/validate/{_segment(subject_ref)}"
    matching = [row for row in view.verification if row.get("subject_ref") == subject_ref]
    status = matching[-1] if matching else {"result": "unknown", "basis": "unobserved", "evidence_refs": ()}
    return (
        '<section id="validation-page" class="panel" aria-labelledby="validation-heading"><h2 id="validation-heading">기능 직접 검증</h2>'
        f'<p>대상: {_e(subject_ref)}</p><p>{_status(status.get("result"), status.get("basis"))}</p>'
        f'{_evidence_links(view, status.get("evidence_refs", ()))}</section>'
        '<section class="panel" aria-labelledby="validation-request-heading"><h2 id="validation-request-heading">검증 요청</h2>'
        f'<form method="post" action="{_e(action)}" class="form-grid"><input type="hidden" name="csrf_token" value="{_e(csrf_token)}">'
        '<label for="validation-input">입력과 환경 요약</label><textarea id="validation-input" name="input_summary" required></textarea>'
        '<label for="validation-expected">기대 결과</label><textarea id="validation-expected" name="expected" required></textarea>'
        '<button type="submit">등록된 Adapter로 검증</button></form></section>'
    )


def render_history(view: TaskReviewView) -> str:
    rows = []
    for event in view.history:
        references = event.get("references", {})
        refs = references.get("evidence_refs", ()) if isinstance(references, Mapping) else ()
        rows.append(
            '<li class="card">'
            f'<h3>#{_e(event.get("sequence"))} {_e(event.get("event_type"))}</h3>'
            f'<p>{_e(event.get("occurred_at"))} · {_e(event.get("redaction_status"))}</p>'
            f'{_evidence_links(view, refs)}</li>'
        )
    export_url = f"{_task_path(view)}/history?format=json&section=summary&section=history"
    return (
        '<section id="history-page" class="panel" aria-labelledby="history-heading"><h2 id="history-heading">Audit와 History</h2>'
        f'<p><a class="button" href="{_e(export_url)}">가려진 JSON 내보내기</a></p>'
        f'<ol>{"".join(rows)}</ol></section>'
    )


def _metadata_list(value: object) -> str:
    if not isinstance(value, Mapping):
        return '<p>metadata 없음</p>'
    items = []
    for key in sorted(value):
        rendered = json.dumps(value[key], ensure_ascii=False, sort_keys=True)
        items.append(f'<dt>{_e(key)}</dt><dd>{_e(rendered)}</dd>')
    return '<dl class="field-grid">' + "".join(items) + '</dl>'


def render_evidence_detail(
    view: TaskReviewView,
    *,
    evidence: EvidenceView,
    raw: bytes | None,
) -> str:
    raw_html = '<p>Raw Evidence는 명시적으로 열지 않았거나 사용할 수 없습니다.</p>'
    if raw is not None:
        raw_html = (
            '<details><summary>Raw Evidence 열기 — 공유 금지 경계를 확인하세요</summary>'
            f'<pre class="raw-evidence" tabindex="0">{_e(raw.decode("utf-8", errors="replace"))}</pre></details>'
        )
    elif evidence.raw_available:
        path = f"{_task_path(view)}/evidence/{_segment(evidence.evidence_id)}?raw=1"
        raw_html = f'<p><a href="{_e(path)}">Raw Evidence 명시적으로 열기</a></p>'
    return (
        '<section id="evidence-detail" class="panel" aria-labelledby="evidence-detail-heading"><h2 id="evidence-detail-heading">Evidence 상세</h2>'
        f'<p>{_e(evidence.evidence_id)}</p>{_status(evidence.result, evidence.basis)}'
        f'<p>참조 종류: {_e(evidence.reference_kind)} · Redaction: {_e(evidence.redaction_status)}</p>'
        '<h3>허용된 Metadata</h3>' + _metadata_list(evidence.metadata)
        + '<h3>Raw disclosure</h3>' + raw_html + '</section>'
    )


def render_document(
    *,
    title: str,
    task_id: str,
    main: str,
    status: str,
    nonce: str,
) -> bytes:
    task = _segment(task_id)
    safe_nonce = _e(nonce)
    return (
        '<!doctype html><html lang="ko"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        f'<title>{_e(title)} · DevHarness</title><style nonce="{safe_nonce}">{dashboard_css()}</style></head><body>'
        '<a class="skip-link" href="#main-content">본문으로 건너뛰기</a>'
        '<header class="site-header"><div><div class="brand">DevHarness</div><h1>' + _e(title) + '</h1></div>'
        '<button type="button" id="theme-toggle" aria-pressed="false">어두운 테마</button></header>'
        '<nav class="site-header" aria-label="Task 검토"><ul>'
        f'<li><a href="/tasks/{_e(task)}">Task Review</a></li>'
        f'<li><a href="/tasks/{_e(task)}/harness">Harness</a></li>'
        f'<li><a href="/tasks/{_e(task)}/history">History</a></li></ul></nav>'
        f'<div class="status-region" role="status" aria-live="polite" aria-atomic="true">{_e(status)}</div>'
        f'<main id="main-content" tabindex="-1">{main}</main>'
        '<footer><p>Local review interface · Summary → Trace → Evidence → Decision</p></footer>'
        f'<script nonce="{safe_nonce}">{dashboard_script()}</script></body></html>'
    ).encode("utf-8")
