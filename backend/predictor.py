#!/usr/bin/env python3
"""
Echo v2 - Predictive Fail Detection Engine
Analyzes player performance metrics to predict if they'll fail the current puzzle,
and decides when to switch to a different puzzle type.
"""

import json
import math
import random
from typing import Any


class FailPredictor:
    """
    Analyzes attempt history to predict failure and trigger puzzle switches.

    Rules:
    - If player fails same puzzle 2 times: analyze metrics
    - If LLM predicts they'd fail on a 3rd showing, generate new puzzle
    - If they actually fail 3rd time: forced puzzle switch
    """

    def __init__(self, llm_client=None):
        self.llm_client = llm_client

    def analyze_attempts(self, attempts: list[dict]) -> dict:
        """
        Analyze a list of attempt dicts for the same puzzle.
        
        Returns:
            dict with: fail_predicted (bool), confidence (float), 
                       metrics_summary, recommendation
        """
        if len(attempts) < 2:
            return {"prediction": False, "confidence": 0, "reason": "not_enough_data"}

        # Sort by attempt_number
        attempts = sorted(attempts, key=lambda a: a.get("attempt_number", 0))

        times = [a.get("time_taken_ms", 0) or 0 for a in attempts]
        correct_flags = [a.get("is_correct", False) for a in attempts]
        hesitation = [a.get("hesitation_ms", 0) or 0 for a in attempts]

        # Trend: are they getting faster or slower?
        if len(times) >= 2 and times[-1] > times[0]:
            speed_trend = "slowing_down"
        elif len(times) >= 2:
            speed_trend = "speeding_up"
        else:
            speed_trend = "stable"

        # Are they hesitating more?
        if len(hesitation) >= 2 and hesitation[-1] > hesitation[0] * 1.3:
            hesitation_trend = "increasing"
        elif len(hesitation) >= 2 and hesitation[-1] < hesitation[0] * 0.7:
            hesitation_trend = "decreasing"
        else:
            hesitation_trend = "stable"

        # Did they all fail?
        all_failed = all(not c for c in correct_flags)

        # Score = weighted combination
        fail_score = 0.0
        reasons = []

        if all_failed:
            fail_score += 0.5
            reasons.append("all_attempts_failed")

        if speed_trend == "slowing_down":
            fail_score += 0.2
            reasons.append("slowing_down")

        if hesitation_trend == "increasing":
            fail_score += 0.2
            reasons.append("hesitation_increasing")

        # Speed variance high = inconsistent = likely to fail
        if len(times) >= 2:
            avg_time = sum(times) / len(times)
            variance = sum((t - avg_time) ** 2 for t in times) / len(times)
            std_dev = math.sqrt(variance)
            if avg_time > 0 and std_dev / avg_time > 0.5:
                fail_score += 0.1
                reasons.append("high_variance")

        confidence = min(1.0, fail_score + 0.3)  # Base confidence
        prediction = confidence > 0.6

        return {
            "prediction": prediction,
            "confidence": round(confidence, 2),
            "speed_trend": speed_trend,
            "hesitation_trend": hesitation_trend,
            "all_failed": all_failed,
            "attempt_count": len(attempts),
            "reasons": reasons,
            "recommendation": "switch_puzzle" if prediction or len(attempts) >= 3 else "retry",
        }

    def predict_with_llm(self, attempts: list[dict], llm_client) -> dict:
        """
        Use the LLM to make a more nuanced prediction.
        Returns None if LLM unavailable, else prediction dict.
        """
        if not llm_client:
            return None

        try:
            summary = {
                "attempts": len(attempts),
                "correct": sum(1 for a in attempts if a.get("is_correct")),
                "avg_time_ms": sum(a.get("time_taken_ms", 0) or 0 for a in attempts) / max(len(attempts), 1),
                "avg_hesitation_ms": sum(a.get("hesitation_ms", 0) or 0 for a in attempts) / max(len(attempts), 1),
                "speed_trend": "increasing" if len(attempts) >= 2 and attempts[-1].get("time_taken_ms", 0) > attempts[0].get("time_taken_ms", 0) else "decreasing_or_stable",
            }

            prompt = f"""Given this player data for a puzzle attempt, predict: will they fail if shown this puzzle again?

Player data:
- Total attempts: {summary['attempts']}
- Correct attempts: {summary['correct']}
- Average time per attempt: {summary['avg_time_ms']:.0f}ms
- Average hesitation: {summary['avg_hesitation_ms']:.0f}ms
- Speed trend: {summary['speed_trend']}

Respond with ONLY a JSON object: {{"will_fail": true/false, "confidence": 0.0-1.0, "reason": "brief reason"}}"""

            hint, source, latency = llm_client(
                error_type="fail_prediction",
                attempt_count=summary["attempts"],
                state="struggle",
                player_speed="slow" if summary["avg_time_ms"] > 2000 else "normal",
            )

            if hint:
                try:
                    # Extract JSON from LLM response
                    llm_response = json.loads(hint)
                    return {
                        "prediction": llm_response.get("will_fail", True),
                        "confidence": llm_response.get("confidence", 0.5),
                        "reason": llm_response.get("reason", "llm_analysis"),
                        "source": "llm",
                    }
                except (json.JSONDecodeError, TypeError):
                    pass

            return None
        except Exception:
            return None

    def get_next_puzzle_type(self, current_type: str, fail_count: int, level: int) -> str:
        """
        Choose the next puzzle type when switching.
        Avoids the same type consecutively.
        """
        from puzzles import PUZZLE_TYPES
        available = [t for t in PUZZLE_TYPES if t != current_type]

        # If failing a lot, switch to psychology (lower cognitive load)
        if fail_count >= 3:
            return "psychology_question"

        # Rotate through types
        idx = (PUZZLE_TYPES.index(current_type) + 1) % len(PUZZLE_TYPES)
        return PUZZLE_TYPES[idx]