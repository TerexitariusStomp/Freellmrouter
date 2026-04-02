from typing import Dict, List, Optional
from pydantic import BaseModel


class Provider(BaseModel):
    id: str
    name: str
    tier: str
    url: str
    best_for: List[str]
    rpm: Optional[int] = None
    daily: Optional[int] = None
    daily_extended: Optional[int] = None
    models: List[str]
    featured_model: str
    notes: Optional[str] = None
    capability_scores: Dict[str, int]
    credit_pct: Optional[int] = None
    data_training: bool = False
    key_var: str
    hermes_provider_mode: str = "main"  # "native" or "main"
    provider: Optional[str] = None
    base_url: Optional[str] = None
    api_key_env: Optional[str] = None
    rate_limits: Optional[Dict] = None
    free_tier_type: Optional[str] = None
    quota_detection_method: Optional[str] = None
    healthcheck_method: Optional[str] = None
    training_policy: Optional[str] = None
    supports_vision: bool = False
    supports_long_context: bool = False
    supports_tool_calling: bool = False
    supports_json_mode: bool = False
    priority: int = 0
    enabled: bool = True


# Provider registry data from the HTML file
PROVIDERS_DATA = [
    {
        "id": "openrouter",
        "name": "OpenRouter",
        "tier": "free",
        "url": "https://openrouter.ai/api/v1",
        "best_for": ["general", "coding", "reasoning", "vision", "long"],
        "rpm": 20,
        "daily": 50,
        "daily_extended": 1000,
        "models": [
            "deepseek/deepseek-r1:free",
            "meta-llama/llama-3.3-70b-instruct:free",
            "qwen/qwen3-235b-a22b:free",
            "google/gemma-3-27b-it:free"
        ],
        "featured_model": "meta-llama/llama-3.3-70b-instruct:free",
        "notes": "50 req/day free, 1000/day with $10 lifetime topup",
        "capability_scores": {
            "general": 92,
            "coding": 88,
            "reasoning": 95,
            "vision": 80,
            "long": 85,
            "fast": 60
        },
        "credit_pct": None,  # unlimited free tier
        "data_training": False,
        "key_var": "OPENROUTER_API_KEY",
        "hermes_provider_mode": "native",
        "provider": "openrouter",
        "priority": 10
    },
    {
        "id": "google_aistudio",
        "name": "Google AI Studio",
        "tier": "free",
        "url": "https://generativelanguage.googleapis.com/v1beta",
        "best_for": ["long", "general", "vision"],
        "rpm": 15,
        "daily": 1500,
        "models": [
            "gemini-2.0-flash",
            "gemini-2.0-flash-lite",
            "gemini-1.5-flash"
        ],
        "featured_model": "gemini-2.0-flash",
        "notes": "Up to 1500 req/day on Flash-Lite. Data used for training outside EEA.",
        "capability_scores": {
            "general": 90,
            "coding": 82,
            "reasoning": 88,
            "vision": 91,
            "long": 95,
            "fast": 85
        },
        "credit_pct": None,
        "data_training": True,
        "key_var": "GOOGLE_AI_STUDIO_KEY",
        "hermes_provider_mode": "main",
        "provider": "main",
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai",
        "api_key_env": "GOOGLE_AI_STUDIO_KEY",
        "priority": 9
    },
    {
        "id": "groq",
        "name": "Groq",
        "tier": "free",
        "url": "https://api.groq.com/openai/v1",
        "best_for": ["fast", "general", "coding"],
        "rpm": 30,
        "daily": 14400,
        "models": [
            "llama-3.3-70b-versatile",
            "llama-3.1-8b-instant",
            "gemma2-9b-it",
            "qwen-qwq-32b"
        ],
        "featured_model": "llama-3.3-70b-versatile",
        "notes": "Very high daily req. Context limited on free. Fastest inference.",
        "capability_scores": {
            "general": 87,
            "coding": 84,
            "reasoning": 82,
            "vision": 0,
            "long": 65,
            "fast": 99
        },
        "credit_pct": None,
        "data_training": False,
        "key_var": "GROQ_API_KEY",
        "hermes_provider_mode": "main",
        "provider": "main",
        "base_url": "https://api.groq.com/openai/v1",
        "api_key_env": "GROQ_API_KEY",
        "priority": 8
    },
    {
        "id": "cerebras",
        "name": "Cerebras",
        "tier": "free",
        "url": "https://api.cerebras.ai/v1",
        "best_for": ["fast", "general"],
        "rpm": 30,
        "daily": 14400,
        "models": [
            "llama-3.3-70b",
            "llama3.1-8b",
            "qwen-3-32b"
        ],
        "featured_model": "llama-3.3-70b",
        "notes": "8K context on free tier. Very fast wafer-scale hardware.",
        "capability_scores": {
            "general": 86,
            "coding": 80,
            "reasoning": 80,
            "vision": 0,
            "long": 40,
            "fast": 98
        },
        "credit_pct": None,
        "data_training": False,
        "key_var": "CEREBRAS_API_KEY",
        "hermes_provider_mode": "main",
        "provider": "main",
        "base_url": "https://api.cerebras.ai/v1",
        "api_key_env": "CEREBRAS_API_KEY",
        "priority": 7
    },
    {
        "id": "mistral",
        "name": "Mistral La Plateforme",
        "tier": "free",
        "url": "https://api.mistral.ai/v1",
        "best_for": ["coding", "general"],
        "rpm": 60,
        "daily": None,
        "models": [
            "mistral-small-latest",
            "open-mistral-nemo",
            "open-codestral-mamba"
        ],
        "featured_model": "mistral-small-latest",
        "notes": "Requires data training opt-in + phone verification.",
        "capability_scores": {
            "general": 85,
            "coding": 90,
            "reasoning": 82,
            "vision": 0,
            "long": 78,
            "fast": 75
        },
        "credit_pct": None,
        "data_training": True,
        "key_var": "MISTRAL_API_KEY",
        "hermes_provider_mode": "main",
        "provider": "main",
        "base_url": "https://api.mistral.ai/v1",
        "api_key_env": "MISTRAL_API_KEY",
        "priority": 6
    },
    {
        "id": "cohere",
        "name": "Cohere",
        "tier": "free",
        "url": "https://api.cohere.com/v1",
        "best_for": ["general", "long"],
        "rpm": 20,
        "daily": 1000,
        "models": [
            "command-a",
            "command-r-plus",
            "command-r"
        ],
        "featured_model": "command-a",
        "notes": "1000 req/month shared quota.",
        "capability_scores": {
            "general": 83,
            "coding": 72,
            "reasoning": 78,
            "vision": 0,
            "long": 88,
            "fast": 70
        },
        "credit_pct": None,
        "data_training": False,
        "key_var": "COHERE_API_KEY",
        "hermes_provider_mode": "main",
        "provider": "main",
        "base_url": "https://api.cohere.com/v1",
        "api_key_env": "COHERE_API_KEY",
        "priority": 5
    },
    {
        "id": "cloudflare",
        "name": "Cloudflare Workers AI",
        "tier": "free",
        "url": "https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/run",
        "best_for": ["fast", "general"],
        "rpm": None,
        "daily": None,
        "models": [
            "@cf/meta/llama-3.3-70b-instruct-fp8-fast",
            "@cf/qwen/qwq-32b",
            "@cf/mistral/mistral-small-3.1-24b-instruct"
        ],
        "featured_model": "@cf/meta/llama-3.3-70b-instruct-fp8-fast",
        "notes": "10,000 neurons/day. Edge deployment, global low latency.",
        "capability_scores": {
            "general": 80,
            "coding": 78,
            "reasoning": 76,
            "vision": 72,
            "long": 60,
            "fast": 92
        },
        "credit_pct": None,
        "data_training": False,
        "key_var": "CF_API_TOKEN",
        "hermes_provider_mode": "main",
        "provider": "main",
        "base_url": "https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/run",
        "api_key_env": "CF_API_TOKEN",
        "priority": 4
    },
    {
        "id": "together",
        "name": "Together AI (Trial)",
        "tier": "trial",
        "url": "https://api.together.xyz/v1",
        "best_for": ["general", "coding", "reasoning"],
        "rpm": 60,
        "daily": None,
        "models": [
            "meta-llama/Llama-3.3-70B-Instruct-Turbo",
            "deepseek-ai/DeepSeek-R1",
            "mistralai/Mistral-7B-Instruct-v0.2"
        ],
        "featured_model": "meta-llama/Llama-3.3-70B-Instruct-Turbo",
        "notes": "$1 credit when payment method added.",
        "capability_scores": {
            "general": 89,
            "coding": 87,
            "reasoning": 90,
            "vision": 75,
            "long": 82,
            "fast": 78
        },
        "credit_pct": 72,
        "data_training": False,
        "key_var": "TOGETHER_API_KEY",
        "hermes_provider_mode": "main",
        "provider": "main",
        "base_url": "https://api.together.xyz/v1",
        "api_key_env": "TOGETHER_API_KEY",
        "priority": 3
    },
    {
        "id": "github_models",
        "name": "GitHub Models",
        "tier": "free",
        "url": "https://models.inference.ai.azure.com",
        "best_for": ["general", "coding", "reasoning"],
        "rpm": None,
        "daily": None,
        "models": [
            "gpt-4o",
            "meta/Llama-3.3-70B-Instruct",
            "deepseek/DeepSeek-R1",
            "openai/o3-mini"
        ],
        "featured_model": "gpt-4o",
        "notes": "Limits depend on Copilot tier. Very restrictive token limits.",
        "capability_scores": {
            "general": 93,
            "coding": 93,
            "reasoning": 94,
            "vision": 88,
            "long": 78,
            "fast": 72
        },
        "credit_pct": None,
        "data_training": False,
        "key_var": "GITHUB_TOKEN",
        "hermes_provider_mode": "main",
        "provider": "main",
        "base_url": "https://models.inference.ai.azure.com",
        "api_key_env": "GITHUB_TOKEN",
        "priority": 2
    },
    {
        "id": "huggingface",
        "name": "HuggingFace Inference",
        "tier": "free",
        "url": "https://api-inference.huggingface.co/models",
        "best_for": ["general"],
        "rpm": None,
        "daily": None,
        "models": [
            "meta-llama/Llama-3.1-70B-Instruct",
            "mistralai/Mistral-7B-Instruct-v0.3"
        ],
        "featured_model": "meta-llama/Llama-3.1-70B-Instruct",
        "notes": "$0.10/month in free credits. <10GB models only (some exceptions).",
        "capability_scores": {
            "general": 78,
            "coding": 74,
            "reasoning": 72,
            "vision": 60,
            "long": 68,
            "fast": 55
        },
        "credit_pct": 85,
        "data_training": False,
        "key_var": "HUGGINGFACE_API_KEY",
        "hermes_provider_mode": "main",
        "provider": "main",
        "base_url": "https://api-inference.huggingface.co/models",
        "api_key_env": "HUGGINGFACE_API_KEY",
        "priority": 1
    },
    {
        "id": "hyperbolic",
        "name": "Hyperbolic",
        "tier": "trial",
        "url": "https://api.hyperbolic.xyz/v1",
        "best_for": ["coding", "reasoning", "general"],
        "rpm": None,
        "daily": None,
        "models": [
            "deepseek-ai/DeepSeek-V3-0324",
            "meta-llama/Llama-3.1-405B-Instruct",
            "Qwen/QwQ-32B"
        ],
        "featured_model": "deepseek-ai/DeepSeek-V3-0324",
        "notes": "$1 trial credit.",
        "capability_scores": {
            "general": 88,
            "coding": 90,
            "reasoning": 91,
            "vision": 70,
            "long": 80,
            "fast": 70
        },
        "credit_pct": 45,
        "data_training": False,
        "key_var": "HYPERBOLIC_API_KEY",
        "hermes_provider_mode": "main",
        "provider": "main",
        "base_url": "https://api.hyperbolic.xyz/v1",
        "api_key_env": "HYPERBOLIC_API_KEY",
        "priority": 0
    },
    {
        "id": "sambanova",
        "name": "SambaNova Cloud",
        "tier": "trial",
        "url": "https://api.sambanova.ai/v1",
        "best_for": ["reasoning", "general"],
        "rpm": None,
        "daily": None,
        "models": [
            "Meta-Llama-3.3-70B-Instruct",
            "Llama-4-Maverick-17B-128E-Instruct",
            "DeepSeek-R1-0528"
        ],
        "featured_model": "Meta-Llama-3.3-70B-Instruct",
        "notes": "$5 credit for 3 months.",
        "capability_scores": {
            "general": 86,
            "coding": 82,
            "reasoning": 89,
            "vision": 0,
            "long": 80,
            "fast": 82
        },
        "credit_pct": 60,
        "data_training": False,
        "key_var": "SAMBANOVA_API_KEY",
        "hermes_provider_mode": "main",
        "provider": "main",
        "base_url": "https://api.sambanova.ai/v1",
        "api_key_env": "SAMBANOVA_API_KEY",
        "priority": -1
    },
    {
        "id": "puter",
        "name": "Puter",
        "tier": "free",
        "url": "https://api.puter.com/puterai/openai/v1",
        "best_for": ["general", "coding", "reasoning", "vision", "long", "fast"],
        "rpm": 60,
        "daily": None,
        "models": [
            "openai/gpt-5-nano",
            "openai/gpt-4o",
            "anthropic/claude-sonnet-4-5",
            "google/gemini-3-pro-preview",
            "deepseek/deepseek-r1",
            "x-ai/grok-4.20-beta",
            "meta-llama/llama-4-maverick",
            "mistralai/mistral-small-2603"
        ],
        "featured_model": "openai/gpt-5-nano",
        "notes": "500+ models via single token. User-pays model. No separate provider keys needed.",
        "capability_scores": {
            "general": 98,
            "coding": 95,
            "reasoning": 97,
            "vision": 95,
            "long": 96,
            "fast": 90
        },
        "credit_pct": None,
        "data_training": False,
        "key_var": "PUTER_AUTH_TOKEN",
        "hermes_provider_mode": "main",
        "provider": "main",
        "base_url": "https://api.puter.com/puterai/openai/v1",
        "api_key_env": "PUTER_AUTH_TOKEN",
        "priority": 100
    },
    {
        "id": "kluster",
        "name": "Kluster",
        "tier": "free",
        "url": "https://api.kluster.ai/v1",
        "best_for": ["general", "coding", "reasoning"],
        "rpm": 30,
        "daily": None,
        "models": ["kluster-sonnet", "kluster-flash"],
        "featured_model": "kluster-sonnet",
        "notes": "Free tier via CLI auth.",
        "capability_scores": {
            "general": 82,
            "coding": 80,
            "reasoning": 78,
            "vision": 60,
            "long": 70,
            "fast": 75
        },
        "credit_pct": None,
        "data_training": False,
        "key_var": "KLUSTER_API_KEY",
        "hermes_provider_mode": "main",
        "provider": "main",
        "base_url": "https://api.kluster.ai/v1",
        "api_key_env": "KLUSTER_API_KEY",
        "priority": 5
    },
    {
        "id": "llm7",
        "name": "LLM7",
        "tier": "free",
        "url": "https://api.llm7.io/v1",
        "best_for": ["general", "coding"],
        "rpm": 20,
        "daily": None,
        "models": ["llm7-pro", "llm7-lite"],
        "featured_model": "llm7-pro",
        "notes": "Free tier via token authentication.",
        "capability_scores": {
            "general": 78,
            "coding": 76,
            "reasoning": 74,
            "vision": 50,
            "long": 65,
            "fast": 70
        },
        "credit_pct": None,
        "data_training": False,
        "key_var": "LLM7_API_KEY",
        "hermes_provider_mode": "main",
        "provider": "main",
        "base_url": "https://api.llm7.io/v1",
        "api_key_env": "LLM7_API_KEY",
        "priority": 4
    },
    {
        "id": "pollinations",
        "name": "Pollinations",
        "tier": "free",
        "url": "https://text.pollinations.ai/openai",
        "best_for": ["general", "fast"],
        "rpm": 30,
        "daily": None,
        "models": ["openai", "claude", "gemini"],
        "featured_model": "openai",
        "notes": "No API key required. Completely free.",
        "capability_scores": {
            "general": 75,
            "coding": 70,
            "reasoning": 72,
            "vision": 60,
            "long": 60,
            "fast": 85
        },
        "credit_pct": None,
        "data_training": False,
        "key_var": "POLLINATIONS_API_KEY",
        "hermes_provider_mode": "main",
        "provider": "main",
        "base_url": "https://text.pollinations.ai/openai",
        "api_key_env": "POLLINATIONS_API_KEY",
        "priority": 3
    },
    {
        "id": "airforce",
        "name": "Airforce",
        "tier": "free",
        "url": "https://api.airforce/v1",
        "best_for": ["general", "coding"],
        "rpm": 20,
        "daily": None,
        "models": ["gpt-4o", "claude-sonnet", "gemini-pro"],
        "featured_model": "gpt-4o",
        "notes": "Free tier via API key.",
        "capability_scores": {
            "general": 80,
            "coding": 78,
            "reasoning": 76,
            "vision": 70,
            "long": 65,
            "fast": 72
        },
        "credit_pct": None,
        "data_training": False,
        "key_var": "AIRFORCE_API_KEY",
        "hermes_provider_mode": "main",
        "provider": "main",
        "base_url": "https://api.airforce/v1",
        "api_key_env": "AIRFORCE_API_KEY",
        "priority": 2
    },
    {
        "id": "runwayml",
        "name": "RunwayML",
        "tier": "free",
        "url": "https://api.runwayml.com/v1",
        "best_for": ["vision", "general"],
        "rpm": 10,
        "daily": None,
        "models": ["runway-gen3", "runway-gen4"],
        "featured_model": "runway-gen4",
        "notes": "Free tier with limited credits.",
        "capability_scores": {
            "general": 70,
            "coding": 60,
            "reasoning": 65,
            "vision": 90,
            "long": 55,
            "fast": 60
        },
        "credit_pct": None,
        "data_training": False,
        "key_var": "RUNWAYML_API_KEY",
        "hermes_provider_mode": "main",
        "provider": "main",
        "base_url": "https://api.runwayml.com/v1",
        "api_key_env": "RUNWAYML_API_KEY",
        "priority": 1
    },
    {
        "id": "ollama_cloud",
        "name": "Ollama Cloud",
        "tier": "free",
        "url": "https://ollama.com/api/v1",
        "best_for": ["general", "coding"],
        "rpm": 30,
        "daily": None,
        "models": ["llama3.3:70b", "qwen2.5:72b", "deepseek-r1:70b"],
        "featured_model": "llama3.3:70b",
        "notes": "Free cloud-hosted Ollama instances.",
        "capability_scores": {
            "general": 82,
            "coding": 80,
            "reasoning": 78,
            "vision": 65,
            "long": 75,
            "fast": 70
        },
        "credit_pct": None,
        "data_training": False,
        "key_var": "OLLAMA_API_KEY",
        "hermes_provider_mode": "main",
        "provider": "main",
        "base_url": "https://ollama.com/api/v1",
        "api_key_env": "OLLAMA_API_KEY",
        "priority": 1
    },
    {
        "id": "lobehub",
        "name": "LobeHub",
        "tier": "free",
        "url": "https://api.lobehub.com/v1",
        "best_for": ["general", "coding"],
        "rpm": 20,
        "daily": None,
        "models": ["gpt-4o", "claude-sonnet", "gemini-pro"],
        "featured_model": "gpt-4o",
        "notes": "Free tier via API key.",
        "capability_scores": {
            "general": 78,
            "coding": 76,
            "reasoning": 74,
            "vision": 68,
            "long": 65,
            "fast": 70
        },
        "credit_pct": None,
        "data_training": False,
        "key_var": "LOBEHUB_API_KEY",
        "hermes_provider_mode": "main",
        "provider": "main",
        "base_url": "https://api.lobehub.com/v1",
        "api_key_env": "LOBEHUB_API_KEY",
        "priority": 0
    },
    {
        "id": "poe",
        "name": "Poe",
        "tier": "free",
        "url": "https://api.poe.com/v1",
        "best_for": ["general", "reasoning"],
        "rpm": 20,
        "daily": None,
        "models": ["claude-sonnet-4-5", "gpt-5-nano", "gemini-pro"],
        "featured_model": "claude-sonnet-4-5",
        "notes": "Free tier with daily limits.",
        "capability_scores": {
            "general": 85,
            "coding": 80,
            "reasoning": 88,
            "vision": 75,
            "long": 70,
            "fast": 72
        },
        "credit_pct": None,
        "data_training": False,
        "key_var": "POE_API_KEY",
        "hermes_provider_mode": "main",
        "provider": "main",
        "base_url": "https://api.poe.com/v1",
        "api_key_env": "POE_API_KEY",
        "priority": 0
    },
    {
        "id": "ibm",
        "name": "IBM watsonx",
        "tier": "free",
        "url": "https://us-south.ml.cloud.ibm.com",
        "best_for": ["general", "reasoning"],
        "rpm": 20,
        "daily": None,
        "models": ["ibm/granite-3-8b-instruct", "ibm/granite-34b-code-instruct"],
        "featured_model": "ibm/granite-34b-code-instruct",
        "notes": "Free tier via IBM Cloud API key.",
        "capability_scores": {
            "general": 75,
            "coding": 78,
            "reasoning": 74,
            "vision": 50,
            "long": 70,
            "fast": 65
        },
        "credit_pct": None,
        "data_training": False,
        "key_var": "IBM_API_KEY",
        "hermes_provider_mode": "main",
        "provider": "main",
        "base_url": "https://us-south.ml.cloud.ibm.com",
        "api_key_env": "IBM_API_KEY",
        "priority": -1
    },
    {
        "id": "fireworks",
        "name": "Fireworks AI",
        "tier": "free",
        "url": "https://api.fireworks.ai/inference/v1",
        "best_for": ["general", "coding", "reasoning"],
        "rpm": 30,
        "daily": None,
        "models": ["accounts/fireworks/models/llama-v3p3-70b-instruct", "accounts/fireworks/models/deepseek-r1"],
        "featured_model": "accounts/fireworks/models/llama-v3p3-70b-instruct",
        "notes": "Free tier with generous limits.",
        "capability_scores": {
            "general": 84,
            "coding": 82,
            "reasoning": 80,
            "vision": 65,
            "long": 75,
            "fast": 78
        },
        "credit_pct": None,
        "data_training": False,
        "key_var": "FIREWORKS_API_KEY",
        "hermes_provider_mode": "main",
        "provider": "main",
        "base_url": "https://api.fireworks.ai/inference/v1",
        "api_key_env": "FIREWORKS_API_KEY",
        "priority": -1
    },
    {
        "id": "vercel",
        "name": "Vercel AI Gateway",
        "tier": "free",
        "url": "https://gateway.vercel.com/openai",
        "best_for": ["general", "coding"],
        "rpm": 30,
        "daily": None,
        "models": ["gpt-4o", "claude-sonnet", "gemini-pro"],
        "featured_model": "gpt-4o",
        "notes": "Free tier via Vercel AI Gateway.",
        "capability_scores": {
            "general": 82,
            "coding": 80,
            "reasoning": 78,
            "vision": 72,
            "long": 68,
            "fast": 75
        },
        "credit_pct": None,
        "data_training": False,
        "key_var": "VERCEL_AI_KEY",
        "hermes_provider_mode": "main",
        "provider": "main",
        "base_url": "https://gateway.vercel.com/openai",
        "api_key_env": "VERCEL_AI_KEY",
        "priority": -1
    },
    {
        "id": "aimlapi",
        "name": "AIMLAPI",
        "tier": "free",
        "url": "https://api.aimlapi.com/v1",
        "best_for": ["general", "coding"],
        "rpm": 20,
        "daily": None,
        "models": ["gpt-4o", "claude-sonnet", "gemini-pro"],
        "featured_model": "gpt-4o",
        "notes": "Free tier via API key.",
        "capability_scores": {
            "general": 78,
            "coding": 76,
            "reasoning": 74,
            "vision": 68,
            "long": 65,
            "fast": 70
        },
        "credit_pct": None,
        "data_training": False,
        "key_var": "AIMLAPI_API_KEY",
        "hermes_provider_mode": "main",
        "provider": "main",
        "base_url": "https://api.aimlapi.com/v1",
        "api_key_env": "AIMLAPI_API_KEY",
        "priority": -2
    },
    {
        "id": "arcee",
        "name": "Arcee AI",
        "tier": "free",
        "url": "https://chat.arcee.ai/api/v1",
        "best_for": ["general", "coding"],
        "rpm": 20,
        "daily": None,
        "models": ["arcee-pro", "arcee-lite"],
        "featured_model": "arcee-pro",
        "notes": "Free tier via API key.",
        "capability_scores": {
            "general": 76,
            "coding": 74,
            "reasoning": 72,
            "vision": 60,
            "long": 65,
            "fast": 68
        },
        "credit_pct": None,
        "data_training": False,
        "key_var": "ARCEE_API_KEY",
        "hermes_provider_mode": "main",
        "provider": "main",
        "base_url": "https://chat.arcee.ai/api/v1",
        "api_key_env": "ARCEE_API_KEY",
        "priority": -2
    },
    {
        "id": "minimax",
        "name": "MiniMax",
        "tier": "free",
        "url": "https://api.minimax.io/v1",
        "best_for": ["general", "coding"],
        "rpm": 20,
        "daily": None,
        "models": ["MiniMax-Text-01", "MiniMax-VL-01"],
        "featured_model": "MiniMax-Text-01",
        "notes": "Free tier with generous limits.",
        "capability_scores": {
            "general": 78,
            "coding": 76,
            "reasoning": 74,
            "vision": 70,
            "long": 68,
            "fast": 72
        },
        "credit_pct": None,
        "data_training": False,
        "key_var": "MINIMAX_API_KEY",
        "hermes_provider_mode": "main",
        "provider": "main",
        "base_url": "https://api.minimax.io/v1",
        "api_key_env": "MINIMAX_API_KEY",
        "priority": -2
    },
    {
        "id": "stepfun",
        "name": "Stepfun",
        "tier": "free",
        "url": "https://api.stepfun.com/v1",
        "best_for": ["general", "reasoning"],
        "rpm": 20,
        "daily": None,
        "models": ["step-1", "step-1v"],
        "featured_model": "step-1",
        "notes": "Free tier via API key.",
        "capability_scores": {
            "general": 76,
            "coding": 72,
            "reasoning": 78,
            "vision": 68,
            "long": 65,
            "fast": 70
        },
        "credit_pct": None,
        "data_training": False,
        "key_var": "STEPFUN_API_KEY",
        "hermes_provider_mode": "main",
        "provider": "main",
        "base_url": "https://api.stepfun.com/v1",
        "api_key_env": "STEPFUN_API_KEY",
        "priority": -3
    },
    {
        "id": "zai",
        "name": "Z.AI",
        "tier": "free",
        "url": "https://api.z.ai/v1",
        "best_for": ["general", "coding"],
        "rpm": 20,
        "daily": None,
        "models": ["glm-4-plus", "glm-4-flash"],
        "featured_model": "glm-4-plus",
        "notes": "Free tier via API key.",
        "capability_scores": {
            "general": 76,
            "coding": 74,
            "reasoning": 72,
            "vision": 65,
            "long": 68,
            "fast": 70
        },
        "credit_pct": None,
        "data_training": False,
        "key_var": "ZAI_API_KEY",
        "hermes_provider_mode": "main",
        "provider": "main",
        "base_url": "https://api.z.ai/v1",
        "api_key_env": "ZAI_API_KEY",
        "priority": -3
    }
]


class ProviderRegistry:
    def __init__(self):
        self.providers: Dict[str, Provider] = {}
        self._load_providers()
    
    def _load_providers(self):
        """Load providers from the hardcoded data"""
        for provider_data in PROVIDERS_DATA:
            provider = Provider(**provider_data)
            self.providers[provider.id] = provider
    
    def get_provider(self, provider_id: str) -> Optional[Provider]:
        """Get a provider by ID"""
        return self.providers.get(provider_id)
    
    def get_enabled_providers(self) -> List[Provider]:
        """Get all enabled providers"""
        return [p for p in self.providers.values() if p.enabled]
    
    def get_providers_by_capability(self, capability: str) -> List[Provider]:
        """Get providers that support a specific capability"""
        return [
            p for p in self.providers.values() 
            if p.enabled and p.capability_scores.get(capability, 0) > 0
        ]
    
    def get_hermes_native_providers(self) -> List[Provider]:
        """Get providers that Hermes supports natively"""
        return [
            p for p in self.providers.values() 
            if p.enabled and p.hermes_provider_mode == "native"
        ]
    
    def get_hermes_main_providers(self) -> List[Provider]:
        """Get providers that need to be used via Hermes 'main' mode"""
        return [
            p for p in self.providers.values() 
            if p.enabled and p.hermes_provider_mode == "main"
        ]


# Global registry instance
provider_registry = ProviderRegistry()