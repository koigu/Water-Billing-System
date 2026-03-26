import { useEffect, useMemo, useState } from 'react'
import { addReading, fetchCustomers, fetchReadings } from '../api/adminApi'

export default function ReadingsPage() {
  const [readings, setReadings] = useState([])
  const [customers, setCustomers] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [message, setMessage] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [form, setForm] = useState({ customer_id: '', reading_value: '' })
  const [filters, setFilters] = useState({
    customer_id: '',
    date_from: '',
    date_to: '',
  })
  const monthLabels = useMemo(
    () => [
      'January',
      'February',
      'March',
      'April',
      'May',
      'June',
      'July',
      'August',
      'September',
      'October',
      'November',
      'December',
    ],
    []
  )

  const customerMap = useMemo(() => {
    const map = {}
    for (const c of customers) {
      const id = c.id || c.account_number
      map[id] = c.name || `Customer ${id}`
    }
    return map
  }, [customers])

  const filteredReadings = useMemo(() => {
    return readings.filter((r) => {
      const matchesCustomer =
        !filters.customer_id || String(r.customer_id) === String(filters.customer_id)
      if (!matchesCustomer) return false

      const recorded = new Date(r.recorded_at)

      if (filters.date_from) {
        const from = new Date(`${filters.date_from}T00:00:00`)
        if (recorded < from) return false
      }
      if (filters.date_to) {
        const to = new Date(`${filters.date_to}T23:59:59`)
        if (recorded > to) return false
      }

      return true
    })
  }, [readings, filters])

  const readingRows = useMemo(() => {
    const rows = new Map()
    const resolveMonthIndex = (reading) => {
      if (reading.reading_month) {
        const parsed = new Date(reading.reading_month)
        if (!Number.isNaN(parsed.getTime())) return parsed.getMonth()
      }
      if (reading.recorded_at) {
        const parsed = new Date(reading.recorded_at)
        if (!Number.isNaN(parsed.getTime())) return parsed.getMonth()
      }
      return null
    }

    for (const reading of filteredReadings) {
      const monthIndex = resolveMonthIndex(reading)
      if (monthIndex == null) continue

      const customerId = reading.customer_id
      if (!rows.has(customerId)) {
        rows.set(customerId, {
          customer_id: customerId,
          customer_name: customerMap[customerId] || 'Unknown',
          months: Array(12).fill('-'),
          monthDates: Array(12).fill(null),
        })
      }

      const row = rows.get(customerId)
      const recordedAt = reading.recorded_at ? new Date(reading.recorded_at).getTime() : null
      const currentDate = row.monthDates[monthIndex]
      const shouldReplace =
        currentDate == null || (recordedAt != null && recordedAt >= currentDate)

      if (shouldReplace) {
        row.months[monthIndex] = reading.reading_value ?? '-'
        row.monthDates[monthIndex] = recordedAt ?? currentDate ?? 0
      }
    }

    return Array.from(rows.values()).sort((a, b) => String(a.customer_id).localeCompare(String(b.customer_id)))
  }, [filteredReadings, customerMap])

  const loadData = async () => {
    setLoading(true)
    setError(null)
    try {
      const [readingsRes, customersRes] = await Promise.all([fetchReadings(), fetchCustomers()])
      setReadings(readingsRes)
      setCustomers(customersRes)
      if (!form.customer_id && customersRes.length > 0) {
        const firstId = customersRes[0].id || customersRes[0].account_number
        setForm((prev) => ({ ...prev, customer_id: String(firstId) }))
      }
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadData()
  }, [])

  const handleChange = (e) => {
    const { name, value } = e.target
    setForm((prev) => ({ ...prev, [name]: value }))
  }

  const handleFilterChange = (e) => {
    const { name, value } = e.target
    setFilters((prev) => ({ ...prev, [name]: value }))
  }

  const clearFilters = () => {
    setFilters({ customer_id: '', date_from: '', date_to: '' })
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setSubmitting(true)
    setError(null)
    setMessage('')
    try {
      const customerId = Number(form.customer_id)
      const hasReading = String(form.reading_value).trim() !== ''
      const readingValue = hasReading ? Number(form.reading_value) : null
      const result = await addReading(customerId, readingValue)
      setMessage(result?.message || (hasReading ? 'Reading recorded successfully.' : 'Reading marked as missing.'))
      setForm((prev) => ({ ...prev, reading_value: '' }))
      const readingsRes = await fetchReadings()
      setReadings(readingsRes)
    } catch (err) {
      setError(err.message)
    } finally {
      setSubmitting(false)
    }
  }

  const handleDownloadPdf = () => {
    window.print()
  }

  return (
    <div>
      <div className="page-header">
        <div>
          <h2 className="page-title">Meter Readings</h2>
          <p className="page-description">Record monthly meter readings and review status</p>
        </div>
        <button className="button button--ghost" type="button" onClick={handleDownloadPdf}>
          Download PDF
        </button>
      </div>

      <form
        onSubmit={handleSubmit}
        style={{ display: 'grid', gap: '0.5rem', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))' }}
      >
        <select className="input" name="customer_id" value={form.customer_id} onChange={handleChange} required>
          <option value="">Select customer</option>
          {customers.map((c) => {
            const id = c.id || c.account_number
            return (
              <option key={id} value={id}>
                #{id} - {c.name}
              </option>
            )
          })}
        </select>
        <input
          className="input"
          name="reading_value"
          type="number"
          step="0.01"
          min="0"
          value={form.reading_value}
          onChange={handleChange}
          placeholder="Reading value (leave blank if no reading)"
        />
        <button className="button" type="submit" disabled={submitting}>
          {submitting ? 'Saving...' : 'Record Reading'}
        </button>
      </form>

      <div
        style={{
          marginTop: '1rem',
          display: 'grid',
          gap: '0.5rem',
          gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))',
        }}
      >
        <select
          className="input"
          name="customer_id"
          value={filters.customer_id}
          onChange={handleFilterChange}
        >
          <option value="">All customers</option>
          {customers.map((c) => {
            const id = c.id || c.account_number
            return (
              <option key={id} value={id}>
                #{id} - {c.name}
              </option>
            )
          })}
        </select>
        <input
          className="input"
          name="date_from"
          type="date"
          value={filters.date_from}
          onChange={handleFilterChange}
        />
        <input
          className="input"
          name="date_to"
          type="date"
          value={filters.date_to}
          onChange={handleFilterChange}
        />
        <button className="button button--ghost" type="button" onClick={clearFilters}>
          Clear Filters
        </button>
      </div>

      {loading && <div>Loading readings...</div>}
      {error && <div style={{ color: '#dc3545', marginTop: '0.5rem' }}>Error: {error}</div>}
      {message && <div style={{ color: '#0f5132', marginTop: '0.5rem' }}>{message}</div>}

      {!loading && (
        <div style={{ marginTop: '0.75rem', color: '#666' }}>
          Showing {filteredReadings.length} of {readings.length} readings
        </div>
      )}

      {!loading && readingRows.length > 0 && (
        <div className="table-wrapper" style={{ marginTop: '1rem' }}>
          <table>
            <thead>
              <tr>
                <th>Customer ID</th>
                <th>Customer</th>
                {monthLabels.map((label) => (
                  <th key={label}>{label}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {readingRows.map((row) => (
                <tr key={row.customer_id}>
                  <td>{row.customer_id}</td>
                  <td>
                    #{row.customer_id} - {row.customer_name}
                  </td>
                  {row.months.map((value, index) => (
                    <td key={`${row.customer_id}-${monthLabels[index]}`}>{value}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {!loading && filteredReadings.length === 0 && !error && (
        <div style={{ marginTop: '1rem', textAlign: 'center', color: '#666' }}>
          No readings match the selected filters.
        </div>
      )}
    </div>
  )
}
