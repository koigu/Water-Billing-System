import { useEffect, useState } from 'react'
import { fetchInvoices, payInvoice } from '../api/adminApi'

function StatusBadge({ status }) {
  const normalized = (status || '').toLowerCase()
  if (normalized === 'paid') return <span className="badge badge--success">Paid</span>
  if (normalized === 'overdue') return <span className="badge badge--danger">Overdue</span>
  return <span className="badge badge--warning">Pending</span>
}

export default function InvoicesPage() {
  const [invoices, setInvoices] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    fetchInvoices()
      .then((res) => {
        setInvoices(res)
        setLoading(false)
      })
      .catch((err) => {
        setError(err.message)
        setLoading(false)
      })
  }, [])

  const handlePay = async (id) => {
    try {
      const paid = await payInvoice(id)
      setInvoices((prev) => prev.map((inv) => (inv.id === id ? paid : inv)))
    } catch (err) {
      alert(`Failed to mark invoice as paid: ${err.message}`)
    }
  }

  return (
    <div>
      <div className="page-header">
        <div>
          <h2 className="page-title">Invoices</h2>
          <p className="page-description">Track billing status and payments</p>
        </div>
      </div>

      {loading && <div>Loading invoices...</div>}
      {error && <div style={{ color: '#dc3545' }}>Error: {error}</div>}

      {!loading && invoices.length > 0 && (
        <div className="table-wrapper">
          <table>
            <thead>
              <tr>
                <th>ID</th>
                <th>Customer ID</th>
                <th>Amount</th>
                <th>Due Date</th>
                <th>Status</th>
                <th>Location</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {invoices.map((inv) => (
                <tr key={inv.id}>
                  <td>{inv.id}</td>
                  <td>{inv.customer_id}</td>
                  <td>{inv.amount.toFixed(2)} KES</td>
                  <td>{new Date(inv.due_date).toLocaleDateString()}</td>
                  <td>
                    <StatusBadge status={inv.status} />
                  </td>
                  <td>{inv.location || '-'}</td>
                  <td>
                    {inv.status !== 'paid' && (
                      <button
                        type="button"
                        className="button button--small button--ghost"
                        onClick={() => handlePay(inv.id)}
                      >
                        Mark Paid
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
