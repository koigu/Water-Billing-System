import { useEffect, useState } from 'react'
import { customerLogin, fetchPortalData } from '../api/customerApi'

export default function CustomerPortalPage() {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [token, setToken] = useState(null)
  const [portalData, setPortalData] = useState(null)
  const [error, setError] = useState(null)

  const handleLogin = async (e) => {
    e.preventDefault()
    setError(null)
    try {
      const res = await customerLogin(username, password)
      setToken(res.access_token)
    } catch (err) {
      setError(err.message)
    }
  }

  useEffect(() => {
    if (!token) return
    fetchPortalData(token)
      .then((data) => setPortalData(data))
      .catch((err) => setError(err.message))
  }, [token])

  return (
    <div>
      <div className="page-header">
        <div>
          <h2 className="page-title">Customer Portal</h2>
          <p className="page-description">Customers can view usage, invoices and alerts</p>
        </div>
      </div>

      {!token && (
        <form
          onSubmit={handleLogin}
          style={{ display: 'grid', gap: '0.5rem', maxWidth: 320, marginBottom: '1rem' }}
        >
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
            Sign in
          </button>
        </form>
      )}

      {error && <div style={{ color: '#dc3545', marginBottom: '0.5rem' }}>Error: {error}</div>}

      {portalData && (
        <div className="card-grid">
          <div className="card">
            <div className="card__title">Customer</div>
            <div className="card__value">{portalData.customer.name}</div>
            <div className="card__meta">Location: {portalData.customer.location || '-'}</div>
          </div>

          <div className="card">
            <div className="card__title">Total Due</div>
            <div className="card__value">{portalData.total_due.toFixed(2)} KES</div>
          </div>
        </div>
      )}
    </div>
  )
}
