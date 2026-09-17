from sqlalchemy import Column, String, Boolean, ForeignKey, Index
from sqlalchemy.orm import relationship
from app.models.base import BaseModel

class User(BaseModel):
    __tablename__ = "users"

    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    role = Column(String(50), nullable=False, index=True)  # PLATFORM_ADMIN, HOSPITAL_ADMIN, DOCTOR, PATIENT
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    phone = Column(String(30), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)

    # Relationships
    patient_profile = relationship("Patient", back_populates="user", uselist=False, cascade="all, delete-orphan")
    doctor_profile = relationship("Doctor", back_populates="user", uselist=False)
    hospital_staff = relationship("HospitalStaff", back_populates="user", uselist=False)

class HospitalStaff(BaseModel):
    __tablename__ = "hospital_staff"

    hospital_id = Column(String(36), ForeignKey("hospitals.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    role_in_hospital = Column(String(50), default="ADMIN", nullable=False)

    # Relationships
    user = relationship("User", back_populates="hospital_staff")
    hospital = relationship("Hospital", back_populates="staff_members")

    __table_args__ = (
        Index("idx_staff_hospital_user", "hospital_id", "user_id"),
    )

class Patient(BaseModel):
    __tablename__ = "patients"

    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    dob = Column(String(20), nullable=True)
    gender = Column(String(20), nullable=True)
    address = Column(String(255), nullable=True)
    external_patient_id = Column(String(100), nullable=True, index=True)  # EXT-PAT-xxx mapped to Mock EHR

    # Relationships
    user = relationship("User", back_populates="patient_profile")
    preferences = relationship("PatientPreference", back_populates="patient", uselist=False, cascade="all, delete-orphan")
    appointments = relationship("Appointment", back_populates="patient")
    conversations = relationship("AIConversation", back_populates="patient")

class PatientPreference(BaseModel):
    __tablename__ = "patient_preferences"

    patient_id = Column(String(36), ForeignKey("patients.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    preferred_channel = Column(String(50), default="VOICE", nullable=False)  # VOICE, SMS, EMAIL, WEB
    preferred_time_of_day = Column(String(50), default="MORNING", nullable=True)  # MORNING, AFTERNOON, EVENING
    notes = Column(String(500), nullable=True)

    # Relationships
    patient = relationship("Patient", back_populates="preferences")
