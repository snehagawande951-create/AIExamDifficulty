"""Empirical Dataset Audit and Statistical Profiler.

Analyzes question paper benchmarks for:
1. Record counts, missing values, and column integrity.
2. Cognitive class distribution (Bloom's Taxonomy).
3. Question difficulty distribution and continuous scores.
4. Cross-tabulation between Bloom's levels and difficulty tiers (verifying orthogonality).
5. Subject and marks distribution.
6. Duplication and near-duplicate detection (Exact & Jaccard token similarity).
7. Imbalance ratio calculation.
"""

import json
import os
import sys
import pandas as pd
import numpy as np

DATASET_PATH = "data/processed/exam_questions_benchmark.csv"
OUTPUT_REPORT_PATH = "data/interim/dataset_audit_report.json"


def jaccard_similarity(str1: str, str2: str) -> float:
    """Calculate token-level Jaccard similarity between two texts."""
    a = set(str1.lower().split())
    b = set(str2.lower().split())
    if not a or not b:
        return 0.0
    return len(a.intersection(b)) / len(a.union(b))


def run_audit():
    if not os.path.exists(DATASET_PATH):
        print(f"[ERROR] Dataset not found at {DATASET_PATH}")
        sys.exit(1)

    df = pd.read_csv(DATASET_PATH)
    total_records = len(df)
    print(f"================================================================================")
    print(f"EMPIRICAL DATASET AUDIT REPORT: {DATASET_PATH}")
    print(f"================================================================================")
    print(f"Total Question Records : {total_records}")
    print(f"Columns Discovered     : {list(df.columns)}")
    print(f"")

    # 1. Missing Values
    null_counts = df.isnull().sum().to_dict()
    print("--- 1. Missing Values Analysis ---")
    for col, count in null_counts.items():
        pct = (count / total_records) * 100
        print(f"  {col:<30}: {count} missing ({pct:.2f}%)")
    print("")

    # 2. Bloom's Taxonomy Distribution
    print("--- 2. Bloom's Taxonomy Distribution (6 Cognitive Levels) ---")
    bloom_counts = df["blooms_level"].value_counts().to_dict()
    bloom_order = ["Remember", "Understand", "Apply", "Analyze", "Evaluate", "Create"]
    for level in bloom_order:
        count = bloom_counts.get(level, 0)
        pct = (count / total_records) * 100
        print(f"  {level:<15}: {count:>4} questions ({pct:>5.2f}%)")
    
    bloom_max = max(bloom_counts.values())
    bloom_min = min(bloom_counts.values())
    bloom_ir = bloom_max / bloom_min if bloom_min > 0 else float("inf")
    print(f"  Imbalance Ratio (Max/Min): {bloom_ir:.2f}")
    print("")

    # 3. Question Difficulty Distribution
    print("--- 3. Difficulty Level Distribution (3 Tiers) ---")
    diff_counts = df["difficulty_level"].value_counts().to_dict()
    diff_order = ["Easy", "Medium", "Hard"]
    for diff in diff_order:
        count = diff_counts.get(diff, 0)
        pct = (count / total_records) * 100
        print(f"  {diff:<15}: {count:>4} questions ({pct:>5.2f}%)")

    diff_max = max(diff_counts.values())
    diff_min = min(diff_counts.values())
    diff_ir = diff_max / diff_min if diff_min > 0 else float("inf")
    print(f"  Imbalance Ratio (Max/Min): {diff_ir:.2f}")
    print("")

    # 4. Cross-Tabulation: Bloom's vs Difficulty (Testing Independence)
    print("--- 4. Cross-Tabulation: Bloom's Level vs Difficulty Tier ---")
    cross_tab = pd.crosstab(df["blooms_level"], df["difficulty_level"])
    print(cross_tab.to_string())
    print("")

    # 5. Domain / Subject Distribution
    print("--- 5. Subject / Domain Coverage ---")
    subject_counts = df["subject"].value_counts().to_dict()
    for sub, count in subject_counts.items():
        pct = (count / total_records) * 100
        print(f"  {sub:<30}: {count:>4} questions ({pct:>5.2f}%)")
    print("")

    # 6. Marks Statistics
    print("--- 6. Examination Marks Statistics ---")
    marks_summary = df["marks"].describe().to_dict()
    print(f"  Mean Marks : {marks_summary['mean']:.2f} (Std: {marks_summary['std']:.2f})")
    print(f"  Min Marks  : {marks_summary['min']:.1f}")
    print(f"  Median     : {marks_summary['50%']:.1f}")
    print(f"  Max Marks  : {marks_summary['max']:.1f}")
    print("")

    # 7. Duplication & Near-Duplicate Analysis
    print("--- 7. Text Duplicate & Near-Duplicate Analysis ---")
    exact_duplicates = df.duplicated(subset=["question_text"]).sum()
    print(f"  Exact Duplicate Question Texts: {exact_duplicates}")

    # Sample pairwise near-duplicate check (Jaccard > 0.85)
    questions = df["question_text"].tolist()
    near_duplicates = []
    n = min(len(questions), 300)  # Check first 300 for efficiency
    for i in range(n):
        for j in range(i + 1, n):
            sim = jaccard_similarity(questions[i], questions[j])
            if sim >= 0.85:
                near_duplicates.append((i, j, sim, questions[i][:60], questions[j][:60]))

    print(f"  Near-Duplicates Detected (Jaccard >= 0.85 on sample): {len(near_duplicates)}")
    if near_duplicates:
        for nd in near_duplicates[:3]:
            print(f"    - Sim {nd[2]:.2f}: '{nd[3]}...' vs '{nd[4]}...'")
    print("")

    # Export structured JSON report
    os.makedirs(os.path.dirname(OUTPUT_REPORT_PATH), exist_ok=True)
    report = {
        "dataset_path": DATASET_PATH,
        "total_records": total_records,
        "null_counts": null_counts,
        "blooms_distribution": bloom_counts,
        "blooms_imbalance_ratio": round(bloom_ir, 2),
        "difficulty_distribution": diff_counts,
        "difficulty_imbalance_ratio": round(diff_ir, 2),
        "subject_distribution": subject_counts,
        "exact_duplicates": int(exact_duplicates),
        "near_duplicates_sample_count": len(near_duplicates),
    }
    with open(OUTPUT_REPORT_PATH, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    print(f"[SUCCESS] Audit report serialized to {OUTPUT_REPORT_PATH}")
    print("================================================================================")


if __name__ == "__main__":
    run_audit()
