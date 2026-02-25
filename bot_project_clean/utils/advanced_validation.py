"""
Enterprise-grade validation and serialization system.
Provides advanced validation, custom validators, and detailed error reporting.
"""

import re
import phonenumbers
from typing import Any, Dict, List, Optional, Union, Type, Callable
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, date, time
from pydantic import BaseModel, validator, Field, ValidationError, EmailStr
from pydantic.types import constr
from pydantic_core import ValidationError as CoreValidationError
import json

from utils.logging import get_logger

logger = get_logger(__name__)

class ValidationSeverity(Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

@dataclass
class ValidationError:
    """Detailed validation error with context."""
    field: str
    message: str
    severity: ValidationSeverity = ValidationSeverity.ERROR
    code: Optional[str] = None
    value: Any = None
    context: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "field": self.field,
            "message": self.message,
            "severity": self.severity.value,
            "code": self.code,
            "value": self.value,
            "context": self.context
        }

class ValidationResult:
    """Validation result with errors and warnings."""
    
    def __init__(self):
        self.errors: List[ValidationError] = []
        self.warnings: List[ValidationError] = []
        self.is_valid: bool = True
    
    def add_error(self, error: ValidationError) -> None:
        """Add validation error."""
        if error.severity == ValidationSeverity.ERROR or error.severity == ValidationSeverity.CRITICAL:
            self.errors.append(error)
            self.is_valid = False
        elif error.severity == ValidationSeverity.WARNING:
            self.warnings.append(error)
    
    def add_errors(self, errors: List[ValidationError]) -> None:
        """Add multiple validation errors."""
        for error in errors:
            self.add_error(error)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_valid": self.is_valid,
            "errors": [error.to_dict() for error in self.errors],
            "warnings": [warning.to_dict() for warning in self.warnings],
            "error_count": len(self.errors),
            "warning_count": len(self.warnings)
        }

class CustomValidator:
    """Base class for custom validators."""
    
    def __init__(self, message: Optional[str] = None, code: Optional[str] = None):
        self.message = message
        self.code = code
    
    def validate(self, value: Any, field_name: str, context: Dict[str, Any] = None) -> List[ValidationError]:
        """Validate value and return list of validation errors."""
        raise NotImplementedError
    
    def __call__(self, value: Any, field_name: str, context: Dict[str, Any] = None) -> List[ValidationError]:
        return self.validate(value, field_name, context)

class UzbekPhoneValidator(CustomValidator):
    """Validator for Uzbekistan phone numbers."""
    
    def __init__(self, message: Optional[str] = None):
        super().__init__(
            message or "Invalid Uzbekistan phone number. Format: +998 XX XXX XX XX",
            code="invalid_uzbek_phone"
        )
    
    def validate(self, value: Any, field_name: str, context: Dict[str, Any] = None) -> List[ValidationError]:
        errors = []
        
        if not isinstance(value, str):
            errors.append(ValidationError(
                field=field_name,
                message="Phone number must be a string",
                code="invalid_type",
                value=value
            ))
            return errors
        
        try:
            # Parse phone number
            phone_obj = phonenumbers.parse(value, None)
            
            # Check if it's a valid Uzbekistan number
            if not phonenumbers.is_valid_number(phone_obj):
                errors.append(ValidationError(
                    field=field_name,
                    message=self.message,
                    code=self.code,
                    value=value
                ))
            elif phonenumbers.region_code_for_number(phone_obj) != "UZ":
                errors.append(ValidationError(
                    field=field_name,
                    message="Phone number must be from Uzbekistan",
                    code="invalid_region",
                    value=value
                ))
        
        except phonenumbers.NumberParseException as e:
            errors.append(ValidationError(
                field=field_name,
                message=f"Phone number parsing error: {str(e)}",
                code="parse_error",
                value=value
            ))
        
        return errors

class PasswordStrengthValidator(CustomValidator):
    """Validator for strong passwords."""
    
    def __init__(self, min_length: int = 8, require_special: bool = True, 
                 require_numbers: bool = True, require_uppercase: bool = True):
        super().__init__(
            message=f"Password must be at least {min_length} characters long and contain "
                   f"{'special characters, ' if require_special else ''}"
                   f"{'numbers, ' if require_numbers else ''}"
                   f"{'uppercase letters' if require_uppercase else ''}",
            code="weak_password"
        )
        self.min_length = min_length
        self.require_special = require_special
        self.require_numbers = require_numbers
        self.require_uppercase = require_uppercase
    
    def validate(self, value: Any, field_name: str, context: Dict[str, Any] = None) -> List[ValidationError]:
        errors = []
        
        if not isinstance(value, str):
            errors.append(ValidationError(
                field=field_name,
                message="Password must be a string",
                code="invalid_type",
                value=value
            ))
            return errors
        
        # Length check
        if len(value) < self.min_length:
            errors.append(ValidationError(
                field=field_name,
                message=f"Password must be at least {self.min_length} characters long",
                code="too_short",
                value=value,
                context={"min_length": self.min_length}
            ))
        
        # Special characters check
        if self.require_special and not re.search(r'[!@#$%^&*(),.?":{}|<>]', value):
            errors.append(ValidationError(
                field=field_name,
                message="Password must contain special characters",
                code="missing_special",
                value=value
            ))
        
        # Numbers check
        if self.require_numbers and not re.search(r'\d', value):
            errors.append(ValidationError(
                field=field_name,
                message="Password must contain numbers",
                code="missing_numbers",
                value=value
            ))
        
        # Uppercase check
        if self.require_uppercase and not re.search(r'[A-Z]', value):
            errors.append(ValidationError(
                field=field_name,
                message="Password must contain uppercase letters",
                code="missing_uppercase",
                value=value
            ))
        
        return errors

class BusinessHoursValidator(CustomValidator):
    """Validator for business hours."""
    
    def __init__(self, opening_hour: int = 9, closing_hour: int = 22):
        super().__init__(
            message=f"Time must be between {opening_hour}:00 and {closing_hour}:00",
            code="outside_business_hours"
        )
        self.opening_hour = opening_hour
        self.closing_hour = closing_hour
    
    def validate(self, value: Any, field_name: str, context: Dict[str, Any] = None) -> List[ValidationError]:
        errors = []
        
        if isinstance(value, datetime):
            hour = value.hour
        elif isinstance(value, time):
            hour = value.hour
        elif isinstance(value, str):
            try:
                hour = datetime.strptime(value, "%H:%M").hour
            except ValueError:
                errors.append(ValidationError(
                    field=field_name,
                    message="Invalid time format. Use HH:MM",
                    code="invalid_time_format",
                    value=value
                ))
                return errors
        else:
            errors.append(ValidationError(
                field=field_name,
                message="Time must be datetime, time, or string",
                code="invalid_type",
                value=value
            ))
            return errors
        
        if hour < self.opening_hour or hour >= self.closing_hour:
            errors.append(ValidationError(
                field=field_name,
                message=self.message,
                code=self.code,
                value=value,
                context={"opening_hour": self.opening_hour, "closing_hour": self.closing_hour}
            ))
        
        return errors

class AdvancedValidator:
    """Enterprise validation engine with custom validators."""
    
    def __init__(self):
        self._validators: Dict[str, List[CustomValidator]] = {}
        self._global_validators: List[CustomValidator] = []
    
    def add_validator(self, field_name: str, validator: CustomValidator) -> None:
        """Add validator for specific field."""
        if field_name not in self._validators:
            self._validators[field_name] = []
        self._validators[field_name].append(validator)
        logger.info(f"Added validator for field {field_name}: {validator.__class__.__name__}")
    
    def add_global_validator(self, validator: CustomValidator) -> None:
        """Add global validator for all fields."""
        self._global_validators.append(validator)
        logger.info(f"Added global validator: {validator.__class__.__name__}")
    
    def validate(self, data: Dict[str, Any], model_class: Optional[Type[BaseModel]] = None) -> ValidationResult:
        """Validate data with all registered validators."""
        result = ValidationResult()
        
        # Pydantic validation if model class provided
        if model_class:
            try:
                model_class(**data)
            except ValidationError as e:
                for error in e.errors():
                    field = ".".join(str(loc) for loc in error["loc"])
                    result.add_error(ValidationError(
                        field=field,
                        message=error["msg"],
                        code=error["type"],
                        value=error.get("input")
                    ))
        
        # Custom validators
        for field_name, value in data.items():
            # Field-specific validators
            if field_name in self._validators:
                for validator in self._validators[field_name]:
                    errors = validator.validate(value, field_name, data)
                    result.add_errors(errors)
            
            # Global validators
            for validator in self._global_validators:
                errors = validator.validate(value, field_name, data)
                result.add_errors(errors)
        
        return result

# Enhanced Pydantic models with advanced validation
class UserCreateSchema(BaseModel):
    """Enhanced user creation schema with advanced validation."""
    
    username: constr(min_length=3, max_length=50)
    email: EmailStr
    phone: str
    full_name: constr(min_length=2, max_length=100)
    password: str
    
    @validator('username')
    def validate_username(cls, v):
        if not re.match(r'^[a-zA-Z0-9_]+$', v):
            raise ValueError('Username must contain only letters, numbers, and underscores')
        return v
    
    @validator('phone')
    def validate_phone(cls, v):
        validator = UzbekPhoneValidator()
        errors = validator.validate(v, 'phone')
        if errors:
            raise ValueError(errors[0].message)
        return v
    
    @validator('password')
    def validate_password(cls, v):
        validator = PasswordStrengthValidator()
        errors = validator.validate(v, 'password')
        if errors:
            raise ValueError(errors[0].message)
        return v

class BookingCreateSchema(BaseModel):
    """Enhanced booking creation schema with business validation."""
    
    user_id: int
    club_id: int
    computer_id: str
    start_time: datetime
    duration_minutes: int = Field(..., ge=30, le=480)  # 30min to 8hours
    
    @validator('start_time')
    def validate_business_hours(cls, v):
        validator = BusinessHoursValidator()
        errors = validator.validate(v, 'start_time')
        if errors:
            raise ValueError(errors[0].message)
        return v
    
    @validator('duration_minutes')
    def validate_duration_rounding(cls, v):
        """Ensure duration is rounded to 30-minute intervals."""
        if v % 30 != 0:
            raise ValueError("Duration must be in 30-minute intervals")
        return v

class ClubCreateSchema(BaseModel):
    """Enhanced club creation schema with geo-validation."""
    
    name: constr(min_length=2, max_length=100)
    city: constr(min_length=2, max_length=50)
    address: constr(min_length=5, max_length=200)
    latitude: Optional[float] = Field(None, ge=-90, le=90)
    longitude: Optional[float] = Field(None, ge=-180, le=180)
    driver_type: str
    connection_config: Dict[str, Any] = Field(default_factory=dict)
    
    def validate_coordinates(self):
        """Validate coordinates after model creation."""
        if self.latitude is not None:
            if not (37.0 <= self.latitude <= 45.5):
                raise ValueError("Latitude must be within Uzbekistan bounds")
        
        if self.longitude is not None:
            if not (55.9 <= self.longitude <= 73.1):
                raise ValueError("Longitude must be within Uzbekistan bounds")
    
    def validate_driver_config(self):
        """Validate driver configuration."""
        if self.driver_type == 'ICAFE':
            required_fields = ['token', 'cafe_id']
            for field in required_fields:
                if field not in self.connection_config:
                    raise ValueError(f"ICAFE driver requires '{field}' in connection_config")
        
        elif self.driver_type == 'SMARTSHELL':
            required_fields = ['api_url', 'api_key']
            for field in required_fields:
                if field not in self.connection_config:
                    raise ValueError(f"SMARTSHELL driver requires '{field}' in connection_config")

# Global validator instance
advanced_validator = AdvancedValidator()

# Add default validators
advanced_validator.add_validator('phone', UzbekPhoneValidator())
advanced_validator.add_validator('password', PasswordStrengthValidator())
advanced_validator.add_validator('start_time', BusinessHoursValidator())
