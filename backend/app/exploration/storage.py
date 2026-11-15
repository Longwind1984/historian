"""SQLite persistence and an isolated private source vault for exploration v6.

The database is deliberately a control-plane store: it contains identifiers,
state, structured derived artifacts, and provenance metadata.  Original source
bytes live only in :class:`PrivateSourceVault`.  Callers must pass source
locators/IDs through runtime state instead of copying passages into database
payloads or traces.

The local v6.1 topology is single-process with multiple worker threads.  A
repository owns one SQLite connection guarded by an ``RLock`` and uses
``BEGIN IMMEDIATE`` for state transitions.  WAL still permits independent
readers and makes completed work durable across process restarts.
"""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import tempfile
import threading
from typing import Any, Iterator, Mapping, Sequence
from uuid import uuid4


_SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,127}$")
_SAFE_ERROR_CODE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,79}$")
_PRIVATE_TEXT_KEYS = {
    "body",
    "content",
    "excerpt",
    "full_text",
    "paragraph_text",
    "quote",
    "raw_text",
    "source_bytes",
    "source_text",
    "text",
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds")


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex}"


def _require_safe_id(value: str, label: str) -> str:
    if not _SAFE_ID.fullmatch(value):
        raise ValueError(f"{label} must be an opaque ASCII identifier")
    return value


def _canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def _json_object(value: Mapping[str, Any] | None) -> dict[str, Any]:
    if value is None:
        return {}
    # Round-tripping also rejects objects that SQLite could not reproduce.
    result = json.loads(_canonical_json(value))
    if not isinstance(result, dict):
        raise TypeError("metadata must be a JSON object")
    return result


def _reject_private_source_fields(value: Any, path: str = "$") -> None:
    """Reject fields whose contract is raw/private source material.

    This is a structural guard, not a semantic classifier.  It prevents the
    common accidental paths (``source_text``, ``quote``, ``content``) while the
    vault/locator API makes the safe path easier.  Derived summaries remain
    valid under explicit fields such as ``summary`` or ``claim``.
    """

    if isinstance(value, Mapping):
        for key, nested in value.items():
            key_text = str(key)
            if key_text.casefold() in _PRIVATE_TEXT_KEYS:
                raise ValueError(
                    f"private source field {path}.{key_text} must be stored in the vault"
                )
            _reject_private_source_fields(nested, f"{path}.{key_text}")
    elif isinstance(value, (list, tuple)):
        for index, nested in enumerate(value):
            _reject_private_source_fields(nested, f"{path}[{index}]")


class StorageInvariantError(RuntimeError):
    """A requested state change would violate the durable runtime contract."""


class WorkspaceNotFound(StorageInvariantError):
    pass


class RunNotFound(StorageInvariantError):
    pass


class WorkItemNotFound(StorageInvariantError):
    pass


class AttemptNotFound(StorageInvariantError):
    pass


class RunState(str, Enum):
    PLANNED = "planned"
    QUEUED = "queued"
    RUNNING = "running"
    RETRY_WAIT = "retry_wait"
    PAUSED = "paused"
    WAITING_REVIEW = "waiting_review"
    WAITING_INPUT = "waiting_input"
    FAILED = "failed"
    CANCELLED = "cancelled"
    COMPLETED = "completed"


class WorkItemState(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    RETRY_WAIT = "retry_wait"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AttemptState(str, Enum):
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    INTERRUPTED = "interrupted"
    CANCELLED = "cancelled"


@dataclass(frozen=True)
class WorkspaceRecord:
    id: str
    created_at: str
    updated_at: str


@dataclass(frozen=True)
class SourceRecord:
    id: str
    workspace_id: str
    checksum: str
    byte_length: int
    media_type: str
    created_at: str


@dataclass(frozen=True)
class RunRecord:
    id: str
    workspace_id: str
    plan_revision: int
    state: RunState
    cancel_requested: bool
    resume_state: RunState | None
    created_at: str
    updated_at: str


@dataclass(frozen=True)
class WorkItemRecord:
    id: str
    workspace_id: str
    idempotency_key: str
    pass_type: str
    input_revision: int
    spec: dict[str, Any]
    state: WorkItemState
    max_attempts: int
    attempt_count: int
    output_revision: int | None
    last_error_code: str | None
    created_at: str
    updated_at: str


@dataclass(frozen=True)
class AttemptRecord:
    id: int
    run_id: str
    work_item_id: str
    number: int
    state: AttemptState
    error_code: str | None
    trace: dict[str, Any]
    started_at: str
    finished_at: str | None


@dataclass(frozen=True)
class ArtifactRevisionRecord:
    workspace_id: str
    revision: int
    kind: str
    payload: dict[str, Any]
    source_work_item_id: str | None
    created_at: str


@dataclass(frozen=True)
class CheckpointRecord:
    id: int
    run_id: str
    work_item_id: str
    sequence: int
    state: dict[str, Any]
    artifact_revision: int | None
    created_at: str


@dataclass(frozen=True)
class EnsuredWorkItem:
    item: WorkItemRecord
    reused_success: bool


@dataclass(frozen=True)
class ClaimedWorkItem:
    item: WorkItemRecord
    attempt: AttemptRecord


class PrivateSourceVault:
    """Filesystem vault whose paths are derived only from opaque IDs."""

    def __init__(self, root: str | os.PathLike[str]):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        try:
            self.root.chmod(0o700)
        except OSError:
            # Some mounted filesystems do not expose POSIX modes.  The vault
            # remains isolated by its configured directory boundary.
            pass
        self._lock = threading.RLock()

    def _workspace_dir(self, workspace_id: str) -> Path:
        return self.root / _require_safe_id(workspace_id, "workspace_id")

    def _source_path(self, workspace_id: str, source_id: str) -> Path:
        return self._workspace_dir(workspace_id) / (
            _require_safe_id(source_id, "source_id") + ".source"
        )

    def _snapshot_path(
        self, workspace_id: str, source_id: str, revision: int
    ) -> Path:
        if revision < 1:
            raise ValueError("snapshot revision must be positive")
        return self._workspace_dir(workspace_id) / (
            _require_safe_id(source_id, "source_id")
            + f".r{revision}.snapshot"
        )

    def put(self, workspace_id: str, source_id: str, data: bytes) -> None:
        if not isinstance(data, bytes):
            raise TypeError("private source must be bytes")
        workspace_dir = self._workspace_dir(workspace_id)
        destination = self._source_path(workspace_id, source_id)
        with self._lock:
            self._atomic_put(workspace_dir, destination, data)

    def put_snapshot(
        self,
        workspace_id: str,
        source_id: str,
        revision: int,
        data: bytes,
    ) -> None:
        """Persist a reconstructible private parser snapshot outside SQLite."""

        if not isinstance(data, bytes):
            raise TypeError("private source snapshot must be bytes")
        workspace_dir = self._workspace_dir(workspace_id)
        destination = self._snapshot_path(workspace_id, source_id, revision)
        with self._lock:
            self._atomic_put(workspace_dir, destination, data)

    @staticmethod
    def _atomic_put(workspace_dir: Path, destination: Path, data: bytes) -> None:
        workspace_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        fd, temporary_name = tempfile.mkstemp(prefix=".incoming-", dir=workspace_dir)
        temporary = Path(temporary_name)
        try:
            os.fchmod(fd, 0o600)
            with os.fdopen(fd, "wb") as handle:
                handle.write(data)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, destination)
        except BaseException:
            try:
                os.close(fd)
            except OSError:
                pass
            temporary.unlink(missing_ok=True)
            raise

    def read(self, workspace_id: str, source_id: str) -> bytes:
        with self._lock:
            return self._source_path(workspace_id, source_id).read_bytes()

    def read_snapshot(
        self, workspace_id: str, source_id: str, revision: int
    ) -> bytes:
        with self._lock:
            return self._snapshot_path(workspace_id, source_id, revision).read_bytes()

    def exists(self, workspace_id: str, source_id: str) -> bool:
        with self._lock:
            return self._source_path(workspace_id, source_id).is_file()

    def snapshot_exists(
        self, workspace_id: str, source_id: str, revision: int
    ) -> bool:
        with self._lock:
            return self._snapshot_path(
                workspace_id, source_id, revision
            ).is_file()

    def delete_source(self, workspace_id: str, source_id: str) -> None:
        with self._lock:
            path = self._source_path(workspace_id, source_id)
            path.unlink(missing_ok=True)
            workspace_dir = self._workspace_dir(workspace_id)
            snapshot_prefix = _require_safe_id(source_id, "source_id") + ".r"
            if workspace_dir.exists():
                for candidate in workspace_dir.iterdir():
                    if (
                        candidate.is_file()
                        and candidate.name.startswith(snapshot_prefix)
                        and candidate.name.endswith(".snapshot")
                    ):
                        candidate.unlink(missing_ok=True)
            try:
                workspace_dir.rmdir()
            except OSError:
                pass

    def delete_workspace(self, workspace_id: str) -> None:
        """Delete only the flat, opaque files owned by one workspace."""

        with self._lock:
            workspace_dir = self._workspace_dir(workspace_id)
            if not workspace_dir.exists():
                return
            for path in workspace_dir.iterdir():
                if path.is_file() and (
                    path.name.endswith(".source")
                    or path.name.endswith(".snapshot")
                    or path.name.startswith(".incoming-")
                ):
                    path.unlink(missing_ok=True)
                else:
                    raise StorageInvariantError(
                        "vault workspace contains an unexpected entry"
                    )
            workspace_dir.rmdir()


class ExplorationRepository:
    """Thread-safe SQLite repository for local exploration workflows."""

    def __init__(
        self,
        database_path: str | os.PathLike[str],
        vault_path: str | os.PathLike[str],
        *,
        recover_on_open: bool = True,
    ):
        self.database_path = Path(database_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self.vault = PrivateSourceVault(vault_path)
        self._lock = threading.RLock()
        self._connection = sqlite3.connect(
            self.database_path,
            timeout=30,
            check_same_thread=False,
            isolation_level=None,
        )
        self._connection.row_factory = sqlite3.Row
        with self._lock:
            self._connection.execute("PRAGMA foreign_keys = ON")
            self._connection.execute("PRAGMA busy_timeout = 30000")
            journal_mode = self._connection.execute(
                "PRAGMA journal_mode = WAL"
            ).fetchone()[0]
            if str(journal_mode).casefold() != "wal":
                raise StorageInvariantError("SQLite WAL mode is required")
            self._connection.execute("PRAGMA synchronous = FULL")
        self._create_schema()
        if recover_on_open:
            self.recover_interrupted_work()

    def close(self) -> None:
        with self._lock:
            self._connection.close()

    def __enter__(self) -> "ExplorationRepository":
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()

    @contextmanager
    def _transaction(self) -> Iterator[sqlite3.Connection]:
        with self._lock:
            self._connection.execute("BEGIN IMMEDIATE")
            try:
                yield self._connection
            except BaseException:
                self._connection.rollback()
                raise
            else:
                self._connection.commit()

    def _create_schema(self) -> None:
        schema = """
        CREATE TABLE IF NOT EXISTS workspaces (
            id TEXT PRIMARY KEY,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS sources (
            id TEXT PRIMARY KEY,
            workspace_id TEXT NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
            checksum TEXT NOT NULL,
            byte_length INTEGER NOT NULL CHECK (byte_length >= 0),
            media_type TEXT NOT NULL,
            created_at TEXT NOT NULL,
            UNIQUE (workspace_id, checksum)
        );

        CREATE TABLE IF NOT EXISTS runs (
            id TEXT PRIMARY KEY,
            workspace_id TEXT NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
            plan_revision INTEGER NOT NULL CHECK (plan_revision >= 1),
            state TEXT NOT NULL,
            cancel_requested INTEGER NOT NULL DEFAULT 0 CHECK (cancel_requested IN (0, 1)),
            resume_state TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS work_items (
            id TEXT PRIMARY KEY,
            workspace_id TEXT NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
            idempotency_key TEXT NOT NULL,
            pass_type TEXT NOT NULL,
            input_revision INTEGER NOT NULL CHECK (input_revision >= 0),
            spec_json TEXT NOT NULL,
            state TEXT NOT NULL,
            max_attempts INTEGER NOT NULL CHECK (max_attempts >= 1),
            attempt_count INTEGER NOT NULL DEFAULT 0 CHECK (attempt_count >= 0),
            output_revision INTEGER,
            last_error_code TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE (workspace_id, idempotency_key)
        );

        CREATE TABLE IF NOT EXISTS run_work_items (
            run_id TEXT NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
            work_item_id TEXT NOT NULL REFERENCES work_items(id) ON DELETE CASCADE,
            ordinal INTEGER NOT NULL CHECK (ordinal >= 0),
            PRIMARY KEY (run_id, work_item_id),
            UNIQUE (run_id, ordinal)
        );

        CREATE TABLE IF NOT EXISTS attempts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id TEXT NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
            work_item_id TEXT NOT NULL REFERENCES work_items(id) ON DELETE CASCADE,
            number INTEGER NOT NULL CHECK (number >= 1),
            state TEXT NOT NULL,
            error_code TEXT,
            trace_json TEXT NOT NULL,
            started_at TEXT NOT NULL,
            finished_at TEXT,
            UNIQUE (work_item_id, number)
        );

        CREATE TABLE IF NOT EXISTS artifact_revisions (
            workspace_id TEXT NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
            revision INTEGER NOT NULL CHECK (revision >= 1),
            kind TEXT NOT NULL,
            payload_json TEXT NOT NULL,
            source_work_item_id TEXT REFERENCES work_items(id) ON DELETE SET NULL,
            created_at TEXT NOT NULL,
            PRIMARY KEY (workspace_id, revision)
        );

        CREATE TABLE IF NOT EXISTS checkpoints (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id TEXT NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
            work_item_id TEXT NOT NULL REFERENCES work_items(id) ON DELETE CASCADE,
            sequence INTEGER NOT NULL CHECK (sequence >= 1),
            state_json TEXT NOT NULL,
            artifact_revision INTEGER,
            created_at TEXT NOT NULL,
            UNIQUE (run_id, work_item_id, sequence)
        );

        CREATE INDEX IF NOT EXISTS idx_runs_workspace ON runs(workspace_id);
        CREATE INDEX IF NOT EXISTS idx_run_items_run ON run_work_items(run_id, ordinal);
        CREATE INDEX IF NOT EXISTS idx_attempts_item ON attempts(work_item_id, number);
        CREATE INDEX IF NOT EXISTS idx_artifacts_workspace ON artifact_revisions(workspace_id, revision);
        """
        with self._lock:
            self._connection.executescript(schema)
            # Forward-compatible migration for v6 databases created before
            # cancellation remembered a review hold.  SQLite cannot add this
            # nullable column through CREATE TABLE IF NOT EXISTS alone.
            run_columns = {
                str(row["name"])
                for row in self._connection.execute("PRAGMA table_info(runs)")
            }
            if "resume_state" not in run_columns:
                self._connection.execute(
                    "ALTER TABLE runs ADD COLUMN resume_state TEXT"
                )

    @property
    def journal_mode(self) -> str:
        with self._lock:
            return str(
                self._connection.execute("PRAGMA journal_mode").fetchone()[0]
            ).casefold()

    def create_workspace(self, workspace_id: str | None = None) -> WorkspaceRecord:
        workspace_id = _require_safe_id(
            workspace_id or _new_id("ws"), "workspace_id"
        )
        now = _utc_now()
        with self._transaction() as connection:
            connection.execute(
                "INSERT INTO workspaces (id, created_at, updated_at) VALUES (?, ?, ?)",
                (workspace_id, now, now),
            )
        return self.get_workspace(workspace_id)

    def get_workspace(self, workspace_id: str) -> WorkspaceRecord:
        with self._lock:
            row = self._connection.execute(
                "SELECT * FROM workspaces WHERE id = ?", (workspace_id,)
            ).fetchone()
        if row is None:
            raise WorkspaceNotFound(workspace_id)
        return self._workspace_from_row(row)

    def workspace_exists(self, workspace_id: str) -> bool:
        with self._lock:
            return (
                self._connection.execute(
                    "SELECT 1 FROM workspaces WHERE id = ?", (workspace_id,)
                ).fetchone()
                is not None
            )

    def store_source(
        self,
        workspace_id: str,
        data: bytes,
        *,
        media_type: str = "application/octet-stream",
    ) -> SourceRecord:
        if not isinstance(data, bytes):
            raise TypeError("private source must be bytes")
        checksum = hashlib.sha256(data).hexdigest()
        stable_seed = f"{workspace_id}\0{checksum}".encode("utf-8")
        source_id = "src_" + hashlib.sha256(stable_seed).hexdigest()[:24]
        now = _utc_now()

        # Keep vault write + metadata insert inside the repository lock.  This
        # avoids a duplicate concurrent upload deleting the winning file while
        # still relying on SQLite's unique constraint across processes.
        with self._lock:
            self.get_workspace(workspace_id)
            existing = self._connection.execute(
                "SELECT * FROM sources WHERE workspace_id = ? AND checksum = ?",
                (workspace_id, checksum),
            ).fetchone()
            if existing is not None:
                record = self._source_from_row(existing)
                if not self.vault.exists(workspace_id, record.id):
                    self.vault.put(workspace_id, record.id, data)
                return record

            self.vault.put(workspace_id, source_id, data)
            try:
                with self._transaction() as connection:
                    connection.execute(
                        """
                        INSERT INTO sources
                            (id, workspace_id, checksum, byte_length, media_type, created_at)
                        VALUES (?, ?, ?, ?, ?, ?)
                        """,
                        (source_id, workspace_id, checksum, len(data), media_type, now),
                    )
                    connection.execute(
                        "UPDATE workspaces SET updated_at = ? WHERE id = ?",
                        (now, workspace_id),
                    )
            except BaseException:
                self.vault.delete_source(workspace_id, source_id)
                raise
            return self.get_source(source_id)

    def get_source(self, source_id: str) -> SourceRecord:
        with self._lock:
            row = self._connection.execute(
                "SELECT * FROM sources WHERE id = ?", (source_id,)
            ).fetchone()
        if row is None:
            raise StorageInvariantError("source metadata does not exist")
        return self._source_from_row(row)

    def read_source(self, source_id: str) -> bytes:
        source = self.get_source(source_id)
        return self.vault.read(source.workspace_id, source.id)

    def store_source_snapshot(
        self, source_id: str, revision: int, data: bytes
    ) -> None:
        source = self.get_source(source_id)
        with self._lock:
            self.vault.put_snapshot(source.workspace_id, source.id, revision, data)

    def read_source_snapshot(self, source_id: str, revision: int) -> bytes:
        source = self.get_source(source_id)
        return self.vault.read_snapshot(source.workspace_id, source.id, revision)

    def delete_source(self, source_id: str) -> None:
        source = self.get_source(source_id)
        self.vault.delete_source(source.workspace_id, source.id)
        with self._transaction() as connection:
            connection.execute("DELETE FROM sources WHERE id = ?", (source_id,))
            connection.execute(
                "UPDATE workspaces SET updated_at = ? WHERE id = ?",
                (_utc_now(), source.workspace_id),
            )

    def delete_workspace(self, workspace_id: str) -> None:
        self.get_workspace(workspace_id)
        self.vault.delete_workspace(workspace_id)
        with self._transaction() as connection:
            connection.execute("DELETE FROM workspaces WHERE id = ?", (workspace_id,))

    def create_run(
        self,
        workspace_id: str,
        *,
        plan_revision: int,
        run_id: str | None = None,
    ) -> RunRecord:
        self.get_workspace(workspace_id)
        if plan_revision < 1:
            raise ValueError("plan_revision must be positive")
        run_id = _require_safe_id(run_id or _new_id("run"), "run_id")
        now = _utc_now()
        with self._transaction() as connection:
            connection.execute(
                """
                INSERT INTO runs
                    (id, workspace_id, plan_revision, state, cancel_requested, resume_state,
                     created_at, updated_at)
                VALUES (?, ?, ?, ?, 0, NULL, ?, ?)
                """,
                (
                    run_id,
                    workspace_id,
                    plan_revision,
                    RunState.PLANNED.value,
                    now,
                    now,
                ),
            )
        return self.get_run(run_id)

    def get_run(self, run_id: str) -> RunRecord:
        with self._lock:
            row = self._connection.execute(
                "SELECT * FROM runs WHERE id = ?", (run_id,)
            ).fetchone()
        if row is None:
            raise RunNotFound(run_id)
        return self._run_from_row(row)

    def ensure_work_item(
        self,
        run_id: str,
        *,
        idempotency_key: str,
        pass_type: str,
        input_revision: int,
        spec: Mapping[str, Any],
        max_attempts: int,
    ) -> EnsuredWorkItem:
        run = self.get_run(run_id)
        if run.cancel_requested:
            raise StorageInvariantError("cannot enqueue work on a cancelled run")
        if input_revision < 0:
            raise ValueError("input_revision cannot be negative")
        if max_attempts < 1:
            raise ValueError("max_attempts must be positive")
        if not re.fullmatch(r"[0-9a-f]{64}", idempotency_key):
            raise ValueError("idempotency_key must be a SHA-256 hex digest")
        spec_object = _json_object(spec)
        _reject_private_source_fields(spec_object)
        spec_json = _canonical_json(spec_object)
        now = _utc_now()
        item_id = _new_id("wi")

        with self._transaction() as connection:
            row = connection.execute(
                """
                SELECT * FROM work_items
                WHERE workspace_id = ? AND idempotency_key = ?
                """,
                (run.workspace_id, idempotency_key),
            ).fetchone()
            if row is None:
                connection.execute(
                    """
                    INSERT INTO work_items
                        (id, workspace_id, idempotency_key, pass_type,
                         input_revision, spec_json, state, max_attempts,
                         attempt_count, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?)
                    """,
                    (
                        item_id,
                        run.workspace_id,
                        idempotency_key,
                        pass_type,
                        input_revision,
                        spec_json,
                        WorkItemState.QUEUED.value,
                        max_attempts,
                        now,
                        now,
                    ),
                )
                row = connection.execute(
                    "SELECT * FROM work_items WHERE id = ?", (item_id,)
                ).fetchone()
            else:
                if (
                    row["pass_type"] != pass_type
                    or row["input_revision"] != input_revision
                    or row["spec_json"] != spec_json
                ):
                    raise StorageInvariantError(
                        "idempotency key collision with different work specification"
                    )

            ordinal_row = connection.execute(
                "SELECT COALESCE(MAX(ordinal), -1) + 1 FROM run_work_items WHERE run_id = ?",
                (run_id,),
            ).fetchone()
            connection.execute(
                """
                INSERT OR IGNORE INTO run_work_items (run_id, work_item_id, ordinal)
                VALUES (?, ?, ?)
                """,
                (run_id, row["id"], int(ordinal_row[0])),
            )
            self._refresh_run_state_locked(connection, run_id)
            row = connection.execute(
                "SELECT * FROM work_items WHERE id = ?", (row["id"],)
            ).fetchone()

        item = self._work_item_from_row(row)
        return EnsuredWorkItem(
            item=item,
            reused_success=item.state is WorkItemState.SUCCEEDED,
        )

    def get_work_item(self, work_item_id: str) -> WorkItemRecord:
        with self._lock:
            row = self._connection.execute(
                "SELECT * FROM work_items WHERE id = ?", (work_item_id,)
            ).fetchone()
        if row is None:
            raise WorkItemNotFound(work_item_id)
        return self._work_item_from_row(row)

    def list_run_work_items(self, run_id: str) -> list[WorkItemRecord]:
        self.get_run(run_id)
        with self._lock:
            rows = self._connection.execute(
                """
                SELECT work_items.*
                FROM run_work_items
                JOIN work_items ON work_items.id = run_work_items.work_item_id
                WHERE run_work_items.run_id = ?
                ORDER BY run_work_items.ordinal
                """,
                (run_id,),
            ).fetchall()
        return [self._work_item_from_row(row) for row in rows]

    def claim_next_work_item(
        self,
        run_id: str,
        *,
        trace: Mapping[str, Any] | None = None,
    ) -> ClaimedWorkItem | None:
        trace_object = _json_object(trace)
        _reject_private_source_fields(trace_object)
        trace_json = _canonical_json(trace_object)
        now = _utc_now()

        with self._transaction() as connection:
            run_row = connection.execute(
                "SELECT * FROM runs WHERE id = ?", (run_id,)
            ).fetchone()
            if run_row is None:
                raise RunNotFound(run_id)
            if bool(run_row["cancel_requested"]):
                return None
            if run_row["state"] in {
                RunState.WAITING_REVIEW.value,
                RunState.FAILED.value,
                RunState.CANCELLED.value,
                RunState.COMPLETED.value,
            }:
                return None

            row = connection.execute(
                """
                SELECT work_items.*
                FROM run_work_items
                JOIN work_items ON work_items.id = run_work_items.work_item_id
                WHERE run_work_items.run_id = ?
                  AND work_items.state IN (?, ?)
                  AND work_items.attempt_count < work_items.max_attempts
                ORDER BY run_work_items.ordinal
                LIMIT 1
                """,
                (
                    run_id,
                    WorkItemState.QUEUED.value,
                    WorkItemState.RETRY_WAIT.value,
                ),
            ).fetchone()
            if row is None:
                self._refresh_run_state_locked(connection, run_id)
                return None

            attempt_number = int(row["attempt_count"]) + 1
            connection.execute(
                """
                UPDATE work_items
                SET state = ?, attempt_count = ?, updated_at = ?
                WHERE id = ?
                """,
                (
                    WorkItemState.RUNNING.value,
                    attempt_number,
                    now,
                    row["id"],
                ),
            )
            cursor = connection.execute(
                """
                INSERT INTO attempts
                    (run_id, work_item_id, number, state, trace_json, started_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    row["id"],
                    attempt_number,
                    AttemptState.RUNNING.value,
                    trace_json,
                    now,
                ),
            )
            connection.execute(
                "UPDATE runs SET state = ?, updated_at = ? WHERE id = ?",
                (RunState.RUNNING.value, now, run_id),
            )
            claimed_row = connection.execute(
                "SELECT * FROM work_items WHERE id = ?", (row["id"],)
            ).fetchone()
            attempt_row = connection.execute(
                "SELECT * FROM attempts WHERE id = ?", (cursor.lastrowid,)
            ).fetchone()
        return ClaimedWorkItem(
            item=self._work_item_from_row(claimed_row),
            attempt=self._attempt_from_row(attempt_row),
        )

    def complete_attempt(
        self,
        attempt_id: int,
        *,
        artifact_kind: str,
        artifact_payload: Mapping[str, Any],
        checkpoint_state: Mapping[str, Any] | None = None,
        trace_update: Mapping[str, Any] | None = None,
    ) -> ArtifactRevisionRecord:
        payload_object = _json_object(artifact_payload)
        checkpoint_object = _json_object(checkpoint_state)
        trace_object = _json_object(trace_update)
        for value in (payload_object, checkpoint_object, trace_object):
            _reject_private_source_fields(value)
        now = _utc_now()

        with self._transaction() as connection:
            attempt = connection.execute(
                "SELECT * FROM attempts WHERE id = ?", (attempt_id,)
            ).fetchone()
            if attempt is None:
                raise AttemptNotFound(str(attempt_id))
            if attempt["state"] != AttemptState.RUNNING.value:
                raise StorageInvariantError("only a running attempt can complete")
            item = connection.execute(
                "SELECT * FROM work_items WHERE id = ?", (attempt["work_item_id"],)
            ).fetchone()
            revision = self._next_artifact_revision_locked(
                connection, item["workspace_id"]
            )
            connection.execute(
                """
                INSERT INTO artifact_revisions
                    (workspace_id, revision, kind, payload_json,
                     source_work_item_id, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    item["workspace_id"],
                    revision,
                    artifact_kind,
                    _canonical_json(payload_object),
                    item["id"],
                    now,
                ),
            )
            merged_trace = json.loads(attempt["trace_json"])
            merged_trace.update(trace_object)
            _reject_private_source_fields(merged_trace)
            connection.execute(
                """
                UPDATE attempts
                SET state = ?, trace_json = ?, finished_at = ?
                WHERE id = ?
                """,
                (
                    AttemptState.SUCCEEDED.value,
                    _canonical_json(merged_trace),
                    now,
                    attempt_id,
                ),
            )
            connection.execute(
                """
                UPDATE work_items
                SET state = ?, output_revision = ?, last_error_code = NULL,
                    updated_at = ?
                WHERE id = ?
                """,
                (
                    WorkItemState.SUCCEEDED.value,
                    revision,
                    now,
                    item["id"],
                ),
            )
            sequence = int(
                connection.execute(
                    """
                    SELECT COALESCE(MAX(sequence), 0) + 1
                    FROM checkpoints WHERE run_id = ? AND work_item_id = ?
                    """,
                    (attempt["run_id"], item["id"]),
                ).fetchone()[0]
            )
            connection.execute(
                """
                INSERT INTO checkpoints
                    (run_id, work_item_id, sequence, state_json,
                     artifact_revision, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    attempt["run_id"],
                    item["id"],
                    sequence,
                    _canonical_json(checkpoint_object),
                    revision,
                    now,
                ),
            )
            self._refresh_linked_runs_locked(connection, item["id"])

        return self.get_artifact_revision(item["workspace_id"], revision)

    def fail_attempt(
        self,
        attempt_id: int,
        *,
        error_code: str,
        retryable: bool,
        checkpoint_state: Mapping[str, Any] | None = None,
    ) -> WorkItemRecord:
        if not _SAFE_ERROR_CODE.fullmatch(error_code):
            raise ValueError("error_code must be a bounded, non-sensitive code")
        checkpoint_object = _json_object(checkpoint_state)
        _reject_private_source_fields(checkpoint_object)
        now = _utc_now()

        with self._transaction() as connection:
            attempt = connection.execute(
                "SELECT * FROM attempts WHERE id = ?", (attempt_id,)
            ).fetchone()
            if attempt is None:
                raise AttemptNotFound(str(attempt_id))
            if attempt["state"] != AttemptState.RUNNING.value:
                raise StorageInvariantError("only a running attempt can fail")
            item = connection.execute(
                "SELECT * FROM work_items WHERE id = ?", (attempt["work_item_id"],)
            ).fetchone()
            can_retry = retryable and item["attempt_count"] < item["max_attempts"]
            next_state = (
                WorkItemState.RETRY_WAIT if can_retry else WorkItemState.FAILED
            )
            connection.execute(
                """
                UPDATE attempts
                SET state = ?, error_code = ?, finished_at = ? WHERE id = ?
                """,
                (AttemptState.FAILED.value, error_code, now, attempt_id),
            )
            connection.execute(
                """
                UPDATE work_items
                SET state = ?, last_error_code = ?, updated_at = ? WHERE id = ?
                """,
                (next_state.value, error_code, now, item["id"]),
            )
            sequence = int(
                connection.execute(
                    """
                    SELECT COALESCE(MAX(sequence), 0) + 1
                    FROM checkpoints WHERE run_id = ? AND work_item_id = ?
                    """,
                    (attempt["run_id"], item["id"]),
                ).fetchone()[0]
            )
            failure_checkpoint = dict(checkpoint_object)
            failure_checkpoint.update(
                {"error_code": error_code, "retryable": can_retry}
            )
            connection.execute(
                """
                INSERT INTO checkpoints
                    (run_id, work_item_id, sequence, state_json,
                     artifact_revision, created_at)
                VALUES (?, ?, ?, ?, NULL, ?)
                """,
                (
                    attempt["run_id"],
                    item["id"],
                    sequence,
                    _canonical_json(failure_checkpoint),
                    now,
                ),
            )
            self._refresh_linked_runs_locked(connection, item["id"])
            row = connection.execute(
                "SELECT * FROM work_items WHERE id = ?", (item["id"],)
            ).fetchone()
        return self._work_item_from_row(row)

    def retry_work_item(self, work_item_id: str) -> WorkItemRecord:
        now = _utc_now()
        with self._transaction() as connection:
            row = connection.execute(
                "SELECT * FROM work_items WHERE id = ?", (work_item_id,)
            ).fetchone()
            if row is None:
                raise WorkItemNotFound(work_item_id)
            if row["state"] not in (
                WorkItemState.FAILED.value,
                WorkItemState.RETRY_WAIT.value,
            ):
                raise StorageInvariantError("only failed/retry-wait work can retry")
            if row["attempt_count"] >= row["max_attempts"]:
                raise StorageInvariantError("work item exhausted max_attempts")
            connection.execute(
                """
                UPDATE work_items SET state = ?, updated_at = ? WHERE id = ?
                """,
                (WorkItemState.QUEUED.value, now, work_item_id),
            )
            self._refresh_linked_runs_locked(connection, work_item_id)
            row = connection.execute(
                "SELECT * FROM work_items WHERE id = ?", (work_item_id,)
            ).fetchone()
        return self._work_item_from_row(row)

    def request_cancel(self, run_id: str) -> RunRecord:
        now = _utc_now()
        with self._transaction() as connection:
            run = connection.execute(
                "SELECT * FROM runs WHERE id = ?", (run_id,)
            ).fetchone()
            if run is None:
                raise RunNotFound(run_id)
            if run["state"] == RunState.CANCELLED.value:
                return self._run_from_row(run)
            if run["state"] in {
                RunState.COMPLETED.value,
                RunState.FAILED.value,
            }:
                raise StorageInvariantError("a terminal run cannot be cancelled")
            connection.execute(
                """
                UPDATE runs
                SET cancel_requested = 1, resume_state = state, state = ?, updated_at = ?
                WHERE id = ?
                """,
                (RunState.CANCELLED.value, now, run_id),
            )
            # A canonical item may be shared by a second run.  Cancel it only
            # when this is the last active consumer.
            rows = connection.execute(
                """
                SELECT work_items.id
                FROM run_work_items
                JOIN work_items ON work_items.id = run_work_items.work_item_id
                WHERE run_work_items.run_id = ?
                  AND work_items.state IN (?, ?, ?)
                  AND NOT EXISTS (
                      SELECT 1 FROM run_work_items AS other_link
                      JOIN runs AS other_run ON other_run.id = other_link.run_id
                      WHERE other_link.work_item_id = work_items.id
                        AND other_link.run_id != ?
                        AND other_run.cancel_requested = 0
                        AND other_run.state NOT IN (?, ?, ?)
                  )
                """,
                (
                    run_id,
                    WorkItemState.QUEUED.value,
                    WorkItemState.RETRY_WAIT.value,
                    WorkItemState.RUNNING.value,
                    run_id,
                    RunState.CANCELLED.value,
                    RunState.FAILED.value,
                    RunState.COMPLETED.value,
                ),
            ).fetchall()
            item_ids = [row["id"] for row in rows]
            for item_id in item_ids:
                connection.execute(
                    """
                    UPDATE attempts SET state = ?, finished_at = ?
                    WHERE work_item_id = ? AND state = ?
                    """,
                    (
                        AttemptState.CANCELLED.value,
                        now,
                        item_id,
                        AttemptState.RUNNING.value,
                    ),
                )
                connection.execute(
                    "UPDATE work_items SET state = ?, updated_at = ? WHERE id = ?",
                    (WorkItemState.CANCELLED.value, now, item_id),
                )
        return self.get_run(run_id)

    def resume_run(self, run_id: str) -> RunRecord:
        now = _utc_now()
        with self._transaction() as connection:
            row = connection.execute(
                "SELECT * FROM runs WHERE id = ?", (run_id,)
            ).fetchone()
            if row is None:
                raise RunNotFound(run_id)
            if row["state"] != RunState.CANCELLED.value:
                raise StorageInvariantError("only a cancelled run can resume")
            resume_state = row["resume_state"]
            connection.execute(
                """
                UPDATE runs
                SET cancel_requested = 0, resume_state = NULL, updated_at = ?
                WHERE id = ?
                """,
                (now, run_id),
            )
            connection.execute(
                """
                UPDATE work_items SET state = ?, updated_at = ?
                WHERE id IN (
                    SELECT work_item_id FROM run_work_items WHERE run_id = ?
                ) AND state = ? AND attempt_count < max_attempts
                """,
                (
                    WorkItemState.QUEUED.value,
                    now,
                    run_id,
                    WorkItemState.CANCELLED.value,
                ),
            )
            if resume_state == RunState.WAITING_REVIEW.value:
                connection.execute(
                    "UPDATE runs SET state = ?, updated_at = ? WHERE id = ?",
                    (RunState.WAITING_REVIEW.value, now, run_id),
                )
            else:
                self._refresh_run_state_locked(connection, run_id)
        return self.get_run(run_id)

    def mark_waiting_review(self, run_id: str) -> RunRecord:
        """Place a successfully drained run behind the durable review gate.

        The transition is deliberately narrow: a run must have at least one
        linked work item and every linked item must already have succeeded.
        Repeating the transition is idempotent.  Workers cannot claim newly
        linked post-review work until :meth:`release_waiting_review` is called.
        """

        now = _utc_now()
        with self._transaction() as connection:
            run = connection.execute(
                "SELECT * FROM runs WHERE id = ?", (run_id,)
            ).fetchone()
            if run is None:
                raise RunNotFound(run_id)
            if bool(run["cancel_requested"]):
                raise StorageInvariantError("a cancelled run cannot wait for review")
            if run["state"] == RunState.WAITING_REVIEW.value:
                return self._run_from_row(run)
            if run["state"] != RunState.COMPLETED.value:
                raise StorageInvariantError(
                    "only a successfully drained run can wait for review"
                )
            states = [
                row[0]
                for row in connection.execute(
                    """
                    SELECT work_items.state
                    FROM run_work_items
                    JOIN work_items ON work_items.id = run_work_items.work_item_id
                    WHERE run_work_items.run_id = ?
                    """,
                    (run_id,),
                ).fetchall()
            ]
            if not states or any(
                state != WorkItemState.SUCCEEDED.value for state in states
            ):
                raise StorageInvariantError(
                    "review requires at least one fully succeeded work item"
                )
            connection.execute(
                "UPDATE runs SET state = ?, updated_at = ? WHERE id = ?",
                (RunState.WAITING_REVIEW.value, now, run_id),
            )
        return self.get_run(run_id)

    def release_waiting_review(self, run_id: str) -> RunRecord:
        """Release the review hold after a validated reviewer submission.

        Active/final states are accepted as idempotent repeats, but cancelled
        and failed runs must follow their dedicated recovery paths.
        """

        with self._transaction() as connection:
            run = connection.execute(
                "SELECT * FROM runs WHERE id = ?", (run_id,)
            ).fetchone()
            if run is None:
                raise RunNotFound(run_id)
            state = RunState(run["state"])
            if state in {
                RunState.QUEUED,
                RunState.RUNNING,
                RunState.RETRY_WAIT,
                RunState.COMPLETED,
            }:
                return self._run_from_row(run)
            if state is not RunState.WAITING_REVIEW:
                raise StorageInvariantError(
                    "only a run waiting for review can be released"
                )
            self._refresh_run_state_locked(
                connection, run_id, preserve_review_hold=False
            )
        return self.get_run(run_id)

    def get_attempt(self, attempt_id: int) -> AttemptRecord:
        with self._lock:
            row = self._connection.execute(
                "SELECT * FROM attempts WHERE id = ?", (attempt_id,)
            ).fetchone()
        if row is None:
            raise AttemptNotFound(str(attempt_id))
        return self._attempt_from_row(row)

    def list_attempts(self, work_item_id: str) -> list[AttemptRecord]:
        self.get_work_item(work_item_id)
        with self._lock:
            rows = self._connection.execute(
                "SELECT * FROM attempts WHERE work_item_id = ? ORDER BY number",
                (work_item_id,),
            ).fetchall()
        return [self._attempt_from_row(row) for row in rows]

    def get_artifact_revision(
        self, workspace_id: str, revision: int
    ) -> ArtifactRevisionRecord:
        with self._lock:
            row = self._connection.execute(
                """
                SELECT * FROM artifact_revisions
                WHERE workspace_id = ? AND revision = ?
                """,
                (workspace_id, revision),
            ).fetchone()
        if row is None:
            raise StorageInvariantError("artifact revision does not exist")
        return self._artifact_from_row(row)

    def list_checkpoints(self, run_id: str) -> list[CheckpointRecord]:
        self.get_run(run_id)
        with self._lock:
            rows = self._connection.execute(
                "SELECT * FROM checkpoints WHERE run_id = ? ORDER BY id",
                (run_id,),
            ).fetchall()
        return [self._checkpoint_from_row(row) for row in rows]

    def recover_interrupted_work(self) -> int:
        """Convert attempts left running by a crash into retryable work."""

        now = _utc_now()
        with self._transaction() as connection:
            interrupted_rows = connection.execute(
                """
                SELECT attempts.id, attempts.work_item_id
                FROM attempts
                JOIN work_items ON work_items.id = attempts.work_item_id
                WHERE attempts.state = ? AND work_items.state = ?
                """,
                (AttemptState.RUNNING.value, WorkItemState.RUNNING.value),
            ).fetchall()
            touched_items: set[str] = set()
            for row in interrupted_rows:
                connection.execute(
                    """
                    UPDATE attempts SET state = ?, error_code = ?, finished_at = ?
                    WHERE id = ?
                    """,
                    (
                        AttemptState.INTERRUPTED.value,
                        "WORKER_INTERRUPTED",
                        now,
                        row["id"],
                    ),
                )
                item = connection.execute(
                    "SELECT * FROM work_items WHERE id = ?", (row["work_item_id"],)
                ).fetchone()
                next_state = (
                    WorkItemState.RETRY_WAIT
                    if item["attempt_count"] < item["max_attempts"]
                    else WorkItemState.FAILED
                )
                connection.execute(
                    """
                    UPDATE work_items SET state = ?, last_error_code = ?, updated_at = ?
                    WHERE id = ?
                    """,
                    (
                        next_state.value,
                        "WORKER_INTERRUPTED",
                        now,
                        item["id"],
                    ),
                )
                touched_items.add(item["id"])
            for item_id in touched_items:
                self._refresh_linked_runs_locked(connection, item_id)
        return len(interrupted_rows)

    def _next_artifact_revision_locked(
        self, connection: sqlite3.Connection, workspace_id: str
    ) -> int:
        return int(
            connection.execute(
                """
                SELECT COALESCE(MAX(revision), 0) + 1
                FROM artifact_revisions WHERE workspace_id = ?
                """,
                (workspace_id,),
            ).fetchone()[0]
        )

    def _refresh_linked_runs_locked(
        self, connection: sqlite3.Connection, work_item_id: str
    ) -> None:
        run_rows = connection.execute(
            "SELECT run_id FROM run_work_items WHERE work_item_id = ?",
            (work_item_id,),
        ).fetchall()
        for row in run_rows:
            self._refresh_run_state_locked(connection, row["run_id"])

    def _refresh_run_state_locked(
        self,
        connection: sqlite3.Connection,
        run_id: str,
        *,
        preserve_review_hold: bool = True,
    ) -> None:
        run = connection.execute(
            "SELECT * FROM runs WHERE id = ?", (run_id,)
        ).fetchone()
        if run is None:
            raise RunNotFound(run_id)
        if bool(run["cancel_requested"]):
            state = RunState.CANCELLED
        elif (
            preserve_review_hold
            and run["state"] == RunState.WAITING_REVIEW.value
        ):
            state = RunState.WAITING_REVIEW
        else:
            states = [
                row[0]
                for row in connection.execute(
                    """
                    SELECT work_items.state
                    FROM run_work_items
                    JOIN work_items ON work_items.id = run_work_items.work_item_id
                    WHERE run_work_items.run_id = ?
                    """,
                    (run_id,),
                ).fetchall()
            ]
            if not states:
                state = RunState.PLANNED
            elif WorkItemState.RUNNING.value in states:
                state = RunState.RUNNING
            elif WorkItemState.FAILED.value in states:
                state = RunState.FAILED
            elif WorkItemState.RETRY_WAIT.value in states:
                state = RunState.RETRY_WAIT
            elif WorkItemState.CANCELLED.value in states:
                state = RunState.CANCELLED
            elif all(value == WorkItemState.SUCCEEDED.value for value in states):
                state = RunState.COMPLETED
            else:
                state = RunState.QUEUED
        connection.execute(
            "UPDATE runs SET state = ?, updated_at = ? WHERE id = ?",
            (state.value, _utc_now(), run_id),
        )

    @staticmethod
    def _workspace_from_row(row: sqlite3.Row) -> WorkspaceRecord:
        return WorkspaceRecord(
            id=row["id"], created_at=row["created_at"], updated_at=row["updated_at"]
        )

    @staticmethod
    def _source_from_row(row: sqlite3.Row) -> SourceRecord:
        return SourceRecord(
            id=row["id"],
            workspace_id=row["workspace_id"],
            checksum=row["checksum"],
            byte_length=int(row["byte_length"]),
            media_type=row["media_type"],
            created_at=row["created_at"],
        )

    @staticmethod
    def _run_from_row(row: sqlite3.Row) -> RunRecord:
        return RunRecord(
            id=row["id"],
            workspace_id=row["workspace_id"],
            plan_revision=int(row["plan_revision"]),
            state=RunState(row["state"]),
            cancel_requested=bool(row["cancel_requested"]),
            resume_state=(
                RunState(row["resume_state"])
                if row["resume_state"] is not None
                else None
            ),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    @staticmethod
    def _work_item_from_row(row: sqlite3.Row) -> WorkItemRecord:
        return WorkItemRecord(
            id=row["id"],
            workspace_id=row["workspace_id"],
            idempotency_key=row["idempotency_key"],
            pass_type=row["pass_type"],
            input_revision=int(row["input_revision"]),
            spec=json.loads(row["spec_json"]),
            state=WorkItemState(row["state"]),
            max_attempts=int(row["max_attempts"]),
            attempt_count=int(row["attempt_count"]),
            output_revision=(
                int(row["output_revision"])
                if row["output_revision"] is not None
                else None
            ),
            last_error_code=row["last_error_code"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    @staticmethod
    def _attempt_from_row(row: sqlite3.Row) -> AttemptRecord:
        return AttemptRecord(
            id=int(row["id"]),
            run_id=row["run_id"],
            work_item_id=row["work_item_id"],
            number=int(row["number"]),
            state=AttemptState(row["state"]),
            error_code=row["error_code"],
            trace=json.loads(row["trace_json"]),
            started_at=row["started_at"],
            finished_at=row["finished_at"],
        )

    @staticmethod
    def _artifact_from_row(row: sqlite3.Row) -> ArtifactRevisionRecord:
        return ArtifactRevisionRecord(
            workspace_id=row["workspace_id"],
            revision=int(row["revision"]),
            kind=row["kind"],
            payload=json.loads(row["payload_json"]),
            source_work_item_id=row["source_work_item_id"],
            created_at=row["created_at"],
        )

    @staticmethod
    def _checkpoint_from_row(row: sqlite3.Row) -> CheckpointRecord:
        return CheckpointRecord(
            id=int(row["id"]),
            run_id=row["run_id"],
            work_item_id=row["work_item_id"],
            sequence=int(row["sequence"]),
            state=json.loads(row["state_json"]),
            artifact_revision=(
                int(row["artifact_revision"])
                if row["artifact_revision"] is not None
                else None
            ),
            created_at=row["created_at"],
        )


__all__ = [
    "ArtifactRevisionRecord",
    "AttemptNotFound",
    "AttemptRecord",
    "AttemptState",
    "CheckpointRecord",
    "ClaimedWorkItem",
    "EnsuredWorkItem",
    "ExplorationRepository",
    "PrivateSourceVault",
    "RunNotFound",
    "RunRecord",
    "RunState",
    "SourceRecord",
    "StorageInvariantError",
    "WorkItemNotFound",
    "WorkItemRecord",
    "WorkItemState",
    "WorkspaceNotFound",
    "WorkspaceRecord",
]
