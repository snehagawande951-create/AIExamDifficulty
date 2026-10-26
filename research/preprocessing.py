"""Reproducible NLP Preprocessing and Linguistic Feature Extraction Pipeline.

Designed to prevent target leakage:
1. Cleans question strings while stripping trailing exam marks (e.g., "[10 Marks]").
2. Normalizes unicode, quotation marks, math notation, and whitespace.
3. Computes verifiable linguistic, syntactic, and readability features.
"""

import re
import unicodedata
from typing import Dict, Any, List, Optional
import textstat
import pandas as pd


# Regex pattern to match leading question numbers: e.g. "1.", "Q_01:", "2(a)", "2.a", "(iv)", "Q2(a)"
LEADING_INDEX_PATTERN = re.compile(
    r"^\s*(?:(?:Q(?:uestion)?\.?\s*)?\d+(?:[\.\:\)]|\s*\([a-z0-9]+\)|\.[a-z0-9]+)?[\.\:\)]?|\([a-z0-9]+\))\s*",
    re.IGNORECASE,
)

# Regex pattern to match trailing marks notation: e.g. "[10 Marks]", "(5 M)", "[5M]", "(10 marks)"
TRAILING_MARKS_PATTERN = re.compile(
    r"\s*(?:\[\s*\d+(?:\.\d+)?\s*(?:marks?|m)\s*\]|\(\s*\d+(?:\.\d+)?\s*(?:marks?|m)\s*\))\s*$",
    re.IGNORECASE,
)

# Revised Bloom's primary action verbs catalogue (for baseline feature analysis)
BLOOM_ACTION_VERBS = {
    "remember": ["define", "list", "state", "name", "identify", "recall", "label", "what", "who", "when"],
    "understand": ["explain", "describe", "discuss", "summarize", "paraphrase", "classify", "interpret", "clarify"],
    "apply": ["calculate", "compute", "solve", "demonstrate", "apply", "execute", "construct", "implement", "derive"],
    "analyze": ["analyze", "compare", "contrast", "differentiate", "distinguish", "deconstruct", "examine", "investigate"],
    "evaluate": ["evaluate", "critique", "justify", "assess", "judge", "rate", "prioritize", "defend"],
    "create": ["design", "formulate", "propose", "develop", "architect", "synthesize", "invent", "devise"],
}


def clean_question_text(
    text: str,
    strip_marks: bool = True,
    strip_indices: bool = True,
    lowercase: bool = False,
) -> str:
    """Normalize and clean raw question strings.
    
    Args:
        text: Raw examination question text.
        strip_marks: If True, remove trailing marks annotations (prevents label leakage).
        strip_indices: If True, remove leading question numbering prefixes.
        lowercase: If True, convert to lower case.
    
    Returns:
        Cleaned, normalized string.
    """
    if not isinstance(text, str) or not text.strip():
        return ""

    # 1. Unicode Normalization (NFKD)
    normalized = unicodedata.normalize("NFKD", text)

    # 2. Normalize smart quotes, apostrophes, and dashes
    normalized = (
        normalized.replace("“", '"')
        .replace("”", '"')
        .replace("‘", "'")
        .replace("’", "'")
        .replace("—", "-")
        .replace("–", "-")
    )

    # 3. Strip trailing marks to prevent target leakage in NLP features
    if strip_marks:
        normalized = TRAILING_MARKS_PATTERN.sub("", normalized)

    # 4. Strip leading numbering indices
    if strip_indices:
        normalized = LEADING_INDEX_PATTERN.sub("", normalized)

    # 5. Normalize whitespace
    normalized = re.sub(r"\s+", " ", normalized).strip()

    if lowercase:
        normalized = normalized.lower()

    return normalized


def extract_linguistic_features(text: str) -> Dict[str, Any]:
    """Compute structural and readability features for baseline and ablation studies."""
    cleaned = clean_question_text(text, lowercase=False)
    words = cleaned.split()
    word_count = len(words)
    char_count = len(cleaned)
    avg_word_length = char_count / word_count if word_count > 0 else 0.0

    # Readability scores
    flesch_reading_ease = textstat.flesch_reading_ease(cleaned) if word_count >= 3 else 50.0
    flesch_kincaid_grade = textstat.flesch_kincaid_grade(cleaned) if word_count >= 3 else 8.0
    dale_chall = textstat.dale_chall_readability_score(cleaned) if word_count >= 3 else 7.0

    # Action verb keyword indicators
    first_word = words[0].lower().strip(".,:;?") if words else ""
    verb_matches = {}
    for level, verbs in BLOOM_ACTION_VERBS.items():
        # Check if first word is a Bloom verb
        verb_matches[f"first_word_is_{level}"] = int(first_word in verbs)
        # Check overall frequency of Bloom verbs in question
        verb_matches[f"count_{level}_verbs"] = sum(1 for w in words if w.lower().strip(".,:;?") in verbs)

    features = {
        "char_count": char_count,
        "word_count": word_count,
        "avg_word_length": round(avg_word_length, 2),
        "flesch_reading_ease": round(flesch_reading_ease, 2),
        "flesch_kincaid_grade": round(flesch_kincaid_grade, 2),
        "dale_chall_score": round(dale_chall, 2),
        "has_comparison_cue": int(any(w.lower() in ["versus", "vs", "compare", "contrast", "difference"] for w in words)),
        "has_justification_cue": int(any(w.lower() in ["why", "justify", "reason", "proof", "prove"] for w in words)),
        **verb_matches,
    }
    return features


def preprocess_dataframe(df: pd.DataFrame, text_col: str = "question_text") -> pd.DataFrame:
    """Apply cleaning and feature extraction to an entire DataFrame."""
    df_out = df.copy()
    df_out["cleaned_question_text"] = df_out[text_col].apply(
        lambda t: clean_question_text(t, strip_marks=True, strip_indices=True)
    )
    return df_out
