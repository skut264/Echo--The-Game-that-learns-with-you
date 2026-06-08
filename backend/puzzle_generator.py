#!/usr/bin/env python3
"""Echo - LLM Puzzle Generator

Generates unique dynamic puzzles using the Qwen2.5-Coder-7B model.
Also provides LLM-based failure prediction.

Puzzle types:
  - pattern_recognition: Timed sequence/pattern puzzles
  - psychology_question: Mind-bending questions with weighted options
  - spatial_logic: Spatial reasoning challenges
  - sequence_memory: Memorize and recall sequences
  - timing_challenge: Reaction-time based puzzles

Each puzzle includes golden-ratio canvas layout data.
"""

from __future__ import annotations
import json
import time
import random
import httpx
from typing import Any

GENERATOR_ENDPOINT = "http://localhost:11435/v1/chat/completions"
MODEL = "qwen2.5-coder-7b-instruct-q4_k_m.gguf"

PUZZLE_INSTRUCTIONS = """
You are a creative puzzle generator for a cognitive training game called Echo.
You MUST generate UNIQUE, challenging puzzles each time. NEVER repeat yourself.

{type_specific_instruction}

CRITICAL RULES:
1. Every puzzle MUST be unique - different scenario, numbers, layout, or twist each time
2. Do NOT repeat the same puzzle template twice
3. Be creative - use psychology, math tricks, visual patterns, timing traps
4. The 3 options MUST have REALISTIC weights that make the question meaningful
5. The correct_answer MUST be one of the option text values exactly

Return ONLY valid JSON with these fields:
  - prompt: str (the puzzle question/challenge text, 1-2 sentences)
  - options: list of {{"text": str, "weight": int}}  (weight 0-100, higher = more correct)
  - correct_answer: str (must match an option text exactly)
  - time_limit_ms: int (7000-30000 depending on difficulty)
  - metadata: {{"difficulty": int (1-10), "category": str, "hint": str (subtle hint not giving answer)}}
"""

PATTERN_INSTRUCTION = """
Generate a pattern recognition puzzle. Examples of patterns:
- Number sequences with hidden operations
- Visual pattern descriptions requiring matching
- Symbolic logic puzzles
- Mathematical riddles with a clever twist
- Time-based pattern continuation

The options should be 3 choices where one is correct and the others are plausible traps.
"""

PSYCH_INSTRUCTION = """
Generate a psychology/mind-bending question. Examples:
- Cognitive bias traps (confirmation bias, anchoring effect, etc.)
- Probability paradoxes (Monty Hall, base rate fallacy)
- Framing effect questions (same problem, different frames)
- Moral reasoning with weighted choices
- Memory/recollection triggers
- Attention/awareness tests

Each option must have a weight (0-100) representing how "correct" or "optimal" that choice is psychologically.
The weights should NOT be binary (100/0/0) — make them realistic: e.g. one option at 70-95, others at 20-50.
The correct_answer should be the MOST correct psychologically, but wrong answers have partial truth too.

These are NOT trivia questions. They should make the player think about how they think.
"""

SPATIAL_INSTRUCTION = """
Generate a spatial logic puzzle. Examples:
- Mental rotation descriptions
- Path-finding with constraints
- Arrangement puzzles
- Symmetry/mirror reasoning
- Grid-based logic

The options should be 3 choices with varying degrees of correctness.
"""

SEQUENCE_INSTRUCTION = """
Generate a sequence memory challenge. Examples:
- Number/figure sequences with hidden rules
- Cause-effect chains
- Step-by-step procedural reasoning
- Transformation chains
- Pattern of transformations

The options should be 3 choices where one completes/follows the pattern correctly.
"""

TIMING_INSTRUCTION = """
Generate a timing/reaction challenge description. Examples:
- Describe a scenario where timing matters
- Multi-step procedure ordering
- Speed vs accuracy tradeoffs
- Reaction-based reasoning
- Time estimation challenges

The options should be 3 choices with one being optimal timing-wise.
"""

TYPE_INSTRUCTIONS = {
    "pattern_recognition": PATTERN_INSTRUCTION,
    "psychology_question": PSYCH_INSTRUCTION,
    "spatial_logic": SPATIAL_INSTRUCTION,
    "sequence_memory": SEQUENCE_INSTRUCTION,
    "timing_challenge": TIMING_INSTRUCTION,
}


def _call_llm(prompt: str, max_tokens: int = 800, temperature: float = 0.9, timeout: int = 60) -> str | None:
    """Call the Qwen2.5-Coder model through the tunnel."""
    try:
        with httpx.Client(timeout=httpx.Timeout(timeout)) as client:
            resp = client.post(
                GENERATOR_ENDPOINT,
                json={
                    "model": MODEL,
                    "messages": [
                        {"role": "system", "content": "You are a puzzle generator. Return ONLY valid JSON. No explanations, no markdown formatting, no code fences. Just the raw JSON."},
                        {"role": "user", "content": prompt},
                    ],
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                    "top_p": 0.95,
                },
            )
            if resp.status_code == 200:
                return resp.json()["choices"][0]["message"]["content"]
            else:
                print(f"[LLM] Error {resp.status_code}: {resp.text[:200]}")
                return None
    except Exception as e:
        print(f"[LLM] Request failed: {e}")
        return None


def _parse_json(text: str) -> dict | None:
    """Extract JSON from LLM response, handling markdown fences."""
    if not text:
        return None
    # Remove markdown code fences if present
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        text = text.rsplit("```", 1)[0] if "```" in text else text
        text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        print(f"[LLM] Failed to parse JSON: {text[:300]}")
        return None


def generate_puzzle(puzzle_type: str, player_context: dict | None = None) -> dict:
    """
    Generate a unique puzzle of the given type.
    
    Args:
        puzzle_type: One of the PUZZLE_TYPES
        player_context: Optional dict with player stats for personalized puzzles
        
    Returns:
        dict with puzzle data ready for DynamicPuzzle.from_llm()
    """
    type_instruction = TYPE_INSTRUCTIONS.get(puzzle_type, PATTERN_INSTRUCTION)
    
    context_str = ""
    if player_context:
        context_str = (
            f"Player context: {json.dumps(player_context)}\n"
            "Use this to tailor difficulty. "
            f"Time limit range: {7000 + player_context.get('total_attempts', 0) * 0} to {30000 - player_context.get('correct_attempts', 0) * 0}\n"
        )
    
    # Add randomness seed to ensure variety
    seed = int(time.time() * 1000) % 100000
    rand_prompt = f"Use seed {seed}. Generate a completely fresh puzzle no one has seen before."
    
    if puzzle_type == "psychology_question":
        prompt = (
            f"{PUZZLE_INSTRUCTIONS.format(type_specific_instruction=PSYCH_INSTRUCTION)}\n\n"
            f"{rand_prompt}\n"
            f"{context_str}\n"
            "IMPORTANT: The 3 options must have REALISTIC weights (not just 100/0/0). "
            "Each weight 0-100 represents how psychologically 'correct' that option is. "
            "Make the weights nuanced — e.g. best=85, second=45, third=20. "
            "The question should make the player reflect on their own psychology."
        )
    else:
        prompt = (
            f"{PUZZLE_INSTRUCTIONS.format(type_specific_instruction=type_instruction)}\n\n"
            f"{rand_prompt}\n"
            f"{context_str}\n"
        )
    
    text = _call_llm(prompt, temperature=0.95)
    data = _parse_json(text)
    
    if not data:
        # Fallback: generate a simple math puzzle
        a = random.randint(10, 99)
        b = random.randint(10, 99)
        ops = ["+", "-", "*"]
        op = random.choice(ops)
        if op == "+":
            ans = a + b
        elif op == "-":
            ans = a - b
        else:
            ans = a * b
        wrong1 = ans + random.randint(1, 10)
        wrong2 = ans - random.randint(1, 5)
        data = {
            "prompt": f"Quick math: What is {a} {op} {b}?",
            "options": [
                {"text": str(ans), "weight": 100},
                {"text": str(wrong1), "weight": 20},
                {"text": str(wrong2), "weight": 10},
            ],
            "correct_answer": str(ans),
            "time_limit_ms": 10000,
            "metadata": {"difficulty": 3, "category": "math", "hint": f"Think about {op} operation"},
        }
    
    return data


def predict_will_fail(player_context: dict) -> dict:
    """
    Use the LLM to predict if the player will fail the current puzzle again.
    
    Args:
        player_context: dict with failure pattern data (from get_prediction_context())
        
    Returns:
        dict with {"prediction": bool, "confidence": float, "reasoning": str}
    """
    prompt = (
        f"Analyze this player's failure pattern and predict if they will fail again "
        f"if shown the same puzzle type one more time.\n\n"
        f"Player data: {json.dumps(player_context)}\n\n"
        f"Consider:\n"
        f"1. If time_to_fail is DECREASING (speeding up to fail), they're guessing randomly -> WILL FAIL AGAIN\n"
        f"2. If time_to_fail is INCREASING (taking longer), they might learn -> MIGHT IMPROVE\n"
        f"3. Low accuracy + fast decisions = random guessing\n"
        f"4. High hesitation + previous struggle = potential for improvement\n\n"
        f"Return ONLY valid JSON: {{\"prediction\": bool, \"confidence\": 0.0-1.0, \"reasoning\": \"one sentence\"}}"
    )
    
    text = _call_llm(prompt, max_tokens=200, temperature=0.3)
    data = _parse_json(text)
    
    if data and "prediction" in data:
        return {
            "prediction": bool(data["prediction"]),
            "confidence": float(data.get("confidence", 0.7)),
            "reasoning": str(data.get("reasoning", "")),
        }
    
    # Fallback: heuristic
    trend = player_context.get("trend", "insufficient_data")
    failures = player_context.get("failures_so_far", 0)
    speed_delta = player_context.get("speed_delta_ms", 0)
    
    if trend == "faster_at_failing":
        return {"prediction": True, "confidence": 0.8, "reasoning": "Getting faster at failing - likely guessing randomly"}
    elif failures >= 2 and speed_delta < -500:
        return {"prediction": True, "confidence": 0.75, "reasoning": "Significant speed increase in failing pattern"}
    elif failures >= 1 and player_context.get("recent_accuracy_window", 1) < 0.3:
        return {"prediction": True, "confidence": 0.6, "reasoning": "Low overall accuracy combined with this puzzle"}
    else:
        return {"prediction": False, "confidence": 0.5, "reasoning": "Insufficient data for reliable prediction"}


def generate_coaching_hint(puzzle: dict, player_state: str, attempts_data: list[dict]) -> str:
    """Generate an LLM-powered coaching hint based on the player's state."""
    context = {
        "puzzle_prompt": puzzle.get("prompt", ""),
        "player_state": player_state,
        "recent_attempts": attempts_data[-3:] if attempts_data else [],
    }
    
    prompt = (
        f"Generate a ONE-SENTENCE coaching hint for this player.\n"
        f"Context: {json.dumps(context)}\n\n"
        f"Player state is '{player_state}':\n"
        f"  - 'struggle' = they're trying hard but failing. Give a subtle hint.\n"
        f"  - 'skill_gap' = they're hesitating. Give encouragement + strategy tip.\n"
        f"  - 'stable' = they're doing fine. Give a quick tip for mastery.\n\n"
        f"DO NOT give away the answer. Be subtle and psychological.\n"
        f"Return ONLY the hint text, no JSON, no quotes."
    )
    
    text = _call_llm(prompt, max_tokens=100, temperature=0.7)
    if text:
        # Clean any wrapping
        text = text.strip().strip('"').strip("'")
        return text
    
    # Fallback hints
    fallbacks = {
        "struggle": "Look for the hidden pattern — sometimes the simplest answer is right in front of you.",
        "skill_gap": "Take a breath. You've got this. Try breaking the problem into smaller parts.",
        "stable": "Good pace! Now try to see if there's a deeper pattern at work.",
    }
    return fallbacks.get(player_state, "Focus on what the question is really asking.")