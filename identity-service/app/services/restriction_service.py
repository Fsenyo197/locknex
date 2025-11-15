from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import cast
from app.models.staff_model import Staff, StaffRole, Department


class RestrictionService:
    # ---------------- CORE RESTRICTION ---------------- #
    @staticmethod
    async def enforce(actor: "Staff", target: "Staff", action: str):
        """
        Core restriction enforcement.
        Decides what staff can do to another staff based on their roles.
        Supported actions: 'view', 'edit', 'delete', 'create'
        """

        # Superuser restrictions
        if cast(StaffRole, getattr(target, "role")) == StaffRole.SUPERUSER:
            await RestrictionService._enforce_superuser_rules(actor, target, action)

        # Admin restrictions
        elif cast(StaffRole, getattr(target, "role")) == StaffRole.ADMIN:
            await RestrictionService._enforce_admin_rules(actor, target, action)

        # (Optional) Add more role-based restrictions here
        # elif cast(StaffRole, getattr(target, "role")) == StaffRole.MANAGER:
        #     await RestrictionService._enforce_manager_rules(...)

    # ---------------- SUPERUSER RULES ---------------- #
    @staticmethod
    async def _enforce_superuser_rules(actor: "Staff", target: "Staff", action: str):
        """
        Superuser rules:
        - Only the superuser can view/edit/delete their own record.
        - No one can change superuser `role` or `department`.
        """
        if cast(int, getattr(actor, "id")) != cast(int, getattr(target, "id")):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You cannot perform actions on another superuser."
            )

        if action == "edit":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Superuser's 'role' and 'department' cannot be edited."
            )

    # ---------------- ADMIN RULES ---------------- #
    @staticmethod
    async def _enforce_admin_rules(actor: "Staff", target: "Staff", action: str):
        """
        Admin rules:
        - Superuser can view/edit/delete/create Admins.
        - Other staff roles cannot manage Admins.
        """
        if cast(StaffRole, getattr(actor, "role")) == StaffRole.SUPERUSER:
            return  # Superuser can manage admins

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only superuser can manage admins."
        )

    # ---------------- CREATION RESTRICTIONS ---------------- #
    @staticmethod
    async def ensure_single_superuser(db: AsyncSession, role: StaffRole, department: Department):
        """
        Prevent creation of multiple superusers.
        Both role=superuser and department=superuser must remain unique.
        """
        # Check existing superuser role
        if role == StaffRole.SUPERUSER:
            result = await db.execute(select(Staff).filter(Staff.role == StaffRole.SUPERUSER))
            existing = result.scalars().first()
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="A superuser already exists."
                )

        # Check existing superuser department
        if department == Department.SUPERUSER:
            result = await db.execute(select(Staff).filter(Staff.department == Department.SUPERUSER))
            existing = result.scalars().first()
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="A superuser department already exists."
                )
