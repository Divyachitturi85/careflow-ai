from typing import Optional, List
from pydantic import BaseModel, ConfigDict

class SpecialtyResponse(BaseModel):
    id: str
    name: str
    code: Optional[str] = None
    description: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

class DepartmentResponse(BaseModel):
    id: str
    name: str
    code: Optional[str] = None
    description: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

class HospitalResponse(BaseModel):
    id: str
    name: str
    status: str
    city: str
    address: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    external_facility_id: Optional[str] = None
    specialties: List[SpecialtyResponse] = []
    departments: List[DepartmentResponse] = []

    model_config = ConfigDict(from_attributes=True)
