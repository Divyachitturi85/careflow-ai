from typing import Optional
from pydantic import BaseModel, EmailStr, Field, ConfigDict

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in_minutes: int
    role: str
    user_id: str
    email: str
    hospital_id: Optional[str] = None

class TokenPayload(BaseModel):
    sub: str  # User ID
    email: str
    role: str
    hospital_id: Optional[str] = None

class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6)

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6)
    role: str = Field(default="PATIENT")  # PATIENT by default for self-registration
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    phone: Optional[str] = None
    dob: Optional[str] = None
    gender: Optional[str] = None
    address: Optional[str] = None

class UserResponse(BaseModel):
    id: str
    email: str
    role: str
    first_name: str
    last_name: str
    phone: Optional[str] = None
    is_active: bool
    hospital_id: Optional[str] = None
    patient_id: Optional[str] = None
    doctor_id: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
