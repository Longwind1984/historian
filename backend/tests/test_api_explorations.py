"""Private book exploration API contracts."""

from __future__ import annotations

import base64
import io
import os
from pathlib import Path
import zipfile

import pytest

from app.schemas.exploration import (
    EpubImportRequest,
    ImportExplorationRequest,
    SourceFormat,
    PrivateDocument,
)
from app.exploration.planning import compile_analysis_plan
from app.exploration.profiling import build_book_profile
from app.exploration.signals import derive_document_signals
from app.services.exploration_service import (
    ExplorationNotFound,
    ExplorationStore,
    InvalidPrivateText,
    MAX_EPUB_BYTES,
    _validate_epub_archive,
    exploration_store,
)


@pytest.fixture(autouse=True)
def _clear_private_explorations():
    exploration_store.clear()
    yield
    exploration_store.clear()


def _import_markdown(client):
    response = client.post(
        "/api/explorations/import",
        json={
            "source_format": "markdown",
            "content": (
                "# 私人研究文本\n\n"
                "这是一段用户提供的材料，不含可靠页码。\n\n"
                "## 第一部分\n\n"
                "第二段材料用于验证稳定锚点。\n\n"
                "第三段仍属于第一部分。"
            ),
            "author": "用户填写的作者",
            "version_label": "用户填写的版本说明",
            "brief": {
                "question": "作者如何组织这部分材料？",
                "status": "confirmed",
            },
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def _minimal_epub_bytes(
    *, chapter_prefix: str = "", rootfile_path: str = "OPS/content.opf"
) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr(
            "mimetype",
            "application/epub+zip",
            compress_type=zipfile.ZIP_STORED,
        )
        archive.writestr(
            "META-INF/container.xml",
            f"""<?xml version="1.0"?>
            <container xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
              <rootfiles>
                <rootfile full-path="{rootfile_path}"
                  media-type="application/oebps-package+xml"/>
              </rootfiles>
            </container>""",
            compress_type=zipfile.ZIP_DEFLATED,
        )
        archive.writestr(
            "OPS/content.opf",
            """<?xml version="1.0" encoding="utf-8"?>
            <package xmlns="http://www.idpf.org/2007/opf" version="3.0"
              unique-identifier="book-id">
              <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
                <dc:identifier id="book-id">fixture-book</dc:identifier>
                <dc:title>本地 EPUB Fixture</dc:title>
                <dc:creator>测试作者</dc:creator>
                <dc:language>zh</dc:language>
                <dc:publisher>测试出版社</dc:publisher>
                <dc:date>2026</dc:date>
              </metadata>
              <manifest>
                <item id="c1" href="chapter-1.xhtml"
                  media-type="application/xhtml+xml"/>
                <item id="c2" href="chapter-2.xhtml"
                  media-type="application/xhtml+xml"/>
              </manifest>
              <spine>
                <itemref idref="c1"/>
                <itemref idref="c2"/>
              </spine>
            </package>""",
            compress_type=zipfile.ZIP_DEFLATED,
        )
        archive.writestr(
            "OPS/chapter-1.xhtml",
            chapter_prefix
            + """<html xmlns="http://www.w3.org/1999/xhtml">
              <head><title>第一章</title></head>
              <body>
                <h1>第一章 起点</h1>
                <p>第一段，只是测试材料。</p>
                <p>第二段，没有打印页码。</p>
                <script>window.shouldNeverBeRead = true;</script>
              </body>
            </html>""",
            compress_type=zipfile.ZIP_DEFLATED,
        )
        archive.writestr(
            "OPS/chapter-2.xhtml",
            """<html xmlns="http://www.w3.org/1999/xhtml">
              <head><title>第二章</title></head>
              <body><h2>第二章 后续</h2><p>第三段。</p></body>
            </html>""",
            compress_type=zipfile.ZIP_DEFLATED,
        )
    return buffer.getvalue()


def test_import_markdown_builds_private_paragraph_anchors_without_pages(client):
    snapshot = _import_markdown(client)

    assert snapshot["revision"] == 1
    assert snapshot["retention"] == "private_source_vault"
    assert snapshot["entry_mode"] == "book"
    assert snapshot["session_boundary"] == {
        "storage": "sqlite_control_plane_private_vault",
        "private_source_in_database": False,
        "restart_clears_session": False,
        "explicit_delete_required": True,
    }
    assert snapshot["document"]["ephemeral"] is False
    assert snapshot["document"]["title"] == "私人研究文本"
    assert snapshot["document"]["author"] == "用户填写的作者"
    assert snapshot["document"]["version_label"] == "用户填写的版本说明"
    assert snapshot["document"]["source_format"] == "markdown"
    assert snapshot["document"]["section_count"] == 2
    assert snapshot["document"]["paragraph_count"] == 3
    assert "raw_content" not in snapshot["document"]

    paragraphs = [
        paragraph
        for section in snapshot["document"]["sections"]
        for paragraph in section["paragraphs"]
    ]
    assert snapshot["active_anchor_id"] == paragraphs[0]["id"]
    assert all(paragraph["anchor_kind"] == "paragraph" for paragraph in paragraphs)
    assert all(paragraph["page_label"] is None for paragraph in paragraphs)
    assert all(paragraph["id"].startswith("p_") for paragraph in paragraphs)
    assert paragraphs[0]["locator"]["progression_percent"] == 0
    assert paragraphs[-1]["locator"]["progression_percent"] == 100


def test_plain_text_chapter_detection_does_not_invent_book_metadata(client):
    response = client.post(
        "/api/explorations/import",
        json={
            "source_format": "text",
            "content": "导言材料。\n\n第1章 起点\n\n章节正文。\n\n第2节 补充\n\n补充正文。",
        },
    )
    assert response.status_code == 201, response.text
    document = response.json()["document"]

    assert document["title"] == "未命名私人文本"
    assert document["author"] is None
    assert document["version_label"] is None
    assert [section["title"] for section in document["sections"]] == [
        "正文",
        "第1章 起点",
        "第2节 补充",
    ]
    assert all(
        paragraph["page_label"] is None
        for section in document["sections"]
        for paragraph in section["paragraphs"]
    )


def test_oversized_paragraph_is_losslessly_bounded_before_model_batching(client):
    source = "甲" * 30_001
    response = client.post(
        "/api/explorations/import",
        json={"source_format": "text", "content": source},
    )
    assert response.status_code == 201, response.text
    document = PrivateDocument.model_validate(response.json()["document"])
    paragraphs = document.sections[0].paragraphs
    assert len(paragraphs) == 3
    assert "".join(item.text for item in paragraphs) == source
    assert max(len(item.text) for item in paragraphs) <= 12_000

    signals = derive_document_signals(document)
    text_by_anchor = {item.id: item.text for item in paragraphs}
    assert all(
        sum(len(text_by_anchor[anchor_id]) for anchor_id in batch.anchor_ids)
        <= 36_000
        for batch in signals.planning_scope.anchor_batches
    )


def test_question_composer_records_input_without_synthesising_an_answer(client):
    imported = _import_markdown(client)
    response = client.post(
        f"/api/explorations/{imported['id']}/compose",
        json={
            "base_revision": imported["revision"],
            "intent": "question",
            "message": "这段材料与下一节的关系是什么？",
            "anchor_ids": [imported["active_anchor_id"]],
        },
    )
    assert response.status_code == 200, response.text
    body = response.json()

    assert body["outcome"] == "recorded_no_llm"
    assert body["snapshot"]["revision"] == 2
    assert body["snapshot"]["scenes"] == []
    assert body["snapshot"]["claims"] == []
    assert body["snapshot"]["evidence"] == []
    assert body["snapshot"]["composer_entries"][0]["processing_status"] == (
        "recorded_no_llm"
    )


def test_scene_proposal_is_model_inference_pending_review_and_has_no_map_guess(client):
    imported = _import_markdown(client)
    anchor_id = imported["active_anchor_id"]
    response = client.post(
        f"/api/explorations/{imported['id']}/compose",
        json={
            "base_revision": imported["revision"],
            "intent": "propose_scene",
            "message": "把这段材料作为一个待复核的结构节点。",
            "scene_title": "原型 Scene",
            "temporal_label": "用户填写：某一阶段",
            "anchor_ids": [anchor_id],
        },
    )
    assert response.status_code == 200, response.text
    body = response.json()
    snapshot = body["snapshot"]

    assert body["outcome"] == "scene_proposed"
    assert snapshot["revision"] == 2
    assert len(snapshot["scenes"]) == 1
    assert len(snapshot["claims"]) == 1
    assert len(snapshot["evidence"]) == 1

    claim = snapshot["claims"][0]
    assert claim["evidence_level"] == "model_inference"
    assert claim["review_status"] == "pending_review"
    assert claim["provenance"] == "composer_structure_proposal"

    evidence = snapshot["evidence"][0]
    assert evidence["evidence_level"] == "single_source"
    assert evidence["relation"] == "source_context"
    assert evidence["review_status"] == "pending_review"
    assert evidence["locator"]["paragraph_id"] == anchor_id
    assert evidence["locator"]["page_label"] is None
    assert evidence["quote"] is None

    scene = snapshot["scenes"][0]
    assert scene["evidence_level"] == "model_inference"
    assert scene["review_status"] == "pending_review"
    assert scene["temporal_precision"] == "user_supplied"
    assert scene["map_state"] == "no_location"
    assert scene["map_focus"] is None


def test_scene_without_anchor_is_an_explicit_evidence_gap(client):
    imported = _import_markdown(client)
    response = client.post(
        f"/api/explorations/{imported['id']}/compose",
        json={
            "base_revision": imported["revision"],
            "intent": "propose_scene",
            "message": "没有段落依据的待核结构。",
        },
    )
    assert response.status_code == 200, response.text
    snapshot = response.json()["snapshot"]

    assert snapshot["scenes"][0]["evidence_level"] == "evidence_gap"
    assert snapshot["scenes"][0]["evidence_ids"] == []
    assert snapshot["claims"][0]["evidence_level"] == "model_inference"


def test_mutations_use_revision_and_review_never_promotes_inference_to_fact(client):
    imported = _import_markdown(client)
    proposed = client.post(
        f"/api/explorations/{imported['id']}/compose",
        json={
            "base_revision": 1,
            "intent": "propose_scene",
            "message": "待复核结构。",
            "anchor_ids": [imported["active_anchor_id"]],
        },
    ).json()["snapshot"]
    scene_id = proposed["scenes"][0]["id"]

    reviewed = client.post(
        f"/api/explorations/{imported['id']}/mutations",
        json={
            "type": "review_scene",
            "base_revision": proposed["revision"],
            "scene_id": scene_id,
            "decision": "accepted",
        },
    )
    assert reviewed.status_code == 200, reviewed.text
    reviewed_snapshot = reviewed.json()
    assert reviewed_snapshot["scenes"][0]["review_status"] == "accepted"
    assert reviewed_snapshot["scenes"][0]["evidence_level"] == "model_inference"
    assert reviewed_snapshot["claims"][0]["evidence_level"] == "model_inference"

    stale = client.post(
        f"/api/explorations/{imported['id']}/mutations",
        json={
            "type": "set_active_scene",
            "base_revision": proposed["revision"],
            "scene_id": scene_id,
        },
    )
    assert stale.status_code == 409
    assert stale.json()["detail"] == {
        "code": "revision_conflict",
        "expected": proposed["revision"],
        "current": reviewed_snapshot["revision"],
    }


def test_unknown_anchor_is_rejected_without_mutating_revision(client):
    imported = _import_markdown(client)
    response = client.post(
        f"/api/explorations/{imported['id']}/compose",
        json={
            "base_revision": 1,
            "intent": "note",
            "message": "这条锚点不存在。",
            "anchor_ids": ["p_missing"],
        },
    )
    assert response.status_code == 422

    current = client.get(f"/api/explorations/{imported['id']}")
    assert current.status_code == 200
    assert current.json()["revision"] == 1
    assert current.json()["composer_entries"] == []


def test_delete_clears_private_session(client):
    imported = _import_markdown(client)
    response = client.delete(f"/api/explorations/{imported['id']}")
    assert response.status_code == 204
    assert client.get(f"/api/explorations/{imported['id']}").status_code == 404


def test_cache_eviction_does_not_delete_a_durable_exploration():
    store = ExplorationStore(max_sessions=1, ttl_seconds=60)
    request = ImportExplorationRequest(
        source_format=SourceFormat.TEXT,
        content="第一份私有文本。",
    )
    first = store.create(request)
    second = store.create(
        ImportExplorationRequest(
            source_format=SourceFormat.TEXT,
            content="第二份私有文本。",
        )
    )

    assert store.get(first.id).id == first.id
    assert store.get(second.id).id == second.id
    store.close()


def test_cache_character_budget_does_not_delete_durable_sources():
    store = ExplorationStore(
        max_sessions=4,
        ttl_seconds=60,
        max_total_source_chars=18,
    )
    first = store.create(
        ImportExplorationRequest(
            source_format=SourceFormat.TEXT,
            content="第一份材料一二三四五",
        )
    )
    second = store.create(
        ImportExplorationRequest(
            source_format=SourceFormat.TEXT,
            content="第二份材料一二三四五",
        )
    )

    assert store.get(first.id).id == first.id
    assert store.get(second.id).id == second.id
    store.close()


def test_prompt_entry_builds_scope_contract_and_research_question_without_guesses(
    client,
):
    response = client.post(
        "/api/explorations/from-prompt",
        json={"prompt": "我想研究明朝初年的靖难之役。"},
    )
    assert response.status_code == 201, response.text
    snapshot = response.json()

    assert snapshot["entry_mode"] == "prompt"
    assert snapshot["document"] is None
    assert snapshot["brief"] == {
        "question": "我想研究明朝初年的靖难之役。",
        "time_range": None,
        "geography": [],
        "threads": [],
        "status": "draft",
    }
    contract = snapshot["scope_contract"]
    assert contract["original_question"] == "我想研究明朝初年的靖难之役。"
    assert contract["fields_needing_confirmation"] == [
        "time_range",
        "geography",
        "narrative_threads",
    ]
    assert len(contract["starter_questions"]) == 3
    assert contract["processing_status"] == "rule_scaffold"

    assert len(snapshot["scenes"]) == 1
    assert snapshot["scenes"][0]["title"] == "研究问题"
    assert snapshot["scenes"][0]["temporal_label"] is None
    assert snapshot["scenes"][0]["map_state"] == "no_location"
    assert snapshot["scenes"][0]["map_focus"] is None
    assert snapshot["scenes"][0]["evidence_level"] == "evidence_gap"
    assert snapshot["claims"][0]["claim_kind"] == "research_question"
    assert snapshot["claims"][0]["provenance"] == "prompt_scope_scaffold"
    assert snapshot["claims"][0]["evidence_level"] == "evidence_gap"
    assert snapshot["composer_entries"][0]["processing_status"] == "needs_model"


def test_prompt_entry_preserves_only_explicit_user_scope(client):
    response = client.post(
        "/api/explorations/from-prompt",
        json={
            "prompt": "梳理某一阶段的制度变化。",
            "user_supplied_time_range": "用户填写：1402—1424",
            "user_supplied_geography": ["南京", "北京"],
            "user_supplied_threads": ["制度变化"],
        },
    )
    assert response.status_code == 201, response.text
    snapshot = response.json()

    assert snapshot["brief"]["time_range"] == "用户填写：1402—1424"
    assert snapshot["brief"]["geography"] == ["南京", "北京"]
    assert snapshot["scenes"][0]["temporal_label"] == "用户填写：1402—1424"
    assert snapshot["scenes"][0]["temporal_precision"] == "user_supplied"
    assert snapshot["scenes"][0]["map_focus"] is None
    assert snapshot["scope_contract"]["fields_needing_confirmation"] == []


def test_prompt_scope_can_be_refined_with_explicit_user_fields(client):
    imported = client.post(
        "/api/explorations/from-prompt",
        json={"prompt": "梳理一个尚未框定范围的问题。"},
    ).json()
    response = client.post(
        f"/api/explorations/{imported['id']}/mutations",
        json={
            "type": "update_scope_contract",
            "base_revision": imported["revision"],
            "user_supplied_time_range": "用户确认：1942—1945",
            "user_supplied_geography": ["延安"],
            "user_supplied_threads": ["组织变化", "思想脉络"],
        },
    )
    assert response.status_code == 200, response.text
    snapshot = response.json()

    assert snapshot["revision"] == 2
    assert snapshot["scope_contract"]["fields_needing_confirmation"] == []
    assert snapshot["brief"]["time_range"] == "用户确认：1942—1945"
    assert snapshot["brief"]["geography"] == ["延安"]
    assert snapshot["brief"]["threads"] == ["组织变化", "思想脉络"]
    assert snapshot["scenes"][0]["temporal_label"] == "用户确认：1942—1945"
    assert snapshot["scenes"][0]["temporal_precision"] == "user_supplied"
    assert snapshot["scenes"][0]["map_focus"] is None


def test_epub_import_parses_opf_spine_anchors_and_progression(client):
    response = client.post(
        "/api/explorations/import-epub",
        json={
            "content_base64": base64.b64encode(_minimal_epub_bytes()).decode(
                "ascii"
            ),
            "version_label": "用户填写的 EPUB 版本",
        },
    )
    assert response.status_code == 201, response.text
    snapshot = response.json()
    document = snapshot["document"]

    assert snapshot["entry_mode"] == "book"
    assert document["source_format"] == "epub"
    assert document["title"] == "本地 EPUB Fixture"
    assert document["author"] == "测试作者"
    assert document["version_label"] == "用户填写的 EPUB 版本"
    assert document["epub_metadata"] == {
        "opf_path": "OPS/content.opf",
        "language": "zh",
        "identifier": "fixture-book",
        "publisher": "测试出版社",
        "publication_date": "2026",
        "metadata_provenance": "epub_opf",
    }
    assert document["section_count"] == 2
    assert document["paragraph_count"] == 3
    assert [section["title"] for section in document["sections"]] == [
        "第一章 起点",
        "第二章 后续",
    ]
    paragraphs = [
        paragraph
        for section in document["sections"]
        for paragraph in section["paragraphs"]
    ]
    assert [paragraph["locator"]["spine_index"] for paragraph in paragraphs] == [
        0,
        0,
        1,
    ]
    assert [paragraph["locator"]["progression_percent"] for paragraph in paragraphs] == [
        0,
        50,
        100,
    ]
    assert all(paragraph["page_label"] is None for paragraph in paragraphs)
    assert all("window.shouldNeverBeRead" not in p["text"] for p in paragraphs)
    assert "content_base64" not in document
    assert snapshot["reading_progress"]["anchor_id"] == paragraphs[0]["id"]


def test_epub_reading_progress_and_manual_weread_bridge_keep_revision_contract(client):
    imported = client.post(
        "/api/explorations/import-epub",
        json={
            "content_base64": base64.b64encode(_minimal_epub_bytes()).decode(
                "ascii"
            )
        },
    ).json()
    paragraphs = [
        paragraph
        for section in imported["document"]["sections"]
        for paragraph in section["paragraphs"]
    ]
    target = paragraphs[-1]

    progressed = client.post(
        f"/api/explorations/{imported['id']}/mutations",
        json={
            "type": "update_reading_progress",
            "base_revision": imported["revision"],
            "anchor_id": target["id"],
        },
    )
    assert progressed.status_code == 200, progressed.text
    snapshot = progressed.json()
    assert snapshot["active_anchor_id"] == target["id"]
    assert snapshot["reading_progress"]["progression_percent"] == 100
    assert snapshot["reading_progress"]["locator"] == target["locator"]

    synced = client.post(
        f"/api/explorations/{imported['id']}/mutations",
        json={
            "type": "sync_external_reading_progress",
            "base_revision": snapshot["revision"],
            "provider": "weread",
            "url": "https://weread.qq.com/web/reader/example",
            "external_locator": "用户填写：第七章 42%",
            "user_provided_excerpt": "这是用户主动粘贴的短摘录。",
        },
    )
    assert synced.status_code == 200, synced.text
    bridge = synced.json()["external_reading_bridge"]
    assert bridge["provider"] == "weread"
    assert bridge["external_locator"] == "用户填写：第七章 42%"
    assert bridge["user_provided_excerpt"] == "这是用户主动粘贴的短摘录。"
    assert bridge["sync_mode"] == "manual_sync"
    assert bridge["access_boundary"] == "cross_origin_no_dom_access"
    assert bridge["dom_access"] is False

    stale = client.post(
        f"/api/explorations/{imported['id']}/mutations",
        json={
            "type": "update_reading_progress",
            "base_revision": snapshot["revision"],
            "anchor_id": target["id"],
        },
    )
    assert stale.status_code == 409


def test_deep_analysis_only_queues_an_evidence_bounded_request(client):
    imported = _import_markdown(client)
    response = client.post(
        f"/api/explorations/{imported['id']}/compose",
        json={
            "base_revision": imported["revision"],
            "intent": "request_deep_analysis",
            "message": "分析这段材料中的因果链，但不要替作者补结论。",
            "anchor_ids": [imported["active_anchor_id"]],
            "requested_views": [
                "chronology",
                "causal_threads",
                "person_interactions",
                "map_candidates",
            ],
        },
    )
    assert response.status_code == 200, response.text
    body = response.json()
    snapshot = body["snapshot"]

    assert body["outcome"] == "analysis_queued"
    assert snapshot["scenes"] == []
    assert snapshot["claims"] == []
    assert snapshot["evidence"] == []
    assert len(snapshot["analysis_queue"]) == 1
    queued = snapshot["analysis_queue"][0]
    assert queued["evidence_boundary"] == "selected_book_anchors"
    assert queued["processing_status"] == "needs_model"
    assert queued["status"] == "queued"
    assert queued["candidate_output"] is None


def test_epub_rejects_doctype_before_parsing_spine(client):
    response = client.post(
        "/api/explorations/import-epub",
        json={
            "content_base64": base64.b64encode(
                _minimal_epub_bytes(chapter_prefix="<!DOCTYPE html>")
            ).decode("ascii")
        },
    )
    assert response.status_code == 422
    assert "DOCTYPE" in response.json()["detail"]


def test_epub_rejects_parent_traversal_in_container(client):
    response = client.post(
        "/api/explorations/import-epub",
        json={
            "content_base64": base64.b64encode(
                _minimal_epub_bytes(rootfile_path="../content.opf")
            ).decode("ascii")
        },
    )
    assert response.status_code == 422
    assert "Unsafe EPUB archive path" in response.json()["detail"]


def test_epub_request_schema_matches_full_16_mib_base64_envelope():
    expected_base64_chars = 4 * ((MAX_EPUB_BYTES + 2) // 3)

    assert expected_base64_chars == 22_369_624
    assert (
        EpubImportRequest.model_json_schema()["properties"]["content_base64"][
            "maxLength"
        ]
        == expected_base64_chars
    )


def test_epub_over_16_mib_is_rejected_before_zip_unpacking(monkeypatch):
    class OversizedEpubBytes:
        def __len__(self):
            return MAX_EPUB_BYTES + 1

    def fail_if_zip_is_opened(*_args, **_kwargs):
        pytest.fail("oversized EPUB reached ZIP unpacking")

    monkeypatch.setattr(
        "app.services.exploration_service.zipfile.ZipFile",
        fail_if_zip_is_opened,
    )

    with pytest.raises(
        InvalidPrivateText,
        match="EPUB exceeds the 16 MiB compressed-size limit",
    ):
        _validate_epub_archive(OversizedEpubBytes())


def test_epub_api_checks_compressed_limit_before_zip_unpacking(
    client, monkeypatch
):
    payload = b"not-a-zip"

    monkeypatch.setattr(
        "app.services.exploration_service.MAX_EPUB_BYTES",
        len(payload) - 1,
    )

    def fail_if_zip_is_opened(*_args, **_kwargs):
        pytest.fail("oversized EPUB reached ZIP unpacking")

    monkeypatch.setattr(
        "app.services.exploration_service.zipfile.ZipFile",
        fail_if_zip_is_opened,
    )
    response = client.post(
        "/api/explorations/import-epub",
        json={
            "content_base64": base64.b64encode(payload).decode("ascii"),
        },
    )

    assert response.status_code == 422
    assert (
        response.json()["detail"]
        == "EPUB exceeds the 16 MiB compressed-size limit"
    )


def test_real_private_epub_parses_when_opted_in():
    configured_path = os.environ.get("HISTORY_KB_TEST_EPUB")
    if not configured_path:
        pytest.skip("Set HISTORY_KB_TEST_EPUB to opt into the local private EPUB test")
    epub_path = Path(configured_path)
    if not epub_path.is_file():
        pytest.skip("HISTORY_KB_TEST_EPUB does not point to a local file")

    store = ExplorationStore(max_sessions=1, ttl_seconds=60)
    try:
        snapshot = store.create_epub(
            EpubImportRequest(
                content_base64=base64.b64encode(epub_path.read_bytes()).decode("ascii")
            )
        )
        document = snapshot.document
        assert document is not None
        assert document.source_format == SourceFormat.EPUB
        assert document.section_count > 0
        assert document.paragraph_count > 0
        assert document.char_count <= 1_500_000
        assert all(
            paragraph.page_label is None
            for section in document.sections
            for paragraph in section.paragraphs
        )
        assert all(
            paragraph.locator.spine_index is not None
            and paragraph.locator.href is not None
            for section in document.sections
            for paragraph in section.paragraphs
        )

        signals = derive_document_signals(document)
        anchors = {
            paragraph.id: paragraph
            for section in document.sections
            for paragraph in section.paragraphs
        }
        assert len(signals.anchor_ids) == document.paragraph_count
        assert all(
            len(batch.anchor_ids) <= 24
            for batch in signals.planning_scope.anchor_batches
        )
        assert all(
            sum(len(anchors[anchor_id].text) for anchor_id in batch.anchor_ids)
            <= 36_000
            for batch in signals.planning_scope.anchor_batches
        )

        profile = build_book_profile(
            source_checksum=document.checksum_sha256,
            metadata=signals.metadata,
            structure=signals.structure,
            section_signals=signals.sections,
        )
        plan = compile_analysis_plan(
            profile,
            planning_scope=signals.planning_scope,
        )
        work_item_ids = {item.id for item in plan.work_items}
        assert work_item_ids
        assert all(
            dependency in work_item_ids
            for item in plan.work_items
            for dependency in item.depends_on
        )
    finally:
        store.close()
