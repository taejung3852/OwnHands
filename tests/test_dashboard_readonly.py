"""WI-01: real stores, immutable sources, and diagnostic-only partial reads."""
import hashlib
import os
from pathlib import Path
import sqlite3
import unittest
from unittest.mock import patch

from devharness.catalog import Catalog
from devharness.evidence import EvidenceDraft, EvidenceStore, RetentionPolicy
from devharness.events import EventLog
from devharness.lifecycle.store import LifecycleStore
import tests.test_claim_evaluation as fixtures


class DashboardReadonlyTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.ClaimEvaluationTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.tearDown)
        f = self.fixture
        f.configure(checks=('normal', 'retry'))
        self.left = f.observe(content=b'normal evidence')
        self.right = f.observe(check='retry', content=b'retry evidence')
        self.review = f.store.append('review', 'read-review', f.scope, f.evaluate())
        self.snapshot = f.store.append('snapshot', 'read-snapshot', f.scope, {'review': self.review})
        self.raw = EvidenceStore(f.catalog, EventLog(f.catalog)).resolve('evidence:1')

    def open_reader(self):
        self.assertTrue(callable(getattr(Catalog, 'open_readonly', None)), 'read-only Catalog factory')
        self.assertTrue(callable(getattr(LifecycleStore, 'open_readonly', None)), 'read-only lifecycle factory')
        self.assertTrue(callable(getattr(EvidenceStore, 'open_readonly', None)), 'read-only Evidence factory')
        catalog = Catalog.open_readonly(self.fixture.paths)
        self.addCleanup(catalog.close)
        reader = LifecycleStore.open_readonly(catalog)
        self.addCleanup(reader.close)
        return catalog, reader

    def inventory(self):
        root = self.fixture.paths.root
        return {str(p.relative_to(root)): (p.stat().st_mode,
                hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else None)
                for p in [root, *root.rglob('*')]}

    def test_normal_read_does_not_initialize_chmod_or_reconcile(self):
        orphan = self.fixture.paths.objects / 'orphan'
        orphan.write_bytes(b'old unreferenced object')
        os.utime(orphan, (1, 1))
        os.chmod(self.fixture.paths.root, 0o750)
        os.chmod(self.fixture.paths.objects, 0o750)
        before = self.inventory()
        catalog, reader = self.open_reader()
        self.assertEqual(reader.get(self.snapshot)['data']['review'], self.review)
        evidence = EvidenceStore.open_readonly(catalog)
        self.assertEqual(evidence.read_content('evidence:1'), b'normal evidence')
        # Implicit downstream construction must inherit the read-only boundary too.
        self.assertEqual(EvidenceStore(catalog, EventLog(catalog)).read_content('evidence:2'), b'retry evidence')
        self.assertTrue(reader.review_status(self.review)['readable'])
        self.assertFalse(reader.review_status(self.review)['new_evidence_available'])
        self.assertEqual(reader.current('attempt', self.fixture.issue_scope), self.fixture.attempt)
        self.assertEqual(reader.freshness(self.review, self.fixture.spec, self.fixture.code,
            self.fixture.env, {'test:normal': 'd'*64, 'test:retry': 'd'*64})['state'], 'current')
        self.assertEqual(before, self.inventory())

    def test_missing_catalog_and_lifecycle_do_not_create_sources(self):
        self.open_reader()
        missing = Path(self.fixture.temp.name) / 'absent' / 'data'
        with self.assertRaises((OSError, sqlite3.OperationalError)):
            Catalog.open_readonly(missing)
        self.assertFalse(missing.parent.exists())
        catalog = Catalog.open_readonly(self.fixture.paths)
        self.addCleanup(catalog.close)
        with self.assertRaises((OSError, sqlite3.OperationalError)):
            LifecycleStore.open_readonly(catalog, missing / 'lifecycle.sqlite3')
        self.assertFalse(missing.exists())

    def test_old_schema_is_rejected_without_migration(self):
        self.open_reader()
        self.fixture.catalog.connection.execute("UPDATE schema_metadata SET value='2' WHERE key='schema_version'")
        before = self.inventory()
        with self.assertRaisesRegex(RuntimeError, 'schema'):
            Catalog.open_readonly(self.fixture.paths)
        self.assertEqual(before, self.inventory())

    def test_sql_and_writer_methods_cannot_mutate_sources(self):
        catalog, reader = self.open_reader()
        evidence = EvidenceStore.open_readonly(catalog)
        before = self.inventory()
        draft = EvidenceDraft('new', self.fixture.task.task_id, 'c1', 'test_execution',
            'test:normal', 'scope', 'pass', 'observed', {'safe':'value'}, b'new', 'test', 'not_needed')
        calls = [lambda: evidence.put(draft, lambda b:b),
                 lambda: evidence.set_retention(RetentionPolicy('keep_until_user_deletes', None)),
                 lambda: evidence.purge('evidence:1', 'test'),
                 lambda: evidence.reconcile_objects(0),
                 lambda: reader.append('work_issue','new',self.fixture.project_scope,{'title':'new'}),
                 lambda: reader.activate(self.snapshot),
                 lambda: reader.bind_evidence('new',self.fixture.scope,'evidence:1'),
                 lambda: reader.evaluate_review(self.fixture.scope, {})]
        for call in calls:
            with self.assertRaises(PermissionError):
                call()
        for connection in (catalog.connection, reader.connection):
            with self.assertRaises(sqlite3.OperationalError):
                connection.execute('CREATE TABLE forbidden(value TEXT)')
            # mode=ro still protects the original if a caller disables query_only.
            connection.execute('PRAGMA query_only=OFF')
            with self.assertRaises(sqlite3.OperationalError):
                connection.execute('CREATE TABLE forbidden(value TEXT)')
        self.assertEqual(before, self.inventory())

    def test_readonly_factories_reject_writable_catalog(self):
        self.open_reader()
        for factory in (LifecycleStore.open_readonly, EvidenceStore.open_readonly):
            with self.assertRaises(ValueError):
                factory(self.fixture.catalog)

    def test_partial_corrupt_evidence_preserves_sibling_and_strict_get(self):
        _, reader = self.open_reader()
        self.raw.object_path.write_bytes(b'corrupt')
        before = self.inventory()
        result = reader.inspect_closure(self.snapshot)
        self.assertEqual(result.read_health, 'partial')
        self.assertEqual(result.record['data']['review'], self.review)
        self.assertEqual(len(result.diagnostics), 1)
        diagnostic = result.diagnostics[0]
        self.assertEqual((diagnostic.evidence_id, diagnostic.availability), ('evidence:1', 'corrupt'))
        self.assertEqual(diagnostic.reference['id'], 'binding:1')
        self.assertIn(self.right['hash'], {r['hash'] for r in result.records})
        with self.assertRaises(ValueError):
            reader.get(self.snapshot)
        self.assertFalse(reader.review_status(self.review)['readable'])
        self.assertEqual(before, self.inventory())

    def test_complete_partial_reader_reports_no_diagnostics(self):
        _, reader = self.open_reader()
        result = reader.inspect_closure(self.snapshot)
        self.assertEqual(result.read_health, 'complete')
        self.assertEqual(result.diagnostics, ())
        self.assertEqual(result.record, reader.get(self.snapshot))

    def test_missing_raw_is_not_recreated(self):
        _, reader = self.open_reader()
        self.raw.object_path.unlink()
        result = reader.inspect_closure(self.snapshot)
        self.assertEqual(len(result.diagnostics), 1)
        self.assertEqual(result.diagnostics[0].availability, 'missing')
        self.assertFalse(self.raw.object_path.exists())

    def test_directory_raw_preserves_healthy_sibling(self):
        _, reader = self.open_reader()
        self.raw.object_path.unlink()
        self.raw.object_path.mkdir()
        before = self.inventory()
        result = reader.inspect_closure(self.snapshot)
        self.assertEqual(len(result.diagnostics), 1)
        self.assertEqual(result.diagnostics[0].availability, 'corrupt')
        self.assertIn(self.right['hash'], {r['hash'] for r in result.records})
        self.assertEqual(before, self.inventory())

    def test_wal_catalog_rejected_before_sidecar_creation(self):
        self.fixture.catalog.connection.execute('PRAGMA journal_mode=WAL')
        self.fixture.catalog.close()
        before = self.inventory()
        with self.assertRaisesRegex(RuntimeError, 'WAL'):
            Catalog.open_readonly(self.fixture.paths)
        self.assertEqual(before, self.inventory())

    def test_corrupt_raw_parent_preserves_healthy_sibling(self):
        _, reader = self.open_reader()
        self.raw.object_path.unlink()
        self.raw.object_path.parent.rmdir()
        self.raw.object_path.parent.write_bytes(b'corrupt shard')
        result = reader.inspect_closure(self.snapshot)
        self.assertEqual(len(result.diagnostics), 1)
        self.assertEqual(result.diagnostics[0].availability, 'corrupt')
        self.assertIn(self.right['hash'], {r['hash'] for r in result.records})

    def test_wal_lifecycle_rejected_before_sidecar_creation(self):
        self.fixture.store.connection.execute('PRAGMA journal_mode=WAL')
        self.fixture.store.close()
        catalog = Catalog.open_readonly(self.fixture.paths)
        self.addCleanup(catalog.close)
        before = self.inventory()
        with self.assertRaisesRegex(RuntimeError, 'WAL'):
            LifecycleStore.open_readonly(catalog)
        self.assertEqual(before, self.inventory())

    def test_purged_raw_stays_purged(self):
        _, reader = self.open_reader()
        EvidenceStore(self.fixture.catalog, EventLog(self.fixture.catalog)).purge('evidence:1', 'test')
        self.assertEqual(reader.inspect_closure(self.snapshot).diagnostics[0].availability, 'purged')
        self.assertFalse(self.raw.object_path.exists())

    def test_permission_denial_is_diagnostic_without_hiding_other_raw(self):
        _, reader = self.open_reader()
        original = Path.read_bytes
        def read(path):
            if path == self.raw.object_path:
                raise PermissionError('fixture denied')
            return original(path)
        with patch.object(Path, 'read_bytes', read):
            result = reader.inspect_closure(self.snapshot)
        self.assertEqual(len(result.diagnostics), 1)
        self.assertEqual(result.diagnostics[0].availability, 'denied')

    def test_journal_and_reference_corruption_are_not_partial_success(self):
        _, reader = self.open_reader()
        bad = {**self.snapshot, 'hash': '0'*64}
        with self.assertRaises(ValueError):
            reader.inspect_closure(bad)
        self.fixture.store.connection.execute('DROP TRIGGER lifecycle_records_no_update')
        self.fixture.store.connection.execute("UPDATE lifecycle_records SET data_json='{}' WHERE kind='snapshot'")
        with self.assertRaisesRegex(ValueError, 'fingerprint'):
            reader.inspect_closure(self.snapshot)

    def test_wrong_task_evidence_is_not_softened_into_partial(self):
        _, reader = self.open_reader()
        # Stored binding scope must be checked before returning Evidence details.
        from devharness.identity import IdentityRegistry
        other = IdentityRegistry(self.fixture.catalog).create_task_lifecycle(
            'foreign', 'foreign', 'imported', 'a'*40, 'main', '/other', 'env')
        self.fixture.catalog.connection.execute('DROP TRIGGER evidence_canonical_fields_immutable')
        self.fixture.catalog.connection.execute("UPDATE evidence SET task_id=? WHERE evidence_id='evidence:1'",
            (other.task_id,))
        with self.assertRaises(ValueError):
            reader.inspect_closure(self.snapshot)


if __name__ == '__main__':
    unittest.main()
