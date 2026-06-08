#!/usr/bin/env python3
"""Echo - NeuroFlux Dynamic Puzzle Engine

Replaces the old heuristic-only engine with:
- Dynamic puzzle generation via LLM
- Failure pattern tracking (time trends, speed deltas)
- LLM-based prediction of player failure
- Puzzle auto-rotation after 3 failures on same puzzle
- Fibonacci sequence + golden ratio decorative data
- Psychology question generation with weighted options
- Full-canvas spatial layout data
- Enhanced metrics collection for real-time training
"""

from __future__ import annotations
import time
import json
import math
import random
from dataclasses import dataclass, field
from typing import Literal, Any

PlayerState = Literal["stable", "struggle", "skill_gap"]

# ── Dynamic Puzzle Types ──

PUZZLE_TYPES = Literal[
    "pattern_recognition",
    "psychology_question",
    "spatial_logic",
    "sequence_memory",
    "timing_challenge",
]


# ── Dataclasses ──

@dataclass
class PuzzleFailureRecord:
    """Tracks failures for the current puzzle attempt cycle."""
    puzzle_id: str
    puzzle_type: str
    failures: int = 0
    first_fail_time_ms: float | None = None    # time from puzzle show to first fail
    second_fail_time_ms: float | None = None   # time from puzzle show to second fail
    fail_timestamps: list[float] = field(default_factory=list)
    fail_decision_times: list[float] = field(default_factory=list)  # how fast they chose an answer
    is_failing_faster: bool | None = None      # True = getting faster at failing (bad — guessing)
    is_failing_slower: bool | None = None      # True = taking longer (hesitating — skill gap)
    predicted_will_fail_again: bool | None = None  # LLM prediction

    def record_failure(self, time_to_show_ms: float, decision_time_ms: float):
        self.failures += 1
        self.fail_timestamps.append(time.time())
        self.fail_decision_times.append(decision_time_ms)
        if self.first_fail_time_ms is None:
            self.first_fail_time_ms = time_to_show_ms
        elif self.second_fail_time_ms is None:
            self.second_fail_time_ms = time_to_show_ms

    def analyze_trend(self) -> dict:
        """Analyze whether the player is getting faster or slower at failing."""
        if len(self.fail_decision_times) < 2:
            return {"trend": "insufficient_data", "speed_delta": 0.0}

        times = self.fail_decision_times
        first_avg = times[0]
        last_avg = times[-1]

        speed_delta = last_avg - first_avg  # positive = slower, negative = faster

        if abs(speed_delta) < 200:  # <200ms difference = stable
            trend = "stable"
        elif speed_delta < 0:
            trend = "faster_at_failing"
            self.is_failing_faster = True
        else:
            trend = "slower_at_failing"
            self.is_failing_slower = True

        return {
            "trend": trend,
            "speed_delta_ms": round(speed_delta, 1),
            "first_time_to_fail_ms": round(self.first_fail_time_ms or 0, 1),
            "second_time_to_fail_ms": round(self.second_fail_time_ms or 0, 1),
        }

    def needs_rotation(self) -> bool:
        """After 3 consecutive failures on the same puzzle, rotate."""
        return self.failures >= 3


@dataclass
class FibonacciDecoration:
    """Fibonacci spiral + golden ratio data for canvas placement."""
    spiral_points: list[dict] = field(default_factory=list)  # [{x, y, radius, angle}]
    golden_rectangles: list[dict] = field(default_factory=list)
    phi: float = 1.618033988749895

    @classmethod
    def generate(cls, canvas_w: int, canvas_h: int, count: int = 5) -> FibonacciDecoration:
        """Generate Fibonacci spiral points within the canvas bounds."""
        points = []
        rects = []
        phi = 1.618033988749895
        center_x, center_y = canvas_w / 2, canvas_h / 2

        a, b = 1, 1  # Fibonacci seed
        for i in range(count):
            # Place spirals at golden-ratio positions
            angle = (i * 137.5) % 360  # Golden angle in degrees
            rad = math.radians(angle)
            # Golden spiral grows by phi each revolution
            radius = 20 + (b * 8)

            # Distribute across canvas using golden ratio
            px = center_x + math.cos(rad) * radius * (i * 0.5)
            py = center_y + math.sin(rad) * radius * (i * 0.5)

            # Clamp to canvas
            px = max(10, min(canvas_w - 10, px))
            py = max(10, min(canvas_h - 10, py))

            points.append({
                "x": round(px, 1),
                "y": round(py, 1),
                "radius": round(radius, 1),
                "angle_deg": round(angle, 1),
                "fib_n": b,
                "opacity": max(0.1, 1.0 - (i * 0.12)),
            })

            # Generate golden rectangles
            rx = center_x + math.cos(rad) * radius * (i * 0.3)
            ry = center_y + math.sin(rad) * radius * (i * 0.3)
            w = 30 + b * 6
            h = w / phi
            rects.append({
                "x": round(rx, 1),
                "y": round(ry, 1),
                "w": round(w, 1),
                "h": round(h, 1),
                "rotation_deg": round(angle, 1),
            })

            a, b = b, a + b  # Next Fibonacci

        return cls(spiral_points=points, golden_rectangles=rects)


@dataclass
class CanvasLayout:
    """Defines where UI elements sit on the full canvas."""
    canvas_w: int = 800
    canvas_h: int = 600
    puzzle_area: dict = field(default_factory=lambda: {"x": 50, "y": 50, "w": 700, "h": 400})
    hint_area: dict = field(default_factory=lambda: {"x": 50, "y": 480, "w": 700, "h": 80})
    feedback_area: dict = field(default_factory=lambda: {"x": 50, "y": 420, "w": 700, "h": 50})
    fibonacci_decoration: FibonacciDecoration = field(default_factory=lambda: FibonacciDecoration.generate(800, 600))

    def scatter_positions(self, count: int, margin: int = 60) -> list[dict]:
        """Generate scattered positions using golden ratio for visual spread."""
        positions = []
        phi = 1.618033988749895
        area_w = self.puzzle_area["w"] - 2 * margin
        area_h = self.puzzle_area["h"] - 2 * margin
        base_x = self.puzzle_area["x"] + margin
        base_y = self.puzzle_area["y"] + margin

        for i in range(count):
            # Use golden angle for even distribution
            angle = math.radians(i * 137.508)
            radius = (i / max(count, 1)) * min(area_w, area_h) * 0.4
            x = base_x + area_w / 2 + math.cos(angle) * radius
            y = base_y + area_h / 2 + math.sin(angle) * radius
            x = max(base_x, min(base_x + area_w, x))
            y = max(base_y, min(base_y + area_h, y))
            positions.append({"x": round(x), "y": round(y)})

        return positions


@dataclass
class DynamicPuzzle:
    """A dynamically generated puzzle with full metadata."""
    puzzle_id: str
    puzzle_type: PUZZLE_TYPES
    prompt: str                           # The challenge text / question
    options: list[dict] | None = None     # For psych questions: [{text, weight}]
    correct_answer: str | None = None
    answer_positions: list[dict] = field(default_factory=list)  # Golden-ratio placed on canvas
    canvas_layout: CanvasLayout = field(default_factory=CanvasLayout)
    fibonacci_data: FibonacciDecoration = field(default_factory=lambda: FibonacciDecoration.generate(800, 600))
    time_limit_ms: int = 15000
    metadata: dict = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    failure_record: PuzzleFailureRecord | None = None

    @classmethod
    def from_llm(cls, puzzle_type: str, llm_data: dict) -> DynamicPuzzle:
        """Create a puzzle from LLM-generated data."""
        canvas = CanvasLayout()
        fib = FibonacciDecoration.generate(canvas.canvas_w, canvas.canvas_h)
        puzzle_id = f"{puzzle_type}_{int(time.time() * 1000)}_{random.randint(100, 999)}"

        options = llm_data.get("options")
        positions = canvas.scatter_positions(len(options) if options else 4)

        return cls(
            puzzle_id=puzzle_id,
            puzzle_type=puzzle_type,
            prompt=llm_data.get("prompt", ""),
            options=options,
            correct_answer=llm_data.get("correct_answer"),
            answer_positions=positions,
            canvas_layout=canvas,
            fibonacci_data=fib,
            time_limit_ms=llm_data.get("time_limit_ms", 15000),
            metadata=llm_data.get("metadata", {}),
            failure_record=PuzzleFailureRecord(
                puzzle_id=puzzle_id,
                puzzle_type=puzzle_type,
            ),
        )


# ── Enhanced Attempt Snapshot ──

@dataclass
class AttemptSnapshot:
    """Full telemetry for one player attempt."""
    is_correct: bool
    time_per_note_ms: float               # How long puzzle was visible before answer
    decision_time_ms: float               # Time to make the choice
    input_latency_ms: float
    hovered_options: list[str] = field(default_factory=list)  # Which options they hovered
    hover_durations_ms: list[float] = field(default_factory=list)
    option_selected: str | None = None
    puzzle_type: str | None = None
    puzzle_id: str | None = None
    timestamp: float = field(default_factory=time.time)


# ── Core Dynamic Engine ──

class DynamicPuzzleEngine:
    """
    The revamped engine handling:
    - Dynamic puzzle lifecycle (show, fail track, rotate)
    - Failure pattern analysis with speed deltas
    - LLM prediction queries
    - Canvas layout management
    - Player state detection per puzzle
    """

    def __init__(self):
        self._attempts: list[AttemptSnapshot] = []
        self._current_puzzle: DynamicPuzzle | None = None
        self._puzzle_history: list[DynamicPuzzle] = []  # Puzzles shown this session
        self._consecutive_puzzle_failures: int = 0
        self._total_puzzles_played: int = 0
        self._correct_puzzles: int = 0
        self._hesitation_score: float = 0.0  # Running average hesitation
        self._accuracy_trend: list[float] = []  # Rolling accuracy over time
        self._state: PlayerState = "stable"
        self._recovery_streak: int = 0
        self._streak: int = 0  # Win streak for flow detection

    @property
    def state(self) -> PlayerState:
        return self._state

    @property
    def streak(self) -> int:
        return self._streak

    @property
    def total_attempts(self) -> int:
        return len(self._attempts)

    @property
    def correct_attempts(self) -> int:
        return self._correct_puzzles

    def set_puzzle(self, puzzle: DynamicPuzzle):
        """Set the current active puzzle."""
        self._current_puzzle = puzzle
        self._puzzle_history.append(puzzle)

    def get_current_puzzle(self) -> DynamicPuzzle | None:
        return self._current_puzzle

    def process_attempt(self, attempt: AttemptSnapshot) -> dict:
        """Process a player's attempt on the current puzzle."""
        self._attempts.append(attempt)
        self._total_puzzles_played += 1

        result = {
            "state": "stable",
            "puzzle_action": "continue",
            "difficulty_adjustment": 1.0,
            "puzzle_should_rotate": False,
            "should_regenerate": False,
            "failure_analysis": {},
            "fibonacci_data": None,
            "canvas_layout": None,
            "new_puzzle": None,
        }

        if attempt.is_correct:
            self._correct_puzzles += 1
            self._streak += 1
            self._recovery_streak += 1
            self._consecutive_puzzle_failures = 0
            result["state"] = "stable"
            result["puzzle_action"] = "next_puzzle"
            # Generate new puzzle proactively for next round
            return result

        # ── Failure path ──
        self._streak = 0
        puzzle = self._current_puzzle
        if puzzle and puzzle.failure_record:
            record = puzzle.failure_record
            record.record_failure(
                time_to_show_ms=attempt.time_per_note_ms,
                decision_time_ms=attempt.decision_time_ms,
            )
            analysis = record.analyze_trend()
            result["failure_analysis"] = analysis

            # Track hesitation — if they're taking longer each time
            if analysis.get("trend") == "slower_at_failing":
                self._hesitation_score += 0.2
                result["state"] = "skill_gap"
            elif analysis.get("trend") == "faster_at_failing":
                self._hesitation_score = max(0, self._hesitation_score - 0.1)
                result["state"] = "struggle"

            # Check if needs regeneration (LLM prediction)
            if record.failures >= 2:
                result["should_regenerate"] = True

            # Check if needs rotation (>3 failures)
            if record.needs_rotation():
                result["puzzle_should_rotate"] = True
                result["puzzle_action"] = "rotate"
                self._consecutive_puzzle_failures = 0
            else:
                self._consecutive_puzzle_failures = record.failures

        # Attach fibonacci decoration + canvas for client rendering
        if puzzle:
            result["fibonacci_data"] = {
                "points": [vars(p) if hasattr(p, '__dict__') else p for p in puzzle.fibonacci_data.spiral_points],
                "rects": puzzle.fibonacci_data.golden_rectangles,
                "phi": puzzle.fibonacci_data.phi,
            }
            result["canvas_layout"] = {
                "w": puzzle.canvas_layout.canvas_w,
                "h": puzzle.canvas_layout.canvas_h,
                "puzzle_area": puzzle.canvas_layout.puzzle_area,
                "hint_area": puzzle.canvas_layout.hint_area,
                "feedback_area": puzzle.canvas_layout.feedback_area,
            }
            result["answer_positions"] = puzzle.answer_positions

        return result

    def get_prediction_context(self) -> dict:
        """Build context for LLM prediction: will the player fail again?"""
        if not self._current_puzzle or not self._current_puzzle.failure_record:
            return {"prediction": "insufficient_data"}

        record = self._current_puzzle.failure_record
        analysis = record.analyze_trend()

        # Look at overall session trends
        recent = self._attempts[-10:] if len(self._attempts) >= 10 else self._attempts
        recent_correct = sum(1 for a in recent if a.is_correct)
        recent_rate = recent_correct / max(len(recent), 1)

        avg_decision = sum(a.decision_time_ms for a in recent) / max(len(recent), 1)
        avg_hesitation = sum(a.hover_durations_ms for a in recent if a.hover_durations_ms) / max(
            sum(1 for a in recent if a.hover_durations_ms), 1
        )

        return {
            "puzzle_type": record.puzzle_type,
            "failures_so_far": record.failures,
            "first_fail_time_ms": record.first_fail_time_ms,
            "second_fail_time_ms": record.second_fail_time_ms,
            "trend": analysis["trend"],
            "speed_delta_ms": analysis["speed_delta_ms"],
            "recent_accuracy_window": round(recent_rate, 3),
            "avg_decision_time_ms": round(avg_decision, 1),
            "average_hesitation_ms": round(avg_hesitation, 1),
            "total_attempts_session": self._total_puzzles_played,
            "total_correct_session": self._correct_puzzles,
            "consecutive_streak": self._streak,
        }

    def get_dashboard_snapshot(self) -> dict:
        """Return current state for the player dashboard."""
        recent = self._attempts[-20:] if len(self._attempts) >= 20 else self._attempts
        recent_correct = sum(1 for a in recent if a.is_correct)
        win_rate = self._correct_puzzles / max(self._total_puzzles_played, 1)

        # Decision time trend
        decision_times = [a.decision_time_ms for a in recent if a.decision_time_ms > 0]
        avg_decision = sum(decision_times) / max(len(decision_times), 1) if decision_times else 0

        # Hesitation (hover time) trend
        hover_times = [sum(a.hover_durations_ms) / max(len(a.hover_durations_ms), 1)
                      for a in recent if a.hover_durations_ms]
        avg_hesitation = sum(hover_times) / max(len(hover_times), 1) if hover_times else 0

        return {
            "total_attempts": self._total_puzzles_played,
            "correct_attempts": self._correct_puzzles,
            "win_rate": round(win_rate, 3),
            "state": self.state,
            "streak": self._streak,
            "recovery_streak": self._recovery_streak,
            "avg_decision_time_ms": round(avg_decision, 1),
            "avg_hesitation_ms": round(avg_hesitation, 1),
            "recent_window_accuracy": round(recent_correct / max(len(recent), 1), 3),
            "hesitation_score": round(self._hesitation_score, 2),
            "current_puzzle_type": self._current_puzzle.puzzle_type if self._current_puzzle else None,
        }