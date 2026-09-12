"""
Clinical notes and intake routes.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from datetime import datetime, timezone

from db.database import get_db
from models.models import (
    User, Appointment, PatientIntake, ClinicalNote,
    PatientProfile, PhysicianProfile, NoteStatus, AuditLog
)
from schemas.schemas import IntakeChatMessage, IntakeResponse, NoteGenerateRequest, NoteApproveRequest, ClinicalNoteResponse
from core.dependencies import get_current_user, get_current_patient, get_current_physician
from agents.agents import run_intake_turn, generate_physician_brief, draft_clinical_note

router = APIRouter(tags=["Clinical"])

# ── Intake routes ──────────────────────────────────────────────────────────────

@router.post("/intake/{appointment_id}/chat")
async def intake_chat(
    appointment_id: str,
    message: IntakeChatMessage,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_patient),
):
    """
    Send a message in the pre-visit intake conversation.

    The intake agent conducts a structured conversation collecting
    symptoms and history. When complete, it auto-generates the
    physician brief and marks the intake as done.
    """
    # Get the appointment and verify ownership
    appt_result = await db.execute(
        select(Appointment)
        .options(selectinload(Appointment.patient).selectinload(PatientProfile.user))
        .where(Appointment.id == appointment_id)
    )
    appointment = appt_result.scalar_one_or_none()
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")

    # Verify this patient owns the appointment
    if str(appointment.patient.user_id) != str(current_user.id):
        raise HTTPException(status_code=403, detail="Access denied")

    # Get or create the intake record
    intake_result = await db.execute(
        select(PatientIntake).where(PatientIntake.appointment_id == appointment_id)
    )
    intake = intake_result.scalar_one_or_none()

    if not intake:
        intake = PatientIntake(
            appointment_id=appointment.id,
            patient_id=appointment.patient_id,
            conversation=[],
        )
        db.add(intake)
        await db.flush()

    if intake.is_complete:
        raise HTTPException(status_code=400, detail="Intake is already complete")

    # Run one turn of the intake agent
    response_text, structured_data = await run_intake_turn(
        conversation=intake.conversation,
        patient_message=message.message,
        patient_name=current_user.first_name,
    )

    # Update conversation history
    updated_conversation = intake.conversation + [
        {"role": "user", "content": message.message},
        {"role": "assistant", "content": response_text},
    ]
    intake.conversation = updated_conversation

    # If intake is complete, generate the physician brief
    if structured_data and structured_data.get("ready_for_brief"):
        intake.chief_complaint = structured_data.get("chief_complaint")
        intake.symptom_duration = structured_data.get("duration")
        intake.symptom_severity = structured_data.get("severity")
        intake.associated_symptoms = structured_data.get("associated_symptoms", [])
        intake.relevant_history = structured_data.get("relevant_history")
        intake.red_flags = structured_data.get("red_flags", [])

        # Generate the physician brief
        patient = appointment.patient
        patient_info = {
            "name": current_user.full_name,
            "date_of_birth": patient.date_of_birth,
            "appointment_date": appointment.appointment_date,
            "appointment_time": appointment.appointment_time,
            "chronic_conditions": patient.chronic_conditions or [],
            "current_medications": patient.current_medications or [],
            "allergies": patient.allergies or [],
        }
        brief = await generate_physician_brief(structured_data, patient_info)
        intake.ai_brief = brief
        intake.is_complete = True
        intake.completed_at = datetime.now(timezone.utc)

    await db.commit()

    return {
        "response": response_text,
        "is_complete": intake.is_complete,
        "has_red_flags": bool(intake.red_flags),
    }


@router.get("/intake/{appointment_id}", response_model=IntakeResponse)
async def get_intake(
    appointment_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get the intake record for an appointment."""
    result = await db.execute(
        select(PatientIntake).where(PatientIntake.appointment_id == appointment_id)
    )
    intake = result.scalar_one_or_none()
    if not intake:
        raise HTTPException(status_code=404, detail="Intake not found")
    return intake


# ── Clinical note routes ───────────────────────────────────────────────────────

@router.post("/notes/{appointment_id}/generate", response_model=ClinicalNoteResponse)
async def generate_note(
    appointment_id: str,
    data: NoteGenerateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_physician),
):
    """
    Physician submits their post-visit summary; AI drafts the SOAP note.

    The physician writes a free-text summary of the visit and submits it.
    The AI drafts a properly structured SOAP note which the physician
    then reviews and approves (with any amendments).
    """
    # Get appointment with all related data
    appt_result = await db.execute(
        select(Appointment)
        .options(
            selectinload(Appointment.patient).selectinload(PatientProfile.user),
            selectinload(Appointment.intake),
        )
        .where(Appointment.id == appointment_id)
    )
    appointment = appt_result.scalar_one_or_none()
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")

    # Check if note already exists
    existing = await db.execute(
        select(ClinicalNote).where(ClinicalNote.appointment_id == appointment_id)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="A note already exists for this appointment")

    # Build patient context for the note agent
    patient = appointment.patient
    patient_info = {
        "name": patient.user.full_name,
        "date_of_birth": patient.date_of_birth,
        "appointment_date": appointment.appointment_date,
        "chronic_conditions": patient.chronic_conditions or [],
        "current_medications": patient.current_medications or [],
        "allergies": patient.allergies or [],
    }

    # Draft the SOAP note
    note_data = await draft_clinical_note(
        physician_summary=data.physician_summary,
        patient_info=patient_info,
        intake_data=appointment.intake.__dict__ if appointment.intake else None,
    )

    # Get physician profile
    physician_result = await db.execute(
        select(PhysicianProfile).where(PhysicianProfile.user_id == current_user.id)
    )
    physician = physician_result.scalar_one_or_none()

    # Save the AI-drafted note
    note = ClinicalNote(
        appointment_id=appointment.id,
        physician_id=physician.id,
        physician_summary=data.physician_summary,
        subjective=note_data.get("subjective"),
        objective=note_data.get("objective"),
        assessment=note_data.get("assessment"),
        plan=note_data.get("plan"),
        full_note=note_data.get("full_note"),
        status=NoteStatus.AI_DRAFT,
        ai_generated_at=datetime.now(timezone.utc),
    )
    db.add(note)

    db.add(AuditLog(
        user_id=current_user.id,
        action="note.ai_generated",
        resource_type="clinical_note",
        resource_id=str(note.id),
    ))

    await db.commit()
    await db.refresh(note)
    return note


@router.post("/notes/{note_id}/approve", response_model=ClinicalNoteResponse)
async def approve_note(
    note_id: str,
    data: NoteApproveRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_physician),
):
    """
    Physician reviews and approves (optionally amending) an AI-drafted note.

    This is the final gate before the note becomes part of the official record.
    The physician's identity and timestamp are recorded for HIPAA compliance.
    """
    result = await db.execute(select(ClinicalNote).where(ClinicalNote.id == note_id))
    note = result.scalar_one_or_none()
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")

    if note.status == NoteStatus.APPROVED:
        raise HTTPException(status_code=400, detail="Note has already been approved")

    now = datetime.now(timezone.utc)

    # Apply any amendments the physician made
    if data.subjective:
        note.subjective = data.subjective
    if data.objective:
        note.objective = data.objective
    if data.assessment:
        note.assessment = data.assessment
    if data.plan:
        note.plan = data.plan
    if data.amendments:
        note.physician_amendments = data.amendments

    # Rebuild full note from potentially amended sections
    note.full_note = (
        f"SUBJECTIVE:\n{note.subjective}\n\n"
        f"OBJECTIVE:\n{note.objective}\n\n"
        f"ASSESSMENT:\n{note.assessment}\n\n"
        f"PLAN:\n{note.plan}"
    )

    note.status = NoteStatus.APPROVED
    note.physician_reviewed_at = now
    note.approved_at = now
    note.approved_by_id = current_user.id

    db.add(AuditLog(
        user_id=current_user.id,
        action="note.approved",
        resource_type="clinical_note",
        resource_id=str(note.id),
        details={"had_amendments": bool(data.amendments)},
    ))

    await db.commit()
    await db.refresh(note)
    return note


@router.get("/notes/{appointment_id}", response_model=ClinicalNoteResponse)
async def get_note(
    appointment_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get the clinical note for an appointment."""
    result = await db.execute(
        select(ClinicalNote).where(ClinicalNote.appointment_id == appointment_id)
    )
    note = result.scalar_one_or_none()
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    return note
