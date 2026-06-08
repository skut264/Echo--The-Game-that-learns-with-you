#!/usr/bin/env python3
"""
Echo v2 - Puzzle Generator
Generates dynamic puzzles with Fibonacci sequence patterns, golden ratio aesthetics,
and multiple challenge types including multi-choice psychology/psychology questions.
"""

import json
import random
import math
from typing import Any

PHI = (1 + math.sqrt(5)) / 2  # Golden ratio ≈ 1.618


# ── Fibonacci helpers ──

def fib(n: int) -> int:
    """Return the nth Fibonacci number."""
    a, b = 0, 1
    for _ in range(n):
        a, b = b, a + b
    return a


def fib_close_to(target: int) -> int:
    """Return the Fibonacci number closest to target."""
    a, b = 0, 1
    while b < target:
        a, b = b, a + b
    return a if target - a < b - target else b


# ── Golden-ratio grid positions ──

def golden_positions(count: int, canvas_w: int, canvas_h: int) -> list[dict]:
    """Generate positions on a canvas following the golden spiral."""
    positions = []
    for i in range(count):
        angle = i * 2 * math.pi / PHI  # golden angle
        radius = min(canvas_w, canvas_h) * 0.4 * (1 - math.exp(-i / count))
        cx = canvas_w / 2 + radius * math.cos(angle)
        cy = canvas_h / 2 + radius * math.sin(angle)
        positions.append({"x": round(cx, 1), "y": round(cy, 1), "size": max(30, 80 - i * 3)})
    return positions


# ── Puzzle generators ──

def gen_pattern_sequence(level: int, difficulty: float) -> dict:
    """
    A pattern sequence puzzle.
    Difficulty scales sequence length (fib-based) and distractor count.
    """
    seq_len = fib_close_to(max(3, level + 2))
    seq_len = min(seq_len, 13)

    positions = golden_positions(seq_len, 600, 600)
    colors = [
        "#e94560", "#0f3460", "#533483", "#d4a5a5",
        "#2ecc71", "#3498db", "#f39c12", "#9b59b6",
        "#1abc9c", "#e67e22", "#34495e", "#16a085",
        "#c0392b",
    ]

    sequence = []
    fib_idx = 0
    for i in range(seq_len):
        note = {
            "index": i,
            "x": positions[i]["x"],
            "y": positions[i]["y"],
            "size": positions[i]["size"],
            "color": colors[i % len(colors)],
            "freq": 220 + fib(fib_idx + 3) * 20,  # Fibonacci frequencies
            "display_ms": max(200, 600 - int(difficulty * 100)),
        }
        sequence.append(note)
        fib_idx += 1

    # Distractors (wrong notes shown during display)
    num_distractors = min(seq_len - 1, int(difficulty * 2))
    distractor_indices = random.sample(range(seq_len), min(num_distractors, seq_len))

    return {
        "type": "pattern_sequence",
        "sequence_length": seq_len,
        "sequence": sequence,
        "distractor_indices": distractor_indices,
        "canvas_width": 600,
        "canvas_height": 600,
        "instructions": "Watch the pattern, then repeat it in order.",
        "display_speed_ms": max(200, 600 - int(difficulty * 100)),
        "fibonacci_motion": {
            "enabled": True,
            "spiral_growth": PHI,
            "golden_angle": 360 / PHI,
        },
    }


def gen_psychology_question(level: int, difficulty: float) -> dict:
    """
    A multiple-choice psychology/mind-bending question.
    3-4 options each with a weight (correctness score).
    """
    questions_pool = [
        {
            "question": "You see a new pattern forming. Your first instinct is to:",
            "options": [
                {"text": "Wait and analyze all possibilities", "weight": 1.0, "explanation": "Patience reveals structure."},
                {"text": "React immediately before it changes", "weight": 0.3, "explanation": "Speed without understanding leads to errors."},
                {"text": "Look for the underlying rule first", "weight": 0.8, "explanation": "Rules give you an edge."},
                {"text": "Guess and adjust based on feedback", "weight": 0.5, "explanation": "Learning by doing works, but costs time."},
            ],
            "category": "psychology",
        },
        {
            "question": "A sequence feels impossible. What do you do?",
            "options": [
                {"text": "Break it into smaller parts and master each", "weight": 1.0, "explanation": "Chunking is how the brain processes complexity."},
                {"text": "Try faster — maybe muscle memory helps", "weight": 0.2, "explanation": "Speed before accuracy compounds errors."},
                {"text": "Take a short mental break, then retry", "weight": 0.7, "explanation": "Rest resets cognitive load."},
                {"text": "Switch strategies entirely", "weight": 0.6, "explanation": "Flexibility is valuable but can be destabilizing."},
            ],
            "category": "psychology",
        },
        {
            "question": "How many squares can you draw with 9 dots in a 3x3 grid?",
            "options": [
                {"text": "6", "weight": 0.3, "explanation": "Not quite — look for diagonal squares too."},
                {"text": "9", "weight": 0.5, "explanation": "Close. You're only counting the obvious ones."},
                {"text": "14", "weight": 1.0, "explanation": "Correct! 6 small + 2 medium diagonal + 6 tilted."},
                {"text": "20", "weight": 0.1, "explanation": "Overcounting — there aren't that many connections."},
            ],
            "category": "perception",
        },
        {
            "question": "If it takes 10 people 10 hours to build 10 puzzles, how long does it take 1 person to build 1 puzzle?",
            "options": [
                {"text": "1 hour", "weight": 0.2, "explanation": "That's the intuitive trap. Think again."},
                {"text": "10 hours", "weight": 1.0, "explanation": "Correct. Rate: 1 puzzle per person per 10 hours."},
                {"text": "100 hours", "weight": 0.1, "explanation": "Overestimating — check the rate, not the total."},
                {"text": "It depends on coordination", "weight": 0.6, "explanation": "Partially right, but the math gives a clear answer."},
            ],
            "category": "logic",
        },
        {
            "question": "You are shown a sequence: ♠ ♥ ♦ ♣ ♠ ? What comes next?",
            "options": [
                {"text": "♥", "weight": 0.8, "explanation": "Pattern: suits cycle in order of card suits."},
                {"text": "♠", "weight": 0.3, "explanation": "That would be repeating the first element only."},
                {"text": "♣", "weight": 1.0, "explanation": "Correct! The pattern is: spade, heart, diamond, club, repeat."},
                {"text": "♦", "weight": 0.5, "explanation": "One step behind in the cycle."},
            ],
            "category": "pattern",
        },
        {
            "question": "A bat and a ball cost $1.10. The bat costs $1 more than the ball. How much does the ball cost?",
            "options": [
                {"text": "$0.05", "weight": 1.0, "explanation": "Correct! 1.05 + 0.05 = 1.10. The intuitive 0.10 trap is wrong."},
                {"text": "$0.10", "weight": 0.2, "explanation": "The classic cognitive bias trap. If ball=0.10, bat=1.10, total=1.20."},
                {"text": "$0.01", "weight": 0.1, "explanation": "Too low. Check the math again."},
                {"text": "$1.00", "weight": 0.3, "explanation": "Then the bat would be $2.00 — way over."},
            ],
            "category": "psychology",
        },
        {
            "question": "What do you notice first in a complex visual field?",
            "options": [
                {"text": "Movement and change", "weight": 1.0, "explanation": "Human peripheral vision is optimized for detecting motion."},
                {"text": "Bright colors", "weight": 0.6, "explanation": "Color pops, but motion detection is primary."},
                {"text": "Symmetry and patterns", "weight": 0.8, "explanation": "Pattern recognition is strong, but movement triggers first."},
                {"text": "Faces and social cues", "weight": 0.5, "explanation": "Face recognition is fast, but only in foveal vision."},
            ],
            "category": "psychology",
        },
    ]

    # Pick a question based on level/difficulty
    idx = (level + int(difficulty * 10)) % len(questions_pool)
    q = questions_pool[idx].copy()

    # Shuffle options order
    opts = q["options"]
    correct_weight = max(o["weight"] for o in opts)
    random.shuffle(opts)
    # After shuffle, track which now has the highest weight
    q["options"] = opts
    q["correct_index"] = next(i for i, o in enumerate(opts) if o["weight"] == correct_weight)
    q["type"] = "psychology_question"
    q["time_limit_seconds"] = max(10, 30 - int(difficulty * 8))

    return q


def gen_timing_challenge(level: int, difficulty: float) -> dict:
    """
    A timing/rhythm based challenge.
    Player must tap at the right moment.
    """
    fib_n = fib_close_to(max(3, level + 2))
    num_beats = min(fib_n, 8)

    beats = []
    for i in range(num_beats):
        interval = max(200, 800 - int(difficulty * 150))
        beats.append({
            "index": i,
            "delay_ms": interval * (i + 1),
            "expected_window_ms": max(100, 400 - int(difficulty * 50)),
            "freq": 220 + fib(i + 3) * 25,
            "label": chr(65 + i),  # A, B, C...
        })

    return {
        "type": "timing_challenge",
        "beats": beats,
        "sequence_length": num_beats,
        "instructions": "Tap in rhythm with the beats.",
        "total_duration_ms": sum(b["delay_ms"] for b in beats),
        "canvas_width": 600,
        "canvas_height": 600,
        "golden_ratio_pulse": True,
    }


def gen_spatial_logic(level: int, difficulty: float) -> dict:
    """
    A spatial arrangement puzzle using golden-ratio positions.
    """
    n_shapes = fib_close_to(max(4, level + 3))
    n_shapes = min(n_shapes, 12)

    positions = golden_positions(n_shapes, 600, 600)
    shapes = []
    for i, pos in enumerate(positions):
        shapes.append({
            "index": i,
            "x": pos["x"],
            "y": pos["y"],
            "size": pos["size"],
            "rotation": i * 137.5,  # Golden angle
            "type": random.choice(["circle", "hexagon", "square", "triangle"]),
            "color": f"hsl({i * 137.5 % 360}, 70%, 60%)",
        })

    # Rotate positions for the answer
    shift = random.randint(1, n_shapes - 1)
    correct_positions = [shapes[(i + shift) % n_shapes] for i in range(n_shapes)]

    return {
        "type": "spatial_logic",
        "shapes": shapes,
        "correct_order": [s["index"] for s in correct_positions],
        "sequence_length": n_shapes,
        "instructions": "Arrange these shapes in the correct spatial order.",
        "canvas_width": 600,
        "canvas_height": 600,
        "golden_ratio_positions": True,
    }


PUZZLE_GENERATORS = {
    "pattern_sequence": gen_pattern_sequence,
    "psychology_question": gen_psychology_question,
    "timing_challenge": gen_timing_challenge,
    "spatial_logic": gen_spatial_logic,
}

PUZZLE_TYPES = list(PUZZLE_GENERATORS.keys())


def get_puzzle_rotation(level: int) -> str:
    """Rotate through puzzle types based on level."""
    return PUZZLE_TYPES[(level - 1) % len(PUZZLE_TYPES)]


def generate_puzzle(level: int, difficulty: float, puzzle_type: str | None = None) -> dict:
    """Generate a puzzle of the given type, or rotate if None."""
    if puzzle_type is None:
        puzzle_type = get_puzzle_rotation(level)
    gen_fn = PUZZLE_GENERATORS.get(puzzle_type)
    if gen_fn is None:
        puzzle_type = "pattern_sequence"
        gen_fn = PUZZLE_GENERATORS[puzzle_type]
    return gen_fn(level, difficulty)