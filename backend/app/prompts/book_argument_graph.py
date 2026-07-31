"""Prompt contract for source-bounded book argument graphs.

The service builds and returns this contract without invoking a model. Source
text is injected only by a future, explicitly authorised runtime integration;
the queued scaffold contains locators and a verifiable output schema.
"""
from __future__ import annotations

import json

from ..schemas.exploration import (
    ArgumentGraph,
    ArgumentPromptContract,
    SourceLocator,
)


BOOK_ARGUMENT_GRAPH_GUARDRAILS = (
    "忠实保留作者的观察位置和判断主体，不把作者判断改写成无主体历史事实。",
    "每个节点必须以 epistemic_layer 区分历史事实、作者判断、平台推断和不确定性。",
    "只有输入材料对同一命题提供明确冲突时才建立 contradicts 边，不为填满结构强造反方。",
    "每个节点必须引用 source_anchor_ids；它们必须能在 source_locators 中解析到 locator。",
    "不得猜测材料未给出的地点、坐标、行军路线、日期精度、人物动机或因果强度。",
    "证据不足时建立 limitation 节点并降低结论强度，不得用常识或模型记忆补齐。",
    "问题、材料观察、推理机制、行动或转折、后果、限制或不确定性六类节点缺一不可。",
    "只输出符合 output_schema 的 JSON 对象，不输出 Markdown、解释性前后缀或伪引文。",
)


def build_book_argument_prompt_contract(
    *,
    request_text: str,
    source_locators: list[SourceLocator],
    requested_views: list[str],
) -> ArgumentPromptContract:
    """Build a queueable contract; this function never performs a model call."""
    unique_locators: list[SourceLocator] = []
    seen_anchor_ids: set[str] = set()
    for locator in source_locators:
        anchor_id = locator.paragraph_id
        if anchor_id in seen_anchor_ids:
            continue
        seen_anchor_ids.add(anchor_id)
        unique_locators.append(locator.model_copy(deep=True))

    unique_views = list(dict.fromkeys(requested_views))
    return ArgumentPromptContract(
        request_text=request_text,
        source_anchor_ids=[locator.paragraph_id for locator in unique_locators],
        source_locators=unique_locators,
        source_payload_state=(
            "requires_runtime_injection" if unique_locators else "missing_source"
        ),
        requested_views=unique_views,
        guardrails=list(BOOK_ARGUMENT_GRAPH_GUARDRAILS),
        output_schema=ArgumentGraph.model_json_schema(mode="validation"),
    )


def render_book_argument_graph_messages(
    contract: ArgumentPromptContract,
) -> list[dict[str, str]]:
    """Render future model messages while leaving source text as a runtime slot."""
    system_content = "\n".join(
        [
            "你是历史材料论证图编织器，只能使用运行时注入的来源材料。",
            *[f"{index}. {rule}" for index, rule in enumerate(contract.guardrails, 1)],
            "输出 JSON Schema：",
            json.dumps(contract.output_schema, ensure_ascii=False, sort_keys=True),
        ]
    )
    user_payload = {
        "contract_version": contract.contract_version,
        "request_text": contract.request_text,
        "requested_views": contract.requested_views,
        "source_locators": [
            locator.model_dump(mode="json") for locator in contract.source_locators
        ],
        "source_payload": {
            "state": contract.source_payload_state,
            "injection_key": "source_text_by_anchor_id",
            "note": "模型调用前按 anchor_id 注入用户授权的源文本；当前 scaffold 不含正文。",
        },
    }
    return [
        {"role": "system", "content": system_content},
        {
            "role": "user",
            "content": json.dumps(user_payload, ensure_ascii=False, sort_keys=True),
        },
    ]
