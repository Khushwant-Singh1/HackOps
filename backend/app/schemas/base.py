"""
Base response schemas for API endpoints.

This module provides common response structures used across all API endpoints
to ensure consistent response formatting and error handling.
"""

from typing import Generic, TypeVar, Optional, List, Any, Dict
from datetime import datetime

from pydantic import BaseModel, Field


T = TypeVar('T')


class BaseResponse(BaseModel, Generic[T]):
    """
    Base response model for all API endpoints.
    
    Provides a consistent structure for API responses including
    success status, message, and data payload.
    """
    success: bool = Field(..., description="Whether the operation was successful")
    message: str = Field(..., description="Human-readable message describing the result")
    data: Optional[T] = Field(None, description="Response data payload")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Response timestamp")


class PaginatedResponse(BaseModel, Generic[T]):
    """
    Paginated response model for list endpoints.
    
    Extends BaseResponse with pagination metadata for list operations.
    """
    success: bool = Field(..., description="Whether the operation was successful")
    message: str = Field(..., description="Human-readable message describing the result")
    data: List[T] = Field(..., description="List of response data items")
    total: int = Field(..., description="Total number of items available")
    page: int = Field(..., description="Current page number (1-indexed)")
    page_size: int = Field(..., description="Number of items per page")
    total_pages: int = Field(..., description="Total number of pages")
    has_next: bool = Field(..., description="Whether there are more pages")
    has_prev: bool = Field(..., description="Whether there are previous pages")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Response timestamp")
    
    def __init__(self, **data):
        # Calculate pagination metadata
        if 'total_pages' not in data:
            total = data.get('total', 0)
            page_size = data.get('page_size', 1)
            data['total_pages'] = (total + page_size - 1) // page_size if page_size > 0 else 0
        
        if 'has_next' not in data:
            page = data.get('page', 1)
            total_pages = data.get('total_pages', 0)
            data['has_next'] = page < total_pages
        
        if 'has_prev' not in data:
            page = data.get('page', 1)
            data['has_prev'] = page > 1
        
        super().__init__(**data)


class ErrorResponse(BaseModel):
    """
    Error response model for API error responses.
    
    Provides structured error information including error codes,
    messages, and optional debugging details.
    """
    success: bool = Field(False, description="Always false for error responses")
    error_code: str = Field(..., description="Machine-readable error code")
    message: str = Field(..., description="Human-readable error message")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Error timestamp")


class ValidationErrorResponse(ErrorResponse):
    """
    Validation error response model.
    
    Specialized error response for input validation failures.
    """
    error_code: str = Field("VALIDATION_ERROR", description="Validation error code")
    field_errors: Optional[Dict[str, List[str]]] = Field(None, description="Field-specific validation errors")


class HealthCheckResponse(BaseModel):
    """
    Health check response model.
    
    Used for API health and status endpoints.
    """
    status: str = Field(..., description="Service status (healthy, degraded, unhealthy)")
    version: str = Field(..., description="API version")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Health check timestamp")
    services: Optional[Dict[str, str]] = Field(None, description="Status of dependent services")
    uptime: Optional[str] = Field(None, description="Service uptime")


class BulkOperationResponse(BaseModel):
    """
    Bulk operation response model.
    
    Used for endpoints that perform operations on multiple items.
    """
    success: bool = Field(..., description="Whether the overall operation was successful")
    message: str = Field(..., description="Human-readable message describing the result")
    total_items: int = Field(..., description="Total number of items processed")
    successful_items: int = Field(..., description="Number of items processed successfully")
    failed_items: int = Field(..., description="Number of items that failed processing")
    errors: Optional[List[Dict[str, Any]]] = Field(None, description="Details of any errors that occurred")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Response timestamp")


class AsyncOperationResponse(BaseModel):
    """
    Async operation response model.
    
    Used for endpoints that start long-running background operations.
    """
    success: bool = Field(..., description="Whether the operation was started successfully")
    message: str = Field(..., description="Human-readable message describing the result")
    operation_id: str = Field(..., description="Unique identifier for tracking the operation")
    status: str = Field(..., description="Current operation status")
    estimated_completion: Optional[datetime] = Field(None, description="Estimated completion time")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Response timestamp")


# Utility functions for creating responses

def success_response(
    message: str,
    data: Optional[T] = None,
    **kwargs
) -> BaseResponse[T]:
    """
    Create a success response.
    
    Args:
        message: Success message
        data: Response data
        **kwargs: Additional response fields
    
    Returns:
        BaseResponse instance
    """
    return BaseResponse(
        success=True,
        message=message,
        data=data,
        **kwargs
    )


def error_response(
    message: str,
    error_code: str = "INTERNAL_ERROR",
    details: Optional[Dict[str, Any]] = None,
    **kwargs
) -> ErrorResponse:
    """
    Create an error response.
    
    Args:
        message: Error message
        error_code: Machine-readable error code
        details: Additional error details
        **kwargs: Additional response fields
    
    Returns:
        ErrorResponse instance
    """
    return ErrorResponse(
        error_code=error_code,
        message=message,
        details=details,
        **kwargs
    )


def paginated_response(
    message: str,
    data: List[T],
    total: int,
    page: int,
    page_size: int,
    **kwargs
) -> PaginatedResponse[T]:
    """
    Create a paginated response.
    
    Args:
        message: Success message
        data: List of response data items
        total: Total number of items available
        page: Current page number
        page_size: Number of items per page
        **kwargs: Additional response fields
    
    Returns:
        PaginatedResponse instance
    """
    return PaginatedResponse(
        success=True,
        message=message,
        data=data,
        total=total,
        page=page,
        page_size=page_size,
        **kwargs
    )


def validation_error_response(
    message: str = "Validation failed",
    field_errors: Optional[Dict[str, List[str]]] = None,
    **kwargs
) -> ValidationErrorResponse:
    """
    Create a validation error response.
    
    Args:
        message: Error message
        field_errors: Field-specific validation errors
        **kwargs: Additional response fields
    
    Returns:
        ValidationErrorResponse instance
    """
    return ValidationErrorResponse(
        message=message,
        field_errors=field_errors,
        **kwargs
    )
