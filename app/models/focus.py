from sqlalchemy import Column, String, Boolean, DateTime, Integer, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from uuid import uuid4
from app.database import Base


class FocusSession(Base):
    __tablename__ = "focus_sessions"

    id            = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id       = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    mode          = Column(String(50))
    duration_mins = Column(Integer)
    actual_mins   = Column(Integer, nullable=True)
    completed     = Column(Boolean, default=False)
    distractions  = Column(Integer, default=0)
    notes         = Column(Text, nullable=True)
    started_at    = Column(DateTime(timezone=True), server_default=func.now())
    ended_at      = Column(DateTime(timezone=True), nullable=True)

    user = relationship("User", back_populates="focus_sessions")
