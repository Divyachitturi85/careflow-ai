from typing import Optional, Dict, Any
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.models.user import User, Patient, PatientPreference, HospitalStaff
from app.models.doctor import Doctor
from app.schemas.auth import LoginRequest, RegisterRequest, Token, UserResponse
from app.security.auth import verify_password, get_password_hash, create_access_token
from app.security.tenant import get_user_hospital_id

class AuthService:
    @staticmethod
    def authenticate_user(db: Session, login_data: LoginRequest) -> Token:
        user = db.query(User).filter(User.email == login_data.email).first()
        if not user or not verify_password(login_data.password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account has been deactivated. Please contact support."
            )

        hospital_id = get_user_hospital_id(user, db)

        token_payload = {
            "sub": user.id,
            "email": user.email,
            "role": user.role,
            "hospital_id": hospital_id,
        }
        access_token = create_access_token(data=token_payload)

        return Token(
            access_token=access_token,
            token_type="bearer",
            expires_in_minutes=1440,
            role=user.role,
            user_id=user.id,
            email=user.email,
            hospital_id=hospital_id
        )

    @staticmethod
    def register_user(db: Session, reg_data: RegisterRequest) -> UserResponse:
        existing = db.query(User).filter(User.email == reg_data.email).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A user with this email address already exists."
            )

        # Create user
        new_user = User(
            email=reg_data.email,
            hashed_password=get_password_hash(reg_data.password),
            role=reg_data.role,
            first_name=reg_data.first_name,
            last_name=reg_data.last_name,
            phone=reg_data.phone,
            is_active=True
        )
        db.add(new_user)
        db.flush()

        patient_id = None
        # If registering as a patient, automatically create patient profile and preferences
        if reg_data.role == "PATIENT":
            patient = Patient(
                user_id=new_user.id,
                dob=reg_data.dob,
                gender=reg_data.gender,
                address=reg_data.address,
                external_patient_id=f"EXT-PAT-{new_user.id[:8].upper()}"
            )
            db.add(patient)
            db.flush()
            patient_id = patient.id

            prefs = PatientPreference(
                patient_id=patient.id,
                preferred_channel="VOICE",
                preferred_time_of_day="AFTERNOON",
            )
            db.add(prefs)

        db.commit()
        db.refresh(new_user)

        return UserResponse(
            id=new_user.id,
            email=new_user.email,
            role=new_user.role,
            first_name=new_user.first_name,
            last_name=new_user.last_name,
            phone=new_user.phone,
            is_active=new_user.is_active,
            patient_id=patient_id
        )

    @staticmethod
    def get_user_profile(db: Session, user: User) -> UserResponse:
        hospital_id = get_user_hospital_id(user, db)
        patient_id = user.patient_profile.id if user.patient_profile else None
        doctor_id = user.doctor_profile.id if user.doctor_profile else None

        return UserResponse(
            id=user.id,
            email=user.email,
            role=user.role,
            first_name=user.first_name,
            last_name=user.last_name,
            phone=user.phone,
            is_active=user.is_active,
            hospital_id=hospital_id,
            patient_id=patient_id,
            doctor_id=doctor_id
        )
