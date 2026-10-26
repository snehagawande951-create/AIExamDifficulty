"""Automated integration tests for authentication and token lifecycle."""

import pytest
from fastapi.testclient import TestClient


def test_teacher_registration_success(client: TestClient):
    """Verify that a faculty member can self-register with valid details."""
    payload = {
        "email": "prof.sharma@university.edu",
        "full_name": "Dr. Rohit Sharma",
        "password": "StrongPassword123!",
        "role": "TEACHER",
        "institution": "National Institute of Technology",
        "department": "Computer Science & Engineering",
    }
    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == payload["email"]
    assert data["role"] == "TEACHER"
    assert data["is_active"] is True
    assert "hashed_password" not in data


def test_researcher_registration_success(client: TestClient):
    """Verify that an educational researcher can self-register."""
    payload = {
        "email": "dr.alan@researchlab.org",
        "full_name": "Dr. Alan Turing",
        "password": "EnigmaResearch2026!",
        "role": "RESEARCHER",
        "institution": "Cognitive Computing Lab",
        "department": "NLP & AI Research",
    }
    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == payload["email"]
    assert data["role"] == "RESEARCHER"


def test_admin_self_registration_strictly_forbidden(client: TestClient):
    """Verify Section 4.1 rule: Public self-registration for Admin is blocked."""
    payload = {
        "email": "hacker@evil.com",
        "full_name": "Rogue Admin",
        "password": "Password123!",
        "role": "ADMIN",
    }
    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 422  # Pydantic validation error


def test_duplicate_registration_rejected(client: TestClient):
    """Verify that registering with an existing email returns 400 Bad Request."""
    payload = {
        "email": "prof.sharma@university.edu",
        "full_name": "Duplicate Rohit",
        "password": "AnotherPassword123!",
        "role": "TEACHER",
    }
    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 400
    assert "already exists" in response.json()["detail"]


def test_login_success_and_token_response(client: TestClient):
    """Verify login with correct credentials yields access and refresh tokens."""
    payload = {
        "email": "prof.sharma@university.edu",
        "password": "StrongPassword123!",
    }
    response = client.post("/api/v1/auth/login", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == payload["email"]
    assert data["user"]["role"] == "TEACHER"


def test_login_invalid_password(client: TestClient):
    """Verify login fails with wrong password."""
    payload = {
        "email": "prof.sharma@university.edu",
        "password": "WrongPassword!",
    }
    response = client.post("/api/v1/auth/login", json=payload)
    assert response.status_code == 401
    assert "Invalid email or password" in response.json()["detail"]


def test_get_current_user_profile(client: TestClient):
    """Verify /me returns the authenticated user's profile."""
    # 1. Login
    login_res = client.post(
        "/api/v1/auth/login",
        json={"email": "prof.sharma@university.edu", "password": "StrongPassword123!"},
    )
    token = login_res.json()["access_token"]

    # 2. Access /me
    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "prof.sharma@university.edu"
    assert data["role"] == "TEACHER"


def test_token_refresh_and_rotation(client: TestClient):
    """Verify refresh token rotation issues a new token pair and revokes the old one."""
    login_res = client.post(
        "/api/v1/auth/login",
        json={"email": "prof.sharma@university.edu", "password": "StrongPassword123!"},
    )
    refresh_token = login_res.json()["refresh_token"]

    # Refresh
    refresh_res = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert refresh_res.status_code == 200
    new_tokens = refresh_res.json()
    assert "access_token" in new_tokens
    assert "refresh_token" in new_tokens
    assert new_tokens["refresh_token"] != refresh_token

    # Attempting to use the old refresh token must fail (prevent replay attacks)
    replay_res = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert replay_res.status_code == 401


def test_logout_revokes_tokens(client: TestClient):
    """Verify logout revokes user refresh tokens."""
    login_res = client.post(
        "/api/v1/auth/login",
        json={"email": "prof.sharma@university.edu", "password": "StrongPassword123!"},
    )
    access_token = login_res.json()["access_token"]
    refresh_token = login_res.json()["refresh_token"]

    # Logout
    logout_res = client.post(
        "/api/v1/auth/logout",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert logout_res.status_code == 200

    # Refresh attempt with the revoked token must fail
    refresh_res = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert refresh_res.status_code == 401
