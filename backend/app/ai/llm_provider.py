import re
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from pydantic import BaseModel

class ToolCall(BaseModel):
    name: str
    arguments: Dict[str, Any]

class LLMOutput(BaseModel):
    text: str
    intent: str
    tool_calls: List[ToolCall] = []
    requires_clarification: bool = False
    clarification_prompt: Optional[str] = None

class BaseLLMProvider(ABC):
    @abstractmethod
    def process_message(
        self,
        message: str,
        context: Dict[str, Any],
        conversation_history: List[Dict[str, str]],
    ) -> LLMOutput:
        pass

class SmartAgentProvider(BaseLLMProvider):
    """
    Built-in autonomous agent engine for healthcare administrative access.
    Performs deterministic intent parsing, entity extraction, slot resolution,
    and capability tool dispatch with zero external API dependencies.
    """

    def process_message(
        self,
        message: str,
        context: Dict[str, Any],
        conversation_history: List[Dict[str, str]],
    ) -> LLMOutput:
        text = message.strip()
        lower = text.lower()

        # 1. Greetings
        if re.search(r"^(hi|hello|hey|good morning|good afternoon|good evening)\b", lower):
            return LLMOutput(
                text="Hello! I am your CareFlow AI healthcare access assistant. How can I help you today? I can help you find specialists, check real appointment availability, or manage your bookings.",
                intent="GREETING",
            )

        # 2. Rescheduling: "move my appointment", "reschedule"
        if re.search(r"\b(reschedule|move my appointment|change my appointment|change time)\b", lower):
            return LLMOutput(
                text="I can assist you with rescheduling. Let me look up your current appointments and available alternative slots.",
                intent="RESCHEDULE_APPOINTMENT",
                tool_calls=[ToolCall(name="list_appointments", arguments={})],
            )

        # 3. Cancellation: "cancel my appointment", "cancel booking"
        if re.search(r"\b(cancel my appointment|cancel appointment|cancel visit)\b", lower):
            return LLMOutput(
                text="I can help you cancel your appointment. Let me retrieve your active appointments.",
                intent="CANCEL_APPOINTMENT",
                tool_calls=[ToolCall(name="list_appointments", arguments={})],
            )

        # 4. View Appointments: "my appointments", "what appointments do i have", "show appointments"
        if re.search(r"\b(my appointments|view appointments|show appointments|what appointments|my bookings)\b", lower):
            return LLMOutput(
                text="Let me look up your scheduled appointments.",
                intent="GET_APPOINTMENT",
                tool_calls=[ToolCall(name="list_appointments", arguments={})],
            )

        # 5. Hospital Search / Location
        if re.search(r"\b(which hospitals|search hospitals|find hospital|where is citycare|hospital location)\b", lower):
            city_match = re.search(r"\b(vijayawada|hyderabad|guntur)\b", lower)
            city = city_match.group(1).title() if city_match else None
            return LLMOutput(
                text="Searching our approved hospitals for you...",
                intent="SEARCH_HOSPITALS",
                tool_calls=[ToolCall(name="search_hospitals", arguments={"city": city})],
            )

        # 6. Specific Doctor or Specialty Search
        # Examples: "I need an orthopedic doctor", "find cardiologists", "search dr rao"
        specialty = None
        if "ortho" in lower or "bone" in lower or "joint" in lower or "shoulder" in lower or "knee" in lower:
            specialty = "Orthopedics"
        elif "cardio" in lower or "heart" in lower:
            specialty = "Cardiology"
        elif "general" in lower or "primary care" in lower or "physician" in lower:
            specialty = "General Medicine"

        doctor_name = None
        if "rao" in lower:
            doctor_name = "Dr. Rao"
        elif "kumar" in lower:
            doctor_name = "Dr. Kumar"
        elif "priya" in lower:
            doctor_name = "Dr. Priya"

        # Check for slot booking intent: "book the first one", "book friday 3 pm", "actually make that 4 pm", "book dr rao"
        is_booking_intent = bool(re.search(r"\b(book|reserve|schedule|take|select|make it|make that)\b", lower))

        if is_booking_intent:
            # If user refers to a slot (e.g. "first one", "friday 3 pm", "make it 4 pm")
            # and context already has presented_slots:
            if context.get("presented_slots") or context.get("selected_doctor_id"):
                return LLMOutput(
                    text="Processing your slot selection and initiating booking...",
                    intent="BOOK_APPOINTMENT",
                )
            elif specialty or doctor_name:
                # Direct booking request: "Book Dr. Rao this Friday at 3 PM"
                return LLMOutput(
                    text="Let me verify Dr. Rao's actual availability with the scheduling service.",
                    intent="CHECK_AVAILABILITY",
                    tool_calls=[
                        ToolCall(
                            name="check_availability",
                            arguments={"specialty": specialty, "name": doctor_name},
                        )
                    ],
                )
            else:
                # CLARIFICATION REQUIREMENT: User said "book a doctor" without specialty/doctor
                return LLMOutput(
                    text="I would be happy to help you schedule an appointment. What medical specialty or type of doctor would you like to see? (For example: Orthopedics, Cardiology, or General Medicine)",
                    intent="CLARIFICATION",
                    requires_clarification=True,
                    clarification_prompt="SPECIALTY_NEEDED",
                )

        # 7. Doctor Discovery / Availability Search
        if specialty or doctor_name:
            return LLMOutput(
                text=f"Searching for {specialty or doctor_name} specialists and retrieving real availability slots from the scheduling service...",
                intent="SEARCH_DOCTORS",
                tool_calls=[
                    ToolCall(
                        name="search_doctors",
                        arguments={"specialty": specialty, "name": doctor_name},
                    ),
                    ToolCall(
                        name="check_availability",
                        arguments={"specialty": specialty},
                    ),
                ],
            )

        # 8. Human Escalation: "talk to human", "speak to representative", "agent"
        if re.search(r"\b(human|representative|agent|coordinator|operator|talk to someone)\b", lower):
            return LLMOutput(
                text="Transferring your request to a patient care coordinator.",
                intent="HUMAN_ESCALATION",
                tool_calls=[ToolCall(name="transfer_to_human", arguments={"reason": "Patient requested human coordinator"})],
            )

        # 9. General fallback
        return LLMOutput(
            text="I can assist you with discovering specialists, checking real doctor availability, or booking and managing your healthcare appointments at CityCare Hospital. Could you describe what care you are looking for?",
            intent="CLARIFICATION",
            requires_clarification=True,
        )

def get_llm_provider() -> BaseLLMProvider:
    return SmartAgentProvider()
