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

from app.mongodb_multitenant import init_master_collections, shutdown_all_connections, is_master_connected
from app.crud_providers import crud_providers
import app.crud_multitenant as crud
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

#CORS Middlewear
DEFAULT_ALLOWED_ORIGINS = [
    "https://water-billing-system-5q5d.onrender.com",
    "https://water-billing-system-b7jg.onrender.com",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "waterbillsystem-three.vercel.app",
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
        init_master_collections()
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
        shutdown_all_connections()
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
    slug = (
        getattr(request.state, "provider_slug", None)
        or request.session.get("provider_slug")
    )
    if not slug and request.session.get("is_super_admin"):
        try:
            from app.firebase_firestore import list_providers as list_firestore_providers
            providers = [
                provider for provider in list_firestore_providers(active_only=True)
                if provider.get("slug")
            ]
            if len(providers) == 1:
                slug = providers[0]["slug"]
                request.session["provider_slug"] = slug
        except Exception as e:
            logger.warning(f"Could not resolve default Firestore provider for super admin: {e}")

    if not slug and request.session.get("is_super_admin"):
        try:
            providers = crud_providers.list_providers(active_only=True)
            if len(providers) == 1:
                slug = providers[0]["slug"]
                request.session["provider_slug"] = slug
        except Exception as e:
            logger.warning(f"Could not resolve default Mongo provider for super admin: {e}")

    if not slug:
        raise HTTPException(status_code=400, detail="Provider context required")

    provider = getattr(request.state, "provider", None)
    if provider:
        try:
            ensure_mongo_provider_for_workspace(slug, provider)
        except Exception as e:
            logger.warning(f"Could not ensure Mongo billing database for provider {slug}: {e}")

    return slug


def require_admin(request: Request) -> dict:
    """Require admin authentication."""
    is_admin = request.session.get("is_admin")
    if not is_admin:
        raise HTTPException(status_code=401, detail="Admin authentication required")
    return request.state.provider


def require_super_admin(request: Request) -> None:
    """Require super admin authentication."""
    if not request.session.get("is_admin"):
        raise HTTPException(status_code=401, detail="Admin authentication required")
    if not request.session.get("is_super_admin"):
        raise HTTPException(status_code=403, detail="Super admin access required")


def to_response_dict(model_obj):
    """Serialize a Pydantic model across v1/v2."""
    if hasattr(model_obj, "model_dump"):
        return model_obj.model_dump(mode="json")
    return model_obj.dict()


def to_json_safe(value):
    """Convert Mongo/Python values into JSON-safe response values."""
    if isinstance(value, ObjectId):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, list):
        return [to_json_safe(item) for item in value]
    if isinstance(value, dict):
        return {key: to_json_safe(item) for key, item in value.items() if key != "_id"}
    return value


async def read_request_payload(request: Request) -> dict:
    """Read JSON or form payloads for React/API endpoints."""
    content_type = request.headers.get("content-type", "")
    if "application/json" in content_type:
        payload = await request.json()
        return payload or {}
    form = await request.form()
    return dict(form)


def ensure_mongo_provider_for_workspace(provider_slug: str, provider: dict) -> dict:
    """Ensure provider-scoped billing routes have a Mongo tenant database."""
    existing = crud_providers.get_provider(provider_slug)
    if existing:
        return existing

    settings = provider.get("settings") or {}
    rate_per_unit = provider.get("ratePerUnit", settings.get("rate_per_unit", 1.5))
    provider_data = {
        "name": provider.get("name") or provider_slug,
        "slug": provider_slug,
        "contact_email": provider.get("contactEmail", provider.get("contact_email")),
        "contact_phone": provider.get("contactPhone", provider.get("contact_phone")),
        "address": provider.get("address"),
        "settings": {
            **settings,
            "rate_per_unit": rate_per_unit,
            "currency": provider.get("currency", settings.get("currency", "KES")),
        },
        "branding": provider.get("branding", {}),
    }

    try:
        return crud_providers.create_provider(provider_data)
    except ValueError:
        # Another request may have created it first.
        existing = crud_providers.get_provider(provider_slug)
        if existing:
            return existing
        raise


# ==================== HEALTH CHECK ====================

@app.get("/health")
@app.get("/api/health")
def health_check():
    """Health check endpoint (safe)."""
    master_connected = False
    try:
        master_connected = bool(is_master_connected())
    except Exception:
        master_connected = False

    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "master_connected": master_connected,
    }


@app.get("/api/public/providers")
def public_provider_list():
    """List active providers for login and customer portal selection."""
    try:
        from app.firebase_firestore import list_providers as list_firestore_providers
        providers = [
            provider
            for provider in list_firestore_providers(active_only=True)
            if provider.get("isActive", provider.get("is_active", True))
        ]
        if providers:
            return [
                {
                    "name": provider.get("name"),
                    "slug": provider.get("slug"),
                }
                for provider in providers
            ]
    except Exception as e:
        logger.warning(f"Falling back to Mongo providers for public list: {e}")

    providers = crud_providers.list_providers(active_only=True)
    return [{"name": provider.get("name"), "slug": provider.get("slug")} for provider in providers]

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
def api_login(credentials: AdminLoginRequest, request: Request):
    """Admin login API endpoint."""
    import os
    
    # Get credentials
    username = credentials.username
    password = credentials.password
    provider_slug = (
        credentials.provider_slug
        or request.headers.get("X-Provider-Slug")
        or getattr(request.state, "provider_slug", None)
        or request.session.get("provider_slug")
        or request.query_params.get("provider")
    )
    
    # SECURITY FIX: Require ADMIN_USERNAME and ADMIN_PASSWORD env variables
    # If not set, deny login (no hardcoded defaults!)
    admin_user = os.getenv('ADMIN_USERNAME')
    admin_pass = os.getenv('ADMIN_PASSWORD')
    
    if admin_user and admin_pass:
        if username == admin_user and password == admin_pass:
            request.session['is_admin'] = True
            request.session['username'] = username
            request.session['is_super_admin'] = True
            
            return {"message": "Login successful", "username": username}
    
    # Try to authenticate as super admin from MongoDB
    try:
        from app.crud_providers import authenticate_super_admin
        admin = authenticate_super_admin(username, password)
        
        if admin:
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

    if not provider_slug:
        try:
            from app.crud_providers import resolve_provider_slug_for_admin_username
            provider_slug = resolve_provider_slug_for_admin_username(username)
        except Exception as e:
            logger.error(f"Error resolving provider slug for admin login: {e}")

    # If provider_slug is provided, try provider admin
    if provider_slug:
        try:
            from app.crud_providers import authenticate_admin
            admin = authenticate_admin(username, password, provider_slug)
            
            if admin:
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

    if not provider_slug:
        raise HTTPException(
            status_code=400,
            detail="Provider slug is required for provider admin login"
        )

    raise HTTPException(status_code=401, detail="Invalid credentials")


@app.post("/api/admin/firebase-login")
def api_firebase_login(request: Request, payload: dict, authorization: Optional[str] = Header(default=None)):
    """Admin login using a Firebase ID token."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Firebase ID token is required")

    id_token = authorization[7:]

    try:
        from app.firebase_auth import verify_firebase_id_token
        decoded = verify_firebase_id_token(id_token)
    except Exception as e:
        logger.error(f"Firebase token verification failed: {e}")
        raise HTTPException(status_code=401, detail="Invalid Firebase token")

    email = (decoded.get("email") or "").strip().lower()
    firebase_uid = (decoded.get("uid") or "").strip()
    if not email:
        raise HTTPException(status_code=400, detail="Firebase account email is required")

    provider_slug = (
        (payload.get("provider_slug") or "").strip().lower()
        or request.headers.get("X-Provider-Slug")
        or request.session.get("provider_slug")
    )

    try:
        from app.firebase_firestore import get_provider as get_firebase_provider, get_user_profile
        firebase_user = get_user_profile(firebase_uid)
    except Exception as e:
        logger.warning(f"Firestore lookup failed; falling back to Mongo auth mapping: {e}")
        firebase_user = None

    if firebase_user and firebase_user.get("isActive", True) and firebase_user.get("role") == "super_admin":
        request.session["is_admin"] = True
        request.session["is_super_admin"] = True
        request.session["username"] = firebase_user.get("displayName") or email
        request.session["admin_id"] = firebase_uid
        request.session["firebase_uid"] = firebase_uid

        return {
            "message": "Login successful",
            "username": firebase_user.get("displayName") or email,
            "email": email,
            "is_super_admin": True,
            "firebase_uid": firebase_uid,
            "token": id_token,
        }

    if firebase_user and firebase_user.get("isActive", True) and not provider_slug:
        provider_slug = (firebase_user.get("providerSlug") or "").strip().lower() or None

    if not provider_slug:
        raise HTTPException(
            status_code=400,
            detail="Provider slug is required for provider admin login"
        )

    provider = None
    if firebase_user and firebase_user.get("isActive", True):
        provider = get_firebase_provider(provider_slug)
        if not provider:
            raise HTTPException(status_code=404, detail="Provider not found")

        request.session["is_admin"] = True
        request.session["is_super_admin"] = firebase_user.get("role") == "super_admin"
        request.session["username"] = firebase_user.get("displayName") or email
        request.session["admin_id"] = firebase_uid
        request.session["provider_slug"] = provider_slug
        request.session["provider_id"] = provider.get("id", provider_slug)
        request.session["firebase_uid"] = firebase_uid

        return {
            "message": "Login successful",
            "username": firebase_user.get("displayName") or email,
            "email": email,
            "provider_slug": provider_slug,
            "is_super_admin": firebase_user.get("role") == "super_admin",
            "firebase_uid": firebase_uid,
            "token": id_token,
        }

    from app.crud_providers import (
        get_super_admin_by_email,
        get_admin_user_by_email,
        resolve_provider_slug_for_admin_email,
    )

    super_admin = get_super_admin_by_email(email)
    if super_admin and super_admin.get("is_active", True):
        request.session["is_admin"] = True
        request.session["is_super_admin"] = True
        request.session["username"] = super_admin["username"]
        request.session["admin_id"] = super_admin["id"]
        request.session["firebase_uid"] = firebase_uid

        return {
            "message": "Login successful",
            "username": super_admin["username"],
            "email": email,
            "is_super_admin": True,
            "firebase_uid": firebase_uid,
            "token": id_token,
        }

    if not provider_slug:
        provider_slug = resolve_provider_slug_for_admin_email(email)

    if not provider_slug:
        raise HTTPException(
            status_code=400,
            detail="Provider slug is required for provider admin login"
        )

    from app.mongodb_multitenant import get_provider as get_mongo_provider
    provider = get_mongo_provider(provider_slug)
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")

    admin = get_admin_user_by_email(provider["id"], email)
    if not admin or not admin.get("is_active", True):
        raise HTTPException(status_code=403, detail="No active admin account found for this Firebase email")

    request.session["is_admin"] = True
    request.session["is_super_admin"] = bool(admin.get("is_super_admin", False))
    request.session["username"] = admin["username"]
    request.session["admin_id"] = admin["id"]
    request.session["provider_slug"] = provider_slug
    request.session["provider_id"] = provider["id"]
    request.session["firebase_uid"] = firebase_uid

    return {
        "message": "Login successful",
        "username": admin["username"],
        "email": email,
        "provider_slug": provider_slug,
        "is_super_admin": bool(admin.get("is_super_admin", False)),
        "firebase_uid": firebase_uid,
        "token": id_token,
    }


@app.post("/api/admin/logout")
def api_logout(request: Request):
    """Admin logout endpoint."""
    request.session.clear()
    return {"message": "Logged out successfully"}


@app.post("/api/auth/register")
async def register_customer_portal_user(request: Request):
    """Register a customer portal login and mirror the profile to Firestore."""
    content_type = request.headers.get("content-type", "")
    if "application/json" in content_type:
        payload = await request.json()
    else:
        form = await request.form()
        payload = dict(form)

    provider_slug = (
        (payload.get("provider_slug") or "").strip().lower()
        or request.headers.get("X-Provider-Slug")
        or request.query_params.get("provider")
        or request.session.get("provider_slug")
    )
    if not provider_slug:
        raise HTTPException(status_code=400, detail="Provider slug is required")

    try:
        customer_id = int(payload.get("customer_id"))
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="Valid customer_id is required")

    username = (payload.get("username") or "").strip()
    password = payload.get("password") or ""
    email = (payload.get("email") or "").strip().lower() or None
    firebase_uid = (payload.get("firebase_uid") or "").strip() or None
    display_name = (payload.get("display_name") or username).strip()

    if not username or not password:
        raise HTTPException(status_code=400, detail="Username and password are required")

    provider = getattr(request.state, "provider", None)
    if provider:
        ensure_mongo_provider_for_workspace(provider_slug, provider)

    customer = crud.get_customer(provider_slug, customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    existing_auth = crud.get_customer_auth(provider_slug, customer_id)
    existing_username = crud.get_auth_by_username(provider_slug, username)
    if existing_auth:
        raise HTTPException(status_code=409, detail="Customer already has a portal login")
    if existing_username:
        raise HTTPException(status_code=409, detail="Username is already taken")

    auth_doc = crud.create_customer_auth(provider_slug, customer_id, username, password)
    if not auth_doc:
        raise HTTPException(status_code=500, detail="Failed to create customer portal login")

    try:
        from app.firebase_firestore import set_customer_portal_profile, set_user_profile
        set_customer_portal_profile(provider_slug, customer_id, {
            "username": username,
            "email": email,
            "displayName": display_name,
            "role": "customer",
            "isActive": True,
        })
        if firebase_uid:
            set_user_profile(firebase_uid, {
                "displayName": display_name,
                "email": email,
                "providerSlug": provider_slug,
                "customerId": customer_id,
                "role": "customer",
                "isActive": True,
            })
    except Exception as e:
        logger.error(f"Customer portal user created in Mongo but Firestore sync failed: {e}")
        raise HTTPException(status_code=500, detail="Customer login created but Firestore sync failed")

    return {
        "message": "Customer portal user registered",
        "provider_slug": provider_slug,
        "customer_id": customer_id,
        "username": username,
    }


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
    
    return to_json_safe(customers)


@app.post("/api/admin/customers")
async def api_create_customer(request: Request):
    """API: Create a customer."""
    require_admin(request)
    slug = get_provider_slug(request)
    payload = await read_request_payload(request)
    name = (payload.get("name") or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="Customer name is required")

    initial_reading = payload.get("initial_reading")
    if initial_reading in ("", None):
        initial_reading = None
    else:
        try:
            initial_reading = float(initial_reading)
        except (TypeError, ValueError):
            raise HTTPException(status_code=400, detail="Initial reading must be a number")
    
    customer_data = {
        "name": name,
        "phone": payload.get("phone") or None,
        "email": payload.get("email") or None,
        "location": payload.get("location") or None,
        "initial_reading": initial_reading
    }
    
    customer = crud.create_customer(slug, customer_data)
    
    if not customer:
        raise HTTPException(status_code=500, detail="Failed to create customer")
    
    return to_json_safe({"message": "Customer created", "customer": customer, "customer_id": customer["id"]})


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
    
    return to_json_safe(crud.get_all_readings(slug))


@app.post("/api/admin/customers/{customer_id}/readings")
async def api_add_reading(request: Request, customer_id: int):
    """API: Add a reading."""
    require_admin(request)
    slug = get_provider_slug(request)
    payload = await read_request_payload(request)
    reading_value = payload.get("reading_value")
    if reading_value in ("", None):
        reading_value = None
    else:
        try:
            reading_value = float(reading_value)
        except (TypeError, ValueError):
            raise HTTPException(status_code=400, detail="Reading value must be a number")
    
    customer = crud.get_customer(slug, customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    reading = crud.add_reading(slug, customer_id, reading_value)
    return to_json_safe({"message": "Reading added", "reading": reading, "reading_id": reading["id"]})


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
    
    return to_json_safe(crud.list_invoices(slug))


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
    
    return to_json_safe({"message": "Invoice generated", "invoice": inv, "invoice_id": inv["id"], "amount": amount})


@app.post("/api/admin/invoices/{invoice_id}/pay")
def api_pay_invoice(request: Request, invoice_id: int):
    """API: Mark invoice as paid."""
    require_admin(request)
    slug = get_provider_slug(request)
    
    inv = crud.mark_invoice_paid(slug, invoice_id)
    if not inv:
        raise HTTPException(status_code=404, detail="Invoice not found")
    
    return to_json_safe({"message": "Invoice marked as paid", "invoice": inv})


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
    return to_json_safe({"rate": rate, "effective_rate": effective})


@app.post("/api/admin/rate")
async def api_set_rate(request: Request):
    """API: Set rate configuration."""
    require_admin(request)
    slug = get_provider_slug(request)
    payload = await read_request_payload(request)
    mode = payload.get("mode")
    try:
        value = float(payload.get("value"))
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="Rate value must be a number")
    
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
    return to_json_safe(stats)


# ==================== SUPER ADMIN ROUTES ====================

@app.get("/api/super-admin/dashboard")
def api_super_admin_dashboard(request: Request):
    """API: Get platform-wide dashboard statistics for super admins."""
    require_super_admin(request)
    try:
        from app.firebase_firestore import get_platform_stats as get_firestore_platform_stats
        return get_firestore_platform_stats()
    except Exception as e:
        logger.warning(f"Falling back to Mongo platform stats: {e}")
        return crud_providers.get_platform_stats()


@app.get("/api/super-admin/providers")
def api_super_admin_providers(request: Request):
    """API: List all providers for super admin management."""
    require_super_admin(request)
    try:
        from app.firebase_firestore import list_providers as list_firestore_providers
        providers = list_firestore_providers(active_only=False)
        if providers:
            return [
                {
                    "id": provider.get("id", provider.get("slug")),
                    "name": provider.get("name"),
                    "slug": provider.get("slug"),
                    "contact_email": provider.get("contactEmail"),
                    "contact_phone": provider.get("contactPhone"),
                    "address": provider.get("address"),
                    "is_active": provider.get("isActive", True),
                    "settings": {
                        "rate_per_unit": provider.get("ratePerUnit", 1.5),
                        "currency": provider.get("currency", "KES"),
                    },
                    "branding": {},
                    "created_at": provider.get("createdAt"),
                    "updated_at": provider.get("updatedAt"),
                    "database_name": provider.get("database_name", f"firestore_{provider.get('slug')}"),
                    "subscription": None,
                    "admin_user_count": 1 if provider.get("contactEmail") else 0,
                    "customer_count": 0,
                    "invoice_count": 0,
                }
                for provider in providers
            ]
    except Exception as e:
        logger.warning(f"Falling back to Mongo providers for super admin list: {e}")

    providers = crud_providers.list_providers(active_only=False)
    return [to_response_dict(crud_providers.get_provider_detail(provider)) for provider in providers]


@app.post("/api/super-admin/workspace")
def api_super_admin_select_workspace(request: Request, payload: dict):
    """Select a provider workspace for provider-scoped admin routes."""
    require_super_admin(request)

    provider_slug = (payload.get("provider_slug") or "").strip().lower()
    if not provider_slug:
        raise HTTPException(status_code=400, detail="Provider slug is required")

    provider = None
    try:
        from app.firebase_firestore import get_provider as get_firestore_provider
        provider = get_firestore_provider(provider_slug)
        if provider and not provider.get("isActive", provider.get("is_active", True)):
            raise HTTPException(status_code=403, detail="Provider is not active")
    except HTTPException:
        raise
    except Exception as e:
        logger.warning(f"Falling back to Mongo provider lookup for workspace selection: {e}")

    if not provider:
        from app.mongodb_multitenant import get_provider as get_mongo_provider
        provider = get_mongo_provider(provider_slug)
        if provider and not provider.get("is_active", True):
            raise HTTPException(status_code=403, detail="Provider is not active")

    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")

    mongo_provider = ensure_mongo_provider_for_workspace(provider_slug, provider)
    request.session["provider_slug"] = provider_slug
    request.session["provider_id"] = mongo_provider.get("id", provider.get("id", provider_slug))

    return {
        "message": "Workspace selected",
        "provider_slug": provider_slug,
        "provider_name": provider.get("name"),
    }


@app.post("/api/super-admin/providers")
def api_super_admin_create_provider(request: Request, payload: dict):
    """API: Create a new provider."""
    require_super_admin(request)

    name = (payload.get("name") or "").strip()
    slug = (payload.get("slug") or "").strip().lower()
    if not name or not slug:
        raise HTTPException(status_code=400, detail="Provider name and slug are required")

    rate_per_unit = payload.get("rate_per_unit", 1.5)
    try:
        from app.firebase_firestore import create_provider as create_firestore_provider
        provider = create_firestore_provider(slug, {
            "name": name,
            "contact_email": payload.get("contact_email"),
            "contact_phone": payload.get("contact_phone"),
            "address": payload.get("address"),
            "rate_per_unit": rate_per_unit,
            "currency": "KES",
        })
        try:
            ensure_mongo_provider_for_workspace(slug, provider)
        except Exception as e:
            logger.warning(f"Created Firestore provider but could not create Mongo billing database: {e}")
        return {
            "message": "Provider created successfully",
            "provider": {
                "id": provider.get("id", provider.get("slug")),
                "name": provider.get("name"),
                "slug": provider.get("slug"),
                "contact_email": provider.get("contactEmail"),
                "contact_phone": provider.get("contactPhone"),
                "address": provider.get("address"),
                "is_active": provider.get("isActive", True),
                "settings": {
                    "rate_per_unit": provider.get("ratePerUnit", 1.5),
                    "currency": provider.get("currency", "KES"),
                },
                "branding": {},
                "created_at": provider.get("createdAt"),
                "updated_at": provider.get("updatedAt"),
                "database_name": provider.get("database_name", f"firestore_{provider.get('slug')}"),
                "subscription": None,
                "admin_user_count": 1 if provider.get("contactEmail") else 0,
                "customer_count": 0,
                "invoice_count": 0,
            },
        }
    except Exception as e:
        logger.warning(f"Falling back to Mongo provider creation: {e}")
        provider = crud_providers.create_provider({
            "name": name,
            "slug": slug,
            "contact_email": payload.get("contact_email"),
            "contact_phone": payload.get("contact_phone"),
            "address": payload.get("address"),
            "settings": {
                "rate_per_unit": rate_per_unit,
                "currency": "KES",
            },
        })
        return {"message": "Provider created successfully", "provider": to_response_dict(crud_providers.get_provider_detail(provider))}


@app.put("/api/super-admin/providers/{provider_slug}")
def api_super_admin_update_provider(request: Request, provider_slug: str, payload: dict):
    """API: Update provider details."""
    require_super_admin(request)
    update_data = {
        key: value
        for key, value in payload.items()
        if key in {"name", "contact_email", "contact_phone", "address", "is_active"} and value is not None
    }
    try:
        from app.firebase_firestore import update_provider as update_firestore_provider
        provider = update_firestore_provider(provider_slug, update_data)
        if provider:
            return {
                "message": "Provider updated successfully",
                "provider": {
                    "id": provider.get("id", provider.get("slug")),
                    "name": provider.get("name"),
                    "slug": provider.get("slug"),
                    "contact_email": provider.get("contactEmail"),
                    "contact_phone": provider.get("contactPhone"),
                    "address": provider.get("address"),
                    "is_active": provider.get("isActive", True),
                    "settings": {
                        "rate_per_unit": provider.get("ratePerUnit", 1.5),
                        "currency": provider.get("currency", "KES"),
                    },
                    "branding": {},
                    "created_at": provider.get("createdAt"),
                    "updated_at": provider.get("updatedAt"),
                    "database_name": provider.get("database_name", f"firestore_{provider.get('slug')}"),
                    "subscription": None,
                    "admin_user_count": 1 if provider.get("contactEmail") else 0,
                    "customer_count": 0,
                    "invoice_count": 0,
                },
            }
    except Exception as e:
        logger.warning(f"Falling back to Mongo provider update: {e}")

    provider = crud_providers.update_provider(provider_slug, update_data)
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")
    return {"message": "Provider updated successfully", "provider": to_response_dict(crud_providers.get_provider_detail(provider))}


@app.post("/api/super-admin/providers/{provider_slug}/activate")
def api_super_admin_activate_provider(request: Request, provider_slug: str):
    """API: Activate a provider."""
    require_super_admin(request)
    try:
        from app.firebase_firestore import set_provider_active
        if set_provider_active(provider_slug, True):
            return {"message": "Provider activated successfully"}
    except Exception as e:
        logger.warning(f"Falling back to Mongo provider activation: {e}")

    if not crud_providers.activate_provider(provider_slug):
        raise HTTPException(status_code=404, detail="Provider not found")
    return {"message": "Provider activated successfully"}


@app.post("/api/super-admin/providers/{provider_slug}/deactivate")
def api_super_admin_deactivate_provider(request: Request, provider_slug: str):
    """API: Deactivate a provider."""
    require_super_admin(request)
    try:
        from app.firebase_firestore import set_provider_active
        if set_provider_active(provider_slug, False):
            return {"message": "Provider deactivated successfully"}
    except Exception as e:
        logger.warning(f"Falling back to Mongo provider deactivation: {e}")

    if not crud_providers.deactivate_provider(provider_slug):
        raise HTTPException(status_code=404, detail="Provider not found")
    return {"message": "Provider deactivated successfully"}


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
    
    return to_json_safe({
        "customer": customer,
        "recent_invoices": recent_invoices,
        "usage_history": usage_history,
        "benchmark": benchmark,
        "alerts": alerts,
        "total_due": total_due
    })


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
    # Use Railway's PORT env variable
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)

