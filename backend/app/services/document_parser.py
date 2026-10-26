"""Digital Document Parsing and Question Paper Segmentation Service.

Supports:
1. Security validation: Magic bytes inspection, file-size enforcement, path traversal defense.
2. PDF Extraction (PyMuPDF / fitz): Multi-page parsing, layout blocks, scanned document detection.
3. DOCX Extraction (python-docx): Paragraphs, numbered runs, table structures.
4. Question & Section Segmentation: Question index detection (1., 2(a)), marks extraction, section isolation.
5. Traceability: Retains page numbers, original coordinates, and raw question contexts.
"""

import os
import re
import uuid
import zipfile
from dataclasses import dataclass, field
from typing import List, Optional, Tuple, Dict, Any

import fitz  # PyMuPDF
import docx

from backend.app.core.config import settings
from research.preprocessing import clean_question_text

# Allowed file extensions and magic headers
ALLOWED_EXTENSIONS = {".pdf", ".docx"}
DEFAULT_MAX_FILE_SIZE = getattr(settings, "MAX_UPLOAD_SIZE_BYTES", 1024 * 1024 * 1024)  # 1 GB
MAX_FILE_SIZE = DEFAULT_MAX_FILE_SIZE

# Section boundary patterns: e.g., "SECTION A", "Part I", "Group B", "Unit 2"
SECTION_PATTERN = re.compile(
    r"^\s*(?:SECTION|PART|GROUP|UNIT)\s+([A-Z0-9]+)(?:\s*[:\-\—]\s*(.*))?",
    re.IGNORECASE,
)

# Question number patterns: e.g., "Q1.", "1.", "Question 2:", "3(a)", "(b)", "4.1"
QUESTION_START_PATTERN = re.compile(
    r"^\s*(?:(?:Q(?:uestion)?\.?\s*)?(\d+(?:\s*\([a-z0-9]+\)|\.[a-z0-9]+)?|\([a-z0-9]+\))[\.\:\)]\s*)(.*)",
    re.IGNORECASE,
)

# Marks allocation patterns: e.g., "[10 Marks]", "(5M)", "[CO1, 4 Marks]", "(10 marks)", "[5]"
MARKS_PATTERN = re.compile(
    r"(?:\[|\()(?:\s*[A-Z0-9]+[\s,]+)?(\d+(?:\.\d+)?)\s*(?:marks?|m)?\s*(?:\]|\))",
    re.IGNORECASE,
)


@dataclass
class ExtractedQuestion:
    """Individual segmented question record with provenance metadata."""

    question_number: str
    question_text: str
    cleaned_text: str
    marks: Optional[float] = None
    section_name: str = "General"
    page_number: Optional[int] = None
    order_index: int = 0


@dataclass
class ExtractedPaper:
    """Aggregated question paper extraction result."""

    filename: str
    file_type: str
    total_pages: int
    is_scanned_or_empty: bool
    sections: List[str] = field(default_factory=list)
    questions: List[ExtractedQuestion] = field(default_factory=list)
    total_marks: Optional[float] = None
    extraction_notes: List[str] = field(default_factory=list)


def validate_file_upload(
    file_bytes: bytes,
    original_filename: str,
    max_size: Optional[int] = None,
) -> Tuple[str, str]:
    """Validate uploaded file size, extension, and binary signature.
    
    Returns:
        Tuple of (clean_extension, secure_unique_filename)
    
    Raises:
        ValueError if invalid format, size limit exceeded, or magic bytes mismatch.
    """
    effective_limit = max_size if max_size is not None else getattr(settings, "MAX_UPLOAD_SIZE_BYTES", MAX_FILE_SIZE)
    if effective_limit and len(file_bytes) > effective_limit:
        limit_mb = effective_limit // (1024 * 1024)
        raise ValueError(f"File size exceeds maximum permitted limit of {limit_mb} MB.")

    if not file_bytes:
        raise ValueError("Uploaded file is empty (0 bytes).")

    # Defense against Path Traversal
    base_name = os.path.basename(original_filename)
    _, ext = os.path.splitext(base_name.lower())

    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError(f"Unsupported file format '{ext}'. Supported formats: .pdf, .docx")

    # Magic Bytes Validation
    if ext == ".pdf":
        if not file_bytes.startswith(b"%PDF-"):
            raise ValueError("Invalid file signature: File content does not match a valid PDF header.")
    elif ext == ".docx":
        # DOCX is a zip archive containing word/document.xml
        try:
            from io import BytesIO
            with zipfile.ZipFile(BytesIO(file_bytes)) as zf:
                if "word/document.xml" not in zf.namelist():
                    raise ValueError("File is not a valid Microsoft Word (.docx) document.")
        except zipfile.BadZipFile:
            raise ValueError("File content does not match a valid DOCX archive.")

    # Secure UUID-based storage filename
    secure_filename = f"{uuid.uuid4().hex}{ext}"
    return ext.lstrip("."), secure_filename


def extract_marks(line: str) -> Optional[float]:
    """Extract numeric marks if explicitly defined; returns None if not found."""
    matches = MARKS_PATTERN.findall(line)
    if matches:
        try:
            # Take the last matched marks specification on the line
            return float(matches[-1])
        except (ValueError, TypeError):
            return None
    return None


def segment_text_blocks(
    text_blocks: List[Tuple[str, Optional[int]]]
) -> Tuple[List[str], List[ExtractedQuestion], List[str]]:
    """Segment a stream of text blocks (line, page_number) into sections and questions.
    
    Returns:
        Tuple of (detected_sections, extracted_questions, extraction_notes)
    """
    sections: List[str] = []
    questions: List[ExtractedQuestion] = []
    notes: List[str] = []

    current_section = "General"
    current_q_num: Optional[str] = None
    current_q_lines: List[str] = []
    current_q_marks: Optional[float] = None
    current_q_page: Optional[int] = None
    order_idx = 0

    def flush_question():
        nonlocal current_q_num, current_q_lines, current_q_marks, current_q_page, order_idx
        if current_q_num and current_q_lines:
            raw_text = " ".join(current_q_lines).strip()
            # If marks were not captured from prefix/suffix, search entire question text
            if current_q_marks is None:
                current_q_marks = extract_marks(raw_text)

            cleaned = clean_question_text(raw_text, strip_marks=True, strip_indices=True)
            if cleaned:
                order_idx += 1
                questions.append(
                    ExtractedQuestion(
                        question_number=current_q_num,
                        question_text=raw_text,
                        cleaned_text=cleaned,
                        marks=current_q_marks,
                        section_name=current_section,
                        page_number=current_q_page,
                        order_index=order_idx,
                    )
                )
        current_q_num = None
        current_q_lines = []
        current_q_marks = None
        current_q_page = None

    for line_raw, page_num in text_blocks:
        line = line_raw.strip()
        if not line:
            continue

        # Check for Section header
        sec_match = SECTION_PATTERN.match(line)
        if sec_match:
            flush_question()
            sec_name = f"Section {sec_match.group(1).upper()}"
            if sec_match.group(2):
                sec_name += f" - {sec_match.group(2).strip()}"
            current_section = sec_name
            if sec_name not in sections:
                sections.append(sec_name)
            continue

        # Check for Question start
        q_match = QUESTION_START_PATTERN.match(line)
        if q_match:
            flush_question()
            current_q_num = q_match.group(1).strip()
            remainder_text = q_match.group(2).strip()
            current_q_marks = extract_marks(line)
            current_q_page = page_num
            if remainder_text:
                current_q_lines.append(remainder_text)
        else:
            # Continuation of existing question or preliminary metadata
            if current_q_num:
                current_q_lines.append(line)
                if current_q_marks is None:
                    current_q_marks = extract_marks(line)

    flush_question()

    if not sections and questions:
        sections.append("General")

    if not questions:
        notes.append("No explicit numbered questions (e.g., '1.', 'Q2') were detected in the text.")

    return sections, questions, notes


def extract_from_pdf(filepath: str) -> ExtractedPaper:
    """Extract and segment questions from a digital PDF document."""
    doc = fitz.open(filepath)
    total_pages = len(doc)
    text_blocks: List[Tuple[str, Optional[int]]] = []
    total_chars = 0

    for page_idx in range(total_pages):
        page = doc[page_idx]
        page_num = page_idx + 1
        page_text = page.get_text("text")
        total_chars += len(page_text.strip())

        for line in page_text.splitlines():
            if line.strip():
                text_blocks.append((line.strip(), page_num))

    doc.close()

    # Check for scanned or image-only PDF
    is_scanned = total_chars < 50
    notes = []
    if is_scanned:
        notes.append("Document contains insufficient extractable digital text (< 50 characters). Scanned image PDF suspected.")

    sections, questions, seg_notes = segment_text_blocks(text_blocks)
    notes.extend(seg_notes)

    # Compute total marks if available
    known_marks = [q.marks for q in questions if q.marks is not None]
    total_marks = sum(known_marks) if known_marks else None

    return ExtractedPaper(
        filename=os.path.basename(filepath),
        file_type="pdf",
        total_pages=total_pages,
        is_scanned_or_empty=is_scanned,
        sections=sections,
        questions=questions,
        total_marks=total_marks,
        extraction_notes=notes,
    )


def extract_from_docx(filepath: str) -> ExtractedPaper:
    """Extract and segment questions from a Microsoft Word document."""
    doc = docx.Document(filepath)
    text_blocks: List[Tuple[str, Optional[int]]] = []
    total_chars = 0

    for p in doc.paragraphs:
        txt = p.text.strip()
        if txt:
            total_chars += len(txt)
            text_blocks.append((txt, 1))  # DOCX lacks fixed page coordinates

    # Also parse tables if questions are formatted in table rows
    for table in doc.tables:
        for row in table.rows:
            row_texts = [cell.text.strip() for cell in row.cells if cell.text.strip()]
            if row_texts:
                combined_line = " | ".join(row_texts)
                total_chars += len(combined_line)
                text_blocks.append((combined_line, 1))

    is_empty = total_chars < 30
    notes = []
    if is_empty:
        notes.append("Word document contains minimal or no text.")

    sections, questions, seg_notes = segment_text_blocks(text_blocks)
    notes.extend(seg_notes)

    known_marks = [q.marks for q in questions if q.marks is not None]
    total_marks = sum(known_marks) if known_marks else None

    return ExtractedPaper(
        filename=os.path.basename(filepath),
        file_type="docx",
        total_pages=1,
        is_scanned_or_empty=is_empty,
        sections=sections,
        questions=questions,
        total_marks=total_marks,
        extraction_notes=notes,
    )


def parse_document(filepath: str) -> ExtractedPaper:
    """Central entry point to parse either PDF or DOCX question papers."""
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Document file not found at: {filepath}")

    ext = os.path.splitext(filepath)[1].lower()
    if ext == ".pdf":
        return extract_from_pdf(filepath)
    elif ext == ".docx":
        return extract_from_docx(filepath)
    else:
        raise ValueError(f"Unsupported document format: {ext}")
