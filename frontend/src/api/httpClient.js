const API_BASE_URL = 'http://127.0.0.1:8000'
const PROVIDER_SLUG = 'celebration-water'  // Default provider

// Get token from localStorage
function getToken() {
  return localStorage.getItem('token')
}

function clearAuthState() {
  localStorage.removeItem('is_admin')
  localStorage.removeItem('is_super_admin')
  localStorage.removeItem('username')
  localStorage.removeItem('token')
  localStorage.removeItem('provider_slug')
}

function buildHeaders(options = {}) {
  const token = getToken()
  const providerSlug = localStorage.getItem('provider_slug') || PROVIDER_SLUG
  const headers = {
    'Content-Type': 'application/json',
    'X-Provider-Slug': providerSlug,
    ...(options.headers || {}),
  }

  if (token) {
    headers.Authorization = `Bearer ${token}`
  }

  return headers
}

async function handleResponse(res, method, path) {
  if (res.status === 401) {
    clearAuthState()
    if (window.location.pathname !== '/login') {
      window.location.href = '/login'
    }
    throw new Error(`${method} ${path} failed: 401`)
  }

  if (!res.ok) {
    let detail = ''
    try {
      const data = await res.json()
      detail = data?.detail || data?.message || ''
    } catch {
      // Ignore parse errors and fall back to status-only message
    }
    throw new Error(
      detail
        ? `${method} ${path} failed: ${res.status} - ${detail}`
        : `${method} ${path} failed: ${res.status}`
    )
  }

  return res.json()
}

export async function apiGet(path, options = {}) {
  const res = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    credentials: 'include',
    headers: buildHeaders(options),
  })

  return handleResponse(res, 'GET', path)
}

export async function apiPost(path, body, options = {}) {
  const res = await fetch(`${API_BASE_URL}${path}`, {
    method: 'POST',
    ...options,
    credentials: 'include',
    headers: buildHeaders(options),
    body: body ? JSON.stringify(body) : undefined,
  })

  return handleResponse(res, 'POST', path)
}

export async function apiPut(path, body, options = {}) {
  const res = await fetch(`${API_BASE_URL}${path}`, {
    method: 'PUT',
    ...options,
    credentials: 'include',
    headers: buildHeaders(options),
    body: body ? JSON.stringify(body) : undefined,
  })

  return handleResponse(res, 'PUT', path)
}

export async function apiDelete(path, options = {}) {
  const res = await fetch(`${API_BASE_URL}${path}`, {
    method: 'DELETE',
    ...options,
    credentials: 'include',
    headers: buildHeaders(options),
  })

  return handleResponse(res, 'DELETE', path)
}
