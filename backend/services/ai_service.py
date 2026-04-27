"""Unified LLM client — OpenRouter with cost tracking, extended thinking, auto-routing.

Deepresearch pattern: single client for all LLM calls across the app.
Tracks token usage and cost per-request. Supports extended thinking for
reasoning-heavy tasks (stage 3 synthesis, research agent).
"""
from __future__ import annotations
import time
from dataclasses import dataclass, field
from typing import AsyncGenerator
from openai import AsyncOpenAI
from ..config import get_settings

settings = get_settings()

# ── OpenRouter client (OpenAI-compatible) ──
_client = AsyncOpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=settings.openrouter_api_key,
    default_headers={
        "HTTP-Referer": "https://mckinsey-deck-builder.local",
        "X-Title": "McKinsey Deck Builder",
    },
)

# ── Model pricing (USD per 1M tokens) ──
MODEL_PRICING: dict[str, dict[str, float]] = {
    "deepseek/deepseek-v3.2":           {"input": 0.26, "output": 0.38},
    "google/gemini-2.5-flash":           {"input": 0.30, "output": 2.50},
    "google/gemini-3-flash-preview":     {"input": 0.50, "output": 3.00},
    "google/gemini-2.5-pro-preview":     {"input": 1.25, "output": 10.00},
    "google/gemini-2.5-pro":             {"input": 1.25, "output": 10.00},
    "google/gemini-3.1-pro-preview":     {"input": 2.00, "output": 12.00},
    "anthropic/claude-sonnet-4":         {"input": 3.00, "output": 15.00},
    "anthropic/claude-haiku-4.5":        {"input": 1.00, "output": 5.00},
    "openai/gpt-4.1":                    {"input": 2.00, "output": 8.00},
    "openai/gpt-4.1-mini":              {"input": 0.40, "output": 1.60},
}

# ── Task types for auto-routing ──
# KEY CHANGE: critique and refine now use "powerful" tier so the evaluator
# is at least as capable as the generator. A weak critic produces inflated scores.
TASK_ROUTING: dict[str, str] = {
    "classify":    "fast",       # Quick classification, problem definition
    "structure":   "balanced",   # MECE structuring, hypothesis building
    "synthesize":  "powerful",   # Storyline generation, slide creation
    "critique":    "powerful",   # Self-refine critique — MUST be strict, use best model
    "refine":      "powerful",   # Self-refine improvement — needs to follow precise rules
    "research":    "balanced",   # Research agent planning & steps
    "final":       "powerful",   # Final synthesis, research agent output
}


@dataclass
class LLMResponse:
    """Result from a single LLM call with cost metadata."""
    text: str
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0
    duration_ms: float = 0.0
    thinking_text: str = ""


@dataclass
class CostTracker:
    """Accumulated cost tracker for a session or pipeline."""
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_cost_usd: float = 0.0
    calls: list[dict] = field(default_factory=list)

    def record(self, resp: LLMResponse):
        self.total_input_tokens += resp.input_tokens
        self.total_output_tokens += resp.output_tokens
        self.total_cost_usd += resp.cost_usd
        self.calls.append({
            "model": resp.model,
            "input_tokens": resp.input_tokens,
            "output_tokens": resp.output_tokens,
            "cost_usd": round(resp.cost_usd, 6),
            "duration_ms": round(resp.duration_ms, 0),
        })

    def summary(self) -> dict:
        return {
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "total_cost_usd": round(self.total_cost_usd, 6),
            "num_calls": len(self.calls),
            "calls": self.calls,
        }


# ── Global session cost tracker ──
_session_tracker = CostTracker()


def get_cost_tracker() -> CostTracker:
    return _session_tracker


def _compute_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    pricing = MODEL_PRICING.get(model, {"input": 0.5, "output": 1.0})
    return (input_tokens * pricing["input"] + output_tokens * pricing["output"]) / 1_000_000


def _get_model_for_stage(stage: int) -> str:
    """Select the right model tier based on the current stage."""
    if stage <= 1:
        return settings.model_fast
    return settings.model_balanced


def _get_model_for_task(task: str) -> str:
    """Select model based on task type. The "powerful" tier maps to balanced
    in this app (no Gemini Pro needed for Stage 1+2)."""
    tier = TASK_ROUTING.get(task, "balanced")
    if tier == "fast":
        return settings.model_fast
    return settings.model_balanced


async def stream_response(
    system_prompt: str,
    history: list[dict],
    stage: int = 1,
    model_override: str | None = None,
    max_tokens_override: int | None = None,
    task: str | None = None,
) -> AsyncGenerator[str, None]:
    """Stream a response from OpenRouter. Backward-compatible API.

    Automatically selects model tier based on stage or task.
    Yields text tokens as they arrive. Tracks cost.
    """
    if task:
        model = model_override or _get_model_for_task(task)
    else:
        model = model_override or _get_model_for_stage(stage)
    max_tok = max_tokens_override or settings.max_tokens

    messages = [{"role": "system", "content": system_prompt}]
    for msg in history:
        role = msg["role"]
        if role not in ("user", "assistant"):
            continue
        messages.append({"role": role, "content": msg["content"]})

    if not messages or messages[-1]["role"] != "user":
        return

    start = time.time()
    input_tokens = 0
    output_tokens = 0
    full_text = ""

    stream = await _client.chat.completions.create(
        model=model,
        messages=messages,
        max_tokens=max_tok,
        stream=True,
        stream_options={"include_usage": True},
        temperature=0.7,
    )

    async for chunk in stream:
        # Track usage from the final chunk
        if hasattr(chunk, "usage") and chunk.usage:
            input_tokens = getattr(chunk.usage, "prompt_tokens", 0) or 0
            output_tokens = getattr(chunk.usage, "completion_tokens", 0) or 0

        if chunk.choices and chunk.choices[0].delta.content:
            token = chunk.choices[0].delta.content
            full_text += token
            yield token

    # Record cost
    duration = (time.time() - start) * 1000
    cost = _compute_cost(model, input_tokens, output_tokens)
    resp = LLMResponse(
        text=full_text, model=model,
        input_tokens=input_tokens, output_tokens=output_tokens,
        cost_usd=cost, duration_ms=duration,
    )
    _session_tracker.record(resp)


async def complete(
    system_prompt: str,
    user_prompt: str,
    task: str = "structure",
    model_override: str | None = None,
    max_tokens: int | None = None,
    temperature: float = 0.7,
) -> LLMResponse:
    """Non-streaming completion. Returns full LLMResponse with cost metadata.

    Used by self-refine, research agent, and other internal services
    that need the full response before processing.
    """
    model = model_override or _get_model_for_task(task)
    max_tok = max_tokens or settings.max_tokens

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    start = time.time()
    response = await _client.chat.completions.create(
        model=model,
        messages=messages,
        max_tokens=max_tok,
        temperature=temperature,
    )

    text = response.choices[0].message.content or ""
    input_tokens = getattr(response.usage, "prompt_tokens", 0) if response.usage else 0
    output_tokens = getattr(response.usage, "completion_tokens", 0) if response.usage else 0
    duration = (time.time() - start) * 1000
    cost = _compute_cost(model, input_tokens, output_tokens)

    result = LLMResponse(
        text=text, model=model,
        input_tokens=input_tokens, output_tokens=output_tokens,
        cost_usd=cost, duration_ms=duration,
    )
    _session_tracker.record(result)
    return result
