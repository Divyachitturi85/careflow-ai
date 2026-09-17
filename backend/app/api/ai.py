from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.user import User
from app.security.auth import get_current_user
from app.ai.agent import AIAgent, AIChatRequest, AIChatResponse

router = APIRouter(prefix="/api/ai", tags=["AI Patient Access Agent"])

@router.post("/chat", response_model=AIChatResponse)
def chat_with_agent(
    request: AIChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Patient conversational endpoint. Coordinates intent detection,
    anaphoric context resolution, safety guardrails, controlled capability execution,
    and verified appointment confirmation.
    """
    return AIAgent.process_patient_turn(db, request, current_user)
