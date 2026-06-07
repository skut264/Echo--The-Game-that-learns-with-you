#!/usr/bin/env python3
"""Echo - Async Ollama LLM client for coaching hints.

If the LLM takes longer than LLM_TIMEOUT_SECONDS, serve
a cached heuristic fallback hint instead.
"""

import httpx
import json
import asyncio
from config import LLM_API_BASE, LLM_MODEL, LLM_TIMEOUT_SECONDS, LLM_FALLBACK_HINTS


def _build_prompt(error_type: str, attempt_count: int, state: str, player_speed: str) -> str:
    """Build a compact coaching prompt for the LLM."""
    return f"""You are a game coach. The player made an error of type "{error_type}"
on attempt {attempt_count}. Their state is "{state}" and typical speed is "{player_speed}".

Give ONE short, empathetic sentence that helps them improve. No riddles.
Do not give away the answer. Address the specific error type."""


async def get_coaching_hint(
    error_type: str,
    attempt_count: int = 1,
    state: str = "stable",
    player_speed: str = "normal",
) -> tuple[str, str, int]:
    """
    Get a coaching hint from the LLM.

    Returns: (hint_text, source, latency_ms)
      - hint_text: the hint
      - source: "llm" or "heuristic"
      - latency_ms: how long it took
    """
    start = asyncio.get_event_loop().time()

    prompt = _build_prompt(error_type, attempt_count, state, player_speed)
    payload = {
        "model": LLM_MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {
            "num_predict": 60,
            "temperature": 0.3,
        },
    }

    try:
        async with httpx.AsyncClient(timeout=LLM_TIMEOUT_SECONDS) as client:
            resp = await client.post(
                f"{LLM_API_BASE}/api/generate",
                json=payload,
            )
            elapsed = int((asyncio.get_event_loop().time() - start) * 1000)

            if resp.status_code == 200:
                data = resp.json()
                hint = data.get("response", "").strip()
                if hint and len(hint) > 10:
                    return hint, "llm", elapsed

            # Fallback to heuristic
            fallback = LLM_FALLBACK_HINTS.get(error_type, LLM_FALLBACK_HINTS["generic"])
            return fallback, "heuristic", elapsed

    except (httpx.TimeoutException, httpx.ConnectError, httpx.HTTPError):
        elapsed = int((asyncio.get_event_loop().time() - start) * 1000)
        fallback = LLM_FALLBACK_HINTS.get(error_type, LLM_FALLBACK_HINTS["generic"])
        return fallback, "heuristic", elapsed