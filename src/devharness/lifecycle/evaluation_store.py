"""Versioned evaluator boundary. Legacy storage and Evidence remain authoritative."""
import json
from datetime import datetime

from .evaluation import evaluate_review
from .model import canonical_json, fingerprint, reference, require_sha256, require_text

INPUT_KEYS = {'contract_version', 'spec', 'spec_approval', 'baseline', 'code_state', 'environment',
              'test_plan', 'blockers', 'findings', 'exclusions'}


def validate_v2(store, kind, scope, data, *, active=True):
    if kind == 'spec':
        for criterion in data.get('criteria', []):
            checks = criterion.get('checks')
            if not isinstance(checks, list) or not checks:
                raise ValueError('v2 criterion requires non-empty checks')
            ids = []
            for check in checks:
                ids.append(require_text(check.get('check_id'), 'check_id'))
                require_text(check.get('statement'), 'check statement')
                if check.get('role') not in {'success_condition', 'counterexample'}:
                    raise ValueError('unsupported check role')
            if len(ids) != len(set(ids)):
                raise ValueError('duplicate check_id')
        return
    spec = (store._require_approved_spec(data, scope) if active
            else store._require_kind(data.get('spec'), 'spec', scope))
    if spec['data'].get('contract_version') != 2:
        raise ValueError('v2 artifact requires approved v2 Spec')
    if kind == 'baseline':
        require_text(data.get('provenance'), 'pre-change provenance')
        for ref in data.get('observations', []):
            if store.get(ref)['data'].get('contract_version') != 2:
                raise ValueError('v2 baseline requires v2 observations')
    if kind != 'observation':
        return
    criteria = {c['id']: c for c in spec['data']['criteria']}
    cid = data.get('criterion_id')
    if cid is not None:
        if cid not in criteria or data.get('check_id') not in {c['check_id'] for c in criteria[cid]['checks']}:
            raise ValueError('observation must identify approved check')
    else:
        require_text(data.get('check_id'), 'additional observation check_id')
    e = data.get('execution')
    if not isinstance(e, dict):
        raise ValueError('execution receipt required')
    for name in ('id', 'producer', 'provenance'):
        require_text(e.get(name), 'execution ' + name)
    if e.get('status') not in {'completed', 'error', 'not_started'}:
        raise ValueError('invalid execution status')
    if e.get('failure_kind') not in {'none', 'requirement_violation', 'execution_error', 'unknown'}:
        raise ValueError('invalid failure kind')
    if e.get('origin') not in {'live', 'reconstructed'} or not isinstance(e.get('environment_complete'), bool):
        raise ValueError('invalid execution origin or environment coverage')
    start = datetime.fromisoformat(require_text(e.get('started_at'), 'execution start'))
    end = datetime.fromisoformat(require_text(e.get('finished_at'), 'execution end'))
    if start.tzinfo is None or end.tzinfo is None or end < start:
        raise ValueError('execution timestamps must be ordered and timezone-aware')
    for name in ('code_start', 'code_end'):
        store._require_kind(e.get(name), 'code_state', scope)
    for ref in data.get('evidence', []):
        binding = store._require_kind(ref, 'evidence_binding', scope)
        raw = store._validate_legacy_evidence(scope, binding['data']['evidence_id'])
        if raw.fields.get('execution') != e or raw.fields.get('check_id') != data.get('check_id'):
            raise ValueError('execution receipt differs from raw evidence binding')


def _collect(store, scope, inputs):
    """Collect every matching record, never just caller-selected passes."""
    baseline = store.get(inputs['baseline'])['data']
    records, diagnostics, candidates = [], [], []
    # ponytail: journal scan matches the existing store; index if actual history size warrants it.
    rows = store.connection.execute("SELECT * FROM lifecycle_records WHERE kind='observation' ORDER BY sequence")
    for row in rows:
        record = store._record(row)
        d = record['data']
        if record['scope'] != scope or d.get('spec') != inputs['spec']:
            continue
        if d.get('spec_approval') != inputs['spec_approval']:
            continue
        target = baseline if d.get('phase') == 'before' else inputs
        if any(store.get(d[name])['data']['fingerprint'] != store.get(target[name])['data']['fingerprint']
               for name in ('code_state', 'environment')):
            continue
        ref = reference(record['kind'], record['id'], record['revision'], record['hash'])
        record['ref'] = ref
        candidates.append(ref)
        try:
            store.get(ref)
            if d.get('contract_version') != 2:
                raise ValueError('v2 evaluation requires v2 observations')
            validate_v2(store, 'observation', scope, d, active=False)
        except ValueError as error:
            diagnostics.append({'rejected_input_id': ref['id'], 'revision': ref['revision'],
                'criterion_id': d.get('criterion_id'), 'check_id': d.get('check_id'), 'phase': d.get('phase'),
                'reason_code': 'invalid_evidence', 'detail': str(error)})
            continue
        record['environment_fingerprint'] = store.get(d['environment'])['data']['fingerprint']
        target_code = store.get(d['code_state'])['data']['fingerprint']
        record['code_consistent'] = all(store.get(d['execution'][name])['data']['fingerprint'] == target_code
                                        for name in ('code_start', 'code_end'))
        records.append(record)
    return records, diagnostics, candidates


def compose_review(store, scope, inputs):
    if set(inputs) != INPUT_KEYS or inputs.get('contract_version') != 2:
        raise ValueError('v2 evaluation requires canonical inputs')
    store._require_attempt_scope(scope)
    spec = store._require_approved_spec(inputs, scope)['data']
    if spec.get('contract_version') != 2:
        raise ValueError('evaluation requires v2 Spec')
    for name, kind in [('code_state','code_state'), ('environment','environment'), ('baseline','baseline')]:
        store._require_kind(inputs[name], kind, scope)
    baseline = store.get(inputs['baseline'])['data']
    if (baseline.get('contract_version') != 2 or baseline['baseline_kind'] != 'verification'
            or any(baseline[k] != inputs[k] for k in ('spec','spec_approval'))):
        raise ValueError('review requires matching v2 verification baseline')
    require_text(baseline.get('provenance'), 'pre-change provenance')
    criteria = {c['id']: c for c in spec['criteria']}
    seen = set()
    for name in ('test_plan','blockers','findings','exclusions'):
        if not isinstance(inputs[name], list):
            raise ValueError(name + ' must be a list')
    for plan in inputs['test_plan']:
        cid = plan.get('criterion_id')
        if cid not in criteria or plan.get('check_id') not in {c['check_id'] for c in criteria[cid]['checks']}:
            raise ValueError('test plan requires approved check')
        key = (cid, plan['check_id'], require_text(plan.get('test_id'), 'planned test_id'))
        if key in seen:
            raise ValueError('duplicate planned test')
        seen.add(key)
        require_sha256(plan.get('test_meaning'), 'planned test meaning')
    from .store import BLOCKER_REASONS
    for blocker in inputs['blockers']:
        cid = blocker.get('criterion_id')
        if cid not in criteria or not criteria[cid]['required']:
            raise ValueError('only required criteria may block review')
        if blocker.get('check_id') not in {c['check_id'] for c in criteria[cid]['checks']}:
            raise ValueError('blocker requires approved check')
        if blocker.get('reason') not in BLOCKER_REASONS:
            raise ValueError('unsupported blocker reason')
        require_text(blocker.get('source'), 'blocker source')
    for exclusion in inputs['exclusions']:
        cid = exclusion.get('criterion_id')
        if cid not in criteria or criteria[cid]['required']:
            raise ValueError('only optional criteria may be excluded')
        require_text(exclusion.get('reason'), 'exclusion reason')
    records, diagnostics, candidates = _collect(store, scope, inputs)
    findings = list(inputs['findings'])
    for finding in findings:
        require_text(finding.get('reason'), 'finding reason')
        refs = finding.get('observations')
        if not isinstance(refs, list) or not refs:
            raise ValueError('finding requires observations')
        if any(ref not in [r['ref'] for r in records] for ref in refs):
            raise ValueError('finding outside review input scope')
    for r in records:
        if r['data'].get('criterion_id') is None and r['data']['phase'] == 'after':
            if r['data']['result'] in {'fail','inconclusive'}:
                findings.append({'reason':'Additional observation needs review', 'observations':[r['ref']]})
    result = evaluate_review(spec['criteria'], records, inputs['test_plan'], inputs['blockers'],
                             findings, inputs['exclusions'], diagnostics)
    # Invalid references are not inserted into closure; only their rejected identifiers are retained.
    evaluation_inputs = {**inputs, 'blockers': inputs['blockers'], 'findings': inputs['findings']}
    candidate_fingerprint = fingerprint(candidates)
    return {**inputs, **result, 'evaluation_inputs': evaluation_inputs,
        'observation_set_hash': candidate_fingerprint,
        'evaluated_against': fingerprint({'inputs': inputs, 'observations': candidates}),
        'additional_observations': [r['ref'] for r in records if r['data'].get('criterion_id') is None],
        'uncertainties': diagnostics, 'inferences': []}


def validate_review(store, scope, data):
    inputs = data.get('evaluation_inputs')
    if not isinstance(inputs, dict):
        raise ValueError('v2 Review requires evaluator output')
    expected = compose_review(store, scope, inputs)
    if canonical_json(data) != canonical_json(expected):
        raise ValueError('Review differs from complete current evaluation; reevaluate')
