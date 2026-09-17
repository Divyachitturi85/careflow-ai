from typing import Any, Dict, Optional, List
from datetime import datetime
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session, joinedload
from app.models.doctor import Doctor
from app.models.hospital import Hospital, Specialty
from app.capabilities.base import BaseCapability
from app.services.scheduling_service import SchedulingService

class SearchDoctorsInput(BaseModel):
    specialty: Optional[str] = Field(None, description="Doctor medical specialty e.g. Orthopedics")
    hospital_id: Optional[str] = Field(None, description="Filter by hospital ID")
    city: Optional[str] = Field(None, description="Filter by city name")
    name: Optional[str] = Field(None, description="Doctor name keyword")

class SearchDoctorsCapability(BaseCapability):
    name = "search_doctors"
    description = "Search active physicians and specialists across hospitals."
    parameters_schema = SearchDoctorsInput

    def execute(
        self,
        db: Session,
        current_user: Any,
        context: Dict[str, Any],
        correlation_id: str,
        specialty: Optional[str] = None,
        hospital_id: Optional[str] = None,
        city: Optional[str] = None,
        name: Optional[str] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        query = (
            db.query(Doctor)
            .join(Hospital, Doctor.hospital_id == Hospital.id)
            .outerjoin(Specialty, Doctor.specialty_id == Specialty.id)
            .options(joinedload(Doctor.hospital), joinedload(Doctor.specialty))
            .filter(Doctor.status == "ACTIVE", Hospital.status == "APPROVED")
        )

        if specialty:
            query = query.filter(Specialty.name.ilike(f"%{specialty}%"))
        if hospital_id:
            query = query.filter(Doctor.hospital_id == hospital_id)
        if city:
            query = query.filter(Hospital.city.ilike(f"%{city}%"))
        if name:
            query = query.filter(Doctor.name.ilike(f"%{name}%"))

        doctors = query.all()
        return {
            "count": len(doctors),
            "doctors": [
                {
                    "id": d.id,
                    "name": d.name,
                    "specialty": d.specialty.name if d.specialty else "General",
                    "hospital_id": d.hospital_id,
                    "hospital_name": d.hospital.name if d.hospital else None,
                    "qualification": d.qualification,
                    "experience_years": d.experience_years,
                    "consultation_fee": d.consultation_fee,
                    "languages": d.languages,
                }
                for d in doctors
            ],
        }

class CheckAvailabilityInput(BaseModel):
    doctor_id: Optional[str] = Field(None, description="Target doctor ID")
    hospital_id: Optional[str] = Field(None, description="Target hospital ID")
    specialty: Optional[str] = Field(None, description="Specialty to find open slots for")
    city: Optional[str] = Field(None, description="City name")
    name: Optional[str] = Field(None, description="Doctor name keyword")
    doctor_name: Optional[str] = Field(None, description="Doctor name keyword")
    start_date: Optional[datetime] = Field(None, description="Filter slots after date/time")
    end_date: Optional[datetime] = Field(None, description="Filter slots before date/time")

class CheckAvailabilityCapability(BaseCapability):
    name = "check_availability"
    description = "Retrieves REAL database-backed availability slots for active physicians."
    parameters_schema = CheckAvailabilityInput

    def execute(
        self,
        db: Session,
        current_user: Any,
        context: Dict[str, Any],
        correlation_id: str,
        doctor_id: Optional[str] = None,
        hospital_id: Optional[str] = None,
        specialty: Optional[str] = None,
        city: Optional[str] = None,
        name: Optional[str] = None,
        doctor_name: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        target_name = name or doctor_name
        if target_name and not doctor_id:
            doc = db.query(Doctor).filter(Doctor.name.ilike(f"%{target_name}%")).first()
            if doc:
                doctor_id = doc.id

        slots = SchedulingService.get_available_slots(
            db=db,
            doctor_id=doctor_id,
            hospital_id=hospital_id,
            specialty=specialty,
            city=city,
            start_date=start_date,
            end_date=end_date,
        )

        return {
            "count": len(slots),
            "slots": [
                {
                    "slot_id": s.slot_id,
                    "doctor_id": s.doctor_id,
                    "doctor_name": s.doctor_name,
                    "hospital_id": s.hospital_id,
                    "hospital_name": s.hospital_name,
                    "specialty": s.specialty,
                    "start_time": s.start_time.isoformat(),
                    "end_time": s.end_time.isoformat(),
                    "formatted_time": s.start_time.strftime("%A, %b %d at %I:%M %p"),
                }
                for s in slots
            ],
        }
