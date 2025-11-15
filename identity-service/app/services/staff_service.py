from typing import Optional, cast, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException, status, Request
from uuid import UUID
from app.models.staff_model import Staff, StaffRole, Department
from app.schemas.staff_schema import StaffCreate, StaffUpdate
from app.services.restriction_service import RestrictionService
from app.utils.activity_logger import log_activity


# ---------------- CREATE STAFF ---------------- #
async def create_staff(
    db: AsyncSession,
    staff_data: StaffCreate,
    actor: Optional[Staff] = None,
    request: Optional[Request] = None
):
    try:
        model_role = None
        model_department = None

        if getattr(staff_data, "role", None) is not None:
            try:
                model_role = StaffRole[staff_data.role.name]
            except Exception:
                model_role = StaffRole(
                    staff_data.role.value if hasattr(staff_data.role, "value") else staff_data.role
                )

        if getattr(staff_data, "department", None) is not None:
            try:
                model_department = Department[staff_data.department.name]
            except Exception:
                model_department = Department(
                    staff_data.department.value if hasattr(staff_data.department, "value") else staff_data.department
                )

        # ✅ await restriction check
        await RestrictionService.ensure_single_superuser(
            db,
            cast(StaffRole, model_role),
            cast(Department, model_department)
        )

        dept_value = (
            staff_data.department.value
            if getattr(staff_data, "department", None) and hasattr(staff_data.department, "value")
            else staff_data.department
        )
        role_value = (
            staff_data.role.value
            if getattr(staff_data, "role", None) and hasattr(staff_data.role, "value")
            else staff_data.role
        )

        new_staff = Staff(
            user_id=staff_data.user_id,
            department=dept_value,
            role=role_value,
            permissions=staff_data.permissions,
        )

        db.add(new_staff)
        await db.commit()
        await db.refresh(new_staff)

        await log_activity(
            db,
            target_user=new_staff.user,
            activity_type="create_staff_success",
            request=request,
            current_user=actor.user if actor else None,
            description=f"Staff {new_staff.id} created by {actor.user.username if actor else 'system'}"
        )

        return new_staff

    except HTTPException:
        raise
    except Exception as e:
        await log_activity(
            db,
            target_user=actor.user if actor else None,
            activity_type="create_staff_error",
            request=request,
            current_user=actor.user if actor else None,
            description=str(e)
        )
        raise


# ---------------- GET STAFF ---------------- #
async def get_staff(
    db: AsyncSession,
    staff_id: UUID,
    actor: Optional[Staff] = None,
    request: Optional[Request] = None
):
    result = await db.execute(select(Staff).filter(Staff.id == staff_id))
    staff = result.scalars().first()
    if not staff:
        await log_activity(
            db,
            target_user=actor.user if actor else None,
            activity_type="get_staff_failed",
            request=request,
            current_user=actor.user if actor else None,
            description=f"Staff {staff_id} not found"
        )
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Staff not found")

    if actor:
        await RestrictionService.enforce(actor, staff, action="view")

    await log_activity(
        db,
        target_user=staff.user,
        activity_type="get_staff_success",
        request=request,
        current_user=actor.user if actor else None,
        description=f"Staff {staff.id} retrieved by {actor.user.username if actor else 'system'}"
    )

    return staff


# ---------------- LIST STAFF ---------------- #
async def list_staff(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 50,
    actor: Optional[Staff] = None,
    request: Optional[Request] = None
):
    result = await db.execute(select(Staff).offset(skip).limit(limit))
    staff_list = result.scalars().all()

    await log_activity(
        db,
        target_user=actor.user if actor else None,
        activity_type="list_staff",
        request=request,
        current_user=actor.user if actor else None,
        description=f"Listed {len(staff_list)} staff records"
    )

    return staff_list


# ---------------- UPDATE STAFF ---------------- #
async def update_staff(
    db: AsyncSession,
    staff_id: UUID,
    staff_data: StaffUpdate,
    actor: Staff,
    request: Optional[Request] = None
):
    try:
        staff = await get_staff(db, staff_id, actor=actor, request=request)
        await RestrictionService.enforce(actor, staff, action="edit")

        if (getattr(staff_data, "role", None) == StaffRole.SUPERUSER) or (
            getattr(staff_data, "department", None) == Department.SUPERUSER
        ):
            await log_activity(
                db,
                target_user=actor.user,
                activity_type="update_staff_denied",
                request=request,
                current_user=actor.user,
                description="Attempt to assign SUPERUSER role/department denied"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot assign SUPERUSER role/department"
            )

        if staff_data.department is not None:
            dept_val = (
                staff_data.department.value if hasattr(staff_data.department, "value") else staff_data.department
            )
            cast(Any, staff).department = str(dept_val) if dept_val is not None else None

        if staff_data.role is not None:
            role_val = staff_data.role.value if hasattr(staff_data.role, "value") else staff_data.role
            cast(Any, staff).role = str(role_val) if role_val is not None else None

        if staff_data.permissions is not None:
            staff.permissions = staff_data.permissions

        await db.commit()
        await db.refresh(staff)

        await log_activity(
            db,
            target_user=staff.user,
            activity_type="update_staff_success",
            request=request,
            current_user=actor.user,
            description=f"Staff {staff.id} updated by {actor.user.username}"
        )

        return staff

    except HTTPException:
        raise
    except Exception as e:
        await log_activity(
            db,
            target_user=actor.user,
            activity_type="update_staff_error",
            request=request,
            current_user=actor.user,
            description=str(e)
        )
        raise


# ---------------- DELETE STAFF ---------------- #
async def delete_staff(
    db: AsyncSession,
    staff_id: UUID,
    actor: Staff,
    request: Optional[Request] = None
):
    try:
        staff = await get_staff(db, staff_id, actor=actor, request=request)
        await RestrictionService.enforce(actor, staff, action="delete")

        await db.delete(staff)
        await db.commit()

        await log_activity(
            db,
            target_user=staff.user,
            activity_type="delete_staff_success",
            request=request,
            current_user=actor.user,
            description=f"Staff {staff.id} deleted by {actor.user.username}"
        )

        return {"message": "Staff deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        await log_activity(
            db,
            target_user=actor.user,
            activity_type="delete_staff_error",
            request=request,
            current_user=actor.user,
            description=str(e)
        )
        raise
