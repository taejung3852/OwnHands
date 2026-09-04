#!/usr/bin/env bash

set -euo pipefail

probe_dir="$(mktemp -d /tmp/devharness-m0-06.XXXXXX)"

cleanup() {
  case "$probe_dir" in
    /tmp/devharness-m0-06.*) rm -rf -- "$probe_dir" ;;
    *) return 1 ;;
  esac
}
trap cleanup EXIT

db_path="$probe_dir/catalog.sqlite3"
objects_dir="$probe_dir/objects/sha256"
mkdir -p "$objects_dir"

sqlite3 "$db_path" "PRAGMA journal_mode=DELETE;" >/dev/null

sqlite3 "$db_path" <<'SQL'
PRAGMA synchronous=FULL;
PRAGMA foreign_keys=ON;

CREATE TABLE events (
  sequence INTEGER PRIMARY KEY AUTOINCREMENT,
  event_id TEXT NOT NULL UNIQUE,
  event_version INTEGER NOT NULL CHECK (event_version >= 1),
  event_type TEXT NOT NULL,
  project_id TEXT NOT NULL,
  worktree_id TEXT NOT NULL,
  task_id TEXT NOT NULL,
  occurred_at TEXT NOT NULL,
  payload_json TEXT NOT NULL CHECK (json_valid(payload_json)),
  evidence_sha256 TEXT
);

CREATE TABLE evidence_objects (
  sha256 TEXT PRIMARY KEY,
  byte_count INTEGER NOT NULL CHECK (byte_count >= 0),
  media_type TEXT NOT NULL,
  relative_path TEXT NOT NULL UNIQUE,
  redaction_status TEXT NOT NULL,
  collected_at TEXT NOT NULL
);

CREATE TABLE projection_state (
  projection_name TEXT PRIMARY KEY,
  last_sequence INTEGER NOT NULL
);

CREATE TABLE task_event_counts (
  task_id TEXT PRIMARY KEY,
  event_count INTEGER NOT NULL
);

INSERT INTO events (
  event_id, event_version, event_type, project_id, worktree_id, task_id,
  occurred_at, payload_json
) VALUES (
  'event-001', 1, 'task.created', 'project-001', 'worktree-main', 'task-001',
  '2026-09-04T00:00:00Z', '{"source":"synthetic"}'
);
SQL

# A process ending without COMMIT must not expose a partial event.
sqlite3 "$db_path" <<'SQL'
BEGIN IMMEDIATE;
INSERT INTO events (
  event_id, event_version, event_type, project_id, worktree_id, task_id,
  occurred_at, payload_json
) VALUES (
  'event-partial', 1, 'tool.started', 'project-001', 'worktree-main', 'task-001',
  '2026-09-04T00:00:01Z', '{"source":"synthetic"}'
);
SQL

partial_count="$(sqlite3 "$db_path" "SELECT count(*) FROM events WHERE event_id = 'event-partial';")"
test "$partial_count" = "0"

# A killed writer with an open transaction must also recover without exposing its row.
crash_ready="$probe_dir/crash-ready"
python3 - "$db_path" "$crash_ready" <<'PY' &
import sqlite3
import sys
import time

database, ready_path = sys.argv[1:]
connection = sqlite3.connect(database)
connection.execute("BEGIN IMMEDIATE")
connection.execute(
    """
    INSERT INTO events (
      event_id, event_version, event_type, project_id, worktree_id, task_id,
      occurred_at, payload_json
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """,
    (
        "event-crash",
        1,
        "tool.started",
        "project-001",
        "worktree-main",
        "task-001",
        "2026-09-04T00:00:01Z",
        '{"source":"synthetic-crash"}',
    ),
)
open(ready_path, "w", encoding="utf-8").close()
time.sleep(60)
PY
crash_pid=$!

for _ in {1..100}; do
  test -f "$crash_ready" && break
  sleep 0.05
done
test -f "$crash_ready"
kill -KILL "$crash_pid"
wait "$crash_pid" 2>/dev/null || true

crash_count="$(sqlite3 "$db_path" "SELECT count(*) FROM events WHERE event_id = 'event-crash';")"
test "$crash_count" = "0"

# Event IDs make repeated delivery idempotent.
sqlite3 "$db_path" <<'SQL'
INSERT INTO events (
  event_id, event_version, event_type, project_id, worktree_id, task_id,
  occurred_at, payload_json
) VALUES (
  'event-001', 1, 'task.created', 'project-001', 'worktree-main', 'task-001',
  '2026-09-04T00:00:00Z', '{"source":"synthetic"}'
) ON CONFLICT(event_id) DO NOTHING;
SQL

duplicate_count="$(sqlite3 "$db_path" "SELECT count(*) FROM events WHERE event_id = 'event-001';")"
test "$duplicate_count" = "1"

# Raw evidence is addressed by content hash and referenced from the catalog.
raw_source="$probe_dir/synthetic-evidence.txt"
printf '%s\n' 'synthetic evidence; contains no user data' > "$raw_source"
raw_hash="$(shasum -a 256 "$raw_source" | awk '{print $1}')"
object_dir="$objects_dir/${raw_hash:0:2}"
object_path="$object_dir/${raw_hash:2}"
mkdir -p "$object_dir"
cp "$raw_source" "$object_path"
object_bytes="$(wc -c < "$object_path" | tr -d ' ')"
object_relative_path="objects/sha256/${raw_hash:0:2}/${raw_hash:2}"

sqlite3 "$db_path" <<SQL
BEGIN IMMEDIATE;
INSERT INTO evidence_objects (
  sha256, byte_count, media_type, relative_path, redaction_status, collected_at
) VALUES (
  '$raw_hash', $object_bytes, 'text/plain', '$object_relative_path',
  'synthetic-no-sensitive-data', '2026-09-04T00:00:02Z'
);
INSERT INTO events (
  event_id, event_version, event_type, project_id, worktree_id, task_id,
  occurred_at, payload_json, evidence_sha256
) VALUES (
  'event-002', 1, 'test.completed', 'project-001', 'worktree-main', 'task-001',
  '2026-09-04T00:00:02Z', '{"result":"passed"}', '$raw_hash'
);
COMMIT;
SQL

stored_hash="$(shasum -a 256 "$object_path" | awk '{print $1}')"
catalog_hash="$(sqlite3 "$db_path" "SELECT sha256 FROM evidence_objects;")"
test "$raw_hash" = "$stored_hash"
test "$raw_hash" = "$catalog_hash"

# Projection tables are disposable and rebuild from the canonical event table.
sqlite3 "$db_path" <<'SQL'
BEGIN IMMEDIATE;
DELETE FROM task_event_counts;
DELETE FROM projection_state;
INSERT INTO task_event_counts (task_id, event_count)
SELECT task_id, count(*) FROM events GROUP BY task_id;
INSERT INTO projection_state (projection_name, last_sequence)
SELECT 'task_event_counts', coalesce(max(sequence), 0) FROM events;
COMMIT;
SQL

event_head="$(sqlite3 "$db_path" "SELECT max(sequence) FROM events;")"
projected_sequence="$(sqlite3 "$db_path" "SELECT last_sequence FROM projection_state WHERE projection_name = 'task_event_counts';")"
projected_count="$(sqlite3 "$db_path" "SELECT event_count FROM task_event_counts WHERE task_id = 'task-001';")"
test "$event_head" = "$projected_sequence"
test "$projected_count" = "2"

# An unsupported event version must be detectable and must leave the projection stale.
sqlite3 "$db_path" <<'SQL'
INSERT INTO events (
  event_id, event_version, event_type, project_id, worktree_id, task_id,
  occurred_at, payload_json
) VALUES (
  'event-version-unknown', 2, 'future.event', 'project-001', 'worktree-main', 'task-001',
  '2026-09-04T00:00:03Z', '{"source":"synthetic"}'
);
SQL

unknown_version_count="$(sqlite3 "$db_path" "SELECT count(*) FROM events WHERE event_version NOT IN (1);")"
current_event_head="$(sqlite3 "$db_path" "SELECT max(sequence) FROM events;")"
test "$unknown_version_count" = "1"
test "$current_event_head" != "$projected_sequence"

redaction_status="$(sqlite3 "$db_path" "SELECT redaction_status FROM evidence_objects WHERE sha256 = '$raw_hash';")"
test "$redaction_status" = "synthetic-no-sensitive-data"

# Repository-local pointers and any accidental raw fixtures must remain ignored.
repo_root="$(git rev-parse --show-toplevel)"
git -C "$repo_root" check-ignore -q .dev-harness/probe.raw
git -C "$repo_root" check-ignore -q docs/spikes/raw/probe.raw

sqlite_integrity="$(sqlite3 "$db_path" 'PRAGMA integrity_check;')"
test "$sqlite_integrity" = "ok"

printf 'sqlite_version=%s\n' "$(sqlite3 --version | awk '{print $1}')"
printf 'journal_mode=%s\n' "$(sqlite3 "$db_path" 'PRAGMA journal_mode;')"
printf 'partial_write_rollback=passed\n'
printf 'forced_interruption_recovery=passed\n'
printf 'duplicate_event_idempotency=passed\n'
printf 'evidence_content_hash=passed\n'
printf 'projection_rebuild=passed\n'
printf 'unknown_event_version_fails_freshness=passed\n'
printf 'redaction_metadata=passed\n'
printf 'raw_evidence_git_exclusion=passed\n'
printf 'integrity_check=%s\n' "$sqlite_integrity"
