"""Run with PYTHONPATH=src python tests/run_claim_mutations.py.

Change one real rule in an isolated process; an assertion failure must catch it.
No source files are edited. Infrastructure/import errors do not count as kills.
"""
import importlib
import io
import json
from pathlib import Path
import subprocess
import sys
import unittest

MUTATIONS = [
    ('before-direction', 'evaluation', "'pass' if criterion['comparison'] == 'preserve' else 'fail'",
     "'fail' if criterion['comparison'] == 'preserve' else 'pass'"),
    ('coverage-any', 'evaluation', 'all(s == "verified" for s in states)',
     'any(s == "verified" for s in states)'),
    ('ignore-actual-failure', 'evaluation', "if any(v == 'fail' for v, _ in after):", 'if False:'),
    ('ignore-conflicts', 'evaluation', 'if len(outcomes) > 1:', 'if False:'),
    ('omit-stored-failure', 'evaluation_store', 'records.append(record)',
     "records.append(record) if d['result'] != 'fail' else None"),
    ('trust-submitted-summary', 'evaluation_store', 'if canonical_json(data) != canonical_json(expected):',
     'if False:'),
    ('ignore-task-scope', 'store', 'if record.task_id != scope.get("task_id"):', 'if False:'),
    ('skip-raw-integrity', 'store', 'evidence_store.read_content(evidence_id)', 'None'),
]


def child(index):
    name, module_name, before, after = MUTATIONS[index]
    module = importlib.import_module('devharness.lifecycle.' + module_name)
    source = Path(module.__file__).read_text()
    if source.count(before) != 1:
        raise RuntimeError('mutation anchor changed: ' + name)
    exec(compile(source.replace(before, after), str(module.__file__), 'exec'), module.__dict__)
    if module_name == 'store':
        import devharness.lifecycle
        devharness.lifecycle.LifecycleStore = module.LifecycleStore
    suite = unittest.defaultTestLoader.loadTestsFromName('tests.test_claim_evaluation')
    result = unittest.TextTestRunner(stream=io.StringIO()).run(suite)
    killed = bool(result.failures) and not result.errors
    print(json.dumps({'mutation': name, 'killed': killed,
                      'assertion_failures': len(result.failures), 'errors': len(result.errors)}))
    return 0 if killed else 1


if __name__ == '__main__':
    # Script execution places tests/ first; add the repository for tests package imports.
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    if len(sys.argv) == 2:
        raise SystemExit(child(int(sys.argv[1])))
    failed = False
    for i in range(len(MUTATIONS)):
        run = subprocess.run([sys.executable, __file__, str(i)], capture_output=True, text=True)
        print(run.stdout.strip() or run.stderr.strip())
        failed |= run.returncode != 0
    raise SystemExit(int(failed))
