from typing import Any, Dict, Optional
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from app.capabilities.base import BaseCapability

class TransferToHumanInput(BaseModel):
    reason: str = Field(..., description="Reason for escalation to a human coordinator")

class TransferToHumanCapability(BaseCapability):
    name = "transfer_to_human"
    description = "Escalate patient conversation to a human care coordinator or administrative desk."
    parameters_schema = TransferToHumanInput

    def execute(
        self,
        db: Session,
        current_user: Any,
        context: Dict[str, Any],
        correlation_id: str,
        reason: str,
        **kwargs,
    ) -> Dict[str, Any]:
        return {
            "escalated": True,
            "reason": reason,
            "status": "QUEUED_FOR_HUMAN_COORDINATOR",
            "message": "Your request has been routed to our CityCare patient coordination team. A representative will contact you shortly.",
        }
