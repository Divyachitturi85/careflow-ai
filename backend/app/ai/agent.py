import uuid
import json
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from app.models.user import User
from app.models.audit import AuditEvent
from app.ai.safety import AISafetyGuard
from app.ai.context import ContextManager, AIContextData
from app.ai.llm_provider import get_llm_provider, ToolCall
from app.capabilities import CAPABILITY_REGISTRY

class AIChatRequest(BaseModel):
    conversation_id: Optional[str] = Field(None, description="Active conversation UUID")
    message: str = Field(..., description="Patient natural language message")

class AIChatResponse(BaseModel):
    conversation_id: str
    message: str
    intent: str
    tool_calls: List[Dict[str, Any]] = []
    context: Dict[str, Any] = {}
    slots: List[Dict[str, Any]] = []
    appointment: Optional[Dict[str, Any]] = None
    is_safe: bool = True

class AIAgent:
    @staticmethod
    def process_patient_turn(
        db: Session,
        request: AIChatRequest,
        current_user: User,
    ) -> AIChatResponse:
        correlation_id = f"CORR-AI-{uuid.uuid4().hex[:12].upper()}"
        conversation_id = request.conversation_id or str(uuid.uuid4())
        patient_id = current_user.patient_profile.id if current_user.patient_profile else current_user.id

        # 1. AI Safety & Clinical Boundary Guard
        is_safe, refusal_msg, violation = AISafetyGuard.inspect_message(request.message)
        if not is_safe:
            # Audit log safety event
            db.add(
                AuditEvent(
                    correlation_id=correlation_id,
                    actor_id=current_user.id,
                    actor_role=current_user.role,
                    action="AI_SAFETY_VIOLATION_BLOCKED",
                    resource_type="AI_CONVERSATION",
                    resource_id=conversation_id,
                    status="SUCCESS",
                    details_json=json.dumps({"violation": violation}),
                )
            )
            db.commit()

            return AIChatResponse(
                conversation_id=conversation_id,
                message=refusal_msg or "I cannot provide medical advice.",
                intent="SAFETY_REFUSAL",
                is_safe=False,
            )

        # 2. Retrieve / initialize structured conversation context
        context_data = ContextManager.get_or_create_context(db, conversation_id, patient_id)

        # 3. Check for anaphoric slot selection against active context:
        # e.g., "book the first one", "Friday at 3", "actually make that 4 PM"
        slot_match = ContextManager.resolve_slot_reference(context_data, request.message)

        executed_tool_calls: List[Dict[str, Any]] = []
        confirmed_appointment: Optional[Dict[str, Any]] = None
        slots_to_return: List[Dict[str, Any]] = []

        if slot_match:
            # User is selecting a real presented slot from context
            selected_slot_id = slot_match["slot_id"]
            context_data.selected_slot_id = selected_slot_id
            context_data.selected_slot_time = slot_match.get("start_time")
            context_data.current_intent = "BOOK_APPOINTMENT"

            create_cap = CAPABILITY_REGISTRY.get("create_appointment")
            assert create_cap is not None

            res = create_cap.run(
                db=db,
                current_user=current_user,
                context=context_data.model_dump(),
                correlation_id=correlation_id,
                arguments={"slot_id": selected_slot_id},
                conversation_id=conversation_id,
            )

            executed_tool_calls.append({"name": "create_appointment", "result": res.model_dump()})

            if res.success and res.data:
                confirmed_appointment = res.data
                context_data.current_appointment_id = res.data["id"]
                formatted_time = slot_match.get("formatted_time", "your requested time")
                doctor_name = res.data.get("doctor_name", "your doctor")
                hospital_name = res.data.get("hospital_name", "CityCare Hospital")
                ext_id = res.data.get("external_appointment_id", "")

                reply_text = (
                    f"Your appointment with {doctor_name} at {hospital_name} is confirmed for {formatted_time}. "
                    f"(Reference ID: {ext_id}). A pre-visit questionnaire has been assigned to help your doctor prepare."
                )
            else:
                reply_text = f"I'm sorry, I was unable to complete your booking: {res.error}. Would you like to check another slot?"

            ContextManager.save_context(db, context_data)

            return AIChatResponse(
                conversation_id=conversation_id,
                message=reply_text,
                intent="BOOK_APPOINTMENT",
                tool_calls=executed_tool_calls,
                context=context_data.model_dump(),
                appointment=confirmed_appointment,
            )

        # 4. LLM / Autonomous Intent Processing
        llm = get_llm_provider()
        llm_out = llm.process_message(
            message=request.message,
            context=context_data.model_dump(),
            conversation_history=[],
        )

        context_data.current_intent = llm_out.intent

        # 5. Execute any tools requested by LLM
        doctors_found = []
        for tc in llm_out.tool_calls:
            cap = CAPABILITY_REGISTRY.get(tc.name)
            if not cap:
                continue

            # Pass arguments
            args = tc.arguments.copy()
            if tc.name == "create_appointment" and "slot_id" not in args and context_data.selected_slot_id:
                args["slot_id"] = context_data.selected_slot_id
            if tc.name == "check_availability" and "doctor_id" not in args and context_data.selected_doctor_id:
                args["doctor_id"] = context_data.selected_doctor_id

            res = cap.run(
                db=db,
                current_user=current_user,
                context=context_data.model_dump(),
                correlation_id=correlation_id,
                arguments=args,
                conversation_id=conversation_id,
            )
            executed_tool_calls.append({"name": tc.name, "result": res.model_dump()})

            if res.success and res.data:
                if tc.name == "search_doctors" and "doctors" in res.data:
                    doctors_found = res.data["doctors"]
                    if doctors_found:
                        context_data.selected_doctor_id = doctors_found[0]["id"]
                        context_data.selected_doctor_name = doctors_found[0]["name"]
                        context_data.selected_specialty = doctors_found[0]["specialty"]
                        context_data.selected_hospital_id = doctors_found[0]["hospital_id"]
                        context_data.selected_hospital_name = doctors_found[0]["hospital_name"]

                elif tc.name == "check_availability" and "slots" in res.data:
                    slots_to_return = res.data["slots"]
                    context_data.presented_slots = slots_to_return

        # 6. Compose Natural Language Response
        if llm_out.intent == "SEARCH_DOCTORS" or llm_out.intent == "CHECK_AVAILABILITY":
            if slots_to_return:
                doc_name = context_data.selected_doctor_name or "our specialist"
                hosp_name = context_data.selected_hospital_name or "CityCare Hospital"
                slots_text = "\n".join([f"{i+1}. {s['formatted_time']}" for i, s in enumerate(slots_to_return[:4])])
                reply_text = (
                    f"{hosp_name} has {doc_name} available this week. Here are the open slots from our scheduling service:\n\n"
                    f"{slots_text}\n\n"
                    f"Which appointment would you prefer? (You can say 'the first one' or specify a time)"
                )
            elif doctors_found:
                doc_name = doctors_found[0]["name"]
                reply_text = (
                    f"I found {doc_name} ({doctors_found[0]['specialty']}) at {doctors_found[0]['hospital_name']}, "
                    f"but there are currently no open slots in this window. Would you like me to check a different date or doctor?"
                )
            else:
                reply_text = "I could not find any active doctors matching your criteria at this time. Could you specify another specialty or city?"
        else:
            reply_text = llm_out.text

        # 7. Persist updated context
        ContextManager.save_context(db, context_data)

        # 8. Record audit log
        db.add(
            AuditEvent(
                correlation_id=correlation_id,
                actor_id=current_user.id,
                actor_role=current_user.role,
                action="AI_CONVERSATION_TURN",
                resource_type="AI_CONVERSATION",
                resource_id=conversation_id,
                status="SUCCESS",
                details_json=json.dumps({"intent": llm_out.intent}),
            )
        )
        db.commit()

        return AIChatResponse(
            conversation_id=conversation_id,
            message=reply_text,
            intent=llm_out.intent,
            tool_calls=executed_tool_calls,
            context=context_data.model_dump(),
            slots=slots_to_return,
            appointment=confirmed_appointment,
        )
