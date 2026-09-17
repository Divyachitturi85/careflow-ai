from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from datetime import datetime

class QuestionSchema(BaseModel):
    id: str
    order_index: int
    prompt: str
    question_type: str
    options: Optional[List[str]] = None
    is_required: bool

class QuestionnaireSchema(BaseModel):
    id: str
    hospital_id: str
    title: str
    description: Optional[str] = None
    questions: List[QuestionSchema]

class SubmitResponseRequest(BaseModel):
    appointment_id: str
    answers: Dict[str, Any]

class QuestionnaireResponseSchema(BaseModel):
    id: str
    questionnaire_id: str
    appointment_id: str
    patient_id: str
    answers: Dict[str, Any]
    status: str
    completed_at: Optional[datetime] = None
