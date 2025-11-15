from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from uuid import UUID
from app.db import get_db
from app.schemas.staff_schema import StaffCreate, StaffUpdate, StaffResponse
from app.services import staff_service
from app.utils.permission import permission_required
from app.utils.current_user import get_current_user

staff_router = APIRouter(prefix="/staff", tags=["Staff"])


# -------------------------
# Create staff
# -------------------------
@staff_router.post("/", response_model=StaffResponse, status_code=status.HTTP_201_CREATED)
@permission_required("staff:create")
async def create_staff(
    staff_data: StaffCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user),
):
    return await staff_service.create_staff(db, staff_data, actor=current_user.staff)


# -------------------------
# Get staff by ID
# -------------------------
@staff_router.get("/{staff_id}", response_model=StaffResponse)
@permission_required("staff:read")
async def get_staff(
    staff_id: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user),
):
    return await staff_service.get_staff(db, staff_id, actor=current_user.staff)


# -------------------------
# List staff
# -------------------------
@staff_router.get("/", response_model=List[StaffResponse])
@permission_required("staff:list")
async def list_staff(
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user),
):
    return await staff_service.list_staff(db, actor=current_user.staff)


# -------------------------
# Update staff
# -------------------------
@staff_router.put("/{staff_id}", response_model=StaffResponse)
@permission_required("staff:update")
async def update_staff(
    staff_id: UUID,
    staff_data: StaffUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user),
):
    return await staff_service.update_staff(db, staff_id, staff_data, actor=current_user.staff)


# -------------------------
# Delete staff
# -------------------------
@staff_router.delete("/{staff_id}", status_code=status.HTTP_204_NO_CONTENT)
@permission_required("staff:delete")
async def delete_staff(
    staff_id: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user),
):
    return await staff_service.delete_staff(db, staff_id, actor=current_user.staff)
