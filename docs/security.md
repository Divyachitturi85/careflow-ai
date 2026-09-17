# Security, RBAC & Tenant Isolation — CareFlow AI

CareFlow AI implements multi-layered security adhering to healthcare data protection principles.

---

## 1. Role-Based Access Control (RBAC) Matrix

| Resource / Action | PLATFORM_ADMIN | HOSPITAL_ADMIN | DOCTOR | PATIENT |
| :--- | :---: | :---: | :---: | :---: |
| **All Hospitals View** | Full | Own Hospital Only | Assigned Only | Public Discovery |
| **Doctor Schedule Management** | Full | Own Hospital Doctors | Own Calendar Only | View Available Slots |
| **Book Appointment** | Full | On Behalf (Own Hospital) | On Behalf | Self Only |
| **Cancel / Reschedule** | Full | Own Hospital Appts | Own Patients | Self Only |
| **Pre-Visit Questionnaires** | Full | Own Hospital Forms | Own Patient Responses | Self Responses Only |
| **EHR Simulation Controls** | Full | Read-Only Status | No Access | No Access |
| **Reconciliation Queue** | Full | Own Hospital Only | No Access | No Access |
| **Audit Event Logs** | Full | Own Hospital Only | Own Actions | No Access |

---

## 2. Multi-Tenant Isolation Verification

- **Hospital-Level Filtering**: When a `HOSPITAL_ADMIN` requests doctors or appointments, `enforce_hospital_tenant` compares the request's hospital parameter against the administrator's assigned `hospital_id`. Attempting to access an unauthorized hospital returns HTTP `403 Forbidden`.
- **Patient Resource Ownership**: A `PATIENT` user can only access appointments where `patient.user_id == current_user.id`. Accessing another patient's appointment returns HTTP `403 Forbidden`.
- **Doctor Resource Ownership**: A `DOCTOR` user can only view their own schedule and authorized clinical intake responses for their patients.

---

## 3. AI Safety & Clinical Boundary Enforcement

The `AISafetyGuard` runs prior to any LLM reasoning or tool invocation:

1. **Clinical Request Refusal**:
   - Matches patterns for medical diagnoses, prescribing, drug dosages, and symptom cures.
   - Refusal message:
     > *"I am an administrative healthcare access assistant and cannot provide medical diagnoses, prescriptions, or treatment recommendations. I can, however, help you find an appropriate specialist (such as an Orthopedic or Cardiology doctor) and schedule an appointment to discuss your symptoms with a licensed physician. If you are experiencing a medical emergency, please call emergency services (such as 911 / 112) immediately."*
   - Logs `AI_SAFETY_VIOLATION_BLOCKED` to the immutable audit events table.

2. **Prompt Injection Resistance**:
   - Rejects attempts to override instructions, leak system prompts, or bypass safety rules.
   - Returns a structured administrative boundary message without exposing internal architecture.
