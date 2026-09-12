import sqlite3
from datetime import datetime, timezone


def _connect(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: str = "summaries.db") -> None:
    conn = _connect(db_path)
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS summaries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                video_id TEXT NOT NULL,
                url TEXT NOT NULL,
                title TEXT NOT NULL,
                transcript TEXT NOT NULL,
                summary TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.commit()
    finally:
        conn.close()


def save_summary(
    video_id: str,
    url: str,
    title: str,
    transcript: str,
    summary: str,
    db_path: str = "summaries.db",
) -> int:
    conn = _connect(db_path)
    try:
        cursor = conn.execute(
            """
            INSERT INTO summaries (video_id, url, title, transcript, summary, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (video_id, url, title, transcript, summary, datetime.now(timezone.utc).isoformat()),
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def get_history(db_path: str = "summaries.db") -> list[dict]:
    conn = _connect(db_path)
    try:
        rows = conn.execute(
            "SELECT id, title, created_at FROM summaries ORDER BY created_at DESC"
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def get_summary(summary_id: int, db_path: str = "summaries.db") -> dict | None:
    conn = _connect(db_path)
    try:
        row = conn.execute(
            "SELECT * FROM summaries WHERE id = ?", (summary_id,)
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()
