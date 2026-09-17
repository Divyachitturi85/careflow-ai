from typing import Optional
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.models.user import User, HospitalStaff, Patient
from app.models.doctor import Doctor

def get_user_hospital_id(user: User, db: Session) -> Optional[str]:
    """Resolves the hospital_id for the current user based on their role."""
    if user.role == "HOSPITAL_ADMIN":
        staff = db.query(HospitalStaff).filter(HospitalStaff.user_id == user.id).first()
        return staff.hospital_id if staff else None
    elif user.role == "DOCTOR":
        doctor = db.query(Doctor).filter(Doctor.user_id == user.id).first()
        return doctor.hospital_id if doctor else None
    return None

def enforce_hospital_tenant(hospital_id: str, user: User, db: Session) -> None:
    """
    Enforces that the user has permission to access resources belonging to hospital_id.
    - PLATFORM_ADMIN: allowed across all hospitals.
    - HOSPITAL_ADMIN & DOCTOR: strictly restricted to their assigned hospital_id.
    - PATIENT: forbidden from administrative hospital access.
    """
    if user.role == "PLATFORM_ADMIN":
        return

    if user.role in ("HOSPITAL_ADMIN", "DOCTOR"):
        user_hospital_id = get_user_hospital_id(user, db)
        if not user_hospital_id or user_hospital_id != hospital_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Tenant access denied: You cannot access or modify resources belonging to another hospital."
            )
        return

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Access denied: Patient accounts cannot access hospital administrative resources."
    )

def enforce_patient_ownership(patient_id: str, user: User, db: Session) -> Patient:
    """
    Enforces that a patient can only access their own record.
    Doctors/Admins can access patients only within their tenant context.
    """
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient record not found."
        )

    if user.role == "PLATFORM_ADMIN":
        return patient

    if user.role == "PATIENT":
        if patient.user_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: You do not have permission to access another patient's data."
            )
        return patient

    # Hospital admin / Doctor: check that patient has interacted with their hospital
    user_hospital_id = get_user_hospital_id(user, db)
    if not user_hospital_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")
    
    return patient

def enforce_doctor_ownership(doctor_id: str, user: User, db: Session) -> Doctor:
    """
    Enforces doctor ownership and hospital admin tenant boundaries over doctor resources.
    """
    doctor = db.query(Doctor).filter(Doctor.id == doctor_id).first()
    if not doctor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Doctor record not found."
        )

    if user.role == "PLATFORM_ADMIN":
        return doctor

    if user.role == "DOCTOR":
        if doctor.user_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: You cannot access or modify another doctor's private profile or schedule."
            )
        return doctor

    if user.role == "HOSPITAL_ADMIN":
        admin_hospital_id = get_user_hospital_id(user, db)
        if doctor.hospital_id != admin_hospital_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Tenant access denied: Doctor belongs to another hospital."
            )
        return doctor

    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")
