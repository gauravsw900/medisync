/**
 * Physician-facing pages:
 * - Dashboard: today's appointments with AI briefs
 * - Appointment detail: view intake brief, draft note
 * - Note review: approve or amend AI-drafted SOAP note
 */

import { useState, useEffect } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { api } from '../../utils/api'
import { Layout, Card, Badge, Button, LoadingSpinner } from '../shared/Layout'
import useAuthStore from '../../store/authStore'

// ── Physician Dashboard ────────────────────────────────────────────────────────

export function DoctorDashboard() {
  const { user } = useAuthStore()
  const [dashboard, setDashboard] = useState(null)
  const [loading, setLoading] = useState(true)
  const navigate = useNavigate()

  useEffect(() => {
    api.get('/physicians/dashboard').then(setDashboard).finally(() => setLoading(false))
  }, [])

  if (loading) return <Layout><LoadingSpinner /></Layout>

  return (
    <Layout>
      <div className="mb-6">
        <h1 className="text-xl font-semibold text-ink">Good morning, Dr. {user?.last_name}</h1>
        <p className="text-sm text-muted mt-1">{new Date().toLocaleDateString('en-US', { weekday: 'long', month: 'long', day: 'numeric' })}</p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-3 gap-4 mb-6">
        <Card>
          <p className="text-2xl font-semibold text-ink">{dashboard?.today_appointments?.length ?? 0}</p>
          <p className="text-sm text-muted mt-1">Appointments today</p>
        </Card>
        <Card>
          <p className="text-2xl font-semibold text-ink">{dashboard?.pending_notes ?? 0}</p>
          <p className="text-sm text-muted mt-1">Notes awaiting review</p>
        </Card>
        <Card>
          <p className="text-2xl font-semibold text-ink">{dashboard?.total_patients ?? 0}</p>
          <p className="text-sm text-muted mt-1">Total patients</p>
        </Card>
      </div>

      {/* Today's appointments */}
      <Card>
        <h2 className="font-medium text-ink mb-4">Today's schedule</h2>
        {!dashboard?.today_appointments?.length ? (
          <p className="text-muted text-sm text-center py-8">No appointments scheduled for today.</p>
        ) : (
          <div className="space-y-3">
            {dashboard.today_appointments.map(appt => (
              <div key={appt.id} className="flex items-center justify-between p-4 border border-border rounded-lg hover:bg-surface transition-colors">
                <div className="flex items-center gap-4">
                  {/* Time */}
                  <div className="text-center w-14">
                    <p className="font-semibold text-ink text-sm">{appt.appointment_time}</p>
                    <p className="text-xs text-muted">{appt.visit_type}</p>
                  </div>
                  <div className="w-px h-10 bg-border" />
                  {/* Patient info */}
                  <div>
                    <p className="font-medium text-sm text-ink">{appt.reason_for_visit || 'General visit'}</p>
                    <div className="flex gap-2 mt-1">
                      {appt.has_intake
                        ? <Badge variant="success">Intake complete</Badge>
                        : <Badge variant="warning">Awaiting intake</Badge>
                      }
                      {appt.has_note
                        ? <Badge variant="default">Note drafted</Badge>
                        : null
                      }
                    </div>
                  </div>
                </div>
                <Button onClick={() => navigate(`/doctor/appointment/${appt.id}`)} variant="secondary">
                  View
                </Button>
              </div>
            ))}
          </div>
        )}
      </Card>
    </Layout>
  )
}

// ── Appointment Detail ─────────────────────────────────────────────────────────

export function AppointmentDetail() {
  const { appointmentId } = useParams()
  const [appointment, setAppointment] = useState(null)
  const [intake, setIntake] = useState(null)
  const [note, setNote] = useState(null)
  const [loading, setLoading] = useState(true)
  const [summary, setSummary] = useState('')
  const [generatingNote, setGeneratingNote] = useState(false)
  const navigate = useNavigate()

  useEffect(() => {
    const load = async () => {
      try {
        const [appt, intakeData] = await Promise.all([
          api.get(`/appointments/${appointmentId}`),
          api.get(`/intake/${appointmentId}`).catch(() => null),
        ])
        setAppointment(appt)
        setIntake(intakeData)

        if (appt.has_note) {
          const noteData = await api.get(`/notes/${appointmentId}`).catch(() => null)
          setNote(noteData)
        }
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [appointmentId])

  const handleGenerateNote = async () => {
    if (!summary.trim()) return
    setGeneratingNote(true)
    try {
      const noteData = await api.post(`/notes/${appointmentId}/generate`, { physician_summary: summary })
      setNote(noteData)
    } catch (err) {
      alert(err.message)
    } finally {
      setGeneratingNote(false)
    }
  }

  if (loading) return <Layout><LoadingSpinner /></Layout>

  return (
    <Layout>
      <Button onClick={() => navigate('/doctor/dashboard')} variant="secondary" className="mb-4">← Back</Button>

      <div className="grid grid-cols-2 gap-5">
        {/* Left: Intake brief */}
        <div className="space-y-4">
          <Card>
            <h2 className="font-medium text-ink mb-3">Appointment</h2>
            <div className="space-y-2 text-sm">
              <div className="flex gap-3"><span className="text-muted w-24">Date</span><span className="text-ink">{appointment?.appointment_date} at {appointment?.appointment_time}</span></div>
              <div className="flex gap-3"><span className="text-muted w-24">Type</span><span className="text-ink capitalize">{appointment?.visit_type}</span></div>
              <div className="flex gap-3"><span className="text-muted w-24">Reason</span><span className="text-ink">{appointment?.reason_for_visit || 'Not specified'}</span></div>
            </div>
          </Card>

          {intake?.ai_brief ? (
            <Card>
              <div className="flex items-center justify-between mb-3">
                <h2 className="font-medium text-ink">AI-generated physician brief</h2>
                <Badge variant="warning">AI generated</Badge>
              </div>
              <pre className="text-xs text-ink leading-relaxed whitespace-pre-wrap font-sans">
                {intake.ai_brief}
              </pre>
            </Card>
          ) : (
            <Card>
              <p className="text-muted text-sm">Patient has not completed pre-visit intake yet.</p>
            </Card>
          )}
        </div>

        {/* Right: Clinical note */}
        <div>
          {note ? (
            <NoteReview note={note} appointmentId={appointmentId} onApproved={setNote} />
          ) : (
            <Card>
              <h2 className="font-medium text-ink mb-3">Draft clinical note</h2>
              <p className="text-sm text-muted mb-3">
                Summarise the visit and the AI will draft a full SOAP note for your review.
              </p>
              <textarea
                value={summary}
                onChange={e => setSummary(e.target.value)}
                placeholder="E.g. Patient presented with 3-day history of productive cough and low-grade fever. On exam: temp 37.8C, crackles in right lower lobe. CXR ordered — pending. Likely community-acquired pneumonia. Starting amoxicillin 500mg TID x 7 days. F/u in 1 week or sooner if worsening."
                rows={8}
                className="w-full border border-border rounded-md px-3 py-2.5 text-sm text-ink placeholder:text-muted focus:outline-none focus:border-primary-500 resize-none mb-3"
              />
              <Button onClick={handleGenerateNote} disabled={!summary.trim() || generatingNote}>
                {generatingNote ? 'Generating SOAP note...' : 'Generate SOAP note with AI'}
              </Button>
            </Card>
          )}
        </div>
      </div>
    </Layout>
  )
}

// ── Note Review ────────────────────────────────────────────────────────────────

function NoteReview({ note, appointmentId, onApproved }) {
  const [editing, setEditing] = useState({ subjective: note.subjective, objective: note.objective, assessment: note.assessment, plan: note.plan })
  const [amendments, setAmendments] = useState('')
  const [approving, setApproving] = useState(false)

  const handleApprove = async () => {
    setApproving(true)
    try {
      const approved = await api.post(`/notes/${note.id}/approve`, {
        amendments: amendments || undefined,
        ...editing,
      })
      onApproved(approved)
    } catch (err) {
      alert(err.message)
      setApproving(false)
    }
  }

  const soapSections = [
    { key: 'subjective', label: 'S — Subjective' },
    { key: 'objective', label: 'O — Objective' },
    { key: 'assessment', label: 'A — Assessment' },
    { key: 'plan', label: 'P — Plan' },
  ]

  if (note.status === 'approved') {
    return (
      <Card>
        <div className="flex items-center justify-between mb-4">
          <h2 className="font-medium text-ink">Clinical note</h2>
          <Badge variant="success">Approved ✓</Badge>
        </div>
        {soapSections.map(s => (
          <div key={s.key} className="mb-4">
            <p className="text-xs font-semibold text-muted uppercase tracking-wide mb-1">{s.label}</p>
            <p className="text-sm text-ink leading-relaxed">{note[s.key]}</p>
          </div>
        ))}
        {note.physician_amendments && (
          <div className="mt-3 pt-3 border-t border-border">
            <p className="text-xs text-muted">Physician amendments: {note.physician_amendments}</p>
          </div>
        )}
      </Card>
    )
  }

  return (
    <Card>
      <div className="flex items-center justify-between mb-4">
        <h2 className="font-medium text-ink">Review AI-drafted note</h2>
        <Badge variant="warning">Awaiting your approval</Badge>
      </div>
      <p className="text-xs text-muted mb-4">Edit any section below before approving. Your signature confirms this is accurate.</p>

      {soapSections.map(s => (
        <div key={s.key} className="mb-3">
          <label className="text-xs font-semibold text-muted uppercase tracking-wide block mb-1">{s.label}</label>
          <textarea
            value={editing[s.key] || ''}
            onChange={e => setEditing(prev => ({ ...prev, [s.key]: e.target.value }))}
            rows={3}
            className="w-full border border-border rounded-md px-3 py-2 text-sm text-ink focus:outline-none focus:border-primary-500 resize-none"
          />
        </div>
      ))}

      <div className="mb-4">
        <label className="text-xs font-medium text-muted block mb-1">Note any amendments made (optional)</label>
        <input
          value={amendments}
          onChange={e => setAmendments(e.target.value)}
          placeholder="e.g. Corrected diagnosis, updated medication dose"
          className="w-full border border-border rounded-md px-3 py-2 text-sm text-ink focus:outline-none focus:border-primary-500"
        />
      </div>

      <Button onClick={handleApprove} disabled={approving}>
        {approving ? 'Approving...' : 'Approve and sign note'}
      </Button>
    </Card>
  )
}
