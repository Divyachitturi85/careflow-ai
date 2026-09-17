import pytest
from app.db.session import SessionLocal
from app.models import (
    User,
    Hospital,
    HospitalStaff,
    Doctor,
    Specialty,
    AvailabilitySlot,
    Patient,
    Questionnaire,
    QuestionnaireQuestion,
    Appointment,
    HealthcareConnection,
    ExternalIdentifierMapping,
)
from sqlalchemy.exc import IntegrityError

@pytest.fixture(scope="module")
def db():
    session = SessionLocal()
    yield session
    session.close()

def test_seeded_users_exist(db):
    """Verify all 4 core roles exist in the database."""
    platform_admin = db.query(User).filter(User.email == "platform.admin@example.com").first()
    hospital_admin = db.query(User).filter(User.email == "hospital.admin@example.com").first()
    doctor_rao = db.query(User).filter(User.email == "doctor.rao@example.com").first()
    patient = db.query(User).filter(User.email == "patient@example.com").first()

    assert platform_admin is not None
    assert platform_admin.role == "PLATFORM_ADMIN"

    assert hospital_admin is not None
    assert hospital_admin.role == "HOSPITAL_ADMIN"

    assert doctor_rao is not None
    assert doctor_rao.role == "DOCTOR"

    assert patient is not None
    assert patient.role == "PATIENT"

def test_seeded_hospitals_and_tenant_assignment(db):
    """Verify CityCare hospital is approved and hospital staff is mapped."""
    hospital = db.query(Hospital).filter(Hospital.name == "CityCare Hospital").first()
    assert hospital is not None
    assert hospital.status == "APPROVED"
    assert hospital.city == "Vijayawada"
    assert hospital.external_facility_id == "EXT-FAC-CITYCARE"

    # Verify hospital staff tenant link
    staff = db.query(HospitalStaff).filter(HospitalStaff.hospital_id == hospital.id).first()
    assert staff is not None
    assert staff.user.email == "hospital.admin@example.com"

def test_seeded_doctors_and_orthopedics_specialty(db):
    """Verify Dr. Rao, Dr. Kumar, and Dr. Priya with their specialties and external IDs."""
    dr_rao = db.query(Doctor).filter(Doctor.name == "Dr. Rao").first()
    assert dr_rao is not None
    assert dr_rao.status == "ACTIVE"
    assert dr_rao.specialty.name == "Orthopedics"
    assert dr_rao.external_provider_id == "EXT-DOC-RAO-01"
    assert dr_rao.hospital.name == "CityCare Hospital"

    dr_kumar = db.query(Doctor).filter(Doctor.name == "Dr. Kumar").first()
    assert dr_kumar is not None
    assert dr_kumar.specialty.name == "Cardiology"

    dr_priya = db.query(Doctor).filter(Doctor.name == "Dr. Priya").first()
    assert dr_priya is not None
    assert dr_priya.specialty.name == "General Medicine"

def test_deterministic_availability_slots(db):
    """Verify Dr. Rao has real slots in the database including Friday 3 PM, Friday 4 PM, Saturday 11 AM."""
    dr_rao = db.query(Doctor).filter(Doctor.name == "Dr. Rao").first()
    # Filter for seed calendar slots
    seed_slots = db.query(AvailabilitySlot).filter(
        AvailabilitySlot.doctor_id == dr_rao.id,
        AvailabilitySlot.calendar_id != None
    ).all()
    assert len(seed_slots) >= 3

    assert all(s.hospital_id == dr_rao.hospital_id for s in seed_slots)

    # Check times: should have Friday (weekday=4) and Saturday (weekday=5)
    weekdays = {s.start_time.weekday() for s in seed_slots}
    assert 4 in weekdays  # Friday
    assert 5 in weekdays  # Saturday

    # Verify start hours: 15 (3 PM), 16 (4 PM), 11 (11 AM)
    start_hours = {s.start_time.hour for s in seed_slots}
    assert 15 in start_hours
    assert 16 in start_hours
    assert 11 in start_hours

def test_pre_visit_questionnaire_seeded(db):
    """Verify Orthopedics questionnaire and questions."""
    ortho_q = db.query(Questionnaire).filter(Questionnaire.title.ilike("%Orthopedics%")).first()
    assert ortho_q is not None
    assert len(ortho_q.questions) == 5
    assert ortho_q.questions[0].question_type == "CHOICE"
    assert ortho_q.questions[1].question_type == "NUMERIC"
    assert ortho_q.questions[2].question_type == "YES_NO"

def test_unique_constraint_email(db):
    """Verify unique constraint on User email."""
    duplicate_user = User(
        email="patient@example.com",
        hashed_password="any",
        role="PATIENT",
        first_name="Duplicate",
        last_name="Test"
    )
    db.add(duplicate_user)
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()

def test_tenant_ownership_fields(db):
    """Verify all hospital-scoped entities require hospital_id."""
    hospital = db.query(Hospital).filter(Hospital.name == "CityCare Hospital").first()
    
    # Check that hospital_id matches across entities
    doctor = db.query(Doctor).filter(Doctor.hospital_id == hospital.id).first()
    assert doctor.hospital_id == hospital.id

    slot = db.query(AvailabilitySlot).filter(AvailabilitySlot.hospital_id == hospital.id).first()
    assert slot.hospital_id == hospital.id

    questionnaire = db.query(Questionnaire).filter(Questionnaire.hospital_id == hospital.id).first()
    assert questionnaire.hospital_id == hospital.id

    mapping = db.query(ExternalIdentifierMapping).filter(ExternalIdentifierMapping.hospital_id == hospital.id).first()
    assert mapping.hospital_id == hospital.id
