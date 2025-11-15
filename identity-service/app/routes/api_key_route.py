from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from typing import List
from app.db import get_db
from app.models.user_model import User
from app.utils.current_user import get_current_user
from app.utils.permission import permission_required
from app.schemas.api_key_schema import APIKeyResponse, APIKeyCreate, APIKeyUpdate
from app.services import api_key_service


# Router setup
api_key_router = APIRouter(prefix="/api-keys", tags=["API Keys"])


# --------------------------------------------------------
# CREATE API KEY
# --------------------------------------------------------
@api_key_router.post(
    "/",
    response_model=APIKeyResponse,
    status_code=status.HTTP_201_CREATED,
)
@permission_required("create_api_key")
async def create_api_key(
    data: APIKeyCreate,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(get_current_user),
    request = Request,
):
    """
    Create a new API key for a user with optional permissions.
    """
    return await api_key_service.create_api_key(
        db=db,
        user_id=data.user_id,
        api_key_in=data,
        actor=actor,
        request=request,
    )


# --------------------------------------------------------
# GET SINGLE API KEY
# --------------------------------------------------------
@api_key_router.get(
    "/{key_id}",
    response_model=APIKeyResponse,
    status_code=status.HTTP_200_OK,
)
@permission_required("view_api_key")
async def get_api_key(
    key_id: UUID,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(get_current_user),
    request = Request,
):
    """
    Retrieve a single API key by ID.
    """
    return await api_key_service.get_api_key(
        db=db, api_key_id=key_id, actor=actor, request=request
    )


# --------------------------------------------------------
# LIST ALL API KEYS
# --------------------------------------------------------
@api_key_router.get(
    "/",
    response_model=List[APIKeyResponse],
    status_code=status.HTTP_200_OK,
)
@permission_required("view_api_key")
async def list_api_keys(
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(get_current_user),
    request = Request,
):
    """
    Retrieve a list of all API keys.
    """
    return await api_key_service.list_api_keys(
        db=db, actor=actor, request=request
    )


# --------------------------------------------------------
# UPDATE API KEY
# --------------------------------------------------------
@api_key_router.put(
    "/{key_id}",
    response_model=APIKeyResponse,
    status_code=status.HTTP_200_OK,
)
@permission_required("update_api_key")
async def update_api_key(
    key_id: UUID,
    data: APIKeyUpdate,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(get_current_user),
    request = Request,
):
    """
    Update an API key's status, expiration date, or permissions.
    """
    return await api_key_service.update_api_key(
        db=db,
        api_key_id=key_id,
        api_key_in=data,
        actor=actor,
        request=request,
    )


# --------------------------------------------------------
# DELETE API KEY
# --------------------------------------------------------
@api_key_router.delete(
    "/{key_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
@permission_required("delete_api_key")
async def delete_api_key(
    key_id: UUID,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(get_current_user),
    request = Request,
):
    """
    Delete an API key.
    """
    await api_key_service.delete_api_key(
        db=db,
        api_key_id=key_id,
        actor=actor,
        request=request,
    )
    return None
