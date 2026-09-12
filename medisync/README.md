# MediSync — AI-Powered Primary Care Management System

A full-stack practice management platform for US primary care clinics with AI built into the core workflow — not bolted on as an afterthought.

---

## What it does

**For patients:**
- Register, log in, book appointments with available physicians
- Complete an AI-guided pre-visit intake (symptoms, history, concerns)
- View past appointments and visit summaries

**For physicians:**
- Dashboard showing today's schedule with AI-generated pre-visit briefs
- Each brief summarises the patient's intake, flags red flags, and suggests relevant history to review
- After the visit, AI drafts a structured clinical note (SOAP format) — physician reviews and signs off
- Full patient history with all past notes

**For practice admins:**
- Manage physicians, patients, and appointment slots
- View practice-wide analytics
- Audit trail of all AI-generated content and physician approvals

---

## AI agents

| Agent | Input | Output |
|---|---|---|
| **Intake agent** | Patient's free-text symptom description | Structured symptom brief + red flag alerts |
| **Brief agent** | Intake + patient history | 1-page pre-visit physician brief |
| **Note drafting agent** | Physician's post-visit summary | Full SOAP clinical note |

All AI output is clearly labelled as AI-generated and requires physician review before being stored as an approved note. The physician is always in the loop.

---

## Tech stack

| Layer | Technology |
|---|---|
| Frontend | React 18, Tailwind CSS, Zustand |
| Backend | Python 3.11, FastAPI |
| Database | PostgreSQL 15 |
| ORM | SQLAlchemy 2.0 + Alembic migrations |
| Auth | JWT (access + refresh tokens), bcrypt |
| AI | Anthropic Claude API |
| Deployment | Docker + docker-compose |

---

## Getting started

### With Docker (recommended)

```bash
cp .env.example .env
# Add your ANTHROPIC_API_KEY to .env

docker-compose up --build
# Frontend: http://localhost:5173
# API:      http://localhost:8000
# API docs: http://localhost:8000/docs
```

### Without Docker

```bash
# Backend
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # fill in values
alembic upgrade head  # run migrations
python main.py

# Frontend
cd frontend
npm install && npm run dev
```

---

## Default accounts (seeded on first run)

| Role | Email | Password |
|---|---|---|
| Admin | admin@medisync.com | Admin123! |
| Physician | dr.smith@medisync.com | Doctor123! |
| Patient | john.doe@email.com | Patient123! |

---

## Project structure

```
medisync/
├── backend/
│   ├── main.py                    # FastAPI app entry point
│   ├── alembic/                   # Database migrations
│   ├── api/routes/
│   │   ├── auth.py                # Login, register, refresh token
│   │   ├── appointments.py        # Booking, scheduling
│   │   ├── patients.py            # Patient records
│   │   ├── physicians.py          # Physician management
│   │   └── notes.py               # Clinical notes
│   ├── agents/
│   │   ├── intake_agent.py        # Pre-visit symptom collection
│   │   ├── brief_agent.py         # Physician pre-visit brief
│   │   └── note_agent.py          # SOAP note drafter
│   ├── core/
│   │   ├── config.py              # Settings from environment
│   │   ├── security.py            # JWT + bcrypt
│   │   └── dependencies.py        # FastAPI dependencies (get_current_user)
│   ├── db/
│   │   ├── database.py            # SQLAlchemy engine + session
│   │   └── seed.py                # Default data seeder
│   ├── models/                    # SQLAlchemy ORM models
│   └── schemas/                   # Pydantic request/response schemas
├── frontend/
│   └── src/
│       ├── components/
│       │   ├── auth/              # Login, register pages
│       │   ├── patient/           # Patient dashboard, booking, intake
│       │   ├── doctor/            # Physician dashboard, notes
│       │   ├── admin/             # Admin panel
│       │   └── shared/            # Navbar, layout, common UI
│       ├── hooks/                 # useAuth, useApi
│       ├── store/                 # Zustand global state
│       └── utils/                 # API client, helpers
├── docker/
│   ├── Dockerfile.backend
│   └── Dockerfile.frontend
├── docker-compose.yml
└── .env.example
```

---

## Clinical disclaimer

MediSync is a demonstration system. It is not a certified medical device. AI-generated content must always be reviewed and approved by a licensed physician before use in any clinical context.
