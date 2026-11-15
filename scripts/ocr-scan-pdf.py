#!/usr/bin/env python3
"""Checkpointed local OCR for scan-only PDFs.

The durable output is deliberately restricted to directories outside this
repository.  A run stores page-level TXT/TSV checkpoints and an atomic manifest;
rendered page images exist only inside temporary directories.
"""

from __future__ import annotations

import argparse
import csv
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import time
from typing import Dict, Iterable, List, Optional, Sequence, Tuple


CONTRACT_VERSION = "scan_pdf_ocr_manifest.v1"
REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
PAGE_PATTERN = re.compile(r"^page-\d{4,}\.(?:txt|tsv)$")


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _is_within(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


def validate_output_path(output: Path, repository_root: Path = REPOSITORY_ROOT) -> Path:
    """Resolve and reject output paths that are inside the repository."""

    resolved = output.expanduser().resolve()
    resolved_repo = repository_root.resolve()
    if resolved == resolved_repo or _is_within(resolved, resolved_repo):
        raise ValueError(
            "OCR output must be outside the repository so source text cannot be "
            "committed accidentally"
        )
    return resolved


def digest_file(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _run_tool(args: Sequence[str], *, timeout_seconds: float) -> subprocess.CompletedProcess:
    return subprocess.run(
        list(args),
        check=True,
        capture_output=True,
        text=True,
        timeout=timeout_seconds,
    )


def pdf_page_count(pdf: Path, *, timeout_seconds: float) -> int:
    result = _run_tool(["pdfinfo", str(pdf)], timeout_seconds=timeout_seconds)
    match = re.search(r"^Pages:\s+(\d+)\s*$", result.stdout, re.MULTILINE)
    if not match:
        raise RuntimeError("pdfinfo did not return a page count")
    return int(match.group(1))


def tsv_metrics(path: Path) -> Tuple[int, Optional[float], int]:
    scored = 0
    confidence_sum = 0.0
    low_confidence = 0
    with path.open(encoding="utf-8", errors="replace", newline="") as handle:
        for row in csv.DictReader(handle, delimiter="\t"):
            try:
                confidence = float(row.get("conf", "-1"))
            except (TypeError, ValueError):
                continue
            if confidence < 0:
                continue
            scored += 1
            confidence_sum += confidence
            low_confidence += confidence < 60
    average = confidence_sum / scored if scored else None
    return scored, average, low_confidence


def _read_page_result(output: Path, page: int, status: str) -> Dict[str, object]:
    text_name = f"page-{page:04d}.txt"
    tsv_name = f"page-{page:04d}.tsv"
    text_path = output / text_name
    tsv_path = output / tsv_name
    scored, average, low = tsv_metrics(tsv_path)
    return {
        "page": page,
        "status": status,
        "text_file": text_name,
        "tsv_file": tsv_name,
        "characters": len(text_path.read_text(encoding="utf-8", errors="replace")),
        "scored_tokens": scored,
        "average_confidence": round(average, 4) if average is not None else None,
        "low_confidence_tokens": low,
    }


def ocr_page(
    *,
    pdf: Path,
    output: Path,
    page: int,
    scale_to: int,
    languages: str,
    psm: int,
    timeout_seconds: float,
    allow_checkpoint: bool,
) -> Dict[str, object]:
    text_path = output / f"page-{page:04d}.txt"
    tsv_path = output / f"page-{page:04d}.tsv"
    if allow_checkpoint and text_path.is_file() and tsv_path.is_file():
        return _read_page_result(output, page, "checkpoint_reused")

    started = time.monotonic()
    with tempfile.TemporaryDirectory(prefix=f"history-kb-ocr-{page:04d}-") as temp_dir:
        temporary = Path(temp_dir)
        image_prefix = temporary / "page"
        image_path = image_prefix.with_suffix(".png")
        ocr_base = temporary / "ocr"
        _run_tool(
            [
                "pdftoppm",
                "-f",
                str(page),
                "-l",
                str(page),
                "-singlefile",
                "-scale-to",
                str(scale_to),
                "-png",
                str(pdf),
                str(image_prefix),
            ],
            timeout_seconds=timeout_seconds,
        )
        _run_tool(
            [
                "tesseract",
                str(image_path),
                str(ocr_base),
                "-l",
                languages,
                "--psm",
                str(psm),
                "-c",
                "user_defined_dpi=150",
                "txt",
                "tsv",
            ],
            timeout_seconds=timeout_seconds,
        )
        temporary_text = ocr_base.with_suffix(".txt")
        temporary_tsv = ocr_base.with_suffix(".tsv")
        if not temporary_text.is_file() or not temporary_tsv.is_file():
            raise RuntimeError("tesseract did not create both TXT and TSV outputs")
        os.replace(str(temporary_text), str(text_path))
        os.replace(str(temporary_tsv), str(tsv_path))

    result = _read_page_result(output, page, "succeeded")
    result["duration_ms"] = round((time.monotonic() - started) * 1000, 2)
    return result


def atomic_json(path: Path, payload: object) -> None:
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    with temporary.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(str(temporary), str(path))


def _load_existing_manifest(path: Path) -> Optional[Dict[str, object]]:
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"existing manifest is not readable JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise RuntimeError("existing manifest must contain a JSON object")
    return payload


def _checkpoint_identity(
    *, pdf_sha256: str, page_count: int, file_size_bytes: int, languages: str, scale_to: int, psm: int
) -> Dict[str, object]:
    return {
        "source": {
            "pdf_sha256": pdf_sha256,
            "page_count": page_count,
            "file_size_bytes": file_size_bytes,
        },
        "pipeline": {
            "engine": "tesseract",
            "languages": languages,
            "scale_to": scale_to,
            "psm": psm,
        },
    }


def _assert_resume_compatible(
    existing: Optional[Dict[str, object]], identity: Dict[str, object], output: Path
) -> bool:
    checkpoints = [path for path in output.iterdir() if PAGE_PATTERN.match(path.name)]
    if existing is None:
        if checkpoints:
            raise RuntimeError(
                "page checkpoints exist without a manifest; use a new empty output directory"
            )
        return False
    if existing.get("contract_version") != CONTRACT_VERSION:
        raise RuntimeError("existing manifest has an unsupported contract version")
    if existing.get("source") != identity["source"]:
        raise RuntimeError("existing output belongs to a different PDF")
    if existing.get("pipeline") != identity["pipeline"]:
        raise RuntimeError("existing output uses different OCR parameters")
    return True


def _safe_failure(exc: BaseException, redactions: Iterable[str]) -> str:
    if isinstance(exc, subprocess.CalledProcessError):
        detail = str(exc.stderr or exc.stdout or "").strip()
        message = f"CalledProcessError: exit code {exc.returncode}"
        if detail:
            message = f"{message}: {detail}"
    elif isinstance(exc, subprocess.TimeoutExpired):
        message = f"TimeoutExpired: command exceeded {exc.timeout} seconds"
    else:
        message = f"{type(exc).__name__}: {exc}"
    for value in redactions:
        if value:
            message = message.replace(value, "<redacted-path>")
    message = " ".join(message.split())
    return message[:1000]


def _manifest_payload(
    *,
    identity: Dict[str, object],
    status: str,
    started_at: str,
    completed_at: Optional[str],
    duration_ms: float,
    workers: int,
    results: Dict[int, Dict[str, object]],
    failures: Dict[int, str],
) -> Dict[str, object]:
    pages = [results[key] for key in sorted(results)]
    scored_tokens = sum(int(item["scored_tokens"]) for item in pages)
    confidence_sum = sum(
        float(item["average_confidence"]) * int(item["scored_tokens"])
        for item in pages
        if item["average_confidence"] is not None
    )
    low_confidence = sum(int(item["low_confidence_tokens"]) for item in pages)
    reused_pages = [int(item["page"]) for item in pages if item["status"] == "checkpoint_reused"]
    succeeded_pages = [int(item["page"]) for item in pages if item["status"] == "succeeded"]
    return {
        "contract_version": CONTRACT_VERSION,
        "status": status,
        **identity,
        "run": {
            "started_at": started_at,
            "completed_at": completed_at,
            "duration_ms": round(duration_ms, 2),
            "workers": workers,
            "succeeded_pages": succeeded_pages,
            "reused_pages": reused_pages,
            "failed_pages": sorted(failures),
        },
        "summary": {
            "completed_pages": len(results),
            "character_count": sum(int(item["characters"]) for item in pages),
            "scored_tokens": scored_tokens,
            "average_confidence": (
                round(confidence_sum / scored_tokens, 4) if scored_tokens else None
            ),
            "low_confidence_tokens": low_confidence,
            "low_confidence_rate": (
                round(low_confidence / scored_tokens, 6) if scored_tokens else None
            ),
        },
        "pages": pages,
        "failures": {str(key): value for key, value in sorted(failures.items())},
    }


def _require_tools() -> None:
    missing = [tool for tool in ("pdfinfo", "pdftoppm", "tesseract") if not shutil.which(tool)]
    if missing:
        raise RuntimeError(f"required tools are missing: {', '.join(missing)}")


def run_ocr(
    pdf: Path,
    output: Path,
    *,
    workers: int = 6,
    scale_to: int = 2400,
    languages: str = "chi_tra+eng",
    psm: int = 3,
    timeout_seconds: float = 300.0,
) -> int:
    if workers < 1:
        raise ValueError("workers must be at least 1")
    if scale_to < 1:
        raise ValueError("scale-to must be at least 1")
    if psm < 0 or psm > 13:
        raise ValueError("psm must be between 0 and 13")
    if timeout_seconds <= 0:
        raise ValueError("timeout-seconds must be greater than 0")

    source = pdf.expanduser().resolve()
    if not source.is_file():
        raise FileNotFoundError(f"input PDF does not exist: {source}")
    destination = validate_output_path(output)
    destination.mkdir(parents=True, exist_ok=True)
    _require_tools()

    page_count = pdf_page_count(source, timeout_seconds=timeout_seconds)
    identity = _checkpoint_identity(
        pdf_sha256=digest_file(source),
        page_count=page_count,
        file_size_bytes=source.stat().st_size,
        languages=languages,
        scale_to=scale_to,
        psm=psm,
    )
    manifest_path = destination / "manifest.json"
    allow_checkpoint = _assert_resume_compatible(
        _load_existing_manifest(manifest_path), identity, destination
    )
    started_at = _utc_now()
    started = time.monotonic()
    results: Dict[int, Dict[str, object]] = {}
    failures: Dict[int, str] = {}

    def write_manifest(status: str, completed_at: Optional[str] = None) -> None:
        atomic_json(
            manifest_path,
            _manifest_payload(
                identity=identity,
                status=status,
                started_at=started_at,
                completed_at=completed_at,
                duration_ms=(time.monotonic() - started) * 1000,
                workers=workers,
                results=results,
                failures=failures,
            ),
        )

    write_manifest("running")
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {
            executor.submit(
                ocr_page,
                pdf=source,
                output=destination,
                page=page,
                scale_to=scale_to,
                languages=languages,
                psm=psm,
                timeout_seconds=timeout_seconds,
                allow_checkpoint=allow_checkpoint,
            ): page
            for page in range(1, page_count + 1)
        }
        for future in as_completed(futures):
            page = futures[future]
            try:
                results[page] = future.result()
                failures.pop(page, None)
            except Exception as exc:  # retained in the manifest for a later retry
                failures[page] = _safe_failure(
                    exc,
                    (str(source), str(destination)),
                )
            write_manifest("running")
            finished = len(results) + len(failures)
            if finished % 10 == 0 or failures or finished == page_count:
                print(
                    f"completed={len(results)}/{page_count} failed={len(failures)}",
                    flush=True,
                )

    complete = not failures and len(results) == page_count
    write_manifest("complete" if complete else "partial_failure", _utc_now())
    return 0 if complete else 2


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="OCR a scanned PDF into resumable per-page TXT and TSV checkpoints."
    )
    parser.add_argument("pdf", type=Path, help="input PDF")
    parser.add_argument(
        "output",
        type=Path,
        help="empty or compatible checkpoint directory outside this repository",
    )
    parser.add_argument("--workers", type=int, default=6)
    parser.add_argument("--scale-to", type=int, default=2400)
    parser.add_argument("--languages", default="chi_tra+eng")
    parser.add_argument("--psm", type=int, default=3)
    parser.add_argument("--timeout-seconds", type=float, default=300.0)
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    try:
        return run_ocr(
            args.pdf,
            args.output,
            workers=args.workers,
            scale_to=args.scale_to,
            languages=args.languages,
            psm=args.psm,
            timeout_seconds=args.timeout_seconds,
        )
    except (FileNotFoundError, RuntimeError, ValueError, subprocess.SubprocessError) as exc:
        print(f"error: {exc}", file=__import__("sys").stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
