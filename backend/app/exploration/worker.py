"""Independent durable worker for private book-analysis runs.

The HTTP process only writes plans and review decisions. This worker is the
only component that injects private paragraph text into model calls. Its
durable records remain source-free and can be recovered after a restart.
"""

from __future__ import annotations

import argparse
import signal
import sys
import threading
from collections.abc import Callable

from app.core.config import settings

from .control_plane import ExplorationControlPlane
from .georesolution import ReviewedPlaceResolver
from .model_gateway import ModelGateway, build_configured_model_gateway
from .passes import VerifiedLocation
from .pipeline import PipelineResult, run_exploration_pipeline
from .storage import ExplorationRepository, RunState


_RUNNABLE_STATES = (
    RunState.PLANNED.value,
    RunState.QUEUED.value,
    RunState.RETRY_WAIT.value,
)


class ExplorationWorker:
    """Claims one durable run at a time while SQLite arbitrates work items."""

    def __init__(
        self,
        control_plane: ExplorationControlPlane,
        gateway: ModelGateway,
        location_resolver: Callable[[str], VerifiedLocation | None] | None = None,
    ) -> None:
        self.control_plane = control_plane
        self.repository = control_plane.repository
        self.gateway = gateway
        self.location_resolver = location_resolver

    def next_run_id(self, *, excluded: set[str] | None = None) -> str | None:
        excluded = excluded or set()
        placeholders = ",".join("?" for _ in _RUNNABLE_STATES)
        with self.repository._lock:  # noqa: SLF001 - same storage boundary
            rows = self.repository._connection.execute(  # noqa: SLF001
                f"""
                SELECT runs.id
                FROM runs
                JOIN exploration_analysis_runs AS control
                  ON control.run_id = runs.id
                LEFT JOIN exploration_analysis_reviews AS review
                  ON review.run_id = runs.id
                WHERE runs.cancel_requested = 0
                  AND (
                    runs.state IN ({placeholders})
                    OR (
                      runs.state = ?
                      AND review.run_id IS NOT NULL
                      AND review.applied_at IS NULL
                    )
                  )
                ORDER BY runs.created_at, runs.id
                """,
                (*_RUNNABLE_STATES, RunState.WAITING_REVIEW.value),
            ).fetchall()
        return next((str(row["id"]) for row in rows if row["id"] not in excluded), None)

    def process_run(self, run_id: str) -> PipelineResult:
        run = self.repository.get_run(run_id)
        snapshot = self.control_plane.load_snapshot(run.workspace_id)
        if snapshot.document is None:
            raise ValueError("book analysis worker requires a parsed document")
        source_id = self.control_plane._control_record(run.workspace_id).source_id
        reviewer = self.control_plane.reviewer_for_run(run_id)
        result = run_exploration_pipeline(
            snapshot.document,
            repository=self.repository,
            workspace_id=run.workspace_id,
            source_id=source_id,
            gateway=self.gateway,
            reviewer=reviewer,
            run_id=run_id,
            location_resolver=self.location_resolver,
        )
        if reviewer is not None and result.state == RunState.COMPLETED.value:
            self.control_plane.mark_review_applied(run_id)
        return result

    def process_next(self, *, excluded: set[str] | None = None) -> PipelineResult | None:
        run_id = self.next_run_id(excluded=excluded)
        return self.process_run(run_id) if run_id is not None else None


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="history-kb exploration worker")
    parser.add_argument(
        "--once",
        action="store_true",
        help="process at most one runnable run and exit",
    )
    parser.add_argument(
        "--poll-seconds",
        type=float,
        default=settings.exploration_worker_poll_seconds,
        help="idle poll interval (0.1-60 seconds)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if not 0.1 <= args.poll_seconds <= 60:
        raise SystemExit("--poll-seconds must be between 0.1 and 60")

    stop = threading.Event()

    def request_stop(_signum: int, _frame: object) -> None:
        stop.set()

    signal.signal(signal.SIGINT, request_stop)
    signal.signal(signal.SIGTERM, request_stop)
    gateway = build_configured_model_gateway(settings)
    repository = ExplorationRepository(
        settings.exploration_state_dir / "explorations.sqlite3",
        settings.exploration_state_dir / "vault",
    )
    control_plane = ExplorationControlPlane(
        repository,
        model_gateway=gateway,
    )
    try:
        from app.core.data import get_entity_index

        location_resolver = ReviewedPlaceResolver(
            get_entity_index().by_type.get("Place", [])
        )
    except (OSError, RuntimeError, ValueError):
        # Missing/corrupt reviewed data disables promotion to verified geometry;
        # model coordinates remain rejected by the pass validator.
        location_resolver = None
    worker = ExplorationWorker(control_plane, gateway, location_resolver)
    quarantined: set[str] = set()
    try:
        while not stop.is_set():
            run_id = worker.next_run_id(excluded=quarantined)
            if run_id is None:
                if args.once:
                    return 0
                stop.wait(args.poll_seconds)
                continue
            try:
                result = worker.process_run(run_id)
            except Exception as error:  # fail closed; never log private payloads
                quarantined.add(run_id)
                print(
                    f"[exploration-worker] quarantined run={run_id} "
                    f"error={type(error).__name__}",
                    file=sys.stderr,
                    flush=True,
                )
                if args.once:
                    return 1
                continue
            print(
                f"[exploration-worker] run={run_id} state={result.state}",
                flush=True,
            )
            if args.once:
                return 0
    finally:
        repository.close()
        close_gateway = getattr(gateway, "close", None)
        if callable(close_gateway):
            close_gateway()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["ExplorationWorker", "main"]
