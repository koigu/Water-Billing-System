# Frontend Developer Guide: Backend Integration

This document provides everything a frontend developer needs to know to work effectively with the Water Billing System backend.

## Table of Contents
1. [Architecture Overview](#architecture-overview)
2. [API Endpoints](#api-endpoints)
3. [Authentication Flow](#authentication-flow)
4. [Data Models](#data-models)
5. [Common Patterns](#common-patterns)
6. [Integration Examples](#integration-examples)
7. [Error Handling](#error-handling)

---

## Architecture Overview

### Tech Stack
- **Backend**: FastAPI (Python)
- **Database**: MongoDB (primary data) + SQLite (counters)
- **Frontend**: React 19 + Vite
- **Communication**: RESTful HTTP with JSON

### API Base URL
```
http://127.0.0.1:8000
```

### CORS Configuration
The backend allows requests from:
- `http://localhost:5173` (Vite dev server)
- `http://127.0.0.1:5173`

---

## API Endpoints

### Admin Authentication

#### Login
```javascript
POST /api/admin/login
Content-Type: application/json

{
  "username": "admin",
  "password": "changeme"
}
```

**Response (200 OK):**
```json
{
  "message": "Login successful",
  "username": "admin"
}
```

**Response (403 Forbidden):**
```json
{
  "detail": "Invalid credentials"
}
```

#### Logout
```javascript
GET /api/admin/logout
```

**Response:**
```json
{
  "message": "Logged out successfully"
}
```

### Dashboard

#### Get Dashboard Statistics
```javascript
GET /api/admin/dashboard
// Requires authentication (session-based)
```

**Response:**
```json
{
  "total_customers": 25,
  "active_customers": 20,
  "inactive_customers": 5,
  "total_water_usage": 1250.5
}
```

### Customers

#### List All Customers
```javascript
GET /api/admin/customers
// Optional: ?search=john
```

**Response:**
```json
[
  {
    "id": 1,
    "name": "John Doe",
    "phone": "+254700000000",
    "email": "john@example.com",
    "location": "Nairobi",
    "created_at": "2026-02-06T12:00:00Z"
  },
  {
    "id": 2,
    "name": "Jane Smith",
    "phone": "+254700000001",
    "email": "jane@example.com",
    "location": "Kiambu",
    "created_at": "2026-02-07T12:00:00Z"
  }
]
```

#### Create Customer
```javascript
POST /api/admin/customers
Content-Type: application/x-www-form-urlencoded

name=John+Doe&phone=+254700000000&email=john@example.com&location=Nairobi
```

**Response:**
```json
{
  "message": "Customer created",
  "customer_id": 1
}
```

### Meter Readings

#### List All Readings
```javascript
GET /api/admin/readings
```

**Response:**
```json
[
  {
    "id": 1,
    "customer_id": 1,
    "reading_value": 1150,
    "recorded_at": "2026-02-06T12:00:00Z"
  },
  {
    "id": 2,
    "customer_id": 1,
    "reading_value": 1135,
    "recorded_at": "2026-01-06T12:00:00Z"
  }
]
```

#### Add Reading
```javascript
POST /api/admin/customers/{customer_id}/readings
Content-Type: application/x-www-form-urlencoded

reading_value=1200
```

**Response:**
```json
{
  "message": "Reading added",
  "reading_id": 3
}
```

### Invoices

#### List All Invoices
```javascript
GET /api/admin/invoices
```

**Response:**
```json
[
  {
    "id": 1,
    "customer_id": 1,
    "amount": 1800,
    "billing_from": "2026-01-06T12:00:00Z",
    "billing_to": "2026-02-06T12:00:00Z",
    "due_date": "2026-02-21T12:00:00Z",
    "status": "pending",
    "sent_at": "2026-02-06T12:00:00Z",
    "location": "Nairobi"
  }
]
```

**Invoice Status Values:**
- `"pending"` - Not yet paid
- `"paid"` - Payment completed
- `"overdue"` - Past due date

#### Generate Invoice
```javascript
POST /api/admin/invoices/generate/{customer_id}
```

**Response:**
```json
{
  "message": "Invoice generated",
  "invoice_id": 2
}
```

**How invoice calculation works:**
1. Backend fetches the two most recent meter readings
2. Calculates consumption: `Current Reading - Previous Reading`
3. Applies current rate: `Consumption × Rate per Unit`
4. Creates invoice with 15-day due date

**Example:**
- Previous Reading: 1135 m³
- Current Reading: 1150 m³
- Consumption: 15 m³
- Rate: 120 KES/m³
- Invoice Amount: 15 × 120 = **1800 KES**

#### Mark Invoice as Paid
```javascript
POST /api/admin/invoices/{invoice_id}/pay
```

**Response:**
```json
{
  "message": "Invoice marked as paid"
}
```

### Rate Configuration

#### Get Current Rate
```javascript
GET /api/admin/rate
```

**Response:**
```json
{
  "rate": {
    "mode": "fixed",
    "value": 120,
    "updated_at": "2026-02-06T12:00:00Z"
  },
  "effective_rate": 120
}
```

#### Set Rate
```javascript
POST /api/admin/rate
Content-Type: application/x-www-form-urlencoded

mode=fixed&value=120
// OR
mode=percent&value=10  // +10% from base rate
```

**Response:**
```json
{
  "message": "Rate updated"
}
```

**Rate Modes:**
- `"fixed"` - Direct per-unit price (e.g., 120 KES per m³)
- `"percent"` - Percentage adjustment from base rate (e.g., +10%)

### Customer Portal

#### Customer Login
```javascript
POST /api/auth/login
Content-Type: application/json

{
  "username": "customer_username",
  "password": "customer_password"
}
```

**Response:**
```json
{
  "access_token": "base64encoded_token",
  "token_type": "bearer"
}
```

#### Get Portal Data
```javascript
GET /api/customer/portal
Authorization: Bearer {token}
```

**Response:**
```json
{
  "customer": {
    "id": 1,
    "name": "John Doe",
    "phone": "+254700000000",
    "email": "john@example.com",
    "location": "Nairobi"
  },
  "recent_invoices": [...],
  "usage_history": [...],
  "benchmark": {
    "customer_average": 1142.5,
    "location_average": 1250.0,
    "percentile": 35.5,
    "comparison": "Below average - Great conservation!"
  },
  "alerts": [...],
  "total_due": 1800
}
```

---

## Authentication Flow

### Session-Based Auth (Admin)

The admin panel uses session-based authentication:

1. **Login** → Sets session cookie
2. **Subsequent requests** → Cookie sent automatically
3. **Logout** → Clears session

```javascript
// Login flow
const response = await apiPost('/api/admin/login', {
  username,
  password
});

if (response.message === 'Login successful') {
  // Session cookie is set automatically
  localStorage.setItem('is_admin', 'true');
  navigate('/admin/dashboard');
}

// Logout flow
await apiPost('/api/admin/logout', {});
localStorage.removeItem('is_admin');
```

### Token-Based Auth (Customer Portal)

Customer portal uses Bearer token authentication:

```javascript
// Login
const response = await apiPost('/api/auth/login', {
  username: 'customer1',
  password: 'password123'
});

const token = response.access_token;

// Use token in subsequent requests
const portalData = await apiGet('/api/customer/portal', {
  headers: {
    Authorization: `Bearer ${token}`
  }
});
```

---

## Data Models

### Customer
```typescript
interface Customer {
  id: number;
  name: string;
  phone: string | null;
  email: string | null;
  location: string | null;
  created_at: string;  // ISO datetime
}
```

### Meter Reading
```typescript
interface MeterReading {
  id: number;
  customer_id: number;
  reading_value: number;
  recorded_at: string;  // ISO datetime
}
```

### Invoice
```typescript
interface Invoice {
  id: number;
  customer_id: number;
  amount: number;
  billing_from: string | null;
  billing_to: string | null;
  due_date: string;
  sent_at: string | null;
  status: 'pending' | 'paid' | 'overdue' | 'cancelled';
  location: string | null;
  reminder_sent_at: string | null;
}
```

### Rate Configuration
```typescript
interface RateConfig {
  mode: 'fixed' | 'percent';
  value: number;
  updated_at: string | null;
}
```

### Dashboard Stats
```typescript
interface DashboardStats {
  total_customers: number;
  active_customers: number;
  inactive_customers: number;
  total_water_usage: number;
}
```

---

## Common Patterns

### API Client Setup

```javascript
// frontend/src/api/httpClient.js
const API_BASE_URL = 'http://127.0.0.1:8000';

export async function apiGet(path, options = {}) {
  const res = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
      ...(options.headers || {}),
    },
  });

  if (!res.ok) {
    const error = await res.json().catch(() => ({}));
    throw new Error(error.detail || `GET ${path} failed: ${res.status}`);
  }

  return res.json();
}

export async function apiPost(path, body, options = {}) {
  const res = await fetch(`${API_BASE_URL}${path}`, {
    method: 'POST',
    ...options,
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
      ...(options.headers || {}),
    },
    body: body ? JSON.stringify(body) : undefined,
  });

  if (!res.ok) {
    const error = await res.json().catch(() => ({}));
    throw new Error(error.detail || `POST ${path} failed: ${res.status}`);
  }

  return res.json();
}
```

### Admin API Module

```javascript
// frontend/src/api/adminApi.js
import { apiGet, apiPost } from './httpClient';

export function fetchDashboard() {
  return apiGet('/api/admin/dashboard');
}

export function fetchCustomers(search = '') {
  const query = search ? `?search=${encodeURIComponent(search)}` : '';
  return apiGet(`/api/admin/customers${query}`);
}

export function createCustomer(payload) {
  const formData = new URLSearchParams();
  for (const [key, value] of Object.entries(payload)) {
    if (value !== null && value !== undefined) {
      formData.append(key, value);
    }
  }
  
  return apiPost('/api/admin/customers', formData, {
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
  });
}

export function fetchReadings() {
  return apiGet('/api/admin/readings');
}

export function addReading(customerId, readingValue) {
  return apiPost(`/api/admin/customers/${customerId}/readings`, 
    new URLSearchParams({ reading_value: readingValue }),
    { headers: { 'Content-Type': 'application/x-www-form-urlencoded' } }
  );
}

export function fetchInvoices() {
  return apiGet('/api/admin/invoices');
}

export function generateInvoice(customerId) {
  return apiPost(`/api/admin/invoices/generate/${customerId}`);
}

export function payInvoice(invoiceId) {
  return apiPost(`/api/admin/invoices/${invoiceId}/pay`);
}

export function fetchRate() {
  return apiGet('/api/admin/rate');
}

export function updateRate(mode, value) {
  return apiPost('/api/admin/rate',
    new URLSearchParams({ mode, value }),
    { headers: { 'Content-Type': 'application/x-www-form-urlencoded' } }
  );
}
```

### Customer Portal API Module

```javascript
// frontend/src/api/customerApi.js
import { apiGet, apiPost } from './httpClient';

export function customerLogin(username, password) {
  return apiPost('/api/auth/login', { username, password });
}

export function customerRegister(customerId, username, password) {
  const formData = new FormData();
  formData.append('customer_id', customerId);
  formData.append('username', username);
  formData.append('password', password);

  return fetch('http://127.0.0.1:8000/api/auth/register', {
    method: 'POST',
    credentials: 'include',
    body: formData,
  }).then(res => {
    if (!res.ok) throw new Error('Register failed');
    return res.json();
  });
}

export function fetchPortalData(token) {
  return apiGet('/api/customer/portal', {
    headers: { Authorization: `Bearer ${token}` }
  });
}
```

---

## Integration Examples

### Admin Dashboard Page

```jsx
// frontend/src/pages/AdminDashboardPage.jsx
import { useState, useEffect } from 'react';
import { fetchDashboard } from '../api/adminApi';

export default function AdminDashboardPage() {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    async function loadStats() {
      try {
        const data = await fetchDashboard();
        setStats(data);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    }
    loadStats();
  }, []);

  if (loading) return <div>Loading...</div>;
  if (error) return <div>Error: {error}</div>;

  return (
    <div>
      <h1>Dashboard</h1>
      <div className="card-grid">
        <div className="card">
          <div className="card__title">Total Customers</div>
          <div className="card__value">{stats.total_customers}</div>
        </div>
        <div className="card">
          <div className="card__title">Active Customers</div>
          <div className="card__value">{stats.active_customers}</div>
        </div>
        <div className="card">
          <div className="card__title">Inactive Customers</div>
          <div className="card__value">{stats.inactive_customers}</div>
        </div>
        <div className="card">
          <div className="card__title">Total Water Usage (m³)</div>
          <div className="card__value">{stats.total_water_usage}</div>
        </div>
      </div>
    </div>
  );
}
```

### Customers Page with Search

```jsx
// frontend/src/pages/CustomersPage.jsx
import { useState, useEffect } from 'react';
import { fetchCustomers, createCustomer } from '../api/adminApi';

export default function CustomersPage() {
  const [customers, setCustomers] = useState([]);
  const [search, setSearch] = useState('');
  const [showForm, setShowForm] = useState(false);
  const [newCustomer, setNewCustomer] = useState({
    name: '',
    phone: '',
    email: '',
    location: '',
    initial_reading: ''
  });

  async function loadCustomers() {
    const data = await fetchCustomers(search);
    setCustomers(data);
  }

  useEffect(() => {
    loadCustomers();
  }, [search]);

  async function handleSubmit(e) {
    e.preventDefault();
    await createCustomer(newCustomer);
    setShowForm(false);
    setNewCustomer({ name: '', phone: '', email: '', location: '', initial_reading: '' });
    loadCustomers();
  }

  return (
    <div>
      <header className="page-header">
        <div>
          <h1 className="page-title">Customers</h1>
          <p className="page-description">Manage your water customers</p>
        </div>
        <button className="button" onClick={() => setShowForm(!showForm)}>
          {showForm ? 'Cancel' : 'Add Customer'}
        </button>
      </header>

      {showForm && (
        <form onSubmit={handleSubmit} className="card">
          <input
            className="input"
            placeholder="Name"
            value={newCustomer.name}
            onChange={e => setNewCustomer({...newCustomer, name: e.target.value})}
            required
          />
          <input
            className="input"
            placeholder="Phone"
            value={newCustomer.phone}
            onChange={e => setNewCustomer({...newCustomer, phone: e.target.value})}
          />
          <input
            className="input"
            placeholder="Email"
            type="email"
            value={newCustomer.email}
            onChange={e => setNewCustomer({...newCustomer, email: e.target.value})}
          />
          <input
            className="input"
            placeholder="Location"
            value={newCustomer.location}
            onChange={e => setNewCustomer({...newCustomer, location: e.target.value})}
          />
          <input
            className="input"
            type="number"
            placeholder="Initial Reading"
            value={newCustomer.initial_reading}
            onChange={e => setNewCustomer({...newCustomer, initial_reading: e.target.value})}
          />
          <button type="submit" className="button">Create Customer</button>
        </form>
      )}

      <input
        className="input"
        placeholder="Search customers..."
        value={search}
        onChange={e => setSearch(e.target.value)}
        style={{ marginBottom: '1rem' }}
      />

      <div className="table-wrapper">
        <table>
          <thead>
            <tr>
              <th>ID</th>
              <th>Name</th>
              <th>Phone</th>
              <th>Email</th>
              <th>Location</th>
            </tr>
          </thead>
          <tbody>
            {customers.map(customer => (
              <tr key={customer.id}>
                <td>{customer.id}</td>
                <td>{customer.name}</td>
                <td>{customer.phone || '-'}</td>
                <td>{customer.email || '-'}</td>
                <td>{customer.location || '-'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
```

### Readings Page

```jsx
// frontend/src/pages/ReadingsPage.jsx
import { useState, useEffect } from 'react';
import { fetchReadings, addReading, fetchCustomers } from '../api/adminApi';

export default function ReadingsPage() {
  const [readings, setReadings] = useState([]);
  const [customers, setCustomers] = useState([]);
  const [selectedCustomer, setSelectedCustomer] = useState('');
  const [readingValue, setReadingValue] = useState('');

  async function loadData() {
    const [readingsData, customersData] = await Promise.all([
      fetchReadings(),
      fetchCustomers()
    ]);
    setReadings(readingsData);
    setCustomers(customersData);
  }

  useEffect(() => {
    loadData();
  }, []);

  async function handleSubmit(e) {
    e.preventDefault();
    if (!selectedCustomer || !readingValue) return;
    
    await addReading(parseInt(selectedCustomer), parseFloat(readingValue));
    setReadingValue('');
    setSelectedCustomer('');
    loadData();
  }

  return (
    <div>
      <header className="page-header">
        <div>
          <h1 className="page-title">Meter Readings</h1>
          <p className="page-description">Record water meter readings</p>
        </div>
      </header>

      <form onSubmit={handleSubmit} className="card">
        <select
          className="select"
          value={selectedCustomer}
          onChange={e => setSelectedCustomer(e.target.value)}
          required
        >
          <option value="">Select Customer</option>
          {customers.map(c => (
            <option key={c.id} value={c.id}>{c.name} (ID: {c.id})</option>
          ))}
        </select>
        <input
          className="input"
          type="number"
          step="0.01"
          placeholder="Reading Value (m³)"
          value={readingValue}
          onChange={e => setReadingValue(e.target.value)}
          required
        />
        <button type="submit" className="button">Add Reading</button>
      </form>

      <div className="table-wrapper">
        <table>
          <thead>
            <tr>
              <th>ID</th>
              <th>Customer ID</th>
              <th>Reading (m³)</th>
              <th>Recorded At</th>
            </tr>
          </thead>
          <tbody>
            {readings.map(reading => (
              <tr key={reading.id}>
                <td>{reading.id}</td>
                <td>{reading.customer_id}</td>
                <td>{reading.reading_value}</td>
                <td>{new Date(reading.recorded_at).toLocaleString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
```

### Invoices Page

```jsx
// frontend/src/pages/InvoicesPage.jsx
import { useState, useEffect } from 'react';
import { fetchInvoices, generateInvoice, payInvoice, fetchCustomers } from '../api/adminApi';

export default function InvoicesPage() {
  const [invoices, setInvoices] = useState([]);
  const [customers, setCustomers] = useState([]);
  const [selectedCustomer, setSelectedCustomer] = useState('');

  async function loadData() {
    const [invoicesData, customersData] = await Promise.all([
      fetchInvoices(),
      fetchCustomers()
    ]);
    setInvoices(invoicesData);
    setCustomers(customersData);
  }

  useEffect(() => {
    loadData();
  }, []);

  async function handleGenerate(e) {
    e.preventDefault();
    if (!selectedCustomer) return;
    
    await generateInvoice(parseInt(selectedCustomer));
    setSelectedCustomer('');
    loadData();
  }

  async function handlePay(invoiceId) {
    await payInvoice(invoiceId);
    loadData();
  }

  function getStatusBadge(status) {
    const classes = {
      pending: 'badge badge--warning',
      paid: 'badge badge--success',
      overdue: 'badge badge--danger'
    };
    return <span className={classes[status] || 'badge'}>{status}</span>;
  }

  return (
    <div>
      <header className="page-header">
        <div>
          <h1 className="page-title">Invoices</h1>
          <p className="page-description">Manage customer invoices</p>
        </div>
      </header>

      <form onSubmit={handleGenerate} className="card">
        <select
          className="select"
          value={selectedCustomer}
          onChange={e => setSelectedCustomer(e.target.value)}
          required
        >
          <option value="">Select Customer</option>
          {customers.map(c => (
            <option key={c.id} value={c.id}>{c.name} (ID: {c.id})</option>
          ))}
        </select>
        <button type="submit" className="button">Generate Invoice</button>
      </form>

      <div className="table-wrapper">
        <table>
          <thead>
            <tr>
              <th>ID</th>
              <th>Customer</th>
              <th>Amount</th>
              <th>Due Date</th>
              <th>Status</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {invoices.map(invoice => (
              <tr key={invoice.id}>
                <td>{invoice.id}</td>
                <td>{invoice.customer_id}</td>
                <td>KES {invoice.amount.toFixed(2)}</td>
                <td>{new Date(invoice.due_date).toLocaleDateString()}</td>
                <td>{getStatusBadge(invoice.status)}</td>
                <td>
                  {invoice.status !== 'paid' && (
                    <button
                      className="button button--small"
                      onClick={() => handlePay(invoice.id)}
                    >
                      Mark Paid
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
```

---

## Error Handling

### Common HTTP Errors

| Status Code | Meaning | Handling |
|-------------|---------|----------|
| 400 | Bad Request | Validate input data |
| 401 | Unauthorized | Redirect to login |
| 403 | Forbidden | Check permissions |
| 404 | Not Found | Display "Resource not found" |
| 500 | Server Error | Display "Something went wrong" |

### Error Handling Pattern

```javascript
async function fetchData() {
  try {
    const response = await fetch('/api/endpoint');
    
    if (!response.ok) {
      if (response.status === 401) {
        window.location.href = '/login';
        return;
      }
      
      const error = await response.json().catch(() => ({}));
      throw new Error(error.detail || `Error: ${response.status}`);
    }
    
    return await response.json();
  } catch (err) {
    console.error('API Error:', err);
    showNotification(err.message, 'error');
  }
}
```

### Backend Error Response Format

```json
{
  "detail": "Invalid credentials"
}
```

Or for validation errors:

```json
{
  "detail": [
    {
      "loc": ["body", "username"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

---

## Development Tips

### 1. Running Both Frontend and Backend

**Terminal 1 - Backend:**
```bash
cd c:/Users/R/Desktop/Water-Billing-System
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

**Terminal 2 - Frontend:**
```bash
cd c:/Users/R/Desktop/Water-Billing-System/frontend
npm run dev
```

### 2. Default Admin Credentials
- Username: `admin`
- Password: `changeme`

### 3. MongoDB Connection
The backend requires MongoDB to be running. If MongoDB is not available:
- The system will return limited/fallback data
- Some features may not work

### 4. Testing API in Browser
Visit `http://127.0.0.1:8000/docs` for the FastAPI Swagger UI interactive documentation.

---

## File Structure Reference

```
app/
├── main.py              # Main FastAPI application
├── crud.py              # MongoDB CRUD operations
├── schemas.py           # Pydantic schemas
├── mongodb.py           # MongoDB connection
├── notify.py            # SMS/Email/WhatsApp notifications
├── analytics.py         # Analytics service
├── models.py            # Data models
├── middleware.py        # Auth middleware

frontend/
├── src/
│   ├── App.jsx          # Main app with routing
│   ├── api/
│   │   ├── httpClient.js    # Base HTTP client
│   │   ├── adminApi.js      # Admin endpoints
│   │   └── customerApi.js   # Customer endpoints
│   └── pages/
│       ├── LoginPage.jsx
│       ├── AdminDashboardPage.jsx
│       ├── CustomersPage.jsx
│       ├── ReadingsPage.jsx
│       ├── InvoicesPage.jsx
│       └── CustomerPortalPage.jsx
└── package.json
```

---

## Additional Resources

- **FastAPI Docs**: https://fastapi.tiangolo.com
- **React Router**: https://reactrouter.com
- **MongoDB**: https://docs.mongodb.com
- **Backend README**: See `README.md` for full backend documentation
- **Frontend Docs**: See `FRONTEND_DOCS.md` for PWA features

---

*Last Updated: 2026-02-06*

