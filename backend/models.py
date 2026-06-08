#!/usr/bin/env python3
"""Echo - NeuroFlux v1/v2 Database Models & Schema"""

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
            avg_difficulty REAL DEFAULT 1.0,
            puzzle_switches INTEGER DEFAULT 0
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
            hesitation_ms REAL DEFAULT 0,
            difficulty_at_time REAL NOT NULL,
            player_state TEXT DEFAULT 'stable',
            error_type TEXT,
            hint_shown TEXT,
            hint_helped INTEGER,
            puzzle_type TEXT,
            puzzle_id INTEGER
        );

        -- Struggle events
        CREATE TABLE IF NOT EXISTS struggle_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER NOT NULL REFERENCES sessions(id),
            player_id INTEGER NOT NULL REFERENCES players(id),
            detected_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
            state TEXT NOT NULL,
            difficulty_before REAL NOT NULL,
            difficulty_after REAL NOT NULL,
            error_count INTEGER NOT NULL,
            action_taken TEXT
        );

        -- Coaching log
        CREATE TABLE IF NOT EXISTS coaching_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            attempt_id INTEGER REFERENCES attempts(id),
            player_id INTEGER NOT NULL REFERENCES players(id),
            source TEXT NOT NULL,
            hint_text TEXT NOT NULL,
            latency_ms INTEGER,
            error_type TEXT,
            created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
        );

        -- Puzzle definitions
        CREATE TABLE IF NOT EXISTS puzzles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER NOT NULL REFERENCES sessions(id),
            puzzle_type TEXT NOT NULL,
            puzzle_data TEXT NOT NULL,
            shown_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
            shown_count INTEGER DEFAULT 1,
            is_active INTEGER DEFAULT 1,
            is_completed INTEGER DEFAULT 0,
            completed_at TEXT,
            was_skipped INTEGER DEFAULT 0,
            generated_by TEXT DEFAULT 'template'
        );

        -- Puzzle-specific attempts (per puzzle, not per session)
        CREATE TABLE IF NOT EXISTS puzzle_attempts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            puzzle_id INTEGER NOT NULL REFERENCES puzzles(id),
            session_id INTEGER NOT NULL REFERENCES sessions(id),
            player_id INTEGER NOT NULL REFERENCES players(id),
            attempt_number INTEGER NOT NULL,
            is_correct INTEGER NOT NULL,
            time_taken_ms REAL,
            hesitation_ms REAL,
            input_latency_ms REAL,
            error_type TEXT,
            chosen_option INTEGER,
            metrics TEXT,
            attempted_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
        );

        -- Player metrics per session
        CREATE TABLE IF NOT EXISTS player_metrics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            player_id INTEGER NOT NULL REFERENCES players(id),
            session_id INTEGER NOT NULL REFERENCES sessions(id),
            avg_reaction_time_ms REAL,
            reaction_time_trend REAL,
            hesitation_score REAL,
            speed_variance REAL,
            fatigue_index REAL,
            accuracy_trend REAL,
            puzzle_switches INTEGER DEFAULT 0,
            flow_score REAL,
            recorded_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
        );

        -- Fail predictions log
        CREATE TABLE IF NOT EXISTS fail_predictions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            player_id INTEGER NOT NULL REFERENCES players(id),
            puzzle_id INTEGER NOT NULL REFERENCES puzzles(id),
            prediction INTEGER NOT NULL,
            confidence REAL,
            features_used TEXT,
            actual_outcome INTEGER,
            triggered_puzzle_switch INTEGER DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
        );

        -- Challenge questions bank
        CREATE TABLE IF NOT EXISTS challenge_questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            question_type TEXT NOT NULL,
            question_text TEXT NOT NULL,
            options TEXT NOT NULL,
            correct_answer INTEGER NOT NULL,
            difficulty REAL DEFAULT 1.0,
            category TEXT,
            times_used INTEGER DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
        );

        CREATE INDEX IF NOT EXISTS idx_attempts_player ON attempts(player_id);
        CREATE INDEX IF NOT EXISTS idx_attempts_session ON attempts(session_id);
        CREATE INDEX IF NOT EXISTS idx_sessions_player ON sessions(player_id);
        CREATE INDEX IF NOT EXISTS idx_struggle_player ON struggle_events(player_id);
        CREATE INDEX IF NOT EXISTS idx_puzzles_session ON puzzles(session_id);
        CREATE INDEX IF NOT EXISTS idx_puzzle_attempts_puzzle ON puzzle_attempts(puzzle_id);
        CREATE INDEX IF NOT EXISTS idx_puzzle_attempts_player ON puzzle_attempts(player_id);
        CREATE INDEX IF NOT EXISTS idx_fail_predictions_player ON fail_predictions(player_id);
        CREATE INDEX IF NOT EXISTS idx_player_metrics_session ON player_metrics(session_id);
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
                is_flow: int, avg_diff: float, puzzle_switches: int = 0):
    conn = get_connection()
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    conn.execute(
        """UPDATE sessions SET ended_at=?, level_at_end=?, total_attempts=?,
           correct_attempts=?, is_flow_session=?, avg_difficulty=?, puzzle_switches=?
           WHERE id=?""",
        (now, level_end, total, correct, is_flow, avg_diff, puzzle_switches, session_id),
    )
    conn.commit()
    conn.close()


def record_attempt(session_id: int, player_id: int, seq_len: int,
                   is_correct: bool, time_per_note: float | None,
                   input_latency: float | None, difficulty: float,
                   state: str, error_type: str | None,
                   hint_shown: str | None, hint_helped: bool | None,
                   hesitation_ms: float | None = None,
                   puzzle_type: str | None = None,
                   puzzle_id: int | None = None) -> int:
    conn = get_connection()
    cur = conn.execute(
        """INSERT INTO attempts (session_id, player_id, sequence_length,
           is_correct, time_per_note_ms, input_latency_ms, hesitation_ms,
           difficulty_at_time, player_state, error_type,
           hint_shown, hint_helped, puzzle_type, puzzle_id)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (session_id, player_id, seq_len, int(is_correct),
         time_per_note, input_latency, hesitation_ms, difficulty, state,
         error_type, hint_shown, int(hint_helped) if hint_helped is not None else None,
         puzzle_type, puzzle_id),
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
                  AVG(avg_difficulty) as avg_session_difficulty,
                  SUM(puzzle_switches) as total_puzzle_switches
           FROM sessions WHERE player_id=?""",
        (player_id,),
    ).fetchone()

    # Hesitation stats
    hes = conn.execute(
        """SELECT AVG(hesitation_ms) as avg_hesitation,
                  AVG(time_per_note_ms) as avg_time_per_note
           FROM attempts WHERE player_id=? AND hesitation_ms IS NOT NULL""",
        (player_id,),
    ).fetchone()

    # Puzzle type distribution
    types = conn.execute(
        """SELECT puzzle_type, COUNT(*) as count
           FROM attempts WHERE player_id=? AND puzzle_type IS NOT NULL
           GROUP BY puzzle_type""",
        (player_id,),
    ).fetchall()
    puzzle_dist = {r["puzzle_type"]: r["count"] for r in types}

    conn.close()
    return {
        "total_attempts": row["total_attempts"] or 0,
        "correct_attempts": row["correct_attempts"] or 0,
        "win_rate": round((row["correct_attempts"] or 0) / max(row["total_attempts"], 1), 3),
        "avg_time_per_note_ms": round(row["avg_time_per_note"] or 0, 1),
        "avg_hesitation_ms": round(hes["avg_hesitation"] or 0, 1),
        "avg_difficulty": round(row["avg_difficulty"] or 1.0, 2),
        "total_sessions": sess["total_sessions"] or 0,
        "flow_sessions": sess["flow_sessions"] or 0,
        "avg_session_difficulty": round(sess["avg_session_difficulty"] or 1.0, 2),
        "total_puzzle_switches": sess["total_puzzle_switches"] or 0,
        "puzzle_type_distribution": puzzle_dist,
    }


# ── Puzzle-specific DB operations ──

def create_puzzle_db(session_id: int, puzzle_type: str, puzzle_data: dict, generated_by: str = "template") -> int:
    conn = get_connection()
    cur = conn.execute(
        "INSERT INTO puzzles (session_id, puzzle_type, puzzle_data, generated_by) VALUES (?, ?, ?, ?)",
        (session_id, puzzle_type, json.dumps(puzzle_data), generated_by),
    )
    pid = cur.lastrowid
    conn.commit()
    conn.close()
    return pid


def get_puzzle_by_id(puzzle_id: int) -> dict | None:
    conn = get_connection()
    row = conn.execute("SELECT * FROM puzzles WHERE id=?", (puzzle_id,)).fetchone()
    conn.close()
    if row:
        r = dict(row)
        r["puzzle_data"] = json.loads(r["puzzle_data"])
        return r
    return None


def increment_puzzle_shown(puzzle_id: int):
    conn = get_connection()
    conn.execute("UPDATE puzzles SET shown_count = shown_count + 1 WHERE id=?", (puzzle_id,))
    conn.commit()
    conn.close()


def complete_puzzle(puzzle_id: int, was_skipped: bool = False):
    conn = get_connection()
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    conn.execute(
        "UPDATE puzzles SET is_completed=1, completed_at=?, is_active=0, was_skipped=? WHERE id=?",
        (now, int(was_skipped), puzzle_id),
    )
    conn.commit()
    conn.close()


def deactivate_old_puzzles(session_id: int):
    """Deactivate all active puzzles for a session (start fresh)."""
    conn = get_connection()
    conn.execute("UPDATE puzzles SET is_active=0 WHERE session_id=? AND is_active=1", (session_id,))
    conn.commit()
    conn.close()


def get_active_puzzle(session_id: int) -> dict | None:
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM puzzles WHERE session_id=? AND is_active=1 ORDER BY id DESC LIMIT 1",
        (session_id,),
    ).fetchone()
    conn.close()
    if row:
        r = dict(row)
        r["puzzle_data"] = json.loads(r["puzzle_data"])
        return r
    return None


def get_puzzle_attempts(puzzle_id: int) -> list[dict]:
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM puzzle_attempts WHERE puzzle_id=? ORDER BY attempt_number ASC",
        (puzzle_id,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def record_puzzle_attempt(puzzle_id: int, session_id: int, player_id: int,
                          attempt_number: int, is_correct: bool,
                          time_taken_ms: float | None = None,
                          hesitation_ms: float | None = None,
                          input_latency_ms: float | None = None,
                          error_type: str | None = None,
                          chosen_option: int | None = None,
                          metrics: dict | None = None) -> int:
    conn = get_connection()
    cur = conn.execute(
        """INSERT INTO puzzle_attempts (puzzle_id, session_id, player_id,
           attempt_number, is_correct, time_taken_ms, hesitation_ms,
           input_latency_ms, error_type, chosen_option, metrics)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (puzzle_id, session_id, player_id, attempt_number, int(is_correct),
         time_taken_ms, hesitation_ms, input_latency_ms, error_type,
         chosen_option, json.dumps(metrics) if metrics else None),
    )
    aid = cur.lastrowid
    conn.commit()
    conn.close()
    return aid


def record_fail_prediction(player_id: int, puzzle_id: int,
                           prediction: bool, confidence: float,
                           features: dict | None = None,
                           actual_outcome: bool | None = None,
                           triggered_switch: bool = False) -> int:
    conn = get_connection()
    cur = conn.execute(
        """INSERT INTO fail_predictions (player_id, puzzle_id, prediction,
           confidence, features_used, actual_outcome, triggered_puzzle_switch)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (player_id, puzzle_id, int(prediction), confidence,
         json.dumps(features) if features else None,
         int(actual_outcome) if actual_outcome is not None else None,
         int(triggered_switch)),
    )
    pid = cur.lastrowid
    conn.commit()
    conn.close()
    return pid


def record_player_metrics(player_id: int, session_id: int,
                          avg_reaction: float | None = None,
                          reaction_trend: float | None = None,
                          hesitation_score: float | None = None,
                          speed_variance: float | None = None,
                          fatigue_index: float | None = None,
                          accuracy_trend: float | None = None,
                          puzzle_switches: int = 0,
                          flow_score: float | None = None):
    conn = get_connection()
    conn.execute(
        """INSERT INTO player_metrics (player_id, session_id, avg_reaction_time_ms,
           reaction_time_trend, hesitation_score, speed_variance, fatigue_index,
           accuracy_trend, puzzle_switches, flow_score)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (player_id, session_id, avg_reaction, reaction_trend, hesitation_score,
         speed_variance, fatigue_index, accuracy_trend, puzzle_switches, flow_score),
    )
    conn.commit()
    conn.close()


def get_player_metrics(player_id: int, limit: int = 20) -> list[dict]:
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM player_metrics WHERE player_id=? ORDER BY recorded_at DESC LIMIT ?",
        (player_id, limit),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_puzzle_statistics(player_id: int) -> dict:
    """Get per-puzzle-type statistics."""
    conn = get_connection()
    rows = conn.execute(
        """SELECT puzzle_type,
                  COUNT(*) as total,
                  SUM(CASE WHEN is_correct=1 THEN 1 ELSE 0 END) as correct,
                  AVG(hesitation_ms) as avg_hesitation,
                  AVG(time_per_note_ms) as avg_time
           FROM attempts WHERE player_id=? AND puzzle_type IS NOT NULL
           GROUP BY puzzle_type""",
        (player_id,),
    ).fetchall()
    conn.close()
    stats = {}
    for r in rows:
        d = dict(r)
        d["win_rate"] = round((d["correct"] or 0) / max(d["total"], 1), 3)
        stats[d["puzzle_type"]] = d
    return stats