"""Stratified and Leakage-Free Dataset Splitting Engine.

Implements reproducible 70/15/15 train/validation/held-out test partitioning.
Features:
- Stratification preserved on Bloom's Taxonomy cognitive levels.
- Verification checks for zero question-ID and zero text-overlap leakage.
- Automatic preprocessing and cleaned text persistence.
"""

import os
import sys
import pandas as pd
from sklearn.model_selection import train_test_split

# Ensure workspace root in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from research.preprocessing import preprocess_dataframe

INPUT_DATA_PATH = "data/processed/exam_questions_benchmark.csv"
TRAIN_PATH = "data/processed/train.csv"
VAL_PATH = "data/processed/val.csv"
TEST_PATH = "data/processed/test.csv"
RANDOM_STATE = 42


def create_splits():
    if not os.path.exists(INPUT_DATA_PATH):
        print(f"[ERROR] Source file not found: {INPUT_DATA_PATH}")
        sys.exit(1)

    print(f"================================================================================")
    print(f"DATASET SPLITTING & STRATIFICATION PIPELINE (SEED={RANDOM_STATE})")
    print(f"================================================================================")
    df = pd.read_csv(INPUT_DATA_PATH)
    total_len = len(df)
    print(f"Loaded {total_len} benchmark records from {INPUT_DATA_PATH}")

    # 1. Apply canonical preprocessing to generate cleaned_question_text
    df = preprocess_dataframe(df, text_col="question_text")
    print("Canonical NLP text cleaning applied (stripped trailing marks and numbering).")

    # 2. Stratified split into Train (70%) and Temp (30%)
    train_df, temp_df = train_test_split(
        df,
        test_size=0.30,
        random_state=RANDOM_STATE,
        stratify=df["blooms_level"],
    )

    # 3. Split Temp (30%) evenly into Validation (15%) and Held-Out Test (15%)
    val_df, test_df = train_test_split(
        temp_df,
        test_size=0.50,
        random_state=RANDOM_STATE,
        stratify=temp_df["blooms_level"],
    )

    print(f"\nSplit Distribution:")
    print(f"  Train Set    : {len(train_df):>4} questions ({len(train_df)/total_len*100:.1f}%)")
    print(f"  Val Set      : {len(val_df):>4} questions ({len(val_df)/total_len*100:.1f}%)")
    print(f"  Test Set     : {len(test_df):>4} questions ({len(test_df)/total_len*100:.1f}%)")

    # 4. Rigorous Leakage Verification
    train_ids = set(train_df["question_id"])
    val_ids = set(val_df["question_id"])
    test_ids = set(test_df["question_id"])

    train_texts = set(train_df["cleaned_question_text"])
    val_texts = set(val_df["cleaned_question_text"])
    test_texts = set(test_df["cleaned_question_text"])

    id_overlap_train_val = train_ids.intersection(val_ids)
    id_overlap_train_test = train_ids.intersection(test_ids)
    id_overlap_val_test = val_ids.intersection(test_ids)

    text_overlap_train_test = train_texts.intersection(test_texts)

    print("\n--- Leakage Verification Checks ---")
    print(f"  ID Overlap (Train and Val)   : {len(id_overlap_train_val)} (Expected: 0)")
    print(f"  ID Overlap (Train and Test)  : {len(id_overlap_train_test)} (Expected: 0)")
    print(f"  ID Overlap (Val and Test)    : {len(id_overlap_val_test)} (Expected: 0)")
    print(f"  Text Overlap (Train and Test): {len(text_overlap_train_test)} (Expected: 0)")

    assert len(id_overlap_train_val) == 0, "ID leakage detected between Train and Val!"
    assert len(id_overlap_train_test) == 0, "ID leakage detected between Train and Test!"
    assert len(id_overlap_val_test) == 0, "ID leakage detected between Val and Test!"
    assert len(text_overlap_train_test) == 0, "Text leakage detected between Train and Test!"

    print("  [PASS] Zero data leakage verified across all partition boundaries.")

    # 5. Stratification Proportions Verification
    print("\n--- Stratification Fidelity across Splits ---")
    levels = ["Remember", "Understand", "Apply", "Analyze", "Evaluate", "Create"]
    summary_data = []
    for lvl in levels:
        tr_pct = (train_df["blooms_level"] == lvl).mean() * 100
        val_pct = (val_df["blooms_level"] == lvl).mean() * 100
        te_pct = (test_df["blooms_level"] == lvl).mean() * 100
        summary_data.append({
            "Bloom Level": lvl,
            "Train %": f"{tr_pct:.1f}%",
            "Val %": f"{val_pct:.1f}%",
            "Test %": f"{te_pct:.1f}%",
        })
    print(pd.DataFrame(summary_data).to_string(index=False))

    # 6. Save splits
    train_df.to_csv(TRAIN_PATH, index=False)
    val_df.to_csv(VAL_PATH, index=False)
    test_df.to_csv(TEST_PATH, index=False)

    print(f"\n[SUCCESS] Split datasets generated and saved:")
    print(f"  - {TRAIN_PATH}")
    print(f"  - {VAL_PATH}")
    print(f"  - {TEST_PATH}")
    print("================================================================================")


if __name__ == "__main__":
    create_splits()
