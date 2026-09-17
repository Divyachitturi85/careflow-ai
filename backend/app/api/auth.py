from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import LoginRequest, RegisterRequest, Token, UserResponse
from app.services.auth_service import AuthService
from app.security.auth import get_current_user

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

@router.post("/login", response_model=Token)
def login(login_data: LoginRequest, db: Session = Depends(get_db)):
    """Authenticate with email and password to receive a JWT bearer token."""
    return AuthService.authenticate_user(db, login_data)

@router.post("/register", response_model=UserResponse)
def register(reg_data: RegisterRequest, db: Session = Depends(get_db)):
    """Register a new patient account."""
    return AuthService.register_user(db, reg_data)

@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get the currently authenticated user's profile and assigned role."""
    return AuthService.get_user_profile(db, current_user)
