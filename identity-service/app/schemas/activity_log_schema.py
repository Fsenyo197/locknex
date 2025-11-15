from pydantic import BaseModel, ConfigDict
from uuid import UUID
from datetime import datetime
from typing import Optional


class ActivityLogBase(BaseModel):
    user_id: UUID
    activity_type: str
    description: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None


class ActivityLogCreate(ActivityLogBase):
    pass


class ActivityLogResponse(ActivityLogBase):
    id: UUID
    timestamp: datetime

    model_config = ConfigDict(from_attributes=True)
