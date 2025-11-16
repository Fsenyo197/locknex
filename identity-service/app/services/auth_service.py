from datetime import datetime, timedelta, timezone
from typing import Optional, cast
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status
from sqlalchemy import select
from uuid import UUID
from app.config import settings
from app.models.user_model import User, UserStatus
from app.schemas.session_schema import SessionCreate
from app.services.session_service import SessionService
from app.utils.jwt import create_access_token, create_refresh_token
from app.utils.password import verify_password


class AuthService:

    # =====================================================
    # USER AUTHENTICATION (username OR email)
    # =====================================================
    @staticmethod
    async def authenticate_user(
        db: AsyncSession,
        identifier: str,
        password: str
    ) -> User:

        query = select(User).where(
            (User.username == identifier) | (User.email == identifier)
        )

        result = await db.execute(query)
        user = result.scalar_one_or_none()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid login credentials",
            )

        if not verify_password(password, cast(str, user.hashed_password)):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid login credentials",
            )

        return user

    # =====================================================
    # LOGIN LOGIC (FULL)
    # =====================================================
    @staticmethod
    async def login(
        db: AsyncSession,
        identifier: str,
        password: str,
        user_agent: str,
        ip_address: Optional[str],
    ):
        """
        Full login pipeline:
        - Authenticate
        - Check status
        - Generate tokens
        - Create session
        """

        user = await AuthService.authenticate_user(db, identifier, password)

        # 🚫 Only suspended users blocked
        if user.status is UserStatus.SUSPENDED:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Your account is suspended",
            )

        # -------------------------------------------------
        # Create tokens
        # -------------------------------------------------
        access_expires = timedelta(minutes=30)
        refresh_expires = timedelta(days=7)

        access_token = create_access_token(
            data={"sub": str(user.id)},
            expires_delta=access_expires
        )
        refresh_token = create_refresh_token(
            data={"sub": str(user.id)},
            expires_delta=refresh_expires
        )

        # -------------------------------------------------
        # Create DB session entry
        # -------------------------------------------------
        expires_at = datetime.now(timezone.utc) + refresh_expires

        session_in = SessionCreate(
            user_id=cast(UUID, user.id),
            refresh_token=refresh_token,
            user_agent=user_agent,
            ip_address=ip_address,
            expires_at=expires_at,
        )

        await SessionService.create_session(
            db=db,
            session_in=session_in,
            actor=user
        )

        return {
            "user": user,
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
        }

    # =====================================================
    # LOGOUT LOGIC
    # =====================================================
    @staticmethod
    async def logout(
        db: AsyncSession,
        refresh_token: str,
        user_id: str,
        actor: User
    ):
        """
        Logout by invalidating refresh token session.
        """
        if not refresh_token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Refresh token missing from headers",
            )

        await SessionService.invalidate_session(
            db=db,
            refresh_token=refresh_token,
            user_id=user_id,
            actor=actor,
        )

        return {"message": "Logged out successfully"}

