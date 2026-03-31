import json
import sqlite3
from datetime import date
from typing import Optional

from config import DB_PATH


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    with _conn() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                user_id     INTEGER PRIMARY KEY,
                username    TEXT,
                first_name  TEXT,
                joined_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                current_streak INTEGER DEFAULT 0,
                best_streak    INTEGER DEFAULT 0,
                last_played    DATE
            );

            CREATE TABLE IF NOT EXISTS question_pool (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                category      TEXT    NOT NULL,
                question_text TEXT    NOT NULL,
                options       TEXT    NOT NULL,
                correct_index INTEGER NOT NULL,
                last_used     DATE
            );

            CREATE TABLE IF NOT EXISTS daily_questions (
                id               INTEGER PRIMARY KEY AUTOINCREMENT,
                game_date        DATE    NOT NULL,
                question_index   INTEGER NOT NULL,
                question_type    TEXT    NOT NULL,
                question_text    TEXT    NOT NULL,
                options          TEXT    NOT NULL,
                correct_index    INTEGER NOT NULL,
                pool_question_id INTEGER REFERENCES question_pool(id),
                UNIQUE(game_date, question_index)
            );

            CREATE TABLE IF NOT EXISTS game_sessions (
                id                  INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id             INTEGER NOT NULL REFERENCES users(user_id),
                game_date           DATE    NOT NULL,
                started_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                finished_at         TIMESTAMP,
                total_score         INTEGER DEFAULT 0,
                correct_count       INTEGER DEFAULT 0,
                total_time_seconds  REAL    DEFAULT 0,
                UNIQUE(user_id, game_date)
            );

            CREATE TABLE IF NOT EXISTS answers (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id     INTEGER NOT NULL REFERENCES game_sessions(id),
                question_index INTEGER NOT NULL,
                selected_index INTEGER,
                is_correct     BOOLEAN NOT NULL DEFAULT 0,
                time_seconds   REAL    NOT NULL,
                points_earned  INTEGER NOT NULL DEFAULT 0
            );
        """)
        # Migrate existing daily_questions table that lacks pool_question_id
        cols = [r[1] for r in conn.execute("PRAGMA table_info(daily_questions)").fetchall()]
        if "pool_question_id" not in cols:
            conn.execute(
                "ALTER TABLE daily_questions ADD COLUMN pool_question_id INTEGER REFERENCES question_pool(id)"
            )


# ── Users ─────────────────────────────────────────────────────────────────────

def upsert_user(user_id: int, username: Optional[str], first_name: Optional[str]) -> None:
    with _conn() as conn:
        conn.execute("""
            INSERT INTO users (user_id, username, first_name)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                username   = excluded.username,
                first_name = excluded.first_name
        """, (user_id, username, first_name))


def update_streak(user_id: int) -> None:
    today = date.today()
    with _conn() as conn:
        row = conn.execute(
            "SELECT last_played, current_streak, best_streak FROM users WHERE user_id = ?",
            (user_id,)
        ).fetchone()
        if row is None:
            return

        last = date.fromisoformat(row["last_played"]) if row["last_played"] else None
        streak = row["current_streak"]

        if last is None or (today - last).days > 1:
            streak = 1
        elif (today - last).days == 1:
            streak += 1

        best = max(row["best_streak"], streak)
        conn.execute("""
            UPDATE users SET last_played = ?, current_streak = ?, best_streak = ?
            WHERE user_id = ?
        """, (today.isoformat(), streak, best, user_id))


def get_user_stats(user_id: int) -> Optional[sqlite3.Row]:
    with _conn() as conn:
        return conn.execute("""
            SELECT
                u.current_streak,
                u.best_streak,
                CAST(julianday('now') - julianday(u.joined_at) AS INTEGER) AS days_since_joined,
                COALESCE(SUM(gs.total_score), 0) AS all_time_score,
                COUNT(gs.id)                      AS total_games
            FROM users u
            LEFT JOIN game_sessions gs ON gs.user_id = u.user_id AND gs.finished_at IS NOT NULL
            WHERE u.user_id = ?
            GROUP BY u.user_id
        """, (user_id,)).fetchone()


def get_alltime_rank(user_id: int) -> int:
    with _conn() as conn:
        my = conn.execute("""
            SELECT COALESCE(SUM(total_score), 0) AS s
            FROM game_sessions WHERE user_id = ? AND finished_at IS NOT NULL
        """, (user_id,)).fetchone()
        row = conn.execute("""
            SELECT COUNT(DISTINCT user_id) + 1 AS rank
            FROM game_sessions
            WHERE finished_at IS NOT NULL
            GROUP BY user_id
            HAVING SUM(total_score) > ?
        """, (my["s"],)).fetchone()
        # COUNT(DISTINCT ...) in a HAVING subquery — simpler direct approach:
        row2 = conn.execute("""
            SELECT COUNT(*) + 1 AS rank FROM (
                SELECT user_id, SUM(total_score) AS s
                FROM game_sessions WHERE finished_at IS NOT NULL
                GROUP BY user_id
            ) WHERE s > ?
        """, (my["s"],)).fetchone()
        return row2["rank"]


# ── Question pool ─────────────────────────────────────────────────────────────

def pool_count(category: str) -> int:
    with _conn() as conn:
        row = conn.execute(
            "SELECT COUNT(*) AS n FROM question_pool WHERE category = ?", (category,)
        ).fetchone()
        return row["n"]


def seed_pool(category: str, questions: list[dict]) -> None:
    """Insert questions that don't already exist (match on question_text)."""
    with _conn() as conn:
        existing = {
            r[0] for r in conn.execute(
                "SELECT question_text FROM question_pool WHERE category = ?", (category,)
            ).fetchall()
        }
        for q in questions:
            if q["text"] not in existing:
                conn.execute("""
                    INSERT INTO question_pool (category, question_text, options, correct_index)
                    VALUES (?, ?, ?, ?)
                """, (category, q["text"], json.dumps(q["options"]), q["correct_index"]))


def pick_pool_question(category: str, game_date: str) -> Optional[sqlite3.Row]:
    """Pick a question not used in the last 30 days, mark it used."""
    with _conn() as conn:
        row = conn.execute("""
            SELECT * FROM question_pool
            WHERE category = ?
              AND (last_used IS NULL OR last_used <= date(?, '-30 days'))
            ORDER BY RANDOM()
            LIMIT 1
        """, (category, game_date)).fetchone()
        if row:
            conn.execute(
                "UPDATE question_pool SET last_used = ? WHERE id = ?",
                (game_date, row["id"])
            )
        return row


# ── Daily questions ───────────────────────────────────────────────────────────

def store_question(
    game_date: str,
    question_index: int,
    question_type: str,
    question_text: str,
    options: list[str],
    correct_index: int,
    pool_question_id: Optional[int] = None,
) -> None:
    with _conn() as conn:
        conn.execute("""
            INSERT OR IGNORE INTO daily_questions
                (game_date, question_index, question_type, question_text, options, correct_index, pool_question_id)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (game_date, question_index, question_type, question_text, json.dumps(options), correct_index, pool_question_id))


def get_daily_questions(game_date: str) -> list[sqlite3.Row]:
    with _conn() as conn:
        return conn.execute("""
            SELECT * FROM daily_questions
            WHERE game_date = ?
            ORDER BY question_index
        """, (game_date,)).fetchall()


# ── Sessions ──────────────────────────────────────────────────────────────────

def get_session(user_id: int, game_date: str) -> Optional[sqlite3.Row]:
    with _conn() as conn:
        return conn.execute("""
            SELECT * FROM game_sessions WHERE user_id = ? AND game_date = ?
        """, (user_id, game_date)).fetchone()


def create_session(user_id: int, game_date: str) -> int:
    with _conn() as conn:
        cur = conn.execute("""
            INSERT INTO game_sessions (user_id, game_date) VALUES (?, ?)
        """, (user_id, game_date))
        return cur.lastrowid


def finish_session(session_id: int) -> sqlite3.Row:
    with _conn() as conn:
        agg = conn.execute("""
            SELECT
                COALESCE(SUM(points_earned), 0) AS total_score,
                COALESCE(SUM(is_correct), 0)    AS correct_count,
                COALESCE(SUM(time_seconds), 0)  AS total_time
            FROM answers WHERE session_id = ?
        """, (session_id,)).fetchone()

        conn.execute("""
            UPDATE game_sessions
            SET finished_at        = CURRENT_TIMESTAMP,
                total_score        = ?,
                correct_count      = ?,
                total_time_seconds = ?
            WHERE id = ?
        """, (agg["total_score"], agg["correct_count"], agg["total_time"], session_id))

        return conn.execute("SELECT * FROM game_sessions WHERE id = ?", (session_id,)).fetchone()


def get_rank(session_id: int, game_date: str) -> int:
    with _conn() as conn:
        s = conn.execute(
            "SELECT total_score, total_time_seconds FROM game_sessions WHERE id = ?",
            (session_id,)
        ).fetchone()
        row = conn.execute("""
            SELECT COUNT(*) + 1 AS rank FROM game_sessions
            WHERE game_date = ? AND finished_at IS NOT NULL
              AND (
                total_score > ?
                OR (total_score = ? AND total_time_seconds < ?)
              )
        """, (game_date, s["total_score"], s["total_score"], s["total_time_seconds"])).fetchone()
        return row["rank"]


# ── Answers ───────────────────────────────────────────────────────────────────

def record_answer(
    session_id: int,
    question_index: int,
    selected_index: Optional[int],
    is_correct: bool,
    time_seconds: float,
    points_earned: int,
) -> None:
    with _conn() as conn:
        conn.execute("""
            INSERT INTO answers
                (session_id, question_index, selected_index, is_correct, time_seconds, points_earned)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (session_id, question_index, selected_index, is_correct, time_seconds, points_earned))


def reset_user_session(user_id: int, game_date: str) -> bool:
    """Delete a user's session and answers for game_date. Returns True if a session existed."""
    with _conn() as conn:
        row = conn.execute(
            "SELECT id FROM game_sessions WHERE user_id = ? AND game_date = ?",
            (user_id, game_date),
        ).fetchone()
        if row is None:
            return False
        conn.execute("DELETE FROM answers WHERE session_id = ?", (row["id"],))
        conn.execute("DELETE FROM game_sessions WHERE id = ?", (row["id"],))
        return True


def get_user_answers(session_id: int) -> list[sqlite3.Row]:
    with _conn() as conn:
        return conn.execute(
            "SELECT * FROM answers WHERE session_id = ? ORDER BY question_index",
            (session_id,)
        ).fetchall()


# ── Leaderboard ───────────────────────────────────────────────────────────────

def get_leaderboard(game_date: str, limit: int = 10) -> list[sqlite3.Row]:
    with _conn() as conn:
        return conn.execute("""
            SELECT
                gs.total_score, gs.correct_count, gs.total_time_seconds,
                u.username, u.first_name, u.current_streak
            FROM game_sessions gs
            JOIN users u ON gs.user_id = u.user_id
            WHERE gs.game_date = ? AND gs.finished_at IS NOT NULL
            ORDER BY gs.total_score DESC, gs.total_time_seconds ASC
            LIMIT ?
        """, (game_date, limit)).fetchall()


def get_alltime_leaderboard(limit: int = 10) -> list[sqlite3.Row]:
    with _conn() as conn:
        return conn.execute("""
            SELECT
                u.username, u.first_name,
                SUM(gs.total_score)  AS total_score,
                COUNT(gs.id)         AS games_played
            FROM game_sessions gs
            JOIN users u ON gs.user_id = u.user_id
            WHERE gs.finished_at IS NOT NULL
            GROUP BY gs.user_id
            ORDER BY total_score DESC
            LIMIT ?
        """, (limit,)).fetchall()


def get_longest_streak_player(game_date: str) -> Optional[sqlite3.Row]:
    with _conn() as conn:
        return conn.execute("""
            SELECT u.username, u.first_name, u.current_streak
            FROM game_sessions gs
            JOIN users u ON gs.user_id = u.user_id
            WHERE gs.game_date = ? AND gs.finished_at IS NOT NULL
            ORDER BY u.current_streak DESC
            LIMIT 1
        """, (game_date,)).fetchone()


def count_players(game_date: str) -> int:
    with _conn() as conn:
        row = conn.execute("""
            SELECT COUNT(*) AS n FROM game_sessions
            WHERE game_date = ? AND finished_at IS NOT NULL
        """, (game_date,)).fetchone()
        return row["n"]


def get_notifiable_users() -> list[int]:
    """Return user_ids of all users who have completed at least one game."""
    with _conn() as conn:
        rows = conn.execute(
            "SELECT user_id FROM users WHERE last_played IS NOT NULL"
        ).fetchall()
        return [r["user_id"] for r in rows]


def get_unplayed_users_today(game_date: str) -> list[int]:
    """Return user_ids of returning users who have NOT played on game_date."""
    with _conn() as conn:
        rows = conn.execute("""
            SELECT user_id FROM users
            WHERE last_played IS NOT NULL
              AND user_id NOT IN (
                  SELECT user_id FROM game_sessions WHERE game_date = ?
              )
        """, (game_date,)).fetchall()
        return [r["user_id"] for r in rows]


def get_avg_answer_time(user_id: int) -> Optional[float]:
    """Return average answer time in seconds across all answered (non-timeout) questions."""
    with _conn() as conn:
        row = conn.execute("""
            SELECT AVG(a.time_seconds) AS avg_time
            FROM answers a
            JOIN game_sessions gs ON a.session_id = gs.id
            WHERE gs.user_id = ? AND gs.finished_at IS NOT NULL
              AND a.selected_index IS NOT NULL
        """, (user_id,)).fetchone()
        return row["avg_time"] if row and row["avg_time"] is not None else None
