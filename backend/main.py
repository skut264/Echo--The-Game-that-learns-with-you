#!/usr/bin/env python3
"""Echo - NeuroFlux v1 Main FastAPI Application"""

import json
import time
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
import models
import auth
from config import COLOR_MAP, FIB_RULES, get_fib_rule
from engine import AdaptiveGameEngine, AttemptSnapshot
from llm_client import get_coaching_hint

# ── Auth scheme ──
security = HTTPBearer(auto_error=False)


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Extract and validate JWT token."""
    if credentials is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    payload = auth.decode_access_token(credentials.credentials)
    if payload is None:
        raise HTTPException(status_code=401, detail="Invalid token")
    player = models.get_player_by_id(payload.get("sub"))
    if player is None:
        raise HTTPException(status_code=401, detail="User not found")
    return player


# ── Engine instances (in-memory, one per active player) ──
_active_engines: dict[int, AdaptiveGameEngine] = {}
_active_sessions: dict[int, int] = {}  # player_id -> session_id


@asynccontextmanager
async def lifespan(app: FastAPI):
    models.init_db()
    yield


app = FastAPI(title="Echo - NeuroFlux v1", version="1.0.0", lifespan=lifespan)

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
    sequence_length: int
    is_correct: bool
    time_per_note_ms: float | None = None
    input_latency_ms: float | None = None
    error_type: str | None = None


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


# ── Game endpoints ──

@app.post("/api/game/start")
def start_game(player: dict = Depends(get_current_user)):
    """Start a new game session."""
    pid = player["id"]
    session_id = models.create_session(pid)
    _active_engines[pid] = AdaptiveGameEngine()
    _active_sessions[pid] = session_id

    engine = _active_engines[pid]
    rule_info = get_fib_rule(engine.level_state.level)

    return {
        "session_id": session_id,
        "level": engine.level_state.level,
        "sequence_length": engine.level_state.sequence_length,
        "difficulty": engine.level_state.difficulty,
        "current_rule": rule_info[1],
        "color_theme": COLOR_MAP["stable_idle"],
    }


@app.post("/api/game/attempt")
async def game_attempt(
    req: AttemptRequest,
    player: dict = Depends(get_current_user),
):
    """Process a player attempt and return adjustment."""
    pid = player["id"]
    engine = _active_engines.get(pid)
    session_id = _active_sessions.get(pid)

    if not engine or not session_id:
        raise HTTPException(400, "No active game. Call /api/game/start first.")

    # Build snapshot
    snapshot = AttemptSnapshot(
        is_correct=req.is_correct,
        time_per_note_ms=req.time_per_note_ms or 0,
        input_latency_ms=req.input_latency_ms or 0,
    )

    # Process through engine
    adjustment = engine.process_attempt(snapshot)

    # Record attempt in DB
    attempt_id = models.record_attempt(
        session_id=session_id,
        player_id=pid,
        seq_len=req.sequence_length,
        is_correct=req.is_correct,
        time_per_note=req.time_per_note_ms,
        input_latency=req.input_latency_ms,
        difficulty=engine.level_state.difficulty,
        state=adjustment["state"],
        error_type=req.error_type if not req.is_correct else None,
        hint_shown=adjustment.get("coaching"),
        hint_helped=req.is_correct,
    )

    # Record struggle events
    if adjustment["action"] == "rubber_band":
        models.record_struggle(
            session_id=session_id,
            player_id=pid,
            state=adjustment["state"],
            diff_before=engine.level_state.difficulty / adjustment.get("difficulty_adjustment", 1),
            diff_after=engine.level_state.difficulty,
            error_count=engine.level_state.consecutive_losses,
            action=adjustment,
        )

    # Async coaching hint (fire and forget — game gets heuristic hint immediately)
    coaching_hint = None
    coaching_source = "heuristic"
    if adjustment.get("coaching") and req.error_type and not req.is_correct:
        hint, src, latency = await get_coaching_hint(
            error_type=req.error_type or "generic",
            attempt_count=engine.level_state.total_attempts,
            state=adjustment["state"],
            player_speed="fast" if (req.time_per_note_ms or 0) < 1000 else "normal",
        )
        coaching_hint = hint
        coaching_source = src
        models.record_coaching(attempt_id, pid, src, hint, latency, req.error_type)

    # Determine color
    if adjustment["state"] == "struggle":
        color = COLOR_MAP["struggle"]
    elif adjustment["state"] == "skill_gap":
        color = COLOR_MAP["skill_gap"]
    elif adjustment.get("new_rule"):
        color = COLOR_MAP["new_rule_reveal"]
    elif engine.level_state.consecutive_wins >= 3:
        color = COLOR_MAP["flow_success"]
    else:
        color = COLOR_MAP["stable_active"]

    return {
        "state": adjustment["state"],
        "action": adjustment["action"],
        "difficulty": round(engine.level_state.difficulty, 2),
        "level": engine.level_state.level,
        "sequence_length": engine.level_state.sequence_length,
        "consecutive_wins": engine.level_state.consecutive_wins,
        "consecutive_losses": engine.level_state.consecutive_losses,
        "color_theme": color,
        "layer_updates": adjustment.get("layer_updates", {}),
        "coaching": {
            "hint": adjustment.get("coaching"),
            "text": coaching_hint,
            "source": coaching_source,
        },
        "new_rule": adjustment.get("new_rule"),
        "dashboard": engine.get_dashboard_snapshot(),
    }


@app.post("/api/game/end")
def end_game(player: dict = Depends(get_current_user)):
    """End the current game session and compute metrics."""
    pid = player["id"]
    engine = _active_engines.get(pid)
    session_id = _active_sessions.get(pid)

    if not engine or not session_id:
        raise HTTPException(400, "No active game.")

    state = engine.get_dashboard_snapshot()
    is_flow = (
        engine.level_state.consecutive_wins >= 5
        and engine.level_state.difficulty >= 1.0
    )

    models.end_session(
        session_id=session_id,
        level_end=engine.level_state.level,
        total=state["total_attempts"],
        correct=state["correct_attempts"],
        is_flow=int(is_flow),
        avg_diff=state["difficulty"],
    )

    # Clean up
    del _active_engines[pid]
    del _active_sessions[pid]

    return {
        "session_id": session_id,
        "is_flow_session": is_flow,
        "final_level": state["level"],
        "total_attempts": state["total_attempts"],
        "correct_attempts": state["correct_attempts"],
        "win_rate": state["win_rate"],
        "final_difficulty": state["difficulty"],
    }


@app.get("/api/game/state")
def game_state(player: dict = Depends(get_current_user)):
    """Get current game state without making an attempt."""
    pid = player["id"]
    engine = _active_engines.get(pid)
    if not engine:
        raise HTTPException(400, "No active game.")
    return engine.get_dashboard_snapshot()


# ── Dashboard endpoints ──

@app.get("/api/dashboard/stats")
def dashboard_stats(player: dict = Depends(get_current_user)):
    """Aggregate stats for the player dashboard."""
    return models.get_player_stats(player["id"])


@app.get("/api/dashboard/sessions")
def dashboard_sessions(limit: int = 20, player: dict = Depends(get_current_user)):
    """Recent sessions for the player dashboard."""
    return models.get_player_sessions(player["id"], limit)


@app.get("/api/dashboard/recent-attempts")
def dashboard_recent_attempts(limit: int = 20, player: dict = Depends(get_current_user)):
    """Recent attempts for live dashboard."""
    pid = player["id"]
    session_id = _active_sessions.get(pid)
    if not session_id:
        return {"attempts": []}
    return {"attempts": models.get_recent_attempts(pid, session_id, limit)}


# ── Config endpoints (public) ──

@app.get("/api/config/fib-rules")
def get_fib_rules():
    """Public endpoint for the frontend to know Fibonacci progression."""
    return {"rules": {str(k): v for k, v in FIB_RULES.items()}}


@app.get("/api/config/colors")
def get_color_map():
    """Public endpoint for the frontend to know color theming."""
    return COLOR_MAP


@app.get("/api/health")
def health():
    return {"status": "ok", "game": "Echo - NeuroFlux v1"}


# ── Run ──
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8200, reload=True)