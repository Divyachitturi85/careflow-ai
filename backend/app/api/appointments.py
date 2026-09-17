from typing import List, Optional
from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.user import User
from app.security.auth import get_current_user
from app.schemas.appointment import (
    AppointmentResponse,
    CreateAppointmentRequest,
    RescheduleAppointmentRequest,
    CancelAppointmentRequest,
    VerifyAppointmentResponse,
)
from app.services.appointment_service import AppointmentService
from app.integrations.mock_ehr import mock_ehr_connector

router = APIRouter(prefix="/api/appointments", tags=["Appointments"])

@router.post("", response_model=AppointmentResponse)
def create_appointment(
    request: CreateAppointmentRequest,
    idempotency_key_header: Optional[str] = Header(None, alias="Idempotency-Key"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Book an appointment through controlled validation and Mock EHR integration.
    Supports Idempotency-Key header for duplicate prevention.
    """
    if idempotency_key_header and not request.idempotency_key:
        request.idempotency_key = idempotency_key_header

    return AppointmentService.create_appointment(db, request, current_user)

@router.get("", response_model=List[AppointmentResponse])
def list_appointments(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List appointments accessible to the current user based on RBAC and tenant role."""
    return AppointmentService.list_appointments(db, current_user)

@router.get("/{appointment_id}", response_model=AppointmentResponse)
def get_appointment(
    appointment_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieve full details of an appointment including state transitions and events."""
    return AppointmentService.get_appointment(db, appointment_id, current_user)

@router.post("/{appointment_id}/reschedule", response_model=AppointmentResponse)
def reschedule_appointment(
    appointment_id: str,
    request: RescheduleAppointmentRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Reschedule an existing appointment to a new available slot."""
    return AppointmentService.reschedule_appointment(db, appointment_id, request, current_user)

@router.post("/{appointment_id}/cancel", response_model=AppointmentResponse)
def cancel_appointment(
    appointment_id: str,
    request: CancelAppointmentRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Cancel an appointment and release its availability slot."""
    return AppointmentService.cancel_appointment(db, appointment_id, request, current_user)

@router.post("/{appointment_id}/verify", response_model=VerifyAppointmentResponse)
def verify_appointment_external_state(
    appointment_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Explicitly verify internal appointment state against the Mock EHR."""
    appt = AppointmentService.get_appointment(db, appointment_id, current_user)
    if not appt.external_appointment_id:
        return VerifyAppointmentResponse(
            appointment_id=appointment_id,
            is_verified=False,
            status=appt.status,
            details="Appointment does not have an external identifier mapped.",
        )

    is_verified = mock_ehr_connector.verify_appointment(
        external_id=appt.external_appointment_id,
        expected_patient_id=appt.patient_id,  # Will match mapped ID in mock
        expected_provider_id=appt.doctor_id,
        expected_start_time=appt.start_time,
    )

    return VerifyAppointmentResponse(
        appointment_id=appointment_id,
        external_appointment_id=appt.external_appointment_id,
        is_verified=is_verified,
        status=appt.status,
        details="External EHR record matches internal appointment parameters." if is_verified else "Verification failed.",
    )
