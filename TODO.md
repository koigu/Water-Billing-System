 # Water Billing System - MongoDB Analytics Integration

## Overview
Enhance the Water Billing System with MongoDB for advanced analytics, payment analysis, and customer behavior tracking while keeping SQLite for transactional data.

## MongoDB Collections

### 1. usage_trends
Aggregated water usage data for analytics
```json
{
  "_id": ObjectId,
  "customer_id": int,
  "month": string,      // "2024-01"
  "year": int,
  "total_usage": float, // cubic meters
  "readings_count": int,
  "avg_reading": float,
  "min_reading": float,
  "max_reading": float,
  "created_at": datetime
}
```

### 2. payment_analytics
Payment method preferences and timing analysis
```json
{
  "_id": ObjectId,
  "customer_id": int,
  "invoice_id": int,
  "payment_method": string,  // "stripe", "paypal", "cash", "bank_transfer"
  "payment_date": datetime,
  "days_to_pay": int,        // days from due date (negative = early)
  "amount": float,
  "month": string,
  "year": int
}
```

### 3. customer_behavior
Customer behavior patterns and profiles
```json
{
  "_id": ObjectId,
  "customer_id": int,
  "total_invoices": int,
  "total_paid": float,
  "avg_payment_days": float,
  "preferred_payment_method": string,
  "avg_monthly_usage": float,
  "payment_rate": float,     // percentage of invoices paid on time
  "status": string,          // "active", "inactive", "at_risk"
  "last_activity": datetime,
  "created_at": datetime,
  "updated_at": datetime
}
```

### 4. staff_metrics
Staff performance tracking
```json
{
  "_id": ObjectId,
  "staff_id": string,
  "month": string,
  "year": int,
  "invoices_generated": int,
  "payments_collected": float,
  "customers_added": int,
  "readings_recorded": int,
  "efficiency_score": float,
  "created_at": datetime
}
```

### 5. reminder_config
Manager-adjustable reminder settings
```json
{
  "_id": ObjectId,
  "reminder_days": int,      // days after due date to send reminder
  "auto_resend_invoice": bool,
  "max_reminders": int,
  "updated_by": string,
  "updated_at": datetime
}
```

## Implementation Status

### Phase 1: MongoDB Connection & Setup ✅ COMPLETED
- [x] Add pymongo to requirements.txt
- [x] Create app/mongodb.py for MongoDB connection
- [x] Add MongoDB config to .env example
- [x] Create analytics models/schemas

### Phase 2: Data Sync Services ✅ COMPLETED
- [x] Create sync_usage_trends.py - Sync meter readings to usage_trends
- [x] Create sync_payment_analytics.py - Sync payments to analytics
- [x] Create sync_customer_behavior.py - Update customer profiles
- [x] Create sync_staff_metrics.py - Track staff performance

### Phase 3: Analytics API Endpoints ✅ COMPLETED
- [x] GET /api/analytics/usage/monthly - Monthly usage trends
- [x] GET /api/analytics/usage/yearly - Yearly usage trends
- [x] GET /api/analytics/usage/customer/{id} - Customer usage profile
- [x] GET /api/analytics/payments/methods - Payment preferences
- [x] GET /api/analytics/payments/timing - Payment timing analysis
- [x] GET /api/analytics/customers/active - Active/inactive counts
- [x] GET /api/analytics/customers/{id}/profile - Full customer profile
- [x] GET /api/analytics/staff/trends - Staff performance
- [x] GET /api/admin/settings/reminder-days - Get reminder config
- [x] PUT /api/admin/settings/reminder-days - Update reminder config
- [x] GET /api/analytics/staff/top - Top performing staff

### Phase 4: Data Sync API Routes ✅ COMPLETED
- [x] POST /api/admin/sync/analytics - Full sync to MongoDB
- [x] POST /api/admin/sync/usage/{customer_id} - Sync customer usage
- [x] POST /api/admin/sync/customer-behavior/{customer_id} - Sync behavior
- [x] GET /api/admin/mongodb/status - Check MongoDB connection

### Phase 5: Remaining Tasks
- [ ] Update check_and_remind to use configurable reminder days
- [ ] Add scheduled sync job for analytics
- [ ] PDF receipt generation
- [ ] Frontend analytics dashboard

## API Response Examples

### Monthly Usage Trends
```json
{
  "month": "2024-01",
  "total_usage": 1250.5,
  "customer_count": 46,
  "avg_usage_per_customer": 27.19,
  "comparison_to_last_month": 5.2,
  "comparison_to_last_year": 12.3
}
```

### Payment Methods Analysis
```json
{
  "methods": [
    {"method": "stripe", "count": 150, "percentage": 45.0},
    {"method": "paypal", "count": 80, "percentage": 24.0},
    {"method": "cash", "count": 70, "percentage": 21.0},
    {"method": "bank_transfer", "count": 33, "percentage": 10.0}
  ],
  "preferred_method": "stripe",
  "trend": "increasing"  // or "stable", "decreasing"
}
```

### Customer Profile
```json
{
  "customer_id": 1,
  "name": "John Doe",
  "total_invoices": 12,
  "total_paid": 2450.00,
  "avg_monthly_usage": 28.5,
  "preferred_payment_method": "stripe",
  "avg_payment_days": -3.5,  // pays 3.5 days early
  "payment_rate": 92.0,
  "status": "active",
  "usage_trends": [...],
  "payment_history": [...]
}
```

## Files to Create/Modify

### New Files
- `app/mongodb.py` - MongoDB connection
- `app/analytics.py` - Analytics service
- `app/sync_analytics.py` - Data sync functions
- `app/schemas_analytics.py` - Pydantic schemas for analytics

### Modified Files
- `requirements.txt` - Add pymongo
- `app/main.py` - Add analytics endpoints
- `app/crud.py` - Add analytics CRUD functions
- `app/models.py` - (No changes needed, using MongoDB)

## Environment Variables to Add
```
MONGODB_URL=mongodb://localhost:27017
MONGODB_DB=water_billing_analytics
```

## Testing Checklist
- [ ] MongoDB connection works
- [ ] Usage trends sync correctly
- [ ] Payment analytics captured
- [ ] Customer profiles updated
- [ ] Staff metrics tracked
- [ ] Reminder config saves/loads
- [ ] All endpoints return correct data
- [ ] Scheduled jobs run without errors

