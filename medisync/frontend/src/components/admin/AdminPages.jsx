/**
 * Admin dashboard — practice-wide statistics and user management.
 */

import { useState, useEffect } from 'react'
import { api } from '../../utils/api'
import { Layout, Card, LoadingSpinner } from '../shared/Layout'

export function AdminDashboard() {
  const [stats, setStats] = useState(null)
  const [users, setUsers] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    Promise.all([
      api.get('/admin/stats'),
      api.get('/admin/users'),
    ]).then(([s, u]) => { setStats(s); setUsers(u) }).finally(() => setLoading(false))
  }, [])

  const roleColour = { patient: 'text-blue-600 bg-blue-50', physician: 'text-green-700 bg-green-50', admin: 'text-purple-700 bg-purple-50' }

  if (loading) return <Layout><LoadingSpinner /></Layout>

  return (
    <Layout>
      <h1 className="text-xl font-semibold text-ink mb-6">Practice overview</h1>

      <div className="grid grid-cols-3 gap-4 mb-6">
        {[
          { label: 'Total patients', value: stats?.total_patients },
          { label: 'Physicians', value: stats?.total_physicians },
          { label: 'Appointments today', value: stats?.appointments_today },
          { label: 'Total appointments', value: stats?.total_appointments },
          { label: 'Notes pending review', value: stats?.pending_notes },
          { label: 'Completed intakes', value: stats?.completed_intakes },
        ].map(s => (
          <Card key={s.label}>
            <p className="text-2xl font-semibold text-ink">{s.value ?? 0}</p>
            <p className="text-sm text-muted mt-1">{s.label}</p>
          </Card>
        ))}
      </div>

      <Card>
        <h2 className="font-medium text-ink mb-4">All users</h2>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border">
                <th className="text-left py-2 text-xs font-medium text-muted uppercase tracking-wide">Name</th>
                <th className="text-left py-2 text-xs font-medium text-muted uppercase tracking-wide">Email</th>
                <th className="text-left py-2 text-xs font-medium text-muted uppercase tracking-wide">Role</th>
                <th className="text-left py-2 text-xs font-medium text-muted uppercase tracking-wide">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {users.map(u => (
                <tr key={u.id} className="hover:bg-surface">
                  <td className="py-3 font-medium text-ink">{u.name}</td>
                  <td className="py-3 text-muted">{u.email}</td>
                  <td className="py-3">
                    <span className={`text-xs font-medium px-2 py-0.5 rounded capitalize ${roleColour[u.role]}`}>{u.role}</span>
                  </td>
                  <td className="py-3">
                    <span className={`text-xs font-medium px-2 py-0.5 rounded ${u.is_active ? 'text-green-700 bg-green-50' : 'text-red-700 bg-red-50'}`}>
                      {u.is_active ? 'Active' : 'Inactive'}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </Layout>
  )
}
