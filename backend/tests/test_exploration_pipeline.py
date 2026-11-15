"""End-to-end tests for the document/profile/plan/runtime adapter."""

from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path

import pytest

from app.exploration.contracts import AnalysisPass, BookType, ExecutorKind
from app.exploration.model_gateway import DeterministicModelGateway, NoModelGateway
from app.exploration.passes import AnalysisArtifacts
from app.exploration.pipeline import (
    adapt_work_item_spec,
    run_exploration_pipeline,
)
from app.exploration.planning import compile_analysis_plan
from app.exploration.profiling import build_book_profile
from app.exploration.runtime import ExplorationRuntime
from app.exploration.signals import derive_document_signals
from app.exploration.storage import (
    AttemptState,
    ExplorationRepository,
    RunState,
    WorkItemState,
)
from app.schemas.exploration import (
    DocumentLocator,
    DocumentSection,
    ParagraphAnchor,
    PrivateDocument,
    SourceFormat,
)


SECRET = "机密正文-token-4c3f-不得进入运行时数据库"


_TEXT = {
    "event": (
        "755年春，将军率军从范阳城出发，进攻洛阳城；次年军队退守长安城。",
        "756年冬，使者抵达潼关，军队随后返回京城，官员发布命令。",
    ),
    "argument": (
        "作者认为制度结构是关键，因为财政政策改变了治理机制，因此这一证据[1]表明权力关系发生变化。",
        "然而材料[2]并不能说明唯一原因；作者主张应从社会结构、政治组织与经济制度共同解释。",
    ),
    "biography": (
        "李明于1900年出生于青州城。他后来离开故乡，前往京城任职，李明随后返回家乡。",
        "1912年李明再次迁往海州城，他会见友人并建立学校；晚年李明在当地去世。",
    ),
}


def _document(kind: str, *, include_secret: bool = False) -> PrivateDocument:
    base = _TEXT[kind]
    sections = []
    all_text = []
    ordinal = 0
    for section_index in range(3):
        paragraphs = []
        for paragraph_index, template in enumerate(base):
            text = template + (SECRET if include_secret and ordinal == 0 else "")
            anchor_id = f"a_{kind}_{section_index}_{paragraph_index}"
            paragraphs.append(
                ParagraphAnchor(
                    id=anchor_id,
                    section_id=f"s_{kind}_{section_index}",
                    ordinal=ordinal,
                    text=text,
                    locator=DocumentLocator(
                        source_format=SourceFormat.TEXT,
                        section_index=section_index,
                        paragraph_index=paragraph_index,
                        progression_percent=round(ordinal / 5 * 100, 2),
                    ),
                )
            )
            ordinal += 1
            all_text.append(text)
        sections.append(
            DocumentSection(
                id=f"s_{kind}_{section_index}",
                title=f"第{section_index + 1}章",
                level=1,
                ordinal=section_index,
                paragraphs=paragraphs,
            )
        )
    title = {
        "event": "一场战争的进程",
        "argument": "国家制度研究",
        "biography": "李明传",
    }[kind]
    joined = "\n".join(all_text)
    return PrivateDocument(
        id=f"doc_{kind}",
        title=title,
        author="测试作者",
        source_format=SourceFormat.TEXT,
        checksum_sha256=sha256(joined.encode()).hexdigest(),
        char_count=len(joined),
        section_count=len(sections),
        paragraph_count=len(all_text),
        sections=sections,
    )


def _profile(document: PrivateDocument):
    signals = derive_document_signals(document, anchor_batch_size=2)
    return build_book_profile(
        source_checksum=document.checksum_sha256,
        metadata=signals.metadata,
        structure=signals.structure,
        section_signals=signals.sections,
    )


def _repository(tmp_path: Path) -> ExplorationRepository:
    return ExplorationRepository(tmp_path / "pipeline.sqlite3", tmp_path / "vault")


@pytest.mark.parametrize(
    ("kind", "expected"),
    [
        ("event", BookType.EVENT_NARRATIVE),
        ("argument", BookType.ARGUMENTATIVE_MONOGRAPH),
        ("biography", BookType.BIOGRAPHY_MICROHISTORY),
    ],
)
def test_document_signals_route_three_book_shapes_without_historical_claims(
    kind: str,
    expected: BookType,
):
    document = _document(kind)
    signals = derive_document_signals(document, anchor_batch_size=2)
    profile = _profile(document)

    assert profile.primary_type is expected
    assert profile.historical_claims_emitted is False
    assert signals.structure.section_count == 3
    assert len(signals.planning_scope.chapter_ids) == 3
    assert len(signals.planning_scope.anchor_batches) == 3
    assert all(len(batch.anchor_ids) == 2 for batch in signals.planning_scope.anchor_batches)
    serialized = json.dumps(
        {
            "metadata": signals.metadata.model_dump(mode="json"),
            "structure": signals.structure.model_dump(mode="json"),
            "sections": [item.model_dump(mode="json") for item in signals.sections],
        },
        ensure_ascii=False,
    )
    assert document.sections[0].paragraphs[0].text not in serialized


def test_plan_adapter_preserves_identity_scope_versions_and_excludes_body():
    document = _document("event", include_secret=True)
    signals = derive_document_signals(document, anchor_batch_size=2)
    profile = _profile(document)
    plan = compile_analysis_plan(profile, planning_scope=signals.planning_scope)
    item = next(
        candidate
        for candidate in plan.work_items
        if candidate.pass_type is AnalysisPass.PASSAGE_ANALYSIS
    )
    gateway = NoModelGateway()
    adapted = adapt_work_item_spec(
        plan=plan,
        item=item,
        signals=signals,
        source_id=document.id,
        gateway=gateway,
    )
    repeated = adapt_work_item_spec(
        plan=plan,
        item=item,
        signals=signals,
        source_id=document.id,
        gateway=gateway,
    )

    assert adapted.parameters["plan_work_item_id"] == item.id
    assert adapted.parameters["depends_on"] == list(item.depends_on)
    assert adapted.anchor_ids == signals.planning_scope.anchor_batches[0].anchor_ids
    assert adapted.pipeline_version == plan.pipeline_version
    assert adapted.prompt_bundle_version == plan.prompt_bundle_version
    assert adapted.model_route == "none.none"
    assert adapted.idempotency_key == repeated.idempotency_key
    persisted = json.dumps(adapted.storage_payload(), ensure_ascii=False)
    assert SECRET not in persisted
    assert "paragraph" not in persisted.casefold()


def test_no_model_pipeline_stops_waiting_review_with_explicit_gaps(tmp_path: Path):
    document = _document("argument")
    repository = _repository(tmp_path)
    workspace = repository.create_workspace("ws_no_model")

    result = run_exploration_pipeline(
        document,
        repository=repository,
        workspace_id=workspace.id,
        gateway=NoModelGateway(),
        anchor_batch_size=2,
    )

    assert result.state == "waiting_review"
    assert repository.get_run(result.run_id).state is RunState.WAITING_REVIEW
    assert result.profile.primary_type is BookType.ARGUMENTATIVE_MONOGRAPH
    assert result.quality_report.model_not_called_count > 0
    assert any(gap.code == "model_not_called" for gap in result.artifacts.gaps)
    assert result.quality_report.accepted_claim_count == 0
    assert result.projections.argument.nodes == ()
    assert result.projections.timeline.items == ()
    assert "human_review_required" in result.quality_report.blocking_gate_failures
    assert all(
        plan_id in result.completed_plan_work_item_ids
        for plan_id in (
            item.id
            for item in result.plan.work_items
            if item.pass_type not in {AnalysisPass.HUMAN_REVIEW, AnalysisPass.BUILD_PROJECTIONS}
        )
    )
    repository.close()


def test_reviewed_projection_retains_anchor_return_path(tmp_path: Path):
    document = _document("event")
    signals = derive_document_signals(document, anchor_batch_size=2)
    profile = _profile(document)
    plan = compile_analysis_plan(profile, planning_scope=signals.planning_scope)
    structured = {}
    expected_anchor = None
    expected_event = None
    for item in plan.work_items:
        if item.executor is not ExecutorKind.MODEL or item.input_unit.value != "anchor_batch":
            continue
        anchor_ids = next(
            batch.anchor_ids
            for batch in signals.planning_scope.anchor_batches
            if item.scope_key.endswith(f":batch:{batch.id}")
        )
        anchor_id = anchor_ids[0]
        claim_id = f"claim_{item.id}"
        output = {
            "claims": [
                {
                    "id": claim_id,
                    "statement": "来自单一段落锚点的候选陈述。",
                    "kind": "source_statement",
                    "source_anchor_ids": [anchor_id],
                }
            ]
        }
        if item.pass_type is AnalysisPass.EVENT_EXTRACTION:
            event_id = f"event_{item.id}"
            output["events"] = [
                {
                    "id": event_id,
                    "title": "候选事件",
                    "summary": "只重组当前候选主张。",
                    "claim_ids": [claim_id],
                    "source_anchor_ids": [anchor_id],
                }
            ]
            expected_anchor = anchor_id
            expected_event = event_id
        structured[item.id] = output

    gateway = DeterministicModelGateway(structured_extract_outputs=structured)
    repository = _repository(tmp_path)
    workspace = repository.create_workspace("ws_reviewed")

    def accept_all(artifacts: AnalysisArtifacts) -> AnalysisArtifacts:
        return artifacts.model_copy(
            update={
                "claims": [
                    item.model_copy(update={"review_status": "accepted"})
                    for item in artifacts.claims
                ],
                "events": [
                    item.model_copy(update={"review_status": "accepted"})
                    for item in artifacts.events
                ],
            }
        )

    result = run_exploration_pipeline(
        document,
        repository=repository,
        workspace_id=workspace.id,
        gateway=gateway,
        reviewer=accept_all,
        anchor_batch_size=2,
    )

    assert result.state == "completed"
    assert expected_event is not None and expected_anchor is not None
    scene = next(scene for scene in result.projections.scenes if scene.event_id == expected_event)
    assert scene.source_anchor_ids == (expected_anchor,)
    node = next(
        node
        for node in result.projections.argument.nodes
        if node.claim_id in scene.claim_ids
    )
    assert node.source_anchor_ids == (expected_anchor,)
    assert expected_anchor in signals.anchor_ids
    assert result.quality_report.accepted_event_count > 0
    assert "human_review_required" not in result.quality_report.blocking_gate_failures
    repository.close()


def test_waiting_review_run_accepts_later_review_and_reuses_completed_work(
    tmp_path: Path,
):
    document = _document("event")
    repository = _repository(tmp_path)
    workspace = repository.create_workspace("ws_review_later")
    gateway = DeterministicModelGateway()

    waiting = run_exploration_pipeline(
        document,
        repository=repository,
        workspace_id=workspace.id,
        gateway=gateway,
        anchor_batch_size=2,
    )
    assert waiting.state == "waiting_review"
    assert repository.get_run(waiting.run_id).state is RunState.WAITING_REVIEW
    attempts_before_review = sum(
        len(repository.list_attempts(item.id))
        for item in repository.list_run_work_items(waiting.run_id)
    )

    def accept_all(artifacts: AnalysisArtifacts) -> AnalysisArtifacts:
        return artifacts.model_copy(
            update={
                "claims": [
                    item.model_copy(update={"review_status": "accepted"})
                    for item in artifacts.claims
                ],
                "events": [
                    item.model_copy(update={"review_status": "accepted"})
                    for item in artifacts.events
                ],
            }
        )

    completed = run_exploration_pipeline(
        document,
        repository=repository,
        workspace_id=workspace.id,
        gateway=gateway,
        reviewer=accept_all,
        run_id=waiting.run_id,
        anchor_batch_size=2,
    )
    assert completed.state == "completed"
    assert repository.get_run(waiting.run_id).state is RunState.COMPLETED
    assert sum(
        item.attempt_count
        for item in repository.list_run_work_items(waiting.run_id)
        if item.pass_type
        not in {AnalysisPass.HUMAN_REVIEW.value, AnalysisPass.BUILD_PROJECTIONS.value}
    ) == attempts_before_review

    attempts_after_completion = sum(
        len(repository.list_attempts(item.id))
        for item in repository.list_run_work_items(waiting.run_id)
    )
    repeated = run_exploration_pipeline(
        document,
        repository=repository,
        workspace_id=workspace.id,
        gateway=gateway,
        run_id=waiting.run_id,
        anchor_batch_size=2,
    )
    assert repeated.state == "completed"
    assert repository.get_run(waiting.run_id).state is RunState.COMPLETED
    assert sum(
        len(repository.list_attempts(item.id))
        for item in repository.list_run_work_items(waiting.run_id)
    ) == attempts_after_completion
    repository.close()


def test_interrupted_runtime_item_resumes_and_private_body_never_enters_control_plane(
    tmp_path: Path,
):
    document = _document("event", include_secret=True)
    signals = derive_document_signals(document, anchor_batch_size=2)
    profile = _profile(document)
    plan = compile_analysis_plan(profile, planning_scope=signals.planning_scope)
    first_plan_item = plan.work_items[0]

    repository = _repository(tmp_path)
    workspace = repository.create_workspace("ws_resume_pipeline")
    runtime = ExplorationRuntime(repository)
    run = runtime.create_run(workspace.id, plan_revision=1)
    first_runtime_item = runtime.enqueue(
        run.id,
        adapt_work_item_spec(
            plan=plan,
            item=first_plan_item,
            signals=signals,
            source_id=document.id,
            gateway=NoModelGateway(),
        ),
    ).item
    claimed = repository.claim_next_work_item(run.id)
    assert claimed is not None
    assert repository.get_work_item(first_runtime_item.id).state is WorkItemState.RUNNING
    repository.close()

    reopened = _repository(tmp_path)
    assert reopened.get_work_item(first_runtime_item.id).state is WorkItemState.RETRY_WAIT
    result = run_exploration_pipeline(
        document,
        repository=reopened,
        workspace_id=workspace.id,
        gateway=NoModelGateway(),
        run_id=run.id,
        anchor_batch_size=2,
    )

    assert result.state == "waiting_review"
    attempts = reopened.list_attempts(first_runtime_item.id)
    assert [attempt.state for attempt in attempts] == [
        AttemptState.INTERRUPTED,
        AttemptState.SUCCEEDED,
    ]
    assert reopened.get_run(run.id).state is RunState.WAITING_REVIEW
    for item in reopened.list_run_work_items(run.id):
        assert SECRET not in json.dumps(item.spec, ensure_ascii=False)
    for checkpoint in reopened.list_checkpoints(run.id):
        assert SECRET not in json.dumps(checkpoint.state, ensure_ascii=False)
    sqlite_bytes = b"".join(
        path.read_bytes()
        for path in tmp_path.glob("pipeline.sqlite3*")
        if path.is_file()
    )
    assert SECRET.encode() not in sqlite_bytes
    reopened.close()
