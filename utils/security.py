"""
Enterprise security module with advanced authentication, authorization, and protection.
"""

import hashlib
import hmac
import secrets
import time
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
import jwt
from cryptography.fernet import Fernet
from passlib.context import CryptContext
import ipaddress
from functools import wraps
from fastapi import HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from utils.logging import get_logger
from utils.monitoring import metrics_collector

logger = get_logger(__name__)

class SecurityConfig:
    """Security configuration settings."""
    
    # JWT Settings
    JWT_SECRET_KEY: str = secrets.token_urlsafe(32)
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # Password Settings
    PASSWORD_CONTEXT = CryptContext(schemes=["bcrypt"], deprecated="auto")
    
    # Rate Limiting
    RATE_LIMIT_REQUESTS: int = 100
    RATE_LIMIT_WINDOW: int = 3600  # 1 hour
    
    # IP Settings
    ALLOWED_IP_RANGES: List[str] = []  # Empty means allow all
    BLOCKED_IPS: List[str] = []
    
    # Encryption
    ENCRYPTION_KEY: bytes = Fernet.generate_key()

@dataclass
class SecurityContext:
    """Security context for request processing."""
    user_id: Optional[int] = None
    permissions: List[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    request_id: Optional[str] = None
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.permissions is None:
            self.permissions = []
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()

class TokenManager:
    """Enterprise JWT token management."""
    
    def __init__(self, config: SecurityConfig):
        self.config = config
        self._blacklisted_tokens: Dict[str, datetime] = {}
    
    def create_access_token(self, data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
        """Create JWT access token."""
        to_encode = data.copy()
        
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=self.config.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
        
        to_encode.update({
            "exp": expire,
            "iat": datetime.utcnow(),
            "type": "access",
            "jti": secrets.token_urlsafe(16)  # JWT ID for blacklisting
        })
        
        encoded_jwt = jwt.encode(to_encode, self.config.JWT_SECRET_KEY, algorithm=self.config.JWT_ALGORITHM)
        
        # Log token creation
        logger.info(f"Created access token for user {data.get('sub')}")
        metrics_collector.increment_counter("security.tokens.created", tags={"type": "access"})
        
        return encoded_jwt
    
    def create_refresh_token(self, data: Dict[str, Any]) -> str:
        """Create JWT refresh token."""
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(days=self.config.JWT_REFRESH_TOKEN_EXPIRE_DAYS)
        
        to_encode.update({
            "exp": expire,
            "iat": datetime.utcnow(),
            "type": "refresh",
            "jti": secrets.token_urlsafe(16)
        })
        
        encoded_jwt = jwt.encode(to_encode, self.config.JWT_SECRET_KEY, algorithm=self.config.JWT_ALGORITHM)
        
        logger.info(f"Created refresh token for user {data.get('sub')}")
        metrics_collector.increment_counter("security.tokens.created", tags={"type": "refresh"})
        
        return encoded_jwt
    
    def verify_token(self, token: str, token_type: str = "access") -> Optional[Dict[str, Any]]:
        """Verify JWT token and return payload."""
        try:
            payload = jwt.decode(token, self.config.JWT_SECRET_KEY, algorithms=[self.config.JWT_ALGORITHM])
            
            # Check token type
            if payload.get("type") != token_type:
                logger.warning(f"Invalid token type: expected {token_type}, got {payload.get('type')}")
                return None
            
            # Check if token is blacklisted
            jti = payload.get("jti")
            if jti and jti in self._blacklisted_tokens:
                logger.warning(f"Token is blacklisted: {jti}")
                return None
            
            # Check expiration
            exp = payload.get("exp")
            if exp and datetime.utcfromtimestamp(exp) < datetime.utcnow():
                logger.warning("Token has expired")
                return None
            
            return payload
        
        except jwt.ExpiredSignatureError:
            logger.warning("Token signature expired")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid token: {e}")
            return None
    
    def blacklist_token(self, token: str) -> bool:
        """Add token to blacklist."""
        try:
            payload = jwt.decode(token, self.config.JWT_SECRET_KEY, algorithms=[self.config.JWT_ALGORITHM])
            jti = payload.get("jti")
            exp = payload.get("exp")
            
            if jti and exp:
                self._blacklisted_tokens[jti] = datetime.utcfromtimestamp(exp)
                logger.info(f"Blacklisted token: {jti}")
                metrics_collector.increment_counter("security.tokens.blacklisted")
                return True
        
        except jwt.InvalidTokenError as e:
            logger.error(f"Error blacklisting token: {e}")
        
        return False
    
    def cleanup_expired_tokens(self) -> None:
        """Remove expired tokens from blacklist."""
        now = datetime.utcnow()
        expired_tokens = [
            jti for jti, exp_time in self._blacklisted_tokens.items()
            if exp_time < now
        ]
        
        for jti in expired_tokens:
            del self._blacklisted_tokens[jti]
        
        if expired_tokens:
            logger.info(f"Cleaned up {len(expired_tokens)} expired blacklisted tokens")

class PasswordManager:
    """Enterprise password management."""
    
    def __init__(self, config: SecurityConfig):
        self.config = config
    
    def hash_password(self, password: str) -> str:
        """Hash password with bcrypt."""
        hashed = self.config.PASSWORD_CONTEXT.hash(password)
        logger.info("Password hashed successfully")
        return hashed
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify password against hash."""
        try:
            result = self.config.PASSWORD_CONTEXT.verify(plain_password, hashed_password)
            if result:
                logger.info("Password verification successful")
            else:
                logger.warning("Password verification failed")
            return result
        except Exception as e:
            logger.error(f"Password verification error: {e}")
            return False
    
    def generate_secure_password(self, length: int = 12) -> str:
        """Generate secure random password."""
        alphabet = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*"
        password = ''.join(secrets.choice(alphabet) for _ in range(length))
        logger.info("Generated secure password")
        return password

class EncryptionManager:
    """Enterprise data encryption/decryption."""
    
    def __init__(self, config: SecurityConfig):
        self.config = config
        self.cipher = Fernet(config.ENCRYPTION_KEY)
    
    def encrypt(self, data: str) -> str:
        """Encrypt sensitive data."""
        try:
            encrypted_data = self.cipher.encrypt(data.encode())
            logger.debug("Data encrypted successfully")
            return encrypted_data.decode()
        except Exception as e:
            logger.error(f"Encryption error: {e}")
            raise
    
    def decrypt(self, encrypted_data: str) -> str:
        """Decrypt sensitive data."""
        try:
            decrypted_data = self.cipher.decrypt(encrypted_data.encode())
            logger.debug("Data decrypted successfully")
            return decrypted_data.decode()
        except Exception as e:
            logger.error(f"Decryption error: {e}")
            raise
    
    def encrypt_dict(self, data: Dict[str, Any]) -> str:
        """Encrypt dictionary data."""
        import json
        json_str = json.dumps(data)
        return self.encrypt(json_str)
    
    def decrypt_dict(self, encrypted_data: str) -> Dict[str, Any]:
        """Decrypt dictionary data."""
        import json
        json_str = self.decrypt(encrypted_data)
        return json.loads(json_str)

class RateLimiter:
    """Enterprise rate limiting with sliding window."""
    
    def __init__(self, config: SecurityConfig):
        self.config = config
        self._requests: Dict[str, List[float]] = {}
    
    def is_allowed(self, identifier: str, limit: Optional[int] = None, window: Optional[int] = None) -> bool:
        """Check if request is allowed based on rate limit."""
        limit = limit or self.config.RATE_LIMIT_REQUESTS
        window = window or self.config.RATE_LIMIT_WINDOW
        now = time.time()
        
        # Clean old requests
        if identifier in self._requests:
            self._requests[identifier] = [
                req_time for req_time in self._requests[identifier]
                if now - req_time < window
            ]
        else:
            self._requests[identifier] = []
        
        # Check limit
        if len(self._requests[identifier]) >= limit:
            logger.warning(f"Rate limit exceeded for {identifier}: {len(self._requests[identifier])}/{limit}")
            metrics_collector.increment_counter("security.rate_limit.exceeded", tags={"identifier": identifier})
            return False
        
        # Add current request
        self._requests[identifier].append(now)
        return True
    
    def get_remaining_requests(self, identifier: str, limit: Optional[int] = None, window: Optional[int] = None) -> int:
        """Get remaining requests for identifier."""
        limit = limit or self.config.RATE_LIMIT_REQUESTS
        window = window or self.config.RATE_LIMIT_WINDOW
        now = time.time()
        
        if identifier not in self._requests:
            return limit
        
        # Count recent requests
        recent_requests = [
            req_time for req_time in self._requests[identifier]
            if now - req_time < window
        ]
        
        return max(0, limit - len(recent_requests))

class IPFilter:
    """Enterprise IP filtering and geolocation."""
    
    def __init__(self, config: SecurityConfig):
        self.config = config
        self._allowed_networks = []
        self._blocked_networks = []
        
        # Parse IP ranges
        for ip_range in config.ALLOWED_IP_RANGES:
            try:
                self._allowed_networks.append(ipaddress.ip_network(ip_range))
            except ValueError:
                logger.warning(f"Invalid allowed IP range: {ip_range}")
        
        for ip_range in config.BLOCKED_IPS:
            try:
                self._blocked_networks.append(ipaddress.ip_network(ip_range))
            except ValueError:
                logger.warning(f"Invalid blocked IP range: {ip_range}")
    
    def is_allowed(self, ip_address: str) -> bool:
        """Check if IP address is allowed."""
        try:
            ip = ipaddress.ip_address(ip_address)
            
            # Check blocked IPs first
            for network in self._blocked_networks:
                if ip in network:
                    logger.warning(f"IP blocked: {ip_address}")
                    metrics_collector.increment_counter("security.ip.blocked", tags={"ip": ip_address})
                    return False
            
            # If no allowed ranges configured, allow all
            if not self._allowed_networks:
                return True
            
            # Check allowed IPs
            for network in self._allowed_networks:
                if ip in network:
                    logger.debug(f"IP allowed: {ip_address}")
                    return True
            
            logger.warning(f"IP not in allowed list: {ip_address}")
            metrics_collector.increment_counter("security.ip.denied", tags={"ip": ip_address})
            return False
        
        except ValueError:
            logger.error(f"Invalid IP address: {ip_address}")
            return False

class SecurityManager:
    """Enterprise security manager combining all security features."""
    
    def __init__(self, config: SecurityConfig):
        self.config = config
        self.token_manager = TokenManager(config)
        self.password_manager = PasswordManager(config)
        self.encryption_manager = EncryptionManager(config)
        self.rate_limiter = RateLimiter(config)
        self.ip_filter = IPFilter(config)
    
    def create_security_context(self, request: Request) -> SecurityContext:
        """Create security context from request."""
        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("user-agent", "unknown")
        request_id = request.headers.get("x-request-id", secrets.token_urlsafe(8))
        
        return SecurityContext(
            ip_address=client_ip,
            user_agent=user_agent,
            request_id=request_id,
            timestamp=datetime.utcnow()
        )
    
    def authenticate_request(self, request: Request) -> Optional[SecurityContext]:
        """Authenticate request and return security context."""
        context = self.create_security_context(request)
        
        # IP filtering
        if not self.ip_filter.is_allowed(context.ip_address):
            logger.warning(f"Request blocked from IP: {context.ip_address}")
            return None
        
        # Rate limiting
        if not self.rate_limiter.is_allowed(context.ip_address):
            logger.warning(f"Rate limit exceeded for IP: {context.ip_address}")
            return None
        
        # Token authentication
        authorization = request.headers.get("authorization")
        if authorization and authorization.startswith("Bearer "):
            token = authorization.split(" ")[1]
            payload = self.token_manager.verify_token(token)
            
            if payload:
                context.user_id = payload.get("sub")
                context.permissions = payload.get("permissions", [])
                logger.info(f"User authenticated: {context.user_id}")
            else:
                logger.warning("Invalid token provided")
                return None
        
        return context

# Global security manager
security_config = SecurityConfig()
security_manager = SecurityManager(security_config)

# FastAPI Security Dependency
security = HTTPBearer()

async def get_current_user(credentials: HTTPAuthorizationCredentials = security, request: Request = None) -> SecurityContext:
    """FastAPI dependency to get current authenticated user."""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    context = security_manager.create_security_context(request)
    
    # Verify token
    payload = security_manager.token_manager.verify_token(credentials.credentials)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    context.user_id = payload.get("sub")
    context.permissions = payload.get("permissions", [])
    
    return context

def require_permission(permission: str):
    """Decorator to require specific permission."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Get security context from kwargs or request
            context = kwargs.get("security_context")
            if not context or not context.user_id:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required"
                )
            
            if permission not in context.permissions:
                logger.warning(f"Permission denied: {permission} for user {context.user_id}")
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Permission required: {permission}"
                )
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator
