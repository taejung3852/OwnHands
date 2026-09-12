"""Active verification must execute even when legacy Control modules are unavailable."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
ACTIVE_TOOLS = {
    'task.create', 'task.import', 'git.restore_capture',
    'tests.baseline_record', 'tests.compare_runs', 'tests.gap_detect',
    'tests.design_memo', 'git.diff_impact', 'assurance.gate_evaluate',
    'guarantee.evaluate',
}
BLOCK_CONTROL = '''
import importlib.abc, sys
class NoControl(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname in {
            'devharness.control_profile', 'devharness.control_runtime',
            'devharness.managed_tasks', 'devharness.codex_app_server',
            'devharness.context_architecture', 'devharness.mcp.tools.context',
            'devharness.mcp.tools.harness', 'devharness.mcp.legacy',
        } or fullname.lower().startswith('harnesslab'):
            raise ImportError('Control unavailable: ' + fullname)
sys.meta_path.insert(0, NoControl())
'''


class ControlBoundaryTests(unittest.TestCase):
    def run_child(self, code, input=''):
        result = subprocess.run(
            [sys.executable, '-c', BLOCK_CONTROL + code], input=input,
            text=True, capture_output=True, cwd=ROOT,
            env={**os.environ, 'PYTHONPATH': str(ROOT / 'src')}, timeout=60,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return result

    def test_default_registry_excludes_legacy_tools_and_rejects_calls(self):
        result = self.run_child('''
from devharness.mcp.server import McpServer
import json
server = McpServer()
print(json.dumps(sorted(server.tools)))
for name in ('task.prepare', 'task.record_run', 'harness.candidate_apply', 'context.lint'):
    response = server.handle_request({'jsonrpc': '2.0', 'id': 1, 'method': 'tools/call',
                                      'params': {'name': name, 'arguments': {}}})
    assert response['error']['code'] == -32601, response
''')
        self.assertEqual(set(json.loads(result.stdout)), ACTIVE_TOOLS)

    def test_control_free_spec_review_and_core_regressions(self):
        self.run_child('''
import unittest
suite = unittest.defaultTestLoader.loadTestsFromNames([
    'tests.test_lifecycle', 'tests.test_claim_evaluation', 'tests.test_imported_tasks',
    'tests.test_identity', 'tests.test_evidence', 'tests.test_events', 'tests.test_projections',
])
result = unittest.TextTestRunner(verbosity=0).run(suite)
assert result.wasSuccessful()
''')

    def test_both_stdio_entrypoints_create_task_without_control(self):
        for module, prefix in [('devharness', ['mcp-server']), ('devharness.mcp.server', [])]:
            with self.subTest(module=module), tempfile.TemporaryDirectory() as data_root:
                requests = [
                    {'jsonrpc': '2.0', 'id': 1, 'method': 'initialize'},
                    {'jsonrpc': '2.0', 'id': 2, 'method': 'tools/list'},
                    {'jsonrpc': '2.0', 'id': 3, 'method': 'tools/call', 'params': {
                        'name': 'task.create', 'arguments': {
                            'project_locator': '/fixture', 'worktree_locator': '/fixture',
                            'mode': 'imported', 'commit': 'a' * 40, 'branch': 'main',
                            'cwd': '/fixture', 'environment_ref': 'fixture-env',
                            'task_id': 'boundary-task',
                        }}},
                ]
                result = self.run_child(
                    'import runpy\nsys.argv = ' + repr([module, *prefix, '--data-root', data_root])
                    + '\nrunpy.run_module(' + repr(module) + ', run_name="__main__")\n',
                    ''.join(json.dumps(r) + '\n' for r in requests),
                )
                responses = [json.loads(line) for line in result.stdout.splitlines()]
                self.assertEqual(len(responses), 3)
                self.assertEqual({t['name'] for t in responses[1]['result']['tools']}, ACTIVE_TOOLS)
                packet = json.loads(responses[2]['result']['content'][0]['text'])
                self.assertEqual(packet['data']['task_id'], 'boundary-task')

    def test_run_receipt_reader_and_recorder_have_no_control_dependency(self):
        self.run_child('''
from devharness.run_records import AppServerRecord, AppServerRun
from devharness.run_evidence import record_run_evidence
assert AppServerRun([AppServerRecord('notification', 'turn/completed', 'hash')],
                    'thread', 'turn', 'completed', [], 'fixture', 'fixture').terminal_status == 'completed'
''')

    def test_legacy_receipt_storage_scope_and_replay_without_control(self):
        from dataclasses import asdict
        from tests.test_managed_tasks import create_repository, make_request, app_server_run, NOW
        from devharness.catalog import Catalog
        from devharness.paths import DataPaths
        from devharness.identity import IdentityRegistry
        from devharness.evidence import EvidenceDraft, EvidenceStore
        from devharness.events import EventLog
        from devharness.managed_tasks import prepare_managed_task
        from devharness.control_runtime import evaluate_runtime_controls

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            repository, commit, patch_hash = create_repository(root)
            paths = DataPaths.resolve(root / 'data')
            with Catalog.open(paths) as catalog:
                task = IdentityRegistry(catalog).create_task_lifecycle(
                    project_locator=str(repository), worktree_locator=str(repository),
                    mode='managed', commit=commit, branch='fixture-main', cwd=str(repository),
                    environment_ref='environment-managed')
                EvidenceStore(catalog, EventLog(catalog)).put(EvidenceDraft(
                    'evidence-m2-baseline', task.task_id, 'M2-baseline', 'direct_feature_probe',
                    'baseline-managed-v1', 'M2 baseline', 'pass', 'observed',
                    {'artifact_ref': 'baseline-managed-v1'}, b'synthetic M2 baseline',
                    'm3-test', 'not_needed'), lambda value: value)
                prepared = prepare_managed_task(make_request(repository, commit, patch_hash,
                    project_id=task.project_id, worktree_id=task.worktree_id,
                    task_id=task.task_id), now=NOW)
            run = app_server_run()
            payload = {'root': str(paths.root), 'prepared': prepared, 'run': asdict(run),
                       'controls': evaluate_runtime_controls(prepared, run)}
            self.run_child('''
import copy, json
from pathlib import Path
from devharness.catalog import Catalog
from devharness.paths import DataPaths
from devharness.identity import IdentityRegistry
from devharness.run_records import AppServerRecord, AppServerRun
from devharness.run_evidence import ManagedTaskError, record_run_evidence
from devharness.evidence import EvidenceDraft, EvidenceStore
from devharness.events import EventLog
from devharness.projections import ProjectionEngine
data = json.load(sys.stdin)
run = data['run']
run['records'] = [AppServerRecord(**r) for r in run['records']]
run = AppServerRun(**run)
paths = DataPaths.resolve(data['root'])
with Catalog.open(paths) as catalog:
    prepared = data['prepared']
    events = EventLog(catalog)
    store = EvidenceStore(catalog, events)
    foreign = IdentityRegistry(catalog).create_task_lifecycle(
        project_locator='/foreign', worktree_locator='/foreign', mode='managed',
        commit='foreign', branch='main', cwd='/foreign', environment_ref='other')
    store.put(EvidenceDraft('foreign-evidence', foreign.task_id, 'c', 'direct_feature_probe',
        's', 'scope', 'pass', 'observed', {'artifact_ref': 'x'}, b'foreign',
        'fixture', 'not_needed'), lambda value: value)
    attacks = []
    for field, value in [('event_refs', ['task-created:' + foreign.task_id]),
                         ('evidence_refs', ['foreign-evidence']),
                         ('evidence_refs', ['missing-evidence']), ('branch', 'foreign')]:
        attack = copy.deepcopy(prepared)
        attack[field] = value
        attacks.append(attack)
    count = catalog.query_value('SELECT COUNT(*) FROM evidence')
    for attack in attacks:
        try:
            record_run_evidence(catalog, attack, run, data['controls'])
        except ManagedTaskError:
            pass
        else:
            raise AssertionError('accepted foreign or unresolved reference')
        assert catalog.query_value('SELECT COUNT(*) FROM evidence') == count
    packet = record_run_evidence(catalog, prepared, run, data['controls'])
    assert len(packet['evidence_refs']) == 11
    assert len(packet['control_records']) == 6
    contents = {eid: store.read_content(eid) for eid in packet['evidence_refs']}
    task_id = packet['task_id']
    before = ProjectionEngine(catalog, events).project(task_id)
with Catalog.open(paths) as catalog:
    events = EventLog(catalog)
    store = EvidenceStore(catalog, events)
    assert contents == {eid: store.read_content(eid) for eid in contents}
    after = ProjectionEngine(catalog, events).rebuild(task_id)
    assert before.state == after.state == 'ready'
    eid = packet['evidence_refs'][0]
    store.resolve(eid).object_path.write_bytes(b'corrupted')
    try:
        store.read_content(eid)
    except ValueError:
        pass
    else:
        raise AssertionError('accepted corrupted raw evidence')
''', json.dumps(payload))

    def test_plugin_manifest_starts_real_server_from_source_checkout(self):
        from devharness.plugin import load_plugin_package
        with tempfile.TemporaryDirectory() as data_root:
            server = load_plugin_package(ROOT, Path(data_root))['mcp_servers']['ownhands']
            env = dict(os.environ)
            env.pop('PYTHONPATH', None)
            env.update(server['env'])
            result = subprocess.run([sys.executable, *server['args']],
                input=json.dumps({'jsonrpc': '2.0', 'id': 1, 'method': 'tools/list'}) + '\n',
                cwd=server['cwd'], env=env, text=True, capture_output=True, timeout=10)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual({t['name'] for t in json.loads(result.stdout)['result']['tools']}, ACTIVE_TOOLS)
