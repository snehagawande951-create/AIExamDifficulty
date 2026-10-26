"""Pydantic schemas package."""

from backend.app.schemas.user import (
    UserRegister,
    UserLogin,
    UserResponse,
    TokenResponse,
    TokenRefreshRequest,
    UserStatusUpdate,
    UserRoleUpdate,
)
from backend.app.schemas.paper import (
    PaperResponse,
    PaperDetailResponse,
    SectionResponse,
    QuestionResponse,
    PredictionResponse,
    TeacherCorrectionCreate,
    TeacherCorrectionResponse,
    AnalysisRunResponse,
    PaperAnalyticsResponse,
    CognitiveLevelDistribution,
    DifficultyDistribution,
)
from backend.app.schemas.health import HealthResponse

__all__ = [
    "UserRegister",
    "UserLogin",
    "UserResponse",
    "TokenResponse",
    "TokenRefreshRequest",
    "UserStatusUpdate",
    "UserRoleUpdate",
    "PaperResponse",
    "PaperDetailResponse",
    "SectionResponse",
    "QuestionResponse",
    "PredictionResponse",
    "TeacherCorrectionCreate",
    "TeacherCorrectionResponse",
    "AnalysisRunResponse",
    "PaperAnalyticsResponse",
    "CognitiveLevelDistribution",
    "DifficultyDistribution",
    "HealthResponse",
]
