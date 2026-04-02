from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
from enum import Enum
import time
import logging

from .registry import Provider, provider_registry, ProviderRegistry
from .classifiers import TaskType, classify_task
from .scorer import ProviderScorer, ScoringWeights, ProviderScore
from .quota import QuotaManager, quota_manager, QuotaInfo
from .health import HealthMonitor, health_monitor, ProviderHealth, HealthStatus

logger = logging.getLogger(__name__)


class RouterMode(str, Enum):
    """Different modes of operation for the router"""
    SELECT_BEST = "select_best"      # Select single best provider
    RETURN_FALLBACKS = "return_fallbacks"  # Return ranked list with fallbacks
    HERMES_CONFIG = "hermes_config"  # Return Hermes-compatible config


@dataclass
class RouteRequest:
    """Request to route a task to a provider"""
    prompt: str
    task_type: Optional[TaskType] = None
    max_tokens: Optional[int] = None
    require_tool_calling: bool = False
    require_vision: bool = False
    require_json_mode: bool = False
    preferred_providers: Optional[List[str]] = None
    excluded_providers: Optional[List[str]] = None
    mode: RouterMode = RouterMode.SELECT_BEST
    fallback_count: int = 3  # Number of fallbacks to return


@dataclass
class RouteResult:
    """Result of routing a task to providers"""
    selected_provider: Optional[Provider] = None
    selected_score: Optional[ProviderScore] = None
    fallback_providers: List[Provider] = None
    fallback_scores: List[ProviderScore] = None
    task_type: Optional[TaskType] = None
    reasoning: str = ""
    timestamp: float = 0.0
    
    def __post_init__(self):
        if self.timestamp == 0.0:
            self.timestamp = time.time()
        if self.fallback_providers is None:
            self.fallback_providers = []
        if self.fallback_scores is None:
            self.fallback_scores = []


class RouterEngine:
    """Core routing engine that selects providers based on multiple factors"""
    
    def __init__(self, 
                 weights: Optional[ScoringWeights] = None,
                 registry: Optional[ProviderRegistry] = None,
                 quota_mgr: Optional[QuotaManager] = None,
                 health_mon: Optional[HealthMonitor] = None):
        self.registry = registry or provider_registry
        self.quota_manager = quota_mgr or quota_manager
        self.health_monitor = health_mon or health_monitor
        self.scorer = ProviderScorer(weights)
        
        # Start health monitoring if not already started
        if not self.health_monitor._monitor_thread or not self.health_monitor._monitor_thread.is_alive():
            self.health_monitor.start_monitoring()
    
    def route(self, request: RouteRequest) -> RouteResult:
        """
        Route a task to the best available provider(s).
        
        Args:
            request: The routing request containing task details
            
        Returns:
            RouteResult with selected provider and optional fallbacks
        """
        start_time = time.time()
        
        # Classify task if not explicitly provided
        task_type = request.task_type
        if task_type is None:
            task_type = classify_task(
                request.prompt,
                request.max_tokens,
                request.require_tool_calling,
                request.require_vision,
                request.require_json_mode
            )
        
        logger.info(f"Routing task of type: {task_type.value}")
        
        # Get quota and health data for scoring
        quota_data = self.quota_manager.get_quota_data_for_scoring()
        health_data = self.health_monitor.get_health_data_for_scoring()
        
        # Prepare policy data based on request requirements
        policy_data = self._prepare_policy_data(request)
        
        # Prepare preference data (could come from config/user preferences)
        preference_data = self._prepare_preference_data(request)
        
        # Score all providers
        scored_providers = self.scorer.score_providers(
            task_type, quota_data, health_data, policy_data, preference_data
        )
        
        # Filter providers based on request constraints
        filtered_providers = self._filter_providers(
            scored_providers, request
        )
        
        if not filtered_providers:
            logger.warning("No providers available after filtering")
            return RouteResult(
                task_type=task_type,
                reasoning="No providers available matching the criteria",
                timestamp=start_time
            )
        
        # Prepare result based on mode
        result = RouteResult(task_type=task_type, timestamp=start_time)
        
        if request.mode == RouterMode.SELECT_BEST:
            # Select the single best provider
            best_provider, best_score = filtered_providers[0]
            result.selected_provider = best_provider
            result.selected_score = best_score
            
            # Add fallbacks if requested
            if request.fallback_count > 0 and len(filtered_providers) > 1:
                fallback_limit = min(request.fallback_count, len(filtered_providers) - 1)
                result.fallback_providers = [p for p, _ in filtered_providers[1:1+fallback_limit]]
                result.fallback_scores = [s for _, s in filtered_providers[1:1+fallback_limit]]
            
            result.reasoning = self._generate_reasoning(best_provider, best_score, task_type)
        
        elif request.mode == RouterMode.RETURN_FALLBACKS:
            # Return all scored providers as fallbacks (ordered by score)
            result.fallback_providers = [p for p, _ in filtered_providers]
            result.fallback_scores = [s for _, s in filtered_providers]
            
            # Still select the best as the primary choice
            if filtered_providers:
                best_provider, best_score = filtered_providers[0]
                result.selected_provider = best_provider
                result.selected_score = best_score
                result.reasoning = self._generate_reasoning(best_provider, best_score, task_type)
        
        elif request.mode == RouterMode.HERMES_CONFIG:
            # Return Hermes-compatible configuration
            if filtered_providers:
                best_provider, best_score = filtered_providers[0]
                result.selected_provider = best_provider
                result.selected_score = best_score
                result.reasoning = self._generate_hermes_reasoning(best_provider, best_score, task_type)
                
                # Add fallbacks for Hermes
                if request.fallback_count > 0 and len(filtered_providers) > 1:
                    fallback_limit = min(request.fallback_count, len(filtered_providers) - 1)
                    result.fallback_providers = [p for p, _ in filtered_providers[1:1+fallback_limit]]
                    result.fallback_scores = [s for _, s in filtered_providers[1:1+fallback_limit]]
        
        logger.info(f"Selected provider: {result.selected_provider.name if result.selected_provider else 'None'}")
        return result
    
    def _prepare_policy_data(self, request: RouteRequest) -> Dict[str, Dict]:
        """Prepare policy data based on request requirements"""
        policy_data = {}
        
        # Get all providers to initialize policy data
        providers = self.registry.get_enabled_providers()
        for provider in providers:
            policy_data[provider.id] = {}
        
        # Apply request-based policies
        if request.require_vision:
            for provider_id in policy_data:
                policy_data[provider_id]["require_vision"] = True
        
        if request.require_tool_calling:
            for provider_id in policy_data:
                policy_data[provider_id]["require_tool_calling"] = True
        
        if request.require_json_mode:
            for provider_id in policy_data:
                policy_data[provider_id]["require_json_mode"] = True
        
        # Apply excluded providers
        if request.excluded_providers:
            for provider_id in request.excluded_providers:
                if provider_id in policy_data:
                    policy_data[provider_id]["explicitly_excluded"] = True
        
        return policy_data
    
    def _prepare_preference_data(self, request: RouteRequest) -> Dict[str, Dict]:
        """Prepare preference data based on request"""
        preference_data = {}
        
        # Apply preferred providers boost
        if request.preferred_providers:
            for provider_id in request.preferred_providers:
                if provider_id not in preference_data:
                    preference_data[provider_id] = {}
                preference_data[provider_id]["priority"] = 100  # High priority boost
        
        return preference_data
    
    def _filter_providers(self, 
                         scored_providers: List[Tuple[Provider, ProviderScore]], 
                         request: RouteRequest) -> List[Tuple[Provider, ProviderScore]]:
        """Filter providers based on request constraints"""
        filtered = []
        
        for provider, score in scored_providers:
            # Check if provider is explicitly excluded
            if request.excluded_providers and provider.id in request.excluded_providers:
                continue
            
            # Check if provider is available (considering health/circuit breaker)
            if not self.health_monitor.is_provider_available(provider.id):
                continue
            
            # Check if provider supports required capabilities
            if request.require_vision and provider.capability_scores.get("vision", 0) == 0:
                continue
            
            if request.require_tool_calling and not provider.supports_tool_calling:
                continue
            
            if request.require_json_mode and not provider.supports_json_mode:
                continue
            
            # Check if provider is in preferred list (if specified)
            if request.preferred_providers is not None:
                if provider.id not in request.preferred_providers:
                    continue
            
            filtered.append((provider, score))
        
        return filtered
    
    def _generate_reasoning(self, provider: Provider, score: ProviderScore, task_type: TaskType) -> str:
        """Generate human-readable reasoning for provider selection"""
        reasoning_parts = [
            f"Selected {provider.name} for {task_type.value} task",
            f"Score: {score.total_score:.3f}",
            f"Capabilities: {provider.capability_scores.get(task_type.value, 0)}%",
        ]
        
        if provider.credit_pct is not None:
            reasoning_parts.append(f"Credits: {provider.credit_pct}%")
        else:
            # Estimate from quota data
            quota_info = self.quota_manager.get_quota_info(provider.id)
            if not quota_info.is_unlimited and quota_info.requests_used_today > 0:
                if provider.daily:
                    usage_pct = (quota_info.requests_used_today / provider.daily) * 100
                    remaining = max(0, 100 - usage_pct)
                    reasoning_parts.append(f"Quota: {remaining}% remaining")
                elif provider.daily_extended:
                    usage_pct = (quota_info.requests_used_today / provider.daily_extended) * 100
                    remaining = max(0, 100 - usage_pct)
                    reasoning_parts.append(f"Quota: {remaining}% remaining")
        
        health_info = self.health_monitor.get_provider_health(provider.id)
        if health_info:
            reasoning_parts.append(f"Health: {health_info.status.value}")
        
        return " | ".join(reasoning_parts)
    
    def _generate_hermes_reasoning(self, provider: Provider, score: ProviderScore, task_type: TaskType) -> str:
        """Generate reasoning suitable for Hermes configuration"""
        reasoning_parts = [
            f"{provider.name} selected for {task_type.value}",
            f"Score: {score.total_score:.3f}"
        ]
        
        # Add specific strengths
        capability_pct = provider.capability_scores.get(task_type.value, 0)
        if capability_pct >= 90:
            reasoning_parts.append("Excellent capability match")
        elif capability_pct >= 80:
            reasoning_parts.append("Good capability match")
        elif capability_pct >= 70:
            reasoning_parts.append("Fair capability match")
        
        # Add quota/credit info
        if provider.credit_pct is not None:
            reasoning_parts.append(f"{provider.credit_pct}% credits remaining")
        else:
            quota_info = self.quota_manager.get_quota_info(provider.id)
            if not quota_info.is_unlimited:
                if provider.daily:
                    used = quota_info.requests_used_today
                    remaining = max(0, provider.daily - used)
                    reasoning_parts.append(f"{remaining}/{provider.daily} requests remaining")
                elif provider.daily_extended:
                    used = quota_info.requests_used_today
                    remaining = max(0, provider.daily_extended - used)
                    reasoning_parts.append(f"{remaining}/{provider.daily_extended} requests remaining")
        
        # Add health info
        health_info = self.health_monitor.get_provider_health(provider.id)
        if health_info and health_info.status != HealthStatus.HEALTHY:
            reasoning_parts.append(f"Health: {health_info.status.value}")
        
        return " | ".join(reasoning_parts)
    
    def get_hermes_config(self, provider: Provider) -> Dict[str, Any]:
        """
        Generate Hermes-compatible configuration for a provider.
        
        Returns a dictionary that can be used directly in Hermes config.
        """
        config = {}
        
        if provider.hermes_provider_mode == "native":
            # Native Hermes provider
            config["provider"] = provider.provider or provider.id
            config["model"] = provider.featured_model
        else:
            # Use via Hermes 'main' mode with custom base_url
            config["provider"] = "main"
            config["model"] = provider.featured_model
            config["base_url"] = provider.base_url
            if provider.api_key_env:
                config["api_key_env"] = provider.api_key_env
        
        return config
    
    def get_hermes_fallbacks(self, providers: List[Provider]) -> List[Dict[str, Any]]:
        """
        Generate Hermes-compatible fallback configurations.
        
        Returns a list of fallback configurations for Hermes.
        """
        fallbacks = []
        for provider in providers:
            fallback = self.get_hermes_config(provider)
            fallbacks.append(fallback)
        return fallbacks


# Global router engine instance
router_engine = RouterEngine()