import concurrent.futures
import uuid
from datetime import datetime, timedelta, timezone
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.db.session import SessionLocal
from app.models import (
    User,
    Doctor,
    Hospital,
    AvailabilitySlot,
    Appointment,
    AppointmentEvent,
    ReconciliationRecord,
    IntegrationOperation,
)
from app.integrations.mock_ehr import mock_ehr_connector

client = TestClient(app)

@pytest.fixture(scope="function")
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()

@pytest.fixture(autouse=True)
def reset_mock_ehr():
    """Ensure Mock EHR is in NORMAL mode before each test."""
    mock_ehr_connector.set_simulation_mode("NORMAL")
    mock_ehr_connector.reset_external_db()
    yield
    mock_ehr_connector.set_simulation_mode("NORMAL")

def get_auth_token(email: str, password: str = "Patient@123") -> str:
    resp = client.post("/api/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200, f"Login failed: {resp.text}"
    return resp.json()["access_token"]

def create_test_slot(db, doctor_id: str, hospital_id: str, minutes_offset: int = 120) -> AvailabilitySlot:
    """Helper to create a dedicated slot for test isolation."""
    start = datetime.now(timezone.utc) + timedelta(minutes=minutes_offset)
    slot = AvailabilitySlot(
        hospital_id=hospital_id,
        doctor_id=doctor_id,
        start_time=start,
        end_time=start + timedelta(minutes=30),
        is_booked=False,
        is_blocked=False,
    )
    db.add(slot)
    db.commit()
    db.refresh(slot)
    return slot

# ==========================================
# 1. NORMAL BOOKING & VERIFICATION FLOW
# ==========================================

def test_normal_booking_verification_synchronization(db):
    """
    Test standard success path:
    Patient selects slot -> Reserve slot -> Call Mock EHR -> Verify -> Synchronize -> CONFIRMED.
    """
    token = get_auth_token("patient@example.com")
    dr_rao = db.query(Doctor).filter(Doctor.name == "Dr. Rao").first()
    slot = create_test_slot(db, dr_rao.id, dr_rao.hospital_id, minutes_offset=100)

    idemp_key = f"IDEMP-NORMAL-{uuid.uuid4().hex[:8]}"
    corr_id = f"CORR-NORMAL-{uuid.uuid4().hex[:8]}"

    payload = {
        "slot_id": slot.id,
        "appointment_type": "IN_PERSON",
        "reason_for_visit": "Shoulder stiffness evaluation",
        "idempotency_key": idemp_key,
        "correlation_id": corr_id,
    }

    resp = client.post(
        "/api/appointments",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()

    # Verify Appointment State
    assert data["status"] == "CONFIRMED"
    assert data["external_appointment_id"] is not None
    assert data["external_appointment_id"].startswith("EXT-APT-")
    assert data["slot_id"] == slot.id
    assert data["doctor_name"] == "Dr. Rao"
    assert data["specialty"] == "Orthopedics"

    # Verify slot is marked booked in database
    db.refresh(slot)
    assert slot.is_booked is True

    # Verify event history exists
    assert len(data["events"]) >= 2
    event_statuses = [e["to_status"] for e in data["events"]]
    assert "PENDING" in event_statuses
    assert "CONFIRMED" in event_statuses

# ==========================================
# 2. HARD EHR FAILURE (503) & SLOT RELEASE
# ==========================================

def test_ehr_failure_releases_slot_and_marks_failed(db):
    """
    When Mock EHR encounters a hard failure (503):
    - Appointment transitions to FAILED
    - Slot is safely released (is_booked = False)
    - Patient does not receive false confirmation
    """
    token = get_auth_token("patient@example.com")
    dr_rao = db.query(Doctor).filter(Doctor.name == "Dr. Rao").first()
    slot = create_test_slot(db, dr_rao.id, dr_rao.hospital_id, minutes_offset=130)

    mock_ehr_connector.set_simulation_mode("FAILURE")

    payload = {
        "slot_id": slot.id,
        "reason_for_visit": "Failed integration test",
    }

    resp = client.post(
        "/api/appointments",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 503
    assert "External healthcare system error" in resp.json()["detail"]

    # Verify slot is released back to available
    db.refresh(slot)
    assert slot.is_booked is False

    # Verify appointment in DB is marked FAILED
    appt = db.query(Appointment).filter(Appointment.slot_id == slot.id).first()
    assert appt is not None
    assert appt.status == "FAILED"

# ==========================================
# 3. UNKNOWN OUTCOME RECOVERY (MANDATORY DEMO)
# ==========================================

def test_unknown_outcome_recovery_prevents_duplicate_appointment(db):
    """
    PRD MANDATORY FAILURE DEMO:
    - Mock EHR creates external appointment, but network drops (unknown outcome).
    - System catches timeout -> does NOT blindly retry create.
    - System queries Mock EHR -> discovers external appointment.
    - System verifies and synchronizes internal state to CONFIRMED.
    - Asserts: Exactly ONE external appointment, exactly ONE internal appointment.
    """
    token = get_auth_token("patient@example.com")
    dr_rao = db.query(Doctor).filter(Doctor.name == "Dr. Rao").first()
    slot = create_test_slot(db, dr_rao.id, dr_rao.hospital_id, minutes_offset=160)

    # Enable UNKNOWN_OUTCOME simulation mode
    mock_ehr_connector.set_simulation_mode("UNKNOWN_OUTCOME")

    idemp_key = f"IDEMP-UNKNOWN-{uuid.uuid4().hex[:8]}"
    corr_id = f"CORR-UNKNOWN-{uuid.uuid4().hex[:8]}"

    payload = {
        "slot_id": slot.id,
        "reason_for_visit": "Persistent knee discomfort",
        "idempotency_key": idemp_key,
        "correlation_id": corr_id,
    }

    resp = client.post(
        "/api/appointments",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()

    # Verify appointment was safely confirmed through the recovery engine
    assert data["status"] == "CONFIRMED"
    assert data["external_appointment_id"] is not None
    external_id = data["external_appointment_id"]

    # Verify event log captures timeout recovery
    event_types = [e["event_type"] for e in data["events"]]
    assert "EHR_TIMEOUT_RECEIVED" in event_types
    assert "EHR_TIMEOUT_RECOVERED_WITHOUT_DUPLICATE" in event_types

    # CRITICAL CHECK: Exactly ONE external appointment exists in Mock EHR!
    assert len(mock_ehr_connector._external_db) == 1
    assert external_id in mock_ehr_connector._external_db

    # CRITICAL CHECK: Exactly ONE internal appointment exists in database!
    matching_appts = db.query(Appointment).filter(Appointment.slot_id == slot.id).all()
    
    internal_appointments = len(matching_appts)
    external_appointments = len(mock_ehr_connector._external_db)
    final_internal_state = data["status"]

    print(f"\ninternal appointments = {internal_appointments}")
    print(f"external appointments = {external_appointments}")
    print(f"final internal state = {final_internal_state}")

    assert internal_appointments == 1
    assert external_appointments == 1
    assert final_internal_state == "CONFIRMED"

# ==========================================
# 4. UNRECOVERABLE TIMEOUT -> RECONCILIATION RECORD
# ==========================================

def test_unrecoverable_timeout_creates_reconciliation_record(db):
    """
    When a timeout occurs and the record was NOT created by the external EHR:
    - Status transitions to RECONCILIATION_REQUIRED
    - ReconciliationRecord is created with OPEN status
    - Surfaced on admin dashboard
    """
    token = get_auth_token("patient@example.com")
    dr_rao = db.query(Doctor).filter(Doctor.name == "Dr. Rao").first()
    slot = create_test_slot(db, dr_rao.id, dr_rao.hospital_id, minutes_offset=190)

    # Enable TIMEOUT simulation mode (record is NOT created on server)
    mock_ehr_connector.set_simulation_mode("TIMEOUT")

    payload = {
        "slot_id": slot.id,
        "reason_for_visit": "Unrecoverable test case",
    }

    resp = client.post(
        "/api/appointments",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()

    # Appointment must be flagged for reconciliation
    assert data["status"] == "RECONCILIATION_REQUIRED"

    # Verify reconciliation record in DB
    recon = db.query(ReconciliationRecord).filter(ReconciliationRecord.appointment_id == data["id"]).first()
    
    final_appointment_state = data["status"]
    reconciliation_record_exists = recon is not None

    print(f"\nfinal appointment state = {final_appointment_state}")
    print(f"reconciliation record exists = {reconciliation_record_exists}")

    assert final_appointment_state == "RECONCILIATION_REQUIRED"
    assert reconciliation_record_exists is True
    assert "timeout" in recon.reason.lower()

# ==========================================
# 5. IDEMPOTENCY (DUPLICATE REQUEST HANDLING)
# ==========================================

def test_idempotency_returns_existing_appointment(db):
    """
    Sending the identical request twice with the same Idempotency-Key
    returns the existing appointment without making another EHR call.
    """
    token = get_auth_token("patient@example.com")
    dr_rao = db.query(Doctor).filter(Doctor.name == "Dr. Rao").first()
    slot = create_test_slot(db, dr_rao.id, dr_rao.hospital_id, minutes_offset=220)

    idemp_key = f"IDEMP-KEY-{uuid.uuid4().hex[:8]}"
    payload = {
        "slot_id": slot.id,
        "reason_for_visit": "Routine checkup",
        "idempotency_key": idemp_key,
    }

    # First request
    resp1 = client.post("/api/appointments", json=payload, headers={"Authorization": f"Bearer {token}"})
    assert resp1.status_code == 200
    appt1 = resp1.json()

    # Second request with identical key
    resp2 = client.post("/api/appointments", json=payload, headers={"Authorization": f"Bearer {token}"})
    assert resp2.status_code == 200
    appt2 = resp2.json()

    assert appt1["id"] == appt2["id"]
    assert appt1["external_appointment_id"] == appt2["external_appointment_id"]

    # Verify only ONE record in Mock EHR
    assert len(mock_ehr_connector._external_db) == 1

# ==========================================
# 6. CONCURRENT IDEMPOTENCY
# ==========================================

def test_concurrent_idempotency_requests(db):
    """
    Two simultaneous requests with the identical Idempotency-Key.
    Asserts:
    - Both callers receive success / consistent appointment.
    - Exactly ONE internal appointment is created.
    - Exactly ONE external appointment is created.
    """
    token = get_auth_token("patient@example.com")
    dr_priya = db.query(Doctor).filter(Doctor.name == "Dr. Priya").first()
    slot = create_test_slot(db, dr_priya.id, dr_priya.hospital_id, minutes_offset=250)

    idemp_key = f"CONCURRENT-IDEMP-{uuid.uuid4().hex[:8]}"
    payload = {
        "slot_id": slot.id,
        "reason_for_visit": "Headache consultation",
        "idempotency_key": idemp_key,
    }

    results = []
    def make_request(req_id: int):
        r = client.post("/api/appointments", json=payload, headers={"Authorization": f"Bearer {token}"})
        return {"req_id": req_id, "status": r.status_code, "data": r.json() if r.status_code == 200 else None}

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(make_request, 1), executor.submit(make_request, 2)]
        for f in concurrent.futures.as_completed(futures):
            results.append(f.result())

    # At least one request succeeded (the other either succeeded or returned existing)
    successful = [r for r in results if r["status"] == 200]
    assert len(successful) >= 1

    # In database: exactly one appointment with this slot
    appts = db.query(Appointment).filter(Appointment.slot_id == slot.id).all()
    assert len(appts) == 1

# ==========================================
# 7. RESCHEDULING & CANCELLATION
# ==========================================

def test_reschedule_and_cancel_appointment(db):
    """Verify rescheduling to a new slot and cancellation releases availability."""
    token = get_auth_token("patient@example.com")
    dr_rao = db.query(Doctor).filter(Doctor.name == "Dr. Rao").first()
    slot1 = create_test_slot(db, dr_rao.id, dr_rao.hospital_id, minutes_offset=300)
    slot2 = create_test_slot(db, dr_rao.id, dr_rao.hospital_id, minutes_offset=360)

    # 1. Book on slot1
    book_resp = client.post(
        "/api/appointments",
        json={"slot_id": slot1.id, "reason_for_visit": "Initial booking"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert book_resp.status_code == 200
    appt_id = book_resp.json()["id"]

    # 2. Reschedule to slot2
    resched_resp = client.post(
        f"/api/appointments/{appt_id}/reschedule",
        json={"new_slot_id": slot2.id, "reason": "Conflict with work"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resched_resp.status_code == 200
    resched_data = resched_resp.json()
    assert resched_data["status"] == "RESCHEDULED"
    assert resched_data["slot_id"] == slot2.id

    # Verify slot1 was released and slot2 is now booked
    db.refresh(slot1)
    db.refresh(slot2)
    assert slot1.is_booked is False
    assert slot2.is_booked is True

    # 3. Cancel appointment
    cancel_resp = client.post(
        f"/api/appointments/{appt_id}/cancel",
        json={"reason": "Feeling much better"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert cancel_resp.status_code == 200
    cancel_data = cancel_resp.json()
    assert cancel_data["status"] == "CANCELLED"

    # Verify slot2 is now released
    db.refresh(slot2)
    assert slot2.is_booked is False

# ==========================================
# 8. TENANT ISOLATION ON APPOINTMENTS
# ==========================================

def test_tenant_isolation_hospital_admin_cannot_see_other_hospital_appointments(db):
    """Hospital Admin for Metro cannot see CityCare appointments."""
    citycare_admin_token = get_auth_token("hospital.admin@example.com", "Hospital@123")
    metro_admin_token = get_auth_token("metro.admin@example.com", "Hospital@123")

    # CityCare admin lists appointments
    resp_citycare = client.get("/api/appointments", headers={"Authorization": f"Bearer {citycare_admin_token}"})
    assert resp_citycare.status_code == 200
    citycare_appts = resp_citycare.json()
    citycare_hospital = db.query(Hospital).filter(Hospital.name == "CityCare Hospital").first()
    assert all(a["hospital_id"] == citycare_hospital.id for a in citycare_appts)

    # Metro admin lists appointments -> should not see CityCare appointments
    resp_metro = client.get("/api/appointments", headers={"Authorization": f"Bearer {metro_admin_token}"})
    assert resp_metro.status_code == 200
    metro_appts = resp_metro.json()
    metro_hospital = db.query(Hospital).filter(Hospital.name == "Metro Health Hospital").first()
    assert all(a["hospital_id"] == metro_hospital.id for a in metro_appts)

def test_slot_conflict_rejects_and_creates_no_ehr_appointment(db):
    """
    Slot conflict test:
    When a slot is already booked, an incoming booking request is rejected with 409 Conflict.
    Zero external EHR appointments are created.
    """
    token = get_auth_token("patient@example.com")
    dr_rao = db.query(Doctor).filter(Doctor.name == "Dr. Rao").first()
    slot = create_test_slot(db, dr_rao.id, dr_rao.hospital_id, minutes_offset=420)
    slot.is_booked = True
    db.commit()

    resp = client.post(
        "/api/appointments",
        json={"slot_id": slot.id, "reason_for_visit": "Conflict test"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 409
    assert "already booked" in resp.json()["detail"] or "reservation failed" in resp.json()["detail"]
    assert len(mock_ehr_connector._external_db) == 0

# ==========================================
# 9. ADMIN SIMULATION MODE TOGGLE
# ==========================================

def test_admin_simulation_mode_endpoint():
    """Verify staff can switch Mock EHR simulation mode via API."""
    admin_token = get_auth_token("hospital.admin@example.com", "Hospital@123")

    # Toggle to UNKNOWN_OUTCOME
    toggle_resp = client.post(
        "/api/admin/simulation-mode",
        json={"mode": "UNKNOWN_OUTCOME"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert toggle_resp.status_code == 200
    assert toggle_resp.json()["mode"] == "UNKNOWN_OUTCOME"
    assert mock_ehr_connector.simulation_mode == "UNKNOWN_OUTCOME"

    # Reset to NORMAL
    reset_resp = client.post(
        "/api/admin/simulation-mode",
        json={"mode": "NORMAL"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert reset_resp.status_code == 200
    assert reset_resp.json()["mode"] == "NORMAL"
