"""Pydantic schemas for User registration, authentication, and administration."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field, field_validator, ConfigDict
from backend.app.models.user import UserRole


class UserRegister(BaseModel):
    """Schema for public user self-registration."""

    email: EmailStr = Field(description="Unique email address")
    full_name: str = Field(min_length=2, max_length=150, description="User full name")
    password: str = Field(min_length=8, max_length=128, description="Plaintext password (min 8 chars)")
    role: UserRole = Field(
        default=UserRole.TEACHER,
        description="Desired role. Public self-registration permits TEACHER or RESEARCHER only.",
    )
    institution: Optional[str] = Field(default=None, max_length=255, description="Affiliated academic institution")
    institution_code: Optional[str] = Field(default=None, max_length=100, description="Institution / College ID code")
    department: Optional[str] = Field(default=None, max_length=255, description="Academic department")
    designation: Optional[str] = Field(default=None, max_length=255, description="Academic designation / title")

    @field_validator("role")
    @classmethod
    def validate_role_not_admin(cls, role: UserRole) -> UserRole:
        """Enforce Section 4.1 rule: No public self-registration for Admin."""
        if role == UserRole.ADMIN:
            raise ValueError(
                "Self-registration for the Admin role is strictly prohibited. "
                "Administrators must be provisioned via the secure CLI bootstrapping script."
            )
        return role


class UserLogin(BaseModel):
    """Schema for user credential submission."""

    email: EmailStr = Field(description="Account email")
    password: str = Field(description="Account password")


class UserResponse(BaseModel):
    """Safe user profile response representation (excluding password hashes)."""

    id: int
    email: EmailStr
    full_name: str
    role: UserRole
    is_active: bool
    institution: Optional[str] = None
    institution_code: Optional[str] = None
    department: Optional[str] = None
    designation: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TokenResponse(BaseModel):
    """JWT Token pair response."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserResponse


class TokenRefreshRequest(BaseModel):
    """Schema for refreshing an access token using a refresh token."""

    refresh_token: str


class UserStatusUpdate(BaseModel):
    """Schema for administrative account activation/deactivation."""

    is_active: bool


class UserRoleUpdate(BaseModel):
    """Schema for administrative role reassignment."""

    role: UserRole
