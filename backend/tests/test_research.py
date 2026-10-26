"""Automated test suite verifying research and benchmarking API endpoints."""

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def researcher_token(client: TestClient) -> str:
    """Fixture providing an access token for Researcher."""
    client.post(
        "/api/v1/auth/register",
        json={
            "email": "dr.researcher.benchmarks@univ.edu",
            "full_name": "Dr. Researcher",
            "password": "Password123!",
            "role": "RESEARCHER",
            "institution": "Cognitive AI Lab",
            "department": "NLP & Educational Tech",
        },
    )
    res = client.post(
        "/api/v1/auth/login",
        json={"email": "dr.researcher.benchmarks@univ.edu", "password": "Password123!"},
    )
    return res.json()["access_token"]


def test_research_metrics_unauthenticated_rejected(client: TestClient):
    """Verify that unauthenticated requests to research endpoints receive 401 Unauthorized."""
    res = client.get("/api/v1/research/metrics")
    assert res.status_code == 401


def test_research_metrics_endpoint(client: TestClient, researcher_token: str):
    """Verify research metrics returns champion model registry metadata and baseline results."""
    res = client.get(
        "/api/v1/research/metrics",
        headers={"Authorization": f"Bearer {researcher_token}"},
    )
    assert res.status_code == 200
    data = res.json()
    assert "metadata" in data
    assert data["metadata"]["version"] == "1.0.0"
    assert "blooms_champion" in data["metadata"]
    assert "difficulty_champion" in data["metadata"]
    assert data["metadata"]["blooms_test_macro_f1"] > 0.85
    assert data["metadata"]["difficulty_test_macro_f1"] > 0.90
    assert "task_a_blooms" in data
    assert "task_b_difficulty" in data


def test_research_ablations_endpoint(client: TestClient, researcher_token: str):
    """Verify research ablations endpoint returns feature ablation experiment results."""
    res = client.get(
        "/api/v1/research/ablations",
        headers={"Authorization": f"Bearer {researcher_token}"},
    )
    assert res.status_code == 200
    data = res.json()
    assert "task_a_blooms_ablation" in data
    assert "Config_1_TFIDF_Lexical_Only" in data["task_a_blooms_ablation"]
    assert "Config_2_TFIDF_Plus_Readability" in data["task_a_blooms_ablation"]


def test_research_dataset_endpoint(client: TestClient, researcher_token: str):
    """Verify dataset provenance endpoint returns benchmark distributions."""
    res = client.get(
        "/api/v1/research/dataset",
        headers={"Authorization": f"Bearer {researcher_token}"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["total_records"] == 570
    assert "blooms_distribution" in data
    assert "difficulty_distribution" in data
    assert "subject_distribution" in data
