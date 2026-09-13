"""Snapshot-bound Dashboard view models over the existing read-only stores."""
from __future__ import annotations

import base64
import binascii
import json
import sqlite3
import unicodedata
from collections import Counter
from datetime import datetime, timezone

from ..evidence import EvidenceStore
from ..lifecycle.model import NAMESPACE, canonical_json, fingerprint, reference


_STATES = ("verified", "failed", "inconclusive", "unobserved")
_FILTERS = {"all", "needs-review", "blocked", "stale", "ready"}
_NOT_FOUND = "Dashboard resource was not found"


class ReadModelError(Exception):
    def __init__(self, code: str, message: str, *, retryable: bool = False) -> None:
        super().__init__(message)
        self.code = code
        self.retryable = retryable


class DashboardReadModel:
    def __init__(self, catalog, lifecycle, project_id: str):
        if not catalog.readonly or not lifecycle.readonly or lifecycle.catalog is not catalog:
            raise ValueError("Dashboard requires matching read-only stores")
        if not isinstance(project_id, str) or not project_id.strip():
            raise ValueError("project_id must be a non-empty string")
        self.catalog = catalog
        self.lifecycle = lifecycle
        self.project_id = project_id

    def snapshot_key(self, snapshot_ref: dict) -> str:
        record = self.lifecycle._record(self.lifecycle._row_for_reference(snapshot_ref))
        if record["kind"] != "snapshot" or record["scope"].get("project_id") != self.project_id:
            raise ReadModelError("NOT_FOUND", _NOT_FOUND)
        return fingerprint({
            "namespace": NAMESPACE,
            "scope": record["scope"],
            "snapshot_ref": snapshot_ref,
        })

    def read_detail(self, snapshot_key: str) -> dict:
        return self._consistent(lambda: self._public(self._build_state(snapshot_key)))

    def read_claim(self, snapshot_key: str, claim_id: str) -> dict:
        def build():
            state = self._build_state(snapshot_key)
            for claim in state["claims"]:
                if claim["id"] == claim_id:
                    return claim
            raise ReadModelError("NOT_FOUND", _NOT_FOUND)
        return self._consistent(build)

    def read_evidence(self, snapshot_key: str, evidence_key: str) -> dict:
        def build():
            state = self._build_state(snapshot_key)
            entry = state["_evidence"].get(evidence_key)
            if entry is None:
                raise ReadModelError("NOT_FOUND", _NOT_FOUND)
            return self._evidence_vm(snapshot_key, evidence_key, entry)
        return self._consistent(build)

    def read_context(self, snapshot_key: str) -> dict:
        return self._consistent(lambda: self._build_state(snapshot_key)["context"])

    def read_list(self, *, filter: str = "all", q: str = "",
                  cursor: str | None = None, limit: int = 20,
                  presentations: tuple[dict, ...] = (),
                  ready_sequence: int = 0) -> dict:
        if filter not in _FILTERS:
            raise ReadModelError("INVALID_QUERY", "Unsupported Dashboard filter")
        if not isinstance(q, str) or len(q) > 200:
            raise ReadModelError("INVALID_QUERY", "Search query must be at most 200 characters")
        if type(limit) is not int or not 1 <= limit <= 50:
            raise ReadModelError("INVALID_QUERY", "Limit must be between 1 and 50")
        if type(ready_sequence) is not int or ready_sequence < 0:
            raise ReadModelError("INVALID_QUERY", "ready_sequence must be a non-negative integer")
        cursor_data = self._decode_cursor(cursor) if cursor is not None else None
        return self._consistent(lambda: self._build_list(
            filter, q, cursor_data, limit, presentations, ready_sequence
        ))

    def _consistent(self, build):
        try:
            for _ in range(2):
                start = self._source_head()
                result = build()
                end = self._source_head()
                if start == end:
                    if isinstance(result, dict):
                        result = dict(result)
                        result["read_token"] = fingerprint({"source": start, "result": result})
                    return result
            raise ReadModelError("SOURCE_CHANGED", "Dashboard sources changed while reading", retryable=True)
        except ReadModelError:
            raise
        except sqlite3.Error as error:
            raise ReadModelError("SOURCE_UNAVAILABLE", "Dashboard source is unavailable", retryable=True) from error
        except RuntimeError as error:
            code = "UNSUPPORTED_SCHEMA" if "schema" in str(error).lower() else "SOURCE_INTEGRITY_ERROR"
            raise ReadModelError(code, "Dashboard source cannot be verified") from error
        except (OSError, ValueError) as error:
            raise ReadModelError("SOURCE_INTEGRITY_ERROR", "Dashboard source cannot be verified") from error

    def _source_head(self) -> str:
        lifecycle = self.lifecycle.projection()
        tasks = self.catalog.connection.execute(
            "SELECT task_id, created_at FROM tasks WHERE project_id=? ORDER BY task_id",
            (self.project_id,),
        ).fetchall()
        task_ids = [row["task_id"] for row in tasks]
        if not task_ids:
            catalog = []
        else:
            placeholders = ",".join("?" for _ in task_ids)
            events = self.catalog.connection.execute(
                f"SELECT task_id, sequence, fingerprint FROM events WHERE task_id IN ({placeholders}) "
                "ORDER BY task_id, sequence", task_ids,
            ).fetchall()
            evidence = self.catalog.connection.execute(
                f"SELECT evidence_id, fingerprint, purged_at, purge_reason FROM evidence "
                f"WHERE task_id IN ({placeholders}) ORDER BY evidence_id", task_ids,
            ).fetchall()
            catalog = [list(row) for row in tasks] + [list(row) for row in events] + [list(row) for row in evidence]
        return fingerprint({"lifecycle": lifecycle, "catalog": catalog})

    def _records(self, kind: str | None = None) -> list[dict]:
        self.lifecycle._verify_journal()
        sql = "SELECT * FROM lifecycle_records"
        parameters = ()
        if kind is not None:
            sql += " WHERE kind=?"
            parameters = (kind,)
        sql += " ORDER BY sequence"
        return [self.lifecycle._record(row) for row in self.lifecycle.connection.execute(sql, parameters)
                if json.loads(row["scope_json"]).get("project_id") == self.project_id]

    @staticmethod
    def _ref(record: dict) -> dict:
        return reference(record["kind"], record["id"], record["revision"], record["hash"])

    @staticmethod
    def _ref_id(artifact_ref: dict) -> tuple:
        return tuple(artifact_ref[name] for name in ("kind", "id", "revision", "hash"))

    def _resolve_snapshot(self, snapshot_key: str) -> tuple[dict, dict]:
        if not isinstance(snapshot_key, str):
            raise ReadModelError("NOT_FOUND", _NOT_FOUND)
        for record in self._records("snapshot"):
            snapshot_ref = self._ref(record)
            if self.snapshot_key(snapshot_ref) == snapshot_key:
                return snapshot_ref, record
        raise ReadModelError("NOT_FOUND", _NOT_FOUND)

    def _build_state(self, snapshot_key: str, presentations=(), ready_sequence: int = 0) -> dict:
        snapshot_ref, _ = self._resolve_snapshot(snapshot_key)
        closure = self.lifecycle.inspect_closure(snapshot_ref)
        index = {self._ref_id(self._ref(record)): record for record in closure.records}
        snapshot = index[self._ref_id(snapshot_ref)]
        review_ref = snapshot["data"]["review"]
        review = index[self._ref_id(review_ref)]
        if review["kind"] != "review":
            raise ValueError("snapshot does not reference a review")
        spec_ref = review["data"]["spec"]
        spec = index[self._ref_id(spec_ref)]
        issue_ref = spec["data"]["issue"]
        issue = index[self._ref_id(issue_ref)]
        if issue["kind"] != "work_issue":
            raise ValueError("spec does not reference a work issue")
        diagnostics = {item.evidence_id: item for item in closure.diagnostics}
        evidence_entries = {}
        claims = self._claims(review, review_ref, spec, index, diagnostics,
                              snapshot_ref, evidence_entries)
        counts = self._counts(claims, review["data"].get("exclusions", []))
        context = self._context(snapshot, snapshot_ref, review, review_ref, closure.read_health)
        presentation = self._presentation(snapshot_key, snapshot_ref, issue, issue_ref, counts,
                                          context, presentations, ready_sequence)
        problems = self._problems(review, review_ref, claims, closure.diagnostics, evidence_entries)
        state = review["data"].get("review_state")
        labels = {"ready": "판단 가능", "needs-review": "확인 필요", "blocked": "검증 차단"}
        label = "자료 확인 필요" if closure.read_health != "complete" else labels.get(state, "자료 확인 필요")
        reason = ("일부 근거를 읽을 수 없습니다" if closure.read_health != "complete"
                  else "저장된 Review 판정을 표시합니다")
        return {
            "snapshot_key": snapshot_key,
            "snapshot_ref": snapshot_ref,
            "review_ref": review_ref,
            "scope": snapshot["scope"],
            "issue": {"ref": issue_ref, "title": issue["data"]["title"]},
            "snapshot_created_at": snapshot["created_at"],
            "review_state": state,
            "state_label": label,
            "state_reason": reason,
            "counts": counts,
            "required_complete": review["data"].get("required_complete"),
            "context": context,
            "presentation": presentation,
            "claims": claims,
            "problems": problems,
            "context_notices": self._context_notices(context),
            "remaining_problem_count": max(0, len(problems) - 3),
            "source_contract_version": review["data"].get("contract_version", 1),
            "rules_version": review["data"].get("rules_version"),
            "_sequence": snapshot["sequence"],
            "_evidence": evidence_entries,
        }

    @staticmethod
    def _public(state: dict) -> dict:
        return {key: value for key, value in state.items() if not key.startswith("_")}

    @staticmethod
    def _pointer(record_ref: dict, pointer: str) -> dict:
        return {"record_ref": record_ref, "pointer": pointer}

    def _claims(self, review, review_ref, spec, index, diagnostics, snapshot_ref, evidence_entries):
        criteria = {criterion["id"]: criterion for criterion in spec["data"]["criteria"]}
        result = []
        for claim_index, stored in enumerate(review["data"].get("claims", [])):
            claim_id = stored["criterion_id"]
            criterion = criteria[claim_id]
            checks = []
            for check_index, check in enumerate(stored.get("checks", [])):
                checks.append(self._check_vm(
                    check, claim_id, claim_index, check_index, review_ref, index,
                    diagnostics, snapshot_ref, evidence_entries,
                ))
            result.append({
                "id": claim_id,
                "text": criterion["text"],
                "required": criterion["required"],
                "comparison": criterion["comparison"],
                "status": stored["status"],
                "checks": checks,
                "source": self._pointer(review_ref, f"/claims/{claim_index}"),
            })
        return result

    def _check_vm(self, check, claim_id, claim_index, check_index, review_ref,
                  index, diagnostics, snapshot_ref, evidence_entries):
        observations = []
        for observation_ref in check.get("observations", []):
            record = index.get(self._ref_id(observation_ref))
            if record is None:
                raise ValueError("review observation is outside snapshot closure")
            observations.append(self._observation_vm(
                record, observation_ref, claim_id, check["check_id"], index,
                diagnostics, snapshot_ref, evidence_entries,
            ))
        comparison_vms = []
        for comparison in check.get("comparability", []):
            before = [index[self._ref_id(item)] for item in comparison.get("before", [])]
            after = [index[self._ref_id(item)] for item in comparison.get("after", [])]
            comparison_vms.append({
                "test_id": comparison["test_id"],
                "comparable": comparison.get("comparable"),
                "environment": self._same_fingerprint(before, after, "environment", index),
                "test_meaning": self._same_value(before, after, "test_meaning"),
                "expected_before": comparison.get("expected_before"),
                "before_refs": comparison.get("before", []),
                "after_refs": comparison.get("after", []),
            })
        evidence_ids = {entry["evidence_key"] for vm in observations for entry in vm["evidence_links"]}
        unavailable = {entry["evidence_key"] for vm in observations for entry in vm["evidence_links"]
                       if entry["availability"] != "available"}
        base_pointer = f"/claims/{claim_index}/checks/{check_index}"
        return {
            "id": check["check_id"],
            "statement": check["statement"],
            "role": check["role"],
            "status": check["status"],
            "reason_codes": list(check.get("reason_codes", [])),
            "before": [item for item in observations if item["phase"] == "before"],
            "after": [item for item in observations if item["phase"] == "after"],
            "comparisons": comparison_vms,
            "conflicts": [self._pointer(review_ref, f"{base_pointer}/conflicts/{i}")
                          for i, _ in enumerate(check.get("conflicts", []))],
            "evidence_count": len(evidence_ids),
            "unavailable_evidence_count": len(unavailable),
        }

    def _observation_vm(self, record, observation_ref, claim_id, check_id, index,
                        diagnostics, snapshot_ref, evidence_entries):
        data = record["data"]
        links = []
        for binding_ref in data.get("evidence", []):
            binding = index.get(self._ref_id(binding_ref))
            if binding is None or binding["kind"] != "evidence_binding":
                raise ValueError("observation evidence is outside snapshot closure")
            evidence_id = binding["data"]["evidence_id"]
            diagnostic = diagnostics.get(evidence_id)
            availability = "available" if diagnostic is None else diagnostic.availability
            key = self._evidence_key(snapshot_ref, binding_ref, evidence_id)
            source = self._pointer(binding_ref, "/evidence_id")
            link = {"evidence_key": key, "source": source, "availability": availability}
            links.append(link)
            evidence_entries[key] = {
                "binding_ref": binding_ref,
                "evidence_id": evidence_id,
                "claim_id": claim_id,
                "check_id": check_id,
                "availability": availability,
                "source": source,
            }
        return {
            "ref": observation_ref,
            "phase": data["phase"],
            "result": data["result"],
            "basis": data["basis"],
            "test_id": data["test_id"],
            "test_meaning": data["test_meaning"],
            "code_ref": data["code_state"],
            "environment_ref": data["environment"],
            "execution": data.get("execution"),
            "evidence_links": links,
        }

    def _evidence_key(self, snapshot_ref, binding_ref, evidence_id):
        return fingerprint({
            "namespace": NAMESPACE,
            "project_id": self.project_id,
            "snapshot_ref": snapshot_ref,
            "binding_ref": binding_ref,
            "evidence_id": evidence_id,
        })

    @staticmethod
    def _same_value(before, after, name):
        if not before or not after:
            return "unknown"
        values = {item["data"].get(name) for item in before + after}
        return "same" if len(values) == 1 else "different"

    @staticmethod
    def _same_fingerprint(before, after, name, index):
        if not before or not after:
            return "unknown"
        values = set()
        for observation in before + after:
            target = index.get(DashboardReadModel._ref_id(observation["data"][name]))
            if target is None:
                return "unknown"
            values.add(target["data"].get("fingerprint"))
        return "same" if len(values) == 1 else "different"

    @staticmethod
    def _summary(states):
        counts = Counter(states)
        return {"total": sum(counts.values()), **{state: counts[state] for state in _STATES}}

    def _counts(self, claims, exclusions):
        required = [claim for claim in claims if claim["required"]]
        optional = [claim for claim in claims if not claim["required"]]
        excluded = {item.get("criterion_id") for item in exclusions}
        return {
            "all": self._summary([claim["status"] for claim in claims]),
            "required": self._summary([claim["status"] for claim in required]),
            "optional": self._summary([claim["status"] for claim in optional]),
            "excluded_optional_count": len(excluded & {claim["id"] for claim in optional}),
        }

    def _problems(self, review, review_ref, claims, read_diagnostics, evidence_entries):
        data = review["data"]
        required = {claim["id"]: claim["required"] for claim in claims}
        problems = []

        def add(kind, pointer, *, claim_id=None, check_id=None, reason="", description=""):
            source = self._pointer(review_ref, pointer)
            item = {
                "id": fingerprint({"kind": kind, "source": source}),
                "kind": kind,
                "required": required.get(claim_id),
                "claim_id": claim_id,
                "check_id": check_id,
                "reason_code": reason or kind,
                "description": description or reason or kind,
                "sources": [source],
            }
            problems.append(item)

        for i, blocker in enumerate(data.get("blockers", [])):
            add("blocker", f"/blockers/{i}", claim_id=blocker.get("criterion_id"),
                check_id=blocker.get("check_id"), reason=blocker.get("reason", "blocker"),
                description=blocker.get("source", blocker.get("reason", "blocker")))
        for i, claim in enumerate(data.get("claims", [])):
            checks = claim.get("checks", [])
            if checks:
                for j, check in enumerate(checks):
                    if check["status"] != "verified":
                        kind = "failure" if check["status"] == "failed" else check["status"]
                        add(kind, f"/claims/{i}/checks/{j}", claim_id=claim["criterion_id"],
                            check_id=check["check_id"], reason=(check.get("reason_codes") or [kind])[0])
                    for k, conflict in enumerate(check.get("conflicts", [])):
                        add("conflict", f"/claims/{i}/checks/{j}/conflicts/{k}",
                            claim_id=claim["criterion_id"], check_id=check["check_id"],
                            reason=conflict.get("reason_code", "conflict"))
            elif claim["status"] != "verified":
                kind = "failure" if claim["status"] == "failed" else claim["status"]
                add(kind, f"/claims/{i}", claim_id=claim["criterion_id"], reason=kind,
                    description=claim.get("reason", kind))
        diagnostic_field = "diagnostics" if "diagnostics" in data else "uncertainties"
        for field, kind in (("findings", "finding"), (diagnostic_field, "diagnostic")):
            for i, item in enumerate(data.get(field, [])):
                add(kind, f"/{field}/{i}", claim_id=item.get("criterion_id"),
                    check_id=item.get("check_id"),
                    reason=item.get("reason_code", item.get("reason", kind)),
                    description=item.get("detail", item.get("reason", kind)))
        for i, item in enumerate(data.get("exclusions", [])):
            add("excluded", f"/exclusions/{i}", claim_id=item.get("criterion_id"),
                reason="optional_excluded", description=item.get("reason", "Optional claim excluded"))
        entries_by_id = {item["evidence_id"]: item for item in evidence_entries.values()}
        for diagnostic in read_diagnostics:
            entry = entries_by_id.get(diagnostic.evidence_id, {})
            source = self._pointer(diagnostic.reference, "/evidence_id")
            problems.append({
                "id": fingerprint({"kind": "diagnostic", "source": source}),
                "kind": "diagnostic",
                "required": required.get(entry.get("claim_id")),
                "claim_id": entry.get("claim_id"),
                "check_id": entry.get("check_id"),
                "reason_code": "evidence_" + diagnostic.availability,
                "description": diagnostic.reason,
                "sources": [source],
            })
        unique = {(item["kind"], canonical_json(item["sources"][0])): item for item in problems}
        priority = {"blocker": 0, "failure": 1, "diagnostic": 2, "conflict": 2,
                    "finding": 2, "inconclusive": 3, "unobserved": 3, "excluded": 4}
        return sorted(unique.values(), key=lambda item: (
            0 if item["kind"] == "blocker" and item["required"] else priority[item["kind"]],
            item["id"],
        ))

    def _context(self, snapshot, snapshot_ref, review, review_ref, read_health):
        scope = snapshot["scope"]
        issue_scope = {key: scope[key] for key in ("project_id", "issue_id")}
        input_refs = []
        reasons = []
        superseded = False
        freshness = "unknown"
        active_attempt = self.lifecycle.current_activation("attempt", issue_scope)
        if active_attempt is None:
            reasons.append("attempt_missing")
        elif active_attempt["reference"]["id"] != scope["attempt_id"]:
            reasons.append("attempt_changed")
            superseded = True
            input_refs.append(active_attempt["reference"])
        else:
            input_refs.append(active_attempt["reference"])
            spec_activation = self.lifecycle.current_activation("spec", issue_scope)
            current_spec = None if spec_activation is None else spec_activation["reference"]
            current_approval = None if spec_activation is None else spec_activation["approval"]
            current_code = self.lifecycle.current("code_state", scope)
            current_environment = self.lifecycle.current("environment", scope)
            for name, value in (("spec", current_spec), ("code_state", current_code),
                                ("environment", current_environment)):
                if value is None:
                    reasons.append(name + "_missing")
                else:
                    input_refs.append(value)
            if read_health != "complete":
                reasons.append("evidence_unavailable")
            elif current_spec and current_code and current_environment:
                meanings, conflicts = self._current_test_meanings(
                    scope, current_spec, current_approval, current_code, current_environment
                )
                compared = self.lifecycle.freshness(
                    review_ref, current_spec, current_code, current_environment, meanings
                )
                freshness = compared["state"]
                reasons.extend(name + "_changed" if name in {"spec", "code_state", "environment"}
                               else name for name in compared["changed"])
                unknown = set(compared["unknown"]) | conflicts
                reasons.extend("test_meaning_unknown:" + name for name in sorted(unknown))
        if read_health != "complete":
            new_evidence = None
        else:
            status = self.lifecycle.review_status(review_ref)
            new_evidence = status.get("new_evidence_available") if status.get("readable") else None
        newer = None
        candidates = [record for record in self._records("snapshot")
                      if record["scope"].get("issue_id") == scope["issue_id"]
                      and record["sequence"] > snapshot["sequence"]]
        if candidates:
            newer = self.snapshot_key(self._ref(candidates[-1]))
        return {
            "freshness": freshness,
            "reasons": sorted(set(reasons)),
            "basis": "registered_inputs",
            "checked_at": datetime.now(timezone.utc).isoformat(),
            "input_refs": input_refs,
            "new_evidence_available": new_evidence,
            "superseded_attempt": superseded,
            "newer_snapshot_key": newer,
            "read_health": read_health,
        }

    def _current_test_meanings(self, scope, spec_ref, approval_ref, code_ref, environment_ref):
        code = self.lifecycle.get(code_ref)["data"]["fingerprint"]
        environment = self.lifecycle.get(environment_ref)["data"]["fingerprint"]
        values = {}
        for record in self._records("observation"):
            data = record["data"]
            if (record["scope"] != scope or data.get("phase") != "after"
                    or data.get("spec") != spec_ref or data.get("spec_approval") != approval_ref):
                continue
            if (self.lifecycle.get(data["code_state"])["data"]["fingerprint"] != code
                    or self.lifecycle.get(data["environment"])["data"]["fingerprint"] != environment):
                continue
            values.setdefault(data["test_id"], set()).add(data["test_meaning"])
        conflicts = {test_id for test_id, meanings in values.items() if len(meanings) != 1}
        return ({test_id: next(iter(meanings)) for test_id, meanings in values.items()
                 if test_id not in conflicts}, conflicts)

    def _presentation(self, snapshot_key, snapshot_ref, issue, issue_ref, counts,
                      context, presentations, ready_sequence):
        fallback = {
            "status": "unavailable" if context["read_health"] != "complete" else "absent",
            "presentation_id": None,
            "recipe_hash": "",
            "icon": "📋",
            "headline": {"text": issue["data"]["title"], "kind": "intent",
                         "sources": [self._pointer(issue_ref, "/title")]},
            "summary": [{"text": f"{counts['all']['total']}개 조건 중 {counts['all']['verified']}개가 확인됐습니다.",
                         "kind": "observed", "sources": [self._pointer(snapshot_ref, "/review")]}],
            "key_changes": [],
            "attention_items": [],
            "next_checks": [],
            "generated_at": None,
            "generator_model": None,
            "fallback": True,
            "reason_code": "source_partial" if context["read_health"] != "complete" else "presentation_absent",
            "retry_after": None,
        }
        if context["read_health"] != "complete":
            return fallback
        ready = [item for item in presentations if item.get("snapshot_key") == snapshot_key
                 and item.get("status") == "ready" and type(item.get("ready_sequence")) is int
                 and item["ready_sequence"] <= ready_sequence]
        if not ready:
            return fallback
        item = max(ready, key=lambda value: value["ready_sequence"])
        result = dict(fallback)
        for name in result:
            if name in item:
                result[name] = item[name]
        result.update(status="ready", fallback=False, reason_code=None)
        return result

    @staticmethod
    def _context_notices(context):
        notices = []
        if context["freshness"] == "stale":
            notices.append("새 변경사항이 있습니다. 현재 검증은 이전 입력 기준입니다.")
        elif context["freshness"] == "unknown":
            notices.append("현재 입력에 적용되는지 확인할 수 없습니다.")
        if context["new_evidence_available"]:
            notices.append("이 보고서 이후 새 근거가 등록됐습니다. 결과에는 반영되지 않았습니다.")
        if context["newer_snapshot_key"]:
            notices.append("더 최근 보고서가 있습니다.")
        return notices

    def _evidence_vm(self, snapshot_key, evidence_key, entry):
        row = self.catalog.connection.execute(
            "SELECT * FROM evidence WHERE evidence_id=?", (entry["evidence_id"],)
        ).fetchone()
        try:
            record = None if row is None else EvidenceStore.open_readonly(self.catalog)._from_row(row)
        except ValueError:
            if entry["availability"] != "corrupt":
                raise
            record = None
        availability = entry["availability"]
        fields = {} if record is None else record.fields

        def field(name):
            value = fields.get(name)
            if value is None:
                return {"availability": "not_collected", "text": None,
                        "reason_code": "field_not_collected", "source": None,
                        "next_cursor": None, "truncated": False}
            text = value if isinstance(value, str) else canonical_json(value)
            return {"availability": "available", "text": text, "reason_code": None,
                    "source": entry["source"], "next_cursor": None, "truncated": False}

        if availability != "available":
            raw_availability, raw_reason = availability, "evidence_" + availability
        elif record.redaction_status == "reference_only":
            raw_availability, raw_reason = "unsupported", "reference_only"
        else:
            raw_availability, raw_reason = "available", "content_not_loaded"
        raw = {"availability": raw_availability, "text": None, "reason_code": raw_reason,
               "source": entry["source"], "next_cursor": None, "truncated": False}
        metadata = {} if record is None else {
            "evidence_id": record.evidence_id,
            "requirement_id": record.requirement_id,
            "evidence_type": record.evidence_type,
            "subject_ref": record.subject_ref,
            "exact_scope": record.exact_scope,
            "result": record.result,
            "basis": record.basis,
            "content_size": record.content_size,
            "collection_method": record.collection_method,
            "redaction_status": record.redaction_status,
            "created_at": record.created_at,
            "purged_at": record.purged_at,
            "purge_reason": record.purge_reason,
        }
        return {
            "snapshot_key": snapshot_key,
            "claim_id": entry["claim_id"],
            "check_id": entry["check_id"],
            "evidence_key": evidence_key,
            "metadata": metadata,
            "availability": availability,
            "command": field("command"),
            "stdout": field("stdout"),
            "stderr": field("stderr"),
            "diff": field("diff"),
            "raw": raw,
            "cas_hash": None if record is None else record.content_hash,
        }

    def _build_list(self, filter_name, query, cursor, limit, presentations, ready_sequence):
        normalized = unicodedata.normalize("NFKC", query).casefold()
        query_hash = fingerprint({"filter": filter_name, "q": normalized, "limit": limit})
        head = self._source_head()
        if cursor is not None:
            if cursor.get("version") != 1 or cursor.get("query") != query_hash:
                raise ReadModelError("INVALID_QUERY", "Cursor does not match this query")
            if cursor.get("head") != head:
                raise ReadModelError("LIST_CHANGED", "Dashboard list changed", retryable=True)
            cap = cursor.get("ready_sequence")
            if type(cap) is not int or cap < 0 or not isinstance(cursor.get("last"), list):
                raise ReadModelError("INVALID_QUERY", "Cursor is invalid")
        else:
            cap = ready_sequence
        latest = {}
        for snapshot in self._records("snapshot"):
            group = (snapshot["scope"].get("issue_id"), snapshot["scope"].get("attempt_id"))
            if group not in latest or snapshot["sequence"] > latest[group]["sequence"]:
                latest[group] = snapshot
        states = [self._build_state(self.snapshot_key(self._ref(snapshot)), presentations, cap)
                  for snapshot in latest.values()]
        if filter_name != "all":
            states = [state for state in states if self._matches_filter(state, filter_name)]
        if normalized:
            states = [state for state in states if normalized in self._search_text(state)]
        states.sort(key=self._sort_key)
        if cursor is not None:
            last = tuple(cursor["last"])
            states = [state for state in states if self._sort_key(state) > last]
        page, remaining = states[:limit], states[limit:]
        for state in page:
            state["read_token"] = fingerprint({"head": head, "snapshot": state["snapshot_ref"]})
        next_cursor = None
        if remaining:
            next_cursor = self._encode_cursor({"version": 1, "head": head, "query": query_hash,
                                               "last": list(self._sort_key(page[-1])),
                                               "ready_sequence": cap})
        return {
            "items": [self._card(state) for state in page],
            "next_cursor": next_cursor,
            "list_token": fingerprint({"head": head, "query": query_hash, "ready_sequence": cap}),
            "summary_search": "cached_only",
        }

    @staticmethod
    def _matches_filter(state, filter_name):
        if filter_name == "needs-review":
            return state["review_state"] == "needs-review" or state["context"]["read_health"] != "complete"
        if filter_name == "blocked":
            return state["review_state"] == "blocked"
        if filter_name == "stale":
            return state["context"]["freshness"] == "stale"
        return state["review_state"] == "ready"

    @staticmethod
    def _search_text(state):
        presentation = state["presentation"]
        texts = [state["issue"]["title"]]
        if presentation["status"] == "ready":
            headline = presentation.get("headline", {})
            texts.append(headline.get("text", "") if isinstance(headline, dict) else str(headline))
            texts.extend(item.get("text", "") if isinstance(item, dict) else str(item)
                         for item in presentation.get("summary", []))
        return unicodedata.normalize("NFKC", "\n".join(texts)).casefold()

    @staticmethod
    def _sort_key(state):
        review_state = state["review_state"]
        health = state["context"]["read_health"]
        freshness = state["context"]["freshness"]
        if health != "complete" or review_state not in {"ready", "needs-review", "blocked"}:
            rank = 0
        elif review_state == "needs-review":
            rank = 0
        elif review_state == "blocked":
            rank = 1
        elif freshness == "stale":
            rank = 2
        else:
            rank = 3
        ready_unknown = 0 if rank == 3 and freshness == "unknown" else 1
        return rank, ready_unknown, -state["_sequence"], state["snapshot_key"]

    @staticmethod
    def _card(state):
        names = ("snapshot_key", "snapshot_ref", "review_ref", "scope", "issue",
                 "snapshot_created_at", "review_state", "state_label", "state_reason",
                 "counts", "required_complete", "context", "presentation", "read_token")
        return {name: state[name] for name in names if name in state}

    @staticmethod
    def _encode_cursor(value):
        raw = canonical_json(value).encode()
        envelope = canonical_json({"value": value, "checksum": fingerprint(raw)}).encode()
        return base64.urlsafe_b64encode(envelope).rstrip(b"=").decode()

    @staticmethod
    def _decode_cursor(value):
        try:
            raw = base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))
            envelope = json.loads(raw)
            if set(envelope) != {"value", "checksum"}:
                raise ValueError
            if envelope["checksum"] != fingerprint(canonical_json(envelope["value"]).encode()):
                raise ValueError
            return envelope["value"]
        except (TypeError, ValueError, UnicodeError, json.JSONDecodeError, binascii.Error):
            raise ReadModelError("INVALID_QUERY", "Cursor is invalid") from None
