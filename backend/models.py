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

        CREATE INDEX IF NOT EXISTS idx_attempts_player ON attempts(player_id);
        CREATE INDEX IF NOT EXISTS idx_attempts_session ON attempts(session_id);
        CREATE INDEX IF NOT EXISTS idx_sessions_player ON sessions(player_id);
        CREATE INDEX IF NOT EXISTS idx_struggle_player ON struggle_events(player_id);
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