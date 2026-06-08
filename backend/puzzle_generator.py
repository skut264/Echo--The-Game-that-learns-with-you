#!/usr/bin/env python3
"""Echo - Dynamic Puzzle Generator with Fib/Golden Ratio + LLM prediction"""

import math
import json
import random
import time
from typing import Any

PHI = 1.618033988749895
GOLDEN_ANGLE = 137.50776405003785  # degrees

# ── Psychology question bank ──

PSYCH_QUESTIONS = [
    {
        "question": "A bat and a ball cost $1.10. The bat costs $1 more than the ball. How much does the ball cost?",
        "options": [
            {"text": "5 cents", "weight": 1, "reason": "Correct — you avoided the intuitive trap."},
            {"text": "10 cents", "weight": 8, "reason": "Common trap — the fast system took over."},
            {"text": "15 cents", "weight": 5, "reason": "Close but still caught by anchoring."},
        ],
        "correct_index": 0,
        "explanation": "If ball = x, bat = x+1, total = 2x+1 = 1.10, so x = 0.05."
    },
    {
        "question": "Which shape has the largest area? A circle with radius 1, or a square with side length 1.77 (sqrt of pi)?",
        "options": [
            {"text": "The circle is larger", "weight": 3, "reason": "Vertical — you remembered pi."},
            {"text": "The square is larger", "weight": 7, "reason": "Horizontal — intuition bias."},
            {"text": "They are equal", "weight": 1, "reason": "Analytical — you did the math."},
        ],
        "correct_index": 2,
        "explanation": "Circle area = pi*1^2 = pi. Square area = 1.77^2 = 3.1329. They are approximately equal."
    },
    {
        "question": "You flip a fair coin 5 times and get heads every time. What is the probability of heads on the 6th flip?",
        "options": [
            {"text": "50% — each flip is independent", "weight": 1, "reason": "Gambler's fallacy resisted."},
            {"text": "Less than 50% — due for tails", "weight": 9, "reason": "Gambler's fallacy — past doesn't affect future."},
            {"text": "More than 50% — the coin must be biased", "weight": 6, "reason": "Hot hand fallacy — small sample bias."},
        ],
        "correct_index": 0,
        "explanation": "Each coin flip is independent. Probability is always 50%."
    },
    {
        "question": "If it takes 5 machines 5 minutes to make 5 widgets, how long would it take 100 machines to make 100 widgets?",
        "options": [
            {"text": "5 minutes", "weight": 1, "reason": "Correct — each machine makes 1 widget per 5 minutes."},
            {"text": "100 minutes", "weight": 7, "reason": "Linear scaling fallacy — work doesn't compound like that."},
            {"text": "20 minutes", "weight": 5, "reason": "Close but wrong scaling assumption."},
        ],
        "correct_index": 0,
        "explanation": "Each machine makes 1 widget in 5 minutes. 100 machines make 100 widgets in 5 minutes."
    },
    {
        "question": "What comes next in this sequence: 1, 1, 2, 3, 5, 8, 13, ?",
        "options": [
            {"text": "21 — Fibonacci", "weight": 1, "reason": "Correct — you recognized the golden sequence."},
            {"text": "20 — arithmetic progression", "weight": 8, "reason": "Wrong pattern — each term is sum of two prior."},
            {"text": "15 — prime sequence", "weight": 6, "reason": "Wrong sequence type entirely."},
        ],
        "correct_index": 0,
        "explanation": "Fibonacci: each number is the sum of the two preceding numbers. 8 + 13 = 21."
    },
    {
        "question": "Linda is 31, single, outspoken, and very bright. She majored in philosophy. As a student, she was deeply concerned with discrimination and social justice. Which is more probable?",
        "options": [
            {"text": "Linda is a bank teller", "weight": 3, "reason": "Correct — conjunctions are always less probable."},
            {"text": "Linda is a bank teller AND active in the feminist movement", "weight": 8, "reason": "Conjunction fallacy — adding detail makes it seem more likely but IS less probable."},
            {"text": "Linda works in social justice", "weight": 5, "reason": "Representativeness heuristic bias."},
        ],
        "correct_index": 0,
        "explanation": "The conjunction of two events cannot be more probable than either single event. This is the classic Linda problem (Tversky & Kahneman)."
    },
    {
        "question": "A room has 23 people. What is the probability that at least two share a birthday?",
        "options": [
            {"text": "About 50%", "weight": 1, "reason": "Correct — birthday paradox in action."},
            {"text": "About 6%", "weight": 8, "reason": "Extreme underestimation — the math defies intuition."},
            {"text": "About 23%", "weight": 5, "reason": "Still underestimating — the probability climbs fast."},
        ],
        "correct_index": 0,
        "explanation": "With 23 people, P(at least one shared birthday) ~ 50.7%. With 30, it's ~70%. With 57, it's ~99%."
    },
    {
        "question": "Which weighs more: a pound of feathers or a pound of gold?",
        "options": [
            {"text": "They weigh the same — both are a pound", "weight": 1, "reason": "Correct — you ignored the trick framing."},
            {"text": "Feathers — gold is measured in troy pounds", "weight": 6, "reason": "Correct trivia but the question says 'pound' not 'troy pound'."},
            {"text": "Gold — it's denser", "weight": 7, "reason": "Confusing density with weight. A pound is a pound."},
        ],
        "correct_index": 0,
        "explanation": "A pound is a pound regardless of material. This tests whether you separate the trick from the fact."
    },
    {
        "question": "You see a number written as MCMLXXXVIII. What year is it?",
        "options": [
            {"text": "1988", "weight": 1, "reason": "Correct — you decoded Roman numerals."},
            {"text": "1888", "weight": 6, "reason": "You skipped the CM (900) part."},
            {"text": "2188", "weight": 8, "reason": "Added instead of understanding subtractive notation."},
        ],
        "correct_index": 0,
        "explanation": "M=1000, CM=900, LXXX=80, VIII=8. Total: 1988."
    },
    {
        "question": "How many times can you subtract 5 from 25?",
        "options": [
            {"text": "Once — after that it's 20, not 25", "weight": 1, "reason": "Correct — lateral thinking. The trick is in the wording."},
            {"text": "5 times — 25/5 = 5", "weight": 8, "reason": "Mathematical but literal — you can only subtract from the original once."},
            {"text": "Infinite — math is continuous", "weight": 7, "reason": "Overthinking the question completely."},
        ],
        "correct_index": 0,
        "explanation": "Once you subtract 5 from 25, you have 20. You're no longer subtracting from 25."
    },
]


def _golden_spiral_point(index: int, canvas_w: float, canvas_h: float, max_notes: int) -> dict:
    """Position a point on the golden spiral."""
    angle = math.radians(index * GOLDEN_ANGLE)
    # Center at the golden ratio division of the canvas
    cx = canvas_w * 0.382
    cy = canvas_h * 0.382
    # Radius grows with phi^index but capped to fit canvas
    max_r = min(canvas_w, canvas_h) * 0.35
    radius = max_r * (1 - math.pow(PHI, -index - 1))
    # Add some organic jitter
    jitter = 0.92 + random.random() * 0.16
    x = cx + radius * math.cos(angle) * jitter
    y = cy + radius * math.sin(angle) * jitter
    # Element size shrinks with phi
    base_size = 48
    size = max(20, base_size / math.pow(PHI, index / 2 + 1))
    rotation = angle * (180 / math.pi) % 360
    return {"x": round(x, 1), "y": round(y, 1), "size": round(size, 1), "rotation": round(rotation, 1)}


def generate_pattern_puzzle(seq_length: int, difficulty: float) -> dict:
    """Generate a pattern recall puzzle with fibonacci positioning."""
    canvas_w = 800
    canvas_h = 600
    notes = []
    note_colors = ["#e94560", "#0f3460", "#533483", "#ffd700", "#2ecc71", "#3498db", "#e8d5b7", "#ff6b6b"]

    for i in range(seq_length):
        pos = _golden_spiral_point(i, canvas_w, canvas_h, seq_length)
        notes.append({
            "index": i,
            "x": pos["x"],
            "y": pos["y"],
            "size": pos["size"],
            "rotation": pos["rotation"],
            "color": note_colors[i % len(note_colors)],
            "shape": random.choice(["circle", "hexagon", "diamond", "star"]),
        })

    # Fibonacci timing: delay between notes = base / (difficulty * phi^i)
    base_display_ms = 600
    display_timings = [max(150, int(base_display_ms / (difficulty * math.pow(PHI, -i)))) for i in range(seq_length)]

    return {
        "puzzle_type": "pattern_recall",
        "notes": notes,
        "canvas_width": canvas_w,
        "canvas_height": canvas_h,
        "display_timings": display_timings,
        "fib_spiral_visible": True,
        "background_spiral": {
            "arms": 3,
            "growth": PHI,
            "opacity": 0.08,
        },
    }


def generate_motion_puzzle(seq_length: int, difficulty: float) -> dict:
    """Generate a puzzle with objects moving in fibonacci spiral paths."""
    canvas_w = 800
    canvas_h = 600
    cx = canvas_w * 0.382
    cy = canvas_h * 0.382
    objects = []

    for i in range(seq_length):
        start_angle = math.radians(i * GOLDEN_ANGLE)
        end_angle = start_angle + math.radians(180)
        max_r = min(canvas_w, canvas_h) * 0.35

        objects.append({
            "index": i,
            "start_x": round(cx + max_r * 0.2 * math.cos(start_angle), 1),
            "start_y": round(cy + max_r * 0.2 * math.sin(start_angle), 1),
            "end_x": round(cx + max_r * math.cos(end_angle), 1),
            "end_y": round(cy + max_r * math.sin(end_angle), 1),
            "travel_time_ms": int(max(500, 2000 / difficulty * math.pow(PHI, -i))),
            "color": ["#e94560", "#ffd700", "#2ecc71", "#3498db", "#e8d5b7"][i % 5],
            "size": int(max(12, 32 / math.pow(PHI, i / 2))),
        })

    return {
        "puzzle_type": "motion_tracking",
        "objects": objects,
        "canvas_width": canvas_w,
        "canvas_height": canvas_h,
        "fib_spiral_visible": True,
        "background_spiral": {
            "arms": 5,
            "growth": PHI,
            "opacity": 0.06,
        },
    }


def generate_spatial_puzzle(difficulty: float) -> dict:
    """Generate a spatial reasoning puzzle using golden rectangle proportions."""
    canvas_w = 800
    canvas_h = 600
    # Golden rectangle divisions
    rect_w = 300
    rect_h = rect_w / PHI

    shapes = []
    # Generate one correct shape and several altered ones
    num_shapes = 5 + int(difficulty * 2)

    correct_idx = random.randint(0, num_shapes - 1)
    grid_cols = min(5, num_shapes)
    spacing_x = (canvas_w - 100) / grid_cols
    spacing_y = (canvas_h - 200) / max(1, (num_shapes // grid_cols) + 1)

    for i in range(num_shapes):
        col = i % grid_cols
        row = i // grid_cols
        base_x = 50 + col * spacing_x + spacing_x / 2
        base_y = 200 + row * spacing_y + spacing_y / 2

        # The correct shape has exact golden ratio proportions
        if i == correct_idx:
            w = rect_w * 0.15
            h = w / PHI
            shapes.append({
                "x": round(base_x, 1),
                "y": round(base_y, 1),
                "width": round(w, 1),
                "height": round(h, 1),
                "rotation": 0,
                "color": "#2ecc71",
                "is_correct": True,
                "shape": "golden_rect",
            })
        else:
            # Distorted - slightly wrong ratio
            distortion = 0.75 + random.random() * 0.5
            w = rect_w * 0.15
            h = (w / PHI) * distortion
            shapes.append({
                "x": round(base_x, 1),
                "y": round(base_y, 1),
                "width": round(w, 1),
                "height": round(h, 1),
                "rotation": random.uniform(-5, 5),
                "color": "#533483",
                "is_correct": False,
                "shape": "distorted_rect",
            })

    random.shuffle(shapes)

    return {
        "puzzle_type": "spatial_golden",
        "shapes": shapes,
        "canvas_width": canvas_w,
        "canvas_height": canvas_h,
        "correct_index": correct_idx,
        "fib_spiral_visible": True,
    }


def get_psychology_question(difficulty: float) -> dict:
    """Return a random psychology question."""
    q = random.choice(PSYCH_QUESTIONS)
    options = q["options"]
    # Shuffle options but track correct
    indexed = list(enumerate(options))
    random.shuffle(indexed)
    shuffled: list[dict] = []
    new_correct = 0
    for new_idx, (orig_idx, opt) in enumerate(indexed):
        shuffled.append({"text": opt["text"], "weight": opt["weight"], "reason": opt["reason"]})
        if orig_idx == q["correct_index"]:
            new_correct = new_idx
    return {
        "puzzle_type": "psychology_question",
        "question": q["question"],
        "options": shuffled,
        "correct_index": new_correct,
        "explanation": q["explanation"],
        "max_time_ms": int(max(8000, 15000 / difficulty)),
    }


async def llm_predict_failure(
    player_id: int,
    puzzle_type: str,
    attempt_count: int,
    time_to_fail_1_ms: float | None,
    time_to_fail_2_ms: float | None,
    metrics_history: list[dict] | None = None,
) -> dict:
    """Call the Qwen coaching model (qwen2.5:3b) to predict if player will fail again."""
    import httpx

    speed_change = None
    if time_to_fail_1_ms is not None and time_to_fail_2_ms is not None:
        if time_to_fail_1_ms > 0:
            speed_change = (time_to_fail_2_ms - time_to_fail_1_ms) / time_to_fail_1_ms
        else:
            speed_change = 0.0

    metrics_str = ""
    if metrics_history and len(metrics_history) > 0:
        last5 = metrics_history[-5:]
        metrics_str = "Recent metrics: " + json.dumps(last5)

    prompt = f"""You are an adaptive puzzle game AI. Analyze this player's performance pattern and predict if they will fail again.

Puzzle type: {puzzle_type}
Attempt count: {attempt_count}
Time to fail attempt 1: {time_to_fail_1_ms}ms
Time to fail attempt 2: {time_to_fail_2_ms}ms
Speed change: {speed_change} (positive = got slower, negative = got faster)

{metrics_str}

Respond with a JSON object ONLY:
{{"will_fail": bool, "confidence": float (0-1), "reasoning": "brief 1 sentence"}}"""

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.post(
                "http://89.58.33.163:11434/api/generate",
                json={
                    "model": "qwen2.5:3b",
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "num_predict": 80,
                        "temperature": 0.1,
                    },
                },
            )
            if resp.status_code == 200:
                text = resp.json().get("response", "")
                # Extract JSON
                import re
                json_match = re.search(r"\{.*\}", text, re.DOTALL)
                if json_match:
                    result = json.loads(json_match.group())
                    return {
                        "will_fail": result.get("will_fail", True),
                        "confidence": result.get("confidence", 0.5),
                        "reasoning": result.get("reasoning", "LLM analysis"),
                    }
    except Exception as e:
        pass

    # Fallback heuristic
    if speed_change is not None and speed_change < -0.3:
        # Got much faster — panic mode, likely to fail
        return {"will_fail": True, "confidence": 0.65, "reasoning": "Player is rushing (faster by >30%)."}
    if speed_change is not None and speed_change > 0.3:
        # Got slower — disengaging
        return {"will_fail": True, "confidence": 0.55, "reasoning": "Player is slowing down (>30% slower)."}
    if attempt_count >= 2:
        return {"will_fail": True, "confidence": 0.5, "reasoning": "Two consecutive failures. Default prediction."}
    return {"will_fail": False, "confidence": 0.3, "reasoning": "Insufficient data."}


def select_puzzle_type(
    previous_type: str | None,
    fail_count: int,
    available_types: list[str],
) -> str:
    """Select next puzzle type. Avoid repeats, prefer fresh types."""
    if fail_count >= 3 and previous_type:
        # Force switch
        others = [t for t in available_types if t != previous_type]
        if others:
            return random.choice(others)
    if previous_type and random.random() < 0.4:
        others = [t for t in available_types if t != previous_type]
        if others:
            return random.choice(others)
    return random.choice(available_types)


def generate_puzzle(puzzle_type: str, seq_length: int, difficulty: float) -> dict:
    """Dispatch to the appropriate puzzle generator."""
    generators = {
        "pattern_recall": generate_pattern_puzzle,
        "motion_tracking": generate_motion_puzzle,
        "spatial_golden": generate_spatial_puzzle,
    }
    gen = generators.get(puzzle_type)
    if gen:
        if puzzle_type == "spatial_golden":
            return gen(difficulty)
        return gen(seq_length, difficulty)
    return generate_pattern_puzzle(seq_length, difficulty)


def compute_fibonacci_timing(base_ms: int, difficulty: float, index: int = 0) -> int:
    """Compute timing with fibonacci/golden ratio influence."""
    return max(80, int(base_ms / (difficulty * math.pow(PHI, -index + 1))))