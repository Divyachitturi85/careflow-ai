from typing import Any, Dict, Optional, List
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session, joinedload
from app.models.hospital import Hospital, Specialty
from app.capabilities.base import BaseCapability

class SearchHospitalsInput(BaseModel):
    city: Optional[str] = Field(None, description="City where the hospital is located")
    specialty: Optional[str] = Field(None, description="Medical specialty offered")

class SearchHospitalsCapability(BaseCapability):
    name = "search_hospitals"
    description = "Search approved hospitals by city or offered medical specialty."
    parameters_schema = SearchHospitalsInput

    def execute(
        self,
        db: Session,
        current_user: Any,
        context: Dict[str, Any],
        correlation_id: str,
        city: Optional[str] = None,
        specialty: Optional[str] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        query = (
            db.query(Hospital)
            .options(joinedload(Hospital.specialties))
            .filter(Hospital.status == "APPROVED")
        )

        if city:
            query = query.filter(Hospital.city.ilike(f"%{city}%"))
        if specialty:
            query = query.join(Hospital.specialties).filter(Specialty.name.ilike(f"%{specialty}%"))

        hospitals = query.all()
        return {
            "count": len(hospitals),
            "hospitals": [
                {
                    "id": h.id,
                    "name": h.name,
                    "city": h.city,
                    "address": h.address,
                    "phone": h.phone,
                    "specialties": [s.name for s in h.specialties],
                }
                for h in hospitals
            ],
        }
