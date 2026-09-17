from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field

class AppointmentEventResponse(BaseModel):
    id: str
    event_type: str
    from_status: Optional[str] = None
    to_status: str
    metadata_json: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class AppointmentResponse(BaseModel):
    id: str
    hospital_id: str
    hospital_name: str
    patient_id: str
    patient_name: str
    doctor_id: str
    doctor_name: str
    specialty: str
    slot_id: str
    start_time: datetime
    end_time: datetime
    status: str
    appointment_type: str
    reason_for_visit: Optional[str] = None
    external_appointment_id: Optional[str] = None
    idempotency_key: Optional[str] = None
    correlation_id: str
    created_at: datetime
    events: List[AppointmentEventResponse] = []

    model_config = ConfigDict(from_attributes=True)

class CreateAppointmentRequest(BaseModel):
    slot_id: str = Field(..., description="ID of the validated availability slot")
    patient_id: Optional[str] = Field(None, description="Target patient ID (inferred from auth if omitted)")
    appointment_type: str = Field("IN_PERSON", description="Consultation type")
    reason_for_visit: Optional[str] = Field(None, description="Chief complaint or visit reason")
    idempotency_key: Optional[str] = Field(None, description="Client idempotency key")
    correlation_id: Optional[str] = Field(None, description="Distributed correlation ID")

class RescheduleAppointmentRequest(BaseModel):
    new_slot_id: str = Field(..., description="ID of the newly selected available slot")
    reason: Optional[str] = Field(None, description="Reason for rescheduling")

class CancelAppointmentRequest(BaseModel):
    reason: Optional[str] = Field("Patient requested cancellation", description="Reason for cancellation")

class VerifyAppointmentResponse(BaseModel):
    appointment_id: str
    external_appointment_id: Optional[str] = None
    is_verified: bool
    status: str
    details: str
