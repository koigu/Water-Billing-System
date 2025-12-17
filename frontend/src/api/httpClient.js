const API_BASE_URL = 'http://127.0.0.1:8000'
const PROVIDER_SLUG = 'celebration-water'  // Default provider

// Get token from localStorage
function getToken() {
  return localStorage.getItem('token')
}

export async function apiGet(path, options = {}) {
  const token = getToken()
  const res = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
      'X-Provider-Slug': PROVIDER_SLUG,
      'Authorization': token ? `Bearer ${token}` : '',
      ...(options.headers || {}),
    },
  })

  if (!res.ok) {
    throw new Error(`GET ${path} failed: ${res.status}`)
  }

  return res.json()
}

export async function apiPost(path, body, options = {}) {
  const token = getToken()
  const res = await fetch(`${API_BASE_URL}${path}`, {
    method: 'POST',
    ...options,
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
      'X-Provider-Slug': PROVIDER_SLUG,
      'Authorization': token ? `Bearer ${token}` : '',
      ...(options.headers || {}),
    },
    body: body ? JSON.stringify(body) : undefined,
  })

  if (!res.ok) {
    throw new Error(`POST ${path} failed: ${res.status}`)
  }

  return res.json()
}
