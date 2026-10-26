"""Examination Paper and Section SQLAlchemy models."""

import enum
from typing import List, Optional
from sqlalchemy import String, Float, Text, Enum, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.app.db.base_class import Base


class PaperStatus(str, enum.Enum):
    """Processing lifecycle states of an uploaded question paper."""

    UPLOADED = "UPLOADED"
    EXTRACTED = "EXTRACTED"
    ANALYZED = "ANALYZED"
    FAILED = "FAILED"


class Paper(Base):
    """Examination paper document entity with strict owner isolation."""

    __tablename__ = "papers"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    owner_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    subject: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    academic_year: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    term: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    
    # Document storage details
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    stored_filepath: Mapped[str] = mapped_column(String(500), nullable=False)
    file_type: Mapped[str] = mapped_column(String(10), nullable=False)  # pdf, docx
    file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    
    total_marks: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    status: Mapped[PaperStatus] = mapped_column(
        Enum(PaperStatus, native_enum=False),
        default=PaperStatus.UPLOADED,
        nullable=False,
    )
    extraction_metadata: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON string

    # Relationships
    owner: Mapped["User"] = relationship("User", back_populates="papers")
    sections: Mapped[List["Section"]] = relationship(
        "Section", back_populates="paper", cascade="all, delete-orphan", order_by="Section.order_index"
    )
    questions: Mapped[List["Question"]] = relationship(
        "Question", back_populates="paper", cascade="all, delete-orphan", order_by="Question.order_index"
    )
    analysis_runs: Mapped[List["AnalysisRun"]] = relationship(
        "AnalysisRun", back_populates="paper", cascade="all, delete-orphan"
    )


class Section(Base):
    """Paper section grouping (e.g. Section A, Section B)."""

    __tablename__ = "sections"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    paper_id: Mapped[int] = mapped_column(
        ForeignKey("papers.id", ondelete="CASCADE"), nullable=False, index=True
    )
    section_name: Mapped[str] = mapped_column(String(100), nullable=False)
    instructions: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    order_index: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Relationships
    paper: Mapped["Paper"] = relationship("Paper", back_populates="sections")
    questions: Mapped[List["Question"]] = relationship("Question", back_populates="section")
