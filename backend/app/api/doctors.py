from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, joinedload
from app.db.session import get_db
from app.models.doctor import Doctor
from app.models.hospital import Hospital, Specialty
from app.schemas.doctor import DoctorResponse

router = APIRouter(prefix="/api/doctors", tags=["Doctors"])

@router.get("", response_model=List[DoctorResponse])
def get_doctors(
    hospital_id: Optional[str] = Query(None, description="Filter by hospital ID"),
    specialty: Optional[str] = Query(None, description="Filter by specialty (e.g. Orthopedics, Cardiology)"),
    city: Optional[str] = Query(None, description="Filter by hospital city"),
    name: Optional[str] = Query(None, description="Filter by doctor name"),
    db: Session = Depends(get_db),
):
    """
    Search active doctors across approved hospitals.
    Supports filtering by hospital, specialty, city, and name.
    """
    query = (
        db.query(Doctor)
        .join(Hospital, Doctor.hospital_id == Hospital.id)
        .outerjoin(Specialty, Doctor.specialty_id == Specialty.id)
        .options(
            joinedload(Doctor.hospital),
            joinedload(Doctor.specialty),
        )
        .filter(
            Doctor.status == "ACTIVE",
            Hospital.status == "APPROVED",
        )
    )

    if hospital_id:
        query = query.filter(Doctor.hospital_id == hospital_id)
    if specialty:
        query = query.filter(Specialty.name.ilike(f"%{specialty}%"))
    if city:
        query = query.filter(Hospital.city.ilike(f"%{city}%"))
    if name:
        query = query.filter(Doctor.name.ilike(f"%{name}%"))

    doctors = query.all()

    return [
        DoctorResponse(
            id=d.id,
            hospital_id=d.hospital_id,
            hospital_name=d.hospital.name if d.hospital else None,
            name=d.name,
            specialty_id=d.specialty_id,
            specialty_name=d.specialty.name if d.specialty else None,
            qualification=d.qualification,
            experience_years=d.experience_years,
            languages=d.languages,
            consultation_fee=d.consultation_fee,
            status=d.status,
            external_provider_id=d.external_provider_id,
        )
        for d in doctors
    ]

@router.get("/{doctor_id}", response_model=DoctorResponse)
def get_doctor_by_id(doctor_id: str, db: Session = Depends(get_db)):
    """Retrieve profile and qualifications for a specific doctor."""
    doctor = (
        db.query(Doctor)
        .options(
            joinedload(Doctor.hospital),
            joinedload(Doctor.specialty),
        )
        .filter(Doctor.id == doctor_id)
        .first()
    )
    if not doctor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Doctor with ID '{doctor_id}' was not found.",
        )

    return DoctorResponse(
        id=doctor.id,
        hospital_id=doctor.hospital_id,
        hospital_name=doctor.hospital.name if doctor.hospital else None,
        name=doctor.name,
        specialty_id=doctor.specialty_id,
        specialty_name=doctor.specialty.name if doctor.specialty else None,
        qualification=doctor.qualification,
        experience_years=doctor.experience_years,
        languages=doctor.languages,
        consultation_fee=doctor.consultation_fee,
        status=doctor.status,
        external_provider_id=doctor.external_provider_id,
    )
