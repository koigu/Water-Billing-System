import { useEffect, useState } from 'react'
import {
  bulkDeleteCustomers,
  createCustomer,
  deleteCustomer,
  fetchCustomers,
  bulkGenerateInvoices,
  generateInvoice,
  updateCustomer,
} from '../api/adminApi'

const EMPTY_FORM = { name: '', phone: '', email: '', location: '', initial_reading: '' }
const EMPTY_EDIT_FORM = { name: '', phone: '', email: '', location: '' }

export default function CustomersPage() {
  const [customers, setCustomers] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [actionMessage, setActionMessage] = useState('')
  const [selectedCustomerIds, setSelectedCustomerIds] = useState([])
  const [form, setForm] = useState(EMPTY_FORM)
  const [submitting, setSubmitting] = useState(false)
  const [editId, setEditId] = useState(null)
  const [editForm, setEditForm] = useState(EMPTY_EDIT_FORM)
  const [viewCustomer, setViewCustomer] = useState(null)
  const [updating, setUpdating] = useState(false)
  const [bulkDeleting, setBulkDeleting] = useState(false)
  const [bulkGenerating, setBulkGenerating] = useState(false)

  const getCustomerId = (c) => c.id || c.account_number

  const loadCustomers = async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await fetchCustomers()
      setCustomers(res)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadCustomers()
  }, [])

  useEffect(() => {
    const validIds = new Set(customers.map((c) => getCustomerId(c)))
    setSelectedCustomerIds((prev) => prev.filter((id) => validIds.has(id)))
  }, [customers])

  const handleChange = (e) => {
    const { name, value } = e.target
    setForm((prev) => ({ ...prev, [name]: value }))
  }

  const handleEditChange = (e) => {
    const { name, value } = e.target
    setEditForm((prev) => ({ ...prev, [name]: value }))
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setSubmitting(true)
    setActionMessage('')
    setError(null)
    try {
      const payload = {
        name: form.name,
        phone: form.phone || null,
        email: form.email || null,
        location: form.location || null,
        initial_reading: form.initial_reading ? parseFloat(form.initial_reading) : null,
      }
      const created = await createCustomer(payload)
      setCustomers((prev) => [created, ...prev])
      setForm(EMPTY_FORM)
      setActionMessage('Customer added successfully.')
    } catch (err) {
      setError(err.message)
    } finally {
      setSubmitting(false)
    }
  }

  const handleOpenEdit = (customer) => {
    setViewCustomer(null)
    setEditId(getCustomerId(customer))
    setEditForm({
      name: customer.name || '',
      phone: customer.phone || '',
      email: customer.email || '',
      location: customer.location || '',
    })
    setActionMessage('')
    setError(null)
  }

  const handleCancelEdit = () => {
    setEditId(null)
    setEditForm(EMPTY_EDIT_FORM)
  }

  const handleViewCustomer = (customer) => {
    setEditId(null)
    setEditForm(EMPTY_EDIT_FORM)
    setViewCustomer(customer)
    setActionMessage('')
    setError(null)
  }

  const handleCloseView = () => {
    setViewCustomer(null)
  }

  const handleSaveEdit = async (e) => {
    e.preventDefault()
    if (!editId) {
      return
    }

    setUpdating(true)
    setActionMessage('')
    setError(null)
    try {
      const payload = {
        name: editForm.name || null,
        phone: editForm.phone || null,
        email: editForm.email || null,
        location: editForm.location || null,
      }
      const updated = await updateCustomer(editId, payload)
      setCustomers((prev) => prev.map((c) => (getCustomerId(c) === editId ? { ...c, ...updated } : c)))
      setActionMessage('Customer updated successfully.')
      handleCancelEdit()
    } catch (err) {
      setError(err.message)
    } finally {
      setUpdating(false)
    }
  }

  const handleDelete = async (customerId, customerName) => {
    const confirmed = window.confirm(`Delete customer "${customerName}" and related records?`)
    if (!confirmed) {
      return
    }
    setActionMessage('')
    setError(null)
    try {
      await deleteCustomer(customerId)
      setCustomers((prev) => prev.filter((c) => getCustomerId(c) !== customerId))
      setSelectedCustomerIds((prev) => prev.filter((id) => id !== customerId))
      setActionMessage('Customer deleted successfully.')
    } catch (err) {
      setError(err.message)
    }
  }

  const handleToggleCustomer = (customerId) => {
    setSelectedCustomerIds((prev) =>
      prev.includes(customerId) ? prev.filter((id) => id !== customerId) : [...prev, customerId]
    )
  }

  const allSelected = customers.length > 0 && selectedCustomerIds.length === customers.length

  const handleToggleSelectAll = () => {
    if (allSelected) {
      setSelectedCustomerIds([])
      return
    }
    setSelectedCustomerIds(customers.map((c) => getCustomerId(c)))
  }

  const handleBulkDelete = async () => {
    if (selectedCustomerIds.length === 0) {
      return
    }

    const confirmed = window.confirm(`Delete ${selectedCustomerIds.length} selected customers?`)
    if (!confirmed) {
      return
    }

    setBulkDeleting(true)
    setActionMessage('')
    setError(null)
    try {
      const result = await bulkDeleteCustomers(selectedCustomerIds)
      const deletedIds = result.deleted_ids || []
      setCustomers((prev) => prev.filter((c) => !deletedIds.includes(getCustomerId(c))))
      setSelectedCustomerIds([])
      setActionMessage(
        `Bulk delete finished: ${result.deleted_count || 0} deleted, ${result.not_found_count || 0} missing.`
      )
    } catch (err) {
      setError(err.message)
    } finally {
      setBulkDeleting(false)
    }
  }

  const handleBulkGenerateInvoices = async () => {
    if (selectedCustomerIds.length === 0) {
      return
    }
    setBulkGenerating(true)
    setActionMessage('')
    setError(null)
    try {
      const result = await bulkGenerateInvoices(selectedCustomerIds)
      setActionMessage(
        `Bulk invoice generation: ${result.created_count || 0} created, ${result.failed_count || 0} failed.`
      )
    } catch (err) {
      setError(err.message)
    } finally {
      setBulkGenerating(false)
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

  const formatBalance = (balance) => {
    if (balance === undefined || balance === null) return '-'
    return typeof balance === 'number' ? `KES ${balance.toLocaleString()}` : balance
  }

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

      <form
        onSubmit={handleSubmit}
        style={{ display: 'grid', gap: '0.5rem', gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))' }}
      >
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
          placeholder="Initial reading (m3)"
          value={form.initial_reading}
          onChange={handleChange}
          type="number"
          step="0.01"
        />
        <button className="button" type="submit" disabled={submitting}>
          {submitting ? 'Saving...' : 'Add Customer'}
        </button>
      </form>

      {editId && (
        <form
          onSubmit={handleSaveEdit}
          style={{
            marginTop: '1rem',
            display: 'grid',
            gap: '0.5rem',
            gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))',
          }}
        >
          <input className="input" name="name" placeholder="Customer name" value={editForm.name} onChange={handleEditChange} required />
          <input className="input" name="phone" placeholder="Phone" value={editForm.phone} onChange={handleEditChange} />
          <input className="input" name="email" placeholder="Email" value={editForm.email} onChange={handleEditChange} />
          <input className="input" name="location" placeholder="Location" value={editForm.location} onChange={handleEditChange} />
          <button className="button" type="submit" disabled={updating}>
            {updating ? 'Updating...' : 'Save Changes'}
          </button>
          <button className="button button--ghost" type="button" onClick={handleCancelEdit}>
            Cancel
          </button>
        </form>
      )}

      {viewCustomer && (
        <div style={{ marginTop: '1rem', padding: '1rem', border: '1px solid #ddd', borderRadius: '8px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <h3 style={{ margin: 0 }}>Customer Details</h3>
            <button className="button button--ghost" type="button" onClick={handleCloseView}>
              Close
            </button>
          </div>
          <div style={{ marginTop: '0.75rem', display: 'grid', gap: '0.5rem', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))' }}>
            <div><strong>ID:</strong> #{viewCustomer.account_number || viewCustomer.id}</div>
            <div><strong>Name:</strong> {viewCustomer.name || '-'}</div>
            <div><strong>Phone:</strong> {viewCustomer.phone || '-'}</div>
            <div><strong>Email:</strong> {viewCustomer.email || '-'}</div>
            <div><strong>Location:</strong> {viewCustomer.location || '-'}</div>
            <div><strong>Type:</strong> {viewCustomer.customer_type || '-'}</div>
            <div><strong>Meter #:</strong> {viewCustomer.meter_number || '-'}</div>
            <div><strong>Status:</strong> {viewCustomer.status || '-'}</div>
            <div><strong>Balance:</strong> {formatBalance(viewCustomer.balance)}</div>
          </div>
        </div>
      )}

      {selectedCustomerIds.length > 0 && (
        <div style={{ marginTop: '1rem', display: 'flex', gap: '0.75rem', alignItems: 'center' }}>
          <strong>{selectedCustomerIds.length} selected</strong>
          <button className="button" type="button" onClick={handleBulkGenerateInvoices} disabled={bulkGenerating}>
            {bulkGenerating ? 'Generating...' : 'Generate Invoices'}
          </button>
          <button className="button button--danger" type="button" onClick={handleBulkDelete} disabled={bulkDeleting}>
            {bulkDeleting ? 'Deleting...' : 'Delete Selected'}
          </button>
        </div>
      )}

      {loading && <div>Loading customers...</div>}
      {error && <div style={{ color: '#dc3545', marginTop: '0.5rem' }}>Error: {error}</div>}
      {actionMessage && <div style={{ color: '#0f5132', marginTop: '0.5rem' }}>{actionMessage}</div>}

      {!loading && customers.length > 0 && (
        <div className="table-wrapper" style={{ marginTop: '1rem' }}>
          <table>
            <thead>
              <tr>
                <th>
                  <input type="checkbox" checked={allSelected} onChange={handleToggleSelectAll} />
                </th>
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
              {customers.map((c) => {
                const id = getCustomerId(c)
                return (
                  <tr key={id}>
                    <td>
                      <input type="checkbox" checked={selectedCustomerIds.includes(id)} onChange={() => handleToggleCustomer(id)} />
                    </td>
                    <td>#{c.account_number || c.id}</td>
                    <td>{c.name}</td>
                    <td>{c.customer_type || '-'}</td>
                    <td>{c.phone || '-'}</td>
                    <td>{c.location || '-'}</td>
                    <td>{c.meter_number || '-'}</td>
                    <td>
                      <span className={`status-badge ${getStatusClass(c.status)}`}>{c.status || 'N/A'}</span>
                    </td>
                    <td>{formatBalance(c.balance)}</td>
                    <td style={{ display: 'flex', gap: '0.4rem', flexWrap: 'wrap' }}>
                      <button type="button" className="button button--small button--ghost" onClick={() => handleViewCustomer(c)}>
                        View
                      </button>
                      <button type="button" className="button button--small button--ghost" onClick={() => handleOpenEdit(c)}>
                        Edit
                      </button>
                      <button type="button" className="button button--small button--ghost" onClick={() => handleGenerateInvoice(id)}>
                        Generate Invoice
                      </button>
                      <button
                        type="button"
                        className="button button--small button--danger"
                        onClick={() => handleDelete(id, c.name || `#${id}`)}
                      >
                        Delete
                      </button>
                    </td>
                  </tr>
                )
              })}
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
