from typing import List, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.user import User
from app.models.integration import IntegrationOperation, ReconciliationRecord
from app.security.rbac import require_staff_or_admin, require_hospital_admin
from app.integrations.mock_ehr import mock_ehr_connector

router = APIRouter(prefix="/api/admin", tags=["Admin & Observability"])

class SimulationModeRequest(BaseModel):
    mode: str  # NORMAL, TIMEOUT, FAILURE, UNKNOWN_OUTCOME

class SimulationModeResponse(BaseModel):
    mode: str
    description: str

class IntegrationOperationResponse(BaseModel):
    id: str
    operation_id: str
    correlation_id: str
    hospital_id: str
    operation_type: str
    status: str
    response_code: Optional[int] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class ReconciliationRecordResponse(BaseModel):
    id: str
    operation_id: str
    appointment_id: str
    hospital_id: str
    reason: str
    status: str
    retry_count: int
    resolution_notes: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class ResolveReconciliationRequest(BaseModel):
    resolution_notes: str

@router.get("/simulation-mode", response_model=SimulationModeResponse)
def get_simulation_mode(current_user: User = Depends(require_staff_or_admin)):
    """Inspect current Mock EHR simulation mode."""
    descriptions = {
        "NORMAL": "Normal synchronous integration behavior",
        "TIMEOUT": "Network timeout before external record creation",
        "FAILURE": "Hard upstream EHR 503 service outage",
        "UNKNOWN_OUTCOME": "Network timeout after external creation (triggers query-before-retry recovery)",
    }
    mode = mock_ehr_connector.simulation_mode
    return SimulationModeResponse(mode=mode, description=descriptions.get(mode, ""))

@router.post("/simulation-mode", response_model=SimulationModeResponse)
def set_simulation_mode(
    request: SimulationModeRequest,
    current_user: User = Depends(require_staff_or_admin),
):
    """
    Developer/Admin demo control to toggle Mock EHR failure modes:
    - NORMAL
    - TIMEOUT
    - FAILURE
    - UNKNOWN_OUTCOME
    """
    try:
        mock_ehr_connector.set_simulation_mode(request.mode)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return get_simulation_mode(current_user)

@router.get("/operations", response_model=List[IntegrationOperationResponse])
def get_integration_operations(
    hospital_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    current_user: User = Depends(require_hospital_admin),
    db: Session = Depends(get_db),
):
    """View integration operation logs with correlation IDs."""
    query = db.query(IntegrationOperation)
    if current_user.role == "HOSPITAL_ADMIN" and current_user.hospital_staff:
        query = query.filter(IntegrationOperation.hospital_id == current_user.hospital_staff.hospital_id)
    elif hospital_id:
        query = query.filter(IntegrationOperation.hospital_id == hospital_id)

    if status:
        query = query.filter(IntegrationOperation.status == status)

    return query.order_by(IntegrationOperation.created_at.desc()).limit(100).all()

@router.get("/reconciliations", response_model=List[ReconciliationRecordResponse])
def get_reconciliation_records(
    current_user: User = Depends(require_hospital_admin),
    db: Session = Depends(get_db),
):
    """View unresolvable integration records requiring administrative attention."""
    query = db.query(ReconciliationRecord)
    if current_user.role == "HOSPITAL_ADMIN" and current_user.hospital_staff:
        query = query.filter(ReconciliationRecord.hospital_id == current_user.hospital_staff.hospital_id)

    return query.order_by(ReconciliationRecord.created_at.desc()).all()

@router.post("/reconciliations/{record_id}/resolve", response_model=ReconciliationRecordResponse)
def resolve_reconciliation_record(
    record_id: str,
    request: ResolveReconciliationRequest,
    current_user: User = Depends(require_hospital_admin),
    db: Session = Depends(get_db),
):
    """Resolve an open reconciliation record with operator notes."""
    record = db.query(ReconciliationRecord).filter(ReconciliationRecord.id == record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Reconciliation record not found.")

    record.status = "RESOLVED"
    record.resolution_notes = request.resolution_notes
    record.resolved_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(record)
    return record
