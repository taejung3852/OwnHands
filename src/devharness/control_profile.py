from __future__ import annotations

import base64
import hashlib
import html
import json
import os
import tempfile
import tomllib
from datetime import datetime
from pathlib import Path


class ControlProfileError(ValueError):
    pass


CONTEXT_TYPES = {"agents_instruction", "hwpx_tool_contract"}
CONTROL_TYPES = {"codex_config", "rule", "hook"}
SUPPORTED_CODEX_VERSION = "0.153.3"
INTERVIEW_DECISIONS = (
    ("failure_impact", ("low", "high"), "low", "The fixture is isolated and locally reversible."),
    ("external_effect", ("none", "write"), "none", "No required external write was observed."),
    ("protected_data", ("none", "sensitive"), "none", "Only sensitive path names, not values, were observed."),
    ("permission_expansion", ("none", "network"), "none", "The supported fixture commands are local."),
    ("validation", ("tests", "manual"), "tests", "A deterministic test command was discovered."),
)


def _canonical(value: object) -> str:
    try:
        return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)
    except (TypeError, ValueError) as error:
        raise ControlProfileError(f"value is not canonical JSON: {error}") from error


def _hash(value: object) -> str:
    payload = value if isinstance(value, bytes) else _canonical(value).encode("utf-8")
    return "sha256:" + hashlib.sha256(payload).hexdigest()


def _source(path: Path, root: Path, source_type: str, observed_at: str) -> dict:
    relative = path.relative_to(root).as_posix()
    evidence_ref = f"evidence:profile:{relative}"
    return {
        "source_id": f"source:{relative}",
        "source_type": source_type,
        "path": relative,
        "content_hash": _hash(path.read_bytes()),
        "scope": "project" if relative == "AGENTS.md" else str(Path(relative).parent),
        "freshness": {"status": "current", "basis": "observed", "checked_at": observed_at},
        "realization": {
            "configured": {"result": "pass", "basis": "observed", "evidence_refs": [evidence_ref]},
            "loaded": {"result": "not_run", "basis": "unobserved", "evidence_refs": []},
            "enforced": {"result": "not_run", "basis": "unobserved", "evidence_refs": []},
        },
    }


def profile_project(root: Path | str, identity: dict, *, observed_at: str) -> dict:
    root = Path(root).resolve()
    if not root.is_dir():
        raise ControlProfileError("project root must be a directory")
    for key in ("project_id", "worktree_id", "environment_ref"):
        if not isinstance(identity.get(key), str) or not identity[key]:
            raise ControlProfileError(f"profile identity is missing {key}")

    structure, unobserved, sensitive = [], [], []
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root).as_posix()
        if path.is_symlink():
            unobserved.append({"path": relative, "basis": "unobserved", "reason": "symbolic links are not followed"})
            continue
        if path.is_file():
            structure.append(relative)
            name = path.name.lower()
            if name in {".env", ".env.local", "credentials.json", "secrets.json"} or name.endswith((".pem", ".key")):
                sensitive.append({"path": relative, "basis": "observed", "value_exposed": False})

    source_specs = {
        "AGENTS.md": "agents_instruction",
        "REQUIREMENTS.md": "project_contract",
        "pyproject.toml": "project_manifest",
        ".codex/config.toml": "codex_config",
        ".codex/hooks.json": "hook",
        "hwpx-tool-contract.json": "hwpx_tool_contract",
        "external-services.json": "external_service_declaration",
    }
    sources = []
    for relative, source_type in source_specs.items():
        path = root / relative
        if path.is_file() and not path.is_symlink():
            sources.append(_source(path, root, source_type, observed_at))
    rules_root = root / ".codex/rules"
    if rules_root.is_dir():
        sources.extend(
            _source(path, root, "rule", observed_at)
            for path in sorted(rules_root.glob("*.rules"))
            if path.is_file() and not path.is_symlink()
        )

    commands = []
    pyproject = root / "pyproject.toml"
    if pyproject.is_file():
        try:
            configured = tomllib.loads(pyproject.read_text(encoding="utf-8"))["tool"]["ownhands"]["commands"]
            commands = [
                {"kind": kind, "command": command, "source_ref": "source:pyproject.toml"}
                for kind, command in sorted(configured.items())
                if isinstance(command, str) and command
            ]
        except (KeyError, tomllib.TOMLDecodeError, UnicodeDecodeError):
            unobserved.append({"path": "pyproject.toml", "basis": "unobserved", "reason": "supported command table could not be read"})

    hwpx = {"basis": "unobserved", "tools": [], "reason": "no supported HWPX tool contract"}
    hwpx_path = root / "hwpx-tool-contract.json"
    if hwpx_path.is_file():
        try:
            document = json.loads(hwpx_path.read_text(encoding="utf-8"))
            tools = [
                {key: item[key] for key in ("name", "input", "output")}
                for item in document["tools"]
                if isinstance(item, dict) and all(isinstance(item.get(key), str) for key in ("name", "input", "output"))
            ]
            hwpx = {"basis": "observed", "tools": tools, "source_ref": "source:hwpx-tool-contract.json"}
        except (KeyError, json.JSONDecodeError, UnicodeDecodeError):
            unobserved.append({"path": "hwpx-tool-contract.json", "basis": "unobserved", "reason": "tool contract is unsupported or malformed"})

    services = []
    services_path = root / "external-services.json"
    if services_path.is_file():
        try:
            document = json.loads(services_path.read_text(encoding="utf-8"))
            services = [
                {key: item[key] for key in ("name", "purpose", "endpoint_host")}
                for item in document["services"]
                if isinstance(item, dict) and all(isinstance(item.get(key), str) for key in ("name", "purpose", "endpoint_host"))
            ]
        except (KeyError, json.JSONDecodeError, UnicodeDecodeError):
            unobserved.append({"path": "external-services.json", "basis": "unobserved", "reason": "service declarations are unsupported or malformed"})

    report = {
        "profile_version": "1.0",
        **{key: identity[key] for key in ("project_id", "worktree_id", "environment_ref")},
        "observed_at": observed_at,
        "structure": structure,
        "commands": commands,
        "sources": sources,
        "sensitive_paths": sensitive,
        "external_services": services,
        "hwpx_tool_contract": hwpx,
        "unobserved": unobserved,
    }
    report["fingerprint"] = _hash(report)
    return report


def run_interview(profile: dict, responses: list[object]) -> dict:
    transcript, decisions, unresolved = [], [], []
    response_index = 0
    for decision_id, choices, recommendation, reason in INTERVIEW_DECISIONS:
        chosen = {item["decision_id"]: item for item in decisions}
        inferred = (
            decision_id == "external_effect" and not profile.get("external_services")
            or decision_id == "protected_data" and not profile.get("sensitive_paths")
            or decision_id == "permission_expansion"
            and chosen.get("external_effect", {}).get("status") in {"answered", "recommended"}
            and chosen["external_effect"]["value"] == "none"
            or decision_id == "validation"
            and any(item.get("kind") == "test" for item in profile.get("commands", []))
        )
        if inferred:
            decisions.append({"decision_id": decision_id, "status": "recommended", "value": recommendation, "basis": "observed"})
            continue
        response = responses[response_index] if response_index < len(responses) else None
        response_index += 1
        question = {
            "decision_ids": [decision_id],
            "prompt": f"Choose the {decision_id.replace('_', ' ')} boundary.",
            "choices": list(choices),
            "recommendation": recommendation,
            "reason": reason,
        }
        if response in choices:
            status, value = "answered", response
        elif response == "decline":
            status, value = "declined", recommendation
            unresolved.append(decision_id)
        elif response is None or response == "":
            status, value = "silent", recommendation
            unresolved.append(decision_id)
        else:
            status, value = "ambiguous", recommendation
            unresolved.append(decision_id)
        decisions.append({"decision_id": decision_id, "status": status, "value": value, "basis": "synthetic_fixture"})
        transcript.append({"question": question, "response": response, "decision": decisions[-1]})
    result = {
        "interview_version": "1.0",
        "profile_ref": profile["fingerprint"],
        "transcript": transcript,
        "decisions": decisions,
        "unresolved_decisions": unresolved,
        "question_count": len(transcript),
        "approval_granted": False,
        "evidence_basis": "synthetic_fixture",
    }
    result["decision_hash"] = _hash(result)
    return result


def build_baseline(
    profile: dict,
    interview: dict,
    *,
    version: int,
    predecessor_ref: str | None,
    event_refs: list[str],
    evidence_refs: list[str],
) -> dict:
    if not isinstance(version, int) or isinstance(version, bool) or version < 1:
        raise ControlProfileError("baseline version must be a positive integer")
    if version > 1 and not predecessor_ref:
        raise ControlProfileError("a predecessor reference is required for a replacement baseline")
    if version == 1 and predecessor_ref is not None:
        raise ControlProfileError("the first baseline cannot have a predecessor")
    if interview.get("profile_ref") != profile.get("fingerprint"):
        raise ControlProfileError("interview profile reference is stale")
    project_id = profile["project_id"]
    baseline = {
        "baseline_version": "1.0",
        "baseline_id": f"baseline:{project_id}:v{version}",
        "version": version,
        "predecessor_ref": predecessor_ref,
        "project_id": project_id,
        "worktree_id": profile["worktree_id"],
        "environment_ref": profile["environment_ref"],
        "profile_ref": profile["fingerprint"],
        "interview_ref": interview["decision_hash"],
        "source_fingerprints": {item["source_id"]: item["content_hash"] for item in profile["sources"]},
        "sources": profile["sources"],
        "commands": profile["commands"],
        "sensitive_paths": profile["sensitive_paths"],
        "external_services": profile["external_services"],
        "hwpx_tool_contract": profile["hwpx_tool_contract"],
        "unobserved": profile["unobserved"],
        "event_refs": list(event_refs),
        "evidence_refs": list(evidence_refs),
    }
    baseline["fingerprint"] = _hash(baseline)
    return baseline


def assess_baseline_freshness(baseline: dict, profile: dict, trigger: str, available_refs: set[str]) -> dict:
    for key in ("project_id", "worktree_id", "environment_ref"):
        if baseline.get(key) != profile.get(key):
            raise ControlProfileError("baseline and profile identity do not match")
    if not set(baseline.get("event_refs", []) + baseline.get("evidence_refs", [])) <= available_refs:
        raise ControlProfileError("baseline reference closure failed")
    if trigger == "unsupported_change":
        return {"status": "unobserved", "basis": "unobserved", "reason": "the change trigger is unsupported"}
    if trigger == "manual_refresh":
        return {"status": "stale", "basis": "observed", "reason": "manual refresh was requested"}
    stale = baseline.get("profile_ref") != profile.get("fingerprint")
    return {"status": "stale" if stale else "fresh", "basis": "observed", "reason": "profile fingerprint changed" if stale else "profile fingerprint is unchanged"}


def _overlap(left: str, right: str) -> bool:
    left_root = left.removesuffix("/**").rstrip("/")
    right_root = right.removesuffix("/**").rstrip("/")
    return left_root == right_root or left_root.startswith(right_root + "/") or right_root.startswith(left_root + "/")


def build_execution_contract(baseline: dict, overlay: dict, approvals: list[dict], *, now: str) -> dict:
    if overlay.get("baseline_ref") != baseline.get("baseline_id") or overlay.get("baseline_fingerprint") != baseline.get("fingerprint"):
        raise ControlProfileError("overlay baseline reference is stale")
    task = overlay.get("task", {})
    for key in ("project_id", "worktree_id", "environment_ref"):
        if task.get(key) != baseline.get(key):
            raise ControlProfileError("task and baseline identity do not match")
    if task.get("mode") not in {"managed", "imported"}:
        raise ControlProfileError("task mode is invalid")
    if any(_overlap(writable, protected) for writable in overlay.get("writable_paths", []) for protected in overlay.get("protected_targets", [])):
        raise ControlProfileError("writable scope overlaps a protected target")
    source_types = {item["source_id"]: item["source_type"] for item in baseline["sources"]}
    instructions = overlay.get("instruction_overlay", {}).get("source_refs", [])
    controls = overlay.get("control_overlay", {}).get("source_refs", [])
    if any(source_types.get(ref) not in CONTEXT_TYPES for ref in instructions):
        raise ControlProfileError("instruction_overlay contains a non-Context source")
    if any(source_types.get(ref) not in CONTROL_TYPES for ref in controls):
        raise ControlProfileError("control_overlay contains a non-Control source")

    active_permissions, hard_block = [], False
    now_value = datetime.fromisoformat(now.replace("Z", "+00:00"))
    for expansion in overlay.get("permission_expansions", []):
        for key in ("permission", "scope", "reason", "duration", "approval_ref"):
            if not isinstance(expansion.get(key), str) or not expansion[key]:
                raise ControlProfileError(f"permission expansion requires {key}")
        if expansion["duration"] != "task":
            raise ControlProfileError("permission expansion duration must be task")
        approval = next((item for item in approvals if item.get("approval_id") == expansion["approval_ref"]), None)
        approved = False
        if approval:
            try:
                expiry = datetime.fromisoformat(approval["expires_at"].replace("Z", "+00:00"))
            except (KeyError, AttributeError, ValueError):
                expiry = now_value
            approved = all((
                approval.get("decision") == "approved",
                approval.get("decision_source") == "explicit_product_approval",
                approval.get("task_id") == task.get("task_id"),
                approval.get("permission") == expansion["permission"],
                approval.get("scope") == expansion["scope"],
                expiry > now_value,
            ))
        active_permissions.append({**expansion, "active": approved, "basis": "observed" if approved else "unobserved"})
        hard_block = hard_block or not approved

    contract = {
        "contract_version": "1.0",
        "contract_id": f"contract:{task['task_id']}",
        "task": task,
        "baseline_ref": baseline["baseline_id"],
        "baseline_fingerprint": baseline["fingerprint"],
        "overlay_ref": overlay["overlay_id"],
        "instruction_overlay": overlay["instruction_overlay"],
        "control_overlay": overlay["control_overlay"],
        "writable_paths": overlay["writable_paths"],
        "protected_targets": overlay["protected_targets"],
        "permissions": active_permissions,
        "approval_triggers": overlay["approval_triggers"],
        "validation_criteria": overlay["validation_criteria"],
        "gate_criteria": overlay["gate_criteria"],
        "gate_status": "hard_block" if hard_block else "ready_for_preview",
        "unobserved": overlay["unobserved_paths"],
        "event_refs": baseline["event_refs"],
        "evidence_refs": baseline["evidence_refs"],
        "realization": {
            "configured": {"result": "not_run", "basis": "unobserved"},
            "loaded": {"result": "not_run", "basis": "unobserved"},
            "enforced": {"result": "not_run", "basis": "unobserved"},
        },
    }
    contract["fingerprint"] = _hash(contract)
    return contract


def _artifact(path: str, artifact_type: str, content: str, existing: dict[str, str]) -> dict:
    before = existing.get(path)
    return {
        "path": path,
        "artifact_type": artifact_type,
        "source_class": "context" if artifact_type == "agents" else "control",
        "content": content,
        "before_hash": _hash(before.encode("utf-8")) if before is not None else None,
        "after_hash": _hash(content.encode("utf-8")),
        "status": "unchanged" if before == content else "changed",
    }


def compile_control_profile(contract: dict, existing: dict[str, str], *, codex_version: str = SUPPORTED_CODEX_VERSION) -> dict:
    active = [item for item in contract["permissions"] if item["active"]]
    sandbox = {"mode": "workspace-write", "writable_paths": contract["writable_paths"], "protected_targets": contract["protected_targets"]}
    approval = {"policy": "on-request", "triggers": contract["approval_triggers"], "active_expansions": active}
    contents = (
        (".codex/config.toml", "config", 'sandbox_mode = "workspace-write"\napproval_policy = "on-request"\n'),
        ("AGENTS.md", "agents", "# ownhands task overlay\n\nFollow the Task Execution Contract and run its validation criteria.\n"),
        (".codex/rules/ownhands.rules", "rules", 'prefix_rule(pattern=["python", "-m", "unittest"], decision="allow")\n'),
        (".codex/hooks.json", "hooks", _canonical({"hooks": [{"event": "after_task", "command": contract["validation_criteria"][0]}]}) + "\n"),
        (".ownhands/sandbox.json", "sandbox", _canonical(sandbox) + "\n"),
        (".ownhands/approval.json", "approval", _canonical(approval) + "\n"),
    )
    artifacts = [_artifact(path, artifact_type, content, existing) for path, artifact_type, content in contents]
    findings = []
    existing_config = existing.get(".codex/config.toml")
    if existing_config is not None and existing_config != contents[0][2]:
        findings.append({"code": "precedence_conflict", "severity": "hard", "basis": "observed", "location": ".codex/config.toml"})
    hooks = existing.get(".codex/hooks.json")
    if hooks:
        try:
            events = [item.get("event") for item in json.loads(hooks).get("hooks", [])]
            if len(events) != len(set(events)):
                findings.append({"code": "duplicate_hook", "severity": "hard", "basis": "observed", "location": ".codex/hooks.json"})
        except (AttributeError, json.JSONDecodeError):
            findings.append({"code": "unknown_hook_format", "severity": "hard", "basis": "unobserved", "location": ".codex/hooks.json"})
    rule_lines = [
        (path, line.strip())
        for path, content in sorted(existing.items())
        if path.startswith(".codex/rules/") and path.endswith(".rules")
        for line in content.splitlines()
        if line.strip()
    ]
    seen_rules: set[str] = set()
    duplicate_rule_path = None
    for path, line in rule_lines:
        if line in seen_rules:
            duplicate_rule_path = path
            break
        seen_rules.add(line)
    if duplicate_rule_path:
        findings.append({"code": "duplicate_rule", "severity": "hard", "basis": "observed", "location": duplicate_rule_path})
    if any(item["scope"] in {"*", "/"} for item in active):
        findings.append({"code": "excessive_permission", "severity": "hard", "basis": "observed", "location": "permissions"})
    if not contract["protected_targets"]:
        findings.append({"code": "missing_protected_target", "severity": "hard", "basis": "observed", "location": "protected_targets"})
    if codex_version != SUPPORTED_CODEX_VERSION:
        findings.append({"code": "unsupported_codex_version", "severity": "hard", "basis": "unobserved", "location": "environment"})
    compiler = {
        "compiler_version": "1.0",
        "contract_ref": contract["contract_id"],
        "contract_fingerprint": contract["fingerprint"],
        "codex_version": codex_version,
        "dry_run": True,
        "artifacts": artifacts,
        "findings": findings,
        "apply_ready": contract["gate_status"] == "ready_for_preview" and not findings,
        "restore": {"status": "unavailable", "journal_path": None},
        "realization": {
            "configured": {"result": "not_run", "basis": "unobserved"},
            "loaded": {"result": "not_run", "basis": "unobserved"},
            "enforced": {"result": "not_run", "basis": "unobserved"},
        },
    }
    compiler["diff_hash"] = _hash([{key: item[key] for key in ("path", "before_hash", "after_hash", "status")} for item in artifacts])
    return compiler


def _atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}-", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


JOURNAL_NAME = ".ownhands-rollback-journal.json"


def _disposable_root(root: Path | str) -> Path:
    resolved = Path(root).resolve()
    marker = resolved / ".ownhands-disposable"
    if not marker.is_file() or marker.is_symlink():
        raise ControlProfileError("apply is restricted to a marked disposable tree")
    return resolved


def _contained_target(root: Path, relative_path: object) -> Path:
    if not isinstance(relative_path, str) or not relative_path or relative_path == "." or "\\" in relative_path:
        raise ControlProfileError("artifact path must be contained under the disposable root")
    raw_parts = relative_path.split("/")
    candidate = Path(relative_path)
    if candidate.is_absolute() or any(part in {"", ".", ".."} for part in raw_parts):
        raise ControlProfileError("artifact path must be contained under the disposable root")
    target = root.joinpath(*candidate.parts)
    current = root
    for index, part in enumerate(candidate.parts):
        current = current / part
        if current.is_symlink():
            raise ControlProfileError("artifact path contains a symlink")
        if index < len(candidate.parts) - 1 and current.exists() and not current.is_dir():
            raise ControlProfileError("artifact parent must be a directory")
    if not target.resolve(strict=False).is_relative_to(root):
        raise ControlProfileError("artifact path must be contained under the disposable root")
    return target


def apply_candidate(compiled: dict, root: Path | str, approval: dict) -> dict:
    root = _disposable_root(root)
    if approval.get("decision") != "approved" or approval.get("decision_source") != "explicit_product_approval" or approval.get("contract_ref") != compiled.get("contract_ref"):
        raise ControlProfileError("apply requires explicit product approval for this contract")
    if not compiled.get("apply_ready"):
        raise ControlProfileError("compiler findings block apply")
    journal_path = _contained_target(root, JOURNAL_NAME)
    if journal_path.exists() or journal_path.is_symlink():
        raise ControlProfileError("an apply journal already exists")
    entries = []
    targets: set[Path] = set()
    for artifact in compiled["artifacts"]:
        path = _contained_target(root, artifact.get("path"))
        if path == journal_path:
            raise ControlProfileError("artifact target conflicts with the apply journal")
        if path in targets:
            raise ControlProfileError("artifact targets must be unique")
        targets.add(path)
        if path.exists() and not path.is_file():
            raise ControlProfileError("artifact target must be a regular file")
        if not isinstance(artifact.get("content"), str) or _hash(artifact["content"].encode("utf-8")) != artifact.get("after_hash"):
            raise ControlProfileError("artifact content hash is invalid")
        before = path.read_bytes() if path.exists() else None
        actual_hash = _hash(before) if before is not None else None
        if actual_hash != artifact["before_hash"]:
            raise ControlProfileError(f"stale diff for {artifact['path']}")
        entries.append({
            "path": artifact["path"],
            "before_hash": artifact["before_hash"],
            "after_hash": artifact["after_hash"],
            "before_content": base64.b64encode(before).decode("ascii") if before is not None else None,
        })
    journal = {"journal_version": "1.0", "contract_ref": compiled["contract_ref"], "diff_hash": compiled["diff_hash"], "status": "prepared", "entries": entries}
    _atomic_write(journal_path, json.dumps(journal, ensure_ascii=False, indent=2) + "\n")
    for artifact in compiled["artifacts"]:
        path = _contained_target(root, artifact["path"])
        _atomic_write(path, artifact["content"])
    verified = all(_hash((root / item["path"]).read_bytes()) == item["after_hash"] for item in entries)
    if not verified:
        raise ControlProfileError("applied artifact hash verification failed")
    journal["status"] = "applied"
    _atomic_write(journal_path, json.dumps(journal, ensure_ascii=False, indent=2) + "\n")
    return {"journal_path": str(journal_path), "diff_hash": compiled["diff_hash"], "verified": True}


def rollback_candidate(root: Path | str, journal_path: Path | str) -> dict:
    root = _disposable_root(root)
    expected_journal = root / JOURNAL_NAME
    supplied_journal = Path(journal_path)
    if not supplied_journal.is_absolute() or supplied_journal != expected_journal:
        raise ControlProfileError("rollback requires the expected journal")
    journal_path = _contained_target(root, JOURNAL_NAME)
    if journal_path.is_symlink() or not journal_path.is_file():
        raise ControlProfileError("rollback requires the expected journal")
    journal = json.loads(journal_path.read_text(encoding="utf-8"))
    if journal.get("status") != "applied":
        raise ControlProfileError("journal is not in applied state")
    restorations = []
    targets: set[Path] = set()
    for entry in journal["entries"]:
        path = _contained_target(root, entry.get("path"))
        if path in targets:
            raise ControlProfileError("rollback targets must be unique")
        targets.add(path)
        if not path.is_file() or _hash(path.read_bytes()) != entry.get("after_hash"):
            raise ControlProfileError(f"rollback target changed after apply: {entry['path']}")
        before_content = entry.get("before_content")
        if before_content is None:
            restored = None
        else:
            try:
                restored = base64.b64decode(before_content, validate=True)
            except (TypeError, ValueError) as error:
                raise ControlProfileError("rollback journal content is invalid") from error
            if _hash(restored) != entry.get("before_hash"):
                raise ControlProfileError("rollback journal before hash is invalid")
            try:
                restored = restored.decode("utf-8")
            except UnicodeDecodeError as error:
                raise ControlProfileError("rollback journal content is not UTF-8") from error
        restorations.append((entry, path, restored))
    for entry, path, restored in restorations:
        path = _contained_target(root, entry["path"])
        if restored is None:
            path.unlink()
        else:
            _atomic_write(path, restored)
    verified = all(
        (not (root / item["path"]).exists() if item["before_hash"] is None else _hash((root / item["path"]).read_bytes()) == item["before_hash"])
        for item in journal["entries"]
    )
    if not verified:
        raise ControlProfileError("rollback verification failed")
    journal["status"] = "rolled_back"
    _atomic_write(journal_path, json.dumps(journal, ensure_ascii=False, indent=2) + "\n")
    return {"journal_path": str(journal_path), "verified": True, "status": "rolled_back"}


def render_control_preview(contract: dict, compiled: dict, evidence_index: dict[str, str]) -> str:
    if compiled.get("contract_ref") != contract.get("contract_id") or compiled.get("contract_fingerprint") != contract.get("fingerprint"):
        raise ControlProfileError("compiler diff is stale for the contract")
    expected_diff = _hash([{key: item[key] for key in ("path", "before_hash", "after_hash", "status")} for item in compiled["artifacts"]])
    if compiled.get("diff_hash") != expected_diff:
        raise ControlProfileError("compiler diff hash is stale")
    refs = contract.get("event_refs", []) + contract.get("evidence_refs", [])
    if not set(refs) <= set(evidence_index):
        raise ControlProfileError("preview evidence drill-down is unresolved")
    artifact_rows = "".join(
        f"<tr><td>{html.escape(item['path'])}</td><td>{html.escape(item['artifact_type'])}</td><td>{html.escape(item['status'].title())}</td></tr>"
        for item in compiled["artifacts"]
    )
    findings = "".join(f"<li><strong>{html.escape(item['severity'].title())}:</strong> {html.escape(item['code'])} at {html.escape(item['location'])}</li>" for item in compiled["findings"]) or "<li>None observed</li>"
    links = "".join(f'<li id="{html.escape(ref)}"><a href="{html.escape(evidence_index[ref], quote=True)}">{html.escape(ref)}</a></li>' for ref in refs)
    protected = ", ".join(html.escape(path) for path in contract["protected_targets"])
    unobserved = "".join(f"<li>{html.escape(item['path'])}: {html.escape(item['reason'])}</li>" for item in contract["unobserved"]) or "<li>None recorded</li>"
    restore = "Restore unavailable" if compiled["restore"]["journal_path"] is None else f"Restore: {html.escape(compiled['restore']['journal_path'])}"
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>ownhands M2 Control Preview</title>
<style>body{{max-width:72rem;margin:2rem auto;padding:0 1rem;font:16px/1.5 system-ui}}table{{border-collapse:collapse;width:100%}}th,td{{border:1px solid;padding:.5rem;text-align:left}}.boundary{{border-left:.35rem solid;padding:.75rem}}</style></head>
<body><a href="#main">Skip to review</a><main id="main" tabindex="-1">
<h1>ownhands M2 Control Preview</h1><p>This is a local M2 review artifact, not the M5 production UI.</p>
<h2>Task contract</h2><p><strong>ID:</strong> {html.escape(contract['contract_id'])}</p><p><strong>Goal:</strong> {html.escape(contract['task']['goal'])}</p>
<svg role="img" aria-labelledby="boundary-title boundary-desc" viewBox="0 0 600 90"><title id="boundary-title">Permission boundary</title><desc id="boundary-desc">Writable, protected, and unobserved boundaries are labeled with text.</desc><text x="10" y="25">Writable</text><text x="210" y="25">Protected</text><text x="410" y="25">Unobserved</text></svg>
<p><strong>Protected:</strong> {protected}</p><h2>Before and after</h2><table><thead><tr><th>File</th><th>Class</th><th>Status</th></tr></thead><tbody>{artifact_rows}</tbody></table>
<h2>Conflicts</h2><ul>{findings}</ul><h2>Unobserved</h2><ul>{unobserved}</ul>
<h2>Restore path</h2><p>{restore}</p><h2>Evidence drill-down</h2><ul>{links}</ul>
<p><strong>Configured:</strong> candidate only · <strong>Loaded:</strong> Unobserved · <strong>Enforced:</strong> Unobserved</p>
</main></body></html>"""
