"""User administration API endpoints for the Admin role."""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.orm import Session

from backend.app.core.deps import require_role, get_db
from backend.app.models.user import User, UserRole
from backend.app.models.audit import AuditEvent
from backend.app.schemas.user import UserResponse, UserStatusUpdate, UserRoleUpdate

router = APIRouter()


@router.get(
    "/",
    response_model=List[UserResponse],
    summary="List users (Admin only)",
    description="Retrieve system users with optional role filtering and pagination.",
)
def list_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    role: Optional[UserRole] = None,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_role([UserRole.ADMIN])),
):
    """Admin-only user listing."""
    query = db.query(User)
    if role:
        query = query.filter(User.role == role)
    return query.offset(skip).limit(limit).all()


@router.get(
    "/{user_id}",
    response_model=UserResponse,
    summary="Get user details by ID (Admin only)",
)
def get_user_by_id(
    user_id: int,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_role([UserRole.ADMIN])),
):
    """Retrieve full details of a user account."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.patch(
    "/{user_id}/status",
    response_model=UserResponse,
    summary="Activate or deactivate a user account (Admin only)",
)
def update_user_status(
    user_id: int,
    status_in: UserStatusUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_role([UserRole.ADMIN])),
):
    """Activate, deactivate, or suspend an account."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.id == current_admin.id and not status_in.is_active:
        raise HTTPException(
            status_code=400,
            detail="Administrators cannot deactivate their own account.",
        )

    user.is_active = status_in.is_active
    audit = AuditEvent(
        user_id=current_admin.id,
        action="USER_STATUS_UPDATED",
        resource_type="USER",
        resource_id=str(user.id),
        ip_address=request.client.host if request.client else None,
        details=f"Admin {current_admin.email} set active={user.is_active} for {user.email}",
    )
    db.add(audit)
    db.commit()
    db.refresh(user)
    return user


@router.patch(
    "/{user_id}/role",
    response_model=UserResponse,
    summary="Change user role (Admin only)",
)
def update_user_role(
    user_id: int,
    role_in: UserRoleUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_role([UserRole.ADMIN])),
):
    """Assign or change authorized application roles."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    old_role = user.role.value
    user.role = role_in.role

    audit = AuditEvent(
        user_id=current_admin.id,
        action="USER_ROLE_UPDATED",
        resource_type="USER",
        resource_id=str(user.id),
        ip_address=request.client.host if request.client else None,
        details=f"Admin {current_admin.email} changed role of {user.email} from {old_role} to {user.role.value}",
    )
    db.add(audit)
    db.commit()
    db.refresh(user)
    return user
