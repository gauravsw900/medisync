"""
Database seeder — creates default accounts and sample data on first run.

Creates:
- 1 admin account
- 2 physician accounts with profiles and availability slots
- 2 patient accounts with medical history
- Appointment slots for the next 7 days

Run with: python -c "import asyncio; from db.seed import seed; asyncio.run(seed())"
Or automatically on startup if DATABASE_SEEDED env var is not set.
"""

import asyncio
from datetime import date, timedelta
from sqlalchemy import select
from db.database import AsyncSessionLocal
from models.models import User, UserRole, PatientProfile, PhysicianProfile, AvailabilitySlot
from core.security import hash_password


SEED_USERS = [
    {
        "email": "admin@medisync.com",
        "password": "Admin123!",
        "role": UserRole.ADMIN,
        "first_name": "Practice",
        "last_name": "Administrator",
        "phone": "555-000-0001",
    },
    {
        "email": "dr.smith@medisync.com",
        "password": "Doctor123!",
        "role": UserRole.PHYSICIAN,
        "first_name": "Sarah",
        "last_name": "Smith",
        "phone": "555-000-0002",
        "physician_profile": {
            "specialty": "Primary Care / Family Medicine",
            "npi_number": "1234567890",
            "license_number": "CA-12345",
            "license_state": "CA",
            "bio": "Dr. Smith has 15 years of experience in primary care with a focus on preventive medicine and chronic disease management.",
            "accepting_patients": True,
            "consultation_fee": 150.0,
        }
    },
    {
        "email": "dr.johnson@medisync.com",
        "password": "Doctor123!",
        "role": UserRole.PHYSICIAN,
        "first_name": "Marcus",
        "last_name": "Johnson",
        "phone": "555-000-0003",
        "physician_profile": {
            "specialty": "Internal Medicine",
            "npi_number": "0987654321",
            "license_number": "CA-67890",
            "license_state": "CA",
            "bio": "Dr. Johnson specialises in internal medicine with expertise in cardiovascular risk management and diabetes care.",
            "accepting_patients": True,
            "consultation_fee": 175.0,
        }
    },
    {
        "email": "john.doe@email.com",
        "password": "Patient123!",
        "role": UserRole.PATIENT,
        "first_name": "John",
        "last_name": "Doe",
        "phone": "555-111-2222",
        "patient_profile": {
            "date_of_birth": "1975-03-15",
            "gender": "Male",
            "blood_type": "O+",
            "height_cm": 178.0,
            "weight_kg": 85.0,
            "chronic_conditions": ["Type 2 Diabetes", "Hypertension"],
            "current_medications": [
                {"name": "Metformin", "dose": "500mg", "frequency": "Twice daily"},
                {"name": "Lisinopril", "dose": "10mg", "frequency": "Once daily"},
            ],
            "allergies": [
                {"allergen": "Penicillin", "reaction": "Rash"}
            ],
            "insurance_provider": "Blue Cross Blue Shield",
            "insurance_member_id": "BCBS-123456789",
            "emergency_contact_name": "Jane Doe",
            "emergency_contact_phone": "555-111-3333",
        }
    },
    {
        "email": "emily.chen@email.com",
        "password": "Patient123!",
        "role": UserRole.PATIENT,
        "first_name": "Emily",
        "last_name": "Chen",
        "phone": "555-444-5555",
        "patient_profile": {
            "date_of_birth": "1990-07-22",
            "gender": "Female",
            "blood_type": "A-",
            "height_cm": 162.0,
            "weight_kg": 58.0,
            "chronic_conditions": ["Asthma"],
            "current_medications": [
                {"name": "Albuterol inhaler", "dose": "90mcg", "frequency": "As needed"},
                {"name": "Fluticasone", "dose": "100mcg", "frequency": "Twice daily"},
            ],
            "allergies": [],
            "insurance_provider": "Aetna",
            "insurance_member_id": "AET-987654321",
            "emergency_contact_name": "Wei Chen",
            "emergency_contact_phone": "555-444-6666",
        }
    },
]


async def seed():
    """Run the database seeder."""
    async with AsyncSessionLocal() as db:
        print("Seeding database...")

        physician_profiles = []

        for user_data in SEED_USERS:
            # Check if user already exists
            existing = await db.execute(select(User).where(User.email == user_data["email"]))
            if existing.scalar_one_or_none():
                print(f"  Skipping {user_data['email']} — already exists")
                continue

            # Create user
            user = User(
                email=user_data["email"],
                hashed_password=hash_password(user_data["password"]),
                role=user_data["role"],
                first_name=user_data["first_name"],
                last_name=user_data["last_name"],
                phone=user_data.get("phone"),
            )
            db.add(user)
            await db.flush()
            print(f"  Created user: {user_data['email']} ({user_data['role'].value})")

            # Create profile
            if "physician_profile" in user_data:
                profile = PhysicianProfile(user_id=user.id, **user_data["physician_profile"])
                db.add(profile)
                await db.flush()
                physician_profiles.append(profile)

            elif "patient_profile" in user_data:
                profile = PatientProfile(user_id=user.id, **user_data["patient_profile"])
                db.add(profile)

        await db.flush()

        # Create availability slots for each physician for next 7 days
        for physician in physician_profiles:
            for days_ahead in range(1, 8):
                slot_date = str(date.today() + timedelta(days=days_ahead))
                # Skip weekends
                day_of_week = (date.today() + timedelta(days=days_ahead)).weekday()
                if day_of_week >= 5:  # Saturday=5, Sunday=6
                    continue

                # Create 6 slots per day: 9am, 9:30, 10, 10:30, 2pm, 2:30pm
                time_slots = [
                    ("09:00", "09:30"),
                    ("09:30", "10:00"),
                    ("10:00", "10:30"),
                    ("10:30", "11:00"),
                    ("14:00", "14:30"),
                    ("14:30", "15:00"),
                ]
                for start, end in time_slots:
                    slot = AvailabilitySlot(
                        physician_id=physician.id,
                        slot_date=slot_date,
                        start_time=start,
                        end_time=end,
                    )
                    db.add(slot)

        await db.commit()
        print("Database seeded successfully.")
        print("\nDefault accounts:")
        print("  Admin:     admin@medisync.com / Admin123!")
        print("  Physician: dr.smith@medisync.com / Doctor123!")
        print("  Physician: dr.johnson@medisync.com / Doctor123!")
        print("  Patient:   john.doe@email.com / Patient123!")
        print("  Patient:   emily.chen@email.com / Patient123!")


if __name__ == "__main__":
    asyncio.run(seed())
