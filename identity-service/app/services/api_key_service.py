from typing import Optional, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from fastapi import HTTPException, status
from uuid import UUID
from datetime import datetime, timezone
from app.models.api_key_model import APIKey
from app.models.permission_model import Permission
from app.schemas.api_key_schema import APIKeyCreate, APIKeyUpdate
from app.utils.activity_logger import log_activity


# -------------------------------
# CREATE API KEY
# -------------------------------
async def create_api_key(
    db: AsyncSession,
    user_id: UUID,
    api_key_in: APIKeyCreate,
    actor=None,
    request=None,
) -> APIKey:
    try:
        api_key = APIKey(
            user_id=user_id,
            key_hash=api_key_in.key_hash,
            secret=api_key_in.secret,
            is_active=api_key_in.is_active,
            expires_at=api_key_in.expires_at,
        )

        # ✅ Attach permissions
        if api_key_in.permissions:
            result = await db.execute(
                select(Permission).filter(Permission.id.in_(api_key_in.permissions))
            )
            perms = result.scalars().all()
            api_key.permissions = perms

        db.add(api_key)
        await db.commit()
        await db.refresh(api_key)

        await log_activity(
            db, actor, "api_key_create_success", request=request,
            description=f"API key created for user_id={user_id}"
        )
        return api_key
    except Exception as e:
        await db.rollback()
        await log_activity(db, actor, "api_key_create_error", request=request, description=str(e))
        raise


# -------------------------------
# GET SINGLE API KEY
# -------------------------------
async def get_api_key(
    db: AsyncSession,
    api_key_id: UUID,
    actor=None,
    request=None,
) -> APIKey:
    result = await db.execute(select(APIKey).filter(APIKey.id == api_key_id))
    api_key = result.scalar_one_or_none()

    if not api_key:
        await log_activity(
            db, actor, "api_key_get_not_found", request=request,
            description=f"API key {api_key_id} not found"
        )
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="API Key not found")

    await log_activity(
        db, actor, "api_key_get_success", request=request,
        description=f"API key {api_key_id} retrieved"
    )
    return api_key


# -------------------------------
# LIST API KEYS
# -------------------------------
async def list_api_keys(
    db: AsyncSession,
    user_id: Optional[UUID] = None,
    actor=None,
    request=None,
) -> List[APIKey]:
    stmt = select(APIKey)
    if user_id:
        stmt = stmt.filter(APIKey.user_id == user_id)

    result = await db.execute(stmt)
    keys = list(result.scalars().all())

    await log_activity(
        db, actor, "api_key_list", request=request,
        description=f"Listed API keys (user_id={user_id if user_id else 'all'})"
    )
    return keys


# -------------------------------
# UPDATE API KEY
# -------------------------------
async def update_api_key(
    db: AsyncSession,
    api_key_id: UUID,
    api_key_in: APIKeyUpdate,
    actor=None,
    request=None,
) -> APIKey:
    try:
        api_key = await get_api_key(db, api_key_id, actor=actor, request=request)

        if api_key_in.is_active is not None:
            setattr(api_key, "is_active", api_key_in.is_active)
        if api_key_in.expires_at is not None:
            setattr(api_key, "expires_at", api_key_in.expires_at)

        # ✅ Update permissions
        if api_key_in.permissions is not None:
            result = await db.execute(
                select(Permission).filter(Permission.id.in_(api_key_in.permissions))
            )
            perms = result.scalars().all()
            api_key.permissions = perms

        # assign to the instance attribute using setattr to satisfy static type checkers
        setattr(api_key, "date_updated", datetime.now(timezone.utc))
        await db.commit()
        await db.refresh(api_key)

        await log_activity(
            db, actor, "api_key_update_success", request=request,
            description=f"API key {api_key_id} updated"
        )
        return api_key
    except Exception as e:
        await db.rollback()
        await log_activity(db, actor, "api_key_update_error", request=request, description=str(e))
        raise


# -------------------------------
# DELETE API KEY
# -------------------------------
async def delete_api_key(
    db: AsyncSession,
    api_key_id: UUID,
    actor=None,
    request=None,
) -> None:
    try:
        api_key = await get_api_key(db, api_key_id, actor=actor, request=request)
        await db.delete(api_key)
        await db.commit()

        await log_activity(
            db, actor, "api_key_delete_success", request=request,
            description=f"API key {api_key_id} deleted"
        )
    except Exception as e:
        await db.rollback()
        await log_activity(db, actor, "api_key_delete_error", request=request, description=str(e))
        raise
