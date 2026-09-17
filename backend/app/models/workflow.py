from sqlalchemy import Column, String, Integer, Boolean, ForeignKey, Index, Text, DateTime
from sqlalchemy.orm import relationship
from app.models.base import BaseModel

class Workflow(BaseModel):
    __tablename__ = "workflows"

    hospital_id = Column(String(36), ForeignKey("hospitals.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    trigger_event = Column(String(100), nullable=False, index=True)  # APPOINTMENT_CONFIRMED, APPOINTMENT_CANCELLED
    is_active = Column(Boolean, default=True, nullable=False)

    # Relationships
    hospital = relationship("Hospital", back_populates="workflows")
    executions = relationship("WorkflowExecution", back_populates="workflow", cascade="all, delete-orphan")

class WorkflowExecution(BaseModel):
    __tablename__ = "workflow_executions"

    workflow_id = Column(String(36), ForeignKey("workflows.id", ondelete="CASCADE"), nullable=False, index=True)
    appointment_id = Column(String(36), ForeignKey("appointments.id", ondelete="CASCADE"), nullable=False, index=True)
    current_step = Column(String(100), nullable=False)  # ASSIGN_QUESTIONNAIRE, SCHEDULE_REMINDER, SEND_NOTIFICATIONS
    status = Column(String(50), default="RUNNING", nullable=False, index=True)  # RUNNING, COMPLETED, FAILED, RETRIED
    step_history_json = Column(Text, default="[]", nullable=False)
    retry_count = Column(Integer, default=0, nullable=False)
    executed_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    workflow = relationship("Workflow", back_populates="executions")
    appointment = relationship("Appointment", back_populates="workflow_executions")

class Notification(BaseModel):
    __tablename__ = "notifications"

    recipient_id = Column(String(36), nullable=False, index=True)  # User ID
    recipient_role = Column(String(50), nullable=False, index=True)  # PATIENT, DOCTOR, HOSPITAL_ADMIN, PLATFORM_ADMIN
    appointment_id = Column(String(36), ForeignKey("appointments.id", ondelete="SET NULL"), nullable=True, index=True)
    title = Column(String(200), nullable=False)
    body = Column(Text, nullable=False)
    channel = Column(String(50), default="IN_APP", nullable=False)  # IN_APP, EMAIL, SMS
    is_read = Column(Boolean, default=False, nullable=False, index=True)
