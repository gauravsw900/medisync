/**
 * Login and Register pages.
 */

import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import useAuthStore from '../../store/authStore'

function FormInput({ label, type = 'text', value, onChange, placeholder, required = true }) {
  return (
    <div>
      <label className="block text-sm font-medium text-ink mb-1.5">{label}</label>
      <input
        type={type}
        value={value}
        onChange={e => onChange(e.target.value)}
        placeholder={placeholder}
        required={required}
        className="w-full border border-border rounded-md px-3 py-2.5 text-sm text-ink placeholder:text-muted focus:outline-none focus:border-primary-500 focus:ring-1 focus:ring-primary-500"
      />
    </div>
  )
}

export function LoginPage() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const { login, isLoading, error } = useAuthStore()
  const navigate = useNavigate()

  const handleSubmit = async (e) => {
    e.preventDefault()
    try {
      const user = await login(email, password)
      // Redirect based on role
      const redirects = { patient: '/patient/dashboard', physician: '/doctor/dashboard', admin: '/admin/dashboard' }
      navigate(redirects[user.role] || '/')
    } catch {}
  }

  return (
    <div className="min-h-screen bg-surface flex items-center justify-center px-4">
      <div className="w-full max-w-sm">
        {/* Logo */}
        <div className="text-center mb-8">
          <div className="w-10 h-10 bg-primary-600 rounded-xl flex items-center justify-center mx-auto mb-3">
            <span className="text-white font-bold">M</span>
          </div>
          <h1 className="text-xl font-semibold text-ink">Sign in to MediSync</h1>
          <p className="text-sm text-muted mt-1">Primary care management platform</p>
        </div>

        <form onSubmit={handleSubmit} className="bg-white border border-border rounded-xl p-6 space-y-4">
          <FormInput label="Email" type="email" value={email} onChange={setEmail} placeholder="you@example.com" />
          <FormInput label="Password" type="password" value={password} onChange={setPassword} placeholder="••••••••" />

          {error && (
            <p className="text-sm text-danger-text bg-danger-bg border border-danger-border rounded-md px-3 py-2">
              {error}
            </p>
          )}

          <button
            type="submit"
            disabled={isLoading}
            className="w-full bg-primary-600 text-white rounded-md py-2.5 text-sm font-medium hover:bg-primary-700 transition-colors disabled:opacity-50"
          >
            {isLoading ? 'Signing in...' : 'Sign in'}
          </button>
        </form>

        <p className="text-center text-sm text-muted mt-4">
          Don't have an account?{' '}
          <Link to="/register" className="text-primary-600 hover:underline font-medium">Create one</Link>
        </p>

        {/* Demo credentials */}
        <div className="mt-6 p-4 bg-white border border-border rounded-xl text-xs text-muted space-y-1">
          <p className="font-medium text-ink mb-2">Demo accounts</p>
          <p>Patient: john.doe@email.com / Patient123!</p>
          <p>Doctor:  dr.smith@medisync.com / Doctor123!</p>
          <p>Admin:   admin@medisync.com / Admin123!</p>
        </div>
      </div>
    </div>
  )
}

export function RegisterPage() {
  const [form, setForm] = useState({ email: '', password: '', first_name: '', last_name: '', role: 'patient', phone: '' })
  const { register, isLoading, error } = useAuthStore()
  const navigate = useNavigate()

  const set = (field) => (value) => setForm(prev => ({ ...prev, [field]: value }))

  const handleSubmit = async (e) => {
    e.preventDefault()
    try {
      const user = await register(form)
      const redirects = { patient: '/patient/dashboard', physician: '/doctor/dashboard', admin: '/admin/dashboard' }
      navigate(redirects[user.role] || '/')
    } catch {}
  }

  return (
    <div className="min-h-screen bg-surface flex items-center justify-center px-4 py-8">
      <div className="w-full max-w-sm">
        <div className="text-center mb-8">
          <div className="w-10 h-10 bg-primary-600 rounded-xl flex items-center justify-center mx-auto mb-3">
            <span className="text-white font-bold">M</span>
          </div>
          <h1 className="text-xl font-semibold text-ink">Create your account</h1>
        </div>

        <form onSubmit={handleSubmit} className="bg-white border border-border rounded-xl p-6 space-y-4">
          <div className="grid grid-cols-2 gap-3">
            <FormInput label="First name" value={form.first_name} onChange={set('first_name')} placeholder="John" />
            <FormInput label="Last name" value={form.last_name} onChange={set('last_name')} placeholder="Doe" />
          </div>
          <FormInput label="Email" type="email" value={form.email} onChange={set('email')} placeholder="you@example.com" />
          <FormInput label="Password" type="password" value={form.password} onChange={set('password')} placeholder="Min 8 chars, 1 uppercase, 1 number" />
          <FormInput label="Phone" type="tel" value={form.phone} onChange={set('phone')} placeholder="555-000-0000" required={false} />

          <div>
            <label className="block text-sm font-medium text-ink mb-1.5">I am a</label>
            <select
              value={form.role}
              onChange={e => setForm(p => ({ ...p, role: e.target.value }))}
              className="w-full border border-border rounded-md px-3 py-2.5 text-sm text-ink focus:outline-none focus:border-primary-500"
            >
              <option value="patient">Patient</option>
              <option value="physician">Physician</option>
            </select>
          </div>

          {error && (
            <p className="text-sm text-danger-text bg-danger-bg border border-danger-border rounded-md px-3 py-2">{error}</p>
          )}

          <button
            type="submit"
            disabled={isLoading}
            className="w-full bg-primary-600 text-white rounded-md py-2.5 text-sm font-medium hover:bg-primary-700 transition-colors disabled:opacity-50"
          >
            {isLoading ? 'Creating account...' : 'Create account'}
          </button>
        </form>

        <p className="text-center text-sm text-muted mt-4">
          Already have an account?{' '}
          <Link to="/login" className="text-primary-600 hover:underline font-medium">Sign in</Link>
        </p>
      </div>
    </div>
  )
}
