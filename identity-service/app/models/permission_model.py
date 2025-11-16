from sqlalchemy import Column, String, ForeignKey, Table
from sqlalchemy.orm import relationship
from app.models.base_model import BaseModel


class Permission(BaseModel):
    __tablename__ = "permissions"

    name = Column(String(100), unique=True, nullable=False, index=True)
    staffs = relationship("Staff", secondary="staff_permissions", back_populates="permissions")


StaffPermissions = Table(
    "staff_permissions",
    BaseModel.metadata,
    Column("staff_id", ForeignKey("staffs.id", ondelete="CASCADE"), primary_key=True, index=True),
    Column("permission_id", ForeignKey("permissions.id", ondelete="CASCADE"), primary_key=True, index=True),
)
