"""Research Feature Ablation Study and Qualitative Error Analysis.

Systematically investigates the marginal contribution of:
1. Lexical Representation (TF-IDF N-grams).
2. Readability & Structural Metrics (Flesch, Dale-Chall, word length).
3. Syntactic & Cognitive Action Verb Indicators.
4. Subject / Curriculum Domain Metadata.
5. Examination Marks (Target Leakage Analysis).

Also executes granular error analysis on held-out test predictions.
All outputs are serialized to research/experiments/ablation_and_error_analysis.json.
"""

import json
import os
import sys
from typing import Dict, Any, List
import numpy as np
import pandas as pd

from sklearn.compose import ColumnTransformer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.metrics import accuracy_score, f1_score, classification_report, confusion_matrix

# Ensure workspace root in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from research.preprocessing import extract_linguistic_features, clean_question_text

TRAIN_PATH = "data/processed/train.csv"
VAL_PATH = "data/processed/val.csv"
TEST_PATH = "data/processed/test.csv"
OUTPUT_EXPERIMENT_PATH = "research/experiments/ablation_and_error_analysis.json"


def prepare_feature_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Enrich dataframe with extracted linguistic and structural features."""
    df_out = df.copy()
    feature_rows = []
    for text in df_out["cleaned_question_text"]:
        feat = extract_linguistic_features(text)
        feature_rows.append(feat)

    feat_df = pd.DataFrame(feature_rows)
    for col in feat_df.columns:
        df_out[col] = feat_df[col].values

    return df_out


def build_pipeline(
    include_text: bool = True,
    include_readability: bool = False,
    include_syntax: bool = False,
    include_subject: bool = False,
    include_marks: bool = False,
) -> Pipeline:
    """Build a composable ColumnTransformer pipeline based on active ablation features."""
    transformers = []

    if include_text:
        transformers.append(
            ("tfidf", TfidfVectorizer(ngram_range=(1, 2), max_features=2500, sublinear_tf=True), "cleaned_question_text")
        )

    readability_cols = [
        "char_count", "word_count", "avg_word_length",
        "flesch_reading_ease", "flesch_kincaid_grade", "dale_chall_score"
    ]
    if include_readability:
        transformers.append(
            ("readability", StandardScaler(), readability_cols)
        )

    syntax_cols = [
        "has_comparison_cue", "has_justification_cue",
        "first_word_is_remember", "first_word_is_understand", "first_word_is_apply",
        "first_word_is_analyze", "first_word_is_evaluate", "first_word_is_create",
        "count_remember_verbs", "count_understand_verbs", "count_apply_verbs",
        "count_analyze_verbs", "count_evaluate_verbs", "count_create_verbs"
    ]
    if include_syntax:
        transformers.append(
            ("syntax", StandardScaler(), syntax_cols)
        )

    if include_subject:
        transformers.append(
            ("subject", OneHotEncoder(handle_unknown="ignore"), ["subject"])
        )

    if include_marks:
        transformers.append(
            ("marks", StandardScaler(), ["marks"])
        )

    preprocessor = ColumnTransformer(transformers=transformers)
    pipeline = Pipeline([
        ("preprocessor", preprocessor),
        ("clf", LogisticRegression(C=2.0, class_weight="balanced", max_iter=1000, random_state=42))
    ])
    return pipeline


def evaluate_ablation(pipeline, train_df, val_df, test_df, target_col: str, classes: list) -> Dict[str, Any]:
    """Train on train_df, evaluate on val_df and held-out test_df."""
    pipeline.fit(train_df, train_df[target_col])

    # Validation
    y_val = val_df[target_col].values
    y_val_pred = pipeline.predict(val_df)
    val_acc = accuracy_score(y_val, y_val_pred)
    val_macro_f1 = f1_score(y_val, y_val_pred, average="macro", zero_division=0)

    # Test
    y_test = test_df[target_col].values
    y_test_pred = pipeline.predict(test_df)
    test_acc = accuracy_score(y_test, y_test_pred)
    test_macro_f1 = f1_score(y_test, y_test_pred, average="macro", zero_division=0)
    test_weighted_f1 = f1_score(y_test, y_test_pred, average="weighted", zero_division=0)

    report = classification_report(y_test, y_test_pred, target_names=classes, output_dict=True, zero_division=0)

    return {
        "val_accuracy": round(float(val_acc), 4),
        "val_macro_f1": round(float(val_macro_f1), 4),
        "test_accuracy": round(float(test_acc), 4),
        "test_macro_f1": round(float(test_macro_f1), 4),
        "test_weighted_f1": round(float(test_weighted_f1), 4),
        "test_per_class": {
            cls: {
                "precision": round(float(report[cls]["precision"]), 4),
                "recall": round(float(report[cls]["recall"]), 4),
                "f1": round(float(report[cls]["f1-score"]), 4),
            }
            for cls in classes if cls in report
        },
    }


def run_ablations():
    print("================================================================================")
    print("PHASE 6: RESEARCH FEATURE ABLATION & QUALITATIVE ERROR ANALYSIS")
    print("================================================================================")

    train_df = prepare_feature_dataframe(pd.read_csv(TRAIN_PATH))
    val_df = prepare_feature_dataframe(pd.read_csv(VAL_PATH))
    test_df = prepare_feature_dataframe(pd.read_csv(TEST_PATH))

    bloom_classes = ["Remember", "Understand", "Apply", "Analyze", "Evaluate", "Create"]
    diff_classes = ["Easy", "Medium", "Hard"]

    ablation_configs = {
        "Config_1_TFIDF_Lexical_Only": {
            "include_text": True, "include_readability": False, "include_syntax": False,
            "include_subject": False, "include_marks": False,
        },
        "Config_2_TFIDF_Plus_Readability": {
            "include_text": True, "include_readability": True, "include_syntax": False,
            "include_subject": False, "include_marks": False,
        },
        "Config_3_TFIDF_Plus_CognitiveSyntax": {
            "include_text": True, "include_readability": False, "include_syntax": True,
            "include_subject": False, "include_marks": False,
        },
        "Config_4_Full_Hybrid_Ensemble": {
            "include_text": True, "include_readability": True, "include_syntax": True,
            "include_subject": True, "include_marks": False,
        },
        "Config_5_Leakage_Analysis_With_Marks": {
            "include_text": True, "include_readability": True, "include_syntax": True,
            "include_subject": True, "include_marks": True,
        },
    }

    # 1. Run Task A Ablations (Bloom's Taxonomy)
    print("\n--- Task A: Bloom's Taxonomy Feature Ablation ---")
    task_a_results = {}
    for cfg_name, kwargs in ablation_configs.items():
        pipe = build_pipeline(**kwargs)
        res = evaluate_ablation(pipe, train_df, val_df, test_df, "blooms_level", bloom_classes)
        task_a_results[cfg_name] = res
        print(f"  {cfg_name:<38} | Val F1: {res['val_macro_f1']:.4f} | Test F1: {res['test_macro_f1']:.4f} | Test Acc: {res['test_accuracy']:.4f}")

    # 2. Run Task B Ablations (Question Difficulty)
    print("\n--- Task B: Question Difficulty Feature Ablation ---")
    task_b_results = {}
    for cfg_name, kwargs in ablation_configs.items():
        pipe = build_pipeline(**kwargs)
        res = evaluate_ablation(pipe, train_df, val_df, test_df, "difficulty_level", diff_classes)
        task_b_results[cfg_name] = res
        print(f"  {cfg_name:<38} | Val F1: {res['val_macro_f1']:.4f} | Test F1: {res['test_macro_f1']:.4f} | Test Acc: {res['test_accuracy']:.4f}")

    # 3. Qualitative Error Analysis on Held-Out Test Set (Best Production Model)
    print("\n--------------------------------------------------------------------------------")
    print("QUALITATIVE ERROR ANALYSIS (HELD-OUT TEST SET, N=86)")
    print("--------------------------------------------------------------------------------")
    best_pipe_bloom = build_pipeline(include_text=True)
    best_pipe_bloom.fit(train_df, train_df["blooms_level"])
    y_test_pred_bloom = best_pipe_bloom.predict(test_df)

    best_pipe_diff = build_pipeline(include_text=True)
    best_pipe_diff.fit(train_df, train_df["difficulty_level"])
    y_test_pred_diff = best_pipe_diff.predict(test_df)

    misclassified_bloom = []
    misclassified_diff = []

    for idx, row in test_df.reset_index(drop=True).iterrows():
        actual_bloom = row["blooms_level"]
        pred_bloom = y_test_pred_bloom[idx]
        actual_diff = row["difficulty_level"]
        pred_diff = y_test_pred_diff[idx]

        if actual_bloom != pred_bloom:
            misclassified_bloom.append({
                "question_id": row["question_id"],
                "subject": row["subject"],
                "text": row["cleaned_question_text"],
                "actual": actual_bloom,
                "predicted": pred_bloom,
            })

        if actual_diff != pred_diff:
            misclassified_diff.append({
                "question_id": row["question_id"],
                "subject": row["subject"],
                "text": row["cleaned_question_text"],
                "actual": actual_diff,
                "predicted": pred_diff,
            })

    print(f"Bloom's Taxonomy Test Misclassifications: {len(misclassified_bloom)} / {len(test_df)} ({len(misclassified_bloom)/len(test_df)*100:.1f}%)")
    for item in misclassified_bloom[:4]:
        print(f"  - [{item['question_id']}] Actual: {item['actual']:<10} | Pred: {item['predicted']:<10} | Text: \"{item['text'][:70]}...\"")

    print(f"\nQuestion Difficulty Test Misclassifications: {len(misclassified_diff)} / {len(test_df)} ({len(misclassified_diff)/len(test_df)*100:.1f}%)")
    for item in misclassified_diff[:4]:
        print(f"  - [{item['question_id']}] Actual: {item['actual']:<10} | Pred: {item['predicted']:<10} | Text: \"{item['text'][:70]}...\"")

    # Serialize Full Analysis
    output_data = {
        "task_a_blooms_ablation": task_a_results,
        "task_b_difficulty_ablation": task_b_results,
        "error_analysis": {
            "blooms_misclassified_count": len(misclassified_bloom),
            "blooms_misclassified_samples": misclassified_bloom,
            "difficulty_misclassified_count": len(misclassified_diff),
            "difficulty_misclassified_samples": misclassified_diff,
        },
    }

    os.makedirs(os.path.dirname(OUTPUT_EXPERIMENT_PATH), exist_ok=True)
    with open(OUTPUT_EXPERIMENT_PATH, "w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=2)

    print(f"\n[SUCCESS] Ablation and error analysis saved to {OUTPUT_EXPERIMENT_PATH}")
    print("================================================================================")


if __name__ == "__main__":
    run_ablations()
