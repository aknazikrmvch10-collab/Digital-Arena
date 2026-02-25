"""
Enterprise Event Bus for decoupled, event-driven architecture.
Supports async event handling, middleware, and event sourcing.
"""

import asyncio
import json
import time
from typing import Any, Dict, List, Callable, Optional, Type
from dataclasses import dataclass, asdict
from enum import Enum
from abc import ABC, abstractmethod
import uuid
from datetime import datetime

from utils.logging import get_logger

logger = get_logger(__name__)

class EventPriority(Enum):
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4

@dataclass
class Event:
    """Base event class with metadata."""
    event_id: str
    event_type: str
    data: Dict[str, Any]
    timestamp: float
    priority: EventPriority = EventPriority.NORMAL
    correlation_id: Optional[str] = None
    causation_id: Optional[str] = None
    version: int = 1
    
    def __post_init__(self):
        if not self.event_id:
            self.event_id = str(uuid.uuid4())
        if not self.timestamp:
            self.timestamp = time.time()
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Event':
        return cls(**data)

class EventHandler(ABC):
    """Abstract base class for event handlers."""
    
    @abstractmethod
    async def handle(self, event: Event) -> None:
        """Handle the event."""
        pass
    
    @property
    @abstractmethod
    def event_types(self) -> List[str]:
        """Return list of event types this handler handles."""
        pass

class EventMiddleware(ABC):
    """Abstract base class for event middleware."""
    
    @abstractmethod
    async def before_handle(self, event: Event) -> Optional[Event]:
        """Called before event is handled. Return None to stop processing."""
        pass
    
    @abstractmethod
    async def after_handle(self, event: Event, result: Any = None) -> None:
        """Called after event is handled."""
        pass
    
    @abstractmethod
    async def on_error(self, event: Event, error: Exception) -> None:
        """Called when handler raises an exception."""
        pass

class EventStore:
    """In-memory event store for event sourcing."""
    
    def __init__(self, max_size: int = 10000):
        self._events: List[Event] = []
        self._max_size = max_size
        self._lock = asyncio.Lock()
    
    async def append(self, event: Event) -> None:
        """Append event to store."""
        async with self._lock:
            self._events.append(event)
            # Trim if necessary
            if len(self._events) > self._max_size:
                self._events = self._events[-self._max_size:]
    
    async def get_events(
        self, 
        event_type: Optional[str] = None,
        since: Optional[float] = None,
        limit: Optional[int] = None
    ) -> List[Event]:
        """Get events with optional filtering."""
        events = self._events.copy()
        
        if event_type:
            events = [e for e in events if e.event_type == event_type]
        
        if since:
            events = [e for e in events if e.timestamp >= since]
        
        # Sort by timestamp
        events.sort(key=lambda e: e.timestamp)
        
        if limit:
            events = events[-limit:]
        
        return events
    
    async def get_event(self, event_id: str) -> Optional[Event]:
        """Get specific event by ID."""
        for event in self._events:
            if event.event_id == event_id:
                return event
        return None

class EventBus:
    """Enterprise-grade Event Bus with middleware and persistence."""
    
    def __init__(self, event_store: Optional[EventStore] = None):
        self._handlers: Dict[str, List[EventHandler]] = {}
        self._middleware: List[EventMiddleware] = []
        self._event_store = event_store or EventStore()
        self._stats = {
            "events_published": 0,
            "events_handled": 0,
            "handler_errors": 0,
            "middleware_errors": 0
        }
    
    def subscribe(self, handler: EventHandler) -> None:
        """Subscribe handler to event types."""
        for event_type in handler.event_types:
            if event_type not in self._handlers:
                self._handlers[event_type] = []
            self._handlers[event_type].append(handler)
            logger.info(f"Subscribed handler {handler.__class__.__name__} to {event_type}")
    
    def unsubscribe(self, handler: EventHandler) -> None:
        """Unsubscribe handler from all event types."""
        for event_type, handlers in self._handlers.items():
            if handler in handlers:
                handlers.remove(handler)
                logger.info(f"Unsubscribed handler {handler.__class__.__name__} from {event_type}")
    
    def add_middleware(self, middleware: EventMiddleware) -> None:
        """Add middleware to the event processing pipeline."""
        self._middleware.append(middleware)
        logger.info(f"Added middleware {middleware.__class__.__name__}")
    
    async def publish(self, event: Event) -> None:
        """Publish event to all subscribers."""
        try:
            # Store event
            await self._event_store.append(event)
            
            # Get handlers for this event type
            handlers = self._handlers.get(event.event_type, [])
            
            if not handlers:
                logger.debug(f"No handlers for event type: {event.event_type}")
                return
            
            # Process middleware before handling
            for middleware in self._middleware:
                try:
                    event = await middleware.before_handle(event)
                    if event is None:
                        logger.info("Middleware stopped event processing")
                        return
                except Exception as e:
                    self._stats["middleware_errors"] += 1
                    await middleware.on_error(event, e)
                    logger.error(f"Middleware before_handle error: {e}")
            
            # Handle event
            tasks = []
            for handler in handlers:
                task = asyncio.create_task(self._handle_with_middleware(handler, event))
                tasks.append(task)
            
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)
            
            self._stats["events_published"] += 1
            logger.info(f"Published event {event.event_type} to {len(handlers)} handlers")
            
        except Exception as e:
            logger.error(f"Error publishing event {event.event_type}: {e}")
            raise
    
    async def _handle_with_middleware(self, handler: EventHandler, event: Event) -> None:
        """Handle event with middleware support."""
        try:
            result = await handler.handle(event)
            
            # Process middleware after handling
            for middleware in self._middleware:
                try:
                    await middleware.after_handle(event, result)
                except Exception as e:
                    self._stats["middleware_errors"] += 1
                    await middleware.on_error(event, e)
                    logger.error(f"Middleware after_handle error: {e}")
            
            self._stats["events_handled"] += 1
            
        except Exception as e:
            self._stats["handler_errors"] += 1
            
            # Process middleware error handling
            for middleware in self._middleware:
                try:
                    await middleware.on_error(event, e)
                except Exception as middleware_error:
                    logger.error(f"Middleware on_error error: {middleware_error}")
            
            logger.error(f"Handler {handler.__class__.__name__} error: {e}")
    
    async def publish_batch(self, events: List[Event]) -> None:
        """Publish multiple events efficiently."""
        tasks = [self.publish(event) for event in events]
        await asyncio.gather(*tasks, return_exceptions=True)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get event bus statistics."""
        return {
            **self._stats,
            "handlers_count": sum(len(handlers) for handlers in self._handlers.values()),
            "middleware_count": len(self._middleware),
            "event_types": list(self._handlers.keys())
        }
    
    async def get_events(self, **kwargs) -> List[Event]:
        """Get events from the event store."""
        return await self._event_store.get_events(**kwargs)

# Domain Events
class BookingCreatedEvent(Event):
    def __init__(self, booking_data: Dict[str, Any], **kwargs):
        super().__init__(
            event_id=str(uuid.uuid4()),
            event_type="booking.created",
            data=booking_data,
            timestamp=time.time(),
            **kwargs
        )

class BookingCancelledEvent(Event):
    def __init__(self, booking_data: Dict[str, Any], **kwargs):
        super().__init__(
            event_id=str(uuid.uuid4()),
            event_type="booking.cancelled",
            data=booking_data,
            timestamp=time.time(),
            **kwargs
        )

class UserRegisteredEvent(Event):
    def __init__(self, user_data: Dict[str, Any], **kwargs):
        super().__init__(
            event_id=str(uuid.uuid4()),
            event_type="user.registered",
            data=user_data,
            timestamp=time.time(),
            **kwargs
        )

class PaymentProcessedEvent(Event):
    def __init__(self, payment_data: Dict[str, Any], **kwargs):
        super().__init__(
            event_id=str(uuid.uuid4()),
            event_type="payment.processed",
            data=payment_data,
            timestamp=time.time(),
            priority=EventPriority.HIGH,
            **kwargs
        )

# Global event bus instance
event_bus = EventBus()
