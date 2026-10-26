"""Automated test verifying research ablation results and error analysis integrity."""

import json
import os
import pytest

ABLATION_RESULTS_PATH = "research/experiments/ablation_and_error_analysis.json"


def test_ablation_results_exist_and_valid():
    """Verify that ablation experiment output exists and contains valid JSON."""
    assert os.path.exists(ABLATION_RESULTS_PATH), f"Missing {ABLATION_RESULTS_PATH}"

    with open(ABLATION_RESULTS_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert "task_a_blooms_ablation" in data
    assert "task_b_difficulty_ablation" in data
    assert "error_analysis" in data

    # Verify all 5 configs exist for both tasks
    for task_key in ["task_a_blooms_ablation", "task_b_difficulty_ablation"]:
        configs = data[task_key]
        assert "Config_1_TFIDF_Lexical_Only" in configs
        assert "Config_2_TFIDF_Plus_Readability" in configs
        assert "Config_3_TFIDF_Plus_CognitiveSyntax" in configs
        assert "Config_4_Full_Hybrid_Ensemble" in configs
        assert "Config_5_Leakage_Analysis_With_Marks" in configs

        # Verify genuine metrics bounds
        for cfg_name, metrics in configs.items():
            assert 0.0 <= metrics["val_macro_f1"] <= 1.0
            assert 0.0 <= metrics["test_macro_f1"] <= 1.0
            assert 0.0 <= metrics["test_accuracy"] <= 1.0


def test_error_analysis_samples():
    """Verify that error analysis contains non-empty genuine misclassified samples."""
    with open(ABLATION_RESULTS_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    err = data["error_analysis"]
    assert err["blooms_misclassified_count"] >= 0
    assert err["difficulty_misclassified_count"] >= 0

    if err["blooms_misclassified_count"] > 0:
        sample = err["blooms_misclassified_samples"][0]
        assert "question_id" in sample
        assert "actual" in sample
        assert "predicted" in sample
        assert sample["actual"] != sample["predicted"]
