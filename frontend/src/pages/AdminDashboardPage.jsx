import { useState, useEffect } from 'react'
import {
  bulkGenerateInvoices,
  bulkSendReminders,
  fetchCustomers,
  fetchDashboard,
  fetchInvoices,
  fetchReadings,
} from '../api/adminApi'

export default function AdminDashboardPage() {
  const [data, setData] = useState(null)
  const [cycleData, setCycleData] = useState({
    cycleLabel: '',
    missingReadings: [],
    invoiceEligibleCustomerIds: [],
    overdueInvoiceIds: [],
  })
  const [loading, setLoading] = useState(true)
  const [runningGenerate, setRunningGenerate] = useState(false)
  const [runningReminders, setRunningReminders] = useState(false)
  const [actionMessage, setActionMessage] = useState('')
  const [error, setError] = useState(null)

  const getMonthKey = (dateLike) => {
    const d = new Date(dateLike)
    return `${d.getUTCFullYear()}-${String(d.getUTCMonth() + 1).padStart(2, '0')}`
  }

  const loadDashboard = async () => {
    setLoading(true)
    setError(null)
    try {
      const [dashboard, customers, readings, invoices] = await Promise.all([
        fetchDashboard(),
        fetchCustomers(),
        fetchReadings(),
        fetchInvoices(),
      ])
      setData(dashboard)

      const now = new Date()
      const cycleKey = getMonthKey(now)
      const cycleLabel = now.toLocaleDateString(undefined, { month: 'long', year: 'numeric' })

      const customerIdsWithCycleReading = new Set(
        readings
          .filter((r) => getMonthKey(r.recorded_at) === cycleKey)
          .map((r) => r.customer_id)
      )
      const missingReadings = customers.filter((c) => {
        const id = c.id || c.account_number
        return !customerIdsWithCycleReading.has(id)
      })

      const readingsByCustomer = new Map()
      for (const r of readings) {
        const list = readingsByCustomer.get(r.customer_id) || []
        list.push(r)
        readingsByCustomer.set(r.customer_id, list)
      }

      const customerIdsWithCycleInvoice = new Set(
        invoices
          .filter((inv) => {
            const created = inv.created_at || inv.billing_to || inv.due_date
            return created && getMonthKey(created) === cycleKey
          })
          .map((inv) => inv.customer_id)
      )

      const invoiceEligibleCustomerIds = customers
        .map((c) => c.id || c.account_number)
        .filter((id) => {
          const readingCount = (readingsByCustomer.get(id) || []).length
          return readingCount >= 2 && !customerIdsWithCycleInvoice.has(id)
        })

      const overdueInvoiceIds = invoices
        .filter((inv) => inv.status === 'overdue' && !inv.reminder_sent_at)
        .map((inv) => inv.id)

      setCycleData({
        cycleLabel,
        missingReadings,
        invoiceEligibleCustomerIds,
        overdueInvoiceIds,
      })
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadDashboard()
  }, [])

  const handleGenerateCycleInvoices = async () => {
    if (cycleData.invoiceEligibleCustomerIds.length === 0) {
      setActionMessage('No customers are currently eligible for invoice generation in this cycle.')
      return
    }
    setRunningGenerate(true)
    setActionMessage('')
    setError(null)
    try {
      const result = await bulkGenerateInvoices(cycleData.invoiceEligibleCustomerIds)
      setActionMessage(
        `Cycle invoice run complete: ${result.created_count || 0} created, ${result.failed_count || 0} failed.`
      )
      await loadDashboard()
    } catch (err) {
      setError(err.message)
    } finally {
      setRunningGenerate(false)
    }
  }

  const handleSendOverdueReminders = async () => {
    if (cycleData.overdueInvoiceIds.length === 0) {
      setActionMessage('No overdue invoices pending reminders.')
      return
    }
    setRunningReminders(true)
    setActionMessage('')
    setError(null)
    try {
      const result = await bulkSendReminders(cycleData.overdueInvoiceIds)
      setActionMessage(
        `Reminder run complete: ${result.sent_count || 0} sent, ${result.failed_count || 0} failed.`
      )
      await loadDashboard()
    } catch (err) {
      setError(err.message)
    } finally {
      setRunningReminders(false)
    }
  }

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

      <section className="cycle-ops">
        <div className="cycle-ops__head">
          <div>
            <h3 className="cycle-ops__title">Cycle Operations</h3>
            <p className="cycle-ops__subtitle">{cycleData.cycleLabel || 'Current cycle'}</p>
          </div>
          <button className="button button--ghost" type="button" onClick={loadDashboard}>
            Refresh
          </button>
        </div>
        <div className="cycle-ops__grid">
          <div className="cycle-ops__item">
            <span className="cycle-ops__label">Missing Readings</span>
            <strong className="cycle-ops__value">{cycleData.missingReadings.length}</strong>
          </div>
          <div className="cycle-ops__item">
            <span className="cycle-ops__label">Eligible For Invoice</span>
            <strong className="cycle-ops__value">{cycleData.invoiceEligibleCustomerIds.length}</strong>
          </div>
          <div className="cycle-ops__item">
            <span className="cycle-ops__label">Overdue Needing Reminder</span>
            <strong className="cycle-ops__value">{cycleData.overdueInvoiceIds.length}</strong>
          </div>
        </div>
        <div className="cycle-ops__actions">
          <button
            className="button"
            type="button"
            onClick={handleGenerateCycleInvoices}
            disabled={runningGenerate}
          >
            {runningGenerate ? 'Generating...' : 'Generate All Invoices For Cycle'}
          </button>
          <button
            className="button button--danger"
            type="button"
            onClick={handleSendOverdueReminders}
            disabled={runningReminders}
          >
            {runningReminders ? 'Sending...' : 'Send All Overdue Reminders'}
          </button>
        </div>
        {actionMessage && <div className="cycle-ops__message">{actionMessage}</div>}
      </section>

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
