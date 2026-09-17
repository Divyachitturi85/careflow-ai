from datetime import datetime, timezone
from typing import List, Optional, Tuple
from fastapi import HTTPException, status
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_, update
from app.models.doctor import AvailabilitySlot, Doctor, BlockedSlot, Calendar
from app.models.hospital import Hospital, Specialty
from app.schemas.scheduling import SlotResponse, SlotValidationResponse

import threading

_sqlite_concurrency_lock = threading.Lock()

class SchedulingService:
    @staticmethod
    def get_available_slots(
        db: Session,
        doctor_id: Optional[str] = None,
        hospital_id: Optional[str] = None,
        specialty: Optional[str] = None,
        city: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[SlotResponse]:
        """
        Retrieves real bookable slots from the database.
        Ensures doctor is ACTIVE, hospital is APPROVED, calendar is ACTIVE,
        and slot is neither booked nor blocked.
        """
        query = (
            db.query(AvailabilitySlot)
            .join(Doctor, AvailabilitySlot.doctor_id == Doctor.id)
            .join(Hospital, AvailabilitySlot.hospital_id == Hospital.id)
            .outerjoin(Calendar, AvailabilitySlot.calendar_id == Calendar.id)
            .outerjoin(Specialty, Doctor.specialty_id == Specialty.id)
            .filter(
                AvailabilitySlot.is_booked == False,
                AvailabilitySlot.is_blocked == False,
                Doctor.status == "ACTIVE",
                Hospital.status == "APPROVED",
                or_(Calendar.id == None, Calendar.is_active == True),
            )
        )

        if doctor_id:
            query = query.filter(AvailabilitySlot.doctor_id == doctor_id)
        if hospital_id:
            query = query.filter(AvailabilitySlot.hospital_id == hospital_id)
        if specialty:
            query = query.filter(Specialty.name.ilike(f"%{specialty}%"))
        if city:
            query = query.filter(Hospital.city.ilike(f"%{city}%"))
        if start_date:
            query = query.filter(AvailabilitySlot.start_time >= start_date)
        if end_date:
            query = query.filter(AvailabilitySlot.start_time <= end_date)

        slots = query.order_by(AvailabilitySlot.start_time.asc()).all()

        # Filter out any slot that overlaps with doctor's BlockedSlot periods
        results: List[SlotResponse] = []
        for s in slots:
            is_blocked_by_leave = (
                db.query(BlockedSlot)
                .filter(
                    BlockedSlot.doctor_id == s.doctor_id,
                    BlockedSlot.start_time <= s.end_time,
                    BlockedSlot.end_time >= s.start_time,
                )
                .first()
            )
            if is_blocked_by_leave:
                continue

            results.append(
                SlotResponse(
                    slot_id=s.id,
                    doctor_id=s.doctor.id,
                    doctor_name=s.doctor.name,
                    hospital_id=s.hospital.id,
                    hospital_name=s.hospital.name,
                    specialty=s.doctor.specialty.name if s.doctor.specialty else "General",
                    start_time=s.start_time,
                    end_time=s.end_time,
                    available=True,
                )
            )

        return results

    @staticmethod
    def validate_slot(
        db: Session, slot_id: str
    ) -> Tuple[bool, Optional[str], Optional[AvailabilitySlot]]:
        """
        Validates whether a slot is currently available and bookable.
        Returns: (is_valid, reason, slot_record)
        """
        slot = (
            db.query(AvailabilitySlot)
            .options(
                joinedload(AvailabilitySlot.doctor).joinedload(Doctor.specialty),
                joinedload(AvailabilitySlot.hospital),
                joinedload(AvailabilitySlot.calendar),
            )
            .filter(AvailabilitySlot.id == slot_id)
            .first()
        )

        if not slot:
            return False, "Slot not found in scheduling system.", None

        if slot.is_booked:
            return False, "Slot is already booked by another appointment.", slot

        if slot.is_blocked:
            return False, "Slot is blocked from scheduling.", slot

        if not slot.doctor or slot.doctor.status != "ACTIVE":
            return False, f"Doctor is inactive or unavailable (status: {slot.doctor.status if slot.doctor else 'Unknown'}).", slot

        if not slot.hospital or slot.hospital.status != "APPROVED":
            return False, "Hospital is not in approved status.", slot

        if slot.calendar and not slot.calendar.is_active:
            return False, "Doctor consultation calendar is currently disabled.", slot

        # Check overlapping blocked leave
        leave = (
            db.query(BlockedSlot)
            .filter(
                BlockedSlot.doctor_id == slot.doctor_id,
                BlockedSlot.start_time <= slot.end_time,
                BlockedSlot.end_time >= slot.start_time,
            )
            .first()
        )
        if leave:
            return False, f"Doctor has blocked time during this slot: {leave.reason or 'Leave'}.", slot

        return True, None, slot

    @staticmethod
    def revalidate_and_reserve_slot(
        db: Session, slot_id: str
    ) -> AvailabilitySlot:
        """
        Atomically revalidates and reserves a slot immediately before booking.
        Uses database row locking (FOR UPDATE on PostgreSQL) and compare-and-swap
        atomic update to guarantee that concurrent requests targeting the same slot
        will never both succeed.
        """
        is_sqlite = db.bind and db.bind.dialect.name == "sqlite"
        if is_sqlite:
            with _sqlite_concurrency_lock:
                return SchedulingService._execute_slot_reservation(db, slot_id)
        else:
            return SchedulingService._execute_slot_reservation(db, slot_id)

    @staticmethod
    def _execute_slot_reservation(db: Session, slot_id: str) -> AvailabilitySlot:
        from sqlalchemy.exc import OperationalError, IntegrityError

        try:
            # Query slot with row locking if PostgreSQL
            try:
                slot = db.query(AvailabilitySlot).filter(AvailabilitySlot.id == slot_id).with_for_update().first()
            except Exception:
                slot = db.query(AvailabilitySlot).filter(AvailabilitySlot.id == slot_id).first()

            if not slot:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Slot with ID '{slot_id}' was not found.",
                )

            # Immediate revalidation check under lock
            is_valid, reason, _ = SchedulingService.validate_slot(db, slot_id)
            if not is_valid:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Slot reservation failed: {reason}",
                )

            # Atomic compare-and-swap update (is_booked: False -> True)
            stmt = (
                update(AvailabilitySlot)
                .where(
                    AvailabilitySlot.id == slot_id,
                    AvailabilitySlot.is_booked == False,
                    AvailabilitySlot.is_blocked == False,
                )
                .values(is_booked=True)
            )
            result = db.execute(stmt)

            if result.rowcount == 0:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Slot was just booked by a concurrent request (rowcount=0).",
                )

            db.flush()
            db.refresh(slot)
            return slot
        except (OperationalError, IntegrityError) as e:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Slot reservation conflict: {type(e).__name__} - {str(e)}",
            ) from e

    @staticmethod
    def release_slot(db: Session, slot_id: str) -> None:
        """Releases a reserved or booked slot back to available state (e.g. upon cancellation)."""
        slot = db.query(AvailabilitySlot).filter(AvailabilitySlot.id == slot_id).first()
        if slot:
            slot.is_booked = False
            db.flush()
