# tests/test_api_ocr_run.py
from __future__ import annotations
from pathlib import Path
from fastapi.testclient import TestClient
import os
import io
import pytest

# Import the app
try:
    from backend.main import app  # adjust path if different
except Exception as e:
    pytest.skip(f"Cannot import backend.main: {e}", allow_module_level=True)

client = TestClient(app)

def _make_pdf_in_memory() -> bytes:
    try:
        import fitz  # PyMuPDF
    except Exception:
        # Minimal PDF bytes (valid but tiny) if PyMuPDF isn't available
        return (b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
                b"2 0 obj<</Type/Pages/Count 1/Kids[3 0 R]>>endobj\n"
                b"3 0 obj<</Type/Page/MediaBox[0 0 200 200]/Parent 2 0 R/Contents 4 0 R>>endobj\n"
                b"4 0 obj<</Length 44>>stream\nBT /F1 12 Tf 72 120 Td (OWLIN TEST) Tj ET\nendstream\nendobj\nxref\n0 5\n0000000000 65535 f \n"
                b"trailer<</Root 1 0 R/Size 5>>\nstartxref\n0\n%%EOF")
    # build small PDF using fitz
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 120), "OWLIN TEST")
    buf = doc.tobytes()
    doc.close()
    return buf

def test_ocr_run_disabled_by_default(monkeypatch):
    monkeypatch.setenv("FEATURE_OCR_PIPELINE_V2", "false")
    resp = client.post(
        "/api/ocr/run",
        files={"file": ("demo.pdf", _make_pdf_in_memory(), "application/pdf")}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("status") == "disabled"
    assert data.get("flag") == "FEATURE_OCR_PIPELINE_V2"

def test_ocr_run_enabled_basic(monkeypatch, tmp_path: Path):
    # Enable feature; ensure artifacts directory exists
    monkeypatch.setenv("FEATURE_OCR_PIPELINE_V2", "true")
    monkeypatch.setenv("OCR_ARTIFACT_ROOT", str(tmp_path / "uploads"))
    resp = client.post(
        "/api/ocr/run",
        files={"file": ("demo.pdf", _make_pdf_in_memory(), "application/pdf")}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("feature") == "v2"
    assert "status" in data
    assert "pages" in data
    assert "overall_confidence" in data
    # Check artifact dir creation
    artifact_dir = data.get("artifact_dir")
    if artifact_dir:
        assert Path(artifact_dir).exists()
