import json
from datetime import datetime, timedelta, timezone
from passlib.context import CryptContext
from app.db.session import SessionLocal, engine, Base
from app.models import (
    User,
    Hospital,
    HospitalStaff,
    Department,
    Specialty,
    Doctor,
    Calendar,
    AvailabilitySlot,
    Patient,
    PatientPreference,
    Questionnaire,
    QuestionnaireQuestion,
    HealthcareConnection,
    ExternalIdentifierMapping,
    Workflow,
)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def get_upcoming_weekday(target_weekday: int, hour: int, minute: int = 0) -> datetime:
    """
    Returns a datetime in UTC for the next occurrence of target_weekday (0=Monday, 4=Friday, 5=Saturday).
    If today is that day and the time has passed or within 2 hours, moves to next week's day.
    """
    now = datetime.now(timezone.utc)
    days_ahead = target_weekday - now.weekday()
    if days_ahead <= 0:
        days_ahead += 7
    target_date = now + timedelta(days=days_ahead)
    return target_date.replace(hour=hour, minute=minute, second=0, microsecond=0)

def seed_data(reset: bool = False):
    """Seed deterministic demo data."""
    if reset:
        print("Dropping existing tables and rebuilding schema...")
        Base.metadata.drop_all(bind=engine)

    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
        # Check if already seeded
        if not reset:
            existing_hospital = db.query(Hospital).filter(Hospital.name == "CityCare Hospital").first()
            if existing_hospital:
                print("Database already seeded. Skipping...")
                return

        print("Seeding CareFlow AI demo data...")

        # 1. Users
        platform_admin_user = User(
            email="platform.admin@example.com",
            hashed_password=hash_password("Admin@123"),
            role="PLATFORM_ADMIN",
            first_name="Platform",
            last_name="Admin",
            phone="+1-800-555-0100"
        )

        hospital_admin_user = User(
            email="hospital.admin@example.com",
            hashed_password=hash_password("Hospital@123"),
            role="HOSPITAL_ADMIN",
            first_name="CityCare",
            last_name="Admin",
            phone="+1-800-555-0101"
        )

        dr_rao_user = User(
            email="doctor.rao@example.com",
            hashed_password=hash_password("Doctor@123"),
            role="DOCTOR",
            first_name="Rao",
            last_name="Surapaneni",
            phone="+1-800-555-0102"
        )

        dr_kumar_user = User(
            email="doctor.kumar@example.com",
            hashed_password=hash_password("Doctor@123"),
            role="DOCTOR",
            first_name="Rajesh",
            last_name="Kumar",
            phone="+1-800-555-0103"
        )

        dr_priya_user = User(
            email="doctor.priya@example.com",
            hashed_password=hash_password("Doctor@123"),
            role="DOCTOR",
            first_name="Priya",
            last_name="Sharma",
            phone="+1-800-555-0104"
        )

        patient_user = User(
            email="patient@example.com",
            hashed_password=hash_password("Patient@123"),
            role="PATIENT",
            first_name="Kavita",
            last_name="Reddy",
            phone="+1-800-555-0199"
        )

        # Secondary tenant for isolation tests
        metro_admin_user = User(
            email="metro.admin@example.com",
            hashed_password=hash_password("Hospital@123"),
            role="HOSPITAL_ADMIN",
            first_name="Metro",
            last_name="Admin",
            phone="+1-800-555-0201"
        )

        db.add_all([
            platform_admin_user, 
            hospital_admin_user, 
            dr_rao_user, 
            dr_kumar_user, 
            dr_priya_user, 
            patient_user,
            metro_admin_user
        ])
        db.flush()

        # 2. Hospitals
        citycare_hospital = Hospital(
            name="CityCare Hospital",
            status="APPROVED",
            city="Vijayawada",
            address="14-2 Benz Circle, Vijayawada, AP 520010",
            phone="+91-866-2490000",
            email="info@citycare.org",
            external_facility_id="EXT-FAC-CITYCARE"
        )

        metro_hospital = Hospital(
            name="Metro Health Hospital",
            status="APPROVED",
            city="Hyderabad",
            address="5-9 Banjara Hills Road 12, Hyderabad, TS 500034",
            phone="+91-40-23450000",
            email="info@metrohealth.org",
            external_facility_id="EXT-FAC-METRO"
        )

        db.add_all([citycare_hospital, metro_hospital])
        db.flush()

        # Staff assignments
        citycare_staff = HospitalStaff(
            hospital_id=citycare_hospital.id,
            user_id=hospital_admin_user.id,
            role_in_hospital="ADMIN"
        )
        metro_staff = HospitalStaff(
            hospital_id=metro_hospital.id,
            user_id=metro_admin_user.id,
            role_in_hospital="ADMIN"
        )
        db.add_all([citycare_staff, metro_staff])

        # 3. Patient Profile & Preferences
        patient_profile = Patient(
            user_id=patient_user.id,
            dob="1992-05-14",
            gender="Female",
            address="Ring Road, Vijayawada",
            external_patient_id="EXT-PAT-1001"
        )
        db.add(patient_profile)
        db.flush()

        patient_prefs = PatientPreference(
            patient_id=patient_profile.id,
            preferred_channel="VOICE",
            preferred_time_of_day="AFTERNOON",
            notes="Prefers afternoon appointments; English/Telugu communication"
        )
        db.add(patient_prefs)

        # 4. Departments & Specialties
        dept_ortho = Department(
            hospital_id=citycare_hospital.id,
            name="Orthopedics & Joint Reconstruction",
            code="ORTHO",
            description="Comprehensive musculoskeletal, joint, and trauma care"
        )
        dept_cardio = Department(
            hospital_id=citycare_hospital.id,
            name="Cardiology & Vascular Sciences",
            code="CARDIO",
            description="Heart care, diagnostics, and preventive cardiology"
        )
        dept_general = Department(
            hospital_id=citycare_hospital.id,
            name="General Medicine & Family Practice",
            code="GENMED",
            description="Primary care, diagnostics, and routine evaluations"
        )

        spec_ortho = Specialty(
            hospital_id=citycare_hospital.id,
            name="Orthopedics",
            code="ORTHO",
            description="Specializes in bones, joints, ligaments, tendons, and spine"
        )
        spec_cardio = Specialty(
            hospital_id=citycare_hospital.id,
            name="Cardiology",
            code="CARDIO",
            description="Specializes in heart disorders and cardiovascular health"
        )
        spec_general = Specialty(
            hospital_id=citycare_hospital.id,
            name="General Medicine",
            code="GENMED",
            description="Specializes in comprehensive adult primary care"
        )

        db.add_all([dept_ortho, dept_cardio, dept_general, spec_ortho, spec_cardio, spec_general])
        db.flush()

        # 5. Doctors
        dr_rao = Doctor(
            hospital_id=citycare_hospital.id,
            user_id=dr_rao_user.id,
            name="Dr. Rao",
            specialty_id=spec_ortho.id,
            department_id=dept_ortho.id,
            qualification="MBBS, MS (Orthopedics), MCh (Joint Surgery)",
            experience_years=14,
            languages="English, Telugu, Hindi",
            consultation_fee=120.0,
            status="ACTIVE",
            external_provider_id="EXT-DOC-RAO-01"
        )

        dr_kumar = Doctor(
            hospital_id=citycare_hospital.id,
            user_id=dr_kumar_user.id,
            name="Dr. Kumar",
            specialty_id=spec_cardio.id,
            department_id=dept_cardio.id,
            qualification="MBBS, MD, DM (Cardiology)",
            experience_years=18,
            languages="English, Telugu, Hindi",
            consultation_fee=150.0,
            status="ACTIVE",
            external_provider_id="EXT-DOC-KUMAR-02"
        )

        dr_priya = Doctor(
            hospital_id=citycare_hospital.id,
            user_id=dr_priya_user.id,
            name="Dr. Priya",
            specialty_id=spec_general.id,
            department_id=dept_general.id,
            qualification="MBBS, MD (General Medicine)",
            experience_years=9,
            languages="English, Telugu",
            consultation_fee=80.0,
            status="ACTIVE",
            external_provider_id="EXT-DOC-PRIYA-03"
        )

        db.add_all([dr_rao, dr_kumar, dr_priya])
        db.flush()

        # 6. Calendars & Availability Slots
        cal_rao = Calendar(
            hospital_id=citycare_hospital.id,
            doctor_id=dr_rao.id,
            name="Dr. Rao Consultation Schedule",
            is_active=True
        )
        cal_kumar = Calendar(
            hospital_id=citycare_hospital.id,
            doctor_id=dr_kumar.id,
            name="Dr. Kumar Cardiology Clinic",
            is_active=True
        )
        cal_priya = Calendar(
            hospital_id=citycare_hospital.id,
            doctor_id=dr_priya.id,
            name="Dr. Priya Primary Care Clinic",
            is_active=True
        )
        db.add_all([cal_rao, cal_kumar, cal_priya])
        db.flush()

        # Deterministic slots for Dr. Rao:
        # Friday 3:00 PM (15:00 UTC)
        # Friday 4:00 PM (16:00 UTC)
        # Saturday 11:00 AM (11:00 UTC)
        friday_date = get_upcoming_weekday(4, 15, 0)
        friday_slot_1 = AvailabilitySlot(
            hospital_id=citycare_hospital.id,
            doctor_id=dr_rao.id,
            calendar_id=cal_rao.id,
            start_time=friday_date,
            end_time=friday_date + timedelta(minutes=45),
            is_booked=False,
            is_blocked=False
        )

        friday_slot_2_time = get_upcoming_weekday(4, 16, 0)
        friday_slot_2 = AvailabilitySlot(
            hospital_id=citycare_hospital.id,
            doctor_id=dr_rao.id,
            calendar_id=cal_rao.id,
            start_time=friday_slot_2_time,
            end_time=friday_slot_2_time + timedelta(minutes=45),
            is_booked=False,
            is_blocked=False
        )

        saturday_slot_time = get_upcoming_weekday(5, 11, 0)
        saturday_slot = AvailabilitySlot(
            hospital_id=citycare_hospital.id,
            doctor_id=dr_rao.id,
            calendar_id=cal_rao.id,
            start_time=saturday_slot_time,
            end_time=saturday_slot_time + timedelta(minutes=45),
            is_booked=False,
            is_blocked=False
        )

        # Slots for Dr. Kumar (Thursday 10 AM, 11 AM)
        thursday_date_1 = get_upcoming_weekday(3, 10, 0)
        kumar_slot_1 = AvailabilitySlot(
            hospital_id=citycare_hospital.id,
            doctor_id=dr_kumar.id,
            calendar_id=cal_kumar.id,
            start_time=thursday_date_1,
            end_time=thursday_date_1 + timedelta(minutes=45),
            is_booked=False,
            is_blocked=False
        )

        # Slots for Dr. Priya (Monday 2 PM, 3 PM)
        monday_date_1 = get_upcoming_weekday(0, 14, 0)
        priya_slot_1 = AvailabilitySlot(
            hospital_id=citycare_hospital.id,
            doctor_id=dr_priya.id,
            calendar_id=cal_priya.id,
            start_time=monday_date_1,
            end_time=monday_date_1 + timedelta(minutes=30),
            is_booked=False,
            is_blocked=False
        )

        db.add_all([friday_slot_1, friday_slot_2, saturday_slot, kumar_slot_1, priya_slot_1])

        # 7. Healthcare System Connection & Mappings
        ehr_conn = HealthcareConnection(
            hospital_id=citycare_hospital.id,
            connector_type="MOCK_EHR",
            base_url="http://localhost:8000/api/mock-ehr",
            status="CONNECTED",
            simulation_mode="NORMAL"
        )
        db.add(ehr_conn)

        mappings = [
            ExternalIdentifierMapping(
                hospital_id=citycare_hospital.id,
                entity_type="PATIENT",
                internal_id=patient_profile.id,
                external_id="EXT-PAT-1001"
            ),
            ExternalIdentifierMapping(
                hospital_id=citycare_hospital.id,
                entity_type="DOCTOR",
                internal_id=dr_rao.id,
                external_id="EXT-DOC-RAO-01"
            ),
            ExternalIdentifierMapping(
                hospital_id=citycare_hospital.id,
                entity_type="DOCTOR",
                internal_id=dr_kumar.id,
                external_id="EXT-DOC-KUMAR-02"
            ),
            ExternalIdentifierMapping(
                hospital_id=citycare_hospital.id,
                entity_type="DOCTOR",
                internal_id=dr_priya.id,
                external_id="EXT-DOC-PRIYA-03"
            ),
            ExternalIdentifierMapping(
                hospital_id=citycare_hospital.id,
                entity_type="FACILITY",
                internal_id=citycare_hospital.id,
                external_id="EXT-FAC-CITYCARE"
            ),
        ]
        db.add_all(mappings)

        # 8. Pre-Visit Questionnaire
        ortho_questionnaire = Questionnaire(
            hospital_id=citycare_hospital.id,
            specialty_id=spec_ortho.id,
            title="Orthopedics Pre-Visit Patient Intake",
            description="Pre-consultation clinical questionnaire to assist the orthopedic care team",
            is_active=True
        )
        db.add(ortho_questionnaire)
        db.flush()

        questions = [
            QuestionnaireQuestion(
                questionnaire_id=ortho_questionnaire.id,
                order_index=1,
                prompt="Which joint or musculoskeletal area is causing discomfort?",
                question_type="CHOICE",
                options_json=json.dumps(["Shoulder", "Knee", "Hip", "Spine/Back", "Other"]),
                is_required=True
            ),
            QuestionnaireQuestion(
                questionnaire_id=ortho_questionnaire.id,
                order_index=2,
                prompt="On a scale of 1 to 10, how would you rate your pain level today?",
                question_type="NUMERIC",
                options_json=None,
                is_required=True
            ),
            QuestionnaireQuestion(
                questionnaire_id=ortho_questionnaire.id,
                order_index=3,
                prompt="Did this condition start following a sudden injury, fall, or accident?",
                question_type="YES_NO",
                options_json=json.dumps(["Yes", "No"]),
                is_required=True
            ),
            QuestionnaireQuestion(
                questionnaire_id=ortho_questionnaire.id,
                order_index=4,
                prompt="Approximately how long have you been experiencing these symptoms?",
                question_type="SHORT_TEXT",
                options_json=None,
                is_required=True
            ),
            QuestionnaireQuestion(
                questionnaire_id=ortho_questionnaire.id,
                order_index=5,
                prompt="Have you had any previous surgery, physical therapy, or imaging (X-ray/MRI) for this issue?",
                question_type="YES_NO",
                options_json=json.dumps(["Yes", "No"]),
                is_required=True
            ),
        ]
        db.add_all(questions)

        # 9. Workflows
        post_booking_wf = Workflow(
            hospital_id=citycare_hospital.id,
            name="Post-Booking Intake & Reminder Workflow",
            trigger_event="APPOINTMENT_CONFIRMED",
            is_active=True
        )
        db.add(post_booking_wf)

        db.commit()
        print("Database seeded successfully with CityCare Hospital, Doctors, Slots, and Questionnaire.")

    except Exception as e:
        db.rollback()
        print(f"Error seeding database: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    import sys
    should_reset = "--reset" in sys.argv
    seed_data(reset=should_reset)
