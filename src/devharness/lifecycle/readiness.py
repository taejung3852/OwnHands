from __future__ import annotations

import json

from .model import STAGE_SCOPE_KEYS, canonical_json, fingerprint


REQUIREMENTS = {
    ("goal", "discover"): (),
    ("issue", "refine"): (),
    ("spec", "draft"): ("issue",),
    ("spec", "review"): ("spec",),
    ("spec", "activate"): ("spec", "approval"),
    ("baseline", "capture"): ("spec", "approval", "code_state", "environment"),
    ("execution", "perform"): ("attempt", "spec", "approval", "code_state", "environment"),
    ("review", "compose"): ("spec", "approval", "code_state", "environment", "baseline"),
    ("review", "complete"): ("review", "snapshot"),
    ("decision", "decide"): ("snapshot",),
}

EXPECTED_KINDS = {
    "issue": "work_issue",
    "spec": "spec",
    "approval": "spec_approval",
    "attempt": "attempt",
    "code_state": "code_state",
    "environment": "environment",
    "baseline": "baseline",
    "review": "review",
    "snapshot": "snapshot",
}

def inspect_stage(store, stage: str, action: str, scope: dict, inputs: dict, request_context: dict) -> dict:
    required = REQUIREMENTS.get((stage, action))
    if required is None:
        raise ValueError(f"unsupported lifecycle stage/action: {stage}/{action}")
    if not isinstance(inputs, dict) or not isinstance(request_context, dict):
        raise ValueError("inputs and request_context must be objects")

    inputs = json.loads(canonical_json(inputs))
    request_context = json.loads(canonical_json(request_context))
    checks = []
    input_refs = []
    records = {}
    invalid = False
    if set(scope) != STAGE_SCOPE_KEYS[stage]:
        invalid = True
        checks.append({"input": "scope", "status": "invalid", "reason": "invalid_stage_scope"})
    if "attempt_id" in scope:
        issue_scope = {key: scope[key] for key in ("project_id", "issue_id")}
        active_attempt = store.current("attempt", issue_scope)
        if active_attempt is None or store.get(active_attempt)["scope"] != scope:
            checks.append({"input": "attempt", "status": "missing", "reason": "inactive_attempt"})
    if stage in {"goal", "issue"}:
        if not isinstance(request_context.get("request"), str) or not request_context["request"].strip():
            checks.append({"input": "request", "status": "missing", "reason": "user_request_missing"})
        if not isinstance(request_context.get("source"), str) or not request_context["source"].strip():
            checks.append({"input": "request_source", "status": "missing", "reason": "request_source_missing"})
    for name in required:
        value = inputs.get(name)
        if value is None:
            checks.append({"input": name, "status": "missing", "reason": "required_input_missing"})
            continue
        try:
            record = store.get(value)
            store.assert_reference_scope(value, scope)
        except ValueError as error:
            invalid = True
            checks.append({"input": name, "status": "invalid", "reason": "invalid_reference", "detail": str(error)})
        else:
            expected_kind = EXPECTED_KINDS[name]
            if record["kind"] != expected_kind:
                invalid = True
                checks.append({"input": name, "status": "invalid", "reason": "unexpected_artifact_kind",
                               "expected": expected_kind, "actual": record["kind"], "reference": value})
                continue
            records[name] = record
            input_refs.append(value)
            if name == "spec" and stage in {"baseline", "execution", "review"}:
                issue_scope = {key: scope[key] for key in ("project_id", "issue_id")}
                if store.current("spec", issue_scope) != value:
                    checks.append({"input": name, "status": "missing", "reason": "inactive_spec_revision", "reference": value})
                    continue
            if name == "approval" and (
                record["data"].get("spec") != inputs.get("spec")
                or record["data"].get("actor", {}).get("kind") != "human"
                or record["data"].get("decision") != "approved"
            ):
                invalid = True
                checks.append({"input": name, "status": "invalid", "reason": "approval_not_usable",
                               "reference": value})
                continue
            if name == "approval" and stage in {"baseline", "execution", "review"}:
                issue_scope = {key: scope[key] for key in ("project_id", "issue_id")}
                activation = store.current_activation("spec", issue_scope)
                if activation is None or activation["reference"] != inputs.get("spec") or activation["approval"] != value:
                    checks.append({"input": name, "status": "missing", "reason": "inactive_spec_approval",
                                   "reference": value})
                    continue
            checks.append({"input": name, "status": "available", "reason": "validated_reference", "reference": value})

    if stage == "review" and action == "compose" and {"spec", "approval", "environment", "baseline"} <= set(records):
        baseline_data = records["baseline"]["data"]
        fields = ("spec", "approval") if baseline_data.get("contract_version") == 2 else ("spec", "approval", "environment")
        mismatches = [name for name in fields
                      if baseline_data.get("spec_approval" if name == "approval" else name) != inputs[name]]
        if mismatches:
            invalid = True
            checks.append({"input": "baseline", "status": "invalid", "reason": "baseline_input_mismatch",
                           "fields": mismatches, "reference": inputs["baseline"]})
        if baseline_data.get("baseline_kind") != "verification":
            invalid = True
            checks.append({"input": "baseline", "status": "invalid", "reason": "baseline_not_verification",
                           "reference": inputs["baseline"]})
    if stage == "review" and action == "complete" and {"review", "snapshot"} <= set(records):
        if records["snapshot"]["data"].get("review") != inputs["review"]:
            invalid = True
            checks.append({"input": "snapshot", "status": "invalid", "reason": "snapshot_review_mismatch",
                           "reference": inputs["snapshot"]})

    missing = any(check["status"] == "missing" for check in checks)
    readiness = "invalid" if invalid else "needs-input" if missing else "ready"
    evaluated = {"scope": scope, "inputs": inputs, "request_context": request_context, "rules_version": 1}
    return {
        "namespace": "ownhands.lifecycle",
        "schema_version": 1,
        "stage": stage,
        "action": action,
        "subject_ref": dict(scope),
        "input_refs": input_refs,
        "request_context": request_context,
        "readiness": readiness,
        "checks": checks,
        "evaluated_against": {**evaluated, "hash": fingerprint(evaluated)},
    }
