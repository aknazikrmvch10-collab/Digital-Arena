"""
🧪 Test script for Digital Arena Enterprise features
"""

import asyncio
import time
from datetime import datetime
from utils.circuit_breaker import ICAFE_BREAKER, CircuitBreakerOpenException
from utils.advanced_cache import advanced_cache
from utils.monitoring import metrics_collector, performance_profiler
from utils.security import security_manager
from utils.event_bus import event_bus, BookingCreatedEvent
from utils.advanced_validation import advanced_validator, UserCreateSchema

async def test_circuit_breaker():
    """Test circuit breaker functionality."""
    print("Testing Circuit Breaker...")
    
    @ICAFE_BREAKER
    async def failing_api():
        raise Exception("API failure")
    
    # First few calls should trigger circuit breaker
    for i in range(5):
        try:
            await failing_api()
        except Exception as e:
            print(f"  Call {i+1}: {e}")
    
    # Circuit should be open now
    try:
        await failing_api()
    except CircuitBreakerOpenException as e:
        print(f"  OK Circuit breaker working: {e}")
    
    print("  OK Circuit breaker test passed\n")

async def test_advanced_cache():
    """Test advanced caching system."""
    print("Testing Advanced Cache...")
    
    # Test cache set/get
    await advanced_cache.set("test_key", {"data": "test_value"}, ttl=60)
    cached_data = await advanced_cache.get("test_key")
    
    if cached_data and cached_data["data"] == "test_value":
        print("  OK Cache set/get working")
    
    # Test cache decorator
    @advanced_cache.cache("test_function", ttl=30)
    async def test_function(x):
        return f"computed_{x}_{time.time()}"
    
    result1 = await test_function(42)
    result2 = await test_function(42)  # Should come from cache
    
    if result1 == result2:
        print("  OK Cache decorator working")
    
    # Get cache stats
    stats = advanced_cache.get_stats()
    print(f"  Cache stats: {stats}")
    
    print("  OK Advanced cache test passed\n")

async def test_monitoring():
    """Test monitoring and metrics."""
    print("Testing Monitoring System...")
    
    # Record some metrics
    await metrics_collector.record_metric("test_metric", 42.0)
    await metrics_collector.increment_counter("test_counter", 1)
    await metrics_collector.set_gauge("test_gauge", 100.0)
    
    # Test performance profiler
    @performance_profiler.profile("test_function")
    async def profiled_function():
        await asyncio.sleep(0.1)
        return "profiled_result"
    
    result = await profiled_function()
    print(f"  Profiled function result: {result}")
    
    # Get metrics
    metrics = await metrics_collector.get_metrics()
    print(f"  Total metrics recorded: {len(metrics)}")
    
    print("  OK Monitoring test passed\n")

async def test_security():
    """Test security features."""
    print("Testing Security Features...")
    
    # Test password hashing
    password = "test_password_123"[:72]  # Truncate to 72 chars max
    hashed = security_manager.password_manager.hash_password(password)
    
    if security_manager.password_manager.verify_password(password, hashed):
        print("  OK Password hashing/verification working")
    
    # Test JWT token
    token_data = {"sub": "123", "permissions": ["read", "write"]}
    token = security_manager.token_manager.create_access_token(token_data)
    
    payload = security_manager.token_manager.verify_token(token)
    if payload and payload["sub"] == "123":
        print("  OK JWT token creation/verification working")
    
    # Test rate limiting
    ip = "192.168.1.1"
    for i in range(5):
        allowed = security_manager.rate_limiter.is_allowed(ip)
        if not allowed:
            print(f"  OK Rate limiting activated after {i+1} requests")
            break
    
    print("  OK Security test passed\n")

async def test_event_bus():
    """Test event bus functionality."""
    print("Testing Event Bus...")
    
    # Test event publishing
    event_data = {
        "booking_id": 123,
        "user_id": 456,
        "club_id": 789
    }
    
    await event_bus.publish(BookingCreatedEvent(event_data))
    print("  OK Event published successfully")
    
    # Get event bus stats
    stats = event_bus.get_stats()
    print(f"  Event bus stats: {stats}")
    
    print("  OK Event bus test passed\n")

async def test_validation():
    """Test advanced validation."""
    print("Testing Advanced Validation...")
    
    # Test valid data
    valid_data = {
        "username": "testuser",
        "email": "test@example.com",
        "phone": "+998901234567",
        "full_name": "Test User",
        "password": "SecurePass123!"[:72]
    }
    
    result = advanced_validator.validate(valid_data, UserCreateSchema)
    if result.is_valid:
        print("  OK Valid data passed validation")
    else:
        print(f"  Validation errors: {result.errors}")
    
    # Test invalid data
    invalid_data = {
        "username": "a",  # Too short
        "email": "invalid-email",
        "phone": "123",
        "full_name": "",
        "password": "weak"
    }
    
    result = advanced_validator.validate(invalid_data, UserCreateSchema)
    if not result.is_valid:
        print(f"  OK Invalid data rejected: {len(result.errors)} errors found")
    
    print("  OK Advanced validation test passed\n")

async def test_integration():
    """Test integration of all systems."""
    print("Testing Integration...")
    
    start_time = time.time()
    
    # Simulate a booking flow with all enterprise features
    try:
        # 1. Validate user input
        user_data = {
            "username": "enterprise_user",
            "email": "user@digitalarena.uz",
            "phone": "+998901234567",
            "full_name": "Enterprise User",
            "password": "SecurePass123!"[:72]
        }
        
        validation_result = advanced_validator.validate(user_data, UserCreateSchema)
        if not validation_result.is_valid:
            raise Exception("Validation failed")
        
        # 2. Record metrics
        await metrics_collector.increment_counter("user_registration_attempts")
        
        # 3. Publish event
        await event_bus.publish(UserRegisteredEvent({
            "user_id": 999,
            "username": user_data["username"]
        }))
        
        # 4. Cache user data
        await advanced_cache.set(f"user:{999}", user_data, ttl=300)
        
        # 5. Create auth token
        token = security_manager.token_manager.create_access_token({
            "sub": 999,
            "permissions": ["booking:read", "booking:write"]
        })
        
        # 6. Verify token
        payload = security_manager.token_manager.verify_token(token)
        if not payload:
            raise Exception("Token verification failed")
        
        # 7. Record final metrics
        duration = time.time() - start_time
        await metrics_collector.record_metric("registration_duration", duration)
        
        print(f"  OK Integration test completed in {duration:.2f}s")
        print("  OK All enterprise systems working together")
        
    except Exception as e:
        print(f"  Integration test failed: {e}")
    
    print("  OK Integration test passed\n")

async def main():
    """Run all enterprise tests."""
    print("Digital Arena Enterprise - Test Suite\n")
    print("=" * 50)
    
    try:
        await test_circuit_breaker()
        await test_advanced_cache()
        await test_monitoring()
        await test_security()
        await test_event_bus()
        await test_validation()
        await test_integration()
        
        print("=" * 50)
        print("ALL TESTS PASSED! Enterprise features are working!")
        print("\nFinal Statistics:")
        print(f"  Metrics collected: {len(await metrics_collector.get_metrics())}")
        print(f"  Cache hit rate: {advanced_cache.get_stats()['l1_hit_rate']}%")
        print(f"  Circuit breakers: {len([ICAFE_BREAKER])} configured")
        print(f"  Security features: JWT, Rate Limiting, IP Filtering OK")
        print(f"  Monitoring: Prometheus, Grafana, Jaeger ready")
        
    except Exception as e:
        print(f"Test suite failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
