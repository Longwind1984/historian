"""Offline contract tests for the real model boundary and LangGraph shell."""

from __future__ import annotations

import json
from pathlib import Path
from time import sleep
from types import SimpleNamespace

import httpx
import pytest

from app.exploration.model_gateway import (
    CrossUnitSynthesisRequest,
    EvidenceJudgeRequest,
    ModelTimeouts,
    OpenAICompatibleModelGateway,
    StructuredExtractRequest,
    build_configured_model_gateway,
)
from app.exploration.runtime import PermanentWorkError, RetryableWorkError
from app.exploration.workflow_graph import (
    WorkflowStepResult,
    build_exploration_workflow,
    initial_workflow_state,
    sqlite_checkpointer,
    workflow_config,
)


SIMPLE_SCHEMAS = {
    capability: {
        "type": "object",
        "properties": {"capability": {"type": "string", "const": capability}},
        "required": ["capability"],
        "additionalProperties": False,
    }
    for capability in (
        "structured_extract",
        "cross_unit_synthesis",
        "evidence_judge",
    )
}


def _response(capability: str, status_code: int = 200) -> httpx.Response:
    return httpx.Response(
        status_code,
        json={
            "choices": [
                {
                    "message": {
                        "content": json.dumps({"capability": capability})
                    }
                }
            ]
        },
    )


def _gateway(handler, *, secret: str = "fixture-private-token", total: float = 1):
    return OpenAICompatibleModelGateway(
        base_url="https://models.example.test/v1",
        api_key=secret,
        structured_extract_model="extract-model",
        cross_unit_synthesis_model="synthesis-model",
        evidence_judge_model="judge-model",
        output_schemas=SIMPLE_SCHEMAS,
        timeouts=ModelTimeouts(
            connect=0.2,
            read=0.2,
            write=0.2,
            pool=0.2,
            total=total,
        ),
        transport=httpx.MockTransport(handler),
    )


def _default_schema_gateway(handler):
    return OpenAICompatibleModelGateway(
        base_url="https://models.example.test/v1",
        api_key="fixture-private-token",
        structured_extract_model="extract-model",
        cross_unit_synthesis_model="synthesis-model",
        evidence_judge_model="judge-model",
        transport=httpx.MockTransport(handler),
    )


def test_openai_compatible_envelope_routes_models_and_keeps_source_runtime_only():
    requests: list[dict] = []

    def handler(request: httpx.Request) -> httpx.Response:
        envelope = json.loads(request.content)
        user = json.loads(envelope["messages"][1]["content"])
        requests.append(
            {
                "authorization": request.headers["authorization"],
                "envelope": envelope,
                "user": user,
                "timeout": request.extensions["timeout"],
            }
        )
        return _response(user["capability"])

    gateway = _gateway(handler)
    extract = gateway.structured_extract(
        StructuredExtractRequest(
            unit_id="unit-1",
            source_anchor_ids=["anchor-1"],
            requested_outputs=["claims"],
            source_text_by_anchor_id={"anchor-1": "private paragraph"},
        )
    )
    synthesis = gateway.cross_unit_synthesis(
        CrossUnitSynthesisRequest(
            synthesis_id="synthesis-1",
            input_artifact_ids=["claim-1"],
            lower_level_artifacts=[{"id": "claim-1"}],
        )
    )
    judgment = gateway.evidence_judge(
        EvidenceJudgeRequest(
            judgment_id="judgment-1",
            candidate_artifact_ids=["claim-1"],
            candidate_artifacts=[{"id": "claim-1"}],
            evidence_artifacts=[],
        )
    )
    gateway.close()

    assert [item.model for item in (extract, synthesis, judgment)] == [
        "extract-model",
        "synthesis-model",
        "judge-model",
    ]
    assert [item["envelope"]["model"] for item in requests] == [
        "extract-model",
        "synthesis-model",
        "judge-model",
    ]
    assert [item["user"]["capability"] for item in requests] == [
        "structured_extract",
        "cross_unit_synthesis",
        "evidence_judge",
    ]
    assert requests[0]["user"]["input"]["source_text_by_anchor_id"] == {
        "anchor-1": "private paragraph"
    }
    assert requests[0]["envelope"]["response_format"] == {
        "type": "json_schema",
        "json_schema": {
            "name": "history_kb_structured_extract",
            "strict": True,
            "schema": SIMPLE_SCHEMAS["structured_extract"],
        },
    }
    assert requests[0]["timeout"] == {
        "connect": 0.2,
        "read": 0.2,
        "write": 0.2,
        "pool": 0.2,
    }
    assert extract.model_dump() == {
        "capability": "structured_extract",
        "status": "succeeded",
        "provider": "openai_compatible",
        "model": "extract-model",
        "output_digest": extract.output_digest,
        "error_code": None,
    }


def test_default_capability_schemas_match_the_pass_parser_contract():
    responses = {
        "structured_extract": {
            "claims": [],
            "temporal_refs": [],
            "location_refs": [],
            "events": [],
        },
        "cross_unit_synthesis": {"claims": []},
        "evidence_judge": {
            "relations": [],
            "counterevidence_not_found_claim_ids": [],
        },
    }
    seen_schemas = {}

    def handler(request: httpx.Request) -> httpx.Response:
        envelope = json.loads(request.content)
        user = json.loads(envelope["messages"][1]["content"])
        capability = user["capability"]
        seen_schemas[capability] = envelope["response_format"]["json_schema"]["schema"]
        return httpx.Response(
            200,
            json={
                "choices": [
                    {"message": {"content": json.dumps(responses[capability])}}
                ]
            },
        )

    gateway = _default_schema_gateway(handler)
    extract = gateway.structured_extract(
        StructuredExtractRequest(
            unit_id="unit-1",
            source_anchor_ids=["anchor-1"],
            source_text_by_anchor_id={"anchor-1": "private paragraph"},
        )
    )
    synthesis = gateway.cross_unit_synthesis(
        CrossUnitSynthesisRequest(
            synthesis_id="synthesis-1",
            input_artifact_ids=["claim-1"],
            lower_level_artifacts=[{"id": "claim-1"}],
        )
    )
    judgment = gateway.evidence_judge(
        EvidenceJudgeRequest(
            judgment_id="judgment-1",
            candidate_artifact_ids=["claim-1"],
            candidate_artifacts=[{"id": "claim-1"}],
            evidence_artifacts=[],
        )
    )
    gateway.close()

    assert extract.output == responses["structured_extract"]
    assert synthesis.output == responses["cross_unit_synthesis"]
    assert judgment.output == responses["evidence_judge"]
    assert "location_refs" in seen_schemas["structured_extract"]["required"]
    assert "locations" not in seen_schemas["structured_extract"]["properties"]
    assert seen_schemas["evidence_judge"]["required"] == [
        "relations",
        "counterevidence_not_found_claim_ids",
    ]


def test_configured_gateway_has_no_silent_remote_fallback():
    offline = build_configured_model_gateway(
        SimpleNamespace(exploration_model_provider="none")
    )
    assert offline.provider == "none"

    with pytest.raises(ValueError, match="requires base URL"):
        build_configured_model_gateway(
            SimpleNamespace(exploration_model_provider="openai_compatible")
        )
    with pytest.raises(ValueError, match="unsupported"):
        build_configured_model_gateway(
            SimpleNamespace(exploration_model_provider="mystery-provider")
        )


@pytest.mark.parametrize(
    ("handler", "expected_error"),
    [
        (
            lambda request: (_ for _ in ()).throw(
                httpx.ReadTimeout("contains provider detail", request=request)
            ),
            "MODEL_IO_TIMEOUT",
        ),
        (lambda _request: httpx.Response(429, text="secret response"), "MODEL_RATE_LIMITED"),
        (lambda _request: httpx.Response(503, text="secret response"), "MODEL_UPSTREAM_5XX"),
    ],
)
def test_retryable_provider_failures_are_classified_without_fallback(
    handler, expected_error
):
    gateway = _gateway(handler)
    with pytest.raises(RetryableWorkError) as raised:
        gateway.structured_extract(
            StructuredExtractRequest(
                unit_id="unit-1",
                source_anchor_ids=["anchor-1"],
                source_text_by_anchor_id={"anchor-1": "private paragraph"},
            )
        )
    gateway.close()
    assert raised.value.error_code == expected_error
    assert str(raised.value) == expected_error


def test_total_deadline_is_separate_from_httpx_phase_timeouts():
    def slow_handler(_request: httpx.Request) -> httpx.Response:
        sleep(0.08)
        return _response("structured_extract")

    gateway = _gateway(slow_handler, total=0.01)
    with pytest.raises(RetryableWorkError, match="MODEL_TOTAL_TIMEOUT"):
        gateway.structured_extract(
            StructuredExtractRequest(
                unit_id="unit-1",
                source_anchor_ids=["anchor-1"],
                source_text_by_anchor_id={"anchor-1": "private paragraph"},
            )
        )
    gateway.close()


@pytest.mark.parametrize(
    ("response", "expected_error"),
    [
        (httpx.Response(200, text="not json"), "MODEL_INVALID_RESPONSE_ENVELOPE"),
        (
            httpx.Response(
                200,
                json={"choices": [{"message": {"content": "not json"}}]},
            ),
            "MODEL_INVALID_JSON",
        ),
        (
            httpx.Response(
                200,
                json={"choices": [{"message": {"content": "[]"}}]},
            ),
            "MODEL_OUTPUT_NOT_OBJECT",
        ),
        (
            httpx.Response(
                200,
                json={"choices": [{"message": {"content": '{"unknown":true}'}}]},
            ),
            "MODEL_SCHEMA_MISMATCH",
        ),
    ],
)
def test_malformed_outputs_fail_closed(response, expected_error):
    gateway = _gateway(lambda _request: response)
    with pytest.raises(PermanentWorkError) as raised:
        gateway.structured_extract(
            StructuredExtractRequest(
                unit_id="unit-1",
                source_anchor_ids=["anchor-1"],
                source_text_by_anchor_id={"anchor-1": "private paragraph"},
            )
        )
    gateway.close()
    assert raised.value.error_code == expected_error


def test_api_key_never_appears_in_repr_or_provider_errors():
    secret = "fixture-sensitive-token"
    gateway = _gateway(
        lambda _request: httpx.Response(400, text=f"echo {secret}"),
        secret=secret,
    )
    assert secret not in repr(gateway)
    with pytest.raises(PermanentWorkError) as raised:
        gateway.structured_extract(
            StructuredExtractRequest(
                unit_id="unit-1",
                source_anchor_ids=["anchor-1"],
                source_text_by_anchor_id={"anchor-1": "private paragraph"},
            )
        )
    gateway.close()
    assert secret not in str(raised.value)
    assert raised.value.error_code == "MODEL_REQUEST_REJECTED"


class RecordingAdapter:
    """Test adapter that commits one result per semantic idempotency key."""

    def __init__(self) -> None:
        self.committed: dict[str, WorkflowStepResult] = {}
        self.steps: list[str] = []

    def execute_once(
        self,
        *,
        idempotency_key,
        step,
        run_id,
        input_artifact_ids,
        control_metadata,
    ) -> WorkflowStepResult:
        del run_id, input_artifact_ids, control_metadata
        if idempotency_key not in self.committed:
            self.steps.append(step)
            outputs = {
                "profile": ("profile-1",),
                "plan": ("plan-1",),
                "dispatch": ("work-1", "work-2"),
                "quality": ("quality-1",),
                "human_review": ("review-1",),
                "projection": ("projection-1",),
            }[step]
            self.committed[idempotency_key] = WorkflowStepResult(outputs)
        return self.committed[idempotency_key]


def _checkpoint_bytes(path: Path) -> bytes:
    return b"".join(
        item.read_bytes()
        for item in path.parent.glob(path.name + "*")
        if item.is_file()
    )


def test_langgraph_checkpoints_resume_at_human_review_and_never_store_source_text(
    tmp_path: Path,
):
    checkpoint_path = tmp_path / "workflow.sqlite3"
    adapter = RecordingAdapter()
    graph = build_exploration_workflow(
        adapter,
        checkpointer=sqlite_checkpointer(checkpoint_path),
    )
    config = workflow_config("workflow-1")
    private_marker = "NEVER-CHECKPOINT-PRIVATE-正文"
    initial = initial_workflow_state(
        workflow_id="workflow-1",
        run_id="run-1",
        source_id="source-1",
        source_checksum="a" * 64,
    )
    # Unknown source text is rejected at graph ingress before LangGraph creates
    # a checkpoint. Source retrieval belongs to workers, not graph state.
    caller_input = {**initial, "source_text": private_marker}

    with pytest.raises(Exception, match="source_text|extra"):
        graph.invoke(caller_input, config)
    assert private_marker.encode() not in _checkpoint_bytes(checkpoint_path)

    interrupted = graph.invoke(initial, config)
    snapshot = graph.get_state(config)
    assert interrupted["status"] == "quality_checked"
    assert snapshot.next == ("human_review",)
    assert adapter.steps == ["profile", "plan", "dispatch", "quality"]
    assert "source_text" not in snapshot.values
    assert private_marker.encode() not in _checkpoint_bytes(checkpoint_path)

    graph.update_state(config, {"review_decision": "approved"})
    completed = graph.invoke(None, config)
    assert completed["status"] == "completed"
    assert completed["projection_bundle_id"] == "projection-1"
    assert adapter.steps == [
        "profile",
        "plan",
        "dispatch",
        "quality",
        "human_review",
        "projection",
    ]
    assert private_marker.encode() not in _checkpoint_bytes(checkpoint_path)


def test_rejected_review_ends_without_projection_side_effect(tmp_path: Path):
    adapter = RecordingAdapter()
    graph = build_exploration_workflow(
        adapter,
        checkpointer=sqlite_checkpointer(tmp_path / "rejected.sqlite3"),
    )
    config = workflow_config("workflow-rejected")
    graph.invoke(
        initial_workflow_state(
            workflow_id="workflow-rejected",
            run_id="run-rejected",
            source_id="source-rejected",
            source_checksum="b" * 64,
        ),
        config,
    )
    graph.update_state(config, {"review_decision": "rejected"})
    completed = graph.invoke(None, config)

    assert completed["status"] == "completed_without_projection"
    assert "projection_bundle_id" not in completed
    assert adapter.steps[-1] == "human_review"
    assert "projection" not in adapter.steps
