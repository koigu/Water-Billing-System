import { useEffect, useMemo, useState } from 'react'
import { customerLogin, fetchPortalData } from '../api/customerApi'

export default function CustomerPortalPage() {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [token, setToken] = useState(localStorage.getItem('customer_token'))
  const [portalData, setPortalData] = useState(null)
  const [loadingPortal, setLoadingPortal] = useState(false)
  const [error, setError] = useState(null)

  const usageSummary = useMemo(() => {
    const points = portalData?.usage_history || []
    if (points.length === 0) return { latest: '-', avg: '-' }
    const latest = points[points.length - 1]?.reading ?? '-'
    const avg = (
      points.reduce((sum, p) => sum + Number(p.reading || 0), 0) / points.length
    ).toFixed(2)
    return { latest, avg }
  }, [portalData])

  const handleLogin = async (e) => {
    e.preventDefault()
    setError(null)
    try {
      const res = await customerLogin(username, password)
      const nextToken = res.access_token
      setToken(nextToken)
      localStorage.setItem('customer_token', nextToken)
      setPassword('')
    } catch (err) {
      setError(err.message)
    }
  }

  const handleLogout = () => {
    localStorage.removeItem('customer_token')
    setToken(null)
    setPortalData(null)
    setError(null)
  }

  useEffect(() => {
    if (!token) return
    setLoadingPortal(true)
    setError(null)
    fetchPortalData(token)
      .then((data) => setPortalData(data))
      .catch((err) => {
        setError(err.message)
        localStorage.removeItem('customer_token')
        setToken(null)
      })
      .finally(() => setLoadingPortal(false))
  }, [token])

  return (
    <div className="customer-portal">
      <div className="page-header">
        <div>
          <h2 className="page-title">Customer Portal</h2>
          <p className="page-description">View usage, recent invoices, and account alerts</p>
        </div>
      </div>

      {!token && (
        <form onSubmit={handleLogin} className="card customer-portal__login">
          <h3 style={{ marginTop: 0 }}>Portal Login</h3>
          <input
            className="input"
            placeholder="Username"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            required
          />
          <input
            className="input"
            type="password"
            placeholder="Password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />
          <button className="button" type="submit">
            Sign In
          </button>
        </form>
      )}

      {error && <div style={{ color: '#dc3545', marginBottom: '0.7rem' }}>Error: {error}</div>}
      {loadingPortal && <div>Loading portal...</div>}

      {portalData && (
        <>
          <div style={{ marginBottom: '0.8rem' }}>
            <button className="button button--logout" onClick={handleLogout} type="button">
              Sign Out
            </button>
          </div>

          <div className="card-grid">
            <div className="card">
              <div className="card__title">Customer</div>
              <div className="card__value">{portalData.customer?.name || '-'}</div>
              <div className="card__meta">Location: {portalData.customer?.location || '-'}</div>
            </div>

            <div className="card">
              <div className="card__title">Total Due</div>
              <div className="card__value">{Number(portalData.total_due || 0).toFixed(2)} KES</div>
            </div>

            <div className="card">
              <div className="card__title">Latest Reading</div>
              <div className="card__value">{usageSummary.latest}</div>
              <div className="card__meta">Average: {usageSummary.avg}</div>
            </div>
          </div>

          <div className="table-wrapper" style={{ marginTop: '1rem' }}>
            <table>
              <thead>
                <tr>
                  <th>Invoice #</th>
                  <th>Amount</th>
                  <th>Status</th>
                  <th>Due Date</th>
                </tr>
              </thead>
              <tbody>
                {(portalData.recent_invoices || []).map((inv) => (
                  <tr key={inv.id}>
                    <td>#{inv.id}</td>
                    <td>{Number(inv.amount || 0).toFixed(2)} KES</td>
                    <td>{inv.status || '-'}</td>
                    <td>{inv.due_date ? new Date(inv.due_date).toLocaleDateString() : '-'}</td>
                  </tr>
                ))}
                {(!portalData.recent_invoices || portalData.recent_invoices.length === 0) && (
                  <tr>
                    <td colSpan={4} style={{ textAlign: 'center', color: '#6b7a96' }}>
                      No invoices found.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>

          <div className="table-wrapper" style={{ marginTop: '1rem' }}>
            <table>
              <thead>
                <tr>
                  <th>Alert Type</th>
                  <th>Message</th>
                </tr>
              </thead>
              <tbody>
                {(portalData.alerts || []).map((alert) => (
                  <tr key={alert.id}>
                    <td>{alert.alert_type || '-'}</td>
                    <td>{alert.message || '-'}</td>
                  </tr>
                ))}
                {(!portalData.alerts || portalData.alerts.length === 0) && (
                  <tr>
                    <td colSpan={2} style={{ textAlign: 'center', color: '#6b7a96' }}>
                      No alerts available.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  )
}
