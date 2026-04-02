"""
Command-line interface for the Hermes Free Router.

This module provides a CLI that can be used to select the best LLM provider/model
for a given task, with output formatted for easy consumption by Hermes Agent.
"""

import typer
import json
from typing import Optional, List
from enum import Enum

from .library import HermesFreeRouter, select_model
from .classifiers import TaskType


app = typer.Typer(
    name="hermes-free-router",
    help="Hermes Free LLM Router - Select the best free LLM provider for your task",
    add_completion=False,
)


class TaskTypeEnum(str, Enum):
    """Task types for CLI argument validation"""
    GENERAL = "general"
    CODING = "coding"
    REASONING = "reasoning"
    VISION = "vision"
    LONG = "long"
    FAST = "fast"


@app.command()
def pick(
    prompt: str = typer.Argument(..., help="The prompt to route"),
    task_type: Optional[TaskTypeEnum] = typer.Option(
        None, "--task-type", "-t", help="Type of task (general, coding, reasoning, vision, long, fast)"
    ),
    max_tokens: Optional[int] = typer.Option(
        None, "--max-tokens", "-m", help="Maximum tokens requested"
    ),
    require_tool_calling: bool = typer.Option(
        False, "--tool-calling", help="Require tool calling capability"
    ),
    require_vision: bool = typer.Option(
        False, "--vision", help="Require vision capability"
    ),
    require_json_mode: bool = typer.Option(
        False, "--json-mode", help="Require JSON mode capability"
    ),
    preferred_providers: Optional[List[str]] = typer.Option(
        None, "--preferred", "-p", help="Preferred provider IDs (can be used multiple times)"
    ),
    excluded_providers: Optional[List[str]] = typer.Option(
        None, "--excluded", "-e", help="Excluded provider IDs (can be used multiple times)"
    ),
    fallback_count: int = typer.Option(
        3, "--fallback-count", "-f", help="Number of fallback options to include"
    ),
    json_output: bool = typer.Option(
        True, "--json/--no-json", help="Output as JSON (default) or human-readable format"
    ),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Verbose output"
    )
):
    """
    Pick the best LLM provider/model for a given prompt.
    
    Examples:
        hermes-free-router pick "Write a Python function to calculate fibonacci numbers" --task-type coding
        hermes-free-router pick "Explain quantum entanglement" --task-type reasoning --json
        hermes-free-router pick "What's in this image?" --task-type vision --require-vision
    """
    try:
        # Convert task_type enum to string if provided
        task_type_str = task_type.value if task_type else None
        
        # Call the router
        result = select_model(
            prompt=prompt,
            task_type=task_type_str,
            max_tokens=max_tokens,
            require_tool_calling=require_tool_calling,
            require_vision=require_vision,
            require_json_mode=require_json_mode,
            preferred_providers=preferred_providers,
            excluded_providers=excluded_providers,
            fallback_count=fallback_count
        )
        
        if json_output:
            # Output as JSON
            typer.echo(json.dumps(result, indent=2))
        else:
            # Output as human-readable format
            if result.get("provider"):
                typer.echo(f"Selected Provider: {result.get('provider')}")
                typer.echo(f"Model: {result.get('model')}")
                typer.echo(f"Reason: {result.get('reason')}")
                typer.echo(f"Score: {result.get('score')}")
                
                if "base_url" in result:
                    typer.echo(f"Base URL: {result['base_url']}")
                if "api_key_env" in result:
                    typer.echo(f"API Key Env: {result['api_key_env']}")
                
                if result.get("fallbacks"):
                    typer.echo("\nFallbacks:")
                    for i, fallback in enumerate(result["fallbacks"], 1):
                        typer.echo(f"  {i}. {fallback.get('provider')} - {fallback.get('model')} "
                                 f"(score: {fallback.get('score')})")
            else:
                typer.echo(f"Error: {result.get('reason', 'No suitable provider available')}")
                raise typer.Exit(code=1)
    
    except Exception as e:
        typer.echo(f"Error: {str(e)}", err=True)
        raise typer.Exit(code=1)


@app.command()
def providers(
    enabled_only: bool = typer.Option(
        True, "--enabled-only/--all", help="Show only enabled providers (default) or all providers"
    ),
    json_output: bool = typer.Option(
        False, "--json", help="Output as JSON"
    )
):
    """
    List all available providers.
    """
    try:
        router = HermesFreeRouter()
        providers_list = router.list_providers(enabled_only=enabled_only)
        
        if json_output:
            typer.echo(json.dumps(providers_list, indent=2))
        else:
            if not providers_list:
                typer.echo("No providers found.")
                return
            
            typer.echo(f"{'Enabled' if enabled_only else 'All'} Providers:")
            typer.echo("-" * 80)
            
            for provider in providers_list:
                status = "✓" if provider.get("enabled") else "✗"
                typer.echo(f"{status} {provider.get('name')} ({provider.get('id')})")
                typer.echo(f"    Best for: {', '.join(provider.get('best_for', []))}")
                typer.echo(f"    Featured model: {provider.get('featured_model')}")
                typer.echo(f"    RPM: {provider.get('rpm') or 'N/A'}")
                typer.echo(f"    Daily quota: {provider.get('daily') or 'N/A'}")
                typer.echo("")
    
    except Exception as e:
        typer.echo(f"Error: {str(e)}", err=True)
        raise typer.Exit(code=1)


@app.command()
def stats(
    json_output: bool = typer.Option(
        False, "--json", help="Output as JSON"
    )
):
    """
    Show usage statistics for all providers.
    """
    try:
        router = HermesFreeRouter()
        stats = router.get_usage_stats()
        
        if json_output:
            typer.echo(json.dumps(stats, indent=2))
        else:
            typer.echo("Usage Statistics:")
            typer.echo("-" * 40)
            typer.echo(f"Total requests today: {stats.get('total_requests_today', 0)}")
            typer.echo(f"Total tokens today: {stats.get('total_tokens_today', 0)}")
            typer.echo("")
            
            provider_stats = stats.get("provider_stats", [])
            if provider_stats:
                typer.echo("Provider Breakdown:")
                for provider_stat in provider_stats:
                    typer.echo(f"  {provider_stat.get('provider_id')}: "
                             f"{provider_stat.get('requests_used_today', 0)} requests, "
                             f"{provider_stat.get('tokens_used_today', 0)} tokens, "
                             f"{provider_stat.get('estimated_credit_remaining', 0):.2%} credit remaining")
    
    except Exception as e:
        typer.echo(f"Error: {str(e)}", err=True)
        raise typer.Exit(code=1)


@app.command()
def health(
    provider_id: Optional[str] = typer.Option(
        None, "--provider", "-p", help="Check specific provider ID (default: all providers)"
    ),
    json_output: bool = typer.Option(
        False, "--json", help="Output as JSON"
    )
):
    """
    Check health status of providers.
    """
    try:
        router = HermesFreeRouter()
        health_data = router.health_check(provider_id=provider_id)
        
        if json_output:
            typer.echo(json.dumps(health_data, indent=2))
        else:
            if provider_id:
                # Single provider output
                typer.echo(f"Health check for provider: {provider_id}")
                typer.echo("-" * 40)
                typer.echo(f"Status: {health_data.get('status')}")
                typer.echo(f"Response time: {health_data.get('response_time', 0):.2f}s")
                if health_data.get('status_code'):
                    typer.echo(f"Status code: {health_data.get('status_code')}")
                if health_data.get('error_message'):
                    typer.echo(f"Error: {health_data.get('error_message')}")
                typer.echo(f"Timestamp: {health_data.get('timestamp')}")
            else:
                # All providers output
                typer.echo("Provider Health Status:")
                typer.echo("-" * 80)
                
                for pid, data in health_data.items():
                    status_icon = {
                        "healthy": "✓",
                        "degraded": "⚠",
                        "unhealthy": "✗",
                        "unknown": "?"
                    }.get(data.get("status", "unknown"), "?")
                    
                    availability = "✓ Available" if data.get("is_available") else "✗ Unavailable"
                    typer.echo(f"{status_icon} {pid}: {data.get('status')} | {availability} | "
                             f"Failures: {data.get('consecutive_failures')} | "
                             f"Circuit: {data.get('circuit_breaker_state')}")
    
    except Exception as e:
        typer.echo(f"Error: {str(e)}", err=True)
        raise typer.Exit(code=1)


@app.command()
def version():
    """
    Show version information.
    """
    typer.echo("Hermes Free Router v0.1.0")


if __name__ == "__main__":
    app()