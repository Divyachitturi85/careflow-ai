# End-to-End Booking Sequence — CareFlow AI

This sequence document illustrates the complete patient booking journey through CareFlow AI.

---

## 1. Sequence Diagram

```mermaid
sequenceDiagram
    autonumber
    actor Patient
    participant Browser as Browser (Voice/Text UI)
    participant Agent as AI Agent (AIAgent)
    participant Safety as AISafetyGuard
    participant Context as ContextManager
    participant Cap as Capability Layer
    participant Sched as SchedulingService
    participant Appt as AppointmentService
    participant EHR as MockEHRConnector
    participant DB as PostgreSQL / DB

    Note over Patient,Browser: Phase 1: Doctor Discovery & Availability
    Patient->>Browser: "I need to see an orthopedic doctor this week" (Voice or Text)
    Browser->>Agent: POST /api/ai/chat { message, conversation_id }
    Agent->>Safety: inspect_message(text)
    Safety-->>Agent: is_safe: true
    Agent->>Context: get_or_create_context()
    Agent->>Cap: execute("search_doctors", { specialty: "Orthopedics" })
    Cap->>Sched: get_available_slots(specialty: "Orthopedics")
    Sched->>DB: Query ACTIVE doctors & bookable slots
    DB-->>Sched: Dr. Rao slots [Friday 3 PM, Friday 4 PM, Saturday 11 AM]
    Sched-->>Cap: Return available slots
    Cap-->>Agent: Slots payload
    Agent->>Context: save_context(presented_slots)
    Agent-->>Browser: "CityCare Hospital has Dr. Rao available. Here are the open slots..."
    Browser-->>Patient: Speaks response + Displays interactive slot cards

    Note over Patient,Browser: Phase 2: Anaphoric Slot Selection & Booking
    Patient->>Browser: "Book the first one" (Voice or Click)
    Browser->>Agent: POST /api/ai/chat { message: "Book the first one" }
    Agent->>Context: resolve_slot_reference(text)
    Context-->>Agent: Resolves Friday 3:00 PM slot (slot_id: 9aba...)
    Agent->>Cap: execute("create_appointment", { slot_id })
    Cap->>Appt: create_appointment(request)

    Note over Appt,DB: Phase 3: Atomic Compare-and-Swap Reservation
    Appt->>Sched: revalidate_and_reserve_slot(slot_id)
    Sched->>DB: UPDATE availability_slots SET is_booked=TRUE WHERE id=slot_id AND is_booked=FALSE
    DB-->>Sched: 1 row updated (atomic success)
    Appt->>DB: INSERT INTO appointments (status="PENDING", idempotency_key, correlation_id)

    Note over Appt,EHR: Phase 4: Mock EHR Booking & External Verification
    Appt->>EHR: create_appointment(payload)
    EHR-->>Appt: { external_appointment_id: "EXT-APT-8A91B", status: "CONFIRMED" }
    Appt->>EHR: verify_appointment("EXT-APT-8A91B")
    EHR-->>Appt: verified: true, external_status: "CONFIRMED"

    Note over Appt,DB: Phase 5: Internal Synchronization & Pre-Visit Trigger
    Appt->>DB: UPDATE appointments SET status="CONFIRMED", external_id="EXT-APT-8A91B"
    Appt->>DB: INSERT INTO appointment_events (to_status="CONFIRMED")
    Appt->>DB: INSERT INTO workflow_executions (step="ASSIGN_QUESTIONNAIRE")
    Appt-->>Cap: Appointment confirmation response
    Cap-->>Agent: Confirmed appointment details
    Agent-->>Browser: "Your appointment with Dr. Rao is confirmed for Friday at 3:00 PM. Ref: EXT-APT-8A91B."
    Browser-->>Patient: Displays Confirmation Card + "Complete Intake Questionnaire" Button
```

---

## 2. Key Transactional Invariants

1. **AI Never Emits Fake Slots**: Every slot presented to the patient originated directly from a live `AvailabilitySlot` record in the database.
2. **Double-Booking Impossibility**: Even if two patients select the same slot at the exact same millisecond, the atomic database compare-and-swap guarantees only one update returns `1`. The second receives `409 Conflict` and no duplicate EHR appointment is ever created.
3. **External Verification**: Internal status does not transition to `CONFIRMED` until the external EHR connector has independently confirmed the appointment exists and is valid.
4. **Automated Pre-Visit Trigger**: Upon confirmation, CareFlow AI assigns the specialty-specific intake questionnaire and registers a post-booking workflow.
