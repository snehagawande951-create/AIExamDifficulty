"""Production Machine Learning Inference Service.

Stateless, thread-safe inference engine that loads versioned scikit-learn
pipelines from models/registry/v1.0.0/ and executes dual-task predictions:
1. Task A: Bloom's Taxonomy Cognitive Level (6 classes) + Posterior Probabilities
2. Task B: Question Difficulty (3 classes: Easy, Medium, Hard) + Continuous Score
"""

import json
import os
from typing import Dict, Any, List, Optional
import joblib
import numpy as np

from research.preprocessing import clean_question_text

DEFAULT_REGISTRY_PATH = os.path.join(
    os.path.dirname(__file__), "../../../models/registry/v1.0.0"
)


class MLEngine:
    """Thread-safe inference manager for academic question classification."""

    def __init__(self, registry_dir: str = DEFAULT_REGISTRY_PATH):
        self.registry_dir = os.path.abspath(registry_dir)
        self.blooms_model = None
        self.difficulty_model = None
        self.metadata = {}
        self.model_version = "1.0.0"
        self._load_models()

    def _load_models(self) -> None:
        """Load serialized model artifacts and metadata from registry."""
        blooms_path = os.path.join(self.registry_dir, "blooms_model.joblib")
        diff_path = os.path.join(self.registry_dir, "difficulty_model.joblib")
        meta_path = os.path.join(self.registry_dir, "model_metadata.json")

        if not os.path.exists(blooms_path) or not os.path.exists(diff_path):
            raise FileNotFoundError(
                f"Model artifacts missing in registry directory: {self.registry_dir}"
            )

        self.blooms_model = joblib.load(blooms_path)
        self.difficulty_model = joblib.load(diff_path)

        if os.path.exists(meta_path):
            with open(meta_path, "r", encoding="utf-8") as f:
                self.metadata = json.load(f)
                self.model_version = self.metadata.get("version", "1.0.0")

    def predict_bloom(self, text: str) -> Dict[str, Any]:
        """Classify question into Bloom's Taxonomy level with probabilities."""
        cleaned = clean_question_text(text)
        if not cleaned:
            return {
                "blooms_level": "Remember",
                "confidence": 0.0,
                "probabilities": {},
            }

        probs = self.blooms_model.predict_proba([cleaned])[0]
        classes = self.blooms_model.classes_
        top_idx = int(np.argmax(probs))
        predicted_class = str(classes[top_idx])
        confidence = float(probs[top_idx])

        prob_dict = {
            str(cls): round(float(p), 4) for cls, p in zip(classes, probs)
        }

        return {
            "blooms_level": predicted_class,
            "confidence": round(confidence, 4),
            "probabilities": prob_dict,
        }

    def predict_difficulty(self, text: str) -> Dict[str, Any]:
        """Classify question difficulty tier and compute continuous score."""
        cleaned = clean_question_text(text)
        if not cleaned:
            return {
                "difficulty_level": "Medium",
                "confidence": 0.0,
                "probabilities": {},
                "continuous_score": 0.50,
            }

        probs = self.difficulty_model.predict_proba([cleaned])[0]
        classes = self.difficulty_model.classes_
        top_idx = int(np.argmax(probs))
        predicted_class = str(classes[top_idx])
        confidence = float(probs[top_idx])

        prob_dict = {
            str(cls): round(float(p), 4) for cls, p in zip(classes, probs)
        }

        # Weighted continuous difficulty score: Easy=0.20, Medium=0.55, Hard=0.88
        p_easy = prob_dict.get("Easy", 0.0)
        p_med = prob_dict.get("Medium", 0.0)
        p_hard = prob_dict.get("Hard", 0.0)
        continuous_score = (0.20 * p_easy) + (0.55 * p_med) + (0.88 * p_hard)

        return {
            "difficulty_level": predicted_class,
            "confidence": round(confidence, 4),
            "probabilities": prob_dict,
            "continuous_score": round(float(continuous_score), 4),
        }

    def analyze_question(self, text: str) -> Dict[str, Any]:
        """Execute dual-task inference on an examination question."""
        bloom_res = self.predict_bloom(text)
        diff_res = self.predict_difficulty(text)

        return {
            "cleaned_text": clean_question_text(text),
            "blooms_level": bloom_res["blooms_level"],
            "blooms_confidence": bloom_res["confidence"],
            "blooms_probabilities": bloom_res["probabilities"],
            "difficulty_level": diff_res["difficulty_level"],
            "difficulty_confidence": diff_res["confidence"],
            "difficulty_probabilities": diff_res["probabilities"],
            "continuous_difficulty_score": diff_res["continuous_score"],
            "model_version": self.model_version,
            "bloom_model_name": self.metadata.get("blooms_champion", "TFIDF_LogisticRegression"),
            "difficulty_model_name": self.metadata.get("difficulty_champion", "TFIDF_LogisticRegression"),
        }

    def batch_analyze_questions(self, texts: List[str]) -> List[Dict[str, Any]]:
        """Vectorized batch analysis for entire examination papers."""
        return [self.analyze_question(t) for t in texts]


# Module-level singleton instance for FastAPI injection
ml_engine = MLEngine()
