export const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/$/, '')
const DEFAULT_PROVIDER_SLUG = (import.meta.env.VITE_DEFAULT_PROVIDER_SLUG || '').trim()

// Get token from localStorage
function getToken() {
  return localStorage.getItem('token')
}

function clearAuthState() {
  localStorage.removeItem('is_admin')
  localStorage.removeItem('is_super_admin')
  localStorage.removeItem('username')
  localStorage.removeItem('firebase_email')
  localStorage.removeItem('token')
  localStorage.removeItem('provider_slug')
}

function getProviderSlug() {
  return (localStorage.getItem('provider_slug') || DEFAULT_PROVIDER_SLUG || '').trim()
}

function withProviderQuery(path, providerSlug) {
  const slug = (providerSlug ?? getProviderSlug()).trim()
  if (!slug || !path.startsWith('/api/admin/')) {
    return path
  }

  const [pathname, queryString = ''] = path.split('?')
  const params = new URLSearchParams(queryString)
  if (!params.has('provider')) {
    params.set('provider', slug)
  }

  const query = params.toString()
  return query ? `${pathname}?${query}` : pathname
}

function buildHeaders(options = {}) {
  const token = getToken()
  const providerSlug = options.providerSlug ?? getProviderSlug()
  const headers = {
    'Content-Type': 'application/json',
    ...(options.headers || {}),
  }

  if (providerSlug) {
    headers['X-Provider-Slug'] = providerSlug
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
      if (Array.isArray(detail)) {
        detail = detail
          .map((item) => item?.msg || item?.message || JSON.stringify(item))
          .join('; ')
      } else if (detail && typeof detail === 'object') {
        detail = detail.msg || detail.message || JSON.stringify(detail)
      }
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
  const { providerSlug, ...fetchOptions } = options
  const requestPath = withProviderQuery(path, providerSlug)
  const res = await fetch(`${API_BASE_URL}${requestPath}`, {
    ...fetchOptions,
    credentials: 'include',
    headers: buildHeaders({ ...fetchOptions, providerSlug }),
  })

  return handleResponse(res, 'GET', requestPath)
}

export async function apiPost(path, body, options = {}) {
  const { providerSlug, ...fetchOptions } = options
  const requestPath = withProviderQuery(path, providerSlug)
  const res = await fetch(`${API_BASE_URL}${requestPath}`, {
    method: 'POST',
    ...fetchOptions,
    credentials: 'include',
    headers: buildHeaders({ ...fetchOptions, providerSlug }),
    body: body ? JSON.stringify(body) : undefined,
  })

  return handleResponse(res, 'POST', requestPath)
}

export async function apiPut(path, body, options = {}) {
  const { providerSlug, ...fetchOptions } = options
  const requestPath = withProviderQuery(path, providerSlug)
  const res = await fetch(`${API_BASE_URL}${requestPath}`, {
    method: 'PUT',
    ...fetchOptions,
    credentials: 'include',
    headers: buildHeaders({ ...fetchOptions, providerSlug }),
    body: body ? JSON.stringify(body) : undefined,
  })

  return handleResponse(res, 'PUT', requestPath)
}

export async function apiDelete(path, options = {}) {
  const { providerSlug, ...fetchOptions } = options
  const requestPath = withProviderQuery(path, providerSlug)
  const res = await fetch(`${API_BASE_URL}${requestPath}`, {
    method: 'DELETE',
    ...fetchOptions,
    credentials: 'include',
    headers: buildHeaders({ ...fetchOptions, providerSlug }),
  })

  return handleResponse(res, 'DELETE', requestPath)
}
