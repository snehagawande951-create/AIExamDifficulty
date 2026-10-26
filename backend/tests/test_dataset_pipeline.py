"""Automated test suite verifying dataset splits, leakage isolation, and preprocessing."""

import os
import pandas as pd
import pytest
from research.preprocessing import clean_question_text, extract_linguistic_features

TRAIN_PATH = "data/processed/train.csv"
VAL_PATH = "data/processed/val.csv"
TEST_PATH = "data/processed/test.csv"


def test_splits_exist_and_counts_match():
    """Verify that all three partitioned CSV files exist and sum to the total benchmark count."""
    assert os.path.exists(TRAIN_PATH), f"Missing {TRAIN_PATH}"
    assert os.path.exists(VAL_PATH), f"Missing {VAL_PATH}"
    assert os.path.exists(TEST_PATH), f"Missing {TEST_PATH}"

    train_df = pd.read_csv(TRAIN_PATH)
    val_df = pd.read_csv(VAL_PATH)
    test_df = pd.read_csv(TEST_PATH)

    assert len(train_df) == 399
    assert len(val_df) == 85
    assert len(test_df) == 86
    assert len(train_df) + len(val_df) + len(test_df) == 570


def test_zero_leakage_between_splits():
    """Verify zero overlap between Question IDs and cleaned question texts."""
    train_df = pd.read_csv(TRAIN_PATH)
    val_df = pd.read_csv(VAL_PATH)
    test_df = pd.read_csv(TEST_PATH)

    train_ids = set(train_df["question_id"])
    val_ids = set(val_df["question_id"])
    test_ids = set(test_df["question_id"])

    assert len(train_ids.intersection(val_ids)) == 0, "ID leakage between Train and Val"
    assert len(train_ids.intersection(test_ids)) == 0, "ID leakage between Train and Test"
    assert len(val_ids.intersection(test_ids)) == 0, "ID leakage between Val and Test"

    train_texts = set(train_df["cleaned_question_text"])
    test_texts = set(test_df["cleaned_question_text"])
    assert len(train_texts.intersection(test_texts)) == 0, "Cleaned text leakage between Train and Test"


def test_stratification_fidelity():
    """Verify all 6 Bloom levels are represented in Train, Val, and Held-Out Test sets."""
    train_df = pd.read_csv(TRAIN_PATH)
    val_df = pd.read_csv(VAL_PATH)
    test_df = pd.read_csv(TEST_PATH)

    expected_levels = {"Remember", "Understand", "Apply", "Analyze", "Evaluate", "Create"}

    assert set(train_df["blooms_level"]) == expected_levels
    assert set(val_df["blooms_level"]) == expected_levels
    assert set(test_df["blooms_level"]) == expected_levels


def test_preprocessing_strips_marks_and_indices():
    """Verify that trailing marks and leading indices are removed to prevent target leakage."""
    raw_q = "Q1. Define what a deadlock is in an operating system. [10 Marks]"
    cleaned = clean_question_text(raw_q, strip_marks=True, strip_indices=True)
    assert not cleaned.startswith("Q1.")
    assert not cleaned.endswith("[10 Marks]")
    assert cleaned == "Define what a deadlock is in an operating system."

    raw_q2 = "2(a) Explain the Banker's algorithm for deadlock avoidance. (6M)"
    cleaned2 = clean_question_text(raw_q2, strip_marks=True, strip_indices=True)
    assert not cleaned2.startswith("2(a)")
    assert not cleaned2.endswith("(6M)")
    assert cleaned2 == "Explain the Banker's algorithm for deadlock avoidance."


def test_linguistic_feature_extractor():
    """Verify that linguistic feature extraction yields expected keys and non-null metrics."""
    sample_text = "Analyze the asymptotic time and space complexity of Dijkstra's algorithm for dense graphs."
    features = extract_linguistic_features(sample_text)

    assert "word_count" in features
    assert features["word_count"] > 5
    assert "flesch_reading_ease" in features
    assert "first_word_is_analyze" in features
    assert features["first_word_is_analyze"] == 1
    assert features["first_word_is_remember"] == 0
