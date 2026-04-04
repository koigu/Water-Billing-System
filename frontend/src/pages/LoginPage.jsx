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

      if (response.message === 'Login successful') {
        localStorage.setItem('is_admin', 'true')
        localStorage.setItem('is_super_admin', response.is_super_admin ? 'true' : 'false')
        localStorage.setItem('username', response.username || username)
        if (response.token || response.access_token) {
          localStorage.setItem('token', response.token || response.access_token)
        } else {
          localStorage.removeItem('token')
        }
        if (response.provider_slug) {
          localStorage.setItem('provider_slug', response.provider_slug)
        } else {
          localStorage.removeItem('provider_slug')
        }
        if (onLogin) {
          onLogin({
            is_super_admin: !!response.is_super_admin,
            provider_slug: response.provider_slug || null,
          })
        }
        navigate(response.is_super_admin ? '/super-admin/dashboard' : '/admin/dashboard')
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
          <span className="login-showcase__badge">Celebration Waters Operations Workspace</span>
          <h1 className="login-showcase__title">
            Keep every <span>meter reading</span>, every <span>invoice</span>, and every customer
            <br />
            fully accountable.
          </h1>
          <p className="login-showcase__desc">
            A practical platform for utility teams and new staff: record usage, run billing cycles,
            and follow up overdue accounts from one control center.
          </p>

          <div className="login-showcase__grid">
            <div className="login-showcase__item">
              <h3>Meter reading discipline</h3>
              <p>Track collection coverage by cycle and quickly identify missed households.</p>
            </div>
            <div className="login-showcase__item">
              <h3>Billing clarity</h3>
              <p>Generate invoices with transparent usage-to-amount calculations.</p>
            </div>
            <div className="login-showcase__item">
              <h3>Reminder workflows</h3>
              <p>Follow up overdue balances with reminders and clear status visibility.</p>
            </div>
            <div className="login-showcase__item">
              <h3>Fast onboarding</h3>
              <p>New users can understand daily operations quickly through cycle actions.</p>
            </div>
          </div>
        </section>

        <section className="login-panel card">
          <div className="login-panel__logo">CW</div>
          <h2 className="login-panel__title">Welcome to Celebration Waters</h2>
          <p className="login-panel__subtitle">Sign in to access the billing and operations dashboard.</p>

          {error && <div className="login__error">{error}</div>}

          <form onSubmit={handleLogin} className="login__form">
            <div className="login__field">
              <label className="login__label" htmlFor="admin-username">Username</label>
              <input
                id="admin-username"
                name="username"
                type="text"
                className="input login__input"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="Enter username"
                autoComplete="username"
                required
              />
            </div>

            <div className="login__field">
              <label className="login__label" htmlFor="admin-password">Password</label>
              <input
                id="admin-password"
                name="password"
                type="password"
                className="input login__input"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Enter password"
                autoComplete="current-password"
                required
              />
            </div>

            <button type="submit" className="button login__btn" disabled={loading}>
              {loading ? 'Signing in...' : 'Sign In'}
            </button>
          </form>

          <div className="login-panel__divider">OR</div>
          <Link to="/portal" className="button button--ghost login__portal-link">
            Open Customer Portal
          </Link>
          <div className="login__hint">Use credentials assigned by your system administrator.</div>
        </section>
      </div>
    </div>
  )
}
