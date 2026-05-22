from pydantic import BaseModel, Field
from typing import Optional
from uuid import UUID
from datetime import datetime


class CounselorNoteCreate(BaseModel):
    student_id: UUID
    note: str = Field(min_length=1)
    is_private: bool = True
    risk_level: str = Field(default="low", pattern="^(low|medium|high|critical)$")


class CounselorNoteUpdate(BaseModel):
    note: Optional[str] = None
    is_private: Optional[bool] = None
    risk_level: Optional[str] = Field(None, pattern="^(low|medium|high|critical)$")


class CounselorNoteResponse(BaseModel):
    id: UUID
    counselor_id: UUID
    student_id: UUID
    note: str
    is_private: bool
    risk_level: str
    created_at: datetime

    model_config = {"from_attributes": True}


class RiskFlagResponse(BaseModel):
    id: UUID
    student_id: UUID
    triggered_by: str
    severity: str
    message: str
    resolved: bool
    resolved_at: Optional[datetime]
    created_at: datetime

    model_config = {"from_attributes": True}


class FocusSessionCreate(BaseModel):
    mode: str
    duration_mins: int = Field(gt=0)
    notes: Optional[str] = None


class FocusSessionUpdate(BaseModel):
    actual_mins: Optional[int] = None
    completed: Optional[bool] = None
    distractions: Optional[int] = None
    notes: Optional[str] = None
    ended_at: Optional[datetime] = None


class FocusSessionResponse(BaseModel):
    id: UUID
    user_id: UUID
    mode: str
    duration_mins: int
    actual_mins: Optional[int]
    completed: bool
    distractions: int
    notes: Optional[str]
    started_at: datetime
    ended_at: Optional[datetime]

    model_config = {"from_attributes": True}
