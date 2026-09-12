/**
 * App — routing and auth guards.
 *
 * Routes are protected by role — a patient can't access /doctor/* routes.
 * Unauthenticated users are redirected to /login.
 */

import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import useAuthStore from './store/authStore'
import { LoginPage, RegisterPage } from './components/auth/AuthPages'
import { PatientDashboard, BookAppointment, IntakeChat } from './components/patient/PatientPages'
import { DoctorDashboard, AppointmentDetail } from './components/doctor/DoctorPages'
import { AdminDashboard } from './components/admin/AdminPages'

// Protected route — redirects to login if not authenticated
function Protected({ children, role }) {
  const { user } = useAuthStore()
  if (!user) return <Navigate to="/login" replace />
  if (role && user.role !== role) return <Navigate to={`/${user.role === 'physician' ? 'doctor' : user.role}/dashboard`} replace />
  return children
}

export default function App() {
  const { user } = useAuthStore()

  // Redirect from root based on role
  const defaultPath = user
    ? user.role === 'physician' ? '/doctor/dashboard'
    : user.role === 'admin' ? '/admin/dashboard'
    : '/patient/dashboard'
    : '/login'

  return (
    <BrowserRouter>
      <Routes>
        {/* Public */}
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />

        {/* Patient routes */}
        <Route path="/patient/dashboard" element={<Protected role="patient"><PatientDashboard /></Protected>} />
        <Route path="/patient/book" element={<Protected role="patient"><BookAppointment /></Protected>} />
        <Route path="/patient/intake/:appointmentId" element={<Protected role="patient"><IntakeChat /></Protected>} />

        {/* Doctor routes */}
        <Route path="/doctor/dashboard" element={<Protected role="physician"><DoctorDashboard /></Protected>} />
        <Route path="/doctor/appointment/:appointmentId" element={<Protected role="physician"><AppointmentDetail /></Protected>} />

        {/* Admin routes */}
        <Route path="/admin/dashboard" element={<Protected role="admin"><AdminDashboard /></Protected>} />

        {/* Default redirect */}
        <Route path="*" element={<Navigate to={defaultPath} replace />} />
      </Routes>
    </BrowserRouter>
  )
}
