from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.orm import Session
from uuid import UUID
from typing import List
from app.schemas.permission_schema import PermissionCreate, PermissionResponse
from app.services.permission_service import create_permission as svc_create_permission, get_permission as svc_get_permission, list_permissions as svc_list_permissions, update_permission as svc_update_permission, delete_permission as svc_delete_permission
from app.db import get_db
from app.models.user_model import User
from app.utils.current_user import get_current_user
from app.utils.permission import permission_required

permission_router = APIRouter(prefix="/permissions", tags=["Permissions"])


# -------------------------
# Create Permission
# -------------------------
@permission_router.post("/", response_model=PermissionResponse, status_code=status.HTTP_201_CREATED)
@permission_required("permission:create")
def create_permission(
    permission_in: PermissionCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    permission = svc_create_permission(db, permission_in)
    return permission


# -------------------------
# Get Permission by ID
# -------------------------
@permission_router.get("/{permission_id}", response_model=PermissionResponse)
@permission_required("permission:read")
def get_permission(
    permission_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    permission = svc_get_permission(db, permission_id)
    return permission


# -------------------------
# List Permissions
# -------------------------
@permission_router.get("/", response_model=List[PermissionResponse])
@permission_required("permission:list")
def list_permissions(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    permissions = svc_list_permissions(db)
    return permissions


# -------------------------
# Update Permission
# -------------------------
@permission_router.put("/{permission_id}", response_model=PermissionResponse)
@permission_required("permission:update")
def update_permission(
    permission_id: UUID,
    permission_in: PermissionCreate,  # Reuse create schema for updates
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    permission = svc_update_permission(db, permission_id, permission_in)
    return permission


# -------------------------
# Delete Permission
# -------------------------
@permission_router.delete("/{permission_id}", status_code=status.HTTP_204_NO_CONTENT)
@permission_required("permission:delete")
def delete_permission(
    permission_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc_delete_permission(db, permission_id)
    return {"detail": "Permission deleted successfully"}
