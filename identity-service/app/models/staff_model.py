from sqlalchemy import Column, Enum, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import enum
from app.models.base_model import BaseModel


class StaffRole(str, enum.Enum):
    SUPERUSER = "superuser"
    ADMIN = "admin"
    SUPPORT = "support"
    COMPLIANCE = "compliance"
    MANAGER = "manager"
    GENERAL = "general"


class Department(str, enum.Enum):
    SUPERUSER = "superuser"
    FINANCE = "finance"
    MARKETING = "marketing"
    SUPPORT = "support"
    COMPLIANCE = "compliance"
    MANAGEMENT = "management"
    GENERAL = "general"


class Staff(BaseModel):
    __tablename__ = "staffs"

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    department = Column(Enum(Department, values_callable=lambda x: [e.value for e in x]), nullable=False, default=Department.GENERAL, index=True)
    role = Column(Enum(StaffRole, values_callable=lambda x: [e.value for e in x]), nullable=False, default=StaffRole.GENERAL, index=True)

    # --- Relationships ---
    permissions = relationship("Permission", secondary="staff_permissions", back_populates="staffs")
    user = relationship("User", back_populates="staff_profile")

    __table_args__ = (
        # Only one staff can ever have department=superuser
        Index(
            "uq_staff_superuser_department",
            "department",
            unique=True,
            postgresql_where=(department == Department.SUPERUSER)
        ),
    )
