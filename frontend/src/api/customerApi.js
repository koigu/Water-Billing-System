import { API_BASE_URL } from './httpClient'

const DEFAULT_PROVIDER_SLUG = (import.meta.env.VITE_DEFAULT_PROVIDER_SLUG || '').trim()

function getProviderSlug() {
  return (localStorage.getItem('provider_slug') || DEFAULT_PROVIDER_SLUG || '').trim()
}

function withProvider(path, providerSlug = getProviderSlug()) {
  const slug = (providerSlug || '').trim()
  if (!slug) return path
  const [pathname, queryString = ''] = path.split('?')
  const params = new URLSearchParams(queryString)
  if (!params.has('provider')) {
    params.set('provider', slug)
  }
  const query = params.toString()
  return query ? `${pathname}?${query}` : pathname
}

function providerHeaders(providerSlug = getProviderSlug()) {
  return providerSlug ? { 'X-Provider-Slug': providerSlug } : {}
}

async function parseResponse(res, method, path) {
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

export async function customerLogin(username, password, providerSlug) {
  const path = withProvider('/api/customer/login', providerSlug)
  const res = await fetch(`${API_BASE_URL}${path}`, {
    method: 'POST',
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
      ...providerHeaders(providerSlug),
    },
    body: JSON.stringify({ username, password }),
  })
  return parseResponse(res, 'POST', path)
}

export function customerRegister(customerId, username, password, providerSlug) {
  const path = withProvider('/api/auth/register', providerSlug)
  const formData = new FormData()
  const slug = (providerSlug || getProviderSlug()).trim()
  if (slug) {
    formData.append('provider_slug', slug)
  }
  formData.append('customer_id', customerId)
  formData.append('username', username)
  formData.append('password', password)

  return fetch(`${API_BASE_URL}${path}`, {
    method: 'POST',
    credentials: 'include',
    headers: {
      ...providerHeaders(providerSlug),
    },
    body: formData,
  }).then((res) => parseResponse(res, 'POST', path))
}

export async function fetchPortalData(token, providerSlug) {
  const path = withProvider('/api/customer/portal', providerSlug)
  const res = await fetch(`${API_BASE_URL}${path}`, {
    method: 'GET',
    credentials: 'include',
    headers: {
      Authorization: `Bearer ${token}`,
      ...providerHeaders(providerSlug),
    },
  })
  return parseResponse(res, 'GET', path)
}
