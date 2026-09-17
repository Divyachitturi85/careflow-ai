from typing import Any, Dict, Optional
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from app.capabilities.base import BaseCapability
from app.schemas.appointment import (
    CreateAppointmentRequest,
    RescheduleAppointmentRequest,
    CancelAppointmentRequest,
)
from app.services.appointment_service import AppointmentService

class CreateAppointmentInput(BaseModel):
    slot_id: str = Field(..., description="ID of the real availability slot to book")
    patient_id: Optional[str] = Field(None, description="Patient ID")
    reason_for_visit: Optional[str] = Field(None, description="Symptom or visit reason")
    appointment_type: str = Field("IN_PERSON", description="Visit type")

class CreateAppointmentCapability(BaseCapability):
    name = "create_appointment"
    description = "Books an appointment through the full pipeline: slot reservation, Mock EHR call, external verification, and state synchronization."
    parameters_schema = CreateAppointmentInput

    def execute(
        self,
        db: Session,
        current_user: Any,
        context: Dict[str, Any],
        correlation_id: str,
        slot_id: str,
        patient_id: Optional[str] = None,
        reason_for_visit: Optional[str] = None,
        appointment_type: str = "IN_PERSON",
        **kwargs,
    ) -> Dict[str, Any]:
        req = CreateAppointmentRequest(
            slot_id=slot_id,
            patient_id=patient_id,
            reason_for_visit=reason_for_visit,
            appointment_type=appointment_type,
            correlation_id=correlation_id,
        )
        response = AppointmentService.create_appointment(db, req, current_user)
        return response.model_dump(mode="json")

class GetAppointmentInput(BaseModel):
    appointment_id: str = Field(..., description="Internal appointment UUID")

class GetAppointmentCapability(BaseCapability):
    name = "get_appointment"
    description = "Retrieve details, verification, and event status of a specific appointment."
    parameters_schema = GetAppointmentInput

    def execute(
        self,
        db: Session,
        current_user: Any,
        context: Dict[str, Any],
        correlation_id: str,
        appointment_id: str,
        **kwargs,
    ) -> Dict[str, Any]:
        response = AppointmentService.get_appointment(db, appointment_id, current_user)
        return response.model_dump(mode="json")

class ListAppointmentsCapability(BaseCapability):
    name = "list_appointments"
    description = "List all existing and past appointments for the active patient."

    def execute(
        self,
        db: Session,
        current_user: Any,
        context: Dict[str, Any],
        correlation_id: str,
        **kwargs,
    ) -> Dict[str, Any]:
        responses = AppointmentService.list_appointments(db, current_user)
        return {
            "count": len(responses),
            "appointments": [r.model_dump(mode="json") for r in responses],
        }

class RescheduleAppointmentInput(BaseModel):
    appointment_id: str = Field(..., description="ID of appointment to reschedule")
    new_slot_id: str = Field(..., description="ID of the new slot to move to")
    reason: Optional[str] = Field(None, description="Reason for reschedule")

class RescheduleAppointmentCapability(BaseCapability):
    name = "reschedule_appointment"
    description = "Reschedule an existing appointment to a new available slot."
    parameters_schema = RescheduleAppointmentInput

    def execute(
        self,
        db: Session,
        current_user: Any,
        context: Dict[str, Any],
        correlation_id: str,
        appointment_id: str,
        new_slot_id: str,
        reason: Optional[str] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        req = RescheduleAppointmentRequest(new_slot_id=new_slot_id, reason=reason)
        response = AppointmentService.reschedule_appointment(db, appointment_id, req, current_user)
        return response.model_dump(mode="json")

class CancelAppointmentInput(BaseModel):
    appointment_id: str = Field(..., description="ID of appointment to cancel")
    reason: Optional[str] = Field("Patient requested cancellation", description="Cancellation reason")

class CancelAppointmentCapability(BaseCapability):
    name = "cancel_appointment"
    description = "Cancel an existing appointment and release its availability slot."
    parameters_schema = CancelAppointmentInput

    def execute(
        self,
        db: Session,
        current_user: Any,
        context: Dict[str, Any],
        correlation_id: str,
        appointment_id: str,
        reason: Optional[str] = "Patient requested cancellation",
        **kwargs,
    ) -> Dict[str, Any]:
        req = CancelAppointmentRequest(reason=reason)
        response = AppointmentService.cancel_appointment(db, appointment_id, req, current_user)
        return response.model_dump(mode="json")
