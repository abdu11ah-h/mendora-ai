from sqlalchemy import Column, String, Boolean, DateTime, Text, Enum, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from uuid import uuid4
from app.database import Base


class CounselorNote(Base):
    __tablename__ = "counselor_notes"

    id           = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    counselor_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    student_id   = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    note         = Column(Text, nullable=False)
    is_private   = Column(Boolean, default=True)
    risk_level   = Column(Enum("low", "medium", "high", "critical", name="risk_level"), default="low")
    created_at   = Column(DateTime(timezone=True), server_default=func.now())


class RiskFlag(Base):
    __tablename__ = "risk_flags"

    id           = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    student_id   = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    triggered_by = Column(String(100))
    severity     = Column(Enum("low", "medium", "high", "critical", name="flag_severity"))
    message      = Column(Text)
    resolved     = Column(Boolean, default=False)
    resolved_at  = Column(DateTime(timezone=True), nullable=True)
    created_at   = Column(DateTime(timezone=True), server_default=func.now())
