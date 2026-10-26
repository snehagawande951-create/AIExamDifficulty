"""Phase 10: End-to-End System Acceptance Testing across User Lifecycles.

Verifies complete multi-role integration:
1. System readiness & Admin onboarding
2. Faculty paper lifecycle (PDF & DOCX ingestion, parsing, dual-task ML analysis, human-in-the-loop review, analytics, PDF/CSV export)
3. Researcher model benchmarks, feature ablations, and dataset provenance
4. Institutional governance and user deactivation enforcement
"""

import io
import os
import pytest
from fastapi.testclient import TestClient

FIXTURES_DIR = "backend/tests/fixtures"
SAMPLE_PDF = os.path.join(FIXTURES_DIR, "sample_cs_exam.pdf")
SAMPLE_DOCX = os.path.join(FIXTURES_DIR, "sample_se_exam.docx")


# ---------------------------------------------------------------------------
# Role Access Helpers
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def admin_auth(client: TestClient) -> dict:
    res = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@institution.edu", "password": "AdminSecr3t!2026"},
    )
    assert res.status_code == 200
    return {"token": res.json()["access_token"], "user": res.json()["user"]}


@pytest.fixture(scope="module")
def faculty_auth(client: TestClient) -> dict:
    client.post(
        "/api/v1/auth/register",
        json={
            "email": "faculty.e2e@univ.edu",
            "full_name": "Prof. Eleanor Vance",
            "password": "Password123!",
            "role": "TEACHER",
            "institution": "Institute of Engineering",
            "department": "Computer Science",
        },
    )
    res = client.post(
        "/api/v1/auth/login",
        json={"email": "faculty.e2e@univ.edu", "password": "Password123!"},
    )
    assert res.status_code == 200
    return {"token": res.json()["access_token"], "user": res.json()["user"]}


@pytest.fixture(scope="module")
def researcher_auth(client: TestClient) -> dict:
    client.post(
        "/api/v1/auth/register",
        json={
            "email": "researcher.e2e@univ.edu",
            "full_name": "Dr. Ronald Evans",
            "password": "Password123!",
            "role": "RESEARCHER",
            "institution": "Institute of Engineering",
            "department": "NLP & AI Laboratory",
        },
    )
    res = client.post(
        "/api/v1/auth/login",
        json={"email": "researcher.e2e@univ.edu", "password": "Password123!"},
    )
    assert res.status_code == 200
    return {"token": res.json()["access_token"], "user": res.json()["user"]}


# ---------------------------------------------------------------------------
# E2E Acceptance Scenarios
# ---------------------------------------------------------------------------

def test_e2e_01_system_readiness_and_diagnostics(client: TestClient, admin_auth: dict):
    """Scenario 1: Verify system health and admin readiness."""
    health_res = client.get("/api/v1/health")
    assert health_res.status_code == 200
    health_data = health_res.json()
    assert health_data["status"] == "ok"
    assert health_data["database"] == "connected"

    # Admin checks user management
    users_res = client.get(
        "/api/v1/users/",
        headers={"Authorization": f"Bearer {admin_auth['token']}"},
    )
    assert users_res.status_code == 200
    users = users_res.json()
    assert len(users) >= 1
    assert any(u["role"] == "ADMIN" for u in users)


def test_e2e_02_faculty_full_pdf_workflow(client: TestClient, faculty_auth: dict):
    """Scenario 2: Faculty uploads PDF, runs ML inference, reviews predictions, generates reports."""
    headers = {"Authorization": f"Bearer {faculty_auth['token']}"}

    # 1. Upload PDF Examination Paper
    with open(SAMPLE_PDF, "rb") as f:
        pdf_bytes = f.read()

    upload_res = client.post(
        "/api/v1/papers/upload",
        headers=headers,
        data={
            "title": "Algorithms & Data Structures Endterm 2026",
            "subject": "Computer Science",
            "institution": "Institute of Engineering",
            "academic_term": "Spring 2026",
        },
        files={"file": ("sample_cs_exam.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
    )
    assert upload_res.status_code == 201
    paper = upload_res.json()
    paper_id = paper["id"]
    assert paper["title"] == "Algorithms & Data Structures Endterm 2026"
    assert paper["total_questions"] > 0
    assert len(paper["questions"]) > 0

    # 2. Run ML Analysis Orchestration (Dual-Task)
    analyze_res = client.post(f"/api/v1/papers/{paper_id}/analyze", headers=headers)
    assert analyze_res.status_code == 200
    analyzed_paper = analyze_res.json()
    assert analyzed_paper["status"] == "ANALYZED"

    # Verify all questions received valid Bloom's and Difficulty classifications
    valid_blooms = {"REMEMBER", "UNDERSTAND", "APPLY", "ANALYZE", "EVALUATE", "CREATE"}
    valid_diffs = {"EASY", "MEDIUM", "HARD"}

    for q in analyzed_paper["questions"]:
        assert q["predicted_blooms_level"] in valid_blooms
        assert 0.0 <= q["blooms_confidence"] <= 1.0
        assert q["predicted_difficulty"] in valid_diffs
        assert 0.0 <= q["difficulty_confidence"] <= 1.0

    target_q = analyzed_paper["questions"][0]
    target_q_id = target_q["id"]

    # 3. Human-in-the-Loop Review & Teacher Correction
    correction_res = client.patch(
        f"/api/v1/papers/{paper_id}/questions/{target_q_id}",
        headers=headers,
        json={
            "manual_blooms_level": "ANALYZE",
            "manual_difficulty": "HARD",
            "teacher_justification": "Requires comparative algorithmic runtime analysis.",
            "correction_notes": "Upgraded from baseline prediction based on syllabus depth.",
        },
    )
    assert correction_res.status_code == 200
    updated_q = correction_res.json()
    assert updated_q["final_blooms_level"] == "ANALYZE"
    assert updated_q["final_difficulty"] == "HARD"
    assert updated_q["is_human_reviewed"] is True

    # 4. Inquire Paper Analytics & Cognitive Balance
    analytics_res = client.get(f"/api/v1/papers/{paper_id}/analytics", headers=headers)
    assert analytics_res.status_code == 200
    analytics = analytics_res.json()
    assert "blooms_distribution" in analytics
    assert "difficulty_distribution" in analytics
    assert "cognitive_balance_index" in analytics
    assert analytics["total_questions"] == len(analyzed_paper["questions"])

    # 5. Export ReportLab PDF Report
    pdf_res = client.get(f"/api/v1/papers/{paper_id}/export/pdf", headers=headers)
    assert pdf_res.status_code == 200
    assert pdf_res.headers["Content-Type"] == "application/pdf"
    assert "attachment" in pdf_res.headers["Content-Disposition"]
    assert pdf_res.content.startswith(b"%PDF")

    # 6. Export Streaming CSV Report
    csv_res = client.get(f"/api/v1/papers/{paper_id}/export/csv", headers=headers)
    assert csv_res.status_code == 200
    assert "text/csv" in csv_res.headers["Content-Type"]
    csv_text = csv_res.content.decode("utf-8")
    assert "Question Number" in csv_text
    assert "Final Bloom Level" in csv_text
    assert "Final Difficulty" in csv_text


def test_e2e_03_faculty_docx_workflow(client: TestClient, faculty_auth: dict):
    """Scenario 3: Faculty uploads Word (.docx) exam paper and processes through ML inference."""
    headers = {"Authorization": f"Bearer {faculty_auth['token']}"}

    with open(SAMPLE_DOCX, "rb") as f:
        docx_bytes = f.read()

    upload_res = client.post(
        "/api/v1/papers/upload",
        headers=headers,
        data={
            "title": "Software Engineering Design Finals",
            "subject": "Software Engineering",
            "institution": "Institute of Engineering",
            "academic_term": "Spring 2026",
        },
        files={"file": ("sample_se_exam.docx", io.BytesIO(docx_bytes), "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
    )
    assert upload_res.status_code == 201
    paper = upload_res.json()
    paper_id = paper["id"]
    assert paper["total_questions"] > 0

    # Execute ML batch analysis
    analyze_res = client.post(f"/api/v1/papers/{paper_id}/analyze", headers=headers)
    assert analyze_res.status_code == 200
    analyzed = analyze_res.json()
    assert analyzed["status"] == "ANALYZED"


def test_e2e_04_researcher_benchmarking_portal(client: TestClient, researcher_auth: dict):
    """Scenario 4: Researcher accesses model benchmarks, ablations, and dataset distributions."""
    headers = {"Authorization": f"Bearer {researcher_auth['token']}"}

    # Model performance & registry
    metrics_res = client.get("/api/v1/research/metrics", headers=headers)
    assert metrics_res.status_code == 200
    metrics_data = metrics_res.json()
    assert "metadata" in metrics_data
    assert "task_a_blooms" in metrics_data
    assert "task_b_difficulty" in metrics_data

    # Ablation studies
    ablations_res = client.get("/api/v1/research/ablations", headers=headers)
    assert ablations_res.status_code == 200
    ablations_data = ablations_res.json()
    assert "feature_ablation_runs" in ablations_data
    assert "leakage_analysis" in ablations_data
    assert "error_analysis_cases" in ablations_data

    # Dataset provenance
    dataset_res = client.get("/api/v1/research/dataset", headers=headers)
    assert dataset_res.status_code == 200
    dataset_data = dataset_res.json()
    assert "total_records" in dataset_data
    assert "stratified_splits" in dataset_data


def test_e2e_05_admin_user_lifecycle_governance(client: TestClient, admin_auth: dict):
    """Scenario 5: Admin manages user lifecycle and enforces deactivation bar."""
    admin_headers = {"Authorization": f"Bearer {admin_auth['token']}"}

    # 1. Register a faculty account to test deactivation
    client.post(
        "/api/v1/auth/register",
        json={
            "email": "temp.faculty@univ.edu",
            "full_name": "Temporary Faculty",
            "password": "Password123!",
            "role": "TEACHER",
        },
    )

    # 2. Locate user in admin user list
    users_res = client.get("/api/v1/users/", headers=admin_headers)
    assert users_res.status_code == 200
    target_user = next((u for u in users_res.json() if u["email"] == "temp.faculty@univ.edu"), None)
    assert target_user is not None
    user_id = target_user["id"]

    # 3. Deactivate user
    deactivate_res = client.patch(
        f"/api/v1/users/{user_id}/status",
        headers=admin_headers,
        json={"is_active": False},
    )
    assert deactivate_res.status_code == 200
    assert deactivate_res.json()["is_active"] is False

    # 4. Attempt login with deactivated credentials -> 403 Forbidden
    login_res = client.post(
        "/api/v1/auth/login",
        json={"email": "temp.faculty@univ.edu", "password": "Password123!"},
    )
    assert login_res.status_code == 403
    assert "Account is deactivated" in login_res.json()["detail"]

    # 5. Reactivate user
    reactivate_res = client.patch(
        f"/api/v1/users/{user_id}/status",
        headers=admin_headers,
        json={"is_active": True},
    )
    assert reactivate_res.status_code == 200
    assert reactivate_res.json()["is_active"] is True

    # 6. Verify login succeeds once reactivated
    login_success = client.post(
        "/api/v1/auth/login",
        json={"email": "temp.faculty@univ.edu", "password": "Password123!"},
    )
    assert login_success.status_code == 200
    assert "access_token" in login_success.json()
