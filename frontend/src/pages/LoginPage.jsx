import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
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
      <div className="login-container card">
        <div className="login__header">
          <span className="login__badge">Utility Ops</span>
          <h1 className="login__title">Water Billing Control Center</h1>
          <p className="login__subtitle">Sign in to manage cycles, readings, invoices, and reminders.</p>
        </div>

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

        <div className="login__hint">Use your assigned admin credentials.</div>
      </div>
    </div>
  )
}
