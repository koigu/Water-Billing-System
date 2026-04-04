"""
Provider CRUD Operations for Multi-Tenant Water Billing System.
Handles provider management, admin users, and authentication.
Supports TWO-TIER ADMIN SYSTEM:
- Super Admin: Platform-wide access, manages all providers, billing, analytics
- Provider Admin: Manages their own provider's customers, invoices, readings
"""
import os
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from passlib.context import CryptContext
from bson import ObjectId

from app import mongodb_multitenant as mt_db
from app.models import (
    ProviderCreate,
    ProviderUpdate,
    ProviderSettings,
    ProviderBranding,
    AdminUserCreate,
    AdminUserUpdate,
    AdminUserInDB,
    AdminLoginRequest,
    AdminLoginResponse,
    AdminUserResponse,
    ProviderResponse,
    ProviderDetailResponse,
    # Super Admin schemas
    SuperAdminCreate,
    SuperAdminLoginRequest,
    SuperAdminLoginResponse,
    SuperAdminResponse,
    PlatformStats,
    ProviderPerformance,
    LoginLog,
    ProviderSubscription,
    PaymentRecord,
)

logger = logging.getLogger(__name__)
logger.info("*** crud_providers.py module loading started ***")

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT configuration
JWT_SECRET = os.getenv("JWT_SECRET", "your-super-secret-jwt-key-change-in-production")
JWT_ALGORITHM = "HS256"
TOKEN_EXPIRE_HOURS = 24


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against a hash."""
    return pwd_context.verify(plain_password, hashed_password)


def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    return pwd_context.hash(password)


# ==================== SUPER ADMIN CRUD (Platform-Wide) ====================

def get_super_admin_collection():
    """Get the super admin users collection from master database."""
    return mt_db.get_master_db()["super_admins"]


def get_login_logs_collection():
    """Get the login logs collection from master database."""
    return mt_db.get_master_db()["login_logs"]


def get_provider_subscriptions_collection():
    """Get the provider subscriptions collection from master database."""
    return mt_db.get_master_db()["provider_subscriptions"]


def get_payment_records_collection():
    """Get the payment records collection from master database."""
    return mt_db.get_master_db()["payment_records"]


def get_next_super_admin_id() -> int:
    """Get next auto-increment ID for super admin."""
    master_db = mt_db.get_master_db()
    result = master_db["admin_counter"].find_one_and_update(
        {"_id": "super_admins"},
        {"$inc": {"seq": 1}},
        upsert=True,
        return_document=True
    )
    return result.get("seq", 1)


def get_next_subscription_id() -> int:
    """Get next auto-increment ID for subscriptions."""
    master_db = mt_db.get_master_db()
    result = master_db["admin_counter"].find_one_and_update(
        {"_id": "subscriptions"},
        {"$inc": {"seq": 1}},
        upsert=True,
        return_document=True
    )
    return result.get("seq", 1)


def get_next_payment_record_id() -> int:
    """Get next auto-increment ID for payment records."""
    master_db = mt_db.get_master_db()
    result = master_db["admin_counter"].find_one_and_update(
        {"_id": "payment_records"},
        {"$inc": {"seq": 1}},
        upsert=True,
        return_document=True
    )
    return result.get("seq", 1)


def get_next_login_log_id() -> int:
    """Get next auto-increment ID for login logs."""
    master_db = mt_db.get_master_db()
    result = master_db["admin_counter"].find_one_and_update(
        {"_id": "login_logs"},
        {"$inc": {"seq": 1}},
        upsert=True,
        return_document=True
    )
    return result.get("seq", 1)


def create_super_admin(admin_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create a super admin user (platform-wide access).
    
    Args:
        admin_data: Dictionary containing super admin information
    
    Returns:
        Created super admin document
    """
    try:
        # Check if super admin already exists
        existing = get_super_admin_collection().find_one({
            "username": admin_data["username"]
        })
        if existing:
            raise ValueError("Super admin with this username already exists")
        
        # Hash password
        password_hash = hash_password(admin_data["password"])
        
        # Create super admin document
        super_admin_doc = {
            "id": get_next_super_admin_id(),
            "username": admin_data["username"],
            "email": admin_data.get("email"),
            "full_name": admin_data.get("full_name"),
            "password_hash": password_hash,
            "is_active": True,
            "created_at": datetime.utcnow(),
            "updated_at": None,
            "last_login": None
        }
        
        # Insert into master database
        result = get_super_admin_collection().insert_one(super_admin_doc)
        super_admin_doc["_id"] = result.inserted_id
        
        logger.info(f"Created super admin: {super_admin_doc['username']}")
        
        return super_admin_doc
        
    except ValueError as e:
        logger.error(f"Super admin creation failed: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error creating super admin: {e}")
        raise


def get_super_admin_by_username(username: str) -> Optional[Dict[str, Any]]:
    """Get super admin by username."""
    return get_super_admin_collection().find_one({"username": username})


def get_super_admin_by_id(admin_id: int) -> Optional[Dict[str, Any]]:
    """Get super admin by ID."""
    return get_super_admin_collection().find_one({"id": admin_id})


def authenticate_super_admin(username: str, password: str, ip_address: str = None, user_agent: str = None) -> Optional[Dict[str, Any]]:
    """
    Authenticate a super admin user.
    
    Args:
        username: Admin username
        password: Plain text password
        ip_address: Client IP address for logging
        user_agent: Client user agent for logging
    
    Returns:
        Super admin document if authenticated, None otherwise
    """
    # Get super admin
    admin = get_super_admin_by_username(username)
    
    if not admin:
        logger.warning(f"Super admin authentication failed: User not found - {username}")
        log_login_attempt("super_admin", 0, username, False, "User not found", ip_address, user_agent)
        return None
    
    if not admin.get("is_active", True):
        logger.warning(f"Super admin authentication failed: User inactive - {username}")
        log_login_attempt("super_admin", admin["id"], username, False, "User inactive", ip_address, user_agent)
        return None
    
    # Verify password
    if not verify_password(password, admin["password_hash"]):
        logger.warning(f"Super admin authentication failed: Invalid password - {username}")
        log_login_attempt("super_admin", admin["id"], username, False, "Invalid password", ip_address, user_agent)
        return None
    
    # Update last login
    get_super_admin_collection().update_one(
        {"_id": admin["_id"]},
        {"$set": {"last_login": datetime.utcnow()}}
    )
    
    admin["last_login"] = datetime.utcnow()
    
    logger.info(f"Super admin authenticated: {username}")
    
    # Log successful login
    log_login_attempt("super_admin", admin["id"], username, True, None, ip_address, user_agent)
    
    return admin


def log_login_attempt(
    user_type: str,
    user_id: int,
    username: str,
    success: bool,
    failure_reason: str = None,
    ip_address: str = None,
    user_agent: str = None
):
    """Log a login attempt."""
    log_doc = {
        "id": get_next_login_log_id(),
        "user_type": user_type,  # "super_admin", "provider_admin", "customer"
        "user_id": user_id,
        "username": username,
        "ip_address": ip_address,
        "user_agent": user_agent,
        "login_time": datetime.utcnow(),
        "success": success,
        "failure_reason": failure_reason
    }
    
    # For provider admins, we need to find provider_id
    if user_type == "provider_admin":
        admin = mt_db.get_admin_users_collection().find_one({"username": username})
        if admin:
            log_doc["provider_id"] = admin.get("provider_id")
            log_doc["provider_slug"] = mt_db.get_provider_by_id(admin.get("provider_id", 0)).get("slug") if admin.get("provider_id") else None
    
    get_login_logs_collection().insert_one(log_doc)


def create_super_admin_token(super_admin: Dict[str, Any]) -> str:
    """
    Create JWT token for super admin.
    
    Args:
        super_admin: Super admin document
    
    Returns:
        JWT token string
    """
    import base64
    import json
    
    # Create token payload
    payload = {
        "admin_id": super_admin["id"],
        "username": super_admin["username"],
        "admin_type": "super_admin",
        "exp": datetime.utcnow() + timedelta(hours=24),
        "iat": datetime.utcnow()
    }
    
    # Encode as base64
    token_data = base64.b64encode(json.dumps(payload).encode()).decode()
    
    return f"super_admin_{token_data}"


def verify_super_admin_token(token: str) -> Optional[Dict[str, Any]]:
    """Verify a super admin token."""
    try:
        import base64
        import json
        
        if not token.startswith("super_admin_"):
            return None
        
        # Decode token
        token_data = token[13:]  # Remove "super_admin_" prefix
        payload = json.loads(base64.b64decode(token_data.encode()).decode())
        
        # Check expiration
        exp = datetime.fromisoformat(payload.get("exp"))
        if datetime.utcnow() > exp:
            return None
        
        # Verify admin still exists and is active
        admin = get_super_admin_by_id(payload.get("admin_id"))
        if not admin or not admin.get("is_active", True):
            return None
        
        return admin
        
    except Exception as e:
        logger.error(f"Super admin token verification failed: {e}")
        return None


def login_super_admin(credentials: SuperAdminLoginRequest, ip_address: str = None, user_agent: str = None) -> Optional[SuperAdminLoginResponse]:
    """
    Login a super admin and return response with token.
    
    Args:
        credentials: Login credentials
        ip_address: Client IP for logging
        user_agent: Client user agent for logging
    
    Returns:
        SuperAdminLoginResponse with token or None if failed
    """
    # Authenticate super admin
    admin = authenticate_super_admin(
        username=credentials.username,
        password=credentials.password,
        ip_address=ip_address,
        user_agent=user_agent
    )
    
    if not admin:
        return None
    
    # Create token
    token = create_super_admin_token(admin)
    
    # Build response
    admin_response = SuperAdminResponse(
        id=admin["id"],
        username=admin["username"],
        email=admin.get("email"),
        full_name=admin.get("full_name"),
        is_active=admin.get("is_active", True),
        last_login=admin.get("last_login")
    )
    
    return SuperAdminLoginResponse(
        access_token=token,
        token_type="bearer",
        expires_in=86400,  # 24 hours
        super_admin=admin_response
    )


# ==================== PLATFORM ANALYTICS ====================

def get_platform_stats() -> PlatformStats:
    """Get platform-wide statistics for super admin dashboard."""
    providers = list(mt_db.get_providers_collection().find())
    
    total_providers = len(providers)
    active_providers = sum(1 for p in providers if p.get("is_active", True))
    
    total_customers = 0
    total_invoices = 0
    total_payments = 0.0
    total_revenue = 0.0
    pending_invoices = 0
    overdue_invoices = 0
    
    # Aggregate stats from all provider databases
    for provider in providers:
        if not provider.get("is_active", True):
            continue
        
        try:
            db = mt_db.get_provider_db(provider["slug"])
            if db:
                # Count customers
                total_customers += db["customers"].count_documents({"is_active": True})
                
                # Count invoices
                invoices = list(db["invoices"].find())
                total_invoices += len(invoices)
                
                # Calculate payments
                payments = list(db["payments"].find({"status": "completed"}))
                total_payments += sum(p.get("amount", 0) for p in payments)
                
                # Calculate revenue (paid invoices)
                paid_invoices = [inv for inv in invoices if inv.get("status") == "paid"]
                total_revenue += sum(inv.get("amount", 0) for inv in paid_invoices)
                
                # Count pending and overdue
                pending_invoices += sum(1 for inv in invoices if inv.get("status") == "pending")
                overdue_invoices += sum(1 for inv in invoices if inv.get("status") == "overdue")
                
        except Exception as e:
            logger.error(f"Error getting stats for provider {provider['slug']}: {e}")
            continue
    
    return PlatformStats(
        total_providers=total_providers,
        active_providers=active_providers,
        total_customers=total_customers,
        total_invoices=total_invoices,
        total_payments=round(total_payments, 2),
        total_revenue=round(total_revenue, 2),
        pending_invoices=pending_invoices,
        overdue_invoices=overdue_invoices
    )


def get_provider_performance(provider_slug: str) -> Optional[ProviderPerformance]:
    """Get performance metrics for a specific provider."""
    provider = mt_db.get_provider(provider_slug)
    if not provider:
        return None
    
    try:
        db = mt_db.get_provider_db(provider_slug)
        if not db:
            return None
        
        # Get stats
        total_customers = db["customers"].count_documents({"is_active": True})
        invoices = list(db["invoices"].find())
        total_invoices = len(invoices)
        
        # Calculate revenue
        paid_invoices = [inv for inv in invoices if inv.get("status") == "paid"]
        total_revenue = sum(inv.get("amount", 0) for inv in paid_invoices)
        
        # Calculate active customers (with activity in last 90 days)
        from datetime import timedelta
        ninety_days_ago = datetime.utcnow() - timedelta(days=90)
        active_customers = db["customers"].count_documents({
            "id": {"$in": db["meter_readings"].distinct("customer_id", {"recorded_at": {"$gte": ninety_days_ago}})}
        })
        
        # Calculate payment rate
        payment_rate = (len(paid_invoices) / total_invoices * 100) if total_invoices > 0 else 0.0
        
        # Get last activity
        last_reading = db["meter_readings"].find_one(sort=[("recorded_at", -1)])
        last_activity = last_reading.get("recorded_at") if last_reading else None
        
        return ProviderPerformance(
            provider_id=provider["id"],
            provider_name=provider["name"],
            provider_slug=provider["slug"],
            total_customers=total_customers,
            total_invoices=total_invoices,
            total_revenue=round(total_revenue, 2),
            active_customers=active_customers,
            payment_rate=round(payment_rate, 2),
            last_activity=last_activity
        )
        
    except Exception as e:
        logger.error(f"Error getting performance for provider {provider_slug}: {e}")
        return None


def get_all_providers_performance() -> List[ProviderPerformance]:
    """Get performance metrics for all providers."""
    providers = mt_db.list_providers(active_only=False)
    
    performances = []
    for provider in providers:
        perf = get_provider_performance(provider["slug"])
        if perf:
            performances.append(perf)
    
    return performances


def get_login_logs(limit: int = 100, user_type: str = None) -> List[Dict[str, Any]]:
    """Get login logs with optional filtering."""
    query = {}
    if user_type:
        query["user_type"] = user_type
    
    return list(get_login_logs_collection().find(query).sort("login_time", -1).limit(limit))


def get_recent_login_logs(provider_slug: str = None, limit: int = 50) -> List[Dict[str, Any]]:
    """Get recent login logs for a provider or platform."""
    if provider_slug:
        # Get provider's admin users' IDs
        provider = mt_db.get_provider(provider_slug)
        if not provider:
            return []
        
        admin_ids = [admin["id"] for admin in mt_db.get_admin_users_collection().find({"provider_id": provider["id"]})]
        
        return list(get_login_logs_collection().find({
            "user_type": "provider_admin",
            "user_id": {"$in": admin_ids}
        }).sort("login_time", -1).limit(limit))
    
    # Platform-wide logs
    return list(get_login_logs_collection().find().sort("login_time", -1).limit(limit))


# ==================== PROVIDER SUBSCRIPTION & BILLING ====================

def create_provider_subscription(provider_id: int, plan: str = "basic", monthly_fee: float = 0.0) -> Dict[str, Any]:
    """Create a subscription for a provider."""
    subscription_doc = {
        "id": get_next_subscription_id(),
        "provider_id": provider_id,
        "plan": plan,
        "monthly_fee": monthly_fee,
        "customer_limit": 100 if plan == "basic" else (500 if plan == "premium" else -1),
        "features": get_plan_features(plan),
        "billing_cycle_start": datetime.utcnow(),
        "next_billing_date": datetime.utcnow() + timedelta(days=30),
        "last_payment_date": None,
        "last_payment_amount": 0.0,
        "payment_status": "active",
        "paybill_number": None,
        "till_number": None,
        "created_at": datetime.utcnow(),
        "updated_at": None
    }
    
    get_provider_subscriptions_collection().insert_one(subscription_doc)
    
    logger.info(f"Created subscription for provider {provider_id}: {plan} plan")
    
    return subscription_doc


def get_provider_subscription(provider_id: int) -> Optional[Dict[str, Any]]:
    """Get subscription for a provider."""
    return get_provider_subscriptions_collection().find_one({"provider_id": provider_id})


def update_provider_subscription(provider_id: int, update_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Update provider subscription."""
    update_data["updated_at"] = datetime.utcnow()
    
    return get_provider_subscriptions_collection().find_one_and_update(
        {"provider_id": provider_id},
        {"$set": update_data},
        return_document=True
    )


def record_payment(payment_data: Dict[str, Any]) -> Dict[str, Any]:
    """Record a subscription payment."""
    payment_doc = {
        "id": get_next_payment_record_id(),
        "provider_id": payment_data["provider_id"],
        "amount": payment_data["amount"],
        "payment_method": payment_data.get("payment_method", "cash"),
        "transaction_id": payment_data.get("transaction_id"),
        "payment_date": datetime.utcnow(),
        "payment_period_start": payment_data.get("payment_period_start"),
        "payment_period_end": payment_data.get("payment_period_end"),
        "status": payment_data.get("status", "completed"),
        "notes": payment_data.get("notes")
    }
    
    get_payment_records_collection().insert_one(payment_doc)
    
    # Update subscription
    update_provider_subscription(payment_data["provider_id"], {
        "last_payment_date": datetime.utcnow(),
        "last_payment_amount": payment_data["amount"],
        "payment_status": "active",
        "next_billing_date": datetime.utcnow() + timedelta(days=30)
    })
    
    logger.info(f"Recorded payment for provider {payment_data['provider_id']}: {payment_data['amount']}")
    
    return payment_doc


def get_provider_payments(provider_id: int) -> List[Dict[str, Any]]:
    """Get all payments for a provider."""
    return list(get_payment_records_collection().find(
        {"provider_id": provider_id}
    ).sort("payment_date", -1))


def get_plan_features(plan: str) -> List[str]:
    """Get features for a subscription plan."""
    plans = {
        "basic": [
            "Up to 100 customers",
            "Basic invoicing",
            "Email support",
            "Standard analytics"
        ],
        "premium": [
            "Up to 500 customers",
            "Advanced invoicing",
            "SMS & Email support",
            "Advanced analytics",
            "Priority support"
        ],
        "enterprise": [
            "Unlimited customers",
            "All invoicing features",
            "24/7 dedicated support",
            "Custom analytics",
            "API access",
            "White-label options"
        ]
    }
    return plans.get(plan, plans["basic"])


# ==================== PROVIDER CRUD ====================

def create_provider(provider_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create a new provider with database and settings.
    
    Args:
        provider_data: Dictionary containing provider information
    
    Returns:
        Created provider document
    """
    try:
        # Create provider in master database
        provider = mt_db.create_provider(provider_data)
        
        # Create subscription for provider
        create_provider_subscription(provider["id"], plan="basic", monthly_fee=0.0)
        
        logger.info(f"Created provider: {provider['name']} (slug: {provider['slug']})")
        
        return provider
        
    except ValueError as e:
        logger.error(f"Provider creation failed: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error creating provider: {e}")
        raise


def get_provider(slug: str) -> Optional[Dict[str, Any]]:
    """Get provider by slug."""
    return mt_db.get_provider(slug)


def get_provider_by_id(provider_id: int) -> Optional[Dict[str, Any]]:
    """Get provider by ID."""
    return mt_db.get_provider_by_id(provider_id)


def list_providers(active_only: bool = True) -> List[Dict[str, Any]]:
    """List all providers."""
    return mt_db.list_providers(active_only)


def update_provider(slug: str, update_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Update provider information."""
    return mt_db.update_provider(slug, update_data)


def deactivate_provider(slug: str) -> bool:
    """Deactivate a provider (soft delete)."""
    return mt_db.deactivate_provider(slug)


def delete_provider(slug: str, delete_database: bool = False) -> bool:
    """Delete a provider."""
    return mt_db.delete_provider(slug, delete_database)


def get_provider_response(provider: Dict[str, Any]) -> ProviderResponse:
    """Convert provider document to response model."""
    return ProviderResponse(
        id=provider["id"],
        name=provider["name"],
        slug=provider["slug"],
        branding=ProviderBranding(**provider.get("branding", {})) if provider.get("branding") else None
    )


def get_provider_detail(provider: Dict[str, Any]) -> ProviderDetailResponse:
    """Get detailed provider information."""
    admin_count = mt_db.get_admin_users_collection().count_documents(
        {"provider_id": provider["id"], "is_active": True}
    )
    
    return ProviderDetailResponse(
        id=provider["id"],
        name=provider["name"],
        slug=provider["slug"],
        contact_email=provider.get("contact_email"),
        contact_phone=provider.get("contact_phone"),
        address=provider.get("address"),
        is_active=provider.get("is_active", True),
        settings=ProviderSettings(**provider.get("settings", {})),
        branding=ProviderBranding(**provider.get("branding", {})) if provider.get("branding") else ProviderBranding(),
        created_at=provider.get("created_at", datetime.utcnow()),
        updated_at=provider.get("updated_at"),
        database_name=provider["database_name"],
        admin_user_count=admin_count
    )


# ==================== ADMIN USER CRUD ====================

def create_admin_user(admin_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create a new admin user for a provider.
    
    Args:
        admin_data: Dictionary containing admin user information
    
    Returns:
        Created admin user document
    """
    try:
        # Validate provider exists
        provider = mt_db.get_provider(admin_data.get("provider_slug") or admin_data.get("provider_id"))
        if not provider:
            raise ValueError("Provider not found")
        
        # Hash password
        password_hash = hash_password(admin_data["password"])
        
        # Create admin user document
        admin_doc = {
            "id": mt_db.get_next_admin_id(),
            "provider_id": provider["id"],
            "username": admin_data["username"],
            "email": admin_data.get("email"),
            "full_name": admin_data.get("full_name"),
            "password_hash": password_hash,
            "is_active": True,
            "is_super_admin": admin_data.get("is_super_admin", False),
            "created_at": datetime.utcnow(),
            "updated_at": None,
            "last_login": None
        }
        
        # Insert into master database
        result = mt_db.get_admin_users_collection().insert_one(admin_doc)
        admin_doc["_id"] = result.inserted_id
        
        logger.info(f"Created admin user: {admin_doc['username']} for provider: {provider['slug']}")
        
        return admin_doc
        
    except ValueError as e:
        logger.error(f"Admin user creation failed: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error creating admin user: {e}")
        raise


def get_admin_user(provider_id: int, admin_id: int) -> Optional[Dict[str, Any]]:
    """Get admin user by ID."""
    return mt_db.get_admin_users_collection().find_one({
        "provider_id": provider_id,
        "id": admin_id
    })


def get_admin_user_by_username(provider_id: int, username: str) -> Optional[Dict[str, Any]]:
    """Get admin user by username."""
    return mt_db.get_admin_users_collection().find_one({
        "provider_id": provider_id,
        "username": username
    })


def list_admin_users(provider_id: int, active_only: bool = True) -> List[Dict[str, Any]]:
    """List all admin users for a provider."""
    query = {"provider_id": provider_id}
    if active_only:
        query["is_active"] = True
    
    return list(mt_db.get_admin_users_collection().find(query))


def update_admin_user(provider_id: int, admin_id: int, update_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Update admin user information."""
    update_data["updated_at"] = datetime.utcnow()
    
    # Don't allow updating password through this method
    if "password" in update_data:
        del update_data["password"]
    
    return mt_db.get_admin_users_collection().find_one_and_update(
        {"provider_id": provider_id, "id": admin_id},
        {"$set": update_data},
        return_document=True
    )


def deactivate_admin_user(provider_id: int, admin_id: int) -> bool:
    """Deactivate an admin user."""
    result = mt_db.get_admin_users_collection().update_one(
        {"provider_id": provider_id, "id": admin_id},
        {"$set": {"is_active": False, "updated_at": datetime.utcnow()}}
    )
    return result.modified_count > 0


def delete_admin_user(provider_id: int, admin_id: int) -> bool:
    """Delete an admin user."""
    result = mt_db.get_admin_users_collection().delete_one({
        "provider_id": provider_id,
        "id": admin_id
    })
    return result.deleted_count > 0


def update_admin_password(provider_id: int, admin_id: int, new_password: str) -> bool:
    """Update admin user password."""
    password_hash = hash_password(new_password)
    
    result = mt_db.get_admin_users_collection().update_one(
        {"provider_id": provider_id, "id": admin_id, "is_active": True},
        {"$set": {"password_hash": password_hash, "updated_at": datetime.utcnow()}}
    )
    
    return result.modified_count > 0


# ==================== ADMIN AUTHENTICATION ====================

def authenticate_admin(username: str, password: str, provider_slug: str = None) -> Optional[Dict[str, Any]]:
    """
    Authenticate an admin user.
    
    Args:
        username: Admin username
        password: Plain text password
        provider_slug: Provider slug (required if not using subdomain)
    
    Returns:
        Admin user document if authenticated, None otherwise
    """
    try:
        # Get provider
        if provider_slug:
            provider = mt_db.get_provider(provider_slug)
        else:
            # Try to get provider from context or session
            raise ValueError("Provider slug is required")
        
        if not provider:
            logger.warning(f"Authentication failed: Provider not found - {provider_slug}")
            return None
        
        # Get admin user
        admin = get_admin_user_by_username(provider["id"], username)
        
        if not admin:
            logger.warning(f"Authentication failed: User not found - {username}")
            return None
        
        if not admin.get("is_active", True):
            logger.warning(f"Authentication failed: User inactive - {username}")
            return None
        
        # Verify password
        if not verify_password(password, admin["password_hash"]):
            logger.warning(f"Authentication failed: Invalid password - {username}")
            return None
        
        # Update last login
        mt_db.get_admin_users_collection().update_one(
            {"_id": admin["_id"]},
            {"$set": {"last_login": datetime.utcnow()}}
        )
        
        admin["last_login"] = datetime.utcnow()
        
        logger.info(f"Admin authenticated: {username} for provider: {provider['slug']}")
        
        return admin
        
    except Exception as e:
        logger.error(f"Authentication error: {e}")
        return None


def create_admin_token(admin_user: Dict[str, Any], provider: Dict[str, Any]) -> str:
    """
    Create JWT token for admin user.
    
    Args:
        admin_user: Admin user document
        provider: Provider document
    
    Returns:
        JWT token string
    """
    import base64
    import json
    
    # Create token payload
    payload = {
        "admin_id": admin_user["id"],
        "username": admin_user["username"],
        "provider_id": provider["id"],
        "provider_slug": provider["slug"],
        "is_super_admin": admin_user.get("is_super_admin", False),
        "exp": datetime.utcnow() + timedelta(hours=TOKEN_EXPIRE_HOURS),
        "iat": datetime.utcnow()
    }
    
    # Encode as base64 (simple token for now, would use JWT in production)
    token_data = base64.b64encode(json.dumps(payload).encode()).decode()
    
    return f"admin_{token_data}"


def verify_admin_token(token: str, provider_slug: str = None) -> bool:
    """
    Verify an admin token.
    
    Args:
        token: JWT token string
        provider_slug: Provider slug (optional)
    
    Returns:
        True if token is valid, False otherwise
    """
    try:
        import base64
        import json
        
        if not token.startswith("admin_"):
            return False
        
        # Decode token
        token_data = token[6:]  # Remove "admin_" prefix
        payload = json.loads(base64.b64decode(token_data.encode()).decode())
        
        # Check expiration
        exp = datetime.fromisoformat(payload.get("exp"))
        if datetime.utcnow() > exp:
            return False
        
        # Check provider match
        if provider_slug and payload.get("provider_slug") != provider_slug:
            return False
        
        return True
        
    except Exception as e:
        logger.error(f"Token verification failed: {e}")
        return False


def decode_admin_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Decode admin token payload.
    
    Args:
        token: JWT token string
    
    Returns:
        Token payload dict or None if invalid
    """
    try:
        import base64
        import json
        
        if not token.startswith("admin_"):
            return None
        
        token_data = token[6:]
        payload = json.loads(base64.b64decode(token_data.encode()).decode())
        
        return payload
        
    except Exception as e:
        logger.error(f"Token decode failed: {e}")
        return None


def login_admin(credentials: AdminLoginRequest) -> Optional[AdminLoginResponse]:
    """
    Login an admin user and return response with token.
    
    Args:
        credentials: Login credentials
    
    Returns:
        AdminLoginResponse with token or None if failed
    """
    # Authenticate admin
    admin = authenticate_admin(
        username=credentials.username,
        password=credentials.password,
        provider_slug=credentials.provider_slug
    )
    
    if not admin:
        return None
    
    # Get provider
    provider = mt_db.get_provider(credentials.provider_slug) if credentials.provider_slug else None
    
    if not provider:
        return None
    
    # Create token
    token = create_admin_token(admin, provider)
    
    # Build response
    admin_response = AdminUserResponse(
        id=admin["id"],
        username=admin["username"],
        email=admin.get("email"),
        full_name=admin.get("full_name"),
        is_active=admin.get("is_active", True),
        is_super_admin=admin.get("is_super_admin", False),
        last_login=admin.get("last_login"),
        provider_id=admin["provider_id"]
    )
    
    provider_response = ProviderResponse(
        id=provider["id"],
        name=provider["name"],
        slug=provider["slug"],
        branding=ProviderBranding(**provider.get("branding", {})) if provider.get("branding") else None
    )
    
    return AdminLoginResponse(
        access_token=token,
        token_type="bearer",
        expires_in=TOKEN_EXPIRE_HOURS * 3600,
        admin_user=admin_response,
        provider=provider_response
    )


# ==================== ADMIN RESPONSE CONVERSION ====================

def get_admin_user_response(admin: Dict[str, Any]) -> AdminUserResponse:
    """Convert admin document to response model."""
    return AdminUserResponse(
        id=admin["id"],
        username=admin["username"],
        email=admin.get("email"),
        full_name=admin.get("full_name"),
        is_active=admin.get("is_active", True),
        is_super_admin=admin.get("is_super_admin", False),
        last_login=admin.get("last_login"),
        provider_id=admin["provider_id"]
    )


# ==================== PROVIDER SETTINGS ====================

def update_provider_settings(slug: str, settings: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Update provider settings."""
    return update_provider(slug, {"settings": settings})


def update_provider_branding(slug: str, branding: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Update provider branding."""
    return update_provider(slug, {"branding": branding})


def get_provider_settings(slug: str) -> ProviderSettings:
    """Get provider settings."""
    provider = get_provider(slug)
    if provider:
        return ProviderSettings(**provider.get("settings", {}))
    return ProviderSettings()


def get_provider_branding(slug: str) -> ProviderBranding:
    """Get provider branding."""
    provider = get_provider(slug)
    if provider:
        return ProviderBranding(**provider.get("branding", {}))
    return ProviderBranding()


# ==================== PROVIDER ACTIVATION ====================

def activate_provider(slug: str) -> bool:
    """Activate a provider."""
    result = update_provider(slug, {"is_active": True})
    return result is not None


# ==================== UTILITY FUNCTIONS ====================

def provider_exists(slug: str) -> bool:
    """Check if provider exists."""
    return get_provider(slug) is not None


def admin_user_exists(provider_id: int, username: str) -> bool:
    """Check if admin username exists for provider."""
    return get_admin_user_by_username(provider_id, username) is not None


def is_provider_active(slug: str) -> bool:
    """Check if provider is active."""
    provider = get_provider(slug)
    return provider.get("is_active", False) if provider else False


# ==================== EXPORTED FUNCTIONS ====================

__all__ = [
    # Password utilities
    "verify_password",
    "hash_password",
    
    # Provider CRUD
    "create_provider",
    "get_provider",
    "get_provider_by_id",
    "list_providers",
    "update_provider",
    "deactivate_provider",
    "delete_provider",
    "get_provider_response",
    "get_provider_detail",
    
    # Admin User CRUD
    "create_admin_user",
    "get_admin_user",
    "get_admin_user_by_username",
    "list_admin_users",
    "update_admin_user",
    "deactivate_admin_user",
    "delete_admin_user",
    "update_admin_password",
    "get_admin_user_response",
    
    # Authentication
    "authenticate_admin",
    "create_admin_token",
    "verify_admin_token",
    "decode_admin_token",
    "login_admin",
    
    # Settings
    "update_provider_settings",
    "update_provider_branding",
    "get_provider_settings",
    "get_provider_branding",
    
    # Activation
    "activate_provider",
    
    # Utilities
    "provider_exists",
    "admin_user_exists",
    "is_provider_active",
]

# ==================== CRUD PROVIDERS NAMESPACE ====================
# Fix for main_multitenant.py import expectation

class CrudProviders:
    """Namespace object matching main_multitenant.py expectations."""
    pass

crud_providers = CrudProviders()

# Dynamically attach all exported functions to the namespace object
for func_name in __all__:
    if func_name in globals():
        setattr(crud_providers, func_name, globals()[func_name])

