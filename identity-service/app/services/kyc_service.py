from typing import Optional, Any, cast
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException
from app.models.user_model import User, UserStatus
from app.models.kyc_model import KYCVerification
from app.schemas.kyc_schema import KYCVerificationCreate
from app.utils.activity_logger import log_activity


class KYCService:
    # -------------------------
    # Submit KYC
    # -------------------------
    @staticmethod
    async def submit_kyc(
        db: AsyncSession,
        user: User,
        kyc_in: KYCVerificationCreate,
        actor: Optional[User] = None,
        request=None
    ) -> KYCVerification:
        """Submit new KYC attempt for user (keeps history)."""
        try:
            kyc = KYCVerification(user_id=user.id, **kyc_in.dict())
            db.add(kyc)

            # Update user status to pending KYC
            user.status = cast(Any, UserStatus.PENDING_KYC.value)
            await db.commit()
            await db.refresh(kyc)

            await log_activity(
                db, actor or user, "kyc_submit_success", request=request,
                description=f"KYC submitted for user {user.username}"
            )

            return kyc
        except Exception as e:
            await db.rollback()
            await log_activity(
                db, actor or user, "kyc_submit_error", request=request,
                description=str(e)
            )
            raise

    # -------------------------
    # Get latest KYC
    # -------------------------
    @staticmethod
    async def get_latest_kyc(
        user: User,
        db: AsyncSession,
        actor: Optional[User] = None,
        request=None
    ) -> Optional[KYCVerification]:
        """Return most recent KYC record for a user."""
        try:
            stmt = (
                select(KYCVerification)
                .filter_by(user_id=user.id)
                .order_by(KYCVerification.date_created.desc())
                .limit(1)
            )
            result = await db.execute(stmt)
            latest = result.scalar_one_or_none()

            if not latest:
                await log_activity(
                    db, actor or user, "kyc_get_none", request=request,
                    description=f"No KYC records found for user {user.username}"
                )
                return None

            await log_activity(
                db, actor or user, "kyc_get_latest", request=request,
                description=f"Latest KYC retrieved for user {user.username}"
            )

            return latest
        except Exception as e:
            await log_activity(
                db, actor or user, "kyc_get_error", request=request,
                description=str(e)
            )
            raise
