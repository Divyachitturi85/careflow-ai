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
    Questionnaire,
    QuestionnaireResponse,
)

client = TestClient(app)

def get_auth_token(email: str = "patient@example.com", password: str = "Patient@123") -> str:
    resp = client.post("/api/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200
    return resp.json()["access_token"]

def test_questionnaire_flow_for_appointment():
    token = get_auth_token()
    session = SessionLocal()
    try:
        # Fetch seeded patient and dr rao
        patient_user = session.query(User).filter(User.email == "patient@example.com").first()
        doctor_rao = session.query(Doctor).filter(Doctor.name == "Dr. Rao").first()
        hospital = session.query(Hospital).filter(Hospital.name == "CityCare Hospital").first()
        slot = session.query(AvailabilitySlot).filter(AvailabilitySlot.doctor_id == doctor_rao.id).first()

        # Create a test appointment
        test_appt = Appointment(
            hospital_id=hospital.id,
            patient_id=patient_user.patient_profile.id,
            doctor_id=doctor_rao.id,
            slot_id=slot.id,
            status="CONFIRMED",
            correlation_id="CORR-TEST-Q",
        )
        session.add(test_appt)
        session.commit()
        appt_id = test_appt.id
        doc_id = doctor_rao.id
    finally:
        session.close()

    # 1. Fetch questionnaire for appointment
    resp = client.get(
        f"/api/questionnaires/appointment/{appt_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "questionnaire" in data
    assert "Orthopedics Pre-Visit" in data["questionnaire"]["title"]
    assert len(data["questionnaire"]["questions"]) == 5
    assert data["response"] is None

    # 2. Submit questionnaire response
    questions = data["questionnaire"]["questions"]
    answers = {
        questions[0]["id"]: "Left knee / joint",
        questions[1]["id"]: "7",
        questions[2]["id"]: "Walking, stairs",
        questions[3]["id"]: "About 3 weeks",
        questions[4]["id"]: "No",
    }
    submit_resp = client.post(
        "/api/questionnaires/responses",
        json={"appointment_id": appt_id, "answers": answers},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert submit_resp.status_code == 200
    assert submit_resp.json()["status"] == "COMPLETED"

    # 3. Verify retrieved questionnaire now has completed response
    resp2 = client.get(
        f"/api/questionnaires/appointment/{appt_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp2.status_code == 200
    assert resp2.json()["response"] is not None
    assert resp2.json()["response"]["status"] == "COMPLETED"
    assert resp2.json()["response"]["answers"][questions[0]["id"]] == "Left knee / joint"

    # 4. Doctor review
    doc_token = get_auth_token("doctor.rao@example.com", "Doctor@123")
    doc_resp = client.get(
        f"/api/questionnaires/doctor/{doc_id}/responses",
        headers={"Authorization": f"Bearer {doc_token}"},
    )
    assert doc_resp.status_code == 200
    doc_data = doc_resp.json()
    assert doc_data["count"] >= 1
    matching = [r for r in doc_data["responses"] if r["appointment_id"] == appt_id]
    assert len(matching) == 1

    # Cleanup
    session = SessionLocal()
    try:
        session.query(QuestionnaireResponse).filter(QuestionnaireResponse.appointment_id == appt_id).delete()
        session.query(Appointment).filter(Appointment.id == appt_id).delete()
        session.commit()
    finally:
        session.close()
