"""Focused contract tests for source-bounded argument graph generation."""
from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

from app.prompts.book_argument_graph import (
    BOOK_ARGUMENT_GRAPH_GUARDRAILS,
    render_book_argument_graph_messages,
)
from app.schemas.exploration import (
    ArgumentGraph,
    ComposeRequest,
    ImportExplorationRequest,
    SourceFormat,
)
from app.services.exploration_service import ExplorationStore


def _graph_payload() -> dict:
    node_types = [
        ("question", "platform_inference"),
        ("material_observation", "author_judgment"),
        ("reasoning_mechanism", "platform_inference"),
        ("action_or_turn", "historical_fact"),
        ("consequence", "author_judgment"),
        ("limitation", "uncertainty"),
    ]
    return {
        "id": "graph_fixture",
        "question": "材料如何组织这段因果链？",
        "nodes": [
            {
                "id": f"node_{node_type}",
                "node_type": node_type,
                "title": node_type,
                "summary": f"{node_type} 摘要",
                "detail": f"{node_type} 详情",
                "epistemic_layer": layer,
                "source_anchor_ids": ["anchor_1"],
            }
            for node_type, layer in node_types
        ],
        "edges": [
            {
                "id": "edge_question_observation",
                "from_node_id": "node_question",
                "to_node_id": "node_material_observation",
                "relation": "frames",
                "label": "界定观察对象",
                "source_anchor_ids": ["anchor_1"],
            },
            {
                "id": "edge_observation_mechanism",
                "from_node_id": "node_material_observation",
                "to_node_id": "node_reasoning_mechanism",
                "relation": "grounds",
                "label": "支撑机制判断",
                "source_anchor_ids": ["anchor_1"],
            },
            {
                "id": "edge_mechanism_turn",
                "from_node_id": "node_reasoning_mechanism",
                "to_node_id": "node_action_or_turn",
                "relation": "explains",
                "label": "解释行动转折",
                "source_anchor_ids": ["anchor_1"],
            },
            {
                "id": "edge_turn_consequence",
                "from_node_id": "node_action_or_turn",
                "to_node_id": "node_consequence",
                "relation": "leads_to",
                "label": "导向后果",
                "source_anchor_ids": ["anchor_1"],
            },
            {
                "id": "edge_limitation_consequence",
                "from_node_id": "node_limitation",
                "to_node_id": "node_consequence",
                "relation": "qualifies",
                "label": "限制外推",
                "source_anchor_ids": ["anchor_1"],
            },
        ],
    }


def test_argument_graph_requires_a_limitation_and_resolvable_edges_without_forcing_templates():
    graph = ArgumentGraph.model_validate(_graph_payload())
    assert {node.node_type.value for node in graph.nodes} == {
        "question",
        "material_observation",
        "reasoning_mechanism",
        "action_or_turn",
        "consequence",
        "limitation",
    }

    compact_graph = _graph_payload()
    compact_graph["nodes"] = [compact_graph["nodes"][1], compact_graph["nodes"][-1]]
    compact_graph["edges"] = [
        {
            "id": "edge_limitation_observation",
            "from_node_id": "node_limitation",
            "to_node_id": "node_material_observation",
            "relation": "qualifies",
            "label": "限制外推",
            "source_anchor_ids": ["anchor_1"],
        }
    ]
    assert len(ArgumentGraph.model_validate(compact_graph).nodes) == 2

    missing_limitation = _graph_payload()
    missing_limitation["nodes"][-1] = {
        **missing_limitation["nodes"][-1],
        "id": "node_question_duplicate_kind",
        "node_type": "question",
    }
    with pytest.raises(ValidationError, match="missing required safety node types"):
        ArgumentGraph.model_validate(missing_limitation)

    dangling_edge = _graph_payload()
    dangling_edge["edges"][0]["to_node_id"] = "node_not_present"
    with pytest.raises(ValidationError, match="references an unknown node"):
        ArgumentGraph.model_validate(dangling_edge)


def test_deep_analysis_builds_fixed_needs_model_prompt_contract_without_calling_model():
    store = ExplorationStore()
    snapshot = store.create(
        ImportExplorationRequest(
            source_format=SourceFormat.MARKDOWN,
            content="# 第一章\n\n这是只在进程内保存的私有材料。",
            title="私有测试书",
        )
    )
    anchor = snapshot.document.sections[0].paragraphs[0]
    result = store.compose(
        snapshot.id,
        ComposeRequest(
            base_revision=snapshot.revision,
            intent="request_deep_analysis",
            message="分析作者怎样从材料观察推到后果。",
            anchor_ids=[anchor.id],
            requested_views=["causal_threads", "map_candidates"],
        ),
    )

    queued = result.snapshot.analysis_queue[0]
    contract = queued.prompt_contract
    assert queued.processing_status == "needs_model"
    assert queued.candidate_output is None
    assert contract.contract_version == "book_argument_graph.v1"
    assert contract.invocation_status == "not_called"
    assert contract.processing_status == "needs_model"
    assert contract.source_anchor_ids == [anchor.id]
    assert contract.source_locators[0].paragraph_id == anchor.id
    assert contract.source_locators[0].page_label is None
    assert contract.source_payload_state == "requires_runtime_injection"
    assert contract.guardrails == list(BOOK_ARGUMENT_GRAPH_GUARDRAILS)
    assert contract.output_schema["title"] == "ArgumentGraph"

    serialized_contract = contract.model_dump_json()
    assert "这是只在进程内保存的私有材料" not in serialized_contract

    messages = render_book_argument_graph_messages(contract)
    assert [message["role"] for message in messages] == ["system", "user"]
    assert "忠实保留作者" in messages[0]["content"]
    assert "不为填满结构强造反方" in messages[0]["content"]
    assert "不得猜测材料未给出的地点、坐标、行军路线" in messages[0]["content"]
    user_payload = json.loads(messages[1]["content"])
    assert user_payload["source_payload"]["state"] == "requires_runtime_injection"
    assert user_payload["source_payload"]["injection_key"] == (
        "source_text_by_anchor_id"
    )
    assert "这是只在进程内保存的私有材料" not in messages[1]["content"]
