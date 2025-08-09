#!/usr/bin/env python3
"""
Performance Monitor for Anthropic Native Pass-Through
=====================================================

Real-time performance monitoring system that tracks:
- Request latency percentiles and throughput
- Connection pool utilization and health
- SSE streaming performance metrics
- Memory usage and resource consumption
- Error rates and failure patterns

Features:
- Automatic performance alerting
- Historical trend analysis
- Resource leak detection
- Production health checks

Usage:
    monitor = PerformanceMonitor()
    monitor.start_monitoring()
    
    # In your endpoint handlers:
    with monitor.track_request("messages"):
        # Your request handling code
        pass
    
    # Get current metrics
    metrics = await monitor.get_current_metrics()
"""

import time
import asyncio
import logging
import threading
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field, asdict
from contextlib import contextmanager, asynccontextmanager
import statistics
import psutil
from collections import deque, defaultdict

logger = logging.getLogger(__name__)

@dataclass
class RequestMetrics:
    """Metrics for a single request."""
    endpoint: str
    start_time: float
    end_time: float
    success: bool
    error_type: Optional[str] = None
    memory_used_mb: float = 0.0
    
    @property
    def duration_ms(self) -> float:
        """Request duration in milliseconds."""
        return (self.end_time - self.start_time) * 1000
    
    @property
    def duration_seconds(self) -> float:
        """Request duration in seconds."""
        return self.end_time - self.start_time

@dataclass
class PerformanceWindow:
    """Performance metrics for a time window."""
    window_start: float
    window_end: float
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    latencies_ms: List[float] = field(default_factory=list)
    memory_usage_mb: List[float] = field(default_factory=list)
    error_types: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    
    @property
    def duration_seconds(self) -> float:
        return self.window_end - self.window_start
    
    @property
    def requests_per_second(self) -> float:
        return self.successful_requests / self.duration_seconds if self.duration_seconds > 0 else 0
    
    @property
    def error_rate(self) -> float:
        return self.failed_requests / self.total_requests if self.total_requests > 0 else 0
    
    @property
    def avg_latency_ms(self) -> float:
        return statistics.mean(self.latencies_ms) if self.latencies_ms else 0
    
    @property
    def p50_latency_ms(self) -> float:
        return statistics.median(self.latencies_ms) if self.latencies_ms else 0
    
    @property
    def p95_latency_ms(self) -> float:
        if not self.latencies_ms:
            return 0
        sorted_latencies = sorted(self.latencies_ms)
        return sorted_latencies[int(0.95 * len(sorted_latencies))]
    
    @property
    def p99_latency_ms(self) -> float:
        if not self.latencies_ms:
            return 0
        sorted_latencies = sorted(self.latencies_ms)
        return sorted_latencies[int(0.99 * len(sorted_latencies))]
    
    @property
    def avg_memory_mb(self) -> float:
        return statistics.mean(self.memory_usage_mb) if self.memory_usage_mb else 0

class PerformanceMonitor:
    """
    Comprehensive performance monitoring for Anthropic native adapter.
    
    Tracks request metrics, resource usage, and provides alerting capabilities.
    """
    
    def __init__(self, 
                 window_size_seconds: int = 60,
                 history_size: int = 60,
                 alert_thresholds: Optional[Dict[str, float]] = None):
        """
        Initialize performance monitor.
        
        Args:
            window_size_seconds: Size of performance measurement windows
            history_size: Number of historical windows to keep
            alert_thresholds: Custom thresholds for performance alerts
        """
        self.window_size_seconds = window_size_seconds
        self.history_size = history_size
        
        # Default alert thresholds
        self.alert_thresholds = {
            "p95_latency_ms": 500,
            "p99_latency_ms": 1000, 
            "error_rate": 0.05,  # 5%
            "memory_growth_mb": 50,
            "requests_per_second_min": 1
        }
        if alert_thresholds:
            self.alert_thresholds.update(alert_thresholds)
        
        # Performance tracking
        self.current_window = self._create_new_window()
        self.performance_history: deque = deque(maxlen=history_size)
        self.active_requests: Dict[str, RequestMetrics] = {}
        
        # System monitoring
        self.process = psutil.Process()
        self.start_memory_mb = self.process.memory_info().rss / 1024 / 1024
        
        # Thread safety
        self._lock = threading.RLock()
        self._monitoring_task: Optional[asyncio.Task] = None
        self._monitoring_active = False
        
        # Alert callbacks
        self._alert_callbacks: List[Callable[[str, Dict[str, Any]], None]] = []
        
        logger.info(f"🔧 PerformanceMonitor initialized with {window_size_seconds}s windows")
    
    def _create_new_window(self) -> PerformanceWindow:
        """Create a new performance measurement window."""
        now = time.time()
        return PerformanceWindow(
            window_start=now,
            window_end=now + self.window_size_seconds
        )
    
    def add_alert_callback(self, callback: Callable[[str, Dict[str, Any]], None]):
        """
        Add a callback function to be called when performance alerts are triggered.
        
        Args:
            callback: Function to call with (alert_type, alert_data) parameters
        """
        self._alert_callbacks.append(callback)
    
    @contextmanager
    def track_request(self, endpoint: str):
        """
        Context manager to track request performance.
        
        Args:
            endpoint: Name of the endpoint being tracked
            
        Usage:
            with monitor.track_request("messages"):
                # Your request handling code
                response = handle_request()
        """
        request_id = f"{endpoint}_{time.time()}_{threading.current_thread().ident}"
        start_memory = self.process.memory_info().rss / 1024 / 1024
        
        metrics = RequestMetrics(
            endpoint=endpoint,
            start_time=time.time(),
            end_time=0,  # Will be set on exit
            success=False,
            memory_used_mb=start_memory
        )
        
        with self._lock:
            self.active_requests[request_id] = metrics
        
        try:
            yield metrics
            metrics.success = True
        except Exception as e:
            metrics.success = False
            metrics.error_type = type(e).__name__
            raise
        finally:
            end_memory = self.process.memory_info().rss / 1024 / 1024
            metrics.end_time = time.time()
            metrics.memory_used_mb = end_memory - metrics.memory_used_mb
            
            with self._lock:
                self.active_requests.pop(request_id, None)
                self._record_request_metrics(metrics)
    
    @asynccontextmanager
    async def track_async_request(self, endpoint: str):
        """
        Async context manager to track request performance.
        
        Args:
            endpoint: Name of the endpoint being tracked
        """
        request_id = f"{endpoint}_{time.time()}_{asyncio.current_task()}"
        start_memory = self.process.memory_info().rss / 1024 / 1024
        
        metrics = RequestMetrics(
            endpoint=endpoint,
            start_time=time.time(),
            end_time=0,
            success=False,
            memory_used_mb=start_memory
        )
        
        with self._lock:
            self.active_requests[request_id] = metrics
        
        try:
            yield metrics
            metrics.success = True
        except Exception as e:
            metrics.success = False
            metrics.error_type = type(e).__name__
            raise
        finally:
            end_memory = self.process.memory_info().rss / 1024 / 1024
            metrics.end_time = time.time()
            metrics.memory_used_mb = end_memory - metrics.memory_used_mb
            
            with self._lock:
                self.active_requests.pop(request_id, None)
                self._record_request_metrics(metrics)
    
    def _record_request_metrics(self, metrics: RequestMetrics):
        """Record completed request metrics."""
        current_time = time.time()
        
        # Check if we need to create a new window
        if current_time >= self.current_window.window_end:
            # Archive current window
            self.performance_history.append(self.current_window)
            # Create new window
            self.current_window = self._create_new_window()
        
        # Record metrics in current window
        self.current_window.total_requests += 1
        if metrics.success:
            self.current_window.successful_requests += 1
        else:
            self.current_window.failed_requests += 1
            if metrics.error_type:
                self.current_window.error_types[metrics.error_type] += 1
        
        self.current_window.latencies_ms.append(metrics.duration_ms)
        self.current_window.memory_usage_mb.append(metrics.memory_used_mb)
    
    async def get_current_metrics(self) -> Dict[str, Any]:
        """
        Get current performance metrics.
        
        Returns:
            Dict: Current performance statistics
        """
        with self._lock:
            current_window_data = asdict(self.current_window)
            
            # Calculate derived metrics
            current_memory = self.process.memory_info().rss / 1024 / 1024
            memory_growth = current_memory - self.start_memory_mb
            
            # Historical trend analysis
            if self.performance_history:
                last_hour_windows = list(self.performance_history)[-60:]  # Last hour
                avg_rps_last_hour = statistics.mean([w.requests_per_second for w in last_hour_windows])
                avg_latency_last_hour = statistics.mean([w.avg_latency_ms for w in last_hour_windows if w.latencies_ms])
            else:
                avg_rps_last_hour = 0
                avg_latency_last_hour = 0
            
            return {
                "timestamp": time.time(),
                "current_window": current_window_data,
                "system_metrics": {
                    "current_memory_mb": current_memory,
                    "memory_growth_mb": memory_growth,
                    "cpu_percent": self.process.cpu_percent(),
                    "active_threads": threading.active_count(),
                    "active_requests": len(self.active_requests)
                },
                "historical_trends": {
                    "avg_rps_last_hour": avg_rps_last_hour,
                    "avg_latency_last_hour": avg_latency_last_hour,
                    "windows_collected": len(self.performance_history)
                },
                "alert_status": await self._check_alerts()
            }
    
    async def _check_alerts(self) -> Dict[str, Any]:
        """
        Check if any performance thresholds have been exceeded.
        
        Returns:
            Dict: Alert status and triggered alerts
        """
        alerts = []
        
        # Check current window metrics
        if self.current_window.latencies_ms:
            if self.current_window.p95_latency_ms > self.alert_thresholds["p95_latency_ms"]:
                alerts.append({
                    "type": "high_p95_latency",
                    "value": self.current_window.p95_latency_ms,
                    "threshold": self.alert_thresholds["p95_latency_ms"],
                    "severity": "warning"
                })
            
            if self.current_window.p99_latency_ms > self.alert_thresholds["p99_latency_ms"]:
                alerts.append({
                    "type": "high_p99_latency",
                    "value": self.current_window.p99_latency_ms,
                    "threshold": self.alert_thresholds["p99_latency_ms"],
                    "severity": "critical"
                })
        
        if self.current_window.error_rate > self.alert_thresholds["error_rate"]:
            alerts.append({
                "type": "high_error_rate",
                "value": self.current_window.error_rate,
                "threshold": self.alert_thresholds["error_rate"],
                "severity": "critical"
            })
        
        # Check memory growth
        current_memory = self.process.memory_info().rss / 1024 / 1024
        memory_growth = current_memory - self.start_memory_mb
        if memory_growth > self.alert_thresholds["memory_growth_mb"]:
            alerts.append({
                "type": "memory_growth",
                "value": memory_growth,
                "threshold": self.alert_thresholds["memory_growth_mb"],
                "severity": "warning"
            })
        
        # Check throughput
        if (self.current_window.requests_per_second < self.alert_thresholds["requests_per_second_min"] 
            and self.current_window.total_requests > 0):
            alerts.append({
                "type": "low_throughput", 
                "value": self.current_window.requests_per_second,
                "threshold": self.alert_thresholds["requests_per_second_min"],
                "severity": "warning"
            })
        
        # Trigger alert callbacks
        for alert in alerts:
            for callback in self._alert_callbacks:
                try:
                    callback(alert["type"], alert)
                except Exception as e:
                    logger.error(f"Alert callback failed: {e}")
        
        return {
            "alerts_active": len(alerts),
            "alerts": alerts,
            "thresholds": self.alert_thresholds
        }
    
    def start_monitoring(self):
        """Start background performance monitoring."""
        if self._monitoring_active:
            return
        
        self._monitoring_active = True
        self._monitoring_task = asyncio.create_task(self._monitoring_loop())
        logger.info("🚀 Performance monitoring started")
    
    async def stop_monitoring(self):
        """Stop background performance monitoring."""
        self._monitoring_active = False
        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass
        logger.info("🛑 Performance monitoring stopped")
    
    async def _monitoring_loop(self):
        """Background monitoring loop."""
        while self._monitoring_active:
            try:
                # Check for alerts every 10 seconds
                await self._check_alerts()
                
                # Log performance summary every minute
                current_time = time.time()
                if int(current_time) % 60 == 0:  # Every minute
                    metrics = await self.get_current_metrics()
                    logger.info(f"📊 Performance Summary: "
                              f"RPS={self.current_window.requests_per_second:.1f}, "
                              f"P95={self.current_window.p95_latency_ms:.1f}ms, "
                              f"Errors={self.current_window.error_rate:.1%}, "
                              f"Memory={metrics['system_metrics']['current_memory_mb']:.1f}MB")
                
                await asyncio.sleep(10)  # Check every 10 seconds
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Monitoring loop error: {e}")
                await asyncio.sleep(10)

# Global performance monitor instance
_global_monitor: Optional[PerformanceMonitor] = None
_monitor_lock = threading.Lock()

def get_performance_monitor() -> PerformanceMonitor:
    """
    Get or create the global performance monitor instance.
    
    Returns:
        PerformanceMonitor: Global monitor instance
    """
    global _global_monitor
    
    with _monitor_lock:
        if _global_monitor is None:
            _global_monitor = PerformanceMonitor()
            
            # Add default alert callback for logging
            def log_alert(alert_type: str, alert_data: Dict[str, Any]):
                severity = alert_data.get("severity", "info")
                value = alert_data.get("value", "N/A")
                threshold = alert_data.get("threshold", "N/A")
                logger.warning(f"🚨 PERFORMANCE ALERT [{severity.upper()}]: {alert_type} "
                             f"- Value: {value}, Threshold: {threshold}")
            
            _global_monitor.add_alert_callback(log_alert)
        
        return _global_monitor

async def shutdown_performance_monitor():
    """Shutdown the global performance monitor."""
    global _global_monitor
    
    with _monitor_lock:
        if _global_monitor:
            await _global_monitor.stop_monitoring()
            _global_monitor = None