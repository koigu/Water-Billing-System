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
        // Store auth state and token in localStorage
        localStorage.setItem('is_admin', 'true')
        localStorage.setItem('username', response.username || username)
        localStorage.setItem('token', token)
        // Call onLogin to update parent state and trigger navigation
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
      <div className="login-container">
        <div className="login__brand">
          <span className="brand__logo">💧</span>
          <span className="brand__title">Water Billing</span>
        </div>
        
        <h2 className="login__title">Admin Login</h2>
        
        {error && <div className="login__error">{error}</div>}
        
        <form onSubmit={handleLogin} className="login__form">
          <div className="form-group">
            <label className="form-label">Username</label>
            <input
              type="text"
              className="form-input"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="Enter username"
              required
            />
          </div>
          
          <div className="form-group">
            <label className="form-label">Password</label>
            <input
              type="password"
              className="form-input"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Enter password"
              required
            />
          </div>
          
          <button 
            type="submit" 
            className="btn btn--primary login__btn"
            disabled={loading}
          >
            {loading ? 'Signing in...' : 'Sign In'}
          </button>
        </form>
        
        <div className="login__hint">
          Default credentials: admin / changeme
        </div>
      </div>
    </div>
  )
}

