"""
Multi-Tenant Provider Models for Water Billing System.
Defines Provider/Tenant schema with admin users, branding, and settings.
Supports TWO-TIER ADMIN SYSTEM:
- Super Admin: Platform-wide access, manages all providers, billing, analytics
- Provider Admin: Manages their own provider's customers, invoices, readings
"""
from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, EmailStr, Field
import secrets
import re


def generate_db_suffix(length: int = 8) -> str:
    """Generate a random suffix for database names."""
    return secrets.token_hex(length // 2)


def validate_slug(slug: str) -> str:
    """Validate and normalize provider slug."""
    # Convert to lowercase, replace spaces with hyphens, remove special chars
    slug = slug.lower().strip()
    slug = re.sub(r'[^\w\-]', '', slug)
    slug = re.sub(r'[-_]+', '-', slug)  # Replace multiple hyphens/underscores
    return slug


# ==================== SUPER ADMIN SCHEMAS (Platform-Wide) ====================

class SuperAdminBase(BaseModel):
    """Base super admin schema."""
    username: str = Field(..., min_length=3, max_length=50)
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    is_active: bool = Field(default=True)


class SuperAdminCreate(SuperAdminBase):
    """Schema for creating a super admin."""
    password: str = Field(..., min_length=8)


class SuperAdminInDB(SuperAdminBase):
    """Super admin schema as stored in database."""
    id: int
    password_hash: str
    last_login: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True
        arbitrary_types_allowed = True



class SuperAdminLoginRequest(BaseModel):
    """Super admin login request."""
    username: str
    password: str


class SuperAdminLoginResponse(BaseModel):
    """Super admin login response."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int = 86400  # 24 hours
    super_admin: "SuperAdminResponse"


class SuperAdminResponse(BaseModel):
    """Super admin public response."""
    id: int
    username: str
    email: Optional[str] = None
    full_name: Optional[str] = None
    is_active: bool
    last_login: Optional[datetime] = None
    
    class Config:
        from_attributes = True


# ==================== PLATFORM ANALYTICS SCHEMAS ====================

class PlatformStats(BaseModel):
    """Platform-wide statistics for super admin dashboard."""
    total_providers: int
    active_providers: int
    total_customers: int
    total_invoices: int
    total_payments: float
    total_revenue: float
    pending_invoices: int
    overdue_invoices: int
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None


class ProviderPerformance(BaseModel):
    """Performance metrics for a single provider."""
    provider_id: int
    provider_name: str
    provider_slug: str
    total_customers: int
    total_invoices: int
    total_revenue: float
    active_customers: int
    payment_rate: float  # Percentage of invoices paid on time
    last_activity: Optional[datetime] = None


class LoginLog(BaseModel):
    """Login activity log."""
    id: int
    user_type: str  # "super_admin", "provider_admin", "customer"
    user_id: int
    username: str
    provider_id: Optional[int] = None
    provider_slug: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    login_time: datetime = Field(default_factory=datetime.utcnow)
    success: bool
    failure_reason: Optional[str] = None


# ==================== PROVIDER SUBSCRIPTION/BILLING SCHEMAS ====================

class ProviderSubscription(BaseModel):
    """Provider subscription/billing information."""
    id: int
    provider_id: int
    plan: str = Field(default="basic", description="basic, premium, enterprise")
    monthly_fee: float = Field(default=0.0)
    customer_limit: int = Field(default=100)
    features: List[str] = Field(default_factory=list)
    
    # Billing cycle
    billing_cycle_start: Optional[datetime] = None
    next_billing_date: Optional[datetime] = None
    last_payment_date: Optional[datetime] = None
    last_payment_amount: float = 0.0
    payment_status: str = Field(default="active", description="active, overdue, suspended, cancelled")
    
    # M-Pesa / Payment info
    paybill_number: Optional[str] = None
    till_number: Optional[str] = None
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class PaymentRecord(BaseModel):
    """Record of provider subscription payments."""
    id: int
    provider_id: int
    amount: float
    payment_method: str  # mpesa, bank, cash
    transaction_id: Optional[str] = None
    payment_date: datetime = Field(default_factory=datetime.utcnow)
    payment_period_start: Optional[datetime] = None
    payment_period_end: Optional[datetime] = None
    status: str = Field(default="completed")  # completed, pending, failed
    notes: Optional[str] = None
    
    class Config:
        from_attributes = True


# ==================== PROVIDER SCHEMAS ====================

class ProviderBase(BaseModel):
    """Base provider schema with common fields."""
    name: str = Field(..., min_length=2, max_length=100)
    slug: str = Field(..., min_length=2, max_length=50, description="URL-friendly identifier")
    contact_email: Optional[EmailStr] = None
    contact_phone: Optional[str] = None
    address: Optional[str] = None


class ProviderCreate(ProviderBase):
    """Schema for creating a new provider."""
    # Admin user will be created separately
    pass


class ProviderUpdate(BaseModel):
    """Schema for updating provider information."""
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    contact_email: Optional[EmailStr] = None
    contact_phone: Optional[str] = None
    address: Optional[str] = None
    is_active: Optional[bool] = None


class ProviderSettings(BaseModel):
    """Provider-specific settings and configuration."""
    # Rate Configuration
    rate_per_unit: float = Field(default=50.0, ge=0, description="Base rate per water unit")
    rate_mode: str = Field(default="fixed", description="Rate calculation mode: fixed or tiered")
    currency: str = Field(default="KES", description="Currency code")
    
    # Billing Settings
    billing_cycle_days: int = Field(default=30, ge=1, le=365)
    payment_due_days: int = Field(default=15, ge=1, le=90)
    late_payment_penalty_percent: float = Field(default=5.0, ge=0, le=100)
    
    # Reminder Settings
    reminder_days_before_due: int = Field(default=5, ge=0, le=30)
    auto_resend_invoices: bool = Field(default=True)
    max_reminders_per_invoice: int = Field(default=3, ge=0, le=10)
    
    # Notification Settings
    send_sms_notifications: bool = Field(default=True)
    send_email_notifications: bool = Field(default=True)
    twilio_enabled: bool = Field(default=False)
    email_enabled: bool = Field(default=False)
    
    # System Settings
    require_initial_reading: bool = Field(default=True)
    allow_negative_readings: bool = Field(default=False)
    invoice_number_prefix: str = Field(default="INV", description="Prefix for invoice numbers")


class ProviderBranding(BaseModel):
    """Provider-specific branding configuration."""
    logo_url: Optional[str] = None
    primary_color: str = Field(default="#3B82F6", description="Primary brand color (hex)")
    secondary_color: str = Field(default="#1E40AF", description="Secondary brand color (hex)")
    company_name_display: Optional[str] = None
    website_url: Optional[str] = None
    facebook_url: Optional[str] = None
    twitter_url: Optional[str] = None


class ProviderInDB(ProviderBase):
    """Provider schema as stored in database."""
    id: int
    database_name: str = Field(..., description="Full database name for this provider")
    database_suffix: str = Field(..., description="Random suffix for DB name")
    is_active: bool = Field(default=True, description="Whether provider can access system")
    settings: ProviderSettings = Field(default_factory=ProviderSettings)
    branding: ProviderBranding = Field(default_factory=ProviderBranding)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None
    created_by: Optional[str] = None  # Admin who created this provider
    
    class Config:
        from_attributes = True


class ProviderResponse(BaseModel):
    """Public-facing provider response (limited info)."""
    id: int
    name: str
    slug: str
    branding: Optional[ProviderBranding] = None
    
    class Config:
        from_attributes = True


# ==================== PROVIDER ADMIN SCHEMAS ====================

class AdminUserBase(BaseModel):
    """Base provider admin user schema."""
    username: str = Field(..., min_length=3, max_length=50)
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    is_active: bool = Field(default=True)


class AdminUserCreate(AdminUserBase):
    """Schema for creating a provider admin user."""
    password: str = Field(..., min_length=8, description="Admin password")
    provider_id: int = Field(..., description="Provider this admin belongs to")


class AdminUserUpdate(BaseModel):
    """Schema for updating a provider admin user."""
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    is_active: Optional[bool] = None


class AdminUserInDB(AdminUserBase):
    """Provider admin user schema as stored in database."""
    id: int
    provider_id: int
    password_hash: str = Field(..., description="bcrypt hashed password")
    last_login: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class AdminUserResponse(BaseModel):
    """Public-facing provider admin user response."""
    id: int
    username: str
    email: Optional[str] = None
    full_name: Optional[str] = None
    is_active: bool
    last_login: Optional[datetime] = None
    provider_id: int
    provider_name: str
    
    class Config:
        from_attributes = True


class AdminLoginRequest(BaseModel):
    """Provider admin login request schema."""
    username: str
    password: str
    provider_slug: Optional[str] = None  # Optional if using subdomain


class AdminLoginResponse(BaseModel):
    """Provider admin login response schema."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int = 3600  # 1 hour
    admin_user: AdminUserResponse
    provider: ProviderResponse


# ==================== PROVIDER LISTING ====================

class ProviderListResponse(BaseModel):
    """Response for listing providers (super admin only)."""
    providers: list["ProviderDetailResponse"]
    total: int
    page: int
    page_size: int
    
    class Config:
        from_attributes = True


class ProviderDetailResponse(BaseModel):
    """Detailed provider response (for super admin dashboard)."""
    id: int
    name: str
    slug: str
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    address: Optional[str] = None
    is_active: bool
    settings: ProviderSettings
    branding: ProviderBranding
    created_at: datetime
    updated_at: Optional[datetime] = None
    database_name: str
    
    # Subscription info
    subscription: Optional[ProviderSubscription] = None
    
    # Stats
    admin_user_count: int
    customer_count: int
    invoice_count: int
    
    class Config:
        from_attributes = True


# ==================== UTILITY FUNCTIONS ====================

def generate_provider_database_name(slug: str) -> str:
    """Generate full database name for a provider."""
    suffix = generate_db_suffix(8)
    return f"wb_{slug}_{suffix}"


class ModelHelper:
    """Helper class for model operations."""
    
    @staticmethod
    def create_provider_settings(**kwargs) -> ProviderSettings:
        """Create ProviderSettings with defaults."""
        return ProviderSettings(**kwargs)
    
    @staticmethod
    def create_provider_branding(**kwargs) -> ProviderBranding:
        """Create ProviderBranding with defaults."""
        return ProviderBranding(**kwargs)
    
    @staticmethod
    def validate_admin_username(username: str) -> bool:
        """Validate admin username format."""
        return bool(re.match(r'^[a-zA-Z0-9_]+$', username))
    
    @staticmethod
    def validate_provider_slug(slug: str) -> tuple[bool, str]:
        """Validate provider slug and return (is_valid, normalized_slug)."""
        normalized = validate_slug(slug)
        if not normalized:
            return False, ""
        if len(normalized) < 2:
            return False, ""
        if len(normalized) > 50:
            return False, ""
        return True, normalized

