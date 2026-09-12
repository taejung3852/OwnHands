"""Claim rules exercised through the real journal and Evidence store."""
import copy
import unittest

import tests.test_lifecycle as fixtures
from devharness import lifecycle
from devharness.evidence import EvidenceDraft, EvidenceStore
from devharness.events import EventLog


class ClaimEvaluationTests(unittest.TestCase):
    code_state_data = staticmethod(fixtures.LifecycleTests.code_state_data)
    approve = fixtures.LifecycleTests.approve
    tearDown = fixtures.LifecycleTests.tearDown

    def setUp(self):
        fixtures.LifecycleTests.setUp(self)
        self.configure()

    def configure(self, comparison='current', checks=('normal',), optional=False):
        data = copy.deepcopy(self.spec_data)
        data['contract_version'] = 2
        self.generation = getattr(self, 'generation', 0) + 1
        data['document']['text'] += '\nFixture scenario ' + str(self.generation)
        data['criteria'][0].update(comparison=comparison, required=not optional,
            checks=[{'check_id': c, 'statement': 'Must satisfy ' + c,
                     'role': 'success_condition' if c == 'normal' else 'counterexample'} for c in checks])
        self.spec = self.store.append('spec', 'spec:82', self.issue_scope, data)
        self.approval = self.approve(self.spec)
        self.checks = checks

    def observe(self, result='pass', phase='after', check='normal', execution_id=None,
                environment=None, code=None, meaning='d' * 64, failure_kind=None,
                execution_status='completed', end_code=None, origin='live', test_id=None, criterion='c1', environment_complete=True, content=None):
        self.counter += 1
        code = code or self.code
        execution = {'id': execution_id or 'run:' + str(self.counter), 'status': execution_status,
            'failure_kind': failure_kind or ('requirement_violation' if result == 'fail' else 'none'),
            'producer': 'fixture runner', 'started_at': '2026-09-13T00:00:00Z',
            'finished_at': '2026-09-13T00:00:01Z', 'origin': origin,
            'code_start': code, 'code_end': end_code or code,
            'environment_complete': environment_complete, 'provenance': 'fixture captured execution'}
        fields = {'test_id': test_id or 'test:' + check, 'criterion_id': criterion, 'check_id': check,
                  'phase': phase, 'spec_hash': self.spec['hash'], 'code_hash': code['hash'],
                  'environment_hash': (environment or self.env)['hash'],
                  'test_meaning': meaning, 'execution': execution}
        eid = 'evidence:' + str(self.counter)
        EvidenceStore(self.catalog, EventLog(self.catalog)).put(EvidenceDraft(
            eid, self.task.task_id, 'c1', 'test_execution', 'test:' + check, check,
            result, 'observed', fields, content or ('fixture result=' + result).encode(),
            'fixture runner', 'not_needed'), lambda b: b)
        binding = self.store.bind_evidence('binding:' + str(self.counter), self.scope, eid)
        data = {'contract_version': 2, 'spec': self.spec, 'spec_approval': self.approval,
            'code_state': code, 'environment': environment or self.env,
            'test_id': test_id or 'test:' + check, 'criterion_id': criterion, 'check_id': check,
            'phase': phase, 'test_meaning': meaning, 'result': result, 'basis': 'observed',
            'selection_reason': 'Checks approved behavior', 'evidence': [binding], 'execution': execution}
        return self.store.append('observation', 'obs:' + str(self.counter), self.scope, data)

    def inputs(self, before=(), environment=None, code=None, blockers=None):
        baseline = self.store.append('baseline', 'baseline:82', self.scope,
            {'contract_version': 2, 'spec': self.spec, 'spec_approval': self.approval,
             'code_state': self.code, 'environment': self.env, 'baseline_kind': 'verification',
             'observations': list(before), 'missing_reason': '' if before else 'Before not run',
             'provenance': 'Captured pre-change fixture snapshot'})
        return {'contract_version': 2, 'spec': self.spec, 'spec_approval': self.approval,
            'baseline': baseline, 'code_state': code or self.code, 'environment': environment or self.env,
            'test_plan': [{'criterion_id': 'c1', 'check_id': c, 'test_id': 'test:' + c,
                           'test_meaning': 'd' * 64} for c in self.checks],
            'blockers': blockers or [], 'findings': [], 'exclusions': []}

    def evaluate(self, **kwargs):
        self.assertTrue(callable(getattr(self.store, 'evaluate_review', None)),
                        'Store must derive Claim results from all matching observations')
        return self.store.evaluate_review(self.scope, self.inputs(**kwargs))

    def test_truth_table(self):
        cases = [('current', None, 'pass', 'verified'), ('current', None, 'fail', 'failed'),
            ('preserve', 'pass', 'pass', 'verified'), ('preserve', 'fail', 'pass', 'inconclusive'),
            ('preserve', None, 'pass', 'inconclusive'), ('improve', 'fail', 'pass', 'verified'),
            ('improve', 'pass', 'pass', 'inconclusive'), ('improve', None, 'pass', 'inconclusive'),
            ('improve', 'fail', 'fail', 'failed'), ('current', None, None, 'unobserved')]
        for comparison, before, after, expected in cases:
            with self.subTest(comparison=comparison, before=before, after=after):
                self.configure(comparison)
                left = [self.observe(before, 'before')] if before else []
                if after:
                    self.observe(after)
                result = self.evaluate(before=left)
                self.assertEqual(result['claims'][0]['status'], expected)

    def test_failure_is_not_hidden_by_a_later_pass_or_missing_check(self):
        self.configure(checks=('normal', 'concurrent', 'retry'))
        failed = self.observe('fail', check='concurrent')
        self.observe(check='concurrent')
        self.observe()
        result = self.evaluate()
        self.assertEqual(result['claims'][0]['status'], 'failed')
        self.assertEqual(result['coverage']['checks']['unobserved'], 1)
        self.assertIn(failed, result['claims'][0]['observations'])

    def test_same_execution_conflict_shows_both_sources(self):
        first = self.observe('pass', execution_id='same')
        second = self.observe('fail', execution_id='same')
        result = self.evaluate()
        check = result['claims'][0]['checks'][0]
        self.assertEqual(check['status'], 'inconclusive')
        self.assertEqual(set(r['id'] for r in check['conflicts'][0]['observations']),
                         {first['id'], second['id']})
        self.observe('fail')
        self.assertEqual(self.evaluate()['claims'][0]['status'], 'failed')

    def test_environment_difference_is_storable_as_inconclusive(self):
        self.configure('preserve')
        left = self.observe(phase='before')
        env = self.store.append('environment', 'env:changed', self.scope, lifecycle.environment_state('changed'))
        self.observe(environment=env)
        data = self.evaluate(before=[left], environment=env)
        self.assertEqual(data['claims'][0]['status'], 'inconclusive')
        ref = self.store.append('review', 'review:82', self.scope, data)
        self.assertEqual(self.store.get(ref)['data']['review_state'], 'needs-review')

    def test_optional_failure_and_optional_unavailable_need_attention(self):
        self.configure(optional=True)
        self.observe('fail')
        result = self.evaluate()
        self.assertTrue(result['required_complete'])
        self.assertEqual(result['review_state'], 'needs-review')
        self.configure(optional=True)
        self.observe('inconclusive', failure_kind='execution_error', execution_status='error')
        self.assertEqual(self.evaluate()['review_state'], 'needs-review')

    def test_required_blocker_preserves_other_results(self):
        self.configure(checks=('normal', 'concurrent'))
        self.observe('fail')
        result = self.evaluate(blockers=[{'criterion_id':'c1', 'check_id':'concurrent',
            'reason':'required_external_service_unavailable', 'source':'runner:service unavailable'}])
        self.assertEqual(result['review_state'], 'blocked')
        self.assertEqual(result['claims'][0]['status'], 'failed')

    def test_forged_summary_cannot_bypass_store(self):
        self.observe('fail')
        data = self.evaluate()
        data['claims'][0]['status'] = 'verified'
        with self.assertRaises(ValueError):
            self.store.append('review', 'forged', self.scope, data)

    def test_additional_evidence_requires_new_evaluation(self):
        self.observe()
        data = self.evaluate()
        ref = self.store.append('review', 'first', self.scope, data)
        self.observe('fail')
        with self.assertRaises(ValueError):
            self.store.append('review', 'outdated', self.scope, data)
        self.assertTrue(self.store.review_status(ref)['new_evidence_available'])
        self.assertEqual(self.store.get(ref)['data']['claims'][0]['status'], 'verified')

    def test_code_change_cannot_inherit_old_pass(self):
        self.observe()
        code = self.store.append('code_state','code:new',self.scope,self.code_state_data('new'))
        result = self.evaluate(code=code)
        self.assertEqual(result['claims'][0]['status'], 'unobserved')

    def test_changed_test_meaning_and_execution_error_do_not_verify(self):
        self.configure('preserve')
        left = self.observe(phase='before', meaning='e' * 64)
        self.observe()
        self.assertEqual(self.evaluate(before=[left])['claims'][0]['status'], 'inconclusive')
        self.configure()
        self.observe('fail', execution_status='error', failure_kind='execution_error')
        result=self.evaluate()
        self.assertEqual(result['claims'][0]['status'], 'inconclusive')
        self.assertEqual(result['review_state'], 'blocked')


    def test_all_approved_checks_remain_visible(self):
        self.configure(checks=('normal', 'retry'))
        self.observe()
        result = self.evaluate()
        self.assertEqual(result['claims'][0]['status'], 'inconclusive')
        self.assertEqual(result['coverage']['checks']['total'], 2)
        self.assertEqual(result['coverage']['checks']['unobserved'], 1)

    def test_missing_planned_test_cannot_be_hidden_by_other_pass(self):
        self.observe()
        inputs = self.inputs()
        inputs['test_plan'].append({'criterion_id':'c1','check_id':'normal',
            'test_id':'second-test','test_meaning':'d'*64})
        result=self.store.evaluate_review(self.scope,inputs)
        self.assertEqual(result['claims'][0]['status'],'inconclusive')

    def test_intentionally_excluded_optional_is_distinct_from_execution_failure(self):
        self.configure(optional=True)
        inputs=self.inputs()
        inputs['exclusions']=[{'criterion_id':'c1','reason':'Not selected for this change'}]
        result=self.store.evaluate_review(self.scope,inputs)
        self.assertEqual(result['review_state'],'ready')
        self.assertEqual(result['coverage']['optional']['unobserved'],1)
        self.observe('inconclusive',execution_status='error',failure_kind='execution_error')
        self.assertEqual(self.store.evaluate_review(self.scope,inputs)['review_state'],'needs-review')

    def test_downgrade_cannot_bypass_approved_v2_spec(self):
        ref=self.observe()
        d=self.store.get(ref)['data'];d.pop('contract_version')
        with self.assertRaises(ValueError):
            self.store.append('observation','downgraded',self.scope,d)

    def test_other_task_evidence_is_rejected(self):
        ref=self.observe()
        d=self.store.get(ref)['data']
        from devharness.identity import IdentityRegistry
        other=IdentityRegistry(self.catalog).create_task_lifecycle(
            'other','worktree','imported','a'*40,'main','/other','env')
        raw=EvidenceStore(self.catalog,EventLog(self.catalog))
        original=raw.resolve('evidence:1')
        raw.put(EvidenceDraft('foreign',other.task_id,'c1','test_execution','test:normal','normal',
            'pass','observed',original.fields,b'foreign output','runner','not_needed'),lambda b:b)
        with self.assertRaises(ValueError):
            self.store.bind_evidence('foreign-binding',self.scope,'foreign')

    def test_corrupt_after_is_reported_without_inserting_invalid_reference(self):
        ref=self.observe()
        raw=EvidenceStore(self.catalog,EventLog(self.catalog)).resolve('evidence:1')
        from pathlib import Path
        Path(raw.object_path).write_bytes(b'corrupt')
        data=self.evaluate()
        self.assertEqual(data['claims'][0]['status'],'unobserved')
        self.assertEqual(data['review_state'],'blocked')
        self.assertEqual(data['diagnostics'][0]['rejected_input_id'],ref['id'])
        saved=self.store.append('review','corrupt-report',self.scope,data)
        self.assertEqual(self.store.get(saved)['data']['review_state'],'blocked')

    def test_execution_code_changes_and_equal_recapture(self):
        same=self.store.append('code_state','recaptured',self.scope,self.code_state_data())
        self.observe(end_code=same)
        self.assertEqual(self.evaluate()['claims'][0]['status'],'verified')
        self.configure()
        changed=self.store.append('code_state','changed',self.scope,self.code_state_data('changed'))
        self.observe(end_code=changed)
        self.assertEqual(self.evaluate()['claims'][0]['status'],'inconclusive')

    def test_same_run_conflicting_metadata_is_not_a_valid_failure(self):
        self.observe('pass',execution_id='same')
        self.observe('fail',execution_id='same',meaning='e'*64)
        self.assertEqual(self.evaluate()['claims'][0]['status'],'inconclusive')

    def test_same_environment_content_with_new_id_is_comparable(self):
        self.configure('preserve')
        left=self.observe(phase='before')
        env=self.store.append('environment','env:same',self.scope,lifecycle.environment_state('fixture'))
        self.observe(environment=env)
        self.assertEqual(self.evaluate(before=[left],environment=env)['claims'][0]['status'],'verified')

    def test_conflicting_before_cannot_be_cherry_picked(self):
        self.configure('preserve')
        left=self.observe(phase='before')
        self.observe('fail',phase='before')
        self.observe()
        self.assertEqual(self.evaluate(before=[left])['claims'][0]['status'],'inconclusive')

    def test_reconstructed_origin_is_preserved_and_human_decision_cannot_rewrite(self):
        self.configure('improve')
        left=self.observe('fail',phase='before',origin='reconstructed')
        self.observe()
        data=self.evaluate(before=[left])
        ref=self.store.append('review','restored',self.scope,data)
        snapshot=self.store.append('snapshot','snap',self.scope,{'review':ref})
        self.store.append('human_decision','decision',self.scope,{'snapshot':snapshot,
            'actor':{'kind':'human','id':'owner'},'decision':'defer','reason':'Pending inspection','source':'user'})
        self.assertEqual(self.store.get(ref)['data'],data)
        self.assertEqual(self.store.get(left)['data']['execution']['origin'],'reconstructed')
        self.assertFalse(self.store.review_status(ref)['new_evidence_available'])


    def test_equal_code_and_environment_recapture_cannot_hide_failed_run(self):
        failed=self.observe('fail')
        code=self.store.append('code_state','same:new',self.scope,self.code_state_data())
        env=self.store.append('environment','same:env',self.scope,lifecycle.environment_state('fixture'))
        self.observe(code=code,environment=env)
        result=self.evaluate(code=code,environment=env)
        self.assertEqual(result['claims'][0]['status'],'failed')
        self.assertIn(failed,result['claims'][0]['observations'])

    def test_before_conflict_is_attention_even_for_current_claim(self):
        self.observe('pass',phase='before',execution_id='before-run')
        self.observe('fail',phase='before',execution_id='before-run')
        self.observe()
        result=self.evaluate()
        self.assertEqual(result['claims'][0]['status'],'verified')
        self.assertEqual(result['review_state'],'needs-review')

    def test_same_execution_with_different_test_id_is_conflicting_metadata(self):
        self.observe('pass',execution_id='same')
        self.observe('fail',execution_id='same',test_id='other-name')
        result=self.evaluate()
        self.assertEqual(result['claims'][0]['status'],'inconclusive')
        self.assertEqual(len(result['claims'][0]['checks'][0]['conflicts']),1)

    def test_invalid_before_does_not_block_current(self):
        self.observe('pass',phase='before')
        from pathlib import Path
        raw=EvidenceStore(self.catalog,EventLog(self.catalog)).resolve('evidence:1')
        Path(raw.object_path).write_bytes(b'corrupt')
        self.observe('inconclusive',failure_kind='unknown')
        result=self.evaluate()
        self.assertEqual(result['claims'][0]['status'],'inconclusive')
        self.assertEqual(result['review_state'],'needs-review')


    def test_historical_status_does_not_apply_new_spec_approval_to_old_receipts(self):
        self.observe()
        old=self.store.append('review','historical',self.scope,self.evaluate())
        self.configure('preserve')
        status=self.store.review_status(old)
        self.assertTrue(status['readable'])
        self.assertEqual(status['diagnostics'],[])

    def test_receipt_cannot_claim_fields_different_from_raw_evidence(self):
        ref=self.observe()
        data=self.store.get(ref)['data'];data['execution']['id']='fabricated'
        with self.assertRaises(ValueError):
            self.store.append('observation','mislabeled',self.scope,data)

    def test_unknown_version_and_empty_checks_are_rejected(self):
        data=copy.deepcopy(self.store.get(self.spec)['data'])
        data['contract_version']=3
        with self.assertRaises(ValueError):
            self.store.append('spec','unsupported',self.issue_scope,data)
        data['contract_version']=2;data['criteria'][0]['checks']=[]
        with self.assertRaises(ValueError):
            self.store.append('spec','empty',self.issue_scope,data)

    def test_stage_readiness_accepts_valid_different_phase_environments(self):
        env=self.store.append('environment','new-env',self.scope,lifecycle.environment_state('new'))
        i=self.inputs(environment=env)
        result=self.store.inspect_stage('review','compose',self.scope,
            {'spec':i['spec'],'approval':i['spec_approval'],'baseline':i['baseline'],
             'code_state':i['code_state'],'environment':i['environment']}, {})
        self.assertEqual(result['readiness'],'ready')


    def test_additional_defect_keeps_required_completion_and_attention(self):
        self.observe()
        extra=self.observe('fail',check='outside-spec',criterion=None)
        result=self.evaluate()
        self.assertTrue(result['required_complete'])
        self.assertEqual(result['review_state'],'needs-review')
        self.assertIn(extra,result['additional_observations'])
        self.assertTrue(result['findings'])

    def test_unknown_environment_and_not_run_never_verify(self):
        self.observe(environment_complete=False)
        self.assertEqual(self.evaluate()['claims'][0]['status'],'inconclusive')
        self.configure()
        self.observe('not_run',execution_status='not_started')
        self.assertEqual(self.evaluate()['claims'][0]['status'],'unobserved')

    def test_saved_review_freshness_is_separate_from_claim(self):
        self.observe()
        ref=self.store.append('review','freshness',self.scope,self.evaluate())
        changed=self.store.append('code_state','freshness:new',self.scope,self.code_state_data('changed'))
        fresh=self.store.freshness(ref,self.spec,changed,self.env,{'test:normal':'d'*64})
        self.assertEqual(fresh['state'],'stale')
        self.assertEqual(self.store.get(ref)['data']['claims'][0]['status'],'verified')


    def corrupt_evidence(self, evidence_id):
        from pathlib import Path
        raw = EvidenceStore(self.catalog, EventLog(self.catalog)).resolve(evidence_id)
        Path(raw.object_path).write_bytes(b'corrupted evidence')

    def test_corrupt_failure_plus_pass_cannot_complete_required_check(self):
        self.configure(checks=('normal', 'retry'))
        bad = self.observe('fail')
        self.corrupt_evidence('evidence:1')
        self.observe()
        self.observe(check='retry')
        data = self.evaluate()
        claim = data['claims'][0]
        self.assertEqual(claim['status'], 'inconclusive')
        self.assertEqual([c['status'] for c in claim['checks']], ['inconclusive', 'verified'])
        self.assertFalse(data['required_complete'])
        self.assertEqual(data['coverage']['required']['verified'], 0)
        self.assertEqual(data['review_state'], 'blocked')
        self.assertEqual(data['blockers'], [{'criterion_id': 'c1', 'check_id': 'normal',
            'reason': 'invalid_required_evidence', 'source': bad['id']}])
        self.assertEqual(claim['checks'][0]['diagnostics'][0]['rejected_input_id'], bad['id'])
        stored = self.store.append('review', 'integrity-report', self.scope, data)
        self.assertFalse(self.store.get(stored)['data']['required_complete'])
        self.assertNotIn(bad, claim['observations'])

    def test_corrupt_optional_failure_does_not_undo_required_completion(self):
        self.configure(optional=True)
        spec = copy.deepcopy(self.store.get(self.spec)['data'])
        spec['criteria'].append({'id': 'c2', 'text': 'Required goal', 'required': True,
            'comparison': 'current', 'checks': [{'check_id': 'normal', 'statement': 'Required behavior',
                                               'role': 'success_condition'}]})
        self.spec = self.store.append('spec', 'spec:82', self.issue_scope, spec)
        self.approval = self.approve(self.spec)
        self.observe('fail')
        self.corrupt_evidence('evidence:1')
        self.observe()
        self.observe(criterion='c2')
        inputs = self.inputs()
        inputs['test_plan'].append({'criterion_id': 'c2', 'check_id': 'normal',
                                   'test_id': 'test:normal', 'test_meaning': 'd' * 64})
        data = self.store.evaluate_review(self.scope, inputs)
        self.assertEqual(data['claims'][0]['status'], 'inconclusive')
        self.assertEqual(data['claims'][1]['status'], 'verified')
        self.assertEqual(data['coverage']['required']['verified'], 1)
        self.assertTrue(data['required_complete'])
        self.assertEqual(data['blockers'], [])
        self.assertEqual(data['review_state'], 'needs-review')

    def test_corruption_does_not_override_independently_observed_failure(self):
        self.observe('fail')
        self.corrupt_evidence('evidence:1')
        self.observe('fail', content=b'independent observed requirement violation')
        self.observe()
        data = self.evaluate()
        self.assertEqual(data['claims'][0]['status'], 'failed')
        self.assertFalse(data['required_complete'])
        self.assertEqual(data['review_state'], 'needs-review')
        self.assertEqual(data['blockers'], [])
        self.assertTrue(data['diagnostics'])

    def test_corrupt_before_plus_valid_after_respects_comparison_type(self):
        cases = [('current', 'pass', 'verified', True, 'needs-review'),
                 ('preserve', 'pass', 'inconclusive', False, 'blocked'),
                 ('improve', 'fail', 'inconclusive', False, 'blocked')]
        for comparison, valid_before, expected, complete, review in cases:
            with self.subTest(comparison=comparison):
                self.configure(comparison)
                bad = self.observe('fail', phase='before', content=('bad ' + comparison).encode())
                self.corrupt_evidence('evidence:' + str(self.counter))
                left = self.observe(valid_before, phase='before', content=('good ' + comparison).encode())
                self.observe()
                data = self.evaluate(before=[left])
                self.assertEqual(data['claims'][0]['status'], expected)
                self.assertEqual(data['required_complete'], complete)
                self.assertEqual(data['review_state'], review)
                self.assertEqual(data['diagnostics'][0]['rejected_input_id'], bad['id'])


if __name__ == '__main__':
    unittest.main()
