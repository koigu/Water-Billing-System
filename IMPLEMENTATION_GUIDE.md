# Multi-Tenant Water Billing System - Implementation Guide

## Table of Contents
1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Installation](#installation)
4. [Configuration](#configuration)
5. [Quick Start](#quick-start)
6. [Architecture](#architecture)
7. [API Reference](#api-reference)
8. [Testing](#testing)
9. [Troubleshooting](#troubleshooting)
10. [Migration Guide](#migration-guide)
11. [Phase 2 & 3 Roadmap](#phase-2--3-roadmap)

---

## Overview

This guide will help you implement the multi-tenant water billing system. The system transforms your single-tenant application into a SaaS-ready platform where each water provider gets their own isolated database.

### Key Benefits
- **Data Isolation**: Each provider has a dedicated database
- **Scalability**: Add unlimited providers without code changes
- **Security**: Complete separation between providers
- **White-Label Ready**: Custom branding per provider

---

## Prerequisites

Before starting, ensure you have:

### Software Requirements
- Python 3.8+
- MongoDB 4.4+
- pip (Python package manager)
- Git (for version control)

### MongoDB Setup
```bash
# Install MongoDB (Ubuntu/Debian)
sudo apt-get install mongodb

# Start MongoDB
sudo systemctl start mongodb

# Verify MongoDB is running
mongosh --eval "db.version()"
```

### Python Setup
```bash
# Check Python version
python --version  # Should be 3.8+

# Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows
```

---

## Installation

### Step 1: Clone and Navigate
```bash
cd /path/to/Water-Billing-System
```

### Step 2: Install Dependencies
```bash
# Install all dependencies
pip install -r requirements_multitenant.txt

# Verify installation
pip list | grep -E "fastapi|pymongo|passlib"
```

Expected output:
```
fastapi                 0.95.2+
pymongo                 4.5.0+
passlib                 1.7.4+
python-jose             3.3.0+
```

### Step 3: Configure Environment
```bash
# Copy template to .env
cp .env.template .env

# Edit .env with your settings
nano .env
```

---

## Configuration

### Required Settings

#### `.env` File
```env
# MongoDB Configuration
MONGODB_URL=mongodb://localhost:27017
MASTER_DB_NAME=water_billing_master

# Security (CHANGE THESE!)
JWT_SECRET=your-super-secret-jwt-key-min-32-chars

# Default Rate
RATE_PER_UNIT=1.5
```

### MongoDB Setup

#### 1. Create Admin User (if not exists)
```javascript
// In MongoDB shell
use admin
db.createUser({
  user: "admin",
  pwd: "secure_password",
  roles: ["root"]
})
```

#### 2. Enable Authentication (optional for development)
```bash
# Edit /etc/mongod.conf
security:
  authorization: enabled

# Restart MongoDB
sudo systemctl restart mongodb
```

---

## Quick Start

### Step 1: Initialize the System

#### Option A: Interactive Setup
```bash
python app/setup_first_provider.py
```

Follow the prompts:
```
============================================================
  MULTI-TENANT WATER BILLING SYSTEM
  Provider Onboarding Wizard
============================================================

Checking prerequisites...
✓ MongoDB connection successful
✓ Master database collections initialized

PROVIDER INFORMATION
Company Name: Kiambu Water Services
URL Slug: kiambu-water
Contact Email: admin@kiambu-water.com
Contact Phone: +254700000000

ADMIN USER INFORMATION
Admin Username: admin
Admin Password: ********
Admin Email: admin@kiambu-water.com

BILLING CONFIGURATION
Rate per Water Unit (KES): 1.5

Creating provider...
✓ Provider created: Kiambu Water Services
✓ Database: wb_kiambu_water_a7f3c9d2
✓ Admin user created: admin

SETUP COMPLETE!
```

#### Option B: Programmatic Setup
```python
from app import crud_providers

# Create provider
provider = crud_providers.create_provider({
    "name": "My Water Company",
    "slug": "my-water-company",
    "contact_email": "admin@mywater.com",
    "settings": {"rate_per_unit": 1.5}
})

# Create admin user
admin = crud_providers.create_admin_user({
    "provider_slug": "my-water-company",
    "username": "admin",
    "password": "securepassword123",
    "email": "admin@mywater.com",
    "is_super_admin": True
})
```

### Step 2: Start the Server
```bash
# Development
python -m uvicorn app.main_multitenant:app --reload --port 8000

# Production
gunicorn app.main_multitenant:app -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

### Step 3: Verify Installation
```bash
# Health check
curl http://localhost:8000/health

# Expected response
{
  "status": "healthy",
  "timestamp": "2026-02-06T12:00:00Z",
  "master_connected": true
}
```

---

## Architecture

### Database Structure

```
MongoDB
├── water_billing_master (Master DB)
│   ├── providers (Provider registry)
│   │   └── {id, name, slug, database_name, settings, branding, ...}
│   ├── admin_users (Admin authentication)
│   │   └── {id, provider_id, username, password_hash, ...}
│   └── provider_counter (Auto-increment IDs)
│
├── wb_kiambu_water_a7f3c9d2 (Provider DB 1)
│   ├── customers
│   ├── meter_readings
│   ├── invoices
│   ├── payments
│   ├── rate_config
│   ├── customer_auth
│   └── ...
│
└── wb_nairobi_west_x9k2m7p1 (Provider DB 2)
    ├── customers
    ├── meter_readings
    ├── invoices
    ├── payments
    └── ...
```

### Request Flow

```
Client Request
     │
     ├─► Subdomain: kiambu-water.yourdomain.com
     │       OR
     ├─► Header: X-Provider-Slug: kiambu-water
     │       OR
     └─► Query: ?provider=kiambu-water
               │
               ▼
      ProviderContextMiddleware
               │
               ▼
      Validate Provider (Master DB)
               │
               ▼
      Get Provider's Database
               │
               ▼
      Route to CRUD Operations
      (Customer, Invoice, etc.)
               │
               ▼
      Return Response
```

---

## API Reference

### Authentication

#### Admin Login
```http
POST /api/admin/login
Content-Type: application/json

{
  "username": "admin",
  "password": "password123",
  "provider_slug": "kiambu-water"
}
```

Response:
```json
{
  "access_token": "admin_eyJ...",
  "token_type": "bearer",
  "expires_in": 3600,
  "admin_user": {
    "id": 1,
    "username": "admin",
    "email": "admin@kiambu-water.com",
    "is_active": true,
    "is_super_admin": true,
    "provider_id": 1
  },
  "provider": {
    "id": 1,
    "name": "Kiambu Water Services",
    "slug": "kiambu-water"
  }
}
```

### Customers

#### List Customers
```http
GET /api/admin/customers
X-Provider-Slug: kiambu-water
Authorization: Bearer admin_eyJ...
```

Response:
```json
[
  {
    "id": 1,
    "name": "John Doe",
    "phone": "+254700000000",
    "email": "john@example.com",
    "location": "Nairobi",
    "is_active": true,
    "created_at": "2026-02-06T12:00:00Z"
  }
]
```

#### Create Customer
```http
POST /api/admin/customers
X-Provider-Slug: kiambu-water
Content-Type: application/x-www-form-urlencoded

name=John+Doe&phone=+254700000000&email=john@example.com&location=Nairobi
```

### Invoices

#### Generate Invoice
```http
POST /api/admin/invoices/generate/1
X-Provider-Slug: kiambu-water
Authorization: Bearer admin_eyJ...
```

Response:
```json
{
  "message": "Invoice generated",
  "invoice_id": 1,
  "amount": 150.0
}
```

### Provider Identification

All API endpoints require provider identification. Use one of these methods:

#### Method 1: HTTP Header (Recommended for API clients)
```http
X-Provider-Slug: kiambu-water
```

#### Method 2: Query Parameter (For testing)
```http
GET /api/admin/dashboard?provider=kiambu-water
```

#### Method 3: Subdomain (For production)
```
GET http://kiambu-water.yourdomain.com/api/admin/dashboard
```

---

## Testing

### Unit Tests
```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_rate_and_invoice.py -v

# Run with coverage
pytest tests/ --cov=app --cov-report=html
```

### Manual Testing

#### Test 1: Health Check
```bash
curl http://localhost:8000/health
```

#### Test 2: Admin Login
```bash
curl -X POST http://localhost:8000/api/admin/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"password123","provider_slug":"kiambu-water"}'
```

#### Test 3: Create Customer
```bash
curl -X POST http://localhost:8000/api/admin/customers \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -H "X-Provider-Slug: kiambu-water" \
  -H "Authorization: Bearer <token>" \
  -d "name=John Doe&phone=+254700000000&email=john@example.com"
```

#### Test 4: List Customers
```bash
curl http://localhost:8000/api/admin/customers \
  -H "X-Provider-Slug: kiambu-water" \
  -H "Authorization: Bearer <token>"
```

### Integration Testing Checklist

- [ ] Master database connects successfully
- [ ] First provider creates successfully
- [ ] Admin user can login
- [ ] Customer created in provider's database
- [ ] Data isolation verified (two providers see different data)
- [ ] Provider middleware rejects invalid providers
- [ ] Rate configuration works per provider
- [ ] Invoice generation works correctly

---

## Troubleshooting

### Common Issues

#### 1. MongoDB Connection Failed
```
Error: pymongo.errors.ServerSelectionTimeoutError
```

**Solution:**
```bash
# Check MongoDB is running
sudo systemctl status mongodb

# Check MongoDB URL in .env
MONGODB_URL=mongodb://localhost:27017

# Test connection
mongosh --eval "db.version()"
```

#### 2. Provider Not Found
```
Error: 404 Provider 'xxx' not found
```

**Solution:**
1. Verify provider slug is correct
2. Check provider is active: `python -c "from app import crud_providers; print(crud_providers.list_providers())"`
3. Ensure master database is initialized

#### 3. Admin Login Failed
```
Error: 401 Invalid credentials
```

**Solution:**
1. Verify username and password
2. Check provider slug is correct
3. Ensure admin user exists: `python -c "from app import crud_providers; print(crud_providers.list_admin_users(1))"`

#### 4. Collection Not Found
```
Error: Collection not found
```

**Solution:**
```bash
# Re-run setup to initialize collections
python app/setup_first_provider.py

# Or manually initialize
from app import mongodb_multitenant as mt_db
mt_db.init_master_collections()
```

#### 5. JWT Token Invalid
```
Error: 401 Unauthorized
```

**Solution:**
1. Check token hasn't expired (24 hours default)
2. Verify provider slug matches token's provider
3. Re-login to get new token

### Debug Mode
```bash
# Enable debug logging
export LOG_LEVEL=DEBUG
python -m uvicorn app.main_multitenant:app --reload
```

### Log Files
```bash
# Check application logs
tail -f logs/uvicorn.log
```

---

## Migration Guide

### Migrating from Single-Tenant

If you have existing data in a single-tenant system:

#### Step 1: Export Existing Data
```python
# Old single-tenant code
old_customers = list(db.customers.find())
old_invoices = list(db.invoices.find())
old_readings = list(db.meter_readings.find())
```

#### Step 2: Create New Provider
```python
# Create provider for migration
provider = crud_providers.create_provider({
    "name": "Migrated Provider",
    "slug": "migrated-provider",
    "settings": {...}
})
```

#### Step 3: Import Data
```python
# Import customers to new provider's database
for customer in old_customers:
    crud.create_customer("migrated-provider", {
        "name": customer["name"],
        "phone": customer.get("phone"),
        "email": customer.get("email"),
        "location": customer.get("location")
    })
```

---

## Phase 2 & 3 Roadmap

### Phase 2: Domain Routing & White-Label (Week 2)

#### Features
- [ ] DNS configuration for subdomains
- [ ] SSL certificates per subdomain (Let's Encrypt)
- [ ] Custom domain support
- [ ] Provider branding in UI
- [ ] Email templates with provider branding

#### Implementation
```python
# Custom domain mapping
CUSTOM_DOMAINS = {
    "billing.kiambu-water.com": "kiambu-water",
    "water.mycompany.com": "my-company"
}
```

### Phase 3: Provider Self-Service (Week 3-4)

#### Features
- [ ] Provider signup flow
- [ ] Billing/subscription management
- [ ] Provider admin dashboard
- [ ] Team management
- [ ] Provider analytics dashboard
- [ ] Usage-based pricing tiers

---

## Support

### Getting Help
1. Check this guide first
2. Review [QUICK_REFERENCE.md](./QUICK_REFERENCE.md)
3. Check application logs
4. Contact support

### Reporting Issues
When reporting issues, include:
- Full error message
- Steps to reproduce
- Environment details (OS, Python version, MongoDB version)
- Relevant configuration

---

## Quick Reference

| Task | Command |
|------|---------|
| Install dependencies | `pip install -r requirements_multitenant.txt` |
| Setup first provider | `python app/setup_first_provider.py` |
| Start server | `python -m uvicorn app.main_multitenant:app --reload` |
| List providers | `python -c "from app import crud_providers; print(crud_providers.list_providers())"` |
| Delete provider | `python app/setup_first_provider.py delete <slug>` |
| Run tests | `pytest tests/ -v` |

---

**Document Version:** 1.0  
**Last Updated:** 2026-02-06  
**Maintained By:** Development Team

