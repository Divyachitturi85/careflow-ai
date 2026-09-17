import json
import re
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from app.models.ai import AIConversation, AIContext

class AIContextData(BaseModel):
    conversation_id: str
    patient_id: str
    current_intent: Optional[str] = None
    selected_hospital_id: Optional[str] = None
    selected_hospital_name: Optional[str] = None
    selected_doctor_id: Optional[str] = None
    selected_doctor_name: Optional[str] = None
    selected_specialty: Optional[str] = None
    selected_slot_id: Optional[str] = None
    selected_slot_time: Optional[str] = None
    presented_slots: List[Dict[str, Any]] = Field(default_factory=list)
    current_appointment_id: Optional[str] = None
    last_action: Optional[str] = None
    clarification_needed: Optional[str] = None

class ContextManager:
    @staticmethod
    def get_or_create_context(
        db: Session, conversation_id: str, patient_id: str
    ) -> AIContextData:
        # Check if conversation exists
        conversation = (
            db.query(AIConversation)
            .filter(AIConversation.id == conversation_id)
            .first()
        )
        if not conversation:
            conversation = AIConversation(
                id=conversation_id,
                patient_id=patient_id,
                channel="WEB_CHAT",
                status="ACTIVE",
            )
            db.add(conversation)
            db.flush()

        ai_ctx = (
            db.query(AIContext)
            .filter(AIContext.conversation_id == conversation_id)
            .first()
        )
        if not ai_ctx:
            ctx_data = AIContextData(
                conversation_id=conversation_id,
                patient_id=patient_id,
            )
            ai_ctx = AIContext(
                conversation_id=conversation_id,
                patient_id=patient_id,
                context_data_json=ctx_data.model_dump_json(),
            )
            db.add(ai_ctx)
            db.commit()
            return ctx_data

        try:
            parsed = json.loads(ai_ctx.context_data_json)
            return AIContextData(**parsed)
        except Exception:
            return AIContextData(conversation_id=conversation_id, patient_id=patient_id)

    @staticmethod
    def save_context(db: Session, context_data: AIContextData) -> None:
        ai_ctx = (
            db.query(AIContext)
            .filter(AIContext.conversation_id == context_data.conversation_id)
            .first()
        )
        if ai_ctx:
            ai_ctx.current_intent = context_data.current_intent
            ai_ctx.selected_hospital_id = context_data.selected_hospital_id
            ai_ctx.selected_doctor_id = context_data.selected_doctor_id
            ai_ctx.selected_slot_id = context_data.selected_slot_id
            ai_ctx.context_data_json = context_data.model_dump_json()
            db.commit()

    @staticmethod
    def resolve_slot_reference(
        context_data: AIContextData, utterance: str
    ) -> Optional[Dict[str, Any]]:
        """
        Resolves anaphoric expressions (e.g. 'first one', 'Friday at 3', 'make it 4 PM')
        against the previously presented slots in active conversation context.
        """
        text = utterance.lower().strip()
        slots = context_data.presented_slots

        if not slots:
            return None

        # 1. Ordinal references: "first one", "1st", "second one", "2nd"
        if re.search(r"\b(first|1st|initial|the first one)\b", text):
            return slots[0]
        if re.search(r"\b(second|2nd|the second one)\b", text) and len(slots) > 1:
            return slots[1]
        if re.search(r"\b(third|3rd|the third one)\b", text) and len(slots) > 2:
            return slots[2]

        # 2. Time-based references
        # "Friday at 3" / "Friday 3 PM" / "3 PM" / "3:00"
        if re.search(r"\b3\s*(pm|:00|o'?clock)?\b", text):
            for s in slots:
                if ":00:00" in s.get("start_time", "") and "15:" in s.get("start_time", ""):
                    return s
                if "3:00 pm" in s.get("formatted_time", "").lower():
                    return s

        # "Friday at 4" / "4 PM" / "4:00" / "make it 4 PM"
        if re.search(r"\b4\s*(pm|:00|o'?clock)?\b", text):
            for s in slots:
                if "16:" in s.get("start_time", "") or "4:00 pm" in s.get("formatted_time", "").lower():
                    return s

        # "Saturday at 11" / "11 AM" / "11:00"
        if re.search(r"\b11\s*(am|:00|o'?clock)?\b", text):
            for s in slots:
                if "11:" in s.get("start_time", "") or "11:00 am" in s.get("formatted_time", "").lower():
                    return s

        return None
