# tests/test_scan_pipeline_skeleton.py
import os
from pathlib import Path
import pytest

# Allow import even if optional deps are missing
from backend.ocr.owlin_scan_pipeline import process_document

@pytest.mark.skipif("fitz" not in globals(), reason="PyMuPDF not available")
def test_process_pdf_minimal(tmp_path: Path):
    """
    Creates a 1-page PDF on the fly using PyMuPDF (if installed),
    runs the pipeline, and checks basic artifact layout.
    """
    try:
        import fitz  # type: ignore
    except Exception:
        pytest.skip("PyMuPDF not installed")

    pdf_path = tmp_path / "sample.pdf"
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), "OWLIN TEST PDF", fontsize=14)
    doc.save(str(pdf_path))
    doc.close()

    out = process_document(pdf_path)
    assert out["status"] in ("ok", "partial")
    assert "pages" in out and len(out["pages"]) >= 1
    assert "artifact_dir" in out
    assert Path(out["artifact_dir"]).exists()
    assert Path(out["artifact_dir"]) .joinpath("pages").exists()
    assert Path(out["artifact_dir"]) .joinpath("ocr_output.json").exists()


def test_process_missing_file():
    out = process_document("does_not_exist.pdf")
    assert out["status"] == "error"
    assert "File not found" in out["error"]
