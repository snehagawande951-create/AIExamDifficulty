"""Authentication API endpoints (Register, Login, Token Refresh, Logout, Me)."""

from datetime import datetime, timezone, timedelta
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session

from backend.app.core.config import settings
from backend.app.core.deps import get_current_active_user, get_db, revoked_token_jtis, oauth2_scheme
from backend.app.core.security import (
    get_password_hash,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_token,
)
from backend.app.models.user import User, RefreshToken, UserRole
from backend.app.models.audit import AuditEvent
from backend.app.schemas.user import (
    UserRegister,
    UserLogin,
    UserResponse,
    TokenResponse,
    TokenRefreshRequest,
)

router = APIRouter()


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new Teacher or Researcher account",
)
def register_user(
    user_in: UserRegister,
    request: Request,
    db: Session = Depends(get_db),
) -> Any:
    """Public self-registration for Faculty and Researchers."""
    existing_user = db.query(User).filter(User.email == user_in.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email address already exists.",
        )

    hashed_password = get_password_hash(user_in.password)
    new_user = User(
        email=user_in.email,
        full_name=user_in.full_name,
        hashed_password=hashed_password,
        role=user_in.role,
        is_active=True,
        institution=user_in.institution,
        institution_code=user_in.institution_code,
        department=user_in.department,
        designation=user_in.designation,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    # Record Audit Event
    audit = AuditEvent(
        user_id=new_user.id,
        action="USER_REGISTERED",
        resource_type="USER",
        resource_id=str(new_user.id),
        ip_address=request.client.host if request.client else None,
        details=f"User registered with role {new_user.role.value}",
    )
    db.add(audit)
    db.commit()

    return new_user


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Log into the application using email and password",
)
def login(
    credentials: UserLogin,
    request: Request,
    db: Session = Depends(get_db),
) -> Any:
    """Unified login for all three user roles (Admin, Teacher, Researcher)."""
    user = db.query(User).filter(User.email == credentials.email).first()
    if not user or not verify_password(credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated. Please contact an administrator.",
        )

    # Generate Tokens
    access_token = create_access_token(subject=str(user.id), role=user.role.value)
    refresh_token = create_refresh_token(subject=str(user.id))

    # Persist Refresh Token Hash
    expires_at = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    db_token = RefreshToken(
        user_id=user.id,
        token_hash=hash_token(refresh_token),
        expires_at=expires_at,
        is_revoked=False,
    )
    db.add(db_token)

    # Record Audit Log
    audit = AuditEvent(
        user_id=user.id,
        action="USER_LOGIN",
        resource_type="AUTH",
        resource_id=str(user.id),
        ip_address=request.client.host if request.client else None,
        details=f"Successful login for {user.email} ({user.role.value})",
    )
    db.add(audit)
    db.commit()

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=user,
    )


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Refresh access token using a valid refresh token",
)
def refresh_token(
    refresh_in: TokenRefreshRequest,
    db: Session = Depends(get_db),
) -> Any:
    """Validate refresh token and rotate with a new token pair."""
    payload = decode_token(refresh_in.refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )

    user_id_str = payload.get("sub")
    try:
        user_id = int(user_id_str)
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token subject",
        )

    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account inactive or not found",
        )

    # Check database persistence and revocation
    thash = hash_token(refresh_in.refresh_token)
    stored_token = (
        db.query(RefreshToken)
        .filter(RefreshToken.token_hash == thash, RefreshToken.user_id == user.id)
        .first()
    )

    if not stored_token or stored_token.is_revoked:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token has been revoked or is invalid",
        )

    token_exp = stored_token.expires_at
    if token_exp.tzinfo is None:
        token_exp = token_exp.replace(tzinfo=timezone.utc)

    if token_exp < datetime.now(timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token has expired",
        )

    # Token Rotation: Revoke previous refresh token
    stored_token.is_revoked = True

    # Generate new tokens
    new_access_token = create_access_token(subject=str(user.id), role=user.role.value)
    new_refresh_token = create_refresh_token(subject=str(user.id))

    new_expires_at = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    new_db_token = RefreshToken(
        user_id=user.id,
        token_hash=hash_token(new_refresh_token),
        expires_at=new_expires_at,
        is_revoked=False,
    )
    db.add(new_db_token)
    db.commit()

    return TokenResponse(
        access_token=new_access_token,
        refresh_token=new_refresh_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=user,
    )


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get currently authenticated user profile",
)
def get_current_user_profile(
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """Return profile data of the currently logged in user."""
    return current_user


@router.post(
    "/logout",
    summary="Revoke active refresh tokens for the current user",
)
def logout(
    current_user: User = Depends(get_current_active_user),
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> Any:
    """Revoke current access token and all active refresh tokens for the user."""
    payload = decode_token(token)
    if payload and payload.get("jti"):
        revoked_token_jtis.add(payload.get("jti"))

    db.query(RefreshToken).filter(
        RefreshToken.user_id == current_user.id,
        RefreshToken.is_revoked.is_(False),
    ).update({"is_revoked": True})

    audit = AuditEvent(
        user_id=current_user.id,
        action="USER_LOGOUT",
        resource_type="AUTH",
        resource_id=str(current_user.id),
        details=f"User {current_user.email} logged out",
    )
    db.add(audit)
    db.commit()

    return {"message": "Successfully logged out. Refresh tokens revoked."}
