"""Automated test suite verifying digital document parsing and question segmentation."""

import os
import pytest
from backend.app.services.document_parser import (
    validate_file_upload,
    extract_from_pdf,
    extract_from_docx,
    parse_document,
)

FIXTURES_DIR = "backend/tests/fixtures"
SAMPLE_PDF = os.path.join(FIXTURES_DIR, "sample_cs_exam.pdf")
SAMPLE_DOCX = os.path.join(FIXTURES_DIR, "sample_se_exam.docx")
SCANNED_PDF = os.path.join(FIXTURES_DIR, "scanned_empty.pdf")


def test_upload_validation_valid_pdf():
    """Verify upload validation succeeds for valid PDF bytes and generates secure UUID filename."""
    with open(SAMPLE_PDF, "rb") as f:
        content = f.read()

    ext, secure_name = validate_file_upload(content, "CS301_Final_Exam.pdf")
    assert ext == "pdf"
    assert secure_name.endswith(".pdf")
    assert len(secure_name) > 30  # UUID hex length + extension


def test_upload_validation_valid_docx():
    """Verify upload validation succeeds for valid DOCX bytes."""
    with open(SAMPLE_DOCX, "rb") as f:
        content = f.read()

    ext, secure_name = validate_file_upload(content, "SE402_Midterm.docx")
    assert ext == "docx"
    assert secure_name.endswith(".docx")


def test_upload_validation_oversized_file():
    """Verify upload validation rejects files exceeding the configured maximum permitted limit."""
    huge_bytes = b"%PDF-" + b"0" * 2048
    with pytest.raises(ValueError, match="exceeds maximum permitted limit"):
        validate_file_upload(huge_bytes, "huge.pdf", max_size=1024)


def test_upload_validation_unsupported_format():
    """Verify upload validation rejects unsupported file extensions."""
    with pytest.raises(ValueError, match="Unsupported file format"):
        validate_file_upload(b"test data", "malicious_script.exe")


def test_upload_validation_magic_bytes_mismatch():
    """Verify upload validation detects file spoofing (non-PDF content with .pdf extension)."""
    fake_pdf = b"This is plain text disguised as a PDF file"
    with pytest.raises(ValueError, match="does not match a valid PDF header"):
        validate_file_upload(fake_pdf, "spoofed.pdf")


def test_pdf_extraction_sections_and_questions():
    """Verify PyMuPDF extracts sections, questions, marks, and page numbers from PDF exam."""
    assert os.path.exists(SAMPLE_PDF)
    paper = extract_from_pdf(SAMPLE_PDF)

    assert paper.file_type == "pdf"
    assert paper.total_pages == 2
    assert paper.is_scanned_or_empty is False

    # Verify sections
    assert len(paper.sections) >= 3
    section_names = [s.upper() for s in paper.sections]
    assert any("SECTION A" in s for s in section_names)
    assert any("SECTION B" in s for s in section_names)
    assert any("SECTION C" in s for s in section_names)

    # Verify questions count
    assert len(paper.questions) == 10

    # Verify individual questions and marks
    q1 = paper.questions[0]
    assert q1.question_number in ["1", "Q1"]
    assert "deadlock" in q1.cleaned_text.lower()
    assert q1.marks == 2.0
    assert q1.page_number == 1

    # Verify question on page 2
    q10 = paper.questions[-1]
    assert q10.question_number in ["10", "Q10"]
    assert "microkernel" in q10.cleaned_text.lower()
    assert q10.marks == 12.0
    assert q10.page_number == 2

    # Verify total marks sum
    assert paper.total_marks is not None
    assert paper.total_marks > 40.0


def test_docx_extraction_sections_and_questions():
    """Verify python-docx extracts sections, questions, and marks from Word exam."""
    assert os.path.exists(SAMPLE_DOCX)
    paper = extract_from_docx(SAMPLE_DOCX)

    assert paper.file_type == "docx"
    assert paper.is_scanned_or_empty is False
    assert len(paper.questions) == 5

    # Verify sections
    assert len(paper.sections) >= 2
    assert any("SECTION A" in s.upper() for s in paper.sections)
    assert any("SECTION B" in s.upper() for s in paper.sections)

    # Verify marks
    q1 = paper.questions[0]
    assert q1.marks == 3.0
    assert "cohesion" in q1.cleaned_text.lower()

    q5 = paper.questions[4]
    assert q5.marks == 10.0
    assert "kafka" in q5.cleaned_text.lower()


def test_scanned_empty_pdf_detection():
    """Verify parser detects documents with insufficient digital text and flags them."""
    assert os.path.exists(SCANNED_PDF)
    paper = extract_from_pdf(SCANNED_PDF)

    assert paper.is_scanned_or_empty is True
    assert len(paper.questions) == 0
    assert any("insufficient extractable digital text" in note.lower() for note in paper.extraction_notes)


def test_parse_document_dispatcher():
    """Verify parse_document automatically selects correct extractor by extension."""
    pdf_res = parse_document(SAMPLE_PDF)
    assert pdf_res.file_type == "pdf"

    docx_res = parse_document(SAMPLE_DOCX)
    assert docx_res.file_type == "docx"
