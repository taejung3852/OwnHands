#!/usr/bin/env bash

set -euo pipefail

repo_root="$(git rev-parse --show-toplevel)"
matrix="$repo_root/docs/product/guarantee-matrix.v1.json"
matrix_schema="$repo_root/docs/product/guarantee-matrix.schema.json"
control_schema="$repo_root/docs/product/control-validation.schema.json"
control_example="$repo_root/docs/product/control-validation.example.json"
report_schema="$repo_root/docs/product/task-guarantee-report.schema.json"
report_example="$repo_root/docs/product/task-guarantee-report.example.json"
fixtures="$repo_root/docs/spikes/guarantee-matrix-fixtures.json"

schema_fixture_dir="$(mktemp -d)"
empty_claim_results_fixture="$schema_fixture_dir/empty-claim-results.json"
duplicate_claim_result_fixture="$schema_fixture_dir/duplicate-claim-result.json"
distinct_duplicate_claim_id_fixture="$schema_fixture_dir/distinct-duplicate-claim-id.json"
foreign_task_control_fixture="$schema_fixture_dir/foreign-task-control.json"
unrelated_control_fixture="$schema_fixture_dir/unrelated-control.json"
hidden_failed_control_fixture="$schema_fixture_dir/hidden-failed-control.json"
overclaim_report_fixture="$schema_fixture_dir/overclaim-report.json"
empty_residual_risks_fixture="$schema_fixture_dir/empty-residual-risks.json"
duplicate_control_record_fixture="$schema_fixture_dir/duplicate-control-record.json"
evidence_free_report_fixture="$schema_fixture_dir/evidence-free-report.json"
different_control_id_fixture="$schema_fixture_dir/different-control-id.json"
different_control_boundary_fixture="$schema_fixture_dir/different-control-boundary.json"
different_control_check_scope_fixture="$schema_fixture_dir/different-control-check-scope.json"
missing_category_matrix_fixture="$schema_fixture_dir/missing-category-matrix.json"
duplicate_category_matrix_fixture="$schema_fixture_dir/duplicate-category-matrix.json"
cleanup_schema_fixtures() {
  unlink "$empty_claim_results_fixture" "$duplicate_claim_result_fixture" \
    "$distinct_duplicate_claim_id_fixture" "$foreign_task_control_fixture" \
    "$unrelated_control_fixture" "$hidden_failed_control_fixture" \
    "$overclaim_report_fixture" "$empty_residual_risks_fixture" \
    "$duplicate_control_record_fixture" "$evidence_free_report_fixture" \
    "$different_control_id_fixture" "$different_control_boundary_fixture" \
    "$different_control_check_scope_fixture" "$missing_category_matrix_fixture" \
    "$duplicate_category_matrix_fixture" 2>/dev/null || true
  rmdir "$schema_fixture_dir" 2>/dev/null || true
}
trap cleanup_schema_fixtures EXIT

validate_report_schema() {
  npm_config_offline=true npx --yes --package ajv-cli@5.0.0 --package ajv-formats@3.0.1 \
    ajv validate --spec=draft2020 --strict-types=true --strict-tuples=true \
    -c ajv-formats -s "$report_schema" -d "$1"
}

validate_matrix_schema() {
  npm_config_offline=true npx --yes --package ajv-cli@5.0.0 --package ajv-formats@3.0.1 \
    ajv validate --spec=draft2020 --strict-types=true --strict-tuples=true \
    -c ajv-formats -s "$matrix_schema" -d "$1"
}

validate_control_schema() {
  npm_config_offline=true npx --yes --package ajv-cli@5.0.0 --package ajv-formats@3.0.1 \
    ajv validate --spec=draft2020 --strict-types=true --strict-tuples=true \
    -c ajv-formats -s "$control_schema" -d "$1"
}

expect_report_schema_rejection() {
  local output status
  set +e
  output="$(validate_report_schema "$1" 2>&1)"
  status=$?
  set -e
  if [ "$status" -ne 1 ] || ! rg -q 'invalid' <<<"$output"; then
    printf '%s\n' "$output" >&2
    return 1
  fi
}

expect_matrix_schema_rejection() {
  local output status
  set +e
  output="$(validate_matrix_schema "$1" 2>&1)"
  status=$?
  set -e
  if [ "$status" -ne 1 ] || ! rg -q 'invalid' <<<"$output"; then
    printf '%s\n' "$output" >&2
    return 1
  fi
}

jq -e . "$matrix" "$matrix_schema" "$control_schema" "$control_example" "$report_schema" "$report_example" "$fixtures" >/dev/null

validate_matrix_schema "$matrix" >/dev/null
jq '.claims = .claims[:-1]' "$matrix" >"$missing_category_matrix_fixture"
jq '.claims[1].category = .claims[0].category' "$matrix" >"$duplicate_category_matrix_fixture"
expect_matrix_schema_rejection "$missing_category_matrix_fixture"
expect_matrix_schema_rejection "$duplicate_category_matrix_fixture"

validate_report_schema "$report_example" >/dev/null
jq '.claim_results = []' "$report_example" >"$empty_claim_results_fixture"
jq '.claim_results += [.claim_results[0]]' "$report_example" >"$duplicate_claim_result_fixture"
jq '.claim_results += [(.claim_results[0] | .scope += " — 다른 객체") ]' \
  "$report_example" >"$distinct_duplicate_claim_id_fixture"
expect_report_schema_rejection "$empty_claim_results_fixture"
expect_report_schema_rejection "$duplicate_claim_result_fixture"
validate_report_schema "$distinct_duplicate_claim_id_fixture" >/dev/null

jq '.scope.project_id = "foreign-project" |
  .scope.worktree_id = "foreign-worktree" |
  .scope.task_id = "foreign-task" |
  .scope.environment_ref = "foreign-environment"' \
  "$control_example" >"$foreign_task_control_fixture"
jq '.control_type = "sandbox"' \
  "$control_example" >"$unrelated_control_fixture"
jq '.record_id = "control-validation-hidden-fail" |
  .checks.configured.result = "fail" |
  .checks.configured.evidence_refs = ["evidence-profile-failure"]' \
  "$control_example" >"$hidden_failed_control_fixture"
jq '.claim_results[0].permitted_statement = "전체 시스템이 안전하고 모든 회귀를 찾았다" |
  .claim_results[0].scope = "전체 시스템"' \
  "$report_example" >"$overclaim_report_fixture"
jq '.claim_results[0].residual_risks = []' \
  "$report_example" >"$empty_residual_risks_fixture"
jq '.control_id = "config.duplicate-profile"' \
  "$control_example" >"$duplicate_control_record_fixture"
jq '.claim_results[0].requirement_results[0].evidence_refs = []' \
  "$report_example" >"$evidence_free_report_fixture"
jq '.control_id = "config.other-profile"' \
  "$control_example" >"$different_control_id_fixture"
jq '.scope.boundary = "다른 Control Profile"' \
  "$control_example" >"$different_control_boundary_fixture"
jq '.checks.configured.exact_scope = "다른 Control Profile"' \
  "$control_example" >"$different_control_check_scope_fixture"
validate_control_schema "$foreign_task_control_fixture" >/dev/null
validate_control_schema "$unrelated_control_fixture" >/dev/null
validate_control_schema "$hidden_failed_control_fixture" >/dev/null
validate_control_schema "$duplicate_control_record_fixture" >/dev/null
validate_control_schema "$different_control_id_fixture" >/dev/null
validate_control_schema "$different_control_boundary_fixture" >/dev/null
validate_control_schema "$different_control_check_scope_fixture" >/dev/null
validate_report_schema "$overclaim_report_fixture" >/dev/null
expect_report_schema_rejection "$empty_residual_risks_fixture"
expect_report_schema_rejection "$evidence_free_report_fixture"

jq -e 'all(.report_contract_fixtures[];
  (.matrix_version | type) == "string" and
  (.task_mode == "managed" or .task_mode == "imported") and
  all(.requirement_results[]; has("requirement_id"))
)' "$fixtures" >/dev/null

expected_report_envelope_fixture_names='conflicting verdicts for one claim are rejected
empty claim results are rejected
identical claim results are rejected
same claim id with different result objects is rejected'
actual_report_envelope_fixture_names="$(jq -r '.report_envelope_fixtures[].name' "$fixtures" | sort)"
test "$actual_report_envelope_fixture_names" = "$expected_report_envelope_fixture_names"
jq -e 'all(.report_envelope_fixtures[];
  (.matrix_version | type) == "string" and
  (.task.mode == "managed" or .task.mode == "imported") and
  (.pre_fix_gate_result == "accepted") and
  .expected_contract_valid == false and
  all(.claim_results[];
    has("claim_id") and has("verdict") and has("requirement_results") and
    has("control_validation_refs") and has("conflict_refs") and has("permitted_statement"))
)' "$fixtures" >/dev/null

required_adversarial_fixture_names='conflicting validation records contradict a required control
conflicting verdicts for one claim are rejected
duplicate requirement id is rejected
empty claim results are rejected
identical claim results are rejected
imported task cannot support a managed-only claim
mismatched matrix version is rejected
missing required requirement id is rejected
same claim id with different result objects is rejected
supported report rejects a failed required control check
supported report rejects an unresolvable control validation reference
unknown claim id is rejected
unknown requirement id is rejected'
while IFS= read -r fixture_name; do
  jq -e --arg name "$fixture_name" '
    any((.report_contract_fixtures + .report_envelope_fixtures)[]; .name == $name)
  ' "$fixtures" >/dev/null
done <<<"$required_adversarial_fixture_names"

expected_integration_mutation_fixture_names='different control boundary cannot support a claim
different control check scope cannot support a claim
duplicate control validation record ids are rejected
foreign task control cannot support a claim
global overclaim wording is rejected
report cannot omit a relevant failed control record
same type different control id cannot support a claim
supported report requires evidence references
supported report requires residual risks
unrelated control identity cannot support a claim'
actual_integration_mutation_fixture_names="$(jq -r '.integration_mutation_fixtures[].name' "$fixtures" | sort)"
test "$actual_integration_mutation_fixture_names" = "$expected_integration_mutation_fixture_names"
jq -e 'all(.integration_mutation_fixtures[];
  (.pre_fix_gate_result == "accepted" or
    .pre_fix_schema_result == "valid" or
    .adversarial_only == true) and
  .expected_contract_valid == false
)' "$fixtures" >/dev/null

pre_fix_fail_open_count="$(jq '[.report_contract_fixtures[] | select(has("pre_fix_gate_result"))] | length' "$fixtures")"
test "$pre_fix_fail_open_count" = "7"
expected_pre_fix_fail_open_names='conflicting validation records contradict a required control
duplicate requirement id is rejected
imported task cannot support a managed-only claim
mismatched matrix version is rejected
missing required requirement id is rejected
unknown claim id is rejected
unknown requirement id is rejected'
actual_pre_fix_fail_open_names="$(jq -r '.report_contract_fixtures[] | select(has("pre_fix_gate_result")) | .name' "$fixtures" | sort)"
test "$actual_pre_fix_fail_open_names" = "$expected_pre_fix_fail_open_names"
jq -e 'all(.report_contract_fixtures[] | select(has("pre_fix_gate_result"));
  (.pre_fix_gate_result == "accepted" or .pre_fix_gate_result == "skipped_fail_open") and
  .expected_contract_valid == false
)' "$fixtures" >/dev/null

expected_categories='actual_changes_identified
agents_instruction_loaded
approval_applied_action
config_conflict_identified
config_loaded
control_profile_created
dashboard_fresh
defined_regression_scope_passed
feature_directly_validated
hook_invoked_event
mcp_tool_callable
related_features_analyzed
related_tests_executed
rule_blocked_probe
sandbox_blocked_boundary
workspace_restore_point_created'

actual_categories="$(jq -r '.claims[].category' "$matrix" | sort)"
test "$actual_categories" = "$expected_categories"

claim_count="$(jq '.claims | length' "$matrix")"
unique_claim_count="$(jq '[.claims[].claim_id] | unique | length' "$matrix")"
unique_category_count="$(jq '[.claims[].category] | unique | length' "$matrix")"
test "$claim_count" = "$unique_claim_count"
test "$claim_count" = "$unique_category_count"

jq -e 'all(.claims[];
  [.required_evidence[].requirement_id] as $ids |
  ($ids | length) == ($ids | unique | length)
)' "$matrix" >/dev/null

expected_control_selectors='GM-001:control_profile:configured:profile-artifact
GM-002:active_config:loaded:resolved-config
GM-003:agents_instruction:loaded:instruction-source
GM-004:rule:enforced:rule-decision
GM-006:sandbox:enforced:sandbox-denial
GM-007:approval_policy:enforced:approval-transaction'
actual_control_selectors="$(jq -r '
  .claims[] as $claim |
  $claim.required_control_selectors[] |
  "\($claim.claim_id):\(.control_type):\(.check):\(.subject_requirement_id)"
' "$matrix" | sort)"
test "$actual_control_selectors" = "$expected_control_selectors"

matrix_control_types="$(jq -r '.["$defs"].claim.properties.required_control_selectors.items.properties.control_type.enum[]' "$matrix_schema" | sort)"
validation_control_types="$(jq -r '.properties.control_type.enum[]' "$control_schema" | sort)"
test "$matrix_control_types" = "$validation_control_types"

expected_global_forbidden_wording='Rollback 가능하다
모든 회귀를 찾았다
무결성이 보장된다
영향이 없다
완벽하게 통제됐다
전체 시스템이 안전하다
테스트가 충분하다'
actual_global_forbidden_wording="$(jq -r '.global_forbidden_wording[]' "$matrix" | sort)"
test "$actual_global_forbidden_wording" = "$expected_global_forbidden_wording"
jq -e 'all(.claims[]; . as $claim |
  all((.forbidden_wording + $matrix_forbidden)[]; . as $forbidden |
    ($claim.claim | contains($forbidden) | not)))
' --argjson matrix_forbidden "$(jq '.global_forbidden_wording' "$matrix")" "$matrix" >/dev/null

jq -e 'all(.claims[];
  [.required_evidence[].requirement_id] as $requirement_ids |
  ([.required_control_selectors[].check] | sort) ==
    (.required_realization_checks | sort) and
  ([.required_control_selectors[].control_type] | length) ==
    ([.required_control_selectors[].control_type] | unique | length) and
  all(.required_control_selectors[]; . as $selector |
    any($requirement_ids[]; . == $selector.subject_requirement_id))
)' "$matrix" >/dev/null

jq -e 'all(.claims[];
  (.required_evidence | length) > 0 and
  (.allowed_basis | length) > 0 and
  (.applicable_task_modes | length) > 0 and
  (.forbidden_wording | length) > 0 and
  (.residual_risks | length) > 0
)' "$matrix" >/dev/null

jq -e '
  ["GM-002", "GM-003", "GM-004", "GM-005", "GM-006", "GM-007", "GM-014"] as $managed_only |
  all(.claims[]; . as $claim |
    all($claim.applicable_task_modes[]; . == "managed" or . == "imported") and
    if ($managed_only | index($claim.claim_id)) != null then
      $claim.applicable_task_modes == ["managed"]
    else
      $claim.applicable_task_modes == ["managed", "imported"]
    end)
' "$matrix" >/dev/null

jq -e '.task.mode == "imported"' "$report_example" >/dev/null

if rg -n '"control_state"' "$control_schema" "$matrix_schema" "$report_schema" >/dev/null; then
  printf 'single_control_state=failed\n' >&2
  exit 1
fi

jq -e '
  .control_type == "control_profile" and
  .scope.environment_ref == "environment-synthetic" and
  .checks.configured == {
    result: "pass",
    basis: "observed",
    evidence_refs: ["evidence-profile-hash", "evidence-profile-parse"],
    inference_from: [],
    checked_at: "2026-09-04T00:00:00Z",
    exact_scope: "합성 Control Profile 파일 한 개",
    residual_risks: ["다른 profile과 실제 project config는 확인하지 않음"]
  } and
  .checks.loaded.result == "not_run" and
  .checks.loaded.basis == "unobserved" and
  .checks.enforced.result == "not_run" and
  .checks.enforced.basis == "unobserved"
' "$control_example" >/dev/null

calculated="$(jq -n --slurpfile matrix "$matrix" --slurpfile fixture_data "$fixtures" '
  def matrix_claim($id): $matrix[0].claims[] | select(.claim_id == $id);
  def calculate($fixture):
    (matrix_claim($fixture.claim_id)) as $claim |
    if ($claim.applicable_task_modes | index($fixture.task_mode)) == null then
      "not_evaluated"
    elif any($fixture.requirement_results[];
      (.conflict_refs | length) > 0 or
      (.result == "fail" and .basis == "observed")
    ) then
      "contradicted"
    elif any($claim.required_realization_checks[];
      . as $check |
      $fixture.realization_results[$check].result == "fail" and
      $fixture.realization_results[$check].basis == "observed"
    ) then
      "contradicted"
    elif any($claim.required_realization_checks[];
      . as $check |
      ($fixture.realization_results[$check].result != "pass") or
      ($fixture.realization_results[$check].basis as $basis |
        ($claim.allowed_basis | index($basis)) == null)
    ) then
      "not_evaluated"
    elif any($fixture.requirement_results[];
      . as $requirement |
      ($requirement.result != "pass") or
      (($claim.allowed_basis | index($requirement.basis)) == null)
    ) then
      "not_evaluated"
    else
      "supported"
    end;
  [$fixture_data[0].fixtures[] | {
    name,
    expected: .expected_verdict,
    actual: calculate(.)
  }]
')"

jq -e 'all(.[]; .expected == .actual)' <<<"$calculated" >/dev/null

jq -n -e \
  --slurpfile matrix "$matrix" \
  --slurpfile control "$control_example" \
  --slurpfile report "$report_example" \
  --slurpfile foreign_task_control "$foreign_task_control_fixture" \
  --slurpfile unrelated_control "$unrelated_control_fixture" \
  --slurpfile hidden_failed_control "$hidden_failed_control_fixture" \
  --slurpfile overclaim_report "$overclaim_report_fixture" \
  --slurpfile duplicate_control_record "$duplicate_control_record_fixture" \
  --slurpfile evidence_free_report "$evidence_free_report_fixture" \
  --slurpfile different_control_id "$different_control_id_fixture" \
  --slurpfile different_control_boundary "$different_control_boundary_fixture" \
  --slurpfile different_control_check_scope "$different_control_check_scope_fixture" \
  --slurpfile fixture_data "$fixtures" '
  def matrix_claim($id):
    ([$matrix[0].claims[] | select(.claim_id == $id)][0] // null);
  def task_scope_complete($task):
    all([
      $task.project_id,
      $task.worktree_id,
      $task.task_id,
      $task.target_commit,
      $task.environment_ref
    ][]; type == "string" and length > 0) and
    ($task.mode == "managed" or $task.mode == "imported");
  def task_scope_matches($task; $validation):
    $validation.scope.project_id == $task.project_id and
    $validation.scope.worktree_id == $task.worktree_id and
    $validation.scope.task_id == $task.task_id and
    $validation.scope.environment_ref == $task.environment_ref;
  def selector_requirement($selector; $result):
    ([$result.requirement_results[] |
      select(.requirement_id == $selector.subject_requirement_id)][0] // null);
  def selector_records($selector; $result; $task; $validations):
    (selector_requirement($selector; $result)) as $requirement |
    [$validations[] |
      select(.control_type == $selector.control_type and
        .control_id == $requirement.subject_ref and
        task_scope_matches($task; .))];
  def required_validation_ids($result; $claim; $task; $validations):
    [$claim.required_control_selectors[] as $selector |
      selector_records($selector; $result; $task; $validations)[] |
      .record_id] | unique;
  def validation_refs_match($result; $claim; $task; $validations):
    ($result.control_validation_refs | length) ==
      ($result.control_validation_refs | unique | length) and
    if ($claim.applicable_task_modes | index($task.mode)) == null then
      ($result.control_validation_refs | length) == 0
    else
      ($result.control_validation_refs | sort) ==
        (required_validation_ids($result; $claim; $task; $validations) | sort)
    end;
  def basis_material_valid($item):
    if $item.basis == "observed" then
      ($item.evidence_refs | length) > 0
    elif $item.basis == "inferred" then
      ($item.inference_from | length) > 0
    elif $item.basis == "unobserved" then
      ($item.evidence_refs | length) == 0 and
      ($item.inference_from | length) == 0
    else
      false
    end;
  def requirement_ids_match($result; $claim):
    [$claim.required_evidence[].requirement_id] as $required |
    [$result.requirement_results[].requirement_id] as $reported |
    ($reported | length) == ($reported | unique | length) and
    ($reported | sort) == ($required | sort);
  def calculated_verdict($result; $claim; $task; $validations):
    if ($claim.applicable_task_modes | index($task.mode)) == null then
      "not_evaluated"
    elif ($result.conflict_refs | length) > 0 or
      any($result.requirement_results[];
        (.conflict_refs | length) > 0 or
        (.result == "fail" and .basis == "observed"))
    then "contradicted"
    elif any($claim.required_control_selectors[];
      . as $selector |
      selector_records($selector; $result; $task; $validations) as $records |
      any($records[]; .checks[$selector.check].result == "fail" and
        .checks[$selector.check].basis == "observed") or
      (([$records[].checks[$selector.check].result] | index("pass")) != null and
       ([$records[].checks[$selector.check].result] | index("fail")) != null))
    then "contradicted"
    elif any($claim.required_control_selectors[];
        . as $selector |
        (selector_requirement($selector; $result)) as $requirement |
        selector_records($selector; $result; $task; $validations) as $records |
        ($records | length) == 0 or
        any($records[];
          .scope.boundary != $requirement.exact_scope or
          .checks[$selector.check].exact_scope != $requirement.exact_scope or
          (.checks[$selector.check] | .result != "pass" or
            (.basis as $basis | ($claim.allowed_basis | index($basis)) == null) or
            (basis_material_valid(.) | not)))) or
      any($result.requirement_results[]; . as $requirement |
        $requirement.result != "pass" or
        ($claim.allowed_basis | index($requirement.basis)) == null or
        (basis_material_valid($requirement) | not))
    then "not_evaluated"
    else "supported"
    end;
  def supported_wording_valid($result; $claim):
    ($result.permitted_statement == $claim.claim) and
    all($result.requirement_results[]; .exact_scope == $result.scope) and
    all($claim.residual_risks[]; . as $risk |
      ($result.residual_risks | index($risk)) != null) and
    all(($matrix[0].global_forbidden_wording + $claim.forbidden_wording)[];
      . as $forbidden |
      ($result.permitted_statement | contains($forbidden) | not) and
      ($result.scope | contains($forbidden) | not));
  def report_contract_valid($matrix_version; $task; $validations):
    . as $result |
    (matrix_claim($result.claim_id)) as $claim |
    if $matrix_version != $matrix[0].matrix_version or $claim == null then
      false
    elif task_scope_complete($task) | not then
      false
    elif ([$validations[].record_id] | length) !=
      ([$validations[].record_id] | unique | length) then
      false
    elif requirement_ids_match($result; $claim) | not then
      false
    elif validation_refs_match($result; $claim; $task; $validations) | not then
      false
    elif calculated_verdict($result; $claim; $task; $validations) != $result.verdict then
      false
    elif $result.verdict == "supported" then
      all($result.requirement_results[]; . as $requirement |
        $requirement.result == "pass" and
        ($claim.allowed_basis | index($requirement.basis)) != null and
        ($requirement.conflict_refs | length) == 0) and
      ($result.conflict_refs | length) == 0 and
      supported_wording_valid($result; $claim)
    elif $result.verdict == "contradicted" or $result.verdict == "not_evaluated" then
      $result.permitted_statement == null
    else
      false
    end;
  def report_document_valid($document; $validations):
    [$document.claim_results[].claim_id] as $claim_ids |
    ($document.matrix_version == $matrix[0].matrix_version) and
    ($document.claim_results | length) > 0 and
    ($claim_ids | length) == ($claim_ids | unique | length) and
    all($document.claim_results | group_by(.claim_id)[];
      ([.[].verdict] | unique | length) == 1) and
    all($document.claim_results[];
      report_contract_valid($document.matrix_version; $document.task; $validations));
  def unit_task($mode): {
    project_id: "project-synthetic",
    worktree_id: "worktree-main",
    task_id: "task-synthetic",
    mode: $mode,
    target_commit: "0000000000000000000000000000000000000000",
    environment_ref: "environment-synthetic"
  };
  def unit_result($fixture; $claim):
    $fixture |
    .scope = (.scope // "합성 fixture 범위") |
    .residual_risks = (.residual_risks // $claim.residual_risks) |
    .requirement_results |= map(
      .subject_ref = (.subject_ref //
        (if ($claim.required_control_selectors | length) > 0
         then "control-unit" else "subject-unit" end)) |
      .exact_scope = (.exact_scope // "합성 fixture 범위") |
      .evidence_refs = (.evidence_refs //
        (if .basis == "observed" then ["evidence-unit"] else [] end)) |
      .inference_from = (.inference_from //
        (if .basis == "inferred" then ["inference-unit"] else [] end)));
  def unit_validations($fixture; $claim):
    [$fixture.control_validations[] |
      .control_id = (.control_id // "control-unit") |
      .control_type = (.control_type // $claim.required_control_selectors[0].control_type) |
      .scope = (.scope // {
        project_id: "project-synthetic",
        worktree_id: "worktree-main",
        task_id: "task-synthetic",
        boundary: "합성 fixture 범위",
        environment_ref: "environment-synthetic"
      }) |
      .checks |= with_entries(
        .value.exact_scope = (.value.exact_scope // "합성 fixture 범위") |
        .value.evidence_refs = (.value.evidence_refs //
          (if .value.basis == "observed" then ["evidence-unit"] else [] end)) |
        .value.inference_from = (.value.inference_from //
          (if .value.basis == "inferred" then ["inference-unit"] else [] end)))] ;
  report_document_valid($report[0]; [$control[0]]) and
  all($fixture_data[0].report_contract_fixtures[]; . as $fixture |
    (matrix_claim($fixture.claim_id)) as $claim |
    (unit_result($fixture; $claim) |
      report_contract_valid($fixture.matrix_version; unit_task($fixture.task_mode);
        unit_validations($fixture; $claim))) == $fixture.expected_contract_valid) and
  all($fixture_data[0].report_envelope_fixtures[]; . as $fixture |
    ($fixture |
      .task = unit_task(.task.mode) |
      .claim_results |= map(. as $result |
        (matrix_claim($result.claim_id)) as $claim |
        unit_result($result; $claim)) |
      report_document_valid(.; [])) == $fixture.expected_contract_valid) and
  (report_document_valid($report[0]; [$foreign_task_control[0]]) == false) and
  (report_document_valid($report[0]; [$unrelated_control[0]]) == false) and
  (report_document_valid($report[0]; [$control[0], $hidden_failed_control[0]]) == false) and
  (report_document_valid($overclaim_report[0]; [$control[0]]) == false) and
  (report_document_valid($report[0]; [$control[0], $duplicate_control_record[0]]) == false) and
  (report_document_valid($evidence_free_report[0]; [$control[0]]) == false) and
  (report_document_valid($report[0]; [$different_control_id[0]]) == false) and
  (report_document_valid($report[0]; [$different_control_boundary[0]]) == false) and
  (report_document_valid($report[0]; [$different_control_check_scope[0]]) == false)
' >/dev/null

printf 'json_syntax=passed\n'
printf 'schema_empty_claim_results_rejected=passed\n'
printf 'schema_exact_duplicate_claim_rejected=passed\n'
printf 'schema_distinct_duplicate_claim_id_requires_gate=passed\n'
printf 'schema_empty_supported_residual_risks_rejected=passed\n'
printf 'matrix_schema_category_mutations_rejected=2\n'
printf 'core_category_coverage=passed\n'
printf 'unique_claim_mapping=passed\n'
printf 'unique_requirement_mapping=passed\n'
printf 'task_mode_applicability=passed\n'
printf 'single_control_state_absent=passed\n'
printf 'independent_control_checks=passed\n'
printf 'insufficient_evidence_fail_safe=passed\n'
printf 'conflicting_evidence_fail_safe=passed\n'
printf 'observed_control_failure_verdict=passed\n'
printf 'task_report_wording_gate=passed\n'
printf 'report_fixture_context=passed\n'
printf 'required_control_resolution_gate=passed\n'
printf 'verdict_swap_rejection=passed\n'
printf 'matrix_version_gate=passed\n'
printf 'claim_membership_gate=passed\n'
printf 'requirement_id_gate=passed\n'
printf 'all_control_records_gate=passed\n'
printf 'pre_fix_fail_open_cases_rejected=%s\n' "$pre_fix_fail_open_count"
printf 'report_envelope_fixtures_rejected=4\n'
printf 'claim_results_nonempty_gate=passed\n'
printf 'claim_id_uniqueness_gate=passed\n'
printf 'claim_verdict_conflict_gate=passed\n'
printf 'required_adversarial_fixture_coverage=23\n'
printf 'schema_valid_integration_mutations_rejected=8\n'
printf 'schema_adversarial_mutations_rejected=2\n'
printf 'control_selector_scope_binding=passed\n'
printf 'control_instance_subject_binding=passed\n'
printf 'control_selector_mapping=passed\n'
printf 'control_type_schema_alignment=passed\n'
printf 'global_forbidden_wording_coverage=passed\n'
printf 'canonical_wording_and_risk_gate=passed\n'
printf 'basis_material_gate=passed\n'
printf 'adversarial_report_contract=passed\n'
