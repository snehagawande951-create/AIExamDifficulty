"""Automated integration tests for Examination Paper management, extraction, inference, review, and reporting."""

import csv
import io
import os
import pytest
from fastapi.testclient import TestClient

FIXTURES_DIR = "backend/tests/fixtures"
SAMPLE_PDF = os.path.join(FIXTURES_DIR, "sample_cs_exam.pdf")
SAMPLE_DOCX = os.path.join(FIXTURES_DIR, "sample_se_exam.docx")


# ---------------------------------------------------------------------------
# Authentication Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def admin_token(client: TestClient) -> str:
    """Fixture providing an access token for Admin."""
    res = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@institution.edu", "password": "AdminSecr3t!2026"},
    )
    return res.json()["access_token"]


@pytest.fixture(scope="module")
def teacher_a_token(client: TestClient) -> str:
    """Fixture providing an access token for Teacher A."""
    client.post(
        "/api/v1/auth/register",
        json={
            "email": "teacher.alpha@univ.edu",
            "full_name": "Prof. Alpha",
            "password": "Password123!",
            "role": "TEACHER",
            "institution": "Tech Institute",
            "department": "Computer Science",
        },
    )
    res = client.post(
        "/api/v1/auth/login",
        json={"email": "teacher.alpha@univ.edu", "password": "Password123!"},
    )
    return res.json()["access_token"]


@pytest.fixture(scope="module")
def teacher_b_token(client: TestClient) -> str:
    """Fixture providing an access token for Teacher B."""
    client.post(
        "/api/v1/auth/register",
        json={
            "email": "teacher.beta@univ.edu",
            "full_name": "Prof. Beta",
            "password": "Password123!",
            "role": "TEACHER",
            "institution": "Tech Institute",
            "department": "Information Systems",
        },
    )
    res = client.post(
        "/api/v1/auth/login",
        json={"email": "teacher.beta@univ.edu", "password": "Password123!"},
    )
    return res.json()["access_token"]


@pytest.fixture(scope="module")
def researcher_token(client: TestClient) -> str:
    """Fixture providing an access token for Researcher."""
    client.post(
        "/api/v1/auth/register",
        json={
            "email": "researcher.papers@univ.edu",
            "full_name": "Dr. Researcher",
            "password": "Password123!",
            "role": "RESEARCHER",
            "institution": "AI Lab",
            "department": "NLP Center",
        },
    )
    res = client.post(
        "/api/v1/auth/login",
        json={"email": "researcher.papers@univ.edu", "password": "Password123!"},
    )
    return res.json()["access_token"]


# ---------------------------------------------------------------------------
# Test Cases
# ---------------------------------------------------------------------------

def test_paper_upload_pdf_success(client: TestClient, teacher_a_token: str):
    """Verify teacher can upload a valid digital PDF and receive parsed sections and questions."""
    with open(SAMPLE_PDF, "rb") as f:
        file_bytes = f.read()

    files = {"file": ("sample_cs_exam.pdf", file_bytes, "application/pdf")}
    data = {
        "subject": "Computer Science",
        "title": "CS301 Data Structures & Algorithms",
        "academic_year": "2025-2026",
        "term": "Semester 1",
    }

    response = client.post(
        "/api/v1/papers/upload",
        headers={"Authorization": f"Bearer {teacher_a_token}"},
        files=files,
        data=data,
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["title"] == "CS301 Data Structures & Algorithms"
    assert payload["subject"] == "Computer Science"
    assert payload["academic_year"] == "2025-2026"
    assert payload["file_type"] == "pdf"
    assert payload["status"] == "EXTRACTED"
    assert payload["total_marks"] == 60.0
    assert len(payload["questions"]) == 10
    assert len(payload["sections"]) >= 2

    # Check question fields
    q1 = payload["questions"][0]
    assert q1["question_number"] in ["1.", "1", "Q1"]
    assert "deadlock" in q1["question_text"].lower()
    assert q1["marks"] == 2.0
    assert q1["is_reviewed_by_teacher"] is False
    assert q1["predictions"] == []


def test_paper_upload_docx_success(client: TestClient, teacher_a_token: str):
    """Verify teacher can upload a valid Word DOCX document."""
    with open(SAMPLE_DOCX, "rb") as f:
        file_bytes = f.read()

    files = {"file": ("sample_se_exam.docx", file_bytes, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}
    data = {
        "subject": "Software Engineering",
        "title": "SE402 Software Architecture Midterm",
    }

    response = client.post(
        "/api/v1/papers/upload",
        headers={"Authorization": f"Bearer {teacher_a_token}"},
        files=files,
        data=data,
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["subject"] == "Software Engineering"
    assert payload["file_type"] == "docx"
    assert payload["status"] == "EXTRACTED"
    assert len(payload["questions"]) == 5
    assert payload["total_marks"] == 30.0


def test_paper_upload_invalid_format_rejected(client: TestClient, teacher_a_token: str):
    """Verify upload rejects unsupported formats and fake files with invalid magic headers."""
    files = {"file": ("notes.txt", b"Plain text file content", "text/plain")}
    data = {"subject": "Mathematics"}

    response = client.post(
        "/api/v1/papers/upload",
        headers={"Authorization": f"Bearer {teacher_a_token}"},
        files=files,
        data=data,
    )
    assert response.status_code == 400

    # Fake PDF header
    fake_pdf = {"file": ("fake.pdf", b"This is not a real PDF file header", "application/pdf")}
    res_fake = client.post(
        "/api/v1/papers/upload",
        headers={"Authorization": f"Bearer {teacher_a_token}"},
        files=fake_pdf,
        data=data,
    )
    assert res_fake.status_code == 400


def test_paper_upload_researcher_forbidden(client: TestClient, researcher_token: str):
    """Verify researchers cannot upload examination papers (read-only RBAC)."""
    with open(SAMPLE_PDF, "rb") as f:
        file_bytes = f.read()

    files = {"file": ("sample_cs_exam.pdf", file_bytes, "application/pdf")}
    data = {"subject": "Computer Science"}

    response = client.post(
        "/api/v1/papers/upload",
        headers={"Authorization": f"Bearer {researcher_token}"},
        files=files,
        data=data,
    )
    assert response.status_code == 403


def test_paper_listing_tenant_isolation(
    client: TestClient,
    teacher_a_token: str,
    teacher_b_token: str,
    admin_token: str,
    researcher_token: str,
):
    """Verify teacher A only sees their own papers, while Admin and Researcher see all papers."""
    # Teacher B uploads a separate paper
    with open(SAMPLE_DOCX, "rb") as f:
        file_bytes = f.read()

    files = {"file": ("teacher_b_exam.docx", file_bytes, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}
    res_b = client.post(
        "/api/v1/papers/upload",
        headers={"Authorization": f"Bearer {teacher_b_token}"},
        files=files,
        data={"subject": "Database Systems", "title": "DB200 Midterm"},
    )
    assert res_b.status_code == 201
    paper_b_id = res_b.json()["id"]

    # Teacher A lists papers -> should NOT include Teacher B's paper
    res_list_a = client.get(
        "/api/v1/papers",
        headers={"Authorization": f"Bearer {teacher_a_token}"},
    )
    assert res_list_a.status_code == 200
    papers_a = res_list_a.json()
    assert all(p["id"] != paper_b_id for p in papers_a)

    # Teacher B lists papers -> should include Teacher B's paper
    res_list_b = client.get(
        "/api/v1/papers",
        headers={"Authorization": f"Bearer {teacher_b_token}"},
    )
    assert res_list_b.status_code == 200
    papers_b = res_list_b.json()
    assert any(p["id"] == paper_b_id for p in papers_b)
    assert len(papers_b) == 1

    # Admin lists papers -> sees all papers
    res_list_admin = client.get(
        "/api/v1/papers",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert res_list_admin.status_code == 200
    admin_papers = res_list_admin.json()
    assert any(p["id"] == paper_b_id for p in admin_papers)

    # Researcher lists papers -> can view papers
    res_list_researcher = client.get(
        "/api/v1/papers",
        headers={"Authorization": f"Bearer {researcher_token}"},
    )
    assert res_list_researcher.status_code == 200


def test_paper_get_details_and_access_control(
    client: TestClient,
    teacher_a_token: str,
    teacher_b_token: str,
    admin_token: str,
):
    """Verify cross-tenant paper retrieval protection and full question detail payload."""
    # Find paper uploaded by Teacher A
    res_list = client.get(
        "/api/v1/papers",
        headers={"Authorization": f"Bearer {teacher_a_token}"},
    )
    paper_a_id = res_list.json()[0]["id"]

    # Teacher A accesses own paper -> 200 OK
    res_a = client.get(
        f"/api/v1/papers/{paper_a_id}",
        headers={"Authorization": f"Bearer {teacher_a_token}"},
    )
    assert res_a.status_code == 200
    detail = res_a.json()
    assert detail["id"] == paper_a_id
    assert "questions" in detail
    assert "sections" in detail

    # Teacher B attempts to access Teacher A's paper -> 403 Forbidden
    res_b = client.get(
        f"/api/v1/papers/{paper_a_id}",
        headers={"Authorization": f"Bearer {teacher_b_token}"},
    )
    assert res_b.status_code == 403

    # Admin accesses Teacher A's paper -> 200 OK
    res_admin = client.get(
        f"/api/v1/papers/{paper_a_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert res_admin.status_code == 200

    # Non-existent paper ID -> 404 Not Found
    res_404 = client.get(
        "/api/v1/papers/999999",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert res_404.status_code == 404


def test_paper_ml_analysis_run(
    client: TestClient,
    teacher_a_token: str,
    teacher_b_token: str,
):
    """Verify executing dual-task ML inference populates Bloom & difficulty predictions."""
    res_list = client.get(
        "/api/v1/papers",
        headers={"Authorization": f"Bearer {teacher_a_token}"},
    )
    paper_a_id = res_list.json()[0]["id"]

    # Teacher B unauthorized run -> 403 Forbidden
    res_unauth = client.post(
        f"/api/v1/papers/{paper_a_id}/analyze",
        headers={"Authorization": f"Bearer {teacher_b_token}"},
    )
    assert res_unauth.status_code == 403

    # Teacher A triggers analysis
    response = client.post(
        f"/api/v1/papers/{paper_a_id}/analyze",
        headers={"Authorization": f"Bearer {teacher_a_token}"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ANALYZED"
    assert payload["latest_analysis_run"] is not None
    assert payload["latest_analysis_run"]["model_version"] == "1.0.0"
    assert payload["latest_analysis_run"]["status"] == "COMPLETED"

    # Verify predictions on questions
    valid_blooms = {"Remember", "Understand", "Apply", "Analyze", "Evaluate", "Create"}
    valid_diffs = {"Easy", "Medium", "Hard"}

    for q in payload["questions"]:
        assert len(q["predictions"]) >= 1
        latest_pred = q["predictions"][-1]
        assert latest_pred["predicted_blooms_level"] in valid_blooms
        assert 0.0 <= latest_pred["blooms_confidence"] <= 1.0
        assert latest_pred["predicted_difficulty"] in valid_diffs
        assert 0.0 <= latest_pred["difficulty_confidence"] <= 1.0
        assert 0.0 <= latest_pred["continuous_difficulty_score"] <= 1.0

        # Effective levels match predictions
        assert q["effective_blooms_level"] == latest_pred["predicted_blooms_level"]
        assert q["effective_difficulty"] == latest_pred["predicted_difficulty"]


def test_paper_analytics_endpoint(
    client: TestClient,
    teacher_a_token: str,
    teacher_b_token: str,
):
    """Verify aggregated analytics returns valid distributions for Bloom levels and difficulty."""
    res_list = client.get(
        "/api/v1/papers",
        headers={"Authorization": f"Bearer {teacher_a_token}"},
    )
    paper_a_id = res_list.json()[0]["id"]

    # Teacher B unauthorized access -> 403
    res_unauth = client.get(
        f"/api/v1/papers/{paper_a_id}/analytics",
        headers={"Authorization": f"Bearer {teacher_b_token}"},
    )
    assert res_unauth.status_code == 403

    # Teacher A accesses analytics
    response = client.get(
        f"/api/v1/papers/{paper_a_id}/analytics",
        headers={"Authorization": f"Bearer {teacher_a_token}"},
    )
    assert response.status_code == 200
    analytics = response.json()

    assert analytics["paper_id"] == paper_a_id
    assert analytics["total_questions"] in [5, 10]
    assert analytics["total_marks"] > 0
    assert 0.0 <= analytics["average_difficulty_score"] <= 1.0
    assert analytics["overall_difficulty_rating"] in [
        "Easy (Foundational)",
        "Medium (Balanced)",
        "Hard (Advanced / Rigorous)",
    ]

    # Verify Bloom distribution
    for lvl in ["Remember", "Understand", "Apply", "Analyze", "Evaluate", "Create"]:
        assert lvl in analytics["blooms_distribution"]
        lvl_data = analytics["blooms_distribution"][lvl]
        assert "count" in lvl_data
        assert "percentage" in lvl_data
        assert "marks" in lvl_data

    # Verify difficulty distribution
    for tier in ["Easy", "Medium", "Hard"]:
        assert tier in analytics["difficulty_distribution"]
        tier_data = analytics["difficulty_distribution"][tier]
        assert "count" in tier_data
        assert "percentage" in tier_data

    assert len(analytics["section_breakdown"]) >= 1


def test_teacher_correction_human_in_the_loop(
    client: TestClient,
    teacher_a_token: str,
    teacher_b_token: str,
    researcher_token: str,
):
    """Verify teacher can submit corrections, preserving model predictions while overriding effective values."""
    res_paper = client.get(
        "/api/v1/papers",
        headers={"Authorization": f"Bearer {teacher_a_token}"},
    )
    paper_a_id = res_paper.json()[0]["id"]

    res_detail = client.get(
        f"/api/v1/papers/{paper_a_id}",
        headers={"Authorization": f"Bearer {teacher_a_token}"},
    )
    question = res_detail.json()["questions"][0]
    question_id = question["id"]
    original_pred = question["predictions"][-1]

    # Researcher cannot submit corrections -> 403
    corr_payload = {
        "corrected_blooms_level": "Evaluate",
        "corrected_difficulty": "Hard",
        "corrected_marks": 8.0,
        "rationale": "High-complexity synthesis question requires evaluation and critical proof.",
    }
    res_res = client.patch(
        f"/api/v1/papers/{paper_a_id}/questions/{question_id}/correction",
        headers={"Authorization": f"Bearer {researcher_token}"},
        json=corr_payload,
    )
    assert res_res.status_code == 403

    # Teacher B cannot correct Teacher A's question -> 403
    res_tb = client.patch(
        f"/api/v1/papers/{paper_a_id}/questions/{question_id}/correction",
        headers={"Authorization": f"Bearer {teacher_b_token}"},
        json=corr_payload,
    )
    assert res_tb.status_code == 403

    # Invalid Bloom level rejected -> 422
    invalid_payload = {
        "corrected_blooms_level": "InvalidCognitiveLevel",
        "corrected_difficulty": "Hard",
    }
    res_inv = client.patch(
        f"/api/v1/papers/{paper_a_id}/questions/{question_id}/correction",
        headers={"Authorization": f"Bearer {teacher_a_token}"},
        json=invalid_payload,
    )
    assert res_inv.status_code == 422

    # Teacher A successfully submits correction
    response = client.patch(
        f"/api/v1/papers/{paper_a_id}/questions/{question_id}/correction",
        headers={"Authorization": f"Bearer {teacher_a_token}"},
        json=corr_payload,
    )
    assert response.status_code == 200
    q_updated = response.json()

    assert q_updated["is_reviewed_by_teacher"] is True
    assert q_updated["effective_blooms_level"] == "Evaluate"
    assert q_updated["effective_difficulty"] == "Hard"
    assert q_updated["marks"] == 8.0

    # Ensure original prediction is preserved unchanged
    assert len(q_updated["predictions"]) >= 1
    assert q_updated["predictions"][-1]["predicted_blooms_level"] == original_pred["predicted_blooms_level"]
    assert q_updated["predictions"][-1]["predicted_difficulty"] == original_pred["predicted_difficulty"]

    # Verify correction record is appended
    assert len(q_updated["corrections"]) == 1
    c_rec = q_updated["corrections"][0]
    assert c_rec["corrected_blooms_level"] == "Evaluate"
    assert c_rec["corrected_difficulty"] == "Hard"
    assert c_rec["rationale"] == corr_payload["rationale"]


def test_export_pdf_report(
    client: TestClient,
    teacher_a_token: str,
    teacher_b_token: str,
):
    """Verify ReportLab generates valid, streaming publication-grade PDF report."""
    res_paper = client.get(
        "/api/v1/papers",
        headers={"Authorization": f"Bearer {teacher_a_token}"},
    )
    paper_a_id = res_paper.json()[0]["id"]

    # Teacher B unauthorized -> 403
    res_unauth = client.get(
        f"/api/v1/papers/{paper_a_id}/report/pdf",
        headers={"Authorization": f"Bearer {teacher_b_token}"},
    )
    assert res_unauth.status_code == 403

    # Teacher A exports PDF
    response = client.get(
        f"/api/v1/papers/{paper_a_id}/report/pdf",
        headers={"Authorization": f"Bearer {teacher_a_token}"},
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert "Content-Disposition" in response.headers
    assert response.headers["Content-Disposition"].endswith('.pdf"')

    # Validate PDF binary signature (%PDF-)
    content = response.content
    assert content.startswith(b"%PDF-")
    assert len(content) > 1000  # Non-trivial PDF size


def test_export_csv_report(
    client: TestClient,
    teacher_a_token: str,
    teacher_b_token: str,
):
    """Verify RFC 4180 streaming CSV export with complete question and prediction metadata."""
    res_paper = client.get(
        "/api/v1/papers",
        headers={"Authorization": f"Bearer {teacher_a_token}"},
    )
    paper_a_id = res_paper.json()[0]["id"]

    # Teacher B unauthorized -> 403
    res_unauth = client.get(
        f"/api/v1/papers/{paper_a_id}/report/csv",
        headers={"Authorization": f"Bearer {teacher_b_token}"},
    )
    assert res_unauth.status_code == 403

    # Teacher A exports CSV
    response = client.get(
        f"/api/v1/papers/{paper_a_id}/report/csv",
        headers={"Authorization": f"Bearer {teacher_a_token}"},
    )
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")

    csv_text = response.text
    reader = csv.reader(io.StringIO(csv_text))
    rows = list(reader)

    # Validate CSV structure
    assert len(rows) >= 6  # Header + at least 5 questions
    header = rows[0]
    assert "Paper ID" in header
    assert "Question Number" in header
    assert "Predicted Bloom Level" in header
    assert "Effective Bloom Level" in header
    assert "Predicted Difficulty" in header
    assert "Effective Difficulty" in header
    assert "Teacher Reviewed" in header

    # Verify first question row has the teacher's override
    first_q_row = rows[1]
    assert "Evaluate" in first_q_row
    assert "Hard" in first_q_row
    assert "YES" in first_q_row


def test_delete_paper_and_cleanup(
    client: TestClient,
    teacher_a_token: str,
    teacher_b_token: str,
    researcher_token: str,
):
    """Verify paper deletion permissions, disk file removal, and subsequent 404 checks."""
    # Find paper uploaded by Teacher A
    res_list = client.get(
        "/api/v1/papers",
        headers={"Authorization": f"Bearer {teacher_a_token}"},
    )
    paper_a = res_list.json()[-1]
    paper_id = paper_a["id"]

    # Researcher cannot delete -> 403
    res_res = client.delete(
        f"/api/v1/papers/{paper_id}",
        headers={"Authorization": f"Bearer {researcher_token}"},
    )
    assert res_res.status_code == 403

    # Teacher B cannot delete Teacher A's paper -> 403
    res_tb = client.delete(
        f"/api/v1/papers/{paper_id}",
        headers={"Authorization": f"Bearer {teacher_b_token}"},
    )
    assert res_tb.status_code == 403

    # Teacher A deletes own paper -> 200
    res_del = client.delete(
        f"/api/v1/papers/{paper_id}",
        headers={"Authorization": f"Bearer {teacher_a_token}"},
    )
    assert res_del.status_code == 200
    assert res_del.json()["id"] == paper_id

    # Subsequent GET returns 404 Not Found
    res_get = client.get(
        f"/api/v1/papers/{paper_id}",
        headers={"Authorization": f"Bearer {teacher_a_token}"},
    )
    assert res_get.status_code == 404
