from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from uuid import UUID
from app.models.permission_model import Permission
from app.schemas.permission_schema import PermissionCreate


# -------------------------
# Create Permission
# -------------------------
def create_permission(db: Session, permission_in: PermissionCreate):
    existing_permission = db.query(Permission).filter(Permission.name == permission_in.name).first()
    if existing_permission:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Permission with name '{permission_in.name}' already exists.",
        )

    new_permission = Permission(name=permission_in.name)
    db.add(new_permission)
    db.commit()
    db.refresh(new_permission)
    return new_permission


# -------------------------
# Get Permission by ID
# -------------------------
def get_permission(db: Session, permission_id: UUID):
    permission = db.query(Permission).filter(Permission.id == permission_id).first()
    if not permission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Permission not found.",
        )
    return permission


# -------------------------
# List Permissions
# -------------------------
def list_permissions(db: Session):
    return db.query(Permission).order_by(Permission.date_created.desc()).all()


# -------------------------
# Update Permission
# -------------------------
def update_permission(db: Session, permission_id: UUID, permission_in: PermissionCreate):
    permission = db.query(Permission).filter(Permission.id == permission_id).first()
    if not permission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Permission not found.",
        )

    # Ensure name uniqueness
    existing = db.query(Permission).filter(
        Permission.name == permission_in.name,
        Permission.id != permission_id
    ).first()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Another permission with name '{permission_in.name}' already exists.",
        )

    setattr(permission, "name", permission_in.name)
    db.commit()
    db.refresh(permission)
    return permission


# -------------------------
# Delete Permission
# -------------------------
def delete_permission(db: Session, permission_id: UUID):
    permission = db.query(Permission).filter(Permission.id == permission_id).first()
    if not permission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Permission not found.",
        )

    db.delete(permission)
    db.commit()
