from pydantic import StringConstraints, BaseModel, EmailStr, ConfigDict
from typing import Optional, Annotated
from uuid import UUID
from datetime import datetime, date
from enum import Enum
from app.schemas.kyc_schema import KYCVerificationResponse, KYCVerificationCreate, KYCVerificationUpdate
from typing_extensions import Annotated


class UserStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    PENDING_KYC = "pending_kyc"
    KYC_REJECTED = "kyc_rejected"


class CurrentUserResponse(BaseModel):
    id: UUID
    username: str
    email: str


# -----------------------------
# User Schemas
# -----------------------------
class UserBase(BaseModel):
    username: Annotated[str, Annotated[str, StringConstraints(min_length=3, max_length=50)]]
    email: EmailStr
    phone_number: str
    is_verified: bool = False
    is_staff: bool = False
    status: UserStatus = UserStatus.PENDING_KYC


class UserCreate(UserBase):
    password: Annotated[str, Annotated[str, StringConstraints(min_length=8)]]
    twofa_secret: Optional[str] = None
    kyc: Optional[KYCVerificationCreate] = None


class UserUpdate(BaseModel):
    username: Optional[Annotated[str, Annotated[str, StringConstraints(min_length=3, max_length=50)]]] = None
    email: Optional[EmailStr] = None
    phone_number: Optional[str] = None
    password: Optional[Annotated[str, Annotated[str, StringConstraints(min_length=8)]]] = None
    is_verified: Optional[bool] = None
    status: Optional[UserStatus] = None
    twofa_secret: Optional[str] = None
    kyc: Optional[KYCVerificationUpdate] = None


class UserResponse(UserBase):
    id: UUID
    date_created: datetime
    date_updated: datetime
    latest_kyc: Optional[KYCVerificationResponse] = None

    model_config = ConfigDict(from_attributes=True)
