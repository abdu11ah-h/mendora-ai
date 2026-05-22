from pydantic import BaseModel, Field
from typing import Optional, List
from uuid import UUID
from datetime import datetime


class MoodLogCreate(BaseModel):
    mood: str
    emoji: Optional[str] = None
    stress_level: int = Field(ge=0, le=100)
    energy_level: Optional[int] = Field(None, ge=0, le=100)
    sleep_hours: Optional[float] = None
    mood_score: Optional[int] = Field(None, ge=0, le=100)
    journal_note: Optional[str] = None
    tags: Optional[List[str]] = None


class MoodLogResponse(BaseModel):
    id: UUID
    user_id: UUID
    mood: str
    emoji: Optional[str]
    stress_level: int
    energy_level: Optional[int]
    sleep_hours: Optional[float]
    mood_score: Optional[int]
    journal_note: Optional[str]
    tags: Optional[List[str]]
    logged_at: datetime

    model_config = {"from_attributes": True}


class ChatMessageResponse(BaseModel):
    id: UUID
    session_id: UUID
    role: str
    content: str
    detected_emotion: Optional[str]
    crisis_detected: bool
    gemini_used: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class ChatSessionResponse(BaseModel):
    id: UUID
    user_id: UUID
    title: Optional[str]
    is_active: bool
    crisis_flag: bool
    created_at: datetime
    updated_at: Optional[datetime]
    messages: List[ChatMessageResponse] = []

    model_config = {"from_attributes": True}


class ChatSessionCreate(BaseModel):
    title: Optional[str] = None


class SendMessageRequest(BaseModel):
    content: str = Field(min_length=1)
