from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, joinedload
from app.db.session import get_db
from app.models.hospital import Hospital, Specialty
from app.schemas.hospital import HospitalResponse, SpecialtyResponse, DepartmentResponse

router = APIRouter(prefix="/api/hospitals", tags=["Hospitals"])

@router.get("", response_model=List[HospitalResponse])
def get_hospitals(
    city: Optional[str] = Query(None, description="Filter by city name"),
    specialty: Optional[str] = Query(None, description="Filter by specialty offered"),
    db: Session = Depends(get_db),
):
    """
    List approved hospitals available for patient care.
    Supports filtering by city and specialty.
    """
    query = (
        db.query(Hospital)
        .options(
            joinedload(Hospital.specialties),
            joinedload(Hospital.departments),
        )
        .filter(Hospital.status == "APPROVED")
    )

    if city:
        query = query.filter(Hospital.city.ilike(f"%{city}%"))

    if specialty:
        query = query.join(Hospital.specialties).filter(Specialty.name.ilike(f"%{specialty}%"))

    hospitals = query.all()

    return [
        HospitalResponse(
            id=h.id,
            name=h.name,
            status=h.status,
            city=h.city,
            address=h.address,
            phone=h.phone,
            email=h.email,
            external_facility_id=h.external_facility_id,
            specialties=[SpecialtyResponse.model_validate(s) for s in h.specialties],
            departments=[DepartmentResponse.model_validate(d) for d in h.departments],
        )
        for h in hospitals
    ]

@router.get("/{hospital_id}", response_model=HospitalResponse)
def get_hospital_by_id(hospital_id: str, db: Session = Depends(get_db)):
    """Retrieve details for a specific hospital."""
    hospital = (
        db.query(Hospital)
        .options(
            joinedload(Hospital.specialties),
            joinedload(Hospital.departments),
        )
        .filter(Hospital.id == hospital_id)
        .first()
    )
    if not hospital:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Hospital with ID '{hospital_id}' not found.",
        )

    return HospitalResponse(
        id=hospital.id,
        name=hospital.name,
        status=hospital.status,
        city=hospital.city,
        address=hospital.address,
        phone=hospital.phone,
        email=hospital.email,
        external_facility_id=hospital.external_facility_id,
        specialties=[SpecialtyResponse.model_validate(s) for s in hospital.specialties],
        departments=[DepartmentResponse.model_validate(d) for d in hospital.departments],
    )
