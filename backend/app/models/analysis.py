"""AnalysisRun, Prediction, and TeacherCorrection SQLAlchemy models."""

from typing import List, Optional
from sqlalchemy import String, Float, Text, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.app.db.base_class import Base


class AnalysisRun(Base):
    """Execution instance of the ML analysis pipeline for an examination paper."""

    __tablename__ = "analysis_runs"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    paper_id: Mapped[int] = mapped_column(
        ForeignKey("papers.id", ondelete="CASCADE"), nullable=False, index=True
    )
    triggered_by_user_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    
    model_version: Mapped[str] = mapped_column(String(50), nullable=False)
    bloom_model_name: Mapped[str] = mapped_column(String(100), nullable=False)
    difficulty_model_name: Mapped[str] = mapped_column(String(100), nullable=False)
    
    execution_duration_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="COMPLETED", nullable=False)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    paper: Mapped["Paper"] = relationship("Paper", back_populates="analysis_runs")
    predictions: Mapped[List["Prediction"]] = relationship(
        "Prediction", back_populates="analysis_run", cascade="all, delete-orphan"
    )


class Prediction(Base):
    """Raw model inference outputs for an individual question."""

    __tablename__ = "predictions"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    analysis_run_id: Mapped[int] = mapped_column(
        ForeignKey("analysis_runs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    question_id: Mapped[int] = mapped_column(
        ForeignKey("questions.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Task A: Bloom's Taxonomy Prediction (6 Cognitive Levels)
    predicted_blooms_level: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    blooms_confidence: Mapped[float] = mapped_column(Float, nullable=False)
    blooms_probabilities: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON string

    # Task B: Question Difficulty Prediction (Easy, Medium, Hard)
    predicted_difficulty: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    difficulty_confidence: Mapped[float] = mapped_column(Float, nullable=False)
    difficulty_probabilities: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON string
    continuous_difficulty_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Relationships
    analysis_run: Mapped["AnalysisRun"] = relationship("AnalysisRun", back_populates="predictions")
    question: Mapped["Question"] = relationship("Question", back_populates="predictions")


class TeacherCorrection(Base):
    """Human teacher adjustments and overrides over model predictions."""

    __tablename__ = "teacher_corrections"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    question_id: Mapped[int] = mapped_column(
        ForeignKey("questions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    teacher_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    original_blooms_level: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    corrected_blooms_level: Mapped[str] = mapped_column(String(50), nullable=False)

    original_difficulty: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    corrected_difficulty: Mapped[str] = mapped_column(String(50), nullable=False)

    corrected_marks: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    corrected_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    rationale: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    question: Mapped["Question"] = relationship("Question", back_populates="corrections")
    teacher: Mapped["User"] = relationship("User", back_populates="corrections")
