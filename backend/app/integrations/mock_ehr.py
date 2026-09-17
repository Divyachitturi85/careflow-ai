import uuid
from datetime import datetime, timezone
from typing import Dict, Optional
from app.integrations.base import (
    HealthcareSystemConnector,
    ExternalAppointmentRequest,
    ExternalAppointmentRecord,
    EHRIntegrationError,
    EHRTimeoutError,
)

class MockEHRConnector(HealthcareSystemConnector):
    """
    Mock implementation of an external Hospital EHR system (e.g. Epic, Cerner).
    Maintains an independent external record store and supports failure simulations:
    - NORMAL: Normal synchronous success
    - TIMEOUT: Network timeout without record creation
    - FAILURE: Hard upstream EHR failure (503)
    - UNKNOWN_OUTCOME: Record created in EHR, but network drops before response reaches CareFlow AI
    """

    def __init__(self, default_mode: str = "NORMAL"):
        self.simulation_mode: str = default_mode.upper()
        self._external_db: Dict[str, ExternalAppointmentRecord] = {}
        self._seq: int = 1000

    def set_simulation_mode(self, mode: str):
        valid_modes = {"NORMAL", "TIMEOUT", "FAILURE", "UNKNOWN_OUTCOME"}
        mode_upper = mode.upper()
        if mode_upper not in valid_modes:
            raise ValueError(f"Invalid mode '{mode}'. Must be one of {valid_modes}")
        self.simulation_mode = mode_upper

    def reset_external_db(self):
        """Helper to clear external database for clean testing."""
        self._external_db.clear()
        self._seq = 1000

    def create_appointment(
        self, request: ExternalAppointmentRequest
    ) -> ExternalAppointmentRecord:
        # Check idempotency first in external store
        for record in self._external_db.values():
            if record.idempotency_key == request.idempotency_key:
                return record

        # 1. Failure simulation: Hard upstream error
        if self.simulation_mode == "FAILURE":
            raise EHRIntegrationError(
                "EHR upstream service unavailable (HTTP 503 - Service Unavailable)"
            )

        # 2. Failure simulation: Network timeout before creation
        if self.simulation_mode == "TIMEOUT":
            raise EHRTimeoutError(
                "EHR gateway connection timeout (HTTP 504 - Gateway Timeout)"
            )

        # 3. Create the external record in Mock EHR
        self._seq += 1
        external_id = f"EXT-APT-{self._seq}"
        record = ExternalAppointmentRecord(
            external_id=external_id,
            patient_external_id=request.patient_external_id,
            provider_external_id=request.provider_external_id,
            facility_external_id=request.facility_external_id,
            start_time=request.start_time,
            end_time=request.end_time,
            status="BOOKED",
            correlation_id=request.correlation_id,
            idempotency_key=request.idempotency_key,
            created_at=datetime.now(timezone.utc),
            metadata={"appointment_type": request.appointment_type, "reason": request.reason},
        )
        self._external_db[external_id] = record

        # 4. Failure simulation: Unknown outcome (created on server, but client timeout)
        if self.simulation_mode == "UNKNOWN_OUTCOME":
            raise EHRTimeoutError(
                f"Network dropped after external commit. Record {external_id} was created, but response was lost."
            )

        return record

    def get_appointment(
        self, external_id: str
    ) -> Optional[ExternalAppointmentRecord]:
        return self._external_db.get(external_id)

    def find_by_correlation(
        self, correlation_id: str, idempotency_key: str, provider_id: str, start_time: datetime
    ) -> Optional[ExternalAppointmentRecord]:
        """
        Searches the Mock EHR for an existing appointment by idempotency key or provider & slot time.
        Used by the recovery engine to determine actual state after a timeout.
        """
        for record in self._external_db.values():
            if record.idempotency_key == idempotency_key:
                return record
            if record.correlation_id == correlation_id:
                return record
            if (
                record.provider_external_id == provider_id
                and record.start_time == start_time
                and record.status != "CANCELLED"
            ):
                return record
        return None

    def verify_appointment(
        self,
        external_id: str,
        expected_patient_id: str,
        expected_provider_id: str,
        expected_start_time: datetime,
    ) -> bool:
        record = self.get_appointment(external_id)
        if not record:
            return False
        if record.status != "BOOKED":
            return False
        if record.patient_external_id != expected_patient_id:
            return False
        if record.provider_external_id != expected_provider_id:
            return False
        if record.start_time != expected_start_time:
            return False
        return True

    def reschedule_appointment(
        self, external_id: str, new_start_time: datetime, new_end_time: datetime
    ) -> ExternalAppointmentRecord:
        record = self._external_db.get(external_id)
        if not record:
            raise EHRIntegrationError(f"External appointment '{external_id}' not found.")
        
        record.start_time = new_start_time
        record.end_time = new_end_time
        record.status = "RESCHEDULED"
        return record

    def cancel_appointment(self, external_id: str, reason: str) -> bool:
        record = self._external_db.get(external_id)
        if not record:
            return False
        record.status = "CANCELLED"
        record.metadata["cancel_reason"] = reason
        return True

# Singleton connector instance for the application
mock_ehr_connector = MockEHRConnector()
