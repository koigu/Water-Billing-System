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

  const monthlyUsage = useMemo(() => {
    const points = portalData?.usage_history || []
    if (!points.length) return []

    const byMonth = new Map()
    for (const point of points) {
      const rawDate = point.date || point.recorded_at
      if (!rawDate) continue

      let dateObj
      if (typeof rawDate === 'string' && /^\d{4}-\d{2}$/.test(rawDate)) {
        dateObj = new Date(`${rawDate}-01T00:00:00Z`)
      } else {
        dateObj = new Date(rawDate)
      }
      if (Number.isNaN(dateObj.getTime())) continue

      const monthKey = `${dateObj.getUTCFullYear()}-${String(dateObj.getUTCMonth() + 1).padStart(2, '0')}`
      const current = byMonth.get(monthKey) || { total: 0, count: 0 }
      current.total += Number(point.reading || 0)
      current.count += 1
      byMonth.set(monthKey, current)
    }

    return Array.from(byMonth.entries())
      .sort(([a], [b]) => (a > b ? 1 : -1))
      .map(([monthKey, agg]) => {
        const dateObj = new Date(`${monthKey}-01T00:00:00Z`)
        return {
          monthKey,
          label: dateObj.toLocaleDateString(undefined, { month: 'short', year: '2-digit' }),
          reading: agg.count ? Number((agg.total / agg.count).toFixed(2)) : 0,
        }
      })
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
          <h2 className="page-title">Celebration Waters Customer Portal</h2>
          <p className="page-description">Check usage history, invoices, alerts, and current account balance</p>
        </div>
      </div>

      {!token && (
        <form onSubmit={handleLogin} className="card customer-portal__login">
          <h3 style={{ marginTop: 0 }}>Customer Sign In</h3>
          <label htmlFor="customer-username">Username</label>
          <input
            id="customer-username"
            name="username"
            className="input"
            placeholder="Username"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            autoComplete="username"
            required
          />
          <label htmlFor="customer-password">Password</label>
          <input
            id="customer-password"
            name="password"
            className="input"
            type="password"
            placeholder="Password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete="current-password"
            required
          />
          <button className="button" type="submit">
            Access Portal
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
            <div style={{ padding: '0.85rem 0.9rem 0.25rem', fontWeight: 600, color: '#1f2f4d' }}>
              Meter Readings Trend (Monthly)
            </div>
            <div style={{ padding: '0 0.9rem 0.9rem' }}>
              {monthlyUsage.length > 1 ? (
                <svg viewBox="0 0 760 220" width="100%" height="220" role="img" aria-label="Monthly meter readings chart">
                  <line x1="50" y1="180" x2="730" y2="180" stroke="#9db0d1" strokeWidth="1" />
                  <line x1="50" y1="20" x2="50" y2="180" stroke="#9db0d1" strokeWidth="1" />
                  {(() => {
                    const maxValue = Math.max(...monthlyUsage.map((d) => d.reading), 1)
                    const stepX = monthlyUsage.length > 1 ? 680 / (monthlyUsage.length - 1) : 680
                    const plotPoints = monthlyUsage.map((d, idx) => {
                      const x = 50 + idx * stepX
                      const y = 180 - (d.reading / maxValue) * 150
                      return { ...d, x, y }
                    })
                    const polylinePoints = plotPoints.map((p) => `${p.x},${p.y}`).join(' ')
                    return (
                      <>
                        <polyline points={polylinePoints} fill="none" stroke="#0b5ed7" strokeWidth="2.5" />
                        {plotPoints.map((p) => (
                          <g key={p.monthKey}>
                            <circle cx={p.x} cy={p.y} r="3.5" fill="#0b5ed7" />
                            <text x={p.x} y="198" textAnchor="middle" fontSize="11" fill="#5b6b8b">
                              {p.label}
                            </text>
                          </g>
                        ))}
                      </>
                    )
                  })()}
                </svg>
              ) : (
                <div style={{ color: '#6b7a96' }}>Not enough monthly data points to draw trend.</div>
              )}
            </div>
          </div>

          <div className="table-wrapper" style={{ marginTop: '1rem' }}>
            <table>
              <thead>
                <tr>
                  <th>Invoice ID</th>
                  <th>Amount</th>
                  <th>Status</th>
                  <th>Due Date</th>
                </tr>
              </thead>
              <tbody>
                {(portalData.recent_invoices || []).map((inv) => (
                  <tr key={inv.id}>
                    <td>
                      <span className="invoice-id-chip">#{inv.id}</span>
                    </td>
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
