from sqlalchemy import Column, String, Integer, Boolean, ForeignKey, Index, Text, DateTime
from sqlalchemy.orm import relationship
from app.models.base import BaseModel

class Questionnaire(BaseModel):
    __tablename__ = "questionnaires"

    hospital_id = Column(String(36), ForeignKey("hospitals.id", ondelete="CASCADE"), nullable=False, index=True)
    specialty_id = Column(String(36), ForeignKey("specialties.id", ondelete="SET NULL"), nullable=True, index=True)
    doctor_id = Column(String(36), ForeignKey("doctors.id", ondelete="SET NULL"), nullable=True, index=True)
    title = Column(String(200), nullable=False)
    description = Column(String(500), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)

    # Relationships
    hospital = relationship("Hospital", back_populates="questionnaires")
    specialty = relationship("Specialty", back_populates="questionnaires")
    questions = relationship("QuestionnaireQuestion", back_populates="questionnaire", cascade="all, delete-orphan", order_by="QuestionnaireQuestion.order_index")
    responses = relationship("QuestionnaireResponse", back_populates="questionnaire")

class QuestionnaireQuestion(BaseModel):
    __tablename__ = "questionnaire_questions"

    questionnaire_id = Column(String(36), ForeignKey("questionnaires.id", ondelete="CASCADE"), nullable=False, index=True)
    order_index = Column(Integer, default=0, nullable=False)
    prompt = Column(String(500), nullable=False)
    question_type = Column(String(50), nullable=False)  # YES_NO, CHOICE, MULTIPLE_CHOICE, NUMERIC, SHORT_TEXT
    options_json = Column(Text, nullable=True)  # JSON array for choices e.g. ["Shoulder", "Knee", "Hip"]
    is_required = Column(Boolean, default=True, nullable=False)

    # Relationships
    questionnaire = relationship("Questionnaire", back_populates="questions")

class QuestionnaireResponse(BaseModel):
    __tablename__ = "questionnaire_responses"

    questionnaire_id = Column(String(36), ForeignKey("questionnaires.id", ondelete="CASCADE"), nullable=False, index=True)
    appointment_id = Column(String(36), ForeignKey("appointments.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    patient_id = Column(String(36), ForeignKey("patients.id", ondelete="CASCADE"), nullable=False, index=True)
    answers_json = Column(Text, nullable=False)  # JSON mapping question_id -> answer
    status = Column(String(50), default="COMPLETED", nullable=False, index=True)  # PENDING, COMPLETED
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    questionnaire = relationship("Questionnaire", back_populates="responses")
    appointment = relationship("Appointment", back_populates="questionnaire_response")
