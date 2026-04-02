# Free LLM Router — Hermes Agent Integration
# =============================================================================
# Smart routing between 24 free-tier LLM providers for the Hermes CLI agent.
# Based on the full Freellmrouter architecture:
#   ProviderRegistry | ProviderScorer | QuotaManager | HealthMonitor | TaskClassifier
# =============================================================================

## Architecture

This integration bridges the Freellmrouter Python architecture
(`hermes_free_router/app/`) with the Hermes CLI agent (`~/.hermes/`).

```
Freellmrouter Core (Python)          Hermes Integration (Bash/Python/Config)
┌──────────────────────────┐        ┌─────────────────────────────────────┐
│ ProviderRegistry.py      │───────▶│ router_config.yaml                  │
│  • 24 providers          │        │  • All provider definitions          │
│  • 4 tiers (S+/A/B/C)    │        │  • Capability scores (6 dimensions)  │
│  • Capability scores     │        │  • Rate limits & daily quotas        │
├──────────────────────────┤        ├─────────────────────────────────────┤
│ ProviderScorer.py        │───────▶│ free-llm-router.py                  │
│  • Multi-factor scoring  │        │  • Live CLI interface               │
│  • Credit-weight: 40%    │        │  • Connectivity testing             │
│  • Capability: 35%       │        │  • Task-type ranking                │
│  • Speed: 25%           │        │  • Circuit breaker display          │
├──────────────────────────┤        ├─────────────────────────────────────┤
│ QuotaManager.py          │───────▶│ router_quota.sqlite                 │
│  • SQLite persistence    │        │  • Request logging                  │
│  • Request tracking      │        │  • 429 rate-limit tracking         │
│  • Failure counting      │        │  • Consecutive failure windows       │
├──────────────────────────┤        ├─────────────────────────────────────┤
│ HealthMonitor.py         │───────▶│ (embedded in free-llm-router)       │
│  • Circuit breaker       │        │  • closed → half → open            │
│  • 3-failure threshold   │        │  • 5-min 429 cooldown              │
│  • Recovery timeout      │        └─────────────────────────────────────┘
├──────────────────────────┤        ┌─────────────────────────────────────┐
│ Classifiers.py           │───────▶│ config.yaml fallback_providers      │
│  • Task type keywords    │        │  • Quality-ordered fallback chain   │
│  • general/coding/etc    │        │  • S+ → A → B → C tier ordering     │
│  • Capability mapping    │        │  • Direct Hermes integration        │
└──────────────────────────┘        └─────────────────────────────────────┘
```

## Files

| File | Purpose |
|------|---------|
| `free-llm-router.py` | Standalone CLI tool — status, testing, routing recommendations |
| `router_config.yaml` | Full provider registry for use by Freellmrouter Python code |
| `README.md` | This file |

## Quick Start

```bash
# Run from anywhere (must be in PATH or specify full path)
~/.local/bin/free-llm-router status     # All 24 providers with key status
~/.local/bin/free-llm-router best coding    # Best providers for coding
~/.local/bin/free-llm-router test 10    # Live connectivity test
~/.local/bin/free-llm-router health     # Circuit breaker status
~/.local/bin/free-llm-router recommend  # Time-aware routing suggestions
```

## Provider Quality Tiers

### Tier S+ — Flagship (best quality, use first)
1. **Google AI Studio** — Gemini 3 Pro: 1.5K req/day, excellent long context + vision
2. **Mistral La Plateforme** — Mistral Large: strong coding, requires data training opt-in
3. **Poe** — Claude 3.7 Sonnet: best complex reasoning, daily limits

### Tier A — 70B-Class (excellent generalists)
4. **Groq** — Llama 3.3 70B: **14,400 req/day**, fastest inference (99/100 speed)
5. **Together AI** — Llama 3.3 70B Turbo: $1 trial, strong coding/reasoning
6. **Fireworks AI** — Llama 3.3 70B: generous free limits
7. **Cerebras** — Llama 3.1 70B: 14,400 req/day, wafer-scale, 8K context
8. **Z.AI** — GLM-4 Plus: bilingual (Chinese/English)
9. **Cloudflare** — Llama 3.3 70B: 10K neurons/day, edge-deployed

### Tier B — Solid Mid-Tier (good for most tasks)
10. **Cohere** — Command-R-Plus: 1K req/month, best long context (88/100)
11. **Kluster AI** — Llama 3.3 70B: free CLI auth
12. **MiniMax** — Text-01: multi-modal
13. **Puter** — GPT-4o: **500+ models via single token, unlimited**
14. **Vercel AI Gateway** — GPT-4o: Vercel's gateway
15. **AIML API** — GPT-4o: third-party proxy
16. **LLM7** — GPT-4o: **unlimited free**
17. **LobeHub** — Claude Sonnet 4: Claude aggregator
18. **Stepfun** — Step-2-16K: Chinese reasoning

### Tier C — Budget/Emergency (last resort)
19. **Airforce** — GPT-4o: free proxy, variable reliability
20. **Pollinations** — OpenAI-Large: no auth needed, unlimited
21. **Arcee AI** — Blitz: smaller model, fast
22. **IBM** — Granite 3 8B: smallest, emergency only
23. **Ollama Cloud** — Llama 3.3: cloud-hosted
24. **Ollama Local** — Llama 3.3: local, no API key

## Routing Strategy

### Quality-First Fallback (config.yaml fallback_providers)
Hermes tries the primary model first, then falls back through S+ → A → B → C tiers.
This ensures best quality while maintaining availability.

### Capability-Based Selection (free-llm-router best <task>)
For specific task types, the router identifies providers with the highest capability score:

| Task Type | Best Provider | Score | Second | Score |
|-----------|--------------|-------|--------|-------|
| Coding | Puter GPT-4o | 95 | Mistral Large | 90 |
| Reasoning | Puter GPT-4o | 97 | Together 70B | 90 |
| Vision | Google Gemini Pro | 91 | Puter GPT-4o | 95 |
| Long Context | Google Gemini Pro | 95 | Puter GPT-4o | 96 |
| Speed | Groq 70B | 99 | Cerebras 70B | 98 |

### Rate-Limit Aware Routing (recommend)
- **Off-peak (00-06 UTC)**: S+ tier free — use all flagship providers
- **Morning (06-12 UTC)**: Groq 14.4K + Cerebras 14.4K fresh for bulk tasks
- **Midday (12-18 UTC)**: Rotate to B-tier unlimited (Puter, LLM7, Pollinations)
- **Evening (18-00 UTC)**: Save Mistral/Cohere for midnight UTC reset

### Circuit Breaker (HealthMonitor)
Automatic per-provider circuit breaker:
- **Closed** (healthy): Full use
- **Half-Open** (1-2 failures): Degraded use, being monitored
- **Open** (3+ failures): Skipped automatically until recovery
- **429 Cooldown**: Rate-limited providers cool for 5 minutes before retry

## Scoring System (ProviderScorer)

The multi-factor scoring system weights:

| Factor | Weight | Description |
|--------|--------|-------------|
| Credit/Quota | 40% | Remaining daily quota vs. total limit |
| Capability | 35% | Task-specific capability score (0-100) |
| Speed | 25% | RPM normalized to max across all providers |
| Health | 0% | Circuit breaker state (configured but not weighted by default) |

Total Score = (credit × 0.40) + (capability × 0.35) + (speed × 0.25)

## Hermes Config Integration

The `router_config.yaml` provides all provider definitions as YAML for use by Freellmrouter's Python modules. The actual Hermes agent reads from `~/.hermes/config.yaml` which has the fallback_providers chain ordered by quality tier.

### Switching Primary Provider
```bash
# Option 1: Use the CLI tool
~/.local/bin/free-llm-router switch groq

# Option 2: Hermes CLI
hermes model groq/llama-3.3-70b-versatile

# Option 3: Edit config.yaml directly
# Change model.default, model.provider, model.base_url
```

## SQLite Quota Database
`router_quota.sqlite` tracks:
- All HTTP requests made to providers
- Success/failure status
- HTTP response codes
- Response times

Used by the circuit breaker to automatically skip failing providers.

## License
Same as parent Freellmrouter project.
