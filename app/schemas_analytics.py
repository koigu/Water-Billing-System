"""
Pydantic schemas for analytics service validation.
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, validator, ConfigDict
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

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


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

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


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

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


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


class StaffMetricsCreate(StaffMetricsBase):
    """Schema for creating staff metrics."""
    pass


class StaffMetricsResponse(StaffMetricsBase):
    """Schema for staff metrics response."""
    id: Optional[str] = None
    efficiency_score: float
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class StaffTrend(BaseModel):
    """Schema for staff performance trend."""
    staff_id: str
    period: str
    efficiency_score: float
    invoices_generated: int
    payments_collected: float
    customers_added: int
    readings_recorded: int
    trend_direction: TrendDirection


class TopPerformingStaff(BaseModel):
    """Schema for top performing staff."""
    staff_id: str
    total_invoices: int
    total_payments: float
    total_customers: int
    total_readings: int
    avg_efficiency: float
    months_active: int
    rank: int


# ==================== Reminder Config Schemas ====================

class ReminderConfigBase(BaseModel):
    """Base schema for reminder configuration."""
    reminder_days: int = Field(..., ge=0, le=30)
    auto_resend_invoice: bool = True
    max_reminders: int = Field(..., ge=1, le=10)


class ReminderConfigCreate(ReminderConfigBase):
    """Schema for creating reminder config."""
    updated_by: str = Field(..., min_length=1)


class ReminderConfigResponse(ReminderConfigBase):
    """Schema for reminder config response."""
    updated_by: Optional[str] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


# ==================== Revenue Analytics Schemas ====================

class RevenueAnalytics(BaseModel):
    """Schema for revenue analytics."""
    month: str
    year: int
    total_revenue: float
    invoice_count: int
    paid_amount: float
    pending_amount: float
    overdue_amount: float
    collection_rate: float
    avg_invoice_value: float
    revenue_trend: TrendDirection
    revenue_change_percentage: float


class RevenueForecast(BaseModel):
    """Schema for revenue forecast."""
    predicted_month: str
    predicted_revenue: float
    confidence_low: float
    confidence_high: float
    confidence_score: float
    factors: List[str] = []


class RevenueSummary(BaseModel):
    """Schema for revenue summary."""
    current_month: str
    current_month_revenue: float
    previous_month_revenue: float
    month_over_month_change: float
    year_to_date_revenue: float
    projected_monthly_revenue: float
    forecast: List[RevenueForecast] = []


# ==================== Data Quality Schemas ====================

class DataQualityMetric(BaseModel):
    """Schema for data quality metric."""
    collection_name: str
    metric_name: str
    value: float
    status: str  # "good", "warning", "critical"
    threshold: float
    description: str


class DataQualityReport(BaseModel):
    """Schema for data quality report."""
    generated_at: datetime
    overall_score: float
    metrics: List[DataQualityMetric]
    issues: List[str] = []
    recommendations: List[str] = []


class CollectionStats(BaseModel):
    """Schema for collection statistics."""
    collection_name: str
    document_count: int
    index_count: int
    size_bytes: float
    last_updated: Optional[datetime] = None


# ==================== Dashboard Analytics Schemas ====================

class DashboardAnalytics(BaseModel):
    """Schema for dashboard analytics overview."""
    total_customers: int
    active_customers: int
    inactive_customers: int
    total_revenue: float
    revenue_this_month: float
    revenue_last_month: float
    avg_payment_days: float
    collection_rate: float
    top_payment_methods: List[PaymentMethodAnalysis] = []
    customer_segments: List[CustomerSegmentStats] = []
    data_quality_score: float


class TrendSummary(BaseModel):
    """Schema for trend summary."""
    metric_name: str
    current_value: float
    previous_value: float
    change: float
    change_percentage: float
    trend: TrendDirection
    prediction: Optional[float] = None


# ==================== Pagination Schemas ====================

class PaginationParams(BaseModel):
    """Schema for pagination parameters."""
    skip: int = Field(default=0, ge=0)
    limit: int = Field(default=100, ge=1, le=1000)


class PaginatedResponse(BaseModel):
    """Schema for paginated response."""
    data: List[Any]
    total: int
    skip: int
    limit: int
    has_more: bool


# ==================== Date Range Schemas ====================

class DateRangeParams(BaseModel):
    """Schema for date range parameters."""
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None

    @validator('end_date')
    def validate_end_date(cls, v, values):
        if v and 'start_date' in values and values['start_date'] and v < values['start_date']:
            raise ValueError('end_date cannot be before start_date')
        return v

