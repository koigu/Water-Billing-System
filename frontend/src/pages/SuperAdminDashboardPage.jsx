import { useEffect, useMemo, useState } from 'react'
import {
  activateProvider,
  createProvider,
  deactivateProvider,
  fetchProviders,
  fetchSuperAdminDashboard,
} from '../api/adminApi'

const EMPTY_PROVIDER_FORM = {
  name: '',
  slug: '',
  contact_email: '',
  contact_phone: '',
  address: '',
  rate_per_unit: '1.5',
}

export default function SuperAdminDashboardPage() {
  const [stats, setStats] = useState(null)
  const [providers, setProviders] = useState([])
  const [form, setForm] = useState(EMPTY_PROVIDER_FORM)
  const [loading, setLoading] = useState(true)
  const [creating, setCreating] = useState(false)
  const [actionBusy, setActionBusy] = useState('')
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')

  const activeProviders = useMemo(
    () => providers.filter((provider) => provider.is_active !== false).length,
    [providers]
  )

  const loadData = async () => {
    setLoading(true)
    setError('')
    try {
      const [dashboardStats, providerList] = await Promise.all([
        fetchSuperAdminDashboard(),
        fetchProviders(),
      ])
      setStats(dashboardStats)
      setProviders(providerList)
    } catch (err) {
      setError(err.message || 'Failed to load super admin dashboard')
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

  const handleCreateProvider = async (e) => {
    e.preventDefault()
    setCreating(true)
    setMessage('')
    setError('')
    try {
      const payload = {
        name: form.name.trim(),
        slug: form.slug.trim().toLowerCase(),
        contact_email: form.contact_email || null,
        contact_phone: form.contact_phone || null,
        address: form.address || null,
        rate_per_unit: parseFloat(form.rate_per_unit || '1.5'),
      }
      await createProvider(payload)
      setForm(EMPTY_PROVIDER_FORM)
      setMessage('Provider created successfully.')
      await loadData()
    } catch (err) {
      setError(err.message || 'Failed to create provider')
    } finally {
      setCreating(false)
    }
  }

  const toggleProviderStatus = async (provider) => {
    const slug = provider.slug
    const activate = provider.is_active === false
    setActionBusy(slug)
    setMessage('')
    setError('')
    try {
      if (activate) {
        await activateProvider(slug)
        setMessage(`Provider "${provider.name}" activated.`)
      } else {
        await deactivateProvider(slug)
        setMessage(`Provider "${provider.name}" deactivated.`)
      }
      await loadData()
    } catch (err) {
      setError(err.message || 'Failed to update provider status')
    } finally {
      setActionBusy('')
    }
  }

  if (loading) return <div>Loading companies...</div>

  return (
    <div>
      <div className="page-header">
        <div>
          <h2 className="page-title">Companies</h2>
          <p className="page-description">Manage multiple water companies from one place</p>
        </div>
      </div>

      <div className="card-grid">
        <div className="card">
          <div className="card__title">Total Providers</div>
          <div className="card__value">{stats?.total_providers ?? providers.length}</div>
        </div>
        <div className="card">
          <div className="card__title">Active Providers</div>
          <div className="card__value">{stats?.active_providers ?? activeProviders}</div>
        </div>
        <div className="card">
          <div className="card__title">Total Customers</div>
          <div className="card__value">{stats?.total_customers ?? 0}</div>
        </div>
        <div className="card">
          <div className="card__title">Total Revenue</div>
          <div className="card__value">KES {Number(stats?.total_revenue || 0).toLocaleString()}</div>
        </div>
      </div>

      <form className="super-admin-form" onSubmit={handleCreateProvider}>
        <h3 className="super-admin-form__title">Create Water Company</h3>
        <div className="super-admin-form__grid">
          <input
            className="input"
            name="name"
            value={form.name}
            onChange={handleChange}
            placeholder="Company name"
            required
          />
          <input
            className="input"
            name="slug"
            value={form.slug}
            onChange={handleChange}
            placeholder="Slug (e.g. lakeview-water)"
            required
          />
          <input
            className="input"
            type="email"
            name="contact_email"
            value={form.contact_email}
            onChange={handleChange}
            placeholder="Contact email"
          />
          <input
            className="input"
            name="contact_phone"
            value={form.contact_phone}
            onChange={handleChange}
            placeholder="Contact phone"
          />
          <input
            className="input"
            name="address"
            value={form.address}
            onChange={handleChange}
            placeholder="Address"
          />
          <input
            className="input"
            type="number"
            min="0"
            step="0.01"
            name="rate_per_unit"
            value={form.rate_per_unit}
            onChange={handleChange}
            placeholder="Rate per unit"
            required
          />
        </div>
        <button className="button" type="submit" disabled={creating}>
          {creating ? 'Creating...' : 'Create Provider'}
        </button>
      </form>

      {error && <div style={{ color: '#dc3545', marginTop: '0.75rem' }}>Error: {error}</div>}
      {message && <div style={{ color: '#0f5132', marginTop: '0.75rem' }}>{message}</div>}

      <div className="table-wrapper">
        <table>
          <thead>
            <tr>
              <th>Provider</th>
              <th>Slug</th>
              <th>Contact</th>
              <th>Status</th>
              <th>Created</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {providers.map((provider) => (
              <tr key={provider.slug}>
                <td>{provider.name}</td>
                <td>{provider.slug}</td>
                <td>{provider.contact_email || provider.contact_phone || '-'}</td>
                <td>
                  {provider.is_active === false ? (
                    <span className="badge badge--danger">Inactive</span>
                  ) : (
                    <span className="badge badge--success">Active</span>
                  )}
                </td>
                <td>{provider.created_at ? new Date(provider.created_at).toLocaleDateString() : '-'}</td>
                <td>
                  <button
                    type="button"
                    className="button button--small button--ghost"
                    disabled={actionBusy === provider.slug}
                    onClick={() => toggleProviderStatus(provider)}
                  >
                    {actionBusy === provider.slug
                      ? 'Updating...'
                      : provider.is_active === false
                      ? 'Activate'
                      : 'Deactivate'}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
