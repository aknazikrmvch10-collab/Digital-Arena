import structlog
import logging
import sys

def configure_structlog():
    """Configure structured logging for the application."""
    
    # Configure standard logging to use structlog
    logging.basicConfig(format="%(message)s", stream=sys.stdout, level=logging.INFO)
    
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.dev.set_exc_info,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer() # Use JSON for production
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )

def get_logger(name=None):
    return structlog.get_logger(name)
