"""
Water Billing System - MongoDB-Only Implementation.
Complete rewrite using MongoDB instead of SQLite/SQLAlchemy.
"""
import os
from fastapi import FastAPI, HTTPException, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, timedelta
from dotenv import load_dotenv
from app import crud, notify, mongodb
from app import schemas
import logging
import csv
import io
import base64
import os
from typing import List, Optional
from pydantic import BaseModel
from bson import ObjectId

load_dotenv()

logger = logging.getLogger("uvicorn")
logging.basicConfig(level=logging.INFO)

templates = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__), "../templates"))

app = FastAPI(title="Water Billing System")

# CORS middleware for frontend-backend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Session middleware for user authentication
# Configure session to work with cross-origin requests
app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("SECRET_KEY", "your-secret-key-change-in-production"),
    max_age=3600 * 24,  # 24 hours
    session_cookie="session",
    same_site="lax",  # Allow cookies to work in same-site context
    https_only=False,  # Allow in development (set to True in production with HTTPS)
)


def check_admin_auth(request: Request) -> bool:
    """Check if admin is authenticated via session or Bearer token."""
    # Check session first
    if request.session.get("is_admin"):
        return True
    
    # Check Authorization header for Bearer token
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
        # For development: accept any non-empty token from localStorage
        # In production, you would validate against a database or cache
        if token and len(token) > 10:
            return True
    
    return False


class CustomerUpdatePayload(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    location: Optional[str] = None


class BulkCustomerDeletePayload(BaseModel):
    customer_ids: List[int]


class BulkInvoiceGeneratePayload(BaseModel):
    customer_ids: List[int]


class BulkReminderPayload(BaseModel):
    invoice_ids: List[int]


def serialize_mongo(data):
    """Convert MongoDB ObjectId values to JSON-safe strings and drop internal _id keys."""
    if isinstance(data, list):
        return [serialize_mongo(item) for item in data]
    if isinstance(data, dict):
        return {
            key: serialize_mongo(value)
            for key, value in data.items()
            if key != "_id"
        }
    if isinstance(data, ObjectId):
        return str(data)
    return data


def generate_invoice_for_customer(customer_id: int):
    """Generate an invoice for a customer and return (invoice, error_message)."""
    rate = crud.get_effective_rate()
    calc = crud.calculate_amount_from_readings(customer_id, rate)
    if not calc:
        return None, "Not enough readings to calculate invoice"

    amount, billing_from, billing_to = calc
    due_date = datetime.utcnow() + timedelta(days=15)
    customer = crud.get_customer(customer_id)
    if not customer:
        return None, "Customer not found"

    inv = crud.create_invoice(customer_id, amount, due_date, customer.get("location"))
    if customer:
        notify.send_invoice_message(customer, inv, method="all")
    return inv, None


# Mount static files
app.mount("/static", StaticFiles(directory=os.path.join(os.path.dirname(__file__), "../static")), name="static")


def init_db():
    """Initialize MongoDB collections and indexes."""
    if mongodb.is_connected():
        mongodb.init_collections()
        mongodb.init_counter(mongodb.get_db())


@app.on_event("startup")
def startup_event():
    init_db()
    # Start scheduler
    scheduler = BackgroundScheduler()
    scheduler.add_job(check_and_remind, "interval", minutes=60, next_run_time=datetime.utcnow())
    scheduler.start()
    app.state.scheduler = scheduler


@app.on_event("shutdown")
def shutdown_event():
    sched = getattr(app.state, "scheduler", None)
    if sched:
        sched.shutdown()
    mongodb.close_connection()


# ==================== PAGE ROUTES ====================

@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    customers = crud.list_customers()
    invoices = crud.list_invoices()
    rate = crud.get_rate_config()
    effective = crud.get_effective_rate()
    stats = crud.get_dashboard_stats()
    is_admin = request.session.get("is_admin", False)
    username = request.session.get("username")
    return templates.TemplateResponse("index.html", {
        "request": request,
        "customers": customers,
        "invoices": invoices,
        "rate": rate,
        "effective_rate": effective,
        "stats": stats,
        "is_admin": is_admin,
        "username": username
    })


@app.get("/customers", response_class=HTMLResponse)
def customers_page(request: Request, search: str = None):
    if search and search.strip():
        customers = crud.search_customers_by_name(search.strip())
        search_performed = True
        search_term = search.strip()
    else:
        customers = crud.list_customers()
        search_performed = False
        search_term = ""

    is_admin = request.session.get("is_admin", False)
    username = request.session.get("username")
    return templates.TemplateResponse("customers.html", {
        "request": request,
        "customers": customers,
        "is_admin": is_admin,
        "username": username,
        "search_performed": search_performed,
        "search_term": search_term
    })


@app.get("/readings", response_class=HTMLResponse)
def readings_page(request: Request):
    customers = crud.list_customers()
    readings = crud.get_all_readings()
    is_admin = request.session.get("is_admin", False)
    username = request.session.get("username")
    return templates.TemplateResponse("readings.html", {
        "request": request,
        "readings": readings,
        "customers": customers,
        "is_admin": is_admin,
        "username": username
    })


@app.get("/invoices", response_class=HTMLResponse)
def invoices_page(request: Request):
    invoices = crud.list_invoices()
    is_admin = request.session.get("is_admin", False)
    username = request.session.get("username")
    return templates.TemplateResponse("invoices.html", {
        "request": request,
        "invoices": invoices,
        "is_admin": is_admin,
        "username": username
    })


# ==================== FORM ACTION ROUTES ====================

@app.post("/customers")
def create_customer(
    name: str = Form(...),
    phone: str = Form(None),
    email: str = Form(None),
    location: str = Form(None),
    initial_reading: float = Form(None)
):
    customer_data = {
        "name": name,
        "phone": phone,
        "email": email,
        "location": location,
        "initial_reading": initial_reading
    }
    crud.create_customer(customer_data)
    return RedirectResponse(url="/", status_code=303)


@app.post("/customers/{customer_id}/readings")
def add_reading(customer_id: int, reading_value: float = Form(...)):
    customer = crud.get_customer(customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    crud.add_reading(customer_id, reading_value)
    return RedirectResponse(url="/", status_code=303)


@app.post("/invoices/generate/{customer_id}")
def generate_invoice(customer_id: int):
    rate = crud.get_effective_rate()
    calc = crud.calculate_amount_from_readings(customer_id, rate)
    if not calc:
        raise HTTPException(status_code=400, detail="Not enough readings to calculate invoice")
    
    amount, billing_from, billing_to = calc
    due_date = datetime.utcnow() + timedelta(days=15)
    customer = crud.get_customer(customer_id)
    
    inv = crud.create_invoice(customer_id, amount, due_date, customer.get("location") if customer else None)
    
    # Send invoice notification
    if customer:
        notify.send_invoice_message(customer, inv, method="all")
    
    # Update invoice with sent time
    db = mongodb.get_db()
    if db:
        db["invoices"].update_one(
            {"id": inv.get("id")},
            {"$set": {"sent_at": datetime.utcnow()}}
        )
    
    return RedirectResponse(url="/", status_code=303)


@app.post("/invoices/{invoice_id}/pay")
def pay_invoice(invoice_id: int):
    inv = crud.mark_invoice_paid(invoice_id)
    if not inv:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return RedirectResponse(url="/", status_code=303)


@app.post('/rate')
def set_rate(mode: str = Form(...), value: float = Form(...), request: Request = None):
    if not request or not request.session.get("is_admin"):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    if mode not in ("fixed", "percent"):
        raise HTTPException(status_code=400, detail="Invalid mode")
    
    crud.set_rate_config(mode, value)
    return RedirectResponse(url='/', status_code=303)


# ==================== AUTH ROUTES ====================

@app.get('/login', response_class=HTMLResponse)
def login_form(request: Request):
    return templates.TemplateResponse('login.html', {'request': request})


@app.post('/login')
def login(username: str = Form(...), password: str = Form(...), request: Request = None):
    # SECURITY FIX: Require ADMIN_USERNAME and ADMIN_PASSWORD env variables
    # If not set, deny login (no hardcoded defaults!)
    admin_user = os.getenv('ADMIN_USERNAME')
    admin_pass = os.getenv('ADMIN_PASSWORD')
    
    if not admin_user or not admin_pass:
        raise HTTPException(status_code=403, detail='Admin credentials not configured')
    
    if username == admin_user and password == admin_pass:
        request.session['is_admin'] = True
        request.session['username'] = username
        return RedirectResponse(url='/', status_code=303)
    
    raise HTTPException(status_code=403, detail='Invalid credentials')


@app.post('/api/admin/login')
def api_login(request: Request, credentials: schemas.LoginCredentials):
    """Admin login API endpoint - authenticates against super admins in MongoDB"""
    from app import crud_providers
    import secrets
    
    # Try to authenticate as super admin first
    admin = crud_providers.authenticate_super_admin(credentials.username, credentials.password)
    
    if admin:
        # Generate a simple token
        token = secrets.token_urlsafe(32)
        request.session['is_admin'] = True
        request.session['is_super_admin'] = True
        request.session['username'] = admin['username']
        request.session['admin_id'] = admin['id']
        request.session['token'] = token
        return {"message": "Login successful", "username": admin['username'], "token": token}
    
    # If not super admin, try provider admin authentication
    # Get all providers and check each one
    try:
        from app import mongodb_multitenant as mt_db
        providers = mt_db.list_providers()
        
        for provider in providers:
            admin = crud_providers.authenticate_admin(
                credentials.username, 
                credentials.password, 
                provider['slug']
            )
            if admin:
                # Generate a simple token
                token = secrets.token_urlsafe(32)
                request.session['is_admin'] = True
                request.session['is_super_admin'] = admin.get('is_super_admin', False)
                request.session['username'] = admin['username']
                request.session['admin_id'] = admin['id']
                request.session['provider_slug'] = provider['slug']
                request.session['token'] = token
                return {"message": "Login successful", "username": admin['username'], "token": token}
    except Exception as e:
        logger.error(f"Error checking provider admins: {e}")
    
    # Also check environment variables for simple auth
    # SECURITY FIX: Require ADMIN_USERNAME and ADMIN_PASSWORD env variables
    admin_user = os.getenv('ADMIN_USERNAME')
    admin_pass = os.getenv('ADMIN_PASSWORD')
    
    if admin_user and admin_pass:
        if credentials.username == admin_user and credentials.password == admin_pass:
            # Generate a simple token
            token = secrets.token_urlsafe(32)
            request.session['is_admin'] = True
            request.session['username'] = credentials.username
            request.session['token'] = token
            return {"message": "Login successful", "username": credentials.username, "token": token}
    
    raise HTTPException(status_code=401, detail="Invalid credentials")


@app.get('/api/admin/logout')
def api_logout(request: Request):
    """Admin logout API endpoint"""
    request.session.clear()
    return {"message": "Logged out successfully"}


@app.get('/logout')
def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url='/', status_code=303)


# ==================== ADMIN API ROUTES ====================

@app.get("/api/admin/dashboard")
def api_dashboard(request: Request):
    """Get dashboard statistics"""
    if not check_admin_auth(request):
        raise HTTPException(status_code=401, detail="Admin access required")
    stats = crud.get_dashboard_stats()
    db = crud.get_db()

    total_invoices = 0
    pending_invoices = 0
    overdue_invoices = 0
    total_readings = 0
    rate = crud.get_rate_config()
    effective_rate = crud.get_effective_rate()

    if db is not None:
        total_invoices = db["invoices"].count_documents({})
        pending_invoices = db["invoices"].count_documents({"status": "pending"})
        overdue_invoices = db["invoices"].count_documents({"status": "overdue"})
        total_readings = db["meter_readings"].count_documents({})

    return {
        "stats": stats,
        "rate": serialize_mongo(rate),
        "effective_rate": effective_rate,
        "total_invoices": total_invoices,
        "pending_invoices": pending_invoices,
        "overdue_invoices": overdue_invoices,
        "total_readings": total_readings,
    }


@app.get("/api/admin/customers")
def api_customers(request: Request, search: str = None):
    """Get list of customers"""
    if not check_admin_auth(request):
        raise HTTPException(status_code=401, detail="Admin access required")
    
    if search and search.strip():
        customers = crud.search_customers_by_name(search.strip())
    else:
        customers = crud.list_customers()
    return serialize_mongo(customers)


@app.post("/api/admin/customers")
def api_create_customer(request: Request, customer_data: schemas.CustomerCreate):
    """Create a new customer"""
    if not check_admin_auth(request):
        raise HTTPException(status_code=401, detail="Admin access required")

    customer = crud.create_customer(customer_data.dict())
    if not customer:
        raise HTTPException(status_code=500, detail="Failed to create customer")
    return {"message": "Customer created", "customer": serialize_mongo(customer)}


@app.put("/api/admin/customers/{customer_id}")
def api_update_customer(customer_id: int, request: Request, customer_data: CustomerUpdatePayload):
    """Update an existing customer"""
    if not check_admin_auth(request):
        raise HTTPException(status_code=401, detail="Admin access required")

    update_data = {k: v for k, v in customer_data.dict().items() if v is not None}
    if not update_data:
        raise HTTPException(status_code=400, detail="No fields provided for update")

    customer = crud.update_customer(customer_id, update_data)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    return {"message": "Customer updated", "customer": serialize_mongo(customer)}


@app.delete("/api/admin/customers/{customer_id}")
def api_delete_customer(customer_id: int, request: Request):
    """Delete a customer"""
    if not check_admin_auth(request):
        raise HTTPException(status_code=401, detail="Admin access required")

    deleted = crud.delete_customer(customer_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Customer not found")
    return {"message": "Customer deleted", "customer_id": customer_id}


@app.post("/api/admin/customers/bulk-delete")
def api_bulk_delete_customers(request: Request, payload: BulkCustomerDeletePayload):
    """Delete multiple customers and return per-item results"""
    if not check_admin_auth(request):
        raise HTTPException(status_code=401, detail="Admin access required")

    if not payload.customer_ids:
        raise HTTPException(status_code=400, detail="customer_ids cannot be empty")

    deleted_ids = []
    not_found_ids = []
    for customer_id in payload.customer_ids:
        if crud.delete_customer(customer_id):
            deleted_ids.append(customer_id)
        else:
            not_found_ids.append(customer_id)

    return {
        "message": "Bulk delete completed",
        "requested_count": len(payload.customer_ids),
        "deleted_count": len(deleted_ids),
        "not_found_count": len(not_found_ids),
        "deleted_ids": deleted_ids,
        "not_found_ids": not_found_ids,
    }


@app.get("/api/admin/readings")
def api_readings(request: Request):
    """Get all meter readings"""
    if not check_admin_auth(request):
        raise HTTPException(status_code=401, detail="Admin access required")
    return serialize_mongo(crud.get_all_readings())


@app.post("/api/admin/customers/{customer_id}/readings")
def api_add_reading(customer_id: int, request: Request, reading_data: schemas.MeterReadingCreate):
    """Add a meter reading for a customer"""
    if not check_admin_auth(request):
        raise HTTPException(status_code=401, detail="Admin access required")
    customer = crud.get_customer(customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    reading = crud.add_reading(customer_id, reading_data.reading_value)
    return {"message": "Reading added", "reading_id": reading.get("id")}


@app.get("/api/admin/invoices")
def api_invoices(request: Request):
    """Get list of invoices"""
    if not check_admin_auth(request):
        raise HTTPException(status_code=401, detail="Admin access required")
    return serialize_mongo(crud.list_invoices())


@app.post("/api/admin/invoices/generate/{customer_id}")
def api_generate_invoice(customer_id: int, request: Request):
    """Generate an invoice for a customer"""
    if not check_admin_auth(request):
        raise HTTPException(status_code=401, detail="Admin access required")

    inv, error_message = generate_invoice_for_customer(customer_id)
    if error_message:
        raise HTTPException(status_code=400, detail=error_message)

    return {"message": "Invoice generated", "invoice_id": inv.get("id")}


@app.post("/api/admin/invoices/bulk-generate")
def api_bulk_generate_invoices(request: Request, payload: BulkInvoiceGeneratePayload):
    """Generate invoices for multiple customers."""
    if not check_admin_auth(request):
        raise HTTPException(status_code=401, detail="Admin access required")
    if not payload.customer_ids:
        raise HTTPException(status_code=400, detail="customer_ids cannot be empty")

    created_invoice_ids = []
    failures = []
    for customer_id in payload.customer_ids:
        inv, error_message = generate_invoice_for_customer(customer_id)
        if inv:
            created_invoice_ids.append(inv.get("id"))
        else:
            failures.append({"customer_id": customer_id, "reason": error_message})

    return {
        "message": "Bulk invoice generation completed",
        "requested_count": len(payload.customer_ids),
        "created_count": len(created_invoice_ids),
        "failed_count": len(failures),
        "invoice_ids": created_invoice_ids,
        "failures": failures,
    }


@app.post("/api/admin/invoices/{invoice_id}/pay")
def api_pay_invoice(invoice_id: int, request: Request):
    """Mark an invoice as paid"""
    if not check_admin_auth(request):
        raise HTTPException(status_code=401, detail="Admin access required")

    inv = crud.mark_invoice_paid(invoice_id)
    if not inv:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return {"message": "Invoice marked as paid", "invoice": serialize_mongo(inv)}


@app.post("/api/admin/invoices/{invoice_id}/send-reminder")
def api_send_invoice_reminder(invoice_id: int, request: Request):
    """Send reminder for a specific invoice."""
    if not check_admin_auth(request):
        raise HTTPException(status_code=401, detail="Admin access required")

    invoice = crud.get_invoice(invoice_id)
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    customer = crud.get_customer(invoice.get("customer_id"))
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    sent = notify.send_invoice_message(customer, invoice, method="all")
    updated_invoice = crud.mark_reminder_sent(invoice_id, datetime.utcnow())

    return {
        "message": "Reminder processed",
        "sent": bool(sent),
        "invoice": serialize_mongo(updated_invoice or invoice),
    }


@app.post("/api/admin/reminders/bulk-send")
def api_bulk_send_reminders(request: Request, payload: BulkReminderPayload):
    """Send reminders for multiple invoices."""
    if not check_admin_auth(request):
        raise HTTPException(status_code=401, detail="Admin access required")
    if not payload.invoice_ids:
        raise HTTPException(status_code=400, detail="invoice_ids cannot be empty")

    sent_ids = []
    failed = []
    for invoice_id in payload.invoice_ids:
        invoice = crud.get_invoice(invoice_id)
        if not invoice:
            failed.append({"invoice_id": invoice_id, "reason": "Invoice not found"})
            continue

        customer = crud.get_customer(invoice.get("customer_id"))
        if not customer:
            failed.append({"invoice_id": invoice_id, "reason": "Customer not found"})
            continue

        sent = notify.send_invoice_message(customer, invoice, method="all")
        crud.mark_reminder_sent(invoice_id, datetime.utcnow())
        if sent:
            sent_ids.append(invoice_id)
        else:
            failed.append({"invoice_id": invoice_id, "reason": "No provider delivery succeeded"})

    return {
        "message": "Bulk reminders processed",
        "requested_count": len(payload.invoice_ids),
        "sent_count": len(sent_ids),
        "failed_count": len(failed),
        "sent_ids": sent_ids,
        "failed": failed,
    }


@app.get("/api/admin/rate")
def api_get_rate(request: Request):
    """Get current rate configuration"""
    if not check_admin_auth(request):
        raise HTTPException(status_code=401, detail="Admin access required")
    rate = crud.get_rate_config()
    effective = crud.get_effective_rate()
    return {"rate": rate, "effective_rate": effective}


@app.post("/api/admin/rate")
def api_set_rate(mode: str = Form(...), value: float = Form(...), request: Request = None):
    """Set rate configuration"""
    if not request or not check_admin_auth(request):
        raise HTTPException(status_code=403, detail="Admin access required")
    if mode not in ("fixed", "percent"):
        raise HTTPException(status_code=400, detail="Invalid mode")
    
    crud.set_rate_config(mode, value)
    return {"message": "Rate updated"}


# ==================== CUSTOMER PORTAL ROUTES ====================

@app.get("/customer/login", response_class=HTMLResponse)
def customer_login_page(request: Request):
    return templates.TemplateResponse("customer_login.html", {"request": request})


@app.get("/customer/portal", response_class=HTMLResponse)
def customer_portal_page(request: Request):
    return templates.TemplateResponse("customer_portal.html", {"request": request})


@app.post("/api/auth/login")
def customer_login(login_data: schemas.CustomerLogin):
    """Customer login endpoint"""
    auth = crud.authenticate_customer(login_data.username, login_data.password)
    if not auth:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # Generate token
    token_data = f"{auth.get('customer_id')}:{datetime.utcnow().isoformat()}"
    token = base64.b64encode(token_data.encode()).decode()
    
    return {"access_token": token, "token_type": "bearer"}


@app.post("/api/auth/register")
def customer_register(customer_id: int = Form(...), username: str = Form(...), password: str = Form(...)):
    """Customer registration endpoint"""
    customer = crud.get_customer(customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    existing_auth = crud.get_auth_by_username(username)
    if existing_auth:
        raise HTTPException(status_code=400, detail="Username already taken")
    
    auth = crud.create_customer_auth(customer_id, username, password)
    return {"message": "Registration successful", "customer_id": customer_id}


@app.get("/api/customer/portal")
def get_customer_portal_data(request: Request):
    """Get customer portal data"""
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid token")
    
    try:
        token = auth_header.split(" ")[1]
        token_data = base64.b64decode(token).decode()
        customer_id = int(token_data.split(":")[0])
    except:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    customer = crud.get_customer(customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    # Get recent invoices
    invoices = crud.get_customer_invoices(customer_id)
    recent_invoices = invoices[:5]
    
    # Get usage history
    usage_history = crud.get_customer_usage_history(customer_id)
    
    # Get benchmark data
    benchmark = crud.get_customer_benchmark(customer_id)
    
    # Get alerts
    alerts = crud.get_customer_alerts(customer_id)
    
    # Calculate total due
    total_due = sum(inv.get("amount", 0) for inv in recent_invoices if inv.get("status") in ["pending", "overdue"])
    
    return serialize_mongo({
        "customer": customer,
        "recent_invoices": recent_invoices,
        "usage_history": usage_history,
        "benchmark": benchmark,
        "alerts": alerts,
        "total_due": total_due
    })


# ==================== ANALYTICS API ROUTES (MongoDB) ====================

@app.get("/api/analytics/usage/monthly")
def api_monthly_usage_trends(request: Request, year: int = None, month: int = None):
    """Get monthly usage trends from MongoDB"""
    from app.analytics import get_analytics_service
    
    if not check_admin_auth(request):
        raise HTTPException(status_code=401, detail="Admin access required")
    
    analytics = get_analytics_service()
    if not analytics:
        raise HTTPException(status_code=503, detail="MongoDB not connected")
    
    trends = analytics.get_monthly_usage_trends(year, month)
    return {"trends": trends}


@app.get("/api/analytics/usage/yearly")
def api_yearly_usage_trends(request: Request, year: int = None):
    """Get yearly usage trends from MongoDB"""
    from app.analytics import get_analytics_service
    
    if not request.session.get("is_admin"):
        raise HTTPException(status_code=401, detail="Admin access required")
    
    analytics = get_analytics_service()
    if not analytics:
        raise HTTPException(status_code=503, detail="MongoDB not connected")
    
    trends = analytics.get_yearly_usage_trends(year)
    return {"trends": trends}


@app.get("/api/analytics/usage/customer/{customer_id}")
def api_customer_usage_trends(request: Request, customer_id: int, months: int = 12):
    """Get usage trends for a specific customer from MongoDB"""
    from app.analytics import get_analytics_service
    
    if not request.session.get("is_admin"):
        raise HTTPException(status_code=401, detail="Admin access required")
    
    analytics = get_analytics_service()
    if not analytics:
        raise HTTPException(status_code=503, detail="MongoDB not connected")
    
    trends = analytics.get_customer_usage_trends(customer_id, months)
    return {"customer_id": customer_id, "trends": trends}


@app.get("/api/analytics/payments/methods")
def api_payment_methods_analysis(request: Request):
    """Get payment method preferences analysis from MongoDB"""
    from app.analytics import get_analytics_service
    
    if not request.session.get("is_admin"):
        raise HTTPException(status_code=401, detail="Admin access required")
    
    analytics = get_analytics_service()
    if not analytics:
        raise HTTPException(status_code=503, detail="MongoDB not connected")
    
    analysis = analytics.get_payment_methods_analysis()
    return analysis


@app.get("/api/analytics/payments/timing")
def api_payment_timing_analysis(request: Request, customer_id: int = None):
    """Get payment timing patterns from MongoDB"""
    from app.analytics import get_analytics_service
    
    if not request.session.get("is_admin"):
        raise HTTPException(status_code=401, detail="Admin access required")
    
    analytics = get_analytics_service()
    if not analytics:
        raise HTTPException(status_code=503, detail="MongoDB not connected")
    
    timing = analytics.get_payment_timing_analysis(customer_id)
    return {"timing": timing}


@app.get("/api/analytics/customers/active")
def api_active_inactive_counts(request: Request):
    """Get active/inactive customer counts from MongoDB"""
    from app.analytics import get_analytics_service
    
    if not request.session.get("is_admin"):
        raise HTTPException(status_code=401, detail="Admin access required")
    
    analytics = get_analytics_service()
    if not analytics:
        raise HTTPException(status_code=503, detail="MongoDB not connected")
    
    counts = analytics.get_active_inactive_counts()
    return counts


@app.get("/api/analytics/customers/{customer_id}/profile")
def api_customer_profile(request: Request, customer_id: int):
    """Get full customer profile with analytics from MongoDB"""
    from app.analytics import get_analytics_service
    
    if not request.session.get("is_admin"):
        raise HTTPException(status_code=401, detail="Admin access required")
    
    analytics = get_analytics_service()
    if not analytics:
        raise HTTPException(status_code=503, detail="MongoDB not connected")
    
    profile = analytics.get_customer_profile(customer_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Customer profile not found")
    
    return profile


@app.get("/api/analytics/staff/trends")
def api_staff_trends(request: Request, staff_id: str = None, months: int = 6):
    """Get staff performance trends from MongoDB"""
    from app.analytics import get_analytics_service
    
    if not request.session.get("is_admin"):
        raise HTTPException(status_code=401, detail="Admin access required")
    
    analytics = get_analytics_service()
    if not analytics:
        raise HTTPException(status_code=503, detail="MongoDB not connected")
    
    trends = analytics.get_staff_trends(staff_id, months)
    return {"trends": trends}


@app.get("/api/analytics/staff/top")
def api_top_performing_staff(request: Request, limit: int = 5):
    """Get top performing staff members from MongoDB"""
    from app.analytics import get_analytics_service
    
    if not request.session.get("is_admin"):
        raise HTTPException(status_code=401, detail="Admin access required")
    
    analytics = get_analytics_service()
    if not analytics:
        raise HTTPException(status_code=503, detail="MongoDB not connected")
    
    top_staff = analytics.get_top_performing_staff(limit)
    return {"top_staff": top_staff}


# ==================== REMINDER CONFIG API ROUTES ====================

@app.get("/api/admin/settings/reminder-days")
def api_get_reminder_config(request: Request):
    """Get reminder configuration"""
    from app.analytics import get_analytics_service
    
    if not request.session.get("is_admin"):
        raise HTTPException(status_code=401, detail="Admin access required")
    
    analytics = get_analytics_service()
    if not analytics:
        raise HTTPException(status_code=503, detail="MongoDB not connected")
    
    config = analytics.get_reminder_config()
    return config


@app.put("/api/admin/settings/reminder-days")
def api_set_reminder_config(
    request: Request,
    reminder_days: int = Form(...),
    auto_resend_invoice: bool = Form(True),
    max_reminders: int = Form(3)
):
    """Set reminder configuration"""
    from app.analytics import get_analytics_service
    
    if not request.session.get("is_admin"):
        raise HTTPException(status_code=401, detail="Admin access required")
    
    analytics = get_analytics_service()
    if not analytics:
        raise HTTPException(status_code=503, detail="MongoDB not connected")
    
    username = request.session.get("username", "unknown")
    success = analytics.set_reminder_config(
        reminder_days=reminder_days,
        auto_resend_invoice=auto_resend_invoice,
        max_reminders=max_reminders,
        updated_by=username
    )
    
    if success:
        return {"message": "Reminder settings updated", "config": analytics.get_reminder_config()}
    raise HTTPException(status_code=500, detail="Failed to update reminder settings")


# ==================== DATA SYNC API ROUTES ====================

@app.post("/api/admin/sync/analytics")
def api_sync_analytics(request: Request):
    """Trigger full sync of data to MongoDB analytics"""
    from app.sync_analytics import get_sync_service
    
    if not request.session.get("is_admin"):
        raise HTTPException(status_code=401, detail="Admin access required")
    
    sync_service = get_sync_service()
    if not sync_service:
        raise HTTPException(status_code=503, detail="MongoDB not connected")
    
    results = sync_service.run_full_sync()
    return {"message": "Sync completed", "results": results}


# ==================== MONGODB STATUS API ROUTE ====================

@app.get("/api/admin/mongodb/status")
def api_mongodb_status(request: Request):
    """Check MongoDB connection status"""
    if not request.session.get("is_admin"):
        raise HTTPException(status_code=401, detail="Admin access required")
    
    connected = mongodb.is_connected()
    if connected:
        mongodb.init_collections()
        return {"status": "connected", "message": "MongoDB is connected and collections initialized"}
    return {"status": "disconnected", "message": "MongoDB is not connected"}


# ==================== SCHEDULED JOB ====================

def check_and_remind():
    """Run every hour: mark overdue invoices and send reminders based on configurable settings."""
    from app.analytics import get_analytics_service
    
    # Get reminder configuration from MongoDB
    reminder_days = 5  # Default
    max_reminders = 3  # Default
    auto_resend = True

    analytics = get_analytics_service()
    if analytics:
        config = analytics.get_reminder_config()
        reminder_days = config.get("reminder_days", 5)
        max_reminders = config.get("max_reminders", 3)
        auto_resend = config.get("auto_resend_invoice", True)
        logger.info(f"Using reminder config: days={reminder_days}, max={max_reminders}, auto={auto_resend}")

    # Update overdue statuses
    changed = crud.update_overdue_invoices()
    logger.info(f"Updated {changed} invoices to overdue")

    if not auto_resend:
        logger.info("Auto-resend invoices disabled in settings")
        return

    # Find invoices overdue by reminder_days and not paid
    db = mongodb.get_db()
    if db is None:
        return
    
    cutoff = datetime.utcnow() - timedelta(days=reminder_days)
    overdue_invoices = list(db["invoices"].find({"status": "overdue"}))

    reminders_sent = 0
    for inv in overdue_invoices:
        if inv.get("due_date") <= cutoff and not inv.get("reminder_sent_at"):
            customer = crud.get_customer(inv.get("customer_id"))
            if customer:
                sent = notify.send_invoice_message(customer, inv, method="all")
                if sent:
                    crud.mark_reminder_sent(inv.get("id"), datetime.utcnow())
                    reminders_sent += 1
                    logger.info(f"Sent reminder for invoice {inv.get('id')} to customer {customer.get('id')}")

    if reminders_sent > 0:
        logger.info(f"Sent {reminders_sent} invoice reminders")

