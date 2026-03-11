"""Memory Module - Persistent SQLite storage for chat and vision history"""

import sqlite3
import os
import base64
from datetime import datetime

_DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "memory", "alia_memory.db")
_IMG_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "memory", "images")


def _connect():
    os.makedirs(os.path.dirname(_DB_PATH), exist_ok=True)
    conn = sqlite3.connect(_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create tables if they don't exist."""
    with _connect() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS chat_log (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT    NOT NULL,
                role      TEXT    NOT NULL,
                content   TEXT    NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS vision_log (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp  TEXT NOT NULL,
                question   TEXT NOT NULL,
                image_path TEXT,
                answer     TEXT NOT NULL
            )
        """)
        conn.commit()


def save_chat(role: str, content: str):
    """Save a single chat message."""
    with _connect() as conn:
        conn.execute(
            "INSERT INTO chat_log (timestamp, role, content) VALUES (?, ?, ?)",
            (datetime.now().isoformat(), role, content)
        )
        conn.commit()


def save_vision(question: str, image_b64: str | None, answer: str):
    """Save a vision interaction. Writes the image to disk if provided."""
    img_path = None
    if image_b64:
        os.makedirs(_IMG_DIR, exist_ok=True)
        fname = f"{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}.jpg"
        img_path = os.path.join(_IMG_DIR, fname)
        with open(img_path, "wb") as f:
            f.write(base64.b64decode(image_b64))

    with _connect() as conn:
        conn.execute(
            "INSERT INTO vision_log (timestamp, question, image_path, answer) VALUES (?, ?, ?, ?)",
            (datetime.now().isoformat(), question, img_path, answer)
        )
        conn.commit()


def load_recent_chat(limit: int = 20) -> list[dict]:
    """Return the last `limit` chat messages ordered oldest-first."""
    with _connect() as conn:
        rows = conn.execute(
            "SELECT role, content FROM chat_log ORDER BY id DESC LIMIT ?",
            (limit,)
        ).fetchall()
    return [{"role": r["role"], "content": r["content"]} for r in reversed(rows)]


def get_vision_context(question: str, limit: int = 5) -> list[dict]:
    """
    Return recent vision Q&A pairs that share keywords with the current question.
    Used to inject memory hints into GPT-4o's prompt.
    """
    words = [w for w in question.lower().split() if len(w) > 3]
    if not words:
        return _get_latest_vision(limit)

    with _connect() as conn:
        # Simple keyword match — find entries whose question contains any query word
        placeholders = " OR ".join(["LOWER(question) LIKE ?" for _ in words])
        params = [f"%{w}%" for w in words] + [limit]
        rows = conn.execute(
            f"SELECT question, answer FROM vision_log WHERE {placeholders} ORDER BY id DESC LIMIT ?",
            params
        ).fetchall()

    if not rows:
        return _get_latest_vision(limit)
    return [{"question": r["question"], "answer": r["answer"]} for r in rows]


def _get_latest_vision(limit: int) -> list[dict]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT question, answer FROM vision_log ORDER BY id DESC LIMIT ?",
            (limit,)
        ).fetchall()
    return [{"question": r["question"], "answer": r["answer"]} for r in rows]


def stats() -> dict:
    """Return basic counts for display."""
    with _connect() as conn:
        chats = conn.execute("SELECT COUNT(*) FROM chat_log").fetchone()[0]
        visions = conn.execute("SELECT COUNT(*) FROM vision_log").fetchone()[0]
    return {"chat_messages": chats, "vision_interactions": visions}
