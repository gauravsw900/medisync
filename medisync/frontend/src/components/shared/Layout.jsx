/**
 * Shared layout — Navbar and page wrapper.
 */

import { Link, useNavigate, useLocation } from 'react-router-dom'
import clsx from 'clsx'
import useAuthStore from '../../store/authStore'

function NavLink({ to, children }) {
  const location = useLocation()
  const active = location.pathname.startsWith(to)
  return (
    <Link
      to={to}
      className={clsx(
        'px-3 py-2 rounded-md text-sm font-medium transition-colors',
        active
          ? 'bg-primary-50 text-primary-700'
          : 'text-muted hover:text-ink hover:bg-surface',
      )}
    >
      {children}
    </Link>
  )
}

export function Navbar() {
  const { user, logout } = useAuthStore()
  const navigate = useNavigate()

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  const navLinks = {
    patient: [
      { to: '/patient/dashboard', label: 'Dashboard' },
      { to: '/patient/book', label: 'Book appointment' },
      { to: '/patient/profile', label: 'My profile' },
    ],
    physician: [
      { to: '/doctor/dashboard', label: 'Dashboard' },
      { to: '/doctor/appointments', label: 'Appointments' },
    ],
    admin: [
      { to: '/admin/dashboard', label: 'Dashboard' },
      { to: '/admin/users', label: 'Users' },
    ],
  }

  const links = user ? (navLinks[user.role] || []) : []

  return (
    <nav className="bg-white border-b border-border sticky top-0 z-10">
      <div className="max-w-6xl mx-auto px-4 py-3 flex items-center justify-between">
        <div className="flex items-center gap-6">
          {/* Logo */}
          <Link to="/" className="flex items-center gap-2">
            <div className="w-7 h-7 bg-primary-600 rounded-lg flex items-center justify-center">
              <span className="text-white text-xs font-bold">M</span>
            </div>
            <span className="font-semibold text-ink text-sm">MediSync</span>
          </Link>

          {/* Nav links */}
          <div className="flex items-center gap-1">
            {links.map(l => <NavLink key={l.to} to={l.to}>{l.label}</NavLink>)}
          </div>
        </div>

        {/* User menu */}
        {user && (
          <div className="flex items-center gap-3">
            <span className="text-sm text-muted">
              {user.first_name} {user.last_name}
              <span className="ml-1.5 text-xs bg-primary-50 text-primary-700 px-1.5 py-0.5 rounded capitalize">
                {user.role}
              </span>
            </span>
            <button
              onClick={handleLogout}
              className="text-sm text-muted hover:text-ink border border-border rounded-md px-3 py-1.5 transition-colors"
            >
              Sign out
            </button>
          </div>
        )}
      </div>
    </nav>
  )
}

export function Layout({ children }) {
  return (
    <div className="min-h-screen bg-surface">
      <Navbar />
      <main className="max-w-6xl mx-auto px-4 py-6">
        {children}
      </main>
    </div>
  )
}

// Reusable UI primitives
export function Card({ children, className = '' }) {
  return (
    <div className={clsx('bg-white rounded-lg border border-border p-5', className)}>
      {children}
    </div>
  )
}

export function Badge({ children, variant = 'default' }) {
  const styles = {
    default: 'bg-surface text-muted border-border',
    success: 'bg-success-bg text-success-text border-success-border',
    warning: 'bg-warning-bg text-warning-text border-warning-border',
    danger:  'bg-danger-bg text-danger-text border-danger-border',
    primary: 'bg-primary-50 text-primary-700 border-primary-100',
  }
  return (
    <span className={clsx('text-xs font-medium px-2 py-0.5 rounded border', styles[variant])}>
      {children}
    </span>
  )
}

export function Button({ children, onClick, variant = 'primary', disabled = false, className = '', type = 'button' }) {
  const styles = {
    primary: 'bg-primary-600 text-white hover:bg-primary-700 border-transparent',
    secondary: 'bg-white text-ink hover:bg-surface border-border',
    danger: 'bg-danger-bg text-danger-text hover:opacity-90 border-danger-border',
  }
  return (
    <button
      type={type}
      onClick={onClick}
      disabled={disabled}
      className={clsx(
        'px-4 py-2 text-sm font-medium rounded-md border transition-colors',
        styles[variant],
        disabled && 'opacity-50 cursor-not-allowed',
        className,
      )}
    >
      {children}
    </button>
  )
}

export function LoadingSpinner() {
  return (
    <div className="flex items-center justify-center py-12">
      <div className="w-8 h-8 border-2 border-primary-200 border-t-primary-600 rounded-full animate-spin" />
    </div>
  )
}
