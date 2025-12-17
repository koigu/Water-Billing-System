# Multi-Tenant Water Billing System - Quick Reference

## 🚀 Quick Start Commands

```bash
# 1. Install dependencies
pip install -r requirements_multitenant.txt

# 2. Copy and configure environment
cp .env.template .env
nano .env

# 3. Setup first provider (interactive)
python app/setup_first_provider.py

# 4. Start the server
python -m uvicorn app.main_multitenant:app --reload --port 8000

# 5. Access the application
# Health check: http://localhost:8000/health
# Dashboard: http://localhost:8000/
```

---

## 📁 File Structure

```
Water-Billing-System/
├── app/
│   ├── main_multitenant.py      # Main FastAPI application
│   ├── models.py                # Provider & Admin schemas
│   ├── mongodb_multitenant.py  # Multi-tenant DB manager
│   ├── middleware.py           # Provider context middleware
│   ├── crud_providers.py        # Provider CRUD operations
│   ├── crud_multitent.py        # Tenant-isolated operations
│   └── setup_first_provider.py # Onboarding script
├── requirements_multitenant.txt
├── .env.template
├── IMPLEMENTATION_GUIDE.md
└── QUICK_REFERENCE.md  ← You are here
```

---

## 🔗 Endpoint Update Patterns

### Old (Single-Tenant)
```python
# OLD CODE
@app.get("/api/admin/customers")
def list_customers():
    return crud.list_customers()  # Uses single DB
```

### New (Multi-Tenant)
```python
# NEW CODE
@app.get("/api/admin/customers")
def list_customers(request: Request):
    slug = get_provider_slug(request)
    return crud.list_customers(slug)  # Uses provider's DB
```

---

## 🔐 Authentication Flow

```
1. Client sends credentials:
{
  "username": "admin",
  "password": "password123",
  "provider_slug": "kiambu-water"
}

2. Server validates against master DB
3. Returns JWT token with provider context

4. Subsequent requests:
   - Header: X-Provider-Slug: kiambu-water
   - Authorization: Bearer <token>
```

---

## 🗄️ Database Naming

| Database | Name | Purpose |
|----------|------|---------|
| Master | `water_billing_master` | Provider registry & admin users |
| Provider 1 | `wb_kiambu_water_a7f3c9d2` | Kiambu Water's data |
| Provider 2 | `wb_nairobi_west_x9k2m7p1` | Nairobi West's data |

---

## 🏷️ Provider Identification Methods

### 1. HTTP Header (API Clients)
```http
X-Provider-Slug: kiambu-water
```

### 2. Query Parameter (Testing)
```
http://localhost:8000/api/admin/dashboard?provider=kiambu-water
```

### 3. Subdomain (Production)
```
http://kiambu-water.yourdomain.com/api/admin/dashboard
```

---

## 📊 Key API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/admin/login` | Admin login |
| GET | `/api/admin/dashboard` | Dashboard stats |
| GET | `/api/admin/customers` | List customers |
| POST | `/api/admin/customers` | Create customer |
| GET | `/api/admin/readings` | List readings |
| POST | `/api/admin/customers/{id}/readings` | Add reading |
| GET | `/api/admin/invoices` | List invoices |
| POST | `/api/admin/invoices/generate/{id}` | Generate invoice |
| POST | `/api/admin/invoices/{id}/pay` | Mark paid |
| GET | `/api/admin/rate` | Get rate config |
| POST | `/api/admin/rate` | Set rate config |

---

## 🔧 Common Tasks

### List All Providers
```bash
python app/setup_first_provider.py list
```

### Delete a Provider
```bash
python app/setup_first_provider.py delete <slug>
```

### Check Provider Connection
```python
from app import mongodb_multitenant as mt_db

# Check master DB
print(mt_db.is_master_connected())

# Get provider
provider = mt_db.get_provider("kiambu-water")
print(provider["database_name"])
```

### Create Provider Programmatically
```python
from app import crud_providers

# Create provider
provider = crud_providers.create_provider({
    "name": "My Water Company",
    "slug": "my-water",
    "contact_email": "admin@mywater.com",
    "settings": {"rate_per_unit": 1.5}
})

# Create admin
crud_providers.create_admin_user({
    "provider_slug": "my-water",
    "username": "admin",
    "password": "securepassword123",
    "is_super_admin": True
})
```

---

## 🐛 Troubleshooting

### MongoDB Connection Failed
```bash
# Check MongoDB is running
sudo systemctl status mongodb

# Test connection
mongosh --eval "db.version()"
```

### Provider Not Found (404)
```python
# Verify provider exists
from app import crud_providers
providers = crud_providers.list_providers()
print(providers)
```

### Admin Login Failed (401)
```python
# Check admin user
from app import crud_providers
admins = crud_providers.list_admin_users(provider_id=1)
print(admins)
```

### Collection Not Found
```bash
# Re-initialize collections
python -c "from app import mongodb_multitenant as mt_db; mt_db.init_master_collections()"
```

---

## 📝 Copy-Paste Commands

### Development Setup
```bash
cd /path/to/Water-Billing-System
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements_multitenant.txt
cp .env.template .env
# Edit .env with your MongoDB URL
python app/setup_first_provider.py
python -m uvicorn app.main_multitenant:app --reload
```

### Production Setup
```bash
# With systemd
sudo cp deployment/water-billing.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable water-billing
sudo systemctl start water-billing

# With Docker
docker build -t water-billing .
docker run -d -p 8000:8000 --env-file .env water-billing
```

---

## 🔐 Security Checklist

- [ ] Change `JWT_SECRET` in `.env`
- [ ] Enable MongoDB authentication
- [ ] Use HTTPS in production
- [ ] Set up CORS properly
- [ ] Regular database backups
- [ ] Rate limiting on API
- [ ] Input validation

---

## 📈 Performance Tips

1. **Connection Pooling**: Already configured in `mongodb_multitenant.py`
2. **Indexes**: Automatically created on collection initialization
3. **Caching**: Provider connections cached per process
4. **Batching**: Use bulk operations for large imports

---

## 📞 Common Errors

| Error | Cause | Solution |
|-------|-------|----------|
| 404 Provider not found | Invalid slug | Verify slug in provider list |
| 401 Unauthorized | No/invalid token | Re-login to get token |
| 400 Bad Request | Missing provider | Add X-Provider-Slug header |
| 500 Internal Error | DB not connected | Check MongoDB URL |

---

## 🔄 Migration Checklist

- [ ] Export old single-tenant data
- [ ] Create new provider
- [ ] Import customers
- [ ] Import readings
- [ ] Import invoices
- [ ] Import payments
- [ ] Test end-to-end
- [ ] Update DNS (if subdomain routing)
- [ ] Switch traffic to new system

---

## 📚 Related Documentation

- [IMPLEMENTATION_GUIDE.md](./IMPLEMENTATION_GUIDE.md) - Full implementation guide
- [README.md](./README.md) - Project overview
- [app/main_multitenant.py](./app/main_multitenant.py) - API documentation

---

**Quick Reference Version:** 1.0  
**Last Updated:** 2026-02-06

