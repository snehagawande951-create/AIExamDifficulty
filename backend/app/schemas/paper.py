"""Pydantic schemas for examination papers, questions, analysis, and reviews."""

import json
from datetime import datetime
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from backend.app.models.paper import PaperStatus


# ---------------------------------------------------------------------------
# Prediction & Inference Schemas
# ---------------------------------------------------------------------------

class PredictionResponse(BaseModel):
    """Schema for individual question prediction results."""

    id: int
    analysis_run_id: int
    question_id: int
    predicted_blooms_level: str
    blooms_confidence: float
    blooms_probabilities: Optional[Dict[str, float]] = None
    predicted_difficulty: str
    difficulty_confidence: float
    difficulty_probabilities: Optional[Dict[str, float]] = None
    continuous_difficulty_score: Optional[float] = None
    created_at: datetime

    @field_validator("blooms_probabilities", mode="before")
    @classmethod
    def parse_blooms_probs(cls, v: Any) -> Optional[Dict[str, float]]:
        if isinstance(v, str):
            try:
                return json.loads(v)
            except Exception:
                return None
        return v

    @field_validator("difficulty_probabilities", mode="before")
    @classmethod
    def parse_diff_probs(cls, v: Any) -> Optional[Dict[str, float]]:
        if isinstance(v, str):
            try:
                return json.loads(v)
            except Exception:
                return None
        return v

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Teacher Correction Schemas
# ---------------------------------------------------------------------------

class TeacherCorrectionCreate(BaseModel):
    """Payload for submitting human corrections/overrides on a question."""

    corrected_blooms_level: Optional[str] = Field(None, description="Target Bloom cognitive level")
    manual_blooms_level: Optional[str] = Field(None, description="Alternative alias for target Bloom cognitive level")
    corrected_difficulty: Optional[str] = Field(None, description="Target difficulty tier: Easy, Medium, Hard")
    manual_difficulty: Optional[str] = Field(None, description="Alternative alias for difficulty tier")
    corrected_marks: Optional[float] = Field(None, ge=0.0, description="Updated marks allocation")
    corrected_text: Optional[str] = Field(None, description="Corrected or normalized question text")
    rationale: Optional[str] = Field(None, description="Teacher's academic reasoning for adjustment")
    teacher_justification: Optional[str] = Field(None, description="Alternative alias for teacher's reasoning")
    correction_notes: Optional[str] = Field(None, description="Additional correction notes")

    @model_validator(mode="before")
    @classmethod
    def reconcile_aliases(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "manual_blooms_level" in data and not data.get("corrected_blooms_level"):
                data["corrected_blooms_level"] = data["manual_blooms_level"]
            if "manual_difficulty" in data and not data.get("corrected_difficulty"):
                data["corrected_difficulty"] = data["manual_difficulty"]
            if "teacher_justification" in data and not data.get("rationale"):
                data["rationale"] = data["teacher_justification"]
        return data

    @field_validator("corrected_blooms_level")
    @classmethod
    def validate_bloom_level(cls, v: Optional[str]) -> Optional[str]:
        if not v:
            return v
        valid_levels = {"Remember", "Understand", "Apply", "Analyze", "Evaluate", "Create"}
        capitalized = v.strip().capitalize()
        if capitalized not in valid_levels:
            raise ValueError(f"Invalid Bloom's level '{v}'. Allowed: {sorted(list(valid_levels))}")
        return capitalized

    @field_validator("corrected_difficulty")
    @classmethod
    def validate_difficulty(cls, v: Optional[str]) -> Optional[str]:
        if not v:
            return v
        valid_tiers = {"Easy", "Medium", "Hard"}
        capitalized = v.strip().capitalize()
        if capitalized not in valid_tiers:
            raise ValueError(f"Invalid difficulty '{v}'. Allowed: {sorted(list(valid_tiers))}")
        return capitalized


class TeacherCorrectionResponse(BaseModel):
    """Schema representing recorded human correction."""

    id: int
    question_id: int
    teacher_id: int
    original_blooms_level: Optional[str] = None
    corrected_blooms_level: str
    original_difficulty: Optional[str] = None
    corrected_difficulty: str
    corrected_marks: Optional[float] = None
    corrected_text: Optional[str] = None
    rationale: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Section & Question Schemas
# ---------------------------------------------------------------------------

class SectionResponse(BaseModel):
    """Paper section schema."""

    id: int
    paper_id: int
    section_name: str
    instructions: Optional[str] = None
    order_index: int

    model_config = ConfigDict(from_attributes=True)


class QuestionResponse(BaseModel):
    """Extracted question with its latest prediction and teacher corrections."""

    id: int
    paper_id: int
    section_id: Optional[int] = None
    section_name: Optional[str] = None
    question_number: str
    question_text: str
    marks: Optional[float] = None
    page_number: Optional[int] = None
    order_index: int
    is_reviewed_by_teacher: bool
    predictions: List[PredictionResponse] = []
    corrections: List[TeacherCorrectionResponse] = []

    # Effective fields (either teacher override or latest prediction)
    effective_blooms_level: Optional[str] = None
    effective_difficulty: Optional[str] = None
    predicted_blooms_level: Optional[str] = None
    predicted_difficulty: Optional[str] = None
    blooms_confidence: Optional[float] = None
    difficulty_confidence: Optional[float] = None
    continuous_difficulty_score: Optional[float] = None
    teacher_justification: Optional[str] = None
    rationale: Optional[str] = None
    final_blooms_level: Optional[str] = None
    final_difficulty: Optional[str] = None
    is_human_reviewed: bool = False

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Analysis Run Schemas
# ---------------------------------------------------------------------------

class AnalysisRunResponse(BaseModel):
    """Metadata regarding an ML analysis pipeline run."""

    id: int
    paper_id: int
    triggered_by_user_id: Optional[int] = None
    model_version: str
    bloom_model_name: str
    difficulty_model_name: str
    execution_duration_ms: Optional[int] = None
    status: str
    error_message: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Examination Paper Schemas
# ---------------------------------------------------------------------------

class PaperResponse(BaseModel):
    """Basic paper summary schema for list views."""

    id: int
    owner_id: int
    title: str
    subject: str
    academic_year: Optional[str] = None
    term: Optional[str] = None
    original_filename: str
    file_type: str
    file_size_bytes: int
    total_marks: Optional[float] = None
    status: PaperStatus
    total_questions: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PaperDetailResponse(BaseModel):
    """Comprehensive paper schema including nested sections, questions, and runs."""

    id: int
    owner_id: int
    title: str
    subject: str
    academic_year: Optional[str] = None
    term: Optional[str] = None
    original_filename: str
    file_type: str
    file_size_bytes: int
    total_marks: Optional[float] = None
    status: PaperStatus
    total_questions: int = 0
    extraction_metadata: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    sections: List[SectionResponse] = []
    questions: List[QuestionResponse] = []
    latest_analysis_run: Optional[AnalysisRunResponse] = None

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Analytics & Aggregations Schemas
# ---------------------------------------------------------------------------

class CognitiveLevelDistribution(BaseModel):
    """Distribution counts and marks for a single Bloom's level."""

    count: int = 0
    percentage: float = 0.0
    marks: float = 0.0
    marks_percentage: float = 0.0


class DifficultyDistribution(BaseModel):
    """Distribution counts and marks for a difficulty tier."""

    count: int = 0
    percentage: float = 0.0
    marks: float = 0.0
    marks_percentage: float = 0.0


class PaperAnalyticsResponse(BaseModel):
    """Aggregated academic analytics for an examination paper."""

    paper_id: int
    paper_title: str
    total_questions: int
    total_marks: float
    average_difficulty_score: float  # Scale 0.0 - 1.0
    overall_difficulty_rating: str   # Easy, Medium, Hard
    reviewed_questions_count: int
    review_progress_percentage: float
    cognitive_balance_index: float = Field(default=0.85, description="Cognitive balance index across taxonomy")
    
    blooms_distribution: Dict[str, CognitiveLevelDistribution]
    difficulty_distribution: Dict[str, DifficultyDistribution]
    section_breakdown: List[Dict[str, Any]]
