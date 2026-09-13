"""Partial *read health*, never a new Claim or Review verdict."""
from dataclasses import dataclass
from typing import Literal, TYPE_CHECKING

from ..evidence import EvidenceStore
from .model import reference

if TYPE_CHECKING:
    from .store import LifecycleStore


@dataclass(frozen=True)
class ReadDiagnostic:
    reference: dict
    evidence_id: str
    availability: Literal['missing', 'purged', 'corrupt', 'denied']
    reason: str


@dataclass(frozen=True)
class ClosureRead:
    # These are journal-validated metadata, not a claim that every raw object is readable.
    record: dict
    records: tuple[dict, ...]
    diagnostics: tuple[ReadDiagnostic, ...]

    @property
    def read_health(self) -> Literal['complete', 'partial']:
        return 'partial' if self.diagnostics else 'complete'


def inspect_closure(store: 'LifecycleStore', artifact_ref: dict) -> ClosureRead:
    """Keep strict traversal/scope checks; only unavailable Evidence is softened."""
    if not store.readonly:
        raise ValueError('partial inspection requires a read-only lifecycle store')
    evidence = EvidenceStore.open_readonly(store.catalog)
    diagnostics = []
    records = []

    def inspect_binding(binding):
        eid = binding['data']['evidence_id']
        ref = reference(binding['kind'], binding['id'], binding['revision'], binding['hash'])

        def rejected(availability, reason):
            diagnostics.append(ReadDiagnostic(ref, eid, availability, reason))

        row = store.catalog.connection.execute(
            'SELECT * FROM evidence WHERE evidence_id=?', (eid,)).fetchone()
        if row is None:
            rejected('missing', 'Evidence record is missing')
            return
        # Scope errors are not availability gaps and must never expose foreign records.
        if row['task_id'] != binding['scope'].get('task_id'):
            raise ValueError('evidence belongs to another task')
        try:
            record = evidence._from_row(row)
        except ValueError:
            rejected('corrupt', 'Evidence metadata failed integrity validation')
            return
        if record.purged_at is not None:
            rejected('purged', 'Evidence was purged')
            return
        try:
            evidence._validate_object(record)
        except FileNotFoundError:
            rejected('missing', 'Evidence object is missing')
        except PermissionError:
            rejected('denied', 'Evidence object is inaccessible')
        except (ValueError, IsADirectoryError, NotADirectoryError):
            rejected('corrupt', 'Evidence object failed integrity validation')

    with store._transaction(write=False):
        store._verify_journal()
        root = store._get_with_closure(artifact_ref, set(), inspect_evidence=inspect_binding,
                                      records=records)
    return ClosureRead(root, tuple(records), tuple(diagnostics))
