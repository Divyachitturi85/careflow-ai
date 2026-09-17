from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field

class SlotResponse(BaseModel):
    slot_id: str
    doctor_id: str
    doctor_name: str
    hospital_id: str
    hospital_name: str
    specialty: str
    start_time: datetime
    end_time: datetime
    available: bool

    model_config = ConfigDict(from_attributes=True)

class SlotValidationResponse(BaseModel):
    slot_id: str
    is_valid: bool
    reason: Optional[str] = None
    slot: Optional[SlotResponse] = None

class BookSlotRequest(BaseModel):
    slot_id: str = Field(..., description="ID of the real availability slot to book")
    patient_id: Optional[str] = Field(None, description="Patient ID (defaults to current authenticated user's patient profile)")
    appointment_type: str = Field("IN_PERSON", description="Consultation type e.g. IN_PERSON, VIDEO")
    reason_for_visit: Optional[str] = Field(None, description="Reason or symptom summary")
    idempotency_key: Optional[str] = Field(None, description="Unique client key for idempotency")
    correlation_id: Optional[str] = Field(None, description="End-to-end operation tracking ID")
