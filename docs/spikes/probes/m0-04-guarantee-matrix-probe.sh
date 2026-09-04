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
cleanup_schema_fixtures() {
  unlink "$empty_claim_results_fixture" "$duplicate_claim_result_fixture" \
    "$distinct_duplicate_claim_id_fixture" 2>/dev/null || true
  rmdir "$schema_fixture_dir" 2>/dev/null || true
}
trap cleanup_schema_fixtures EXIT

validate_report_schema() {
  npm_config_offline=true npx --yes --package ajv-cli@5.0.0 --package ajv-formats@3.0.1 \
    ajv validate --spec=draft2020 --strict-types=true --strict-tuples=true \
    -c ajv-formats -s "$report_schema" -d "$1"
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

jq -e . "$matrix" "$matrix_schema" "$control_schema" "$control_example" "$report_schema" "$report_example" "$fixtures" >/dev/null

validate_report_schema "$report_example" >/dev/null
jq '.claim_results = []' "$report_example" >"$empty_claim_results_fixture"
jq '.claim_results += [.claim_results[0]]' "$report_example" >"$duplicate_claim_result_fixture"
jq '.claim_results += [(.claim_results[0] | .scope += " — 다른 객체") ]' \
  "$report_example" >"$distinct_duplicate_claim_id_fixture"
expect_report_schema_rejection "$empty_claim_results_fixture"
expect_report_schema_rejection "$duplicate_claim_result_fixture"
validate_report_schema "$distinct_duplicate_claim_id_fixture" >/dev/null

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
  --slurpfile fixture_data "$fixtures" '
  def matrix_claim($id):
    ([$matrix[0].claims[] | select(.claim_id == $id)][0] // null);
  def linked_checks($result; $check; $validations):
    [$result.control_validation_refs[] as $reference |
      $validations[] |
      select(.record_id == $reference) |
      .checks[$check]];
  def validation_refs_resolve($result; $validations):
    all($result.control_validation_refs[]; . as $reference |
      any($validations[]; .record_id == $reference));
  def requirement_ids_match($result; $claim):
    [$claim.required_evidence[].requirement_id] as $required |
    [$result.requirement_results[].requirement_id] as $reported |
    ($reported | length) == ($reported | unique | length) and
    ($reported | sort) == ($required | sort);
  def calculated_verdict($result; $claim; $task_mode; $validations):
    if ($claim.applicable_task_modes | index($task_mode)) == null then
      "not_evaluated"
    elif ($result.conflict_refs | length) > 0 or
      any($result.requirement_results[];
        (.conflict_refs | length) > 0 or
        (.result == "fail" and .basis == "observed"))
    then "contradicted"
    elif any($claim.required_realization_checks[];
      linked_checks($result; .; $validations) as $checks |
      any($checks[]; .result == "fail" and .basis == "observed") or
      (([$checks[].result] | index("pass")) != null and
       ([$checks[].result] | index("fail")) != null))
    then "contradicted"
    elif any($claim.required_realization_checks[];
        linked_checks($result; .; $validations) as $checks |
        ($checks | length) == 0 or
        any($checks[]; .result != "pass" or
          (.basis as $basis | ($claim.allowed_basis | index($basis)) == null))) or
      any($result.requirement_results[]; . as $requirement |
        $requirement.result != "pass" or
        ($claim.allowed_basis | index($requirement.basis)) == null)
    then "not_evaluated"
    else "supported"
    end;
  def report_contract_valid($matrix_version; $task_mode; $validations):
    . as $result |
    (matrix_claim($result.claim_id)) as $claim |
    if $matrix_version != $matrix[0].matrix_version or $claim == null then
      false
    elif requirement_ids_match($result; $claim) | not then
      false
    elif validation_refs_resolve($result; $validations) | not then
      false
    elif calculated_verdict($result; $claim; $task_mode; $validations) != $result.verdict then
      false
    elif $result.verdict == "supported" then
      all($result.requirement_results[]; . as $requirement |
        $requirement.result == "pass" and
        ($claim.allowed_basis | index($requirement.basis)) != null and
        ($requirement.conflict_refs | length) == 0) and
      ($result.conflict_refs | length) == 0 and
      ($result.permitted_statement | type == "string" and length > 0) and
      all($claim.forbidden_wording[]; . as $forbidden |
        ($result.permitted_statement | contains($forbidden) | not))
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
      report_contract_valid($document.matrix_version; $document.task.mode; $validations));
  report_document_valid($report[0]; [$control[0]]) and
  all($fixture_data[0].report_contract_fixtures[]; . as $fixture |
    (report_contract_valid($fixture.matrix_version; $fixture.task_mode; $fixture.control_validations)) ==
      $fixture.expected_contract_valid) and
  all($fixture_data[0].report_envelope_fixtures[]; . as $fixture |
    report_document_valid($fixture; $fixture.control_validations) == $fixture.expected_contract_valid)
' >/dev/null

printf 'json_syntax=passed\n'
printf 'schema_empty_claim_results_rejected=passed\n'
printf 'schema_exact_duplicate_claim_rejected=passed\n'
printf 'schema_distinct_duplicate_claim_id_requires_gate=passed\n'
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
printf 'required_adversarial_fixture_coverage=13\n'
printf 'adversarial_report_contract=passed\n'
