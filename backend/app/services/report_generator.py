"""Report Generation Service for Academic Question Paper Analysis.

Provides:
1. Professional PDF generation via ReportLab (A4 format, custom header/footer,
   cognitive demand distributions, difficulty index, question matrix, HotS vs LotS).
2. Streaming RFC 4180 CSV export for institutional archiving and spreadsheet audits.
"""

import csv
import io
from datetime import datetime
from typing import Dict, Any, List, Optional

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, mm
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    KeepTogether,
    HRFlowable,
)
from reportlab.pdfgen import canvas

from backend.app.models.paper import Paper
from backend.app.models.question import Question


# ---------------------------------------------------------------------------
# Dynamic Two-Pass Canvas for Page Numbering & Running Footers
# ---------------------------------------------------------------------------

class NumberedCanvas(canvas.Canvas):
    """Custom canvas that calculates total pages and renders running footers."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_footer(num_pages)
            super().showPage()
        super().save()

    def draw_footer(self, page_count: int):
        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#64748B"))  # Slate-500
        
        # Top footer separator line
        self.setStrokeColor(colors.HexColor("#E2E8F0"))
        self.setLineWidth(0.5)
        self.line(36, 32, A4[0] - 36, 32)
        
        # Left branding
        self.drawString(
            36, 20,
            "Automatic Question Paper Difficulty Analyzer • Academic Audit Report"
        )
        
        # Right page counter
        page_str = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(A4[0] - 36, 20, page_str)
        self.restoreState()


# ---------------------------------------------------------------------------
# Analytics Computation Helpers
# ---------------------------------------------------------------------------

BLOOM_LEVELS = ["Remember", "Understand", "Apply", "Analyze", "Evaluate", "Create"]
DIFFICULTY_TIERS = ["Easy", "Medium", "Hard"]


def compute_paper_analytics(paper: Paper) -> Dict[str, Any]:
    """Compute aggregate Bloom and difficulty metrics across paper questions."""
    total_q = len(paper.questions)
    total_marks = 0.0
    known_marks = 0.0

    blooms_counts = {lvl: 0 for lvl in BLOOM_LEVELS}
    blooms_marks = {lvl: 0.0 for lvl in BLOOM_LEVELS}

    diff_counts = {d: 0 for d in DIFFICULTY_TIERS}
    diff_marks = {d: 0.0 for d in DIFFICULTY_TIERS}

    continuous_scores: List[float] = []
    reviewed_count = 0

    for q in paper.questions:
        q_marks = q.marks if q.marks is not None else 0.0
        total_marks += q_marks
        if q.marks is not None:
            known_marks += q_marks

        if q.is_reviewed_by_teacher:
            reviewed_count += 1

        # Determine effective values (latest correction has precedence)
        effective_bloom = None
        effective_diff = None
        cont_score = None

        if q.corrections:
            latest_corr = sorted(q.corrections, key=lambda c: c.created_at)[-1]
            effective_bloom = latest_corr.corrected_blooms_level
            effective_diff = latest_corr.corrected_difficulty
            if latest_corr.corrected_marks is not None:
                q_marks = latest_corr.corrected_marks
        elif q.predictions:
            latest_pred = sorted(q.predictions, key=lambda p: p.created_at)[-1]
            effective_bloom = latest_pred.predicted_blooms_level
            effective_diff = latest_pred.predicted_difficulty
            cont_score = latest_pred.continuous_difficulty_score

        if effective_bloom in blooms_counts:
            blooms_counts[effective_bloom] += 1
            blooms_marks[effective_bloom] += q_marks

        if effective_diff in diff_counts:
            diff_counts[effective_diff] += 1
            diff_marks[effective_diff] += q_marks

        if cont_score is not None:
            continuous_scores.append(cont_score)
        elif effective_diff == "Easy":
            continuous_scores.append(0.20)
        elif effective_diff == "Medium":
            continuous_scores.append(0.55)
        elif effective_diff == "Hard":
            continuous_scores.append(0.88)

    avg_difficulty = (
        sum(continuous_scores) / len(continuous_scores) if continuous_scores else 0.50
    )

    if avg_difficulty < 0.35:
        overall_rating = "Easy (Foundational)"
    elif avg_difficulty < 0.65:
        overall_rating = "Medium (Balanced)"
    else:
        overall_rating = "Hard (Advanced / Rigorous)"

    # HOTS (Higher-Order Thinking Skills) vs LOTS (Lower-Order)
    hots_q = (
        blooms_counts["Apply"]
        + blooms_counts["Analyze"]
        + blooms_counts["Evaluate"]
        + blooms_counts["Create"]
    )
    lots_q = blooms_counts["Remember"] + blooms_counts["Understand"]

    hots_marks = (
        blooms_marks["Apply"]
        + blooms_marks["Analyze"]
        + blooms_marks["Evaluate"]
        + blooms_marks["Create"]
    )
    lots_marks = blooms_marks["Remember"] + blooms_marks["Understand"]

    return {
        "total_questions": total_q,
        "total_marks": total_marks,
        "reviewed_count": reviewed_count,
        "review_percentage": round((reviewed_count / total_q * 100), 1) if total_q else 0.0,
        "average_difficulty_score": round(avg_difficulty, 3),
        "overall_difficulty_rating": overall_rating,
        "blooms_counts": blooms_counts,
        "blooms_marks": blooms_marks,
        "diff_counts": diff_counts,
        "diff_marks": diff_marks,
        "hots_questions": hots_q,
        "lots_questions": lots_q,
        "hots_marks": hots_marks,
        "lots_marks": lots_marks,
    }


# ---------------------------------------------------------------------------
# Report Generator Class
# ---------------------------------------------------------------------------

class ReportGenerator:
    """Enterprise report engine producing PDF and CSV outputs."""

    @staticmethod
    def generate_pdf(paper: Paper) -> bytes:
        """Generate a complete, publication-grade academic PDF evaluation report."""
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            leftMargin=36,
            rightMargin=36,
            topMargin=36,
            bottomMargin=48,
        )

        styles = getSampleStyleSheet()

        # Custom Palette & Typographic Styles
        PRIMARY_COLOR = colors.HexColor("#1E1B4B")     # Deep Indigo
        ACCENT_COLOR = colors.HexColor("#4F46E5")      # Vibrant Indigo
        BG_LIGHT = colors.HexColor("#F8FAFC")          # Slate 50
        TEXT_MUTED = colors.HexColor("#64748B")        # Slate 500
        BORDER_COLOR = colors.HexColor("#CBD5E1")      # Slate 300

        title_style = ParagraphStyle(
            "ReportTitle",
            parent=styles["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=18,
            leading=22,
            textColor=PRIMARY_COLOR,
            spaceAfter=4,
        )

        subtitle_style = ParagraphStyle(
            "ReportSubtitle",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=10,
            leading=14,
            textColor=TEXT_MUTED,
            spaceAfter=12,
        )

        section_heading = ParagraphStyle(
            "SectionHeading",
            parent=styles["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=12,
            leading=16,
            textColor=PRIMARY_COLOR,
            spaceBefore=12,
            spaceAfter=6,
        )

        cell_text = ParagraphStyle(
            "CellText",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=8,
            leading=11,
            textColor=colors.HexColor("#1E293B"),
        )

        cell_bold = ParagraphStyle(
            "CellBold",
            parent=cell_text,
            fontName="Helvetica-Bold",
        )

        story = []
        analytics = compute_paper_analytics(paper)

        # 1. Header & Title Block
        story.append(Paragraph("EXAMINATION DIFFICULTY & COGNITIVE LEVEL AUDIT REPORT", title_style))
        owner_name = f"{paper.owner.full_name} ({paper.owner.email})" if paper.owner else "N/A"
        date_str = datetime.utcnow().strftime("%B %d, %Y - %H:%M UTC")
        story.append(
            Paragraph(
                f"Generated for: <b>{owner_name}</b> | Date: <b>{date_str}</b>",
                subtitle_style,
            )
        )
        story.append(HRFlowable(width="100%", thickness=1.5, color=ACCENT_COLOR, spaceAfter=10))

        # 2. Paper Metadata & Executive Summary Card
        meta_data = [
            [
                Paragraph("<b>Paper Title:</b>", cell_bold),
                Paragraph(paper.title, cell_text),
                Paragraph("<b>Subject:</b>", cell_bold),
                Paragraph(paper.subject, cell_text),
            ],
            [
                Paragraph("<b>Academic Year:</b>", cell_bold),
                Paragraph(paper.academic_year or "N/A", cell_text),
                Paragraph("<b>Term:</b>", cell_bold),
                Paragraph(paper.term or "N/A", cell_text),
            ],
            [
                Paragraph("<b>Total Questions:</b>", cell_bold),
                Paragraph(str(analytics["total_questions"]), cell_text),
                Paragraph("<b>Total Marks:</b>", cell_bold),
                Paragraph(f"{analytics['total_marks']:.1f}", cell_text),
            ],
            [
                Paragraph("<b>Difficulty Index:</b>", cell_bold),
                Paragraph(f"{analytics['average_difficulty_score']:.2f} / 1.00", cell_text),
                Paragraph("<b>Overall Rating:</b>", cell_bold),
                Paragraph(f"<b>{analytics['overall_difficulty_rating']}</b>", cell_text),
            ],
            [
                Paragraph("<b>Teacher Review:</b>", cell_bold),
                Paragraph(
                    f"{analytics['reviewed_count']}/{analytics['total_questions']} "
                    f"({analytics['review_percentage']}%) verified",
                    cell_text,
                ),
                Paragraph("<b>File Reference:</b>", cell_bold),
                Paragraph(f"{paper.original_filename} ({paper.file_type.upper()})", cell_text),
            ],
        ]

        meta_table = Table(meta_data, colWidths=[90, 170, 90, 170])
        meta_table.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), BG_LIGHT),
                ("BOX", (0, 0), (-1, -1), 1, BORDER_COLOR),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ])
        )
        story.append(meta_table)
        story.append(Spacer(1, 10))

        # 3. Cognitive Domain (Bloom's Revised Taxonomy) Distribution Table
        story.append(Paragraph("1. Bloom's Revised Taxonomy Cognitive Breakdown", section_heading))
        bloom_header = [
            Paragraph("<b>Cognitive Domain</b>", cell_bold),
            Paragraph("<b>Category Type</b>", cell_bold),
            Paragraph("<b>Questions</b>", cell_bold),
            Paragraph("<b>% Questions</b>", cell_bold),
            Paragraph("<b>Total Marks</b>", cell_bold),
            Paragraph("<b>% Marks</b>", cell_bold),
        ]
        bloom_rows = [bloom_header]

        total_q = analytics["total_questions"] or 1
        total_m = analytics["total_marks"] or 1.0

        for lvl in BLOOM_LEVELS:
            cnt = analytics["blooms_counts"][lvl]
            mrk = analytics["blooms_marks"][lvl]
            cat_type = "HOTS (Higher Order)" if lvl in {"Apply", "Analyze", "Evaluate", "Create"} else "LOTS (Lower Order)"
            bloom_rows.append([
                Paragraph(lvl, cell_text),
                Paragraph(cat_type, cell_text),
                Paragraph(str(cnt), cell_text),
                Paragraph(f"{(cnt / total_q) * 100:.1f}%", cell_text),
                Paragraph(f"{mrk:.1f}", cell_text),
                Paragraph(f"{(mrk / total_m) * 100:.1f}%", cell_text),
            ])

        # HOTS vs LOTS Summary Row
        bloom_rows.append([
            Paragraph("<b>HOTS Total (Apply-Create)</b>", cell_bold),
            Paragraph("<b>Higher Order Skills</b>", cell_bold),
            Paragraph(f"<b>{analytics['hots_questions']}</b>", cell_bold),
            Paragraph(f"<b>{(analytics['hots_questions'] / total_q) * 100:.1f}%</b>", cell_bold),
            Paragraph(f"<b>{analytics['hots_marks']:.1f}</b>", cell_bold),
            Paragraph(f"<b>{(analytics['hots_marks'] / total_m) * 100:.1f}%</b>", cell_bold),
        ])

        bloom_table = Table(bloom_rows, colWidths=[100, 110, 75, 75, 80, 80])
        bloom_table.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E0E7FF")),  # Indigo-100
                ("BOX", (0, 0), (-1, -1), 1, BORDER_COLOR),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
                ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#F1F5F9")),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ])
        )
        story.append(bloom_table)
        story.append(Spacer(1, 10))

        # 4. Difficulty Tier Distribution Table
        story.append(Paragraph("2. Question Difficulty Tier Breakdown", section_heading))
        diff_header = [
            Paragraph("<b>Difficulty Tier</b>", cell_bold),
            Paragraph("<b>Cognitive Expectation</b>", cell_bold),
            Paragraph("<b>Questions</b>", cell_bold),
            Paragraph("<b>% Questions</b>", cell_bold),
            Paragraph("<b>Total Marks</b>", cell_bold),
            Paragraph("<b>% Marks</b>", cell_bold),
        ]
        diff_rows = [diff_header]

        diff_desc = {
            "Easy": "Direct recall / foundational understanding",
            "Medium": "Procedural application & basic analysis",
            "Hard": "Complex synthesis, evaluation & design",
        }

        for tier in DIFFICULTY_TIERS:
            cnt = analytics["diff_counts"][tier]
            mrk = analytics["diff_marks"][tier]
            diff_rows.append([
                Paragraph(tier, cell_text),
                Paragraph(diff_desc.get(tier, ""), cell_text),
                Paragraph(str(cnt), cell_text),
                Paragraph(f"{(cnt / total_q) * 100:.1f}%", cell_text),
                Paragraph(f"{mrk:.1f}", cell_text),
                Paragraph(f"{(mrk / total_m) * 100:.1f}%", cell_text),
            ])

        diff_table = Table(diff_rows, colWidths=[90, 160, 65, 65, 70, 70])
        diff_table.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#FEF3C7")),  # Amber-100
                ("BOX", (0, 0), (-1, -1), 1, BORDER_COLOR),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ])
        )
        story.append(diff_table)
        story.append(Spacer(1, 12))

        # 5. Question-by-Question Granular Matrix
        story.append(Paragraph("3. Detailed Question Analysis & Human Review Matrix", section_heading))
        q_header = [
            Paragraph("<b>Q#</b>", cell_bold),
            Paragraph("<b>Sec</b>", cell_bold),
            Paragraph("<b>Marks</b>", cell_bold),
            Paragraph("<b>Question Text Snippet</b>", cell_bold),
            Paragraph("<b>Bloom Level</b>", cell_bold),
            Paragraph("<b>Difficulty</b>", cell_bold),
            Paragraph("<b>Review</b>", cell_bold),
        ]
        q_rows = [q_header]

        for q in paper.questions:
            # Determine effective bloom and difficulty
            eff_bloom = "N/A"
            eff_diff = "N/A"
            review_badge = "Auto"
            
            if q.corrections:
                latest_corr = sorted(q.corrections, key=lambda c: c.created_at)[-1]
                eff_bloom = f"<b>{latest_corr.corrected_blooms_level}</b>*"
                eff_diff = f"<b>{latest_corr.corrected_difficulty}</b>*"
                review_badge = "Override"
            elif q.predictions:
                latest_pred = sorted(q.predictions, key=lambda p: p.created_at)[-1]
                eff_bloom = f"{latest_pred.predicted_blooms_level} ({latest_pred.blooms_confidence:.0%})"
                eff_diff = f"{latest_pred.predicted_difficulty} ({latest_pred.difficulty_confidence:.0%})"
                review_badge = "Model"

            sec_name = q.section.section_name if q.section else "General"
            snippet = q.question_text[:110] + ("..." if len(q.question_text) > 110 else "")
            marks_str = f"{q.marks:.1f}" if q.marks is not None else "-"

            q_rows.append([
                Paragraph(q.question_number, cell_text),
                Paragraph(sec_name[:10], cell_text),
                Paragraph(marks_str, cell_text),
                Paragraph(snippet, cell_text),
                Paragraph(eff_bloom, cell_text),
                Paragraph(eff_diff, cell_text),
                Paragraph(review_badge, cell_text),
            ])

        q_table = Table(q_rows, colWidths=[35, 45, 38, 222, 85, 55, 40], repeatRows=1)
        q_table.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F1F5F9")),
                ("BOX", (0, 0), (-1, -1), 1, BORDER_COLOR),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ])
        )
        story.append(q_table)
        story.append(Spacer(1, 15))

        # 6. Academic Sign-off Section (KeepTogether to ensure signatures stay on same page)
        sign_block = []
        sign_block.append(HRFlowable(width="100%", thickness=1, color=BORDER_COLOR, spaceAfter=8))
        sign_block.append(Paragraph("<b>ACADEMIC AUDIT SIGN-OFF & VERIFICATION</b>", cell_bold))
        sign_block.append(Spacer(1, 15))

        sig_data = [
            [
                Paragraph("________________________________________<br/><b>Course Instructor / Faculty Examiner</b><br/>Date: ", cell_text),
                Paragraph("________________________________________<br/><b>Head of Department / Academic Dean</b><br/>Date: ", cell_text),
            ]
        ]
        sig_table = Table(sig_data, colWidths=[260, 260])
        sig_table.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
        sign_block.append(sig_table)
        
        story.append(KeepTogether(sign_block))

        # Build PDF document
        doc.build(story, canvasmaker=NumberedCanvas)
        return buffer.getvalue()

    @staticmethod
    def generate_csv(paper: Paper) -> str:
        """Generate an RFC 4180 streaming CSV export of all questions and model inferences."""
        output = io.StringIO()
        writer = csv.writer(output, quoting=csv.QUOTE_MINIMAL)

        # Header row
        writer.writerow([
            "Paper ID",
            "Paper Title",
            "Subject",
            "Question Number",
            "Section",
            "Marks",
            "Page Number",
            "Question Text",
            "Predicted Bloom Level",
            "Bloom Confidence",
            "Corrected Bloom Level",
            "Effective Bloom Level",
            "Final Bloom Level",
            "Predicted Difficulty",
            "Difficulty Confidence",
            "Continuous Difficulty Score",
            "Corrected Difficulty",
            "Effective Difficulty",
            "Final Difficulty",
            "Teacher Reviewed",
            "Teacher Rationale",
        ])

        for q in paper.questions:
            latest_pred = None
            if q.predictions:
                latest_pred = sorted(q.predictions, key=lambda p: p.created_at)[-1]

            latest_corr = None
            if q.corrections:
                latest_corr = sorted(q.corrections, key=lambda c: c.created_at)[-1]

            pred_bloom = latest_pred.predicted_blooms_level if latest_pred else ""
            bloom_conf = f"{latest_pred.blooms_confidence:.4f}" if latest_pred else ""
            corr_bloom = latest_corr.corrected_blooms_level if latest_corr else ""
            eff_bloom = corr_bloom or pred_bloom

            pred_diff = latest_pred.predicted_difficulty if latest_pred else ""
            diff_conf = f"{latest_pred.difficulty_confidence:.4f}" if latest_pred else ""
            cont_score = (
                f"{latest_pred.continuous_difficulty_score:.4f}"
                if (latest_pred and latest_pred.continuous_difficulty_score is not None)
                else ""
            )
            corr_diff = latest_corr.corrected_difficulty if latest_corr else ""
            eff_diff = corr_diff or pred_diff

            sec_name = q.section.section_name if q.section else "General"
            teacher_rationale = latest_corr.rationale if latest_corr else ""

            writer.writerow([
                paper.id,
                paper.title,
                paper.subject,
                q.question_number,
                sec_name,
                q.marks if q.marks is not None else "",
                q.page_number if q.page_number is not None else "",
                q.question_text,
                pred_bloom,
                bloom_conf,
                corr_bloom,
                eff_bloom,
                eff_bloom,
                pred_diff,
                diff_conf,
                cont_score,
                corr_diff,
                eff_diff,
                eff_diff,
                "YES" if (q.is_reviewed_by_teacher or latest_corr is not None) else "NO",
                teacher_rationale,
            ])

        return output.getvalue()
