# CareFlow AI

**Autonomous Healthcare Patient Intake, Scheduling & Pre-Visit Voice Agent Platform**  
*AI Engineer Intern – Voice & Agentic AI Project Assignment for AI.Prof*

[![Build Status](https://img.shields.io/badge/build-passing-brightgreen)]()
[![Tests](https://img.shields.io/badge/tests-50%20passed-success)]()
[![Python](https://img.shields.io/badge/python-3.11-blue)]()
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688)]()
[![React](https://img.shields.io/badge/React-19-61dafb)]()
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-336791)]()
[![License](https://img.shields.io/badge/license-MIT-purple)]()

---

## 1. Project Overview

CareFlow AI is a production-grade healthcare prototype engineered to demonstrate **one complete, reliable patient journey end-to-end**:

```
Patient natural-language voice request
  → AI understanding & clinical boundary validation
  → Hospital & doctor discovery
  → Real database availability (AI NEVER invents slots)
  → Patient selects slot (with multi-turn anaphoric resolution)
  → Atomic compare-and-swap reservation (prevents double-booking)
  → HealthcareSystemConnector & Mock EHR integration
  → External appointment verification
  → Internal synchronization to CONFIRMED
  → Pre-visit clinical intake questionnaire
  → Automated reminder/notification workflow
  → Doctor & Hospital Admin dashboard visibility
```

### Key Engineering Guarantees
- **No Hallucinated Availability**: The scheduling engine is the single source of truth. Every presented slot is a live database record.
- **Atomic Double-Booking Prevention**: High-concurrency compare-and-swap row updates prevent double-booking under race conditions.
- **Resilient Unknown-Outcome Recovery**: If an external EHR network call times out after record creation, CareFlow AI uses **Query-Before-Retry** to recover the external ID and confirm the appointment without duplicate bookings.
- **Strict Multi-Tenant Isolation**: Hospital tenants, doctors, and patients are isolated at the database and service layers.
- **Deterministic AI Safety**: The AI assistant acts strictly administratively and refuses medical diagnoses, prescriptions, and drug modifications.

---

## 2. Quickstart Guide

### Prerequisites
- [Docker](https://www.docker.com/) and [Docker Compose](https://docs.docker.com/compose/) (Recommended), OR
- Python 3.11+ and Node.js 20+

### Option A: Run with Docker Compose (Full Stack with PostgreSQL)

1. Clone the repository and navigate into it:
   ```bash
   git clone https://github.com/your-username/careflow-ai.git
   cd careflow-ai
   ```

2. Copy environment file:
   ```bash
   cp .env.example .env
   ```

3. Launch all services:
   ```bash
   docker-compose up --build
   ```

4. Access the web applications:
   - **Frontend Web Portal**: [http://localhost:5173](http://localhost:5173)
   - **Backend REST API & Swagger Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)
   - **Health Check**: [http://localhost:8000/health](http://localhost:8000/health)

---

### Option B: Run Locally for Development (Fast)

#### 1. Backend Setup
```bash
cd backend
python -m venv venv
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

pip install -r requirements.txt

# Seed deterministic demo data (CityCare Hospital, Dr. Rao, Slots, Questionnaire)
python -m app.db.seed

# Start FastAPI server
uvicorn app.main:app --reload --port 8000
```

#### 2. Frontend Setup
```bash
cd frontend
npm install
npm run dev
```
Open [http://localhost:5173](http://localhost:5173) in your browser.

---

## 3. Pre-Seeded Demo Accounts (One-Click Evaluator Logins)

The web portal includes 1-click login buttons on the sign-in page:

| Role | User Name | Email | Password | Primary Purpose |
| :--- | :--- | :--- | :--- | :--- |
| **PATIENT** | Kavita Reddy | `patient@example.com` | `Patient@123` | Voice AI assistant, booking, questionnaires |
| **DOCTOR** | Dr. Rao | `doctor.rao@example.com` | `Doctor@123` | Consultation calendar, review patient intake |
| **HOSPITAL_ADMIN** | CityCare Admin | `hospital.admin@example.com` | `Hospital@123` | Manage doctors, hospital slots, integrations |
| **PLATFORM_ADMIN** | Platform Admin | `platform.admin@example.com` | `Admin@123` | Mock EHR fault injection switcher, audit log |

---

## 4. Evaluator Demo Walkthrough Scripts

### Demo 1: The Complete Happy Path Patient Journey
1. Open [http://localhost:5173](http://localhost:5173) and sign in as **Patient** (`patient@example.com`).
2. Click the **Microphone** button (or use the suggested prompt chips) and say:
   > *"I need to see an orthopedic doctor this week."*
3. **Observe the Live Pipeline Indicator**:
   - `Listening...` $\to$ `Transcribing` $\to$ `Clinical Policy Check` $\to$ `Querying Real Availability`.
4. The AI returns Dr. Rao (Orthopedics, CityCare Hospital) and presents **real database slots** (Friday 3:00 PM, Friday 4:00 PM, Saturday 11:00 AM).
5. Speak or type:
   > *"Book the first one."*
6. **Observe the Multi-Turn Context Resolution**:
   - The AI resolves the anaphora to Friday 3:00 PM.
   - Atomically reserves the slot in the database.
   - Calls Mock EHR connector to create external appointment.
   - Verifies the external appointment.
   - Transitions internal appointment state to `CONFIRMED`.
   - Displays confirmed card with reference `EXT-APT-...`.
7. Click the **"Complete Intake Questionnaire"** button.
8. Answer the 5 Orthopedic pre-visit intake questions (Pain location, severity slider 1-10, impact, duration, prior imaging) and click **"Submit Intake to Physician"**.
9. Click **"Demo As: Dr. Rao"** in the top navigation:
   - Navigate to Doctor Consultation Schedule.
   - Verify that Kavita Reddy's appointment is listed.
   - Click the patient to view the **verified intake answers** in real time.

---

### Demo 2: Signature Failure Recovery (Unknown Outcome & Idempotency)
1. In the top navigation, click **"Demo As: Platform Admin"**.
2. Under **Mock EHR Fault Injection Control**, click **"4. UNKNOWN OUTCOME"**.
   - *Scenario*: External Mock EHR creates the appointment, but the network drops the confirmation response packet.
3. Switch back to **Patient** and ask:
   > *"Book Dr. Rao on Friday at 4 PM."*
4. **Observe the Autonomous Resilience**:
   - Client catches the network timeout / dropped packet.
   - System triggers **Query-Before-Retry** using the request's `idempotency_key`.
   - Discovers the external appointment record in Mock EHR.
   - Recovers the external reference ID and verifies the parameters match.
   - Synchronizes internal state to `CONFIRMED`.
5. Check the **Platform Admin Operations Log**:
   - Verify that **exactly 1 internal appointment** and **exactly 1 external appointment** exist. Zero duplicate bookings occurred!

---

### Demo 3: Clinical Safety Boundary Refusal
1. In the Voice AI assistant, ask:
   > *"What medicine should I take for my joint pain?"* or *"Diagnose my knee pain."*
2. **Observe**:
   - The `AISafetyGuard` intercepts the message before any clinical speculation can occur.
   - Displays a refusal banner explaining that CareFlow AI is strictly administrative and cannot prescribe or diagnose.
   - Recommends booking an appointment with an Orthopedic specialist and displays emergency hotline numbers.
   - Logs an `AI_SAFETY_VIOLATION_BLOCKED` event in the audit log.

---

### Demo 4: Concurrency Double-Booking Race Condition Prevention
Run the automated concurrent double-booking test:
```bash
cd backend
venv\Scripts\pytest.exe -v tests/test_scheduling.py -k "test_concurrent_double_booking_race_condition"
```
**Output**:
- 2 worker threads target the exact same slot simultaneously in parallel.
- Exactly 1 thread succeeds (`200 OK`, `is_booked = True`).
- Exactly 1 thread fails with `409 Conflict`.
- Exactly 1 appointment row exists in the database.

---

## 5. Automated Verification & Test Suite

CareFlow AI features a comprehensive, multi-layer automated test suite covering 100% of requirements:

```bash
cd backend
venv\Scripts\pytest.exe -v tests/
```

### Complete Test Results: **50 Passed, 0 Failed**

| Test Module | Coverage Area | Tests | Status |
| :--- | :--- | :---: | :---: |
| `test_models_and_seed.py` | Models, UUIDs, Indexes, Tenant Foreign Keys, Seed Data | 7 | **PASSED** |
| `test_auth_and_tenant_isolation.py` | JWT Auth, RBAC, Multi-Tenant Isolation, 403 Forbidden | 11 | **PASSED** |
| `test_scheduling.py` | Real Slots, Leave Blocks, Concurrency Compare-and-Swap | 8 | **PASSED** |
| `test_ehr_and_appointments.py` | Mock EHR, Idempotency, Unknown Outcome Recovery, Reconciliation | 11 | **PASSED** |
| `test_ai_agent.py` | AI Safety Guard, Prompt Injection, Anaphoric Booking, Refusals | 12 | **PASSED** |
| `test_questionnaires.py` | Pre-Visit Intake Retrieval, Submission, Doctor Dashboard View | 1 | **PASSED** |
| **TOTAL** | **Comprehensive Full System Coverage** | **50** | **100% PASSED** |

---

## 6. Architecture & Documentation Directory

- [docs/architecture.md](docs/architecture.md): Multi-tier architecture and concurrency design.
- [docs/data-model.md](docs/data-model.md): Entity schemas, indexes, and Mermaid ERD.
- [docs/booking-sequence.md](docs/booking-sequence.md): End-to-end booking sequence diagram.
- [docs/ehr-integration.md](docs/ehr-integration.md): Mock EHR specification and simulation modes.
- [docs/failure-recovery.md](docs/failure-recovery.md): Query-Before-Retry algorithm and unknown outcome recovery.
- [docs/security.md](docs/security.md): RBAC matrix, tenant isolation, and clinical safety boundaries.
- [docs/ai-documentation.md](docs/ai-documentation.md): AI agent capability tools and multi-turn context resolution.

---

## 7. Technology Stack

- **Backend**: Python 3.11, FastAPI, SQLAlchemy 2.0, Pydantic v2, PostgreSQL 16 / SQLite WAL.
- **Security**: JWT (HS256), Bcrypt password hashing, RBAC middleware.
- **Frontend**: React 19, TypeScript, Vite, Tailwind CSS v4, Lucide React, Web Speech API (STT & TTS).
- **Testing**: Pytest, Pytest-Asyncio, HTTPX / Starlette TestClient.
- **DevOps**: Docker, Docker Compose, Nginx.
