"""Automated tests for ML Inference Service and model outputs."""

import pytest
from backend.app.services.ml_engine import ml_engine


def test_ml_engine_loaded():
    """Verify that models and metadata are initialized from registry."""
    assert ml_engine.blooms_model is not None
    assert ml_engine.difficulty_model is not None
    assert ml_engine.model_version == "1.0.0"


def test_bloom_prediction_remember():
    """Verify inference on a direct recall question yields Remember."""
    question = "Define an abstract data type (ADT) and state two examples."
    res = ml_engine.predict_bloom(question)

    assert res["blooms_level"] == "Remember"
    assert res["confidence"] > 0.50
    assert "Remember" in res["probabilities"]

    # Verify probability distribution sums to 1.0
    prob_sum = sum(res["probabilities"].values())
    assert pytest.approx(prob_sum, abs=1e-3) == 1.0


def test_bloom_prediction_create():
    """Verify inference on a synthesis/design question yields Create."""
    question = (
        "Design a novel fault-tolerant architecture integrating "
        "distributed stream multiplexing to achieve 99.999% availability."
    )
    res = ml_engine.predict_bloom(question)

    assert res["blooms_level"] == "Create"
    assert res["confidence"] > 0.50
    assert "Create" in res["probabilities"]


def test_difficulty_prediction_easy():
    """Verify difficulty prediction on basic factual question."""
    question = "What is a primary key in a relational database? [2 Marks]"
    res = ml_engine.predict_difficulty(question)

    assert res["difficulty_level"] == "Easy"
    assert res["confidence"] > 0.50
    assert 0.10 <= res["continuous_score"] <= 0.40


def test_difficulty_prediction_hard():
    """Verify difficulty prediction on multi-step complex analysis question."""
    question = (
        "Critique the use of a Fibonacci Heap over a Binary Heap in Prim's algorithm "
        "for dense versus sparse graphs. Justify under which graph density it is superior."
    )
    res = ml_engine.predict_difficulty(question)

    assert res["difficulty_level"] == "Hard"
    assert res["confidence"] > 0.50
    assert 0.65 <= res["continuous_score"] <= 1.0


def test_dual_task_analysis_schema():
    """Verify analyze_question produces complete, schema-compliant outputs."""
    question = "Analyze the time complexity of QuickSort in worst and best cases."
    result = ml_engine.analyze_question(question)

    assert "cleaned_text" in result
    assert "blooms_level" in result
    assert "blooms_confidence" in result
    assert "blooms_probabilities" in result
    assert "difficulty_level" in result
    assert "difficulty_confidence" in result
    assert "difficulty_probabilities" in result
    assert "continuous_difficulty_score" in result
    assert result["model_version"] == "1.0.0"
    assert result["bloom_model_name"] == "TFIDF_LogisticRegression"


def test_batch_analyze_questions():
    """Verify batch inference handles multiple questions without error."""
    questions = [
        "Define deadlock.",
        "Explain virtual memory.",
        "Calculate page faults using FIFO for 3 frames.",
    ]
    results = ml_engine.batch_analyze_questions(questions)
    assert len(results) == 3
    assert all("blooms_level" in r for r in results)
    assert all("difficulty_level" in r for r in results)
