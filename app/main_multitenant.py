import os
import logging
from datetime import datetime, timedelta
from fastapi import FastAPI, HTTPException, Request, Form, Depends, Header
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from apscheduler.schedulers.background import BackgroundScheduler
from typing import Optional, List
from bson import ObjectId

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.mongodb_multitenant import mongodb_multitenant as mt_db
from app.crud_providers import crud_providers
from app.crud_multitenant import crud_multitenant as crud
from app.middleware import ProviderContextMiddleware, ErrorHandlingMiddleware
from app.models import (
    AdminLoginRequest,
    AdminUserResponse,
    ProviderResponse,
)

# Load environment
from dotenv import load_dotenv
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("uvicorn")
APP_ENV = os.getenv("APP_ENV", "development").lower()
DEFAULT_ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]
ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.getenv("ALLOWED_ORIGINS", ",".join(DEFAULT_ALLOWED_ORIGINS)).split(",")
    if origin.strip()
]

# Initialize templates
templates_dir = os.path.join(os.path.dirname(__file__), "..", "templates")
templates = Jinja2Templates(directory=templates_dir)

# ==================== FASTAPI APP ====================

app = FastAPI(
    title="Water Billing System - Multi-Tenant",
    description="Multi-tenant water billing system with database-per-provider architecture",
    version="2.0.0"
)

# Add middleware (order matters - last added is first executed)
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    allow_origin_regex=r"https://.*\.vercel\.app",
)
app.add_middleware(ErrorHandlingMiddleware)
app.add_middleware(ProviderContextMiddleware)

# Add SessionMiddleware FIRST (before other middleware)
app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("SESSION_SECRET", "your-session-secret-change-in-production"),
    max_age=86400,  # 24 hours
    same_site="none" if APP_ENV == "production" else "lax",
    https_only=APP_ENV == "production",
    domain=os.getenv("SESSION_COOKIE_DOMAIN") or None,
)

# Mount static files
static_dir = os.path.join(os.path.dirname(__file__), "..", "static")
app.mount("/static", StaticFiles(directory=static_dir), name="static")


# ==================== STARTUP/SHUTDOWN ====================

@app.on_event("startup")
def startup_event():
    """Initialize databases and start scheduler."""
    logger.info("Starting multi-tenant water billing system...")
    
    # Initialize master database
    try:
        mt_db.init_master_collections()
        logger.info("Master database initialized")
    except Exception as e:
        logger.error(f"Failed to initialize master database: {e}")
    
    try:
        scheduler = BackgroundScheduler()
        scheduler.add_job(check_and_remind, "interval", minutes=60)
        scheduler.start()
        app.state.scheduler = scheduler
        logger.info("Scheduler enabled safely")
    except Exception as e:
        logger.error(f"Scheduler failed to start: {e}")
        logger.info("Scheduler disabled - using manual reminders")
    
    logger.info("Application started successfully")


@app.on_event("shutdown")
def shutdown_event():
    """Shutdown scheduler and close connections."""
    # Scheduler is disabled, so we don't need to shut it down
    # sched = getattr(app.state, "scheduler", None)
    # if sched:
    #     sched.shutdown()
    
    try:
        mt_db.shutdown_all_connections()
    except Exception as e:
        logger.error(f"Error closing connections: {e}")
    
    logger.info("Application shutdown complete")


# ==================== UTILITY FUNCTIONS ====================

def get_current_provider(request: Request) -> dict:
    """Get current provider from request context."""
    provider = getattr(request.state, "provider", None)
    if not provider:
        raise HTTPException(status_code=400, detail="Provider context required")
    return provider


def get_provider_slug(request: Request) -> str:
    """Get provider slug from request context."""
    slug = getattr(request.state, "provider_slug", None)
    if not slug:
        raise HTTPException(status_code=400, detail="Provider context required")
    return slug


def require_admin(request: Request) -> dict:
    """Require admin authentication."""
    is_admin = request.session.get("is_admin")
    if not is_admin:
        raise HTTPException(status_code=401, detail="Admin authentication required")
    return request.state.provider


# ==================== HEALTH CHECK ====================

@app.get("/health")
@app.get("/api/health")
def health_check():
    """Health check endpoint (safe)."""
    master_connected = False
    try:
        # call mt_db.is_master_connected() if available, otherwise safely return False
        is_connected_fn = getattr(mt_db, "is_master_connected", None)
        if callable(is_connected_fn):
            try:
                master_connected = bool(is_connected_fn())
            except Exception:
                master_connected = False
        else:
            master_connected = False
    except Exception:
        master_connected = False

    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "master_connected": master_connected,
    }


# ==================== AUTH ROUTES ====================

@app.get("/api/auth/login", response_class=HTMLResponse)
def login_page(request: Request):
    """Admin login page."""
    return templates.TemplateResponse("login.html", {"request": request})


@app.post("/api/auth/login")
def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    provider_slug: str = Form(None)
):
    """Admin login endpoint."""
    # Use provider_slug from form or context
    slug = provider_slug or get_provider_slug(request)
    
    # Authenticate
    admin = crud_providers.authenticate_admin(username, password, slug)
    
    if not admin:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # Create session
    request.session["is_admin"] = True
    request.session["admin_id"] = admin["id"]
    request.session["username"] = admin["username"]
    request.session["provider_id"] = admin["provider_id"]
    request.session["provider_slug"] = slug
    
    return RedirectResponse(url="/", status_code=303)



@app.post("/api/admin/login")
def api_login(credentials: AdminLoginRequest, request: Request = None):
    """Admin login API endpoint."""
    import os
    
    # Get credentials
    username = credentials.username
    password = credentials.password
    provider_slug = credentials.provider_slug
    
    # SECURITY FIX: Require ADMIN_USERNAME and ADMIN_PASSWORD env variables
    # If not set, deny login (no hardcoded defaults!)
    admin_user = os.getenv('ADMIN_USERNAME')
    admin_pass = os.getenv('ADMIN_PASSWORD')
    
    if admin_user and admin_pass:
        if username == admin_user and password == admin_pass:
            if request:
                request.session['is_admin'] = True
                request.session['username'] = username
                request.session['is_super_admin'] = True
            
            return {"message": "Login successful", "username": username}
    
    # Try to authenticate as super admin from MongoDB
    try:
        from app.crud_providers import authenticate_super_admin
        admin = authenticate_super_admin(username, password)
        
        if admin:
            if request:
                request.session['is_admin'] = True
                request.session['is_super_admin'] = True
                request.session['username'] = admin['username']
                request.session['admin_id'] = admin['id']
            
            return {
                "message": "Login successful", 
                "username": admin['username'],
                "is_super_admin": True
            }
    except Exception as e:
        logger.error(f"Error with super admin auth: {e}")
    
    # If provider_slug is provided, try provider admin
    if provider_slug:
        try:
            from app.crud_providers import authenticate_admin
            admin = authenticate_admin(username, password, provider_slug)
            
            if admin:
                if request:
                    request.session['is_admin'] = True
                    request.session['is_super_admin'] = admin.get('is_super_admin', False)
                    request.session['username'] = admin['username']
                    request.session['admin_id'] = admin['id']
                    request.session['provider_slug'] = provider_slug
                
                return {
                    "message": "Login successful", 
                    "username": admin['username'],
                    "provider_slug": provider_slug
                }
        except Exception as e:
            logger.error(f"Error with provider admin auth: {e}")
    
    raise HTTPException(status_code=401, detail="Invalid credentials")


@app.post("/api/admin/logout")
def api_logout(request: Request):
    """Admin logout endpoint."""
    request.session.clear()
    return {"message": "Logged out successfully"}


@app.get("/logout")
def logout(request: Request):
    """Logout page redirect."""
    request.session.clear()
    return RedirectResponse(url="/", status_code=303)


# ==================== DASHBOARD ====================

@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    """Dashboard home page."""
    provider = getattr(request.state, "provider", None)
    
    if not provider:
        # No provider - show welcome page
        return templates.TemplateResponse("index.html", {
            "request": request,
            "customers": [],
            "invoices": [],
            "rate": {"mode": "fixed", "value": 1.5},
            "effective_rate": 1.5,
            "stats": {
                "total_customers": 0,
                "active_customers": 0,
                "total_water_usage": 0,
                "total_revenue": 0,
                "pending_invoices": 0,
                "overdue_invoices": 0
            },
            "is_admin": False,
            "provider_name": None
        })
    
    # Get provider data
    slug = provider["slug"]
    
    try:
        stats = crud.get_dashboard_stats(slug)
        customers = crud.list_customers(slug, limit=10)
        invoices = crud.list_invoices(slug, limit=10)
        rate = crud.get_rate_config(slug)
        effective = crud.get_effective_rate(slug)
    except Exception as e:
        logger.error(f"Error loading dashboard: {e}")
        stats = {
            "total_customers": 0,
            "active_customers": 0,
            "total_water_usage": 0,
            "total_revenue": 0,
            "pending_invoices": 0,
            "overdue_invoices": 0
        }
        customers = []
        invoices = []
        rate = {"mode": "fixed", "value": 1.5}
        effective = 1.5
    
    is_admin = request.session.get("is_admin", False)
    
    return templates.TemplateResponse("index.html", {
        "request": request,
        "customers": customers,
        "invoices": invoices,
        "rate": rate,
        "effective_rate": effective,
        "stats": stats,
        "is_admin": is_admin,
        "provider_name": provider.get("name"),
        "branding": provider.get("branding", {})
    })


# ==================== CUSTOMER ROUTES ====================

@app.get("/customers", response_class=HTMLResponse)
def customers_page(request: Request, search: str = None):
    """Customers listing page."""
    slug = get_provider_slug(request)
    is_admin = request.session.get("is_admin", False)
    
    if search and search.strip():
        customers = crud.search_customers_by_name(slug, search.strip())
        search_performed = True
        search_term = search.strip()
    else:
        customers = crud.list_customers(slug)
        search_performed = False
        search_term = ""
    
    return templates.TemplateResponse("customers.html", {
        "request": request,
        "customers": customers,
        "is_admin": is_admin,
        "search_performed": search_performed,
        "search_term": search_term
    })


@app.post("/customers")
def create_customer(
    request: Request,
    name: str = Form(...),
    phone: str = Form(None),
    email: str = Form(None),
    location: str = Form(None),
    initial_reading: float = Form(None)
):
    """Create a new customer."""
    require_admin(request)
    slug = get_provider_slug(request)
    
    customer_data = {
        "name": name,
        "phone": phone,
        "email": email,
        "location": location,
        "initial_reading": initial_reading
    }
    
    customer = crud.create_customer(slug, customer_data)
    
    if not customer:
        raise HTTPException(status_code=500, detail="Failed to create customer")
    
    return RedirectResponse(url="/customers", status_code=303)


@app.get("/api/admin/customers")
def api_list_customers(request: Request, search: str = None):
    """API: List customers."""
    require_admin(request)
    slug = get_provider_slug(request)
    
    if search and search.strip():
        customers = crud.search_customers_by_name(slug, search.strip())
    else:
        customers = crud.list_customers(slug)
    
    return customers


@app.post("/api/admin/customers")
def api_create_customer(
    request: Request,
    name: str = Form(...),
    phone: str = Form(None),
    email: str = Form(None),
    location: str = Form(None),
    initial_reading: float = Form(None)
):
    """API: Create a customer."""
    require_admin(request)
    slug = get_provider_slug(request)
    
    customer_data = {
        "name": name,
        "phone": phone,
        "email": email,
        "location": location,
        "initial_reading": initial_reading
    }
    
    customer = crud.create_customer(slug, customer_data)
    
    if not customer:
        raise HTTPException(status_code=500, detail="Failed to create customer")
    
    return {"message": "Customer created", "customer_id": customer["id"]}


# ==================== READINGS ROUTES ====================

@app.get("/readings", response_class=HTMLResponse)
def readings_page(request: Request):
    """Readings listing page."""
    slug = get_provider_slug(request)
    is_admin = request.session.get("is_admin", False)
    
    customers = crud.list_customers(slug)
    readings = crud.get_all_readings(slug)
    
    return templates.TemplateResponse("readings.html", {
        "request": request,
        "readings": readings,
        "customers": customers,
        "is_admin": is_admin
    })


@app.post("/customers/{customer_id}/readings")
def add_reading(request: Request, customer_id: int, reading_value: float = Form(...)):
    """Add a meter reading."""
    # Note: In production, add admin check
    slug = get_provider_slug(request)
    customer = crud.get_customer(slug, customer_id)
    
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    crud.add_reading(slug, customer_id, reading_value)
    return RedirectResponse(url="/readings", status_code=303)


@app.get("/api/admin/readings")
def api_list_readings(request: Request):
    """API: List readings."""
    require_admin(request)
    slug = get_provider_slug(request)
    
    return crud.get_all_readings(slug)


@app.post("/api/admin/customers/{customer_id}/readings")
def api_add_reading(
    request: Request,
    customer_id: int,
    reading_value: float = Form(...)

):
    """API: Add a reading."""
    require_admin(request)
    slug = get_provider_slug(request)
    
    customer = crud.get_customer(slug, customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    reading = crud.add_reading(slug, customer_id, reading_value)
    return {"message": "Reading added", "reading_id": reading["id"]}


# ==================== INVOICE ROUTES ====================

@app.get("/invoices", response_class=HTMLResponse)
def invoices_page(request: Request):
    """Invoices listing page."""
    slug = get_provider_slug(request)
    is_admin = request.session.get("is_admin", False)
    
    invoices = crud.list_invoices(slug)
    
    return templates.TemplateResponse("invoices.html", {
        "request": request,
        "invoices": invoices,
        "is_admin": is_admin
    })


@app.post("/invoices/generate/{customer_id}")
def generate_invoice(request: Request, customer_id: int):
    """Generate an invoice for a customer."""
    slug = get_provider_slug(request)
    
    rate = crud.get_effective_rate(slug)
    calc = crud.calculate_amount_from_readings(slug, customer_id, rate)
    
    if not calc:
        raise HTTPException(status_code=400, detail="Not enough readings to calculate invoice")
    
    amount, billing_from, billing_to = calc
    due_date = datetime.utcnow() + timedelta(days=15)
    customer = crud.get_customer(slug, customer_id)
    
    inv = crud.create_invoice(
        slug, customer_id, amount, due_date,
        billing_from=billing_from,
        billing_to=billing_to,
        location=customer.get("location") if customer else None
    )
    
    return RedirectResponse(url="/invoices", status_code=303)


@app.post("/invoices/{invoice_id}/pay")
def pay_invoice(request: Request, invoice_id: int):
    """Mark an invoice as paid."""
    slug = get_provider_slug(request)
    
    inv = crud.mark_invoice_paid(slug, invoice_id)
    if not inv:
        raise HTTPException(status_code=404, detail="Invoice not found")
    
    return RedirectResponse(url="/invoices", status_code=303)


@app.get("/api/admin/invoices")
def api_list_invoices(request: Request):
    """API: List invoices."""
    require_admin(request)
    slug = get_provider_slug(request)
    
    return crud.list_invoices(slug)


@app.post("/api/admin/invoices/generate/{customer_id}")
def api_generate_invoice(request: Request, customer_id: int):
    """API: Generate an invoice."""
    require_admin(request)
    slug = get_provider_slug(request)
    
    rate = crud.get_effective_rate(slug)
    calc = crud.calculate_amount_from_readings(slug, customer_id, rate)
    
    if not calc:
        raise HTTPException(status_code=400, detail="Not enough readings to calculate invoice")
    
    amount, billing_from, billing_to = calc
    due_date = datetime.utcnow() + timedelta(days=15)
    customer = crud.get_customer(slug, customer_id)
    
    inv = crud.create_invoice(
        slug, customer_id, amount, due_date,
        billing_from=billing_from,
        billing_to=billing_to,
        location=customer.get("location") if customer else None
    )
    
    return {"message": "Invoice generated", "invoice_id": inv["id"], "amount": amount}


@app.post("/api/admin/invoices/{invoice_id}/pay")
def api_pay_invoice(request: Request, invoice_id: int):
    """API: Mark invoice as paid."""
    require_admin(request)
    slug = get_provider_slug(request)
    
    inv = crud.mark_invoice_paid(slug, invoice_id)
    if not inv:
        raise HTTPException(status_code=404, detail="Invoice not found")
    
    return {"message": "Invoice marked as paid"}


# ==================== RATE ROUTES ====================

@app.post('/rate')
def set_rate(
    request: Request,
    mode: str = Form(...),
    value: float = Form(...)

):
    """Set rate configuration."""
    require_admin(request)
    slug = get_provider_slug(request)
    
    if mode not in ("fixed", "percent"):
        raise HTTPException(status_code=400, detail="Invalid mode")
    
    crud.set_rate_config(slug, mode, value)
    return RedirectResponse(url='/', status_code=303)


@app.get("/api/admin/rate")
def api_get_rate(request: Request):
    """API: Get rate configuration."""
    require_admin(request)
    slug = get_provider_slug(request)
    
    rate = crud.get_rate_config(slug)
    effective = crud.get_effective_rate(slug)
    return {"rate": rate, "effective_rate": effective}


@app.post("/api/admin/rate")
def api_set_rate(
    request: Request,
    mode: str = Form(...),
    value: float = Form(...)

):
    """API: Set rate configuration."""
    require_admin(request)
    slug = get_provider_slug(request)
    
    if mode not in ("fixed", "percent"):
        raise HTTPException(status_code=400, detail="Invalid mode")
    
    crud.set_rate_config(slug, mode, value)
    return {"message": "Rate updated"}


# ==================== DASHBOARD STATS ====================

@app.get("/api/admin/dashboard")
def api_dashboard(request: Request):
    """API: Get dashboard statistics."""
    require_admin(request)
    slug = get_provider_slug(request)
    
    stats = crud.get_dashboard_stats(slug)
    return stats


# ==================== CUSTOMER PORTAL ====================

@app.get("/customer/login", response_class=HTMLResponse)
def customer_login_page(request: Request):
    """Customer login page."""
    return templates.TemplateResponse("customer_login.html", {"request": request})


@app.get("/customer/portal", response_class=HTMLResponse)
def customer_portal_page(request: Request):
    """Customer portal page."""
    return templates.TemplateResponse("customer_portal.html", {"request": request})


@app.post("/api/customer/login")
def customer_login(request: Request, login_data: dict):
    """Customer login endpoint."""
    username = login_data.get("username")
    password = login_data.get("password")
    
    if not username or not password:
        raise HTTPException(status_code=400, detail="Username and password required")
    
    slug = get_provider_slug(request)
    auth = crud.authenticate_customer(slug, username, password)
    
    if not auth:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # Generate token
    token_data = f"{auth.get('customer_id')}:{datetime.utcnow().isoformat()}"
    import base64
    token = base64.b64encode(token_data.encode()).decode()
    
    return {"access_token": token, "token_type": "bearer"}


@app.get("/api/customer/portal")
def get_customer_portal_data(request: Request):
    """Get customer portal data."""
    # Get provider slug
    slug = get_provider_slug(request)
    
    # Get customer ID from token (simplified)
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid token")
    
    try:
        import base64
        token = auth_header.split(" ")[1]
        token_data = base64.b64decode(token).decode()
        customer_id = int(token_data.split(":")[0])
    except:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    customer = crud.get_customer(slug, customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    # Get recent invoices
    invoices = crud.get_customer_invoices(slug, customer_id)
    recent_invoices = invoices[:5]
    
    # Get usage history
    usage_history = crud.get_customer_usage_history(slug, customer_id)
    
    # Get benchmark
    benchmark = crud.get_customer_benchmark(slug, customer_id)
    
    # Get alerts
    alerts = crud.get_customer_alerts(slug, customer_id)
    
    # Calculate total due
    total_due = sum(inv.get("amount", 0) for inv in recent_invoices if inv.get("status") in ["pending", "overdue"])
    
    return {
        "customer": customer,
        "recent_invoices": recent_invoices,
        "usage_history": usage_history,
        "benchmark": benchmark,
        "alerts": alerts,
        "total_due": total_due
    }


# ==================== SETUP ROUTES ====================

@app.get("/setup", response_class=HTMLResponse)
def setup_page(request: Request):
    """Provider setup page."""
    return templates.TemplateResponse("setup.html", {"request": request})


@app.post("/setup")
def create_first_provider(
    name: str = Form(...),
    slug: str = Form(...),
    username: str = Form(...),
    password: str = Form(...),
    email: str = Form(None),
    rate_per_unit: float = Form(1.5)
):
    """Create the first provider."""
    try:
        # Create provider
        provider = crud_providers.create_provider({
            "name": name,
            "slug": slug.lower().strip(),
            "contact_email": email,
            "settings": {
                "rate_per_unit": rate_per_unit,
                "currency": "KES"
            }
        })
        
        # Create admin user
        crud_providers.create_admin_user({
            "provider_slug": slug.lower().strip(),
            "username": username,
            "password": password,
            "email": email,
            "is_super_admin": True
        })
        
        return {"message": "Provider created successfully", "slug": slug}
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Setup error: {e}")
        raise HTTPException(status_code=500, detail="Failed to create provider")


# ==================== SCHEDULED JOBS ====================

def check_and_remind():
    """Run every hour: mark overdue invoices and send reminders."""
    logger.info("Running scheduled reminder job...")
    
    # Get all active providers
    providers = crud_providers.list_providers(active_only=True)
    
    for provider in providers:
        slug = provider["slug"]
        
        try:
            # Update overdue invoices
            changed = crud.update_overdue_invoices(slug)
            if changed > 0:
                logger.info(f"Updated {changed} invoices to overdue for provider {slug}")
            
            # Get reminder config
            reminder_config = crud.get_reminder_config(slug)
            reminder_days = reminder_config.get("reminder_days", 5)
            auto_resend = reminder_config.get("auto_resend_invoice", True)
            max_reminders = reminder_config.get("max_reminders", 3)
            
            if not auto_resend:
                continue
            
            # Find invoices to remind
            db = crud.get_provider_db(slug)
            if not db:
                continue
            
            cutoff = datetime.utcnow() - timedelta(days=reminder_days)
            overdue_invoices = list(db["invoices"].find({"status": "overdue"}))
            
            reminders_sent = 0
            for inv in overdue_invoices:
                if inv.get("due_date") <= cutoff and not inv.get("reminder_sent_at"):
                    customer = crud.get_customer(slug, inv.get("customer_id"))
                    if customer:
                        # Send notification (simplified)
                        logger.info(f"Sending reminder for invoice {inv.get('id')} to customer {customer.get('id')}")
                        crud.mark_reminder_sent(slug, inv.get('id'))
                        reminders_sent += 1
            
            if reminders_sent > 0:
                logger.info(f"Sent {reminders_sent} reminders for provider {slug}")
                
        except Exception as e:
            logger.error(f"Error processing reminders for provider {slug}: {e}")


# ==================== UTILITY FUNCTION ====================

def provide_request() -> Request:
    """Helper to get request object when not in route context."""
    # This is a workaround for routes that need request but don't have it
    # In production, ensure all routes have request parameter
    raise RuntimeError("Request context required")


# ==================== EXPORT ====================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

