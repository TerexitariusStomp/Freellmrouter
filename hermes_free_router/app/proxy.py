"""
OpenAI-compatible proxy server for the Hermes Free Router.

Routes requests to the best free LLM provider. Puter is the primary provider
(500+ models via single token), with fallbacks to 21 other free providers.
"""

from typing import Dict, Any, Optional, List
import json
import logging
import os
import time
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Header, Request
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel
import httpx

load_dotenv()

logger = logging.getLogger(__name__)

app = FastAPI(
    title="FreeRouter Proxy",
    description="OpenAI-compatible proxy that routes requests to free LLM providers",
    version="0.2.0"
)


class ProviderConfig:
    def __init__(self, name: str, base_url: str, api_key: str,
                 models: List[str], featured_model: str, priority: int = 0,
                 headers: Optional[Dict[str, str]] = None):
        self.name = name
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.models = models
        self.featured_model = featured_model
        self.priority = priority
        self.extra_headers = headers or {}


PROVIDERS: List[ProviderConfig] = []

def _add(name, base_url, key, models, featured, priority=0, headers=None):
    if key:
        PROVIDERS.append(ProviderConfig(name, base_url, key, models, featured, priority, headers))

# =====================================================================
# ALL 22 PROVIDERS
# =====================================================================

# 1. Puter — PRIMARY: 500+ models, single token, user-pays model
_add("puter", "https://api.puter.com/puterai/openai/v1",
     os.getenv("PUTER_AUTH_TOKEN", ""),
     ["openai/gpt-5-nano","openai/gpt-4o","openai/gpt-5.4-nano",
      "anthropic/claude-sonnet-4-5","anthropic/claude-sonnet-4-6",
      "google/gemini-3-pro-preview","google/gemini-3.1-pro-preview",
      "deepseek/deepseek-r1","x-ai/grok-4.20-beta",
      "meta-llama/llama-4-maverick","mistralai/mistral-small-2603",
      "openai/o3-mini","openai/o4-mini"],
     "openai/gpt-5-nano", priority=100)

# 2. OpenRouter — free tier models
_add("openrouter", "https://openrouter.ai/api/v1",
     os.getenv("OPENROUTER_API_KEY", ""),
     ["meta-llama/llama-3.3-70b-instruct:free","google/gemma-3-27b-it:free",
      "qwen/qwen3-235b-a22b:free","deepseek/deepseek-r1:free"],
     "meta-llama/llama-3.3-70b-instruct:free", priority=90)

# 3. Google AI Studio
_add("google_aistudio", "https://generativelanguage.googleapis.com/v1beta/openai",
     os.getenv("GOOGLE_AI_STUDIO_KEY", ""),
     ["gemini-2.0-flash","gemini-2.0-flash-lite","gemini-1.5-flash"],
     "gemini-2.0-flash", priority=85)

# 4. Groq — fastest inference
_add("groq", "https://api.groq.com/openai/v1",
     os.getenv("GROQ_API_KEY", ""),
     ["llama-3.3-70b-versatile","llama-3.1-8b-instant","gemma2-9b-it","qwen-qwq-32b"],
     "llama-3.3-70b-versatile", priority=80)

# 5. Cerebras — wafer-scale speed
_add("cerebras", "https://api.cerebras.ai/v1",
     os.getenv("CEREBRAS_API_KEY", ""),
     ["llama-3.3-70b","llama3.1-8b","qwen-3-32b"],
     "llama-3.3-70b", priority=75)

# 6. Mistral
_add("mistral", "https://api.mistral.ai/v1",
     os.getenv("MISTRAL_API_KEY", ""),
     ["mistral-small-latest","open-mistral-nemo","open-codestral-mamba"],
     "mistral-small-latest", priority=70)

# 7. Cohere
_add("cohere", "https://api.cohere.com/compatibility/v1",
     os.getenv("COHERE_API_KEY", ""),
     ["command-r-plus","command-r","command-a"],
     "command-r-plus", priority=65)

# 8. Cloudflare Workers AI
_add("cloudflare", "https://api.cloudflare.com/client/v4/accounts",
     os.getenv("CF_API_TOKEN", ""),
     ["@cf/meta/llama-3.3-70b-instruct-fp8-fast","@cf/qwen/qwq-32b"],
     "@cf/meta/llama-3.3-70b-instruct-fp8-fast", priority=60)

# 9. Together AI
_add("together", "https://api.together.xyz/v1",
     os.getenv("TOGETHER_API_KEY", ""),
     ["meta-llama/Llama-3.3-70B-Instruct-Turbo","deepseek-ai/DeepSeek-R1"],
     "meta-llama/Llama-3.3-70B-Instruct-Turbo", priority=55)

# 10. Fireworks AI
_add("fireworks", "https://api.fireworks.ai/inference/v1",
     os.getenv("FIREWORKS_API_KEY", ""),
     ["accounts/fireworks/models/llama-v3p3-70b-instruct",
      "accounts/fireworks/models/deepseek-r1"],
     "accounts/fireworks/models/llama-v3p3-70b-instruct", priority=50)

# 11. Vercel AI Gateway
_add("vercel", "https://gateway.vercel.com/openai",
     os.getenv("VERCEL_AI_KEY", ""),
     ["gpt-4o","claude-sonnet-4-5","gemini-2.0-flash"],
     "gpt-4o", priority=48)

# 12. Kluster
_add("kluster", "https://api.kluster.ai/v1",
     os.getenv("KLUSTER_API_KEY", ""),
     ["kluster-sonnet","kluster-flash"],
     "kluster-sonnet", priority=45)

# 13. LLM7
_add("llm7", "https://api.llm7.io/v1",
     os.getenv("LLM7_API_KEY", ""),
     ["llm7-pro","llm7-lite"],
     "llm7-pro", priority=42)

# 14. Pollinations — no key needed, OpenAI-compatible endpoint
_add("pollinations", "https://text.pollinations.ai/openai",
     os.getenv("POLLINATIONS_API_KEY", "no-key-needed"),
     ["openai","claude","gemini"],
     "openai", priority=40)

# 15. Airforce
_add("airforce", "https://api.airforce/v1",
     os.getenv("AIRFORCE_API_KEY", ""),
     ["gpt-4o","claude-sonnet","gemini-pro"],
     "gpt-4o", priority=38)

# 16. RunwayML
_add("runwayml", "https://api.runwayml.com/v1",
     os.getenv("RUNWAYML_API_KEY", ""),
     ["runway-gen4","runway-gen3"],
     "runway-gen4", priority=35)

# 17. Ollama Cloud
_add("ollama_cloud", "https://ollama.com/api/v1",
     os.getenv("OLLAMA_API_KEY", ""),
     ["llama3.3:70b","qwen2.5:72b","deepseek-r1:70b"],
     "llama3.3:70b", priority=32)

# 18. LobeHub
_add("lobehub", "https://api.lobehub.com/v1",
     os.getenv("LOBEHUB_API_KEY", ""),
     ["gpt-4o","claude-sonnet-4-5","gemini-2.0-flash"],
     "gpt-4o", priority=30)

# 19. Poe
_add("poe", "https://api.poe.com/v1",
     os.getenv("POE_API_KEY", ""),
     ["claude-sonnet-4-5","gpt-5-nano","gemini-2.0-flash"],
     "claude-sonnet-4-5", priority=28)

# 20. IBM watsonx
_add("ibm", "https://us-south.ml.cloud.ibm.com/m1/v1",
     os.getenv("IBM_API_KEY", ""),
     ["ibm/granite-34b-code-instruct","ibm/granite-3-8b-instruct"],
     "ibm/granite-34b-code-instruct", priority=25)

# 21. AIMLAPI
_add("aimlapi", "https://api.aimlapi.com/v1",
     os.getenv("AIMLAPI_API_KEY", ""),
     ["gpt-4o","claude-sonnet-4-5","gemini-2.0-flash"],
     "gpt-4o", priority=22)

# 22. Arcee AI
_add("arcee", "https://chat.arcee.ai/api/v1",
     os.getenv("ARCEE_API_KEY", ""),
     ["arcee-pro","arcee-lite"],
     "arcee-pro", priority=20)

# 23. MiniMax
_add("minimax", "https://api.minimax.io/v1",
     os.getenv("MINIMAX_API_KEY", ""),
     ["MiniMax-Text-01","MiniMax-VL-01"],
     "MiniMax-Text-01", priority=18)

# 24. Stepfun
_add("stepfun", "https://api.stepfun.com/v1",
     os.getenv("STEPFUN_API_KEY", ""),
     ["step-1","step-1v"],
     "step-1", priority=15)

# 25. Z.AI
_add("zai", "https://api.z.ai/v1",
     os.getenv("ZAI_API_KEY", ""),
     ["glm-4-plus","glm-4-flash"],
     "glm-4-plus", priority=12)

# Sort by priority descending
PROVIDERS.sort(key=lambda p: p.priority, reverse=True)

# Track failures per provider
FAILURE_COUNT: Dict[str, int] = {}
COOLDOWN_UNTIL: Dict[str, float] = {}


def get_available_providers() -> List[ProviderConfig]:
    now = time.time()
    return [p for p in PROVIDERS if not (p.name in COOLDOWN_UNTIL and now < COOLDOWN_UNTIL[p.name])]


def record_failure(provider_name: str):
    FAILURE_COUNT[provider_name] = FAILURE_COUNT.get(provider_name, 0) + 1
    COOLDOWN_UNTIL[provider_name] = time.time() + 60


def record_success(provider_name: str):
    FAILURE_COUNT[provider_name] = 0
    COOLDOWN_UNTIL.pop(provider_name, None)


# ---- OpenAI-compatible models ----

class ChatMessage(BaseModel):
    role: str
    content: Any


class ChatCompletionRequest(BaseModel):
    model: str = "auto"
    messages: List[ChatMessage]
    max_tokens: Optional[int] = None
    temperature: Optional[float] = None
    top_p: Optional[float] = None
    n: int = 1
    stream: bool = False
    stop: Optional[Any] = None
    presence_penalty: Optional[float] = None
    frequency_penalty: Optional[float] = None
    tools: Optional[List[Dict]] = None
    tool_choice: Optional[Any] = None


# ---- Endpoints ----

@app.get("/health")
async def health_check():
    available = get_available_providers()
    return {
        "status": "healthy",
        "providers_total": len(PROVIDERS),
        "providers_available": len(available),
        "provider_names": [p.name for p in available],
        "cooldowns": {k: round(v - time.time(), 1) for k, v in COOLDOWN_UNTIL.items()}
    }


@app.get("/providers")
async def list_providers():
    return {
        "providers": [
            {
                "name": p.name,
                "base_url": p.base_url,
                "models": p.models,
                "featured_model": p.featured_model,
                "priority": p.priority,
                "available": p.name not in COOLDOWN_UNTIL or time.time() >= COOLDOWN_UNTIL[p.name]
            }
            for p in PROVIDERS
        ]
    }


@app.get("/")
async def root():
    return {
        "name": "FreeRouter Proxy",
        "version": "0.2.0",
        "providers_loaded": len(PROVIDERS),
        "endpoints": {
            "GET /health": "Health check",
            "GET /providers": "List providers",
            "POST /v1/chat/completions": "OpenAI-compatible chat",
            "GET /v1/models": "List models",
        }
    }


@app.get("/v1/models")
@app.post("/v1/models")
async def list_models():
    all_models = []
    for p in PROVIDERS:
        for m in p.models:
            all_models.append({
                "id": m,
                "object": "model",
                "owned_by": p.name,
                "created": int(time.time())
            })
    return {"object": "list", "data": all_models}


@app.post("/v1/chat/completions")
async def chat_completions(request: ChatCompletionRequest):
    available = get_available_providers()
    if not available:
        raise HTTPException(status_code=503, detail="All providers are in cooldown")

    messages = [{"role": msg.role, "content": msg.content} for msg in request.messages]

    body: Dict[str, Any] = {"messages": messages}
    if request.max_tokens is not None:
        body["max_tokens"] = request.max_tokens
    if request.temperature is not None:
        body["temperature"] = request.temperature
    if request.top_p is not None:
        body["top_p"] = request.top_p
    if request.stream:
        body["stream"] = True
    if request.stop is not None:
        body["stop"] = request.stop
    if request.presence_penalty is not None:
        body["presence_penalty"] = request.presence_penalty
    if request.frequency_penalty is not None:
        body["frequency_penalty"] = request.frequency_penalty
    if request.tools:
        body["tools"] = request.tools
    if request.tool_choice:
        body["tool_choice"] = request.tool_choice

    last_error = None

    for provider in available:
        model = request.model if request.model != "auto" else provider.featured_model
        if provider.name != "puter" and "/" in model:
            model = provider.featured_model

        body["model"] = model
        url = f"{provider.base_url}/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {provider.api_key}",
            **provider.extra_headers,
        }

        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                if request.stream:
                    return await _stream_forward(client, url, headers, body, provider.name, model)
                else:
                    resp = await client.post(url, json=body, headers=headers)

                    if resp.status_code == 429:
                        record_failure(provider.name)
                        logger.warning(f"429 on {provider.name}, trying next...")
                        last_error = f"Rate limited: {provider.name}"
                        continue

                    if resp.status_code >= 400:
                        record_failure(provider.name)
                        logger.warning(f"{provider.name} returned {resp.status_code}: {resp.text[:200]}")
                        last_error = f"{provider.name} HTTP {resp.status_code}"
                        continue

                    record_success(provider.name)
                    data = resp.json()
                    data["model"] = model
                    data["x_provider"] = provider.name
                    return data

        except httpx.ConnectTimeout:
            record_failure(provider.name)
            last_error = f"Timeout: {provider.name}"
        except httpx.ReadTimeout:
            record_failure(provider.name)
            last_error = f"Read timeout: {provider.name}"
        except Exception as e:
            record_failure(provider.name)
            last_error = f"Error on {provider.name}: {str(e)}"

    raise HTTPException(status_code=503, detail=f"All providers failed. Last: {last_error}")


async def _stream_forward(client: httpx.AsyncClient, url: str, headers: dict,
                          body: dict, provider_name: str, model: str):
    async def generate():
        try:
            async with client.stream("POST", url, json=body, headers=headers) as resp:
                if resp.status_code >= 400:
                    yield f'data: {{"error": "{resp.status_code} - {provider_name}"}}\n\n'
                    return
                record_success(provider_name)
                async for chunk in resp.aiter_bytes():
                    yield chunk
        except Exception as e:
            yield f'data: {{"error": "{str(e)}"}}\n\n'

    return StreamingResponse(generate(), media_type="text/event-stream")
