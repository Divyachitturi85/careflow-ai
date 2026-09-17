import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.db.session import SessionLocal
from app.models import User, Hospital, Doctor, Patient
from app.security.tenant import (
    enforce_hospital_tenant,
    enforce_patient_ownership,
    enforce_doctor_ownership,
)
from fastapi import HTTPException

client = TestClient(app)

@pytest.fixture(scope="module")
def db():
    session = SessionLocal()
    yield session
    session.close()

def test_login_all_four_roles():
    """Verify login and JWT token issuance for all 4 roles."""
    roles_credentials = [
        ("platform.admin@example.com", "Admin@123", "PLATFORM_ADMIN"),
        ("hospital.admin@example.com", "Hospital@123", "HOSPITAL_ADMIN"),
        ("doctor.rao@example.com", "Doctor@123", "DOCTOR"),
        ("patient@example.com", "Patient@123", "PATIENT"),
    ]
    for email, password, expected_role in roles_credentials:
        response = client.post(
            "/api/auth/login",
            json={"email": email, "password": password},
        )
        assert response.status_code == 200, f"Failed login for {email}: {response.text}"
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["role"] == expected_role
        assert data["email"] == email

def test_login_bad_credentials():
    """Verify 401 is returned on invalid email or password."""
    response = client.post(
        "/api/auth/login",
        json={"email": "patient@example.com", "password": "WrongPassword!"},
    )
    assert response.status_code == 401
    assert "Incorrect email or password" in response.json()["detail"]

def test_auth_me_authenticated():
    """Verify /api/auth/me returns current user profile."""
    login_resp = client.post(
        "/api/auth/login",
        json={"email": "patient@example.com", "password": "Patient@123"},
    )
    token = login_resp.json()["access_token"]

    response = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "patient@example.com"
    assert data["role"] == "PATIENT"
    assert data["patient_id"] is not None

def test_auth_me_unauthenticated():
    """Verify 401 when no token is supplied."""
    response = client.get("/api/auth/me")
    assert response.status_code == 401
    assert "Authentication credentials were not provided" in response.json()["detail"]

def test_auth_me_invalid_token():
    """Verify 401 when an invalid token is supplied."""
    response = client.get(
        "/api/auth/me",
        headers={"Authorization": "Bearer invalid.token.value"},
    )
    assert response.status_code == 401

def test_patient_registration_flow(db):
    """Verify registering a new patient account and rejecting duplicates."""
    import uuid
    unique_suffix = uuid.uuid4().hex[:6]
    new_email = f"patient_{unique_suffix}@example.com"
    reg_payload = {
        "email": new_email,
        "password": "SecurePassword123!",
        "role": "PATIENT",
        "first_name": "Arun",
        "last_name": "Varma",
        "phone": "+91-9876543210",
        "dob": "1995-08-20",
        "gender": "Male",
        "address": "Brotipet, Guntur"
    }
    
    # 1. Successful registration
    response = client.post("/api/auth/register", json=reg_payload)
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["email"] == new_email
    assert data["role"] == "PATIENT"
    assert data["patient_id"] is not None

    # 2. Login with newly registered user
    login_resp = client.post(
        "/api/auth/login",
        json={"email": new_email, "password": "SecurePassword123!"}
    )
    assert login_resp.status_code == 200

    # 3. Duplicate registration must fail with 400
    dup_resp = client.post("/api/auth/register", json=reg_payload)
    assert dup_resp.status_code == 400
    assert "already exists" in dup_resp.json()["detail"]

# ==========================================
# CRITICAL TENANT ISOLATION TESTS
# ==========================================

def test_tenant_isolation_hospital_admin_cannot_access_other_hospital(db):
    """
    CRITICAL: Hospital A (CityCare) admin MUST NEVER access Hospital B (Metro) resources.
    """
    citycare_admin = db.query(User).filter(User.email == "hospital.admin@example.com").first()
    metro_admin = db.query(User).filter(User.email == "metro.admin@example.com").first()

    citycare_hospital = db.query(Hospital).filter(Hospital.name == "CityCare Hospital").first()
    metro_hospital = db.query(Hospital).filter(Hospital.name == "Metro Health Hospital").first()

    # CityCare admin accessing CityCare -> OK
    enforce_hospital_tenant(citycare_hospital.id, citycare_admin, db)

    # CityCare admin attempting to access Metro Health -> 403 FORBIDDEN
    with pytest.raises(HTTPException) as exc_info:
        enforce_hospital_tenant(metro_hospital.id, citycare_admin, db)
    assert exc_info.value.status_code == 403
    assert "Tenant access denied" in exc_info.value.detail

    # Metro admin attempting to access CityCare -> 403 FORBIDDEN
    with pytest.raises(HTTPException) as exc_info:
        enforce_hospital_tenant(citycare_hospital.id, metro_admin, db)
    assert exc_info.value.status_code == 403
    assert "Tenant access denied" in exc_info.value.detail

def test_patient_cannot_access_hospital_tenant_admin(db):
    """Patient cannot access any hospital administrative boundary."""
    patient = db.query(User).filter(User.email == "patient@example.com").first()
    citycare = db.query(Hospital).filter(Hospital.name == "CityCare Hospital").first()

    with pytest.raises(HTTPException) as exc_info:
        enforce_hospital_tenant(citycare.id, patient, db)
    assert exc_info.value.status_code == 403
    assert "Patient accounts cannot access hospital administrative resources" in exc_info.value.detail

def test_platform_admin_can_access_all_hospitals(db):
    """Platform Admin has global oversight across all hospital tenants."""
    platform_admin = db.query(User).filter(User.email == "platform.admin@example.com").first()
    citycare = db.query(Hospital).filter(Hospital.name == "CityCare Hospital").first()
    metro = db.query(Hospital).filter(Hospital.name == "Metro Health Hospital").first()

    # Should not raise any HTTPException
    enforce_hospital_tenant(citycare.id, platform_admin, db)
    enforce_hospital_tenant(metro.id, platform_admin, db)

def test_patient_resource_ownership(db):
    """Patient A cannot access Patient B's records."""
    patient_a_user = db.query(User).filter(User.email == "patient@example.com").first()
    patient_a = patient_a_user.patient_profile

    # Look up any other patient in the db
    other_patient = db.query(Patient).filter(Patient.id != patient_a.id).first()
    assert other_patient is not None

    # Patient A accessing Patient A -> OK
    enforce_patient_ownership(patient_a.id, patient_a_user, db)

    # Patient A attempting to access Patient B -> 403 FORBIDDEN
    with pytest.raises(HTTPException) as exc_info:
        enforce_patient_ownership(other_patient.id, patient_a_user, db)
    assert exc_info.value.status_code == 403
    assert "You do not have permission to access another patient's data" in exc_info.value.detail

def test_doctor_resource_ownership(db):
    """Doctor Rao cannot access or modify Doctor Kumar's private resources."""
    dr_rao_user = db.query(User).filter(User.email == "doctor.rao@example.com").first()
    dr_rao = dr_rao_user.doctor_profile

    dr_kumar_user = db.query(User).filter(User.email == "doctor.kumar@example.com").first()
    dr_kumar = dr_kumar_user.doctor_profile

    # Dr. Rao accessing Dr. Rao -> OK
    enforce_doctor_ownership(dr_rao.id, dr_rao_user, db)

    # Dr. Rao attempting to modify Dr. Kumar's profile -> 403 FORBIDDEN
    with pytest.raises(HTTPException) as exc_info:
        enforce_doctor_ownership(dr_kumar.id, dr_rao_user, db)
    assert exc_info.value.status_code == 403
    assert "You cannot access or modify another doctor's private profile" in exc_info.value.detail
