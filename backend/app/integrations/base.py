from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from pydantic import BaseModel
from datetime import datetime

class ExternalAppointmentRequest(BaseModel):
    patient_external_id: str
    provider_external_id: str
    facility_external_id: str
    start_time: datetime
    end_time: datetime
    appointment_type: str = "IN_PERSON"
    reason: Optional[str] = None
    correlation_id: str
    idempotency_key: str

class ExternalAppointmentRecord(BaseModel):
    external_id: str
    patient_external_id: str
    provider_external_id: str
    facility_external_id: str
    start_time: datetime
    end_time: datetime
    status: str  # BOOKED, RESCHEDULED, CANCELLED
    correlation_id: str
    idempotency_key: str
    created_at: datetime
    metadata: Dict[str, Any] = {}

class EHRIntegrationError(Exception):
    """Raised when an external EHR call fails definitively (e.g. 500, 503)."""
    pass

class EHRTimeoutError(Exception):
    """Raised when an external EHR network call times out with an unknown outcome (e.g. 504)."""
    pass

class HealthcareSystemConnector(ABC):
    """
    Abstract interface for healthcare EHR integrations (Mock EHR, Epic, Cerner, FHIR).
    Ensures appointment service remains completely decoupled from EHR vendor specifics.
    """

    @abstractmethod
    def create_appointment(
        self, request: ExternalAppointmentRequest
    ) -> ExternalAppointmentRecord:
        """Create an appointment in the external healthcare system."""
        pass

    @abstractmethod
    def get_appointment(
        self, external_id: str
    ) -> Optional[ExternalAppointmentRecord]:
        """Retrieve an external appointment by its vendor identifier."""
        pass

    @abstractmethod
    def find_by_correlation(
        self, correlation_id: str, idempotency_key: str, provider_id: str, start_time: datetime
    ) -> Optional[ExternalAppointmentRecord]:
        """
        Queries external EHR to check if an appointment was created during a timeout
        or unknown-outcome scenario, preventing duplicate booking.
        """
        pass

    @abstractmethod
    def verify_appointment(
        self, external_id: str, expected_patient_id: str, expected_provider_id: str, expected_start_time: datetime
    ) -> bool:
        """Verifies external appointment record matches internal booking parameters."""
        pass

    @abstractmethod
    def reschedule_appointment(
        self, external_id: str, new_start_time: datetime, new_end_time: datetime
    ) -> ExternalAppointmentRecord:
        """Reschedule an existing external appointment."""
        pass

    @abstractmethod
    def cancel_appointment(
        self, external_id: str, reason: str
    ) -> bool:
        """Cancel an external appointment."""
        pass
