# AI Agent & Capabilities Specification — CareFlow AI

CareFlow AI employs an autonomous agent architecture with strict sandboxing and tool-calling boundaries.

---

## 1. Agent Design Principles

1. **No Direct DB Access**: The LLM never writes raw SQL, executes SQLAlchemy queries, or modifies database rows directly.
2. **No Direct Mock EHR Calls**: The LLM cannot call external EHR APIs directly; it must delegate to domain services (`SchedulingService`, `AppointmentService`).
3. **Controlled Capability Tools**: All actions are executed via strictly validated Pydantic parameter schemas.
4. **Deterministic Anaphoric Context**: The agent resolves ambiguous phrases ("first one", "Friday at 3", "actually make that 4 PM") using explicit structured conversation context (`AIContext`).

---

## 2. Controlled Capabilities Registry

| Capability Name | Input Schema | Description |
| :--- | :--- | :--- |
| **`search_doctors`** | `{ specialty?, city?, name? }` | Queries active physicians across approved hospitals. |
| **`check_availability`** | `{ doctor_id?, specialty?, name? }` | Retrieves real database-backed availability slots for active physicians. |
| **`create_appointment`** | `{ slot_id, reason_for_visit? }` | Validates slot, atomically reserves it, creates appointment, verifies with Mock EHR, and synchronizes to `CONFIRMED`. |
| **`get_appointment`** | `{ appointment_id }` | Retrieves status and details of a specific appointment. |
| **`list_appointments`** | `{}` | Lists all active appointments for the current authenticated patient. |
| **`reschedule_appointment`**| `{ appointment_id, new_slot_id }` | Reallocates an appointment to a new open slot. |
| **`cancel_appointment`** | `{ appointment_id, reason? }` | Cancels appointment and releases the slot. |
| **`transfer_to_human`** | `{ reason? }` | Escalates conversation to a human healthcare coordinator. |

---

## 3. Multi-Turn Anaphoric Resolution

The `ContextManager` tracks:
- `presented_slots`: The ordered list of slots recently returned from the scheduling engine.
- `selected_doctor_id`: The physician discovered in earlier turns.
- `conversation_id`: The thread session identifier.

When a user says:
- *"Book the first one"* $\to$ Resolves `slots[0]`
- *"Make that 4 PM"* $\to$ Resolves slot matching hour 16:00
- *"Book Dr. Rao"* $\to$ Passes `doctor_id` from context to booking capability.
