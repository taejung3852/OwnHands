"""Deterministic rules over resolved lifecycle records; no execution or I/O."""
from collections import Counter, defaultdict
from .model import canonical_json

RULES_VERSION = 2


def _summary(states):
    counts = Counter(states)
    return {"total": sum(counts.values()), **{s: counts[s] for s in
            ("verified", "failed", "inconclusive", "unobserved")}}


def _status(states):
    if "failed" in states:
        return "failed"
    if states and all(s == "verified" for s in states):
        return "verified"
    return "unobserved" if all(s == "unobserved" for s in states) else "inconclusive"


def _runs(records):
    groups = defaultdict(list)
    for record in records:
        d = record['data']
        groups[(d['execution']['id'],)].append(record)
    results, conflicts = [], []
    for key, items in sorted(groups.items()):
        outcomes = {canonical_json([r['data']['result'], r['data']['basis'],
                    r['data']['test_id'], r['data']['test_meaning'], r['data']['execution']]) for r in items}
        refs = [r['ref'] for r in items]
        if len(outcomes) > 1:
            conflicts.append({'execution_id': key[0], 'observations': refs,
                              'reason_code': 'conflicting_execution_results'})
            results.append(('unknown', items[0]))
            continue
        d = items[0]['data']
        e = d['execution']
        if d['result'] == 'not_run' or d['basis'] == 'unobserved':
            verdict = 'missing'
        elif (d['basis'] != 'observed' or not d['evidence'] or e['status'] != 'completed'
              or not items[0]['code_consistent']
              or not e['environment_complete']):
            verdict = 'unknown'
        elif d['result'] == 'fail' and e['failure_kind'] == 'requirement_violation':
            verdict = 'fail'
        elif d['result'] == 'pass' and e['failure_kind'] == 'none':
            verdict = 'pass'
        else:
            verdict = 'unknown'
        results.append((verdict, items[0]))
    return results, conflicts


def evaluate_claim(criterion, observations, test_plan, diagnostics=()):
    """Caller resolves evidence/scope. Store recomputes before persisting this result."""
    checks = []
    for check in criterion['checks']:
        records = [r for r in observations if r['data'].get('criterion_id') == criterion['id']
                   and r['data'].get('check_id') == check['check_id']]
        after, conflicts = _runs([r for r in records if r['data']['phase'] == 'after'])
        before, before_conflicts = _runs([r for r in records if r['data']['phase'] == 'before'])
        plan = [p for p in test_plan if p['criterion_id'] == criterion['id']
                and p['check_id'] == check['check_id']]
        reasons, comparisons = [], []
        if any(v == 'fail' for v, _ in after):
            state, reasons = 'failed', ['observed_requirement_violation']
        elif not after or all(v == 'missing' for v, _ in after):
            state, reasons = 'unobserved', ['after_not_observed']
        else:
            if any(v == 'unknown' for v, _ in after):
                reasons.append('after_uncertain_or_conflicting')
            if not plan:
                reasons.append('test_plan_missing')
            for p in plan:
                matching = [(v, r) for v, r in after if r['data']['test_id'] == p['test_id']
                            and r['data']['test_meaning'] == p['test_meaning']]
                if not matching or any(v != 'pass' for v, _ in matching):
                    reasons.append('planned_test_not_verified')
                    continue
                if criterion['comparison'] == 'current':
                    continue
                left = [(v, r) for v, r in before if r['data']['test_id'] == p['test_id']]
                right = matching[0][1]
                same = [(v, r) for v, r in left if r['data']['test_meaning'] == p['test_meaning']
                        and r['environment_fingerprint'] == right['environment_fingerprint']]
                expected = 'pass' if criterion['comparison'] == 'preserve' else 'fail'
                # Every observed Before run counts; a convenient result cannot hide a conflict.
                comparable = bool(same) and all(v == expected for v, _ in same)
                comparisons.append({'test_id': p['test_id'], 'comparable': comparable,
                    'before': [r['ref'] for _, r in left],
                    'after': [r['ref'] for _, r in matching], 'expected_before': expected})
                if not comparable:
                    reasons.append('before_missing_incomparable_or_wrong_result')
            state = 'inconclusive' if reasons else 'verified'
        relevant_diagnostics = [d for d in diagnostics
            if d.get('criterion_id') == criterion['id'] and d.get('check_id') == check['check_id']
            and (d.get('phase') == 'after' or criterion['comparison'] != 'current')]
        if relevant_diagnostics and state == 'verified':
            state, reasons = 'inconclusive', ['relevant_evidence_invalid']
        checks.append({**check, 'status': state, 'diagnostics': relevant_diagnostics,
            'reason_codes': sorted(set(reasons)) or ['requirements_observed'],
            'observations': [r['ref'] for r in records],
            'evidence': [e for r in records for e in r['data']['evidence']],
            'comparability': comparisons, 'conflicts': conflicts + before_conflicts})
    state = _status([c['status'] for c in checks])
    return {'criterion_id': criterion['id'], 'required': criterion['required'],
            'comparison': criterion['comparison'], 'status': state,
            'reason': 'All approved checks evaluated; inspect per-check reasons.',
            'checks': checks, 'observations': [r['ref'] for r in observations
                if r['data'].get('criterion_id') == criterion['id']]}


def evaluate_review(criteria, observations, test_plan, blockers, findings, exclusions, diagnostics):
    claims = [evaluate_claim(c, observations, test_plan, diagnostics) for c in criteria]
    required = [c for c in claims if c['required']]
    complete = all(c['status'] == 'verified' for c in required)
    excluded = {e['criterion_id'] for e in exclusions}
    attention = (not complete or bool(findings) or bool(diagnostics)
                 or any(k['conflicts'] for c in claims for k in c['checks']) or any(
        c['status'] != 'verified' and not (not c['required'] and c['status'] == 'unobserved'
                                         and c['criterion_id'] in excluded) for c in claims))
    active_blockers = list(blockers)
    for c in claims:
        for check in c['checks']:
            if not c['required'] or check['status'] == 'verified':
                continue
            for diagnostic in diagnostics:
                if (check['status'] in {'unobserved', 'inconclusive'}
                        and (diagnostic.get('phase') == 'after' or c['comparison'] != 'current')
                        and diagnostic.get('criterion_id') == c['criterion_id']
                        and diagnostic.get('check_id') == check['check_id']):
                    active_blockers.append({'criterion_id': c['criterion_id'], 'check_id': check['check_id'],
                        'reason': 'invalid_required_evidence', 'source': diagnostic['rejected_input_id']})
            for r in observations:
                d = r['data']
                if (d.get('criterion_id') == c['criterion_id'] and d.get('check_id') == check['check_id']
                        and d['phase'] == 'after' and d['execution']['status'] == 'error'):
                    active_blockers.append({'criterion_id': c['criterion_id'], 'check_id': check['check_id'],
                        'reason': 'verification_execution_failed', 'source': d['execution']['id']})
    return {'rules_version': RULES_VERSION, 'claims': claims,
        'required_complete': complete,
        'review_state': 'blocked' if active_blockers else 'needs-review' if attention else 'ready',
        'blockers': active_blockers, 'findings': findings, 'diagnostics': diagnostics,
        'coverage': {'required': _summary([c['status'] for c in required]),
                     'optional': _summary([c['status'] for c in claims if not c['required']]),
                     'checks': _summary([k['status'] for c in claims for k in c['checks']])},
        'gaps': [{'criterion_id': c['criterion_id'], 'check_id': k['check_id'],
                  'status': k['status'], 'reasons': k['reason_codes']}
                 for c in claims for k in c['checks'] if k['status'] in {'unobserved', 'inconclusive'}]}
