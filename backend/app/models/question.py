"""Question SQLAlchemy model."""

from typing import List, Optional
from sqlalchemy import String, Float, Text, Boolean, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.app.db.base_class import Base


class Question(Base):
    """Extracted question or sub-question within an examination paper."""

    __tablename__ = "questions"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    paper_id: Mapped[int] = mapped_column(
        ForeignKey("papers.id", ondelete="CASCADE"), nullable=False, index=True
    )
    section_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("sections.id", ondelete="SET NULL"), nullable=True, index=True
    )
    
    question_number: Mapped[str] = mapped_column(String(50), nullable=False)  # e.g., "1", "2(a)"
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    marks: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    page_number: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    order_index: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    # Review & edit flags
    is_reviewed_by_teacher: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Relationships
    paper: Mapped["Paper"] = relationship("Paper", back_populates="questions")
    section: Mapped[Optional["Section"]] = relationship("Section", back_populates="questions")
    predictions: Mapped[List["Prediction"]] = relationship(
        "Prediction", back_populates="question", cascade="all, delete-orphan"
    )
    corrections: Mapped[List["TeacherCorrection"]] = relationship(
        "TeacherCorrection", back_populates="question", cascade="all, delete-orphan"
    )
