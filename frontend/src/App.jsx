import { Routes, Route, Navigate, NavLink } from 'react-router-dom'
import { useState, useEffect } from 'react'
import './index.css'
import AdminDashboardPage from './pages/AdminDashboardPage'
import CustomersPage from './pages/CustomersPage'
import ReadingsPage from './pages/ReadingsPage'
import InvoicesPage from './pages/InvoicesPage'
import CustomerPortalPage from './pages/CustomerPortalPage'
import LoginPage from './pages/LoginPage'
import { apiPost } from './api/httpClient'

function AppLayout({ children, onLogout }) {
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="sidebar__brand">
          <span className="brand__logo">💧</span>
          <div className="brand__text">
            <span className="brand__title">Water Billing</span>
            <span className="brand__subtitle">Admin Console</span>
          </div>
        </div>
        <nav className="sidebar__nav">
          <NavLink to="/admin/dashboard" className="nav-link">
            Dashboard
          </NavLink>
          <NavLink to="/admin/customers" className="nav-link">
            Customers
          </NavLink>
          <NavLink to="/admin/readings" className="nav-link">
            Meter Readings
          </NavLink>
          <NavLink to="/admin/invoices" className="nav-link">
            Invoices
          </NavLink>
          <NavLink to="/portal" className="nav-link nav-link--secondary">
            Customer Portal
          </NavLink>
        </nav>
      </aside>
      <div className="main">
        <header className="main__topbar">
          <div>
            <h1 className="main__title">Water Billing System</h1>
            <p className="main__subtitle">Modern management of customers, usage and invoices</p>
          </div>
          <button onClick={onLogout} className="button button--logout">
            Sign Out
          </button>
        </header>
        <main className="main__content">{children}</main>
      </div>
    </div>
  )
}

function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(false)

  useEffect(() => {
    // Require both auth flag and token to avoid stale localStorage state
    const adminStatus = localStorage.getItem('is_admin')
    const token = localStorage.getItem('token')
    setIsAuthenticated(adminStatus === 'true' && !!token)
  }, [])

  const handleLogin = () => {
    setIsAuthenticated(true)
  }

  const handleLogout = async () => {
    try {
      await apiPost('/api/admin/logout', {})
    } catch (err) {
      console.log('Logout API call failed, but clearing local state')
    }
    localStorage.removeItem('is_admin')
    localStorage.removeItem('username')
    localStorage.removeItem('token')
    setIsAuthenticated(false)
  }

  // Show login page if not authenticated
  if (!isAuthenticated) {
    return <LoginPage onLogin={handleLogin} />
  }

  return (
    <AppLayout onLogout={handleLogout}>
      <Routes>
        <Route path="/" element={<Navigate to="/admin/dashboard" replace />} />
        <Route path="/admin/dashboard" element={<AdminDashboardPage />} />
        <Route path="/admin/customers" element={<CustomersPage />} />
        <Route path="/admin/readings" element={<ReadingsPage />} />
        <Route path="/admin/invoices" element={<InvoicesPage />} />
        <Route path="/portal" element={<CustomerPortalPage />} />
        <Route path="/login" element={<Navigate to="/admin/dashboard" replace />} />
        <Route path="*" element={<Navigate to="/admin/dashboard" replace />} />
      </Routes>
    </AppLayout>
  )
}

export default App
