# Hermes Free Router

A production-ready **Hermes Agent model router** that decides which LLM provider/model to use from a pool of free or trial-credit LLM API providers.

## Features

- **Multi-Provider Support**: OpenRouter, Google AI Studio, Groq, Cerebras, Mistral, Cohere, Cloudflare Workers AI, Together AI, GitHub Models, Hugging Face Inference, Hyperbolic, SambaNova
- **Intelligent Routing**: Scores providers based on credits remaining, capability fit, speed, health, and policy constraints
- **Hermes Agent Compatible**: Outputs config blocks directly consumable by Hermes Agent
- **Three Integration Modes**:
  1. Python library
  2. CLI tool
  3. OpenAI-compatible proxy server
- **Quota Tracking**: SQLite-based persistence for request/tokens used, 429 tracking, consecutive failures
- **Health Monitoring**: Circuit breaker pattern with automatic failover
- **Task Classification**: Rule-based classifier maps prompts to task types (general, coding, reasoning, vision, long_context, fast)

## Quick Start

### Run with Docker

```bash
cp .env.example .env
# Add your API keys to .env
docker compose up
```

### Run Locally

```bash
pip install -r requirements.txt
cp .env.example .env
# Add your API keys to .env
python -m app.main
```

## Usage

### Python Library

```python
from app.library import HermesFreeRouter

router = HermesFreeRouter()
choice = router.select_model(
    prompt="Write a Python function to calculate fibonacci numbers",
    task_type="coding",
    require_tool_calling=False
)
print(choice)
# {
#   "provider": "groq",
#   "model": "llama-3.3-70b-versatile",
#   "base_url": "https://api.groq.com/openai/v1",
#   "api_key_env": "GROQ_API_KEY",
#   "reason": "Groq selected for speed and available free quota",
#   "score": 0.89
# }
```

### CLI Tool

```bash
# Pick best provider for a task
python -m app.cli pick "Write a Python function" --task-type coding --json

# List all providers
python -m app.cli providers --json

# Check health status
python -m app.cli health --json

# Show usage stats
python -m app.cli stats --json
```

### Proxy Server (OpenAI-Compatible)

The proxy exposes these endpoints:

| Endpoint | Method | Description |
|---|---|---|
| `/v1/chat/completions` | POST | OpenAI-compatible chat completions |
| `/route` | POST | Manual routing (returns provider selection) |
| `/providers` | GET | List available providers |
| `/health` | GET | Health check |

Point Hermes Agent to the proxy using `provider: "main"`:

```yaml
model:
  provider: "main"
  model: "auto"
  base_url: "http://localhost:8000/v1"
```

## Hermes Agent Integration

### Mode A: Native Provider Selection

When the router selects a provider Hermes understands natively (e.g., `openrouter`):

```json
{
  "provider": "openrouter",
  "model": "meta-llama/llama-3.3-70b-instruct:free",
  "reason": "Best free model with remaining quota",
  "score": 0.91
}
```

### Mode B: Custom Endpoint via `main`

When the router selects a provider with an OpenAI-compatible API:

```json
{
  "provider": "main",
  "model": "llama-3.3-70b-versatile",
  "base_url": "https://api.groq.com/openai/v1",
  "api_key_env": "GROQ_API_KEY",
  "reason": "Groq selected for speed and available free quota",
  "score": 0.89
}
```

## Scoring Formula

```
score =
  credit_weight * normalized_credit_remaining +
  capability_weight * task_fit_score +
  speed_weight * normalized_speed +
  health_weight * health_score +
  policy_weight * policy_score +
  preference_weight * manual_priority
```

Weights are configurable in `configs/router.yaml`.

## File Structure

```
hermes_free_router/
  app/
    __init__.py
    main.py
    cli.py
    router.py
    scorer.py
    registry.py
    quota.py
    health.py
    proxy.py
    hermes_adapter.py
    classifiers.py
    storage.py
    library.py
  configs/
    router.yaml
  tests/
    test_router.py
  .env.example
  docker-compose.yml
  Dockerfile
  requirements.txt
  README.md
```

## API Keys

Copy `.env.example` to `.env` and fill in your keys:

```env
OPENROUTER_API_KEY=
GROQ_API_KEY=
GOOGLE_AI_STUDIO_KEY=
CEREBRAS_API_KEY=
MISTRAL_API_KEY=
COHERE_API_KEY=
CF_API_TOKEN=
TOGETHER_API_KEY=
GITHUB_TOKEN=
HUGGINGFACE_API_KEY=
HYPERBOLIC_API_KEY=
SAMBANOVA_API_KEY=
```

## FreeRouter GUI

The project includes a client-side GUI (`freerouter.html`) that can be served as a GitHub Page. Users can:
- Input API keys for each provider (stored in browser localStorage, never sent to any server)
- Route prompts to the best provider
- View provider status, rate limits, and capacity
- Configure routing strategy and scoring weights

### Deploy as GitHub Page

1. Rename `freerouter.html` to `index.html`
2. Push to a GitHub repository
3. Enable GitHub Pages in repository settings (Settings > Pages > Branch: main)
4. Access at `https://<username>.github.io/<repo>/`

## Running Tests

```bash
python -m pytest tests/ -v
```

## License

MIT
