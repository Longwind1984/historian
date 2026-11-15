import importlib.util
import json
from pathlib import Path
import re
import subprocess

import pytest


REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "scripts" / "ocr-scan-pdf.py"


@pytest.fixture()
def ocr_cli():
    spec = importlib.util.spec_from_file_location("scan_pdf_ocr_cli", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _fake_tools(monkeypatch, ocr_cli, *, pages=2, fail_page=None):
    calls = []

    def fake_which(name):
        return f"/test/bin/{name}"

    def fake_run(args, **kwargs):
        calls.append(list(args))
        if args[0] == "pdfinfo":
            return subprocess.CompletedProcess(args, 0, stdout=f"Pages: {pages}\n", stderr="")
        if args[0] == "pdftoppm":
            Path(args[-1]).with_suffix(".png").write_bytes(b"not-a-real-png")
            return subprocess.CompletedProcess(args, 0, stdout="", stderr="")
        if args[0] == "tesseract":
            match = re.search(r"history-kb-ocr-(\d+)-", Path(args[1]).parent.name)
            assert match is not None
            page = int(match.group(1))
            if page == fail_page:
                raise subprocess.CalledProcessError(1, args, stderr="synthetic OCR failure")
            base = Path(args[2])
            base.with_suffix(".txt").write_text(f"page {page} text", encoding="utf-8")
            base.with_suffix(".tsv").write_text(
                "level\tconf\ttext\n5\t90\tpage\n5\t50\ttext\n",
                encoding="utf-8",
            )
            return subprocess.CompletedProcess(args, 0, stdout="", stderr="")
        raise AssertionError(f"unexpected tool: {args[0]}")

    monkeypatch.setattr(ocr_cli.shutil, "which", fake_which)
    monkeypatch.setattr(ocr_cli.subprocess, "run", fake_run)
    return calls


def test_rejects_output_inside_repository(ocr_cli):
    with pytest.raises(ValueError, match="outside the repository"):
        ocr_cli.validate_output_path(REPO / "private-ocr-output")


def test_manifest_is_private_atomic_and_resume_reuses_pages(tmp_path, monkeypatch, ocr_cli):
    source = tmp_path / "private-source.pdf"
    source.write_bytes(b"scan-pdf-fixture")
    output = tmp_path / "ocr-output"
    calls = _fake_tools(monkeypatch, ocr_cli)

    assert ocr_cli.run_ocr(source, output, workers=2) == 0
    manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["contract_version"] == "scan_pdf_ocr_manifest.v1"
    assert manifest["status"] == "complete"
    assert manifest["source"] == {
        "pdf_sha256": ocr_cli.digest_file(source),
        "page_count": 2,
        "file_size_bytes": len(b"scan-pdf-fixture"),
    }
    assert manifest["run"]["failed_pages"] == []
    assert manifest["run"]["duration_ms"] >= 0
    assert manifest["summary"]["completed_pages"] == 2
    assert len(manifest["pages"]) == 2
    assert str(source.resolve()) not in json.dumps(manifest)
    assert not list(output.glob("*.png"))
    assert not list(output.glob(".*.tmp"))
    first_ocr_calls = [args for args in calls if args[0] in {"pdftoppm", "tesseract"}]
    assert len(first_ocr_calls) == 4

    calls.clear()
    assert ocr_cli.run_ocr(source, output, workers=2) == 0
    resumed = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    assert resumed["run"]["reused_pages"] == [1, 2]
    assert not [args for args in calls if args[0] in {"pdftoppm", "tesseract"}]


def test_failed_page_is_recorded_and_retried(tmp_path, monkeypatch, ocr_cli):
    source = tmp_path / "source.pdf"
    source.write_bytes(b"another-scan")
    output = tmp_path / "ocr-output"
    _fake_tools(monkeypatch, ocr_cli, fail_page=2)

    assert ocr_cli.run_ocr(source, output, workers=2) == 2
    failed = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    assert failed["status"] == "partial_failure"
    assert failed["run"]["failed_pages"] == [2]
    assert "synthetic OCR failure" in failed["failures"]["2"]
    assert failed["run"]["reused_pages"] == []

    calls = _fake_tools(monkeypatch, ocr_cli)
    assert ocr_cli.run_ocr(source, output, workers=2) == 0
    recovered = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    assert recovered["status"] == "complete"
    assert recovered["run"]["failed_pages"] == []
    assert recovered["run"]["reused_pages"] == [1]
    assert [args[0] for args in calls].count("pdftoppm") == 1
    assert [args[0] for args in calls].count("tesseract") == 1
