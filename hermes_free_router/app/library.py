"""
Python library interface for the Hermes Free Router.

This module provides a simple Python interface that can be imported and used
by Hermes Agent or other applications to select the best LLM provider/model
for a given task.
"""

from typing import Dict, List, Optional, Union
from dataclasses import asdict

from .router import RouterEngine, RouteRequest, RouteResult, RouterMode
from .classifiers import TaskType
from .registry import Provider
from .scorer import ProviderScore


class HermesFreeRouter:
    """
    Main interface for the Hermes Free Router Python library.
    
    Example usage:
        >>> router = HermesFreeRouter()
        >>> choice = router.select_model(
        ...     prompt="Write a Python function to calculate fibonacci numbers",
        ...     task_type="coding",
        ...     require_tool_calling=False
        ... )
        >>> print(choice)
        {
            "provider": "groq",
            "model": "llama-3.3-70b-versatile",
            "reason": "Groq selected for speed and available free quota",
            "score": 0.89
        }
    """
    
    def __init__(self):
        """Initialize the router with default components."""
        self.router = RouterEngine()
    
    def select_model(self, 
                    prompt: str,
                    task_type: Optional[str] = None,
                    max_tokens: Optional[int] = None,
                    require_tool_calling: bool = False,
                    require_vision: bool = False,
                    require_json_mode: bool = False,
                    preferred_providers: Optional[List[str]] = None,
                    excluded_providers: Optional[List[str]] = None,
                    fallback_count: int = 3) -> Dict:
        """
        Select the best model/provider for a given task.
        
        Args:
            prompt: The user's prompt/input
            task_type: Type of task (general, coding, reasoning, vision, long, fast)
                      If None, will be auto-detected from prompt
            max_tokens: Maximum tokens requested (for long context detection)
            require_tool_calling: Whether tool calling is required
            require_vision: Whether vision capabilities are required
            require_json_mode: Whether JSON mode output is required
            preferred_providers: List of preferred provider IDs (will be boosted in priority)
            excluded_providers: List of provider IDs to exclude from consideration
            fallback_count: Number of fallback options to include in result
            
        Returns:
            Dictionary containing the selected provider information and optional fallbacks
            in a format compatible with Hermes Agent
        """
        # Convert task_type string to enum if provided
        task_type_enum = None
        if task_type:
            try:
                task_type_enum = TaskType(task_type.lower())
            except ValueError:
                # If invalid task type, we'll let the classifier handle it
                pass
        
        # Create route request
        request = RouteRequest(
            prompt=prompt,
            task_type=task_type_enum,
            max_tokens=max_tokens,
            require_tool_calling=require_tool_calling,
            require_vision=require_vision,
            require_json_mode=require_json_mode,
            preferred_providers=preferred_providers,
            excluded_providers=excluded_providers,
            fallback_count=fallback_count,
            mode=RouterMode.HERMES_CONFIG  # We want Hermes-compatible output
        )
        
        # Perform routing
        result = self.router.route(request)
        
        # Format result for Hermes compatibility
        if result.selected_provider is None:
            # No provider available
            return {
                "provider": None,
                "model": None,
                "reason": result.reasoning or "No suitable provider available",
                "score": 0.0,
                "fallbacks": []
            }
        
        # Get Hermes-compatible config for selected provider
        selected_config = self.router.get_hermes_config(result.selected_provider)
        
        # Add reasoning and score
        selected_config["reason"] = result.reasoning or f"Selected {result.selected_provider.name} for {result.task_type.value if result.task_type else 'general'} task"
        selected_config["score"] = result.selected_score.total_score if result.selected_score else 0.0
        
        # Get fallbacks
        fallbacks = []
        if result.fallback_providers and result.fallback_scores:
            hermes_fallbacks = self.router.get_hermes_fallbacks(result.fallback_providers)
            for i, fallback_config in enumerate(hermes_fallbacks):
                fallback_config["reason"] = result.fallback_scores[i].details.get("reason", "") if hasattr(result.fallback_scores[i], 'details') and result.fallback_scores[i].details else f"Fallback option {i+1}"
                fallback_config["score"] = result.fallback_scores[i].total_score
                fallbacks.append(fallback_config)
        
        # Construct final result
        response = {
            "provider": selected_config.get("provider"),
            "model": selected_config.get("model"),
            "reason": selected_config.get("reason"),
            "score": selected_config.get("score", 0.0)
        }
        
        # Add base_url and api_key_env if using main provider mode
        if "base_url" in selected_config:
            response["base_url"] = selected_config["base_url"]
        if "api_key_env" in selected_config:
            response["api_key_env"] = selected_config["api_key_env"]
        
        # Add fallbacks if any
        if fallbacks:
            response["fallbacks"] = fallbacks
        
        return response
    
    def get_provider_info(self, provider_id: str) -> Optional[Dict]:
        """
        Get detailed information about a specific provider.
        
        Args:
            provider_id: The ID of the provider to get information for
            
        Returns:
            Dictionary with provider information or None if not found
        """
        from .registry import provider_registry
        
        provider = provider_registry.get_provider(provider_id)
        if provider is None:
            return None
        
        return {
            "id": provider.id,
            "name": provider.name,
            "tier": provider.tier,
            "url": provider.url,
            "best_for": provider.best_for,
            "rpm": provider.rpm,
            "daily": provider.daily,
            "models": provider.models,
            "featured_model": provider.featured_model,
            "capability_scores": provider.capability_scores,
            "hermes_provider_mode": provider.hermes_provider_mode,
            "supports_vision": provider.supports_vision,
            "supports_long_context": provider.supports_long_context,
            "supports_tool_calling": provider.supports_tool_calling,
            "supports_json_mode": provider.supports_json_mode,
            "priority": provider.priority,
            "enabled": provider.enabled
        }
    
    def list_providers(self, enabled_only: bool = True) -> List[Dict]:
        """
        List all available providers.
        
        Args:
            enabled_only: If True, only return enabled providers
            
        Returns:
            List of provider information dictionaries
        """
        from .registry import provider_registry
        
        if enabled_only:
            providers = provider_registry.get_enabled_providers()
        else:
            providers = list(provider_registry.providers.values())
        
        return [self.get_provider_info(p.id) for p in providers if p is not None]
    
    def get_usage_stats(self) -> Dict:
        """
        Get usage statistics for all providers.
        
        Returns:
            Dictionary with usage statistics
        """
        return self.router.quota_manager.get_usage_stats()
    
    def health_check(self, provider_id: Optional[str] = None) -> Dict:
        """
        Perform health check on providers.
        
        Args:
            provider_id: If provided, check only this provider; otherwise check all
            
        Returns:
            Dictionary with health check results
        """
        if provider_id:
            result = self.router.health_monitor.force_health_check(provider_id)
            return {
                "provider_id": result.provider_id,
                "status": result.status.value,
                "response_time": result.response_time,
                "status_code": result.status_code,
                "error_message": result.error_message,
                "timestamp": result.timestamp
            }
        else:
            # Return health status for all providers
            health_data = self.router.health_monitor.get_health_data_for_scoring()
            return {
                provider_id: {
                    "status": data["status"],
                    "is_available": data["is_available"],
                    "consecutive_failures": data["consecutive_failures"],
                    "circuit_breaker_state": data["circuit_breaker_state"]
                }
                for provider_id, data in health_data.items()
            }


# Convenience function for simple usage
def select_model(prompt: str, 
                task_type: Optional[str] = None,
                **kwargs) -> Dict:
    """
    Convenience function to select a model using the default router instance.
    
    Args:
        prompt: The user's prompt/input
        task_type: Type of task (general, coding, reasoning, vision, long, fast)
        **kwargs: Additional arguments passed to HermesFreeRouter.select_model()
        
    Returns:
        Dictionary containing the selected provider information
    """
    router = HermesFreeRouter()
    return router.select_model(prompt, task_type, **kwargs)


if __name__ == "__main__":
    # Simple CLI for testing the library
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python library.py <prompt> [--task-type TYPE]")
        print("Example: python library.py 'Write a Python function to calculate fibonacci' --task-type coding")
        sys.exit(1)
    
    prompt = sys.argv[1]
    task_type = None
    
    # Parse simple command line arguments
    i = 2
    while i < len(sys.argv):
        if sys.argv[i] == "--task-type" and i + 1 < len(sys.argv):
            task_type = sys.argv[i + 1]
            i += 2
        else:
            i += 1
    
    result = select_model(prompt, task_type)
    import json
    print(json.dumps(result, indent=2))