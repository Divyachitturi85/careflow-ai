from sqlalchemy import Column, String, Integer, Boolean, ForeignKey, Index, Text, DateTime, UniqueConstraint
from sqlalchemy.orm import relationship
from app.models.base import BaseModel

class HealthcareConnection(BaseModel):
    __tablename__ = "healthcare_connections"

    hospital_id = Column(String(36), ForeignKey("hospitals.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    connector_type = Column(String(50), default="MOCK_EHR", nullable=False)
    base_url = Column(String(255), default="http://localhost:8000/api/mock-ehr", nullable=False)
    status = Column(String(50), default="CONNECTED", nullable=False)  # CONNECTED, DEGRADED, DISCONNECTED
    simulation_mode = Column(String(50), default="NORMAL", nullable=False)  # NORMAL, TIMEOUT, FAILURE, UNKNOWN_OUTCOME

    # Relationships
    hospital = relationship("Hospital", back_populates="ehr_connection")

class ExternalIdentifierMapping(BaseModel):
    __tablename__ = "external_identifier_mappings"

    hospital_id = Column(String(36), ForeignKey("hospitals.id", ondelete="CASCADE"), nullable=False, index=True)
    entity_type = Column(String(50), nullable=False, index=True)  # PATIENT, DOCTOR, APPOINTMENT, FACILITY
    internal_id = Column(String(36), nullable=False, index=True)
    external_id = Column(String(100), nullable=False, index=True)

    __table_args__ = (
        UniqueConstraint("hospital_id", "entity_type", "internal_id", name="uq_tenant_entity_mapping"),
        Index("idx_mapping_ext", "hospital_id", "entity_type", "external_id"),
    )

class IntegrationOperation(BaseModel):
    __tablename__ = "integration_operations"

    operation_id = Column(String(100), unique=True, nullable=False, index=True)
    correlation_id = Column(String(100), nullable=False, index=True)
    hospital_id = Column(String(36), ForeignKey("hospitals.id", ondelete="CASCADE"), nullable=False, index=True)
    operation_type = Column(String(100), nullable=False, index=True)  # APPOINTMENT_CREATE, APPOINTMENT_VERIFY, etc.
    payload_json = Column(Text, nullable=True)
    response_code = Column(Integer, nullable=True)
    response_payload_json = Column(Text, nullable=True)
    status = Column(String(50), nullable=False, index=True)  # SUCCESS, TIMEOUT, FAILED, UNKNOWN

    __table_args__ = (
        Index("idx_op_tenant_status", "hospital_id", "status"),
    )

class IntegrationVerification(BaseModel):
    __tablename__ = "integration_verifications"

    operation_id = Column(String(100), nullable=False, index=True)
    internal_appointment_id = Column(String(36), ForeignKey("appointments.id", ondelete="CASCADE"), nullable=False, index=True)
    external_appointment_id = Column(String(100), nullable=False, index=True)
    verified = Column(Boolean, default=False, nullable=False, index=True)
    discrepancy_details = Column(Text, nullable=True)
    verified_at = Column(DateTime(timezone=True), nullable=True)

class ReconciliationRecord(BaseModel):
    __tablename__ = "reconciliation_records"

    operation_id = Column(String(100), nullable=False, index=True)
    appointment_id = Column(String(36), ForeignKey("appointments.id", ondelete="CASCADE"), nullable=False, index=True)
    hospital_id = Column(String(36), ForeignKey("hospitals.id", ondelete="CASCADE"), nullable=False, index=True)
    reason = Column(String(255), nullable=False)
    status = Column(String(50), default="OPEN", nullable=False, index=True)  # OPEN, RESOLVED, IGNORED
    retry_count = Column(Integer, default=0, nullable=False)
    resolution_notes = Column(Text, nullable=True)
    resolved_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("idx_recon_tenant_status", "hospital_id", "status"),
    )
