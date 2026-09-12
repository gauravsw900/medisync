"""
Appointment routes — booking, scheduling, status management.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
from sqlalchemy.orm import selectinload
from datetime import date

from db.database import get_db
from models.models import (
    User, Appointment, AppointmentStatus, AvailabilitySlot,
    PatientProfile, PhysicianProfile, AuditLog
)
from schemas.schemas import AppointmentCreate, AppointmentResponse, AvailabilitySlotResponse
from core.dependencies import get_current_user, get_current_patient, get_current_physician, get_physician_or_admin

router = APIRouter(prefix="/appointments", tags=["Appointments"])


@router.get("/slots/{physician_id}", response_model=list[AvailabilitySlotResponse])
async def get_available_slots(
    physician_id: str,
    date_from: str = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get available (unbooked) appointment slots for a physician."""
    result = await db.execute(
        select(AvailabilitySlot).where(
            and_(
                AvailabilitySlot.physician_id == physician_id,
                AvailabilitySlot.is_booked == False,
                AvailabilitySlot.slot_date >= (date_from or str(date.today())),
            )
        ).order_by(AvailabilitySlot.slot_date, AvailabilitySlot.start_time)
    )
    return result.scalars().all()


@router.post("/book", response_model=AppointmentResponse, status_code=status.HTTP_201_CREATED)
async def book_appointment(
    data: AppointmentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_patient),
):
    """
    Book an appointment for the current patient.

    Locks the slot row to prevent race conditions — two patients
    can't book the same slot simultaneously.
    """
    # Get patient profile
    result = await db.execute(
        select(PatientProfile).where(PatientProfile.user_id == current_user.id)
    )
    patient = result.scalar_one_or_none()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient profile not found")

    # Lock the slot row to prevent double-booking
    slot_result = await db.execute(
        select(AvailabilitySlot)
        .where(AvailabilitySlot.id == data.slot_id)
        .with_for_update()  # Row-level lock
    )
    slot = slot_result.scalar_one_or_none()

    if not slot:
        raise HTTPException(status_code=404, detail="Slot not found")
    if slot.is_booked:
        raise HTTPException(status_code=409, detail="This slot has already been booked")

    # Get physician profile
    physician_result = await db.execute(
        select(PhysicianProfile).where(PhysicianProfile.user_id == data.physician_id)
    )
    physician = physician_result.scalar_one_or_none()
    if not physician:
        raise HTTPException(status_code=404, detail="Physician not found")

    # Create appointment and mark slot as booked
    appointment = Appointment(
        patient_id=patient.id,
        physician_id=physician.id,
        slot_id=slot.id,
        appointment_date=data.appointment_date,
        appointment_time=data.appointment_time,
        reason_for_visit=data.reason_for_visit,
        visit_type=data.visit_type,
        status=AppointmentStatus.SCHEDULED,
    )
    slot.is_booked = True

    db.add(appointment)
    db.add(AuditLog(
        user_id=current_user.id,
        action="appointment.booked",
        resource_type="appointment",
        resource_id=str(appointment.id),
    ))

    await db.commit()
    await db.refresh(appointment)

    return AppointmentResponse(
        id=appointment.id,
        status=appointment.status,
        appointment_date=appointment.appointment_date,
        appointment_time=appointment.appointment_time,
        reason_for_visit=appointment.reason_for_visit,
        visit_type=appointment.visit_type,
        created_at=appointment.created_at,
    )


@router.get("/my", response_model=list[AppointmentResponse])
async def get_my_appointments(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get appointments for the current user.
    Returns different results depending on role:
    - Patient: their own appointments
    - Physician: their scheduled appointments
    """
    if current_user.role.value == "patient":
        profile_result = await db.execute(
            select(PatientProfile).where(PatientProfile.user_id == current_user.id)
        )
        profile = profile_result.scalar_one_or_none()
        if not profile:
            return []

        result = await db.execute(
            select(Appointment)
            .options(
                selectinload(Appointment.physician).selectinload(PhysicianProfile.user),
                selectinload(Appointment.intake),
                selectinload(Appointment.clinical_note),
            )
            .where(Appointment.patient_id == profile.id)
            .order_by(Appointment.appointment_date.desc(), Appointment.appointment_time.desc())
        )
    else:
        profile_result = await db.execute(
            select(PhysicianProfile).where(PhysicianProfile.user_id == current_user.id)
        )
        profile = profile_result.scalar_one_or_none()
        if not profile:
            return []

        result = await db.execute(
            select(Appointment)
            .options(
                selectinload(Appointment.patient).selectinload(PatientProfile.user),
                selectinload(Appointment.intake),
                selectinload(Appointment.clinical_note),
            )
            .where(Appointment.physician_id == profile.id)
            .order_by(Appointment.appointment_date.desc(), Appointment.appointment_time.desc())
        )

    appointments = result.scalars().all()
    return [
        AppointmentResponse(
            id=a.id,
            status=a.status,
            appointment_date=a.appointment_date,
            appointment_time=a.appointment_time,
            reason_for_visit=a.reason_for_visit,
            visit_type=a.visit_type,
            created_at=a.created_at,
            has_intake=a.intake is not None,
            has_note=a.clinical_note is not None,
        )
        for a in appointments
    ]


@router.get("/{appointment_id}", response_model=AppointmentResponse)
async def get_appointment(
    appointment_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a specific appointment. Users can only view their own appointments."""
    result = await db.execute(
        select(Appointment)
        .options(
            selectinload(Appointment.patient).selectinload(PatientProfile.user),
            selectinload(Appointment.physician).selectinload(PhysicianProfile.user),
            selectinload(Appointment.intake),
            selectinload(Appointment.clinical_note),
        )
        .where(Appointment.id == appointment_id)
    )
    appointment = result.scalar_one_or_none()
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")

    return AppointmentResponse(
        id=appointment.id,
        status=appointment.status,
        appointment_date=appointment.appointment_date,
        appointment_time=appointment.appointment_time,
        reason_for_visit=appointment.reason_for_visit,
        visit_type=appointment.visit_type,
        created_at=appointment.created_at,
        has_intake=appointment.intake is not None,
        has_note=appointment.clinical_note is not None,
    )


@router.patch("/{appointment_id}/status")
async def update_appointment_status(
    appointment_id: str,
    new_status: AppointmentStatus,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_physician_or_admin),
):
    """Update appointment status — physicians and admins only."""
    result = await db.execute(select(Appointment).where(Appointment.id == appointment_id))
    appointment = result.scalar_one_or_none()
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")

    appointment.status = new_status
    db.add(AuditLog(
        user_id=current_user.id,
        action=f"appointment.status.{new_status.value}",
        resource_type="appointment",
        resource_id=str(appointment.id),
    ))
    await db.commit()
    return {"status": "updated", "new_status": new_status}
