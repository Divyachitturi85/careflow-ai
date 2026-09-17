# Mock EHR Integration & Connector Abstraction — CareFlow AI

CareFlow AI interfaces with hospital Electronic Health Record (EHR) systems through a clean, vendor-agnostic abstraction layer.

---

## 1. HealthcareSystemConnector Interface

```python
class HealthcareSystemConnector(ABC):
    @abstractmethod
    def create_appointment(self, payload: Dict[str, Any]) -> Dict[str, Any]: ...

    @abstractmethod
    def get_appointment(self, external_id: str) -> Optional[Dict[str, Any]]: ...

    @abstractmethod
    def verify_appointment(self, external_id: str, expected_slot: Dict[str, Any]) -> Dict[str, Any]: ...

    @abstractmethod
    def cancel_appointment(self, external_id: str, reason: Optional[str] = None) -> Dict[str, Any]: ...

    @abstractmethod
    def query_by_idempotency_key(self, idempotency_key: str) -> Optional[Dict[str, Any]]: ...
```

The application domain services never contain vendor-specific EHR SDK code. All integration calls are routed through this contract.

---

## 2. Mock EHR Connector & External Database

The `MockEHRConnector` maintains an independent, isolated in-memory external database (`_external_appointments_db`) that mimics a real external hospital EHR system.

### External Identifier Format
- **Facilities**: `EXT-FAC-CITYCARE`
- **Doctors**: `EXT-DOC-RAO-01`, `EXT-DOC-KUMAR-02`, `EXT-DOC-PRIYA-03`
- **Patients**: `EXT-PAT-KAVITA-01`
- **Appointments**: `EXT-APT-XXXXXX`

The `IdentifierMapper` maintains persistent rows in `external_identifier_mappings` to link internal system UUIDs to their external EHR counterparts with concurrency-safe deduplication.

---

## 3. Simulation Modes for Fault Injection

CareFlow AI includes an administrative simulation switcher for live evaluator testing:

| Mode | Behavior | System Response |
| :--- | :--- | :--- |
| **`NORMAL`** | Normal execution. External appointment created in ~200ms. | Verified immediately and synchronized to `CONFIRMED`. |
| **`TIMEOUT`** | Network call to EHR times out. External appointment NOT created. | System initiates query-before-retry, detects no record, flags `RECONCILIATION_REQUIRED` for safety. |
| **`FAILURE`** | Mock EHR returns HTTP 500 error. | System catches failure, releases internal reserved slot (`is_booked = False`), marks appointment `FAILED`. |
| **`UNKNOWN_OUTCOME`** | **Signature Resilience Scenario**: Mock EHR creates appointment, but network drops response packet. | System catches timeout, triggers **Query-Before-Retry** using `idempotency_key`, discovers external appointment `EXT-APT-xxx`, verifies it, and synchronizes to `CONFIRMED` without duplicate booking! |
