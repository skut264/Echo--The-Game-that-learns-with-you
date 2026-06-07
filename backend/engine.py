#!/usr/bin/env python3
"""Echo - NeuroFlux v1 Adaptive Game Engine (Heuristic Core)

The brain of the game. No ML, no φ, no pseudoscience.
Just sliding windows, state machines, and data-driven thresholds.

Three states:
  - stable:   Player is performing normally
  - struggle: Player is hitting a wall but trying harder
  - skill_gap: Player is giving up (increasing time between attempts)
"""

from __future__ import annotations
import time
import json
from dataclasses import dataclass, field
from typing import Literal
from config import (
    STRUGGLE_WINDOW_SECONDS, ERROR_THRESHOLD, INPUT_LATENCY_SPIKE_MS,
    MASTERY_WINDOW_SIZE, MASTERY_SUCCESS_RATE,
    DIFFICULTY_FLOOR, DIFFICULTY_CEILING, BASELINE_DIFFICULTY,
    FIB_RULES, get_fib_rule,
)

PlayerState = Literal["stable", "struggle", "skill_gap"]


@dataclass
class AttemptSnapshot:
    """Minimal data for heuristic decisions — no DB dependency."""
    is_correct: bool
    time_per_note_ms: float
    input_latency_ms: float
    timestamp: float = field(default_factory=time.time)


@dataclass
class LayerState:
    """State of a single game mechanics layer."""
    disabled: bool = False
    speed_multiplier: float = 1.0
    feedback_boost: bool = False
    time_multiplier: float = 1.0


@dataclass
class LevelState:
    """The current level configuration."""
    level: int = 1
    sequence_length: int = 3
    difficulty: float = 1.0
    consecutive_wins: int = 0
    consecutive_losses: int = 0
    total_attempts: int = 0
    correct_attempts: int = 0
    last_state: PlayerState = "stable"
    layers: dict = field(default_factory=lambda: {
        "timing": LayerState(),
        "patterns": LayerState(),
        "rules": LayerState(),
    })

    @property
    def win_rate_window(self) -> float:
        """Win rate over last MASTERY_WINDOW_SIZE attempts."""
        if self.total_attempts == 0:
            return 0.0
        window = min(self.total_attempts, MASTERY_WINDOW_SIZE)
        # Use rolling window from recent attempts
        return self.correct_attempts / max(self.total_attempts, 1)


class AdaptiveGameEngine:
    """
    The core heuristic engine.

    Usage:
        engine = AdaptiveGameEngine()
        engine.process_attempt(snapshot)  # after every player attempt
        engine.state                       # current PlayerState
        engine.level_state                 # current LevelState
    """

    def __init__(self):
        self.level_state = LevelState()
        self._attempts: list[AttemptSnapshot] = []
        self._recovery_streak: int = 0

    @property
    def state(self) -> PlayerState:
        return self._detect_state()

    def _detect_state(self) -> PlayerState:
        """Detect struggle vs skill_gap vs stable using sliding window."""
        recent = [a for a in self._attempts
                  if a.timestamp > time.time() - STRUGGLE_WINDOW_SECONDS]

        if len(recent) < ERROR_THRESHOLD:
            return "stable"

        errors = [a for a in recent if not a.is_correct]
        if len(errors) < ERROR_THRESHOLD:
            return "stable"

        # Check input latency spike (fatigue/confusion)
        latencies = [a.input_latency_ms for a in recent[-5:]]
        avg_latency = sum(latencies) / max(len(latencies), 1)
        if avg_latency > INPUT_LATENCY_SPIKE_MS:
            return "skill_gap"

        # Distinguish: struggle = speeding up (trying harder)
        #              skill_gap = slowing down (giving up)
        if len(errors) >= 3:
            times = [e.timestamp for e in errors[-3:]]
            deltas = [times[i+1] - times[i] for i in range(len(times)-1)]
            if len(deltas) >= 1 and deltas[-1] > (deltas[0] if len(deltas) > 1 else deltas[0] + 1):
                return "skill_gap"

        return "struggle"

    def process_attempt(self, attempt: AttemptSnapshot) -> dict:
        """
        Process an attempt and return adjustment instructions.

        Returns:
            dict with keys:
              - state: current PlayerState
              - difficulty_adjustment: multiplier change (e.g. 0.92)
              - action: what to do ("none", "rubber_band", "scale_up")
              - coaching: hint key to show (if any)
              - layers: updated LayerState dict
        """
        self._attempts.append(attempt)
        self.level_state.total_attempts += 1
        if attempt.is_correct:
            self.level_state.correct_attempts += 1
            self.level_state.consecutive_wins += 1
            self.level_state.consecutive_losses = 0
        else:
            self.level_state.consecutive_wins = 0
            self.level_state.consecutive_losses += 1

        state = self._detect_state()
        self.level_state.last_state = state

        result = {
            "state": state,
            "difficulty_adjustment": 1.0,
            "action": "none",
            "coaching": None,
            "layer_updates": {},
        }

        if state == "struggle":
            # Small nudge: increase feedback, slight speed relief
            self.level_state.difficulty = max(
                self.level_state.difficulty * 0.92,
                DIFFICULTY_FLOOR,
            )
            result["difficulty_adjustment"] = 0.92
            result["action"] = "rubber_band"
            result["layer_updates"] = {
                "timing": {"feedback_boost": True, "speed_multiplier": 0.85},
            }
            result["coaching"] = "struggle"
            self._recovery_streak = 0

        elif state == "skill_gap":
            # Bigger nudge: remove timing pressure, more time
            self.level_state.difficulty = max(
                self.level_state.difficulty * 0.80,
                DIFFICULTY_FLOOR,
            )
            result["difficulty_adjustment"] = 0.80
            result["action"] = "rubber_band"
            result["layer_updates"] = {
                "timing": {"disabled": True, "time_multiplier": 1.5},
                "patterns": {"feedback_boost": True},
            }
            result["coaching"] = "skill_gap"
            self._recovery_streak = 0

        else:
            # Stable — check for mastery / recovery
            if self._check_mastery():
                self._scale_up()
                result["action"] = "scale_up"
                result["coaching"] = "new_level"
                # Trigger new rule reveal
                rule_info = get_fib_rule(self.level_state.level)
                result["new_rule"] = rule_info[1]
            else:
                # Drift back toward baseline
                if self.level_state.difficulty < BASELINE_DIFFICULTY:
                    self.level_state.difficulty = min(
                        self.level_state.difficulty + 0.05,
                        BASELINE_DIFFICULTY,
                    )
                if self.level_state.difficulty > BASELINE_DIFFICULTY and self.level_state.consecutive_wins >= 3:
                    self.level_state.difficulty = max(
                        self.level_state.difficulty - 0.05,
                        BASELINE_DIFFICULTY,
                    )

            self._recovery_streak += 1
            result["difficulty_adjustment"] = (
                self.level_state.difficulty / max(
                    self.level_state.difficulty / result.get("difficulty_adjustment", 1.0),
                    0.01,
                )
            )

        return result

    def _check_mastery(self) -> bool:
        """Check if the player has achieved mastery to advance."""
        if self.level_state.total_attempts < MASTERY_WINDOW_SIZE:
            return False

        # Last 7 attempts
        recent = self._attempts[-MASTERY_WINDOW_SIZE:]
        correct = sum(1 for a in recent if a.is_correct)

        # Must have >= 80% success rate
        if correct / MASTERY_WINDOW_SIZE < MASTERY_SUCCESS_RATE:
            return False

        # Last 3 must be consecutive successes (no regression)
        if not all(a.is_correct for a in recent[-3:]):
            return False

        # Must be playing confidently (not just slow)
        times = [a.time_per_note_ms for a in recent[-3:] if a.is_correct]
        if times:
            avg_time = sum(times) / len(times)
            if avg_time > 3000:  # >3s per note = too slow
                return False

        return True

    def _scale_up(self):
        """Advance to next Fibonacci level."""
        self.level_state.level += 1
        rule_info = get_fib_rule(self.level_state.level)
        self.level_state.sequence_length = rule_info[0]

        # Re-enable any disabled layers
        for layer in self.level_state.layers.values():
            layer.disabled = False
            layer.speed_multiplier = 0.90
            layer.feedback_boost = False

        self.level_state.consecutive_wins = 0
        self.level_state.consecutive_losses = 0

    def get_dashboard_snapshot(self) -> dict:
        """Return current state for the metrics dashboard."""
        return {
            "level": self.level_state.level,
            "sequence_length": self.level_state.sequence_length,
            "difficulty": round(self.level_state.difficulty, 2),
            "state": self.state,
            "consecutive_wins": self.level_state.consecutive_wins,
            "total_attempts": self.level_state.total_attempts,
            "correct_attempts": self.level_state.correct_attempts,
            "win_rate": round(
                self.level_state.correct_attempts / max(self.level_state.total_attempts, 1), 3
            ),
            "recovery_streak": self._recovery_streak,
        }