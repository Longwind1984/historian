"""Independent worker, review gate, and source-free result integration tests."""

from __future__ import annotations

from app.exploration.control_plane import AnalysisReviewRequest
from app.exploration.model_gateway import NoModelGateway
from app.exploration.storage import RunState
from app.exploration.worker import ExplorationWorker
from app.schemas.exploration import ImportExplorationRequest, SourceFormat
from app.services.exploration_service import ExplorationStore


def test_worker_stops_for_explicit_review_then_publishes_after_submission(tmp_path):
    state_dir = tmp_path / "state"
    private_marker = "PRIVATE-WORKER-MARKER-只可在来源保险库"
    gateway = NoModelGateway()
    store = ExplorationStore(state_dir=state_dir, model_gateway=gateway)
    snapshot = store.create(
        ImportExplorationRequest(
            source_format=SourceFormat.MARKDOWN,
            content=f"# 第一章\n\n755 年，{private_marker}。",
        )
    )
    queued = store.create_analysis_run(
        snapshot.id,
        base_revision=snapshot.revision,
    )
    worker = ExplorationWorker(store.control_plane, gateway)

    waiting = worker.process_next()
    assert waiting is not None
    assert waiting.run_id == queued.id
    assert waiting.state == RunState.WAITING_REVIEW.value
    assert store.repository.get_run(queued.id).state is RunState.WAITING_REVIEW

    result = store.get_analysis_result(snapshot.id, queued.id)
    assert result.status.state == "waiting_review"
    assert result.review_required is True
    assert result.review_submitted is False
    assert result.artifacts.claims == []
    assert result.artifacts.events == []
    assert any(gap.code == "model_not_called" for gap in result.artifacts.gaps)
    assert result.published_projections.argument.nodes == ()

    submitted = store.submit_analysis_review(
        snapshot.id,
        queued.id,
        AnalysisReviewRequest(
            review_token=result.review_token,
            decisions=(),
        ),
    )
    assert submitted.review_submitted is True
    assert submitted.status.state == "waiting_review"

    completed = worker.process_next()
    assert completed is not None
    assert completed.run_id == queued.id
    assert completed.state == RunState.COMPLETED.value
    final = store.get_analysis_result(snapshot.id, queued.id)
    assert final.status.state == "completed"
    assert final.review_required is False
    assert final.review_submitted is True

    database_family = b"".join(
        path.read_bytes()
        for path in state_dir.glob("explorations.sqlite3*")
        if path.is_file()
    )
    assert private_marker.encode("utf-8") not in database_family
    store.close()
