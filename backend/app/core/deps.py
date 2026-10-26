"""FastAPI dependencies for authentication, role-based authorization, and DB sessions."""

from typing import List, Callable
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from backend.app.core.config import settings
from backend.app.core.security import decode_token
from backend.app.db.session import get_db
from backend.app.models.user import User, UserRole

revoked_token_jtis: set = set()

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_PREFIX}/auth/login",
    auto_error=True,
)


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Validate JWT access token and return the authenticated user record."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    payload = decode_token(token)
    if not payload:
        raise credentials_exception

    # Check against revoked JWT jti blacklist
    jti = payload.get("jti")
    if jti and jti in revoked_token_jtis:
        raise credentials_exception

    token_type = payload.get("type")
    user_id_str = payload.get("sub")
    if token_type != "access" or not user_id_str:
        raise credentials_exception

    try:
        user_id = int(user_id_str)
    except (ValueError, TypeError):
        raise credentials_exception

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise credentials_exception

    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """Ensure authenticated user account is active."""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated. Contact an administrator.",
        )
    return current_user


def require_role(allowed_roles: List[UserRole]) -> Callable:
    """Dependency factory enforcing Role-Based Access Control (RBAC)."""

    def role_checker(
        current_user: User = Depends(get_current_active_user),
    ) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    f"Access forbidden: Role '{current_user.role.value}' does not have "
                    f"permission to perform this action. Required: {[r.value for r in allowed_roles]}"
                ),
            )
        return current_user

    return role_checker
