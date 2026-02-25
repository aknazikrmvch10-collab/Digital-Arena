"""
Enterprise monitoring and metrics collection system.
Provides real-time insights into application performance.
"""

import asyncio
import time
import psutil
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from collections import defaultdict, deque
from datetime import datetime, timedelta
import json

from utils.logging import get_logger

logger = get_logger(__name__)

@dataclass
class Metric:
    """Single metric data point."""
    name: str
    value: float
    timestamp: float
    tags: Dict[str, str] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "value": self.value,
            "timestamp": self.timestamp,
            "tags": self.tags
        }

@dataclass
class MetricSummary:
    """Aggregated metric summary."""
    name: str
    count: int
    sum: float
    min: float
    max: float
    avg: float
    tags: Dict[str, str] = field(default_factory=dict)
    
    @classmethod
    def from_metrics(cls, metrics: List[Metric]) -> 'MetricSummary':
        if not metrics:
            raise ValueError("No metrics provided")
        
        values = [m.value for m in metrics]
        return cls(
            name=metrics[0].name,
            count=len(metrics),
            sum=sum(values),
            min=min(values),
            max=max(values),
            avg=sum(values) / len(values),
            tags=metrics[0].tags
        )

class MetricsCollector:
    """Enterprise metrics collection with time-series storage."""
    
    def __init__(self, max_metrics: int = 100000):
        self._metrics: Dict[str, deque] = defaultdict(lambda: deque(maxlen=max_metrics))
        self._counters: Dict[str, float] = defaultdict(float)
        self._gauges: Dict[str, float] = defaultdict(float)
        self._histograms: Dict[str, List[float]] = defaultdict(list)
        self._lock = asyncio.Lock()
        
    async def record_metric(self, name: str, value: float, tags: Optional[Dict[str, str]] = None) -> None:
        """Record a metric value."""
        metric = Metric(
            name=name,
            value=value,
            timestamp=time.time(),
            tags=tags or {}
        )
        
        async with self._lock:
            self._metrics[name].append(metric)
    
    async def increment_counter(self, name: str, value: float = 1.0, tags: Optional[Dict[str, str]] = None) -> None:
        """Increment a counter metric."""
        key = self._make_key(name, tags)
        self._counters[key] += value
        await self.record_metric(f"{name}_counter", self._counters[key], tags)
    
    async def set_gauge(self, name: str, value: float, tags: Optional[Dict[str, str]] = None) -> None:
        """Set a gauge metric."""
        key = self._make_key(name, tags)
        self._gauges[key] = value
        await self.record_metric(f"{name}_gauge", value, tags)
    
    async def record_histogram(self, name: str, value: float, tags: Optional[Dict[str, str]] = None) -> None:
        """Record a histogram metric."""
        key = self._make_key(name, tags)
        self._histograms[key].append(value)
        await self.record_metric(f"{name}_histogram", value, tags)
    
    def _make_key(self, name: str, tags: Optional[Dict[str, str]]) -> str:
        """Create a composite key from name and tags."""
        if not tags:
            return name
        tag_str = ",".join(f"{k}={v}" for k, v in sorted(tags.items()))
        return f"{name}[{tag_str}]"
    
    async def get_metrics(
        self, 
        name: Optional[str] = None,
        since: Optional[float] = None,
        limit: Optional[int] = None
    ) -> List[Metric]:
        """Get metrics with optional filtering."""
        async with self._lock:
            if name:
                if name not in self._metrics:
                    return []
                metrics = list(self._metrics[name])
            else:
                metrics = []
                for metric_list in self._metrics.values():
                    metrics.extend(metric_list)
            
            if since:
                metrics = [m for m in metrics if m.timestamp >= since]
            
            # Sort by timestamp
            metrics.sort(key=lambda m: m.timestamp)
            
            if limit:
                metrics = metrics[-limit:]
            
            return metrics
    
    async def get_summary(self, name: str, since: Optional[float] = None) -> Optional[MetricSummary]:
        """Get aggregated summary for a metric."""
        metrics = await self.get_metrics(name=name, since=since)
        if not metrics:
            return None
        return MetricSummary.from_metrics(metrics)
    
    def get_current_counters(self) -> Dict[str, float]:
        """Get current counter values."""
        return dict(self._counters)
    
    def get_current_gauges(self) -> Dict[str, float]:
        """Get current gauge values."""
        return dict(self._gauges)

class SystemMonitor:
    """System resource monitoring."""
    
    def __init__(self, metrics_collector: MetricsCollector):
        self.metrics = metrics_collector
        self._monitoring = False
        self._task: Optional[asyncio.Task] = None
    
    async def start_monitoring(self, interval: float = 30.0) -> None:
        """Start system monitoring."""
        if self._monitoring:
            return
        
        self._monitoring = True
        self._task = asyncio.create_task(self._monitor_loop(interval))
        logger.info("System monitoring started")
    
    async def stop_monitoring(self) -> None:
        """Stop system monitoring."""
        self._monitoring = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("System monitoring stopped")
    
    async def _monitor_loop(self, interval: float) -> None:
        """Main monitoring loop."""
        while self._monitoring:
            try:
                await self._collect_system_metrics()
                await asyncio.sleep(interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"System monitoring error: {e}")
                await asyncio.sleep(interval)
    
    async def _collect_system_metrics(self) -> None:
        """Collect system metrics."""
        # CPU metrics
        cpu_percent = psutil.cpu_percent(interval=1)
        await self.metrics.set_gauge("system.cpu.percent", cpu_percent)
        
        # Memory metrics
        memory = psutil.virtual_memory()
        await self.metrics.set_gauge("system.memory.percent", memory.percent)
        await self.metrics.set_gauge("system.memory.used_gb", memory.used / (1024**3))
        await self.metrics.set_gauge("system.memory.available_gb", memory.available / (1024**3))
        
        # Disk metrics
        disk = psutil.disk_usage('/')
        await self.metrics.set_gauge("system.disk.percent", disk.percent)
        await self.metrics.set_gauge("system.disk.used_gb", disk.used / (1024**3))
        await self.metrics.set_gauge("system.disk.free_gb", disk.free / (1024**3))
        
        # Network metrics
        network = psutil.net_io_counters()
        await self.metrics.increment_counter("system.network.bytes_sent", network.bytes_sent)
        await self.metrics.increment_counter("system.network.bytes_recv", network.bytes_recv)

class PerformanceProfiler:
    """Performance profiling for functions and endpoints."""
    
    def __init__(self, metrics_collector: MetricsCollector):
        self.metrics = metrics_collector
        self._active_requests: Dict[str, float] = {}
    
    def profile(self, name: str, tags: Optional[Dict[str, str]] = None):
        """Decorator to profile function performance."""
        def decorator(func: Callable) -> Callable:
            if asyncio.iscoroutinefunction(func):
                async def async_wrapper(*args, **kwargs):
                    start_time = time.time()
                    request_id = f"{name}_{start_time}"
                    
                    # Track active requests
                    self._active_requests[request_id] = start_time
                    await self.metrics.increment_counter(f"{name}_active", tags=tags)
                    
                    try:
                        result = await func(*args, **kwargs)
                        await self.metrics.increment_counter(f"{name}_success", tags=tags)
                        return result
                    except Exception as e:
                        await self.metrics.increment_counter(f"{name}_error", tags=tags)
                        raise
                    finally:
                        # Record duration and clean up
                        duration = time.time() - start_time
                        await self.metrics.record_histogram(f"{name}_duration", duration, tags)
                        
                        if request_id in self._active_requests:
                            del self._active_requests[request_id]
                        
                        await self.metrics.increment_counter(f"{name}_active", -1, tags=tags)
                
                return async_wrapper
            else:
                def sync_wrapper(*args, **kwargs):
                    start_time = time.time()
                    request_id = f"{name}_{start_time}"
                    
                    self._active_requests[request_id] = start_time
                    
                    try:
                        result = func(*args, **kwargs)
                        return result
                    finally:
                        duration = time.time() - start_time
                        asyncio.create_task(self.metrics.record_histogram(f"{name}_duration", duration, tags))
                        
                        if request_id in self._active_requests:
                            del self._active_requests[request_id]
                
                return sync_wrapper
        
        return decorator
    
    async def get_active_requests_count(self) -> int:
        """Get count of currently active requests."""
        return len(self._active_requests)

class AlertManager:
    """Alert management based on metric thresholds."""
    
    def __init__(self, metrics_collector: MetricsCollector):
        self.metrics = metrics_collector
        self._rules: List[Dict[str, Any]] = []
        self._alerts: List[Dict[str, Any]] = []
    
    def add_rule(self, name: str, metric_name: str, threshold: float, operator: str = "gt", 
                 severity: str = "warning", tags: Optional[Dict[str, str]] = None) -> None:
        """Add alert rule."""
        rule = {
            "name": name,
            "metric_name": metric_name,
            "threshold": threshold,
            "operator": operator,
            "severity": severity,
            "tags": tags or {}
        }
        self._rules.append(rule)
        logger.info(f"Added alert rule: {name}")
    
    async def check_alerts(self) -> List[Dict[str, Any]]:
        """Check all alert rules and return triggered alerts."""
        triggered_alerts = []
        
        for rule in self._rules:
            try:
                summary = await self.metrics.get_summary(rule["metric_name"])
                if not summary:
                    continue
                
                value = summary.avg  # Use average for alerting
                
                triggered = False
                if rule["operator"] == "gt" and value > rule["threshold"]:
                    triggered = True
                elif rule["operator"] == "lt" and value < rule["threshold"]:
                    triggered = True
                elif rule["operator"] == "eq" and value == rule["threshold"]:
                    triggered = True
                
                if triggered:
                    alert = {
                        "rule_name": rule["name"],
                        "metric_name": rule["metric_name"],
                        "value": value,
                        "threshold": rule["threshold"],
                        "severity": rule["severity"],
                        "timestamp": time.time(),
                        "tags": rule["tags"]
                    }
                    triggered_alerts.append(alert)
                    self._alerts.append(alert)
                    logger.warning(f"Alert triggered: {rule['name']} - {value} {rule['operator']} {rule['threshold']}")
            
            except Exception as e:
                logger.error(f"Error checking alert rule {rule['name']}: {e}")
        
        return triggered_alerts
    
    def get_recent_alerts(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Get recent alerts."""
        since = time.time() - (hours * 3600)
        return [alert for alert in self._alerts if alert["timestamp"] >= since]

# Global monitoring components
metrics_collector = MetricsCollector()
system_monitor = SystemMonitor(metrics_collector)
performance_profiler = PerformanceProfiler(metrics_collector)
alert_manager = AlertManager(metrics_collector)

# Default alert rules
alert_manager.add_rule("high_cpu", "system.cpu.percent", 80, "gt", "critical")
alert_manager.add_rule("high_memory", "system.memory.percent", 85, "gt", "critical")
alert_manager.add_rule("high_disk", "system.disk.percent", 90, "gt", "warning")
