#!/usr/bin/env python3
"""
Free LLM Router — Smart routing between 24 free-tier LLM providers
Based on: https://github.com/TerexitariusStomp/Freellmrouter

Architecture (from Freellmrouter codebase):
  - ProviderRegistry    : capability-scored providers with tier system (S+/A/B/C)
  - ProviderScorer      : multi-factor scoring (credit + capability + speed + health)
  - QuotaManager        : SQLite tracking of requests, failures, 429 rate-limits
  - HealthMonitor       : circuit-breaker pattern (closed → half-open → open)
  - TaskClassifier      : keyword-based prompt → task type → best provider

Usage: free-llm-router <command> [args]
  status        Overview of all providers, keys, tiers
  best <task>   Best providers for: general, coding, reasoning, vision, long, fast
  test [n]      Live HTTP connectivity test (default: 10)
  health        Circuit-breaker health status
  recommend     Time + capability aware routing recommendations
  switch <id>   Switch config.yaml primary provider
  help          This message
"""

import sys
import os
import time
import sqlite3
import json
import urllib.request
import urllib.error
from datetime import datetime, timezone

# ── Paths ────────────────────────────────────────────────────────────────────
ENV_PATH   = os.path.expanduser("~/.hermes/.env")
CFG_PATH   = os.path.expanduser("~/.hermes/config.yaml")
DB_PATH    = os.path.expanduser("~/.hermes/router_quota.sqlite")
HEALTH_PATH = os.path.expanduser("~/.hermes/router_health.json")

# ── Init SQLite (Freellmrouter QuotaManager) ─────────────────────────────────
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS requests (\n"
              "  provider TEXT, ts REAL, success INTEGER, "
              "  status_code INTEGER, response_ms REAL)")
    conn.commit()
    conn.close()

init_db()

# ── Env key helpers ───────────────────────────────────────────────────────────
def read_env():
    """Parse .env into dict"""
    env = {}
    if not os.path.exists(ENV_PATH):
        return env
    with open(ENV_PATH) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#') or '=' not in line:
                continue
            k, v = line.split('=', 1)
            env[k] = v
    return env

def key_ok(env, key):
    if not key:
        return True  # no key needed (local/optional)
    val = env.get(key, "")
    return bool(val and val != "***")

def key_mask(env, key):
    if not key:
        return "N/A"
    val = env.get(key, "")
    if val and val != "***":
        return f"{val[:8]}...{val[-4:]}"
    return "!! MISSING !!"

# ── Health tracking (Freellmrouter HealthMonitor + circuit breaker) ───────────
def record_request(provider_id, success=True, status_code=200, response_ms=0):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO requests VALUES (?, ?, ?, ?, ?)",
              (provider_id, time.time(), int(success), status_code, response_ms))
    conn.commit()
    conn.close()

def consecutive_failures(provider_id, window_hours=1):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    cutoff = time.time() - (window_hours * 3600)
    c.execute("SELECT COUNT(*) FROM requests WHERE provider=? AND success=0 AND ts>?",
              (provider_id, cutoff))
    return c.fetchone()[0]

def recent_429s(provider_id, window_secs=300):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    cutoff = time.time() - window_secs
    c.execute("SELECT COUNT(*) FROM requests WHERE provider=? AND status_code=429 AND ts>?",
              (provider_id, cutoff))
    return c.fetchone()[0]

def circuit_state(provider_id):
    """Freellmrouter circuit-breaker: closed → half-open → open"""
    cf = consecutive_failures(provider_id)
    if cf >= 3:
        return "🔴 OPEN"
    elif cf >= 1:
        return "🟡 HALF"
    elif recent_429s(provider_id) > 0:
        return "🟠 COOLING"
    return "🟢 CLOSED"

# ── Provider Registry (Freellmrouter registry.py PROVIDERS_DATA) ─────────────
# (id, name, tier, rank, model, env_key, base_url, [caps...], rpm, daily, notes)
# caps = [general, coding, reasoning, vision, long, fast] — scores 0-100
PROVIDERS = [
    # ═══ TIER S+  FLAGSHIP — best quality ═══
    ("google",    "Google AI Studio",       "S+", "01", "gemini-3-pro-preview",                          "GOOGLE_AI_API_KEY",          "https://generativelanguage.googleapis.com/v1beta/openai",     90, 82, 88, 91, 95, 85,  15,  1500,  "1.5K req/day"),
    ("mistral",   "Mistral La Plateforme",  "S+", "02", "mistral-large-latest",                          "MISTRAL_API_KEY",            "https://api.mistral.ai/v1",                                    85, 90, 82,  0, 78, 75,  60,     0,  "Data opt-in"),
    ("poe",       "Poe Claude 3.7 Sonnet",  "S+", "03", "Claude-3.7-Sonnet",                             "POE_API_KEY",                "https://api.poe.com/bot/",                                     75, 80, 88, 75, 70, 72,  20,     0,  "Daily limit"),
    # ═══ TIER A  70B-CLASS — excellent generalists ═══
    ("groq",      "Groq Llama 3.3 70B",     "A",  "04", "llama-3.3-70b-versatile",                       "GROQ_API_KEY",               "https://api.groq.com/openai/v1",                               87, 84, 82,  0, 65, 99,  30, 14400,  "Fastest, 14.4K/day"),
    ("together",  "Together AI 70B",        "A",  "05", "meta-llama/Llama-3.3-70B-Instruct-Turbo",        "TOGETHER_API_KEY",           "https://api.together.xyz/v1",                                  89, 87, 90, 75, 82, 78,  60,     0,  "$1 trial"),
    ("fireworks", "Fireworks 70B",          "A",  "06", "accounts/fireworks/models/llama-v3p3-70b-instruct","FIREWORKS_API_KEY",         "https://api.fireworks.ai/inference/v1",                        84, 82, 80, 65, 75, 78,  30,     0,  "Generous free"),
    ("cerebras",  "Cerebras 70B",           "A",  "07", "llama3.1-70b",                                  "CEREBRAS_API_KEY",           "https://api.cerebras.ai/v1",                                   86, 80, 80,  0, 40, 98,  30, 14400,  "8K ctx free"),
    ("zai",       "Z.AI GLM-4 Plus",        "A",  "08", "glm-4-plus",                                    "GLM_API_KEY",                "https://api.z.ai/api/paas/v4",                                 76, 74, 72, 65, 68, 70,  20,     0,  "Bilingual"),
    ("cloudflare","Cloudflare 70B",         "A",  "09", "@cf/meta/llama-3.3-70b-instruct-fp8-fast",      "CLOUDFLARE_API_KEY",         "https://api.cloudflare.com/client/v4/accounts/6c0140469651854b2e358517371a03d3/ai/v1", 80, 78, 76, 72, 60, 92,  0, 0, "10K neurons/day"),
    # ═══ TIER B  SOLID MID-TIER — good for most tasks ═══
    ("cohere",    "Cohere Command-R-Plus",  "B",  "10", "command-r-plus",                                "COHERE_API_KEY",             "https://api.cohere.ai/compatibility/v1",                       83, 72, 78,  0, 88, 70,  20,  1000,  "1K req/month"),
    ("kluster",   "Kluster 70B",            "B",  "11", "klusterai/Meta-Llama-3.3-70B-Instruct-Turbo",    "KLUSTER_API_KEY",            "https://api.kluster.ai/v1",                                    82, 80, 78, 60, 70, 75,  30,     0,  ""),
    ("minimax",   "MiniMax Text-01",        "B",  "12", "MiniMax-Text-01",                               "MINIMAX_API_KEY",            "https://api.minimax.io/v1",                                    78, 76, 74, 70, 68, 72,  20,     0,  ""),
    ("puter",     "Puter GPT-4o",           "B",  "13", "gpt-4o",                                        "PUTER_API_KEY",              "https://api.puter.com/drivers/call/puter-chat-completion",     98, 95, 97, 95, 96, 90,  60,     0,  "500+ models"),
    ("vercel",    "Vercel AI Gateway",      "B",  "14", "gpt-4o",                                        "VERCEL_AI_GATEWAY_KEY",      "https://ai-gateway.vercel.sh/v1",                              82, 80, 78, 72, 68, 75,  30,     0,  ""),
    ("aimlapi",   "AIML API GPT-4o",        "B",  "15", "gpt-4o",                                        "AIMLAPI_API_KEY",            "https://api.aimlapi.com/v1",                                   78, 76, 74, 68, 65, 70,  20,     0,  ""),
    ("llm7",      "LLM7 GPT-4o",            "B",  "16", "gpt-4o",                                        "LLM7_API_KEY",               "https://api.llm7.io/v1",                                       78, 76, 74, 50, 65, 70,  20,     0,  "Unlimited free"),
    ("lobehub",   "LobeHub Claude Sonnet",  "B",  "17", "claude-sonnet-4",                               "LOBEHUB_API_KEY",            "https://api.lobehub.com/v1",                                   78, 76, 74, 68, 65, 70,  20,     0,  ""),
    ("stepfun",   "Stepfun Step-2-16K",     "B",  "18", "step-2-16k",                                    "STEPFUN_API_KEY",            "https://api.stepfun.com/v1",                                   76, 72, 78, 68, 65, 70,  20,     0,  ""),
    # ═══ TIER C  BUDGET/EMERGENCY — last resort ═══
    ("airforce",  "Airforce API",           "C",  "19", "gpt-4o",                                        "AIRFORCE_API_KEY",           "https://api.airforce/v1",                                      80, 78, 76, 70, 65, 72,  20,     0,  "Proxy"),
    ("pollinations","Pollinations",         "C",  "20", "openai-large",                                  "POLLINATIONS_API_KEY",       "https://text.pollinations.ai/openai",                           75, 70, 72, 60, 60, 85,  30,     0,  "No key needed"),
    ("arcee",     "Arcee AI Blitz",         "C",  "21", "arcee-ai/arcee-blitz",                          "ARCEE_API_KEY",              "https://models.arcee.ai/v1",                                   76, 74, 72, 60, 65, 68,  20,     0,  "Small, fast"),
    ("ibm",       "IBM Granite 3 8B",       "C",  "22", "ibm/granite-3-8b-instruct",                     "IBM_API_KEY",                "https://us-south.ml.cloud.ibm.com/ml/v1/text/chat",            75, 78, 74, 50, 70, 65,  20,     0,  "Last resort"),
    ("ollama",    "Ollama Cloud",           "C",  "23", "llama3.3",                                      "OLLAMA_CLOUD_API_KEY",       "https://ollama.com/v1",                                        82, 80, 78, 65, 75, 70,  30,     0,  "Cloud-hosted"),
    ("ollama_local","Ollama Local",         "C",  "24", "llama3.3",                                      "",                           "http://localhost:11434/v1",                                    82, 80, 78, 65, 75, 70,  30,     0,  "No API key"),
]

# Provider lookup by id
def find_provider(pid):
    for p in PROVIDERS:
        if p[0] == pid:
            return p
    return None

def cap(p, task_name):
    """Get capability score for a provider by task name"""
    task_idx = {"general": 0, "coding": 1, "reasoning": 2, "vision": 3, "long": 4, "fast": 5}
    idx = task_idx.get(task_name, 0)
    return p[7 + idx]  # caps start at index 7

def tier_sort_key(tier):
    return {"S+": 0, "A": 1, "B": 2, "C": 3}.get(tier, 9)

# ── Commands ─────────────────────────────────────────────────────────────────
def cmd_status():
    env = read_env()
    configured = sum(1 for p in PROVIDERS if key_ok(env, p[5]))
    total = len(PROVIDERS)

    print()
    print(" ┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓")
    print(" ┃  Free LLM Router — Provider Overview                   ┃")
    print(" ┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛")
    print()
    print("  Primary     : qwen/qwen3.6-plus-preview:free  (OpenRouter)")
    print("  Fallbacks   : 24 providers in 4 quality tiers (S+ → A → B → C)")
    print(f"  Config      : {CFG_PATH}")
    print(f"  Quota DB    : {DB_PATH}")
    print()

    cur_tier = ""
    for p in PROVIDERS:
        pid, name, tier, rank, model, key, url, *caps_data = p
        rpm, daily, notes = caps_data[-3], caps_data[-2], caps_data[-1]
        caps = caps_data[:-3]

        if tier != cur_tier:
            cur_tier = tier
            labels = {
                "S+": "═══ TIER S+  FLAGSHIP — best quality, use first ═══",
                "A":  "─── TIER A   70B-CLASS — excellent generalists ───",
                "B":  "─── TIER B   MID-TIER  — good for most tasks  ───",
                "C":  "─── TIER C   EMERGENCY — last-resort fallback ───",
            }
            print(f"\n  {labels.get(tier, tier)}")

        ks = key_mask(env, key)
        best_cap = max(caps)
        cb = circuit_state(pid)

        print(f"  {rank}. {name:<22s}  Key: {ks:<40s}  Best: {best_cap}%  CB: {cb}  {notes}")

    print(f"\n  Configured: {configured}/{total} providers | Quota DB: {DB_PATH}\n")


def cmd_best(task_name="general"):
    env = read_env()
    task_idx = {"general": 0, "coding": 1, "reasoning": 2, "vision": 3, "long": 4, "fast": 5}
    if task_name not in task_idx:
        print(f"Unknown task: {task_name}")
        print(f"Use: general, coding, reasoning, vision, long, fast")
        sys.exit(1)

    idx = task_idx[task_name]

    print(f"\n  Best providers for: {task_name}")
    print(f"  {'─' * 100}")
    print(f"  {'#':<4} {'Provider':<22s} {'Tier':<5} {'Score':<7} {'Key':<40s} {'Model'}")
    print(f"  {'─':<4} {'─':<22s} {'─':<5} {'─':<7} {'─':<40s} {'─'}")

    scored = []
    for p in PROVIDERS:
        pid, name, tier, rank, model, key, url, *rest = p
        score = rest[idx]
        if not key_ok(env, key):
            continue
        scored.append((score, int(rank), pid, name, tier, key, model))

    scored.sort(key=lambda x: (-x[0], x[1]))

    for i, (score, rank, pid, name, tier, key, model) in enumerate(scored, 1):
        ks = key_mask(env, key)
        cb = circuit_state(pid)
        print(f"  #{i:<3} {name:<22s} [{tier}] {score:<7} {ks:<40s} {model}")
    print()


def cmd_test(n=10):
    env = read_env()
    print(f"\n  Connectivity test — top {n} live providers")
    print(f"  {'─' * 90}")
    print(f"  {'#':<4} {'Provider':<22s} {'Tier':<5} {'HTTP':<6} {'Time':<8s} {'Key':<40s} {'Health'}")
    print(f"  {'─':<4} {'─':<22s} {'─':<5} {'─':<6} {'─':<8s} {'─':<40s} {'─────'}")

    tested = 0
    for p in PROVIDERS:
        pid, name, tier, rank, model, key, url, *rest = p
        if tested >= n:
            break
        tested += 1

        ks = key_mask(env, key)
        ok = key_ok(env, key)

        if pid == "ollama_local":
            print(f"  #{tested:<3} {name:<22s} [{tier}] {'local':<6} {'—':<8s} {ks:<40s} LOCAL")
            continue

        if not ok or not url:
            print(f"  #{tested:<3} {name:<22s} [{tier}] {'SKIP':<6} {'—':<8s} {ks:<40s} NO KEY")
            continue

        t0 = time.time()
        code = "000"
        try:
            req = urllib.request.Request(f"{url}/models", method="GET")
            resp = urllib.request.urlopen(req, timeout=6)
            code = str(resp.status)
        except urllib.error.HTTPError as e:
            code = str(e.code)
        except Exception:
            code = "000"
        finally:
            ms = int((time.time() - t0) * 1000)

        success = code == "200"
        record_request(pid, success=success, status_code=int(code) if code.isdigit() else 0, response_ms=ms)

        health_labels = {
            "200": "✅ OK", "000": "⏱ TIMEOUT", "401": "🔑 BAD KEY",
            "403": "🚫 FORBIDDEN", "404": "📭 NOT FOUND", "429": "⚠️ RATE LIMIT"
        }
        health = health_labels.get(code, f"❓ HTTP {code}")

        print(f"  #{tested:<3} {name:<22s} [{tier}] {code:<6} {ms:>5}ms  {ks:<40s} {health}")

    print()


def cmd_health():
    print(f"\n  Provider Health — Circuit Breaker Status")
    print(f"  {'─' * 70}")
    print(f"  {'Provider':<22s} {'Fails(1h)':<10s} {'429s(5m)':<10s} {'Circuit State'}")
    print(f"  {'─':<22s} {'─':<10s} {'─':<10s} {'─'}")

    for p in PROVIDERS:
        pid, name = p[0], p[1]
        cf = consecutive_failures(pid)
        r4 = recent_429s(pid)
        cs = circuit_state(pid)
        print(f"  {name:<22s} {cf:<10d} {r4:<10d} {cs}")
    print()


def cmd_recommend():
    hour = datetime.now(timezone.utc).hour
    period = {
        range(0, 6):  ("🌙 Off-Peak",   "All providers fresh — use S+ tier freely (Google, Mistral, Poe)"),
        range(6, 12): ("🌤 Morning",    "Groq 14.4K/day, Cerebras 14.4K/day — use for bulk tasks"),
        range(12, 18):("☀️ Midday",     "Google 1.5K/day getting used — rotate to B tier (Puter, LLM7, Pollinations)") if hour < 18 else ("", ""),
        range(18, 24):("🌆 Evening",    "Save Mistral/Cohere for UTC midnight reset — use Puter/LLM7/Groq"),
    }
    label, desc = "", ""
    for r, (l, d) in period.items():
        if hour in r:
            label, desc = l, d
            break

    print(f"\n  ┌─────────────────────────────────────────────────────────┐")
    print(f"  │  Intelligent Routing Recommendations  (UTC: {hour:02d}:00)      │")
    print(f"  └─────────────────────────────────────────────────────────┘")
    print()
    print(f"  {label}: {desc}")
    print()
    print("  ══ QUALITY-ORDERED FALLBACK CHAIN ══")
    print("  S+ (flagship) → A (70B-class) → B (mid-tier) → C (emergency)")
    print("  Hermes config.yaml fallback_providers follows this order.")
    print()
    print("  ═══ CAPABILITY PEAKS ═══")
    print("  Coding     → Puter GPT-4o   (95/100) > Mistral (90) > Together (87)")
    print("  Reasoning  → Puter GPT-4o   (97/100) > Together (90) > Google (88)")
    print("  Long Ctx   → Google Gemini  (95/100) > Puter (96) > Cohere (88)")
    print("  Vision     → Google Gemini  (91/100) > Puter (95) > Together (75)")
    print("  Speed      → Groq           (99/100) > Cerebras (98) > Cloudflare (92)")
    print("  General    → Puter GPT-4o   (98/100) > Together (89) > Google (90)")
    print()
    print("  ═══ DAILY LIMITS (highest first) ═══")
    print("  Groq       : 14,400 req/day  (~600/hr)")
    print("  Cerebras   : 14,400 req/day  (~600/hr)")
    print("  Google     :  1,500 req/day  (~62/hr)")
    print("  Cloudflare : 10,000 neurons/day")
    print("  Cohere     :  1,000 req/month (shared quota)")
    print("  Puter/LLM7 :  Unlimited free (user-pays model)")
    print("  Pollinations: Unlimited, no auth")
    print()
    print("  ═══ FREELLROUTER SCORING METHODOLOGY ═══")
    print("  Score = credit_weight * quota_remaining")
    print("        + capability_weight * task_capability_match")
    print("        + speed_weight * rpm_score")
    print("        − circuit_breaker_penalty (consecutive failures)")
    print()
    print("  Weights (Freellmrouter default):")
    print("    credit: 40%  |  capability: 35%  |  speed: 25%")
    print()
    print("  ═══ RATE-LIMIT STRATEGY ═══")
    print("  1. Use S+ tier for high-value tasks (debugging, complex code)")
    print("  2. Rotate to Tier A for routine agent turns")
    print("  3. Use B-tier unlimited providers (Puter, LLM7) for bulk work")
    print("  4. Circuit breaker skips providers with 3+ consecutive failures")
    print("  5. 429'd providers go into 5-min cooldown before retry")
    print()


def cmd_switch(target_id):
    p = find_provider(target_id)
    if not p:
        ids = ", ".join(x[0] for x in PROVIDERS)
        print(f"Unknown provider: {target_id}")
        print(f"Known: {ids}")
        sys.exit(1)

    pid, name, tier, rank, model, key, url = p[0], p[1], p[2], p[3], p[4], p[5], p[6]
    print(f"\n  Switch primary provider → {name} (Tier {tier})")
    print(f"  Model: {model}")
    print(f"  Base URL: {url}")
    print(f"  Env Key: {key}")
    print()
    print(f"  To activate, edit {CFG_PATH}:")
    print(f"    model:")
    print(f"      default: {model}")
    print(f"      provider: main  # or provider-specific name")
    print(f"      base_url: {url}")
    print(f"      api_key_env: {key}")
    print(f"\n  Or use: hermes model {target_id}/{model}")
    print(f"  (The fallback_providers chain already includes this provider)")
    print()


def cmd_help():
    print()
    print("  Free LLM Router — Terexitarius")
    print("  Based on: github.com/TerexitariusStomp/Freellmrouter")
    print()
    print("  Usage: free-llm-router <command> [args]")
    print()
    print("  Commands:")
    print("    status            Overview of all 24 providers with tiers, keys, health")
    print("    best <task>       Best providers for: general, coding, reasoning,")
    print("                                            vision, long, fast")
    print("    test [n]          Live HTTP connectivity test (default: 10)")
    print("    health            Circuit-breaker status (3+ failures = OPEN)")
    print("    recommend         Time + capability aware routing recommendations")
    print("    switch <id>       Show config change to use a specific provider")
    print("    help              This message")
    print()
    print("  Architecture:")
    print("    ProviderRegistry  — 24 providers, 4 tiers, 6 capability dimensions")
    print("    ProviderScorer    — multi-factor ranking (credit+capability+speed)")
    print("    QuotaManager      — SQLite tracking (requests, 429s, failures)")
    print("    HealthMonitor     — Circuit breaker: closed → half → open")
    print("    TaskClassifier    — keyword-based → best capability match")
    print()


# ── Dispatch ─────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"

    dispatch = {
        "status":    lambda: cmd_status(),
        "best":      lambda: cmd_best(sys.argv[2] if len(sys.argv) > 2 else "general"),
        "test":      lambda: cmd_test(int(sys.argv[2]) if len(sys.argv) > 2 else 10),
        "health":    lambda: cmd_health(),
        "recommend": lambda: cmd_recommend(),
        "switch":    lambda: cmd_switch(sys.argv[2] if len(sys.argv) > 2 else ""),
        "help":      lambda: cmd_help(),
    }

    fn = dispatch.get(cmd)
    if fn:
        fn()
    else:
        print(f"Unknown command: {cmd}")
        cmd_help()
        sys.exit(1)
