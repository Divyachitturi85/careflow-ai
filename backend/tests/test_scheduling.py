import concurrent.futures
from datetime import datetime, timedelta, timezone
import pytest
from fastapi.testclient import TestClient
from fastapi import HTTPException
from app.main import app
from app.db.session import SessionLocal
from app.models import (
    Doctor,
    Hospital,
    AvailabilitySlot,
    BlockedSlot,
)
from app.services.scheduling_service import SchedulingService

client = TestClient(app)

@pytest.fixture(scope="function")
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()

def test_get_hospitals_discovery():
    """Verify hospital discovery and city filtering."""
    # 1. All approved hospitals
    resp = client.get("/api/hospitals")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 1
    names = [h["name"] for h in data]
    assert "CityCare Hospital" in names

    # 2. Filter by city
    resp_city = client.get("/api/hospitals?city=Vijayawada")
    assert resp_city.status_code == 200
    city_data = resp_city.json()
    assert all(h["city"] == "Vijayawada" for h in city_data)
    assert any(h["name"] == "CityCare Hospital" for h in city_data)

def test_get_doctors_discovery():
    """Verify active doctor discovery and specialty filtering."""
    # 1. All active doctors
    resp = client.get("/api/doctors")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 3
    names = [d["name"] for d in data]
    assert "Dr. Rao" in names

    # 2. Filter by specialty 'Orthopedics'
    resp_ortho = client.get("/api/doctors?specialty=Orthopedics")
    assert resp_ortho.status_code == 200
    ortho_data = resp_ortho.json()
    assert len(ortho_data) >= 1
    assert ortho_data[0]["name"] == "Dr. Rao"
    assert ortho_data[0]["specialty_name"] == "Orthopedics"
    assert ortho_data[0]["hospital_name"] == "CityCare Hospital"

def test_inactive_doctor_cannot_expose_slots(db):
    """Ensure inactive doctors are excluded from discovery and availability."""
    dr_rao = db.query(Doctor).filter(Doctor.name == "Dr. Rao").first()
    original_status = dr_rao.status

    try:
        # Deactivate Dr. Rao temporarily
        dr_rao.status = "INACTIVE"
        db.commit()

        # Doctor discovery should now exclude Dr. Rao
        resp = client.get("/api/doctors?name=Dr.%20Rao")
        assert resp.status_code == 200
        assert len(resp.json()) == 0

        # Availability search for Dr. Rao should return 0 slots
        resp_slots = client.get(f"/api/availability?doctor_id={dr_rao.id}")
        assert resp_slots.status_code == 200
        assert len(resp_slots.json()) == 0
    finally:
        # Restore status
        dr_rao.status = original_status
        db.commit()

def test_real_availability_slots_for_dr_rao(db):
    """
    Verify Dr. Rao has real slots from DB (Friday 3 PM, Friday 4 PM, Saturday 11 AM)
    and that availability never returns invented or fake slots.
    """
    dr_rao = db.query(Doctor).filter(Doctor.name == "Dr. Rao").first()
    resp = client.get(f"/api/availability?doctor_id={dr_rao.id}")
    assert resp.status_code == 200
    slots = resp.json()

    assert len(slots) >= 3
    for s in slots:
        assert s["doctor_name"] == "Dr. Rao"
        assert s["hospital_name"] == "CityCare Hospital"
        assert s["specialty"] == "Orthopedics"
        assert s["available"] is True
        assert "start_time" in s
        assert "end_time" in s

    # Verify weekday and hour distributions
    hours = [datetime.fromisoformat(s["start_time"]).hour for s in slots]
    assert 15 in hours  # Friday 3 PM
    assert 16 in hours  # Friday 4 PM
    assert 11 in hours  # Saturday 11 AM

def test_blocked_slot_unavailable(db):
    """A slot marked as is_blocked=True must be unavailable."""
    dr_rao = db.query(Doctor).filter(Doctor.name == "Dr. Rao").first()
    slot = db.query(AvailabilitySlot).filter(AvailabilitySlot.doctor_id == dr_rao.id, AvailabilitySlot.is_booked == False).first()
    
    slot.is_blocked = True
    db.commit()

    try:
        # Availability query must exclude this slot
        resp = client.get(f"/api/availability?doctor_id={dr_rao.id}")
        slot_ids = [s["slot_id"] for s in resp.json()]
        assert slot.id not in slot_ids

        # Direct slot validation must report invalid
        val_resp = client.get(f"/api/availability/{slot.id}")
        assert val_resp.status_code == 200
        val_data = val_resp.json()
        assert val_data["is_valid"] is False
        assert "blocked" in val_data["reason"].lower()
    finally:
        slot.is_blocked = False
        db.commit()

def test_doctor_leave_period_blocks_slots(db):
    """An overlapping BlockedSlot (e.g. vacation / emergency) must exclude the slot."""
    dr_rao = db.query(Doctor).filter(Doctor.name == "Dr. Rao").first()
    slot = db.query(AvailabilitySlot).filter(AvailabilitySlot.doctor_id == dr_rao.id, AvailabilitySlot.is_booked == False).first()

    # Create doctor leave covering this slot
    leave = BlockedSlot(
        hospital_id=dr_rao.hospital_id,
        doctor_id=dr_rao.id,
        start_time=slot.start_time - timedelta(minutes=10),
        end_time=slot.end_time + timedelta(minutes=10),
        reason="Attending Emergency Orthopedic Surgery"
    )
    db.add(leave)
    db.commit()

    try:
        # Slot should be excluded from availability
        resp = client.get(f"/api/availability?doctor_id={dr_rao.id}")
        slot_ids = [s["slot_id"] for s in resp.json()]
        assert slot.id not in slot_ids

        # Validation must fail with the leave reason
        is_valid, reason, _ = SchedulingService.validate_slot(db, slot.id)
        assert is_valid is False
        assert "Emergency Orthopedic Surgery" in reason
    finally:
        db.delete(leave)
        db.commit()

def test_invalid_slot_id():
    """Validating a non-existent slot returns is_valid=False."""
    resp = client.get("/api/availability/non-existent-slot-id")
    assert resp.status_code == 200
    assert resp.json()["is_valid"] is False
    assert "not found" in resp.json()["reason"].lower()

def test_immediate_revalidation_and_reservation(db):
    """
    Verify that revalidate_and_reserve_slot immediately marks slot as booked,
    and a second attempt on the same slot raises 409 Conflict.
    """
    dr_kumar = db.query(Doctor).filter(Doctor.name == "Dr. Kumar").first()
    slot = db.query(AvailabilitySlot).filter(AvailabilitySlot.doctor_id == dr_kumar.id, AvailabilitySlot.is_booked == False).first()
    assert slot is not None

    # First attempt: succeeds
    reserved = SchedulingService.revalidate_and_reserve_slot(db, slot.id)
    assert reserved.is_booked is True

    # Immediate second attempt: must raise 409 CONFLICT
    with pytest.raises(HTTPException) as exc_info:
        SchedulingService.revalidate_and_reserve_slot(db, slot.id)
    assert exc_info.value.status_code == 409
    assert "already booked" in exc_info.value.detail or "concurrent" in exc_info.value.detail

    # Release slot back
    SchedulingService.release_slot(db, slot.id)
    db.commit()
    db.refresh(slot)
    assert slot.is_booked is False

def test_concurrent_double_booking_race_condition():
    """
    CRITICAL CONCURRENCY TEST:
    Two simultaneous booking threads target the exact same slot.
    Asserts:
    - Exactly ONE request succeeds.
    - Exactly ONE request receives a 409 Conflict.
    - The slot ends up booked exactly once.
    """
    # Find an open slot for Dr. Priya
    session = SessionLocal()
    dr_priya = session.query(Doctor).filter(Doctor.name == "Dr. Priya").first()
    slot = session.query(AvailabilitySlot).filter(
        AvailabilitySlot.doctor_id == dr_priya.id,
        AvailabilitySlot.is_booked == False,
    ).first()
    assert slot is not None
    slot_id = slot.id
    session.close()

    results = []

    def attempt_reservation(thread_id: int):
        thread_db = SessionLocal()
        try:
            SchedulingService.revalidate_and_reserve_slot(thread_db, slot_id)
            thread_db.commit()
            return {"thread": thread_id, "success": True, "error": None}
        except HTTPException as e:
            thread_db.rollback()
            return {"thread": thread_id, "success": False, "status_code": e.status_code, "error": e.detail}
        except Exception as e:
            thread_db.rollback()
            return {"thread": thread_id, "success": False, "error": str(e)}
        finally:
            thread_db.close()

    # Launch two simultaneous threads
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(attempt_reservation, 1), executor.submit(attempt_reservation, 2)]
        for f in concurrent.futures.as_completed(futures):
            results.append(f.result())

    success_count = sum(1 for r in results if r["success"] is True)
    failure_count = sum(1 for r in results if r["success"] is False)

    assert success_count == 1, f"Expected exactly 1 success, but got {success_count}. Results: {results}"
    assert failure_count == 1, f"Expected exactly 1 failure, but got {failure_count}. Results: {results}"

    failed_result = next(r for r in results if not r["success"])
    assert failed_result.get("status_code") == 409, f"Failed result should have status 409: {failed_result}"

    # Verify in DB: slot is booked, and cleanup
    verify_db = SessionLocal()
    booked_slot = verify_db.query(AvailabilitySlot).filter(AvailabilitySlot.id == slot_id).first()
    assert booked_slot.is_booked is True
    SchedulingService.release_slot(verify_db, slot_id)
    verify_db.commit()
    verify_db.close()
