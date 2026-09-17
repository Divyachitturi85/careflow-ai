from sqlalchemy import Column, String, Index, ForeignKey
from sqlalchemy.orm import relationship
from app.models.base import BaseModel

class Hospital(BaseModel):
    __tablename__ = "hospitals"

    name = Column(String(200), nullable=False, index=True)
    status = Column(String(50), default="SUBMITTED", nullable=False, index=True)  # DRAFT, SUBMITTED, UNDER_REVIEW, APPROVED, REJECTED, SUSPENDED
    city = Column(String(100), nullable=False, index=True)
    address = Column(String(255), nullable=True)
    phone = Column(String(50), nullable=True)
    email = Column(String(255), nullable=True)
    external_facility_id = Column(String(100), nullable=True, index=True)  # EXT-FAC-xxx

    # Relationships
    staff_members = relationship("HospitalStaff", back_populates="hospital", cascade="all, delete-orphan")
    departments = relationship("Department", back_populates="hospital", cascade="all, delete-orphan")
    specialties = relationship("Specialty", back_populates="hospital", cascade="all, delete-orphan")
    doctors = relationship("Doctor", back_populates="hospital", cascade="all, delete-orphan")
    appointments = relationship("Appointment", back_populates="hospital")
    questionnaires = relationship("Questionnaire", back_populates="hospital", cascade="all, delete-orphan")
    ehr_connection = relationship("HealthcareConnection", back_populates="hospital", uselist=False, cascade="all, delete-orphan")
    workflows = relationship("Workflow", back_populates="hospital", cascade="all, delete-orphan")

class Department(BaseModel):
    __tablename__ = "departments"

    hospital_id = Column(String(36), ForeignKey("hospitals.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    code = Column(String(50), nullable=True)
    description = Column(String(500), nullable=True)

    # Relationships
    hospital = relationship("Hospital", back_populates="departments")
    doctors = relationship("Doctor", back_populates="department")

    __table_args__ = (
        Index("idx_dept_hospital_name", "hospital_id", "name"),
    )

class Specialty(BaseModel):
    __tablename__ = "specialties"

    hospital_id = Column(String(36), ForeignKey("hospitals.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(100), nullable=False, index=True)  # e.g., Orthopedics, Cardiology
    code = Column(String(50), nullable=True)
    description = Column(String(500), nullable=True)

    # Relationships
    hospital = relationship("Hospital", back_populates="specialties")
    doctors = relationship("Doctor", back_populates="specialty")
    questionnaires = relationship("Questionnaire", back_populates="specialty")

    __table_args__ = (
        Index("idx_spec_hospital_name", "hospital_id", "name"),
    )
