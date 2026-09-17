import uuid
import json
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import HTTPException, status
from sqlalchemy.orm import Session, joinedload
from app.models.appointment import Appointment, AppointmentEvent
from app.models.doctor import AvailabilitySlot, Doctor
from app.models.hospital import Hospital, Specialty
from app.models.user import Patient, User
from app.models.integration import (
    IntegrationOperation,
    IntegrationVerification,
    ReconciliationRecord,
)
from app.schemas.appointment import (
    AppointmentResponse,
    AppointmentEventResponse,
    CreateAppointmentRequest,
    RescheduleAppointmentRequest,
    CancelAppointmentRequest,
    VerifyAppointmentResponse,
)
from app.services.scheduling_service import SchedulingService
from app.integrations.base import (
    ExternalAppointmentRequest,
    EHRIntegrationError,
    EHRTimeoutError,
)
from app.integrations.mock_ehr import mock_ehr_connector
from app.integrations.mapper import IdentifierMapper
from app.security.tenant import get_user_hospital_id

class AppointmentService:
    @staticmethod
    def create_appointment(
        db: Session,
        request: CreateAppointmentRequest,
        current_user: User,
    ) -> AppointmentResponse:
        """
        Executes the end-to-end booking flow:
        1. Resolve & authorize patient
        2. Idempotency validation
        3. Immediate slot revalidation & atomic reservation
        4. Internal PENDING appointment creation
        5. Mock EHR create request
        6. Unknown-outcome failure recovery / Query-before-retry
        7. External verification
        8. Internal state synchronization -> CONFIRMED
        9. Audit & event recording
        """
        # 1. Resolve Patient ID
        target_patient_id = request.patient_id
        if not target_patient_id:
            if current_user.role == "PATIENT" and current_user.patient_profile:
                target_patient_id = current_user.patient_profile.id
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="patient_id is required when booking on behalf of a patient.",
                )

        patient = db.query(Patient).filter(Patient.id == target_patient_id).first()
        if not patient:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Patient with ID '{target_patient_id}' not found.",
            )

        # RBAC Check: Patient can only book for self
        if current_user.role == "PATIENT" and patient.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You cannot book appointments on behalf of other patients.",
            )

        # 2. Idempotency Check
        correlation_id = request.correlation_id or f"CORR-{uuid.uuid4().hex[:12].upper()}"
        idempotency_key = request.idempotency_key or f"IDEMP-{patient.id[:8]}-{request.slot_id[:8]}-{uuid.uuid4().hex[:6]}"

        existing_appt = (
            db.query(Appointment)
            .filter(Appointment.idempotency_key == idempotency_key)
            .first()
        )
        if existing_appt:
            if existing_appt.status == "CONFIRMED":
                return AppointmentService._build_response(existing_appt)
            elif existing_appt.status in ("PENDING", "SYNCHRONIZATION_PENDING"):
                # Handle concurrent or pending retry by attempting recovery
                return AppointmentService._recover_and_verify(
                    db, existing_appt, correlation_id
                )
            else:
                # If existing appointment failed or was cancelled, allow fresh attempt with new key
                idempotency_key = f"{idempotency_key}-RETRY-{uuid.uuid4().hex[:6]}"

        # 3. Atomic Slot Revalidation & Reservation
        slot = SchedulingService.revalidate_and_reserve_slot(db, request.slot_id)

        # 4. Create internal Appointment in PENDING state
        appointment = Appointment(
            hospital_id=slot.hospital_id,
            patient_id=patient.id,
            doctor_id=slot.doctor_id,
            slot_id=slot.id,
            status="PENDING",
            appointment_type=request.appointment_type,
            reason_for_visit=request.reason_for_visit,
            idempotency_key=idempotency_key,
            correlation_id=correlation_id,
        )
        db.add(appointment)
        db.flush()

        # Record Initial Event
        db.add(
            AppointmentEvent(
                appointment_id=appointment.id,
                event_type="STATUS_CHANGE",
                from_status=None,
                to_status="PENDING",
                metadata_json=json.dumps({"reason": "Slot reserved; awaiting external EHR verification"}),
            )
        )
        db.commit()

        # 5. Resolve External Identifiers
        ext_patient_id = IdentifierMapper.resolve_external_id(
            db, slot.hospital_id, "PATIENT", patient.id, "EXT-PAT"
        )
        ext_doctor_id = IdentifierMapper.resolve_external_id(
            db, slot.hospital_id, "DOCTOR", slot.doctor_id, "EXT-DOC"
        )
        ext_facility_id = IdentifierMapper.resolve_external_id(
            db, slot.hospital_id, "FACILITY", slot.hospital_id, "EXT-FAC"
        )

        ehr_request = ExternalAppointmentRequest(
            patient_external_id=ext_patient_id,
            provider_external_id=ext_doctor_id,
            facility_external_id=ext_facility_id,
            start_time=slot.start_time,
            end_time=slot.end_time,
            appointment_type=request.appointment_type,
            reason=request.reason_for_visit,
            correlation_id=correlation_id,
            idempotency_key=idempotency_key,
        )

        operation_id = f"OP-{uuid.uuid4().hex[:10].upper()}"
        op = IntegrationOperation(
            operation_id=operation_id,
            correlation_id=correlation_id,
            hospital_id=slot.hospital_id,
            operation_type="APPOINTMENT_CREATE",
            payload_json=ehr_request.model_dump_json(),
            status="IN_PROGRESS",
        )
        db.add(op)
        db.commit()

        # 6. Call Mock EHR Integration Layer
        try:
            ext_record = mock_ehr_connector.create_appointment(ehr_request)

            op.status = "SUCCESS"
            op.response_code = 201
            op.response_payload_json = ext_record.model_dump_json()

            # 7. Verify External Appointment
            verified = mock_ehr_connector.verify_appointment(
                external_id=ext_record.external_id,
                expected_patient_id=ext_patient_id,
                expected_provider_id=ext_doctor_id,
                expected_start_time=slot.start_time,
            )

            db.add(
                IntegrationVerification(
                    operation_id=operation_id,
                    internal_appointment_id=appointment.id,
                    external_appointment_id=ext_record.external_id,
                    verified=verified,
                    verified_at=datetime.now(timezone.utc),
                )
            )

            if not verified:
                appointment.status = "RECONCILIATION_REQUIRED"
                db.add(
                    ReconciliationRecord(
                        operation_id=operation_id,
                        appointment_id=appointment.id,
                        hospital_id=slot.hospital_id,
                        reason="External EHR appointment verification check failed",
                    )
                )
                db.commit()
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail="External appointment was created but failed parameter verification.",
                )

            # 8. Synchronize State to CONFIRMED
            appointment.external_appointment_id = ext_record.external_id
            appointment.status = "CONFIRMED"
            IdentifierMapper.get_or_create_mapping(
                db, slot.hospital_id, "APPOINTMENT", appointment.id, ext_record.external_id
            )

            db.add(
                AppointmentEvent(
                    appointment_id=appointment.id,
                    event_type="STATUS_CHANGE",
                    from_status="PENDING",
                    to_status="CONFIRMED",
                    metadata_json=json.dumps({"external_id": ext_record.external_id, "verified": True}),
                )
            )
            db.commit()
            return AppointmentService._build_response(appointment)

        except EHRTimeoutError:
            # PHASE 9 MANDATORY DEMO: Timeout / Unknown Outcome Recovery
            op.status = "UNKNOWN"
            appointment.status = "SYNCHRONIZATION_PENDING"
            db.add(
                AppointmentEvent(
                    appointment_id=appointment.id,
                    event_type="EHR_TIMEOUT_RECEIVED",
                    from_status="PENDING",
                    to_status="SYNCHRONIZATION_PENDING",
                    metadata_json=json.dumps({"operation_id": operation_id, "action": "Querying Mock EHR before retry"}),
                )
            )
            db.commit()

            # Execute Query-Before-Retry recovery engine
            return AppointmentService._recover_and_verify(
                db, appointment, correlation_id, operation_id
            )

        except EHRIntegrationError as e:
            # Hard Upstream EHR Failure
            op.status = "FAILED"
            op.response_code = 503
            SchedulingService.release_slot(db, slot.id)
            appointment.status = "FAILED"
            db.add(
                AppointmentEvent(
                    appointment_id=appointment.id,
                    event_type="STATUS_CHANGE",
                    from_status="PENDING",
                    to_status="FAILED",
                    metadata_json=json.dumps({"error": str(e)}),
                )
            )
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"External healthcare system error: {str(e)}",
            )

    @staticmethod
    def _recover_and_verify(
        db: Session,
        appointment: Appointment,
        correlation_id: str,
        operation_id: Optional[str] = None,
    ) -> AppointmentResponse:
        """
        Mandatory Failure Recovery Engine (Query-Before-Retry):
        Queries Mock EHR to detect if the external record was created during timeout.
        If found, verifies and synchronizes without creating duplicate appointments.
        If not found and unresolvable, creates a ReconciliationRecord for operator oversight.
        """
        slot = appointment.slot
        ext_doctor_id = IdentifierMapper.resolve_external_id(
            db, appointment.hospital_id, "DOCTOR", appointment.doctor_id, "EXT-DOC"
        )
        ext_patient_id = IdentifierMapper.resolve_external_id(
            db, appointment.hospital_id, "PATIENT", appointment.patient_id, "EXT-PAT"
        )

        # 1. Query Mock EHR for existing appointment by correlation/idempotency
        existing_ext_record = mock_ehr_connector.find_by_correlation(
            correlation_id=correlation_id,
            idempotency_key=appointment.idempotency_key,
            provider_id=ext_doctor_id,
            start_time=slot.start_time,
        )

        if existing_ext_record:
            # External appointment was indeed created by EHR!
            verified = mock_ehr_connector.verify_appointment(
                external_id=existing_ext_record.external_id,
                expected_patient_id=ext_patient_id,
                expected_provider_id=ext_doctor_id,
                expected_start_time=slot.start_time,
            )

            if verified:
                appointment.external_appointment_id = existing_ext_record.external_id
                appointment.status = "CONFIRMED"
                IdentifierMapper.get_or_create_mapping(
                    db,
                    appointment.hospital_id,
                    "APPOINTMENT",
                    appointment.id,
                    existing_ext_record.external_id,
                )

                db.add(
                    AppointmentEvent(
                        appointment_id=appointment.id,
                        event_type="EHR_TIMEOUT_RECOVERED_WITHOUT_DUPLICATE",
                        from_status="SYNCHRONIZATION_PENDING",
                        to_status="CONFIRMED",
                        metadata_json=json.dumps({
                            "external_id": existing_ext_record.external_id,
                            "recovery": "Query-before-retry discovered external record; zero duplicates created",
                        }),
                    )
                )
                db.commit()
                return AppointmentService._build_response(appointment)

        # 2. If not found and cannot be recovered automatically:
        appointment.status = "RECONCILIATION_REQUIRED"
        recon_record = ReconciliationRecord(
            operation_id=operation_id or f"OP-RECON-{uuid.uuid4().hex[:8].upper()}",
            appointment_id=appointment.id,
            hospital_id=appointment.hospital_id,
            reason="Mock EHR timeout occurred and record could not be confirmed via query.",
            status="OPEN",
        )
        db.add(recon_record)
        db.add(
            AppointmentEvent(
                appointment_id=appointment.id,
                event_type="STATUS_CHANGE",
                from_status="SYNCHRONIZATION_PENDING",
                to_status="RECONCILIATION_REQUIRED",
                metadata_json=json.dumps({"reason": "Unresolved external outcome; flagged for admin review"}),
            )
        )
        db.commit()
        return AppointmentService._build_response(appointment)

    @staticmethod
    def get_appointment(
        db: Session, appointment_id: str, current_user: User
    ) -> AppointmentResponse:
        appointment = (
            db.query(Appointment)
            .options(
                joinedload(Appointment.doctor).joinedload(Doctor.specialty),
                joinedload(Appointment.patient).joinedload(Patient.user),
                joinedload(Appointment.hospital),
                joinedload(Appointment.slot),
                joinedload(Appointment.events),
            )
            .filter(Appointment.id == appointment_id)
            .first()
        )
        if not appointment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Appointment '{appointment_id}' not found.",
            )

        # RBAC & Tenant Ownership Checks
        if current_user.role == "PATIENT":
            if appointment.patient.user_id != current_user.id:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")
        elif current_user.role == "DOCTOR":
            if appointment.doctor.user_id != current_user.id:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")
        elif current_user.role == "HOSPITAL_ADMIN":
            admin_hospital_id = get_user_hospital_id(current_user, db)
            if appointment.hospital_id != admin_hospital_id:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant access denied.")

        return AppointmentService._build_response(appointment)

    @staticmethod
    def list_appointments(
        db: Session, current_user: User
    ) -> List[AppointmentResponse]:
        query = db.query(Appointment).options(
            joinedload(Appointment.doctor).joinedload(Doctor.specialty),
            joinedload(Appointment.patient).joinedload(Patient.user),
            joinedload(Appointment.hospital),
            joinedload(Appointment.slot),
            joinedload(Appointment.events),
        )

        if current_user.role == "PATIENT":
            if current_user.patient_profile:
                query = query.filter(Appointment.patient_id == current_user.patient_profile.id)
            else:
                return []
        elif current_user.role == "DOCTOR":
            if current_user.doctor_profile:
                query = query.filter(Appointment.doctor_id == current_user.doctor_profile.id)
            else:
                return []
        elif current_user.role == "HOSPITAL_ADMIN":
            hospital_id = get_user_hospital_id(current_user, db)
            if hospital_id:
                query = query.filter(Appointment.hospital_id == hospital_id)
            else:
                return []

        appts = query.order_by(Appointment.created_at.desc()).all()
        return [AppointmentService._build_response(a) for a in appts]

    @staticmethod
    def reschedule_appointment(
        db: Session,
        appointment_id: str,
        request: RescheduleAppointmentRequest,
        current_user: User,
    ) -> AppointmentResponse:
        appointment = db.query(Appointment).filter(Appointment.id == appointment_id).first()
        if not appointment:
            raise HTTPException(status_code=404, detail="Appointment not found.")

        # Revalidate & reserve new slot
        new_slot = SchedulingService.revalidate_and_reserve_slot(db, request.new_slot_id)
        old_slot_id = appointment.slot_id

        # Update Mock EHR
        if appointment.external_appointment_id:
            mock_ehr_connector.reschedule_appointment(
                appointment.external_appointment_id, new_slot.start_time, new_slot.end_time
            )

        # Release old slot
        SchedulingService.release_slot(db, old_slot_id)

        appointment.slot_id = new_slot.id
        appointment.status = "RESCHEDULED"
        db.add(
            AppointmentEvent(
                appointment_id=appointment.id,
                event_type="STATUS_CHANGE",
                from_status="CONFIRMED",
                to_status="RESCHEDULED",
                metadata_json=json.dumps({"reason": request.reason, "new_slot_id": new_slot.id}),
            )
        )
        db.commit()
        return AppointmentService._build_response(appointment)

    @staticmethod
    def cancel_appointment(
        db: Session,
        appointment_id: str,
        request: CancelAppointmentRequest,
        current_user: User,
    ) -> AppointmentResponse:
        appointment = db.query(Appointment).filter(Appointment.id == appointment_id).first()
        if not appointment:
            raise HTTPException(status_code=404, detail="Appointment not found.")

        # Cancel on Mock EHR
        if appointment.external_appointment_id:
            mock_ehr_connector.cancel_appointment(
                appointment.external_appointment_id, request.reason or "Patient cancellation"
            )

        # Release reserved slot
        SchedulingService.release_slot(db, appointment.slot_id)

        old_status = appointment.status
        appointment.status = "CANCELLED"
        db.add(
            AppointmentEvent(
                appointment_id=appointment.id,
                event_type="STATUS_CHANGE",
                from_status=old_status,
                to_status="CANCELLED",
                metadata_json=json.dumps({"reason": request.reason}),
            )
        )
        db.commit()
        return AppointmentService._build_response(appointment)

    @staticmethod
    def _build_response(appointment: Appointment) -> AppointmentResponse:
        patient_name = (
            f"{appointment.patient.user.first_name} {appointment.patient.user.last_name}"
            if appointment.patient and appointment.patient.user
            else "Patient"
        )
        doctor_name = appointment.doctor.name if appointment.doctor else "Doctor"
        specialty = (
            appointment.doctor.specialty.name
            if appointment.doctor and appointment.doctor.specialty
            else "General"
        )
        hospital_name = appointment.hospital.name if appointment.hospital else "Hospital"

        events = [
            AppointmentEventResponse(
                id=e.id,
                event_type=e.event_type,
                from_status=e.from_status,
                to_status=e.to_status,
                metadata_json=e.metadata_json,
                created_at=e.created_at,
            )
            for e in appointment.events
        ]

        return AppointmentResponse(
            id=appointment.id,
            hospital_id=appointment.hospital_id,
            hospital_name=hospital_name,
            patient_id=appointment.patient_id,
            patient_name=patient_name,
            doctor_id=appointment.doctor_id,
            doctor_name=doctor_name,
            specialty=specialty,
            slot_id=appointment.slot_id,
            start_time=appointment.slot.start_time,
            end_time=appointment.slot.end_time,
            status=appointment.status,
            appointment_type=appointment.appointment_type,
            reason_for_visit=appointment.reason_for_visit,
            external_appointment_id=appointment.external_appointment_id,
            idempotency_key=appointment.idempotency_key,
            correlation_id=appointment.correlation_id,
            created_at=appointment.created_at,
            events=events,
        )
