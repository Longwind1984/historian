"""Full PDF acceptance runner coverage with a tiny private fixture."""

from __future__ import annotations

from hashlib import sha256
import importlib.util
import json
from pathlib import Path
import sys
from time import perf_counter

import pytest

from app.exploration.model_gateway import NoModelGateway
from app.exploration.worker import ExplorationWorker
from app.services.exploration_service import ExplorationStore


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "run-full-pdf-backend-acceptance.py"


@pytest.fixture()
def full_acceptance_runner():
    spec = importlib.util.spec_from_file_location("full_pdf_acceptance_runner", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _write_page(directory: Path, page: int, text: str, confidence: float | None) -> dict:
    (directory / f"page-{page:04d}.txt").write_text(text, encoding="utf-8")
    tsv_confidence = confidence if confidence is not None else -1
    (directory / f"page-{page:04d}.tsv").write_text(
        f"level\tconf\ttext\n5\t{tsv_confidence}\tfixture\n",
        encoding="utf-8",
    )
    return {
        "page": page,
        "status": "succeeded",
        "characters": len(text),
        "scored_tokens": int(confidence is not None),
        "average_confidence": confidence,
        "low_confidence_tokens": 0,
    }


def _fixture_source(tmp_path: Path, *, legacy: bool) -> tuple[Path, Path]:
    pdf = tmp_path / "private-fixture.pdf"
    pdf.write_bytes(b"synthetic-private-pdf")
    ocr_dir = tmp_path / "ocr"
    ocr_dir.mkdir()
    pages = [
        _write_page(
            ocr_dir,
            1,
            "PRIVATE-FULL-PDF-MARKER 第一页讨论政策变化和作者解释。",
            91.0,
        ),
        _write_page(ocr_dir, 2, "", None),
        _write_page(
            ocr_dir,
            3,
            "第三页继续讨论知识分子、整风与政治动员之间的关系。",
            87.5,
        ),
    ]
    summary = {
        "completed_pages": 3,
        "character_count": sum(page["characters"] for page in pages),
        "average_confidence": 89.25,
        "low_confidence_rate": 0.0,
        "duration_ms": 1234.5,
        "failed_pages": [],
    }
    manifest = {
        "contract_version": "scan_pdf_ocr_manifest.v1",
        "source": {
            "pdf_sha256": sha256(pdf.read_bytes()).hexdigest(),
            "page_count": 3,
            "file_size_bytes": pdf.stat().st_size,
        },
        "pages": pages,
        "failures": 0 if legacy else {},
    }
    if legacy:
        manifest["ocr"] = summary
    else:
        manifest.update(
            {
                "status": "complete",
                "pipeline": {"engine": "tesseract"},
                "summary": {
                    key: value
                    for key, value in summary.items()
                    if key not in {"duration_ms", "failed_pages"}
                },
                "run": {
                    "duration_ms": summary["duration_ms"],
                    "failed_pages": [],
                },
            }
        )
    (ocr_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False), encoding="utf-8"
    )
    return pdf, ocr_dir


@pytest.mark.parametrize("legacy", [True, False])
def test_manifest_contracts_build_blank_pages_without_fake_text(
    tmp_path: Path, full_acceptance_runner, legacy: bool
):
    _pdf, ocr_dir = _fixture_source(tmp_path, legacy=legacy)
    manifest = full_acceptance_runner._load_manifest(
        ocr_dir / "manifest.json", expected_page_count=3
    )
    pairs = full_acceptance_runner._validate_page_pairs(
        ocr_dir, expected_page_count=3
    )
    pages, counts = full_acceptance_runner._build_pdf_pages(
        manifest=manifest,
        page_files=pairs,
        printed_page_offset=-1,
    )

    assert counts == {
        "source_pages": 3,
        "readable_pages": 2,
        "rendered_blank_pages": 1,
    }
    assert pages[0].printed_page_label is None
    assert pages[1].printed_page_label == "1"
    assert pages[1].ocr_state.value == "rendered"
    assert pages[1].content == ""
    assert pages[1].ocr_confidence is None
    assert pages[2].ocr_state.value == "ocr_unverified"


def test_full_runner_uses_two_worker_boundaries_and_remains_blocked_without_model(
    tmp_path: Path, monkeypatch, full_acceptance_runner
):
    pdf, ocr_dir = _fixture_source(tmp_path, legacy=False)
    worker_calls: list[str] = []

    def fake_worker(*, repo_root: Path, state_dir: Path, timeout_seconds: float):
        del repo_root, timeout_seconds
        started = perf_counter()
        gateway = NoModelGateway()
        store = ExplorationStore(state_dir=state_dir, model_gateway=gateway)
        try:
            result = ExplorationWorker(store.control_plane, gateway).process_next()
            assert result is not None
            worker_calls.append(result.state)
            return full_acceptance_runner.WorkerRunEvidence(
                returncode=0,
                stdout=f"fake-cross-process state={result.state}",
                stderr="",
                duration_ms=(perf_counter() - started) * 1000,
            )
        finally:
            store.close()

    monkeypatch.setattr(full_acceptance_runner, "_run_worker_once", fake_worker)
    result = full_acceptance_runner._run_acceptance(
        pdf=pdf,
        ocr_dir=ocr_dir,
        state_dir=tmp_path / "state",
        printed_page_offset=-1,
        worker_timeout_seconds=5,
        expected_page_count=3,
    )
    result["content_gold"] = full_acceptance_runner._load_content_gold(None)
    html = full_acceptance_runner._render_report(result)

    assert worker_calls == ["waiting_review", "completed"]
    assert result["overall"] == "blocked"
    assert result["source"]["source_pages"] == 3
    assert result["source"]["readable_pages"] == 2
    assert result["execution"]["claim_count"] == 0
    assert result["execution"]["event_count"] == 0
    checks = {item["code"]: item for item in result["checks"]}
    assert checks["cross_process_worker"]["status"] == "pass"
    assert checks["pdf_page_locator_coverage"]["status"] == "pass"
    assert checks["live_content_quality"]["status"] == "not_run"
    assert "验收未完成：来源与控制面已通过，真实模型未运行" in html
    assert "PRIVATE-FULL-PDF-MARKER" not in html
    assert str(pdf) not in html


def test_external_content_gold_is_diagnostic_not_gateway_pass(
    tmp_path: Path, full_acceptance_runner
):
    path = tmp_path / "gold.json"
    path.write_text(
        json.dumps(
            {
                "coverage": {"sampled_pages": 20, "total_pages": 845},
                "chapter_results": [{"status": "reviewed"}] * 3,
                "cross_chapter_insights": [{"status": "candidate"}] * 2,
                "risks": ["抽样覆盖有限", "不能替代生产 model gateway"],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    summary = full_acceptance_runner._load_content_gold(path)
    assert summary == {
        "status": "run",
        "execution_mode": "codex_agent_external_harness",
        "coverage": {"sampled_pages": 20, "total_pages": 845},
        "chapter_result_count": 3,
        "cross_chapter_insight_count": 2,
        "risks": ["抽样覆盖有限", "不能替代生产 model gateway"],
        "production_gateway_credited": False,
    }


def test_external_content_gold_accepts_real_harness_field_names(
    tmp_path: Path, full_acceptance_runner
):
    path = tmp_path / "real-gold-shape.json"
    path.write_text(
        json.dumps(
            {
                "execution_mode": "codex_agent_external_harness",
                "sample_pages": 20,
                "total_pages": 845,
                "coverage": {"sampled_page_ratio": 20 / 845},
                "chapters": [{"chapter": index} for index in range(10)],
                "cross_chapter_insights": [{"status": "candidate"}] * 5,
                "ocr_and_evidence_risks": [
                    "抽样覆盖有限",
                    "正式引用必须回看 PDF 图像",
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    summary = full_acceptance_runner._load_content_gold(path)

    assert summary["coverage"] == {"sampled_pages": 20, "total_pages": 845}
    assert summary["chapter_result_count"] == 10
    assert summary["cross_chapter_insight_count"] == 5
    assert summary["risks"] == [
        "抽样覆盖有限",
        "正式引用必须回看 PDF 图像",
    ]
    assert summary["production_gateway_credited"] is False


def test_worker_failure_returns_failed_evidence_and_cleans_private_vault(
    tmp_path: Path, monkeypatch, full_acceptance_runner
):
    pdf, ocr_dir = _fixture_source(tmp_path, legacy=False)
    state_dir = tmp_path / "failed-state"

    def failed_worker(*, repo_root: Path, state_dir: Path, timeout_seconds: float):
        del repo_root, state_dir, timeout_seconds
        return full_acceptance_runner.WorkerRunEvidence(
            returncode=1,
            stdout="",
            stderr="synthetic source-free failure",
            duration_ms=1.0,
        )

    monkeypatch.setattr(full_acceptance_runner, "_run_worker_once", failed_worker)
    result = full_acceptance_runner._run_acceptance(
        pdf=pdf,
        ocr_dir=ocr_dir,
        state_dir=state_dir,
        printed_page_offset=0,
        worker_timeout_seconds=5,
        expected_page_count=3,
    )

    assert result["overall"] == "failed"
    checks = {item["code"]: item for item in result["checks"]}
    assert checks["cross_process_worker"]["status"] == "fail"
    assert checks["human_review_gate"]["status"] == "fail"
    assert not any((state_dir / "vault").iterdir())
