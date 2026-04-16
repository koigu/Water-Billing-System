"""
Pydantic schemas for analytics service validation.
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, validator
from enum import Enum


class TrendDirection(str, Enum):
    """Trend direction enumeration."""
    INCREASING = "increasing"
    DECREASING = "decreasing"
    STABLE = "stable"


class CustomerSegment(str, Enum):
    """Customer segment enumeration."""
    HIGH_VALUE = "high_value"
    AT_RISK = "at_risk"
    NEW = "new"
    LOYAL = "loyal"
    CHURNING = "churning"
    AVERAGE = "average"


class PaymentStatus(str, Enum):
    """Payment status enumeration."""
    EARLY = "early"
    ON_TIME = "on_time"
    LATE = "late"


# ==================== Usage Trends Schemas ====================

class UsageTrendBase(BaseModel):
    """Base schema for usage trend data."""
    customer_id: int = Field(..., gt=0, description="Customer ID must be positive")
    month: str = Field(..., min_length=7, max_length=7, description="Month in YYYY-MM format")
    year: int = Field(..., ge=2020, le=2100, description="Year must be between 2020 and 2100")
    total_usage: float = Field(..., ge=0, description="Total usage must be non-negative")
    readings_count: int = Field(..., ge=0, description="Readings count must be non-negative")
    avg_reading: float = Field(..., ge=0, description="Average reading must be non-negative")
    min_reading: float = Field(..., ge=0, description="Minimum reading must be non-negative")
    max_reading: float = Field(..., ge=0, description="Maximum reading must be non-negative")


class UsageTrendCreate(UsageTrendBase):
    """Schema for creating usage trend."""
    pass


class UsageTrendResponse(UsageTrendBase):
    """Schema for usage trend response."""
    id: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    trend_direction: Optional[TrendDirection] = None
    trend_percentage: Optional[float] = None

    class Config:
        from_attributes = True
        allow_population_by_field_name = True


class UsageTrendAnalytics(BaseModel):
    """Schema for usage trend analytics."""
    customer_id: int
    current_usage: float
    previous_usage: float
    usage_change: float
    trend_direction: TrendDirection
    trend_percentage: float
    months_analyzed: int
    avg_monthly_usage: float
    prediction_next_month: Optional[float] = None
    confidence_score: Optional[float] = None


# ==================== Payment Analytics Schemas ====================

class PaymentAnalyticsBase(BaseModel):
    """Base schema for payment analytics."""
    customer_id: int = Field(..., gt=0)
    invoice_id: int = Field(..., gt=0)
    payment_method: str = Field(..., min_length=1)
    payment_date: datetime
    due_date: datetime
    amount: float = Field(..., gt=0)

    @validator('payment_date')
    def validate_payment_date(cls, v, values):
        if 'due_date' in values and v < values['due_date']:
            raise ValueError('payment_date cannot be before due_date')
        return v


class PaymentAnalyticsCreate(PaymentAnalyticsBase):
    """Schema for creating payment analytics."""
    pass


class PaymentAnalyticsResponse(PaymentAnalyticsBase):
    """Schema for payment analytics response."""
    id: Optional[str] = None
    days_to_pay: int
    month: str
    year: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
        allow_population_by_field_name = True


class PaymentMethodAnalysis(BaseModel):
    """Schema for payment method analysis."""
    method: str
    count: int
    percentage: float
    total_amount: float
    avg_days_to_pay: float


class PaymentMethodsResponse(BaseModel):
    """Schema for payment methods analysis response."""
    methods: List[PaymentMethodAnalysis]
    preferred_method: Optional[str] = None
    trend: str = "stable"
    total_payments: int
    total_amount: float


class PaymentTimingAnalysis(BaseModel):
    """Schema for payment timing analysis."""
    year: int
    month: int
    avg_days_to_pay: float
    early_payments: int
    on_time_payments: int
    late_payments: int
    total_payments: int
    on_time_percentage: float
    early_percentage: float
    late_percentage: float
    trend: TrendDirection


# ==================== Customer Behavior Schemas ====================

class CustomerBehaviorBase(BaseModel):
    """Base schema for customer behavior."""
    customer_id: int = Field(..., gt=0)
    total_invoices: int = Field(..., ge=0)
    total_paid: float = Field(..., ge=0)
    avg_payment_days: float = Field(..., ge=0)
    preferred_payment_method: str = Field(..., min_length=1)
    avg_monthly_usage: float = Field(..., ge=0)
    payment_rate: float = Field(..., ge=0, le=100)
    status: str = Field(..., pattern="^(active|inactive)$")


class CustomerBehaviorCreate(CustomerBehaviorBase):
    """Schema for creating customer behavior."""
    pass


class CustomerBehaviorResponse(CustomerBehaviorBase):
    """Schema for customer behavior response."""
    id: Optional[str] = None
    segment: Optional[CustomerSegment] = None
    risk_score: Optional[float] = None
    loyalty_score: Optional[float] = None
    last_activity: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
        allow_population_by_field_name = True


class CustomerProfile(BaseModel):
    """Schema for full customer profile."""
    customer_id: int
    customer_info: Optional[Dict[str, Any]] = None
    behavior: Optional[CustomerBehaviorResponse] = None
    usage_trends: List[UsageTrendResponse] = []
    payment_timing: List[PaymentTimingAnalysis] = []
    segment: CustomerSegment
    risk_score: float
    loyalty_score: float
    recommendations: List[str] = []


class CustomerSegmentStats(BaseModel):
    """Schema for customer segment statistics."""
    segment: CustomerSegment
    count: int
    total_revenue: float
    avg_payment_rate: float
    avg_monthly_usage: float
    percentage_of_total: float


# ==================== Staff Metrics Schemas ====================

class StaffMetricsBase(BaseModel):
    """Base schema for staff metrics."""
    staff_id: str = Field(..., min_length=1)
    month: str = Field(..., min_length=7, max_length=7)
    year: int = Field(..., ge=2020, le=2100)
    invoices_generated: int = Field(..., ge=0)
    payments_collected: float = Field(..., ge=0)
    customers_added: int = Field(..., ge=0)
    readings_recorded: int = Field(..., ge=0)
