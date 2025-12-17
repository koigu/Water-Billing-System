"""
Custom exceptions for analytics service.
"""
from typing import Optional, Any
from datetime import datetime


class AnalyticsException(Exception):
    """Base exception for analytics service."""
    
    def __init__(
        self,
        message: str,
        error_code: str = "ANALYTICS_ERROR",
        details: Optional[dict] = None,
        collection_name: Optional[str] = None,
        operation: Optional[str] = None
    ):
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        self.collection_name = collection_name
        self.operation = operation
        self.timestamp = datetime.utcnow()
        super().__init__(self.message)

    def to_dict(self) -> dict:
        """Convert exception to dictionary for API responses."""
        return {
            "error": True,
            "error_code": self.error_code,
            "message": self.message,
            "details": self.details,
            "collection_name": self.collection_name,
            "operation": self.operation,
            "timestamp": self.timestamp.isoformat()
        }


class DatabaseException(AnalyticsException):
    """Exception raised for database operations."""
    
    def __init__(
        self,
        message: str,
        details: Optional[dict] = None,
        collection_name: Optional[str] = None,
        operation: Optional[str] = None
    ):
        super().__init__(
            message=message,
            error_code="DATABASE_ERROR",
            details=details,
            collection_name=collection_name,
            operation=operation
        )


class ConnectionException(DatabaseException):
    """Exception raised when database connection fails."""
    
    def __init__(
        self,
        message: str = "Database connection failed",
        details: Optional[dict] = None
    ):
        super().__init__(
            message=message,
            details=details,
            operation="connect"
        )


class CollectionNotFoundException(DatabaseException):
    """Exception raised when a collection is not found."""
    
    def __init__(
        self,
        collection_name: str,
        details: Optional[dict] = None
    ):
        super().__init__(
            message=f"Collection '{collection_name}' not found",
            error_code="COLLECTION_NOT_FOUND",
            details=details,
            collection_name=collection_name,
            operation="access"
        )


class DocumentNotFoundException(DatabaseException):
    """Exception raised when a document is not found."""
    
    def __init__(
        self,
        message: str = "Document not found",
        document_id: Optional[Any] = None,
        collection_name: Optional[str] = None,
        details: Optional[dict] = None
    ):
        error_details = details or {}
        if document_id:
            error_details["document_id"] = str(document_id)
        
        super().__init__(
            message=message,
            error_code="DOCUMENT_NOT_FOUND",
            details=error_details,
            collection_name=collection_name,
            operation="find"
        )


class DuplicateDocumentException(DatabaseException):
    """Exception raised when trying to create a duplicate document."""
    
    def __init__(
        self,
        message: str = "Document already exists",
        query: Optional[dict] = None,
        collection_name: Optional[str] = None,
        details: Optional[dict] = None
    ):
        error_details = details or {}
        if query:
            error_details["query"] = str(query)
        
        super().__init__(
            message=message,
            error_code="DUPLICATE_DOCUMENT",
            details=error_details,
            collection_name=collection_name,
            operation="insert"
        )


class ValidationException(AnalyticsException):
    """Exception raised for validation errors."""
    
    def __init__(
        self,
        message: str,
        field_name: Optional[str] = None,
        field_value: Optional[Any] = None,
        constraints: Optional[dict] = None,
        details: Optional[dict] = None
    ):
        error_details = details or {}
        if field_name:
            error_details["field_name"] = field_name
        if field_value is not None:
            error_details["field_value"] = str(field_value)
        if constraints:
            error_details["constraints"] = constraints
        
        super().__init__(
            message=message,
            error_code="VALIDATION_ERROR",
            details=error_details,
            operation="validate"
        )


class InvalidParameterException(ValidationException):
    """Exception raised for invalid parameters."""
    
    def __init__(
        self,
        param_name: str,
        param_value: Any,
        expected_type: Optional[str] = None,
        details: Optional[dict] = None
    ):
        error_details = details or {}
        error_details["parameter_name"] = param_name
        error_details["parameter_value"] = str(param_value)
        if expected_type:
            error_details["expected_type"] = expected_type
        
        message = f"Invalid parameter '{param_name}': {param_value}"
        if expected_type:
            message += f" (expected {expected_type})"
        
        super().__init__(
            message=message,
            field_name=param_name,
            field_value=param_value,
            constraints={"expected_type": expected_type} if expected_type else None,
            details=error_details
        )


class DateRangeException(ValidationException):
    """Exception raised for invalid date range."""
    
    def __init__(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        details: Optional[dict] = None
    ):
        error_details = details or {}
        if start_date:
            error_details["start_date"] = start_date.isoformat()
        if end_date:
            error_details["end_date"] = end_date.isoformat()
        
        message = "Invalid date range"
        if start_date and end_date and end_date < start_date:
            message = "end_date cannot be before start_date"
        
        super().__init__(
            message=message,
            field_name="date_range",
            field_value={"start": start_date, "end": end_date},
            constraints={"start_date": "must be before end_date"},
            details=error_details
        )


class AggregationException(AnalyticsException):
    """Exception raised for aggregation pipeline errors."""
    
    def __init__(
        self,
        message: str,
        pipeline: Optional[list] = None,
        collection_name: Optional[str] = None,
        details: Optional[dict] = None
    ):
        error_details = details or {}
        if pipeline:
            error_details["pipeline"] = str(pipeline)
        
        super().__init__(
            message=message,
            error_code="AGGREGATION_ERROR",
            details=error_details,
            collection_name=collection_name,
            operation="aggregate"
        )


class CacheException(AnalyticsException):
    """Exception raised for cache operations."""
    
    def __init__(
        self,
        message: str,
        cache_key: Optional[str] = None,
        details: Optional[dict] = None
    ):
        error_details = details or {}
        if cache_key:
            error_details["cache_key"] = cache_key
        
        super().__init__(
            message=message,
            error_code="CACHE_ERROR",
            details=error_details,
            operation="cache"
        )


class CacheMissException(CacheException):
    """Exception raised when cache key is not found."""
    
    def __init__(
        self,
        cache_key: str,
        details: Optional[dict] = None
    ):
        super().__init__(
            message=f"Cache miss for key: {cache_key}",
            cache_key=cache_key,
            details=details
        )


class ForecastException(AnalyticsException):
    """Exception raised for forecasting errors."""
    
    def __init__(
        self,
        message: str,
        forecast_type: Optional[str] = None,
        details: Optional[dict] = None
    ):
        error_details = details or {}
        if forecast_type:
            error_details["forecast_type"] = forecast_type
        
        super().__init__(
            message=message,
            error_code="FORECAST_ERROR",
            details=error_details,
            operation="forecast"
        )


class InsufficientDataException(ForecastException):
    """Exception raised when there's not enough data for forecasting."""
    
    def __init__(
        self,
        required_data_points: int,
        available_data_points: int,
        forecast_type: str = "general",
        details: Optional[dict] = None
    ):
        error_details = details or {}
        error_details["required_data_points"] = required_data_points
        error_details["available_data_points"] = available_data_points
        
        message = (
            f"Insufficient data for {forecast_type} forecast. "
            f"Required: {required_data_points}, Available: {available_data_points}"
        )
        
        super().__init__(
            message=message,
            forecast_type=forecast_type,
            details=error_details
        )


class SegmentException(AnalyticsException):
    """Exception raised for customer segmentation errors."""
    
    def __init__(
        self,
        message: str,
        segment_name: Optional[str] = None,
        details: Optional[dict] = None
    ):
        error_details = details or {}
        if segment_name:
            error_details["segment_name"] = segment_name
        
        super().__init__(
            message=message,
            error_code="SEGMENT_ERROR",
            details=error_details,
            operation="segment"
        )


class InvalidSegmentException(SegmentException):
    """Exception raised when an invalid segment is specified."""
    
    def __init__(
        self,
        segment_name: str,
        valid_segments: list,
        details: Optional[dict] = None
    ):
        error_details = details or {}
        error_details["segment_name"] = segment_name
        error_details["valid_segments"] = valid_segments
        
        message = (
            f"Invalid segment '{segment_name}'. "
            f"Valid segments: {', '.join(valid_segments)}"
        )
        
        super().__init__(
            message=message,
            segment_name=segment_name,
            details=error_details
        )


class DataQualityException(AnalyticsException):
    """Exception raised for data quality issues."""
    
    def __init__(
        self,
        message: str,
        collection_name: str,
        quality_metric: Optional[str] = None,
        current_value: Optional[float] = None,
        threshold: Optional[float] = None,
        details: Optional[dict] = None
    ):
        error_details = details or {}
        if collection_name:
            error_details["collection_name"] = collection_name
        if quality_metric:
            error_details["quality_metric"] = quality_metric
        if current_value is not None:
            error_details["current_value"] = current_value
        if threshold is not None:
            error_details["threshold"] = threshold
        
        super().__init__(
            message=message,
            error_code="DATA_QUALITY_ERROR",
            details=error_details,
            collection_name=collection_name,
            operation="quality_check"
        )


class RateLimitException(AnalyticsException):
    """Exception raised when rate limit is exceeded."""
    
    def __init__(
        self,
        message: str = "Rate limit exceeded",
        limit: Optional[int] = None,
        window: Optional[int] = None,
        details: Optional[dict] = None
    ):
        error_details = details or {}
        if limit:
            error_details["limit"] = limit
        if window:
            error_details["window_seconds"] = window
        
        super().__init__(
            message=message,
            error_code="RATE_LIMIT_EXCEEDED",
            details=error_details,
            operation="rate_limit"
        )


def handle_exception(func):
    """Decorator to handle exceptions in analytics service methods."""
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except AnalyticsException:
            raise
        except Exception as e:
            raise AnalyticsException(
                message=str(e),
                error_code="UNEXPECTED_ERROR",
                details={"exception_type": type(e).__name__}
            )
    return wrapper

