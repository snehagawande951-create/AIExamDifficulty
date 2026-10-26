"""Script to generate realistic academic examination papers in PDF and DOCX for testing.

Creates test fixtures in backend/tests/fixtures/:
1. sample_cs_exam.pdf (Multi-section, marks, 2 pages)
2. sample_se_exam.docx (Word document with headings, questions, and marks)
3. scanned_empty.pdf (PDF without extractable text)
"""

import os
import sys
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.lib import colors
import docx

FIXTURES_DIR = "backend/tests/fixtures"


def generate_pdf_exam():
    filepath = os.path.join(FIXTURES_DIR, "sample_cs_exam.pdf")
    doc = SimpleDocTemplate(filepath, pagesize=letter, rightMargin=54, leftMargin=54, topMargin=54, bottomMargin=54)
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "ExamTitle", parent=styles["Heading1"], alignment=1, fontSize=15, leading=18, spaceAfter=8
    )
    sub_title = ParagraphStyle(
        "SubTitle", parent=styles["Normal"], alignment=1, fontSize=10, leading=13, spaceAfter=14
    )
    sec_header = ParagraphStyle(
        "SecHeader", parent=styles["Heading2"], fontSize=12, leading=15, spaceBefore=14, spaceAfter=6, textColor=colors.navy
    )
    q_style = ParagraphStyle(
        "QuestionText", parent=styles["Normal"], fontSize=10, leading=14, spaceAfter=8, leftIndent=12
    )

    story = [
        Paragraph("NATIONAL INSTITUTE OF TECHNOLOGY", title_style),
        Paragraph("DEPARTMENT OF COMPUTER SCIENCE & ENGINEERING<br/>END SEMESTER EXAMINATION (ACADEMIC YEAR 2025-2026)", sub_title),
        Paragraph("Course: CS-301 Operating Systems | Max Marks: 50 | Duration: 3 Hours", sub_title),
        Spacer(1, 10),
        
        # Section A
        Paragraph("SECTION A (Short Answer Questions - Answer all)", sec_header),
        Paragraph("1. Define a deadlock and state the four necessary Coffman conditions. [2 Marks]", q_style),
        Paragraph("2. What is the primary role of the Translation Lookaside Buffer (TLB) in paging? [2 Marks]", q_style),
        Paragraph("3. State the difference between preemptive and non-preemptive CPU scheduling algorithms. [2 Marks]", q_style),
        Paragraph("4. Define an inode in UNIX file systems and state what information it stores. [2 Marks]", q_style),
        Spacer(1, 12),

        # Section B
        Paragraph("SECTION B (Analytical & Application Questions)", sec_header),
        Paragraph("5. Explain the step-by-step execution of Banker's Algorithm for deadlock avoidance with 3 processes. [6 Marks]", q_style),
        Paragraph("6. Calculate the average turnaround time and waiting time for Round Robin scheduling with time quantum q=4. [6 Marks]", q_style),
        Paragraph("7. Apply the FIFO and Optimal page replacement algorithms to the given reference string for 3 page frames. [6 Marks]", q_style),
        
        PageBreak(),  # Force page 2

        # Section C
        Paragraph("SECTION C (Comprehensive Design & System Evaluation)", sec_header),
        Paragraph("8. Analyze the producer-consumer problem using POSIX semaphores and identify where race conditions can arise. [10 Marks]", q_style),
        Paragraph("9. Architect a reader-writer synchronization locking primitive in C that prevents writer starvation. [12 Marks]", q_style),
        Paragraph("10. Critique the security and performance trade-offs of microkernel architectures versus monolithic kernels. [12 Marks]", q_style),
    ]

    doc.build(story)
    print(f"[CREATED] {filepath}")


def generate_docx_exam():
    filepath = os.path.join(FIXTURES_DIR, "sample_se_exam.docx")
    doc = docx.Document()

    # Header
    doc.add_heading("UNIVERSITY FACULTY OF ENGINEERING", level=0)
    p_meta = doc.add_paragraph("Course: SE-402 Software Architecture & Engineering\nTime: 2 Hours | Max Marks: 30")
    p_meta.runs[0].bold = True

    # Section A
    doc.add_heading("SECTION A - Conceptual Foundations", level=1)
    doc.add_paragraph("1. Define high cohesion and low coupling in modular software design. [3 Marks]")
    doc.add_paragraph("2. What is the fundamental difference between functional and non-functional requirements? [3 Marks]")
    doc.add_paragraph("3. State the primary goal of the Single Responsibility Principle (SRP) in SOLID. [4 Marks]")

    # Section B
    doc.add_heading("SECTION B - Architecture & Problem Solving", level=1)
    doc.add_paragraph("4. Analyze the risk matrix for migrating a monolithic legacy application to microservices. [10 Marks]")
    doc.add_paragraph("5. Design an event-driven publish-subscribe architecture using Apache Kafka for real-time telemetry. [10 Marks]")

    doc.save(filepath)
    print(f"[CREATED] {filepath}")


def generate_empty_scanned_pdf():
    filepath = os.path.join(FIXTURES_DIR, "scanned_empty.pdf")
    doc = SimpleDocTemplate(filepath, pagesize=letter)
    story = [
        # Blank canvas without any text flowables
        Spacer(1, 500)
    ]
    doc.build(story)
    print(f"[CREATED] {filepath}")


if __name__ == "__main__":
    os.makedirs(FIXTURES_DIR, exist_ok=True)
    generate_pdf_exam()
    generate_docx_exam()
    generate_empty_scanned_pdf()
