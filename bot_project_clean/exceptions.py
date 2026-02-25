"""
Custom exception classes for the bot project.
"""

from fastapi import HTTPException, status


class BookingConflictError(HTTPException):
    """Raised when a booking conflicts with an existing one."""
    def __init__(self, detail: str = "Booking conflict - this time slot is already taken"):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail=detail
        )


class NotFoundError(HTTPException):
    """Raised when a resource is not found."""
    def __init__(self, resource: str = "Resource"):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{resource} not found"
        )


class ValidationError(HTTPException):
    """Raised when input validation fails."""
    def __init__(self, detail: str = "Invalid input"):
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=detail
        )


class AuthenticationError(HTTPException):
    """Raised when authentication fails."""
    def __init__(self, detail: str = "Authentication failed"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"}
        )


class PermissionDeniedError(HTTPException):
    """Raised when user doesn't have permission."""
    def __init__(self, detail: str = "Access denied"):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail
        )


class DatabaseError(HTTPException):
    """Raised when a database error occurs."""
    def __init__(self, detail: str = "Database error"):
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=detail
        )


class ServiceUnavailableError(HTTPException):
    """Raised when an external service is unavailable."""
    def __init__(self, service: str = "Service"):
        super().__init__(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"{service} is temporarily unavailable"
        )
