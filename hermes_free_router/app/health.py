import time
import threading
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum
from .registry import Provider
import logging

logger = logging.getLogger(__name__)


class HealthStatus(Enum):
    """Health status of a provider"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class HealthCheckResult:
    """Result of a health check for a provider"""
    provider_id: str
    status: HealthStatus
    response_time: float = 0.0
    status_code: Optional[int] = None
    error_message: Optional[str] = None
    timestamp: float = 0.0
    
    def __post_init__(self):
        if self.timestamp == 0.0:
            self.timestamp = time.time()


class CircuitBreakerState(Enum):
    """States of the circuit breaker"""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, requests blocked
    HALF_OPEN = "half_open"  # Testing if service recovered


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker"""
    failure_threshold: int = 5          # Number of failures to open circuit
    recovery_timeout: int = 60          # Seconds to wait before trying half-open
    expected_exception: tuple = ()      # Exceptions that count as failures
    success_threshold: int = 3          # Successes needed to close from half-open


@dataclass
class ProviderHealth:
    """Health information for a provider"""
    provider_id: str
    status: HealthStatus = HealthStatus.UNKNOWN
    last_check_time: float = 0.0
    last_check_result: Optional[HealthCheckResult] = None
    consecutive_failures: int = 0
    consecutive_successes: int = 0
    total_requests: int = 0
    failed_requests: int = 0
    average_response_time: float = 0.0
    circuit_breaker_state: CircuitBreakerState = CircuitBreakerState.CLOSED
    circuit_breaker_failures: int = 0
    circuit_breaker_last_failure_time: float = 0.0
    circuit_breaker_success_count: int = 0


class HealthMonitor:
    """Monitors provider health and implements circuit breaker pattern"""
    
    def __init__(self, check_interval: int = 30):
        self.check_interval = check_interval  # seconds
        self.providers_health: Dict[str, ProviderHealth] = {}
        self._monitor_thread: Optional[threading.Thread] = None
        self._stop_monitoring = threading.Event()
        self._lock = threading.Lock()
        
        # Initialize health status for known providers
        self._initialize_provider_health()
    
    def _initialize_provider_health(self):
        """Initialize health status for all known providers"""
        from .registry import provider_registry
        
        providers = provider_registry.get_enabled_providers()
        for provider in providers:
            if provider.id not in self.providers_health:
                self.providers_health[provider.id] = ProviderHealth(
                    provider_id=provider.id,
                    status=HealthStatus.UNKNOWN
                )
    
    def start_monitoring(self):
        """Start the health monitoring thread"""
        if self._monitor_thread is None or not self._monitor_thread.is_alive():
            self._stop_monitoring.clear()
            self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
            self._monitor_thread.start()
            logger.info("Started health monitoring thread")
    
    def stop_monitoring(self):
        """Stop the health monitoring thread"""
        self._stop_monitoring.set()
        if self._monitor_thread and self._monitor_thread.is_alive():
            self._monitor_thread.join(timeout=5.0)
            logger.info("Stopped health monitoring thread")
    
    def _monitor_loop(self):
        """Main monitoring loop"""
        while not self._stop_monitoring.is_set():
            try:
                self._perform_health_checks()
                self._stop_monitoring.wait(self.check_interval)
            except Exception as e:
                logger.error(f"Error in health monitoring loop: {e}")
                self._stop_monitoring.wait(5.0)  # Wait a bit before retrying
    
    def _perform_health_checks(self):
        """Perform health checks on all providers"""
        from .registry import provider_registry
        
        providers = provider_registry.get_enabled_providers()
        for provider in providers:
            try:
                result = self._check_provider_health(provider)
                self._update_health_status(provider.id, result)
            except Exception as e:
                logger.error(f"Health check failed for provider {provider.id}: {e}")
                # Create a failed health check result
                result = HealthCheckResult(
                    provider_id=provider.id,
                    status=HealthStatus.UNHEALTHY,
                    error_message=str(e)
                )
                self._update_health_status(provider.id, result)
    
    def _check_provider_health(self, provider) -> HealthCheckResult:
        """
        Perform a health check on a single provider.
        In a real implementation, this would make an actual HTTP request.
        For now, we'll simulate based on existing data.
        """
        start_time = time.time()
        
        # Get recent quota data to inform health status
        from .quota import quota_manager
        quota_info = quota_manager.get_quota_info(provider.id)
        
        # Simulate health check based on quota and recent failures
        response_time = time.time() - start_time
        
        # Determine health status based on various factors
        if quota_info.consecutive_failures >= 3:
            status = HealthStatus.UNHEALTHY
            error_msg = f"Provider has {quota_info.consecutive_failures} consecutive failures"
        elif quota_info.consecutive_failures >= 1:
            status = HealthStatus.DEGRADED
            error_msg = f"Provider has {quota_info.consecutive_failures} recent failures"
        elif quota_info.last_429_time > 0:
            # Check if 429 was recent (within last 5 minutes)
            time_since_429 = time.time() - quota_info.last_429_time
            if time_since_429 < 300:  # 5 minutes
                status = HealthStatus.DEGRADED
                error_msg = "Provider recently rate limited (429)"
            else:
                status = HealthStatus.HEALTHY
                error_msg = None
        else:
            status = HealthStatus.HEALTHY
            error_msg = None
        
        return HealthCheckResult(
            provider_id=provider.id,
            status=status,
            response_time=response_time,
            error_message=error_msg
        )
    
    def _update_health_status(self, provider_id: str, result: HealthCheckResult):
        """Update health status for a provider based on check result"""
        with self._lock:
            if provider_id not in self.providers_health:
                self.providers_health[provider_id] = ProviderHealth(provider_id=provider_id)
            
            health = self.providers_health[provider_id]
            health.last_check_time = result.timestamp
            health.last_check_result = result
            
            # Update failure/success counters
            if result.status == HealthStatus.HEALTHY:
                health.consecutive_successes += 1
                health.consecutive_failures = 0
            else:
                health.consecutive_failures += 1
                health.consecutive_successes = 0
            
            # Update overall status
            health.status = result.status
            
            # Update response time (rolling average)
            if health.average_response_time == 0.0:
                health.average_response_time = result.response_time
            else:
                # Exponential moving average
                health.average_response_time = (0.7 * health.average_response_time) + (0.3 * result.response_time)
            
            # Update circuit breaker state
            self._update_circuit_breaker(health, result)
            
            logger.debug(f"Updated health for {provider_id}: {health.status.value} "
                        f"(failures: {health.consecutive_failures}, "
                        f"circuit: {health.circuit_breaker_state.value})")
    
    def _update_circuit_breaker(self, health: ProviderHealth, result: HealthCheckResult):
        """Update circuit breaker state based on health check result"""
        config = CircuitBreakerConfig()  # Use default config
        
        if health.circuit_breaker_state == CircuitBreakerState.OPEN:
            # Check if we should try half-open
            time_since_failure = time.time() - health.circuit_breaker_last_failure_time
            if time_since_failure >= config.recovery_timeout:
                health.circuit_breaker_state = CircuitBreakerState.HALF_OPEN
                health.circuit_breaker_success_count = 0
                logger.info(f"Circuit breaker for {health.provider_id} moved to HALF_OPEN")
        
        elif health.circuit_breaker_state == CircuitBreakerState.HALF_OPEN:
            if result.status == HealthStatus.HEALTHY:
                health.circuit_breaker_success_count += 1
                if health.circuit_breaker_success_count >= config.success_threshold:
                    health.circuit_breaker_state = CircuitBreakerState.CLOSED
                    health.circuit_breaker_failures = 0
                    logger.info(f"Circuit breaker for {health.provider_id} moved to CLOSED")
            else:
                # Failed during half-open, go back to open
                health.circuit_breaker_state = CircuitBreakerState.OPEN
                health.circuit_breaker_failures += 1
                health.circuit_breaker_last_failure_time = time.time()
                logger.warning(f"Circuit breaker for {health.provider_id} moved back to OPEN")
        
        elif health.circuit_breaker_state == CircuitBreakerState.CLOSED:
            if result.status != HealthStatus.HEALTHY:
                health.circuit_breaker_failures += 1
                if health.circuit_breaker_failures >= config.failure_threshold:
                    health.circuit_breaker_state = CircuitBreakerState.OPEN
                    health.circuit_breaker_last_failure_time = time.time()
                    logger.warning(f"Circuit breaker for {health.provider_id} moved to OPEN")
    
    def get_provider_health(self, provider_id: str) -> Optional[ProviderHealth]:
        """Get health information for a provider"""
        with self._lock:
            return self.providers_health.get(provider_id)
    
    def is_provider_available(self, provider_id: str) -> bool:
        """Check if a provider is available for use (considering circuit breaker)"""
        health = self.get_provider_health(provider_id)
        if not health:
            return True  # Unknown providers are considered available by default
        
        # Check circuit breaker state
        if health.circuit_breaker_state == CircuitBreakerState.OPEN:
            return False
        
        # Consider degraded providers as available but with lower priority
        return health.status in [HealthStatus.HEALTHY, HealthStatus.DEGRADED]
    
    def get_health_data_for_scoring(self) -> Dict[str, Dict]:
        """Get health data formatted for the scoring system"""
        health_data = {}
        with self._lock:
            for provider_id, health in self.providers_health.items():
                health_data[provider_id] = {
                    "status": health.status.value,
                    "consecutive_failures": health.consecutive_failures,
                    "last_healthcheck_result": health.last_check_result.status.value if health.last_check_result else None,
                    "average_response_time": health.average_response_time,
                    "circuit_breaker_state": health.circuit_breaker_state.value,
                    "is_available": self.is_provider_available(provider_id)
                }
        return health_data
    
    def force_health_check(self, provider_id: str) -> HealthCheckResult:
        """Force an immediate health check for a specific provider"""
        from .registry import provider_registry
        
        provider = provider_registry.get_provider(provider_id)
        if not provider:
            raise ValueError(f"Unknown provider: {provider_id}")
        
        if not provider.enabled:
            return HealthCheckResult(
                provider_id=provider_id,
                status=HealthStatus.UNHEALTHY,
                error_message="Provider is disabled"
            )
        
        result = self._check_provider_health(provider)
        self._update_health_status(provider_id, result)
        return result


# Global health monitor instance
health_monitor = HealthMonitor()