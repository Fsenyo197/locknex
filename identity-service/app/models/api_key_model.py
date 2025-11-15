from sqlalchemy import Column, String, DateTime, Boolean, ForeignKey, Table
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.models.base_model import BaseModel


class APIKey(BaseModel):
    __tablename__ = "api_keys"

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    key_hash = Column(String(255), nullable=False, index=True)
    secret = Column(String(128), nullable=False, index=True)
    is_active = Column(Boolean, default=True, index=True)
    expires_at = Column(DateTime, nullable=True, index=True)

    user = relationship("User", back_populates="api_keys")
    permissions = relationship("Permission", secondary="api_key_permissions")


api_key_permissions = Table(
    "api_key_permissions",
    BaseModel.metadata,
    Column("api_key_id", ForeignKey("api_keys.id", ondelete="CASCADE"), primary_key=True, index=True),
    Column("permission_id", ForeignKey("permissions.id", ondelete="CASCADE"), primary_key=True, index=True),
)
