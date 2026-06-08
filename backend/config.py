#!/usr/bin/env python3
"""Echo - NeuroFlux Configuration

Central constants for the dynamic puzzle engine.
"""

from pathlib import Path
import secrets

# ── Paths ──
BASE_DIR = Path(__file__).parent
DB_PATH = BASE_DIR / "echo.db"

# ── JWT Auth ──
SECRET_KEY = secrets.token_hex(32)
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 1440  # 24 hours

# ── Old engine constants (kept for surface reference) ──
DIFFICULTY_FLOOR = 0.5
DIFFICULTY_CEILING = 5.0
BASELINE_DIFFICULTY = 1.0
STRUGGLE_WINDOW_SECONDS = 60
ERROR_THRESHOLD = 2
INPUT_LATENCY_SPIKE_MS = 2000
MASTERY_WINDOW_SIZE = 7
MASTERY_SUCCESS_RATE = 0.8

# ── Dynamic puzzle constants ──
PUZZLE_TYPES = [
    "pattern_recognition",
    "psychology_question",
    "spatial_logic",
    "sequence_memory",
    "timing_challenge",
]

# Max times to retry generation of same puzzle type before switching
MAX_GENERATION_RETRIES = 3

# Timeouts
PUZZLE_GENERATION_TIMEOUT = 60  # LLM call timeout
COACHING_TIMEOUT = 30
PREDICTION_TIMEOUT = 30

# ── Fibonacci progression (cosmetic only) ──
FIB_RULES = {
    1: (3, "Narrow — memorize 3-note patterns"),
    2: (5, "Standard — 5-note sequences"),
    3: (8, "Expanded — 8-item challenges"),
    4: (13, "Advanced — recognize 13 elements"),
    5: (21, "Master — 21-step complex patterns"),
}


def get_fib_rule(level: int) -> tuple[int, str]:
    """Get the Fibonacci rule for a given level."""
    key = min(level, max(FIB_RULES.keys()))
    if key not in FIB_RULES:
        return (3, "Narrow")
    return FIB_RULES[key]


# ── Color themes ──
COLOR_MAP = {
    "stable_idle": "#1a1a2e",
    "stable": "#16213e",
    "struggle": "#2d1b2a",
    "skill_gap": "#1b1b2f",
    "flow": "#1a2e1a",
    "success_burst": "#2ecc71",
    "fail": "#e94560",
    "hint": "#ffd700",
    "fibonacci": "#00d4ff",
    "psychology": "#b388ff",
}

# ── Canvas ──
CANVAS_W = 800
CANVAS_H = 600

PUZZLE_AREA = {"x": 50, "y": 50, "w": 700, "h": 400}
HINT_AREA = {"x": 50, "y": 480, "w": 700, "h": 80}
FEEDBACK_AREA = {"x": 50, "y": 420, "w": 700, "h": 50}