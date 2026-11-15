#!/usr/bin/env python3
"""Run the full private PDF/OCR acceptance lane and render a source-free report.

This runner intentionally forces ``EXPLORATION_MODEL_PROVIDER=none``.  It can
prove full-source ingestion, durable recovery and two real worker process
boundaries, but it must never describe that control-plane evidence as content
analysis.
"""

from __future__ import annotations

import argparse
from collections import Counter
import csv
from dataclasses import asdict, dataclass
from datetime import datetime
from hashlib import sha256
from html import escape
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from time import perf_counter
from typing import Any, Literal


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "backend"))

from app.exploration.control_plane import AnalysisReviewRequest  # noqa: E402
from app.exploration.model_gateway import NoModelGateway  # noqa: E402
from app.schemas.exploration import (  # noqa: E402
    ExplorationBrief,
    ImportExplorationRequest,
    OcrState,
    PdfOcrPageInput,
    SourceFormat,
)
from app.services.exploration_service import ExplorationStore  # noqa: E402


CONTRACT_VERSION = "full_pdf_backend_acceptance.v1"
OCR_CONTRACT_VERSION = "scan_pdf_ocr_manifest.v1"
EXPECTED_PAGE_COUNT = 845
PAGE_FILE = re.compile(r"^page-(\d{4,})\.(txt|tsv)$")
CheckStatus = Literal["pass", "fail", "not_run"]


@dataclass(frozen=True)
class AcceptanceCheck:
    code: str
    status: CheckStatus
    detail: str


@dataclass(frozen=True)
class WorkerRunEvidence:
    returncode: int
    stdout: str
    stderr: str
    duration_ms: float


@dataclass(frozen=True)
class OcrManifestEvidence:
    pdf_sha256: str
    page_count: int
    completed_pages: int
    failed_pages: tuple[int, ...]
    failures_count: int
    ocr_duration_ms: float | None
    average_confidence: float | None
    low_confidence_rate: float | None
    character_count: int
    page_records: tuple[dict[str, Any], ...]


def _args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run full 845-page PDF/OCR backend acceptance"
    )
    parser.add_argument("--pdf", type=Path, required=True)
    parser.add_argument("--ocr-dir", type=Path, required=True)
    parser.add_argument("--state-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--content-gold-json",
        type=Path,
        default=None,
        help="optional source-free external Codex-agent harness summary",
    )
    parser.add_argument(
        "--printed-page-offset",
        type=int,
        default=0,
        help=(
            "printed label = one-based physical PDF page + this offset; "
            "labels <= 0 are omitted"
        ),
    )
    parser.add_argument("--worker-timeout-seconds", type=float, default=1800)
    return parser.parse_args(argv)


def _digest_file(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _failure_count(value: Any) -> int:
    if value is None:
        return 0
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return max(value, 0)
    if isinstance(value, (dict, list, tuple, set)):
        return len(value)
    raise ValueError("manifest failures must be a count or collection")


def _normalise_failed_pages(value: Any) -> tuple[int, ...]:
    if value is None:
        return ()
    if not isinstance(value, list):
        raise ValueError("manifest failed_pages must be a list")
    return tuple(sorted(int(page) for page in value))


def _load_manifest(
    manifest_path: Path, *, expected_page_count: int = EXPECTED_PAGE_COUNT
) -> OcrManifestEvidence:
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("OCR manifest must contain an object")
    if payload.get("contract_version") != OCR_CONTRACT_VERSION:
        raise ValueError("unsupported OCR manifest contract_version")
    source = payload.get("source")
    if not isinstance(source, dict):
        raise ValueError("OCR manifest source is missing")
    page_count = int(source.get("page_count", -1))
    if page_count != expected_page_count:
        raise ValueError(
            f"OCR manifest must cover {expected_page_count} PDF pages, got {page_count}"
        )

    # The first real full-book OCR used an ``ocr`` summary.  The durable CLI
    # writes the same facts under ``summary`` plus ``pipeline`` and ``run``.
    legacy_ocr = payload.get("ocr") if isinstance(payload.get("ocr"), dict) else {}
    summary = payload.get("summary") if isinstance(payload.get("summary"), dict) else {}
    run = payload.get("run") if isinstance(payload.get("run"), dict) else {}
    completed_pages = int(
        summary.get("completed_pages", legacy_ocr.get("completed_pages", -1))
    )
    failed_pages = _normalise_failed_pages(
        run.get("failed_pages", legacy_ocr.get("failed_pages", []))
    )
    failures_count = _failure_count(payload.get("failures"))
    if completed_pages != expected_page_count:
        raise ValueError(
            f"OCR manifest completed {completed_pages}/{expected_page_count} pages"
        )
    if failed_pages or failures_count:
        raise ValueError(
            f"OCR manifest contains failures: pages={list(failed_pages)}, "
            f"records={failures_count}"
        )
    status = payload.get("status")
    if status is not None and status != "complete":
        raise ValueError(f"OCR manifest status is not complete: {status}")

    raw_pages = payload.get("pages")
    if not isinstance(raw_pages, list) or len(raw_pages) != expected_page_count:
        raise ValueError(
            f"OCR manifest pages must contain {expected_page_count} records"
        )
    page_records: list[dict[str, Any]] = []
    numbers: list[int] = []
    for raw in raw_pages:
        if not isinstance(raw, dict):
            raise ValueError("OCR manifest page record must be an object")
        page = int(raw.get("page", -1))
        numbers.append(page)
        page_records.append(dict(raw))
    if numbers != list(range(1, expected_page_count + 1)):
        raise ValueError("OCR manifest page records must be ordered, unique and complete")

    def optional_number(key: str) -> float | None:
        value = summary.get(key, legacy_ocr.get(key))
        return float(value) if value is not None else None

    duration_value = run.get("duration_ms", legacy_ocr.get("duration_ms"))
    character_count = int(
        summary.get("character_count", legacy_ocr.get("character_count", 0))
    )
    return OcrManifestEvidence(
        pdf_sha256=str(source.get("pdf_sha256", "")),
        page_count=page_count,
        completed_pages=completed_pages,
        failed_pages=failed_pages,
        failures_count=failures_count,
        ocr_duration_ms=(float(duration_value) if duration_value is not None else None),
        average_confidence=optional_number("average_confidence"),
        low_confidence_rate=optional_number("low_confidence_rate"),
        character_count=character_count,
        page_records=tuple(page_records),
    )


def _validate_page_pairs(
    ocr_dir: Path, *, expected_page_count: int = EXPECTED_PAGE_COUNT
) -> dict[int, dict[str, Path]]:
    actual: dict[int, dict[str, Path]] = {}
    for path in ocr_dir.iterdir():
        match = PAGE_FILE.match(path.name)
        if match:
            actual.setdefault(int(match.group(1)), {})[match.group(2)] = path
    expected = set(range(1, expected_page_count + 1))
    if set(actual) != expected:
        missing = sorted(expected - set(actual))
        extra = sorted(set(actual) - expected)
        raise ValueError(f"OCR page files mismatch: missing={missing}, extra={extra}")
    incomplete = [page for page, files in actual.items() if set(files) != {"txt", "tsv"}]
    if incomplete:
        raise ValueError(f"OCR TXT/TSV pairing incomplete for pages: {incomplete}")
    return actual


def _tsv_average_confidence(path: Path) -> float | None:
    total = 0.0
    count = 0
    with path.open(encoding="utf-8", errors="replace", newline="") as handle:
        for row in csv.DictReader(handle, delimiter="\t"):
            try:
                confidence = float(row.get("conf", "-1"))
            except (TypeError, ValueError):
                continue
            if confidence >= 0:
                total += confidence
                count += 1
    return total / count if count else None


def _build_pdf_pages(
    *,
    manifest: OcrManifestEvidence,
    page_files: dict[int, dict[str, Path]],
    printed_page_offset: int,
) -> tuple[list[PdfOcrPageInput], dict[str, int]]:
    pages: list[PdfOcrPageInput] = []
    readable_pages = 0
    rendered_pages = 0
    for record in manifest.page_records:
        physical_page = int(record["page"])
        content = page_files[physical_page]["txt"].read_text(
            encoding="utf-8", errors="replace"
        ).strip()
        printed = physical_page + printed_page_offset
        printed_label = str(printed) if printed > 0 else None
        if not content:
            rendered_pages += 1
            page = PdfOcrPageInput(
                pdf_page_index=physical_page - 1,
                printed_page_label=printed_label,
                ocr_state=OcrState.RENDERED,
                ocr_confidence=None,
                content="",
            )
        else:
            readable_pages += 1
            confidence = record.get("average_confidence")
            if confidence is None:
                confidence = _tsv_average_confidence(page_files[physical_page]["tsv"])
            page = PdfOcrPageInput(
                pdf_page_index=physical_page - 1,
                printed_page_label=printed_label,
                ocr_state=OcrState.OCR_UNVERIFIED,
                ocr_confidence=float(confidence) if confidence is not None else 0.0,
                content=content,
            )
        pages.append(page)
    return pages, {
        "source_pages": len(pages),
        "readable_pages": readable_pages,
        "rendered_blank_pages": rendered_pages,
    }


def _safe_worker_text(value: str, *, state_dir: Path) -> str:
    return " ".join(value.replace(str(state_dir), "<state-dir>").split())[:2000]


def _bounded_text(value: Any, *, limit: int = 240) -> str:
    text = " ".join(str(value).split())
    if len(text) > limit:
        return f"{text[: limit - 1]}…"
    return text


def _count_value(payload: dict[str, Any], *keys: str) -> int:
    for key in keys:
        value = payload.get(key)
        if isinstance(value, int) and not isinstance(value, bool):
            return max(value, 0)
        if isinstance(value, (list, dict)):
            return len(value)
    return 0


def _load_content_gold(path: Path | None) -> dict[str, Any]:
    """Reduce an external harness result to a bounded, source-free summary.

    The harness is useful diagnostic evidence, but it is not the production
    model gateway and therefore never satisfies ``live_content_quality``.
    """

    empty = {
        "status": "not_run",
        "execution_mode": "codex_agent_external_harness",
        "coverage": {"sampled_pages": 0, "total_pages": EXPECTED_PAGE_COUNT},
        "chapter_result_count": 0,
        "cross_chapter_insight_count": 0,
        "risks": [],
        "production_gateway_credited": False,
    }
    if path is None or not path.is_file():
        return empty
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("content gold summary must contain an object")
    coverage = payload.get("coverage")
    coverage = coverage if isinstance(coverage, dict) else {}
    sampled_pages = coverage.get(
        "sampled_pages",
        coverage.get(
            "covered_pages",
            payload.get("sampled_pages", payload.get("sample_pages", 0)),
        ),
    )
    total_pages = coverage.get("total_pages", payload.get("total_pages", EXPECTED_PAGE_COUNT))
    if not isinstance(sampled_pages, int) or not isinstance(total_pages, int):
        raise ValueError("content gold coverage counts must be integers")
    risks_value = payload.get(
        "risks", payload.get("ocr_and_evidence_risks", [])
    )
    if isinstance(risks_value, dict):
        risks_iterable = risks_value.values()
    elif isinstance(risks_value, list):
        risks_iterable = risks_value
    else:
        risks_iterable = [risks_value] if risks_value else []
    return {
        "status": "run",
        "execution_mode": "codex_agent_external_harness",
        "coverage": {
            "sampled_pages": max(sampled_pages, 0),
            "total_pages": max(total_pages, 0),
        },
        "chapter_result_count": _count_value(
            payload, "chapter_result_count", "chapter_results", "chapters"
        ),
        "cross_chapter_insight_count": _count_value(
            payload,
            "cross_chapter_insight_count",
            "cross_chapter_insights",
            "syntheses",
        ),
        "risks": [_bounded_text(value) for value in risks_iterable][:12],
        "production_gateway_credited": False,
    }


def _run_worker_once(
    *, repo_root: Path, state_dir: Path, timeout_seconds: float
) -> WorkerRunEvidence:
    env = os.environ.copy()
    env["EXPLORATION_STATE_DIR"] = str(state_dir)
    env["EXPLORATION_MODEL_PROVIDER"] = "none"
    for key in (
        "EXPLORATION_MODEL_BASE_URL",
        "EXPLORATION_MODEL_API_KEY",
        "EXPLORATION_EXTRACT_MODEL",
        "EXPLORATION_SYNTHESIS_MODEL",
        "EXPLORATION_JUDGE_MODEL",
    ):
        env.pop(key, None)
    started = perf_counter()
    try:
        completed = subprocess.run(
            [str(repo_root / "scripts" / "run-exploration-worker.sh"), "--once"],
            cwd=repo_root,
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )
    except subprocess.TimeoutExpired as error:
        return WorkerRunEvidence(
            returncode=124,
            stdout=_safe_worker_text(
                (error.stdout or b"").decode("utf-8", errors="replace")
                if isinstance(error.stdout, bytes)
                else (error.stdout or ""),
                state_dir=state_dir,
            ),
            stderr="worker timed out",
            duration_ms=round((perf_counter() - started) * 1000, 3),
        )
    except OSError as error:
        return WorkerRunEvidence(
            returncode=127,
            stdout="",
            stderr=_bounded_text(f"worker launch failed: {type(error).__name__}"),
            duration_ms=round((perf_counter() - started) * 1000, 3),
        )
    return WorkerRunEvidence(
        returncode=completed.returncode,
        stdout=_safe_worker_text(completed.stdout, state_dir=state_dir),
        stderr=_safe_worker_text(completed.stderr, state_dir=state_dir),
        duration_ms=round((perf_counter() - started) * 1000, 3),
    )


def _source_fragments(pages: list[PdfOcrPageInput]) -> list[bytes]:
    fragments: list[bytes] = []
    for page in pages:
        text = page.content.strip()
        for offset in range(0, len(text), 64):
            fragment = text[offset : offset + 32]
            if len(fragment) >= 16:
                fragments.append(fragment.encode("utf-8"))
    return fragments


def _database_bytes(state_dir: Path) -> bytes:
    return b"".join(
        path.read_bytes()
        for path in state_dir.glob("explorations.sqlite3*")
        if path.is_file()
    )


def _check(code: str, condition: bool, detail: str) -> AcceptanceCheck:
    return AcceptanceCheck(code=code, status="pass" if condition else "fail", detail=detail)


def _run_acceptance(
    *,
    pdf: Path,
    ocr_dir: Path,
    state_dir: Path,
    printed_page_offset: int,
    worker_timeout_seconds: float,
    expected_page_count: int = EXPECTED_PAGE_COUNT,
) -> dict[str, Any]:
    started = perf_counter()
    pdf = pdf.expanduser().resolve()
    ocr_dir = ocr_dir.expanduser().resolve()
    state_dir = state_dir.expanduser().resolve()
    if not pdf.is_file():
        raise ValueError("input PDF does not exist")
    if not (ocr_dir / "manifest.json").is_file():
        raise ValueError("OCR manifest does not exist")
    try:
        state_dir.relative_to(REPO_ROOT.resolve())
    except ValueError:
        pass
    else:
        raise ValueError("acceptance state-dir must be outside the repository")
    state_dir.mkdir(parents=True, exist_ok=True)
    if any(state_dir.iterdir()):
        raise ValueError("acceptance state-dir must be empty")

    manifest = _load_manifest(
        ocr_dir / "manifest.json", expected_page_count=expected_page_count
    )
    pdf_digest = _digest_file(pdf)
    if pdf_digest != manifest.pdf_sha256:
        raise ValueError("PDF SHA-256 does not match the OCR manifest")
    page_files = _validate_page_pairs(
        ocr_dir, expected_page_count=expected_page_count
    )
    pages, page_counts = _build_pdf_pages(
        manifest=manifest,
        page_files=page_files,
        printed_page_offset=printed_page_offset,
    )
    fragments = _source_fragments(pages)

    store = ExplorationStore(state_dir=state_dir, model_gateway=NoModelGateway())
    created = None
    deletion_ok = False
    first_worker: WorkerRunEvidence | None = None
    second_worker: WorkerRunEvidence | None = None
    try:
        created = store.create(
            ImportExplorationRequest(
                source_format=SourceFormat.PDF_OCR,
                pdf_checksum_sha256=pdf_digest,
                pdf_pages=pages,
                title="中华人民共和国史 第三卷：思考与选择",
                author="沈志华",
                version_label="完整私人 PDF；全页 OCR 未人工逐字复核",
                brief=ExplorationBrief(
                    question=(
                        "作者如何解释1956至1957年间从知识分子会议到反右派运动"
                        "的政策转向，以及知识分子、党内整风与政治动员之间的关系？"
                    ),
                    time_range="1956—1957",
                    geography=["中国"],
                    threads=["政策转向", "知识分子", "党内整风", "政治动员", "证据方法"],
                    status="confirmed",
                ),
            )
        )
        document = created.document
        assert document is not None and document.pdf_ocr_metadata is not None
        exploration_id = created.id
        waiting_profile, waiting_plan = store.control_plane.planning_adapter.build(created)
        run = store.create_analysis_run(exploration_id, base_revision=created.revision)
        run_id = run.id
        source_checksum = document.checksum_sha256
        paragraph_count = document.paragraph_count
        section_count = document.section_count
        character_count = document.char_count
        store.close()

        first_worker = _run_worker_once(
            repo_root=REPO_ROOT,
            state_dir=state_dir,
            timeout_seconds=worker_timeout_seconds,
        )
        store = ExplorationStore(state_dir=state_dir, model_gateway=NoModelGateway())
        recovered = store.get(exploration_id)
        recovery_ok = bool(
            recovered.document
            and recovered.document.checksum_sha256 == source_checksum
            and recovered.document.paragraph_count == paragraph_count
            and recovered.document.pdf_ocr_metadata
            and recovered.document.pdf_ocr_metadata.pdf_checksum_sha256 == pdf_digest
            and recovered.document.pdf_ocr_metadata.page_count == expected_page_count
        )
        waiting = store.get_analysis_result(exploration_id, run_id)
        review_gate_ok = bool(
            first_worker.returncode == 0
            and waiting.status.state == "waiting_review"
            and waiting.review_required
            and not waiting.review_submitted
        )
        if review_gate_ok:
            store.submit_analysis_review(
                exploration_id,
                run_id,
                AnalysisReviewRequest(
                    review_token=waiting.review_token,
                    decisions=(),
                ),
            )
        store.close()

        second_worker = _run_worker_once(
            repo_root=REPO_ROOT,
            state_dir=state_dir,
            timeout_seconds=worker_timeout_seconds,
        )
        store = ExplorationStore(state_dir=state_dir, model_gateway=NoModelGateway())
        final = store.get_analysis_result(exploration_id, run_id)
        completed_ok = bool(
            second_worker.returncode == 0 and final.status.state == "completed"
        )
        artifacts = final.artifacts
        projections = final.published_projections
        gap_counts = Counter(item.code for item in artifacts.gaps)
        no_model_ok = bool(
            not artifacts.claims
            and not artifacts.events
            and not projections.argument.nodes
            and not projections.timeline.items
            and gap_counts.get("model_not_called", 0) > 0
        )

        anchors = [
            paragraph
            for section in recovered.document.sections
            for paragraph in section.paragraphs
        ] if recovered.document else []
        readable_page_indices = {
            page.pdf_page_index for page in pages if page.ocr_state is not OcrState.RENDERED
        }
        anchored_page_indices = {
            anchor.locator.pdf_page_index
            for anchor in anchors
            if anchor.locator.source_format is SourceFormat.PDF_OCR
            and anchor.locator.pdf_page_index is not None
        }
        locator_coverage_ok = bool(
            anchors
            and all(
                anchor.locator.source_format is SourceFormat.PDF_OCR
                and anchor.locator.pdf_page_index is not None
                and anchor.locator.ocr_state is OcrState.OCR_UNVERIFIED
                for anchor in anchors
            )
            and anchored_page_indices == readable_page_indices
        )

        database = _database_bytes(state_dir)
        source_isolation_ok = bool(
            all(fragment not in database for fragment in fragments)
            and str(state_dir).encode("utf-8") not in database
            and str(pdf).encode("utf-8") not in database
            and str(ocr_dir).encode("utf-8") not in database
        )
        selected_passes = Counter(
            item.pass_type.value for item in waiting_plan.work_items
        )
        skipped_passes = {
            item.pass_type.value: item.reason_code
            for item in waiting_plan.skipped_passes
        }

        store.delete(exploration_id)
        deletion_ok = not (state_dir / "vault" / exploration_id).exists()
    finally:
        try:
            if created is not None and not deletion_ok:
                store.delete(created.id)
        except Exception:
            try:
                cleanup_store = ExplorationStore(
                    state_dir=state_dir, model_gateway=NoModelGateway()
                )
                try:
                    cleanup_store.delete(created.id)
                finally:
                    cleanup_store.close()
            except Exception:
                pass
        try:
            store.close()
        except Exception:
            pass

    assert first_worker is not None and second_worker is not None
    checks = [
        _check(
            "full_source_manifest",
            manifest.completed_pages == expected_page_count
            and not manifest.failed_pages
            and manifest.failures_count == 0,
            f"OCR manifest 覆盖 {manifest.completed_pages}/{expected_page_count} 页且无失败。",
        ),
        _check(
            "pdf_checksum",
            pdf_digest == manifest.pdf_sha256,
            "输入 PDF 的 SHA-256 与 OCR manifest 一致。",
        ),
        _check(
            "page_file_pairing",
            len(page_files) == expected_page_count,
            f"{expected_page_count} 页 TXT/TSV 均一一对应。",
        ),
        _check(
            "durable_recovery",
            recovery_ok,
            "关闭导入进程后，从私有保险库恢复相同来源指纹、段落与 PDF 页元数据。",
        ),
        _check(
            "pdf_page_locator_coverage",
            locator_coverage_ok,
            f"{len(anchored_page_indices)}/{len(readable_page_indices)} 个可读页具有页级锚点；空白页不伪造正文。",
        ),
        _check(
            "human_review_gate",
            review_gate_ok,
            "第一次独立 worker 后停于 waiting_review，并在进程重开后提交明确空复核。",
        ),
        _check(
            "cross_process_worker",
            first_worker.returncode == 0
            and second_worker.returncode == 0
            and completed_ok,
            "两次 --once worker 均由独立进程恢复并完成各自阶段。",
        ),
        _check(
            "explicit_no_model",
            no_model_ok,
            "强制 NoModel 产生模型未调用缺口，且保持 0 主张、0 事件、0 发布投影。",
        ),
        _check(
            "sqlite_source_isolation",
            source_isolation_ok,
            "SQLite 未发现来源抽样片段、输入路径或状态目录。",
        ),
        _check(
            "private_vault_deletion",
            deletion_ok,
            "删除探索后，对应私有来源保险库目录消失。",
        ),
        AcceptanceCheck(
            code="live_content_quality",
            status="not_run",
            detail="provider=none；真实模型没有运行，内容质量验收受阻。",
        ),
    ]
    overall = "failed" if any(item.status == "fail" for item in checks) else "blocked"
    return {
        "contract_version": CONTRACT_VERSION,
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "overall": overall,
        "case": {
            "series": "中华人民共和国史（1949—1981）",
            "volume": "第三卷：思考与选择（1956—1957）",
            "author": "沈志华",
            "source_scope": "完整私人 PDF；OCR 未人工逐字复核",
        },
        "source": {
            "pdf_sha256": pdf_digest,
            "document_checksum_sha256": source_checksum,
            **page_counts,
            "manifest_completed_pages": manifest.completed_pages,
            "character_count": character_count,
            "paragraph_count": paragraph_count,
            "section_count": section_count,
            "ocr_average_confidence": manifest.average_confidence,
            "ocr_low_confidence_rate": manifest.low_confidence_rate,
        },
        "routing": {
            "primary_book_type": waiting_profile.primary_type.value,
            "classification_confidence": waiting_profile.classification_confidence,
            "type_scores": {
                item.book_type.value: item.score for item in waiting_profile.type_scores
            },
            "uncertainties": [item.code for item in waiting_profile.uncertainties],
            "selected_passes": dict(sorted(selected_passes.items())),
            "skipped_passes": dict(sorted(skipped_passes.items())),
            "planned_work_item_count": waiting_plan.estimated_work_item_count,
        },
        "execution": {
            "worker_mode": "two_real_subprocesses",
            "model_provider": "none",
            "state_sequence": [run.state, waiting.status.state, final.status.state],
            "workers": [asdict(first_worker), asdict(second_worker)],
            "gap_counts": dict(sorted(gap_counts.items())),
            "claim_count": len(artifacts.claims),
            "event_count": len(artifacts.events),
            "published_argument_nodes": len(projections.argument.nodes),
            "published_timeline_items": len(projections.timeline.items),
            "ocr_duration_ms": manifest.ocr_duration_ms,
            "acceptance_duration_ms": round((perf_counter() - started) * 1000, 3),
        },
        "checks": [asdict(item) for item in checks],
    }


def _pill(status: str) -> str:
    labels = {"pass": "通过", "fail": "失败", "not_run": "未运行"}
    return f'<span class="pill {status}">{labels[status]}</span>'


def _format_duration(value: float | None) -> str:
    if value is None:
        return "未记录"
    seconds = value / 1000
    if seconds >= 60:
        return f"{seconds / 60:.1f} 分钟"
    return f"{seconds:.1f} 秒"


def _render_report(result: dict[str, Any]) -> str:
    checks_html = "".join(
        "<tr>"
        f"<td>{_pill(item['status'])}</td>"
        f"<td><code>{escape(item['code'])}</code></td>"
        f"<td>{escape(item['detail'])}</td>"
        "</tr>"
        for item in result["checks"]
    )
    workers_html = "".join(
        f"<article><b>Worker {index}</b><span>{item['returncode']}</span>"
        f"<p>{escape(item['stdout'] or '无标准输出')}</p>"
        f"<small>{escape(_format_duration(item['duration_ms']))}</small></article>"
        for index, item in enumerate(result["execution"]["workers"], 1)
    )
    embedded = json.dumps(result, ensure_ascii=False, sort_keys=True).replace("</", "<\\/")
    source = result["source"]
    execution = result["execution"]
    routing = result["routing"]
    content_gold = result["content_gold"]
    gold_coverage = content_gold["coverage"]
    gold_risks = "".join(f"<li>{escape(item)}</li>" for item in content_gold["risks"])
    gold_html = (
        "<p>未提供外部内容金标摘要；本项未运行。</p>"
        if content_gold["status"] == "not_run"
        else (
            f"<p><code>{escape(content_gold['execution_mode'])}</code> 抽查 "
            f"{gold_coverage['sampled_pages']}/{gold_coverage['total_pages']} 页，形成 "
            f"{content_gold['chapter_result_count']} 个章节结果与 "
            f"{content_gold['cross_chapter_insight_count']} 个跨章洞见。</p>"
            f"<ul>{gold_risks}</ul>"
        )
    )
    verdict = "执行失败" if result["overall"] == "failed" else "受阻"
    return f"""<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>《中华人民共和国史》第三卷完整 PDF 后端验收</title>
<style>
:root{{--paper:#f4f0e6;--ink:#17202a;--muted:#66707a;--line:#d7cebb;--red:#a84232;--green:#286652;--amber:#9a6d18}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--paper);color:var(--ink);font-family:-apple-system,BlinkMacSystemFont,"PingFang SC","Microsoft YaHei",sans-serif;line-height:1.6}}
main{{max-width:1180px;margin:auto;padding:48px 28px 80px}}.eyebrow{{color:var(--red);font-size:12px;font-weight:800;letter-spacing:.15em}}
h1{{max-width:980px;margin:12px 0 16px;font:750 clamp(34px,5vw,64px)/1.08 Georgia,"Noto Serif SC",serif;letter-spacing:-.035em}}h2{{margin:0 0 18px;font:700 26px/1.2 Georgia,"Noto Serif SC",serif}}
.lede{{max-width:880px;color:#48535d;font-size:18px}}.verdict{{margin:30px 0;padding:22px 24px;border:1px solid var(--line);background:rgba(255,255,255,.45);display:grid;grid-template-columns:160px 1fr;gap:24px}}.verdict strong{{font:700 30px/1.1 Georgia,serif;color:var(--amber)}}
.grid{{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin:24px 0 48px}}.metric{{padding:20px;border:1px solid var(--line);background:rgba(255,255,255,.32)}}.metric b{{display:block;font:700 28px/1.1 Georgia,serif;margin:7px 0}}.metric small{{color:var(--muted)}}
section{{margin-top:50px}}table{{width:100%;border-collapse:collapse;background:rgba(255,255,255,.25)}}th,td{{padding:12px 14px;border-bottom:1px solid var(--line);text-align:left;vertical-align:top}}th{{color:var(--muted);font-size:12px}}code{{font-family:"SFMono-Regular",monospace;font-size:12px}}
.pill{{display:inline-block;padding:2px 8px;border-radius:999px;font-size:12px;font-weight:800}}.pass{{background:#dce9e2;color:var(--green)}}.fail{{background:#f0d9d3;color:var(--red)}}.not_run{{background:#eee3c5;color:var(--amber)}}
.workers{{display:grid;grid-template-columns:1fr 1fr;gap:14px}}.workers article{{padding:18px;border:1px solid var(--line);background:#faf7ef}}.workers span{{float:right;font-weight:800}}.workers p{{color:var(--muted);font:12px/1.5 "SFMono-Regular",monospace;overflow-wrap:anywhere}}
.note{{border-left:4px solid var(--amber);padding:16px 18px;background:#ece3d0}}footer{{margin-top:58px;padding-top:18px;border-top:1px solid var(--line);color:var(--muted);font-size:12px}}
@media(max-width:760px){{.grid,.workers{{grid-template-columns:1fr}}.verdict{{grid-template-columns:1fr}}}}
</style></head><body><main>
<div class="eyebrow">HISTORY-KB · FULL PDF BACKEND ACCEPTANCE</div>
<h1>验收未完成：来源与控制面已通过，真实模型未运行</h1>
<p class="lede">这次输入是《中华人民共和国史》第三卷的完整 {source['source_pages']} 页私人 PDF/OCR，不是 9 张公开样例。报告证明了多少，就只写多少；没有模型内容输出时，不生成替代性的历史结论。</p>
<div class="verdict"><strong>{verdict}</strong><div><p><b>当前结论：</b>{'存在控制面失败项，不能进入模型验收。' if result['overall']=='failed' else '完整来源导入、跨进程恢复、复核闸门、来源隔离与删除已接受验收；内容质量仍未运行。'}</p><p>provider 固定为 <code>none</code>，所以整体结果按规则保持 <code>{result['overall']}</code>，绝不升级为通过或有条件通过。</p></div></div>
<div class="grid">
<div class="metric"><small>来源覆盖</small><b>{source['manifest_completed_pages']}/{source['source_pages']}</b><span>{source['readable_pages']} 个可读页 · {source['rendered_blank_pages']} 个空白页</span></div>
<div class="metric"><small>解析</small><b>{source['paragraph_count']} 段</b><span>{source['character_count']} 字符 · {source['section_count']} 个页节</span></div>
<div class="metric"><small>OCR 平均置信度</small><b>{source['ocr_average_confidence'] if source['ocr_average_confidence'] is not None else '未测'}</b><span>低置信词元率 {source['ocr_low_confidence_rate'] if source['ocr_low_confidence_rate'] is not None else '未测'}</span></div>
<div class="metric"><small>真实耗时</small><b>{escape(_format_duration(execution['acceptance_duration_ms']))}</b><span>OCR {escape(_format_duration(execution['ocr_duration_ms']))}</span></div>
</div>
<section><h2>逐项验收</h2><table><thead><tr><th>状态</th><th>检查</th><th>可复核证据</th></tr></thead><tbody>{checks_html}</tbody></table></section>
<section><h2>两次真实跨进程 Worker</h2><div class="workers">{workers_html}</div><p class="note">第一次 worker 只推进到人工复核闸门；关闭并重开状态存储、提交明确空复核后，第二次 worker 才完成。两次输出只含 run ID 与状态，不含原文。</p></section>
<section><h2>类型路由</h2><p>主类型 <code>{escape(routing['primary_book_type'])}</code>，置信度 {routing['classification_confidence']:.3f}；规划 {routing['planned_work_item_count']} 个工作项。该结果证明路由与规划实际运行，不证明这些分类或任何历史洞见已经由真实模型验证。</p></section>
<section><h2>外部内容抽查</h2>{gold_html}<p class="note">这一路径不是生产 model gateway，结果只作为后续金标与风险线索，不计入 <code>live_content_quality</code> 通过项。</p></section>
<section><h2>内容边界</h2><p>最终产物：{execution['claim_count']} 条主张、{execution['event_count']} 个事件、{execution['published_argument_nodes']} 个论证节点、{execution['published_timeline_items']} 个时间轴项目。这里的零不是“没有历史内容”，而是 NoModel 安全通道拒绝编造。</p><p class="note">下一道门必须配置真实 provider，再以人工金标验收主张归因、事件时序、作者判断、证据定位和跨章节综合；在那之前，产品不能宣称已经理解或拆解本书。</p></section>
<footer>报告不含 PDF 原图、OCR 原文、绝对路径或凭证。来源仅以 SHA-256、页数、计数和来源安全的运行状态表示。</footer>
<script id="run-data" type="application/json">{embedded}</script></main></body></html>"""


def _assert_source_free_report(
    html: str, *, forbidden_paths: list[Path], pages: list[PdfOcrPageInput]
) -> None:
    for path in forbidden_paths:
        if str(path.expanduser().resolve()) in html:
            raise RuntimeError("report contains an absolute private path")
    for fragment in _source_fragments(pages):
        if fragment.decode("utf-8", errors="ignore") in html:
            raise RuntimeError("report contains OCR source text")


def main(argv: list[str] | None = None) -> int:
    args = _args(argv)
    if args.worker_timeout_seconds <= 0:
        print("error: worker timeout must be greater than zero", file=sys.stderr)
        return 2
    try:
        result = _run_acceptance(
            pdf=args.pdf,
            ocr_dir=args.ocr_dir,
            state_dir=args.state_dir,
            printed_page_offset=args.printed_page_offset,
            worker_timeout_seconds=args.worker_timeout_seconds,
        )
        result["content_gold"] = _load_content_gold(args.content_gold_json)
        html = _render_report(result)
        manifest = _load_manifest(args.ocr_dir / "manifest.json")
        page_files = _validate_page_pairs(args.ocr_dir)
        pages, _ = _build_pdf_pages(
            manifest=manifest,
            page_files=page_files,
            printed_page_offset=args.printed_page_offset,
        )
        _assert_source_free_report(
            html,
            forbidden_paths=[
                args.pdf,
                args.ocr_dir,
                args.state_dir,
                *([args.content_gold_json] if args.content_gold_json else []),
            ],
            pages=pages,
        )
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(html, encoding="utf-8")
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    print(
        json.dumps(
            {
                "output": str(args.output),
                "overall": result["overall"],
                "source_pages": result["source"]["source_pages"],
                "model_provider": result["execution"]["model_provider"],
            },
            ensure_ascii=False,
        )
    )
    return 2 if result["overall"] == "failed" else 3


if __name__ == "__main__":
    raise SystemExit(main())
