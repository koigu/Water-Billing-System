import { useEffect, useState } from 'react'
import { bulkSendReminders, fetchInvoices, payInvoice, sendInvoiceReminder } from '../api/adminApi'

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
  const [selectedInvoiceIds, setSelectedInvoiceIds] = useState([])
  const [actionMessage, setActionMessage] = useState('')
  const [bulkSending, setBulkSending] = useState(false)

  const loadInvoices = async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await fetchInvoices()
      setInvoices(res)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadInvoices()
  }, [])

  useEffect(() => {
    const validIds = new Set(invoices.map((inv) => inv.id))
    setSelectedInvoiceIds((prev) => prev.filter((id) => validIds.has(id)))
  }, [invoices])

  const handlePay = async (id) => {
    setActionMessage('')
    setError(null)
    try {
      const paid = await payInvoice(id)
      setInvoices((prev) => prev.map((inv) => (inv.id === id ? { ...inv, ...paid, status: 'paid' } : inv)))
      setActionMessage(`Invoice #${id} marked as paid.`)
    } catch (err) {
      setError(`Failed to mark invoice as paid: ${err.message}`)
    }
  }

  const handleSendReminder = async (id) => {
    setActionMessage('')
    setError(null)
    try {
      const result = await sendInvoiceReminder(id)
      const updated = result.invoice
      if (updated) {
        setInvoices((prev) => prev.map((inv) => (inv.id === id ? { ...inv, ...updated } : inv)))
      }
      setActionMessage(`Reminder processed for invoice #${id}.`)
    } catch (err) {
      setError(`Failed to send reminder: ${err.message}`)
    }
  }

  const handleToggleInvoice = (invoiceId) => {
    setSelectedInvoiceIds((prev) =>
      prev.includes(invoiceId) ? prev.filter((id) => id !== invoiceId) : [...prev, invoiceId]
    )
  }

  const allSelected = invoices.length > 0 && selectedInvoiceIds.length === invoices.length

  const handleToggleSelectAll = () => {
    if (allSelected) {
      setSelectedInvoiceIds([])
      return
    }
    setSelectedInvoiceIds(invoices.map((inv) => inv.id))
  }

  const handleBulkSendReminders = async () => {
    if (selectedInvoiceIds.length === 0) {
      return
    }
    setBulkSending(true)
    setActionMessage('')
    setError(null)
    try {
      const result = await bulkSendReminders(selectedInvoiceIds)
      setActionMessage(
        `Bulk reminders complete: ${result.sent_count || 0} sent, ${result.failed_count || 0} failed.`
      )
      await loadInvoices()
      setSelectedInvoiceIds([])
    } catch (err) {
      setError(`Failed to send bulk reminders: ${err.message}`)
    } finally {
      setBulkSending(false)
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

      {selectedInvoiceIds.length > 0 && (
        <div style={{ marginBottom: '0.75rem', display: 'flex', gap: '0.75rem', alignItems: 'center' }}>
          <strong>{selectedInvoiceIds.length} selected</strong>
          <button className="button" type="button" onClick={handleBulkSendReminders} disabled={bulkSending}>
            {bulkSending ? 'Sending...' : 'Send Reminders'}
          </button>
        </div>
      )}

      {loading && <div>Loading invoices...</div>}
      {error && <div style={{ color: '#dc3545' }}>Error: {error}</div>}
      {actionMessage && <div style={{ color: '#0f5132' }}>{actionMessage}</div>}

      {!loading && invoices.length > 0 && (
        <div className="table-wrapper">
          <table>
            <thead>
              <tr>
                <th>
                  <input type="checkbox" checked={allSelected} onChange={handleToggleSelectAll} />
                </th>
                <th>ID</th>
                <th>Customer ID</th>
                <th>Amount</th>
                <th>Due Date</th>
                <th>Status</th>
                <th>Reminder Sent</th>
                <th>Location</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {invoices.map((inv) => (
                <tr key={inv.id}>
                  <td>
                    <input
                      type="checkbox"
                      checked={selectedInvoiceIds.includes(inv.id)}
                      onChange={() => handleToggleInvoice(inv.id)}
                    />
                  </td>
                  <td>{inv.id}</td>
                  <td>{inv.customer_id}</td>
                  <td>{Number(inv.amount || 0).toFixed(2)} KES</td>
                  <td>{inv.due_date ? new Date(inv.due_date).toLocaleDateString() : '-'}</td>
                  <td>
                    <StatusBadge status={inv.status} />
                  </td>
                  <td>{inv.reminder_sent_at ? new Date(inv.reminder_sent_at).toLocaleString() : 'No'}</td>
                  <td>{inv.location || '-'}</td>
                  <td style={{ display: 'flex', gap: '0.4rem', flexWrap: 'wrap' }}>
                    {inv.status !== 'paid' && (
                      <button type="button" className="button button--small button--ghost" onClick={() => handlePay(inv.id)}>
                        Mark Paid
                      </button>
                    )}
                    <button
                      type="button"
                      className="button button--small button--ghost"
                      onClick={() => handleSendReminder(inv.id)}
                    >
                      Send Reminder
                    </button>
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
