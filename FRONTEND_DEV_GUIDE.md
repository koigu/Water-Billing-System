# Frontend Developer Guide - Backend Changes

## Recent Backend Changes

### 1. Invoice Generation Fix (500 Error Fix)
**File:** `app/main.py`

The invoice generation endpoint was returning a 500 Internal Server Error. This has been fixed by:
- Adding try-except blocks around notification calls to prevent crashes
- The invoice will now be created even if SMS/email notifications fail
- Error logging has been added for failed notifications

**Endpoint:** `POST /invoices/generate/{customer_id}`
- Returns: 303 Redirect on success
- Previously: 500 Internal Server Error

### 2. Africa's Talking SMS Configuration
**File:** `.env`

Added the following environment variables:
```
AFRICAS_TALKING_USERNAME=celebration
AFRICAS_TALKING_API_KEY=celebration
AFRICAS_TALKING_IS_SANDBOX=true
SMS_PROVIDER=africas_talking
```

## Frontend Tasks

### 1. Update Invoice Generation UI
The frontend should handle the invoice generation response properly:

```javascript
// Example: Handle invoice generation
async function generateInvoice(customerId) {
    try {
        const response = await fetch(`/invoices/generate/${customerId}`, {
            method: 'POST'
        });
        
        if (response.ok) {
            // Success - redirect or show success message
            window.location.href = '/';
        } else if (response.status === 400) {
            // Bad request - not enough readings
            const data = await response.json();
            alert(data.detail || 'Not enough meter readings to generate invoice');
        } else if (response.status === 401) {
            // Unauthorized
            alert('Please login first');
            window.location.href = '/login';
        } else {
            // Other errors
            alert('Failed to generate invoice');
        }
    } catch (error) {
        console.error('Error:', error);
        alert('An error occurred while generating the invoice');
    }
}
```

### 2. API Endpoints Reference

The backend now supports these API endpoints:

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/invoices/generate/{customer_id}` | Generate invoice for customer |
| POST | `/api/admin/invoices/generate/{customer_id}` | Generate invoice (API with auth) |
| POST | `/api/admin/invoices/bulk-generate` | Generate invoices for multiple customers |
| POST | `/api/admin/invoices/{id}/pay` | Mark invoice as paid |
| POST | `/api/admin/invoices/{id}/send-reminder` | Send invoice reminder |
| POST | `/api/admin/invoices/{id}/send-reminder` | Send reminder to customer |
| GET | `/api/admin/invoices` | List all invoices |

### 3. Error Handling Improvements

The backend now returns proper HTTP status codes:
- `200` - Success
- `400` - Bad Request (e.g., not enough readings)
- `401` - Unauthorized
- `404` - Not Found
- `500` - Internal Server Error (should be rare now)

### 4. Testing Checklist

Please verify:
- [ ] Invoice generation works without crashing
- [ ] Appropriate error messages shown to users
- [ ] Loading states during invoice generation
- [ ] Invoice list refreshes after generation
- [ ] Mobile responsive design still works

## Notes for Frontend

1. **Authentication:** The API endpoints require Bearer token authentication. Store the token from login and include in headers:
   ```javascript
   headers: {
       'Authorization': `Bearer ${token}`
   }
   ```

2. **Rate Configuration:** The rate can be either "fixed" (flat rate) or "percent" (percentage above base rate). Display this appropriately.

3. **Invoice Status:** Invoices can have status: "pending", "paid", "overdue", "cancelled"

4. **Meter Readings:** Customers need at least 2 meter readings before an invoice can be generated.

## Contact

For questions about backend API changes, refer to:
- `app/main.py` - Main application routes
- `app/crud.py` - Database operations  
- `app/notify.py` - Notification system

