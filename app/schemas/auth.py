from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from uuid import UUID
from datetime import datetime


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    role: str = Field(default="student", pattern="^(student|counselor|admin)$")
    university: Optional[str] = None
    department: Optional[str] = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class VerifyEmailRequest(BaseModel):
    token: str


class ResendVerificationRequest(BaseModel):
    email: EmailStr


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(min_length=8)


class UserProfile(BaseModel):
    id: UUID
    email: str
    first_name: str
    last_name: str
    role: str
    is_verified: bool
    is_active: bool
    avatar_url: Optional[str]
    university: Optional[str]
    department: Optional[str]
    created_at: datetime
    last_login: Optional[datetime]

    model_config = {"from_attributes": True}


class UpdateProfileRequest(BaseModel):
    first_name: Optional[str] = Field(None, max_length=100)
    last_name: Optional[str] = Field(None, max_length=100)
    avatar_url: Optional[str] = None
    university: Optional[str] = None
    department: Optional[str] = None
