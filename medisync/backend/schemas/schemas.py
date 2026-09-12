"""
Pydantic schemas — request validation and response serialisation.

Separate from SQLAlchemy models intentionally:
- Models define the database structure
- Schemas define the API contract
- This separation lets you evolve each independently

Naming convention:
- XxxCreate: fields needed to create a resource
- XxxUpdate: fields that can be updated (all optional)
- XxxResponse: what the API returns (never includes passwords)
- XxxInDB: internal representation with all fields
"""

from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional, Any
from datetime import datetime
from uuid import UUID
from models.models import UserRole, AppointmentStatus, NoteStatus
import re


# ── Auth schemas ───────────────────────────────────────────────────────────────

class UserRegister(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=100)
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    role: UserRole
    phone: Optional[str] = None

    @field_validator("password")
    @classmethod
    def password_strength(cls, v):
        """Enforce minimum password complexity."""
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not re.search(r"[0-9]", v):
            raise ValueError("Password must contain at least one number")
        return v


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: "UserResponse"


class RefreshRequest(BaseModel):
    refresh_token: str


# ── User schemas ───────────────────────────────────────────────────────────────

class UserResponse(BaseModel):
    id: UUID
    email: str
    role: UserRole
    first_name: str
    last_name: str
    phone: Optional[str]
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Patient profile schemas ────────────────────────────────────────────────────

class PatientProfileUpdate(BaseModel):
    date_of_birth: Optional[str] = None
    gender: Optional[str] = None
    blood_type: Optional[str] = None
    height_cm: Optional[float] = None
    weight_kg: Optional[float] = None
    allergies: Optional[list[dict]] = None
    current_medications: Optional[list[dict]] = None
    chronic_conditions: Optional[list[str]] = None
    insurance_provider: Optional[str] = None
    insurance_member_id: Optional[str] = None
    emergency_contact_name: Optional[str] = None
    emergency_contact_phone: Optional[str] = None


class PatientProfileResponse(BaseModel):
    id: UUID
    user_id: UUID
    date_of_birth: Optional[str]
    gender: Optional[str]
    blood_type: Optional[str]
    height_cm: Optional[float]
    weight_kg: Optional[float]
    allergies: list
    current_medications: list
    chronic_conditions: list
    insurance_provider: Optional[str]
    insurance_member_id: Optional[str]
    emergency_contact_name: Optional[str]
    emergency_contact_phone: Optional[str]

    model_config = {"from_attributes": True}


# ── Physician schemas ──────────────────────────────────────────────────────────

class PhysicianResponse(BaseModel):
    id: UUID
    user: UserResponse
    specialty: str
    bio: Optional[str]
    accepting_patients: bool
    consultation_fee: Optional[float]
    npi_number: Optional[str]

    model_config = {"from_attributes": True}


# ── Appointment schemas ────────────────────────────────────────────────────────

class AppointmentCreate(BaseModel):
    physician_id: UUID
    slot_id: UUID
    appointment_date: str   # YYYY-MM-DD
    appointment_time: str   # HH:MM
    reason_for_visit: Optional[str] = None
    visit_type: str = "in_person"


class AppointmentResponse(BaseModel):
    id: UUID
    status: AppointmentStatus
    appointment_date: str
    appointment_time: str
    reason_for_visit: Optional[str]
    visit_type: str
    created_at: datetime
    patient: Optional["PatientSummary"] = None
    physician: Optional["PhysicianSummary"] = None
    has_intake: bool = False
    has_note: bool = False

    model_config = {"from_attributes": True}


class PatientSummary(BaseModel):
    """Minimal patient info shown in appointment context"""
    id: UUID
    user: UserResponse
    date_of_birth: Optional[str]
    chronic_conditions: list
    allergies: list
    current_medications: list

    model_config = {"from_attributes": True}


class PhysicianSummary(BaseModel):
    """Minimal physician info shown in appointment context"""
    id: UUID
    user: UserResponse
    specialty: str

    model_config = {"from_attributes": True}


class AvailabilitySlotResponse(BaseModel):
    id: UUID
    slot_date: str
    start_time: str
    end_time: str
    is_booked: bool

    model_config = {"from_attributes": True}


# ── Intake schemas ─────────────────────────────────────────────────────────────

class IntakeChatMessage(BaseModel):
    """A single message sent during the intake conversation"""
    message: str


class IntakeResponse(BaseModel):
    id: UUID
    appointment_id: UUID
    conversation: list
    chief_complaint: Optional[str]
    symptom_severity: Optional[int]
    red_flags: list
    ai_brief: Optional[str]
    is_complete: bool

    model_config = {"from_attributes": True}


# ── Clinical note schemas ──────────────────────────────────────────────────────

class NoteGenerateRequest(BaseModel):
    """Physician submits their post-visit summary for AI to draft into a SOAP note"""
    physician_summary: str = Field(
        min_length=10,
        description="Physician's free-text summary of the visit"
    )


class NoteApproveRequest(BaseModel):
    """Physician approves (optionally amending) the AI-drafted note"""
    amendments: Optional[str] = None    # What the physician changed
    # Physician can override any SOAP field directly
    subjective: Optional[str] = None
    objective: Optional[str] = None
    assessment: Optional[str] = None
    plan: Optional[str] = None


class ClinicalNoteResponse(BaseModel):
    id: UUID
    appointment_id: UUID
    subjective: Optional[str]
    objective: Optional[str]
    assessment: Optional[str]
    plan: Optional[str]
    full_note: Optional[str]
    status: NoteStatus
    physician_amendments: Optional[str]
    ai_generated_at: Optional[datetime]
    approved_at: Optional[datetime]

    model_config = {"from_attributes": True}


# ── Dashboard schemas ──────────────────────────────────────────────────────────

class PhysicianDashboard(BaseModel):
    """All data needed to render the physician's daily dashboard"""
    today_appointments: list[AppointmentResponse]
    pending_notes: int          # Notes awaiting physician approval
    total_patients: int
    upcoming_appointments: list[AppointmentResponse]


class AdminStats(BaseModel):
    total_patients: int
    total_physicians: int
    total_appointments: int
    appointments_today: int
    pending_notes: int
    completed_intakes: int
