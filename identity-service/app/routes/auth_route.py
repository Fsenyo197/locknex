from fastapi import APIRouter, Depends, Request, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.db import get_db
from app.services.auth_service import AuthService
from app.schemas.auth_schema import LoginResponse
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

    result = await AuthService.login(
        db=db,
        identifier=email,
        password=password,
        user_agent=request.headers.get("user-agent", "unknown"),
        ip_address=request.client.host if request.client else None,
    )

    await log_activity(
        db, result["user"], "login_success", request=request,
        description=f"User {result['user'].email} logged in successfully"
    )

    return result


# =========================================================
# LOGOUT
# =========================================================
@auth_router.post("/logout")
async def logout(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    refresh_token = request.headers.get("X-Refresh-Token")
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing X-Refresh-Token header",
        )

    result = await AuthService.logout(
        db=db,
        refresh_token=refresh_token,
        user_id=str(user.id),
        actor=user,
    )

    await log_activity(
        db, user, "logout_success", request=request,
        description=f"User {user.email} logged out successfully"
    )

    return result
