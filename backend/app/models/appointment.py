from sqlalchemy import Column, String, ForeignKey, Index, Text
from sqlalchemy.orm import relationship
from app.models.base import BaseModel

class Appointment(BaseModel):
    __tablename__ = "appointments"

    hospital_id = Column(String(36), ForeignKey("hospitals.id", ondelete="CASCADE"), nullable=False, index=True)
    patient_id = Column(String(36), ForeignKey("patients.id", ondelete="CASCADE"), nullable=False, index=True)
    doctor_id = Column(String(36), ForeignKey("doctors.id", ondelete="CASCADE"), nullable=False, index=True)
    slot_id = Column(String(36), ForeignKey("availability_slots.id", ondelete="RESTRICT"), unique=True, nullable=False, index=True)

    status = Column(
        String(50), 
        default="PENDING", 
        nullable=False, 
        index=True
    )  # REQUESTED, PENDING, CONFIRMED, RESCHEDULED, CANCELLED, COMPLETED, NO_SHOW, FAILED, SYNCHRONIZATION_PENDING, RECONCILIATION_REQUIRED

    appointment_type = Column(String(50), default="IN_PERSON", nullable=False)
    reason_for_visit = Column(String(500), nullable=True)
    
    # EHR Integration linkage
    external_appointment_id = Column(String(100), nullable=True, index=True)  # EXT-APT-xxx
    
    # Idempotency & Observability
    idempotency_key = Column(String(255), unique=True, nullable=True, index=True)
    correlation_id = Column(String(100), nullable=False, index=True)
    notes = Column(Text, nullable=True)

    # Relationships
    hospital = relationship("Hospital", back_populates="appointments")
    patient = relationship("Patient", back_populates="appointments")
    doctor = relationship("Doctor", back_populates="appointments")
    slot = relationship("AvailabilitySlot", back_populates="appointment")
    events = relationship("AppointmentEvent", back_populates="appointment", cascade="all, delete-orphan", order_by="AppointmentEvent.created_at")
    questionnaire_response = relationship("QuestionnaireResponse", back_populates="appointment", uselist=False)
    workflow_executions = relationship("WorkflowExecution", back_populates="appointment")

    __table_args__ = (
        Index("idx_appt_hospital_patient", "hospital_id", "patient_id"),
        Index("idx_appt_hospital_doctor", "hospital_id", "doctor_id"),
        Index("idx_appt_status", "status"),
    )

class AppointmentEvent(BaseModel):
    __tablename__ = "appointment_events"

    appointment_id = Column(String(36), ForeignKey("appointments.id", ondelete="CASCADE"), nullable=False, index=True)
    event_type = Column(String(100), nullable=False, index=True)  # STATUS_CHANGE, EHR_SUBMIT, EHR_VERIFY, RECONCILIATION
    from_status = Column(String(50), nullable=True)
    to_status = Column(String(50), nullable=False)
    metadata_json = Column(Text, nullable=True)  # JSON-encoded extra event data (correlation, error traces)

    # Relationships
    appointment = relationship("Appointment", back_populates="events")

    __table_args__ = (
        Index("idx_event_appt_created", "appointment_id", "created_at"),
    )
