"""Research Baseline Training, Model Selection, and Rigorous Evaluation Pipeline.

Trains and benchmarks multiple candidate models across:
- Task A: Revised Bloom's Taxonomy (6 Classes: Remember, Understand, Apply, Analyze, Evaluate, Create)
- Task B: Question Difficulty (3 Classes: Easy, Medium, Hard)

Protocol:
1. Train candidates on train.csv (399 records).
2. Validate and compare candidates on val.csv (85 records) using Macro-F1.
3. Evaluate best selected champion on held-out test.csv (86 records).
4. Compute per-class Precision, Recall, F1, Confusion Matrices, and probability calibrations.
5. Serialize genuine evaluation results to research/experiments/baseline_experiment_results.json.
6. Export champion artifacts to models/registry/v1.0.0/ for backend inference.
"""

import json
import os
import sys
import joblib
import numpy as np
import pandas as pd
from typing import Dict, Any, Tuple

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.svm import LinearSVC
from sklearn.calibration import CalibratedClassifierCV
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score,
    f1_score,
    precision_score,
    recall_score,
    classification_report,
    confusion_matrix,
)
from sklearn.pipeline import Pipeline

# Ensure workspace root in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from research.preprocessing import BLOOM_ACTION_VERBS, clean_question_text

TRAIN_PATH = "data/processed/train.csv"
VAL_PATH = "data/processed/val.csv"
TEST_PATH = "data/processed/test.csv"
EXPERIMENTS_DIR = "research/experiments"
REGISTRY_DIR = "models/registry/v1.0.0"


class RuleBasedBloomClassifier:
    """Action verb heuristic baseline for Bloom's Taxonomy."""

    def __init__(self):
        self.classes_ = np.array([
            "Remember", "Understand", "Apply", "Analyze", "Evaluate", "Create"
        ])
        self.verb_map = {}
        for level, verbs in BLOOM_ACTION_VERBS.items():
            for v in verbs:
                self.verb_map[v] = level.capitalize()

    def fit(self, X, y):
        return self

    def predict(self, X) -> np.ndarray:
        preds = []
        for text in X:
            words = text.lower().split()
            found = "Understand"  # Default fallback
            for w in words:
                clean_w = w.strip(".,:;?'\"()")
                if clean_w in self.verb_map:
                    found = self.verb_map[clean_w]
                    break
            preds.append(found)
        return np.array(preds)

    def predict_proba(self, X) -> np.ndarray:
        preds = self.predict(X)
        probas = []
        for p in preds:
            row = [0.1] * len(self.classes_)
            idx = list(self.classes_).index(p)
            row[idx] = 0.5
            total = sum(row)
            probas.append([r / total for r in row])
        return np.array(probas)


def evaluate_model(
    model, X, y, target_names: list
) -> Dict[str, Any]:
    """Calculate comprehensive evaluation metrics."""
    y_pred = model.predict(X)
    acc = accuracy_score(y, y_pred)
    macro_f1 = f1_score(y, y_pred, average="macro", zero_division=0)
    weighted_f1 = f1_score(y, y_pred, average="weighted", zero_division=0)
    
    report = classification_report(
        y, y_pred, target_names=target_names, output_dict=True, zero_division=0
    )
    cm = confusion_matrix(y, y_pred, labels=target_names).tolist()

    return {
        "accuracy": round(float(acc), 4),
        "macro_f1": round(float(macro_f1), 4),
        "weighted_f1": round(float(weighted_f1), 4),
        "per_class": {
            cls: {
                "precision": round(float(report[cls]["precision"]), 4),
                "recall": round(float(report[cls]["recall"]), 4),
                "f1": round(float(report[cls]["f1-score"]), 4),
                "support": int(report[cls]["support"]),
            }
            for cls in target_names if cls in report
        },
        "confusion_matrix": cm,
        "labels": target_names,
    }


def run_baseline_experiments():
    os.makedirs(EXPERIMENTS_DIR, exist_ok=True)
    os.makedirs(REGISTRY_DIR, exist_ok=True)

    print("================================================================================")
    print("PHASE 5: NLP BASELINE TRAINING AND RESEARCH EVALUATION")
    print("================================================================================")

    # 1. Load Data
    train_df = pd.read_csv(TRAIN_PATH)
    val_df = pd.read_csv(VAL_PATH)
    test_df = pd.read_csv(TEST_PATH)

    X_train = train_df["cleaned_question_text"].values
    X_val = val_df["cleaned_question_text"].values
    X_test = test_df["cleaned_question_text"].values

    y_train_bloom = train_df["blooms_level"].values
    y_val_bloom = val_df["blooms_level"].values
    y_test_bloom = test_df["blooms_level"].values

    y_train_diff = train_df["difficulty_level"].values
    y_val_diff = val_df["difficulty_level"].values
    y_test_diff = test_df["difficulty_level"].values

    bloom_classes = ["Remember", "Understand", "Apply", "Analyze", "Evaluate", "Create"]
    diff_classes = ["Easy", "Medium", "Hard"]

    print(f"Dataset partitions loaded: Train={len(train_df)}, Val={len(val_df)}, Test={len(test_df)}")

    # -------------------------------------------------------------------------
    # Task A: Bloom's Taxonomy Classification
    # -------------------------------------------------------------------------
    print("\n--------------------------------------------------------------------------------")
    print("TASK A: BLOOM'S TAXONOMY CLASSIFICATION (6 CLASSES)")
    print("--------------------------------------------------------------------------------")

    bloom_candidates = {
        "Rule_Based_Heuristic": RuleBasedBloomClassifier(),
        "TFIDF_LogisticRegression": Pipeline([
            ("tfidf", TfidfVectorizer(ngram_range=(1, 2), max_features=2500, sublinear_tf=True)),
            ("clf", LogisticRegression(C=2.0, class_weight="balanced", max_iter=1000, random_state=42)),
        ]),
        "TFIDF_Calibrated_LinearSVM": Pipeline([
            ("tfidf", TfidfVectorizer(ngram_range=(1, 2), max_features=2500, sublinear_tf=True)),
            ("clf", CalibratedClassifierCV(
                LinearSVC(C=1.0, class_weight="balanced", random_state=42, dual=True),
                cv=3
            )),
        ]),
        "TFIDF_RandomForest": Pipeline([
            ("tfidf", TfidfVectorizer(ngram_range=(1, 2), max_features=1500)),
            ("clf", RandomForestClassifier(n_estimators=150, class_weight="balanced", random_state=42)),
        ]),
    }

    bloom_val_results = {}
    for name, model in bloom_candidates.items():
        model.fit(X_train, y_train_bloom)
        metrics = evaluate_model(model, X_val, y_val_bloom, bloom_classes)
        bloom_val_results[name] = metrics
        print(f"  {name:<30} | Val Acc: {metrics['accuracy']:.4f} | Val Macro-F1: {metrics['macro_f1']:.4f}")

    # Select best ML model for Task A (prioritizing statistical models with calibrated probabilities)
    ml_bloom_candidates = {k: v for k, v in bloom_val_results.items() if k != "Rule_Based_Heuristic"}
    best_bloom_name = max(ml_bloom_candidates, key=lambda k: ml_bloom_candidates[k]["macro_f1"])
    best_bloom_model = bloom_candidates[best_bloom_name]
    print(f"\n>> Selected Statistical ML Champion for Bloom's Taxonomy: {best_bloom_name}")

    # Final held-out test evaluation for Task A champion
    bloom_test_metrics = evaluate_model(best_bloom_model, X_test, y_test_bloom, bloom_classes)
    print(f"   [HELD-OUT TEST SET] Accuracy: {bloom_test_metrics['accuracy']:.4f} | Macro-F1: {bloom_test_metrics['macro_f1']:.4f}")

    # -------------------------------------------------------------------------
    # Task B: Question Difficulty Classification
    # -------------------------------------------------------------------------
    print("\n--------------------------------------------------------------------------------")
    print("TASK B: QUESTION DIFFICULTY CLASSIFICATION (3 CLASSES)")
    print("--------------------------------------------------------------------------------")

    diff_candidates = {
        "TFIDF_LogisticRegression": Pipeline([
            ("tfidf", TfidfVectorizer(ngram_range=(1, 2), max_features=2500, sublinear_tf=True)),
            ("clf", LogisticRegression(C=1.5, class_weight="balanced", max_iter=1000, random_state=42)),
        ]),
        "TFIDF_Calibrated_LinearSVM": Pipeline([
            ("tfidf", TfidfVectorizer(ngram_range=(1, 2), max_features=2500, sublinear_tf=True)),
            ("clf", CalibratedClassifierCV(
                LinearSVC(C=1.0, class_weight="balanced", random_state=42, dual=True),
                cv=3
            )),
        ]),
        "TFIDF_RandomForest": Pipeline([
            ("tfidf", TfidfVectorizer(ngram_range=(1, 2), max_features=1500)),
            ("clf", RandomForestClassifier(n_estimators=150, class_weight="balanced", random_state=42)),
        ]),
    }

    diff_val_results = {}
    for name, model in diff_candidates.items():
        model.fit(X_train, y_train_diff)
        metrics = evaluate_model(model, X_val, y_val_diff, diff_classes)
        diff_val_results[name] = metrics
        print(f"  {name:<30} | Val Acc: {metrics['accuracy']:.4f} | Val Macro-F1: {metrics['macro_f1']:.4f}")

    best_diff_name = max(diff_val_results, key=lambda k: diff_val_results[k]["macro_f1"])
    best_diff_model = diff_candidates[best_diff_name]
    print(f"\n>> Selected Champion for Question Difficulty: {best_diff_name}")

    # Final held-out test evaluation for Task B champion
    diff_test_metrics = evaluate_model(best_diff_model, X_test, y_test_diff, diff_classes)
    print(f"   [HELD-OUT TEST SET] Accuracy: {diff_test_metrics['accuracy']:.4f} | Macro-F1: {diff_test_metrics['macro_f1']:.4f}")

    # -------------------------------------------------------------------------
    # Serialize Experiment Results
    # -------------------------------------------------------------------------
    experiment_record = {
        "experiment_name": "baseline_model_selection_v1",
        "date": "2026-10-11",
        "task_a_blooms_taxonomy": {
            "validation_results": bloom_val_results,
            "champion_model": best_bloom_name,
            "held_out_test_results": bloom_test_metrics,
        },
        "task_b_question_difficulty": {
            "validation_results": diff_val_results,
            "champion_model": best_diff_name,
            "held_out_test_results": diff_test_metrics,
        },
    }

    exp_file = os.path.join(EXPERIMENTS_DIR, "baseline_experiment_results.json")
    with open(exp_file, "w", encoding="utf-8") as f:
        json.dump(experiment_record, f, indent=2)
    print(f"\n[SAVED] Research evaluation logged to {exp_file}")

    # -------------------------------------------------------------------------
    # Save Artifacts to Model Registry
    # -------------------------------------------------------------------------
    bloom_model_path = os.path.join(REGISTRY_DIR, "blooms_model.joblib")
    diff_model_path = os.path.join(REGISTRY_DIR, "difficulty_model.joblib")
    meta_path = os.path.join(REGISTRY_DIR, "model_metadata.json")

    joblib.dump(best_bloom_model, bloom_model_path)
    joblib.dump(best_diff_model, diff_model_path)

    metadata = {
        "version": "1.0.0",
        "model_type": "baseline",
        "blooms_champion": best_bloom_name,
        "difficulty_champion": best_diff_name,
        "blooms_test_accuracy": bloom_test_metrics["accuracy"],
        "blooms_test_macro_f1": bloom_test_metrics["macro_f1"],
        "difficulty_test_accuracy": diff_test_metrics["accuracy"],
        "difficulty_test_macro_f1": diff_test_metrics["macro_f1"],
        "blooms_classes": bloom_classes,
        "difficulty_classes": diff_classes,
        "artifacts": {
            "blooms_model": "blooms_model.joblib",
            "difficulty_model": "difficulty_model.joblib",
        },
    }
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)

    print(f"[SAVED] Champion model artifacts exported to {REGISTRY_DIR}")
    print("================================================================================")


if __name__ == "__main__":
    run_baseline_experiments()
