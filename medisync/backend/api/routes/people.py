"""
Patient, physician, and admin routes.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from datetime import date

from db.database import get_db
from models.models import (
    User, PatientProfile, PhysicianProfile, Appointment,
    AvailabilitySlot, AppointmentStatus, ClinicalNote, NoteStatus,
    PatientIntake, AuditLog, UserRole
)
from schemas.schemas import (
    PatientProfileUpdate, PatientProfileResponse,
    PhysicianResponse, PhysicianDashboard, AdminStats, AppointmentResponse
)
from core.dependencies import (
    get_current_user, get_current_patient, get_current_physician,
    get_current_admin, get_physician_or_admin
)

patients_router = APIRouter(prefix="/patients", tags=["Patients"])
physicians_router = APIRouter(prefix="/physicians", tags=["Physicians"])
admin_router = APIRouter(prefix="/admin", tags=["Admin"])


# ── Patient routes ─────────────────────────────────────────────────────────────

@patients_router.get("/profile", response_model=PatientProfileResponse)
async def get_my_profile(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_patient),
):
    """Get the current patient's profile."""
    result = await db.execute(
        select(PatientProfile).where(PatientProfile.user_id == current_user.id)
    )
    profile = result.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return profile


@patients_router.put("/profile", response_model=PatientProfileResponse)
async def update_my_profile(
    data: PatientProfileUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_patient),
):
    """Update the current patient's profile."""
    result = await db.execute(
        select(PatientProfile).where(PatientProfile.user_id == current_user.id)
    )
    profile = result.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    # Only update fields that were provided
    for field, value in data.model_dump(exclude_none=True).items():
        setattr(profile, field, value)

    db.add(AuditLog(
        user_id=current_user.id,
        action="patient.profile.updated",
        resource_type="patient_profile",
        resource_id=str(profile.id),
    ))
    await db.commit()
    await db.refresh(profile)
    return profile


@patients_router.get("/{patient_id}", response_model=PatientProfileResponse)
async def get_patient_profile(
    patient_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_physician_or_admin),
):
    """Get a patient's profile — physicians and admins only."""
    result = await db.execute(
        select(PatientProfile).where(PatientProfile.id == patient_id)
    )
    profile = result.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail="Patient not found")

    db.add(AuditLog(
        user_id=current_user.id,
        action="patient.profile.viewed",
        resource_type="patient_profile",
        resource_id=str(profile.id),
    ))
    await db.commit()
    return profile


# ── Physician routes ───────────────────────────────────────────────────────────

@physicians_router.get("/", response_model=list[PhysicianResponse])
async def list_physicians(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all active physicians — used by patients when booking."""
    result = await db.execute(
        select(PhysicianProfile)
        .options(selectinload(PhysicianProfile.user))
        .join(User)
        .where(User.is_active == True, PhysicianProfile.accepting_patients == True)
    )
    return result.scalars().all()


@physicians_router.get("/dashboard", response_model=PhysicianDashboard)
async def get_physician_dashboard(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_physician),
):
    """
    The physician's main dashboard — today's appointments with AI briefs.
    This is the page they see when they log in each morning.
    """
    physician_result = await db.execute(
        select(PhysicianProfile).where(PhysicianProfile.user_id == current_user.id)
    )
    physician = physician_result.scalar_one_or_none()
    if not physician:
        raise HTTPException(status_code=404, detail="Physician profile not found")

    today = str(date.today())

    # Today's appointments with patient data and intake status
    today_result = await db.execute(
        select(Appointment)
        .options(
            selectinload(Appointment.patient).selectinload(PatientProfile.user),
            selectinload(Appointment.intake),
            selectinload(Appointment.clinical_note),
        )
        .where(
            Appointment.physician_id == physician.id,
            Appointment.appointment_date == today,
            Appointment.status.in_([AppointmentStatus.SCHEDULED, AppointmentStatus.CONFIRMED, AppointmentStatus.IN_PROGRESS]),
        )
        .order_by(Appointment.appointment_time)
    )
    today_appointments = today_result.scalars().all()

    # Count notes pending physician approval
    pending_result = await db.execute(
        select(func.count(ClinicalNote.id))
        .join(Appointment)
        .where(
            Appointment.physician_id == physician.id,
            ClinicalNote.status == NoteStatus.AI_DRAFT,
        )
    )
    pending_notes = pending_result.scalar() or 0

    # Total unique patients
    patient_result = await db.execute(
        select(func.count(func.distinct(Appointment.patient_id)))
        .where(Appointment.physician_id == physician.id)
    )
    total_patients = patient_result.scalar() or 0

    return PhysicianDashboard(
        today_appointments=[
            AppointmentResponse(
                id=a.id,
                status=a.status,
                appointment_date=a.appointment_date,
                appointment_time=a.appointment_time,
                reason_for_visit=a.reason_for_visit,
                visit_type=a.visit_type,
                created_at=a.created_at,
                has_intake=a.intake is not None and a.intake.is_complete,
                has_note=a.clinical_note is not None,
            )
            for a in today_appointments
        ],
        pending_notes=pending_notes,
        total_patients=total_patients,
        upcoming_appointments=[],
    )


# ── Admin routes ───────────────────────────────────────────────────────────────

@admin_router.get("/stats", response_model=AdminStats)
async def get_admin_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    """Practice-wide statistics for the admin dashboard."""
    today = str(date.today())

    async def count(model, *conditions):
        result = await db.execute(select(func.count(model.id)).where(*conditions))
        return result.scalar() or 0

    return AdminStats(
        total_patients=await count(User, User.role == UserRole.PATIENT, User.is_active == True),
        total_physicians=await count(User, User.role == UserRole.PHYSICIAN, User.is_active == True),
        total_appointments=await count(Appointment),
        appointments_today=await count(Appointment, Appointment.appointment_date == today),
        pending_notes=await count(ClinicalNote, ClinicalNote.status == NoteStatus.AI_DRAFT),
        completed_intakes=await count(PatientIntake, PatientIntake.is_complete == True),
    )


@admin_router.get("/users")
async def list_all_users(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    """List all users in the system."""
    result = await db.execute(select(User).order_by(User.created_at.desc()))
    users = result.scalars().all()
    return [{"id": u.id, "email": u.email, "role": u.role, "name": u.full_name, "is_active": u.is_active} for u in users]


@admin_router.post("/slots")
async def create_availability_slot(
    physician_id: str,
    slot_date: str,
    start_time: str,
    end_time: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    """Create an availability slot for a physician."""
    slot = AvailabilitySlot(
        physician_id=physician_id,
        slot_date=slot_date,
        start_time=start_time,
        end_time=end_time,
    )
    db.add(slot)
    await db.commit()
    return {"id": str(slot.id), "slot_date": slot_date, "start_time": start_time}
