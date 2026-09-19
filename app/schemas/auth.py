# app/schemas/auth.py

from pydantic import BaseModel, EmailStr
from typing import Optional
from app.models.user import UserRole


class UserCreate(BaseModel):
    full_name: str
    email: EmailStr
    password: str
    role: UserRole = UserRole.CUSTOMER


class UserUpdate(BaseModel):
    full_name: Optional[str] = None


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class OAuthGoogleRequest(BaseModel):
    id_token: str


class OAuthAppleRequest(BaseModel):
    id_token: str
    full_name: Optional[str] = None


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str


class VerifyEmailRequest(BaseModel):
    token: str


class ResendVerificationRequest(BaseModel):
    email: EmailStr


class UserResponse(BaseModel):
    id: int
    full_name: str
    email: EmailStr
    role: UserRole
    is_verified: bool

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str
    role: str
    user: UserResponse
    is_new_user: Optional[bool] = False