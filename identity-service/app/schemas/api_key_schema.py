from __future__ import annotations
from typing import Optional, List
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field
from app.schemas.permission_schema import PermissionResponse


class APIKeyBase(BaseModel):
    user_id: UUID
    key_hash: str
    secret: str
    is_active: bool = True
    expires_at: Optional[datetime] = None


class APIKeyCreate(APIKeyBase):
    permissions: Optional[List[UUID]] = None


class APIKeyUpdate(BaseModel):
    is_active: Optional[bool] = None
    expires_at: Optional[datetime] = None
    permissions: Optional[List[UUID]] = None


class APIKeyResponse(APIKeyBase):
    id: UUID
    date_created: datetime
    date_updated: datetime
    permissions: List[PermissionResponse] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)
