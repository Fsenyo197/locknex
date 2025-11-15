from pydantic import BaseModel, ConfigDict
from uuid import UUID
from datetime import datetime
from typing import Optional, List
from enum import Enum
from app.schemas.permission_schema import PermissionResponse


class StaffRole(str, Enum):
    SUPERUSER = "superuser"
    ADMIN = "admin"
    SUPPORT = "support"
    COMPLIANCE = "compliance"
    MANAGER = "manager"
    GENERAL = "General"

class Department(str, Enum):
    SUPERUSER = "superuser"
    FINANCE = "Finance"
    MARKETING = "Marketing"
    SUPPORT = "Support"
    COMPLIANCE = "Compliance"
    MANAGEMENT = "Management"
    GENERAL = "General"


class StaffBase(BaseModel):
    department: Department = Department.GENERAL
    role: StaffRole = StaffRole.GENERAL


class StaffCreate(StaffBase):
    user_id: UUID
    permissions: Optional[List[str]] = None


class StaffUpdate(BaseModel):
    department: Optional[Department] = None
    role: Optional[StaffRole] = None
    permissions: Optional[List[str]] = None


class StaffResponse(StaffBase):
    id: UUID
    user_id: UUID
    date_created: datetime
    date_updated: datetime
    permissions: List[PermissionResponse] = []

    model_config = ConfigDict(from_attributes=True)
