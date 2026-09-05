from __future__ import annotations

import hashlib
import json
import re
import shutil
from pathlib import Path


CONTEXT_TYPES = {
    "agents_instruction",
    "instruction_overlay",
    "project_context",
    "reference",
    "skill",
    "task_instruction",
}
CONTROL_TYPES = {"approval_policy", "control_config", "hook", "rule", "sandbox"}
APPLICABILITY_DECISIONS = {
    "maintain",
    "add_for_task",
    "exclude_for_task",
    "replace_with_specific",
    "forbidden",
    "unobserved",
}
TRIGGERS = {
    "task_start",
    "scope_expansion",
    "phase_transition",
    "external_effect_or_permission_added",
    "before_completion_claim",
}
SUPPORTED_LINT_SUFFIXES = {".json", ".md", ".rules", ".txt", ".toml"}
SHA256 = re.compile(r"^sha256:[0-9a-f]{64}$")
REFERENCE = re.compile(r"`([^`]*(?:/|\.[A-Za-z0-9]+)[^`]*)`")
ASSIGNMENT = re.compile(r"^\s*([A-Za-z][A-Za-z0-9_.-]*)\s*=\s*(.+?)\s*$")


class ContextArchitectureError(ValueError):
    pass


def _canonical(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _fingerprint(value: object) -> str:
    return "sha256:" + hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _require_exact_fields(value: object, expected: set[str], name: str) -> dict:
    if not isinstance(value, dict) or set(value) != expected:
        actual = set(value) if isinstance(value, dict) else set()
        missing = sorted(expected - actual)
        extra = sorted(actual - expected)
        raise ContextArchitectureError(
            f"{name} fields do not match contract; missing={missing}, extra={extra}"
        )
    return value


def _require_text(value: object, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ContextArchitectureError(f"{name} must be a non-empty string")
    return value


def _require_unique_texts(value: object, name: str) -> list[str]:
    if not isinstance(value, list) or not all(isinstance(item, str) and item for item in value):
        raise ContextArchitectureError(f"{name} must contain strings")
    if len(value) != len(set(value)):
        raise ContextArchitectureError(f"{name} contains duplicates")
    return value


def _validate_check(value: object, name: str) -> set[str]:
    check_value = _require_exact_fields(
        value,
        {
            "result",
            "basis",
            "evidence_refs",
            "inference_from",
            "checked_at",
            "exact_scope",
            "residual_risks",
        },
        name,
    )
    result = check_value["result"]
    basis = check_value["basis"]
    if result not in {"pass", "fail", "not_run", "not_applicable"}:
        raise ContextArchitectureError(f"{name} result is invalid")
    if basis not in {"observed", "inferred", "unobserved"}:
        raise ContextArchitectureError(f"{name} basis is invalid")
    evidence_refs = set(_require_unique_texts(check_value["evidence_refs"], f"{name} evidence_refs"))
    inference_from = _require_unique_texts(check_value["inference_from"], f"{name} inference_from")
    if result in {"pass", "fail", "not_applicable"} and basis == "unobserved":
        raise ContextArchitectureError(f"{name} {result} cannot use unobserved basis")
    if result == "not_run" and (
        basis != "unobserved" or evidence_refs or inference_from or check_value["checked_at"] is not None
    ):
        raise ContextArchitectureError(f"{name} not_run must remain unobserved")
    if basis == "observed" and (not evidence_refs or not check_value["checked_at"]):
        raise ContextArchitectureError(f"{name} observed basis requires evidence and time")
    if basis == "inferred" and (not inference_from or not check_value["checked_at"]):
        raise ContextArchitectureError(f"{name} inferred basis requires inference provenance")
    if not isinstance(check_value["exact_scope"], str):
        raise ContextArchitectureError(f"{name} exact_scope must be a string")
    _require_unique_texts(check_value["residual_risks"], f"{name} residual_risks")
    return evidence_refs | set(inference_from)


def _validate_source(value: object, source_class: str, position: int) -> tuple[str, set[str]]:
    name = f"{source_class}_sources[{position}]"
    item = _require_exact_fields(
        value,
        {
            "source_id",
            "source_type",
            "locator",
            "content_hash",
            "version",
            "scope",
            "freshness",
            "applicability",
            "realization",
        },
        name,
    )
    source_id = _require_text(item["source_id"], f"{name} source_id")
    allowed_types = CONTEXT_TYPES if source_class == "context" else CONTROL_TYPES
    if item["source_type"] not in allowed_types:
        raise ContextArchitectureError(f"{source_class}_sources contains wrong source_type")
    locator = _require_exact_fields(item["locator"], {"kind", "value"}, f"{name} locator")
    if locator["kind"] not in {"repository_path", "runtime_id", "managed_policy"}:
        raise ContextArchitectureError(f"{name} locator kind is invalid")
    _require_text(locator["value"], f"{name} locator value")
    if not isinstance(item["content_hash"], str) or not SHA256.fullmatch(item["content_hash"]):
        raise ContextArchitectureError(f"{name} content_hash must be sha256")
    _require_text(item["version"], f"{name} version")
    scope = _require_exact_fields(item["scope"], {"kind", "value"}, f"{name} scope")
    if scope["kind"] not in {"global", "project", "worktree", "task", "phase", "boundary"}:
        raise ContextArchitectureError(f"{name} scope kind is invalid")
    _require_text(scope["value"], f"{name} scope value")

    freshness = _require_exact_fields(
        item["freshness"], {"status", "basis", "checked_at", "evidence_refs"}, f"{name} freshness"
    )
    if freshness["status"] not in {"current", "stale", "unknown"}:
        raise ContextArchitectureError(f"{name} freshness status is invalid")
    if freshness["basis"] not in {"observed", "inferred", "unobserved"}:
        raise ContextArchitectureError(f"{name} freshness basis is invalid")
    references = set(_require_unique_texts(freshness["evidence_refs"], f"{name} freshness evidence_refs"))
    if freshness["basis"] == "observed" and (not references or not freshness["checked_at"]):
        raise ContextArchitectureError(f"{name} observed freshness requires evidence")
    if freshness["basis"] == "unobserved" and (references or freshness["checked_at"] is not None):
        raise ContextArchitectureError(f"{name} unobserved freshness cannot cite evidence")

    applicability = _require_exact_fields(
        item["applicability"], {"decision", "basis", "reason", "evidence_refs"}, f"{name} applicability"
    )
    if applicability["decision"] not in APPLICABILITY_DECISIONS:
        raise ContextArchitectureError(f"{name} applicability decision is invalid")
    if applicability["basis"] not in {"observed", "inferred", "unobserved"}:
        raise ContextArchitectureError(f"{name} applicability basis is invalid")
    _require_text(applicability["reason"], f"{name} applicability reason")
    applicability_refs = set(
        _require_unique_texts(applicability["evidence_refs"], f"{name} applicability evidence_refs")
    )
    if applicability["decision"] == "unobserved" and applicability["basis"] != "unobserved":
        raise ContextArchitectureError(f"{name} unobserved decision requires unobserved basis")
    if applicability["basis"] == "observed" and not applicability_refs:
        raise ContextArchitectureError(f"{name} observed applicability requires evidence")
    if applicability["basis"] == "unobserved" and applicability_refs:
        raise ContextArchitectureError(f"{name} unobserved applicability cannot cite evidence")
    references |= applicability_refs

    realization = _require_exact_fields(
        item["realization"], {"configured", "loaded", "enforced"}, f"{name} realization"
    )
    for check_name in ("configured", "loaded", "enforced"):
        references |= _validate_check(realization[check_name], f"{name} realization.{check_name}")
    return source_id, references


def validate_manifest(manifest: dict, evidence_ids: set[str], event_ids: set[str]) -> None:
    document = _require_exact_fields(
        manifest,
        {
            "manifest_version",
            "manifest_id",
            "task",
            "context_sources",
            "control_sources",
            "instruction_overlay",
            "control_overlay",
            "event_refs",
            "evidence_refs",
            "generated_at",
        },
        "manifest",
    )
    if document["manifest_version"] != "1.0":
        raise ContextArchitectureError("manifest version mismatch")
    _require_text(document["manifest_id"], "manifest_id")
    task = _require_exact_fields(
        document["task"],
        {"project_id", "worktree_id", "task_id", "mode", "target_commit", "cwd", "environment_ref"},
        "task",
    )
    for field in ("project_id", "worktree_id", "task_id", "target_commit", "cwd", "environment_ref"):
        _require_text(task[field], f"task {field}")
    if task["mode"] not in {"managed", "imported"}:
        raise ContextArchitectureError("task mode is invalid")
    if not isinstance(document["context_sources"], list) or not isinstance(document["control_sources"], list):
        raise ContextArchitectureError("source collections must be arrays")
    context_ids: set[str] = set()
    control_ids: set[str] = set()
    nested_references: set[str] = set()
    for index, item in enumerate(document["context_sources"]):
        source_id, references = _validate_source(item, "context", index)
        if source_id in context_ids:
            raise ContextArchitectureError("duplicate context source_id")
        context_ids.add(source_id)
        nested_references |= references
    for index, item in enumerate(document["control_sources"]):
        source_id, references = _validate_source(item, "control", index)
        if source_id in context_ids | control_ids:
            raise ContextArchitectureError("duplicate or mixed source_id")
        control_ids.add(source_id)
        nested_references |= references

    instruction = _require_exact_fields(
        document["instruction_overlay"], {"source_refs", "skill_invocations", "excluded_source_refs"}, "instruction_overlay"
    )
    instruction_refs = set(_require_unique_texts(instruction["source_refs"], "instruction_overlay source_refs"))
    excluded_refs = set(
        _require_unique_texts(instruction["excluded_source_refs"], "instruction_overlay excluded_source_refs")
    )
    if not instruction_refs <= context_ids or not excluded_refs <= context_ids:
        raise ContextArchitectureError("instruction_overlay may reference only context_sources")
    if instruction_refs & excluded_refs:
        raise ContextArchitectureError("instruction_overlay cannot activate and exclude the same source")
    if not isinstance(instruction["skill_invocations"], list):
        raise ContextArchitectureError("skill_invocations must be an array")
    nested_event_references: set[str] = set()
    for invocation in instruction["skill_invocations"]:
        invocation = _require_exact_fields(
            invocation, {"source_ref", "reference_refs", "event_ref", "evidence_refs"}, "skill invocation"
        )
        if invocation["source_ref"] not in context_ids:
            raise ContextArchitectureError("skill invocation must reference context source")
        if not set(_require_unique_texts(invocation["reference_refs"], "reference_refs")) <= context_ids:
            raise ContextArchitectureError("skill reference must reference context source")
        nested_references |= set(_require_unique_texts(invocation["evidence_refs"], "skill evidence_refs"))
        nested_event_references.add(_require_text(invocation["event_ref"], "skill event_ref"))

    control = _require_exact_fields(
        document["control_overlay"], {"source_refs", "immutable_source_refs"}, "control_overlay"
    )
    control_refs = set(_require_unique_texts(control["source_refs"], "control_overlay source_refs"))
    immutable_refs = set(
        _require_unique_texts(control["immutable_source_refs"], "control_overlay immutable_source_refs")
    )
    if not control_refs <= control_ids or not immutable_refs <= control_refs:
        raise ContextArchitectureError("control_overlay may reference only active control_sources")

    declared_evidence = set(_require_unique_texts(document["evidence_refs"], "evidence_refs"))
    declared_events = set(_require_unique_texts(document["event_refs"], "event_refs"))
    if not nested_references <= declared_evidence or not declared_evidence <= evidence_ids:
        raise ContextArchitectureError("unresolved evidence reference")
    if not nested_event_references <= declared_events or not declared_events <= event_ids:
        raise ContextArchitectureError("unresolved event reference")


def _finding(rule_id: str, evidence: str, location: str, impact: str, suggestion: str) -> dict:
    return {
        "rule_id": rule_id,
        "evidence": evidence,
        "location": location,
        "impact": impact,
        "suggestion": suggestion,
        "basis": "observed",
    }


def lint_context(root: Path, sources: list[dict]) -> dict:
    root = Path(root).resolve()
    findings: list[dict] = []
    unobserved: list[dict] = []
    readable: list[tuple[dict, list[str]]] = []
    source_ids = {item["source_id"] for item in sources}
    for item in sources:
        path = root / item["path"]
        if path.suffix not in SUPPORTED_LINT_SUFFIXES:
            unobserved.append(
                {"source_ref": item["source_id"], "basis": "unobserved", "reason": f"unsupported file format: {path.suffix or '<none>'}"}
            )
            continue
        if not path.is_file():
            findings.append(
                _finding("missing_source", item["path"], f"{item['path']}:1", "declared context cannot be inspected", "restore the file or exclude the source")
            )
            continue
        lines = path.read_text(encoding="utf-8").splitlines()
        readable.append((item, lines))
        for command in item.get("command_refs", []):
            executable = command.split()[0]
            if shutil.which(executable) is None:
                findings.append(
                    _finding("missing_command_reference", command, f"{item['path']}:1", "the referenced command is not available in the lint environment", "install it for the target environment or remove the reference")
                )
        for skill_ref in item.get("skill_refs", []):
            if skill_ref not in source_ids:
                findings.append(
                    _finding("missing_skill_reference", skill_ref, f"{item['path']}:1", "the router points to an undeclared Skill", "declare the Skill source or remove the route")
                )
        for code_ref in item.get("code_refs", []):
            code_path = root / code_ref["path"]
            if code_path.is_file() and code_ref["symbol"] not in code_path.read_text(encoding="utf-8"):
                findings.append(
                    _finding("stale_code_description", f"{code_ref['path']}:{code_ref['symbol']}", f"{item['path']}:1", "the documented symbol is absent from current code", "update the reference after inspecting the current API")
                )
        if item.get("source_type") == "skill" and item.get("invoked") is False:
            findings.append(
                _finding("uninvoked_skill", item["source_id"], f"{item['path']}:1", "the declared Skill was not invoked for this Task", "exclude it from the Task overlay or record the intended trigger")
            )
        if item.get("scope") == "task" and item.get("placement") == "always_loaded":
            findings.append(
                _finding("task_instruction_always_loaded", item["source_id"], f"{item['path']}:1", "task-only guidance can affect unrelated tasks", "move it to instruction_overlay")
            )
        if item.get("duplicates_control"):
            findings.append(
                _finding("deterministic_control_restatement", item["duplicates_control"], f"{item['path']}:1", "natural language can drift from the enforced control", "keep the control authoritative and link to it")
            )
        for line_number, line in enumerate(lines, 1):
            if re.search(r"\b(always|never|all tasks)\b|모든 작업|항상|절대", line, re.IGNORECASE):
                findings.append(
                    _finding("broad_universal_wording", line.strip(), f"{item['path']}:{line_number}", "guidance may apply beyond its intended scope", "state the exact task, phase, or boundary")
                )
            inventory = ASSIGNMENT.match(line)
            if inventory and inventory.group(1).lower() in {"files", "file_list", "repository_files"} and inventory.group(2).count(",") >= 10:
                findings.append(
                    _finding("oversized_repository_inventory", line.strip(), f"{item['path']}:{line_number}", "large static inventories crowd context and become stale", "replace the inventory with an on-demand reference")
                )
            for reference in REFERENCE.findall(line):
                candidate = reference.split("#", 1)[0]
                if candidate and not candidate.startswith(("http://", "https://")) and not (root / candidate).exists():
                    findings.append(
                        _finding("stale_reference", reference, f"{item['path']}:{line_number}", "the instruction points to a missing path", "update or remove the reference after review")
                    )

    occurrences: dict[str, list[str]] = {}
    assignments: dict[str, list[tuple[str, str]]] = {}
    for item, lines in readable:
        if item.get("source_type") == "skill":
            continue
        for line_number, line in enumerate(lines, 1):
            normalized = " ".join(line.strip().lower().split())
            if normalized:
                occurrences.setdefault(normalized, []).append(f"{item['path']}:{line_number}")
            match = ASSIGNMENT.match(line)
            if match:
                assignments.setdefault(match.group(1).lower(), []).append((match.group(2).strip(), f"{item['path']}:{line_number}"))
    for text, locations in occurrences.items():
        if len({location.split(":", 1)[0] for location in locations}) > 1:
            findings.append(
                _finding("duplicate_instruction", text, locations[0], "the same guidance is loaded from multiple sources", "keep one authoritative source and reference it elsewhere")
            )
    for key, values in assignments.items():
        if len({value for value, _ in values}) > 1:
            findings.append(
                _finding("conflicting_instruction", f"{key}: {sorted({value for value, _ in values})}", values[0][1], "the same instruction key has incompatible values", "choose one scoped authority and mark the other excluded")
            )

    skills: dict[tuple[str, str], list[dict]] = {}
    for item in sources:
        if item.get("source_type") == "skill":
            skills.setdefault((item.get("skill_name", ""), item.get("trigger", "")), []).append(item)
    for (skill_name, trigger), colliding in skills.items():
        if len({item.get("router") for item in colliding}) > 1:
            findings.append(
                _finding("router_collision", f"{skill_name}: {trigger}", f"{colliding[0]['path']}:1", "more than one router owns the same skill trigger", "assign one router and make the other route explicitly")
            )
    findings.sort(key=lambda item: (item["rule_id"], item["location"], item["evidence"]))
    unobserved.sort(key=lambda item: item["source_ref"])
    return {
        "lint_version": "1.0",
        "root": str(root),
        "findings": findings,
        "unobserved": unobserved,
        "false_positive_boundary": "lexical matches require human review; semantic paraphrases and dynamic paths are unobserved",
        "autofix_applied": False,
    }


class ApplicabilityGate:
    def __init__(self) -> None:
        self._last_fingerprint: str | None = None

    def evaluate(self, gate_input: dict) -> dict:
        if gate_input.get("trigger") not in TRIGGERS:
            raise ContextArchitectureError("invalid applicability trigger")
        for item in gate_input.get("sources", []):
            if item.get("source_class") not in {"context", "control"}:
                raise ContextArchitectureError("invalid source_class")
            if item.get("deterministic") and item.get("requested_decision") in {"exclude_for_task", "forbidden"}:
                raise ContextArchitectureError("deterministic control cannot be weakened")
        fingerprint = _fingerprint(gate_input)
        cache_hit = fingerprint == self._last_fingerprint
        self._last_fingerprint = fingerprint
        active = set(gate_input.get("active_source_refs", []))
        task = gate_input["task"]
        overlays = {"context": [], "control": []}
        for item in gate_input["sources"]:
            if not item.get("content_hash"):
                decision, basis, reason = "unobserved", "unobserved", "source freshness or identity cannot be confirmed"
            elif item.get("lint_status") in {"conflicting", "stale"}:
                decision, basis, reason = "forbidden", "observed", f"lint status is {item['lint_status']}"
            elif item.get("replaced_by"):
                decision, basis, reason = "replace_with_specific", "observed", f"replaced by {item['replaced_by']}"
            elif item.get("deterministic"):
                decision = "maintain" if item["source_id"] in active else "add_for_task"
                basis, reason = "observed", "deterministic control remains active across applicability changes"
            else:
                applies = item.get("applies_to", {})
                matches = task.get("scope") in applies.get("scopes", []) and task.get("phase") in applies.get("phases", [])
                if matches:
                    decision = "maintain" if item["source_id"] in active else "add_for_task"
                    basis, reason = "observed", "declared scope and phase match"
                else:
                    decision, basis, reason = "exclude_for_task", "observed", "declared scope or phase does not match"
            overlays[item["source_class"]].append(
                {"source_ref": item["source_id"], "decision": decision, "basis": basis, "reason": reason}
            )
        return {
            "gate_version": "1.0",
            "trigger": gate_input["trigger"],
            "input_fingerprint": fingerprint,
            "cache_hit": cache_hit,
            "instruction_overlay": overlays["context"],
            "control_overlay": overlays["control"],
        }


def evaluate_context_guarantees(matrix: dict, manifest: dict, evidence_records: list[dict]) -> list[dict]:
    if matrix.get("matrix_version") != "1.5-proposed-1":
        raise ContextArchitectureError("context guarantee matrix version mismatch")
    by_type: dict[str, list[dict]] = {}
    for record in evidence_records:
        by_type.setdefault(record.get("evidence_type", ""), []).append(record)
    manifest_id = manifest["manifest_id"]
    task_id = manifest["task"]["task_id"]
    context_ids = {item["source_id"] for item in manifest["context_sources"]}

    def belongs_to_manifest(item: dict) -> bool:
        fields = item.get("fields", {})
        if fields.get("manifest_ref") != manifest_id or fields.get("task_ref") != task_id:
            return False
        if "source_ref" in fields and fields["source_ref"] not in context_ids:
            return False
        if "source_refs" in fields:
            source_refs = fields["source_refs"]
            if not isinstance(source_refs, list) or not source_refs or not set(source_refs) <= context_ids:
                return False
        return True

    results = []
    for claim in matrix["claims"]:
        matching = []
        conflicts = []
        for requirement in claim["required_evidence"]:
            candidates = by_type.get(requirement["type"], [])
            adequate = [
                item
                for item in candidates
                if item.get("basis") in claim["allowed_basis"]
                and set(requirement["required_fields"]) <= set(item.get("fields", {}))
                and belongs_to_manifest(item)
            ]
            matching.extend(item for item in adequate if item.get("result") == "pass")
            conflicts.extend(item for item in adequate if item.get("result") == "fail")
        if conflicts:
            verdict = "contradicted"
        elif len(matching) >= len(claim["required_evidence"]):
            verdict = "supported"
        else:
            verdict = "not_evaluated"
        results.append(
            {
                "claim_id": claim["claim_id"],
                "category": claim["category"],
                "verdict": verdict,
                "evidence_refs": sorted({item["evidence_id"] for item in matching}),
                "conflict_refs": sorted({item["evidence_id"] for item in conflicts}),
                "residual_risks": claim["residual_risks"],
                "permitted_statement": claim["claim"] if verdict == "supported" else None,
            }
        )
    return results


def validate_status_report(report: dict, manifest: dict, matrix: dict, evidence_records: list[dict]) -> None:
    document = _require_exact_fields(
        report,
        {
            "report_version",
            "matrix_version",
            "manifest_ref",
            "active_context",
            "active_controls",
            "excluded_context",
            "applicability_results",
            "lint_findings",
            "claim_results",
        },
        "status report",
    )
    if document["report_version"] != "1.0" or document["matrix_version"] != matrix["matrix_version"]:
        raise ContextArchitectureError("status report version mismatch")
    if document["manifest_ref"] != manifest["manifest_id"]:
        raise ContextArchitectureError("status report manifest mismatch")
    context_ids = set(manifest["instruction_overlay"]["source_refs"])
    control_ids = set(manifest["control_overlay"]["source_refs"])
    evidence_ids = {item["evidence_id"] for item in evidence_records}
    for section, allowed in (("active_context", context_ids), ("active_controls", control_ids)):
        if not isinstance(document[section], list):
            raise ContextArchitectureError(f"{section} must be an array")
        for item in document[section]:
            if item.get("source_ref") not in allowed:
                raise ContextArchitectureError(f"{section} contains the wrong source class")
            item_evidence = set(item.get("evidence_refs", []))
            if not item_evidence or not item_evidence <= evidence_ids:
                raise ContextArchitectureError(f"{section} contains unresolved evidence")
    for section in ("excluded_context", "applicability_results", "lint_findings"):
        if not isinstance(document[section], list):
            raise ContextArchitectureError(f"{section} must be an array")
        for item in document[section]:
            if not set(item.get("evidence_refs", [])) <= evidence_ids:
                raise ContextArchitectureError(f"{section} contains unresolved evidence")
    expected = evaluate_context_guarantees(matrix, manifest, evidence_records)
    if document["claim_results"] != expected:
        raise ContextArchitectureError("claim_results do not match authoritative evaluation")


def _validate_package(package: dict) -> None:
    _require_exact_fields(
        package,
        {
            "package_version",
            "package_id",
            "fixture",
            "fixed_conditions",
            "conditions",
            "repetitions",
            "crossover_order",
            "metrics",
        },
        "comparison package",
    )
    if package["package_version"] != "1.0" or package["repetitions"] != 3:
        raise ContextArchitectureError("comparison package version or repetitions mismatch")
    if set(package["conditions"]) != {"A", "B", "C"}:
        raise ContextArchitectureError("comparison conditions must be A, B, and C")
    if len(package["crossover_order"]) != 9 or any(package["crossover_order"].count(key) != 3 for key in "ABC"):
        raise ContextArchitectureError("comparison package must schedule exactly 9 balanced runs")
    _require_text(package["fixed_conditions"].get("model"), "comparison model")
    _require_text(package["fixed_conditions"].get("reasoning_effort"), "comparison reasoning effort")
    _require_text(package["fixed_conditions"].get("prompt"), "comparison prompt")


def build_comparison_plan(package: dict, target_commit: str) -> list[dict]:
    _validate_package(package)
    _require_text(target_commit, "target_commit")
    fixed = package["fixed_conditions"]
    prompt_hash = _fingerprint(fixed["prompt"])
    environment_fingerprint = _fingerprint(fixed["environment"])
    control_fingerprint = _fingerprint(fixed["controls"])
    counts = {"A": 0, "B": 0, "C": 0}
    plan = []
    for sequence, condition in enumerate(package["crossover_order"], 1):
        counts[condition] += 1
        plan.append(
            {
                "run_id": f"{package['package_id']}-{sequence:02d}",
                "sequence": sequence,
                "condition": condition,
                "repetition": counts[condition],
                "fixture_id": package["fixture"]["fixture_id"],
                "target_commit": target_commit,
                "model": fixed["model"],
                "reasoning_effort": fixed["reasoning_effort"],
                "prompt_hash": prompt_hash,
                "environment_fingerprint": environment_fingerprint,
                "control_fingerprint": control_fingerprint,
                "context_fingerprint": _fingerprint(package["conditions"][condition]),
            }
        )
    return plan


def evaluate_comparison(package: dict, runs: list[dict]) -> dict:
    _validate_package(package)
    if len(runs) != 9:
        raise ContextArchitectureError("comparison requires exactly 9 runs")
    run_ids = [item.get("run_id") for item in runs]
    if len(set(run_ids)) != 9:
        raise ContextArchitectureError("comparison run_id values must be unique")
    for fixed_field, label in (
        ("target_commit", "commit"),
        ("model", "model"),
        ("reasoning_effort", "reasoning effort"),
        ("prompt_hash", "prompt"),
        ("environment_fingerprint", "environment"),
        ("control_fingerprint", "control"),
    ):
        if len({item.get(fixed_field) for item in runs}) != 1:
            raise ContextArchitectureError(f"comparison {label} changed across runs")
    expected_pairs = {(condition, repetition) for condition in "ABC" for repetition in (1, 2, 3)}
    if {(item.get("condition"), item.get("repetition")) for item in runs} != expected_pairs:
        raise ContextArchitectureError("comparison is missing a condition repetition")
    expected_context = {
        condition: _fingerprint(package["conditions"][condition]) for condition in "ABC"
    }
    if any(
        item.get("context_fingerprint") != expected_context.get(item.get("condition"))
        for item in runs
    ):
        raise ContextArchitectureError("comparison context fingerprint does not match condition")
    expected_plan = build_comparison_plan(package, runs[0]["target_commit"])
    plan_fields = ("sequence", "condition", "repetition", "run_id", "context_fingerprint")
    if any(
        any(run.get(field) != expected.get(field) for field in plan_fields)
        for run, expected in zip(runs, expected_plan)
    ):
        raise ContextArchitectureError("runs do not match the fixed comparison plan")
    required_metrics = set(package["metrics"])
    for run in runs:
        metrics = run.get("metrics")
        if not isinstance(metrics, dict) or set(metrics) != required_metrics:
            raise ContextArchitectureError("comparison metric fields do not match")
        for name, metric in metrics.items():
            if metric.get("basis") == "unobserved" and metric.get("value") is not None:
                raise ContextArchitectureError(f"unobserved metric cannot invent a value: {name}")
            if name in {"input_tokens", "output_tokens"} and metric.get("basis") == "observed" and not metric.get("receipt_ref"):
                raise ContextArchitectureError("observed token metrics require a runtime receipt")
            if name in {"human_understanding", "human_review_seconds"} and metric.get("basis") == "observed" and not metric.get("reviewer_ref"):
                raise ContextArchitectureError("observed human review metrics require a reviewer record")
    terminal_runs = [run for run in runs if run.get("status") in {"completed", "failed", "aborted"}]
    completed_runs = [run for run in runs if run.get("status") == "completed"]
    failure_counts = {
        "failed": sum(run.get("status") == "failed" for run in runs),
        "aborted": sum(run.get("status") == "aborted" for run in runs),
    }
    machine_metrics = (
        "requirements_met",
        "tests_passed",
        "instruction_violations",
        "out_of_scope_changes",
    )
    machine_observed = len(terminal_runs) == 9 and all(
        run["metrics"][name].get("basis") == "observed"
        and run["metrics"][name].get("value") is not None
        for run in runs
        for name in machine_metrics
    )
    if not machine_observed:
        return {
            "comparison_id": package["package_id"],
            "run_count": 9,
            "completed_run_count": len(completed_runs),
            "terminal_run_count": len(terminal_runs),
            "failure_counts": failure_counts,
            "improvement_verdict": "not_evaluated",
            "recommended_conditions": [],
            "permitted_statement": None,
            "human_metrics_basis": "unobserved",
            "residual_risks": [
                "no improvement claim is permitted until all nine runs and machine metrics are observed"
            ],
        }

    for run in runs:
        for name in ("requirements_met", "tests_passed"):
            if not isinstance(run["metrics"][name]["value"], bool):
                raise ContextArchitectureError(f"{name} must be a boolean")
        for name in ("instruction_violations", "out_of_scope_changes"):
            value = run["metrics"][name]["value"]
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ContextArchitectureError(f"{name} must be a non-negative integer")

    summary = {}
    for condition in "ABC":
        condition_runs = [run for run in runs if run["condition"] == condition]
        summary[condition] = {
            "requirements_met": sum(run["metrics"]["requirements_met"]["value"] for run in condition_runs),
            "tests_passed": sum(run["metrics"]["tests_passed"]["value"] for run in condition_runs),
            "instruction_violations": sum(run["metrics"]["instruction_violations"]["value"] for run in condition_runs),
            "out_of_scope_changes": sum(run["metrics"]["out_of_scope_changes"]["value"] for run in condition_runs),
        }
    baseline = summary["A"]
    recommended = []
    for condition in "BC":
        candidate = summary[condition]
        non_regressing = (
            candidate["requirements_met"] >= baseline["requirements_met"]
            and candidate["tests_passed"] >= baseline["tests_passed"]
            and candidate["instruction_violations"] <= baseline["instruction_violations"]
            and candidate["out_of_scope_changes"] <= baseline["out_of_scope_changes"]
        )
        improved = candidate != baseline and (
            candidate["requirements_met"] > baseline["requirements_met"]
            or candidate["tests_passed"] > baseline["tests_passed"]
            or candidate["instruction_violations"] < baseline["instruction_violations"]
            or candidate["out_of_scope_changes"] < baseline["out_of_scope_changes"]
        )
        if non_regressing and improved:
            recommended.append(condition)
    verdict = "recommended" if recommended else "no_improvement"
    statement = (
        f"관찰된 9회 fixture 실행의 기계 지표에서 {', '.join(recommended)} 조건이 A보다 비퇴행 개선됐다"
        if recommended
        else "관찰된 9회 fixture 실행의 기계 지표에서 A보다 비퇴행 개선된 Context 조건이 없었다"
    )
    return {
        "comparison_id": package["package_id"],
        "run_count": 9,
        "completed_run_count": len(completed_runs),
        "terminal_run_count": len(terminal_runs),
        "failure_counts": failure_counts,
        "improvement_verdict": verdict,
        "recommended_conditions": recommended,
        "permitted_statement": statement,
        "machine_summary": summary,
        "individual_results": [
            {
                "run_id": run["run_id"],
                "condition": run["condition"],
                "status": run["status"],
                "metrics": {name: run["metrics"][name] for name in machine_metrics},
            }
            for run in runs
        ],
        "human_metrics_basis": "unobserved",
        "residual_risks": [
            "human understanding and review time remain unobserved",
            "one fixture and one model configuration do not support broader generalization",
        ],
    }
