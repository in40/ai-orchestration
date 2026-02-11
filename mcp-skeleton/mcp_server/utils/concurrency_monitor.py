"""
Concurrency Monitoring and Diagnostics for MCP Server
Tracks concurrent request handling and performance metrics
"""
import asyncio
import time
from typing import Dict, Any, Optional
from dataclasses import dataclass
from collections import deque
import threading


@dataclass
class RequestMetrics:
    """Data class to store metrics for a single request"""
    request_id: str
    method: str
    start_time: float
    end_time: Optional[float] = None
    duration: Optional[float] = None
    status: str = "processing"  # processing, completed, error
    error: Optional[str] = None


class ConcurrencyMonitor:
    """Monitors concurrent request handling and tracks performance metrics"""
    
    def __init__(self, max_history: int = 1000):
        self.max_history = max_history
        self.current_concurrent_requests = 0
        self.max_concurrent_requests = 0
        self.total_requests = 0
        self.completed_requests = 0
        self.failed_requests = 0
        self.lock = threading.Lock()
        
        # Store recent request metrics
        self.request_history = deque(maxlen=max_history)
        self.start_time = time.time()
        
        # Track ongoing requests
        self.ongoing_requests: Dict[str, RequestMetrics] = {}

    def request_started(self, request_id: str, method: str) -> RequestMetrics:
        """Called when a request starts processing"""
        with self.lock:
            self.total_requests += 1
            self.current_concurrent_requests += 1
            
            if self.current_concurrent_requests > self.max_concurrent_requests:
                self.max_concurrent_requests = self.current_concurrent_requests
                
            metric = RequestMetrics(
                request_id=request_id,
                method=method,
                start_time=time.time()
            )
            
            self.ongoing_requests[request_id] = metric
            return metric

    def request_finished(self, request_id: str, status: str = "completed", error: Optional[str] = None):
        """Called when a request finishes processing"""
        with self.lock:
            if request_id in self.ongoing_requests:
                metric = self.ongoing_requests[request_id]
                metric.end_time = time.time()
                metric.duration = metric.end_time - metric.start_time
                metric.status = status
                metric.error = error
                
                # Move to history
                self.request_history.append(metric)
                del self.ongoing_requests[request_id]
                
                self.current_concurrent_requests -= 1
                
                if status == "completed":
                    self.completed_requests += 1
                else:
                    self.failed_requests += 1

    def get_metrics(self) -> Dict[str, Any]:
        """Get current performance metrics"""
        with self.lock:
            # Calculate average duration from completed requests
            total_duration = sum(m.duration for m in self.request_history if m.duration is not None)
            avg_duration = total_duration / len([m for m in self.request_history if m.duration is not None]) if self.request_history else 0
            
            # Calculate requests per second
            uptime = time.time() - self.start_time
            req_per_sec = self.completed_requests / uptime if uptime > 0 else 0
            
            # Get top methods by count
            method_counts = {}
            for metric in self.request_history:
                method_counts[metric.method] = method_counts.get(metric.method, 0) + 1
            
            return {
                "current_concurrent_requests": self.current_concurrent_requests,
                "max_concurrent_requests": self.max_concurrent_requests,
                "total_requests": self.total_requests,
                "completed_requests": self.completed_requests,
                "failed_requests": self.failed_requests,
                "uptime_seconds": uptime,
                "requests_per_second": req_per_sec,
                "average_duration_ms": avg_duration * 1000,
                "top_methods": sorted(method_counts.items(), key=lambda x: x[1], reverse=True)[:10],
                "active_requests": len(self.ongoing_requests)
            }

    def get_detailed_metrics(self) -> Dict[str, Any]:
        """Get detailed metrics including recent request history"""
        basic_metrics = self.get_metrics()
        
        with self.lock:
            recent_requests = list(self.request_history)[-20:]  # Last 20 requests
            active_requests = list(self.ongoing_requests.values())
            
            return {
                **basic_metrics,
                "recent_requests": [
                    {
                        "id": r.request_id,
                        "method": r.method,
                        "duration_ms": r.duration * 1000 if r.duration else None,
                        "status": r.status,
                        "start_time": r.start_time
                    }
                    for r in recent_requests
                ],
                "active_requests_details": [
                    {
                        "id": r.request_id,
                        "method": r.method,
                        "elapsed_ms": (time.time() - r.start_time) * 1000,
                        "start_time": r.start_time
                    }
                    for r in active_requests
                ]
            }


# Global monitor instance
monitor = ConcurrencyMonitor()


def get_monitor() -> ConcurrencyMonitor:
    """Get the global concurrency monitor instance"""
    return monitor