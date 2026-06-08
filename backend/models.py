#!/usr/bin/env python3
"""Echo - NeuroFlux v1 Database Models & Schema"""

import sqlite3
import json
from datetime import datetime, timezone
from pathlib import Path
from config import DB_PATH


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    """Create all tables. Safe to call multiple times."""
    conn = get_connection()
    conn.executescript("""
        -- Players
        CREATE TABLE IF NOT EXISTS players (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
            total_sessions INTEGER DEFAULT 0,
            total_flow_sessions INTEGER DEFAULT 0
        );

        -- Sessions
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            player_id INTEGER NOT NULL REFERENCES players(id),
            started_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
            ended_at TEXT,
            level_at_start INTEGER DEFAULT 1,
            level_at_end INTEGER DEFAULT 1,
            total_attempts INTEGER DEFAULT 0,
            correct_attempts INTEGER DEFAULT 0,
            is_flow_session INTEGER DEFAULT 0,
            avg_difficulty REAL DEFAULT 1.0
        );

        -- Attempts (telemetry)
        CREATE TABLE IF NOT EXISTS attempts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER NOT NULL REFERENCES sessions(id),
            player_id INTEGER NOT NULL REFERENCES players(id),
            attempted_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
            sequence_length INTEGER NOT NULL,
            is_correct INTEGER NOT NULL,
            time_per_note_ms REAL,
            input_latency_ms REAL,
            difficulty_at_time REAL NOT NULL,
            player_state TEXT DEFAULT 'stable',
            error_type TEXT,
            hint_shown TEXT,
            hint_helped INTEGER
        );

        -- Struggle events
        CREATE TABLE IF NOT EXISTS struggle_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER NOT NULL REFERENCES sessions(id),
            player_id INTEGER NOT NULL REFERENCES players(id),
            detected_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
            state TEXT NOT NULL,  -- 'struggle' or 'skill_gap'
            difficulty_before REAL NOT NULL,
            difficulty_after REAL NOT NULL,
            error_count INTEGER NOT NULL,
            action_taken TEXT  -- JSON: what rubber-band did
        );

        -- Coaching log
        CREATE TABLE IF NOT EXISTS coaching_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            attempt_id INTEGER REFERENCES attempts(id),
            player_id INTEGER NOT NULL REFERENCES players(id),
            source TEXT NOT NULL,  -- 'heuristic' or 'llm'
            hint_text TEXT NOT NULL,
            latency_ms INTEGER,
            error_type TEXT,
            created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
        );

        CREATE TABLE IF NOT EXISTS puzzle_generations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER NOT NULL REFERENCES sessions(id),
            puzzle_type TEXT NOT NULL,
            puzzle_data TEXT NOT NULL,
            generation_params TEXT,
            created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
        );

        CREATE TABLE IF NOT EXISTS puzzle_analyses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            attempt_id INTEGER REFERENCES attempts(id),
            player_id INTEGER NOT NULL REFERENCES players(id),
            puzzle_type TEXT NOT NULL,
            time_to_fail_ms REAL,
            prev_time_to_fail_ms REAL,
            speed_change REAL,
            llm_prediction INTEGER,
            llm_confidence REAL,
            llm_reasoning TEXT,
            switched_puzzle INTEGER DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
        );

        CREATE TABLE IF NOT EXISTS psych_questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER NOT NULL REFERENCES sessions(id),
            player_id INTEGER NOT NULL REFERENCES players(id),
            question TEXT NOT NULL,
            options TEXT NOT NULL,
            selected_index INTEGER,
            correct_index INTEGER NOT NULL,
            weight_chosen REAL,
            is_correct INTEGER,
            created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
        );

        CREATE TABLE IF NOT EXISTS player_metrics_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            player_id INTEGER NOT NULL REFERENCES players(id),
            session_id INTEGER NOT NULL REFERENCES sessions(id),
            snapshot_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
            avg_time_per_note_ms REAL,
            variance_time_per_note REAL,
            error_rate_rolling REAL,
            reaction_time_improvement REAL,
            fatigue_score REAL,
            puzzle_type TEXT,
            llm_generated_puzzle INTEGER DEFAULT 0
        );

        CREATE INDEX IF NOT EXISTS idx_attempts_player ON attempts(player_id);
        CREATE INDEX IF NOT EXISTS idx_attempts_session ON attempts(session_id);
        CREATE INDEX IF NOT EXISTS idx_sessions_player ON sessions(player_id);
        CREATE INDEX IF NOT EXISTS idx_struggle_player ON struggle_events(player_id);
        CREATE INDEX IF NOT EXISTS idx_puzzle_analyses ON puzzle_analyses(player_id, puzzle_type);
        CREATE INDEX IF NOT EXISTS idx_metrics_snapshot ON player_metrics_snapshots(player_id, session_id);
    """)
    conn.commit()
    conn.close()


def create_player(username: str, email: str, password_hash: str) -> int:
    conn = get_connection()
    cur = conn.execute(
        "INSERT INTO players (username, email, password_hash) VALUES (?, ?, ?)",
        (username, email, password_hash),
    )
    player_id = cur.lastrowid
    conn.commit()
    conn.close()
    return player_id


def get_player_by_username(username: str) -> dict | None:
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM players WHERE username = ?", (username,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def get_player_by_email(email: str) -> dict | None:
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM players WHERE email = ?", (email,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def get_player_by_id(player_id: int) -> dict | None:
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM players WHERE id = ?", (player_id,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def create_session(player_id: int, level: int = 1) -> int:
    conn = get_connection()
    cur = conn.execute(
        "INSERT INTO sessions (player_id, level_at_start) VALUES (?, ?)",
        (player_id, level),
    )
    session_id = cur.lastrowid
    conn.commit()
    conn.close()
    return session_id


def end_session(session_id: int, level_end: int, total: int, correct: int,
                is_flow: int, avg_diff: float):
    conn = get_connection()
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    conn.execute(
        """UPDATE sessions SET ended_at=?, level_at_end=?, total_attempts=?,
           correct_attempts=?, is_flow_session=?, avg_difficulty=?
           WHERE id=?""",
        (now, level_end, total, correct, is_flow, avg_diff, session_id),
    )
    conn.commit()
    conn.close()


def record_attempt(session_id: int, player_id: int, seq_len: int,
                   is_correct: bool, time_per_note: float | None,
                   input_latency: float | None, difficulty: float,
                   state: str, error_type: str | None,
                   hint_shown: str | None, hint_helped: bool | None) -> int:
    conn = get_connection()
    cur = conn.execute(
        """INSERT INTO attempts (session_id, player_id, sequence_length,
           is_correct, time_per_note_ms, input_latency_ms,
           difficulty_at_time, player_state, error_type,
           hint_shown, hint_helped)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (session_id, player_id, seq_len, int(is_correct),
         time_per_note, input_latency, difficulty, state,
         error_type, hint_shown, int(hint_helped) if hint_helped is not None else None),
    )
    aid = cur.lastrowid
    conn.commit()
    conn.close()
    return aid


def record_struggle(session_id: int, player_id: int, state: str,
                    diff_before: float, diff_after: float,
                    error_count: int, action: dict):
    conn = get_connection()
    conn.execute(
        """INSERT INTO struggle_events (session_id, player_id, state,
           difficulty_before, difficulty_after, error_count, action_taken)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (session_id, player_id, state, diff_before, diff_after,
         error_count, json.dumps(action)),
    )
    conn.commit()
    conn.close()


def record_coaching(attempt_id: int, player_id: int, source: str,
                    hint_text: str, latency_ms: int, error_type: str):
    conn = get_connection()
    conn.execute(
        """INSERT INTO coaching_log (attempt_id, player_id, source,
           hint_text, latency_ms, error_type) VALUES (?, ?, ?, ?, ?, ?)""",
        (attempt_id, player_id, source, hint_text, latency_ms, error_type),
    )
    conn.commit()
    conn.close()


def get_recent_attempts(player_id: int, session_id: int, limit: int = 20):
    """Get the most recent N attempts for a player in a session."""
    conn = get_connection()
    rows = conn.execute(
        """SELECT * FROM attempts WHERE player_id=? AND session_id=?
           ORDER BY attempted_at DESC LIMIT ?""",
        (player_id, session_id, limit),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_player_sessions(player_id: int, limit: int = 20):
    conn = get_connection()
    rows = conn.execute(
        """SELECT * FROM sessions WHERE player_id=?
           ORDER BY started_at DESC LIMIT ?""",
        (player_id, limit),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def record_puzzle_generation(session_id: int, puzzle_type: str, puzzle_data: dict, params: dict | None = None) -> int:
    conn = get_connection()
    cur = conn.execute(
        "INSERT INTO puzzle_generations (session_id, puzzle_type, puzzle_data, generation_params) VALUES (?, ?, ?, ?)",
        (session_id, puzzle_type, json.dumps(puzzle_data), json.dumps(params) if params else None),
    )
    gid = cur.lastrowid
    conn.commit()
    conn.close()
    return gid


def record_puzzle_analysis(attempt_id: int, player_id: int, puzzle_type: str,
                            time_to_fail_ms: float | None, prev_time_to_fail_ms: float | None,
                            speed_change: float | None, llm_prediction: bool | None,
                            llm_confidence: float | None, llm_reasoning: str | None,
                            switched: bool = False) -> int:
    conn = get_connection()
    cur = conn.execute(
        """INSERT INTO puzzle_analyses (attempt_id, player_id, puzzle_type,
           time_to_fail_ms, prev_time_to_fail_ms, speed_change,
           llm_prediction, llm_confidence, llm_reasoning, switched_puzzle)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (attempt_id, player_id, puzzle_type, time_to_fail_ms, prev_time_to_fail_ms,
         speed_change, int(llm_prediction) if llm_prediction is not None else None,
         llm_confidence, llm_reasoning, int(switched)),
    )
    aid = cur.lastrowid
    conn.commit()
    conn.close()
    return aid


def record_psych_question(session_id: int, player_id: int, question: str,
                           options: list, selected_index: int | None,
                           correct_index: int, weight_chosen: float,
                           is_correct: bool | None) -> int:
    conn = get_connection()
    cur = conn.execute(
        """INSERT INTO psych_questions (session_id, player_id, question, options,
           selected_index, correct_index, weight_chosen, is_correct)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (session_id, player_id, question, json.dumps(options),
         selected_index, correct_index, weight_chosen,
         int(is_correct) if is_correct is not None else None),
    )
    qid = cur.lastrowid
    conn.commit()
    conn.close()
    return qid


def record_metrics_snapshot(player_id: int, session_id: int,
                             avg_time_ms: float | None, variance_time: float | None,
                             error_rate: float | None, reaction_improvement: float | None,
                             fatigue: float | None, puzzle_type: str | None,
                             llm_gen: bool = False) -> int:
    conn = get_connection()
    cur = conn.execute(
        """INSERT INTO player_metrics_snapshots (player_id, session_id,
           avg_time_per_note_ms, variance_time_per_note, error_rate_rolling,
           reaction_time_improvement, fatigue_score, puzzle_type, llm_generated_puzzle)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (player_id, session_id, avg_time_ms, variance_time,
         error_rate, reaction_improvement, fatigue, puzzle_type, int(llm_gen)),
    )
    sid = cur.lastrowid
    conn.commit()
    conn.close()
    return sid


def get_metrics_history(player_id: int, session_id: int, limit: int = 10) -> list[dict]:
    conn = get_connection()
    rows = conn.execute(
        """SELECT * FROM player_metrics_snapshots
           WHERE player_id=? AND session_id=?
           ORDER BY snapshot_at DESC LIMIT ?""",
        (player_id, session_id, limit),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_last_two_fail_attempts(player_id: int, puzzle_type: str) -> list[dict]:
    """Get the two most recent failed attempts for a specific puzzle type."""
    conn = get_connection()
    rows = conn.execute(
        """SELECT * FROM attempts
           WHERE player_id=? AND is_correct=0 AND error_type IS NOT NULL
           ORDER BY attempted_at DESC LIMIT 2""",
        (player_id,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_player_stats(player_id: int) -> dict:
    """Aggregate stats for the player dashboard."""
    conn = get_connection()
    row = conn.execute(
        """SELECT
            COUNT(*) as total_attempts,
            SUM(is_correct) as correct_attempts,
            AVG(time_per_note_ms) as avg_time_per_note,
            AVG(difficulty_at_time) as avg_difficulty
           FROM attempts WHERE player_id=?""",
        (player_id,),
    ).fetchone()
    sess = conn.execute(
        """SELECT COUNT(*) as total_sessions,
                  SUM(is_flow_session) as flow_sessions,
                  AVG(avg_difficulty) as avg_session_difficulty
           FROM sessions WHERE player_id=?""",
        (player_id,),
    ).fetchone()
    conn.close()
    return {
        "total_attempts": row["total_attempts"] or 0,
        "correct_attempts": row["correct_attempts"] or 0,
        "win_rate": round((row["correct_attempts"] or 0) / max(row["total_attempts"], 1), 3),
        "avg_time_per_note_ms": round(row["avg_time_per_note"] or 0, 1),
        "avg_difficulty": round(row["avg_difficulty"] or 1.0, 2),
        "total_sessions": sess["total_sessions"] or 0,
        "flow_sessions": sess["flow_sessions"] or 0,
        "avg_session_difficulty": round(sess["avg_session_difficulty"] or 1.0, 2),
    }