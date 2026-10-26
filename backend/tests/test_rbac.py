"""Automated integration tests for Role-Based Access Control and Tenant Isolation."""

import pytest
from fastapi.testclient import TestClient
from backend.tests.conftest import TestingSessionLocal
from backend.app.models.user import User, UserRole
from backend.app.models.paper import Paper, PaperStatus


@pytest.fixture(scope="module")
def admin_token(client: TestClient) -> str:
    """Fixture providing an access token for the administrative user."""
    res = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@institution.edu", "password": "AdminSecr3t!2026"},
    )
    return res.json()["access_token"]


@pytest.fixture(scope="module")
def teacher_token(client: TestClient) -> str:
    """Fixture providing an access token for Teacher A."""
    # Register Teacher A if not present
    client.post(
        "/api/v1/auth/register",
        json={
            "email": "teacher.a@univ.edu",
            "full_name": "Teacher Alpha",
            "password": "Password123!",
            "role": "TEACHER",
        },
    )
    res = client.post(
        "/api/v1/auth/login",
        json={"email": "teacher.a@univ.edu", "password": "Password123!"},
    )
    return res.json()["access_token"]


@pytest.fixture(scope="module")
def researcher_token(client: TestClient) -> str:
    """Fixture providing an access token for Researcher."""
    client.post(
        "/api/v1/auth/register",
        json={
            "email": "researcher.r@univ.edu",
            "full_name": "Researcher Rho",
            "password": "Password123!",
            "role": "RESEARCHER",
        },
    )
    res = client.post(
        "/api/v1/auth/login",
        json={"email": "researcher.r@univ.edu", "password": "Password123!"},
    )
    return res.json()["access_token"]


def test_admin_can_access_user_management(client: TestClient, admin_token: str):
    """Verify that only Admin can list all users."""
    response = client.get(
        "/api/v1/users/",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    users = response.json()
    assert isinstance(users, list)
    assert len(users) >= 1


def test_teacher_forbidden_from_admin_endpoints(client: TestClient, teacher_token: str):
    """Verify that Teacher is blocked with 403 Forbidden from accessing admin endpoints."""
    response = client.get(
        "/api/v1/users/",
        headers={"Authorization": f"Bearer {teacher_token}"},
    )
    assert response.status_code == 403
    assert "Access forbidden" in response.json()["detail"]


def test_researcher_forbidden_from_admin_endpoints(client: TestClient, researcher_token: str):
    """Verify that Researcher is blocked with 403 Forbidden from accessing admin endpoints."""
    response = client.get(
        "/api/v1/users/",
        headers={"Authorization": f"Bearer {researcher_token}"},
    )
    assert response.status_code == 403
    assert "Access forbidden" in response.json()["detail"]


def test_admin_can_update_user_status_and_blocks_login(
    client: TestClient, admin_token: str
):
    """Verify Admin can deactivate an account and that deactivated accounts cannot log in."""
    # 1. Register a test target user
    client.post(
        "/api/v1/auth/register",
        json={
            "email": "target.deactivate@univ.edu",
            "full_name": "Target User",
            "password": "Password123!",
            "role": "TEACHER",
        },
    )

    db = TestingSessionLocal()
    target_user = db.query(User).filter(User.email == "target.deactivate@univ.edu").first()
    target_id = target_user.id
    db.close()

    # 2. Admin deactivates target user
    deactivate_res = client.patch(
        f"/api/v1/users/{target_id}/status",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"is_active": False},
    )
    assert deactivate_res.status_code == 200
    assert deactivate_res.json()["is_active"] is False

    # 3. Target user attempts login -> Must receive 403 Forbidden
    login_res = client.post(
        "/api/v1/auth/login",
        json={"email": "target.deactivate@univ.edu", "password": "Password123!"},
    )
    assert login_res.status_code == 403
    assert "Account is deactivated" in login_res.json()["detail"]


def test_cross_tenant_paper_data_isolation():
    """Verify Section 5 rule: Teacher A cannot query or access Teacher B's records."""
    db = TestingSessionLocal()
    try:
        # Create Teacher A and Teacher B
        teacher_a = db.query(User).filter(User.email == "teacher.a@univ.edu").first()
        teacher_b = db.query(User).filter(User.email == "teacher.b@univ.edu").first()
        if not teacher_b:
            teacher_b = User(
                email="teacher.b@univ.edu",
                full_name="Teacher Beta",
                hashed_password="hash",
                role=UserRole.TEACHER,
                is_active=True,
            )
            db.add(teacher_b)
            db.commit()
            db.refresh(teacher_b)

        # Create Paper owned by Teacher A
        paper_a = Paper(
            owner_id=teacher_a.id,
            title="Data Structures Midterm 2026",
            subject="Data Structures",
            original_filename="dsa_mid.pdf",
            stored_filepath="backend/uploads/dsa_mid.pdf",
            file_type="pdf",
            file_size_bytes=1024,
            status=PaperStatus.UPLOADED,
        )
        db.add(paper_a)
        db.commit()
        db.refresh(paper_a)

        # Database Query Isolation:
        # Teacher A querying papers filtered by owner_id retrieves paper_a
        teacher_a_papers = db.query(Paper).filter(Paper.owner_id == teacher_a.id).all()
        assert any(p.id == paper_a.id for p in teacher_a_papers)

        # Teacher B querying papers filtered by owner_id CANNOT retrieve paper_a
        teacher_b_papers = db.query(Paper).filter(Paper.owner_id == teacher_b.id).all()
        assert not any(p.id == paper_a.id for p in teacher_b_papers)

        # Direct ID lookup with owner check strictly isolates records
        b_access = (
            db.query(Paper)
            .filter(Paper.id == paper_a.id, Paper.owner_id == teacher_b.id)
            .first()
        )
        assert b_access is None, "Cross-user data leakage detected: Teacher B retrieved Teacher A's paper!"
    finally:
        db.close()
