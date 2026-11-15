"""Provider-neutral model boundary for the v6 exploration pipeline.

The workflow depends on capabilities, never on a vendor SDK.  Requests keep
private source text in runtime-only fields so their normal serialisation is
safe to persist as a work-item/checkpoint envelope.  Implementations must
still treat the in-memory objects as private.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from copy import deepcopy
from dataclasses import dataclass
from hashlib import sha256
import json
from time import monotonic
from typing import Any, Literal, Mapping, Protocol, Sequence, runtime_checkable

import httpx

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .runtime import PermanentWorkError, RetryableWorkError


JsonObject = dict[str, Any]
Capability = Literal[
    "structured_extract",
    "cross_unit_synthesis",
    "evidence_judge",
]


def _digest_json(value: Any) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    ).encode("utf-8")
    return sha256(encoded).hexdigest()


class StructuredExtractRequest(BaseModel):
    """A bounded source packet for one local extraction pass."""

    model_config = ConfigDict(extra="forbid")

    unit_id: str = Field(min_length=1, max_length=200)
    source_anchor_ids: list[str] = Field(min_length=1, max_length=80)
    input_artifact_ids: list[str] = Field(default_factory=list, max_length=200)
    requested_outputs: list[str] = Field(default_factory=list, max_length=20)
    analysis_focus: str = Field(default="passage_analysis", min_length=1, max_length=80)
    source_text_by_anchor_id: dict[str, str] = Field(
        exclude=True,
        repr=False,
        description="Runtime-only private source injection; never checkpointed.",
    )

    @model_validator(mode="after")
    def _source_packet_matches_anchor_list(self) -> StructuredExtractRequest:
        if len(set(self.source_anchor_ids)) != len(self.source_anchor_ids):
            raise ValueError("source_anchor_ids must be unique")
        if set(self.source_text_by_anchor_id) != set(self.source_anchor_ids):
            raise ValueError(
                "source_text_by_anchor_id must exactly match source_anchor_ids"
            )
        return self


class CrossUnitSynthesisRequest(BaseModel):
    """Structured lower-level artifacts for a cross-unit synthesis pass."""

    model_config = ConfigDict(extra="forbid")

    synthesis_id: str = Field(min_length=1, max_length=200)
    input_artifact_ids: list[str] = Field(min_length=1, max_length=500)
    lower_level_artifacts: list[JsonObject] = Field(exclude=True, repr=False)
    required_output_kind: str = "platform_inference"


class EvidenceJudgeRequest(BaseModel):
    """Independent review request separated from the generating pass."""

    model_config = ConfigDict(extra="forbid")

    judgment_id: str = Field(min_length=1, max_length=200)
    candidate_artifact_ids: list[str] = Field(min_length=1, max_length=500)
    evidence_artifact_ids: list[str] = Field(default_factory=list, max_length=500)
    candidate_artifacts: list[JsonObject] = Field(exclude=True, repr=False)
    evidence_artifacts: list[JsonObject] = Field(exclude=True, repr=False)


class GatewayResult(BaseModel):
    """A persistence-safe result envelope.

    ``output`` is intentionally excluded from normal serialisation.  The
    workflow validates it and persists typed artifacts instead.  This prevents
    a generic model trace from becoming a shadow copy of a private source.
    """

    model_config = ConfigDict(extra="forbid")

    capability: str
    status: str = Field(pattern="^(succeeded|not_called|failed)$")
    provider: str
    model: str
    output_digest: str | None = None
    output: JsonObject | None = Field(default=None, exclude=True, repr=False)
    error_code: str | None = None

    @model_validator(mode="after")
    def _status_matches_output(self) -> GatewayResult:
        if self.status == "succeeded" and self.output is None:
            raise ValueError("A succeeded gateway result requires output")
        if self.status != "succeeded" and self.output is not None:
            raise ValueError("Only a succeeded gateway result may carry output")
        if self.output is not None and self.output_digest != _digest_json(self.output):
            raise ValueError("output_digest does not match output")
        return self


@runtime_checkable
class ModelGateway(Protocol):
    """Capability contract consumed by deterministic workflow code."""

    def structured_extract(self, request: StructuredExtractRequest) -> GatewayResult:
        ...

    def cross_unit_synthesis(
        self, request: CrossUnitSynthesisRequest
    ) -> GatewayResult:
        ...

    def evidence_judge(self, request: EvidenceJudgeRequest) -> GatewayResult:
        ...


class NoModelGateway:
    """Explicit local/offline route that never fabricates a model response."""

    provider = "none"
    model = "none"

    def _not_called(self, capability: str) -> GatewayResult:
        return GatewayResult(
            capability=capability,
            status="not_called",
            provider=self.provider,
            model=self.model,
            error_code="model_not_configured",
        )

    def structured_extract(self, request: StructuredExtractRequest) -> GatewayResult:
        return self._not_called("structured_extract")

    def cross_unit_synthesis(
        self, request: CrossUnitSynthesisRequest
    ) -> GatewayResult:
        return self._not_called("cross_unit_synthesis")

    def evidence_judge(self, request: EvidenceJudgeRequest) -> GatewayResult:
        return self._not_called("evidence_judge")


class DeterministicModelGateway:
    """Fixture/fake gateway used for recovery and contract tests.

    Results are selected by request ID.  There is no fallback generation: a
    missing fixture is reported as ``not_called``.  This makes the fake useful
    for proving orchestration without smuggling historical assumptions into
    production code.
    """

    provider = "deterministic"
    model = "fixture-v1"

    def __init__(
        self,
        *,
        structured_extract_outputs: Mapping[str, JsonObject] | None = None,
        cross_unit_synthesis_outputs: Mapping[str, JsonObject] | None = None,
        evidence_judge_outputs: Mapping[str, JsonObject] | None = None,
    ) -> None:
        self._outputs: dict[str, Mapping[str, JsonObject]] = {
            "structured_extract": structured_extract_outputs or {},
            "cross_unit_synthesis": cross_unit_synthesis_outputs or {},
            "evidence_judge": evidence_judge_outputs or {},
        }

    def _result(self, capability: str, request_id: str) -> GatewayResult:
        fixture = self._outputs[capability].get(request_id)
        if fixture is None:
            return GatewayResult(
                capability=capability,
                status="not_called",
                provider=self.provider,
                model=self.model,
                error_code="fixture_missing",
            )
        output = deepcopy(dict(fixture))
        return GatewayResult(
            capability=capability,
            status="succeeded",
            provider=self.provider,
            model=self.model,
            output=output,
            output_digest=_digest_json(output),
        )

    def structured_extract(self, request: StructuredExtractRequest) -> GatewayResult:
        return self._result("structured_extract", request.unit_id)

    def cross_unit_synthesis(
        self, request: CrossUnitSynthesisRequest
    ) -> GatewayResult:
        return self._result("cross_unit_synthesis", request.synthesis_id)

    def evidence_judge(self, request: EvidenceJudgeRequest) -> GatewayResult:
        return self._result("evidence_judge", request.judgment_id)


@dataclass(frozen=True)
class ModelTimeouts:
    """Explicit transport and wall-clock bounds for one provider call.

    HTTPX's four timeout values bound individual I/O phases. ``total`` is a
    separate caller deadline enforced around the complete request. A timed-out
    transport thread remains bounded by the per-phase limits and its result is
    discarded; it can never be interpreted as a successful model response.
    """

    connect: float = 5.0
    read: float = 30.0
    write: float = 10.0
    pool: float = 5.0
    total: float = 45.0

    def __post_init__(self) -> None:
        values = (self.connect, self.read, self.write, self.pool, self.total)
        if any(value <= 0 or value > 3600 for value in values):
            raise ValueError("model timeouts must be within (0, 3600] seconds")

    def as_httpx(self) -> httpx.Timeout:
        return httpx.Timeout(
            connect=self.connect,
            read=self.read,
            write=self.write,
            pool=self.pool,
        )


@dataclass(frozen=True)
class CapabilityRoute:
    """One independently selectable model and its exact output contract."""

    model: str
    output_schema: Mapping[str, Any]
    max_output_tokens: int = 4096

    def __post_init__(self) -> None:
        if not self.model or len(self.model) > 200:
            raise ValueError("model must be a bounded non-empty identifier")
        if not isinstance(self.output_schema, Mapping):
            raise ValueError("output_schema must be a JSON Schema object")
        if self.output_schema.get("type") != "object":
            raise ValueError("capability output_schema must have type=object")
        if not 1 <= self.max_output_tokens <= 128_000:
            raise ValueError("max_output_tokens is outside the supported range")


_STRING_ARRAY = {
    "type": "array",
    "items": {"type": "string"},
}


_DEFAULT_SCHEMAS: dict[Capability, JsonObject] = {
    "structured_extract": {
        "type": "object",
        "properties": {
            "claims": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string"},
                        "statement": {"type": "string"},
                        "kind": {
                            "type": "string",
                            "enum": ["source_statement", "author_judgment"],
                        },
                        "speaker": {"type": ["string", "null"]},
                        "source_anchor_ids": _STRING_ARRAY,
                        "derived_from_claim_ids": _STRING_ARRAY,
                        "external_source_ids": _STRING_ARRAY,
                        "limitations": _STRING_ARRAY,
                    },
                    "required": [
                        "id",
                        "statement",
                        "kind",
                        "speaker",
                        "source_anchor_ids",
                        "derived_from_claim_ids",
                        "external_source_ids",
                        "limitations",
                    ],
                    "additionalProperties": False,
                },
            },
            "temporal_refs": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string"},
                        "original_label": {"type": "string"},
                        "source_anchor_ids": _STRING_ARRAY,
                        "normalization_status": {
                            "type": "string",
                            "enum": ["verbatim", "candidate"],
                        },
                        "normalized_start": {"type": "null"},
                        "normalized_end": {"type": "null"},
                        "precision": {
                            "type": "string",
                            "enum": [
                                "exact_day",
                                "month",
                                "year",
                                "range",
                                "relative",
                                "unknown",
                            ],
                        },
                    },
                    "required": [
                        "id",
                        "original_label",
                        "source_anchor_ids",
                        "normalization_status",
                        "normalized_start",
                        "normalized_end",
                        "precision",
                    ],
                    "additionalProperties": False,
                },
            },
            "location_refs": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string"},
                        "original_label": {"type": "string"},
                        "source_anchor_ids": _STRING_ARRAY,
                        "resolved_entity_id": {"type": ["string", "null"]},
                        "geometry_status": {
                            "type": "string",
                            "enum": ["candidate", "ambiguous", "none"],
                        },
                    },
                    "required": [
                        "id",
                        "original_label",
                        "source_anchor_ids",
                        "resolved_entity_id",
                        "geometry_status",
                    ],
                    "additionalProperties": False,
                },
            },
            "events": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string"},
                        "title": {"type": "string"},
                        "summary": {"type": "string"},
                        "claim_ids": _STRING_ARRAY,
                        "source_anchor_ids": _STRING_ARRAY,
                        "temporal_ref_ids": _STRING_ARRAY,
                        "location_ref_ids": _STRING_ARRAY,
                        "person_ids": _STRING_ARRAY,
                    },
                    "required": [
                        "id",
                        "title",
                        "summary",
                        "claim_ids",
                        "source_anchor_ids",
                        "temporal_ref_ids",
                        "location_ref_ids",
                        "person_ids",
                    ],
                    "additionalProperties": False,
                },
            },
        },
        "required": [
            "claims",
            "temporal_refs",
            "location_refs",
            "events",
        ],
        "additionalProperties": False,
    },
    "cross_unit_synthesis": {
        "type": "object",
        "properties": {
            "claims": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string"},
                        "statement": {"type": "string"},
                        "kind": {"type": "string", "const": "platform_inference"},
                        "speaker": {"type": "null"},
                        "source_anchor_ids": _STRING_ARRAY,
                        "derived_from_claim_ids": _STRING_ARRAY,
                        "external_source_ids": _STRING_ARRAY,
                        "limitations": _STRING_ARRAY,
                    },
                    "required": [
                        "id",
                        "statement",
                        "kind",
                        "speaker",
                        "source_anchor_ids",
                        "derived_from_claim_ids",
                        "external_source_ids",
                        "limitations",
                    ],
                    "additionalProperties": False,
                },
            },
        },
        "required": ["claims"],
        "additionalProperties": False,
    },
    "evidence_judge": {
        "type": "object",
        "properties": {
            "relations": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string"},
                        "from_claim_id": {"type": "string"},
                        "to_claim_id": {"type": "string"},
                        "relation": {
                            "type": "string",
                            "enum": [
                                "supports",
                                "corroborates",
                                "supplements",
                                "different_scope",
                                "method_difference",
                                "narrows",
                                "contradicts",
                                "causal_proposal",
                                "author_interprets",
                                "model_infers",
                            ],
                        },
                        "source_anchor_ids": _STRING_ARRAY,
                        "external_source_ids": _STRING_ARRAY,
                        "comparison_scope": {"type": ["string", "null"]},
                    },
                    "required": [
                        "id",
                        "from_claim_id",
                        "to_claim_id",
                        "relation",
                        "source_anchor_ids",
                        "external_source_ids",
                        "comparison_scope",
                    ],
                    "additionalProperties": False,
                },
            },
            "counterevidence_not_found_claim_ids": _STRING_ARRAY,
        },
        "required": ["relations", "counterevidence_not_found_claim_ids"],
        "additionalProperties": False,
    },
}


_CAPABILITY_INSTRUCTIONS: dict[Capability, str] = {
    "structured_extract": (
        "Analyse only the supplied anchor packet. Separate statements made by the "
        "source from the author's judgments; do not emit platform inferences here. "
        "Every claim, time mention, place mention, and event must cite only supplied "
        "anchor IDs. Preserve dates and place names verbatim; never invent page numbers, "
        "coordinates, normalized dates, identities, motives, causal links, or missing "
        "context. Use candidate/ambiguous/none for locations because geometry is verified "
        "outside the model. Empty arrays are correct when the passage does not support an "
        "artifact. IDs must be deterministic within this request and all references must "
        "resolve inside the returned object."
    ),
    "cross_unit_synthesis": (
        "Synthesize only from the supplied lower-level claim objects. Emit platform_"
        "inference claims, list every supporting claim ID in derived_from_claim_ids, "
        "retain the union of source anchors, and state at least one concrete limitation. "
        "Do not restate an author's interpretation as an independent fact and do not add "
        "outside knowledge. Prefer a small number of high-information connections over "
        "generic summaries."
    ),
    "evidence_judge": (
        "Judge relations among the supplied candidates; do not generate new claims. "
        "Only use contradicts when claims address a comparable scope and material evidence "
        "is identified. Different emphasis is not opposition. If no counterevidence is "
        "present, record the claim ID in counterevidence_not_found_claim_ids; absence of "
        "counterevidence never confirms a claim."
    ),
}


def _json_type_matches(value: Any, expected: str) -> bool:
    return {
        "object": isinstance(value, dict),
        "array": isinstance(value, list),
        "string": isinstance(value, str),
        "integer": isinstance(value, int) and not isinstance(value, bool),
        "number": isinstance(value, (int, float)) and not isinstance(value, bool),
        "boolean": isinstance(value, bool),
        "null": value is None,
    }.get(expected, False)


def _validate_json_schema(value: Any, schema: Mapping[str, Any], path: str = "$") -> None:
    """Validate the bounded JSON-Schema subset used by capability contracts.

    This intentionally rejects unsupported schema keywords rather than
    pretending they were enforced. The supported subset covers the strict
    object/array/scalar contracts emitted by this pipeline without adding a
    second schema dependency to the production image.
    """

    supported = {
        "type",
        "properties",
        "required",
        "additionalProperties",
        "items",
        "enum",
        "const",
        "minItems",
        "maxItems",
        "minLength",
        "maxLength",
        "description",
        "title",
        "$schema",
    }
    unsupported = set(schema) - supported
    if unsupported:
        raise ValueError(f"unsupported JSON Schema keywords at {path}")

    expected = schema.get("type")
    expected_types = (
        tuple(expected)
        if isinstance(expected, list) and all(isinstance(item, str) for item in expected)
        else (expected,)
        if isinstance(expected, str)
        else ()
    )
    if not expected_types or not any(
        _json_type_matches(value, candidate) for candidate in expected_types
    ):
        raise ValueError(f"JSON Schema type mismatch at {path}")
    if "const" in schema and value != schema["const"]:
        raise ValueError(f"JSON Schema const mismatch at {path}")
    if "enum" in schema and value not in schema["enum"]:
        raise ValueError(f"JSON Schema enum mismatch at {path}")

    effective_type = next(
        candidate for candidate in expected_types if _json_type_matches(value, candidate)
    )
    if effective_type == "object":
        properties = schema.get("properties", {})
        required = schema.get("required", [])
        if not isinstance(properties, Mapping) or not isinstance(required, Sequence):
            raise ValueError(f"invalid object schema at {path}")
        missing = set(required) - set(value)
        if missing:
            raise ValueError(f"JSON Schema required property missing at {path}")
        unknown = set(value) - set(properties)
        if schema.get("additionalProperties") is False and unknown:
            raise ValueError(f"JSON Schema additional property at {path}")
        for key, item in value.items():
            child_schema = properties.get(key)
            if child_schema is not None:
                if not isinstance(child_schema, Mapping):
                    raise ValueError(f"invalid property schema at {path}.{key}")
                _validate_json_schema(item, child_schema, f"{path}.{key}")
    elif effective_type == "array":
        minimum = schema.get("minItems", 0)
        maximum = schema.get("maxItems")
        if len(value) < minimum or (maximum is not None and len(value) > maximum):
            raise ValueError(f"JSON Schema array length mismatch at {path}")
        item_schema = schema.get("items")
        if item_schema is not None:
            if not isinstance(item_schema, Mapping):
                raise ValueError(f"invalid item schema at {path}")
            for index, item in enumerate(value):
                _validate_json_schema(item, item_schema, f"{path}[{index}]")
    elif effective_type == "string":
        minimum = schema.get("minLength", 0)
        maximum = schema.get("maxLength")
        if len(value) < minimum or (maximum is not None and len(value) > maximum):
            raise ValueError(f"JSON Schema string length mismatch at {path}")


class OpenAICompatibleModelGateway:
    """Strict OpenAI-compatible chat-completions implementation.

    The API key is kept in a private slot and never included in repr, error
    messages, persisted envelopes, or provider response diagnostics. Provider
    bodies are also deliberately excluded from raised errors because they can
    echo private prompts or authorization details.
    """

    provider = "openai_compatible"

    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        structured_extract_model: str,
        cross_unit_synthesis_model: str,
        evidence_judge_model: str,
        output_schemas: Mapping[Capability, Mapping[str, Any]] | None = None,
        timeouts: ModelTimeouts | None = None,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        if not base_url or not api_key:
            raise ValueError("base_url and api_key are required")
        schemas = output_schemas or _DEFAULT_SCHEMAS
        missing = set(_DEFAULT_SCHEMAS) - set(schemas)
        if missing:
            raise ValueError("all three capability output schemas are required")
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._timeouts = timeouts or ModelTimeouts()
        self._routes: dict[Capability, CapabilityRoute] = {
            "structured_extract": CapabilityRoute(
                structured_extract_model,
                deepcopy(dict(schemas["structured_extract"])),
            ),
            "cross_unit_synthesis": CapabilityRoute(
                cross_unit_synthesis_model,
                deepcopy(dict(schemas["cross_unit_synthesis"])),
            ),
            "evidence_judge": CapabilityRoute(
                evidence_judge_model,
                deepcopy(dict(schemas["evidence_judge"])),
            ),
        }
        self._client = httpx.Client(
            base_url=self._base_url + "/",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            timeout=self._timeouts.as_httpx(),
            transport=transport,
            follow_redirects=False,
        )

    def __repr__(self) -> str:
        models = {name: route.model for name, route in self._routes.items()}
        return (
            f"{type(self).__name__}(base_url={self._base_url!r}, "
            f"models={models!r}, timeouts={self._timeouts!r})"
        )

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "OpenAICompatibleModelGateway":
        return self

    def __exit__(self, *_args: object) -> None:
        self.close()

    @staticmethod
    def _request_id(
        capability: Capability,
        request: StructuredExtractRequest
        | CrossUnitSynthesisRequest
        | EvidenceJudgeRequest,
    ) -> str:
        if capability == "structured_extract":
            assert isinstance(request, StructuredExtractRequest)
            return request.unit_id
        if capability == "cross_unit_synthesis":
            assert isinstance(request, CrossUnitSynthesisRequest)
            return request.synthesis_id
        assert isinstance(request, EvidenceJudgeRequest)
        return request.judgment_id

    @staticmethod
    def _private_input(
        capability: Capability,
        request: StructuredExtractRequest
        | CrossUnitSynthesisRequest
        | EvidenceJudgeRequest,
    ) -> JsonObject:
        if capability == "structured_extract":
            assert isinstance(request, StructuredExtractRequest)
            return {
                "unit_id": request.unit_id,
                "source_anchor_ids": request.source_anchor_ids,
                "input_artifact_ids": request.input_artifact_ids,
                "requested_outputs": request.requested_outputs,
                "analysis_focus": request.analysis_focus,
                "source_text_by_anchor_id": request.source_text_by_anchor_id,
            }
        if capability == "cross_unit_synthesis":
            assert isinstance(request, CrossUnitSynthesisRequest)
            return {
                "synthesis_id": request.synthesis_id,
                "input_artifact_ids": request.input_artifact_ids,
                "lower_level_artifacts": request.lower_level_artifacts,
                "required_output_kind": request.required_output_kind,
            }
        assert isinstance(request, EvidenceJudgeRequest)
        return {
            "judgment_id": request.judgment_id,
            "candidate_artifact_ids": request.candidate_artifact_ids,
            "evidence_artifact_ids": request.evidence_artifact_ids,
            "candidate_artifacts": request.candidate_artifacts,
            "evidence_artifacts": request.evidence_artifacts,
        }

    def _envelope(
        self,
        capability: Capability,
        request: StructuredExtractRequest
        | CrossUnitSynthesisRequest
        | EvidenceJudgeRequest,
    ) -> JsonObject:
        route = self._routes[capability]
        private_input = self._private_input(capability, request)
        return {
            "model": route.model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "Return exactly one JSON object matching the supplied strict "
                        "schema. Do not add prose or markdown. "
                        + _CAPABILITY_INSTRUCTIONS[capability]
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "capability": capability,
                            "request_id": self._request_id(capability, request),
                            "input": private_input,
                        },
                        ensure_ascii=False,
                        separators=(",", ":"),
                    ),
                },
            ],
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": f"history_kb_{capability}",
                    "strict": True,
                    "schema": deepcopy(dict(route.output_schema)),
                },
            },
            "temperature": 0,
            "max_tokens": route.max_output_tokens,
        }

    def _post_with_total_deadline(self, envelope: JsonObject) -> httpx.Response:
        executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="history-kb-model")
        future = executor.submit(
            self._client.post,
            "chat/completions",
            json=envelope,
        )
        started = monotonic()
        try:
            response = future.result(timeout=self._timeouts.total)
        except FutureTimeoutError as exc:
            future.cancel()
            raise RetryableWorkError("MODEL_TOTAL_TIMEOUT") from None
        except httpx.TimeoutException:
            raise RetryableWorkError("MODEL_IO_TIMEOUT") from None
        except httpx.TransportError:
            raise RetryableWorkError("MODEL_TRANSPORT_ERROR") from None
        finally:
            executor.shutdown(wait=False, cancel_futures=True)
        if monotonic() - started > self._timeouts.total:
            raise RetryableWorkError("MODEL_TOTAL_TIMEOUT")
        return response

    def _call(
        self,
        capability: Capability,
        request: StructuredExtractRequest
        | CrossUnitSynthesisRequest
        | EvidenceJudgeRequest,
    ) -> GatewayResult:
        route = self._routes[capability]
        response = self._post_with_total_deadline(self._envelope(capability, request))
        if response.status_code == 429:
            raise RetryableWorkError("MODEL_RATE_LIMITED")
        if 500 <= response.status_code <= 599:
            raise RetryableWorkError("MODEL_UPSTREAM_5XX")
        if not 200 <= response.status_code <= 299:
            raise PermanentWorkError("MODEL_REQUEST_REJECTED")

        try:
            body = response.json()
            content = body["choices"][0]["message"]["content"]
        except (ValueError, KeyError, IndexError, TypeError):
            raise PermanentWorkError("MODEL_INVALID_RESPONSE_ENVELOPE") from None
        if not isinstance(content, str):
            raise PermanentWorkError("MODEL_INVALID_RESPONSE_ENVELOPE")
        try:
            output = json.loads(content)
        except (json.JSONDecodeError, TypeError):
            raise PermanentWorkError("MODEL_INVALID_JSON") from None
        if not isinstance(output, dict):
            raise PermanentWorkError("MODEL_OUTPUT_NOT_OBJECT")
        try:
            _validate_json_schema(output, route.output_schema)
        except ValueError:
            raise PermanentWorkError("MODEL_SCHEMA_MISMATCH") from None
        return GatewayResult(
            capability=capability,
            status="succeeded",
            provider=self.provider,
            model=route.model,
            output=output,
            output_digest=_digest_json(output),
        )

    def structured_extract(self, request: StructuredExtractRequest) -> GatewayResult:
        return self._call("structured_extract", request)

    def cross_unit_synthesis(
        self, request: CrossUnitSynthesisRequest
    ) -> GatewayResult:
        return self._call("cross_unit_synthesis", request)

    def evidence_judge(self, request: EvidenceJudgeRequest) -> GatewayResult:
        return self._call("evidence_judge", request)


def build_configured_model_gateway(config: object) -> ModelGateway:
    """Build the explicit runtime route without ever falling back to a model.

    The configuration object is intentionally structural so tests can supply a
    tiny namespace without importing the global application settings. Missing
    credentials fail during worker startup; the system never silently changes
    from a requested remote provider to an offline fixture.
    """

    provider = str(getattr(config, "exploration_model_provider", "none")).strip()
    if provider in {"", "none"}:
        return NoModelGateway()
    if provider == "deterministic":
        return DeterministicModelGateway()
    if provider != "openai_compatible":
        raise ValueError("unsupported exploration model provider")

    required = {
        "base_url": getattr(config, "exploration_model_base_url", None),
        "api_key": getattr(config, "exploration_model_api_key", None),
        "structured_extract_model": getattr(
            config, "exploration_extract_model", None
        ),
        "cross_unit_synthesis_model": getattr(
            config, "exploration_synthesis_model", None
        ),
        "evidence_judge_model": getattr(config, "exploration_judge_model", None),
    }
    if any(not value for value in required.values()):
        raise ValueError(
            "openai_compatible exploration provider requires base URL, API key, "
            "and all three capability model routes"
        )
    connect = float(
        getattr(config, "exploration_model_connect_timeout_seconds", 5)
    )
    total = float(getattr(config, "exploration_model_total_timeout_seconds", 45))
    return OpenAICompatibleModelGateway(
        **required,
        timeouts=ModelTimeouts(
            connect=connect,
            read=min(total, 30.0),
            write=min(total, 10.0),
            pool=min(connect, 5.0),
            total=total,
        ),
    )


__all__ = [
    "Capability",
    "CapabilityRoute",
    "CrossUnitSynthesisRequest",
    "DeterministicModelGateway",
    "EvidenceJudgeRequest",
    "GatewayResult",
    "JsonObject",
    "ModelGateway",
    "ModelTimeouts",
    "NoModelGateway",
    "OpenAICompatibleModelGateway",
    "StructuredExtractRequest",
    "build_configured_model_gateway",
]
