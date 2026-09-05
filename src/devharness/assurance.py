from __future__ import annotations

import copy
import fnmatch
import hashlib
import json
import subprocess
import tempfile
from pathlib import Path


HASH_PREFIX = "sha256:"
RESULTS = {"pass", "fail", "not_run", "inconclusive", "missing"}
BASES = {"observed", "inferred", "unobserved"}
CLASSIFICATIONS = {"new_feature", "regression"}
BLOCK_LEVELS = {"hard", "soft"}
RELATION_TYPES = {"feature", "contract", "dependency", "test"}


class AssuranceError(ValueError):
    pass


def canonical_json(value: object) -> str:
    try:
        return json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
    except (TypeError, ValueError) as error:
        raise AssuranceError(f"value is not canonical JSON: {error}") from error


def fingerprint(value: object) -> str:
    payload = value if isinstance(value, bytes) else canonical_json(value).encode("utf-8")
    return HASH_PREFIX + hashlib.sha256(payload).hexdigest()


def _is_hash(value: object) -> bool:
    if not isinstance(value, str) or not value.startswith(HASH_PREFIX):
        return False
    digest = value[len(HASH_PREFIX) :]
    return len(digest) == 64 and all(character in "0123456789abcdef" for character in digest)


def _text(value: object, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise AssuranceError(f"{name} must be a non-empty string")
    return value


def _unique_strings(value: object, name: str, *, allow_empty: bool = True) -> list[str]:
    if not isinstance(value, list) or (not allow_empty and not value):
        raise AssuranceError(f"{name} must be a list")
    result = [_text(item, name) for item in value]
    if len(result) != len(set(result)):
        raise AssuranceError(f"{name} contains a duplicate value")
    return result


def _unique_records(value: object, key: str, name: str, *, allow_empty: bool = True) -> list[dict]:
    if not isinstance(value, list) or (not allow_empty and not value):
        raise AssuranceError(f"{name} must be a list")
    records: list[dict] = []
    identities: list[str] = []
    for item in value:
        if not isinstance(item, dict):
            raise AssuranceError(f"{name} entries must be objects")
        identities.append(_text(item.get(key), f"{name}.{key}"))
        records.append(item)
    if len(identities) != len(set(identities)):
        raise AssuranceError(f"{name} contains a duplicate {key}")
    return records


def _validate_task(task: object) -> dict:
    if not isinstance(task, dict):
        raise AssuranceError("task identity is missing")
    required = ("project_id", "worktree_id", "environment_ref", "task_id")
    return {key: _text(task.get(key), f"task.{key}") for key in required}


def _validate_hash(value: object, name: str) -> str:
    if not _is_hash(value):
        raise AssuranceError(f"{name} must be a sha256 fingerprint")
    return value


def validate_assurance_draft(draft: object, gate_criteria: list[str]) -> dict:
    if not isinstance(draft, dict):
        raise AssuranceError("contract assurance_draft is missing")
    criteria = _unique_records(draft.get("criteria"), "criterion_id", "assurance_draft.criteria", allow_empty=False)
    criterion_ids = [item["criterion_id"] for item in criteria]
    if set(criterion_ids) != set(gate_criteria):
        missing = sorted(set(gate_criteria) - set(criterion_ids))
        unknown = sorted(set(criterion_ids) - set(gate_criteria))
        raise AssuranceError(f"assurance criteria mismatch; missing={missing}, unknown={unknown}")
    for criterion in criteria:
        if criterion.get("block_level") not in BLOCK_LEVELS:
            raise AssuranceError("assurance criterion block_level is invalid")

    tests = _unique_records(draft.get("tests"), "test_id", "assurance_draft.tests")
    test_ids = {item["test_id"] for item in tests}
    for test in tests:
        _text(test.get("command"), "assurance test command")
        _text(test.get("selection_scope"), "assurance test selection_scope")
        if test.get("classification") not in CLASSIFICATIONS:
            raise AssuranceError("assurance test classification is invalid")
        _unique_strings(test.get("code_refs"), "assurance test code_refs")

    mappings = _unique_records(draft.get("mappings"), "criterion_id", "assurance_draft.mappings", allow_empty=False)
    mapping_ids = {item["criterion_id"] for item in mappings}
    if mapping_ids != set(gate_criteria):
        missing = sorted(set(gate_criteria) - mapping_ids)
        unknown = sorted(mapping_ids - set(gate_criteria))
        raise AssuranceError(f"assurance mappings mismatch; missing={missing}, unknown={unknown}")
    for mapping in mappings:
        mapped_tests = _unique_strings(mapping.get("test_ids"), "assurance mapping test_ids")
        unknown_tests = sorted(set(mapped_tests) - test_ids)
        if unknown_tests:
            raise AssuranceError(f"assurance mapping has unknown test: {unknown_tests}")
        _unique_strings(mapping.get("viewpoints"), "assurance mapping viewpoints")
        _text(mapping.get("reason"), "assurance mapping reason")

    hypotheses = _unique_records(
        draft.get("impact_hypotheses"),
        "hypothesis_id",
        "assurance_draft.impact_hypotheses",
    )
    for hypothesis in hypotheses:
        _unique_strings(hypothesis.get("path_globs"), "impact hypothesis path_globs", allow_empty=False)
        _unique_strings(hypothesis.get("relation_refs"), "impact hypothesis relation_refs")
        if hypothesis.get("basis") not in {"declared", "static_observed"}:
            raise AssuranceError("impact hypothesis basis is invalid")
    return copy.deepcopy(draft)


def _validate_contract(contract: object) -> tuple[dict, dict]:
    if not isinstance(contract, dict):
        raise AssuranceError("contract must be an object")
    _text(contract.get("contract_id"), "contract_id")
    _validate_task(contract.get("task"))
    gate_criteria = _unique_strings(contract.get("gate_criteria"), "gate_criteria", allow_empty=False)
    _unique_strings(contract.get("validation_criteria"), "validation_criteria", allow_empty=False)
    _unique_strings(contract.get("protected_targets"), "protected_targets")
    actual = _validate_hash(contract.get("fingerprint"), "contract fingerprint")
    body = {key: value for key, value in contract.items() if key != "fingerprint"}
    if actual != fingerprint(body):
        raise AssuranceError("contract fingerprint does not match its contents")
    draft = validate_assurance_draft(contract.get("assurance_draft"), gate_criteria)
    return contract, draft


def _repository(path: Path | str) -> Path:
    repository = Path(path).resolve()
    if not repository.is_dir():
        raise AssuranceError("repository must be a directory")
    result = _git(repository, "rev-parse", "--show-toplevel", text=True).strip()
    if Path(result).resolve() != repository:
        raise AssuranceError("repository must be the exact Git worktree root")
    return repository


def _git(
    repository: Path,
    *arguments: str,
    input_bytes: bytes | None = None,
    text: bool = False,
) -> bytes | str:
    try:
        completed = subprocess.run(
            ["git", *arguments],
            cwd=repository,
            input=input_bytes,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=False,
        )
    except (OSError, subprocess.CalledProcessError) as error:
        detail = getattr(error, "stderr", b"")
        if isinstance(detail, bytes):
            detail = detail.decode("utf-8", errors="replace")
        raise AssuranceError(f"Git operation failed: {detail.strip()}") from error
    return completed.stdout.decode("utf-8") if text else completed.stdout


def _restore_public(restore_point: dict) -> dict:
    return {key: copy.deepcopy(value) for key, value in restore_point.items() if not key.startswith("_")}


def capture_restore_point(repository: Path | str, task: dict, observed_at: str) -> dict:
    repository = _repository(repository)
    identity = _validate_task(task)
    observed_at = _text(observed_at, "observed_at")
    start_commit = _git(repository, "rev-parse", "HEAD", text=True).strip()
    tracked_patch = _git(repository, "diff", "--binary", "HEAD", "--")
    tracked_patch_hash = fingerprint(tracked_patch)
    start_patch_hash = fingerprint({"start_commit": start_commit, "tracked_patch_hash": fingerprint(b"")})
    exclusions = [
        {"area": "untracked_content", "basis": "unobserved", "reason": "Git tracked patch excludes untracked files"},
        {"area": "submodules", "basis": "unobserved", "reason": "submodule working trees are not reconstructed"},
        {"area": "symbolic_links", "basis": "unobserved", "reason": "link targets are not captured or followed"},
    ]
    public = {
        "restore_point_version": "1.0",
        "restore_point_id": "restore:" + fingerprint(
            {"task": identity, "start_commit": start_commit, "tracked_patch_hash": tracked_patch_hash}
        ).removeprefix(HASH_PREFIX),
        "task": identity,
        "observed_at": observed_at,
        "start_commit": start_commit,
        "start_patch_hash": start_patch_hash,
        "tracked_patch_hash": tracked_patch_hash,
        "tracked_patch_size": len(tracked_patch),
        "scope": "local_tracked_git_workspace",
        "exclusions": exclusions,
    }
    return {**public, "_tracked_patch": tracked_patch}


def verify_restore_point(repository: Path | str, restore_point: dict) -> dict:
    repository = _repository(repository)
    if not isinstance(restore_point, dict) or not isinstance(restore_point.get("_tracked_patch"), bytes):
        raise AssuranceError("restore point lacks the captured tracked patch")
    patch = restore_point["_tracked_patch"]
    if fingerprint(patch) != restore_point.get("tracked_patch_hash"):
        raise AssuranceError("restore point tracked patch is stale or corrupted")
    source_before = _git(repository, "status", "--porcelain=v1", "-z")
    with tempfile.TemporaryDirectory(prefix="ownhands-m4-restore-") as temporary:
        clone = Path(temporary) / "clone"
        try:
            subprocess.run(
                ["git", "clone", "--quiet", "--no-hardlinks", str(repository), str(clone)],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
        except (OSError, subprocess.CalledProcessError) as error:
            raise AssuranceError("disposable clone creation failed") from error
        _git(clone, "checkout", "--quiet", restore_point["start_commit"])
        if patch:
            _git(clone, "apply", "--binary", "-", input_bytes=patch)
            added = _git(clone, "ls-files", "--others", "--exclude-standard", "-z")
            added_paths = [
                item.decode("utf-8", errors="surrogateescape")
                for item in added.split(b"\0")
                if item
            ]
            if added_paths:
                _git(clone, "add", "-N", "--", *added_paths)
        reconstructed = _git(clone, "diff", "--binary", "HEAD", "--")
        reconstructed_hash = fingerprint(reconstructed)
    source_after = _git(repository, "status", "--porcelain=v1", "-z")
    source_unchanged = source_before == source_after
    passed = reconstructed_hash == restore_point["tracked_patch_hash"] and source_unchanged
    return {
        "verification_version": "1.0",
        "restore_point_ref": restore_point["restore_point_id"],
        "task": copy.deepcopy(restore_point["task"]),
        "result": "pass" if passed else "fail",
        "basis": "observed",
        "method": "disposable_local_clone_reconstruction",
        "reconstructed_patch_hash": reconstructed_hash,
        "source_worktree_unchanged": source_unchanged,
        "exclusions": copy.deepcopy(restore_point["exclusions"]),
        "evidence_refs": [],
    }


def _changed_paths(repository: Path) -> list[dict]:
    raw = _git(repository, "diff", "--name-status", "--no-renames", "-z", "HEAD", "--")
    pieces = raw.split(b"\0")
    if pieces and pieces[-1] == b"":
        pieces.pop()
    if len(pieces) % 2:
        raise AssuranceError("Git changed-path output was malformed")
    changed = []
    for index in range(0, len(pieces), 2):
        status = pieces[index].decode("ascii", errors="strict")
        path = pieces[index + 1].decode("utf-8", errors="surrogateescape")
        changed.append({"path": path, "status": status, "basis": "observed"})
    return sorted(changed, key=lambda item: item["path"])


def _matches(path: str, pattern: str) -> bool:
    return fnmatch.fnmatchcase(path, pattern) or (
        pattern.endswith("/**") and path == pattern[:-3]
    )


def analyze_impact(
    repository: Path | str,
    restore_point: dict,
    contract: dict,
    relation_catalog: dict,
    observed_at: str,
) -> dict:
    repository = _repository(repository)
    contract, draft = _validate_contract(contract)
    if restore_point.get("task") != _validate_task(contract["task"]):
        raise AssuranceError("restore point and contract identity mismatch")
    actual_patch = _git(repository, "diff", "--binary", "HEAD", "--")
    if fingerprint(actual_patch) != restore_point.get("tracked_patch_hash"):
        raise AssuranceError("actual Git diff no longer matches the Restore Point")
    if not isinstance(relation_catalog, dict):
        raise AssuranceError("relation catalog must be an object")
    declared = _unique_records(relation_catalog.get("relations"), "relation_id", "relations")
    changed_paths = _changed_paths(repository)
    joined = []
    matched_paths: set[str] = set()
    relation_ids = set()
    for relation in declared:
        relation_id = relation["relation_id"]
        relation_ids.add(relation_id)
        pattern = _text(relation.get("changed_path_glob"), "relation changed_path_glob")
        relation_type = relation.get("relation_type")
        if relation_type not in RELATION_TYPES:
            raise AssuranceError("relation type is invalid")
        basis = relation.get("basis")
        if basis not in {"declared", "static_observed"}:
            raise AssuranceError("relation basis is invalid")
        target_ref = _text(relation.get("target_ref"), "relation target_ref")
        evidence_refs = _unique_strings(relation.get("evidence_refs"), "relation evidence_refs")
        paths = [item["path"] for item in changed_paths if _matches(item["path"], pattern)]
        if not paths:
            continue
        matched_paths.update(paths)
        joined_relation = {
            "relation_id": relation_id,
            "relation_type": relation_type,
            "target_ref": target_ref,
            "changed_paths": paths,
            "basis": basis,
            "evidence_refs": evidence_refs,
        }
        if relation_type == "test":
            classification = relation.get("required_classification")
            if classification not in CLASSIFICATIONS:
                raise AssuranceError("test relation required_classification is invalid")
            joined_relation["required_classification"] = classification
        joined.append(joined_relation)

    hypotheses = draft["impact_hypotheses"]
    referenced_relations = {
        relation_ref for hypothesis in hypotheses for relation_ref in hypothesis["relation_refs"]
    }
    unknown_relations = sorted(referenced_relations - relation_ids)
    if unknown_relations:
        raise AssuranceError(f"impact hypothesis has unknown relation: {unknown_relations}")

    exclusions = copy.deepcopy(restore_point.get("exclusions", []))
    for item in relation_catalog.get("excluded", []):
        if not isinstance(item, dict):
            raise AssuranceError("excluded relation area must be an object")
        exclusions.append(
            {"area": _text(item.get("area"), "excluded area"), "basis": "unobserved", "reason": _text(item.get("reason"), "excluded reason")}
        )
    unique_exclusions = {item["area"]: item for item in exclusions}

    unobserved = []
    for item in relation_catalog.get("unobserved", []):
        if not isinstance(item, dict):
            raise AssuranceError("unobserved relation area must be an object")
        unobserved.append(
            {"area": _text(item.get("area"), "unobserved area"), "basis": "unobserved", "reason": _text(item.get("reason"), "unobserved reason")}
        )
    for path in sorted({item["path"] for item in changed_paths} - matched_paths):
        unobserved.append(
            {"area": f"changed_path:{path}", "basis": "unobserved", "reason": "no declared relation matched this changed path"}
        )
    protected_changes = [
        item["path"]
        for item in changed_paths
        if any(_matches(item["path"], pattern) for pattern in contract["protected_targets"])
    ]
    result = {
        "impact_version": "1.0",
        "contract_id": contract["contract_id"],
        "contract_fingerprint": contract["fingerprint"],
        "restore_point_ref": restore_point["restore_point_id"],
        "observed_at": _text(observed_at, "observed_at"),
        "analysis_scope": "actual tracked Git diff joined to declared relations",
        "changed_paths": changed_paths,
        "relations": sorted(joined, key=lambda item: item["relation_id"]),
        "protected_target_changes": sorted(protected_changes),
        "exclusions": [unique_exclusions[key] for key in sorted(unique_exclusions)],
        "unobserved": sorted(unobserved, key=lambda item: item["area"]),
        "claims_complete_dependency_analysis": False,
    }
    result["fingerprint"] = fingerprint(result)
    return result


def build_test_design(contract: dict, impact: dict, requirement_catalog: list[dict]) -> dict:
    contract, draft = _validate_contract(contract)
    requirements = _unique_records(requirement_catalog, "criterion_id", "requirement_catalog", allow_empty=False)
    required_by_id = {item["criterion_id"]: item for item in requirements}
    criterion_ids = set(contract["gate_criteria"])
    unknown = sorted(set(required_by_id) - criterion_ids)
    missing = sorted(criterion_ids - set(required_by_id))
    if unknown or missing:
        raise AssuranceError(f"requirement catalog criterion mismatch; missing={missing}, unknown={unknown}")
    tests = {item["test_id"]: copy.deepcopy(item) for item in draft["tests"]}
    criteria = {item["criterion_id"]: item for item in draft["criteria"]}
    mappings = []
    for mapping in draft["mappings"]:
        criterion_id = mapping["criterion_id"]
        requirement = required_by_id[criterion_id]
        expected_tests = _unique_strings(requirement.get("test_ids"), "requirement test_ids")
        if set(expected_tests) != set(mapping["test_ids"]):
            raise AssuranceError(f"contract mapping differs from requirement catalog for {criterion_id}")
        required_viewpoints = _unique_strings(requirement.get("required_viewpoints"), "required_viewpoints")
        selected_viewpoints = list(mapping["viewpoints"])
        mappings.append(
            {
                "criterion_id": criterion_id,
                "block_level": criteria[criterion_id]["block_level"],
                "tests": [tests[test_id] for test_id in mapping["test_ids"]],
                "selected_viewpoints": selected_viewpoints,
                "required_viewpoints": required_viewpoints,
                "omitted_viewpoints": [item for item in required_viewpoints if item not in selected_viewpoints],
                "reason": mapping["reason"],
            }
        )
    design = {
        "design_version": "1.0",
        "contract_id": contract["contract_id"],
        "contract_fingerprint": contract["fingerprint"],
        "impact_fingerprint": impact.get("fingerprint"),
        "selected_tests": [copy.deepcopy(item) for item in draft["tests"]],
        "mappings": mappings,
    }
    design["fingerprint"] = fingerprint(design)
    return design


def record_test_baseline(
    contract: dict,
    selection: list[dict],
    receipts: list[dict],
    observed_at: str,
) -> dict:
    contract, draft = _validate_contract(contract)
    selected = _unique_records(selection, "test_id", "test selection", allow_empty=False)
    authoritative = {item["test_id"]: item for item in draft["tests"]}
    if {item["test_id"] for item in selected} != set(authoritative):
        raise AssuranceError("test selection must match the exact contract test selection")
    for item in selected:
        if item != authoritative[item["test_id"]]:
            raise AssuranceError("test selection differs from the contract assurance draft")
    records = _unique_records(receipts, "test_id", "test receipts", allow_empty=False)
    if {item["test_id"] for item in records} != set(authoritative):
        raise AssuranceError("receipts must cover the exact test selection")
    validated = []
    for receipt in records:
        test = authoritative[receipt["test_id"]]
        for key in ("classification", "selection_scope"):
            if receipt.get(key) != test[key]:
                raise AssuranceError(f"receipt {key} differs from contract test selection")
        if receipt.get("validation_command") != test["command"]:
            raise AssuranceError("receipt validation command differs from contract test selection")
        if receipt.get("code_refs") != test["code_refs"]:
            raise AssuranceError("receipt code_refs differ from contract test selection")
        if receipt.get("command_fingerprint") != fingerprint({"command": test["command"]}):
            raise AssuranceError("receipt command fingerprint is invalid")
        _text(receipt.get("criterion_id"), "receipt criterion_id")
        if receipt["criterion_id"] not in contract["gate_criteria"]:
            raise AssuranceError("receipt has an unknown contract criterion")
        _validate_hash(receipt.get("environment_fingerprint"), "receipt environment_fingerprint")
        if receipt.get("contract_fingerprint") != contract["fingerprint"]:
            raise AssuranceError("receipt contract fingerprint is stale")
        _validate_hash(receipt.get("start_patch_hash"), "receipt start_patch_hash")
        _validate_hash(receipt.get("target_patch_hash"), "receipt target_patch_hash")
        result = receipt.get("result")
        basis = receipt.get("basis")
        if result not in RESULTS or basis not in BASES:
            raise AssuranceError("receipt result or basis is invalid")
        evidence_refs = _unique_strings(receipt.get("evidence_refs"), "receipt evidence_refs")
        conflict_refs = _unique_strings(receipt.get("conflict_refs"), "receipt conflict_refs")
        if result in {"missing", "not_run"}:
            if basis != "unobserved" or evidence_refs:
                raise AssuranceError("missing or not_run receipt must be unobserved without Evidence")
        elif basis == "observed" and not evidence_refs:
            raise AssuranceError("observed receipt lacks Evidence")
        elif result in {"pass", "fail"} and basis != "observed":
            raise AssuranceError("test pass or fail must be observed")
        validated.append(copy.deepcopy(receipt))
    validated.sort(key=lambda item: item["test_id"])
    run = {
        "test_run_version": "1.0",
        "contract_id": contract["contract_id"],
        "contract_fingerprint": contract["fingerprint"],
        "task_id": contract["task"]["task_id"],
        "observed_at": _text(observed_at, "observed_at"),
        "selection_fingerprint": fingerprint(selected),
        "receipts": validated,
        "evidence_refs": sorted({ref for item in validated for ref in item["evidence_refs"]}),
    }
    run["fingerprint"] = fingerprint(run)
    return run


def compare_test_runs(before: dict, after: dict) -> dict:
    if not isinstance(before, dict) or not isinstance(after, dict):
        raise AssuranceError("test runs must be objects")
    before_receipts = {item["test_id"]: item for item in _unique_records(before.get("receipts"), "test_id", "before receipts")}
    after_receipts = {item["test_id"]: item for item in _unique_records(after.get("receipts"), "test_id", "after receipts")}
    comparisons = []
    for test_id in sorted(set(before_receipts) | set(after_receipts)):
        left = before_receipts.get(test_id)
        right = after_receipts.get(test_id)
        if left is None:
            status, criterion, classification, refs = "missing_before", right.get("criterion_id"), right.get("classification"), right.get("evidence_refs", [])
        elif right is None:
            status, criterion, classification, refs = "missing_after", left.get("criterion_id"), left.get("classification"), left.get("evidence_refs", [])
        else:
            criterion = right.get("criterion_id")
            classification = right.get("classification")
            refs = sorted(set(left.get("evidence_refs", [])) | set(right.get("evidence_refs", [])))
            stale_fields = (
                "criterion_id",
                "classification",
                "validation_command",
                "selection_scope",
                "contract_fingerprint",
                "start_patch_hash",
                "target_patch_hash",
                "code_refs",
            )
            if any(left.get(key) != right.get(key) for key in stale_fields):
                status = "stale"
            elif left.get("command_fingerprint") != right.get("command_fingerprint") or left.get("environment_fingerprint") != right.get("environment_fingerprint"):
                status = "incomparable"
            elif left.get("conflict_refs") or right.get("conflict_refs"):
                status = "contradicted"
            elif left.get("result") == "missing":
                status = "missing_before"
            elif right.get("result") == "missing":
                status = "missing_after"
            elif left.get("result") == "not_run" or right.get("result") == "not_run":
                status = "not_run"
            elif left.get("result") == "inconclusive" or right.get("result") == "inconclusive":
                status = "inconclusive"
            elif right.get("result") == "fail":
                status = "regression"
            elif right.get("result") == "pass" and right.get("basis") == "observed" and left.get("basis") == "observed":
                status = "comparable_pass"
            else:
                status = "incomparable"
        comparisons.append(
            {"test_id": test_id, "criterion_id": criterion, "classification": classification, "status": status, "evidence_refs": refs}
        )
    result = {
        "comparison_version": "1.0",
        "contract_id": after.get("contract_id"),
        "contract_fingerprint": after.get("contract_fingerprint"),
        "before_ref": before.get("fingerprint"),
        "after_ref": after.get("fingerprint"),
        "comparisons": comparisons,
    }
    result["fingerprint"] = fingerprint(result)
    return result


def detect_test_gaps(contract: dict, impact: dict, design: dict, comparison: dict) -> dict:
    contract, draft = _validate_contract(contract)
    criterion_levels = {item["criterion_id"]: item["block_level"] for item in draft["criteria"]}
    selected = {item["test_id"]: item for item in design.get("selected_tests", [])}
    mappings = {item["criterion_id"]: item for item in design.get("mappings", [])}
    comparisons = {item["test_id"]: item for item in comparison.get("comparisons", [])}
    gaps = []

    def add(kind: str, required: bool, reason: str, *, criterion_id: str | None = None, relation_id: str | None = None, test_id: str | None = None) -> None:
        identity = {"kind": kind, "criterion_id": criterion_id, "relation_id": relation_id, "test_id": test_id, "reason": reason}
        gaps.append(
            {
                "gap_id": "gap:" + fingerprint(identity).removeprefix(HASH_PREFIX),
                "kind": kind,
                "required": required,
                **({"criterion_id": criterion_id} if criterion_id else {}),
                **({"relation_id": relation_id} if relation_id else {}),
                **({"test_id": test_id} if test_id else {}),
                "reason": reason,
            }
        )

    for criterion_id in contract["gate_criteria"]:
        required = criterion_levels[criterion_id] == "hard"
        mapping = mappings.get(criterion_id)
        tests = [] if mapping is None else mapping.get("tests", [])
        if not tests:
            add("no_adequate_test", required, "Contract criterion has no selected test", criterion_id=criterion_id)
            continue
        if not any(comparisons.get(item["test_id"], {}).get("status") == "comparable_pass" for item in tests):
            add("no_adequate_test", required, "Contract criterion lacks observed comparable test Evidence", criterion_id=criterion_id)
        for viewpoint in mapping.get("omitted_viewpoints", []):
            add("missing_viewpoint", required, f"Required {viewpoint} coverage is omitted", criterion_id=criterion_id)

    for relation in impact.get("relations", []):
        if relation.get("relation_type") != "test":
            continue
        test_id = relation.get("target_ref")
        selected_test = selected.get(test_id)
        required_classification = relation.get("required_classification")
        if selected_test is None:
            add("no_adequate_test", True, "Impacted test relation has no selected test", relation_id=relation.get("relation_id"), test_id=test_id)
        elif selected_test.get("classification") != required_classification:
            add("wrong_test_classification", True, f"{selected_test.get('classification')} cannot satisfy required {required_classification} coverage", relation_id=relation.get("relation_id"), test_id=test_id)
    unique = {item["gap_id"]: item for item in gaps}
    result = {
        "gap_report_version": "1.0",
        "contract_id": contract["contract_id"],
        "contract_fingerprint": contract["fingerprint"],
        "gaps": [unique[key] for key in sorted(unique)],
    }
    result["fingerprint"] = fingerprint(result)
    return result


def _identity_mismatch(contract: dict, artifact: dict) -> bool:
    return (
        artifact.get("contract_id") is not None
        and artifact.get("contract_id") != contract["contract_id"]
        or artifact.get("contract_fingerprint") is not None
        and artifact.get("contract_fingerprint") != contract["fingerprint"]
    )


def _override_record(contract: dict, override: dict | None, decision: str) -> dict:
    if override is None:
        return {"status": "not_requested"}
    required_text = ("approved_by", "approval_ref", "reason", "residual_risk")
    scope = override.get("decision_scope") if isinstance(override, dict) else None
    exact = (
        isinstance(override, dict)
        and override.get("decision_source") == "explicit_product_approval"
        and isinstance(scope, dict)
        and scope.get("contract_id") == contract["contract_id"]
        and scope.get("contract_fingerprint") == contract["fingerprint"]
        and scope.get("decision") == "soft_block_override"
        and all(isinstance(override.get(key), str) and override[key].strip() for key in required_text)
    )
    accepted = decision == "soft_block" and exact
    return {
        "status": "accepted" if accepted else "rejected",
        "decision_source": override.get("decision_source") if isinstance(override, dict) else None,
        "decision_scope": copy.deepcopy(scope),
        "approved_by": override.get("approved_by") if isinstance(override, dict) else None,
        "approval_ref": override.get("approval_ref") if isinstance(override, dict) else None,
        "reason": override.get("reason") if isinstance(override, dict) else None,
        "residual_risk": override.get("residual_risk") if isinstance(override, dict) else None,
    }


def evaluate_regression_gate(
    contract: dict,
    impact: dict,
    design: dict,
    comparison: dict,
    gaps: dict,
    override: dict | None = None,
) -> dict:
    contract, draft = _validate_contract(contract)
    hard_reasons = []
    soft_reasons = []
    for artifact_name, artifact in (("impact", impact), ("test design", design), ("comparison", comparison), ("gap report", gaps)):
        if _identity_mismatch(contract, artifact):
            hard_reasons.append(f"{artifact_name} identity/reference mismatch")
    if contract.get("gate_status") == "hard_block":
        hard_reasons.append("Task Execution Contract is already hard-blocked")
    if impact.get("protected_target_changes"):
        hard_reasons.append("protected target changed")
    criterion_levels = {item["criterion_id"]: item["block_level"] for item in draft["criteria"]}
    for item in comparison.get("comparisons", []):
        if item.get("status") == "comparable_pass":
            continue
        criterion_id = item.get("criterion_id")
        reason = f"{item.get('test_id')} comparison is {item.get('status')}"
        if criterion_levels.get(criterion_id, "hard") == "hard":
            hard_reasons.append(reason)
        else:
            soft_reasons.append(reason)
    for item in gaps.get("gaps", []):
        reason = f"{item.get('kind')}: {item.get('reason')}"
        (hard_reasons if item.get("required") else soft_reasons).append(reason)
    for item in impact.get("unobserved", []):
        soft_reasons.append(f"Unobserved {item.get('area')}: {item.get('reason')}")
    if hard_reasons:
        initial = "hard_block"
    elif soft_reasons:
        initial = "soft_block"
    else:
        initial = "pass"
    override_record = _override_record(contract, override, initial)
    decision = "pass" if override_record["status"] == "accepted" else initial
    result = {
        "gate_version": "1.0",
        "contract_id": contract["contract_id"],
        "contract_fingerprint": contract["fingerprint"],
        "initial_decision": initial,
        "decision": decision,
        "basis": "observed" if initial in {"pass", "hard_block"} else "unobserved",
        "hard_reasons": sorted(set(hard_reasons)),
        "soft_reasons": sorted(set(soft_reasons)),
        "override": override_record,
        "evidence_refs": sorted({ref for item in comparison.get("comparisons", []) for ref in item.get("evidence_refs", [])}),
    }
    result["fingerprint"] = fingerprint(result)
    return result


def _collect_evidence_refs(value: object) -> set[str]:
    found: set[str] = set()
    if isinstance(value, dict):
        for key, item in value.items():
            if key == "evidence_refs":
                found.update(_unique_strings(item, "evidence_refs"))
            else:
                found.update(_collect_evidence_refs(item))
    elif isinstance(value, list):
        for item in value:
            found.update(_collect_evidence_refs(item))
    return found


def build_assurance_packet(
    *,
    contract: dict,
    restore_point: dict,
    restore_verification: dict,
    impact: dict,
    test_design: dict,
    before: dict,
    after: dict,
    comparison: dict,
    gaps: dict,
    gate: dict,
    evidence_refs: list[str],
    observed_at: str,
) -> dict:
    contract, _ = _validate_contract(contract)
    if restore_point.get("task") != _validate_task(contract["task"]):
        raise AssuranceError("packet restore identity mismatch")
    for artifact_name, artifact in (
        ("impact", impact), ("test design", test_design), ("before", before),
        ("after", after), ("comparison", comparison), ("gaps", gaps), ("gate", gate),
    ):
        if _identity_mismatch(contract, artifact):
            raise AssuranceError(f"packet {artifact_name} identity/reference mismatch")
    declared_refs = set(_unique_strings(evidence_refs, "packet evidence_refs"))
    public_restore = _restore_public(restore_point)
    sections = {
        "restore_point": public_restore,
        "restore_verification": copy.deepcopy(restore_verification),
        "impact": copy.deepcopy(impact),
        "test_design": copy.deepcopy(test_design),
        "before": copy.deepcopy(before),
        "after": copy.deepcopy(after),
        "comparison": copy.deepcopy(comparison),
        "gaps": copy.deepcopy(gaps),
        "gate": copy.deepcopy(gate),
    }
    used_refs = _collect_evidence_refs(sections)
    if not used_refs <= declared_refs:
        raise AssuranceError(f"packet Evidence reference closure failed: {sorted(used_refs - declared_refs)}")
    input_payload = {
        "contract_id": contract["contract_id"],
        "contract_fingerprint": contract["fingerprint"],
        "sections": sections,
        "evidence_refs": sorted(declared_refs),
    }
    input_fingerprint = fingerprint(input_payload)
    packet = {
        "packet_version": "1.0",
        "packet_id": "assurance:" + input_fingerprint.removeprefix(HASH_PREFIX),
        "contract_id": contract["contract_id"],
        "contract_fingerprint": contract["fingerprint"],
        "task": copy.deepcopy(contract["task"]),
        "observed_at": _text(observed_at, "observed_at"),
        "input_fingerprint": input_fingerprint,
        **sections,
        "evidence_refs": sorted(declared_refs),
    }
    packet["fingerprint"] = fingerprint(packet)
    return packet
