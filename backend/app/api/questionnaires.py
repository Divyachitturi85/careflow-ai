import json
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.security.auth import get_current_user
from app.security.rbac import require_roles
from app.models import (
    User,
    Appointment,
    Questionnaire,
    QuestionnaireQuestion,
    QuestionnaireResponse,
    Doctor,
    Workflow,
    WorkflowExecution,
    AuditEvent,
)
from app.schemas.questionnaire import (
    QuestionnaireSchema,
    QuestionSchema,
    SubmitResponseRequest,
    QuestionnaireResponseSchema,
)

router = APIRouter(prefix="/api/questionnaires", tags=["Questionnaires"])

@router.get("/appointment/{appointment_id}")
def get_questionnaire_for_appointment(
    appointment_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieves the assigned intake questionnaire and any existing response for an appointment."""
    appointment = db.query(Appointment).filter(Appointment.id == appointment_id).first()
    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appointment not found.",
        )

    # RBAC: Patient can only access their own, Doctor can access own patient's, Admin can access hospital's
    if current_user.role == "PATIENT":
        if not current_user.patient_profile or appointment.patient_id != current_user.patient_profile.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")
    elif current_user.role == "DOCTOR":
        if not current_user.doctor_profile or appointment.doctor_id != current_user.doctor_profile.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")
    elif current_user.role == "HOSPITAL_ADMIN":
        if current_user.staff_profile and appointment.hospital_id != current_user.staff_profile.hospital_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")

    # Find questionnaire matching specialty, or doctor, or hospital default
    doctor = db.query(Doctor).filter(Doctor.id == appointment.doctor_id).first()
    questionnaire = None

    if doctor and doctor.specialty_id:
        questionnaire = (
            db.query(Questionnaire)
            .filter(
                Questionnaire.hospital_id == appointment.hospital_id,
                Questionnaire.specialty_id == doctor.specialty_id,
                Questionnaire.is_active == True,
            )
            .first()
        )

    if not questionnaire:
        questionnaire = (
            db.query(Questionnaire)
            .filter(
                Questionnaire.hospital_id == appointment.hospital_id,
                Questionnaire.is_active == True,
            )
            .first()
        )

    if not questionnaire:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No intake questionnaire found for this appointment.",
        )

    # Check existing response
    existing_resp = (
        db.query(QuestionnaireResponse)
        .filter(QuestionnaireResponse.appointment_id == appointment_id)
        .first()
    )

    questions_out = []
    for q in questionnaire.questions:
        opts = json.loads(q.options_json) if q.options_json else None
        questions_out.append(
            {
                "id": q.id,
                "order_index": q.order_index,
                "prompt": q.prompt,
                "question_type": q.question_type,
                "options": opts,
                "is_required": q.is_required,
            }
        )

    return {
        "questionnaire": {
            "id": questionnaire.id,
            "hospital_id": questionnaire.hospital_id,
            "title": questionnaire.title,
            "description": questionnaire.description,
            "questions": questions_out,
        },
        "response": {
            "id": existing_resp.id,
            "status": existing_resp.status,
            "answers": json.loads(existing_resp.answers_json),
            "completed_at": existing_resp.completed_at.isoformat() if existing_resp.completed_at else None,
        } if existing_resp else None,
    }

@router.post("/responses")
def submit_questionnaire_response(
    req: SubmitResponseRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Submits answers for an appointment's pre-visit questionnaire."""
    appointment = db.query(Appointment).filter(Appointment.id == req.appointment_id).first()
    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appointment not found.",
        )

    if current_user.role == "PATIENT":
        if not current_user.patient_profile or appointment.patient_id != current_user.patient_profile.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")

    # Find questionnaire
    doctor = db.query(Doctor).filter(Doctor.id == appointment.doctor_id).first()
    questionnaire = (
        db.query(Questionnaire)
        .filter(
            Questionnaire.hospital_id == appointment.hospital_id,
            Questionnaire.is_active == True,
        )
        .first()
    )
    if not questionnaire:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Questionnaire not found.")

    existing_resp = (
        db.query(QuestionnaireResponse)
        .filter(QuestionnaireResponse.appointment_id == req.appointment_id)
        .first()
    )

    now = datetime.now(timezone.utc)
    if existing_resp:
        existing_resp.answers_json = json.dumps(req.answers)
        existing_resp.status = "COMPLETED"
        existing_resp.completed_at = now
        response_record = existing_resp
    else:
        response_record = QuestionnaireResponse(
            questionnaire_id=questionnaire.id,
            appointment_id=req.appointment_id,
            patient_id=appointment.patient_id,
            answers_json=json.dumps(req.answers),
            status="COMPLETED",
            completed_at=now,
        )
        db.add(response_record)

    # Update workflow execution state if exists
    wf = (
        db.query(Workflow)
        .filter(
            Workflow.hospital_id == appointment.hospital_id,
            Workflow.trigger_event == "APPOINTMENT_CONFIRMED",
            Workflow.is_active == True,
        )
        .first()
    )
    if wf:
        wf_exec = (
            db.query(WorkflowExecution)
            .filter(
                WorkflowExecution.workflow_id == wf.id,
                WorkflowExecution.appointment_id == appointment.id,
            )
            .first()
        )
        if not wf_exec:
            wf_exec = WorkflowExecution(
                workflow_id=wf.id,
                appointment_id=appointment.id,
                current_step="COMPLETED",
                status="COMPLETED",
                step_history_json=json.dumps([{"step": "QUESTIONNAIRE_SUBMITTED", "timestamp": now.isoformat()}]),
            )
            db.add(wf_exec)
        else:
            wf_exec.current_step = "COMPLETED"
            wf_exec.status = "COMPLETED"

    # Audit log
    db.add(
        AuditEvent(
            correlation_id=appointment.correlation_id,
            actor_id=current_user.id,
            actor_role=current_user.role,
            action="QUESTIONNAIRE_SUBMITTED",
            resource_type="QUESTIONNAIRE_RESPONSE",
            resource_id=response_record.id,
            status="SUCCESS",
            details_json=json.dumps({"appointment_id": appointment.id, "answers_count": len(req.answers)}),
        )
    )
    db.commit()
    db.refresh(response_record)

    return {
        "status": "COMPLETED",
        "message": "Pre-visit questionnaire submitted successfully.",
        "completed_at": now.isoformat(),
    }

@router.get("/doctor/{doctor_id}/responses")
def get_doctor_questionnaire_responses(
    doctor_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["DOCTOR", "HOSPITAL_ADMIN", "PLATFORM_ADMIN"])),
):
    """Doctor view of patient intake responses for clinical preparation."""
    if current_user.role == "DOCTOR":
        if not current_user.doctor_profile or current_user.doctor_profile.id != doctor_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")

    doctor = db.query(Doctor).filter(Doctor.id == doctor_id).first()
    if not doctor:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Doctor not found.")

    if current_user.role == "HOSPITAL_ADMIN":
        if current_user.staff_profile and doctor.hospital_id != current_user.staff_profile.hospital_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied to other hospital doctors.")

    appts = (
        db.query(Appointment)
        .filter(Appointment.doctor_id == doctor_id)
        .join(QuestionnaireResponse, Appointment.id == QuestionnaireResponse.appointment_id)
        .all()
    )

    results = []
    for a in appts:
        if a.questionnaire_response:
            results.append({
                "appointment_id": a.id,
                "patient_name": f"{a.patient.user.first_name} {a.patient.user.last_name}" if a.patient and a.patient.user else "Unknown Patient",
                "appointment_time": a.slot.start_time.strftime("%A, %b %d at %I:%M %p") if a.slot else "N/A",
                "status": a.questionnaire_response.status,
                "completed_at": a.questionnaire_response.completed_at.isoformat() if a.questionnaire_response.completed_at else None,
                "answers": json.loads(a.questionnaire_response.answers_json),
            })

    return {"count": len(results), "responses": results}
