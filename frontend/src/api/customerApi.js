import { apiGet, apiPost } from './httpClient'

export function customerLogin(username, password) {
  return apiPost('/api/auth/login', { username, password })
}

export function customerRegister(customerId, username, password) {
  const formData = new FormData()
  formData.append('customer_id', customerId)
  formData.append('username', username)
  formData.append('password', password)

  return fetch('http://127.0.0.1:8000/api/auth/register', {
    method: 'POST',
    credentials: 'include',
    body: formData,
  }).then((res) => {
    if (!res.ok) {
      throw new Error(`Register failed: ${res.status}`)
    }
    return res.json()
  })
}

export function fetchPortalData(token) {
  return apiGet('/api/customer/portal', {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  })
}

export function createPayment(token, payment) {
  return apiPost('/api/customer/payments', payment, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  })
}

export function markAlertRead(token, alertId) {
  return apiPost(`/api/customer/alerts/${alertId}/read`, null, {
    method: 'PUT',
    headers: {
      Authorization: `Bearer ${token}`,
    },
  })
}
