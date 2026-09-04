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

jq -e . "$matrix" "$matrix_schema" "$control_schema" "$control_example" "$report_schema" "$report_example" "$fixtures" >/dev/null

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
    elif any($fixture.requirement_results[]; (.conflict_refs | length) > 0 or .result == "fail") then
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
  def matrix_claim($id): $matrix[0].claims[] | select(.claim_id == $id);
  def required_controls_valid($result; $claim; $validations):
    all($claim.required_realization_checks[]; . as $check |
      any(
        $result.control_validation_refs[] as $reference |
        $validations[] |
        {reference: $reference, validation: .};
        .validation.record_id == .reference and
        .validation.checks[$check].result == "pass" and
        (.validation.checks[$check].basis as $basis |
          ($claim.allowed_basis | index($basis)) != null)));
  def report_contract_valid($validations):
    . as $result |
    (matrix_claim($result.claim_id)) as $claim |
    if $result.verdict == "supported" then
      ($result.requirement_results | length) > 0 and
      all($result.requirement_results[]; . as $requirement |
        $requirement.result == "pass" and
        ($claim.allowed_basis | index($requirement.basis)) != null and
        ($requirement.conflict_refs | length) == 0) and
      ($result.conflict_refs | length) == 0 and
      ($result.permitted_statement | type == "string" and length > 0) and
      all($claim.forbidden_wording[]; . as $forbidden |
        ($result.permitted_statement | contains($forbidden) | not)) and
      required_controls_valid($result; $claim; $validations)
    elif $result.verdict == "contradicted" or $result.verdict == "not_evaluated" then
      $result.permitted_statement == null
    else
      false
    end;
  all($report[0].claim_results[]; report_contract_valid([$control[0]])) and
  all($fixture_data[0].report_contract_fixtures[]; . as $fixture |
    (report_contract_valid($fixture.control_validations)) == $fixture.expected_contract_valid)
' >/dev/null

printf 'json_syntax=passed\n'
printf 'core_category_coverage=passed\n'
printf 'unique_claim_mapping=passed\n'
printf 'task_mode_applicability=passed\n'
printf 'single_control_state_absent=passed\n'
printf 'independent_control_checks=passed\n'
printf 'insufficient_evidence_fail_safe=passed\n'
printf 'conflicting_evidence_fail_safe=passed\n'
printf 'task_report_wording_gate=passed\n'
printf 'required_control_resolution_gate=passed\n'
printf 'adversarial_report_contract=passed\n'
