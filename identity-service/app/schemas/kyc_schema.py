from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import date, datetime
from uuid import UUID
from enum import Enum


class KYCStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class KYCVerificationBase(BaseModel):
    full_name: Optional[str] = None
    date_of_birth: Optional[date] = None
    nationality: Optional[str] = None
    address_line1: Optional[str] = None
    address_line2: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    postal_code: Optional[str] = None
    country: Optional[str] = None
    document_type: Optional[str] = None
    document_number: Optional[str] = None
    document_image_url: Optional[str] = None
    selfie_image_url: Optional[str] = None
    kyc_notes: Optional[str] = None
    status: Optional[KYCStatus] = KYCStatus.PENDING


class KYCVerificationCreate(KYCVerificationBase):
    pass


class KYCVerificationUpdate(KYCVerificationBase):
    pass


class KYCVerificationResponse(KYCVerificationBase):
    id: UUID
    date_created: datetime
    date_updated: datetime

    model_config = ConfigDict(from_attributes=True)
