"""Health check and diagnostics endpoint with live database connectivity test."""

import platform
import sys
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session
from backend.app.core.config import settings
from backend.app.db.session import get_db, get_database_engine_name
from backend.app.schemas.health import HealthResponse

router = APIRouter()


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="System Health & Diagnostic Check",
    description="Returns live system diagnostics, environment status, and genuine database health.",
)
def check_health(db: Session = Depends(get_db)) -> HealthResponse:
    """Return genuine operational status of the service and database."""
    try:
        db.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception as e:
        db_status = f"disconnected ({str(e)})"

    return HealthResponse(
        status="ok" if db_status == "connected" else "degraded",
        project_name=settings.PROJECT_NAME,
        version=settings.VERSION,
        environment=settings.ENVIRONMENT,
        system_info={
            "python_version": sys.version.split()[0],
            "platform": platform.platform(),
            "debug_mode": settings.DEBUG,
        },
        database_status=db_status,
        database=db_status,
        database_engine=get_database_engine_name(),
    )
