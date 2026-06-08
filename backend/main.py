#!/usr/bin/env python3
"""Echo - NeuroFlux Dynamic Puzzle API

Complete FastAPI backend with:
- Dynamic puzzle generation via LLM
- Failure pattern tracking and prediction
- Puzzle rotation on 3 failures
- LLM-based coaching
- Enhanced dashboard with puzzle-centric metrics
"""

import json
import time
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
import models
import auth
from config import COLOR_MAP, PUZZLE_TYPES
from engine import DynamicPuzzleEngine, DynamicPuzzle, AttemptSnapshot
import puzzle_generator


# ── Auth ──
security = HTTPBearer(auto_error=False)


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    if credentials is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    payload = auth.decode_access_token(credentials.credentials)
    if payload is None:
        raise HTTPException(status_code=401, detail="Invalid token")
    player = models.get_player_by_id(payload.get("sub"))
    if player is None:
        raise HTTPException(status_code=401, detail="User not found")
    return player


# ── Engine store (in-memory, per active player) ──
_active_engines: dict[int, DynamicPuzzleEngine] = {}
_active_sessions: dict[int, int] = {}  # player_id -> session_id
_active_puzzles: dict[int, DynamicPuzzle] = {}  # player_id -> current puzzle

# Track puzzle type rotation to avoid same type twice
_last_puzzle_types: dict[int, str] = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    models.init_db()
    yield


app = FastAPI(title="Echo - NeuroFlux Dynamic", version="2.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Schemas ──

class RegisterRequest(BaseModel):
    username: str
    email: EmailStr
    password: str


class LoginRequest(BaseModel):
    username: str
    password: str


class AttemptRequest(BaseModel):
    puzzle_id: str
    puzzle_type: str
    prompt: str | None = None
    correct_answer: str | None = None
    is_correct: bool
    decision_time_ms: float | None = None
    time_visible_ms: float | None = None
    input_latency_ms: float | None = None
    option_selected: str | None = None
    hovered_options: list[str] = []
    hover_durations_ms: list[float] = []
    puzzle_attempt_count: int = 1
    canvas_positions: list | None = None


# ── Auth endpoints ──

@app.post("/api/register")
def register(req: RegisterRequest):
    if models.get_player_by_username(req.username):
        raise HTTPException(400, "Username already exists")
    if models.get_player_by_email(req.email):
        raise HTTPException(400, "Email already exists")

    pwd_hash = auth.hash_password(req.password)
    player_id = models.create_player(req.username, req.email, pwd_hash)
    token = auth.create_access_token({"sub": player_id, "username": req.username})
    return {"token": token, "player_id": player_id, "username": req.username}


@app.post("/api/login")
def login(req: LoginRequest):
    player = models.get_player_by_username(req.username)
    if not player or not auth.verify_password(req.password, player["password_hash"]):
        raise HTTPException(401, "Invalid credentials")

    token = auth.create_access_token({"sub": player["id"], "username": player["username"]})
    return {"token": token, "player_id": player["id"], "username": player["username"]}


# ── Puzzle generation helper ──

def _pick_puzzle_type(player_id: int, force_type: str | None = None) -> str:
    """Pick a puzzle type, avoiding the last one used."""
    last_type = _last_puzzle_types.get(player_id)
    if force_type:
        return force_type
    available = [t for t in PUZZLE_TYPES if t != last_type]
    if not available:
        available = PUZZLE_TYPES
    chosen = __import__("random").choice(available)
    _last_puzzle_types[player_id] = chosen
    return chosen


def _get_player_context(player_id: int, engine: DynamicPuzzleEngine) -> dict:
    """Build player context for puzzle personalization."""
    snapshot = engine.get_dashboard_snapshot()
    return {
        "total_attempts": snapshot["total_attempts"],
        "correct_attempts": snapshot["correct_attempts"],
        "win_rate": snapshot["win_rate"],
        "state": snapshot["state"],
        "streak": snapshot["streak"],
        "avg_decision_time_ms": snapshot["avg_decision_time_ms"],
    }


# ── Game endpoints ──

@app.post("/api/game/start")
async def start_game(player: dict = Depends(get_current_user)):
    """Start a new game session with dynamic puzzles."""
    pid = player["id"]
    session_id = models.create_session(pid)

    engine = DynamicPuzzleEngine()
    _active_engines[pid] = engine
    _active_sessions[pid] = session_id
    _last_puzzle_types.pop(pid, None)

    # Generate first puzzle
    puzzle_type = _pick_puzzle_type(pid)
    player_ctx = _get_player_context(pid, engine)
    llm_data = puzzle_generator.generate_puzzle(puzzle_type, player_ctx)
    puzzle = DynamicPuzzle.from_llm(puzzle_type, llm_data)
    engine.set_puzzle(puzzle)
    _active_puzzles[pid] = puzzle

    return {
        "session_id": session_id,
        "puzzle": {
            "puzzle_id": puzzle.puzzle_id,
            "puzzle_type": puzzle.puzzle_type,
            "prompt": puzzle.prompt,
            "options": puzzle.options,
            "time_limit_ms": puzzle.time_limit_ms,
            "metadata": puzzle.metadata,
            "answer_positions": puzzle.answer_positions,
            "fibonacci_data": {
                "points": puzzle.fibonacci_data.spiral_points,
                "rects": puzzle.fibonacci_data.golden_rectangles,
                "phi": puzzle.fibonacci_data.phi,
            },
            "canvas_layout": {
                "w": puzzle.canvas_layout.canvas_w,
                "h": puzzle.canvas_layout.canvas_h,
                "puzzle_area": puzzle.canvas_layout.puzzle_area,
                "hint_area": puzzle.canvas_layout.hint_area,
                "feedback_area": puzzle.canvas_layout.feedback_area,
            },
        },
        "dashboard": engine.get_dashboard_snapshot(),
        "color_theme": COLOR_MAP["stable_idle"],
    }


async def _generate_next_puzzle(pid: int, engine: DynamicPuzzleEngine,
                                 force_type: str | None = None) -> DynamicPuzzle:
    """Generate a new puzzle, possibly of a specific type."""
    puzzle_type = _pick_puzzle_type(pid, force_type)
    player_ctx = _get_player_context(pid, engine)
    llm_data = puzzle_generator.generate_puzzle(puzzle_type, player_ctx)
    puzzle = DynamicPuzzle.from_llm(puzzle_type, llm_data)
    engine.set_puzzle(puzzle)
    _active_puzzles[pid] = puzzle
    return puzzle


async def _handle_failure_prediction(pid: int, engine: DynamicPuzzleEngine,
                                      session_id: int) -> dict:
    """Analyze failure pattern, predict, decide on regeneration."""
    ctx = engine.get_prediction_context()
    result = {"predicted_will_fail": None, "should_regenerate": False, "prediction": None}

    # After 2 failures, predict using LLM
    if ctx.get("failures_so_far", 0) >= 2:
        prediction = puzzle_generator.predict_will_fail(ctx)
        result["prediction"] = prediction
        result["predicted_will_fail"] = prediction["prediction"]

        # Record the prediction
        pred_id = models.record_prediction(
            player_id=pid,
            puzzle_id=engine._current_puzzle.puzzle_id,
            predicted_fail=prediction["prediction"],
            confidence=prediction["confidence"],
            reasoning=prediction["reasoning"],
            context_json=ctx,
        )

        # If predicted fail, regenerate the puzzle
        if prediction["prediction"]:
            result["should_regenerate"] = True

    return result


# ── Attempt endpoint ──

@app.post("/api/game/attempt")
async def game_attempt(
    req: AttemptRequest,
    player: dict = Depends(get_current_user),
):
    pid = player["id"]
    engine = _active_engines.get(pid)
    session_id = _active_sessions.get(pid)

    if not engine or not session_id:
        raise HTTPException(400, "No active game. Call /api/game/start first.")

    old_puzzle = _active_puzzles.get(pid)

    # Build snapshot
    snapshot = AttemptSnapshot(
        is_correct=req.is_correct,
        time_per_note_ms=req.time_visible_ms or 0,
        decision_time_ms=req.decision_time_ms or 0,
        input_latency_ms=req.input_latency_ms or 0,
        hovered_options=req.hovered_options,
        hover_durations_ms=req.hover_durations_ms,
        option_selected=req.option_selected,
        puzzle_type=req.puzzle_type,
        puzzle_id=req.puzzle_id,
    )

    # Process through engine
    adjustment = engine.process_attempt(snapshot)
    state = adjustment["state"]

    # Record puzzle attempt in DB
    if old_puzzle:
        db_puzzle_id = models.record_puzzle(
            session_id=session_id,
            player_id=pid,
            puzzle_id=req.puzzle_id,
            puzzle_type=req.puzzle_type,
            prompt=req.prompt or old_puzzle.prompt,
            options=old_puzzle.options or [],
            correct_answer=req.correct_answer or old_puzzle.correct_answer or "",
            player_answer=req.option_selected,
            is_correct=req.is_correct,
            time_visible_ms=req.time_visible_ms or 0,
            decision_time_ms=req.decision_time_ms or 0,
            hovered_options=req.hovered_options,
            attempt_count=req.puzzle_attempt_count,
            canvas_positions=req.canvas_positions,
        )

    # Color theme based on state
    if req.is_correct:
        color = COLOR_MAP["success_burst"]
    elif state == "struggle":
        color = COLOR_MAP["struggle"]
    elif state == "skill_gap":
        color = COLOR_MAP["skill_gap"]
    else:
        color = COLOR_MAP["fail"]

    # Generate coaching hint
    coaching_hint = None
    coaching_source = "none"
    if adjustment.get("state") in ("struggle", "skill_gap") and old_puzzle:
        recent_attempts = []
        recent = models.get_player_stats(pid).get("total_puzzles", 0)
        coaching_hint = puzzle_generator.generate_coaching_hint(
            {"prompt": old_puzzle.prompt},
            adjustment["state"],
            [{"is_correct": req.is_correct, "decision_time_ms": req.decision_time_ms}],
        )
        coaching_source = "llm"

    # Handle failure prediction and puzzle management
    prediction_result = {}
    new_puzzle_data = None
    should_rotate = adjustment.get("puzzle_should_rotate", False)
    should_regenerate = adjustment.get("should_regenerate", False)

    if not req.is_correct:
        # Analyze failure pattern
        if adjustment.get("failure_analysis", {}).get("trend") != "insufficient_data":
            models.record_struggle(
                session_id=session_id, player_id=pid,
                state=state,
                fail_count=adjustment.get("failure_analysis", {}).get("speed_delta_ms", 0),
                trend_data=adjustment.get("failure_analysis", {}),
            )

        # LLM prediction on 2nd+ failure
        prediction_result = await _handle_failure_prediction(pid, engine, session_id)
        should_regenerate = prediction_result.get("should_regenerate", should_regenerate)

    # Determine next puzzle action
    needs_new_puzzle = (
        req.is_correct  # Correct — move to next puzzle
        or should_rotate  # 3 failures — force rotate
        or should_regenerate  # LLM predicted failure — regenerate
    )

    if needs_new_puzzle:
        # Record rotation if applicable
        if should_rotate and old_puzzle:
            models.record_rotation(
                session_id=session_id, player_id=pid,
                old_puzzle_id=old_puzzle.puzzle_id,
                old_puzzle_type=old_puzzle.puzzle_type,
                failures=old_puzzle.failure_record.failures if old_puzzle.failure_record else 0,
                trend_data=adjustment.get("failure_analysis", {}),
                prediction=str(prediction_result.get("predicted_will_fail", "unknown")),
                new_puzzle_type=_pick_puzzle_type(pid),
            )

        # Force different type if rotating due to failures
        force_type = None
        if should_rotate and old_puzzle:
            force_type = _pick_puzzle_type(pid)

        # Generate next puzzle
        new_puzzle = await _generate_next_puzzle(pid, engine, force_type)
        new_puzzle_data = {
            "puzzle_id": new_puzzle.puzzle_id,
            "puzzle_type": new_puzzle.puzzle_type,
            "prompt": new_puzzle.prompt,
            "options": new_puzzle.options,
            "time_limit_ms": new_puzzle.time_limit_ms,
            "metadata": new_puzzle.metadata,
            "answer_positions": new_puzzle.answer_positions,
            "fibonacci_data": {
                "points": new_puzzle.fibonacci_data.spiral_points,
                "rects": new_puzzle.fibonacci_data.golden_rectangles,
                "phi": new_puzzle.fibonacci_data.phi,
            },
            "canvas_layout": {
                "w": new_puzzle.canvas_layout.canvas_w,
                "h": new_puzzle.canvas_layout.canvas_h,
                "puzzle_area": new_puzzle.canvas_layout.puzzle_area,
                "hint_area": new_puzzle.canvas_layout.hint_area,
                "feedback_area": new_puzzle.canvas_layout.feedback_area,
            },
        }

    return {
        "is_correct": req.is_correct,
        "state": state,
        "color_theme": color,
        "coaching": {
            "hint": coaching_hint,
            "source": coaching_source,
        },
        "failure_analysis": adjustment.get("failure_analysis", {}),
        "prediction": prediction_result.get("prediction"),
        "predicted_will_fail": prediction_result.get("predicted_will_fail"),
        "puzzle_action": adjustment.get("puzzle_action", "continue"),
        "should_rotate": should_rotate,
        "should_regenerate": should_regenerate,
        "fibonacci_data": adjustment.get("fibonacci_data"),
        "canvas_layout": adjustment.get("canvas_layout"),
        "new_puzzle": new_puzzle_data,
        "dashboard": engine.get_dashboard_snapshot(),
    }


@app.post("/api/game/end")
async def end_game(player: dict = Depends(get_current_user)):
    pid = player["id"]
    engine = _active_engines.get(pid)
    session_id = _active_sessions.get(pid)

    if not engine or not session_id:
        raise HTTPException(400, "No active game.")

    snapshot = engine.get_dashboard_snapshot()
    is_flow = engine.streak >= 5

    models.end_session(
        session_id=session_id,
        total=snapshot["total_attempts"],
        correct=snapshot["correct_attempts"],
        is_flow=int(is_flow),
        avg_diff=snapshot["win_rate"],
    )

    _active_engines.pop(pid, None)
    _active_sessions.pop(pid, None)
    _active_puzzles.pop(pid, None)
    _last_puzzle_types.pop(pid, None)

    return {
        "session_id": session_id,
        "is_flow_session": is_flow,
        "total_puzzles": snapshot["total_attempts"],
        "correct_puzzles": snapshot["correct_attempts"],
        "win_rate": snapshot["win_rate"],
        "streak": snapshot["streak"],
    }


@app.get("/api/game/state")
def game_state(player: dict = Depends(get_current_user)):
    pid = player["id"]
    engine = _active_engines.get(pid)
    if not engine:
        raise HTTPException(400, "No active game.")

    puzzle = _active_puzzles.get(pid)

    return {
        "dashboard": engine.get_dashboard_snapshot(),
        "current_puzzle": {
            "puzzle_id": puzzle.puzzle_id,
            "puzzle_type": puzzle.puzzle_type,
            "prompt": puzzle.prompt,
            "options": puzzle.options,
            "time_limit_ms": puzzle.time_limit_ms,
        } if puzzle else None,
    }


# ── Dashboard endpoints ──

@app.get("/api/dashboard/stats")
def dashboard_stats(player: dict = Depends(get_current_user)):
    return models.get_player_stats(player["id"])


@app.get("/api/dashboard/sessions")
def dashboard_sessions(limit: int = 20, player: dict = Depends(get_current_user)):
    return models.get_player_sessions(player["id"], limit)


@app.get("/api/dashboard/puzzles")
def dashboard_puzzles(limit: int = 20, player: dict = Depends(get_current_user)):
    return {"puzzles": models.get_puzzle_history(player["id"], limit)}


@app.get("/api/dashboard/predictions")
def dashboard_predictions(limit: int = 20, player: dict = Depends(get_current_user)):
    return {"predictions": models.get_prediction_history(player["id"], limit)}


@app.get("/api/dashboard/rotations")
def dashboard_rotations(limit: int = 20, player: dict = Depends(get_current_user)):
    return {"rotations": models.get_rotation_history(player["id"], limit)}


@app.get("/api/regen-puzzle")
async def regen_puzzle(player: dict = Depends(get_current_user)):
    """Force-regenerate the current puzzle (for 'skip' feature)."""
    pid = player["id"]
    engine = _active_engines.get(pid)
    if not engine:
        raise HTTPException(400, "No active game.")

    new_puzzle = await _generate_next_puzzle(pid, engine)
    return {
        "puzzle": {
            "puzzle_id": new_puzzle.puzzle_id,
            "puzzle_type": new_puzzle.puzzle_type,
            "prompt": new_puzzle.prompt,
            "options": new_puzzle.options,
            "time_limit_ms": new_puzzle.time_limit_ms,
            "metadata": new_puzzle.metadata,
            "answer_positions": new_puzzle.answer_positions,
            "fibonacci_data": {
                "points": new_puzzle.fibonacci_data.spiral_points,
                "rects": new_puzzle.fibonacci_data.golden_rectangles,
                "phi": new_puzzle.fibonacci_data.phi,
            },
            "canvas_layout": {
                "w": new_puzzle.canvas_layout.canvas_w,
                "h": new_puzzle.canvas_layout.canvas_h,
                "puzzle_area": new_puzzle.canvas_layout.puzzle_area,
                "hint_area": new_puzzle.canvas_layout.hint_area,
                "feedback_area": new_puzzle.canvas_layout.feedback_area,
            },
        },
    }


# ── Config endpoints ──

@app.get("/api/config/puzzle-types")
def get_puzzle_types():
    return {"types": PUZZLE_TYPES}


@app.get("/api/config/colors")
def get_colors():
    return COLOR_MAP