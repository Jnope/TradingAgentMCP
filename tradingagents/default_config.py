import os

_TRADINGAGENTS_HOME = os.path.join(os.path.expanduser("~"), ".tradingagents")

_ENV_OVERRIDES = {
    "MCP_LLM_PROVIDER":         "llm_provider",
    "MCP_DEEP_THINK_LLM":       "deep_think_llm",
    "MCP_QUICK_THINK_LLM":      "quick_think_llm",
    "MCP_BACKEND_URL":          "backend_url",
    "MCP_OUTPUT_LANGUAGE":      "output_language",
    "MCP_MAX_DEBATE_ROUNDS":    "max_debate_rounds",
    "MCP_MAX_RISK_DISCUSS_ROUNDS": "max_risk_discuss_rounds",
    "MCP_CHECKPOINT_ENABLED":   "checkpoint_enabled",
    "MCP_BENCHMARK_TICKER":     "benchmark_ticker",
    "TRADINGAGENTS_LLM_PROVIDER":       "llm_provider",
    "TRADINGAGENTS_DEEP_THINK_LLM":     "deep_think_llm",
    "TRADINGAGENTS_QUICK_THINK_LLM":    "quick_think_llm",
    "TRADINGAGENTS_LLM_BACKEND_URL":    "backend_url",
    "TRADINGAGENTS_OUTPUT_LANGUAGE":    "output_language",
    "TRADINGAGENTS_MAX_DEBATE_ROUNDS":  "max_debate_rounds",
    "TRADINGAGENTS_MAX_RISK_ROUNDS":    "max_risk_discuss_rounds",
    "TRADINGAGENTS_CHECKPOINT_ENABLED": "checkpoint_enabled",
    "TRADINGAGENTS_BENCHMARK_TICKER":   "benchmark_ticker",
}


def _coerce(value: str, reference):
    if isinstance(reference, bool):
        return value.strip().lower() in ("true", "1", "yes", "on")
    if isinstance(reference, int) and not isinstance(reference, bool):
        return int(value)
    if isinstance(reference, float):
        return float(value)
    return value


def _apply_env_overrides(config: dict) -> dict:
    for env_var, key in _ENV_OVERRIDES.items():
        raw = os.environ.get(env_var)
        if raw is None or raw == "":
            continue
        config[key] = _coerce(raw, config.get(key))
    return config


DEFAULT_CONFIG = _apply_env_overrides({
    "project_dir": os.path.abspath(os.path.join(os.path.dirname(__file__), ".")),
    "results_dir": os.getenv("TRADINGAGENTS_RESULTS_DIR", os.path.join(_TRADINGAGENTS_HOME, "logs")),
    "data_cache_dir": os.getenv("TRADINGAGENTS_CACHE_DIR", os.path.join(_TRADINGAGENTS_HOME, "cache")),
    "memory_log_path": os.getenv("TRADINGAGENTS_MEMORY_LOG_PATH", os.path.join(_TRADINGAGENTS_HOME, "memory", "trading_memory.md")),
    "memory_log_max_entries": None,

    "llm_provider": "openai",
    "deep_think_llm": "gpt-4o",
    "quick_think_llm": "gpt-4o-mini",
    "backend_url": None,

    "google_thinking_level": None,
    "openai_reasoning_effort": None,
    "anthropic_effort": None,

    "checkpoint_enabled": False,

    "output_language": "Chinese",

    "max_debate_rounds": 1,
    "max_risk_discuss_rounds": 1,
    "max_recur_limit": 100,
    "analyst_concurrency_limit": 1,

    "benchmark_ticker": "000300",
})
