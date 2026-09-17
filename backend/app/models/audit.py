from sqlalchemy import Column, String, Float, ForeignKey, Index, Text, DateTime
from app.models.base import BaseModel, utc_now

class AuditEvent(BaseModel):
    __tablename__ = "audit_events"

    operation_id = Column(String(100), nullable=True, index=True)
    correlation_id = Column(String(100), nullable=False, index=True)
    actor_id = Column(String(36), nullable=True, index=True)
    actor_role = Column(String(50), nullable=True, index=True)
    hospital_id = Column(String(36), nullable=True, index=True)  # Nullable for platform admin actions
    action = Column(String(100), nullable=False, index=True)
    resource_type = Column(String(100), nullable=False, index=True)
    resource_id = Column(String(100), nullable=True, index=True)
    status = Column(String(50), nullable=False, index=True)  # SUCCESS, FAILED, WARN
    details_json = Column(Text, nullable=True)  # Strictly non-PHI audit metadata

    __table_args__ = (
        Index("idx_audit_tenant_action", "hospital_id", "action"),
        Index("idx_audit_corr_time", "correlation_id", "created_at"),
    )

class OperationalMetric(BaseModel):
    __tablename__ = "operational_metrics"

    metric_name = Column(String(100), nullable=False, index=True)
    metric_value = Column(Float, nullable=False)
    labels_json = Column(Text, nullable=True)
    recorded_at = Column(DateTime(timezone=True), default=utc_now, nullable=False, index=True)
