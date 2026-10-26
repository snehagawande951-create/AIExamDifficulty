"""User, Role, and RefreshToken SQLAlchemy models."""

import enum
from datetime import datetime
from typing import List, Optional
from sqlalchemy import String, Boolean, DateTime, Enum, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.app.db.base_class import Base


class UserRole(str, enum.Enum):
    """The three mandatory application user roles."""

    ADMIN = "ADMIN"
    TEACHER = "TEACHER"
    RESEARCHER = "RESEARCHER"


class User(Base):
    """Application user entity with RBAC role and institutional affiliation."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, native_enum=False),
        default=UserRole.TEACHER,
        nullable=False,
        index=True,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    institution: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    institution_code: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    department: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    designation: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Relationships
    refresh_tokens: Mapped[List["RefreshToken"]] = relationship(
        "RefreshToken", back_populates="user", cascade="all, delete-orphan"
    )
    papers: Mapped[List["Paper"]] = relationship(
        "Paper", back_populates="owner", cascade="all, delete-orphan"
    )
    corrections: Mapped[List["TeacherCorrection"]] = relationship(
        "TeacherCorrection", back_populates="teacher", cascade="all, delete-orphan"
    )
    audit_events: Mapped[List["AuditEvent"]] = relationship(
        "AuditEvent", back_populates="user"
    )


class RefreshToken(Base):
    """Persisted refresh token hashes for session lifecycle management."""

    __tablename__ = "refresh_tokens"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    token_hash: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    is_revoked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Relationship
    user: Mapped["User"] = relationship("User", back_populates="refresh_tokens")
