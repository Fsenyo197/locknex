from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from uuid import UUID
from app.db import get_db
from app.schemas.user_schema import UserCreate, UserUpdate, UserResponse
from app.services.user_service import UserService
from app.utils.current_user import get_current_user

user_router = APIRouter(prefix="/users", tags=["Users"])


# -------------------------
# Create User
# -------------------------
@user_router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    request : Request,
    user_in: UserCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user)
):
    return await UserService.create_user(
        db, user_in, current_user=current_user, request=request
    )


# -------------------------
# Get Single User
# -------------------------
@user_router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    request : Request,
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return await UserService.get_user_by_id(
        db, user_id, current_user=current_user, request=request
    )


# -------------------------
# List Users
# -------------------------
@user_router.get("/", response_model=List[UserResponse])
async def list_users(
    request : Request,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user)
):
    return await UserService.list_users(
        db, current_user=current_user, skip=skip, limit=limit, request=request
    )


# -------------------------
# Update User
# -------------------------
@user_router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    request : Request,
    user_id: UUID,
    user_in: UserUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user)
):
    user = await UserService.get_user_by_id(
        db, user_id, current_user=current_user, request=request
    )
    return await UserService.update_user(
        db, user, user_in, current_user=current_user, request=request
    )


# -------------------------
# Delete User
# -------------------------
@user_router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    request : Request,
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user)
):
    user = await UserService.get_user_by_id(
        db, user_id, current_user=current_user, request=request
    )
    await UserService.delete_user(
        db, user, current_user=current_user, request=request
    )
    return None
