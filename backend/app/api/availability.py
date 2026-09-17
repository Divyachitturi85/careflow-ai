from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.schemas.scheduling import SlotResponse, SlotValidationResponse
from app.services.scheduling_service import SchedulingService

router = APIRouter(prefix="/api/availability", tags=["Scheduling & Availability"])

@router.get("", response_model=List[SlotResponse])
def get_availability(
    doctor_id: Optional[str] = Query(None, description="Filter slots for a specific doctor"),
    hospital_id: Optional[str] = Query(None, description="Filter slots for a hospital"),
    specialty: Optional[str] = Query(None, description="Filter by specialty (e.g. Orthopedics)"),
    city: Optional[str] = Query(None, description="Filter by city"),
    start_date: Optional[datetime] = Query(None, description="Earliest start date/time in UTC"),
    end_date: Optional[datetime] = Query(None, description="Latest start date/time in UTC"),
    db: Session = Depends(get_db),
):
    """
    Query real, bookable appointment slots.
    Guarantees:
    - Never generates fake or invented slots.
    - Only returns real database-backed availability.
    - Filters out booked, blocked, and inactive doctor slots.
    """
    return SchedulingService.get_available_slots(
        db=db,
        doctor_id=doctor_id,
        hospital_id=hospital_id,
        specialty=specialty,
        city=city,
        start_date=start_date,
        end_date=end_date,
    )

@router.get("/{slot_id}", response_model=SlotValidationResponse)
def validate_slot_availability(slot_id: str, db: Session = Depends(get_db)):
    """
    Validate a specific slot immediately before selection or booking.
    Returns whether the slot is valid and ready to be reserved.
    """
    is_valid, reason, slot = SchedulingService.validate_slot(db, slot_id)
    slot_details = None
    if slot:
        slot_details = SlotResponse(
            slot_id=slot.id,
            doctor_id=slot.doctor.id,
            doctor_name=slot.doctor.name,
            hospital_id=slot.hospital.id,
            hospital_name=slot.hospital.name,
            specialty=slot.doctor.specialty.name if slot.doctor.specialty else "General",
            start_time=slot.start_time,
            end_time=slot.end_time,
            available=(not slot.is_booked and not slot.is_blocked),
        )

    return SlotValidationResponse(
        slot_id=slot_id,
        is_valid=is_valid,
        reason=reason,
        slot=slot_details,
    )
