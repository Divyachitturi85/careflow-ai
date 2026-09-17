from typing import Dict, List, Optional
from app.capabilities.base import BaseCapability, CapabilityResult
from app.capabilities.hospital_caps import SearchHospitalsCapability
from app.capabilities.scheduling_caps import SearchDoctorsCapability, CheckAvailabilityCapability
from app.capabilities.appointment_caps import (
    CreateAppointmentCapability,
    GetAppointmentCapability,
    ListAppointmentsCapability,
    RescheduleAppointmentCapability,
    CancelAppointmentCapability,
)
from app.capabilities.context_caps import TransferToHumanCapability

CAPABILITIES_LIST: List[BaseCapability] = [
    SearchHospitalsCapability(),
    SearchDoctorsCapability(),
    CheckAvailabilityCapability(),
    CreateAppointmentCapability(),
    GetAppointmentCapability(),
    ListAppointmentsCapability(),
    RescheduleAppointmentCapability(),
    CancelAppointmentCapability(),
    TransferToHumanCapability(),
]

CAPABILITY_REGISTRY: Dict[str, BaseCapability] = {
    cap.name: cap for cap in CAPABILITIES_LIST
}

def get_capability(name: str) -> Optional[BaseCapability]:
    return CAPABILITY_REGISTRY.get(name)

def list_capabilities() -> List[BaseCapability]:
    return CAPABILITIES_LIST

__all__ = [
    "BaseCapability",
    "CapabilityResult",
    "CAPABILITY_REGISTRY",
    "get_capability",
    "list_capabilities",
    "SearchHospitalsCapability",
    "SearchDoctorsCapability",
    "CheckAvailabilityCapability",
    "CreateAppointmentCapability",
    "GetAppointmentCapability",
    "ListAppointmentsCapability",
    "RescheduleAppointmentCapability",
    "CancelAppointmentCapability",
    "TransferToHumanCapability",
]
