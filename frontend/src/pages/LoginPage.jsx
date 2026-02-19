import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { apiPost } from '../api/httpClient'

export default function LoginPage({ onLogin }) {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const navigate = useNavigate()

  const handleLogin = async (e) => {
    e.preventDefault()
    setError('')
    setLoading(true)

    try {
      const response = await apiPost('/api/admin/login', { username, password })
      const token = response.token || response.access_token

      if (!token) {
        throw new Error('Login succeeded but no token was returned')
      }

      if (response.message === 'Login successful') {
        localStorage.setItem('is_admin', 'true')
        localStorage.setItem('username', response.username || username)
        localStorage.setItem('token', token)
        if (onLogin) {
          onLogin()
        }
        navigate('/admin/dashboard')
      }
    } catch (err) {
      setError(err.message || 'Invalid credentials')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="login-page">
      <div className="login-page__bg" />
      <div className="login-layout">
        <section className="login-showcase">
          <span className="login-showcase__badge">Secure Utility Operations Workspace</span>
          <h1 className="login-showcase__title">
            Keep every <span>meter reading</span>, every <span>invoice</span>, and every account
            <br />
            fully accountable.
          </h1>
          <p className="login-showcase__desc">
            Built for water service teams: monitor usage, generate billing cycles, and track overdue
            accounts from one secure control center.
          </p>

          <div className="login-showcase__grid">
            <div className="login-showcase__item">
              <h3>Meter reading discipline</h3>
              <p>Track collection coverage by cycle and quickly identify missing readings.</p>
            </div>
            <div className="login-showcase__item">
              <h3>Billing clarity</h3>
              <p>Generate invoices in batches with transparent usage-to-amount calculations.</p>
            </div>
            <div className="login-showcase__item">
              <h3>Reminder workflows</h3>
              <p>Follow up overdue accounts with bulk reminders and operational visibility.</p>
            </div>
            <div className="login-showcase__item">
              <h3>Role-based access</h3>
              <p>Separate admin operations from customer portal sign-in in a secure workflow.</p>
            </div>
          </div>
        </section>

        <section className="login-panel card">
          <div className="login-panel__logo">WB</div>
          <h2 className="login-panel__title">Welcome back</h2>
          <p className="login-panel__subtitle">Sign in to access your water billing workspace.</p>

          {error && <div className="login__error">{error}</div>}

          <form onSubmit={handleLogin} className="login__form">
            <div className="login__field">
              <label className="login__label">Username</label>
              <input
                type="text"
                className="input login__input"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="Enter username"
                required
              />
            </div>

            <div className="login__field">
              <label className="login__label">Password</label>
              <input
                type="password"
                className="input login__input"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Enter password"
                required
              />
            </div>

            <button type="submit" className="button login__btn" disabled={loading}>
              {loading ? 'Signing in...' : 'Sign In'}
            </button>
          </form>

          <div className="login-panel__divider">OR</div>
          <Link to="/portal" className="button button--ghost login__portal-link">
            Explore Customer Portal
          </Link>
          <div className="login__hint">Use your assigned admin credentials.</div>
        </section>
      </div>
    </div>
  )
}
