from sqlalchemy import Column, String, Boolean, DateTime, Integer, Float, Text, Enum, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from uuid import uuid4
from app.database import Base


class MoodLog(Base):
    __tablename__ = "mood_logs"

    id           = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id      = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    mood         = Column(String(50), nullable=False)
    emoji        = Column(String(10), nullable=True)
    stress_level = Column(Integer, nullable=False)
    energy_level = Column(Integer, nullable=True)
    sleep_hours  = Column(Float, nullable=True)
    mood_score   = Column(Integer, nullable=True)
    journal_note = Column(Text, nullable=True)
    tags         = Column(ARRAY(String), nullable=True)
    logged_at    = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="mood_logs")


class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id     = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    title       = Column(String(200), nullable=True)
    is_active   = Column(Boolean, default=True)
    crisis_flag = Column(Boolean, default=False)
    created_at  = Column(DateTime(timezone=True), server_default=func.now())
    updated_at  = Column(DateTime(timezone=True), onupdate=func.now())

    messages = relationship(
        "ChatMessage",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="ChatMessage.created_at",
    )
    user = relationship("User", back_populates="chat_sessions")


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id               = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    session_id       = Column(UUID(as_uuid=True), ForeignKey("chat_sessions.id", ondelete="CASCADE"))
    role             = Column(Enum("user", "ai", name="message_role"), nullable=False)
    content          = Column(Text, nullable=False)
    detected_emotion = Column(String(50), nullable=True)
    crisis_detected  = Column(Boolean, default=False)
    gemini_used      = Column(Boolean, default=False)
    created_at       = Column(DateTime(timezone=True), server_default=func.now())

    session = relationship("ChatSession", back_populates="messages")
