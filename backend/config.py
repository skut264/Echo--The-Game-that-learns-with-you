#!/usr/bin/env python3
"""Echo - NeuroFlux v1 Backend Configuration"""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

# Database
DATABASE_URL = f"sqlite:///{BASE_DIR}/echo.db"
DB_PATH = BASE_DIR / "echo.db"

# Auth
SECRET_KEY = os.environ.get("ECHO_SECRET_KEY", "echo-dev-secret-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days

# Game defaults
DEFAULT_GRID_SIZE = 3
INITIAL_DIFFICULTY = 1.0
DIFFICULTY_FLOOR = 0.6
DIFFICULTY_CEILING = 1.3
BASELINE_DIFFICULTY = 1.0

# Struggle detection
STRUGGLE_WINDOW_SECONDS = 60
ERROR_THRESHOLD = 3
INPUT_LATENCY_SPIKE_MS = 500

# Mastery threshold (5 out of 7)
MASTERY_WINDOW_SIZE = 7
MASTERY_SUCCESS_RATE = 0.80

# Fibonacci rule table
# Level -> (sequence_length, new_rule_description)
FIB_RULES = {
    0: (3, "Base: Match the pattern"),
    1: (3, "Base: Match the pattern"),
    2: (5, "Rule A: Notes have rhythm timing"),
    3: (5, "Rule B: Some notes are distractors (wrong color)"),
    5: (8, "Rule C: Moving targets — notes shift position"),
    8: (8, "Combo: Timing + Distractors + Movement"),
    13: (13, "Combo+: All rules + speed rapid fire"),
}

def get_fib_rule(level: int) -> tuple:
    """Look up the Fibonacci rule set for a given level.
    Returns the closest rule set at or below the level.
    """
    fib_keys = sorted(FIB_RULES.keys())
    applicable = 0
    for k in fib_keys:
        if k <= level:
            applicable = k
    return FIB_RULES[applicable]

# Colors
COLOR_MAP = {
    "stable_idle": "#1a1a2e",
    "stable_active": "#16213e",
    "struggle": "#2b2d42",
    "skill_gap": "#3b3b4f",
    "coaching": "#e8d5b7",
    "flow_success": "#e94560",
    "new_rule_reveal": "#ffd700",
}

# LLM
LLM_API_BASE = os.environ.get("OLLAMA_HOST", "http://89.58.33.163:11434")
LLM_MODEL = "qwen2.5:3b"
LLM_TIMEOUT_SECONDS = 2.0
LLM_FALLBACK_HINTS = {
    "timing": "Focus on the rhythm — each note has a beat.",
    "position": "Watch the sequence from start to end before tapping.",
    "distractor": "Ignore wrong colors — match the pattern, not the flash.",
    "calculation": "Take it one note at a time. Breathe between taps.",
    "generic": "You've got this. Slow down and watch the full sequence.",
}