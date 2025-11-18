from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import cast
from app.models.staff_model import Staff, StaffRole, Department


class RestrictionService:

    SUPPORTED_ACTIONS = {"view", "edit", "delete", "create"}

    # ---------------- CORE ENFORCER ---------------- #
    @staticmethod
    async def enforce(actor: "Staff", target: "Staff", action: str):

        if action not in RestrictionService.SUPPORTED_ACTIONS:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported action '{action}'."
            )

        actor_role = cast(StaffRole, actor.role)
        target_role = cast(StaffRole, target.role)

        # SUPERUSER target
        if target_role == StaffRole.SUPERUSER:
            await RestrictionService._superuser_rules(actor, target, action)

        # ADMIN target
        elif target_role == StaffRole.ADMIN:
            await RestrictionService._admin_rules(actor, target, action)

        # NORMAL staff (target is neither admin nor superuser)
        else:
            await RestrictionService._normal_staff_rules(actor, target, action)

    # ---------------- SUPERUSER RULES ---------------- #
    @staticmethod
    async def _superuser_rules(actor: "Staff", target: "Staff", action: str):

        actor_id = cast(int, actor.id)
        target_id = cast(int, target.id)

        if actor_id != target_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You cannot perform actions on another superuser."
            )

        # Superuser editing own record:
        if action == "edit":
            # Allowed: updating profile fields
            # Blocked: changing role & department
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Superuser's 'role' and 'department' cannot be edited."
            )

        return

    # ---------------- ADMIN RULES ---------------- #
    @staticmethod
    async def _admin_rules(actor: "Staff", target: "Staff", action: str):

        actor_role = cast(StaffRole, actor.role)

        # Only superuser may manage admins
        if actor_role == StaffRole.SUPERUSER:
            return  # Full access to admins

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only superusers can manage admins."
        )

    # ---------------- NORMAL STAFF RULES ---------------- #
    @staticmethod
    async def _normal_staff_rules(actor: "Staff", target: "Staff", action: str):

        actor_role = cast(StaffRole, actor.role)

        # Admin can manage normal staff
        if actor_role == StaffRole.ADMIN:
            return

        # Superuser can manage anyone
        if actor_role == StaffRole.SUPERUSER:
            return

        # Normal staff cannot manage others
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to manage this staff member."
        )

    # ---------------- CREATION RESTRICTIONS ---------------- #
    @staticmethod
    async def ensure_single_superuser(db: AsyncSession, role: StaffRole, department: Department):

        # Block multiple superusers
        if role == StaffRole.SUPERUSER:
            result = await db.execute(
                select(Staff).filter(Staff.role == StaffRole.SUPERUSER)
            )
            existing = result.scalars().first()

            if existing:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="A superuser already exists."
                )

        # Prevent multiple superuser departments
        if department == Department.SUPERUSER:
            result = await db.execute(
                select(Staff).filter(Staff.department == Department.SUPERUSER)
            )
            existing = result.scalars().first()

            if existing:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="A superuser department already exists."
                )
