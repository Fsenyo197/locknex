from typing import Optional
from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.activity_log_model import ActivityLog
from app.models.user_model import User
from app.services.restriction_service import RestrictionService
from sqlalchemy.exc import SQLAlchemyError


async def log_activity(
    db: AsyncSession,
    target_user: Optional[User] = None,
    activity_type: Optional[str] = None,
    request: Optional[Request] = None,
    current_user: Optional[User] = None,
    **kwargs,
) -> Optional[ActivityLog]:
    """
    Logs a user activity into the ActivityLog table.
    If no current_user is provided, logging is skipped completely.
    """

    # ---------------------------------------------
    # 🚨 SKIP LOGGING ENTIRELY IF NO CURRENT USER
    # ---------------------------------------------
    if current_user is None:
        return None

    # Enforce restrictions (only if both users provided)
    if current_user and target_user:
        await RestrictionService.enforce(
            current_user.staff_profile,
            target_user.staff_profile,
            action="view_logs",
        )

    # Extract request metadata (if available)
    ip_address = None
    user_agent = None
    if request:
        ip_address = request.client.host if request.client else None
        user_agent = request.headers.get("user-agent")

    # Create log entry
    log = ActivityLog(
        user_id=current_user.id,
        activity_type=activity_type,
        ip_address=ip_address,
        user_agent=user_agent,
        **kwargs,
    )

    try:
        db.add(log)
        await db.commit()
        await db.refresh(log)
        return log
    except SQLAlchemyError as e:
        await db.rollback()
        raise e
