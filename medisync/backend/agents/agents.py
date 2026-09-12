"""
AI Agents for MediSync
=======================

Three agents, each with a distinct role:

1. IntakeAgent — conversational pre-visit symptom collection
   Input:  Patient's free-text messages
   Output: Structured symptom data + conversation history

2. BriefAgent — physician pre-visit brief generator
   Input:  Completed intake data + patient medical history
   Output: 1-page structured brief for the physician

3. NoteAgent — post-visit SOAP note drafter
   Input:  Physician's free-text visit summary
   Output: Full SOAP-format clinical note

Design principles:
- Each agent has a focused, single responsibility
- All AI output is clearly labelled as AI-generated
- Physician review is always required before notes are approved
- Agents use structured JSON output for reliable parsing
"""

import json
import re
from anthropic import Anthropic
from core.config import settings

client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)
MODEL = "claude-sonnet-4-6"


# ── Agent 1: Intake Agent ─────────────────────────────────────────────────────

INTAKE_SYSTEM_PROMPT = """You are MediSync's patient intake assistant for a US primary care clinic.

Your job is to collect the patient's symptoms and relevant history before their appointment so their physician is fully prepared.

## Conversation approach
- Be warm, clear, and professional
- Ask one question at a time — never multiple questions in one message
- Use plain English, no medical jargon
- You have 5-7 exchanges to collect what you need

## What to collect (in this order)
1. Main reason for the visit / chief complaint
2. How long the symptoms have been present
3. Severity (1-10 scale)
4. Associated symptoms (what else they're experiencing)
5. Anything that makes it better or worse
6. Relevant medical history or medications they think are relevant
7. Any specific concerns or questions for the physician

## Red flags to identify immediately
Ask specifically about these if the chief complaint is relevant:
- Chest pain + shortness of breath
- Sudden severe headache ("worst of my life")
- Facial drooping, arm weakness, speech difficulty (stroke)
- Severe abdominal pain
- High fever (>103°F) with stiff neck
- Signs of severe allergic reaction

If ANY red flag is present, immediately tell the patient to call 911 or go to the ER. Do not continue the intake.

## When to end the intake
After collecting the above information (typically 5-7 exchanges), output ONLY this JSON block:

```intake_complete
{
  "chief_complaint": "...",
  "duration": "...",
  "severity": <1-10>,
  "associated_symptoms": ["...", "..."],
  "aggravating_factors": "...",
  "relieving_factors": "...",
  "relevant_history": "...",
  "patient_questions": ["..."],
  "red_flags": [],
  "ready_for_brief": true
}
```

If red flags are present, include them in the red_flags array and set ready_for_brief to false."""


async def run_intake_turn(
    conversation: list[dict],
    patient_message: str,
    patient_name: str,
) -> tuple[str, dict | None]:
    """
    Process one turn of the intake conversation.

    Args:
        conversation: Full conversation history so far
        patient_message: The patient's latest message
        patient_name: Patient's first name for personalisation

    Returns:
        Tuple of (assistant_response_text, structured_data_or_None)
        structured_data is returned only when the intake is complete
    """
    # Add the patient's message to history
    messages = conversation + [{"role": "user", "content": patient_message}]

    # Personalise the system prompt with the patient's name
    system = INTAKE_SYSTEM_PROMPT + f"\n\nThe patient's name is {patient_name}. Address them by name occasionally but not in every message."

    response = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        system=system,
        messages=messages,
    )

    response_text = response.content[0].text

    # Check if the intake is complete (agent output the JSON block)
    intake_data = None
    match = re.search(r'```intake_complete\s*([\s\S]*?)\s*```', response_text)
    if match:
        try:
            intake_data = json.loads(match.group(1))
            # Strip the JSON block from the displayed response
            response_text = response_text.replace(match.group(0), "").strip()
            if not response_text:
                response_text = "Thank you — I have everything I need. Your physician will be well-prepared for your visit. See you soon!"
        except json.JSONDecodeError:
            pass  # Keep going if JSON is malformed

    return response_text, intake_data


# ── Agent 2: Brief Agent ──────────────────────────────────────────────────────

BRIEF_SYSTEM_PROMPT = """You are a clinical documentation assistant for a US primary care clinic.

Your job is to generate a concise, structured pre-visit brief for a physician based on the patient's intake and medical history.

The brief should take the physician 60 seconds to read and give them everything they need to walk into the room prepared.

## Output format — always use this exact structure:

```
PATIENT BRIEF — [Patient Name] — [Appointment Date] [Time]
Generated by MediSync AI — Requires physician review

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

CHIEF COMPLAINT
[1-2 sentences]

PRESENTING SYMPTOMS
• [Symptom]: [duration, severity, character]
• [Symptom]: ...

VITALS (if available)
To be obtained at visit

RELEVANT HISTORY
• Conditions: [list]
• Current medications: [list]
• Allergies: [list]
• Last visit: [date if known]

RED FLAGS
[List any concerning symptoms, or "None identified"]

PATIENT'S QUESTIONS FOR PHYSICIAN
1. [Question]
2. ...

SUGGESTED FOCUS AREAS
[2-3 things the physician may want to assess based on the presentation]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
AI-GENERATED — Physician review required before use
```

Be clinical and precise. Use standard medical terminology. Do not speculate beyond the presented information."""


async def generate_physician_brief(
    intake_data: dict,
    patient_info: dict,
) -> str:
    """
    Generate a structured pre-visit brief for the physician.

    Args:
        intake_data: Structured output from the intake agent
        patient_info: Patient's demographics and medical history

    Returns:
        Formatted brief as a string
    """
    # Build the context for the brief agent
    context = f"""
Patient Information:
- Name: {patient_info.get('name', 'Unknown')}
- DOB: {patient_info.get('date_of_birth', 'Not provided')}
- Appointment: {patient_info.get('appointment_date', '')} at {patient_info.get('appointment_time', '')}

Medical History:
- Chronic conditions: {', '.join(patient_info.get('chronic_conditions', [])) or 'None on file'}
- Current medications: {json.dumps(patient_info.get('current_medications', [])) or 'None on file'}
- Allergies: {json.dumps(patient_info.get('allergies', [])) or 'None on file'}

Intake Summary:
- Chief complaint: {intake_data.get('chief_complaint', 'Not provided')}
- Duration: {intake_data.get('duration', 'Not provided')}
- Severity: {intake_data.get('severity', 'Not rated')}/10
- Associated symptoms: {', '.join(intake_data.get('associated_symptoms', [])) or 'None reported'}
- Aggravating factors: {intake_data.get('aggravating_factors', 'None reported')}
- Relieving factors: {intake_data.get('relieving_factors', 'None reported')}
- Relevant history (patient-reported): {intake_data.get('relevant_history', 'None reported')}
- Patient questions: {json.dumps(intake_data.get('patient_questions', []))}
- Red flags identified: {json.dumps(intake_data.get('red_flags', []))}

Generate the physician brief now.
"""

    response = client.messages.create(
        model=MODEL,
        max_tokens=1500,
        system=BRIEF_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": context}],
    )

    return response.content[0].text


# ── Agent 3: Note Drafting Agent ──────────────────────────────────────────────

NOTE_SYSTEM_PROMPT = """You are a clinical documentation specialist for a US primary care practice.

Your job is to take a physician's post-visit summary and transform it into a properly structured SOAP note suitable for the medical record.

## SOAP format
- Subjective: Patient's reported symptoms, history, and concerns (in their words)
- Objective: Measurable findings — vitals, physical exam, test results
- Assessment: Clinical impression — diagnosis or differential diagnoses with ICD-10 codes where possible
- Plan: Treatment plan, prescriptions, referrals, follow-up, patient education

## Guidelines
- Write in clinical prose, not bullet points (unless listing medications/diagnoses)
- Use standard medical abbreviations (BP, HR, Hx, Dx, Rx, f/u, etc.)
- Include ICD-10 codes for diagnoses where you can determine them
- Flag anything marked as uncertain with "[to be confirmed]"
- If information for a SOAP section is missing, note "Not documented this visit"
- Keep the Assessment concise — 2-4 diagnoses maximum
- The Plan should be specific: drug name, dose, frequency, duration

## Output format — return ONLY this JSON:
{
  "subjective": "...",
  "objective": "...",
  "assessment": "...",
  "plan": "...",
  "full_note": "SUBJECTIVE:\\n...\\n\\nOBJECTIVE:\\n...\\n\\nASSESSMENT:\\n...\\n\\nPLAN:\\n..."
}"""


async def draft_clinical_note(
    physician_summary: str,
    patient_info: dict,
    intake_data: dict | None = None,
) -> dict:
    """
    Draft a SOAP clinical note from the physician's post-visit summary.

    Args:
        physician_summary: Physician's free-text description of the visit
        patient_info: Patient demographics and history for context
        intake_data: Pre-visit intake data for Subjective section

    Returns:
        Dict with subjective, objective, assessment, plan, full_note
    """
    context = f"""
Patient: {patient_info.get('name')}, DOB: {patient_info.get('date_of_birth', 'Unknown')}
Visit date: {patient_info.get('appointment_date', 'Unknown')}

Known medical history:
- Conditions: {', '.join(patient_info.get('chronic_conditions', [])) or 'None on file'}
- Medications: {json.dumps(patient_info.get('current_medications', [])) or 'None on file'}
- Allergies: {json.dumps(patient_info.get('allergies', [])) or 'NKDA'}

Pre-visit intake (patient-reported):
{f"Chief complaint: {intake_data.get('chief_complaint')}" if intake_data else "No intake data available"}
{f"Duration: {intake_data.get('duration')}" if intake_data else ""}
{f"Severity: {intake_data.get('severity')}/10" if intake_data else ""}

Physician's post-visit summary:
{physician_summary}

Draft the SOAP note now.
"""

    response = client.messages.create(
        model=MODEL,
        max_tokens=2000,
        system=NOTE_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": context}],
    )

    response_text = response.content[0].text

    # Parse the JSON response
    try:
        # Find JSON block
        json_match = re.search(r'\{[\s\S]*"subjective"[\s\S]*\}', response_text)
        if json_match:
            return json.loads(json_match.group())
    except json.JSONDecodeError:
        pass

    # Fallback if JSON parsing fails
    return {
        "subjective": "See physician summary",
        "objective": "Not documented",
        "assessment": "See physician summary",
        "plan": "See physician summary",
        "full_note": f"PHYSICIAN SUMMARY:\n{physician_summary}\n\n[AI note drafting failed — manual entry required]",
    }
