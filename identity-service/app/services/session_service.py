from datetime import datetime, timezone
from fastapi import HTTPException, status
from typing import Any, cast
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from app.models.session_model import Session as UserSession
from app.schemas.session_schema import SessionCreate, SessionResponse
from app.utils.activity_logger import log_activity


class SessionService:

    # -------------------------------
    # Utility: enforce UUID type only for user_id
    # -------------------------------
    @staticmethod
    def _as_uuid(value: str | UUID, field: str) -> UUID:
        if isinstance(value, UUID):
            return value
        try:
            return UUID(str(value))
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid {field} UUID format"
            )

    # -------------------------------
    # CREATE SESSION
    # -------------------------------
    @staticmethod
    async def create_session(
        db: AsyncSession,
        session_in: SessionCreate,
        actor=None,
        request=None
    ) -> SessionResponse:

        try:
            session_data = session_in.model_dump()

            # ONLY user_id must be UUID
            session_data["user_id"] = SessionService._as_uuid(
                session_data["user_id"], "user_id"
            )

            # refresh_token stays a STRING (Option A)
            # no UUID validation

            session = UserSession(**session_data)

            db.add(session)
            await db.commit()
            await db.refresh(session)

            await log_activity(
                db, actor, "session_create_success", request=request,
                description=f"Session created for user_id={session.user_id}"
            )

            return SessionResponse.from_orm(session)

        except Exception as e:
            await db.rollback()
            await log_activity(
                db, actor, "session_create_error", request=request,
                description=str(e)
            )
            raise

    # -------------------------------
    # INVALIDATE SESSION
    # -------------------------------
    @staticmethod
    async def invalidate_session(
        db: AsyncSession,
        refresh_token: str,
        user_id: str | UUID,
        actor=None,
        request=None
    ) -> None:

        user_uuid = SessionService._as_uuid(user_id, "user_id")

        result = await db.execute(
            select(UserSession).filter_by(
                user_id=user_uuid,
                refresh_token=refresh_token,
                is_valid=True
            )
        )
        session = result.unique().scalar_one_or_none()

        if not session:
            await log_activity(
                db, actor, "session_invalidate_failed", request=request,
                description=f"No active session found for user_id={user_uuid}"
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found or already invalidated",
            )

        stmt = (
            update(UserSession)
            .where(UserSession.id == session.id)
            .values(is_valid=False)
        )

        await db.execute(stmt)
        await db.commit()

        await log_activity(
            db, actor, "session_invalidate_success", request=request,
            description=f"Session invalidated for user_id={user_uuid}"
        )

    # -------------------------------
    # VALIDATE REFRESH TOKEN
    # -------------------------------
    @staticmethod
    async def validate_refresh_token(
        db: AsyncSession,
        refresh_token: str,
        user_id: str | UUID,
        actor=None,
        request=None
    ) -> UserSession:

        user_uuid = SessionService._as_uuid(user_id, "user_id")

        result = await db.execute(
            select(UserSession).filter_by(
                user_id=user_uuid,
                refresh_token=refresh_token,
                is_valid=True
            )
        )
        session = result.unique().scalar_one_or_none()

        if not session:
            await log_activity(
                db, actor, "session_validate_failed", request=request,
                description=f"Invalid refresh token for user_id={user_uuid}"
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired refresh token",
            )

        expires_at = cast(datetime, session.expires_at)
        if expires_at < datetime.now(timezone.utc):
            await log_activity(
                db, actor, "session_validate_failed", request=request,
                description=f"Expired refresh token for user_id={user_uuid}"
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired refresh token",
            )

        await log_activity(
            db, actor, "session_validate_success", request=request,
            description=f"Valid refresh token for user_id={user_uuid}"
        )

        return session
