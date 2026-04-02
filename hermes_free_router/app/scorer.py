from typing import Dict, List, Optional, Tuple
from .registry import Provider, provider_registry
from .classifiers import TaskType
import math


class ScoringWeights:
    """Configurable weights for the scoring system"""
    def __init__(self, 
                 credit_weight: float = 0.4,
                 capability_weight: float = 0.35,
                 speed_weight: float = 0.25,
                 health_weight: float = 0.0,
                 policy_weight: float = 0.0,
                 preference_weight: float = 0.0):
        self.credit_weight = credit_weight
        self.capability_weight = capability_weight
        self.speed_weight = speed_weight
        self.health_weight = health_weight
        self.policy_weight = policy_weight
        self.preference_weight = preference_weight
    
    def normalize(self):
        """Normalize weights so they sum to 1.0"""
        total = self.credit_weight + self.capability_weight + self.speed_weight + \
                self.health_weight + self.policy_weight + self.preference_weight
        if total > 0:
            self.credit_weight /= total
            self.capability_weight /= total
            self.speed_weight /= total
            self.health_weight /= total
            self.policy_weight /= total
            self.preference_weight /= total


class ProviderScore:
    """Score for a provider based on various factors"""
    def __init__(self, provider: Provider):
        self.provider = provider
        self.credit_score = 0.0
        self.capability_score = 0.0
        self.speed_score = 0.0
        self.health_score = 0.0
        self.policy_score = 0.0
        self.preference_score = 0.0
        self.total_score = 0.0
        self.details = {}
    
    def to_dict(self) -> Dict:
        """Convert score to dictionary for serialization"""
        return {
            "provider_id": self.provider.id,
            "provider_name": self.provider.name,
            "credit_score": self.credit_score,
            "capability_score": self.capability_score,
            "speed_score": self.speed_score,
            "health_score": self.health_score,
            "policy_score": self.policy_score,
            "preference_score": self.preference_score,
            "total_score": self.total_score,
            "details": self.details
        }


class ProviderScorer:
    """Scores providers based on multiple factors"""
    
    def __init__(self, weights: Optional[ScoringWeights] = None):
        self.weights = weights or ScoringWeights()
        self.weights.normalize()
    
    def score_provider(self, 
                      provider: Provider, 
                      task_type: TaskType,
                      quota_data: Optional[Dict] = None,
                      health_data: Optional[Dict] = None,
                      policy_data: Optional[Dict] = None,
                      preference_data: Optional[Dict] = None) -> ProviderScore:
        """
        Score a provider for a given task type.
        
        Args:
            provider: The provider to score
            task_type: The type of task being performed
            quota_data: Optional quota/credit data for the provider
            health_data: Optional health data for the provider
            policy_data: Optional policy compliance data
            preference_data: Optional manual preference data
            
        Returns:
            ProviderScore object with all scoring components
        """
        score = ProviderScore(provider)
        
        # Credit/quota score
        score.credit_score = self._calculate_credit_score(provider, quota_data)
        score.details["credit_score"] = score.credit_score
        
        # Capability score
        score.capability_score = self._calculate_capability_score(provider, task_type)
        score.details["capability_score"] = score.capability_score
        
        # Speed score (based on RPM)
        score.speed_score = self._calculate_speed_score(provider)
        score.details["speed_score"] = score.speed_score
        
        # Health score
        score.health_score = self._calculate_health_score(provider, health_data)
        score.details["health_score"] = score.health_score
        
        # Policy score
        score.policy_score = self._calculate_policy_score(provider, policy_data)
        score.details["policy_score"] = score.policy_score
        
        # Preference score (manual priority boost)
        score.preference_score = self._calculate_preference_score(provider, preference_data)
        score.details["preference_score"] = score.preference_score
        
        # Calculate weighted total score
        score.total_score = (
            score.credit_score * self.weights.credit_weight +
            score.capability_score * self.weights.capability_weight +
            score.speed_score * self.weights.speed_weight +
            score.health_score * self.weights.health_weight +
            score.policy_score * self.weights.policy_weight +
            score.preference_score * self.weights.preference_weight
        )
        
        return score
    
    def _calculate_credit_score(self, provider: Provider, quota_data: Optional[Dict]) -> float:
        """
        Calculate credit score based on remaining credits/quota.
        
        Returns a value between 0.0 and 1.0 where:
        - 1.0 = full quota/credits available
        - 0.0 = no quota/credits available
        """
        # If provider has explicit credit percentage
        if provider.credit_pct is not None:
            return provider.credit_pct / 100.0
        
        # If provider has daily limit and we have usage data
        if provider.daily is not None and quota_data:
            provider_id = provider.id
            if provider_id in quota_data:
                used = quota_data[provider_id].get("requests_used", 0)
                daily_limit = provider.daily
                if daily_limit > 0:
                    remaining_ratio = max(0.0, 1.0 - (used / daily_limit))
                    return remaining_ratio
        
        # If provider has daily extended limit and we have usage data
        if provider.daily_extended is not None and quota_data:
            provider_id = provider.id
            if provider_id in quota_data:
                used = quota_data[provider_id].get("requests_used", 0)
                daily_limit = provider.daily_extended
                if daily_limit > 0:
                    remaining_ratio = max(0.0, 1.0 - (used / daily_limit))
                    return remaining_ratio
        
        # Default to high score for providers with unknown/unlimited quota
        # In practice, this would be adjusted based on actual usage tracking
        return 0.8  # Conservative default
    
    def _calculate_capability_score(self, provider: Provider, task_type: TaskType) -> float:
        """
        Calculate capability score based on provider's strength for the task type.
        
        Returns a value between 0.0 and 1.0 where:
        - 1.0 = excellent capability for this task type
        - 0.0 = no capability for this task type
        """
        capability_map = {
            TaskType.GENERAL: "general",
            TaskType.CODING: "coding",
            TaskType.REASONING: "reasoning",
            TaskType.VISION: "vision",
            TaskType.LONG_CONTEXT: "long",
            TaskType.FAST: "fast"
        }
        
        capability_key = capability_map[task_type]
        raw_score = provider.capability_scores.get(capability_key, 0)
        return raw_score / 100.0  # Convert from percentage to ratio
    
    def _calculate_speed_score(self, provider: Provider) -> float:
        """
        Calculate speed score based on provider's RPM (requests per minute).
        
        Returns a value between 0.0 and 1.0 where:
        - 1.0 = highest speed among providers
        - 0.0 = lowest speed among providers
        """
        if provider.rpm is None:
            return 0.5  # Neutral score for unknown speed
        
        # Normalize RPM score (assuming max RPM of ~100 for normalization)
        # In practice, we might want to dynamically calculate this based on all providers
        max_rpm = 100  # Assumed maximum RPM for normalization
        return min(1.0, provider.rpm / max_rpm)
    
    def _calculate_health_score(self, provider: Provider, health_data: Optional[Dict]) -> float:
        """
        Calculate health score based on provider's current health status.
        
        Returns a value between 0.0 and 1.0 where:
        - 1.0 = fully healthy
        - 0.0 = completely unhealthy/unavailable
        """
        if not health_data:
            return 1.0  # Assume healthy if no health data provided
        
        provider_id = provider.id
        if provider_id not in health_data:
            return 1.0  # Assume healthy if no data for this provider
        
        provider_health = health_data[provider_id]
        
        # Check for recent failures
        consecutive_failures = provider_health.get("consecutive_failures", 0)
        if consecutive_failures >= 3:
            return 0.0  # Completely unhealthy after 3+ consecutive failures
        elif consecutive_failures == 2:
            return 0.3  # Poor health after 2 failures
        elif consecutive_failures == 1:
            return 0.6  # Degraded health after 1 failure
        
        # Check last healthcheck result
        last_check = provider_health.get("last_healthcheck_result", True)
        if not last_check:
            return 0.2  # Unhealthy based on last check
        
        # Check for rate limiting
        last_429_time = provider_health.get("last_429_time")
        if last_429_time:
            # In a real implementation, we'd check how recent this was
            # For now, we'll penalize somewhat
            return 0.5
        
        return 1.0  # Fully healthy
    
    def _calculate_policy_score(self, provider: Provider, policy_data: Optional[Dict]) -> float:
        """
        Calculate policy score based on provider's compliance with policies.
        
        Returns a value between 0.0 and 1.0 where:
        - 1.0 = fully compliant with all policies
        - 0.0 = violates important policies
        """
        if not policy_data:
            return 1.0  # Assume compliant if no policy data
        
        provider_id = provider.id
        if provider_id not in policy_data:
            return 1.0  # Assume compliant if no data for this provider
        
        provider_policy = policy_data[provider_id]
        score = 1.0
        
        # Check data training policy
        if provider_policy.get("exclude_data_training", False) and provider.data_training:
            score *= 0.0  # Completely exclude if policy says to avoid data training providers
        
        # Check open-weight models preference
        if provider_policy.get("prefer_open_weight", False):
            # In a real implementation, we'd check if the model is open-weight
            # For now, we'll assume some providers are open-weight
            open_weight_providers = {"openrouter", "groq", "cerebras", "mistral", "together", "github_models", "huggingface", "hyperbolic", "sambanova"}
            if provider.id in open_weight_providers:
                score *= 1.2  # Boost for open-weight models
            else:
                score *= 0.8  # Slight penalty for non-open-weight
        
        # Check vision requirement
        if provider_policy.get("require_vision", False) and provider.capability_scores.get("vision", 0) == 0:
            score *= 0.0  # Exclude if vision required but not supported
        
        # Check long context requirement
        if provider_policy.get("require_long_context", False) and provider.capability_scores.get("long", 0) < 50:
            score *= 0.0  # Exclude if long context required but insufficient
        
        # Check tool calling requirement
        if provider_policy.get("require_tool_calling", False) and not provider.supports_tool_calling:
            score *= 0.0  # Exclude if tool calling required but not supported
        
        # Check JSON mode requirement
        if provider_policy.get("require_json_mode", False) and not provider.supports_json_mode:
            score *= 0.0  # Exclude if JSON mode required but not supported
        
        # Ensure score stays in bounds
        return max(0.0, min(1.0, score))
    
    def _calculate_preference_score(self, provider: Provider, preference_data: Optional[Dict]) -> float:
        """
        Calculate preference score based on manual preferences/priorities.
        
        Returns a value where higher values indicate stronger preference.
        """
        if not preference_data:
            return float(provider.priority)  # Use built-in priority
        
        provider_id = provider.id
        if provider_id not in preference_data:
            return float(provider.priority)  # Use built-in priority if no override
        
        # Return the preference value, defaulting to built-in preference if not specified
        return preference_data[provider_id].get("priority", float(provider.priority))
    
    def score_providers(self, 
                       task_type: TaskType,
                       quota_data: Optional[Dict] = None,
                       health_data: Optional[Dict] = None,
                       policy_data: Optional[Dict] = None,
                       preference_data: Optional[Dict] = None) -> List[Tuple[Provider, ProviderScore]]:
        """
        Score all enabled providers for a given task type.
        
        Returns:
            List of (provider, score) tuples sorted by score descending
        """
        enabled_providers = provider_registry.get_enabled_providers()
        scored_providers = []
        
        for provider in enabled_providers:
            score = self.score_provider(
                provider, task_type, quota_data, health_data, policy_data, preference_data
            )
            scored_providers.append((provider, score))
        
        # Sort by total score descending
        scored_providers.sort(key=lambda x: x[1].total_score, reverse=True)
        return scored_providers