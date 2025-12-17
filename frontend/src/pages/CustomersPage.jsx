import { useEffect, useState } from 'react'
import { fetchCustomers, createCustomer, generateInvoice } from '../api/adminApi'

export default function CustomersPage() {
  const [customers, setCustomers] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [form, setForm] = useState({ name: '', phone: '', email: '', location: '', initial_reading: '' })
  const [submitting, setSubmitting] = useState(false)

  useEffect(() => {
    fetchCustomers()
      .then((res) => {
        setCustomers(res)
        setLoading(false)
      })
      .catch((err) => {
        setError(err.message)
        setLoading(false)
      })
  }, [])

  const handleChange = (e) => {
    const { name, value } = e.target
    setForm((prev) => ({ ...prev, [name]: value }))
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setSubmitting(true)
    try {
      const payload = {
        name: form.name,
        phone: form.phone || null,
        email: form.email || null,
        location: form.location || null,
        initial_reading: form.initial_reading ? parseFloat(form.initial_reading) : null,
      }
      const created = await createCustomer(payload)
      setCustomers((prev) => [...prev, created])
      setForm({ name: '', phone: '', email: '', location: '', initial_reading: '' })
    } catch (err) {
      setError(err.message)
    } finally {
      setSubmitting(false)
    }
  }

  const handleGenerateInvoice = async (customerId) => {
    try {
      await generateInvoice(customerId)
      alert('Invoice generated and notification sent (if configured).')
    } catch (err) {
      alert(`Failed to generate invoice: ${err.message}`)
    }
  }

  // Helper to get customer ID (supports both 'id' and 'account_number')
  const getCustomerId = (c) => c.id || c.account_number

  // Helper to format balance
  const formatBalance = (balance) => {
    if (balance === undefined || balance === null) return '-'
    return typeof balance === 'number' ? `KES ${balance.toLocaleString()}` : balance
  }

  // Helper to get status class
  const getStatusClass = (status) => {
    if (!status) return ''
    const s = status.toUpperCase()
    if (s === 'ACTIVE') return 'status--active'
    if (s === 'INACTIVE') return 'status--inactive'
    if (s === 'SUSPENDED') return 'status--suspended'
    return ''
  }

  return (
    <div>
      <div className="page-header">
        <div>
          <h2 className="page-title">Customers</h2>
          <p className="page-description">Manage customer records and initial meter readings</p>
        </div>
      </div>

      <form onSubmit={handleSubmit} style={{ display: 'grid', gap: '0.5rem', gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))' }}>
        <input
          className="input"
          name="name"
          placeholder="Customer name"
          value={form.name}
          onChange={handleChange}
          required
        />
        <input className="input" name="phone" placeholder="Phone" value={form.phone} onChange={handleChange} />
        <input className="input" name="email" placeholder="Email" value={form.email} onChange={handleChange} />
        <input className="input" name="location" placeholder="Location" value={form.location} onChange={handleChange} />
        <input
          className="input"
          name="initial_reading"
          placeholder="Initial reading (m³)"
          value={form.initial_reading}
          onChange={handleChange}
          type="number"
          step="0.01"
        />
        <button className="button" type="submit" disabled={submitting}>
          {submitting ? 'Saving...' : 'Add Customer'}
        </button>
      </form>

      {loading && <div>Loading customers...</div>}
      {error && <div style={{ color: '#dc3545', marginTop: '0.5rem' }}>Error: {error}</div>}

      {!loading && customers.length > 0 && (
        <div className="table-wrapper" style={{ marginTop: '1rem' }}>
          <table>
            <thead>
              <tr>
                <th>Acct #</th>
                <th>Name</th>
                <th>Type</th>
                <th>Phone</th>
                <th>Location</th>
                <th>Meter #</th>
                <th>Status</th>
                <th>Balance</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {customers.map((c) => (
                <tr key={getCustomerId(c)}>
                  <td>#{c.account_number || c.id}</td>
                  <td>{c.name}</td>
                  <td>{c.customer_type || '-'}</td>
                  <td>{c.phone || '-'}</td>
                  <td>{c.location || '-'}</td>
                  <td>{c.meter_number || '-'}</td>
                  <td>
                    <span className={`status-badge ${getStatusClass(c.status)}`}>
                      {c.status || 'N/A'}
                    </span>
                  </td>
                  <td>{formatBalance(c.balance)}</td>
                  <td>
                    <button
                      type="button"
                      className="button button--small button--ghost"
                      onClick={() => handleGenerateInvoice(getCustomerId(c))}
                    >
                      Generate Invoice
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {!loading && customers.length === 0 && !error && (
        <div style={{ marginTop: '1rem', textAlign: 'center', color: '#666' }}>
          No customers found. Add your first customer above.
        </div>
      )}

      <style>{`
        .status-badge {
          display: inline-block;
          padding: 0.25rem 0.5rem;
          border-radius: 4px;
          font-size: 0.75rem;
          font-weight: 500;
          background: #e0e0e0;
          color: #333;
        }
        .status--active {
          background: #d4edda;
          color: #155724;
        }
        .status--inactive {
          background: #fff3cd;
          color: #856404;
        }
        .status--suspended {
          background: #f8d7da;
          color: #721c24;
        }
      `}</style>
    </div>
  )
}
