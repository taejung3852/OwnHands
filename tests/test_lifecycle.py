from __future__ import annotations

import copy
import json
import sqlite3
import subprocess
import tempfile
import unittest
from pathlib import Path

from devharness.catalog import Catalog
from devharness.paths import DataPaths
from devharness.identity import IdentityRegistry
from devharness.events import EventLog
from devharness.evidence import EvidenceDraft, EvidenceStore
from devharness.projections import ProjectionEngine
from devharness import lifecycle
from devharness.lifecycle.model import fingerprint

FIXTURES = Path(__file__).parent / 'fixtures' / 'lifecycle'


class LifecycleTests(unittest.TestCase):
    @staticmethod
    def code_state_data(marker='initial'):
        body = {'code_state_version': 1, 'commit': 'a' * 40,
                'files': [{'path': 'fixture', 'origin': 'tracked', 'kind': 'file',
                           'mode': 0o644, 'hash': fingerprint(marker)}],
                'coverage': 'complete', 'exclusions': []}
        return {**body, 'fingerprint': fingerprint(body)}

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.paths = DataPaths.resolve(Path(self.temp.name) / 'private')
        self.catalog = Catalog.open(self.paths)
        self.task = IdentityRegistry(self.catalog).create_task_lifecycle(
            'project', 'worktree', 'imported', 'a' * 40, 'main', '/fixture', 'env')
        self.store = lifecycle.LifecycleStore(self.catalog)
        self.project_scope = {'project_id': self.task.project_id}
        self.issue = self.store.append('work_issue', 'issue:80', self.project_scope,
            {'title': 'Widget', 'source': 'https://example.invalid/issues/80',
             'content': 'Preserve widget', 'request_refs': []})
        self.issue_scope = {**self.project_scope, 'issue_id': 'issue:80'}
        self.scope = {**self.issue_scope, 'task_id': self.task.task_id, 'attempt_id': 'attempt:1'}
        self.attempt = self.store.append('attempt', 'attempt:1', self.scope,
            {'issue': self.issue, 'previous': None})
        self.store.activate(self.attempt)
        self.spec_data = {'issue': self.issue, 'document': {'path': 'docs/issues/80.md',
            'text': '# Widget\nPreserve widget'}, 'criteria': [
                {'id': 'c1', 'text': 'Preserve widget', 'required': True, 'comparison': 'before_after'}]}
        self.spec = self.store.append('spec', 'spec:80', self.issue_scope, self.spec_data)
        self.approval = self.approve(self.spec)
        self.code = self.store.append('code_state', 'code:1', self.scope,
                                      self.code_state_data())
        self.env = self.store.append('environment', 'env:1', self.scope,
                                     lifecycle.environment_state('fixture'))
        self.counter = 0

    def tearDown(self):
        self.store.close()
        self.catalog.close()
        self.temp.cleanup()

    def approve(self, spec):
        approval = self.store.append('spec_approval', 'approve:' + str(spec['revision']), self.issue_scope,
            {'spec': spec, 'actor': {'kind': 'human', 'id': 'owner'}, 'decision': 'approved',
             'reason': 'Agreed criteria', 'source': 'conversation:approval'})
        self.store.activate(spec, approval=approval)
        return approval

    def observation(self, phase='after', result='pass', meaning='d' * 64, env=None,
                    criterion='c1', scope=None, basis='observed', code=None):
        self.counter += 1
        scope = scope or self.scope
        evidence_id = 'legacy:' + str(self.counter)
        fields = {'test_id': 'widget', 'criterion_id': criterion, 'phase': phase,
                  'spec_hash': self.spec['hash'], 'code_hash': (code or self.code)['hash'],
                  'environment_hash': (env or self.env)['hash'], 'test_meaning': meaning}
        EvidenceStore(self.catalog, EventLog(self.catalog)).put(EvidenceDraft(
            evidence_id, scope['task_id'], criterion or 'additional', 'test_execution',
            'widget', 'widget function', result, basis, fields, b'fixture stdout',
            'fixture runner', 'not_needed'), lambda b: b)
        binding = self.store.bind_evidence('binding:' + str(self.counter), scope, evidence_id)
        return self.store.append('observation', 'obs:' + str(self.counter), scope,
            {'spec': self.spec, 'spec_approval': self.approval,
             'code_state': code or self.code, 'environment': env or self.env,
             'test_id': 'widget', 'criterion_id': criterion, 'phase': phase,
             'test_meaning': meaning, 'result': result, 'basis': basis,
             'selection_reason': 'Shares changed widget code', 'evidence': [binding]})

    def baseline(self, receipts=None):
        return self.store.append('baseline', 'baseline:1', self.scope,
            {'spec': self.spec, 'spec_approval': self.approval,
             'code_state': self.code, 'environment': self.env,
             'baseline_kind': 'verification', 'observations': receipts or [],
             'missing_reason': 'Before unavailable' if not receipts else ''})

    def review(self, status='verified', before=True, after=None, additions=None):
        left = self.observation('before') if before else None
        baseline = self.baseline([left] if left else [])
        right = after or self.observation()
        data = {'spec': self.spec, 'spec_approval': self.approval,
                'code_state': self.code, 'environment': self.env,
                'baseline': baseline, 'claims': [{'criterion_id': 'c1', 'status': status,
                    'observations': [right], 'reason': 'Fixture assessment'}],
                'additional_observations': additions or [], 'uncertainties': [], 'inferences': []}
        return self.store.append('review', 'review:1', self.scope, data)

    def test_human_approval_is_required_and_draft_does_not_replace_current(self):
        changed = copy.deepcopy(self.spec_data)
        changed['document']['text'] += '\nChange meaning'
        draft = self.store.append('spec', 'spec:80', self.issue_scope, changed)
        with self.assertRaises(ValueError):
            self.store.activate(draft)
        self.assertEqual(self.store.current('spec', self.issue_scope), self.spec)
        with self.assertRaises(ValueError):
            self.store.append('spec_approval', 'agent-approval', self.issue_scope,
                {'spec': draft, 'actor': {'kind': 'agent', 'id': 'bot'},
                 'decision': 'approved', 'reason': 'self-approved', 'source': 'bot'})
        self.approve(draft)
        self.assertEqual(self.store.current('spec', self.issue_scope), draft)
        self.assertEqual(self.store.get(self.spec)['data']['document']['text'], self.spec_data['document']['text'])

    def test_spec_comparison_and_human_actor_are_machine_validated(self):
        invalid = copy.deepcopy(self.spec_data)
        invalid['criteria'][0]['comparison'] = 'whatever'
        with self.assertRaises(ValueError):
            self.store.append('spec', 'invalid-comparison', self.issue_scope, invalid)
        with self.assertRaises(ValueError):
            self.store.append('spec_approval', 'anonymous-approval', self.issue_scope,
                {'spec': self.spec, 'actor': {'kind': 'human'}, 'decision': 'approved',
                 'reason': 'No attributable actor', 'source': 'conversation:anonymous'})

    def test_missing_before_cannot_be_verified_but_can_be_reported(self):
        with self.assertRaises(ValueError):
            self.review(before=False)
        review = self.review(status='inconclusive', before=False)
        self.assertEqual(self.store.get(review)['data']['review_state'], 'needs-review')

    def test_unobserved_before_result_cannot_support_verified_regression(self):
        for result in ('not_run', 'inconclusive'):
            with self.subTest(result=result):
                before = self.observation('before', result=result)
                baseline = self.baseline([before])
                after = self.observation()
                with self.assertRaises(ValueError):
                    self.store.append('review', 'invalid-before:' + result, self.scope,
                        {'spec': self.spec, 'spec_approval': self.approval,
                         'code_state': self.code, 'environment': self.env, 'baseline': baseline,
                         'claims': [{'criterion_id': 'c1', 'status': 'verified',
                                     'observations': [after], 'reason': 'Invalid Before'}],
                         'additional_observations': [], 'uncertainties': [], 'inferences': []})

    def test_test_meaning_and_environment_mismatch_never_become_regression_pass(self):
        for right in [self.observation(meaning='e' * 64),
                      self.observation(env=self.store.append('environment', 'env:2', self.scope,
                          lifecycle.environment_state('changed')))]:
            with self.subTest(right=right), self.assertRaises(ValueError):
                self.review(after=right)

    def test_inferred_result_is_not_verified(self):
        with self.assertRaises(ValueError):
            self.review(after=self.observation(basis='inferred'))

    def test_observed_result_requires_bound_evidence(self):
        with self.assertRaises(ValueError):
            self.store.append('observation', 'unsupported-observation', self.scope,
                {'spec': self.spec, 'spec_approval': self.approval,
                 'code_state': self.code, 'environment': self.env,
                 'test_id': 'widget', 'criterion_id': 'c1', 'phase': 'after',
                 'test_meaning': 'd' * 64, 'result': 'pass', 'basis': 'observed',
                 'selection_reason': 'Shares changed widget code', 'evidence': []})

    def test_baseline_only_accepts_matching_before_observations(self):
        after = self.observation('after')
        with self.assertRaises(ValueError):
            self.baseline([after])
        other_env = self.store.append('environment', 'baseline-env:2', self.scope,
                                      lifecycle.environment_state('different'))
        foreign = self.observation('before', env=other_env)
        with self.assertRaises(ValueError):
            self.baseline([foreign])

    def test_code_state_and_environment_require_sha256_fingerprints(self):
        with self.assertRaises(ValueError):
            self.store.append('code_state', 'invalid-code', self.scope,
                              {'fingerprint': 'not-a-hash'})
        with self.assertRaises(ValueError):
            self.store.append('environment', 'invalid-env', self.scope,
                              {'fingerprint': 'not-a-hash', 'description': 'bad'})
        forged_code = self.code_state_data('forged')
        forged_code['fingerprint'] = '0' * 64
        with self.assertRaisesRegex(ValueError, 'does not match'):
            self.store.append('code_state', 'forged-code', self.scope, forged_code)
        forged_env = lifecycle.environment_state('forged')
        forged_env['fingerprint'] = '0' * 64
        with self.assertRaisesRegex(ValueError, 'does not match'):
            self.store.append('environment', 'forged-env', self.scope, forged_env)
        malformed = {'code_state_version': 1, 'commit': 'a' * 40,
                     'files': ['opaque'], 'coverage': 'complete',
                     'exclusions': [{'area': 'private', 'reason': 'not captured'}]}
        malformed['fingerprint'] = fingerprint(malformed)
        with self.assertRaises(ValueError):
            self.store.append('code_state', 'malformed-code', self.scope, malformed)

    def test_additional_failure_is_reported_even_when_required_claim_passes(self):
        additional = self.observation(result='fail', criterion=None)
        review = self.review(additions=[additional])
        self.assertEqual(self.store.get(review)['data']['review_state'], 'needs-review')

    def test_all_review_observations_are_bound_to_review_inputs(self):
        changed_code = self.store.append('code_state', 'code:other', self.scope,
                                         self.code_state_data('other'))
        foreign = self.observation(code=changed_code)
        baseline = self.baseline([self.observation('before')])
        for claims, additional in [
            ([{'criterion_id': 'c1', 'status': 'inconclusive',
               'observations': [foreign], 'reason': 'Could not conclude'}], []),
            ([{'criterion_id': 'c1', 'status': 'inconclusive',
               'observations': [], 'reason': 'Could not conclude'}], [foreign]),
        ]:
            with self.subTest(additional=bool(additional)), self.assertRaises(ValueError):
                self.store.append('review', 'mismatched-review', self.scope,
                    {'spec': self.spec, 'spec_approval': self.approval,
                     'code_state': self.code, 'environment': self.env, 'baseline': baseline,
                     'claims': claims, 'additional_observations': additional,
                     'uncertainties': [], 'inferences': []})

    def test_review_compares_before_code_to_after_code_without_equating_them(self):
        before = self.observation('before')
        baseline = self.baseline([before])
        changed_code = self.store.append('code_state', 'code:after', self.scope,
                                         self.code_state_data('implemented'))
        after = self.observation(code=changed_code)
        review = self.store.append('review', 'changed-code-review', self.scope,
            {'spec': self.spec, 'spec_approval': self.approval,
             'code_state': changed_code, 'environment': self.env, 'baseline': baseline,
             'claims': [{'criterion_id': 'c1', 'status': 'verified',
                         'observations': [after], 'reason': 'Before and After are comparable'}],
             'additional_observations': [], 'uncertainties': [], 'inferences': []})
        self.assertEqual(self.store.get(review)['data']['review_state'], 'ready')

    def test_scoped_references_reject_other_attempt_and_task(self):
        other = {**self.scope, 'attempt_id': 'attempt:2'}
        self.store.append('attempt', 'attempt:2', other, {'issue': self.issue, 'previous': self.attempt})
        with self.assertRaises(ValueError):
            self.store.append('baseline', 'foreign', other,
                {'spec': self.spec, 'spec_approval': self.approval,
                 'code_state': self.code, 'environment': self.env,
                 'baseline_kind': 'micro', 'observations': [], 'missing_reason': ''})
        with self.assertRaises(ValueError):
            self.store.bind_evidence('reuse', other, self.store.get(
                self.store.get(self.observation())['data']['evidence'][0])['data']['evidence_id'])

    def test_attempt_scoped_records_require_a_real_attempt(self):
        ghost = {**self.issue_scope, 'task_id': self.task.task_id, 'attempt_id': 'attempt:ghost'}
        with self.assertRaises(ValueError):
            self.store.append('code_state', 'ghost-code', ghost, self.code_state_data('ghost'))
        readiness = self.store.inspect_stage('baseline', 'capture', ghost, {}, {})
        self.assertEqual(readiness['readiness'], 'needs-input')
        self.assertIn('inactive_attempt', {item['reason'] for item in readiness['checks']})

    def test_evidence_binding_revalidates_raw_object(self):
        observation = self.observation()
        binding = self.store.get(observation)['data']['evidence'][0]
        evidence_id = self.store.get(binding)['data']['evidence_id']
        evidence = EvidenceStore(self.catalog, EventLog(self.catalog)).resolve(evidence_id)
        evidence.object_path.write_bytes(b'corrupt')
        with self.assertRaises(ValueError):
            self.store.get(binding)
        with self.assertRaises(ValueError):
            self.store.get(observation)

    def test_missing_and_purged_evidence_cannot_be_used(self):
        with self.assertRaises(ValueError):
            self.store.bind_evidence('missing-binding', self.scope, 'missing-evidence')
        observation = self.observation()
        binding = self.store.get(observation)['data']['evidence'][0]
        evidence_id = self.store.get(binding)['data']['evidence_id']
        EvidenceStore(self.catalog, EventLog(self.catalog)).purge(evidence_id, 'fixture retention')
        with self.assertRaises(ValueError):
            self.store.get(binding)

    def test_snapshot_and_decision_remain_immutable_after_later_code(self):
        review = self.review()
        snap = self.store.append('snapshot', 'snapshot:1', self.scope, {'review': review})
        snapshot_before = self.store.get(snap)
        projected = self.store.projection()
        self.store.append('human_decision', 'decision:1', self.scope,
            {'snapshot': snap, 'actor': {'kind': 'human', 'id': 'owner'},
             'decision': 'accept', 'reason': 'Reviewed', 'source': 'conversation:decision'})
        self.assertTrue(self.store.projection_status(projected)['needs_refresh'])
        self.assertEqual(self.store.freshness(review, self.spec, self.code, self.env,
                                             {'widget': 'd' * 64})['state'], 'current')
        self.assertEqual(self.store.get(snap), snapshot_before)
        later = self.store.append('code_state', 'code:1', self.scope,
                                  self.code_state_data('later'))
        self.assertEqual(self.store.freshness(review, self.spec, later, self.env,
                                             {'widget': 'd' * 64})['state'], 'stale')

    def test_active_attempt_is_selected_once_per_issue(self):
        self.assertEqual(self.store.current('attempt', self.issue_scope), self.attempt)
        next_scope = {**self.issue_scope, 'task_id': self.task.task_id, 'attempt_id': 'attempt:2'}
        next_attempt = self.store.append('attempt', 'attempt:2', next_scope,
            {'issue': self.issue, 'previous': self.attempt})
        self.store.activate(next_attempt)
        self.assertEqual(self.store.current('attempt', self.issue_scope), next_attempt)
        self.assertEqual(self.store.get(self.attempt)['data']['previous'], None)
        with self.assertRaisesRegex(ValueError, 'active attempt'):
            self.store.append('code_state', 'late-old-code', self.scope,
                              self.code_state_data('late'))
        with self.assertRaisesRegex(ValueError, 'active attempt'):
            self.store.activate(self.code)

    def test_active_spec_exposes_the_exact_approval(self):
        activation = self.store.current_activation('spec', self.issue_scope)
        self.assertEqual(activation['reference'], self.spec)
        self.assertEqual(activation['approval'], self.approval)
        active = self.store.projection()['active']
        self.assertTrue(any(item == {'reference': self.spec, 'approval': self.approval}
                            for item in active.values()))

    def test_attempt_artifacts_use_explicit_active_slots(self):
        self.store.activate(self.code)
        self.assertEqual(self.store.current('code_state', self.scope), self.code)
        micro = self.store.append('baseline', 'micro:1', self.scope,
            {'spec': self.spec, 'spec_approval': self.approval,
             'code_state': self.code, 'environment': self.env,
             'baseline_kind': 'micro', 'observations': [], 'missing_reason': ''})
        verification = self.baseline([])
        self.store.activate(micro, slot='micro')
        self.store.activate(verification, slot='verification')
        self.assertEqual(self.store.current('baseline', self.scope, 'micro'), micro)
        self.assertEqual(self.store.current('baseline', self.scope, 'verification'), verification)
        with self.assertRaises(ValueError):
            self.store.activate(micro, slot='verification')

    def test_journal_replay_and_legacy_projection_are_independent(self):
        legacy_head = len(EventLog(self.catalog).list_for_task(self.task.task_id))
        projection = self.store.projection()
        self.store.close()
        self.store = lifecycle.LifecycleStore(self.catalog)
        self.assertEqual(self.store.projection(), projection)
        self.assertEqual(len(EventLog(self.catalog).list_for_task(self.task.task_id)), legacy_head)
        self.assertEqual(ProjectionEngine(self.catalog, EventLog(self.catalog)).project(self.task.task_id).state, 'ready')
        EvidenceStore(self.catalog, EventLog(self.catalog)).reconcile_objects(grace_period_seconds=0)
        self.assertTrue(self.store.path.exists())
        with Catalog.open(self.paths) as reopened:
            self.assertEqual(IdentityRegistry(reopened).get_task(self.task.task_id), self.task)

    def test_append_is_atomic_on_invalid_reference_and_history_is_not_overwritten(self):
        before = self.store.projection()
        forged = {**self.spec, 'hash': '0' * 64}
        with self.assertRaises(ValueError):
            self.store.append('snapshot', 'bad', self.scope, {'review': forged})
        self.assertEqual(self.store.projection(), before)
        changed = copy.deepcopy(self.spec_data)
        changed['document']['text'] += '\nnew'
        new = self.store.append('spec', 'spec:80', self.issue_scope, changed)
        self.assertEqual(new['revision'], 2)
        self.assertNotEqual(new['hash'], self.spec['hash'])

    def test_same_content_is_idempotent_and_different_content_creates_revision(self):
        same = self.store.append('spec', 'spec:80', self.issue_scope, self.spec_data)
        self.assertEqual(same, self.spec)
        changed = copy.deepcopy(self.spec_data)
        changed['document']['text'] += '\nA new human criterion'
        changed['criteria'].append({'id': 'c2', 'text': 'New criterion',
                                    'required': True, 'comparison': 'current'})
        revised = self.store.append('spec', 'spec:80', self.issue_scope, changed)
        self.assertEqual(revised['revision'], 2)

    def test_idempotent_append_survives_later_activation_changes(self):
        baseline = self.baseline([])
        original = self.store.get(baseline)['data']
        changed = copy.deepcopy(self.spec_data)
        changed['document']['text'] += '\nNew active criteria'
        revised = self.store.append('spec', 'spec:80', self.issue_scope, changed)
        self.approve(revised)
        self.assertEqual(self.store.append('baseline', 'baseline:1', self.scope, original), baseline)

    def test_logical_id_cannot_move_to_another_scope(self):
        other_scope = {**self.project_scope, 'issue_id': 'issue:81'}
        other_issue = self.store.append('work_issue', 'issue:81', self.project_scope,
            {'title': 'Router', 'source': 'https://example.invalid/issues/81',
             'content': 'Route work', 'request_refs': []})
        with self.assertRaises(ValueError):
            self.store.append('spec', 'spec:80', other_scope,
                {'issue': other_issue, 'document': {'path': 'docs/issues/81.md', 'text': '# Router'},
                 'criteria': [{'id': 'x', 'text': 'Route', 'required': True, 'comparison': 'current'}]})

    def test_unapproved_or_inactive_spec_cannot_bind_execution_records(self):
        changed = copy.deepcopy(self.spec_data)
        changed['document']['text'] += '\nUnactivated'
        draft = self.store.append('spec', 'spec:80', self.issue_scope, changed)
        draft_approval = self.store.append('spec_approval', 'draft-approval', self.issue_scope,
            {'spec': draft, 'actor': {'kind': 'human', 'id': 'owner'}, 'decision': 'approved',
             'reason': 'Approved but not activated', 'source': 'conversation:draft'})
        with self.assertRaises(ValueError):
            self.store.append('baseline', 'inactive-baseline', self.scope,
                {'spec': draft, 'spec_approval': draft_approval,
                 'code_state': self.code, 'environment': self.env,
                 'baseline_kind': 'verification', 'observations': [],
                 'missing_reason': 'Before unavailable'})

    def test_outcome_lists_only_accept_scoped_lifecycle_references(self):
        with self.assertRaises(ValueError):
            self.store.append('outcome', 'invalid-outcome', self.scope,
                {'stage': 'review', 'action': 'render', 'inputs': ['review:1'],
                 'outputs': [], 'reused': [], 'status': 'completed', 'gaps': [], 'producer': None})

    def test_current_approved_spec_is_required_for_execution_readiness(self):
        changed = copy.deepcopy(self.spec_data)
        changed['document']['text'] += '\nChanged by human'
        changed['criteria'].append({'id': 'c2', 'text': 'New criterion',
                                    'required': True, 'comparison': 'current'})
        revised = self.store.append('spec', 'spec:80', self.issue_scope, changed)
        revised_approval = self.approve(revised)
        report = self.store.inspect_stage('baseline', 'capture', self.scope,
            {'spec': self.spec, 'approval': self.approval,
             'code_state': self.code, 'environment': self.env}, {})
        self.assertEqual(report['readiness'], 'needs-input')
        self.assertIn('inactive_spec_revision', {item['reason'] for item in report['checks']})
        self.assertIn(self.spec, report['input_refs'])
        current = self.store.inspect_stage('baseline', 'capture', self.scope,
            {'spec': revised, 'approval': revised_approval,
             'code_state': self.code, 'environment': self.env}, {})
        self.assertNotEqual(report['evaluated_against']['hash'], current['evaluated_against']['hash'])

    def test_other_issue_and_other_task_evidence_are_rejected(self):
        other_issue_scope = {**self.project_scope, 'issue_id': 'issue:81'}
        other_issue = self.store.append('work_issue', 'issue:81', self.project_scope,
            {'title': 'Router', 'source': 'https://example.invalid/issues/81',
             'content': 'Route work', 'request_refs': []})
        foreign_spec = self.store.append('spec', 'spec:81', other_issue_scope,
            {'issue': other_issue, 'document': {'path': 'docs/issues/81.md', 'text': '# Router'},
             'criteria': [{'id': 'x', 'text': 'Route', 'required': True, 'comparison': 'current'}]})
        with self.assertRaises(ValueError):
            self.store.append('baseline', 'cross-issue', self.scope,
                {'spec': foreign_spec, 'spec_approval': self.approval,
                 'code_state': self.code, 'environment': self.env,
                 'baseline_kind': 'micro', 'observations': [], 'missing_reason': ''})

        other_task = IdentityRegistry(self.catalog).create_task_lifecycle(
            'project', 'worktree', 'imported', 'a' * 40, 'main', '/fixture', 'env')
        EvidenceStore(self.catalog, EventLog(self.catalog)).put(EvidenceDraft(
            'other-task-proof', other_task.task_id, 'c1', 'test_execution', 'widget',
            'widget', 'pass', 'observed', {'test_id': 'widget'}, b'other task',
            'fixture', 'not_needed'), lambda b: b)
        with self.assertRaises(ValueError):
            self.store.bind_evidence('foreign-task', self.scope, 'other-task-proof')

    def test_unsupported_schema_and_tampered_journal_are_rejected(self):
        database = self.store.path
        self.store.close()
        with sqlite3.connect(database) as connection:
            connection.execute("UPDATE lifecycle_metadata SET value='2' WHERE key='schema_version'")
        with self.assertRaisesRegex(ValueError, 'unsupported lifecycle'):
            lifecycle.LifecycleStore(self.catalog)
        with sqlite3.connect(database) as connection:
            connection.execute("UPDATE lifecycle_metadata SET value='1' WHERE key='schema_version'")
            connection.execute("DROP TRIGGER lifecycle_records_no_update")
            connection.execute("UPDATE lifecycle_records SET data_json='{}' WHERE sequence=1")
        with self.assertRaisesRegex(ValueError, 'fingerprint mismatch'):
            lifecycle.LifecycleStore(self.catalog)

    def test_replay_rejects_activation_with_a_dangling_approval(self):
        changed = copy.deepcopy(self.spec_data)
        changed['document']['text'] += '\nApproved revision'
        revised = self.store.append('spec', 'spec:80', self.issue_scope, changed)
        approval = self.approve(revised)
        database = self.store.path
        self.store.close()
        with sqlite3.connect(database) as connection:
            connection.execute('DROP TRIGGER lifecycle_records_no_delete')
            connection.execute(
                'DELETE FROM lifecycle_records WHERE kind=? AND logical_id=? AND revision=?',
                (approval['kind'], approval['id'], approval['revision']))
        with self.assertRaisesRegex(ValueError, 'unknown or altered lifecycle reference'):
            lifecycle.LifecycleStore(self.catalog)

    def test_direct_execution_outcome_and_shared_readiness_do_not_require_skill(self):
        inputs = {'spec': self.spec, 'approval': self.approval,
                  'code_state': self.code, 'environment': self.env}
        context = {'request': 'Implement approved criteria', 'source': 'conversation:request',
                   'constraints': ['Do not change criteria'], 'change': {'description': 'widget', 'basis': 'inferred'}}
        result = self.store.inspect_stage('baseline', 'capture', self.scope, inputs, context)
        self.assertEqual(result['readiness'], 'ready')
        self.assertEqual(result, self.store.inspect_stage('baseline', 'capture', self.scope, inputs, context))
        outcome = self.store.append('outcome', 'direct:1', self.scope,
            {'stage': 'baseline', 'action': 'capture', 'inputs': list(inputs.values()),
             'outputs': [self.baseline()], 'reused': [self.spec], 'status': 'completed',
             'gaps': [], 'producer': None})
        self.assertIsNone(self.store.get(outcome)['data']['producer'])

    def test_display_only_and_decision_records_do_not_change_semantic_freshness(self):
        review = self.review()
        before = self.store.freshness(review, self.spec, self.code, self.env,
                                      {'widget': 'd' * 64})
        snapshot = self.store.append('snapshot', 'display-snapshot', self.scope, {'review': review})
        self.store.append('human_decision', 'display-decision', self.scope,
            {'snapshot': snapshot, 'actor': {'kind': 'human', 'id': 'owner'},
             'decision': 'accept', 'reason': 'Reviewed', 'source': 'dashboard'})
        self.store.append('outcome', 'display-only', self.scope,
            {'stage': 'review', 'action': 'render', 'inputs': [snapshot], 'outputs': [],
             'reused': [snapshot], 'status': 'completed', 'gaps': [],
             'producer': {'kind': 'dashboard', 'name': 'review-screen', 'version': '1'}})
        self.assertEqual(self.store.freshness(review, self.spec, self.code, self.env,
                                              {'widget': 'd' * 64}), before)

    def test_missing_current_test_meaning_makes_freshness_unknown(self):
        review = self.review()
        result = self.store.freshness(review, self.spec, self.code, self.env, {})
        self.assertEqual(result['state'], 'unknown')
        self.assertEqual(result['unknown'], ['widget'])

    def test_additional_observation_participates_in_semantic_freshness(self):
        additional = self.observation(criterion=None, meaning='e' * 64)
        review = self.review(additions=[additional])
        current = self.store.freshness(review, self.spec, self.code, self.env,
            {'widget': 'd' * 64})
        self.assertEqual(current['state'], 'stale')
        self.assertIn('test_meaning:widget', current['changed'])

    def test_freshness_fixture_covers_input_decision_and_display_changes(self):
        review = self.review()
        revised_data = copy.deepcopy(self.spec_data)
        revised_data['document']['text'] += '\nChanged criterion'
        revised = self.store.append('spec', 'spec:80', self.issue_scope, revised_data)
        changed_code = self.store.append('code_state', 'fixture-code', self.scope,
                                         self.code_state_data('fixture-changed'))
        changed_env = self.store.append('environment', 'fixture-env', self.scope,
                                        lifecycle.environment_state('changed'))
        snapshot = self.store.append('snapshot', 'fixture-snapshot', self.scope, {'review': review})
        current = {'spec': self.spec, 'code': self.code, 'environment': self.env,
                   'meanings': {'widget': 'd' * 64}}
        cases = json.loads((FIXTURES / 'freshness.json').read_text(encoding='utf-8'))
        for index, case in enumerate(cases):
            with self.subTest(case=case['name']):
                values = dict(current)
                if case['change'] == 'spec':
                    values['spec'] = revised
                elif case['change'] == 'code':
                    values['code'] = changed_code
                elif case['change'] == 'environment':
                    values['environment'] = changed_env
                elif case['change'] == 'test':
                    values['meanings'] = {'widget': '0' * 64}
                elif case['change'] == 'unknown-test':
                    values['meanings'] = {}
                elif case['change'] == 'decision':
                    self.store.append('human_decision', f'fixture-decision:{index}', self.scope,
                        {'snapshot': snapshot, 'actor': {'kind': 'human', 'id': 'owner'},
                         'decision': 'accept', 'reason': 'fixture', 'source': 'fixture'})
                elif case['change'] == 'display':
                    self.store.append('outcome', f'fixture-display:{index}', self.scope,
                        {'stage': 'review', 'action': 'render', 'inputs': [snapshot],
                         'outputs': [], 'reused': [snapshot], 'status': 'completed',
                         'gaps': [], 'producer': {'kind': 'dashboard', 'name': 'fixture', 'version': '1'}})
                actual = self.store.freshness(review, values['spec'], values['code'],
                                              values['environment'], values['meanings'])
                self.assertEqual(actual['state'], case['expected'])

    def test_explicit_review_blocker_is_distinct_from_an_unverified_claim(self):
        before = self.observation('before')
        baseline = self.baseline([before])
        after = self.observation()
        review = self.store.append('review', 'blocked-review', self.scope,
            {'spec': self.spec, 'spec_approval': self.approval,
             'code_state': self.code, 'environment': self.env,
             'baseline': baseline, 'claims': [{'criterion_id': 'c1',
                'status': 'inconclusive', 'observations': [after], 'reason': 'Live service unavailable'}],
             'additional_observations': [], 'uncertainties': [], 'inferences': [],
             'blockers': [{'reason': 'required_external_service_unavailable',
                           'source': 'runner:receipt'}]})
        self.assertEqual(self.store.get(review)['data']['review_state'], 'blocked')
        with self.assertRaises(ValueError):
            self.store.append('review', 'vague-blocker-review', self.scope,
                {'spec': self.spec, 'spec_approval': self.approval,
                 'code_state': self.code, 'environment': self.env, 'baseline': baseline,
                 'claims': [{'criterion_id': 'c1', 'status': 'inconclusive',
                             'observations': [], 'reason': 'Impact is merely possible'}],
                 'additional_observations': [], 'uncertainties': [], 'inferences': [],
                 'blockers': [{'reason': 'possible_indirect_impact', 'source': 'agent:guess'}]})

    def test_unknown_scope_or_phase_is_not_ready(self):
        with self.assertRaises(ValueError):
            self.store.inspect_stage('tdd', 'run', self.scope, {}, {})
        report = self.store.inspect_stage('review', 'compose', self.scope,
            {'spec': self.spec, 'approval': self.approval,
             'code_state': self.code, 'environment': self.env}, {})
        self.assertEqual(report['readiness'], 'needs-input')
        self.assertIn('baseline', {item['input'] for item in report['checks']
                                  if item['status'] == 'missing'})
        complete = self.store.inspect_stage('review', 'complete', self.scope, {}, {})
        self.assertEqual(complete['readiness'], 'needs-input')

    def test_readiness_rejects_wrong_artifact_kind_and_requires_request_source(self):
        wrong = self.store.inspect_stage('baseline', 'capture', self.scope,
            {'spec': self.spec, 'approval': self.approval,
             'code_state': self.spec, 'environment': self.env}, {})
        self.assertEqual(wrong['readiness'], 'invalid')
        self.assertIn('unexpected_artifact_kind', {item['reason'] for item in wrong['checks']})
        self.assertEqual(self.store.inspect_stage('goal', 'discover', self.project_scope,
                                                  {}, {})['readiness'], 'needs-input')
        ready = self.store.inspect_stage('goal', 'discover', self.project_scope, {},
            {'request': 'Find a verifiable goal', 'source': 'conversation:1'})
        self.assertEqual(ready['readiness'], 'ready')

    def test_spec_activation_readiness_checks_approval_decision_and_binding(self):
        rejected = self.store.append('spec_approval', 'rejected', self.issue_scope,
            {'spec': self.spec, 'actor': {'kind': 'human', 'id': 'owner'},
             'decision': 'rejected', 'reason': 'Business condition changed',
             'source': 'conversation:rejection'})
        report = self.store.inspect_stage('spec', 'activate', self.issue_scope,
            {'spec': self.spec, 'approval': rejected}, {})
        self.assertEqual(report['readiness'], 'invalid')
        self.assertIn('approval_not_usable', {item['reason'] for item in report['checks']})

    def test_readiness_validates_cross_input_relationships(self):
        baseline = self.baseline([self.observation('before')])
        other_env = self.store.append('environment', 'readiness-env', self.scope,
            lifecycle.environment_state('other'))
        report = self.store.inspect_stage('review', 'compose', self.scope,
            {'spec': self.spec, 'approval': self.approval, 'code_state': self.code,
             'environment': other_env, 'baseline': baseline}, {})
        self.assertEqual(report['readiness'], 'invalid')
        self.assertIn('baseline_input_mismatch', {item['reason'] for item in report['checks']})

        micro = self.store.append('baseline', 'readiness-micro', self.scope,
            {'spec': self.spec, 'spec_approval': self.approval,
             'code_state': self.code, 'environment': self.env,
             'baseline_kind': 'micro', 'observations': [], 'missing_reason': ''})
        micro_report = self.store.inspect_stage('review', 'compose', self.scope,
            {'spec': self.spec, 'approval': self.approval, 'code_state': self.code,
             'environment': self.env, 'baseline': micro}, {})
        self.assertEqual(micro_report['readiness'], 'invalid')
        self.assertIn('baseline_not_verification', {item['reason'] for item in micro_report['checks']})

        first_review = self.review()
        second_review = self.store.append('review', 'review:2', self.scope,
            {**self.store.get(first_review)['data']})
        snapshot = self.store.append('snapshot', 'first-snapshot', self.scope,
                                     {'review': first_review})
        complete = self.store.inspect_stage('review', 'complete', self.scope,
            {'review': second_review, 'snapshot': snapshot}, {})
        self.assertEqual(complete['readiness'], 'invalid')
        self.assertIn('snapshot_review_mismatch', {item['reason'] for item in complete['checks']})


class CodeStateTests(unittest.TestCase):
    def test_same_commit_untracked_tracked_and_mode_changes_have_different_identity(self):
        with tempfile.TemporaryDirectory() as root:
            repo = Path(root)
            def git(*args):
                return subprocess.run(['git', '-C', root, *args], check=True,
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE).stdout
            git('init', '-q'); git('config', 'user.name', 'Fixture'); git('config', 'user.email', 'fixture@example.invalid')
            (repo / 'a').write_text('one'); git('add', '.'); git('commit', '-qm', 'fixture')
            first = lifecycle.capture_code_state(repo)
            (repo / 'new').write_text('new')
            second = lifecycle.capture_code_state(repo)
            (repo / 'a').write_text('two')
            third = lifecycle.capture_code_state(repo)
            (repo / 'a').chmod(0o755)
            fourth = lifecycle.capture_code_state(repo)
            (repo / 'link').symlink_to('a')
            fifth = lifecycle.capture_code_state(repo)
            (repo / 'link').unlink()
            (repo / 'link').symlink_to('new')
            sixth = lifecycle.capture_code_state(repo)
            (repo / 'a').unlink()
            seventh = lifecycle.capture_code_state(repo)
            states = [first, second, third, fourth, fifth, sixth, seventh]
            self.assertEqual(first['commit'], seventh['commit'])
            self.assertEqual(len({state['fingerprint'] for state in states}), len(states))
            self.assertEqual(next(item for item in fifth['files'] if item['path'] == 'link')['kind'], 'symlink')
            self.assertNotEqual(next(item for item in fifth['files'] if item['path'] == 'link')['hash'],
                                next(item for item in sixth['files'] if item['path'] == 'link')['hash'])
            self.assertEqual(next(item for item in seventh['files'] if item['path'] == 'a')['kind'], 'missing')

    def test_ignored_content_is_declared_outside_the_fingerprint_scope(self):
        with tempfile.TemporaryDirectory() as root:
            repo = Path(root)
            def git(*args):
                return subprocess.run(['git', '-C', root, *args], check=True,
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE).stdout
            git('init', '-q'); git('config', 'user.name', 'Fixture'); git('config', 'user.email', 'fixture@example.invalid')
            (repo / '.gitignore').write_text('private/\n')
            (repo / 'a').write_text('one')
            git('add', '.'); git('commit', '-qm', 'fixture')
            (repo / 'private').mkdir(); (repo / 'private' / 'secret').write_text('not captured')
            state = lifecycle.capture_code_state(repo)
            self.assertEqual(state['coverage'], 'partial')
            self.assertIn('private/secret', {item['area'] for item in state['exclusions']})
