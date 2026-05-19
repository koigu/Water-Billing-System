"""
Pydantic schemas for Water Billing System.
MongoDB-compatible schemas (removed SQLAlchemy orm_mode).
"""
from typing import Optional, List, Any, Dict
from pydantic import BaseModel, EmailStr
from datetime import datetime


class CustomerBase(BaseModel):
    name: str
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    location: Optional[str] = None


class CustomerCreate(CustomerBase):
    initial_reading: Optional[float] = None


class Customer(CustomerBase):
    id: int
    created_at: datetime
    # Make all fields optional to handle MongoDB documents
    class Config:
        populate_by_name = True


class CustomerWithReadings(Customer):
    readings: List["MeterReading"] = []
    class Config:
        populate_by_name = True


class MeterReadingCreate(BaseModel):
    reading_value: Optional[float] = None


class MeterReading(BaseModel):
    id: int
    customer_id: int
    reading_value: Optional[float] = None
    status: str = "recorded"
    recorded_at: datetime
    class Config:
        populate_by_name = True


class InvoiceCreate(BaseModel):
    customer_id: int
    amount: float
    due_date: datetime
    location: Optional[str] = None


class Invoice(BaseModel):
    id: int
    customer_id: int
    amount: float
    billing_from: Optional[datetime] = None
    billing_to: Optional[datetime] = None
    due_date: datetime
    sent_at: Optional[datetime] = None
    status: str = "pending"
    location: Optional[str] = None
    reminder_sent_at: Optional[datetime] = None
    class Config:
        populate_by_name = True


class RateConfigBase(BaseModel):
    mode: str
    value: float


class RateConfig(RateConfigBase):
    id: Optional[int] = None
    updated_at: Optional[datetime] = None
    class Config:
        populate_by_name = True


class RateChangeAudit(BaseModel):
    id: int
    username: str
    mode: str
    value: float
    changed_at: datetime
    class Config:
        populate_by_name = True


# Customer Authentication Schemas
class CustomerAuthBase(BaseModel):
    username: str
    is_active: int = 1


class CustomerAuthCreate(CustomerAuthBase):
    password: str


class CustomerAuth(CustomerAuthBase):
    id: Optional[int] = None
    customer_id: int
    created_at: Optional[datetime] = None
    last_login: Optional[datetime] = None
    class Config:
        populate_by_name = True


class CustomerLogin(BaseModel):
    username: str
    password: str


class LoginCredentials(BaseModel):
    username: str
    password: str


# Payment Schemas
class PaymentBase(BaseModel):
    amount: float
    payment_method: str
    transaction_id: Optional[str] = None
    status: str = "completed"
    notes: Optional[str] = None


class PaymentCreate(PaymentBase):
    invoice_id: int
    customer_id: Optional[int] = None


class Payment(PaymentBase):
    id: Optional[int] = None
    invoice_id: int
    customer_id: Optional[int] = None
    payment_date: Optional[datetime] = None
    class Config:
        populate_by_name = True


# Usage Alert Schemas
class UsageAlertBase(BaseModel):
    alert_type: str
    message: str
    threshold_value: Optional[float] = None
    actual_value: Optional[float] = None


class UsageAlertCreate(UsageAlertBase):
    customer_id: int


class UsageAlert(UsageAlertBase):
    id: Optional[int] = None
    customer_id: int
    created_at: Optional[datetime] = None
    is_read: int = 0
    resolved_at: Optional[datetime] = None
    class Config:
        populate_by_name = True


# Analytics Schemas
class UsageData(BaseModel):
    date: str
    usage: float
    reading: float


class BenchmarkData(BaseModel):
    customer_average: Optional[float] = None
    location_average: Optional[float] = None
    percentile: Optional[float] = None
    comparison: Optional[str] = None


class CustomerPortalData(BaseModel):
    customer: Dict[str, Any]
    recent_invoices: List[Dict[str, Any]]
    usage_history: List[Dict[str, Any]]
    benchmark: Optional[Dict[str, Any]]
    alerts: List[Dict[str, Any]]
    total_due: float


class PaymentMethodStats(BaseModel):
    method: str
    count: int
    percentage: float
    total_amount: float
    avg_days_to_pay: float


class PaymentAnalytics(BaseModel):
    methods: List[PaymentMethodStats]
    preferred_method: Optional[str] = None
    trend: str = "stable"
    total_payments: int = 0
    total_amount: float = 0.0


class UsageTrend(BaseModel):
    month: Optional[str] = None
    year: Optional[int] = None
    total_usage: float = 0.0
    customer_count: int = 0
    avg_usage_per_customer: float = 0.0


class StaffMetrics(BaseModel):
    staff_id: str
    total_invoices: int = 0
    total_payments: float = 0.0
    total_customers: int = 0
    total_readings: int = 0
    avg_efficiency: float = 0.0
    months_active: int = 0


class ReminderConfig(BaseModel):
    reminder_days: int = 5
    auto_resend_invoice: bool = True
    max_reminders: int = 3
    updated_by: Optional[str] = None
    updated_at: Optional[datetime] = None


# Update forward references
CustomerWithReadings.update_forward_refs()

