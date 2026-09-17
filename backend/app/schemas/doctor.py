from typing import Optional
from pydantic import BaseModel, ConfigDict

class DoctorResponse(BaseModel):
    id: str
    hospital_id: str
    hospital_name: Optional[str] = None
    name: str
    specialty_id: Optional[str] = None
    specialty_name: Optional[str] = None
    qualification: Optional[str] = None
    experience_years: int
    languages: str
    consultation_fee: float
    status: str
    external_provider_id: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
