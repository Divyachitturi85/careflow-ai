from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, ForeignKey, Index, UniqueConstraint
from sqlalchemy.orm import relationship
from app.models.base import BaseModel

class Doctor(BaseModel):
    __tablename__ = "doctors"

    hospital_id = Column(String(36), ForeignKey("hospitals.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    name = Column(String(100), nullable=False, index=True)
    specialty_id = Column(String(36), ForeignKey("specialties.id", ondelete="SET NULL"), nullable=True, index=True)
    department_id = Column(String(36), ForeignKey("departments.id", ondelete="SET NULL"), nullable=True)
    qualification = Column(String(100), nullable=True)
    experience_years = Column(Integer, default=5)
    languages = Column(String(200), default="English")
    consultation_fee = Column(Float, default=100.0)
    status = Column(String(50), default="ACTIVE", nullable=False, index=True)  # INVITED, ACTIVE, INACTIVE, SUSPENDED
    external_provider_id = Column(String(100), nullable=True, index=True)  # EXT-DOC-xxx

    # Relationships
    user = relationship("User", back_populates="doctor_profile")
    hospital = relationship("Hospital", back_populates="doctors")
    specialty = relationship("Specialty", back_populates="doctors")
    department = relationship("Department", back_populates="doctors")
    calendars = relationship("Calendar", back_populates="doctor", cascade="all, delete-orphan")
    availability_slots = relationship("AvailabilitySlot", back_populates="doctor", cascade="all, delete-orphan")
    blocked_slots = relationship("BlockedSlot", back_populates="doctor", cascade="all, delete-orphan")
    appointments = relationship("Appointment", back_populates="doctor")

class Calendar(BaseModel):
    __tablename__ = "calendars"

    hospital_id = Column(String(36), ForeignKey("hospitals.id", ondelete="CASCADE"), nullable=False, index=True)
    doctor_id = Column(String(36), ForeignKey("doctors.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(100), default="Primary Schedule", nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    # Relationships
    doctor = relationship("Doctor", back_populates="calendars")
    slots = relationship("AvailabilitySlot", back_populates="calendar", cascade="all, delete-orphan")

class AvailabilitySlot(BaseModel):
    __tablename__ = "availability_slots"

    hospital_id = Column(String(36), ForeignKey("hospitals.id", ondelete="CASCADE"), nullable=False, index=True)
    doctor_id = Column(String(36), ForeignKey("doctors.id", ondelete="CASCADE"), nullable=False, index=True)
    calendar_id = Column(String(36), ForeignKey("calendars.id", ondelete="CASCADE"), nullable=True, index=True)
    
    start_time = Column(DateTime(timezone=True), nullable=False, index=True)
    end_time = Column(DateTime(timezone=True), nullable=False, index=True)
    is_booked = Column(Boolean, default=False, nullable=False, index=True)
    is_blocked = Column(Boolean, default=False, nullable=False, index=True)

    # Relationships
    hospital = relationship("Hospital")
    doctor = relationship("Doctor", back_populates="availability_slots")
    calendar = relationship("Calendar", back_populates="slots")
    appointment = relationship("Appointment", back_populates="slot", uselist=False)

    __table_args__ = (
        UniqueConstraint("doctor_id", "start_time", name="uq_doctor_slot_time"),
        Index("idx_slots_lookup", "hospital_id", "doctor_id", "start_time", "is_booked"),
    )

class BlockedSlot(BaseModel):
    __tablename__ = "blocked_slots"

    hospital_id = Column(String(36), ForeignKey("hospitals.id", ondelete="CASCADE"), nullable=False, index=True)
    doctor_id = Column(String(36), ForeignKey("doctors.id", ondelete="CASCADE"), nullable=False, index=True)
    start_time = Column(DateTime(timezone=True), nullable=False, index=True)
    end_time = Column(DateTime(timezone=True), nullable=False, index=True)
    reason = Column(String(255), nullable=True)

    # Relationships
    doctor = relationship("Doctor", back_populates="blocked_slots")
