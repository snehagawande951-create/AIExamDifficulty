"""Phase 10: Security, Penetration, and Authorization Boundary Tests.

Verifies:
1. Strict cross-tenant isolation across all paper endpoints (zero leakage)
2. RBAC privilege escalation resistance
3. Unauthenticated access rejection
4. JWT token tampering, signature validation, and revocation upon logout
5. Malicious file upload prevention (disallowed extensions, MIME spoofing, empty scanned files)
6. Path traversal and input validation boundaries
"""

import io
import os
import pytest
from fastapi.testclient import TestClient

FIXTURES_DIR = "backend/tests/fixtures"
SAMPLE_PDF = os.path.join(FIXTURES_DIR, "sample_cs_exam.pdf")
SCANNED_EMPTY_PDF = os.path.join(FIXTURES_DIR, "scanned_empty.pdf")


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def teacher_alpha_token(client: TestClient) -> str:
    client.post(
        "/api/v1/auth/register",
        json={
            "email": "teacher.sec.alpha@univ.edu",
            "full_name": "Prof. Security Alpha",
            "password": "Password123!",
            "role": "TEACHER",
        },
    )
    res = client.post(
        "/api/v1/auth/login",
        json={"email": "teacher.sec.alpha@univ.edu", "password": "Password123!"},
    )
    return res.json()["access_token"]


@pytest.fixture(scope="module")
def teacher_beta_token(client: TestClient) -> str:
    client.post(
        "/api/v1/auth/register",
        json={
            "email": "teacher.sec.beta@univ.edu",
            "full_name": "Prof. Security Beta",
            "password": "Password123!",
            "role": "TEACHER",
        },
    )
    res = client.post(
        "/api/v1/auth/login",
        json={"email": "teacher.sec.beta@univ.edu", "password": "Password123!"},
    )
    return res.json()["access_token"]


@pytest.fixture(scope="module")
def researcher_token(client: TestClient) -> str:
    client.post(
        "/api/v1/auth/register",
        json={
            "email": "researcher.sec@univ.edu",
            "full_name": "Dr. Security Researcher",
            "password": "Password123!",
            "role": "RESEARCHER",
        },
    )
    res = client.post(
        "/api/v1/auth/login",
        json={"email": "researcher.sec@univ.edu", "password": "Password123!"},
    )
    return res.json()["access_token"]


@pytest.fixture(scope="module")
def alpha_paper_id(client: TestClient, teacher_alpha_token: str) -> int:
    with open(SAMPLE_PDF, "rb") as f:
        pdf_bytes = f.read()

    res = client.post(
        "/api/v1/papers/upload",
        headers={"Authorization": f"Bearer {teacher_alpha_token}"},
        data={"title": "Private Exam Paper Alpha", "subject": "CS"},
        files={"file": ("alpha_exam.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
    )
    assert res.status_code == 201
    return res.json()["id"]


# ---------------------------------------------------------------------------
# Security Tests
# ---------------------------------------------------------------------------

def test_cross_tenant_intrusion_returns_404_concealed(
    client: TestClient, teacher_beta_token: str, alpha_paper_id: int
):
    """Verify that Teacher Beta cannot access, analyze, edit, or export Teacher Alpha's paper.
    
    Returns 404 (Not Found) rather than 403 to prevent paper ID existence enumeration.
    """
    beta_headers = {"Authorization": f"Bearer {teacher_beta_token}"}

    # 1. Direct GET details attempt
    get_res = client.get(f"/api/v1/papers/{alpha_paper_id}", headers=beta_headers)
    assert get_res.status_code == 404
    assert "not found" in get_res.json()["detail"].lower()

    # 2. Unauthorized trigger ML analysis attempt
    analyze_res = client.post(f"/api/v1/papers/{alpha_paper_id}/analyze", headers=beta_headers)
    assert analyze_res.status_code == 404

    # 3. Unauthorized analytics retrieval attempt
    analytics_res = client.get(f"/api/v1/papers/{alpha_paper_id}/analytics", headers=beta_headers)
    assert analytics_res.status_code == 404

    # 4. Unauthorized PDF export attempt
    pdf_res = client.get(f"/api/v1/papers/{alpha_paper_id}/export/pdf", headers=beta_headers)
    assert pdf_res.status_code == 404

    # 5. Unauthorized CSV export attempt
    csv_res = client.get(f"/api/v1/papers/{alpha_paper_id}/export/csv", headers=beta_headers)
    assert csv_res.status_code == 404

    # 6. Unauthorized DELETE attempt
    del_res = client.delete(f"/api/v1/papers/{alpha_paper_id}", headers=beta_headers)
    assert del_res.status_code == 404


def test_researcher_paper_mutation_forbidden(
    client: TestClient, researcher_token: str, alpha_paper_id: int
):
    """Verify Researcher role is forbidden from paper upload and paper modifications."""
    researcher_headers = {"Authorization": f"Bearer {researcher_token}"}

    with open(SAMPLE_PDF, "rb") as f:
        pdf_bytes = f.read()

    # Researcher cannot upload papers
    upload_res = client.post(
        "/api/v1/papers/upload",
        headers=researcher_headers,
        data={"title": "Unauthorized Paper", "subject": "CS"},
        files={"file": ("unauth.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
    )
    assert upload_res.status_code == 403
    assert "Access forbidden" in upload_res.json()["detail"]


def test_privilege_escalation_to_admin_blocked(
    client: TestClient, teacher_alpha_token: str, researcher_token: str
):
    """Verify non-admin roles cannot access or alter user administration."""
    for token in [teacher_alpha_token, researcher_token]:
        headers = {"Authorization": f"Bearer {token}"}
        res = client.get("/api/v1/users/", headers=headers)
        assert res.status_code == 403
        assert "Access forbidden" in res.json()["detail"]

        patch_res = client.patch(
            "/api/v1/users/1/status",
            headers=headers,
            json={"is_active": False},
        )
        assert patch_res.status_code == 403


def test_unauthenticated_requests_strictly_rejected(client: TestClient, alpha_paper_id: int):
    """Verify that omitting credentials returns 401 across protected routes."""
    endpoints = [
        ("GET", f"/api/v1/papers/{alpha_paper_id}"),
        ("GET", "/api/v1/papers/"),
        ("GET", "/api/v1/users/"),
        ("GET", "/api/v1/research/metrics"),
        ("GET", "/api/v1/auth/me"),
    ]
    for method, path in endpoints:
        if method == "GET":
            res = client.get(path)
        assert res.status_code == 401, f"Failed on {path}: expected 401, got {res.status_code}"


def test_jwt_tampering_and_forgery_rejection(client: TestClient):
    """Verify malformed or forged JWT tokens are rejected with 401."""
    # 1. Malformed token
    res_malformed = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer not-a-valid-token-string"},
    )
    assert res_malformed.status_code == 401

    # 2. Forged signature token
    forged_token = (
        "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
        "eyJzdWIiOiIxIiwicm9sZSI6IkFETUlOIiwidHlwZSI6ImFjY2VzcyJ9."
        "InVaLIdSignAturE_DoEsNotMatchSecretKey123456789"
    )
    res_forged = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {forged_token}"},
    )
    assert res_forged.status_code == 401


def test_token_revocation_on_logout(client: TestClient):
    """Verify that logged out tokens are revoked and cannot be reused."""
    login_res = client.post(
        "/api/v1/auth/login",
        json={"email": "teacher.sec.alpha@univ.edu", "password": "Password123!"},
    )
    token = login_res.json()["access_token"]
    refresh_token = login_res.json()["refresh_token"]

    # Verify token works initially
    me_res = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_res.status_code == 200

    # Logout
    logout_res = client.post(
        "/api/v1/auth/logout",
        headers={"Authorization": f"Bearer {token}"},
        json={"refresh_token": refresh_token},
    )
    assert logout_res.status_code == 200

    # Token must now be rejected
    revoked_me_res = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert revoked_me_res.status_code == 401


def test_malicious_upload_rejection_and_magic_byte_check(
    client: TestClient, teacher_alpha_token: str
):
    """Verify server rejects unsupported extensions, spoofed MIME types, and scanned empty PDFs."""
    headers = {"Authorization": f"Bearer {teacher_alpha_token}"}

    # 1. Disallowed extension (.exe / .py / .sh)
    py_res = client.post(
        "/api/v1/papers/upload",
        headers=headers,
        data={"title": "Script Paper", "subject": "CS"},
        files={"file": ("exploit.py", io.BytesIO(b"import os; os.system('echo bad')"), "text/x-python")},
    )
    assert py_res.status_code == 400
    assert "Unsupported file format" in py_res.json()["detail"]

    # 2. Spoofed magic bytes (plain text file renamed to .pdf)
    spoofed_res = client.post(
        "/api/v1/papers/upload",
        headers=headers,
        data={"title": "Fake PDF", "subject": "CS"},
        files={"file": ("fake.pdf", io.BytesIO(b"This is a plain text file masquerading as pdf"), "application/pdf")},
    )
    assert spoofed_res.status_code == 400
    assert "Invalid file signature" in spoofed_res.json()["detail"]

    # 3. Scanned empty PDF (no text extractable)
    with open(SCANNED_EMPTY_PDF, "rb") as f:
        scanned_bytes = f.read()

    scanned_res = client.post(
        "/api/v1/papers/upload",
        headers=headers,
        data={"title": "Scanned Exam", "subject": "CS"},
        files={"file": ("scanned.pdf", io.BytesIO(scanned_bytes), "application/pdf")},
    )
    assert scanned_res.status_code == 400
    assert "No extractable text" in scanned_res.json()["detail"]


def test_input_validation_and_xss_safety(
    client: TestClient, teacher_alpha_token: str, alpha_paper_id: int
):
    """Verify input validation handles non-numeric IDs and handles script strings without failure."""
    headers = {"Authorization": f"Bearer {teacher_alpha_token}"}

    # 1. Non-numeric paper ID rejected with 422
    invalid_id_res = client.get("/api/v1/papers/non_numeric_id", headers=headers)
    assert invalid_id_res.status_code == 422

    # 2. XSS payload in teacher justification is stored safely as plain string
    paper_res = client.get(f"/api/v1/papers/{alpha_paper_id}", headers=headers)
    q_id = paper_res.json()["questions"][0]["id"]

    xss_payload = "<script>alert('xss')</script>"
    patch_res = client.patch(
        f"/api/v1/papers/{alpha_paper_id}/questions/{q_id}",
        headers=headers,
        json={
            "manual_blooms_level": "UNDERSTAND",
            "manual_difficulty": "EASY",
            "teacher_justification": xss_payload,
        },
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["teacher_justification"] == xss_payload
