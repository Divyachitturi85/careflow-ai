import re
from typing import Tuple, Optional

# Patterns for clinical diagnoses, prescribing, and treatment recommendations
CLINICAL_PATTERNS = [
    r"\b(diagnose|diagnosis|what disease|what condition|what is wrong with me)\b",
    r"\bdo i have\b.*?\b(disease|condition|cancer|heart|stroke|diabetes|flu|covid|infection|depression|asthma|hypertension|pneumonia|strep|arthritis|fracture|sprain|disorder|illness|syndrome|attack)\b",
    r"\b(could i have|am i having|am i suffering from)\b.*?\b(disease|cancer|heart|attack|stroke|infection)\b",
    r"\b(what medicine|what medication|prescribe|prescription|which pill|what drug|dosage)\b",
    r"\b(change my medication|stop taking|increase dose|decrease dose|side effects of)\b",
    r"\b(how to treat|cure for|medical advice|remedy for|treat my)\b",
]

PROMPT_INJECTION_PATTERNS = [
    r"ignore (all )?(previous|prior) instructions",
    r"system prompt",
    r"you are now (a|an)",
    r"disregard safety guidelines",
    r"reveal (your|the) (instructions|prompt|secret)",
]

CLINICAL_REFUSAL_MESSAGE = (
    "I am an administrative healthcare access assistant and cannot provide medical diagnoses, "
    "prescriptions, or treatment recommendations. I can, however, help you find an appropriate "
    "specialist (such as an Orthopedic or Cardiology doctor) and schedule an appointment to discuss "
    "your symptoms with a licensed physician. If you are experiencing a medical emergency, please call "
    "emergency services (such as 911 / 112) immediately."
)

INJECTION_REFUSAL_MESSAGE = (
    "I can only assist with healthcare appointment booking, doctor scheduling, and administrative questions."
)

class AISafetyGuard:
    @staticmethod
    def inspect_message(message: str) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Inspects incoming patient message for safety violations.
        Returns: (is_safe, refusal_message, violation_category)
        """
        text = message.lower().strip()

        # 1. Check prompt injection
        for pattern in PROMPT_INJECTION_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                return False, INJECTION_REFUSAL_MESSAGE, "PROMPT_INJECTION"

        # 2. Check clinical boundary violations (diagnosis, prescribing, treatment)
        for pattern in CLINICAL_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                return False, CLINICAL_REFUSAL_MESSAGE, "CLINICAL_REQUEST"

        return True, None, None
