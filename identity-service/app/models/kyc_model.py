from sqlalchemy import Column, String, Date, Text, Enum, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.models.base_model import BaseModel
import enum


class KYCStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class KYCVerification(BaseModel):
    __tablename__ = "kyc_verifications"

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    full_name = Column(String(255), nullable=True)
    date_of_birth = Column(Date, nullable=True)
    nationality = Column(String(100), nullable=True, index=True)
    address_line1 = Column(String(255), nullable=True)
    address_line2 = Column(String(255), nullable=True)
    city = Column(String(100), nullable=True, index=True)
    state = Column(String(100), nullable=True, index=True)
    postal_code = Column(String(20), nullable=True)
    country = Column(String(100), nullable=True)
    document_type = Column(String(50), nullable=True)
    document_number = Column(String(100), nullable=True)
    document_image_url = Column(String(500), nullable=True)
    selfie_image_url = Column(String(500), nullable=True)
    kyc_notes = Column(Text, nullable=True)
    status = Column(Enum(KYCStatus, values_callable=lambda x: [e.value for e in x]), default=KYCStatus.PENDING, index=True)

    # Relationship
    user = relationship("User", back_populates="kyc_verifications")
