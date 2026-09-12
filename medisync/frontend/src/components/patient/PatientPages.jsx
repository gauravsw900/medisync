/**
 * Patient-facing pages:
 * - Dashboard: upcoming appointments
 * - Book: find a physician and book a slot
 * - Intake: pre-visit AI symptom chat
 * - Profile: medical history management
 */

import { useState, useEffect, useRef } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { api } from '../../utils/api'
import { Layout, Card, Badge, Button, LoadingSpinner } from '../shared/Layout'
import useAuthStore from '../../store/authStore'

// ── Dashboard ─────────────────────────────────────────────────────────────────

export function PatientDashboard() {
  const { user } = useAuthStore()
  const [appointments, setAppointments] = useState([])
  const [loading, setLoading] = useState(true)
  const navigate = useNavigate()

  useEffect(() => {
    api.get('/appointments/my').then(setAppointments).finally(() => setLoading(false))
  }, [])

  const statusBadge = {
    scheduled:   <Badge variant="primary">Scheduled</Badge>,
    confirmed:   <Badge variant="success">Confirmed</Badge>,
    completed:   <Badge variant="default">Completed</Badge>,
    cancelled:   <Badge variant="danger">Cancelled</Badge>,
    in_progress: <Badge variant="warning">In progress</Badge>,
  }

  return (
    <Layout>
      <div className="mb-6">
        <h1 className="text-xl font-semibold text-ink">Welcome back, {user?.first_name}</h1>
        <p className="text-sm text-muted mt-1">Your upcoming appointments and health activity</p>
      </div>

      <div className="grid grid-cols-3 gap-4 mb-6">
        <Card>
          <p className="text-2xl font-semibold text-ink">{appointments.filter(a => a.status === 'scheduled').length}</p>
          <p className="text-sm text-muted mt-1">Upcoming appointments</p>
        </Card>
        <Card>
          <p className="text-2xl font-semibold text-ink">{appointments.filter(a => a.has_intake).length}</p>
          <p className="text-sm text-muted mt-1">Intakes completed</p>
        </Card>
        <Card>
          <p className="text-2xl font-semibold text-ink">{appointments.filter(a => a.status === 'completed').length}</p>
          <p className="text-sm text-muted mt-1">Past visits</p>
        </Card>
      </div>

      <Card>
        <div className="flex items-center justify-between mb-4">
          <h2 className="font-medium text-ink">Your appointments</h2>
          <Button onClick={() => navigate('/patient/book')}>Book appointment</Button>
        </div>

        {loading ? <LoadingSpinner /> : appointments.length === 0 ? (
          <div className="text-center py-10">
            <p className="text-muted text-sm">No appointments yet.</p>
            <Button onClick={() => navigate('/patient/book')} className="mt-3">Book your first appointment</Button>
          </div>
        ) : (
          <div className="space-y-3">
            {appointments.map(appt => (
              <div key={appt.id} className="flex items-center justify-between p-4 border border-border rounded-lg hover:bg-surface transition-colors">
                <div>
                  <p className="font-medium text-sm text-ink">{appt.appointment_date} at {appt.appointment_time}</p>
                  <p className="text-xs text-muted mt-0.5">{appt.reason_for_visit || 'General visit'} · {appt.visit_type}</p>
                </div>
                <div className="flex items-center gap-3">
                  {statusBadge[appt.status]}
                  {appt.status === 'scheduled' && !appt.has_intake && (
                    <Button onClick={() => navigate(`/patient/intake/${appt.id}`)} variant="secondary">
                      Complete intake
                    </Button>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </Card>
    </Layout>
  )
}

// ── Book Appointment ──────────────────────────────────────────────────────────

export function BookAppointment() {
  const [physicians, setPhysicians] = useState([])
  const [selectedPhysician, setSelectedPhysician] = useState(null)
  const [slots, setSlots] = useState([])
  const [selectedSlot, setSelectedSlot] = useState(null)
  const [reason, setReason] = useState('')
  const [loading, setLoading] = useState(true)
  const [booking, setBooking] = useState(false)
  const navigate = useNavigate()

  useEffect(() => {
    api.get('/physicians/').then(setPhysicians).finally(() => setLoading(false))
  }, [])

  useEffect(() => {
    if (selectedPhysician) {
      api.get(`/appointments/slots/${selectedPhysician.id}`).then(setSlots)
    }
  }, [selectedPhysician])

  const handleBook = async () => {
    if (!selectedSlot) return
    setBooking(true)
    try {
      const appt = await api.post('/appointments/book', {
        physician_id: selectedPhysician.user.id,
        slot_id: selectedSlot.id,
        appointment_date: selectedSlot.slot_date,
        appointment_time: selectedSlot.start_time,
        reason_for_visit: reason,
      })
      navigate(`/patient/intake/${appt.id}`)
    } catch (err) {
      alert(err.message)
      setBooking(false)
    }
  }

  // Group slots by date
  const slotsByDate = slots.reduce((acc, slot) => {
    if (!acc[slot.slot_date]) acc[slot.slot_date] = []
    acc[slot.slot_date].push(slot)
    return acc
  }, {})

  return (
    <Layout>
      <h1 className="text-xl font-semibold text-ink mb-6">Book an appointment</h1>

      {loading ? <LoadingSpinner /> : (
        <div className="grid grid-cols-3 gap-5">
          {/* Step 1: Choose physician */}
          <div className="col-span-1">
            <h2 className="text-sm font-medium text-ink mb-3">1. Choose a physician</h2>
            <div className="space-y-2">
              {physicians.map(p => (
                <button
                  key={p.id}
                  onClick={() => { setSelectedPhysician(p); setSelectedSlot(null) }}
                  className={`w-full text-left p-3 rounded-lg border transition-colors ${
                    selectedPhysician?.id === p.id
                      ? 'border-primary-500 bg-primary-50'
                      : 'border-border bg-white hover:border-primary-300'
                  }`}
                >
                  <p className="font-medium text-sm text-ink">{p.user.first_name} {p.user.last_name}</p>
                  <p className="text-xs text-muted mt-0.5">{p.specialty}</p>
                  {p.consultation_fee && (
                    <p className="text-xs text-muted mt-0.5">${p.consultation_fee}/visit</p>
                  )}
                </button>
              ))}
            </div>
          </div>

          {/* Step 2: Choose slot */}
          <div className="col-span-2">
            {selectedPhysician ? (
              <>
                <h2 className="text-sm font-medium text-ink mb-3">2. Choose a time slot</h2>
                {Object.keys(slotsByDate).length === 0 ? (
                  <p className="text-muted text-sm">No available slots for this physician.</p>
                ) : (
                  <div className="space-y-4 mb-5">
                    {Object.entries(slotsByDate).map(([date, dateSlots]) => (
                      <div key={date}>
                        <p className="text-xs font-medium text-muted mb-2">{date}</p>
                        <div className="flex flex-wrap gap-2">
                          {dateSlots.map(slot => (
                            <button
                              key={slot.id}
                              onClick={() => setSelectedSlot(slot)}
                              className={`px-3 py-1.5 text-sm rounded-md border transition-colors ${
                                selectedSlot?.id === slot.id
                                  ? 'border-primary-500 bg-primary-50 text-primary-700 font-medium'
                                  : 'border-border bg-white text-ink hover:border-primary-300'
                              }`}
                            >
                              {slot.start_time}
                            </button>
                          ))}
                        </div>
                      </div>
                    ))}
                  </div>
                )}

                {selectedSlot && (
                  <div className="border-t border-border pt-4">
                    <h2 className="text-sm font-medium text-ink mb-2">3. Reason for visit</h2>
                    <textarea
                      value={reason}
                      onChange={e => setReason(e.target.value)}
                      placeholder="Briefly describe why you're coming in..."
                      rows={3}
                      className="w-full border border-border rounded-md px-3 py-2 text-sm text-ink placeholder:text-muted focus:outline-none focus:border-primary-500 resize-none mb-4"
                    />
                    <Button onClick={handleBook} disabled={booking}>
                      {booking ? 'Booking...' : `Book for ${selectedSlot.slot_date} at ${selectedSlot.start_time}`}
                    </Button>
                  </div>
                )}
              </>
            ) : (
              <div className="flex items-center justify-center h-40 border border-dashed border-border rounded-lg">
                <p className="text-muted text-sm">Select a physician to see available times</p>
              </div>
            )}
          </div>
        </div>
      )}
    </Layout>
  )
}

// ── Pre-visit Intake Chat ─────────────────────────────────────────────────────

export function IntakeChat() {
  const { appointmentId } = useParams()
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [complete, setComplete] = useState(false)
  const [hasRedFlags, setHasRedFlags] = useState(false)
  const bottomRef = useRef(null)
  const navigate = useNavigate()

  // Opening message from the AI
  useEffect(() => {
    setMessages([{
      role: 'assistant',
      content: "Hello! I'm here to help prepare for your upcoming visit. Before you see your physician, I'd like to collect some information about what's bringing you in today. This helps your doctor be fully prepared. What's the main reason for your visit?"
    }])
  }, [])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  const sendMessage = async () => {
    if (!input.trim() || loading) return
    const userMsg = input.trim()
    setInput('')
    setMessages(prev => [...prev, { role: 'user', content: userMsg }])
    setLoading(true)

    try {
      const data = await api.post(`/intake/${appointmentId}/chat`, { message: userMsg })
      setMessages(prev => [...prev, { role: 'assistant', content: data.response }])
      if (data.is_complete) setComplete(true)
      if (data.has_red_flags) setHasRedFlags(true)
    } catch (err) {
      setMessages(prev => [...prev, { role: 'assistant', content: `Something went wrong: ${err.message}` }])
    } finally {
      setLoading(false)
    }
  }

  return (
    <Layout>
      <div className="max-w-2xl mx-auto">
        <div className="mb-4">
          <h1 className="text-lg font-semibold text-ink">Pre-visit intake</h1>
          <p className="text-sm text-muted">Your responses help your physician prepare for your visit</p>
        </div>

        {hasRedFlags && (
          <div className="mb-4 p-4 bg-danger-bg border border-danger-border rounded-lg">
            <p className="text-sm font-semibold text-danger-text">⚠ Emergency symptoms detected</p>
            <p className="text-sm text-danger-text mt-1">Based on your symptoms, please call 911 or go to your nearest Emergency Room immediately. Do not wait for your scheduled appointment.</p>
          </div>
        )}

        {/* Chat window */}
        <Card className="mb-3 p-0 overflow-hidden">
          <div className="h-96 overflow-y-auto p-4 space-y-3">
            {messages.map((msg, i) => (
              <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                <div className={`max-w-[80%] px-4 py-2.5 rounded-2xl text-sm leading-relaxed ${
                  msg.role === 'user'
                    ? 'bg-primary-600 text-white rounded-tr-sm'
                    : 'bg-surface border border-border text-ink rounded-tl-sm'
                }`}>
                  {msg.content}
                </div>
              </div>
            ))}
            {loading && (
              <div className="flex justify-start">
                <div className="bg-surface border border-border rounded-2xl rounded-tl-sm px-4 py-3">
                  <div className="flex gap-1">
                    {[0,1,2].map(i => (
                      <div key={i} className="w-1.5 h-1.5 rounded-full bg-muted animate-bounce" style={{ animationDelay: `${i * 0.15}s` }} />
                    ))}
                  </div>
                </div>
              </div>
            )}
            <div ref={bottomRef} />
          </div>

          {/* Input */}
          {!complete && (
            <div className="border-t border-border p-3 flex gap-2">
              <input
                value={input}
                onChange={e => setInput(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && !e.shiftKey && sendMessage()}
                placeholder="Type your response..."
                disabled={loading}
                className="flex-1 border border-border rounded-md px-3 py-2 text-sm text-ink placeholder:text-muted focus:outline-none focus:border-primary-500 disabled:opacity-50"
              />
              <Button onClick={sendMessage} disabled={!input.trim() || loading}>Send</Button>
            </div>
          )}
        </Card>

        {complete && (
          <div className="p-4 bg-success-bg border border-success-border rounded-lg text-center">
            <p className="font-medium text-success-text">Intake complete ✓</p>
            <p className="text-sm text-success-text mt-1 mb-3">Your physician brief has been generated. Your doctor will be well-prepared for your visit.</p>
            <Button onClick={() => navigate('/patient/dashboard')}>Back to dashboard</Button>
          </div>
        )}
      </div>
    </Layout>
  )
}
