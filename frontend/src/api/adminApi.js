import { apiDelete, apiGet, apiPost, apiPut } from './httpClient'

export function fetchDashboard() {
  return apiGet('/api/admin/dashboard')
}

export function fetchCustomers() {
  return apiGet('/api/admin/customers')
}

export function createCustomer(payload) {
  return apiPost('/api/admin/customers', payload).then((res) => res.customer || res)
}

export function updateCustomer(customerId, payload) {
  return apiPut(`/api/admin/customers/${customerId}`, payload).then((res) => res.customer || res)
}

export function deleteCustomer(customerId) {
  return apiDelete(`/api/admin/customers/${customerId}`)
}

export function bulkDeleteCustomers(customerIds) {
  return apiPost('/api/admin/customers/bulk-delete', { customer_ids: customerIds })
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

export function bulkGenerateInvoices(customerIds) {
  return apiPost('/api/admin/invoices/bulk-generate', { customer_ids: customerIds })
}

export function payInvoice(invoiceId) {
  return apiPost(`/api/admin/invoices/${invoiceId}/pay`).then((res) => res.invoice || res)
}

export function sendInvoiceReminder(invoiceId) {
  return apiPost(`/api/admin/invoices/${invoiceId}/send-reminder`)
}

export function bulkSendReminders(invoiceIds) {
  return apiPost('/api/admin/reminders/bulk-send', { invoice_ids: invoiceIds })
}

export function fetchRate() {
  return apiGet('/api/admin/rate')
}

export function updateRate(mode, value) {
  return apiPost('/api/admin/rate', { mode, value })
}

export function fetchSuperAdminDashboard() {
  return apiGet('/api/super-admin/dashboard')
}

export function fetchProviders() {
  return apiGet('/api/super-admin/providers')
}

export function createProvider(payload) {
  return apiPost('/api/super-admin/providers', payload).then((res) => res.provider || res)
}

export function updateProvider(providerSlug, payload) {
  return apiPut(`/api/super-admin/providers/${providerSlug}`, payload).then((res) => res.provider || res)
}

export function activateProvider(providerSlug) {
  return apiPost(`/api/super-admin/providers/${providerSlug}/activate`)
}

export function deactivateProvider(providerSlug) {
  return apiPost(`/api/super-admin/providers/${providerSlug}/deactivate`)
}
