import { apiGet, apiPost } from './httpClient'

export function fetchDashboard() {
  return apiGet('/api/admin/dashboard')
}

export function fetchCustomers() {
  return apiGet('/api/admin/customers')
}

export function createCustomer(payload) {
  return apiPost('/api/admin/customers', payload)
}

export function fetchReadings() {
  return apiGet('/api/admin/readings')
}

export function addReading(customerId, readingValue) {
  return apiPost(`/api/admin/customers/${customerId}/readings`, { reading_value: readingValue })
}

export function fetchInvoices() {
  return apiGet('/api/admin/invoices')
}

export function generateInvoice(customerId) {
  return apiPost(`/api/admin/invoices/generate/${customerId}`)
}

export function payInvoice(invoiceId) {
  return apiPost(`/api/admin/invoices/${invoiceId}/pay`)
}

export function fetchRate() {
  return apiGet('/api/admin/rate')
}

export function updateRate(mode, value) {
  return apiPost('/api/admin/rate', { mode, value })
}
