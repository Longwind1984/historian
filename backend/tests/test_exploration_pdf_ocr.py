"""PDF/OCR import contracts preserve page jumps without leaking local paths."""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from app.schemas.exploration import (
    ComposeRequest,
    ImportExplorationRequest,
    SourceFormat,
)
from app.services.exploration_service import ExplorationStore


PDF_SHA256 = "56f98c55c656f5ca829e3d91788581fb932a07066708009ac7cee92bd0fb08da"


def _request() -> ImportExplorationRequest:
    return ImportExplorationRequest(
        source_format=SourceFormat.PDF_OCR,
        pdf_checksum_sha256=PDF_SHA256,
        title="中华人民共和国史 第三卷",
        author="沈志华",
        pdf_pages=[
            {
                "pdf_page_index": 0,
                "printed_page_label": None,
                "ocr_state": "rendered",
                "ocr_confidence": None,
                "content": "",
            },
            {
                "pdf_page_index": 21,
                "printed_page_label": "1",
                "ocr_state": "ocr_unverified",
                "ocr_confidence": 88.65,
                "content": (
                    "PRIVATE-PDF-OCR-MARKER 第一段 OCR 原文。\n\n"
                    "第二段保留同一 PDF 页定位。"
                ),
            },
            {
                "pdf_page_index": 22,
                "printed_page_label": "2",
                "ocr_state": "ocr_reviewed",
                "ocr_confidence": 99.1,
                "content": "第三段已经逐页复核。",
            },
        ],
    )


def test_pdf_ocr_import_preserves_page_locator_and_recovers_from_vault(tmp_path: Path):
    state_dir = tmp_path / "state"
    store = ExplorationStore(state_dir=state_dir)
    try:
        created = store.create(_request())
        exploration_id = created.id
        document = created.document
        assert document is not None
        assert document.source_format is SourceFormat.PDF_OCR
        assert document.pdf_ocr_metadata is not None
        assert document.pdf_ocr_metadata.pdf_checksum_sha256 == PDF_SHA256
        assert document.pdf_ocr_metadata.page_count == 3
        assert document.pdf_ocr_metadata.pages[0].ocr_state.value == "rendered"
        assert document.pdf_ocr_metadata.pages[0].paragraph_anchor_ids == []

        anchors = [
            paragraph
            for section in document.sections
            for paragraph in section.paragraphs
        ]
        assert [anchor.locator.pdf_page_index for anchor in anchors] == [21, 21, 22]
        assert [anchor.page_label for anchor in anchors] == ["1", "1", "2"]
        assert anchors[0].locator.ocr_state.value == "ocr_unverified"
        assert anchors[-1].locator.ocr_state.value == "ocr_reviewed"
        assert anchors[0].locator.ocr_confidence == 88.65

        proposed = store.compose(
            exploration_id,
            ComposeRequest(
                base_revision=created.revision,
                intent="propose_scene",
                message="仅验证来源回跳，不生成新历史事实。",
                anchor_ids=[anchors[0].id],
                scene_title="PDF 页级回跳",
            ),
        ).snapshot
        evidence_locator = proposed.evidence[0].locator
        assert evidence_locator.page_label == "1"
        assert evidence_locator.document_locator.pdf_page_index == 21
        assert evidence_locator.document_locator.ocr_state.value == "ocr_unverified"

        locator_json = anchors[0].locator.model_dump_json()
        assert "PRIVATE-PDF-OCR-MARKER" not in locator_json
        assert "image_path" not in locator_json
        assert "source_path" not in locator_json
    finally:
        store.close()

    reopened = ExplorationStore(state_dir=state_dir)
    try:
        recovered = reopened.get(exploration_id)
        assert recovered.document is not None
        recovered_anchor = recovered.document.sections[0].paragraphs[0]
        assert recovered_anchor.locator.pdf_page_index == 21
        assert recovered_anchor.page_label == "1"

        database_bytes = b"".join(
            path.read_bytes()
            for path in state_dir.glob("explorations.sqlite3*")
            if path.is_file()
        )
        assert b"PRIVATE-PDF-OCR-MARKER" not in database_bytes
        assert str(tmp_path).encode("utf-8") not in database_bytes

        reordered_payload = _request().model_dump(mode="json")
        reordered_payload["pdf_pages"] = list(
            reversed(reordered_payload["pdf_pages"])
        )
        duplicate = reopened.create(
            ImportExplorationRequest.model_validate(reordered_payload)
        )
        assert duplicate.document is not None
        assert duplicate.document.checksum_sha256 == recovered.document.checksum_sha256
        assert [
            paragraph.id
            for section in duplicate.document.sections
            for paragraph in section.paragraphs
        ] == [
            paragraph.id
            for section in recovered.document.sections
            for paragraph in section.paragraphs
        ]
    finally:
        reopened.close()


def test_pdf_ocr_import_endpoint_returns_page_addressable_anchors(client):
    response = client.post(
        "/api/explorations/import",
        json=_request().model_dump(mode="json"),
    )
    assert response.status_code == 201, response.text
    snapshot = response.json()
    try:
        anchor = snapshot["document"]["sections"][0]["paragraphs"][0]
        assert anchor["page_label"] == "1"
        assert anchor["locator"] == {
            "source_format": "pdf_ocr",
            "section_index": 0,
            "paragraph_index": 0,
            "spine_index": None,
            "href": None,
            "pdf_page_index": 21,
            "printed_page_label": "1",
            "ocr_state": "ocr_unverified",
            "ocr_confidence": 88.65,
            "progression_percent": 0.0,
        }
    finally:
        deleted = client.delete(f"/api/explorations/{snapshot['id']}")
        assert deleted.status_code == 204


def test_pdf_ocr_page_contract_rejects_paths_and_inconsistent_payloads():
    with pytest.raises(ValidationError, match="image_path"):
        ImportExplorationRequest.model_validate(
            {
                "source_format": "pdf_ocr",
                "pdf_checksum_sha256": PDF_SHA256,
                "pdf_pages": [
                    {
                        "pdf_page_index": 0,
                        "ocr_state": "ocr_unverified",
                        "ocr_confidence": 90,
                        "content": "一段 OCR 文本。",
                        "image_path": "/Users/example/private/page-1.png",
                    }
                ],
            }
        )

    with pytest.raises(ValidationError, match="unique"):
        ImportExplorationRequest.model_validate(
            {
                "source_format": "pdf_ocr",
                "pdf_checksum_sha256": PDF_SHA256,
                "pdf_pages": [
                    {
                        "pdf_page_index": 1,
                        "ocr_state": "ocr_unverified",
                        "ocr_confidence": 90,
                        "content": "第一页。",
                    },
                    {
                        "pdf_page_index": 1,
                        "ocr_state": "ocr_reviewed",
                        "ocr_confidence": 100,
                        "content": "重复页。",
                    },
                ],
            }
        )

    with pytest.raises(ValidationError, match="uses pdf_pages"):
        ImportExplorationRequest.model_validate(
            {
                "source_format": "pdf_ocr",
                "content": "不能把无页界的文本冒充 PDF/OCR。",
                "pdf_checksum_sha256": PDF_SHA256,
                "pdf_pages": [
                    {
                        "pdf_page_index": 1,
                        "ocr_state": "ocr_reviewed",
                        "ocr_confidence": 100,
                        "content": "有页界的 OCR 文本。",
                    }
                ],
            }
        )

    for field, value in (
        ("pdf_page_index", -1),
        ("ocr_confidence", -0.1),
        ("ocr_confidence", 100.1),
    ):
        page = {
            "pdf_page_index": 1,
            "ocr_state": "ocr_reviewed",
            "ocr_confidence": 100,
            "content": "边界校验文本。",
        }
        page[field] = value
        with pytest.raises(ValidationError, match=field):
            ImportExplorationRequest.model_validate(
                {
                    "source_format": "pdf_ocr",
                    "pdf_checksum_sha256": PDF_SHA256,
                    "pdf_pages": [page],
                }
            )
