from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Index, Text
from sqlalchemy.orm import relationship
from app.models.base import BaseModel

class AIConversation(BaseModel):
    __tablename__ = "ai_conversations"

    patient_id = Column(String(36), ForeignKey("patients.id", ondelete="CASCADE"), nullable=False, index=True)
    channel = Column(String(50), default="WEB_VOICE", nullable=False)  # WEB_VOICE, WEB_CHAT
    status = Column(String(50), default="ACTIVE", nullable=False, index=True)  # ACTIVE, COMPLETED, ABANDONED
    summary = Column(String(500), nullable=True)

    # Relationships
    patient = relationship("Patient", back_populates="conversations")
    context = relationship("AIContext", back_populates="conversation", uselist=False, cascade="all, delete-orphan")
    capability_executions = relationship("CapabilityExecution", back_populates="conversation", cascade="all, delete-orphan")

class AIContext(BaseModel):
    __tablename__ = "ai_contexts"

    conversation_id = Column(String(36), ForeignKey("ai_conversations.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    patient_id = Column(String(36), ForeignKey("patients.id", ondelete="CASCADE"), nullable=False, index=True)
    
    current_intent = Column(String(100), nullable=True, index=True)
    selected_hospital_id = Column(String(36), nullable=True)
    selected_doctor_id = Column(String(36), nullable=True)
    selected_slot_id = Column(String(36), nullable=True)
    
    # Serialized working memory for clarification and slot resolution
    context_data_json = Column(Text, default="{}", nullable=False)

    # Relationships
    conversation = relationship("AIConversation", back_populates="context")

class CapabilityExecution(BaseModel):
    __tablename__ = "capability_executions"

    conversation_id = Column(String(36), ForeignKey("ai_conversations.id", ondelete="SET NULL"), nullable=True, index=True)
    correlation_id = Column(String(100), nullable=False, index=True)
    capability_name = Column(String(100), nullable=False, index=True)
    
    input_payload_json = Column(Text, nullable=True)
    output_payload_json = Column(Text, nullable=True)
    status = Column(String(50), nullable=False, index=True)  # SUCCESS, FAILED
    execution_ms = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)

    # Relationships
    conversation = relationship("AIConversation", back_populates="capability_executions")

    __table_args__ = (
        Index("idx_cap_name_status", "capability_name", "status"),
        Index("idx_cap_correlation", "correlation_id"),
    )
