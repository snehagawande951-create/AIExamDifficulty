"""Health check schemas."""

from datetime import datetime
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """Schema for health status endpoint."""

    status: str = Field(default="ok", description="Overall system health status")
    project_name: str = Field(description="Name of the service")
    version: str = Field(description="Application version")
    environment: str = Field(description="Runtime environment (development, staging, production)")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="UTC timestamp of the check")
    system_info: Dict[str, Any] = Field(default_factory=dict, description="Diagnostic system details")
    database_status: Optional[str] = Field(default="pending_phase_3", description="Status of the database connection")
    database: Optional[str] = Field(default="connected", description="Database connection health state")
    database_engine: Optional[str] = Field(default="PostgreSQL", description="Underlying database engine (PostgreSQL, MySQL, SQLite)")
