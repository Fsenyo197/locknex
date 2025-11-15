from datetime import timedelta, datetime, timezone
from fastapi import APIRouter, Depends, Request, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import cast
from uuid import UUID
from app.db import get_db
from app.services.user_service import UserService
from app.services.session_service import SessionService
from app.schemas.auth_schema import LoginResponse
from app.schemas.session_schema import SessionCreate
from app.utils.jwt import create_access_token, create_refresh_token
from app.utils.activity_logger import log_activity
from app.utils.current_user import get_current_user

auth_router = APIRouter(prefix="/auth", tags=["Auth"])


# =========================================================
# LOGIN
# =========================================================
@auth_router.post("/login", response_model=LoginResponse)
async def login(
    request: Request,
    email: str,
    password: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Authenticate user, create session, and return JWT tokens (fully async).
    """
    user = await UserService.authenticate_user(db, email, password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    # Token lifetimes
    access_token_expires = timedelta(minutes=30)
    refresh_token_expires = timedelta(days=7)

    # Generate JWT tokens
    access_token = create_access_token(
        data={"sub": str(user.id)}, expires_delta=access_token_expires
    )
    refresh_token = create_refresh_token(
        data={"sub": str(user.id)}, expires_delta=refresh_token_expires
    )

    # Create session record
    expires_at = datetime.now(timezone.utc) + refresh_token_expires
    session_in = SessionCreate(
        user_id=cast(UUID, user.id),
        refresh_token=refresh_token,
        user_agent=request.headers.get("user-agent", "unknown"),
        ip_address=request.client.host if request.client else None,
        expires_at=expires_at,
    )
    await SessionService.create_session(db, session_in, actor=user, request=request)

    await log_activity(
        db, user, "login_success", request=request,
        description=f"User {user.email} logged in successfully"
    )

    return {
        "user": user,
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }


# =========================================================
# LOGOUT
# =========================================================
@auth_router.post("/logout")
async def logout(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    """
    Invalidate the refresh token and end the user session (fully async).
    """
    refresh_token = request.headers.get("X-Refresh-Token")

    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Refresh token missing from headers",
        )

    await SessionService.invalidate_session(
        db=db, refresh_token=refresh_token, user_id=str(user.id), actor=user, request=request
    )

    await log_activity(
        db, user, "logout_success", request=request,
        description=f"User {user.email} logged out successfully"
    )

    return {"message": "Logged out successfully"}
