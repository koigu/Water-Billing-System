import { API_BASE_URL } from './httpClient'

async function parseResponse(res, method, path) {
  if (!res.ok) {
    let detail = ''
    try {
      const data = await res.json()
      detail = data?.detail || data?.message || ''
    } catch {
      // ignore parse errors
    }
    throw new Error(
      detail
        ? `${method} ${path} failed: ${res.status} - ${detail}`
        : `${method} ${path} failed: ${res.status}`
    )
  }
  return res.json()
}

export async function customerLogin(username, password) {
  const path = '/api/customer/login'
  const res = await fetch(`${API_BASE_URL}${path}`, {
    method: 'POST',
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ username, password }),
  })
  return parseResponse(res, 'POST', path)
}

export function customerRegister(customerId, username, password) {
  const path = '/api/auth/register'
  const formData = new FormData()
  formData.append('customer_id', customerId)
  formData.append('username', username)
  formData.append('password', password)

  return fetch(`${API_BASE_URL}${path}`, {
    method: 'POST',
    credentials: 'include',
    body: formData,
  }).then((res) => parseResponse(res, 'POST', path))
}

export async function fetchPortalData(token) {
  const path = '/api/customer/portal'
  const res = await fetch(`${API_BASE_URL}${path}`, {
    method: 'GET',
    credentials: 'include',
    headers: {
      Authorization: `Bearer ${token}`,
    },
  })
  return parseResponse(res, 'GET', path)
}
