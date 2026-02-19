import { useState, useEffect } from 'react'
import { fetchDashboard } from '../api/adminApi'

export default function AdminDashboardPage() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    fetchDashboard()
      .then((res) => {
        setData(res)
        setLoading(false)
      })
      .catch((err) => {
        setError(err.message)
        setLoading(false)
      })
  }, [])

  if (loading) return <div>Loading dashboard...</div>
  if (error) return <div style={{ color: '#dc3545' }}>Error: {error}</div>

  const {
    stats,
    rate,
    effective_rate,
    total_invoices,
    pending_invoices,
    overdue_invoices,
    total_readings,
  } = data || {}

  return (
    <div>
      <div className="page-header">
        <div>
          <h2 className="page-title">Dashboard</h2>
          <p className="page-description">Overview of system stats, customers, and invoices</p>
        </div>
      </div>

      <div className="card-grid">
        <div className="card">
          <div className="card__title">Total Customers</div>
          <div className="card__value">{stats?.total_customers || 0}</div>
        </div>

        <div className="card">
          <div className="card__title">Active Customers</div>
          <div className="card__value">{stats?.active_customers || 0}</div>
          <div className="card__meta">Last 90 days activity</div>
        </div>

        <div className="card">
          <div className="card__title">Total Water Usage</div>
          <div className="card__value">{stats?.total_water_usage || 0} m3</div>
          <div className="card__meta">Calculated from invoices</div>
        </div>

        <div className="card">
          <div className="card__title">Current Rate</div>
          <div className="card__value">{Number(effective_rate || 0).toFixed(2)} KES/m3</div>
          <div className="card__meta">
            Mode: {rate?.mode || '-'} | Value: {rate?.value ?? '-'}
          </div>
        </div>

        <div className="card">
          <div className="card__title">Total Readings</div>
          <div className="card__value">{total_readings || 0}</div>
          <div className="card__meta">All recorded meter readings</div>
        </div>

        <div className="card">
          <div className="card__title">Total Invoices</div>
          <div className="card__value">{total_invoices || 0}</div>
        </div>

        <div className="card">
          <div className="card__title">Pending Invoices</div>
          <div className="card__value">{pending_invoices || 0}</div>
          <div className="card__meta">
            <span className="badge badge--warning">Awaiting payment</span>
          </div>
        </div>

        <div className="card">
          <div className="card__title">Overdue Invoices</div>
          <div className="card__value">{overdue_invoices || 0}</div>
          <div className="card__meta">
            <span className="badge badge--danger">Action required</span>
          </div>
        </div>

        <div className="card">
          <div className="card__title">Inactive Customers</div>
          <div className="card__value">{stats?.inactive_customers || 0}</div>
          <div className="card__meta">No readings in 90 days</div>
        </div>
      </div>
    </div>
  )
}
